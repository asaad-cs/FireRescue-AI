from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from backend.models.frame import Frame
from backend.models.mission_state import HazardLevel
from perception.base.detector import AbstractDetector
from perception.hazard import HazardClassifier
from perception.results.detection import (
    DetectedObject,
    DetectionResult,
    HazardSignal,
    VictimSignal,
)
from perception.types import ZoneHistory
from perception.victim import VictimEstimator

logger = logging.getLogger(__name__)

# Realistic ground-truth confidence by hazard level.
# The detector "knows" the answer but outputs < 1.0 to model sensor noise.
_GT_HAZARD_CONFIDENCE: Dict[HazardLevel, float] = {
    HazardLevel.UNOBSERVED: 0.50,
    HazardLevel.CLEAR: 0.98,
    HazardLevel.LOW: 0.92,
    HazardLevel.MODERATE: 0.85,
    HazardLevel.HIGH: 0.88,
    HazardLevel.CRITICAL: 0.90,
}

# Confidence when hazard level is derived from sensors, not ground truth.
_SENSOR_HAZARD_CONFIDENCE = 0.78


def _zone_id_from_frame(frame: Frame) -> str:
    return f"{frame.pose.x}_{frame.pose.y}_{frame.pose.floor}"


class GroundTruthDetector(AbstractDetector):
    """
    MVP detector that reads simulation ground truth.

    Configured at init with:
      hazard_map — zone_id → known HazardLevel for this scenario
      victim_map — zone_id → detection_probability for victims in this scenario

    For zones in the maps the detector returns scenario-accurate results with
    realistic (sub-1.0) confidence values derived from the scenario parameters.

    For zones NOT in the maps (e.g. in unit tests with empty maps) the detector
    falls back to rule-based sensor analysis so all existing tests continue to
    pass without any map data.

    The simulation internals (Scenario, HazardDefinition, VictimEntity) are
    never exposed through this class's interface; callers pass plain dicts.
    """

    def __init__(
        self,
        hazard_map: Optional[Dict[str, HazardLevel]] = None,
        victim_map: Optional[Dict[str, float]] = None,
    ) -> None:
        self._hazard_map: Dict[str, HazardLevel] = hazard_map or {}
        self._victim_map: Dict[str, float] = victim_map or {}
        self._hazard_classifier = HazardClassifier()
        self._victim_estimator = VictimEstimator()
        self._initialized = False

    @property
    def detector_name(self) -> str:
        return "ground_truth"

    def initialize(self) -> None:
        self._initialized = True
        logger.info(
            "GroundTruthDetector | initialized | %d hazard zones, %d victim zones",
            len(self._hazard_map),
            len(self._victim_map),
        )

    def shutdown(self) -> None:
        self._initialized = False
        logger.info("GroundTruthDetector | shutdown")

    def process(self, frame: Frame) -> DetectionResult:
        zone_id = _zone_id_from_frame(frame)
        env = frame.channels.get("environmental", {})
        has_victim_gt = frame.metadata.get("has_victim_ground_truth", False)

        hazard_signals, hazard_confidence = self._detect_hazard(zone_id, env)
        victim_signals, detected_victims = self._detect_victims(zone_id, env, has_victim_gt)

        detected_objects: List[DetectedObject] = []
        for hs in hazard_signals:
            if hs.hazard_level not in (HazardLevel.CLEAR, HazardLevel.UNOBSERVED):
                detected_objects.append(
                    DetectedObject(
                        object_id=f"hazard-{zone_id}",
                        object_type="HAZARD",
                        zone_id=zone_id,
                        confidence=hs.confidence,
                    )
                )
        for vs in victim_signals:
            detected_objects.append(
                DetectedObject(
                    object_id=vs.victim_id,
                    object_type="VICTIM",
                    zone_id=zone_id,
                    confidence=vs.confidence,
                )
            )

        all_confidences = [hazard_confidence] + [s.confidence for s in victim_signals]
        overall_confidence = sum(all_confidences) / len(all_confidences)

        return DetectionResult(
            frame_id=frame.frame_id,
            zone_id=zone_id,
            detector_name=self.detector_name,
            timestamp=datetime.now(timezone.utc),
            detected_objects=detected_objects,
            victim_signals=victim_signals,
            hazard_signals=hazard_signals,
            confidence_score=round(overall_confidence, 4),
            metadata={"source": "ground_truth", "has_victim_gt": has_victim_gt},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_hazard(
        self, zone_id: str, env: Dict
    ) -> Tuple[List[HazardSignal], float]:
        if zone_id in self._hazard_map:
            level = self._hazard_map[zone_id]
            confidence = _GT_HAZARD_CONFIDENCE.get(level, 0.85)
            return [
                HazardSignal(
                    zone_id=zone_id,
                    hazard_level=level,
                    confidence=confidence,
                    source="ground_truth",
                )
            ], confidence
        # Sensor-based fallback for zones not in the scenario.
        level = self._hazard_classifier.classify(env)
        return [
            HazardSignal(
                zone_id=zone_id,
                hazard_level=level,
                confidence=_SENSOR_HAZARD_CONFIDENCE,
                source="environmental_sensors",
            )
        ], _SENSOR_HAZARD_CONFIDENCE

    def _detect_victims(
        self, zone_id: str, env: Dict, has_victim_gt: bool
    ) -> Tuple[List[VictimSignal], List[DetectedObject]]:
        if zone_id in self._victim_map:
            if not has_victim_gt:
                return [], []
            confidence = self._victim_map[zone_id]
            signal = VictimSignal(
                victim_id=f"victim-{zone_id}",
                zone_id=zone_id,
                confidence=confidence,
                state_estimate="UNKNOWN",
            )
            return [signal], []

        # Sensor-based fallback.
        empty_history = ZoneHistory(zone_id=zone_id)
        victim_probability = self._victim_estimator.estimate(env, empty_history)
        if victim_probability < 0.05:
            return [], []
        signal = VictimSignal(
            victim_id="unknown",
            zone_id=zone_id,
            confidence=round(victim_probability, 4),
            state_estimate="UNKNOWN",
        )
        return [signal], []
