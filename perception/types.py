"""
Shared perception types — imported by all perception sub-modules.

Keeping ZoneHistory and PerceptionResult here (rather than in engine.py)
breaks the circular import that would arise if victim.py needed to import
ZoneHistory from engine.py while engine.py imports VictimEstimator from
victim.py.

External callers (pipeline.py, manager.py, tests) may import these types
from either perception.types or perception.engine (engine.py re-exports them).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from backend.models.mission_state import HazardLevel


@dataclass
class ZoneHistory:
    """
    Per-zone observation history passed to the engine on every call.
    Owned and updated by the Mission Manager after each PerceptionResult.
    """

    zone_id: str
    hazard_levels: List[HazardLevel] = field(default_factory=list)
    victim_probabilities: List[float] = field(default_factory=list)
    last_observed_at: Optional[datetime] = None

    # Alert suppression: keys are "zone_id:AlertType" strings
    active_alert_keys: Set[str] = field(default_factory=set)

    def record(self, hazard_level: HazardLevel, victim_probability: float) -> None:
        self.hazard_levels.append(hazard_level)
        self.victim_probabilities.append(victim_probability)
        self.last_observed_at = datetime.now(timezone.utc)


@dataclass
class PerceptionResult:
    """
    The unified output of the perception framework — the only contract between
    perception and the rest of the system (pipeline, mission manager, API).

    All fields added in Phase 5 have defaults so every existing caller continues
    to work without modification.
    """

    zone_id: str
    hazard_level: HazardLevel
    victim_probability: float          # 0.0 – 1.0

    # Phase 5 enrichment — defaults preserve backward compatibility
    frame_id: str = ""
    confidence_score: float = 0.0      # overall detection confidence 0.0 – 1.0
    timestamp: Optional[datetime] = None
    detected_objects: List = field(default_factory=list)  # List[DetectedObject]
    victim_signals: List = field(default_factory=list)    # List[VictimSignal]
    hazard_signals: List = field(default_factory=list)    # List[HazardSignal]
    detector_name: str = "unknown"

    new_alerts: List = field(default_factory=list)  # List[Alert]
    metadata: Dict = field(default_factory=dict)
