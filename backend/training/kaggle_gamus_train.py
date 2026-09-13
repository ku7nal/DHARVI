"""Train the DepthWizard RGB -> height + semantic + boundary model on GAMUS HDF5.

Kaggle usage:

    python kaggle_gamus_train.py \
        --root /kaggle/input/gamus \
        --output-dir /kaggle/working/depthwizard \
        --image-key image \
        --height-key height \
        --class-key classes \
        --dataset-id owner/gamus --dataset-revision 42

Run with --inspect first when the HDF5 dataset keys are unknown. The script
keeps GAMUS's supplied train/val/test directories as the authoritative splits.
It exports a checkpoint containing model configuration and normalization values
needed by the backend inference service.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from app.semantic_contract import BUILDING_CLASS, CLASS_COUNT, CLASS_NAMES
from training.gamus_audit import audit_dataset, paired_samples

MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass(frozen=True)
class Sample:
    image: Path
    height: Path
    classes: Path
    split: Literal["train", "val", "test"]


def h5_datasets(path: Path) -> list[tuple[str, tuple[int, ...], str]]:
    import h5py

    found: list[tuple[str, tuple[int, ...], str]] = []
    with h5py.File(path, "r") as file:
        def visit(name: str, value: object) -> None:
            if isinstance(value, h5py.Dataset):
                found.append((name, tuple(value.shape), str(value.dtype)))

        file.visititems(visit)
    return found


def read_h5(path: Path, key: str | None, kind: str) -> np.ndarray:
    import h5py

    datasets = h5_datasets(path)
    if key is None:
        candidates = []
        for name, shape, _ in datasets:
            dimensions = len(shape)
            has_rgb_channels = dimensions == 3 and (shape[-1] in (3, 4) or shape[0] in (3, 4))
            is_raster = dimensions in (2, 3)
            if kind == "image" and has_rgb_channels:
                candidates.append(name)
            elif kind != "image" and is_raster and not has_rgb_channels:
                candidates.append(name)
        if len(candidates) != 1:
            raise ValueError(
                f"Could not uniquely infer {kind} dataset in {path.name}. "
                f"Candidates={candidates}; pass --{kind}-key explicitly."
            )
        key = candidates[0]

    with h5py.File(path, "r") as file:
        if key not in file:
            raise KeyError(f"HDF5 key {key!r} was not found in {path}")
        values = np.asarray(file[key])

    if values.ndim == 3 and values.shape[0] in (1, 3, 4) and values.shape[-1] not in (1, 3, 4):
        values = np.moveaxis(values, 0, -1)
    if values.ndim == 3 and values.shape[-1] == 1:
        values = values[..., 0]
    if kind == "image" and (values.ndim != 3 or values.shape[-1] < 3):
        raise ValueError(f"Expected RGB HxWx3 data in {path}, got {values.shape}")
    if kind != "image" and values.ndim != 2:
        raise ValueError(f"Expected 2D raster data in {path}, got {values.shape}")
    return values[..., :3] if kind == "image" else values


def index_split(root: Path, split: Literal["train", "val", "test"]) -> list[Sample]:
    samples: list[Sample] = []
    for image, height, classes in paired_samples(root, split):
        samples.append(Sample(image, height, classes, split))
    return samples


def resize(values: np.ndarray, size: int, nearest: bool = False) -> np.ndarray:
    image = Image.fromarray(values)
    resampling = Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR
    return np.asarray(image.resize((size, size), resampling))


def boundary_mask(building: np.ndarray) -> np.ndarray:
    padded = np.pad(building, 1, constant_values=False)
    interior = (
        padded[1:-1, 1:-1]
        & padded[:-2, 1:-1]
        & padded[2:, 1:-1]
        & padded[1:-1, :-2]
        & padded[1:-1, 2:]
    )
    return building & ~interior


class GamusDataset:
    def __init__(self, samples, image_key, height_key, class_key, image_size, train):
        self.samples = samples
        self.image_key = image_key
        self.height_key = height_key
        self.class_key = class_key
        self.image_size = image_size
        self.train = train

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        import torch

        sample = self.samples[index]
        image = read_h5(sample.image, self.image_key, "image").astype(np.float32)
        if image.max() <= 1.5:
            image *= 255.0
        image = np.clip(image, 0, 255).astype(np.uint8)
        height = read_h5(sample.height, self.height_key, "height").astype(np.float32)
        classes = read_h5(sample.classes, self.class_key, "classes").astype(np.int64)
        if image.shape[:2] != height.shape or height.shape != classes.shape:
            raise ValueError(f"Spatial mismatch in {sample.image.name}: {image.shape}, {height.shape}, {classes.shape}")

        valid = np.isfinite(height) & np.isin(classes, np.arange(CLASS_COUNT))
        height = np.nan_to_num(height, nan=0.0, posinf=0.0, neginf=0.0)
        classes = np.where(valid, classes, 0)
        boundary = boundary_mask(classes == BUILDING_CLASS)

        image = resize(image, self.image_size)
        height = resize(height, self.image_size)
        classes = resize(classes.astype(np.uint8), self.image_size, nearest=True).astype(np.int64)
        valid = resize(valid.astype(np.uint8), self.image_size, nearest=True).astype(bool)
        boundary = resize(boundary.astype(np.uint8), self.image_size, nearest=True).astype(np.float32)

        if self.train:
            if random.random() < 0.5:
                image, height, classes, valid, boundary = [np.flip(value, 1).copy() for value in (image, height, classes, valid, boundary)]
            if random.random() < 0.5:
                image, height, classes, valid, boundary = [np.flip(value, 0).copy() for value in (image, height, classes, valid, boundary)]
            turns = random.randrange(4)
            image, height, classes, valid, boundary = [np.rot90(value, turns).copy() for value in (image, height, classes, valid, boundary)]
            if random.random() < 0.35:
                image = np.clip(image.astype(np.float32) * random.uniform(0.85, 1.15), 0, 255).astype(np.uint8)

        image = (image.astype(np.float32) / 255.0 - MEAN) / STD
        return {
            "image": torch.from_numpy(image.transpose(2, 0, 1)).float(),
            "height": torch.from_numpy(height[None]).float(),
            "classes": torch.from_numpy(classes).long(),
            "valid": torch.from_numpy(valid[None]).bool(),
            "boundary": torch.from_numpy(boundary[None]).float(),
        }


class DepthAnythingMultitask:
    def __init__(self, base, torch_module):
        import torch.nn as nn

        self.torch = torch_module
        self.nn = nn
        self.base = base
        channels = int(getattr(base.config, "hidden_size", getattr(base.config, "reassemble_hidden_size", 384)))
        self.semantic_head = nn.Sequential(nn.Conv2d(channels, 256, 3, padding=1), nn.GELU(), nn.Conv2d(256, CLASS_COUNT, 1))
        self.boundary_head = nn.Sequential(nn.Conv2d(channels, 128, 3, padding=1), nn.GELU(), nn.Conv2d(128, 1, 1))

    def module(self):
        import torch.nn as nn
        parent = self

        class Module(nn.Module):
            def __init__(self):
                super().__init__()
                self.base = parent.base
                self.semantic_head = parent.semantic_head
                self.boundary_head = parent.boundary_head

            def forward(self, pixel_values):
                output = self.base(pixel_values=pixel_values, output_hidden_states=True)
                height = self.torch.nn.functional.interpolate(output.predicted_depth[:, None], size=pixel_values.shape[-2:], mode="bilinear", align_corners=True)
                features = output.hidden_states[-1]
                if features.ndim == 3:
                    side = int(math.sqrt(features.shape[1]))
                    if side * side != features.shape[1]:
                        features = features[:, 1:]
                        side = int(math.sqrt(features.shape[1]))
                    features = features[:, :side * side].transpose(1, 2).reshape(features.shape[0], features.shape[2], side, side)
                semantic = self.torch.nn.functional.interpolate(self.semantic_head(features), size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
                boundary = self.torch.nn.functional.interpolate(self.boundary_head(features), size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
                return {"height": self.torch.relu(height), "semantic": semantic, "boundary": boundary}

        return Module()


def multitask_loss(outputs, target):
    import torch.nn.functional as F

    valid = target["valid"].float()
    height_loss = (F.smooth_l1_loss(outputs["height"], target["height"], reduction="none") * valid).sum() / valid.sum().clamp_min(1)
    semantic_loss = F.cross_entropy(outputs["semantic"], target["classes"], reduction="none")
    semantic_loss = (semantic_loss * valid[:, 0]).sum() / valid[:, 0].sum().clamp_min(1)
    boundary_loss = (F.binary_cross_entropy_with_logits(outputs["boundary"], target["boundary"], reduction="none") * valid).sum() / valid.sum().clamp_min(1)
    return height_loss + 0.35 * semantic_loss + 0.25 * boundary_loss


def run_epoch(model, loader, device, optimizer=None, scaler=None):
    import torch

    training = optimizer is not None
    model.train(training)
    total = 0.0
    count = 0
    for batch in loader:
        batch = {key: value.to(device, non_blocking=True) for key, value in batch.items()}
        if training:
            optimizer.zero_grad(set_to_none=True)
        autocast_context = torch.autocast(device_type="cuda") if device.type == "cuda" else nullcontext()
        with autocast_context:
            outputs = model(batch["image"])
            loss = multitask_loss(outputs, batch)
        if training:
            if scaler is not None:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
        total += float(loss.detach())
        count += 1
    return total / max(count, 1)


def evaluate_loader(model, loader, device) -> dict[str, object]:
    """Return the issue's validation/test metrics from one authoritative split."""
    import torch

    heights: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    predicted_labels: list[np.ndarray] = []
    target_labels: list[np.ndarray] = []
    valid_masks: list[np.ndarray] = []
    predicted_boundaries: list[np.ndarray] = []
    target_boundaries: list[np.ndarray] = []
    model.eval()
    with torch.inference_mode():
        for batch in loader:
            batch = {key: value.to(device, non_blocking=True) for key, value in batch.items()}
            outputs = model(batch["image"])
            heights.append(outputs["height"][:, 0].cpu().numpy())
            targets.append(batch["height"][:, 0].cpu().numpy())
            predicted_labels.append(outputs["semantic"].argmax(dim=1).cpu().numpy())
            target_labels.append(batch["classes"].cpu().numpy())
            valid_masks.append(batch["valid"][:, 0].cpu().numpy().astype(bool))
            predicted_boundaries.append((torch.sigmoid(outputs["boundary"])[:, 0] >= 0.5).cpu().numpy())
            target_boundaries.append((batch["boundary"][:, 0] >= 0.5).cpu().numpy())

    predicted_height = np.concatenate(heights)[np.concatenate(valid_masks)]
    target_height = np.concatenate(targets)[np.concatenate(valid_masks)]
    predicted = np.concatenate(predicted_labels)
    target = np.concatenate(target_labels)
    valid = np.concatenate(valid_masks)
    predicted_boundary = np.concatenate(predicted_boundaries) & valid
    target_boundary = np.concatenate(target_boundaries) & valid
    difference = predicted_height - target_height
    predicted_centered = predicted_height - predicted_height.mean()
    target_centered = target_height - target_height.mean()
    denominator = float(np.sqrt(np.sum(predicted_centered**2) * np.sum(target_centered**2)))
    per_class_iou: dict[str, float] = {}
    for class_id, class_name in enumerate(CLASS_NAMES):
        predicted_class = (predicted == class_id) & valid
        target_class = (target == class_id) & valid
        union = np.sum(predicted_class | target_class)
        per_class_iou[class_name] = float(np.sum(predicted_class & target_class) / union) if union else 0.0
    building_intersection = np.sum((predicted == BUILDING_CLASS) & (target == BUILDING_CLASS) & valid)
    building_union = np.sum(((predicted == BUILDING_CLASS) | (target == BUILDING_CLASS)) & valid)
    boundary_tp = np.sum(predicted_boundary & target_boundary)
    boundary_denominator = np.sum(predicted_boundary) + np.sum(target_boundary)
    return {
        "height_rmse": float(np.sqrt(np.mean(difference**2))) if difference.size else 0.0,
        "height_mae": float(np.mean(np.abs(difference))) if difference.size else 0.0,
        "height_correlation": float(np.sum(predicted_centered * target_centered) / denominator) if denominator else 0.0,
        "per_class_iou": per_class_iou,
        "building_iou": float(building_intersection / building_union) if building_union else 0.0,
        "building_boundary_f1": float(2 * boundary_tp / boundary_denominator) if boundary_denominator else 0.0,
    }


def inspect(root: Path) -> None:
    for split in ("train", "val", "test"):
        path = next((root / "images" / split).glob("*.h5"))
        print(split, path)
        for item in h5_datasets(path):
            print(" ", item)


def main() -> None:
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForDepthEstimation

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("/kaggle/working/depthwizard"))
    parser.add_argument("--model-id", default="depth-anything/Depth-Anything-V2-Base-hf")
    parser.add_argument("--image-key")
    parser.add_argument("--height-key")
    parser.add_argument("--class-key")
    parser.add_argument("--dataset-id", default=os.getenv("KAGGLE_DATASET_ID"))
    parser.add_argument("--dataset-revision", default=os.getenv("KAGGLE_DATASET_REVISION"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--image-size", type=int, default=518)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()

    if args.inspect:
        inspect(args.root)
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest or args.output_dir / "gamus_manifest.json"
    manifest = audit_dataset(
        args.root,
        manifest_path,
        dataset_id=args.dataset_id,
        dataset_revision=args.dataset_revision,
        image_key=args.image_key,
        height_key=args.height_key,
        class_key=args.class_key,
    )
    print(json.dumps({
        "dataset": manifest["dataset"],
        "total_sample_count": manifest["total_sample_count"],
        "splits": {split: report["sample_count"] for split, report in manifest["splits"].items()},
        "manifest": str(manifest_path),
    }, indent=2))
    if args.audit_only:
        return

    random.seed(7)
    np.random.seed(7)
    torch.manual_seed(7)
    train = index_split(args.root, "train")
    validation = index_split(args.root, "val")
    test = index_split(args.root, "test")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_loader = DataLoader(GamusDataset(train, args.image_key, args.height_key, args.class_key, args.image_size, True), batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=device.type == "cuda")
    validation_loader = DataLoader(GamusDataset(validation, args.image_key, args.height_key, args.class_key, args.image_size, False), batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=device.type == "cuda")
    test_loader = DataLoader(GamusDataset(test, args.image_key, args.height_key, args.class_key, args.image_size, False), batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=device.type == "cuda")

    base = AutoModelForDepthEstimation.from_pretrained(args.model_id)
    model = DepthAnythingMultitask(base, torch).module().to(device)
    optimizer = torch.optim.AdamW([
        {"params": model.base.parameters(), "lr": 1e-5},
        {"params": model.semantic_head.parameters(), "lr": 1e-4},
        {"params": model.boundary_head.parameters(), "lr": 1e-4},
    ], weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=3, factor=0.5)
    scaler = torch.cuda.amp.GradScaler(enabled=device.type == "cuda")
    best = float("inf")
    stale = 0

    for epoch in range(args.epochs):
        train_loss = run_epoch(model, train_loader, device, optimizer, scaler)
        val_loss = run_epoch(model, validation_loader, device)
        validation_metrics = evaluate_loader(model, validation_loader, device)
        scheduler.step(val_loss)
        print(json.dumps({"epoch": epoch + 1, "train_loss": train_loss, "val_loss": val_loss, "validation": validation_metrics}))
        if val_loss < best:
            best = val_loss
            stale = 0
            torch.save({
                "state_dict": model.state_dict(),
                "model_id": args.model_id,
                "image_size": args.image_size,
                "class_names": CLASS_NAMES,
                "mean": MEAN.tolist(),
                "std": STD.tolist(),
                "h5_keys": {"image": args.image_key, "height": args.height_key, "classes": args.class_key},
                "val_loss": val_loss,
                "validation_metrics": validation_metrics,
            }, args.output_dir / "depthwizard_gamus_best.pth")
        else:
            stale += 1
            if stale >= 7:
                break

    checkpoint = torch.load(args.output_dir / "depthwizard_gamus_best.pth", map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"])
    test_loss = run_epoch(model, test_loader, device)
    test_metrics = evaluate_loader(model, test_loader, device)
    checkpoint["test_metrics"] = test_metrics
    checkpoint["validation_metrics"] = checkpoint.get("validation_metrics", {})
    torch.save(checkpoint, args.output_dir / "depthwizard_gamus_best.pth")
    metrics = {
        "best_val_loss": best,
        "test_loss": test_loss,
        "validation": checkpoint["validation_metrics"],
        "test": test_metrics,
        "train_samples": len(train),
        "validation_samples": len(validation),
        "test_samples": len(test),
    }
    (args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (args.output_dir / "model_config.json").write_text(json.dumps({"model_id": args.model_id, "image_size": args.image_size, "class_names": CLASS_NAMES, "h5_keys": checkpoint["h5_keys"]}, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
