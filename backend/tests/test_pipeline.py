"""Tests: Pipeline initializes, validates frames, enriches, processes."""
import unittest

from backend.models.frame import Frame, Pose
from backend.pipeline.enricher import Enricher
from backend.pipeline.pipeline import Pipeline
from backend.pipeline.validator import Validator
from perception.detectors.ground_truth import GroundTruthDetector
from perception.engine import PerceptionEngine, ZoneHistory
from perception.registry.registry import DetectorRegistry


def _make_engine() -> PerceptionEngine:
    detector = GroundTruthDetector()
    detector.initialize()
    registry = DetectorRegistry()
    registry.register("ground_truth", detector)
    return PerceptionEngine(registry=registry, active_detector="ground_truth")


def _make_pipeline() -> Pipeline:
    return Pipeline(
        validator=Validator(),
        enricher=Enricher(),
        engine=_make_engine(),
    )


def _valid_frame(mission_id: str = "m1") -> Frame:
    return Frame(
        mission_id=mission_id,
        drone_id="d1",
        pose=Pose(x=1, y=2, floor=1),
        channels={},
    )


class TestPipelineInit(unittest.TestCase):

    def test_pipeline_creates(self):
        pipeline = _make_pipeline()
        self.assertIsNotNone(pipeline)


class TestPipelineProcess(unittest.TestCase):

    def setUp(self):
        self.pipeline = _make_pipeline()

    def test_valid_frame_returns_result(self):
        frame = _valid_frame()
        history = ZoneHistory(zone_id="")
        result = self.pipeline.process(frame, history)
        self.assertIsNotNone(result)

    def test_zone_id_derived_from_pose(self):
        frame = _valid_frame()
        history = ZoneHistory(zone_id="")
        result = self.pipeline.process(frame, history)
        self.assertEqual(result.zone_id, "1_2_1")

    def test_invalid_frame_returns_none(self):
        frame = Frame(
            mission_id="",   # empty mission_id — should fail validation
            drone_id="d1",
            pose=Pose(x=0, y=0, floor=1),
            channels={},
        )
        history = ZoneHistory(zone_id="")
        result = self.pipeline.process(frame, history)
        self.assertIsNone(result)

    def test_result_has_hazard_level(self):
        frame = _valid_frame()
        history = ZoneHistory(zone_id="")
        result = self.pipeline.process(frame, history)
        self.assertIsNotNone(result.hazard_level)

    def test_zone_history_zone_id_set(self):
        frame = _valid_frame()
        history = ZoneHistory(zone_id="")
        self.pipeline.process(frame, history)
        self.assertEqual(history.zone_id, "1_2_1")


class TestValidator(unittest.TestCase):

    def test_valid_frame_passes(self):
        v = Validator()
        frame = _valid_frame()
        self.assertEqual(v.validate(frame), frame)

    def test_missing_mission_id_raises(self):
        v = Validator()
        frame = Frame(mission_id="", drone_id="d1", pose=Pose(x=0, y=0, floor=1), channels={})
        with self.assertRaises(ValueError):
            v.validate(frame)

    def test_missing_drone_id_raises(self):
        v = Validator()
        frame = Frame(mission_id="m1", drone_id="", pose=Pose(x=0, y=0, floor=1), channels={})
        with self.assertRaises(ValueError):
            v.validate(frame)

    def test_channels_not_dict_raises(self):
        v = Validator()
        frame = Frame(mission_id="m1", drone_id="d1", pose=Pose(x=0, y=0, floor=1), channels=None)
        with self.assertRaises(ValueError):
            v.validate(frame)


class TestEnricher(unittest.TestCase):

    def test_zone_id_format(self):
        e = Enricher()
        frame = _valid_frame()
        enriched = e.enrich(frame)
        self.assertEqual(enriched.zone_id, "1_2_1")

    def test_original_frame_preserved(self):
        e = Enricher()
        frame = _valid_frame()
        enriched = e.enrich(frame)
        self.assertIs(enriched.frame, frame)


if __name__ == "__main__":
    unittest.main()
