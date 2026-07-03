"""Tests: YOLODetector — ONNX inference behind AbstractDetector.

ONNX inference is mocked with a deterministic fake session everywhere
except the two opt-in tests that exercise onnxruntime itself (skipped
automatically when onnxruntime or a real exported model is absent).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.models.frame import Frame, Pose
from backend.models.mission_state import HazardLevel
from perception.detectors.ground_truth import GroundTruthDetector
from perception.detectors.yolo import (
    YOLODetector,
    _nms,
    _unletterbox,
    find_latest_model,
)
from perception.engine import PerceptionEngine
from perception.registry.registry import DetectorRegistry
from perception.types import ZoneHistory

FIRE, SMOKE, PERSON = 0, 1, 2
INPUT_SIZE = 640
EXPORTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "ai" / "object_detection" / "models" / "exports"
)


def make_frame(channels=None) -> Frame:
    return Frame(
        mission_id="m-1",
        drone_id="d-1",
        pose=Pose(x=2, y=3, floor=1),
        channels=channels if channels is not None else {},
    )


def make_raw(detections) -> np.ndarray:
    """Build a fake [1, 7, 8400] YOLOv8 head output.

    detections: iterable of (cx, cy, w, h, class_id, confidence) in
    model-input coordinates; all other anchors stay at score 0.
    """
    raw = np.zeros((1, 7, 8400), dtype=np.float32)
    for column, (cx, cy, w, h, class_id, conf) in enumerate(detections):
        raw[0, 0, column] = cx
        raw[0, 1, column] = cy
        raw[0, 2, column] = w
        raw[0, 3, column] = h
        raw[0, 4 + class_id, column] = conf
    return raw


class FakeSession:
    """Deterministic stand-in for an onnxruntime.InferenceSession."""

    def __init__(self, raw: np.ndarray, fail: bool = False) -> None:
        self._raw = raw
        self._fail = fail
        self.received = None

    def run(self, output_names, feeds):
        if self._fail:
            raise RuntimeError("synthetic inference failure")
        self.received = feeds
        return [self._raw]


def make_detector(raw=None, fail=False, **kwargs) -> YOLODetector:
    """A YOLODetector with an injected fake session (no model file)."""
    detector = YOLODetector(model_path="does-not-exist.onnx", **kwargs)
    detector._session = FakeSession(
        raw if raw is not None else make_raw([]), fail=fail
    )
    detector._input_name = "images"
    return detector


def square_image(value: int = 50) -> np.ndarray:
    """A 640x640 image: letterbox scale=1, pad=0 — coordinates map 1:1."""
    return np.full((INPUT_SIZE, INPUT_SIZE, 3), value, dtype=np.uint8)


class TestLifecycleAndFailureHandling(unittest.TestCase):

    def test_detector_name(self):
        self.assertEqual(YOLODetector("x.onnx").detector_name, "yolo")

    def test_missing_model_file_never_raises(self):
        detector = YOLODetector(model_path="no/such/model.onnx")
        detector.initialize()
        self.assertFalse(detector.is_available)
        result = detector.process(make_frame({"rgb": square_image()}))
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.UNOBSERVED
        )
        self.assertIn("not found", result.metadata["unobserved_reason"])

    def test_invalid_model_file_never_raises(self):
        try:
            import onnxruntime  # noqa: F401
        except ImportError:
            self.skipTest("onnxruntime not installed")
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "corrupt.onnx"
            bad.write_bytes(b"this is not an onnx model")
            detector = YOLODetector(model_path=bad)
            detector.initialize()
            self.assertFalse(detector.is_available)
            self.assertIn(
                "failed to load", detector._unavailable_reason
            )

    def test_process_before_initialize_is_unobserved(self):
        detector = YOLODetector(model_path="x.onnx")
        result = detector.process(make_frame({"rgb": square_image()}))
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.UNOBSERVED
        )

    def test_frame_without_rgb_channel_is_unobserved(self):
        detector = make_detector()
        result = detector.process(make_frame({"environmental": {}}))
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.UNOBSERVED
        )
        self.assertIn("rgb", result.metadata["unobserved_reason"])

    def test_inference_failure_never_raises(self):
        detector = make_detector(fail=True)
        result = detector.process(make_frame({"rgb": square_image()}))
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.UNOBSERVED
        )
        self.assertIn("inference failed", result.metadata["unobserved_reason"])

    def test_invalid_rgb_shape_never_raises(self):
        detector = make_detector()
        result = detector.process(
            make_frame({"rgb": np.zeros((10, 10), dtype=np.uint8)})
        )
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.UNOBSERVED
        )

    def test_shutdown_releases_session(self):
        detector = make_detector()
        detector.shutdown()
        self.assertFalse(detector.is_available)

    def test_zone_id_convention_matches_ground_truth(self):
        detector = make_detector()
        result = detector.process(make_frame({"rgb": square_image()}))
        self.assertEqual(result.zone_id, "2_3_1")


class TestPreprocessing(unittest.TestCase):

    def test_tensor_shape_dtype_and_range(self):
        detector = make_detector()
        tensor, scale, pad = detector._preprocess(square_image(255))
        self.assertEqual(tensor.shape, (1, 3, INPUT_SIZE, INPUT_SIZE))
        self.assertEqual(tensor.dtype, np.float32)
        self.assertAlmostEqual(float(tensor.max()), 1.0, places=5)
        self.assertGreaterEqual(float(tensor.min()), 0.0)
        self.assertEqual(scale, 1.0)
        self.assertEqual(pad, (0.0, 0.0))

    def test_letterbox_scale_and_padding_for_wide_image(self):
        detector = make_detector()
        image = np.zeros((320, 640, 3), dtype=np.uint8)  # H=320, W=640
        tensor, scale, pad = detector._preprocess(image)
        self.assertEqual(scale, 1.0)
        self.assertEqual(pad, (0.0, 160.0))  # vertical padding only
        # Padded rows carry the letterbox fill value (114/255).
        self.assertAlmostEqual(
            float(tensor[0, 0, 0, 0]), 114 / 255, places=5
        )

    def test_bgr_to_rgb_conversion(self):
        detector = make_detector()
        image = np.zeros((INPUT_SIZE, INPUT_SIZE, 3), dtype=np.uint8)
        image[:, :, 0] = 255  # blue channel in BGR
        tensor, _, _ = detector._preprocess(image)
        self.assertAlmostEqual(float(tensor[0, 2].max()), 1.0)  # ...is RGB ch 2
        self.assertAlmostEqual(float(tensor[0, 0].max()), 0.0)

    def test_image_from_file_path(self):
        import cv2

        detector = make_detector(
            raw=make_raw([(320, 320, 100, 100, FIRE, 0.9)])
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.png"
            cv2.imwrite(str(path), square_image())
            result = detector.process(make_frame({"rgb": str(path)}))
        self.assertEqual(result.metadata["detections"], 1)


class TestDecodingAndThresholds(unittest.TestCase):

    def test_deterministic_mocked_inference(self):
        detector = make_detector(
            raw=make_raw([(320, 320, 100, 200, FIRE, 0.9)])
        )
        detections = detector._infer(square_image())
        self.assertEqual(len(detections), 1)
        det = detections[0]
        self.assertEqual(det["class_name"], "fire")
        self.assertAlmostEqual(det["confidence"], 0.9, places=5)
        x1, y1, x2, y2 = det["bbox_xyxy"]
        self.assertAlmostEqual(x1, 270.0, places=3)
        self.assertAlmostEqual(y1, 220.0, places=3)
        self.assertAlmostEqual(x2, 370.0, places=3)
        self.assertAlmostEqual(y2, 420.0, places=3)

    def test_confidence_threshold_filters(self):
        detector = make_detector(
            raw=make_raw(
                [
                    (100, 100, 50, 50, FIRE, 0.24),   # below default 0.25
                    (300, 300, 50, 50, SMOKE, 0.26),  # above
                ]
            )
        )
        detections = detector._infer(square_image())
        self.assertEqual([d["class_name"] for d in detections], ["smoke"])

    def test_custom_confidence_threshold(self):
        detector = make_detector(
            raw=make_raw([(300, 300, 50, 50, FIRE, 0.5)]),
            confidence_threshold=0.6,
        )
        self.assertEqual(detector._infer(square_image()), [])

    def test_nms_collapses_overlapping_same_class(self):
        detector = make_detector(
            raw=make_raw(
                [
                    (320, 320, 100, 100, FIRE, 0.9),
                    (325, 325, 100, 100, FIRE, 0.6),  # heavy overlap
                ]
            )
        )
        detections = detector._infer(square_image())
        self.assertEqual(len(detections), 1)
        self.assertAlmostEqual(detections[0]["confidence"], 0.9, places=5)

    def test_nms_keeps_overlapping_different_classes(self):
        detector = make_detector(
            raw=make_raw(
                [
                    (320, 320, 100, 100, FIRE, 0.9),
                    (325, 325, 100, 100, SMOKE, 0.8),
                ]
            )
        )
        detections = detector._infer(square_image())
        self.assertEqual(len(detections), 2)

    def test_boxes_mapped_back_through_letterbox(self):
        # 320x640 image → scale 1, pad_y 160. A box at input-space
        # cy=320 must land at original cy=160.
        detector = make_detector(
            raw=make_raw([(320, 320, 100, 100, PERSON, 0.9)])
        )
        image = np.zeros((320, 640, 3), dtype=np.uint8)
        detections = detector._infer(image)
        x1, y1, x2, y2 = detections[0]["bbox_xyxy"]
        self.assertAlmostEqual(y1, 110.0, places=3)
        self.assertAlmostEqual(y2, 210.0, places=3)
        self.assertAlmostEqual(x1, 270.0, places=3)


class TestNmsHelper(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(
            _nms(np.zeros((0, 4)), np.zeros(0), np.zeros(0, dtype=int), 0.45),
            [],
        )

    def test_highest_score_survives(self):
        boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]],
                         dtype=np.float32)
        scores = np.array([0.5, 0.9, 0.7], dtype=np.float32)
        classes = np.zeros(3, dtype=np.int64)
        keep = _nms(boxes, scores, classes, iou_threshold=0.45)
        self.assertEqual(sorted(keep), [1, 2])

    def test_unletterbox_clips_to_image(self):
        box = np.array([-10.0, 0.0, 700.0, 640.0])
        x1, y1, x2, y2 = _unletterbox(box, 1.0, (0.0, 0.0), 640, 640)
        self.assertEqual((x1, y1, x2, y2), (0.0, 0.0, 640.0, 640.0))


class TestClassMapping(unittest.TestCase):

    def _result(self, detections):
        detector = make_detector(raw=make_raw(detections))
        return detector.process(make_frame({"rgb": square_image()}))

    def test_strong_fire_is_critical(self):
        result = self._result([(320, 320, 100, 100, FIRE, 0.9)])
        signal = result.hazard_signals[0]
        self.assertEqual(signal.hazard_level, HazardLevel.CRITICAL)
        self.assertEqual(signal.source, "yolo")
        self.assertEqual(result.detected_objects[0].object_type, "FIRE")

    def test_weak_fire_is_high(self):
        result = self._result([(320, 320, 100, 100, FIRE, 0.5)])
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.HIGH
        )

    def test_strong_smoke_is_moderate(self):
        result = self._result([(320, 320, 100, 100, SMOKE, 0.8)])
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.MODERATE
        )

    def test_weak_smoke_is_low(self):
        result = self._result([(320, 320, 100, 100, SMOKE, 0.3)])
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.LOW
        )

    def test_person_becomes_victim_signal(self):
        result = self._result([(320, 320, 100, 100, PERSON, 0.8)])
        self.assertEqual(len(result.victim_signals), 1)
        signal = result.victim_signals[0]
        self.assertEqual(signal.victim_id, "unknown")
        self.assertAlmostEqual(signal.confidence, 0.8, places=4)
        self.assertEqual(result.detected_objects[0].object_type, "VICTIM")
        # A person alone is not a hazard: the zone reads CLEAR.
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.CLEAR
        )

    def test_clean_image_reads_clear(self):
        result = self._result([])
        self.assertEqual(len(result.hazard_signals), 1)
        self.assertEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.CLEAR
        )
        self.assertEqual(result.victim_signals, [])

    def test_detected_objects_carry_bboxes(self):
        result = self._result([(320, 320, 100, 100, FIRE, 0.9)])
        metadata = result.detected_objects[0].metadata
        self.assertIn("bbox_xyxy", metadata)
        self.assertEqual(len(metadata["bbox_xyxy"]), 4)

    def test_detection_result_shape(self):
        result = self._result([(320, 320, 100, 100, FIRE, 0.9),
                               (100, 100, 50, 50, PERSON, 0.7)])
        self.assertEqual(result.detector_name, "yolo")
        self.assertEqual(result.zone_id, "2_3_1")
        self.assertAlmostEqual(result.confidence_score, 0.8, places=4)
        self.assertEqual(result.metadata["detections"], 2)


class TestRegistryAndEngineSwitching(unittest.TestCase):

    def _registry(self, raw=None):
        registry = DetectorRegistry()
        gt = GroundTruthDetector()
        gt.initialize()
        registry.register("ground_truth", gt)
        registry.register("yolo", make_detector(raw=raw))
        return registry

    def test_both_detectors_registered(self):
        registry = self._registry()
        self.assertEqual(
            sorted(registry.available()), ["ground_truth", "yolo"]
        )

    def test_engine_routes_to_yolo(self):
        registry = self._registry(
            raw=make_raw([(320, 320, 100, 100, FIRE, 0.9)])
        )
        engine = PerceptionEngine(registry=registry, active_detector="yolo")
        frame = make_frame({"rgb": square_image()})
        enriched = type("EnrichedFrame", (), {"frame": frame, "zone_id": "2_3_1"})()
        result = engine.process(enriched, ZoneHistory(zone_id="2_3_1"))
        self.assertEqual(result.detector_name, "yolo")
        self.assertEqual(result.hazard_level, HazardLevel.CRITICAL)

    def test_engine_routes_to_ground_truth_unchanged(self):
        registry = self._registry()
        engine = PerceptionEngine(registry=registry,
                                  active_detector="ground_truth")
        frame = make_frame({"environmental": {"temperature": 20.0}})
        enriched = type("EnrichedFrame", (), {"frame": frame, "zone_id": "2_3_1"})()
        result = engine.process(enriched, ZoneHistory(zone_id="2_3_1"))
        self.assertEqual(result.detector_name, "ground_truth")

    def test_find_latest_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(find_latest_model(root / "missing"))
            self.assertIsNone(find_latest_model(root))
            (root / "old.onnx").write_bytes(b"a")
            newest = root / "new.onnx"
            newest.write_bytes(b"b")
            import os
            os.utime(root / "old.onnx", (1, 1))
            self.assertEqual(find_latest_model(root), newest)


class TestRealExportedModel(unittest.TestCase):
    """Opt-in integration test against the Phase 8D ONNX export."""

    def test_real_model_end_to_end(self):
        try:
            import onnxruntime  # noqa: F401
        except ImportError:
            self.skipTest("onnxruntime not installed")
        model = find_latest_model(EXPORTS_DIR)
        if model is None:
            self.skipTest("no exported .onnx model present")
        detector = YOLODetector(model_path=model)
        detector.initialize()
        self.assertTrue(detector.is_available)
        result = detector.process(make_frame({"rgb": square_image()}))
        self.assertEqual(result.detector_name, "yolo")
        self.assertGreaterEqual(len(result.hazard_signals), 1)
        self.assertNotEqual(
            result.hazard_signals[0].hazard_level, HazardLevel.UNOBSERVED
        )
        detector.shutdown()
        self.assertFalse(detector.is_available)


if __name__ == "__main__":
    unittest.main()
