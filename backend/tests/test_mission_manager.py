"""Tests: MissionManager initializes, state transitions, on_frame integration."""
import asyncio
import unittest

from backend.mission.manager import MissionManager
from backend.models.frame import Frame, Pose
from backend.models.mission_state import MissionStatus
from backend.pipeline.enricher import Enricher
from backend.pipeline.pipeline import Pipeline
from backend.pipeline.validator import Validator
from perception.detectors.ground_truth import GroundTruthDetector
from perception.engine import PerceptionEngine
from perception.registry.registry import DetectorRegistry


def _make_engine() -> PerceptionEngine:
    detector = GroundTruthDetector()
    detector.initialize()
    registry = DetectorRegistry()
    registry.register("ground_truth", detector)
    return PerceptionEngine(registry=registry, active_detector="ground_truth")


def _make_manager() -> MissionManager:
    pipeline = Pipeline(
        validator=Validator(),
        enricher=Enricher(),
        engine=_make_engine(),
    )
    return MissionManager(pipeline=pipeline)


def _make_frame(mission_id: str) -> Frame:
    return Frame(
        mission_id=mission_id,
        drone_id="drone-1",
        pose=Pose(x=2, y=3, floor=1),
        channels={"environmental": {"temperature": 45.0, "co_level": 12.0, "smoke_density": 0.1}},
    )


class TestMissionManagerInit(unittest.TestCase):

    def test_creates_with_idle_status(self):
        manager = _make_manager()
        mission_id = manager.create_mission()
        state = manager.get_state()
        self.assertIsNotNone(state)
        self.assertEqual(state.status, MissionStatus.IDLE)
        self.assertEqual(state.mission_id, mission_id)

    def test_no_state_before_create(self):
        pipeline = Pipeline(Validator(), Enricher(), _make_engine())
        manager = MissionManager(pipeline=pipeline)
        self.assertIsNone(manager.get_state())


class TestMissionManagerTransitions(unittest.TestCase):

    def setUp(self):
        self.manager = _make_manager()
        self.manager.create_mission()

    def test_start_transitions_to_active(self):
        self.manager.start_mission()
        self.assertEqual(self.manager.get_state().status, MissionStatus.ACTIVE)

    def test_pause_from_active(self):
        self.manager.start_mission()
        self.manager.pause_mission()
        self.assertEqual(self.manager.get_state().status, MissionStatus.PAUSED)

    def test_resume_from_paused(self):
        self.manager.start_mission()
        self.manager.pause_mission()
        self.manager.resume_mission()
        self.assertEqual(self.manager.get_state().status, MissionStatus.ACTIVE)

    def test_end_mission(self):
        self.manager.start_mission()
        self.manager.end_mission()
        self.assertEqual(self.manager.get_state().status, MissionStatus.ENDED)

    def test_cannot_start_active_mission(self):
        self.manager.start_mission()
        with self.assertRaises(RuntimeError):
            self.manager.start_mission()

    def test_state_change_callback_fires(self):
        received = []
        self.manager.register_state_change(lambda s: received.append(s.status))
        self.manager.start_mission()
        self.assertIn(MissionStatus.ACTIVE, received)


class TestMissionManagerOnFrame(unittest.TestCase):

    def setUp(self):
        self.manager = _make_manager()
        mission_id = self.manager.create_mission()
        self.mission_id = mission_id
        self.manager.start_mission()

    def test_on_frame_updates_drone_state(self):
        frame = _make_frame(self.mission_id)
        asyncio.run(self.manager.on_frame(frame))
        state = self.manager.get_state()
        self.assertIsNotNone(state.drone_state)
        self.assertEqual(state.drone_state.drone_id, "drone-1")

    def test_on_frame_updates_zone_states(self):
        frame = _make_frame(self.mission_id)
        asyncio.run(self.manager.on_frame(frame))
        state = self.manager.get_state()
        self.assertGreater(len(state.zone_states), 0)

    def test_on_frame_updates_latest_readings(self):
        frame = _make_frame(self.mission_id)
        asyncio.run(self.manager.on_frame(frame))
        state = self.manager.get_state()
        self.assertEqual(state.latest_readings.temperature, 45.0)

    def test_on_frame_dropped_when_paused(self):
        self.manager.pause_mission()
        frame = _make_frame(self.mission_id)
        asyncio.run(self.manager.on_frame(frame))
        state = self.manager.get_state()
        self.assertIsNone(state.drone_state)


if __name__ == "__main__":
    unittest.main()
