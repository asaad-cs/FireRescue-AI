"""Tests: PerceptionEngine integration — processes enriched frames with real modules."""
import unittest

from backend.models.frame import Frame, Pose
from backend.models.mission_state import HazardLevel
from backend.pipeline.enricher import Enricher, EnrichedFrame
from perception.detectors.ground_truth import GroundTruthDetector
from perception.engine import PerceptionEngine, ZoneHistory
from perception.registry.registry import DetectorRegistry


def _make_engine() -> PerceptionEngine:
    """Build an engine with a GroundTruthDetector using empty maps.

    Empty maps mean the detector falls back to sensor analysis via HazardClassifier,
    so all sensor-based test assertions continue to hold.
    """
    detector = GroundTruthDetector()
    detector.initialize()
    registry = DetectorRegistry()
    registry.register("ground_truth", detector)
    return PerceptionEngine(registry=registry, active_detector="ground_truth")


def _enriched(
    mission_id: str = "m1",
    channels: dict = None,
) -> EnrichedFrame:
    frame = Frame(
        mission_id=mission_id,
        drone_id="d1",
        pose=Pose(x=3, y=4, floor=2),
        channels=channels if channels is not None else {},
    )
    return Enricher().enrich(frame)


class TestPerceptionEngineInit(unittest.TestCase):

    def test_engine_creates(self):
        engine = _make_engine()
        self.assertIsNotNone(engine)


class TestPerceptionEngineProcess(unittest.TestCase):

    def setUp(self):
        self.engine = _make_engine()

    def test_returns_result(self):
        enriched = _enriched()
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertIsNotNone(result)

    def test_zone_id_matches(self):
        enriched = _enriched()
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertEqual(result.zone_id, enriched.zone_id)

    def test_empty_channel_returns_clear(self):
        # No environmental channel → CLEAR (safe default)
        enriched = _enriched(channels={})
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertEqual(result.hazard_level, HazardLevel.CLEAR)

    def test_empty_channel_returns_zero_victim_probability(self):
        enriched = _enriched(channels={})
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertEqual(result.victim_probability, 0.0)

    def test_baseline_env_returns_clear(self):
        env = {"temperature": 22.0, "co_level": 5.0, "smoke_density": 0.03}
        enriched = _enriched(channels={"environmental": env})
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertEqual(result.hazard_level, HazardLevel.CLEAR)

    def test_critical_env_returns_critical(self):
        env = {"temperature": 145.0, "co_level": 680.0, "smoke_density": 0.92}
        enriched = _enriched(channels={"environmental": env})
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertEqual(result.hazard_level, HazardLevel.CRITICAL)

    def test_critical_zone_generates_alerts(self):
        env = {"temperature": 145.0, "co_level": 680.0, "smoke_density": 0.92}
        enriched = _enriched(channels={"environmental": env})
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertGreater(len(result.new_alerts), 0)

    def test_no_alerts_for_baseline(self):
        env = {"temperature": 22.0, "co_level": 5.0, "smoke_density": 0.03}
        enriched = _enriched(channels={"environmental": env})
        history = ZoneHistory(zone_id=enriched.zone_id)
        result = self.engine.process(enriched, history)
        self.assertEqual(result.new_alerts, [])

    def test_alert_not_duplicated_on_second_call(self):
        env = {"temperature": 145.0, "co_level": 680.0, "smoke_density": 0.92}
        history = ZoneHistory(zone_id="3_4_2")
        # First call generates alerts
        enriched = _enriched(channels={"environmental": env})
        result1 = self.engine.process(enriched, history)
        first_count = len(result1.new_alerts)
        # Second call — same zone, same readings, same history
        result2 = self.engine.process(enriched, history)
        self.assertEqual(len(result2.new_alerts), 0,
                         "Second call should not duplicate alerts")


class TestZoneHistory(unittest.TestCase):

    def test_record_appends(self):
        h = ZoneHistory(zone_id="z1")
        h.record(HazardLevel.LOW, 0.3)
        self.assertEqual(len(h.hazard_levels), 1)
        self.assertEqual(h.victim_probabilities[0], 0.3)

    def test_last_observed_at_set_after_record(self):
        h = ZoneHistory(zone_id="z1")
        self.assertIsNone(h.last_observed_at)
        h.record(HazardLevel.CLEAR, 0.0)
        self.assertIsNotNone(h.last_observed_at)

    def test_active_alert_keys_starts_empty(self):
        h = ZoneHistory(zone_id="z1")
        self.assertEqual(len(h.active_alert_keys), 0)


if __name__ == "__main__":
    unittest.main()
