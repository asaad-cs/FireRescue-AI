"""Tests: Error handling — detector failures must not crash the mission."""
import unittest

from backend.models.frame import Frame, Pose
from backend.models.mission_state import HazardLevel
from backend.pipeline.enricher import Enricher
from perception.base.detector import AbstractDetector
from perception.engine import PerceptionEngine, ZoneHistory
from perception.registry.registry import DetectorRegistry
from perception.results.detection import DetectionResult


class _BrokenDetector(AbstractDetector):
    """Always raises an exception — simulates a detector crash."""

    @property
    def detector_name(self) -> str:
        return "broken"

    def initialize(self) -> None:
        pass

    def process(self, frame: Frame) -> DetectionResult:
        raise RuntimeError("Simulated detector crash")

    def shutdown(self) -> None:
        pass


def _make_engine_with_broken_detector() -> PerceptionEngine:
    broken = _BrokenDetector()
    broken.initialize()
    registry = DetectorRegistry()
    registry.register("broken", broken)
    return PerceptionEngine(registry=registry, active_detector="broken")


def _enriched_frame() -> object:
    frame = Frame(
        mission_id="m1",
        drone_id="d1",
        pose=Pose(x=1, y=2, floor=1),
        channels={},
    )
    return Enricher().enrich(frame)


class TestDetectorFailureHandling(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine_with_broken_detector()
        self.enriched = _enriched_frame()
        self.history = ZoneHistory(zone_id="1_2_1")

    def test_broken_detector_does_not_raise(self):
        """Engine must catch detector exceptions and not propagate them."""
        try:
            result = self.engine.process(self.enriched, self.history)
        except Exception as exc:
            self.fail(f"Engine raised an exception on detector failure: {exc}")

    def test_broken_detector_returns_result(self):
        result = self.engine.process(self.enriched, self.history)
        self.assertIsNotNone(result)

    def test_broken_detector_result_is_unobserved(self):
        result = self.engine.process(self.enriched, self.history)
        self.assertEqual(result.hazard_level, HazardLevel.UNOBSERVED)

    def test_broken_detector_victim_probability_zero(self):
        result = self.engine.process(self.enriched, self.history)
        self.assertEqual(result.victim_probability, 0.0)

    def test_broken_detector_no_alerts(self):
        result = self.engine.process(self.enriched, self.history)
        self.assertEqual(result.new_alerts, [])

    def test_zone_id_preserved_on_failure(self):
        result = self.engine.process(self.enriched, self.history)
        self.assertEqual(result.zone_id, self.enriched.zone_id)


class TestUnregisteredDetectorHandling(unittest.TestCase):

    def test_unregistered_detector_does_not_raise(self):
        registry = DetectorRegistry()   # empty — "ground_truth" not registered
        engine = PerceptionEngine(registry=registry, active_detector="ground_truth")
        enriched = _enriched_frame()
        history = ZoneHistory(zone_id="1_2_1")
        try:
            result = engine.process(enriched, history)
        except Exception as exc:
            self.fail(f"Engine raised exception for unregistered detector: {exc}")

    def test_unregistered_detector_returns_unobserved(self):
        registry = DetectorRegistry()
        engine = PerceptionEngine(registry=registry, active_detector="nonexistent")
        enriched = _enriched_frame()
        history = ZoneHistory(zone_id="1_2_1")
        result = engine.process(enriched, history)
        self.assertEqual(result.hazard_level, HazardLevel.UNOBSERVED)


if __name__ == "__main__":
    unittest.main()
