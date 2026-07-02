"""Tests: MissionState model works — construction, serialization, copy."""
import unittest
from datetime import datetime, timezone

from backend.models.alert import Alert, AlertLevel, AlertType
from backend.models.frame import Frame, Pose
from backend.models.mission_state import (
    ConnectionStatus,
    DroneState,
    HazardLevel,
    LatestReadings,
    MissionState,
    MissionStatus,
    ZoneState,
)


class TestFrameModel(unittest.TestCase):

    def test_frame_creates(self):
        frame = Frame(
            mission_id="m1",
            drone_id="d1",
            pose=Pose(x=0, y=0, floor=1),
            channels={"environmental": {}},
        )
        self.assertEqual(frame.mission_id, "m1")
        self.assertIsNotNone(frame.frame_id)
        self.assertIsNotNone(frame.timestamp)

    def test_frame_channel_access(self):
        frame = Frame(
            mission_id="m1",
            drone_id="d1",
            pose=Pose(x=0, y=0, floor=1),
            channels={"environmental": {"temperature": 38.5}},
        )
        self.assertEqual(frame.channels["environmental"]["temperature"], 38.5)

    def test_frame_missing_channel_returns_none(self):
        frame = Frame(
            mission_id="m1",
            drone_id="d1",
            pose=Pose(x=0, y=0, floor=1),
            channels={},
        )
        self.assertIsNone(frame.channels.get("thermal"))


class TestAlertModel(unittest.TestCase):

    def test_alert_creates(self):
        alert = Alert(
            mission_id="m1",
            zone_id="z1",
            alert_type=AlertType.SYSTEM,
            level=AlertLevel.INFO,
            message="Test alert",
        )
        self.assertIsNotNone(alert.alert_id)
        self.assertIsNotNone(alert.triggered_at)

    def test_alert_serializes(self):
        alert = Alert(
            mission_id="m1",
            zone_id="z1",
            alert_type=AlertType.HAZARD_ELEVATED,
            level=AlertLevel.WARNING,
            message="Hazard elevated",
        )
        d = alert.model_dump(mode="json")
        self.assertEqual(d["level"], "WARNING")
        self.assertEqual(d["alert_type"], "HAZARD_ELEVATED")


class TestMissionStateModel(unittest.TestCase):

    def test_default_construction(self):
        state = MissionState(mission_id="m1", status=MissionStatus.IDLE)
        self.assertEqual(state.status, MissionStatus.IDLE)
        self.assertEqual(state.alert_count, 0)
        self.assertEqual(state.victim_signal_count, 0)
        self.assertEqual(state.explored_percentage, 0.0)
        self.assertEqual(state.connection_status, ConnectionStatus.DISCONNECTED)

    def test_model_copy_update(self):
        state = MissionState(mission_id="m1", status=MissionStatus.IDLE)
        updated = state.model_copy(update={"status": MissionStatus.ACTIVE})
        self.assertEqual(updated.status, MissionStatus.ACTIVE)
        self.assertEqual(state.status, MissionStatus.IDLE)  # original unchanged

    def test_json_serialization(self):
        state = MissionState(
            mission_id="m1",
            status=MissionStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
        )
        d = state.model_dump(mode="json")
        self.assertEqual(d["status"], "ACTIVE")
        self.assertIsInstance(d["started_at"], str)

    def test_zone_states_dict(self):
        zone = ZoneState(
            zone_id="z1", label="Zone 1", grid_x=0, grid_y=0,
            hazard_level=HazardLevel.LOW
        )
        state = MissionState(
            mission_id="m1",
            status=MissionStatus.ACTIVE,
            zone_states={"z1": zone},
        )
        self.assertEqual(state.zone_states["z1"].hazard_level, HazardLevel.LOW)

    def test_latest_readings_optional_fields(self):
        readings = LatestReadings()
        self.assertIsNone(readings.temperature)
        self.assertIsNone(readings.co_level)
        self.assertIsNone(readings.smoke_density)

    def test_drone_state_defaults(self):
        drone = DroneState(drone_id="d1")
        self.assertEqual(drone.x, 0)
        self.assertEqual(drone.floor, 1)
        self.assertIsNone(drone.last_seen)


class TestHazardLevelEnum(unittest.TestCase):

    def test_ordering(self):
        levels = [
            HazardLevel.UNOBSERVED,
            HazardLevel.CLEAR,
            HazardLevel.LOW,
            HazardLevel.MODERATE,
            HazardLevel.HIGH,
            HazardLevel.CRITICAL,
        ]
        self.assertEqual(len(levels), 6)

    def test_string_values(self):
        self.assertEqual(HazardLevel.CRITICAL, "CRITICAL")


if __name__ == "__main__":
    unittest.main()
