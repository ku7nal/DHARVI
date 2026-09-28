"""Metric DSM calibration and GeoTIFF export helpers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine


def parse_ground_control_points(raw: str | None) -> list[tuple[float, float, float]]:
    """Parse [{pixelX, pixelY, elevation}] ground-control points."""
    if not raw:
        return []
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("ground_control_points must be valid JSON.") from error
    if not isinstance(values, list):
        raise ValueError("ground_control_points must be a JSON list.")
    points = []
    for point in values:
        if not isinstance(point, dict):
            raise ValueError("Each ground control point must be an object.")
        try:
            x = float(point["pixelX"] if "pixelX" in point else point["x"])
            y = float(point["pixelY"] if "pixelY" in point else point["y"])
            elevation = float(point["elevation"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Each ground control point needs pixelX, pixelY, and elevation.") from error
        if not all(np.isfinite(value) for value in (x, y, elevation)):
            raise ValueError("Ground control point values must be finite.")
        points.append((x, y, elevation))
    return points


def calibrate_dsm(
    height_map: np.ndarray,
    semantic_labels: np.ndarray | None,
    ground_elevation: float | None = None,
    ground_control_points: list[tuple[float, float, float]] | None = None,
    valid_mask: np.ndarray | None = None,
) -> tuple[np.ndarray | None, dict[str, object]]:
    """Calibrate relative nDSM heights against supplied metric ground evidence."""
    heights = np.asarray(height_map, dtype=np.float32)
    points = ground_control_points or []
    ground_mask = None
    if semantic_labels is not None:
        labels = np.asarray(semantic_labels)
        if labels.shape == heights.shape:
            ground_mask = labels == 1
        elif labels.ndim == 2:
            from PIL import Image

            resized = np.asarray(Image.fromarray(labels.astype(np.uint8), mode="L").resize((heights.shape[1], heights.shape[0]), Image.Resampling.NEAREST))
            ground_mask = resized == 1
    if valid_mask is not None:
        validity = np.asarray(valid_mask, dtype=bool)
        if validity.shape != heights.shape:
            raise ValueError("DSM validity mask must match height map dimensions.")
        ground_mask = (ground_mask & validity) if ground_mask is not None else None
    else:
        validity = np.ones(heights.shape, dtype=bool)
    validity &= np.isfinite(heights)
    if ground_mask is not None:
        ground_mask &= validity
    ground_pixels = int(np.count_nonzero(ground_mask)) if ground_mask is not None else 0
    minimum_ground_pixels = max(25, int(heights.size * 0.01))
    if points:
        if len(points) < 3:
            return None, {"status": "invalid_ground_control_points", "method": "ground_control_points", "confidence": 0.0, "residualError": None, "groundPixelCount": ground_pixels}
        if ground_mask is None:
            return None, {"status": "insufficient_ground_evidence", "method": "ground_control_points", "confidence": 0.0, "residualError": None, "groundPixelCount": 0}
        sampled_heights = []
        for x, y, _ in points:
            column = int(round(x))
            row = int(round(y))
            if not (0 <= row < heights.shape[0] and 0 <= column < heights.shape[1]):
                return None, {"status": "invalid_ground_control_points", "method": "ground_control_points", "confidence": 0.0, "residualError": None, "groundPixelCount": ground_pixels}
            if not validity[row, column] or ground_mask is None or not ground_mask[row, column]:
                return None, {"status": "invalid_ground_control_points", "method": "ground_control_points", "confidence": 0.0, "residualError": None, "groundPixelCount": ground_pixels}
            sampled_heights.append(float(heights[row, column]))
        coordinates = np.asarray([[x, y, 1.0] for x, y, _ in points], dtype=np.float64)
        elevations = np.asarray([elevation for _, _, elevation in points], dtype=np.float64)
        if np.linalg.matrix_rank(coordinates) < 3:
            return None, {"status": "invalid_ground_control_points", "method": "ground_control_points", "confidence": 0.0, "residualError": None, "groundPixelCount": ground_pixels}
        coefficients, _, _, _ = np.linalg.lstsq(coordinates, elevations, rcond=None)
        residual = elevations - coordinates @ coefficients
        predicted_ground_error = np.asarray(sampled_heights, dtype=np.float64)
        relative_baseline = float(np.median(predicted_ground_error))
        final_residual = coordinates @ coefficients + predicted_ground_error - relative_baseline - elevations
        residual_error = float(np.sqrt(np.mean(final_residual**2)))
        rows, columns = np.indices(heights.shape)
        ground_surface = coefficients[0] * columns + coefficients[1] * rows + coefficients[2]
        method = "ground_control_points"
        scale = max(float(np.ptp(elevations)), 1.0)
        evidence_count = max(ground_pixels, len(points))
    elif ground_pixels < minimum_ground_pixels:
        return None, {
            "status": "insufficient_ground_evidence",
            "method": None,
            "confidence": 0.0,
            "residualError": None,
            "groundPixelCount": ground_pixels,
        }
    elif ground_elevation is not None and np.isfinite(ground_elevation):
        ground_surface = np.full(heights.shape, float(ground_elevation), dtype=np.float64)
        ground_values = heights[ground_mask]
        relative_baseline = float(np.median(ground_values)) if ground_values.size else 0.0
        residual_error = float(np.sqrt(np.mean((ground_values - relative_baseline) ** 2))) if ground_values.size else 0.0
        method = "ground_pixels_plus_ground_elevation"
        scale = max(abs(float(ground_elevation)), 1.0)
        evidence_count = ground_pixels
    else:
        return None, {"status": "insufficient_ground_evidence", "method": None, "confidence": 0.0, "residualError": None, "groundPixelCount": ground_pixels}

    confidence = float(np.clip(np.exp(-residual_error / scale) * min(1.0, evidence_count / max(minimum_ground_pixels * 4, 1)), 0.0, 1.0))
    dsm = np.where(validity, heights - relative_baseline + ground_surface.astype(np.float32), np.nan).astype(np.float32)
    return dsm.astype(np.float32), {
        "status": "calibrated",
        "method": method,
        "confidence": confidence,
        "residualError": residual_error,
        "groundPixelCount": evidence_count,
    }


def write_dsm_geotiff(path: Path, dsm: np.ndarray, metadata: dict[str, object]) -> None:
    """Write metric DSM values using the source raster's spatial reference."""
    crs = metadata.get("crs")
    transform_values = metadata.get("transform")
    values = np.asarray(dsm, dtype=np.float32)
    if not crs or not isinstance(transform_values, list) or len(transform_values) != 9:
        raise ValueError("A calibrated DSM requires source CRS and affine transform metadata.")
    try:
        transform = Affine(*[float(value) for value in transform_values])
        rasterio.crs.CRS.from_user_input(crs)
    except (TypeError, ValueError, rasterio.errors.CRSError) as error:
        raise ValueError("Source CRS and affine transform metadata must be valid.") from error
    if not np.isfinite(tuple(transform)).all() or transform.is_degenerate:
        raise ValueError("Source affine transform metadata must be finite and invertible.")
    if metadata.get("width") != values.shape[1] or metadata.get("height") != values.shape[0]:
        raise ValueError("DSM dimensions do not match the source raster.")
    source_bounds = metadata.get("bounds")
    source_resolution = metadata.get("resolution")
    if not isinstance(source_bounds, dict) or not isinstance(source_resolution, list) or len(source_resolution) != 2:
        raise ValueError("A calibrated DSM requires source bounds and resolution metadata.")
    bounds = rasterio.transform.array_bounds(values.shape[0], values.shape[1], transform)
    expected = (source_bounds.get("left"), source_bounds.get("bottom"), source_bounds.get("right"), source_bounds.get("top"))
    if any(value is None for value in expected) or not np.allclose(bounds, expected, rtol=0, atol=1e-9):
        raise ValueError("DSM dimensions do not preserve source bounds.")
    if not np.allclose((abs(transform.a), abs(transform.e)), source_resolution, rtol=0, atol=1e-12):
        raise ValueError("DSM transform does not preserve source resolution.")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        with rasterio.open(
            temporary_path,
            "w",
            driver="GTiff",
            height=values.shape[0],
            width=values.shape[1],
            count=1,
            dtype="float32",
            nodata=-9999.0,
            crs=str(crs),
            transform=transform,
            compress="deflate",
        ) as destination:
            destination.write(np.where(np.isfinite(values), values, -9999.0), 1)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)
