"""
YOLODetector — real ONNX inference behind the AbstractDetector interface.

Runs the object detection model trained in the Version 2 AI workspace
(ai/object_detection/, exported to ONNX) against the frame's "rgb"
channel and translates detections into the same DetectionResult
structure GroundTruthDetector produces. The rest of the system —
PerceptionEngine, Pipeline, MissionManager, frontend — cannot tell
which detector produced a result.

Inference pipeline (per frame):
  rgb channel → letterbox resize → BGR→RGB, HWC→CHW, /255 float32
  → ONNX Runtime session.run → decode [1, 4+nc, 8400] head
  → confidence filter → class-aware NMS → un-letterbox to pixel space
  → class mapping (fire/smoke → HazardSignal, person → VictimSignal)

Graceful degradation contract:
  - initialize() never raises: a missing model file, a corrupt model,
    or an absent runtime (onnxruntime/numpy/cv2) leaves the detector
    registered but "unavailable".
  - process() never raises: with no usable model or no "rgb" channel
    it returns a best-effort UNOBSERVED result and says why in the
    result metadata.

Heavy dependencies (numpy, cv2, onnxruntime) are imported lazily so
the MVP keeps running with ground_truth when the ML stack is not
installed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.models.frame import Frame
from backend.models.mission_state import HazardLevel
from perception.base.detector import AbstractDetector
from perception.results.detection import (
    DetectedObject,
    DetectionResult,
    HazardSignal,
    VictimSignal,
)

logger = logging.getLogger(__name__)

# Class names the exported model was trained with, index-aligned with
# ai/object_detection/configs/dataset.yaml. Passed to __init__ so the
# detector itself carries no dataset assumptions.
DEFAULT_CLASS_NAMES: Tuple[str, ...] = ("fire", "smoke", "person")

# Detection confidence at or above which a hazard is escalated one level.
_STRONG_DETECTION_CONF = 0.75

# Hazard mapping: class name → (base level, escalated level).
_HAZARD_LEVELS: Dict[str, Tuple[HazardLevel, HazardLevel]] = {
    "fire": (HazardLevel.HIGH, HazardLevel.CRITICAL),
    "smoke": (HazardLevel.LOW, HazardLevel.MODERATE),
}

# Confidence attached to a CLEAR signal when an image was analysed and
# nothing was found (an observed-clear statement, not certainty).
_CLEAR_CONFIDENCE = 0.85

# Letterbox padding value (Ultralytics convention).
_PAD_VALUE = 114


def find_latest_model(exports_dir: Path) -> Optional[Path]:
    """Return the newest .onnx file under a directory, or None.

    Args:
        exports_dir: Directory to search (not recursive).

    Returns:
        The most recently modified .onnx path, or None when the
        directory holds no exported model.
    """
    if not exports_dir.is_dir():
        return None
    candidates = sorted(
        exports_dir.glob("*.onnx"), key=lambda p: p.stat().st_mtime
    )
    return candidates[-1] if candidates else None


class YOLODetector(AbstractDetector):
    """
    ONNX-Runtime-backed detector for the fire/smoke/person model.

    Configured entirely at construction time (no hardcoded paths):

      model_path            exported .onnx file to load
      confidence_threshold  minimum kept detection confidence
      iou_threshold         NMS IoU threshold
      image_size            square input size the model was exported with
      class_names           index-aligned class names of the model head
    """

    def __init__(
        self,
        model_path: Path | str,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        image_size: int = 640,
        class_names: Sequence[str] = DEFAULT_CLASS_NAMES,
    ) -> None:
        self._model_path = Path(model_path)
        self._confidence_threshold = float(confidence_threshold)
        self._iou_threshold = float(iou_threshold)
        self._image_size = int(image_size)
        self._class_names: Tuple[str, ...] = tuple(class_names)
        self._session: Any = None
        self._input_name: Optional[str] = None
        self._unavailable_reason: Optional[str] = None

    # ------------------------------------------------------------------
    # AbstractDetector interface
    # ------------------------------------------------------------------

    @property
    def detector_name(self) -> str:
        return "yolo"

    @property
    def is_available(self) -> bool:
        """True when a model session is loaded and ready for inference."""
        return self._session is not None

    def initialize(self) -> None:
        """Load the ONNX model. Never raises; failures leave the
        detector registered but unavailable (see class docstring)."""
        self._session = None
        self._unavailable_reason = None
        if not self._model_path.is_file():
            self._unavailable_reason = f"model file not found: {self._model_path}"
            logger.warning("YOLODetector | unavailable | %s", self._unavailable_reason)
            return
        try:
            import onnxruntime as ort

            self._session = ort.InferenceSession(
                str(self._model_path), providers=["CPUExecutionProvider"]
            )
            self._input_name = self._session.get_inputs()[0].name
            logger.info(
                "YOLODetector | initialized | model=%s conf=%.2f iou=%.2f imgsz=%d",
                self._model_path.name,
                self._confidence_threshold,
                self._iou_threshold,
                self._image_size,
            )
        except ImportError as exc:
            self._session = None
            self._unavailable_reason = f"onnxruntime not installed: {exc}"
            logger.warning("YOLODetector | unavailable | %s", self._unavailable_reason)
        except Exception as exc:  # corrupt/incompatible model file
            self._session = None
            self._unavailable_reason = f"failed to load model: {exc}"
            logger.warning("YOLODetector | unavailable | %s", self._unavailable_reason)

    def shutdown(self) -> None:
        self._session = None
        self._input_name = None
        logger.info("YOLODetector | shutdown")

    def process(self, frame: Frame) -> DetectionResult:
        """Run inference on the frame's "rgb" channel.

        Never raises. Returns an UNOBSERVED best-effort result when the
        model is unavailable, the frame carries no image, or inference
        fails; the metadata field explains why.
        """
        zone_id = _zone_id_from_frame(frame)
        if self._session is None:
            return self._unobserved(frame, zone_id, self._unavailable_reason
                                    or "detector not initialized")

        image = frame.channels.get("rgb")
        if image is None:
            return self._unobserved(frame, zone_id, "frame has no 'rgb' channel")

        try:
            detections = self._infer(image)
        except Exception as exc:
            logger.error(
                "YOLODetector | inference failed | frame=%s zone=%s: %s",
                frame.frame_id, zone_id, exc,
            )
            return self._unobserved(frame, zone_id, f"inference failed: {exc}")

        return self._to_detection_result(frame, zone_id, detections)

    # ------------------------------------------------------------------
    # Inference pipeline
    # ------------------------------------------------------------------

    def _infer(self, image: Any) -> List[Dict[str, Any]]:
        """Full pipeline: preprocess → ONNX run → decode → filter → NMS.

        Args:
            image: HxWx3 uint8 BGR numpy array, or a path to an image.

        Returns:
            One dict per kept detection:
            {class_id, class_name, confidence, bbox_xyxy (original pixels)}.
        """
        import numpy as np

        array = self._as_image_array(image)
        tensor, scale, pad = self._preprocess(array)
        raw = self._session.run(None, {self._input_name: tensor})[0]
        boxes, scores, class_ids = self._decode(np.asarray(raw))
        keep = _nms(boxes, scores, class_ids, self._iou_threshold)

        height, width = array.shape[:2]
        detections: List[Dict[str, Any]] = []
        for i in keep:
            x1, y1, x2, y2 = _unletterbox(boxes[i], scale, pad, width, height)
            class_id = int(class_ids[i])
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": self._class_names[class_id],
                    "confidence": float(scores[i]),
                    "bbox_xyxy": [x1, y1, x2, y2],
                }
            )
        return detections

    def _as_image_array(self, image: Any):
        """Coerce the rgb channel value into an HxWx3 uint8 array."""
        import numpy as np

        if isinstance(image, (str, Path)):
            import cv2

            data = np.fromfile(str(image), dtype=np.uint8)
            decoded = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if decoded is None:
                raise ValueError(f"could not decode image file: {image}")
            return decoded
        array = np.asarray(image)
        if array.ndim != 3 or array.shape[2] != 3:
            raise ValueError(
                f"'rgb' channel must be HxWx3, got shape {array.shape}"
            )
        return array.astype(np.uint8, copy=False)

    def _preprocess(self, array) -> Tuple[Any, float, Tuple[float, float]]:
        """Letterbox to the model input size and build the input tensor.

        Returns:
            (NCHW float32 tensor in [0,1], scale factor, (pad_x, pad_y)).
        """
        import cv2
        import numpy as np

        height, width = array.shape[:2]
        size = self._image_size
        scale = min(size / width, size / height)
        new_w, new_h = round(width * scale), round(height * scale)
        pad_x, pad_y = (size - new_w) / 2, (size - new_h) / 2

        resized = cv2.resize(array, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((size, size, 3), _PAD_VALUE, dtype=np.uint8)
        top, left = round(pad_y - 0.1), round(pad_x - 0.1)
        canvas[top:top + new_h, left:left + new_w] = resized

        rgb = canvas[:, :, ::-1]                      # BGR → RGB
        chw = rgb.transpose(2, 0, 1)                  # HWC → CHW
        tensor = chw[np.newaxis].astype(np.float32) / 255.0
        return tensor, scale, (pad_x, pad_y)

    def _decode(self, raw):
        """Decode the YOLOv8 ONNX head and apply the confidence filter.

        Args:
            raw: [1, 4+nc, anchors] output — cx, cy, w, h + class scores.

        Returns:
            (boxes_xyxy, scores, class_ids) numpy arrays in input-tensor
            (letterboxed) coordinates, confidence-filtered.
        """
        import numpy as np

        prediction = raw[0]                            # [4+nc, anchors]
        boxes_cxcywh = prediction[:4].T                # [anchors, 4]
        class_scores = prediction[4:].T                # [anchors, nc]

        class_ids = class_scores.argmax(axis=1)
        scores = class_scores.max(axis=1)
        mask = scores >= self._confidence_threshold

        boxes_cxcywh = boxes_cxcywh[mask]
        cx, cy, w, h = boxes_cxcywh.T
        boxes_xyxy = np.stack(
            [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1
        )
        return boxes_xyxy, scores[mask], class_ids[mask]

    # ------------------------------------------------------------------
    # Result mapping
    # ------------------------------------------------------------------

    def _to_detection_result(
        self, frame: Frame, zone_id: str, detections: List[Dict[str, Any]]
    ) -> DetectionResult:
        """Translate raw detections into the project's DetectionResult."""
        detected_objects: List[DetectedObject] = []
        hazard_signals: List[HazardSignal] = []
        victim_signals: List[VictimSignal] = []

        for index, det in enumerate(detections):
            name = det["class_name"]
            confidence = round(det["confidence"], 4)
            metadata = {"bbox_xyxy": det["bbox_xyxy"], "class_name": name}
            if name in _HAZARD_LEVELS:
                base, escalated = _HAZARD_LEVELS[name]
                level = escalated if confidence >= _STRONG_DETECTION_CONF else base
                hazard_signals.append(
                    HazardSignal(
                        zone_id=zone_id,
                        hazard_level=level,
                        confidence=confidence,
                        source="yolo",
                    )
                )
                detected_objects.append(
                    DetectedObject(
                        object_id=f"{name}-{zone_id}-{index}",
                        object_type=name.upper(),
                        zone_id=zone_id,
                        confidence=confidence,
                        metadata=metadata,
                    )
                )
            elif name == "person":
                victim_signals.append(
                    VictimSignal(
                        victim_id="unknown",
                        zone_id=zone_id,
                        confidence=confidence,
                        state_estimate="UNKNOWN",
                    )
                )
                detected_objects.append(
                    DetectedObject(
                        object_id=f"victim-{zone_id}-{index}",
                        object_type="VICTIM",
                        zone_id=zone_id,
                        confidence=confidence,
                        metadata=metadata,
                    )
                )

        if not hazard_signals:
            # Image analysed, nothing hazardous found: observed clear.
            hazard_signals.append(
                HazardSignal(
                    zone_id=zone_id,
                    hazard_level=HazardLevel.CLEAR,
                    confidence=_CLEAR_CONFIDENCE,
                    source="yolo",
                )
            )

        confidences = [d["confidence"] for d in detections]
        overall = (
            sum(confidences) / len(confidences) if confidences else _CLEAR_CONFIDENCE
        )
        return DetectionResult(
            frame_id=frame.frame_id,
            zone_id=zone_id,
            detector_name=self.detector_name,
            timestamp=datetime.now(timezone.utc),
            detected_objects=detected_objects,
            victim_signals=victim_signals,
            hazard_signals=hazard_signals,
            confidence_score=round(overall, 4),
            metadata={
                "source": "yolo",
                "model": self._model_path.name,
                "detections": len(detections),
            },
        )

    def _unobserved(self, frame: Frame, zone_id: str, reason: str) -> DetectionResult:
        """Best-effort result when no observation could be made."""
        return DetectionResult(
            frame_id=frame.frame_id,
            zone_id=zone_id,
            detector_name=self.detector_name,
            timestamp=datetime.now(timezone.utc),
            hazard_signals=[
                HazardSignal(
                    zone_id=zone_id,
                    hazard_level=HazardLevel.UNOBSERVED,
                    confidence=0.0,
                    source="yolo",
                )
            ],
            confidence_score=0.0,
            metadata={"source": "yolo", "unobserved_reason": reason},
        )


# ----------------------------------------------------------------------
# Module helpers (pure functions — unit-testable without a model)
# ----------------------------------------------------------------------


def _zone_id_from_frame(frame: Frame) -> str:
    """Zone id convention shared by all detectors: '<x>_<y>_<floor>'."""
    return f"{frame.pose.x}_{frame.pose.y}_{frame.pose.floor}"


def _nms(boxes, scores, class_ids, iou_threshold: float) -> List[int]:
    """Class-aware non-maximum suppression (pure numpy).

    Args:
        boxes: [N, 4] xyxy boxes.
        scores: [N] confidences.
        class_ids: [N] integer class ids; boxes only suppress within
            their own class.
        iou_threshold: overlap at or above which the lower-scoring box
            of the same class is suppressed.

    Returns:
        Indices of kept boxes, highest score first.
    """
    import numpy as np

    if len(boxes) == 0:
        return []
    # Offset boxes per class so cross-class overlaps never suppress.
    offsets = class_ids.astype(np.float32) * (boxes.max() + 1.0)
    shifted = boxes + offsets[:, None]

    x1, y1, x2, y2 = shifted.T
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]

    keep: List[int] = []
    while order.size > 0:
        best = order[0]
        keep.append(int(best))
        rest = order[1:]
        inter_w = np.maximum(
            0.0, np.minimum(x2[best], x2[rest]) - np.maximum(x1[best], x1[rest])
        )
        inter_h = np.maximum(
            0.0, np.minimum(y2[best], y2[rest]) - np.maximum(y1[best], y1[rest])
        )
        inter = inter_w * inter_h
        union = areas[best] + areas[rest] - inter
        iou = np.where(union > 0, inter / union, 0.0)
        order = rest[iou < iou_threshold]
    return keep


def _unletterbox(
    box, scale: float, pad: Tuple[float, float], width: int, height: int
) -> Tuple[float, float, float, float]:
    """Map one xyxy box from letterboxed space back to original pixels.

    Args:
        box: xyxy box in model-input coordinates.
        scale: letterbox scale factor that was applied.
        pad: (pad_x, pad_y) letterbox padding that was applied.
        width: original image width.
        height: original image height.

    Returns:
        xyxy box clipped to the original image bounds.
    """
    x1 = (float(box[0]) - pad[0]) / scale
    y1 = (float(box[1]) - pad[1]) / scale
    x2 = (float(box[2]) - pad[0]) / scale
    y2 = (float(box[3]) - pad[1]) / scale
    return (
        max(0.0, min(x1, width)),
        max(0.0, min(y1, height)),
        max(0.0, min(x2, width)),
        max(0.0, min(y2, height)),
    )
