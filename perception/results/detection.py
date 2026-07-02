from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from backend.models.mission_state import HazardLevel


@dataclass
class DetectedObject:
    object_id: str
    object_type: str  # "VICTIM", "HAZARD", "SMOKE", "FIRE"
    zone_id: str
    confidence: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class VictimSignal:
    victim_id: str  # ground truth ID or "unknown" for ML detectors
    zone_id: str
    confidence: float
    state_estimate: str = "UNKNOWN"  # "CONSCIOUS", "UNCONSCIOUS", "UNKNOWN"


@dataclass
class HazardSignal:
    zone_id: str
    hazard_level: HazardLevel
    confidence: float
    source: str = "unknown"  # "temperature", "co", "smoke", "thermal", "ground_truth"


@dataclass
class DetectionResult:
    """
    Native output of every detector.
    The PerceptionEngine converts this to PerceptionResult and attaches alerts.
    """
    frame_id: str
    zone_id: str
    detector_name: str
    timestamp: datetime
    detected_objects: List[DetectedObject] = field(default_factory=list)
    victim_signals: List[VictimSignal] = field(default_factory=list)
    hazard_signals: List[HazardSignal] = field(default_factory=list)
    confidence_score: float = 0.0
    metadata: Dict = field(default_factory=dict)
