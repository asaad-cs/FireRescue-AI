"""
Mission Manager — central coordinator and single source of truth.

Responsibilities:
  - Owns the current MissionState
  - Receives Frames from the DataSource via on_frame callback
  - Drives each Frame through the Pipeline
  - Updates MissionState from PerceptionResults
  - Notifies the Broadcaster after every state change

State transitions:
    IDLE → INITIALIZING → ACTIVE → (PAUSED ↔ ACTIVE) → ENDED
    Any state → CONNECTION_LOST | ERROR on failure

The manager never exposes internal types (Frame, PerceptionResult) to callers.
All external communication goes through MissionState.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

from backend.config.settings import settings
from backend.models.frame import Frame
from backend.models.mission_state import (
    ConnectionStatus,
    DroneState,
    HazardLevel,
    LatestReadings,
    MissionState,
    MissionStatus,
    ZoneState,
)
from backend.pipeline.pipeline import Pipeline
from backend.utils.logger import logger
from perception.engine import ZoneHistory

# Callback type: called by the manager whenever MissionState changes
StateChangeCallback = Callable[[MissionState], None]


class MissionManager:
    """Coordinates mission lifecycle and frame processing."""

    def __init__(self, pipeline: Pipeline) -> None:
        self._pipeline = pipeline
        self._state_change_callbacks: list[StateChangeCallback] = []
        self._zone_histories: Dict[str, ZoneHistory] = {}
        self._mission_state: Optional[MissionState] = None
        self._start_time: Optional[datetime] = None
        self._total_zone_count: int = 0  # set by caller for accurate explored_pct

    # ------------------------------------------------------------------ #
    # External API                                                         #
    # ------------------------------------------------------------------ #

    def get_state(self) -> Optional[MissionState]:
        return self._mission_state

    def set_total_zone_count(self, count: int) -> None:
        """
        Provide the total number of zones in the building so that
        explored_percentage is computed against the full map, not just
        the zones visited so far.
        """
        self._total_zone_count = count

    def register_state_change(self, callback: StateChangeCallback) -> None:
        self._state_change_callbacks.append(callback)

    def create_mission(self) -> str:
        """Create a new mission and return its mission_id."""
        mission_id = str(uuid.uuid4())
        self._zone_histories = {}
        self._start_time = None
        self._mission_state = MissionState(
            mission_id=mission_id,
            status=MissionStatus.IDLE,
            connection_status=ConnectionStatus.DISCONNECTED,
        )
        logger.info("MissionManager.create_mission | mission_id=%s", mission_id)
        self._notify()
        return mission_id

    def start_mission(self) -> None:
        """Transition the mission from IDLE/PAUSED → ACTIVE."""
        if self._mission_state is None:
            raise RuntimeError("No mission created. Call create_mission() first.")
        if self._mission_state.status not in (MissionStatus.IDLE, MissionStatus.PAUSED):
            raise RuntimeError(
                f"Cannot start mission in status {self._mission_state.status}"
            )
        self._start_time = self._start_time or datetime.now(timezone.utc)
        self._mission_state = self._mission_state.model_copy(
            update={
                "status": MissionStatus.ACTIVE,
                "started_at": self._mission_state.started_at or self._start_time,
                "connection_status": ConnectionStatus.CONNECTED,
            }
        )
        logger.info(
            "MissionManager.start_mission | mission_id=%s",
            self._mission_state.mission_id,
        )
        self._notify()

    def pause_mission(self) -> None:
        self._require_status(MissionStatus.ACTIVE, "pause")
        self._mission_state = self._mission_state.model_copy(
            update={"status": MissionStatus.PAUSED}
        )
        logger.info(
            "MissionManager.pause_mission | mission_id=%s",
            self._mission_state.mission_id,
        )
        self._notify()

    def resume_mission(self) -> None:
        self._require_status(MissionStatus.PAUSED, "resume")
        self._mission_state = self._mission_state.model_copy(
            update={"status": MissionStatus.ACTIVE}
        )
        logger.info(
            "MissionManager.resume_mission | mission_id=%s",
            self._mission_state.mission_id,
        )
        self._notify()

    def end_mission(self) -> None:
        if self._mission_state is None:
            return
        now = datetime.now(timezone.utc)
        elapsed = (
            (now - self._start_time).total_seconds() if self._start_time else 0.0
        )
        self._mission_state = self._mission_state.model_copy(
            update={
                "status": MissionStatus.ENDED,
                "ended_at": now,
                "elapsed_seconds": elapsed,
                "connection_status": ConnectionStatus.DISCONNECTED,
            }
        )
        logger.info(
            "MissionManager.end_mission | mission_id=%s elapsed=%.1fs",
            self._mission_state.mission_id,
            elapsed,
        )
        self._notify()

    # ------------------------------------------------------------------ #
    # Frame intake (called by DataSource via callback)                     #
    # ------------------------------------------------------------------ #

    async def on_frame(self, frame: Frame) -> None:
        """Called by the DataSource for each new Frame produced."""
        if self._mission_state is None:
            logger.warning("on_frame: no active mission — frame dropped")
            return
        if self._mission_state.status != MissionStatus.ACTIVE:
            logger.debug(
                "on_frame: mission not ACTIVE (status=%s) — frame dropped",
                self._mission_state.status,
            )
            return

        # Retrieve or create zone history for the zone this frame maps to.
        # We pass a temporary ZoneHistory; the pipeline will set zone_id as a
        # side effect during enrichment, after which we store it keyed correctly.
        temp_history = ZoneHistory(zone_id="")
        result = self._pipeline.process(frame, temp_history)
        if result is None:
            return  # validation failure; already logged by pipeline

        zone_id = result.zone_id
        if zone_id not in self._zone_histories:
            self._zone_histories[zone_id] = ZoneHistory(zone_id=zone_id)
        self._zone_histories[zone_id].record(
            result.hazard_level, result.victim_probability
        )

        self._update_state_from_result(frame, result)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _update_state_from_result(self, frame: Frame, result) -> None:
        """Merge a PerceptionResult into the current MissionState."""
        now = datetime.now(timezone.utc)
        elapsed = (now - self._start_time).total_seconds() if self._start_time else 0.0

        # Update or create the ZoneState for this zone
        existing_zones = dict(self._mission_state.zone_states)
        zone_id = result.zone_id
        existing = existing_zones.get(zone_id)
        # Prefer existing label, then metadata from frame, then fall back to zone_id
        zone_label = (
            existing.label
            if existing
            else frame.metadata.get("zone_label", zone_id)
        )
        existing_zones[zone_id] = ZoneState(
            zone_id=zone_id,
            label=zone_label,
            grid_x=frame.pose.x,
            grid_y=frame.pose.y,
            hazard_level=result.hazard_level,
            victim_probability=result.victim_probability,
            last_observed_at=now,
        )

        # Merge new alerts from PerceptionResult (if any)
        current_alerts = list(self._mission_state.active_alerts)
        existing_alert_ids = {a.alert_id for a in current_alerts}
        for alert in getattr(result, "new_alerts", []):
            if alert.alert_id not in existing_alert_ids:
                current_alerts.append(alert)
                logger.info(
                    "MissionManager | new alert: [%s] %s — %s",
                    alert.level.value,
                    alert.alert_type.value,
                    alert.message,
                )

        # Update drone state
        drone_state = DroneState(
            drone_id=frame.drone_id,
            x=frame.pose.x,
            y=frame.pose.y,
            floor=frame.pose.floor,
            heading=frame.pose.heading,
            last_seen=now,
        )

        # Extract latest readings from the environmental channel if present
        env = frame.channels.get("environmental", {})
        latest_readings = LatestReadings(
            temperature=env.get("temperature"),
            co_level=env.get("co_level"),
            smoke_density=env.get("smoke_density"),
        )

        # Compute derived summary counters
        victim_signal_count = sum(
            1 for z in existing_zones.values() if z.victim_probability > 0.5
        )
        explored = sum(
            1 for z in existing_zones.values()
            if z.hazard_level != HazardLevel.UNOBSERVED
        )
        # Use total_zone_count if set; otherwise fall back to visited zone count
        denominator = self._total_zone_count if self._total_zone_count > 0 else len(existing_zones)
        explored_pct = (explored / max(denominator, 1)) * 100.0

        self._mission_state = self._mission_state.model_copy(
            update={
                "elapsed_seconds": elapsed,
                "drone_state": drone_state,
                "zone_states": existing_zones,
                "active_alerts": current_alerts,
                "latest_readings": latest_readings,
                "victim_signal_count": victim_signal_count,
                "explored_percentage": round(explored_pct, 1),
                "alert_count": len(current_alerts),
            }
        )
        self._notify()

    def _require_status(self, required: MissionStatus, action: str) -> None:
        if self._mission_state is None or self._mission_state.status != required:
            current = self._mission_state.status if self._mission_state else "None"
            raise RuntimeError(
                f"Cannot {action} mission in status {current}; expected {required}"
            )

    def _notify(self) -> None:
        """Call all registered state-change listeners synchronously."""
        if self._mission_state is None:
            return
        for cb in self._state_change_callbacks:
            try:
                cb(self._mission_state)
            except Exception as exc:  # noqa: BLE001
                logger.error("MissionManager._notify: callback error: %s", exc)
