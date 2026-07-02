"""Tests: GroundTruthDetector — the only implemented detector in Phase 5."""
import unittest
from datetime import datetime

from backend.models.frame import Frame, Pose
from backend.models.mission_state import HazardLevel
from perception.detectors.ground_truth import GroundTruthDetector
from perception.results.detection import DetectionResult, HazardSignal, VictimSignal


def _frame(
    x: int = 1,
    y: int = 1,
    floor: int = 1,
    channels: dict = None,
    metadata: dict = None,
) -> Frame:
    return Frame(
        mission_id="test-mission",
        drone_id="test-drone",
        pose=Pose(x=x, y=y, floor=floor),
        channels=channels or {},
        metadata=metadata or {},
    )


class TestGroundTruthDetectorLifecycle(unittest.TestCase):

    def test_detector_name(self):
        d = GroundTruthDetector()
        self.assertEqual(d.detector_name, "ground_truth")

    def test_initialize_no_error(self):
        d = GroundTruthDetector()
        d.initialize()   # must not raise

    def test_shutdown_no_error(self):
        d = GroundTruthDetector()
        d.initialize()
        d.shutdown()     # must not raise

    def test_initialized_flag_set(self):
        d = GroundTruthDetector()
        self.assertFalse(d._initialized)
        d.initialize()
        self.assertTrue(d._initialized)

    def test_shutdown_clears_flag(self):
        d = GroundTruthDetector()
        d.initialize()
        d.shutdown()
        self.assertFalse(d._initialized)


class TestGroundTruthDetectorProcess(unittest.TestCase):

    def setUp(self):
        self.detector = GroundTruthDetector(
            hazard_map={"1_1_1": HazardLevel.CRITICAL, "2_2_1": HazardLevel.CLEAR},
            victim_map={"1_1_1": 0.85},
        )
        self.detector.initialize()

    def test_returns_detection_result(self):
        frame = _frame()
        result = self.detector.process(frame)
        self.assertIsInstance(result, DetectionResult)

    def test_result_has_frame_id(self):
        frame = _frame()
        result = self.detector.process(frame)
        self.assertEqual(result.frame_id, frame.frame_id)

    def test_result_has_zone_id(self):
        frame = _frame(x=1, y=1, floor=1)
        result = self.detector.process(frame)
        self.assertEqual(result.zone_id, "1_1_1")

    def test_result_has_detector_name(self):
        frame = _frame()
        result = self.detector.process(frame)
        self.assertEqual(result.detector_name, "ground_truth")

    def test_result_has_timestamp(self):
        frame = _frame()
        result = self.detector.process(frame)
        self.assertIsInstance(result.timestamp, datetime)

    def test_hazard_zone_returns_correct_level(self):
        frame = _frame(x=1, y=1, floor=1)
        result = self.detector.process(frame)
        self.assertTrue(len(result.hazard_signals) > 0)
        self.assertEqual(result.hazard_signals[0].hazard_level, HazardLevel.CRITICAL)

    def test_clear_zone_returns_clear(self):
        frame = _frame(x=2, y=2, floor=1)
        result = self.detector.process(frame)
        self.assertEqual(result.hazard_signals[0].hazard_level, HazardLevel.CLEAR)

    def test_victim_zone_with_gt_flag_detects_victim(self):
        frame = _frame(x=1, y=1, floor=1, metadata={"has_victim_ground_truth": True})
        result = self.detector.process(frame)
        self.assertTrue(len(result.victim_signals) > 0)

    def test_victim_zone_without_gt_flag_has_no_victim(self):
        frame = _frame(x=1, y=1, floor=1, metadata={"has_victim_ground_truth": False})
        result = self.detector.process(frame)
        self.assertEqual(len(result.victim_signals), 0)

    def test_victim_not_present_in_zone_without_victim_map_entry(self):
        frame = _frame(x=2, y=2, floor=1, metadata={"has_victim_ground_truth": False})
        result = self.detector.process(frame)
        self.assertEqual(len(result.victim_signals), 0)


class TestGroundTruthDetectorSensorFallback(unittest.TestCase):
    """
    When a zone is NOT in the hazard_map, the detector falls back to
    HazardClassifier on the environmental channel.  This preserves the
    behavior of the Phase 4 engine so all existing tests continue to pass.
    """

    def setUp(self):
        self.detector = GroundTruthDetector()   # empty maps
        self.detector.initialize()

    def test_empty_channel_returns_clear(self):
        frame = _frame(channels={})
        result = self.detector.process(frame)
        self.assertEqual(result.hazard_signals[0].hazard_level, HazardLevel.CLEAR)

    def test_critical_sensors_return_critical(self):
        env = {"temperature": 145.0, "co_level": 680.0, "smoke_density": 0.92}
        frame = _frame(channels={"environmental": env})
        result = self.detector.process(frame)
        self.assertEqual(result.hazard_signals[0].hazard_level, HazardLevel.CRITICAL)

    def test_baseline_sensors_return_clear(self):
        env = {"temperature": 22.0, "co_level": 5.0, "smoke_density": 0.03}
        frame = _frame(channels={"environmental": env})
        result = self.detector.process(frame)
        self.assertEqual(result.hazard_signals[0].hazard_level, HazardLevel.CLEAR)

    def test_sensor_fallback_source_label(self):
        frame = _frame()
        result = self.detector.process(frame)
        self.assertEqual(result.hazard_signals[0].source, "environmental_sensors")

    def test_gt_source_label(self):
        d = GroundTruthDetector(hazard_map={"1_1_1": HazardLevel.HIGH})
        d.initialize()
        frame = _frame(x=1, y=1, floor=1)
        result = d.process(frame)
        self.assertEqual(result.hazard_signals[0].source, "ground_truth")


class TestGroundTruthDetectorObjects(unittest.TestCase):

    def setUp(self):
        self.detector = GroundTruthDetector(
            hazard_map={"1_1_1": HazardLevel.HIGH},
            victim_map={"1_1_1": 0.90},
        )
        self.detector.initialize()

    def test_hazard_zone_has_detected_object(self):
        frame = _frame(x=1, y=1, floor=1)
        result = self.detector.process(frame)
        hazard_objects = [o for o in result.detected_objects if o.object_type == "HAZARD"]
        self.assertTrue(len(hazard_objects) > 0)

    def test_victim_zone_has_victim_object(self):
        frame = _frame(x=1, y=1, floor=1, metadata={"has_victim_ground_truth": True})
        result = self.detector.process(frame)
        victim_objects = [o for o in result.detected_objects if o.object_type == "VICTIM"]
        self.assertTrue(len(victim_objects) > 0)

    def test_clear_zone_no_hazard_object(self):
        d = GroundTruthDetector(hazard_map={"9_9_1": HazardLevel.CLEAR})
        d.initialize()
        frame = _frame(x=9, y=9, floor=1)
        result = d.process(frame)
        hazard_objects = [o for o in result.detected_objects if o.object_type == "HAZARD"]
        self.assertEqual(len(hazard_objects), 0)


if __name__ == "__main__":
    unittest.main()
