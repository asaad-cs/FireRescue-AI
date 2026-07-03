"""
Perception Engine — routes frames through the active detector and converts
DetectionResult → PerceptionResult.

Design contract (ADR-04, updated Phase 5):
  - The engine has NO internal state beyond the registry and active-detector name.
  - Input:  EnrichedFrame + ZoneHistory (read-only context)
  - Output: PerceptionResult  (the only contract the rest of the system sees)

The engine never exposes which detector is active; callers (pipeline, manager)
only see PerceptionResult.  Swapping or adding a detector requires touching only
the detector class and the registry registration in main.py — nothing else changes.

ZoneHistory and PerceptionResult are re-exported from perception.types so callers
that import them from perception.engine continue to work unchanged.
"""
from __future__ import annotations

# Re-export shared types — callers may do: from perception.engine import ZoneHistory, PerceptionResult
from perception.types import ZoneHistory, PerceptionResult  # noqa: F401

from backend.models.mission_state import HazardLevel
from backend.utils.logger import logger
from perception.alerts import AlertGenerator
from perception.registry.registry import DetectorRegistry
from perception.results.detection import DetectionResult


def _max_hazard(signals) -> HazardLevel:
    """Return the most severe HazardLevel found in a list of HazardSignal objects."""
    _order = [
        HazardLevel.UNOBSERVED,
        HazardLevel.CLEAR,
        HazardLevel.LOW,
        HazardLevel.MODERATE,
        HazardLevel.HIGH,
        HazardLevel.CRITICAL,
    ]
    if not signals:
        return HazardLevel.CLEAR
    return max(signals, key=lambda s: _order.index(s.hazard_level)).hazard_level


class PerceptionEngine:
    """
    Routes frames through the active detector and translates DetectionResult
    into PerceptionResult. Alert generation stays here (not in detectors) so
    alert deduplication via ZoneHistory is handled in one place.

    The Mission Manager and Pipeline never know which detector is active.
    """

    def __init__(
        self,
        registry: DetectorRegistry,
        active_detector: str = "ground_truth",
    ) -> None:
        self._registry = registry
        self._active = active_detector
        self._alert_generator = AlertGenerator()

    def process(self, enriched_frame, zone_history: ZoneHistory) -> PerceptionResult:
        """
        Process one enriched frame and return a zone assessment.

        enriched_frame: backend.pipeline.enricher.EnrichedFrame
        zone_history:   ZoneHistory for the zone this frame maps to
        """
        frame = enriched_frame.frame
        zone_id = enriched_frame.zone_id

        try:
            detector = self._registry.get(self._active)
            detection: DetectionResult = detector.process(frame)
        except Exception as exc:
            logger.error(
                "PerceptionEngine | detector '%s' failed for frame=%s zone=%s: %s",
                self._active,
                frame.frame_id,
                zone_id,
                exc,
            )
            return PerceptionResult(
                zone_id=zone_id,
                hazard_level=HazardLevel.UNOBSERVED,
                victim_probability=0.0,
                frame_id=frame.frame_id,
                detector_name=self._active,
            )

        hazard_level = _max_hazard(detection.hazard_signals)
        victim_probability = (
            max(s.confidence for s in detection.victim_signals)
            if detection.victim_signals
            else 0.0
        )

        new_alerts = self._alert_generator.generate(
            mission_id=frame.mission_id,
            zone_id=zone_id,
            hazard_level=hazard_level,
            victim_probability=victim_probability,
            active_alert_ids=zone_history.active_alert_keys,
        )

        for alert in new_alerts:
            zone_history.active_alert_keys.add(f"{zone_id}:{alert.alert_type}")

        logger.debug(
            "PerceptionEngine.process | detector=%s frame=%s zone=%s hazard=%s victim=%.2f alerts=%d",
            self._active,
            frame.frame_id,
            zone_id,
            hazard_level,
            victim_probability,
            len(new_alerts),
        )

        return PerceptionResult(
            zone_id=zone_id,
            hazard_level=hazard_level,
            victim_probability=victim_probability,
            frame_id=detection.frame_id,
            confidence_score=detection.confidence_score,
            timestamp=detection.timestamp,
            detected_objects=detection.detected_objects,
            victim_signals=detection.victim_signals,
            hazard_signals=detection.hazard_signals,
            detector_name=detection.detector_name,
            new_alerts=new_alerts,
            metadata=detection.metadata,
        )
