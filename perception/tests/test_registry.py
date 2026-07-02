"""Tests: DetectorRegistry — register, retrieve, and switch detectors by name."""
import unittest

from backend.models.mission_state import HazardLevel
from perception.detectors.ground_truth import GroundTruthDetector
from perception.registry.registry import DetectorRegistry


def _make_gt(name_suffix: str = "") -> GroundTruthDetector:
    d = GroundTruthDetector()
    d.initialize()
    return d


class TestDetectorRegistryBasic(unittest.TestCase):

    def setUp(self):
        self.registry = DetectorRegistry()

    def test_register_and_get(self):
        d = _make_gt()
        self.registry.register("ground_truth", d)
        self.assertIs(self.registry.get("ground_truth"), d)

    def test_available_lists_registered(self):
        self.registry.register("ground_truth", _make_gt())
        self.assertIn("ground_truth", self.registry.available())

    def test_available_empty_initially(self):
        self.assertEqual(self.registry.available(), [])

    def test_get_unregistered_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.registry.get("yolo")

    def test_key_error_message_lists_planned(self):
        try:
            self.registry.get("yolo")
        except KeyError as exc:
            self.assertIn("yolo", str(exc))
            self.assertIn("Planned", str(exc))  # error message mentions planned detectors


class TestDetectorRegistryMultiple(unittest.TestCase):

    def setUp(self):
        self.registry = DetectorRegistry()
        self.d1 = GroundTruthDetector(hazard_map={"1_1_1": HazardLevel.CRITICAL})
        self.d1.initialize()
        self.d2 = GroundTruthDetector(hazard_map={"2_2_1": HazardLevel.HIGH})
        self.d2.initialize()
        self.registry.register("detector_a", self.d1)
        self.registry.register("detector_b", self.d2)

    def test_two_detectors_available(self):
        self.assertEqual(len(self.registry.available()), 2)

    def test_get_first_detector(self):
        self.assertIs(self.registry.get("detector_a"), self.d1)

    def test_get_second_detector(self):
        self.assertIs(self.registry.get("detector_b"), self.d2)

    def test_switch_between_detectors(self):
        # Both accessible by name — simulates switching the active_detector setting
        a = self.registry.get("detector_a")
        b = self.registry.get("detector_b")
        self.assertIsNot(a, b)


class TestDetectorRegistryPlanned(unittest.TestCase):

    def test_planned_includes_known_future_detectors(self):
        r = DetectorRegistry()
        planned = r.planned()
        self.assertIn("yolo", planned)
        self.assertIn("rt_detr", planned)
        self.assertIn("thermal", planned)
        self.assertIn("grounding_dino", planned)
        self.assertIn("multimodal", planned)

    def test_planned_not_in_available(self):
        r = DetectorRegistry()
        for name in r.planned():
            self.assertNotIn(name, r.available())


if __name__ == "__main__":
    unittest.main()
