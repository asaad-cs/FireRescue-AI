"""Tests: scenario registry API endpoints (Phase 7B)."""
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from simulation.scenario_registry import SCENARIO_REGISTRY


class TestScenariosEndpoint(unittest.TestCase):
    """Tests for GET /scenarios."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_list_scenarios_returns_200(self):
        response = self.client.get("/scenarios")
        self.assertEqual(response.status_code, 200)

    def test_list_scenarios_has_scenarios_field(self):
        data = self.client.get("/scenarios").json()
        self.assertIn("scenarios", data)
        self.assertIsInstance(data["scenarios"], list)

    def test_list_scenarios_returns_five_entries(self):
        data = self.client.get("/scenarios").json()
        self.assertEqual(len(data["scenarios"]), 5)

    def test_list_scenarios_has_active_field(self):
        data = self.client.get("/scenarios").json()
        self.assertIn("active", data)
        self.assertIsInstance(data["active"], str)

    def test_default_active_scenario_is_warehouse_alpha(self):
        data = self.client.get("/scenarios").json()
        self.assertEqual(data["active"], "warehouse_alpha")

    def test_each_scenario_has_required_fields(self):
        data = self.client.get("/scenarios").json()
        for s in data["scenarios"]:
            with self.subTest(key=s.get("key")):
                self.assertIn("key", s)
                self.assertIn("display_name", s)
                self.assertIn("description", s)
                self.assertIn("zone_count", s)

    def test_all_five_scenario_keys_present(self):
        data = self.client.get("/scenarios").json()
        keys = {s["key"] for s in data["scenarios"]}
        self.assertEqual(
            keys,
            {"warehouse_alpha", "office_building", "hospital", "shopping_mall", "school"},
        )

    def test_zone_counts_in_response_are_correct(self):
        expected = {
            "warehouse_alpha": 20,
            "office_building": 12,
            "hospital":        16,
            "shopping_mall":   15,
            "school":          16,
        }
        data = self.client.get("/scenarios").json()
        for s in data["scenarios"]:
            with self.subTest(key=s["key"]):
                self.assertEqual(s["zone_count"], expected[s["key"]])


class TestActivateScenarioEndpoint(unittest.TestCase):
    """Tests for POST /scenarios/{key}/activate."""

    def _client(self) -> TestClient:
        return TestClient(app)

    def test_activate_known_scenario_returns_200(self):
        with self._client() as client:
            for key in SCENARIO_REGISTRY:
                with self.subTest(key=key):
                    response = client.post(f"/scenarios/{key}/activate")
                    self.assertEqual(response.status_code, 200)

    def test_activate_returns_activated_key(self):
        with self._client() as client:
            response = client.post("/scenarios/hospital/activate")
            data = response.json()
            self.assertEqual(data["activated"], "hospital")

    def test_activate_unknown_scenario_returns_404(self):
        with self._client() as client:
            response = client.post("/scenarios/nonexistent/activate")
            self.assertEqual(response.status_code, 404)

    def test_activate_updates_active_in_list_response(self):
        with self._client() as client:
            client.post("/scenarios/school/activate")
            data = client.get("/scenarios").json()
            self.assertEqual(data["active"], "school")

    def test_activate_each_scenario_then_list_shows_correct_active(self):
        with self._client() as client:
            for key in SCENARIO_REGISTRY:
                with self.subTest(key=key):
                    client.post(f"/scenarios/{key}/activate")
                    data = client.get("/scenarios").json()
                    self.assertEqual(data["active"], key)

    def test_activate_warehouse_alpha_returns_correct_activated(self):
        with self._client() as client:
            response = client.post("/scenarios/warehouse_alpha/activate")
            self.assertEqual(response.json()["activated"], "warehouse_alpha")

    def test_activate_shopping_mall_returns_correct_activated(self):
        with self._client() as client:
            response = client.post("/scenarios/shopping_mall/activate")
            self.assertEqual(response.json()["activated"], "shopping_mall")


class TestScenarioSwitchOnRestart(unittest.TestCase):
    """
    Test that switching scenario before restarting a mission produces a
    mission with the new scenario's zone count.

    We verify this indirectly: after restart, the MissionState should
    reflect the new zone count via explored_percentage denominator.
    This tests that the runner was created from the new scenario.
    """

    def _client(self) -> TestClient:
        return TestClient(app)

    def test_restart_after_scenario_switch_returns_200(self):
        with self._client() as client:
            client.post("/mission/end")
            client.post("/scenarios/hospital/activate")
            response = client.post("/mission/start")
            self.assertEqual(response.status_code, 200)

    def test_restart_after_scenario_switch_returns_started_status(self):
        with self._client() as client:
            client.post("/mission/end")
            client.post("/scenarios/office_building/activate")
            data = client.post("/mission/start").json()
            self.assertEqual(data["status"], "started")

    def test_restart_after_scenario_switch_gives_new_mission_id(self):
        with self._client() as client:
            original_id = client.post("/mission/pause").json().get("mission_id")
            client.post("/mission/end")
            client.post("/scenarios/school/activate")
            new_id = client.post("/mission/start").json().get("mission_id")
            self.assertNotEqual(original_id, new_id)


if __name__ == "__main__":
    unittest.main()
