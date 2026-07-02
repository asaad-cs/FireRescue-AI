"""
Frame model — the unit that crosses the Data Source Interface.

A Frame is a synchronized sensor snapshot from the drone at a point in time.
It carries a pose (position and orientation) and a channels dictionary.

The channels dictionary is the extensibility point:
  - MVP:    channels["environmental"] = {temperature, co_level, smoke_density}
  - Future: channels["thermal"], channels["rgb"], channels["lidar"]

Adding a new sensor modality means adding a new key to channels.
Nothing else in the system changes.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class Pose:
    """Drone position in the building grid."""

    x: int
    y: int
    floor: int
    heading: float = 0.0  # Degrees; reserved for future spatial alignment


@dataclass
class Frame:
    """Synchronized sensor snapshot from the drone."""

    mission_id: str
    drone_id: str
    pose: Pose
    channels: Dict[str, Any]          # Open dict — any modality can be added
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
