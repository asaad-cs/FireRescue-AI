from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models.frame import Frame
from perception.results.detection import DetectionResult


class AbstractDetector(ABC):
    """
    Every detector must implement this interface.
    Adding a new detector requires creating exactly one subclass of AbstractDetector.
    The output is always DetectionResult; PerceptionEngine converts it to PerceptionResult.
    """

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """Unique identifier for this detector (e.g. "ground_truth", "yolo")."""

    @abstractmethod
    def initialize(self) -> None:
        """Load model weights, warm up the detector, acquire resources."""

    @abstractmethod
    def process(self, frame: Frame) -> DetectionResult:
        """
        Run detection on a single frame.
        Must never raise — catch internal errors and return a best-effort result.
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Release resources (models, file handles, GPU memory)."""
