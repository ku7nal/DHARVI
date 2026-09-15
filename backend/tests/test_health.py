import unittest
from io import BytesIO
from tempfile import NamedTemporaryFile

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from app import main as main_module
from app.main import app
from app.model_service import DepthAnythingModelService, ModelUnavailableError


class HealthEndpointTests(unittest.TestCase):
    def test_health_reports_a_ready_backend(self) -> None:
        response = TestClient(app).get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "depthwizard-api", "version": "0.1.0"},
        )

    def test_1024_tile_starts_cover_both_image_edges_with_overlap(self) -> None:
        service = DepthAnythingModelService(main_module.CHECKPOINT_PATH)
        starts = service._tile_starts(1024)
        covered = np.zeros(1024, dtype=bool)
        for start in starts:
            covered[start:min(start + service.input_size, 1024)] = True

        self.assertEqual(starts[0], 0)
        self.assertEqual(starts[-1], 1024 - service.input_size)
        self.assertTrue(np.all(covered))


class FixturePredictionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_model_service = main_module.model_service
        main_module.model_service = FakeModelService()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        main_module.model_service = self.original_model_service

    def test_uploaded_png_returns_a_model_prediction_with_media_assets(self) -> None:
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
        self.assertFalse(result["isFixture"])
        self.assertEqual(result["sourceName"], "scene.png")
        self.assertEqual(result["heightReference"], "relative")
        self.assertEqual(result["resultType"], "estimated_ndsm")
        self.assertIsNone(result["dsmUrl"])
        self.assertEqual(result["calibration"]["status"], "not_applicable")
        self.assertEqual(result["gridSize"], 256)
        self.assertEqual(len(result["heightData"]), 256 * 256)
        self.assertEqual(result["semanticSource"], "unavailable")
        self.assertIsNone(result["semanticData"])
        self.assertEqual({item["id"] for item in result["semanticClasses"]}, set(range(7)))
        self.assertEqual(result["predictionWidth"], 518)
        self.assertEqual(result["predictionHeight"], 518)
        self.assertEqual(result["minHeight"], 12.0)
        self.assertEqual(result["maxHeight"], 12.0)
        self.assertEqual(self.client.get(result["inputImageUrl"]).status_code, 200)
        self.assertEqual(self.client.get(result["heightMapUrl"]).status_code, 200)

    def test_height_fallback_buildings_use_the_building_class(self) -> None:
        from app.main import _building_regions

        heights = np.zeros((8, 8), dtype=np.float32)
        heights[2:6, 2:6] = 12

        regions = _building_regions(heights.ravel(), 8, 12)

        self.assertEqual(len(regions), 1)
        self.assertEqual(regions[0]["source"], "height_threshold_fallback")

    def test_1024_input_preserves_full_image_dimensions_and_scene_grid(self) -> None:
        image_bytes = BytesIO()
        Image.new("RGB", (1024, 1024), "#8899aa").save(image_bytes, format="PNG")

        response = self.client.post(
            "/api/predict",
            files={"file": ("full-scene.png", image_bytes.getvalue(), "image/png")},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual((result["width"], result["height"]), (1024, 1024))
        self.assertEqual((result["predictionWidth"], result["predictionHeight"]), (518, 518))
        self.assertEqual(len(result["heightData"]), 256 * 256)

    def test_gamus_example_returns_a_fixture_prediction(self) -> None:
        response = self.client.post(
            "/api/predict",
            data={"example_id": "gamus-urban-demo"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sourceName"], "gamus-urban-demo.png")
        self.assertTrue(response.json()["isFixture"])

    def test_gamus_fixture_returns_aligned_seven_class_semantics(self) -> None:
        response = self.client.post(
            "/api/predict",
            data={"example_id": "gamus-urban-demo"},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["semanticSource"], "fixture")
        self.assertEqual(result["semanticGridSize"], result["gridSize"])
        self.assertEqual(len(result["semanticData"]), result["gridSize"] ** 2)
        self.assertEqual(set(result["semanticData"]), set(range(7)))
        self.assertEqual(result["buildingRegionSource"], "semantic_head")
        self.assertTrue(result["buildingRegions"])
        self.assertTrue(all(len(region["footprint"]) >= 3 for region in result["buildingRegions"]))
        self.assertTrue(all("groundHeight" in region for region in result["buildingRegions"]))
        self.assertTrue(all(region["wallHeight"] >= 0 for region in result["buildingRegions"]))
        def signed_area(points: list[list[float]]) -> float:
            return sum(
                points[index][0] * points[(index + 1) % len(points)][1]
                - points[(index + 1) % len(points)][0] * points[index][1]
                for index in range(len(points))
            ) / 2
        self.assertTrue(all(abs(signed_area(region["footprint"])) > 0 for region in result["buildingRegions"]))
        self.assertTrue(all(region["roofType"] in {"flat", "gabled", "hipped", "dome"} for region in result["buildingRegions"]))
        self.assertTrue(all("wallHeight" in region and "roofRise" in region for region in result["buildingRegions"]))
        semantic_response = self.client.get(result["semanticMapUrl"])
        height_response = self.client.get(result["heightMapUrl"])
        input_response = self.client.get(result["inputImageUrl"])
        self.assertEqual(semantic_response.headers["content-type"], "image/png")
        self.assertEqual(Image.open(BytesIO(semantic_response.content)).size, (128, 128))
        self.assertEqual(Image.open(BytesIO(height_response.content)).size, (128, 128))
        self.assertEqual(Image.open(BytesIO(input_response.content)).size, (768, 512))

        semantic_grid = np.asarray(result["semanticData"], dtype=np.uint8).reshape((128, 128))
        input_grid = np.asarray(
            Image.open(BytesIO(input_response.content)).convert("RGB").resize((128, 128), Image.Resampling.BILINEAR),
            dtype=np.uint8,
        )
        expected_height_grid = np.asarray(
            Image.open(BytesIO(input_response.content)).convert("L").resize((128, 128), Image.Resampling.BILINEAR),
            dtype=np.float32,
        ) / 255 * 42.7
        # These independent coordinates are anchored to the fixture image regions.
        self.assertEqual(int(semantic_grid[5, 10]), 4)    # water
        self.assertEqual(int(semantic_grid[60, 10]), 5)   # horizontal road
        self.assertEqual(int(semantic_grid[25, 20]), 3)   # building
        self.assertEqual(int(semantic_grid[100, 10]), 2)  # low vegetation
        self.assertEqual(int(semantic_grid[72, 3]), 6)    # tree
        self.assertEqual(int(semantic_grid[120, 120]), 1) # ground
        self.assertTrue(np.array_equal(input_grid[5, 10], [114, 174, 232]))
        self.assertAlmostEqual(result["heightData"][5 * 128 + 10], float(expected_height_grid[5, 10]), places=2)

    def test_trained_semantics_are_returned_as_an_aligned_reduced_grid(self) -> None:
        main_module.model_service = TrainedSemanticModelService()
        image_bytes = BytesIO()
        Image.new("RGB", (32, 24), "#8899aa").save(image_bytes, format="PNG")

        response = self.client.post(
            "/api/predict",
            files={"file": ("scene.png", image_bytes.getvalue(), "image/png")},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["semanticSource"], "trained")
        self.assertEqual(result["semanticGridSize"], result["gridSize"])
        self.assertEqual(len(result["semanticData"]), result["gridSize"] ** 2)
        self.assertEqual({item["id"] for item in result["semanticClasses"]}, set(range(7)))
        self.assertTrue(set(result["semanticData"]).issubset(set(range(7))))
        self.assertEqual(Image.open(BytesIO(self.client.get(result["semanticMapUrl"]).content)).size, (256, 256))
        self.assertEqual(result["boundarySource"], "trained")
        self.assertEqual(result["boundaryGridSize"], 256)
        self.assertEqual(len(result["boundaryData"]), 256 * 256)
        self.assertGreater(result["boundaryConfidence"], 0.9)
        self.assertEqual(Image.open(BytesIO(self.client.get(result["boundaryMapUrl"]).content)).size, (10, 8))

    def test_semantic_logits_are_resized_before_scene_labels_are_selected(self) -> None:
        from app.main import _prepare_semantic_labels

        logits = np.full((7, 2, 2), -10.0, dtype=np.float32)
        logits[1] = 0.0
        logits[3, 0, 0] = 10.0

        full_labels, scene_labels = _prepare_semantic_labels(logits, 8)

        self.assertEqual(full_labels.shape, (2, 2))
        self.assertEqual(scene_labels.shape, (8, 8))
        self.assertEqual(int(scene_labels[3, 3]), 1)
        self.assertTrue(np.all((scene_labels >= 0) & (scene_labels < 7)))

    def test_model_loading_failure_returns_a_clear_service_error(self) -> None:
        main_module.model_service = FailingModelService()
        image_bytes = BytesIO()
        Image.new("RGB", (32, 24), "#8899aa").save(image_bytes, format="PNG")

        response = self.client.post(
            "/api/predict",
            files={"file": ("scene.png", image_bytes.getvalue(), "image/png")},
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("astra.pth", response.json()["detail"])

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

    def test_oversized_upload_is_rejected_before_model_inference(self) -> None:
        original_limit = main_module.MAX_UPLOAD_BYTES
        main_module.MAX_UPLOAD_BYTES = 4
        try:
            response = self.client.post(
                "/api/predict",
                files={"file": ("scene.png", b"12345", "image/png")},
            )
        finally:
            main_module.MAX_UPLOAD_BYTES = original_limit

        self.assertEqual(response.status_code, 413)
        self.assertIn("too large", response.json()["detail"])

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
        self.assertEqual(result["resultType"], "estimated_ndsm")
        self.assertEqual(result["calibration"]["status"], "insufficient_ground_evidence")

    def test_calibrated_geotiff_returns_metric_dsm_download(self) -> None:
        main_module.model_service = CalibratedModelService()
        with NamedTemporaryFile(suffix=".tif") as raster_file:
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
                data={"ground_elevation": "120.5"},
                files={"file": ("CITY.TIF", raster_file.read(), "image/tiff")},
            )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["resultType"], "metric_dsm")
        self.assertEqual(result["heightReference"], "absolute")
        self.assertEqual(result["calibration"]["status"], "calibrated")
        dsm_response = self.client.get(result["dsmUrl"])
        self.assertEqual(dsm_response.status_code, 200)
        with MemoryFile(dsm_response.content).open() as dataset:
            self.assertEqual(dataset.crs.to_string(), "EPSG:4326")
            self.assertEqual(dataset.transform, transform)
            self.assertEqual(dataset.dtypes[0], "float32")
            np.testing.assert_allclose(dataset.read(1), 120.5, atol=1e-5)

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
        benchmarks = response.json()["benchmarks"]
        self.assertEqual([item["landscapeGroup"] for item in benchmarks], ["urban", "sparse", "hilly", "forested"])
        for benchmark in benchmarks:
            self.assertEqual(benchmark["sourceDataset"], "GAMUS" if benchmark["landscapeGroup"] == "urban" else "Synthetic stress fixture")
            self.assertEqual(benchmark["referenceStatus"], "scaffold_fixture")
            self.assertEqual(benchmark["heightReference"], "relative")
            for asset_key in ("inputImageUrl", "groundTruthUrl", "predictionUrl", "errorMapUrl"):
                self.assertEqual(self.client.get(benchmark[asset_key]).status_code, 200)
            expected_metrics = {"rmse", "mae", "correlation", "semanticMiou", "buildingIoU", "buildingBoundaryF1"}
            self.assertEqual(set(benchmark["metrics"]), expected_metrics)
            self.assertEqual(set(benchmark["comparison"]), {"baseline", "improved"})
            self.assertEqual(set(benchmark["comparison"]["improved"]), expected_metrics)

    def test_metrics_are_zero_for_identical_arrays_and_safe_for_flat_arrays(self) -> None:
        from app.main import compute_metrics

        metrics = compute_metrics(np.ones((2, 2)), np.ones((2, 2)))

        self.assertEqual(metrics, {"rmse": 0.0, "mae": 0.0, "correlation": 0.0})

    def test_semantic_metrics_are_perfect_for_identical_labels(self) -> None:
        from app.main import _semantic_metrics

        labels = np.array([[0, 1, 3], [3, 5, 6]])

        self.assertEqual(_semantic_metrics(labels, labels), {"semanticMiou": 1.0, "buildingIoU": 1.0, "buildingBoundaryF1": 1.0})


class FakeModelService:
    def predict(self, image: Image.Image) -> np.ndarray:
        return np.full((518, 518), 12.0, dtype=np.float32)


class FailingModelService:
    def predict(self, image: Image.Image) -> np.ndarray:
        raise ModelUnavailableError("The fine-tuned model could not be loaded from astra.pth.")


class TrainedSemanticModelService:
    def predict_result(self, image: Image.Image) -> dict[str, np.ndarray]:
        classes = np.indices((8, 10)).sum(axis=0) % 7
        semantic = np.full((7, 8, 10), -10.0, dtype=np.float32)
        for class_id in range(7):
            semantic[class_id][classes == class_id] = 10.0
        boundary = np.zeros((8, 10), dtype=np.float32)
        boundary[0, :] = 1.0
        return {
            "height": np.full((8, 10), 12.0, dtype=np.float32),
            "semantic": semantic,
            "boundary": boundary,
        }


class CalibratedModelService:
    def predict_result(self, image: Image.Image) -> dict[str, np.ndarray]:
        height, width = image.height, image.width
        semantic = np.full((7, height, width), -10.0, dtype=np.float32)
        semantic[1] = 10.0
        return {"height": np.full((height, width), 4.0, dtype=np.float32), "semantic": semantic}


if __name__ == "__main__":
    unittest.main()
