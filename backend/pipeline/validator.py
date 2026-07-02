"""
Validator — first stage of the Processing Pipeline.

Checks that an incoming Frame is structurally sound before it travels further.
Raises ValueError for any frame that fails validation so the pipeline can
safely discard it without affecting mission state.

Phase 3 rules (minimal — enough to catch obviously malformed frames):
  - mission_id must be a non-empty string
  - drone_id must be a non-empty string
  - channels must be a dict (may be empty at this stage)
  - pose x, y must be integers
"""
from __future__ import annotations

from backend.models.frame import Frame
from backend.utils.logger import logger


class Validator:
    """Validates a raw Frame before it enters the enrichment stage."""

    def validate(self, frame: Frame) -> Frame:
        """Return the frame unchanged if valid; raise ValueError if not."""
        if not isinstance(frame.mission_id, str) or not frame.mission_id:
            raise ValueError(f"Frame {frame.frame_id}: missing mission_id")

        if not isinstance(frame.drone_id, str) or not frame.drone_id:
            raise ValueError(f"Frame {frame.frame_id}: missing drone_id")

        if not isinstance(frame.channels, dict):
            raise ValueError(f"Frame {frame.frame_id}: channels must be a dict")

        if not isinstance(frame.pose.x, int) or not isinstance(frame.pose.y, int):
            raise ValueError(f"Frame {frame.frame_id}: pose x/y must be integers")

        logger.debug("Validator.validate | frame=%s OK", frame.frame_id)
        return frame
