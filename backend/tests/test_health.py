import unittest

from fastapi.testclient import TestClient

from app.main import app


class HealthEndpointTests(unittest.TestCase):
    def test_health_reports_a_ready_backend(self) -> None:
        response = TestClient(app).get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "service": "depthwizard-api", "version": "0.1.0"},
        )


if __name__ == "__main__":
    unittest.main()
