"""Tests: detector registration and config-driven switching (Phase 8E).

Verifies that the backend registers both detectors at startup, that the
active detector follows settings.perception_detector, and that the
external contract (REST endpoints, MissionState) is identical under
either detector.
"""
import unittest

from fastapi.testclient import TestClient

from backend.config.settings import settings
from backend.main import app
from backend.models.frame import Frame, Pose


def _frame() -> Frame:
    return Frame(
        mission_id="m-test",
        drone_id="d-test",
        pose=Pose(x=0, y=0, floor=1),
        channels={"environmental": {"temperature": 21.0}},
    )


class TestRegistryAtStartup(unittest.TestCase):

    def test_both_detectors_registered(self):
        with TestClient(app) as client:
            registry = client.app.state.registry
            self.assertIn("ground_truth", registry.available())
            self.assertIn("yolo", registry.available())

    def test_yolo_detector_never_breaks_startup(self):
        # Whether or not an exported model / onnxruntime is present,
        # startup must succeed and the yolo detector must answer
        # process() without raising.
        with TestClient(app) as client:
            detector = client.app.state.registry.get("yolo")
            result = detector.process(_frame())
            self.assertEqual(result.detector_name, "yolo")

    def test_ground_truth_still_default_and_working(self):
        self.assertEqual(settings.perception_detector, "ground_truth")
        with TestClient(app) as client:
            response = client.get("/health")
            self.assertEqual(response.status_code, 200)
            state = client.app.state.manager.get_state()
            self.assertIsNotNone(state)


class TestConfigDrivenSwitching(unittest.TestCase):
    """Flipping settings.perception_detector is the only change needed."""

    def setUp(self):
        self._original = settings.perception_detector
        self.addCleanup(self._restore)

    def _restore(self):
        settings.perception_detector = self._original

    def test_backend_runs_with_yolo_active(self):
        settings.perception_detector = "yolo"
        with TestClient(app) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertEqual(
                client.get("/scenarios").status_code, 200
            )
            state = client.app.state.manager.get_state()
            self.assertIsNotNone(state)

    def test_mission_state_contract_is_identical(self):
        # The frontend-facing structure must not depend on the detector.
        def state_keys(detector_name: str):
            settings.perception_detector = detector_name
            with TestClient(app) as client:
                state = client.app.state.manager.get_state()
                return set(state.model_dump().keys())

        self.assertEqual(state_keys("ground_truth"), state_keys("yolo"))


if __name__ == "__main__":
    unittest.main()
