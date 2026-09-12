from io import BytesIO
import os
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from rasterio.io import MemoryFile

from app.model_service import DepthAnythingModelService, ModelUnavailableError

MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = Path(os.getenv("DEPTHWIZARD_CHECKPOINT", PROJECT_ROOT / "astra.pth"))
model_service = DepthAnythingModelService(CHECKPOINT_PATH)
SCENE_GRID_SIZE = 256
SEMANTIC_CLASSES: tuple[dict[str, object], ...] = (
    {"id": 0, "name": "ground", "label": "Ground", "color": "#b6c99e"},
    {"id": 1, "name": "low_vegetation", "label": "Low vegetation", "color": "#78a66b"},
    {"id": 2, "name": "building", "label": "Building", "color": "#c7cbd1"},
    {"id": 3, "name": "water", "label": "Water", "color": "#72aee8"},
    {"id": 4, "name": "road", "label": "Road", "color": "#f7f5ef"},
    {"id": 5, "name": "tree", "label": "Tree", "color": "#3d744d"},
)


app = FastAPI(title="DepthWizard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "depthwizard-api", "version": app.version}


@app.get("/api/benchmarks")
def benchmarks() -> dict[str, list[dict[str, object]]]:
    return {"benchmarks": [_write_benchmark_assets()]}


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
    """Create a deterministic, image-aligned six-class GAMUS fixture grid."""
    labels = np.full((grid_size, grid_size), 0, dtype=np.uint8)

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
    rectangle(0, 0, grid_size, round(grid_size * 0.08), 3)
    rectangle(0, round(grid_size * 0.41), grid_size, round(grid_size * 0.54), 4)
    rectangle(round(grid_size * 0.43), 0, round(grid_size * 0.51), grid_size, 4)
    rectangle(round(grid_size * 0.04), round(grid_size * 0.58), round(grid_size * 0.38), grid_size, 1)
    scaled_rectangle((30, 32, 280, 170), 2)
    scaled_rectangle((440, 42, 710, 180), 2)
    scaled_rectangle((65, 315, 300, 465), 2)
    scaled_rectangle((440, 315, 700, 475), 2)
    scaled_rectangle((120, 85, 188, 150), 2)
    scaled_rectangle((520, 75, 590, 143), 2)
    scaled_rectangle((485, 350, 565, 440), 2)

    for x, y in [(18, 290), (290, 295), (400, 295), (720, 290), (318, 35), (408, 185)]:
        center_x = round(x / 768 * grid_size)
        center_y = round(y / 512 * grid_size)
        radius = max(2, round(14 / 768 * grid_size))
        yy, xx = np.ogrid[:grid_size, :grid_size]
        labels[(xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius**2] = 5
    return labels


def _write_semantic_asset(labels: np.ndarray, prediction_id: str) -> tuple[str, list[int]]:
    path = MEDIA_DIR / f"{prediction_id}-semantics.png"
    palette = np.asarray([tuple(int(color.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4)) for color in [item["color"] for item in SEMANTIC_CLASSES]], dtype=np.uint8)
    Image.fromarray(palette[labels], mode="RGB").save(path, format="PNG")
    return f"/media/{path.name}", [int(value) for value in labels.ravel()]


def _write_model_prediction_assets(
    image: Image.Image,
    height_map: np.ndarray,
    prediction_id: str,
) -> tuple[str, str, list[float], float, float]:
    image = image.convert("RGB")
    input_path = MEDIA_DIR / f"{prediction_id}-input.png"
    height_path = MEDIA_DIR / f"{prediction_id}-height.png"
    image.save(input_path, format="PNG")

    clean_height_map = np.nan_to_num(height_map.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    clean_height_map = np.maximum(clean_height_map, 0.0)
    min_height = float(clean_height_map.min())
    max_height = float(clean_height_map.max())
    preview_scale = max(max_height, 1e-6)
    preview = np.clip(clean_height_map / preview_scale * 255, 0, 255).astype(np.uint8)
    Image.fromarray(preview, mode="L").save(height_path, format="PNG")

    grid = Image.fromarray(clean_height_map, mode="F").resize((SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.BILINEAR)
    height_data = [round(float(value), 3) for value in np.asarray(grid, dtype=np.float32).ravel()]
    return (
        f"/media/{input_path.name}",
        f"/media/{height_path.name}",
        height_data,
        min_height,
        max_height,
    )


def _building_regions(height_data: list[float], grid_size: int, max_height: float) -> list[dict[str, object]]:
    """Extract conservative, small-building-friendly regions from the estimated nDSM.

    This is deliberately a fallback until a GAMUS semantic head is trained. The
    renderer receives explicit footprints instead of repeating the old browser-side
    threshold/blob logic, and the response labels the source as height-derived.
    """
    values = np.asarray(height_data, dtype=np.float32).reshape((grid_size, grid_size))
    non_zero = values[values > max(float(values.min()), 1e-3)]
    if non_zero.size == 0:
        return []
    threshold = max(float(np.percentile(non_zero, 72)), max_height * 0.2, 0.75)
    mask = values >= threshold
    visited = np.zeros(mask.shape, dtype=bool)
    regions: list[dict[str, object]] = []
    for row in range(grid_size):
        for column in range(grid_size):
            if not mask[row, column] or visited[row, column]:
                continue
            stack = [(row, column)]
            visited[row, column] = True
            cells: list[tuple[int, int]] = []
            while stack:
                current_row, current_column = stack.pop()
                cells.append((current_row, current_column))
                for row_delta, column_delta in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    next_row = current_row + row_delta
                    next_column = current_column + column_delta
                    if 0 <= next_row < grid_size and 0 <= next_column < grid_size and mask[next_row, next_column] and not visited[next_row, next_column]:
                        visited[next_row, next_column] = True
                        stack.append((next_row, next_column))
            # Preserve small structures; only isolated single-pixel noise is removed.
            if len(cells) < 2:
                continue
            rows = [cell[0] for cell in cells]
            columns = [cell[1] for cell in cells]
            min_row, max_row = min(rows), max(rows)
            min_column, max_column = min(columns), max(columns)
            region_heights = np.asarray([values[row, column] for row, column in cells])
            spread = float(np.percentile(region_heights, 90) - np.percentile(region_heights, 10))
            roof_type = "flat" if spread <= max(0.8, max_height * 0.06) else "gabled"
            regions.append({
                "centerX": ((min_column + max_column) / 2 / max(grid_size - 1, 1) - 0.5),
                "centerZ": ((min_row + max_row) / 2 / max(grid_size - 1, 1) - 0.5),
                "width": (max_column - min_column + 1) / grid_size,
                "depth": (max_row - min_row + 1) / grid_size,
                "height": float(np.percentile(region_heights, 70)),
                "roofType": roof_type,
                "source": "height_threshold_fallback",
            })
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


def _write_benchmark_assets() -> dict[str, object]:
    benchmark_id = "gamus-urban-demo"
    image = _fixture_city()
    input_path = MEDIA_DIR / f"{benchmark_id}-input.png"
    reference_path = MEDIA_DIR / f"{benchmark_id}-reference.png"
    prediction_path = MEDIA_DIR / f"{benchmark_id}-prediction.png"
    error_path = MEDIA_DIR / f"{benchmark_id}-error.png"
    image.save(input_path, format="PNG")

    grayscale = ImageOps.grayscale(image).resize((256, 170), Image.Resampling.BILINEAR)
    ground_truth = np.asarray(grayscale, dtype=np.float32) / 255 * 42.7
    smoothed = np.asarray(grayscale.filter(ImageFilter.GaussianBlur(radius=2.2)), dtype=np.float32) / 255 * 42.7
    predicted = np.clip(smoothed * 0.92 + 0.65, 0, 42.7)
    error = np.abs(predicted - ground_truth)

    def save_map(values: np.ndarray, path: Path, scale: float) -> None:
        pixels = np.clip(values / max(scale, 1e-6) * 255, 0, 255).astype(np.uint8)
        Image.fromarray(pixels, mode="L").save(path, format="PNG")

    save_map(ground_truth, reference_path, 42.7)
    save_map(predicted, prediction_path, 42.7)
    save_map(error, error_path, max(float(error.max()), 1.0))
    metrics = compute_metrics(predicted, ground_truth)
    return {
        "id": benchmark_id,
        "name": "GAMUS urban validation example",
        "sourceDataset": "GAMUS",
        "split": "validation",
        "referenceStatus": "scaffold_fixture",
        "inputImageUrl": f"/media/{input_path.name}",
        "groundTruthUrl": f"/media/{reference_path.name}",
        "predictionUrl": f"/media/{prediction_path.name}",
        "errorMapUrl": f"/media/{error_path.name}",
        "metrics": {key: round(value, 4) for key, value in metrics.items()},
        "width": image.width,
        "height": image.height,
    }


def _is_geotiff(filename: str, content_type: str | None) -> bool:
    return filename.lower().endswith((".tif", ".tiff")) or content_type in {"image/tiff", "image/geotiff"}


def _normalize_raster_bands(bands: np.ndarray) -> np.ndarray:
    if bands.dtype == np.uint8:
        return bands
    normalized = np.empty_like(bands, dtype=np.uint8)
    for index, band in enumerate(bands):
        values = np.nan_to_num(band.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        if np.issubdtype(bands.dtype, np.integer):
            high = float(np.iinfo(bands.dtype).max)
            normalized[index] = np.clip(values / max(high, 1.0) * 255, 0, 255).astype(np.uint8)
            continue
        low, high = np.percentile(values, [2, 98])
        if high <= low:
            normalized[index] = np.zeros_like(values, dtype=np.uint8)
        else:
            normalized[index] = np.clip((values - low) / (high - low) * 255, 0, 255).astype(np.uint8)
    return normalized


def _read_geotiff(raw: bytes) -> tuple[Image.Image, dict[str, object]]:
    try:
        with MemoryFile(raw).open() as source:
            if source.count not in (3, 4):
                raise HTTPException(
                    status_code=415,
                    detail=f"This GeoTIFF has {source.count} bands. DepthWizard accepts RGB or RGBA GeoTIFFs only.",
                )
            bands = _normalize_raster_bands(source.read())
            valid_mask = source.dataset_mask() > 0
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
                "bands": source.count,
                "driver": source.driver,
                "validPixelFraction": float(np.mean(valid_mask)),
            }
            return image, metadata
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=400, detail="The uploaded GeoTIFF could not be read.") from error


def _read_image(raw: bytes, filename: str, content_type: str | None) -> tuple[Image.Image, dict[str, object] | None, str]:
    if _is_geotiff(filename, content_type):
        image, metadata = _read_geotiff(raw)
        return image, metadata, "geotiff"
    try:
        return Image.open(BytesIO(raw)).convert("RGB"), None, "image"
    except Exception as error:
        raise HTTPException(status_code=400, detail="The uploaded file is not a readable image.") from error


@app.post("/api/predict")
async def predict(
    file: UploadFile | None = File(default=None),
    example_id: str | None = Form(default=None),
) -> dict[str, object]:
    if file is None and example_id is None:
        raise HTTPException(status_code=400, detail="Upload an image or choose a GAMUS example.")

    prediction_token = uuid4().hex[:10]
    prediction_id = f"prediction-{prediction_token}"
    geospatial_metadata: dict[str, object] | None = None
    input_format = "example"
    is_fixture = False
    semantic_map_url: str | None = None
    semantic_data: list[int] | None = None
    semantic_grid_size: int | None = None
    semantic_source = "unavailable"
    if file is not None:
        raw = await file.read()
        source_name = file.filename or "uploaded-image"
        if not _is_geotiff(source_name, file.content_type) and file.content_type not in {"image/png", "image/jpeg"}:
            raise HTTPException(status_code=415, detail="Use a PNG, JPEG, or RGB GeoTIFF image.")
        image, geospatial_metadata, input_format = _read_image(raw, source_name, file.content_type)
        try:
            height_map = model_service.predict(image)
        except ModelUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        input_url, height_url, height_data, min_height, max_height = _write_model_prediction_assets(
            image,
            height_map,
            prediction_id,
        )
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
    building_regions = _building_regions(height_data, scene_grid_size, max_height)
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
        "semanticClasses": list(SEMANTIC_CLASSES),
        "semanticGridSize": semantic_grid_size,
        "semanticData": semantic_data,
        "semanticMapUrl": semantic_map_url,
        "semanticSource": semantic_source,
        "buildingRegions": building_regions,
        "buildingRegionSource": "height_threshold_fallback",
        "minHeight": min_height,
        "maxHeight": max_height,
        "resultType": "estimated_ndsm",
        "heightUnit": "meters",
        "sourceName": source_name,
        "isFixture": is_fixture,
        "inputFormat": input_format,
        "geospatial": geospatial_metadata,
    }
