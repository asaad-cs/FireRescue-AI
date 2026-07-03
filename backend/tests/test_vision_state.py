"""Tests: Phase 8G vision data path — detector metadata to MissionState."""
from __future__ import annotations

import asyncio
import base64
import unittest

import numpy as np

from backend.mission.manager import MissionManager
from backend.models.frame import Frame, Pose
from backend.models.mission_state import MissionState, MissionStatus, VisionFrame
from perception.detectors.yolo import YOLODetector
from perception.engine import PerceptionEngine
from perception.registry.registry import DetectorRegistry
from perception.tests.test_yolo_detector import (
    FIRE,
    PERSON,
    FakeSession,
    make_detector,
    make_frame,
    make_raw,
    square_image,
)
from perception.types import PerceptionResult, ZoneHistory
from backend.models.mission_state import HazardLevel


class TestDetectorVisionMetadata(unittest.TestCase):

    def _process(self, detections):
        detector = make_detector(raw=make_raw(detections))
        frame = make_frame({"rgb": square_image()})
        frame.metadata["tick"] = 9
        return detector.process(frame)

    def test_vision_payload_present_after_inference(self):
        result = self._process([(320, 320, 100, 100, FIRE, 0.9)])
        vision = result.metadata["vision"]
        self.assertEqual(vision["zone_id"], "2_3_1")
        self.assertEqual(vision["frame_number"], 9)
        self.assertEqual(vision["detector_name"], "yolo")
        self.assertEqual(vision["image_width"], 640)
        self.assertEqual(vision["image_height"], 640)
        self.assertGreaterEqual(vision["inference_ms"], 0.0)
        self.assertEqual(vision["confidence_threshold"], 0.25)

    def test_vision_image_is_valid_jpeg_base64(self):
        result = self._process([])
        data = base64.b64decode(result.metadata["vision"]["image_base64"])
        self.assertEqual(data[:2], b"\xff\xd8")  # JPEG SOI marker

    def test_vision_detections_match_result(self):
        result = self._process([(320, 320, 100, 100, FIRE, 0.9),
                                (100, 100, 50, 50, PERSON, 0.7)])
        detections = result.metadata["vision"]["detections"]
        self.assertEqual(len(detections), 2)
        self.assertEqual(detections[0]["class_name"], "fire")
        self.assertAlmostEqual(detections[0]["confidence"], 0.9, places=4)
        self.assertEqual(len(detections[0]["bbox"]), 4)

    def test_no_vision_without_rgb_channel(self):
        detector = make_detector()
        result = detector.process(make_frame({"environmental": {}}))
        self.assertNotIn("vision", result.metadata)

    def test_vision_payload_validates_as_visionframe_model(self):
        result = self._process([(320, 320, 100, 100, FIRE, 0.9)])
        model = VisionFrame(**result.metadata["vision"])
        self.assertEqual(model.zone_id, "2_3_1")
        self.assertEqual(len(model.detections), 1)


class TestEngineMetadataPassThrough(unittest.TestCase):

    def test_engine_copies_detection_metadata(self):
        registry = DetectorRegistry()
        registry.register(
            "yolo", make_detector(raw=make_raw([(320, 320, 100, 100, FIRE, 0.9)]))
        )
        engine = PerceptionEngine(registry=registry, active_detector="yolo")
        frame = make_frame({"rgb": square_image()})
        enriched = type("EnrichedFrame", (), {"frame": frame, "zone_id": "2_3_1"})()
        result = engine.process(enriched, ZoneHistory(zone_id="2_3_1"))
        self.assertIn("vision", result.metadata)


class _StubPipeline:
    """Pipeline stand-in returning a prepared PerceptionResult."""

    def __init__(self) -> None:
        self.next_result: PerceptionResult | None = None

    def process(self, frame, history):
        return self.next_result


class TestManagerVisionMerge(unittest.TestCase):

    def _manager(self):
        pipeline = _StubPipeline()
        manager = MissionManager(pipeline=pipeline)
        manager.create_mission()
        manager.start_mission()
        return manager, pipeline

    def _frame(self) -> Frame:
        return Frame(
            mission_id="m", drone_id="d", pose=Pose(x=0, y=0, floor=1),
            channels={},
        )

    def _result(self, metadata) -> PerceptionResult:
        return PerceptionResult(
            zone_id="0_0_1",
            hazard_level=HazardLevel.CLEAR,
            victim_probability=0.0,
            frame_id="f-1",
            metadata=metadata,
        )

    def test_vision_lifted_into_mission_state(self):
        manager, pipeline = self._manager()
        pipeline.next_result = self._result(
            {"vision": {"frame_id": "f-1", "zone_id": "0_0_1",
                        "detector_name": "yolo", "frame_number": 3}}
        )
        asyncio.run(manager.on_frame(self._frame()))
        state = manager.get_state()
        self.assertIsNotNone(state.vision)
        self.assertEqual(state.vision.frame_number, 3)
        self.assertEqual(state.vision.detector_name, "yolo")

    def test_vision_cleared_when_result_has_none(self):
        manager, pipeline = self._manager()
        pipeline.next_result = self._result(
            {"vision": {"frame_id": "f-1", "zone_id": "0_0_1"}}
        )
        asyncio.run(manager.on_frame(self._frame()))
        pipeline.next_result = self._result({})
        asyncio.run(manager.on_frame(self._frame()))
        self.assertIsNone(manager.get_state().vision)

    def test_mission_state_serializes_vision(self):
        manager, pipeline = self._manager()
        pipeline.next_result = self._result(
            {"vision": {"frame_id": "f-1", "zone_id": "0_0_1"}}
        )
        asyncio.run(manager.on_frame(self._frame()))
        payload = manager.get_state().model_dump()
        self.assertIn("vision", payload)
        self.assertEqual(payload["vision"]["frame_id"], "f-1")


class TestVisionUnderEachDetector(unittest.TestCase):

    def test_ground_truth_mode_has_no_vision(self):
        from fastapi.testclient import TestClient
        from backend.config.settings import settings
        from backend.main import app

        self.assertEqual(settings.perception_detector, "ground_truth")
        with TestClient(app) as client:
            state = client.app.state.manager.get_state()
            self.assertIsNone(state.vision)
            # The field is still part of the serialized contract.
            self.assertIn("vision", state.model_dump())


if __name__ == "__main__":
    unittest.main()
