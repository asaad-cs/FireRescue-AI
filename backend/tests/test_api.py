"""Tests: REST API routes — informational and mission control endpoints."""
import unittest

from fastapi.testclient import TestClient

from backend.main import app


class TestAPIRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_root_returns_name(self):
        response = self.client.get("/")
        data = response.json()
        self.assertEqual(data["name"], "FireRescue AI")
        self.assertIn("version", data)
        self.assertEqual(data["status"], "running")

    def test_health_returns_200(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_health_returns_ok(self):
        response = self.client.get("/health")
        data = response.json()
        self.assertEqual(data["status"], "ok")

    def test_unknown_route_returns_404(self):
        response = self.client.get("/nonexistent")
        self.assertEqual(response.status_code, 404)


class TestMissionControlEndpoints(unittest.TestCase):
    """
    Mission control endpoint tests.

    Each test uses a fresh TestClient (fresh lifespan) so mission state does
    not bleed between tests. The lifespan auto-starts the mission (IDLE →
    ACTIVE), giving each test a known starting state.
    """

    def _client(self) -> TestClient:
        return TestClient(app)

    # ── pause ──────────────────────────────────────────────────────────────────

    def test_pause_active_mission_returns_200(self):
        with self._client() as client:
            # Mission is ACTIVE after lifespan startup
            response = client.post("/mission/pause")
            self.assertEqual(response.status_code, 200)

    def test_pause_response_has_status_field(self):
        with self._client() as client:
            data = client.post("/mission/pause").json()
            self.assertEqual(data["status"], "paused")

    def test_pause_response_has_mission_id(self):
        with self._client() as client:
            data = client.post("/mission/pause").json()
            self.assertIn("mission_id", data)
            self.assertIsInstance(data["mission_id"], str)
            self.assertGreater(len(data["mission_id"]), 0)

    def test_pause_paused_mission_returns_409(self):
        with self._client() as client:
            client.post("/mission/pause")  # ACTIVE → PAUSED
            response = client.post("/mission/pause")  # PAUSED → 409
            self.assertEqual(response.status_code, 409)

    # ── resume ─────────────────────────────────────────────────────────────────

    def test_resume_paused_mission_returns_200(self):
        with self._client() as client:
            client.post("/mission/pause")      # ACTIVE → PAUSED
            response = client.post("/mission/resume")  # PAUSED → ACTIVE
            self.assertEqual(response.status_code, 200)

    def test_resume_response_has_status_field(self):
        with self._client() as client:
            client.post("/mission/pause")
            data = client.post("/mission/resume").json()
            self.assertEqual(data["status"], "resumed")

    def test_resume_active_mission_returns_409(self):
        with self._client() as client:
            # Mission is ACTIVE; resume requires PAUSED
            response = client.post("/mission/resume")
            self.assertEqual(response.status_code, 409)

    # ── end ────────────────────────────────────────────────────────────────────

    def test_end_active_mission_returns_200(self):
        with self._client() as client:
            response = client.post("/mission/end")
            self.assertEqual(response.status_code, 200)

    def test_end_response_has_status_field(self):
        with self._client() as client:
            data = client.post("/mission/end").json()
            self.assertEqual(data["status"], "ended")

    def test_end_paused_mission_returns_200(self):
        with self._client() as client:
            client.post("/mission/pause")
            response = client.post("/mission/end")
            self.assertEqual(response.status_code, 200)

    # ── start ──────────────────────────────────────────────────────────────────

    def test_start_active_mission_returns_409(self):
        with self._client() as client:
            # Mission is already ACTIVE after lifespan startup
            response = client.post("/mission/start")
            self.assertEqual(response.status_code, 409)

    def test_start_paused_mission_returns_200(self):
        with self._client() as client:
            client.post("/mission/pause")      # ACTIVE → PAUSED
            response = client.post("/mission/start")  # PAUSED → ACTIVE
            self.assertEqual(response.status_code, 200)

    def test_start_response_has_status_field(self):
        with self._client() as client:
            client.post("/mission/pause")
            data = client.post("/mission/start").json()
            self.assertEqual(data["status"], "started")

    # ── 409 response body ─────────────────────────────────────────────────────

    def test_409_response_contains_detail(self):
        with self._client() as client:
            response = client.post("/mission/start")  # Already ACTIVE
            self.assertEqual(response.status_code, 409)
            data = response.json()
            self.assertIn("detail", data)
            self.assertIsInstance(data["detail"], str)

    # ── restart from ENDED ────────────────────────────────────────────────────

    def test_start_ended_mission_restarts_and_returns_200(self):
        with self._client() as client:
            client.post("/mission/end")        # ACTIVE → ENDED
            response = client.post("/mission/start")  # ENDED → new ACTIVE
            self.assertEqual(response.status_code, 200)

    def test_restarted_mission_has_new_mission_id(self):
        with self._client() as client:
            original_id = client.post("/mission/pause").json().get("mission_id")
            client.post("/mission/end")
            restarted_id = client.post("/mission/start").json().get("mission_id")
            self.assertIsInstance(restarted_id, str)
            self.assertGreater(len(restarted_id), 0)
            self.assertNotEqual(original_id, restarted_id)

    def test_restarted_mission_response_has_status_started(self):
        with self._client() as client:
            client.post("/mission/end")
            data = client.post("/mission/start").json()
            self.assertEqual(data["status"], "started")


if __name__ == "__main__":
    unittest.main()
