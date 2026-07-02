"""Tests: MissionRecorder and GET /replay/* endpoints."""
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.main import app
from backend.mission.recorder import MissionRecorder
from backend.models.mission_state import (
    MissionState,
    MissionStatus,
    DroneState,
    LatestReadings,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_state(status: MissionStatus = MissionStatus.ACTIVE, seq: int = 0) -> MissionState:
    """Build a minimal but valid MissionState for recorder tests."""
    return MissionState(
        mission_id=f"test-mission",
        status=status,
        started_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=float(seq),
        drone_state=DroneState(
            drone_id="sim-drone-alpha",
            x=seq % 5,
            y=seq % 4,
            floor=1,
            heading=0.0,
            last_seen=datetime.now(timezone.utc).isoformat(),
        ),
        zone_states={},
        active_alerts=[],
        latest_readings=LatestReadings(
            temperature=22.0 + seq,
            co_level=5.0,
            smoke_density=0.03,
        ),
        alert_count=0,
        victim_signal_count=0,
        explored_percentage=float(seq * 5),
    )


# ── MissionRecorder unit tests ─────────────────────────────────────────────────

class TestMissionRecorderUnit(unittest.TestCase):

    def setUp(self):
        self.recorder = MissionRecorder()

    def test_empty_on_creation(self):
        self.assertEqual(self.recorder.frame_count(), 0)

    def test_get_history_empty_initially(self):
        self.assertEqual(self.recorder.get_history(), [])

    def test_records_single_state(self):
        state = _make_state(seq=0)
        self.recorder.on_state_change(state)
        self.assertEqual(self.recorder.frame_count(), 1)

    def test_records_multiple_states_in_order(self):
        for i in range(5):
            self.recorder.on_state_change(_make_state(seq=i))
        history = self.recorder.get_history()
        self.assertEqual(len(history), 5)
        for i, frame in enumerate(history):
            self.assertAlmostEqual(frame.elapsed_seconds, float(i))

    def test_get_history_returns_list_copy(self):
        self.recorder.on_state_change(_make_state())
        h1 = self.recorder.get_history()
        h2 = self.recorder.get_history()
        self.assertIsNot(h1, h2)

    def test_deep_copy_isolation(self):
        state = _make_state(seq=0)
        self.recorder.on_state_change(state)
        # Mutate the original — should not affect the stored snapshot
        state.elapsed_seconds = 9999.0
        stored = self.recorder.get_history()[0]
        self.assertAlmostEqual(stored.elapsed_seconds, 0.0)

    def test_reset_clears_history(self):
        for i in range(10):
            self.recorder.on_state_change(_make_state(seq=i))
        self.recorder.reset()
        self.assertEqual(self.recorder.frame_count(), 0)
        self.assertEqual(self.recorder.get_history(), [])

    def test_record_after_reset(self):
        self.recorder.on_state_change(_make_state(seq=0))
        self.recorder.reset()
        self.recorder.on_state_change(_make_state(seq=1))
        self.assertEqual(self.recorder.frame_count(), 1)

    def test_frame_count_matches_history_length(self):
        for i in range(7):
            self.recorder.on_state_change(_make_state(seq=i))
        self.assertEqual(self.recorder.frame_count(), len(self.recorder.get_history()))

    def test_records_status_progression(self):
        statuses = [MissionStatus.ACTIVE, MissionStatus.PAUSED, MissionStatus.ENDED]
        for s in statuses:
            self.recorder.on_state_change(_make_state(status=s))
        history = self.recorder.get_history()
        recorded_statuses = [h.status for h in history]
        self.assertEqual(recorded_statuses, statuses)


# ── Replay API endpoint tests ──────────────────────────────────────────────────

class TestReplayFramesEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_replay_frames_returns_200(self):
        response = self.client.get("/replay/frames")
        self.assertEqual(response.status_code, 200)

    def test_replay_frames_has_frames_field(self):
        data = self.client.get("/replay/frames").json()
        self.assertIn("frames", data)
        self.assertIsInstance(data["frames"], list)

    def test_replay_frames_has_count_field(self):
        data = self.client.get("/replay/frames").json()
        self.assertIn("count", data)
        self.assertIsInstance(data["count"], int)

    def test_replay_frames_count_matches_frames_length(self):
        data = self.client.get("/replay/frames").json()
        self.assertEqual(data["count"], len(data["frames"]))

    def test_replay_frames_count_is_non_negative(self):
        data = self.client.get("/replay/frames").json()
        self.assertGreaterEqual(data["count"], 0)

    def test_replay_frame_count_endpoint_returns_200(self):
        response = self.client.get("/replay/frames/count")
        self.assertEqual(response.status_code, 200)

    def test_replay_frame_count_endpoint_has_count_field(self):
        data = self.client.get("/replay/frames/count").json()
        self.assertIn("count", data)

    def test_replay_frame_count_consistent_with_frames(self):
        frames_data = self.client.get("/replay/frames").json()
        count_data = self.client.get("/replay/frames/count").json()
        self.assertEqual(frames_data["count"], count_data["count"])


class TestReplayFramesAfterMission(unittest.TestCase):
    """
    Verify that recorded frames reflect the mission state progression.

    The test client runs the full lifespan which starts a mission and
    runs the simulation tick loop. We let it run briefly, then check
    that frames have been recorded.
    """

    def _client(self) -> TestClient:
        return TestClient(app)

    def test_frames_recorded_after_mission_starts(self):
        with self._client() as client:
            data = client.get("/replay/frames").json()
            # At least the initial ACTIVE state should be recorded
            self.assertGreater(data["count"], 0)

    def test_recorded_frames_are_mission_states(self):
        with self._client() as client:
            data = client.get("/replay/frames").json()
            if data["count"] > 0:
                frame = data["frames"][0]
                self.assertIn("mission_id", frame)
                self.assertIn("status", frame)
                self.assertIn("elapsed_seconds", frame)

    def test_frames_in_chronological_order(self):
        with self._client() as client:
            data = client.get("/replay/frames").json()
            frames = data["frames"]
            if len(frames) < 2:
                return  # not enough frames to check order
            for i in range(len(frames) - 1):
                self.assertLessEqual(
                    frames[i]["elapsed_seconds"],
                    frames[i + 1]["elapsed_seconds"],
                    msg=f"Frame {i} elapsed ({frames[i]['elapsed_seconds']}) "
                        f"> frame {i+1} elapsed ({frames[i+1]['elapsed_seconds']})",
                )

    def test_replay_resets_on_new_mission(self):
        with self._client() as client:
            count_before = client.get("/replay/frames/count").json()["count"]
            client.post("/mission/end")
            client.post("/mission/start")  # restart → recorder.reset()
            count_after = client.get("/replay/frames/count").json()["count"]
            # After reset + new mission, count should be less than original
            # (reset clears history; new mission starts recording fresh)
            self.assertLessEqual(count_after, count_before)


if __name__ == "__main__":
    unittest.main()
