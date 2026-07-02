"""
Processing Pipeline — orchestrates the Validate → Enrich → Perceive stages.

The pipeline is the only component that knows the stage order.
Each stage is injected at construction time so tests can swap them out.

Usage:
    result = pipeline.process(frame, zone_history)
    # result is a PerceptionResult, or None if validation failed
"""
from __future__ import annotations

from typing import Optional

from backend.models.frame import Frame
from backend.pipeline.enricher import Enricher
from backend.pipeline.validator import Validator
from backend.utils.logger import logger
from perception.engine import PerceptionEngine, PerceptionResult, ZoneHistory


class Pipeline:
    """Three-stage frame processing pipeline: Validate → Enrich → Perceive."""

    def __init__(
        self,
        validator: Validator,
        enricher: Enricher,
        engine: PerceptionEngine,
    ) -> None:
        self._validator = validator
        self._enricher = enricher
        self._engine = engine

    def process(
        self, frame: Frame, zone_history: ZoneHistory
    ) -> Optional[PerceptionResult]:
        """
        Run the frame through all three stages.
        Returns None (and logs a warning) if validation fails.
        """
        try:
            validated = self._validator.validate(frame)
        except ValueError as exc:
            logger.warning("Pipeline.process | validation failed: %s", exc)
            return None

        enriched = self._enricher.enrich(validated)
        zone_history.zone_id = enriched.zone_id  # let caller sync the key

        result = self._engine.process(enriched, zone_history)
        logger.debug(
            "Pipeline.process | frame=%s → zone=%s hazard=%s victim=%.2f",
            frame.frame_id,
            result.zone_id,
            result.hazard_level,
            result.victim_probability,
        )
        return result
