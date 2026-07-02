"""
MissionState — the complete display contract for the frontend dashboard.

The Mission Manager owns this object and is the only component that writes to it.
Every field maps directly to something the dashboard renders.
The frontend never receives Frames, PerceptionResults, or internal pipeline data.

Sub-models:
  DroneState     — current drone position and last-seen timestamp
  ZoneState      — per-zone hazard level and victim probability
  LatestReadings — most recent environmental sensor values
  MissionState   — root object pushed to the dashboard on every update
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.alert import Alert


class MissionStatus(str, Enum):
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ENDED = "ENDED"
    CONNECTION_LOST = "CONNECTION_LOST"
    ERROR = "ERROR"


class HazardLevel(str, Enum):
    UNOBSERVED = "UNOBSERVED"
    CLEAR = "CLEAR"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"


class DroneState(BaseModel):
    """Last known position and heading of the drone."""

    drone_id: str
    x: int = 0
    y: int = 0
    floor: int = 1
    heading: float = 0.0
    last_seen: Optional[datetime] = None


class ZoneState(BaseModel):
    """Current assessed state of a single building zone."""

    zone_id: str
    label: str
    grid_x: int
    grid_y: int
    hazard_level: HazardLevel = HazardLevel.UNOBSERVED
    victim_probability: float = 0.0       # 0.0 – 1.0
    last_observed_at: Optional[datetime] = None


class LatestReadings(BaseModel):
    """Most recent environmental readings from the drone's current zone."""

    temperature: Optional[float] = None   # Celsius
    co_level: Optional[float] = None      # parts per million
    smoke_density: Optional[float] = None  # 0.0 – 1.0 normalized


class MissionState(BaseModel):
    """
    Complete mission snapshot pushed to the dashboard on every Frame cycle.

    Summary counters (alert_count, victim_signal_count, explored_percentage)
    are derived from the other fields and provided pre-computed so the
    dashboard never needs to aggregate anything.
    """

    mission_id: str
    status: MissionStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    elapsed_seconds: float = 0.0
    drone_state: Optional[DroneState] = None
    zone_states: Dict[str, ZoneState] = Field(default_factory=dict)
    active_alerts: List[Alert] = Field(default_factory=list)
    latest_readings: LatestReadings = Field(default_factory=LatestReadings)
    alert_count: int = 0
    victim_signal_count: int = 0
    explored_percentage: float = 0.0
    connection_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
