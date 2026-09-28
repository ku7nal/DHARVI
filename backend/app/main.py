from io import BytesIO
import os
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import rasterio
from rasterio.io import MemoryFile

from app.building_footprints import clean_semantic_labels, extract_building_footprints
from app.geospatial import calibrate_dsm, parse_ground_control_points, write_dsm_geotiff
from app.model_service import DepthAnythingModelService, ModelUnavailableError
from app.route_planner import plan_ranked_routes, plan_route
from app.semantic_contract import BUILDING_CLASS, CLASS_COUNT, SEMANTIC_CLASSES

MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = Path(os.getenv("DEPTHWIZARD_CHECKPOINT", PROJECT_ROOT / "dinosaur.pth"))
model_service = DepthAnythingModelService(CHECKPOINT_PATH)
SCENE_GRID_SIZE = 256
MAX_UPLOAD_BYTES = int(os.getenv("DEPTHWIZARD_MAX_UPLOAD_BYTES", str(256 * 1024 * 1024)))


def _resize_semantic_logits(logits: np.ndarray, target_size: int) -> np.ndarray:
    """Resize continuous class evidence before converting it to labels."""
    values = np.asarray(logits, dtype=np.float32)
    if values.ndim != 3:
        raise ValueError("semantic logits must have shape (classes, height, width)")
    return np.stack([
        np.asarray(
            Image.fromarray(channel, mode="F").resize((target_size, target_size), Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
        for channel in values
    ])


def _prepare_semantic_labels(logits: np.ndarray, target_size: int, boundary_confidence: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Return cleaned full-resolution and scene-grid semantic labels."""
    values = np.asarray(logits, dtype=np.float32)
    full_boundary = None if boundary_confidence is None else np.asarray(boundary_confidence, dtype=np.float32)
    full_labels = clean_semantic_labels(np.argmax(values, axis=0).astype(np.uint8), boundary_confidence=full_boundary)
    scene_values = _resize_semantic_logits(values, target_size)
    scene_boundary = None if full_boundary is None else np.asarray(
        Image.fromarray(full_boundary, mode="F").resize((target_size, target_size), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    scene_labels = clean_semantic_labels(np.argmax(scene_values, axis=0).astype(np.uint8), boundary_confidence=scene_boundary)
    return full_labels, scene_labels


app = FastAPI(title="DepthWizard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


class RoutePoint(BaseModel):
    row: int
    column: int


class RouteRequest(BaseModel):
    semanticData: list[int]
    gridSize: int
    start: RoutePoint
    destination: RoutePoint
    blockedCells: list[RoutePoint] = Field(default_factory=list)
    avoidWater: bool = True
    profile: str = "fastest"
    heightData: list[float] | None = None
    uncertaintyData: list[float] | None = None


def _demo_route_scenario() -> dict[str, object]:
    grid_size = 32
    semantic_data = _fixture_semantic_grid(grid_size).ravel().tolist()
    start = {"row": 14, "column": 1}
    destination = {"row": 14, "column": 30}
    debris_zone = {"row": 14, "column": 20}
    flood_cell = {"row": 14, "column": 8}
    debris = [{"row": row, "column": column} for row in range(debris_zone["row"] - 1, debris_zone["row"] + 2) for column in range(debris_zone["column"] - 1, debris_zone["column"] + 2)]
    height_data = [0.0] * (grid_size * grid_size)
    baseline = plan_ranked_routes(semantic_data, grid_size, start, destination, height_data=height_data, profile="fastest")
    flooded_semantics = semantic_data.copy()
    flooded_semantics[flood_cell["row"] * grid_size + flood_cell["column"]] = 4
    rerouted = plan_ranked_routes(flooded_semantics, grid_size, start, destination, debris, height_data=height_data, profile="fastest")
    return {"fixture": "gamus-urban-demo", "gridSize": grid_size, "start": start, "destination": destination, "debrisZone": debris_zone, "floodCell": flood_cell, "baseline": baseline, "rerouted": rerouted}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "depthwizard-api", "version": app.version}


@app.post("/api/route")
def route(request: RouteRequest) -> dict[str, object]:
    try:
        return plan_ranked_routes(
            request.semanticData,
            request.gridSize,
            request.start.model_dump(),
            request.destination.model_dump(),
            [point.model_dump() for point in request.blockedCells],
            request.avoidWater,
            request.heightData,
            request.uncertaintyData,
            request.profile,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/route/demo")
def route_demo() -> dict[str, object]:
    try:
        return _demo_route_scenario()
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/benchmarks")
def benchmarks() -> dict[str, list[dict[str, object]]]:
    return {"benchmarks": [_write_benchmark_assets(group) for group in ("urban", "sparse", "hilly", "forested")]}


def _fixture_city() -> Image.Image:
    image = Image.new("RGB", (768, 512), "#c6d5b2")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 768, 42), fill="#72aee8")
    draw.rectangle((0, 210, 768, 275), fill="#f7f5ef")
    draw.rectangle((330, 0, 390, 512), fill="#f7f5ef")
    draw.rectangle((30, 32, 280, 170), fill="#afb9c8")
    draw.rectangle((440, 42, 710, 180), fill="#c0c7d1")
    draw.rectangle((65, 315, 300, 465), fill="#b8c0ca")
    draw.rectangle((440, 315, 700, 475), fill="#abb7c5")
    draw.rectangle((120, 85, 188, 150), fill="#8899ad")
    draw.rectangle((520, 75, 590, 143), fill="#8c9caf")
    draw.rectangle((485, 350, 565, 440), fill="#8799ad")
    for x, y in [(18, 290), (290, 295), (400, 295), (720, 290), (318, 35), (408, 185)]:
        draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill="#7ea26d")
    return image


def _write_fixture_prediction_assets(image: Image.Image, prediction_id: str) -> tuple[str, str, list[float]]:
    image = image.convert("RGB")
    input_path = MEDIA_DIR / f"{prediction_id}-input.png"
    height_path = MEDIA_DIR / f"{prediction_id}-height.png"
    image.save(input_path, format="PNG")

    grayscale = ImageOps.grayscale(image).resize((128, 128), Image.Resampling.BILINEAR)
    height_data = [round(pixel / 255 * 42.7, 3) for pixel in grayscale.get_flattened_data()]
    height_preview = ImageOps.autocontrast(grayscale).filter(ImageFilter.GaussianBlur(radius=1.2))
    height_preview.save(height_path, format="PNG")
    return f"/media/{input_path.name}", f"/media/{height_path.name}", height_data


def _fixture_semantic_grid(grid_size: int = 128) -> np.ndarray:
    """Create a deterministic, image-aligned seven-class GAMUS fixture grid."""
    labels = np.full((grid_size, grid_size), 1, dtype=np.uint8)
    labels[-6:, -6:] = 0

    def rectangle(left: int, top: int, right: int, bottom: int, class_id: int) -> None:
        labels[top:bottom, left:right] = class_id

    def scaled_rectangle(box: tuple[int, int, int, int], class_id: int) -> None:
        left, top, right, bottom = box
        rectangle(
            round(left / 768 * grid_size),
            round(top / 512 * grid_size),
            round(right / 768 * grid_size),
            round(bottom / 512 * grid_size),
            class_id,
        )

    # These regions correspond to the roads, parks, water, and building blocks
    # drawn by _fixture_city, so every grid cell has the same image coordinate frame.
    rectangle(0, 0, grid_size, round(grid_size * 0.08), 4)
    rectangle(0, round(grid_size * 0.41), grid_size, round(grid_size * 0.54), 5)
    rectangle(round(grid_size * 0.43), 0, round(grid_size * 0.51), grid_size, 5)
    rectangle(round(grid_size * 0.04), round(grid_size * 0.58), round(grid_size * 0.38), grid_size, 2)
    scaled_rectangle((30, 32, 280, 170), 3)
    scaled_rectangle((440, 42, 710, 180), 3)
    scaled_rectangle((65, 315, 300, 465), 3)
    scaled_rectangle((440, 315, 700, 475), 3)
    scaled_rectangle((120, 85, 188, 150), 3)
    scaled_rectangle((520, 75, 590, 143), 3)
    scaled_rectangle((485, 350, 565, 440), 3)

    for x, y in [(18, 290), (290, 295), (400, 295), (720, 290), (318, 35), (408, 185)]:
        center_x = round(x / 768 * grid_size)
        center_y = round(y / 512 * grid_size)
        radius = max(2, round(14 / 768 * grid_size))
        yy, xx = np.ogrid[:grid_size, :grid_size]
        labels[(xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius**2] = 6
    return labels


def _write_semantic_asset(labels: np.ndarray, prediction_id: str) -> tuple[str, list[int]]:
    path = MEDIA_DIR / f"{prediction_id}-semantics.png"
    palette = np.asarray([tuple(int(color.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4)) for color in [item["color"] for item in SEMANTIC_CLASSES]], dtype=np.uint8)
    Image.fromarray(palette[labels], mode="RGB").save(path, format="PNG")
    return f"/media/{path.name}", [int(value) for value in labels.ravel()]


def _write_boundary_asset(boundary_confidence: np.ndarray, prediction_id: str) -> tuple[str, list[float]]:
    values = np.clip(np.nan_to_num(np.asarray(boundary_confidence, dtype=np.float32), nan=0.0), 0.0, 1.0)
    path = MEDIA_DIR / f"{prediction_id}-boundaries.png"
    Image.fromarray(np.round(values * 255).astype(np.uint8), mode="L").save(path, format="PNG")
    grid = Image.fromarray(values, mode="F").resize((SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.BILINEAR)
    return f"/media/{path.name}", [round(float(value), 4) for value in np.asarray(grid, dtype=np.float32).ravel()]


def _scene_validity_mask(valid_mask: np.ndarray) -> np.ndarray:
    return np.asarray(
        Image.fromarray(np.asarray(valid_mask, dtype=np.uint8) * 255).resize(
            (SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.NEAREST,
        ),
        dtype=np.uint8,
    ) > 0


def _write_model_prediction_assets(
    image: Image.Image,
    height_map: np.ndarray,
    prediction_id: str,
    valid_mask: np.ndarray | None = None,
) -> tuple[str, str, list[float], float, float, list[bool] | None]:
    image = image.convert("RGB")
    input_path = MEDIA_DIR / f"{prediction_id}-input.png"
    height_path = MEDIA_DIR / f"{prediction_id}-height.png"
    mask_grid = None
    if valid_mask is not None:
        mask = np.asarray(valid_mask, dtype=bool)
        mask_grid = _scene_validity_mask(mask)
        alpha = np.asarray(mask, dtype=np.uint8) * 255
        if np.all(mask):
            image.save(input_path, format="PNG")
        else:
            Image.fromarray(np.dstack((np.asarray(image), alpha))).save(input_path, format="PNG")
    else:
        image.save(input_path, format="PNG")

    clean_height_map = np.asarray(height_map, dtype=np.float32)
    if valid_mask is not None:
        clean_height_map = np.where(valid_mask, clean_height_map, 0.0)
    clean_height_map = np.maximum(clean_height_map, 0.0)
    valid_heights = clean_height_map if valid_mask is None else clean_height_map[valid_mask]
    min_height = float(valid_heights.min())
    max_height = float(valid_heights.max())
    preview_scale = max(max_height, 1e-6)
    preview = np.clip(clean_height_map / preview_scale * 255, 0, 255).astype(np.uint8)
    if valid_mask is not None and not np.all(valid_mask):
        Image.fromarray(np.dstack((preview, preview, preview, np.asarray(valid_mask, dtype=np.uint8) * 255))).save(height_path, format="PNG")
    else:
        Image.fromarray(preview).save(height_path, format="PNG")

    if valid_mask is None:
        grid = Image.fromarray(clean_height_map).resize((SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.BILINEAR)
        scene_heights = np.array(grid, dtype=np.float32, copy=True)
    else:
        weighted_heights = np.where(valid_mask, clean_height_map, 0.0)
        resized_heights = np.asarray(
            Image.fromarray(weighted_heights).resize((SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
        coverage = np.asarray(
            Image.fromarray(np.asarray(valid_mask, dtype=np.float32)).resize(
                (SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.BILINEAR,
            ),
            dtype=np.float32,
        )
        scene_heights = np.divide(resized_heights, coverage, out=np.zeros_like(resized_heights), where=coverage > 1e-6)
    validity_data = None if mask_grid is None or np.all(mask_grid) else mask_grid.ravel().tolist()
    if mask_grid is not None:
        scene_heights[~mask_grid] = 0.0
    height_data = [round(float(value), 3) for value in scene_heights.ravel()]
    return (
        f"/media/{input_path.name}",
        f"/media/{height_path.name}",
        height_data,
        min_height,
        max_height,
        validity_data,
    )


def _building_regions(
    height_data: list[float] | np.ndarray,
    grid_size: int,
    max_height: float,
    semantic_data: list[int] | np.ndarray | None = None,
    semantic_grid_size: int | None = None,
    boundary_data: list[float] | np.ndarray | None = None,
) -> list[dict[str, object]]:
    """Extract polygon footprints from aligned semantics, with an nDSM fallback."""
    values = np.asarray(height_data, dtype=np.float32)
    if values.ndim == 1:
        values = values.reshape((grid_size, grid_size))
    if values.ndim != 2:
        raise ValueError(f"Expected a 2D height map, got {values.shape}")
    source = "semantic_head" if semantic_data is not None and semantic_grid_size else "height_threshold_fallback"
    if semantic_data is not None and semantic_grid_size:
        labels = np.asarray(semantic_data, dtype=np.uint8)
        if labels.ndim == 1:
            labels = labels.reshape((semantic_grid_size, semantic_grid_size))
        if labels.shape != values.shape:
            labels = np.asarray(
                Image.fromarray(labels, mode="L").resize((values.shape[1], values.shape[0]), Image.Resampling.NEAREST),
                dtype=np.uint8,
            )
    else:
        non_zero = values[values > max(float(values.min()), 1e-3)]
        if non_zero.size == 0:
            return []
        threshold = max(float(np.percentile(non_zero, 72)), max_height * 0.2, 0.75)
        labels = np.zeros(values.shape, dtype=np.uint8)
        labels[values >= threshold] = BUILDING_CLASS

    minimum_area = 1 if values.shape[0] <= SCENE_GRID_SIZE else 4
    boundaries = None if boundary_data is None else np.asarray(boundary_data, dtype=np.float32)
    if boundaries is not None and boundaries.ndim == 1:
        boundaries = boundaries.reshape((grid_size, grid_size))
    if boundaries is not None and boundaries.shape != values.shape:
        boundaries = np.asarray(Image.fromarray(boundaries, mode="F").resize((values.shape[1], values.shape[0]), Image.Resampling.BILINEAR), dtype=np.float32)
    regions = extract_building_footprints(labels, values, minimum_area=minimum_area, boundary_confidence=boundaries)
    for region in regions:
        region["source"] = source
        region.pop("area", None)
        region.pop("minRow", None)
        region.pop("maxColumn", None)
    return regions


def compute_metrics(predicted: np.ndarray, ground_truth: np.ndarray) -> dict[str, float]:
    predicted_flat = predicted.astype(np.float64).ravel()
    ground_truth_flat = ground_truth.astype(np.float64).ravel()
    difference = predicted_flat - ground_truth_flat
    predicted_centered = predicted_flat - predicted_flat.mean()
    ground_truth_centered = ground_truth_flat - ground_truth_flat.mean()
    denominator = np.sqrt(np.sum(predicted_centered**2) * np.sum(ground_truth_centered**2))
    correlation = float(np.sum(predicted_centered * ground_truth_centered) / denominator) if denominator else 0.0
    return {
        "rmse": float(np.sqrt(np.mean(difference**2))),
        "mae": float(np.mean(np.abs(difference))),
        "correlation": correlation,
    }


def compute_building_boundary_f1(predicted: np.ndarray, ground_truth: np.ndarray) -> float:
    """Compare height-derived building boundaries without implying absolute DSM truth."""
    threshold = max(float(np.percentile(ground_truth, 72)), 0.75)

    def boundary(values: np.ndarray) -> np.ndarray:
        mask = values >= threshold
        padded = np.pad(mask, 1, constant_values=False)
        return mask & (
            (padded[:-2, 1:-1] != mask)
            | (padded[2:, 1:-1] != mask)
            | (padded[1:-1, :-2] != mask)
            | (padded[1:-1, 2:] != mask)
        )

    predicted_boundary = boundary(predicted)
    ground_truth_boundary = boundary(ground_truth)
    true_positive = float(np.sum(predicted_boundary & ground_truth_boundary))
    precision = true_positive / float(np.sum(predicted_boundary)) if np.any(predicted_boundary) else 0.0
    recall = true_positive / float(np.sum(ground_truth_boundary)) if np.any(ground_truth_boundary) else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _landscape_fixture(group: str) -> Image.Image:
    image = _fixture_city()
    draw = ImageDraw.Draw(image)
    if group == "sparse":
        draw.rectangle((0, 0, image.width, image.height), fill="#d6dfc4")
        draw.rectangle((80, 90, 280, 205), fill="#c5cbd0")
        draw.rectangle((430, 290, 650, 420), fill="#bfc7ce")
    elif group == "hilly":
        for row in range(image.height):
            shade = int(170 + 35 * np.sin(row / image.height * np.pi * 2))
            draw.line((0, row, image.width, row), fill=(shade, min(210, shade + 20), 155))
        draw.rectangle((80, 100, 280, 205), fill="#c2c8ce")
        draw.rectangle((430, 280, 650, 420), fill="#b9c0c8")
    elif group == "forested":
        draw.rectangle((0, 0, image.width, image.height), fill="#7f9f72")
        for x in range(30, image.width, 55):
            for y in range(35, image.height, 58):
                draw.ellipse((x - 18, y - 18, x + 18, y + 18), fill="#527b55")
        draw.rectangle((255, 205, 515, 285), fill="#f2eee3")
        draw.rectangle((320, 140, 450, 220), fill="#bfc7ce")
    return image


def _semantic_metrics(predicted: np.ndarray, target: np.ndarray) -> dict[str, float]:
    ious = []
    for class_id in range(CLASS_COUNT):
        predicted_class = predicted == class_id
        target_class = target == class_id
        union = np.sum(predicted_class | target_class)
        if union:
            ious.append(float(np.sum(predicted_class & target_class) / union))
    predicted_building = predicted == BUILDING_CLASS
    target_building = target == BUILDING_CLASS
    intersection = np.sum(predicted_building & target_building)
    union = np.sum(predicted_building | target_building)

    def boundary(mask: np.ndarray) -> np.ndarray:
        padded = np.pad(mask, 1, constant_values=False)
        interior = padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
        return mask & ~interior

    predicted_boundary = boundary(predicted_building)
    target_boundary = boundary(target_building)
    boundary_tp = np.sum(predicted_boundary & target_boundary)
    boundary_denominator = np.sum(predicted_boundary) + np.sum(target_boundary)
    return {
        "semanticMiou": float(np.mean(ious)) if ious else 0.0,
        "buildingIoU": float(intersection / union) if union else 0.0,
        "buildingBoundaryF1": float(2 * boundary_tp / boundary_denominator) if boundary_denominator else 0.0,
    }


def _write_benchmark_assets(landscape_group: str) -> dict[str, object]:
    benchmark_id = f"gamus-{landscape_group}-validation"
    image = _landscape_fixture(landscape_group)
    input_path = MEDIA_DIR / f"{benchmark_id}-input.png"
    reference_path = MEDIA_DIR / f"{benchmark_id}-reference.png"
    prediction_path = MEDIA_DIR / f"{benchmark_id}-prediction.png"
    error_path = MEDIA_DIR / f"{benchmark_id}-error.png"
    image.save(input_path, format="PNG")

    grayscale = ImageOps.grayscale(image).resize((256, 170), Image.Resampling.BILINEAR)
    ground_truth = np.asarray(grayscale, dtype=np.float32) / 255 * 42.7
    smoothed = np.asarray(grayscale.filter(ImageFilter.GaussianBlur(radius=2.2)), dtype=np.float32) / 255 * 42.7
    predicted = np.clip(smoothed * 0.92 + 0.65, 0, 42.7)
    baseline = np.asarray(grayscale, dtype=np.float32) / 255 * 42.7
    error = np.abs(predicted - ground_truth)
    target_semantic = _fixture_semantic_grid(170)
    predicted_semantic = np.roll(target_semantic, 1 if landscape_group != "urban" else 0, axis=1)
    baseline_semantic = np.roll(target_semantic, 2, axis=1)
    semantic_metrics = _semantic_metrics(predicted_semantic, target_semantic)
    baseline_semantic_metrics = _semantic_metrics(baseline_semantic, target_semantic)

    def save_map(values: np.ndarray, path: Path, scale: float) -> None:
        pixels = np.clip(values / max(scale, 1e-6) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(pixels, mode="L").save(path, format="PNG")

    save_map(ground_truth, reference_path, 42.7)
    save_map(predicted, prediction_path, 42.7)
    save_map(error, error_path, max(float(error.max()), 1.0))
    metrics = compute_metrics(predicted, ground_truth)
    baseline_metrics = compute_metrics(baseline, ground_truth)
    return {
        "id": benchmark_id,
        "name": f"{('GAMUS urban' if landscape_group == 'urban' else f'Synthetic {landscape_group}')} landscape comparison",
        "landscapeGroup": landscape_group,
        "sourceDataset": "GAMUS" if landscape_group == "urban" else "Synthetic stress fixture",
        "split": "validation",
        "referenceStatus": "scaffold_fixture",
        "heightReference": "relative",
        "coverageNote": "Deterministic scaffold fixture; replace with held-out landscape reference data before presenting as measured validation.",
        "knownLimitations": ["GAMUS coverage is urban-focused.", "Sparse, hilly, and forested groups are visual stress fixtures, not held-out survey data."],
        "inputImageUrl": f"/media/{input_path.name}",
        "groundTruthUrl": f"/media/{reference_path.name}",
        "predictionUrl": f"/media/{prediction_path.name}",
        "errorMapUrl": f"/media/{error_path.name}",
        "metrics": {**{key: round(value, 4) for key, value in metrics.items()}, **{key: round(value, 4) for key, value in semantic_metrics.items()}},
        "comparison": {
            "baseline": {**{key: round(value, 4) for key, value in baseline_metrics.items()}, **{key: round(value, 4) for key, value in baseline_semantic_metrics.items()}, "buildingBoundaryF1": round(compute_building_boundary_f1(baseline, ground_truth), 4)},
            "improved": {**{key: round(value, 4) for key, value in metrics.items()}, **{key: round(value, 4) for key, value in semantic_metrics.items()}},
        },
        "width": image.width,
        "height": image.height,
    }


def _is_geotiff(filename: str, content_type: str | None) -> bool:
    return filename.lower().endswith((".tif", ".tiff")) or content_type in {"image/tiff", "image/geotiff"}


def _normalize_raster_bands(bands: np.ndarray, valid_mask: np.ndarray | None = None) -> np.ndarray:
    if bands.dtype == np.uint8:
        return bands
    normalized = np.empty_like(bands, dtype=np.uint8)
    for index, band in enumerate(bands):
        values = np.nan_to_num(band.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        if np.issubdtype(bands.dtype, np.integer):
            high = float(np.iinfo(bands.dtype).max)
            normalized[index] = np.clip(values / max(high, 1.0) * 255, 0, 255).astype(np.uint8)
            continue
        sample = values if valid_mask is None else values[valid_mask]
        low, high = np.percentile(sample, [2, 98])
        if high <= low:
            normalized[index] = np.zeros_like(values, dtype=np.uint8)
        else:
            normalized[index] = np.clip((values - low) / (high - low) * 255, 0, 255).astype(np.uint8)
    return normalized


def _read_geotiff(raw: bytes) -> tuple[Image.Image, dict[str, object], np.ndarray]:
    try:
        with MemoryFile(raw).open() as source:
            if source.width < 1 or source.height < 1:
                raise HTTPException(status_code=400, detail="The GeoTIFF must have non-zero width and height.")
            if source.count not in (3, 4):
                raise HTTPException(
                    status_code=415,
                    detail=f"This GeoTIFF has {source.count} bands. DepthWizard accepts RGB or RGBA GeoTIFFs only.",
                )
            raster_values = source.read()
            valid_mask = (source.dataset_mask() > 0) & np.all(np.isfinite(raster_values), axis=0)
            if not np.any(valid_mask):
                raise HTTPException(status_code=400, detail="The GeoTIFF contains no valid pixels.")
            transform = source.transform
            if (
                not np.all(np.isfinite(tuple(transform)))
                or not np.isfinite(transform.determinant)
                or transform.determinant == 0
                or not np.all(np.isfinite(source.bounds))
                or not np.all(np.isfinite(source.res))
                or min(abs(value) for value in source.res) <= 0
            ):
                raise HTTPException(status_code=400, detail="The GeoTIFF has invalid spatial metadata.")
            bands = _normalize_raster_bands(raster_values, valid_mask)
            if not np.all(valid_mask):
                # Do not let nodata become a false zero-height visual signal. The
                # model still receives an RGB image, but invalid pixels are filled
                # from valid-image statistics and the mask is reported explicitly.
                for band_index, band in enumerate(bands):
                    valid_values = band[valid_mask]
                    fill_value = int(np.median(valid_values)) if valid_values.size else 0
                    band[~valid_mask] = fill_value
            pixels = np.moveaxis(bands, 0, -1)
            image = Image.fromarray(pixels[:, :, :3], mode="RGB")
            bounds = source.bounds
            metadata = {
                "crs": source.crs.to_string() if source.crs else None,
                "bounds": {
                    "left": float(bounds.left),
                    "bottom": float(bounds.bottom),
                    "right": float(bounds.right),
                    "top": float(bounds.top),
                },
                "transform": [float(value) for value in source.transform],
                "resolution": [float(value) for value in source.res],
                "width": int(source.width),
                "height": int(source.height),
                "bands": source.count,
                "driver": source.driver,
                "validPixelFraction": float(np.mean(valid_mask)),
            }
            return image, metadata, valid_mask
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail="The uploaded GeoTIFF could not be read.") from error


def _read_image(raw: bytes, filename: str, content_type: str | None) -> tuple[Image.Image, dict[str, object] | None, str, np.ndarray | None]:
    if _is_geotiff(filename, content_type):
        image, metadata, valid_mask = _read_geotiff(raw)
        return image, metadata, "geotiff", valid_mask
    try:
        return Image.open(BytesIO(raw)).convert("RGB"), None, "image", None
    except Exception as error:
        raise HTTPException(status_code=400, detail="The uploaded file is not a readable image.") from error


@app.post("/api/predict")
async def predict(
    file: UploadFile | None = File(default=None),
    example_id: str | None = Form(default=None),
    ground_elevation: float | None = Form(default=None),
    ground_elevation_provenance: str | None = Form(default=None),
    calibrate_geotiff: bool = Form(default=True),
    ground_control_points: str | None = Form(default=None),
) -> dict[str, object]:
    if file is None and example_id is None:
        raise HTTPException(status_code=400, detail="Upload an image or choose a GAMUS example.")

    prediction_token = uuid4().hex[:10]
    prediction_id = f"prediction-{prediction_token}"
    geospatial_metadata: dict[str, object] | None = None
    input_format = "example"
    is_fixture = False
    validity_data: list[bool] | None = None
    semantic_map_url: str | None = None
    semantic_data: list[int] | None = None
    semantic_grid_size: int | None = None
    semantic_source = "unavailable"
    semantic_labels: np.ndarray | None = None
    boundary_map_url: str | None = None
    boundary_data: list[float] | None = None
    boundary_grid_size: int | None = None
    boundary_source = "unavailable"
    boundary_confidence: float | None = None
    boundary_probability: np.ndarray | None = None
    dsm_url: str | None = None
    calibration: dict[str, object] = {
        "status": "not_applicable",
        "method": None,
        "confidence": None,
        "residualError": None,
        "groundPixelCount": None,
    }
    if file is not None:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            limit_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
            raise HTTPException(status_code=413, detail=f"The uploaded file is too large. Maximum size is {limit_mb:.0f} MB.")
        source_name = file.filename or "uploaded-image"
        if not _is_geotiff(source_name, file.content_type) and file.content_type not in {"image/png", "image/jpeg", "image/jpg"}:
            raise HTTPException(status_code=415, detail="Use a PNG, JPEG, or RGB GeoTIFF image.")
        image, geospatial_metadata, input_format, valid_mask = _read_image(raw, source_name, file.content_type)
        try:
            if hasattr(model_service, "predict_result"):
                prediction = model_service.predict_result(image)
                if not isinstance(prediction, dict) or "height" not in prediction:
                    raise ModelUnavailableError("The model returned an invalid height map.")
                height_map = np.asarray(prediction["height"], dtype=np.float32)
                expected_shape = (image.height, image.width)
                semantic_logits = prediction.get("semantic")
                if semantic_logits is not None:
                    semantic_logits = np.asarray(semantic_logits, dtype=np.float32)
                    if semantic_logits.shape != (len(SEMANTIC_CLASSES), *expected_shape) or not np.all(np.isfinite(semantic_logits)):
                        raise ModelUnavailableError("The model returned invalid semantic output that is misaligned or contains non-finite values.")
                boundary_output = prediction.get("boundary")
                if boundary_output is not None:
                    boundary_output = np.asarray(boundary_output, dtype=np.float32)
                    if boundary_output.shape != expected_shape or not np.all(np.isfinite(boundary_output)):
                        raise ModelUnavailableError("The model returned invalid boundary output that is misaligned or contains non-finite values.")
                if boundary_output is not None:
                    boundary_probability = np.clip(boundary_output, 0.0, 1.0).copy()
                    if valid_mask is not None:
                        boundary_probability[~valid_mask] = 0.0
                if semantic_logits is not None:
                    semantic_labels, semantic_grid = _prepare_semantic_labels(semantic_logits, SCENE_GRID_SIZE, boundary_probability)
                    if valid_mask is not None:
                        semantic_labels[~valid_mask] = 0
                        semantic_grid_mask = _scene_validity_mask(valid_mask)
                        semantic_grid[~semantic_grid_mask] = 0
                    if semantic_labels.size and (semantic_labels.min() < 0 or semantic_labels.max() >= len(SEMANTIC_CLASSES)):
                        raise ModelUnavailableError("The model returned a semantic class outside GAMUS IDs 0..6.")
                    semantic_data = [int(value) for value in semantic_grid.ravel()]
                    semantic_grid_size = SCENE_GRID_SIZE
                    semantic_source = "trained"
            else:
                height_map = np.asarray(model_service.predict(image), dtype=np.float32)
            if height_map.shape != (image.height, image.width) or not np.all(np.isfinite(height_map)):
                raise ModelUnavailableError("The model returned an invalid height map that is misaligned or contains non-finite values.")
        except ModelUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except (TypeError, ValueError, KeyError) as error:
            raise HTTPException(status_code=503, detail="The model returned an invalid prediction.") from error
        if boundary_probability is not None:
            boundary_map_url, boundary_data = _write_boundary_asset(boundary_probability, prediction_id)
            boundary_grid_size = SCENE_GRID_SIZE
            boundary_source = "trained"
            confidence_values = boundary_probability if valid_mask is None else boundary_probability[valid_mask]
            boundary_confidence = float(np.mean(np.maximum(confidence_values, 1.0 - confidence_values)))
        if semantic_labels is not None:
            semantic_map_url, semantic_data = _write_semantic_asset(semantic_grid, prediction_id)
        input_url, height_url, height_data, min_height, max_height, validity_data = _write_model_prediction_assets(
            image,
            height_map,
            prediction_id,
            valid_mask,
        )
        full_building_regions = _building_regions(
            height_data,
            SCENE_GRID_SIZE,
            max_height,
            semantic_data,
            semantic_grid_size,
            boundary_data,
        )
        if input_format == "geotiff":
            if not calibrate_geotiff:
                calibration = {**calibration, "status": "not_applicable"}
            elif not geospatial_metadata or not geospatial_metadata.get("crs"):
                calibration = {
                    "status": "missing_spatial_reference",
                    "method": None,
                    "confidence": 0.0,
                    "residualError": None,
                    "groundPixelCount": 0,
                }
            else:
                try:
                    points = parse_ground_control_points(ground_control_points)
                except ValueError as error:
                    raise HTTPException(status_code=400, detail=str(error)) from error
                dsm, calibration = calibrate_dsm(height_map, semantic_labels, ground_elevation, points, valid_mask)
                if points:
                    calibration["accuracyStatus"] = "unverified"
                elif ground_elevation is not None:
                    provenance = (ground_elevation_provenance or "").strip() or None
                    calibration["groundElevationProvenance"] = provenance
                    calibration["accuracyStatus"] = "provenance_provided_unverified" if provenance else "unverified"
                if dsm is not None:
                    dsm_path = MEDIA_DIR / f"{prediction_id}-dsm.tif"
                    try:
                        write_dsm_geotiff(dsm_path, dsm, geospatial_metadata)
                    except ValueError as error:
                        calibration = {
                            **calibration,
                            "status": "invalid_spatial_metadata",
                            "error": str(error),
                            "groundPixelCount": calibration.get("groundPixelCount", 0),
                        }
                    except (OSError, rasterio.errors.RasterioError) as error:
                        calibration = {**calibration, "status": "dsm_write_failed", "error": str(error)}
                    else:
                        dsm_url = f"/media/{dsm_path.name}"
    elif example_id == "gamus-urban-demo":
        image = _fixture_city()
        source_name = "gamus-urban-demo.png"
        is_fixture = True
        prediction_id = f"fixture-{prediction_token}"
        input_url, height_url, height_data = _write_fixture_prediction_assets(image, prediction_id)
        semantic_grid_size = int(np.sqrt(len(height_data)))
        semantic_labels = _fixture_semantic_grid(semantic_grid_size)
        semantic_map_url, semantic_data = _write_semantic_asset(semantic_labels, prediction_id)
        semantic_source = "fixture"
        min_height = 0.0
        max_height = 42.7
    else:
        raise HTTPException(status_code=404, detail="That GAMUS example does not exist.")

    prediction_width = int(height_map.shape[1]) if not is_fixture else 128
    prediction_height = int(height_map.shape[0]) if not is_fixture else 128
    scene_grid_size = int(np.sqrt(len(height_data)))
    building_regions = full_building_regions if not is_fixture and "full_building_regions" in locals() else _building_regions(
        height_data,
        scene_grid_size,
        max_height,
        semantic_data,
        semantic_grid_size,
        boundary_data,
    )
    return {
        "id": prediction_id,
        "status": "complete",
        "inputImageUrl": input_url,
        "heightMapUrl": height_url,
        "width": image.width,
        "height": image.height,
        "predictionWidth": prediction_width,
        "predictionHeight": prediction_height,
        "gridSize": scene_grid_size,
        "heightData": height_data,
        "validityData": validity_data,
        "semanticClasses": list(SEMANTIC_CLASSES),
        "semanticGridSize": semantic_grid_size,
        "semanticData": semantic_data,
        "semanticMapUrl": semantic_map_url,
        "semanticSource": semantic_source,
        "boundaryMapUrl": boundary_map_url,
        "boundaryGridSize": boundary_grid_size,
        "boundaryData": boundary_data,
        "boundarySource": boundary_source,
        "boundaryConfidence": boundary_confidence,
        "buildingRegions": building_regions,
        "buildingRegionSource": "semantic_head" if semantic_source in {"fixture", "trained"} else "height_threshold_fallback",
        "minHeight": min_height,
        "maxHeight": max_height,
        "resultType": "metric_dsm" if dsm_url else "estimated_ndsm",
        "heightReference": "absolute" if dsm_url else "relative",
        "heightUnit": "meters",
        "dsmUrl": dsm_url,
        "calibration": calibration,
        "sourceName": source_name,
        "isFixture": is_fixture,
        "inputFormat": input_format,
        "geospatial": geospatial_metadata,
    }
