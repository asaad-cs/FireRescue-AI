"""
Enricher — second stage of the Processing Pipeline.

Takes a validated Frame and attaches derived context that the Perception Engine
will need: primarily a zone_id derived from the drone's grid position.

The zone assignment in Phase 3 uses a simple grid-cell key (x_y_floor).
Future phases may replace this with a spatial lookup against a building map.

EnrichedFrame is a thin wrapper that keeps the original Frame intact
and adds the derived fields alongside it.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.models.frame import Frame
from backend.utils.logger import logger


@dataclass
class EnrichedFrame:
    """A validated Frame with derived zone context attached."""

    frame: Frame
    zone_id: str          # derived from pose; used as dict key in MissionState


class Enricher:
    """Derives zone context from a validated Frame."""

    def enrich(self, frame: Frame) -> EnrichedFrame:
        """Return an EnrichedFrame with zone_id derived from the drone's pose."""
        zone_id = f"{frame.pose.x}_{frame.pose.y}_{frame.pose.floor}"
        logger.debug(
            "Enricher.enrich | frame=%s zone=%s", frame.frame_id, zone_id
        )
        return EnrichedFrame(frame=frame, zone_id=zone_id)
