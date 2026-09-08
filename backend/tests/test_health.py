import unittest
from io import BytesIO
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin

from app.main import app


class HealthEndpointTests(unittest.TestCase):
    def test_health_reports_a_ready_backend(self) -> None:
        response = TestClient(app).get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "depthwizard-api", "version": "0.1.0"},
        )


class FixturePredictionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_uploaded_png_returns_a_fixture_prediction_with_media_assets(self) -> None:
        image_bytes = BytesIO()
        Image.new("RGB", (32, 24), "#8899aa").save(image_bytes, format="PNG")

        response = self.client.post(
            "/api/predict",
            files={"file": ("scene.png", image_bytes.getvalue(), "image/png")},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["resultType"], "estimated_ndsm")
        self.assertTrue(result["isFixture"])
        self.assertEqual(result["sourceName"], "scene.png")
        self.assertEqual(result["gridSize"], 128)
        self.assertEqual(len(result["heightData"]), 128 * 128)
        self.assertEqual(self.client.get(result["inputImageUrl"]).status_code, 200)
        self.assertEqual(self.client.get(result["heightMapUrl"]).status_code, 200)

    def test_gamus_example_returns_a_fixture_prediction(self) -> None:
        response = self.client.post(
            "/api/predict",
            data={"example_id": "gamus-urban-demo"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sourceName"], "gamus-urban-demo.png")

    def test_prediction_requires_an_upload_or_example(self) -> None:
        response = self.client.post("/api/predict")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Upload an image", response.json()["detail"])

    def test_unsupported_file_type_is_rejected(self) -> None:
        response = self.client.post(
            "/api/predict",
            files={"file": ("scene.txt", b"not an image", "text/plain")},
        )

        self.assertEqual(response.status_code, 415)

    def test_rgb_geotiff_preserves_geospatial_metadata(self) -> None:
        with NamedTemporaryFile(suffix=".TIF") as raster_file:
            transform = from_origin(72.8, 19.1, 0.0001, 0.0001)
            with rasterio.open(
                raster_file.name,
                "w",
                driver="GTiff",
                width=8,
                height=6,
                count=3,
                dtype="uint8",
                crs="EPSG:4326",
                transform=transform,
            ) as dataset:
                dataset.write(np.full((3, 6, 8), 120, dtype=np.uint8))
            raster_file.seek(0)
            response = self.client.post(
                "/api/predict",
                files={"file": ("CITY.TIF", raster_file.read(), "application/octet-stream")},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["inputFormat"], "geotiff")
        self.assertEqual(result["geospatial"]["crs"], "EPSG:4326")
        self.assertEqual(result["geospatial"]["bands"], 3)
        self.assertEqual(result["geospatial"]["resolution"], [0.0001, 0.0001])

    def test_rgba_geotiff_is_accepted(self) -> None:
        with NamedTemporaryFile(suffix=".tiff") as raster_file:
            with rasterio.open(raster_file.name, "w", driver="GTiff", width=4, height=4, count=4, dtype="uint8") as dataset:
                dataset.write(np.full((4, 4, 4), 180, dtype=np.uint8))
            raster_file.seek(0)
            response = self.client.post(
                "/api/predict",
                files={"file": ("rgba.tiff", raster_file.read(), "image/tiff")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["geospatial"]["bands"], 4)

    def test_multispectral_geotiff_is_rejected(self) -> None:
        with NamedTemporaryFile(suffix=".tif") as raster_file:
            with rasterio.open(raster_file.name, "w", driver="GTiff", width=4, height=4, count=5, dtype="uint8") as dataset:
                dataset.write(np.full((5, 4, 4), 180, dtype=np.uint8))
            raster_file.seek(0)
            response = self.client.post(
                "/api/predict",
                files={"file": ("multispectral.tif", raster_file.read(), "image/tiff")},
            )

        self.assertEqual(response.status_code, 415)
        self.assertIn("RGB or RGBA", response.json()["detail"])


class BenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_benchmarks_return_reference_prediction_error_assets_and_metrics(self) -> None:
        response = self.client.get("/api/benchmarks")

        self.assertEqual(response.status_code, 200)
        benchmark = response.json()["benchmarks"][0]
        self.assertEqual(benchmark["sourceDataset"], "GAMUS")
        self.assertEqual(benchmark["referenceStatus"], "scaffold_fixture")
        for asset_key in ("inputImageUrl", "groundTruthUrl", "predictionUrl", "errorMapUrl"):
            self.assertEqual(self.client.get(benchmark[asset_key]).status_code, 200)
        self.assertEqual(set(benchmark["metrics"]), {"rmse", "mae", "correlation"})

    def test_metrics_are_zero_for_identical_arrays_and_safe_for_flat_arrays(self) -> None:
        from app.main import compute_metrics

        metrics = compute_metrics(np.ones((2, 2)), np.ones((2, 2)))

        self.assertEqual(metrics, {"rmse": 0.0, "mae": 0.0, "correlation": 0.0})


if __name__ == "__main__":
    unittest.main()
