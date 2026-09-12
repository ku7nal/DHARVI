"""Train and evaluate a height-plus-semantics GAMUS checkpoint.

The command intentionally keeps dataset discovery, validation, training, tiled
inference, and metrics in one reproducible module so a Kaggle run and a local
synthetic fixture use the same seams.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image
from app.semantic_contract import BUILDING_CLASS, CLASS_COUNT

DEFAULT_TILE_SIZE = 518
IMAGE_MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
IMAGE_STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)


@dataclass(frozen=True)
class GamusSample:
    image_path: Path
    height_path: Path
    class_path: Path
    group: str


def _find_match(directory: Path, relative: Path) -> Path | None:
    exact = directory / relative
    if exact.is_file():
        return exact
    candidates = sorted(directory.rglob(f"{relative.stem}.*"))
    if len(candidates) > 1:
        raise ValueError(f"Ambiguous {relative.stem} match under {directory}: {candidates}")
    return candidates[0] if candidates else None


def _group_for(path: Path, images_dir: Path) -> str:
    relative = path.relative_to(images_dir)
    if len(relative.parts) > 1:
        return relative.parts[0]
    # A city/tile prefix is safer than random pixel-level splitting when the
    # downloaded dataset is flattened.
    return ""


def discover_samples(root: Path) -> list[GamusSample]:
    """Discover aligned image/height/class triplets without assuming extensions."""
    images_dir = root / "images"
    heights_dir = root / "heights"
    classes_dir = root / "classes"
    if not images_dir.is_dir() or not heights_dir.is_dir() or not classes_dir.is_dir():
        raise FileNotFoundError("GAMUS root must contain images/, heights/, and classes/ directories.")

    samples: list[GamusSample] = []
    for image_path in sorted(path for path in images_dir.rglob("*") if path.is_file()):
        relative = image_path.relative_to(images_dir)
        height_path = _find_match(heights_dir, relative)
        class_path = _find_match(classes_dir, relative)
        if height_path is None or class_path is None:
            missing = "height" if height_path is None else "class"
            raise FileNotFoundError(f"Missing {missing} raster for image {image_path}.")
        samples.append(GamusSample(image_path, height_path, class_path, _group_for(image_path, images_dir)))
    if not samples:
        raise ValueError(f"No aligned GAMUS triplets were found below {root}.")
    return samples


def split_by_group(samples: Sequence[GamusSample], validation_groups: Sequence[str] | None = None) -> tuple[list[GamusSample], list[GamusSample]]:
    """Split by geographic group, never by individual pixels or random tiles."""
    groups = sorted({sample.group for sample in samples})
    if "" in groups:
        raise ValueError("Geographic groups must be represented by directories under images/; flattened tiles cannot be split safely.")
    if len(groups) < 2 and not validation_groups:
        raise ValueError("At least two geographic groups are required for a separated validation split.")
    selected = set(validation_groups or groups[-max(1, len(groups) // 5):])
    unknown = selected.difference(groups)
    if unknown:
        raise ValueError(f"Validation groups are not present in the dataset: {sorted(unknown)}")
    validation = [sample for sample in samples if sample.group in selected]
    train = [sample for sample in samples if sample.group not in selected]
    if not train or not validation:
        raise ValueError("Geographic split produced an empty train or validation set.")
    return train, validation


def _read_raster(path: Path) -> np.ndarray:
    try:
        import rasterio

        with rasterio.open(path) as source:
            return source.read()
    except Exception:
        return np.asarray(Image.open(path))


def decode_class_mask(values: np.ndarray, palette: dict[tuple[int, int, int], int] | None = None) -> np.ndarray:
    """Decode grayscale IDs or an explicitly supplied RGB class palette."""
    if values.ndim == 2:
        labels = values
    elif values.ndim == 3 and values.shape[0] == 1:
        labels = values[0]
    elif values.ndim == 3 and values.shape[0] in (3, 4):
        labels = np.moveaxis(values[:3], 0, -1)
    elif values.ndim == 3 and values.shape[-1] in (3, 4):
        labels = values[..., :3]
    else:
        raise ValueError(f"Unsupported class raster shape: {values.shape}")

    if labels.ndim == 2:
        decoded = labels.astype(np.int64)
    elif np.all(labels[..., 0] == labels[..., 1]) and np.all(labels[..., 1] == labels[..., 2]):
        decoded = labels[..., 0].astype(np.int64)
    elif palette:
        decoded = np.full(labels.shape[:2], -1, dtype=np.int64)
        for color, class_id in palette.items():
            decoded[np.all(labels == np.asarray(color, dtype=labels.dtype), axis=-1)] = class_id
    else:
        colors = np.unique(labels.reshape(-1, 3), axis=0)
        raise ValueError(f"RGB class mask needs an explicit palette; found {len(colors)} colors.")

    invalid = sorted(set(np.unique(decoded).tolist()).difference(range(CLASS_COUNT)))
    if invalid:
        raise ValueError(f"Class raster contains IDs outside GAMUS 0..{CLASS_COUNT - 1}: {invalid}")
    return decoded


def load_sample(sample: GamusSample, class_palette: dict[tuple[int, int, int], int] | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    image = np.asarray(Image.open(sample.image_path).convert("RGB"))
    height_values = _read_raster(sample.height_path)
    height = height_values[0] if height_values.ndim == 3 else height_values
    classes = decode_class_mask(_read_raster(sample.class_path), class_palette)
    if height.shape != classes.shape or height.shape != image.shape[:2]:
        raise ValueError(f"Spatial alignment mismatch for {sample.image_path.name}: image={image.shape[:2]}, height={height.shape}, classes={classes.shape}")
    height = height.astype(np.float32)
    valid = np.isfinite(height) & (classes >= 0) & (classes < CLASS_COUNT)
    height = np.nan_to_num(height, nan=0.0, posinf=0.0, neginf=0.0)
    return image, height, classes.astype(np.int64), valid


def _resize_array(values: np.ndarray, size: tuple[int, int], nearest: bool = False) -> np.ndarray:
    image = Image.fromarray(values)
    return np.asarray(image.resize(size, Image.Resampling.NEAREST if nearest else Image.Resampling.BILINEAR))


class GamusDataset:
    def __init__(self, samples: Sequence[GamusSample], image_size: int = DEFAULT_TILE_SIZE, train: bool = False, class_palette: dict[tuple[int, int, int], int] | None = None) -> None:
        import torch
        from torch.utils.data import Dataset

        self._dataset_base = Dataset
        self.samples = list(samples)
        self.image_size = image_size
        self.train = train
        self.class_palette = class_palette

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        import torch

        image, height, classes, valid = load_sample(self.samples[index], self.class_palette)
        target_size = (self.image_size, self.image_size)
        image = _resize_array(image, target_size)
        height = _resize_array(height.astype(np.float32), target_size)
        classes = _resize_array(classes.astype(np.uint8), target_size, nearest=True).astype(np.int64)
        valid = _resize_array(valid.astype(np.uint8), target_size, nearest=True).astype(bool)

        if self.train:
            if random.random() < 0.5:
                image, height, classes, valid = [np.flip(value, axis=1).copy() for value in (image, height, classes, valid)]
            if random.random() < 0.5:
                image, height, classes, valid = [np.flip(value, axis=0).copy() for value in (image, height, classes, valid)]
            rotations = random.randrange(4)
            image = np.rot90(image, rotations).copy()
            height = np.rot90(height, rotations).copy()
            classes = np.rot90(classes, rotations).copy()
            valid = np.rot90(valid, rotations).copy()

        image_tensor = torch.from_numpy(((image.astype(np.float32) / 255.0 - IMAGE_MEAN) / IMAGE_STD).transpose(2, 0, 1)).float()
        return {
            "image": image_tensor,
            "height": torch.from_numpy(height[None]).float(),
            "classes": torch.from_numpy(classes).long(),
            "valid": torch.from_numpy(valid[None]).bool(),
        }


class MultitaskDepthAnythingModel:
    """DepthAnything height branch plus a separately initialized semantic head."""

    def __init__(self, base_model, torch_module) -> None:
        import torch.nn as nn

        self.torch = torch_module
        self.nn = nn
        self.model = base_model
        channels = int(getattr(base_model.config, "hidden_size", 384))
        self.semantic_head = nn.Sequential(
            nn.Conv2d(channels, 128, kernel_size=3, padding=1),
            nn.GELU(),
            nn.Conv2d(128, CLASS_COUNT, kernel_size=1),
        )

    def to_module(self):
        import torch.nn as nn

        parent = self

        class Module(nn.Module):
            def __init__(self):
                super().__init__()
                self.torch = parent.torch
                self.model = parent.model
                self.semantic_head = parent.semantic_head

            def forward(self, pixel_values):
                outputs = self.model(pixel_values=pixel_values, output_hidden_states=True)
                height = self.torch.nn.functional.interpolate(
                    outputs.predicted_depth.unsqueeze(1), size=pixel_values.shape[-2:], mode="bilinear", align_corners=True
                )
                features = outputs.hidden_states[-1]
                if features.ndim == 3:
                    token_count = features.shape[1]
                    side = int(math.sqrt(token_count))
                    if side * side != token_count:
                        features = features[:, 1:]
                        side = int(math.sqrt(features.shape[1]))
                    features = features[:, :side * side].transpose(1, 2).reshape(features.shape[0], features.shape[2], side, side)
                semantic = parent.semantic_head(features)
                semantic = self.torch.nn.functional.interpolate(semantic, size=pixel_values.shape[-2:], mode="bilinear", align_corners=False)
                return {"height": self.torch.relu(height), "semantic": semantic}

        return Module()


def load_multitask_model(model_id: str = "depth-anything/Depth-Anything-V2-Small-hf", height_checkpoint: Path | None = None, multitask_checkpoint: Path | None = None):
    import torch
    from transformers import AutoModelForDepthEstimation

    base = AutoModelForDepthEstimation.from_pretrained(model_id)
    model = MultitaskDepthAnythingModel(base, torch).to_module()
    if multitask_checkpoint:
        checkpoint = torch.load(multitask_checkpoint, map_location="cpu", weights_only=False)
        state = checkpoint["state_dict"] if isinstance(checkpoint, dict) and "state_dict" in checkpoint else checkpoint
        model.load_state_dict(state, strict=True)
    elif height_checkpoint:
        checkpoint = torch.load(height_checkpoint, map_location="cpu", weights_only=False)
        state = checkpoint.get("model", checkpoint.get("state_dict", checkpoint)) if isinstance(checkpoint, dict) else checkpoint
        state = {key.removeprefix("module."): value for key, value in state.items()}
        state = {key[len("model."):] if key.startswith("model.model.") else key: value for key, value in state.items()}
        height_state = {key: value for key, value in state.items() if key.startswith("model.")}
        model_state = model.state_dict()
        matched = [key for key, value in height_state.items() if key in model_state and model_state[key].shape == value.shape]
        expected_height_keys = {key for key in model_state if key.startswith("model.")}
        missing_height_keys = expected_height_keys.difference(matched)
        if missing_height_keys:
            raise ValueError(f"Baseline checkpoint {height_checkpoint} is missing {len(missing_height_keys)} height weights.")
        model.load_state_dict(height_state, strict=False)
    return model


def multitask_loss(outputs, targets, class_weights=None) -> dict[str, object]:
    import torch
    import torch.nn.functional as functional

    height = outputs["height"]
    semantic = outputs["semantic"]
    target_height = targets["height"]
    target_classes = targets["classes"]
    valid = targets["valid"].float()
    height_weight = 1.0 + 2.0 * (target_classes == BUILDING_CLASS).float().unsqueeze(1)
    dx = functional.pad(torch.abs(target_height[..., :, 1:] - target_height[..., :, :-1]), (0, 1, 0, 0))
    dy = functional.pad(torch.abs(target_height[..., 1:, :] - target_height[..., :-1, :]), (0, 0, 0, 1))
    height_weight = height_weight + torch.clamp(dx + dy, 0, 4)
    robust_error = functional.smooth_l1_loss(height, target_height, reduction="none")
    height_loss = (robust_error * height_weight * valid).sum() / valid.sum().clamp_min(1.0)
    gradient_loss = (torch.abs(height[..., :, 1:] - height[..., :, :-1] - (target_height[..., :, 1:] - target_height[..., :, :-1])) * valid[..., :, 1:]).sum() / valid[..., :, 1:].sum().clamp_min(1.0)
    semantic_loss = functional.cross_entropy(semantic, target_classes, weight=class_weights, reduction="none")
    semantic_loss = (semantic_loss * valid[:, 0]).sum() / valid[:, 0].sum().clamp_min(1.0)
    probabilities = torch.softmax(semantic, dim=1)
    one_hot = functional.one_hot(target_classes, CLASS_COUNT).permute(0, 3, 1, 2).float()
    dice = (2 * (probabilities * one_hot * valid).sum((0, 2, 3)) + 1e-5) / ((probabilities * valid).sum((0, 2, 3)) + (one_hot * valid).sum((0, 2, 3)) + 1e-5)
    dice_loss = 1 - dice.mean()
    total = height_loss + 0.2 * gradient_loss + 0.3 * semantic_loss + 0.2 * dice_loss
    return {"total": total, "height": height_loss, "gradient": gradient_loss, "semantic": semantic_loss, "dice": dice_loss}


def _tile_starts(length: int, tile_size: int, overlap: float) -> list[int]:
    if length <= tile_size:
        return [0]
    stride = max(1, round(tile_size * (1 - overlap)))
    starts = list(range(0, length - tile_size + 1, stride))
    if starts[-1] != length - tile_size:
        starts.append(length - tile_size)
    return starts


def tiled_inference(model, image: np.ndarray, device, tile_size: int = DEFAULT_TILE_SIZE, overlap: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    import torch

    height, width = image.shape[:2]
    height_sum = np.zeros((height, width), dtype=np.float32)
    semantic_sum = np.zeros((CLASS_COUNT, height, width), dtype=np.float32)
    weights = np.zeros((height, width), dtype=np.float32)
    window_1d = np.maximum(np.hanning(tile_size), 1e-3).astype(np.float32)
    window = np.outer(window_1d, window_1d)
    model.eval()
    with torch.inference_mode():
        for top in _tile_starts(height, tile_size, overlap):
            for left in _tile_starts(width, tile_size, overlap):
                tile = image[top:min(top + tile_size, height), left:min(left + tile_size, width)]
                tile_height, tile_width = tile.shape[:2]
                padded = np.pad(tile, ((0, tile_size - tile_height), (0, tile_size - tile_width), (0, 0)), mode="reflect")
                tensor = torch.from_numpy(((padded.astype(np.float32) / 255.0 - IMAGE_MEAN) / IMAGE_STD).transpose(2, 0, 1)).unsqueeze(0).float().to(device)
                outputs = model(tensor)
                predicted_height = outputs["height"][0, 0].detach().cpu().numpy()[:tile_height, :tile_width]
                predicted_semantic = outputs["semantic"][0].detach().cpu().numpy()[:, :tile_height, :tile_width]
                tile_weight = window[:tile_height, :tile_width]
                height_sum[top:top + tile_height, left:left + tile_width] += predicted_height * tile_weight
                semantic_sum[:, top:top + tile_height, left:left + tile_width] += predicted_semantic * tile_weight
                weights[top:top + tile_height, left:left + tile_width] += tile_weight
    return height_sum / np.maximum(weights, 1e-6), semantic_sum / np.maximum(weights, 1e-6)[None]


def reconstruction_metrics(predicted_height: np.ndarray, target_height: np.ndarray, predicted_semantic: np.ndarray, target_semantic: np.ndarray, valid: np.ndarray) -> dict[str, float]:
    valid = valid.astype(bool)
    difference = (predicted_height - target_height)[valid]
    predicted_centered = difference * 0 + predicted_height[valid] - predicted_height[valid].mean()
    target_centered = target_height[valid] - target_height[valid].mean()
    denominator = float(np.sqrt(np.sum(predicted_centered**2) * np.sum(target_centered**2)))
    correlation = float(np.sum(predicted_centered * target_centered) / denominator) if denominator else 0.0
    predicted_labels = predicted_semantic.argmax(axis=0)
    ious: list[float] = []
    for class_id in range(CLASS_COUNT):
        intersection = np.sum((predicted_labels == class_id) & (target_semantic == class_id) & valid)
        union = np.sum(((predicted_labels == class_id) | (target_semantic == class_id)) & valid)
        if union:
            ious.append(float(intersection / union))
    predicted_building = predicted_labels == BUILDING_CLASS
    target_building = target_semantic == BUILDING_CLASS
    true_positive = np.sum(predicted_building & target_building & valid)
    building_f1 = float(2 * true_positive / max(2 * true_positive + np.sum(predicted_building & valid) - true_positive + np.sum(target_building & valid) - true_positive, 1))

    def boundary(mask: np.ndarray) -> np.ndarray:
        padded = np.pad(mask, 1, mode="constant", constant_values=False)
        neighbours = padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
        return mask & ~neighbours

    predicted_boundary = boundary(predicted_building)
    target_boundary = boundary(target_building)
    tolerance = target_boundary | np.roll(target_boundary, 1, 0) | np.roll(target_boundary, -1, 0) | np.roll(target_boundary, 1, 1) | np.roll(target_boundary, -1, 1)
    boundary_tp = np.sum(predicted_boundary & tolerance & valid)
    boundary_f1 = float(2 * boundary_tp / max(np.sum(predicted_boundary & valid) + np.sum(target_boundary & valid), 1))
    return {
        "height_rmse": float(np.sqrt(np.mean(difference**2))) if difference.size else 0.0,
        "height_mae": float(np.mean(np.abs(difference))) if difference.size else 0.0,
        "height_correlation": correlation,
        "semantic_miou": float(np.mean(ious)) if ious else 0.0,
        "building_f1": building_f1,
        "building_boundary_f1": boundary_f1,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Local GAMUS root containing images/, heights/, and classes/")
    parser.add_argument("--baseline-checkpoint", "--height-checkpoint", dest="baseline_checkpoint", type=Path)
    parser.add_argument("--output", type=Path, default=Path("checkpoints/gamus_multitask.pth"))
    parser.add_argument("--validation-group", action="append", dest="validation_groups")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--image-size", type=int, default=DEFAULT_TILE_SIZE)
    parser.add_argument("--evaluate", action="store_true")
    return parser.parse_args()


def class_weights(samples: Sequence[GamusSample]) -> "object":
    import torch

    counts = np.zeros(CLASS_COUNT, dtype=np.float64)
    for sample in samples:
        _, _, labels, valid = load_sample(sample)
        counts += np.bincount(labels[valid], minlength=CLASS_COUNT)
    weights = 1.0 / np.sqrt(np.maximum(counts, 1.0))
    weights /= weights.mean()
    return torch.from_numpy(weights.astype(np.float32))


def main() -> None:
    import torch
    from torch.utils.data import DataLoader

    args = _parse_args()
    samples = discover_samples(args.root)
    train_samples, validation_samples = split_by_group(samples, args.validation_groups)
    print(json.dumps({"samples": len(samples), "train": len(train_samples), "validation": len(validation_samples), "groups": sorted({sample.group for sample in samples})}, indent=2))
    if args.baseline_checkpoint and args.output.resolve() == args.baseline_checkpoint.resolve():
        raise ValueError("--output must be different from --baseline-checkpoint so baseline weights are retained.")
    if args.evaluate:
        if not args.output.is_file():
            raise FileNotFoundError("--evaluate expects --output to point to an existing multitask checkpoint.")
        model = load_multitask_model(multitask_checkpoint=args.output)
    else:
        model = load_multitask_model(height_checkpoint=args.baseline_checkpoint)
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")
    model.to(device)
    if args.evaluate:
        metrics = evaluate_samples(model, validation_samples, device)
        checkpoint = torch.load(args.output, map_location="cpu", weights_only=False)
        if isinstance(checkpoint, dict) and checkpoint.get("baseline_metrics"):
            metrics = {**{f"multitask_{key}": value for key, value in metrics.items()}, **{f"baseline_{key}": value for key, value in checkpoint["baseline_metrics"].items()}}
        print(json.dumps(metrics, indent=2))
        return

    baseline_metrics = evaluate_height_samples(model, validation_samples, device) if args.baseline_checkpoint else None
    weights = class_weights(train_samples).to(device)

    train_loader = DataLoader(GamusDataset(train_samples, args.image_size, train=True), batch_size=args.batch_size, shuffle=True, num_workers=0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=5, factor=0.5)
    best_rmse = float("inf")
    stale_epochs = 0
    for epoch in range(args.epochs):
        model.train()
        for batch in train_loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            losses = multitask_loss(model(batch["image"]), batch, class_weights=weights)
            losses["total"].backward()
            optimizer.step()
        metrics = evaluate_samples(model, validation_samples, device)
        scheduler.step(metrics["height_rmse"])
        print(json.dumps({"epoch": epoch + 1, **metrics}))
        if metrics["height_rmse"] < best_rmse:
            best_rmse = metrics["height_rmse"]
            stale_epochs = 0
            args.output.parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_type": "gamus_multitask",
                "state_dict": model.state_dict(),
                "metrics": metrics,
                "baseline_metrics": baseline_metrics,
                "initialized_from_baseline": str(args.baseline_checkpoint) if args.baseline_checkpoint else None,
                "validation_groups": sorted({sample.group for sample in validation_samples}),
            }, args.output)
        else:
            stale_epochs += 1
            if stale_epochs >= 10:
                break


def evaluate_samples(model, samples: Sequence[GamusSample], device) -> dict[str, float]:
    metrics = []
    for sample in samples:
        image, height, classes, valid = load_sample(sample)
        predicted_height, predicted_semantic = tiled_inference(model, image, device)
        metrics.append(reconstruction_metrics(predicted_height, height, predicted_semantic, classes, valid))
    if not metrics:
        return {"height_rmse": 0.0, "height_mae": 0.0, "height_correlation": 0.0, "semantic_miou": 0.0, "building_f1": 0.0, "building_boundary_f1": 0.0}
    return {key: float(np.mean([item[key] for item in metrics])) for key in metrics[0]}


def evaluate_height_samples(model, samples: Sequence[GamusSample], device) -> dict[str, float]:
    metrics = []
    for sample in samples:
        image, height, _, valid = load_sample(sample)
        predicted_height, _ = tiled_inference(model, image, device)
        difference = (predicted_height - height)[valid]
        predicted_values = predicted_height[valid]
        target_values = height[valid]
        predicted_centered = predicted_values - predicted_values.mean()
        target_centered = target_values - target_values.mean()
        denominator = float(np.sqrt(np.sum(predicted_centered**2) * np.sum(target_centered**2)))
        metrics.append({
            "height_rmse": float(np.sqrt(np.mean(difference**2))) if difference.size else 0.0,
            "height_mae": float(np.mean(np.abs(difference))) if difference.size else 0.0,
            "height_correlation": float(np.sum(predicted_centered * target_centered) / denominator) if denominator else 0.0,
        })
    if not metrics:
        return {"height_rmse": 0.0, "height_mae": 0.0, "height_correlation": 0.0}
    return {key: float(np.mean([item[key] for item in metrics])) for key in metrics[0]}


if __name__ == "__main__":
    main()
