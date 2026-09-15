"""Fail-fast audit and manifest generation for a complete GAMUS release."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.semantic_contract import BUILDING_CLASS, CLASS_COUNT

SPLITS = ("train", "val", "test")
_PAIR_SUFFIXES = (
    "_IMG",
    "_RGB",
    "_AGL",
    "_DSM",
    "_HEIGHT",
    "_CLASS",
    "_CLS",
    "_CLASSES",
    "_LABEL",
    "_LABELS",
    "_SEMANTIC",
    "_SEMANTICS",
)


class DatasetAuditError(ValueError):
    """Raised when GAMUS cannot be proven to be complete and aligned."""


def _pair_key(path: Path) -> str:
    value = path.stem.upper()
    changed = True
    while changed:
        changed = False
        for suffix in _PAIR_SUFFIXES:
            if value.endswith(suffix):
                value = value[: -len(suffix)]
                changed = True
                break
    return value


def _files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        raise DatasetAuditError(f"Missing GAMUS directory: {directory}")
    return sorted(path for path in directory.rglob("*") if path.is_file())


def _pair_files(root: Path, split: str) -> list[tuple[Path, Path, Path]]:
    directories = {name: root / name / split for name in ("images", "heights", "classes")}
    files = {name: _files(directory) for name, directory in directories.items()}
    indexes: dict[str, dict[str, list[Path]]] = {}
    for kind, values in files.items():
        index: dict[str, list[Path]] = defaultdict(list)
        for path in values:
            index[_pair_key(path)].append(path)
        indexes[kind] = index

    image_keys = set(indexes["images"])
    errors: list[str] = []
    pairs: list[tuple[Path, Path, Path]] = []
    for key in sorted(image_keys):
        image_matches = indexes["images"][key]
        height_matches = indexes["heights"].get(key, [])
        class_matches = indexes["classes"].get(key, [])
        if len(image_matches) != 1 or len(height_matches) != 1 or len(class_matches) != 1:
            errors.append(
                f"{split}:{key} has image={len(image_matches)}, "
                f"height={len(height_matches)}, classes={len(class_matches)} matches"
            )
            continue
        pairs.append((image_matches[0], height_matches[0], class_matches[0]))

    for kind in ("heights", "classes"):
        orphan_keys = set(indexes[kind]).difference(image_keys)
        for key in sorted(orphan_keys):
            errors.append(f"{split}:{kind} contains unmatched sample {key}")
    if errors:
        raise DatasetAuditError("GAMUS alignment audit failed: " + "; ".join(errors))
    if not pairs:
        raise DatasetAuditError(f"No aligned GAMUS samples found in split {split}")
    return pairs


def paired_samples(root: Path, split: str) -> list[tuple[Path, Path, Path]]:
    """Return the verified RGB/height/semantic triplets for one split."""
    return _pair_files(root, split)


def _h5_datasets(path: Path) -> list[tuple[str, tuple[int, ...], str]]:
    import h5py

    found: list[tuple[str, tuple[int, ...], str]] = []
    try:
        with h5py.File(path, "r") as file:
            def visit(name: str, value: object) -> None:
                if isinstance(value, h5py.Dataset):
                    found.append((name, tuple(value.shape), str(value.dtype)))

            file.visititems(visit)
    except (OSError, RuntimeError) as error:
        raise DatasetAuditError(f"Could not read HDF5 file {path}: {error}") from error
    return found


def _select_key(path: Path, key: str | None, kind: str) -> str:
    datasets = _h5_datasets(path)
    available = {name for name, _, _ in datasets}
    if key:
        if key not in available:
            raise DatasetAuditError(f"HDF5 key {key!r} was not found in {path}; available={sorted(available)}")
        return key

    candidates: list[str] = []
    for name, shape, _ in datasets:
        dimensions = len(shape)
        channels = (shape[-1] if shape else None) in (1, 3, 4) or (shape[0] if shape else None) in (1, 3, 4)
        if kind == "image" and dimensions == 3 and channels:
            candidates.append(name)
        elif kind != "image" and dimensions in (2, 3) and not (dimensions == 3 and channels):
            candidates.append(name)
    if len(candidates) != 1:
        raise DatasetAuditError(
            f"Could not uniquely infer {kind} dataset in {path}; candidates={candidates}. "
            f"Pass --{kind}-key explicitly."
        )
    return candidates[0]


def _read_h5(path: Path, key: str | None, kind: str) -> tuple[np.ndarray, str, str]:
    import h5py

    selected = _select_key(path, key, kind)
    try:
        with h5py.File(path, "r") as file:
            values = np.asarray(file[selected])
            dtype = str(file[selected].dtype)
    except (OSError, RuntimeError, KeyError) as error:
        raise DatasetAuditError(f"Could not read HDF5 dataset {selected!r} from {path}: {error}") from error
    if kind == "image":
        if values.ndim == 3 and values.shape[0] in (1, 3, 4) and values.shape[-1] not in (1, 3, 4):
            values = np.moveaxis(values, 0, -1)
        if values.ndim != 3 or values.shape[-1] < 3:
            raise DatasetAuditError(f"Expected RGB HxWx3 data in {path}, got shape {values.shape}")
        return values[..., :3], selected, dtype

    if values.ndim == 3 and values.shape[0] == 1:
        values = values[0]
    if values.ndim != 2:
        raise DatasetAuditError(f"Expected 2D {kind} raster in {path}, got shape {values.shape}")
    return values, selected, dtype


def _class_values(values: np.ndarray, path: Path) -> np.ndarray:
    if values.ndim == 2:
        labels = values
    elif values.ndim == 3 and values.shape[0] in (1, 3, 4):
        labels = np.moveaxis(values, 0, -1)
    elif values.ndim == 3 and values.shape[-1] in (1, 3, 4):
        labels = values
    else:
        raise DatasetAuditError(f"Unsupported semantic raster shape in {path}: {values.shape}")
    if labels.ndim == 3:
        if labels.shape[-1] == 1:
            labels = labels[..., 0]
        elif not np.all(labels[..., 0] == labels[..., 1]) or not np.all(labels[..., 1] == labels[..., 2]):
            raise DatasetAuditError(f"Semantic raster in {path} is RGB; an explicit palette is required")
        else:
            labels = labels[..., 0]
    return labels.astype(np.int64)


def _percentiles(values: np.ndarray) -> dict[str, float]:
    if values.size == 0:
        return {str(percentile): 0.0 for percentile in (0, 1, 5, 25, 50, 75, 95, 99, 100)}
    percentiles = np.percentile(values, (0, 1, 5, 25, 50, 75, 95, 99, 100))
    return {str(percentile): float(value) for percentile, value in zip((0, 1, 5, 25, 50, 75, 95, 99, 100), percentiles)}


def _group_for(image: Path, images_root: Path) -> str:
    relative = image.relative_to(images_root)
    if len(relative.parts) > 1:
        return "/".join(relative.parts[:-1])
    return re.split(r"[_-]", relative.stem, maxsplit=1)[0]


def _stats(values: np.ndarray) -> dict[str, object]:
    finite = values[np.isfinite(values)]
    return {
        "finite_count": int(finite.size),
        "min": float(finite.min()) if finite.size else None,
        "max": float(finite.max()) if finite.size else None,
        "percentiles": _percentiles(finite),
    }


def audit_dataset(
    root: Path,
    output: Path,
    *,
    dataset_id: str | None,
    dataset_revision: str | None,
    image_key: str | None = None,
    height_key: str | None = None,
    class_key: str | None = None,
) -> dict[str, object]:
    """Audit all GAMUS splits and write a compact JSON manifest."""
    if not dataset_revision:
        raise ValueError("A dataset revision is required for the GAMUS audit")
    if not dataset_id:
        raise ValueError("A dataset ID is required for the GAMUS audit")
    root = root.resolve()
    samples: list[dict[str, object]] = []
    split_reports: dict[str, object] = {}
    total_valid = 0
    total_invalid = 0
    for split in SPLITS:
        pairs = _pair_files(root, split)
        split_height_samples: list[np.ndarray] = []
        split_groups: Counter[str] = Counter()
        split_class_counts: Counter[str] = Counter()
        split_valid = 0
        split_invalid = 0
        for image_path, height_path, class_path in pairs:
            image, selected_image_key, image_dtype = _read_h5(image_path, image_key, "image")
            height, selected_height_key, height_dtype = _read_h5(height_path, height_key, "height")
            raw_classes, selected_class_key, class_dtype = _read_h5(class_path, class_key, "classes")
            classes = _class_values(raw_classes, class_path)
            if image.shape[:2] != height.shape or height.shape != classes.shape:
                raise DatasetAuditError(
                    f"Spatial mismatch for {image_path.name}: image={image.shape[:2]}, "
                    f"height={height.shape}, classes={classes.shape}"
                )

            finite_height = np.isfinite(height)
            valid_class = np.isin(classes, np.arange(CLASS_COUNT))
            if not np.all(valid_class):
                invalid_ids = sorted(int(value) for value in np.unique(classes[~valid_class]))
                raise DatasetAuditError(
                    f"Invalid semantic class IDs in {class_path}: {invalid_ids}; "
                    f"expected IDs 0..{CLASS_COUNT - 1}"
                )
            valid = finite_height & valid_class
            class_counts = Counter(str(int(value)) for value in classes[valid])
            split_class_counts.update(class_counts)
            split_groups[_group_for(image_path, root / "images" / split)] += 1
            finite_values = height[finite_height].astype(np.float32, copy=False)
            # Keep aggregate percentiles bounded while retaining exact per-sample
            # min/max/count statistics in the manifest.
            stride = max(1, finite_values.size // 4096)
            split_height_samples.append(finite_values[::stride][:4096].copy())
            split_valid += int(valid.sum())
            split_invalid += int((~valid).sum())
            total_valid += int(valid.sum())
            total_invalid += int((~valid).sum())
            samples.append({
                "split": split,
                "group": _group_for(image_path, root / "images" / split),
                "files": {
                    "image": str(image_path.relative_to(root)),
                    "height": str(height_path.relative_to(root)),
                    "classes": str(class_path.relative_to(root)),
                },
                "dataset_keys": {"image": selected_image_key, "height": selected_height_key, "classes": selected_class_key},
                "dtypes": {"image": image_dtype, "height": height_dtype, "classes": class_dtype},
                "shapes": {"image": list(image.shape), "height": list(height.shape), "classes": list(classes.shape)},
                "height_stats": _stats(height),
                "class_ids": sorted(int(value) for value in np.unique(classes)),
                "class_counts": dict(sorted(class_counts.items())),
                "invalid_pixels": {
                    "height_nonfinite": int((~finite_height).sum()),
                    "class_id_invalid": int((~valid_class).sum()),
                    "total_invalid": int((~valid).sum()),
                },
                "valid_pixel_count": int(valid.sum()),
                "building_pixel_fraction": float(np.sum(valid & (classes == BUILDING_CLASS)) / max(int(valid.sum()), 1)),
            })
        combined = np.concatenate(split_height_samples) if split_height_samples else np.array([], dtype=np.float32)
        split_reports[split] = {
            "sample_count": len(pairs),
            "groups": dict(sorted(split_groups.items())),
            "height_stats": _stats(combined),
            "height_percentiles_are_sampled": True,
            "class_counts": dict(sorted(split_class_counts.items())),
            "valid_pixel_count": split_valid,
            "invalid_pixel_count": split_invalid,
            "building_pixel_fraction": float(split_class_counts.get(str(BUILDING_CLASS), 0) / max(split_valid, 1)),
        }

    manifest: dict[str, object] = {
        "schema_version": 1,
        "dataset": {
            "id": dataset_id,
            "revision": str(dataset_revision),
            "root": str(root),
            "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "splits": split_reports,
        "total_sample_count": len(samples),
        "total_valid_pixel_count": total_valid,
        "total_invalid_pixel_count": total_invalid,
        "samples": samples,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", default=os.getenv("KAGGLE_DATASET_ID"))
    parser.add_argument("--dataset-revision", default=os.getenv("KAGGLE_DATASET_REVISION"))
    parser.add_argument("--image-key")
    parser.add_argument("--height-key")
    parser.add_argument("--class-key")
    args = parser.parse_args()
    manifest = audit_dataset(
        args.root,
        args.output,
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
    }, indent=2))


if __name__ == "__main__":
    main()
