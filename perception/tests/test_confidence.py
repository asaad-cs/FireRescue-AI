"""Tests: Confidence scores — must be realistic (sub-1.0) values."""
import unittest

from backend.models.frame import Frame, Pose
from backend.models.mission_state import HazardLevel
from perception.detectors.ground_truth import GroundTruthDetector


def _frame(x: int = 1, y: int = 1, floor: int = 1, metadata: dict = None) -> Frame:
    return Frame(
        mission_id="m1",
        drone_id="d1",
        pose=Pose(x=x, y=y, floor=floor),
        channels={},
        metadata=metadata or {},
    )


class TestHazardConfidence(unittest.TestCase):

    def _confidence_for(self, level: HazardLevel) -> float:
        d = GroundTruthDetector(hazard_map={"1_1_1": level})
        d.initialize()
        result = d.process(_frame())
        return result.hazard_signals[0].confidence

    def test_critical_confidence_below_one(self):
        self.assertLess(self._confidence_for(HazardLevel.CRITICAL), 1.0)

    def test_high_confidence_below_one(self):
        self.assertLess(self._confidence_for(HazardLevel.HIGH), 1.0)

    def test_moderate_confidence_below_one(self):
        self.assertLess(self._confidence_for(HazardLevel.MODERATE), 1.0)

    def test_clear_confidence_high_but_below_one(self):
        c = self._confidence_for(HazardLevel.CLEAR)
        self.assertLess(c, 1.0)
        self.assertGreater(c, 0.9)   # CLEAR is very certain but not absolute

    def test_all_hazard_confidences_positive(self):
        for level in HazardLevel:
            self.assertGreater(self._confidence_for(level), 0.0)

    def test_sensor_fallback_confidence_below_gt_clear_confidence(self):
        # Sensor-based confidence (0.78) should be lower than GT CLEAR (0.98)
        d_empty = GroundTruthDetector()   # no maps → sensor fallback
        d_empty.initialize()
        sensor_conf = d_empty.process(_frame()).hazard_signals[0].confidence

        d_gt = GroundTruthDetector(hazard_map={"1_1_1": HazardLevel.CLEAR})
        d_gt.initialize()
        gt_conf = d_gt.process(_frame()).hazard_signals[0].confidence

        self.assertLess(sensor_conf, gt_conf)


class TestVictimConfidence(unittest.TestCase):

    def test_victim_confidence_matches_detection_probability(self):
        detection_prob = 0.85
        d = GroundTruthDetector(
            hazard_map={},
            victim_map={"1_1_1": detection_prob},
        )
        d.initialize()
        frame = _frame(metadata={"has_victim_ground_truth": True})
        result = d.process(frame)
        self.assertEqual(len(result.victim_signals), 1)
        self.assertAlmostEqual(result.victim_signals[0].confidence, detection_prob)

    def test_victim_confidence_below_one(self):
        d = GroundTruthDetector(victim_map={"1_1_1": 0.96})
        d.initialize()
        frame = _frame(metadata={"has_victim_ground_truth": True})
        result = d.process(frame)
        self.assertLess(result.victim_signals[0].confidence, 1.0)

    def test_overall_confidence_score_is_set(self):
        d = GroundTruthDetector(
            hazard_map={"1_1_1": HazardLevel.HIGH},
            victim_map={"1_1_1": 0.85},
        )
        d.initialize()
        frame = _frame(metadata={"has_victim_ground_truth": True})
        result = d.process(frame)
        self.assertGreater(result.confidence_score, 0.0)
        self.assertLessEqual(result.confidence_score, 1.0)

    def test_overall_confidence_score_between_zero_and_one(self):
        d = GroundTruthDetector()
        d.initialize()
        result = d.process(_frame())
        self.assertGreaterEqual(result.confidence_score, 0.0)
        self.assertLessEqual(result.confidence_score, 1.0)


if __name__ == "__main__":
    unittest.main()
