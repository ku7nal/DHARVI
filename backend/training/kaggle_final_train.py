"""Final full-data GAMUS training pipeline for DepthWizard.

The script is intentionally notebook-friendly. It performs an exhaustive
alignment audit, native-resolution crop training, multiscale Depth Anything V2
fine-tuning, full-image tiled evaluation, and production checkpoint export.

Smoke test:
    python kaggle_final_train.py --root /kaggle/input/gamus \
      --output-dir /kaggle/working/depthwizard_smoke --smoke-test \
      --dataset-id earthflow/GAMUS --dataset-revision REVISION

Final run:
    python kaggle_final_train.py --root /kaggle/input/gamus \
      --output-dir /kaggle/working/depthwizard_final \
      --dataset-id earthflow/GAMUS --dataset-revision REVISION
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image

try:
    from app.semantic_contract import BUILDING_CLASS, CLASS_COUNT, CLASS_NAMES
except ModuleNotFoundError:  # Standalone Kaggle execution fallback.
    BUILDING_CLASS = 3
    CLASS_COUNT = 7
    CLASS_NAMES = ("others", "ground", "low_vegetation", "building", "water", "road", "tree")

try:
    from training.depthwizard_model import build_depthwizard_model
except ModuleNotFoundError:
    from depthwizard_model import build_depthwizard_model

try:
    from training.gamus_audit import paired_samples
except ModuleNotFoundError:
    import re

    _PAIR_SUFFIXES = ("_IMG", "_RGB", "_AGL", "_DSM", "_HEIGHT", "_CLASS", "_CLASSES", "_CLS", "_LABEL", "_LABELS", "_SEMANTIC", "_SEMANTICS")

    def _pair_key(path: Path) -> str:
        value = path.stem.upper()
        changed = True
        while changed:
            changed = False
            for suffix in _PAIR_SUFFIXES:
                if value.endswith(suffix):
                    value = value[:-len(suffix)]
                    changed = True
                    break
        return value

    def paired_samples(root: Path, split: str) -> list[tuple[Path, Path, Path]]:
        directories = {name: root / name / split for name in ("images", "heights", "classes")}
        indexes: dict[str, dict[str, list[Path]]] = {}
        for kind, directory in directories.items():
            index: dict[str, list[Path]] = {}
            for path in sorted(item for item in directory.rglob("*") if item.is_file()):
                index.setdefault(_pair_key(path), []).append(path)
            indexes[kind] = index
        result = []
        for key in sorted(indexes["images"]):
            image = indexes["images"].get(key, [])
            height = indexes["heights"].get(key, [])
            classes = indexes["classes"].get(key, [])
            if len(image) != 1 or len(height) != 1 or len(classes) != 1:
                raise ValueError(f"Unpaired sample {split}:{key}: image={len(image)}, height={len(height)}, classes={len(classes)}")
            result.append((image[0], height[0], classes[0]))
        if not result:
            raise ValueError(f"No paired samples found in {root} for split {split}")
        return result

MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Sample:
    image: Path
    height: Path
    classes: Path
    split: Literal["train", "val", "test"]
    group: str


def read_h5(path: Path, key: str, kind: str) -> np.ndarray:
    import h5py

    with h5py.File(path, "r") as file:
        if key not in file:
            raise KeyError(f"HDF5 key {key!r} was not found in {path}; available={list(file.keys())}")
        value = np.asarray(file[key])
    if kind == "image":
        if value.ndim == 3 and value.shape[0] in (1, 3, 4) and value.shape[-1] not in (1, 3, 4):
            value = np.moveaxis(value, 0, -1)
        if value.ndim != 3 or value.shape[-1] < 3:
            raise ValueError(f"Expected RGB HxWx3 data in {path}, got {value.shape}")
        value = value[..., :3]
    else:
        if value.ndim == 3 and value.shape[0] == 1:
            value = value[0]
        if value.ndim != 2:
            raise ValueError(f"Expected 2D {kind} raster in {path}, got {value.shape}")
    return np.array(value, copy=True)


def sample_group(path: Path, root: Path) -> str:
    relative = path.relative_to(root / "images")
    if len(relative.parts) > 1:
        return "/".join(relative.parts[:-1])
    return relative.stem.rsplit("_", 1)[0]


def index_samples(root: Path) -> dict[str, list[Sample]]:
    indexed: dict[str, list[Sample]] = {}
    for split in SPLITS:
        values = []
        for image, height, classes in paired_samples(root, split):
            values.append(Sample(image, height, classes, split, sample_group(image, root)))
        indexed[split] = values
    return indexed


def load_triplet(sample: Sample, keys: dict[str, str]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    image = read_h5(sample.image, keys["image"], "image")
    height = read_h5(sample.height, keys["height"], "height").astype(np.float32, copy=False)
    classes = read_h5(sample.classes, keys["classes"], "classes").astype(np.int64, copy=False)
    if image.shape[:2] != height.shape or height.shape != classes.shape:
        raise ValueError(f"Spatial mismatch in {sample.image.name}: {image.shape}, {height.shape}, {classes.shape}")
    if image.dtype != np.uint8:
        image = image.astype(np.float32)
        if float(np.nanmax(image)) <= 1.5:
            image *= 255.0
        image = np.clip(image, 0, 255).astype(np.uint8)
    valid = np.isfinite(height) & np.isin(classes, np.arange(CLASS_COUNT))
    height = np.nan_to_num(height, nan=0.0, posinf=0.0, neginf=0.0)
    classes = np.where(valid, classes, 0).astype(np.int64)
    return image, height, classes, valid


def building_boundary(classes: np.ndarray) -> np.ndarray:
    building = classes == BUILDING_CLASS
    padded = np.pad(building, 1, mode="constant", constant_values=False)
    interior = (
        padded[1:-1, 1:-1]
        & padded[:-2, 1:-1]
        & padded[2:, 1:-1]
        & padded[1:-1, :-2]
        & padded[1:-1, 2:]
    )
    return building & ~interior


def audit_dataset(root: Path, samples: dict[str, list[Sample]], keys: dict[str, str], output: Path, dataset_id: str, revision: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 2,
        "dataset": {"id": dataset_id, "revision": revision, "root": str(root.resolve())},
        "class_names": list(CLASS_NAMES),
        "splits": {},
    }
    for split, values in samples.items():
        counts = np.zeros(CLASS_COUNT, dtype=np.int64)
        finite_values: list[np.ndarray] = []
        invalid = 0
        groups: dict[str, int] = {}
        for sample in values:
            image, height, classes, valid = load_triplet(sample, keys)
            counts += np.bincount(classes[valid].reshape(-1), minlength=CLASS_COUNT)
            finite = height[np.isfinite(height)]
            if finite.size:
                stride = max(1, finite.size // 4096)
                finite_values.append(finite[::stride][:4096])
            invalid += int((~valid).sum())
            groups[sample.group] = groups.get(sample.group, 0) + 1
            if image.shape[:2] != classes.shape:
                raise ValueError(f"Alignment audit failed for {sample.image}")
        values_flat = np.concatenate(finite_values) if finite_values else np.zeros(1, dtype=np.float32)
        report["splits"][split] = {
            "sample_count": len(values),
            "groups": groups,
            "class_counts": counts.tolist(),
            "invalid_pixel_count": invalid,
            "height_percentiles": {str(p): float(np.percentile(values_flat, p)) for p in (0, 50, 75, 90, 95, 99, 99.5, 99.9, 100)},
        }
    report["total_sample_count"] = sum(len(values) for values in samples.values())
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report


def resize_array(value: np.ndarray, size: tuple[int, int], nearest: bool = False) -> np.ndarray:
    if value.dtype == np.bool_:
        value = value.astype(np.uint8)
    image = Image.fromarray(value)
    mode = Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR
    return np.asarray(image.resize((size[1], size[0]), mode))


def choose_crop(mask: np.ndarray, crop_size: int, rng: np.random.Generator) -> tuple[int, int]:
    height, width = mask.shape
    if height <= crop_size or width <= crop_size:
        return max(0, (height - crop_size) // 2), max(0, (width - crop_size) // 2)
    ys, xs = np.where(mask)
    if len(ys) == 0:
        center_y = int(rng.integers(crop_size // 2, height - crop_size // 2 + 1))
        center_x = int(rng.integers(crop_size // 2, width - crop_size // 2 + 1))
    else:
        point = int(rng.integers(len(ys)))
        center_y, center_x = int(ys[point]), int(xs[point])
    top = int(np.clip(center_y - crop_size // 2, 0, height - crop_size))
    left = int(np.clip(center_x - crop_size // 2, 0, width - crop_size))
    return top, left


def reflect_crop(value: np.ndarray, top: int, left: int, size: int, constant: int | float | bool = 0) -> np.ndarray:
    height, width = value.shape[:2]
    pad_bottom = max(0, top + size - height)
    pad_right = max(0, left + size - width)
    if pad_bottom or pad_right:
        if value.ndim == 3:
            pad = ((0, pad_bottom), (0, pad_right), (0, 0))
        else:
            pad = ((0, pad_bottom), (0, pad_right))
        mode = "reflect" if height > 1 and width > 1 else "constant"
        if mode == "constant":
            value = np.pad(value, pad, mode=mode, constant_values=constant)
        else:
            value = np.pad(value, pad, mode=mode)
    return value[top : top + size, left : left + size]


def augment(image: np.ndarray, height: np.ndarray, classes: np.ndarray, valid: np.ndarray, boundary: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, ...]:
    values = [image, height, classes, valid, boundary]
    if rng.random() < 0.5:
        values = [np.flip(value, axis=1).copy() for value in values]
    if rng.random() < 0.5:
        values = [np.flip(value, axis=0).copy() for value in values]
    turns = int(rng.integers(4))
    values = [np.rot90(value, turns).copy() for value in values]
    image, height, classes, valid, boundary = values

    rgb = image.astype(np.float32)
    if rng.random() < 0.6:
        rgb = rgb * float(rng.uniform(0.85, 1.15)) + float(rng.uniform(-8.0, 8.0))
    if rng.random() < 0.4:
        mean = rgb.mean(axis=(0, 1), keepdims=True)
        rgb = (rgb - mean) * float(rng.uniform(0.9, 1.1)) + mean
    if rng.random() < 0.25:
        gamma = float(rng.uniform(0.9, 1.1))
        rgb = 255.0 * np.power(np.clip(rgb / 255.0, 0.0, 1.0), gamma)
    if rng.random() < 0.15:
        rgb += rng.normal(0.0, 2.0, size=rgb.shape)
    image = np.clip(rgb, 0, 255).astype(np.uint8)
    return image, height, classes, valid, boundary


class GamusCropDataset:
    def __init__(self, samples: list[Sample], keys: dict[str, str], crop_size: int, height_scale: float, class_weights: np.ndarray, train: bool, crops_per_sample: int, seed: int = 7) -> None:
        self.samples = samples
        self.keys = keys
        self.crop_size = crop_size
        self.height_scale = height_scale
        self.class_weights = class_weights
        self.train = train
        self.crops_per_sample = max(1, crops_per_sample if train else 1)
        self.seed = seed
        self.epoch = 0

    def __len__(self) -> int:
        return len(self.samples) * self.crops_per_sample

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __getitem__(self, index: int) -> dict[str, Any]:
        import torch

        sample = self.samples[index % len(self.samples)]
        image, height, classes, valid = load_triplet(sample, self.keys)
        boundary = building_boundary(classes).astype(np.float32)
        rng = np.random.default_rng(self.seed + self.epoch * 100003 + index * 17)
        if self.train:
            choice = float(rng.random())
            if choice < 0.25:
                focus = classes == BUILDING_CLASS
            elif choice < 0.40:
                focus = height >= np.percentile(height[valid], 90) if valid.any() else valid
            elif choice < 0.50:
                focus = boundary > 0
            else:
                focus = valid
            top, left = choose_crop(focus, self.crop_size, rng)
        else:
            top, left = choose_crop(valid, self.crop_size, rng)
        image = reflect_crop(image, top, left, self.crop_size)
        height = reflect_crop(height, top, left, self.crop_size)
        classes = reflect_crop(classes, top, left, self.crop_size)
        valid = reflect_crop(valid, top, left, self.crop_size, constant=False).astype(bool)
        boundary = reflect_crop(boundary, top, left, self.crop_size)
        if self.train:
            image, height, classes, valid, boundary = augment(image, height, classes, valid, boundary, rng)
        tensor_image = ((image.astype(np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1)
        return {
            "image": torch.from_numpy(np.ascontiguousarray(tensor_image)).float(),
            "height": torch.from_numpy(np.ascontiguousarray((height / self.height_scale)[None])).float(),
            "classes": torch.from_numpy(np.ascontiguousarray(classes)).long(),
            "valid": torch.from_numpy(np.ascontiguousarray(valid[None])).bool(),
            "boundary": torch.from_numpy(np.ascontiguousarray(boundary[None])).float(),
        }


def make_class_weights(samples: list[Sample], keys: dict[str, str]) -> tuple[np.ndarray, np.ndarray]:
    counts = np.zeros(CLASS_COUNT, dtype=np.float64)
    for sample in samples:
        _, _, classes, valid = load_triplet(sample, keys)
        counts += np.bincount(classes[valid].reshape(-1), minlength=CLASS_COUNT)
    total = max(float(counts.sum()), 1.0)
    weights = np.sqrt(total / (CLASS_COUNT * np.maximum(counts, 1.0)))
    weights = np.clip(weights / max(float(weights.mean()), 1e-6), 0.5, 3.0)
    return counts.astype(np.int64), weights.astype(np.float32)


def multitask_loss(outputs: dict[str, Any], target: dict[str, Any], class_weights: Any, height_scale: float, semantic_weight: float, boundary_weight: float) -> dict[str, Any]:
    import torch
    import torch.nn.functional as F

    valid = target["valid"].float()
    target_height = target["height"]
    target_classes = target["classes"]
    building = (target_classes == BUILDING_CLASS).float().unsqueeze(1)
    tall = (target_height > 0.15).float()
    pixel_weight = (1.0 + 1.25 * building + 0.75 * tall) * valid
    pixel_weight = pixel_weight / pixel_weight.sum(dim=(1, 2, 3), keepdim=True).clamp_min(1.0) * valid.sum(dim=(1, 2, 3), keepdim=True).clamp_min(1.0)

    robust = F.smooth_l1_loss(outputs["height"], target_height, reduction="none", beta=0.05)
    height_loss = (robust * pixel_weight).sum() / pixel_weight.sum().clamp_min(1.0)
    pred_dx = outputs["height"][:, :, :, 1:] - outputs["height"][:, :, :, :-1]
    target_dx = target_height[:, :, :, 1:] - target_height[:, :, :, :-1]
    pred_dy = outputs["height"][:, :, 1:, :] - outputs["height"][:, :, :-1, :]
    target_dy = target_height[:, :, 1:, :] - target_height[:, :, :-1, :]
    valid_x = valid[:, :, :, 1:] * valid[:, :, :, :-1]
    valid_y = valid[:, :, 1:, :] * valid[:, :, :-1, :]
    gradient_loss = ((pred_dx - target_dx).abs() * valid_x).sum() / valid_x.sum().clamp_min(1.0)
    gradient_loss += ((pred_dy - target_dy).abs() * valid_y).sum() / valid_y.sum().clamp_min(1.0)
    log_loss = ((torch.log1p(outputs["height"] * height_scale) - torch.log1p(target_height * height_scale)).abs() * valid).sum() / valid.sum().clamp_min(1.0)

    semantic = F.cross_entropy(outputs["semantic"], target_classes, weight=class_weights, reduction="none")
    semantic_loss = (semantic * valid[:, 0]).sum() / valid[:, 0].sum().clamp_min(1.0)
    probabilities = torch.softmax(outputs["semantic"], dim=1)
    one_hot = F.one_hot(target_classes, CLASS_COUNT).permute(0, 3, 1, 2).float()
    dice_numerator = 2.0 * (probabilities * one_hot * valid).sum(dim=(0, 2, 3)) + 1e-5
    dice_denominator = (probabilities * valid).sum(dim=(0, 2, 3)) + (one_hot * valid).sum(dim=(0, 2, 3)) + 1e-5
    dice_loss = 1.0 - (dice_numerator / dice_denominator).mean()
    semantic_loss = semantic_loss + 0.5 * dice_loss

    boundary_target = target["boundary"]
    positive = boundary_target.sum().clamp_min(1.0)
    negative = (valid - boundary_target * valid).sum().clamp_min(1.0)
    pos_weight = (negative / positive).clamp(1.0, 20.0)
    boundary_raw = F.binary_cross_entropy_with_logits(outputs["boundary"], boundary_target, pos_weight=pos_weight, reduction="none")
    boundary_loss = (boundary_raw * valid).sum() / valid.sum().clamp_min(1.0)
    total = height_loss + 0.20 * gradient_loss + 0.10 * log_loss + semantic_weight * semantic_loss + boundary_weight * boundary_loss
    return {"total": total, "height": height_loss, "gradient": gradient_loss, "log": log_loss, "semantic": semantic_loss, "boundary": boundary_loss}


def amp_context(device: Any):
    import torch

    return torch.autocast(device_type="cuda", dtype=torch.float16) if device.type == "cuda" else nullcontext()


def train_epoch(model: Any, loader: Any, device: Any, optimizer: Any, scaler: Any, scheduler: Any, class_weights: Any, height_scale: float, accumulation: int, epoch: int, total_epochs: int) -> dict[str, float]:
    import torch

    model.train()
    loader.dataset.set_epoch(epoch)
    totals: dict[str, float] = {}
    optimizer.zero_grad(set_to_none=True)
    for step, batch in enumerate(loader):
        batch = {key: value.to(device, non_blocking=True) for key, value in batch.items()}
        progress = epoch / max(total_epochs, 1)
        semantic_weight = 0.15 * min(1.0, max(0.0, (epoch - 2) / 5.0))
        boundary_weight = 0.05 * min(1.0, max(0.0, (epoch - 2) / 5.0))
        with amp_context(device):
            outputs = model(batch["image"])
            losses = multitask_loss(outputs, batch, class_weights, height_scale, semantic_weight, boundary_weight)
            loss = losses["total"] / accumulation
        scaler.scale(loss).backward()
        if (step + 1) % accumulation == 0 or step + 1 == len(loader):
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            optimizer.zero_grad(set_to_none=True)
        for key, value in losses.items():
            totals[key] = totals.get(key, 0.0) + float(value.detach())
    return {key: value / max(len(loader), 1) for key, value in totals.items()}


def tile_starts(length: int, tile_size: int, overlap: float) -> list[int]:
    if length <= tile_size:
        return [0]
    stride = max(1, round(tile_size * (1.0 - overlap)))
    starts = list(range(0, length - tile_size + 1, stride))
    if starts[-1] != length - tile_size:
        starts.append(length - tile_size)
    return starts


def preprocess(image: np.ndarray, torch_module: Any) -> Any:
    values = (image.astype(np.float32) / 255.0 - MEAN) / STD
    return torch_module.from_numpy(np.ascontiguousarray(values.transpose(2, 0, 1))).float().unsqueeze(0)


def tiled_predict(model: Any, image: np.ndarray, device: Any, tile_size: int, overlap: float, height_scale: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    import torch

    h, w = image.shape[:2]
    height_sum = np.zeros((h, w), dtype=np.float64)
    semantic_sum = np.zeros((CLASS_COUNT, h, w), dtype=np.float64)
    boundary_sum = np.zeros((h, w), dtype=np.float64)
    weight_sum = np.zeros((h, w), dtype=np.float64)
    window_1d = np.maximum(np.hanning(tile_size), 1e-3).astype(np.float32)
    window = np.outer(window_1d, window_1d)
    model.eval()
    with torch.inference_mode():
        for top in tile_starts(h, tile_size, overlap):
            for left in tile_starts(w, tile_size, overlap):
                bottom = min(top + tile_size, h)
                right = min(left + tile_size, w)
                tile = image[top:bottom, left:right]
                pad_h, pad_w = tile_size - tile.shape[0], tile_size - tile.shape[1]
                if pad_h or pad_w:
                    tile = np.pad(tile, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect")
                tensor = preprocess(tile, torch).to(device)
                output = model(tensor)
                flipped_tensor = preprocess(np.ascontiguousarray(tile[:, ::-1]), torch).to(device)
                flipped = model(flipped_tensor)
                predicted_height = (output["height"] + torch.flip(flipped["height"], dims=[3]))[0, 0].cpu().numpy() * 0.5 * height_scale
                predicted_semantic = (output["semantic"] + torch.flip(flipped["semantic"], dims=[3]))[0].cpu().numpy() * 0.5
                predicted_boundary = (output["boundary"] + torch.flip(flipped["boundary"], dims=[3]))[0, 0].cpu().numpy() * 0.5
                tile_h, tile_w = bottom - top, right - left
                blend = window[:tile_h, :tile_w]
                height_sum[top:bottom, left:right] += predicted_height[:tile_h, :tile_w] * blend
                semantic_sum[:, top:bottom, left:right] += predicted_semantic[:, :tile_h, :tile_w] * blend
                boundary_sum[top:bottom, left:right] += predicted_boundary[:tile_h, :tile_w] * blend
                weight_sum[top:bottom, left:right] += blend
    denominator = np.maximum(weight_sum, 1e-6)
    return (height_sum / denominator).astype(np.float32), (semantic_sum / denominator[None]).astype(np.float32), (boundary_sum / denominator).astype(np.float32)


def pearson(predicted: np.ndarray, target: np.ndarray) -> float:
    if predicted.size < 2 or float(np.std(predicted)) < 1e-8 or float(np.std(target)) < 1e-8:
        return float("nan")
    return float(np.corrcoef(predicted, target)[0, 1])


def boundary_f1(predicted: np.ndarray, target: np.ndarray) -> float:
    predicted = predicted.astype(bool)
    target = target.astype(bool)
    predicted_count = int(predicted.sum())
    target_count = int(target.sum())
    true_positive = int((predicted & target).sum())
    return float(2 * true_positive / max(predicted_count + target_count, 1))


def sample_metrics(predicted_height: np.ndarray, target_height: np.ndarray, predicted_logits: np.ndarray, target_classes: np.ndarray, predicted_boundary_logits: np.ndarray, valid: np.ndarray) -> dict[str, Any]:
    predicted_classes = predicted_logits.argmax(axis=0)
    mask = valid.astype(bool)
    difference = (predicted_height - target_height)[mask]
    pred_values = predicted_height[mask]
    target_values = target_height[mask]
    per_class_iou = {}
    for class_id, name in enumerate(CLASS_NAMES):
        pred_mask = (predicted_classes == class_id) & mask
        target_mask = (target_classes == class_id) & mask
        union = int((pred_mask | target_mask).sum())
        per_class_iou[name] = float((pred_mask & target_mask).sum() / union) if union else float("nan")
    pred_building = (predicted_classes == BUILDING_CLASS) & mask
    target_building = (target_classes == BUILDING_CLASS) & mask
    building_union = int((pred_building | target_building).sum())
    building_intersection = int((pred_building & target_building).sum())
    return {
        "rmse": float(np.sqrt(np.mean(difference ** 2))) if difference.size else float("nan"),
        "mae": float(np.mean(np.abs(difference))) if difference.size else float("nan"),
        "correlation": pearson(pred_values, target_values),
        "per_class_iou": per_class_iou,
        "semantic_miou": float(np.nanmean(list(per_class_iou.values()))),
        "building_iou": float(building_intersection / building_union) if building_union else float("nan"),
        "building_boundary_f1": boundary_f1(pred_building, target_building),
        "boundary_f1": boundary_f1((predicted_boundary_logits >= 0.0) & mask, building_boundary(target_classes) & mask),
        "valid_pixels": int(mask.sum()),
    }


def clean_json(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    if isinstance(value, np.generic):
        return clean_json(value.item())
    return value


def aggregate_metrics(per_sample: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_sample:
        return {}
    result: dict[str, Any] = {}
    for key in ("rmse", "mae", "correlation", "semantic_miou", "building_iou", "building_boundary_f1", "boundary_f1"):
        values = np.asarray([item[key] for item in per_sample], dtype=np.float64)
        result[f"macro_{key}"] = float(np.nanmean(values)) if np.isfinite(values).any() else None
        result[f"std_{key}"] = float(np.nanstd(values)) if np.isfinite(values).any() else None
    result["pooled_valid_pixels"] = int(sum(item["valid_pixels"] for item in per_sample))
    class_values: dict[str, list[float]] = {name: [] for name in CLASS_NAMES}
    for item in per_sample:
        for name, value in item["per_class_iou"].items():
            if math.isfinite(value):
                class_values[name].append(value)
    result["per_class_iou"] = {name: float(np.mean(values)) if values else None for name, values in class_values.items()}
    result["sample_count"] = len(per_sample)
    return result


def evaluate(model: Any, samples: list[Sample], keys: dict[str, str], device: Any, tile_size: int, overlap: float, height_scale: float, output_dir: Path | None = None, max_visuals: int = 4) -> dict[str, Any]:
    import matplotlib.pyplot as plt

    per_sample = []
    groups: dict[str, list[dict[str, Any]]] = {}
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    for index, sample in enumerate(samples):
        image, height, classes, valid = load_triplet(sample, keys)
        predicted_height, predicted_semantic, predicted_boundary = tiled_predict(model, image, device, tile_size, overlap, height_scale)
        metrics = sample_metrics(predicted_height, height, predicted_semantic, classes, predicted_boundary, valid)
        metrics["sample"] = sample.image.name
        metrics["group"] = sample.group
        per_sample.append(metrics)
        groups.setdefault(sample.group, []).append(metrics)
        if output_dir and index < max_visuals:
            figure, axes = plt.subplots(2, 4, figsize=(18, 9))
            axes[0, 0].imshow(image); axes[0, 0].set_title("RGB")
            axes[0, 1].imshow(height, cmap="magma"); axes[0, 1].set_title("Reference nDSM")
            axes[0, 2].imshow(predicted_height, cmap="magma"); axes[0, 2].set_title("Predicted nDSM")
            axes[0, 3].imshow(np.abs(predicted_height - height), cmap="inferno"); axes[0, 3].set_title("Absolute error")
            axes[1, 0].imshow(classes, vmin=0, vmax=CLASS_COUNT - 1, cmap="tab10"); axes[1, 0].set_title("Reference classes")
            axes[1, 1].imshow(predicted_semantic.argmax(axis=0), vmin=0, vmax=CLASS_COUNT - 1, cmap="tab10"); axes[1, 1].set_title("Predicted classes")
            axes[1, 2].imshow(classes == BUILDING_CLASS, cmap="gray"); axes[1, 2].set_title("Reference buildings")
            axes[1, 3].imshow(predicted_boundary >= 0, cmap="gray"); axes[1, 3].set_title("Predicted boundary")
            for axis in axes.reshape(-1):
                axis.axis("off")
            figure.tight_layout()
            figure.savefig(output_dir / f"{index:03d}_{sample.image.stem}.png", dpi=120)
            plt.close(figure)
    result = aggregate_metrics(per_sample)
    result["by_group"] = {group: aggregate_metrics(values) for group, values in groups.items()}
    result["per_sample"] = per_sample
    return result


def make_scaler(enabled: bool):
    import torch

    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except AttributeError:
        return torch.cuda.amp.GradScaler(enabled=enabled)


def main() -> None:
    import torch
    from torch.utils.data import DataLoader

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", default="depth-anything/Depth-Anything-V2-Base-hf")
    parser.add_argument("--dataset-id", default="local-gamus")
    parser.add_argument("--dataset-revision", default="unknown")
    parser.add_argument("--image-key", default="image")
    parser.add_argument("--height-key", default="image")
    parser.add_argument("--class-key", default="image")
    parser.add_argument("--crop-size", type=int, default=518)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--crops-per-sample", type=int, default=4)
    parser.add_argument("--accumulation", type=int, default=4)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()

    if args.smoke_test:
        args.epochs = 2
        args.crops_per_sample = 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    keys = {"image": args.image_key, "height": args.height_key, "classes": args.class_key}
    samples = index_samples(args.root)
    manifest = audit_dataset(args.root, samples, keys, args.output_dir / "gamus_manifest.json", args.dataset_id, args.dataset_revision)
    print(json.dumps({"dataset": manifest["dataset"], "splits": {key: len(value) for key, value in samples.items()}}, indent=2))
    train_samples = samples["train"]
    train_report = manifest["splits"]["train"]
    height_scale = max(1.0, float(train_report["height_percentiles"]["99.5"]))
    class_counts, class_weights = make_class_weights(train_samples, keys)
    (args.output_dir / "class_histogram.json").write_text(json.dumps({"counts": class_counts.tolist(), "weights": class_weights.tolist()}, indent=2))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_depthwizard_model(args.model_id).to(device)
    for parameter in model.base.parameters():
        parameter.requires_grad = False
    optimizer = torch.optim.AdamW(
        [
            {"params": model.base.parameters(), "lr": 1e-5},
            {"params": list(model.decoder.parameters()) + list(model.height_head.parameters()) + list(model.semantic_head.parameters()) + list(model.boundary_head.parameters()), "lr": 1e-4},
        ],
        weight_decay=1e-4,
    )
    total_steps = max(1, math.ceil(len(train_samples) * args.crops_per_sample / max(args.batch_size, 1) / max(args.accumulation, 1)) * args.epochs)
    warmup_steps = max(1, int(total_steps * 0.05))
    def schedule(step: int) -> float:
        if step < warmup_steps:
            return max(1e-3, float(step + 1) / float(warmup_steps))
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, schedule)
    scaler = make_scaler(device.type == "cuda")
    class_weight_tensor = torch.from_numpy(class_weights).to(device)
    train_dataset = GamusCropDataset(train_samples, keys, args.crop_size, height_scale, class_weights, True, args.crops_per_sample, args.seed)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=args.num_workers, pin_memory=device.type == "cuda", persistent_workers=args.num_workers > 0)
    best_rmse = float("inf")
    history = []
    best_path = args.output_dir / "dinosaur.pth"
    for epoch in range(args.epochs):
        if epoch == 3:
            for parameter in model.base.parameters():
                parameter.requires_grad = True
        started = time.time()
        losses = train_epoch(model, train_loader, device, optimizer, scaler, scheduler, class_weight_tensor, height_scale, args.accumulation, epoch, args.epochs)
        validation = evaluate(model, samples["val"], keys, device, args.crop_size, 0.5, height_scale, args.output_dir / "validation_visuals" / f"epoch_{epoch + 1:03d}", max_visuals=2 if args.smoke_test else 4)
        current_rmse = float(validation.get("macro_rmse") or float("inf"))
        history.append({"epoch": epoch + 1, "losses": losses, "validation": validation, "seconds": time.time() - started})
        print(json.dumps(clean_json({"epoch": epoch + 1, "losses": losses, "validation": {key: validation.get(key) for key in ("macro_rmse", "macro_mae", "macro_correlation", "macro_semantic_miou")}}), indent=2))
        if current_rmse < best_rmse:
            best_rmse = current_rmse
            torch.save(
                {
                    "checkpoint_format": "depthwizard_dpt_multiscale_v2",
                    "state_dict": model.state_dict(),
                    "model_id": args.model_id,
                    "image_size": args.crop_size,
                    "crop_size": args.crop_size,
                    "tile_overlap": 0.5,
                    "class_names": CLASS_NAMES,
                    "class_count": CLASS_COUNT,
                    "building_class": BUILDING_CLASS,
                    "mean": MEAN.tolist(),
                    "std": STD.tolist(),
                    "height_scale": height_scale,
                    "height_target_type": "GAMUS_nDSM_or_AGL",
                    "h5_keys": keys,
                    "dataset": manifest["dataset"],
                    "validation_metrics": validation,
                    "training_config": vars(args),
                },
                best_path,
            )
    checkpoint = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    test_metrics = evaluate(model, samples["test"], keys, device, args.crop_size, 0.5, height_scale, args.output_dir / "test_visuals", max_visuals=8)
    checkpoint["test_metrics"] = test_metrics
    checkpoint["history"] = history
    torch.save(checkpoint, best_path)
    (args.output_dir / "metrics.json").write_text(json.dumps(clean_json({"validation": checkpoint["validation_metrics"], "test": test_metrics, "train_samples": len(samples["train"]), "validation_samples": len(samples["val"]), "test_samples": len(samples["test"]), "smoke_test": args.smoke_test}), indent=2) + "\n")
    (args.output_dir / "model_config.json").write_text(json.dumps(clean_json({"checkpoint_format": checkpoint["checkpoint_format"], "model_id": args.model_id, "image_size": args.crop_size, "height_scale": height_scale, "class_names": CLASS_NAMES, "h5_keys": keys}), indent=2) + "\n")
    (args.output_dir / "training_history.json").write_text(json.dumps(clean_json(history), indent=2) + "\n")
    print(json.dumps(clean_json({"best_checkpoint": str(best_path), "test": test_metrics, "samples": {key: len(value) for key, value in samples.items()}}), indent=2))


if __name__ == "__main__":
    main()
