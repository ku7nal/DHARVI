import unittest
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

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


if __name__ == "__main__":
    unittest.main()
