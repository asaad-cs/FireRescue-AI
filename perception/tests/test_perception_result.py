"""Tests: PerceptionResult unified model — all new fields have working defaults."""
import unittest
from datetime import datetime, timezone

from backend.models.mission_state import HazardLevel
from perception.types import PerceptionResult


class TestPerceptionResultBackwardCompat(unittest.TestCase):
    """All callers that pass only the original 3 required fields must still work."""

    def test_minimal_construction(self):
        r = PerceptionResult(
            zone_id="1_1_1",
            hazard_level=HazardLevel.CLEAR,
            victim_probability=0.0,
        )
        self.assertEqual(r.zone_id, "1_1_1")
        self.assertEqual(r.hazard_level, HazardLevel.CLEAR)
        self.assertEqual(r.victim_probability, 0.0)

    def test_defaults_frame_id(self):
        r = PerceptionResult(zone_id="z", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        self.assertEqual(r.frame_id, "")

    def test_defaults_confidence_score(self):
        r = PerceptionResult(zone_id="z", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        self.assertEqual(r.confidence_score, 0.0)

    def test_defaults_timestamp_none(self):
        r = PerceptionResult(zone_id="z", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        self.assertIsNone(r.timestamp)

    def test_defaults_lists_empty(self):
        r = PerceptionResult(zone_id="z", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        self.assertEqual(r.detected_objects, [])
        self.assertEqual(r.victim_signals, [])
        self.assertEqual(r.hazard_signals, [])
        self.assertEqual(r.new_alerts, [])

    def test_defaults_detector_name(self):
        r = PerceptionResult(zone_id="z", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        self.assertEqual(r.detector_name, "unknown")

    def test_defaults_metadata_empty(self):
        r = PerceptionResult(zone_id="z", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        self.assertEqual(r.metadata, {})


class TestPerceptionResultNewFields(unittest.TestCase):

    def test_all_new_fields_settable(self):
        now = datetime.now(timezone.utc)
        r = PerceptionResult(
            zone_id="1_2_1",
            hazard_level=HazardLevel.HIGH,
            victim_probability=0.75,
            frame_id="frame-abc",
            confidence_score=0.88,
            timestamp=now,
            detected_objects=["obj"],
            victim_signals=["vs"],
            hazard_signals=["hs"],
            detector_name="ground_truth",
            new_alerts=["alert"],
            metadata={"key": "value"},
        )
        self.assertEqual(r.frame_id, "frame-abc")
        self.assertAlmostEqual(r.confidence_score, 0.88)
        self.assertEqual(r.timestamp, now)
        self.assertEqual(r.detected_objects, ["obj"])
        self.assertEqual(r.victim_signals, ["vs"])
        self.assertEqual(r.hazard_signals, ["hs"])
        self.assertEqual(r.detector_name, "ground_truth")

    def test_lists_are_independent_per_instance(self):
        r1 = PerceptionResult(zone_id="z1", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        r2 = PerceptionResult(zone_id="z2", hazard_level=HazardLevel.CLEAR, victim_probability=0.0)
        r1.detected_objects.append("a")
        self.assertEqual(r2.detected_objects, [],
                         "Default list must not be shared across instances")


if __name__ == "__main__":
    unittest.main()
