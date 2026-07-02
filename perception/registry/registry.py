from __future__ import annotations

import logging
from typing import Dict, List

from perception.base.detector import AbstractDetector

logger = logging.getLogger(__name__)

# Detectors that are planned but not yet implemented.
_PLANNED = ["yolo", "rt_detr", "grounding_dino", "thermal", "multimodal"]


class DetectorRegistry:
    """
    Holds live detector instances keyed by name string.
    The MissionManager and Pipeline never interact with this class directly;
    only PerceptionEngine does — keeping detector selection invisible to callers.
    """

    def __init__(self) -> None:
        self._detectors: Dict[str, AbstractDetector] = {}

    def register(self, name: str, detector: AbstractDetector) -> None:
        self._detectors[name] = detector
        logger.info("DetectorRegistry | registered '%s'", name)

    def get(self, name: str) -> AbstractDetector:
        if name not in self._detectors:
            available = list(self._detectors)
            raise KeyError(
                f"Detector '{name}' is not registered. "
                f"Registered: {available}. "
                f"Planned (not yet implemented): {_PLANNED}."
            )
        return self._detectors[name]

    def available(self) -> List[str]:
        """Return names of all currently registered (usable) detectors."""
        return list(self._detectors)

    def planned(self) -> List[str]:
        """Return names of detectors that are recognised but not yet implemented."""
        return list(_PLANNED)
