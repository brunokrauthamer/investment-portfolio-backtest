"""Contract tests for the API health route."""

import unittest

from fastapi.testclient import TestClient

from backend.src.api.main import app


class HealthRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_route_reports_application_liveness(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_route_rejects_unsupported_method(self):
        response = self.client.post("/health")

        self.assertEqual(response.status_code, 405)


if __name__ == "__main__":
    unittest.main()
