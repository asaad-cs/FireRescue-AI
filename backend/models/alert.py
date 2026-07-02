"""
Alert model — a notification generated when a threshold is crossed.

Four severity levels, ordered from lowest to highest urgency:
  INFO      — normal operational event, no action required
  WARNING   — elevated condition, monitor closely
  CRITICAL  — immediate attention needed
  EMERGENCY — life-safety threshold crossed, withdrawal may be required
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertType(str, Enum):
    HAZARD_ELEVATED = "HAZARD_ELEVATED"
    VICTIM_DETECTED = "VICTIM_DETECTED"
    SYSTEM = "SYSTEM"


class Alert(BaseModel):
    """A single alert notification generated during a mission."""

    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str
    zone_id: str
    alert_type: AlertType
    level: AlertLevel
    message: str
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
