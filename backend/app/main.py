from io import BytesIO
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from rasterio.io import MemoryFile


MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


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


def _write_prediction_assets(image: Image.Image, prediction_id: str) -> tuple[str, str, list[float]]:
    image = image.convert("RGB")
    input_path = MEDIA_DIR / f"{prediction_id}-input.png"
    height_path = MEDIA_DIR / f"{prediction_id}-height.png"
    image.save(input_path, format="PNG")

    grayscale = ImageOps.grayscale(image).resize((128, 128), Image.Resampling.BILINEAR)
    height_data = [round(pixel / 255 * 42.7, 3) for pixel in grayscale.get_flattened_data()]
    height_preview = ImageOps.autocontrast(grayscale).filter(ImageFilter.GaussianBlur(radius=1.2))
    height_preview.save(height_path, format="PNG")
    return f"/media/{input_path.name}", f"/media/{height_path.name}", height_data


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

    prediction_id = f"fixture-{uuid4().hex[:10]}"
    geospatial_metadata: dict[str, object] | None = None
    input_format = "example"
    if file is not None:
        raw = await file.read()
        source_name = file.filename or "uploaded-image"
        if not _is_geotiff(source_name, file.content_type) and file.content_type not in {"image/png", "image/jpeg"}:
            raise HTTPException(status_code=415, detail="Use a PNG, JPEG, or RGB GeoTIFF image.")
        image, geospatial_metadata, input_format = _read_image(raw, source_name, file.content_type)
    elif example_id == "gamus-urban-demo":
        image = _fixture_city()
        source_name = "gamus-urban-demo.png"
    else:
        raise HTTPException(status_code=404, detail="That GAMUS example does not exist.")

    input_url, height_url, height_data = _write_prediction_assets(image, prediction_id)
    return {
        "id": prediction_id,
        "status": "complete",
        "inputImageUrl": input_url,
        "heightMapUrl": height_url,
        "width": image.width,
        "height": image.height,
        "predictionWidth": 128,
        "predictionHeight": 128,
        "gridSize": 128,
        "heightData": height_data,
        "minHeight": 0,
        "maxHeight": 42.7,
        "resultType": "estimated_ndsm",
        "heightUnit": "meters",
        "sourceName": source_name,
        "isFixture": True,
        "inputFormat": input_format,
        "geospatial": geospatial_metadata,
    }
