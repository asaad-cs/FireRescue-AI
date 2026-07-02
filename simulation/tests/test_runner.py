"""Tests: SimulationRunner init, Frame generation, scenario, mission completion."""
import asyncio
import unittest

from backend.models.frame import Frame
from simulation.runner import SimulationRunner
from simulation.scenarios import default_scenario
from simulation.sensors import generate_environmental_channel
from simulation.environment import build_warehouse_alpha


def _make_runner(tick_interval: float = 0.0) -> SimulationRunner:
    return SimulationRunner(scenario=default_scenario(), tick_interval=tick_interval)


class TestSimulationRunnerInit(unittest.TestCase):

    def test_runner_creates(self):
        runner = _make_runner()
        self.assertIsNotNone(runner)

    def test_building_initialised(self):
        runner = _make_runner()
        self.assertIsNotNone(runner.building)
        self.assertEqual(runner.building.name, "Warehouse Alpha")

    def test_total_zones_matches_building(self):
        runner = _make_runner()
        self.assertEqual(runner.total_zones(), 20)

    def test_victims_spawned_in_zones(self):
        runner = _make_runner()
        # V-001 in Office A (1,1,1)
        zone_a = runner.building.get_zone_at(1, 1, 1)
        self.assertIn("V-001", zone_a.victim_ids)
        # V-002 in Meeting Room (2,3,1)
        zone_b = runner.building.get_zone_at(2, 3, 1)
        self.assertIn("V-002", zone_b.victim_ids)


class TestFrameGeneration(unittest.TestCase):

    def setUp(self):
        self.runner = _make_runner()
        self.mission_id = "test-mission"

    def test_safe_zone_frame_has_baseline_readings(self):
        zone = self.runner.building.get_zone_at(0, 0, 1)  # Entry — safe
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        env = frame.channels["environmental"]
        self.assertLess(env["temperature"], 30.0)
        self.assertLess(env["co_level"], 20.0)
        self.assertLess(env["smoke_density"], 0.10)

    def test_fire_zone_frame_has_elevated_readings(self):
        zone = self.runner.building.get_zone_at(4, 3, 1)  # Loading Dock — CRITICAL
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        env = frame.channels["environmental"]
        self.assertGreater(env["temperature"], 100.0)
        self.assertGreater(env["co_level"], 500.0)
        self.assertGreater(env["smoke_density"], 0.75)

    def test_victim_zone_has_elevated_co(self):
        zone = self.runner.building.get_zone_at(1, 1, 1)  # Office A — V-001
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        env = frame.channels["environmental"]
        self.assertGreater(env["co_level"], 5.0)  # elevated above baseline

    def test_frame_has_correct_mission_id(self):
        zone = self.runner.building.get_zone_at(0, 0, 1)
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        self.assertEqual(frame.mission_id, self.mission_id)

    def test_frame_has_drone_id(self):
        zone = self.runner.building.get_zone_at(0, 0, 1)
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        self.assertEqual(frame.drone_id, SimulationRunner.DRONE_ID)

    def test_frame_pose_matches_zone(self):
        zone = self.runner.building.get_zone_at(2, 3, 1)
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        self.assertEqual(frame.pose.x, 2)
        self.assertEqual(frame.pose.y, 3)
        self.assertEqual(frame.pose.floor, 1)

    def test_frame_metadata_has_zone_label(self):
        zone = self.runner.building.get_zone_at(0, 0, 1)
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        self.assertIn("zone_label", frame.metadata)
        self.assertEqual(frame.metadata["zone_label"], "Entry Lobby")

    def test_frame_metadata_has_tick(self):
        zone = self.runner.building.get_zone_at(0, 0, 1)
        frame = self.runner._generate_frame(self.mission_id, zone, tick=7)
        self.assertEqual(frame.metadata["tick"], 7)

    def test_frame_environmental_channel_present(self):
        zone = self.runner.building.get_zone_at(0, 0, 1)
        frame = self.runner._generate_frame(self.mission_id, zone, tick=0)
        self.assertIn("environmental", frame.channels)

    def test_frame_is_deterministic(self):
        zone = self.runner.building.get_zone_at(3, 3, 1)  # Storage B — HIGH
        frame1 = self.runner._generate_frame(self.mission_id, zone, tick=0)
        frame2 = self.runner._generate_frame(self.mission_id, zone, tick=0)
        self.assertEqual(
            frame1.channels["environmental"],
            frame2.channels["environmental"],
        )


class TestSimulationLoop(unittest.TestCase):

    def test_run_visits_all_zones(self):
        runner = _make_runner(tick_interval=0.0)
        frames: list[Frame] = []

        async def collect_frame(frame: Frame):
            frames.append(frame)

        asyncio.run(runner.run("m1", collect_frame))
        self.assertEqual(len(frames), 20)

    def test_run_calls_on_complete_after_all_zones(self):
        runner = _make_runner(tick_interval=0.0)
        completed = []

        async def collect_frame(frame: Frame):
            pass

        asyncio.run(runner.run("m1", collect_frame, on_complete=lambda: completed.append(True)))
        self.assertEqual(len(completed), 1)

    def test_run_generates_valid_frames(self):
        runner = _make_runner(tick_interval=0.0)
        frames: list[Frame] = []

        async def collect_frame(frame: Frame):
            frames.append(frame)

        asyncio.run(runner.run("m1", collect_frame))
        for frame in frames:
            self.assertEqual(frame.mission_id, "m1")
            self.assertIn("environmental", frame.channels)
            env = frame.channels["environmental"]
            self.assertIn("temperature", env)
            self.assertIn("co_level", env)
            self.assertIn("smoke_density", env)

    def test_stop_halts_loop(self):
        runner = _make_runner(tick_interval=0.0)
        frames: list[Frame] = []

        async def _run():
            async def collect_frame(frame: Frame):
                frames.append(frame)
                if len(frames) == 3:
                    runner.stop()

            await runner.run("m1", collect_frame)

        asyncio.run(_run())
        # Should have stopped at or near 3 frames
        self.assertLessEqual(len(frames), 4)

    def test_all_zone_ids_in_frames_are_valid(self):
        runner = _make_runner(tick_interval=0.0)
        frames: list[Frame] = []

        async def collect_frame(frame: Frame):
            frames.append(frame)

        asyncio.run(runner.run("m1", collect_frame))
        building_zone_ids = set(runner.building.zones.keys())
        for frame in frames:
            zone_id = f"{frame.pose.x}_{frame.pose.y}_{frame.pose.floor}"
            self.assertIn(zone_id, building_zone_ids)


class TestSensorGeneration(unittest.TestCase):

    def setUp(self):
        self.building = build_warehouse_alpha()

    def test_safe_zone_no_victim(self):
        zone = self.building.get_zone_at(0, 0, 1)
        channel = generate_environmental_channel(zone, None, has_victim=False)
        self.assertAlmostEqual(channel["temperature"], 22.0)
        self.assertAlmostEqual(channel["co_level"], 5.0)
        self.assertAlmostEqual(channel["smoke_density"], 0.03)

    def test_victim_overlay_increases_co(self):
        zone = self.building.get_zone_at(0, 0, 1)
        no_victim = generate_environmental_channel(zone, None, has_victim=False)
        with_victim = generate_environmental_channel(zone, None, has_victim=True)
        self.assertGreater(with_victim["co_level"], no_victim["co_level"])
        self.assertGreater(with_victim["temperature"], no_victim["temperature"])

    def test_hazard_definition_overrides_baseline(self):
        from simulation.scenarios import HazardDefinition
        from backend.models.mission_state import HazardLevel
        zone = self.building.get_zone_at(0, 0, 1)
        hazard = HazardDefinition(
            zone_id="0_0_1",
            fire_intensity=0.9,
            temperature=130.0,
            co_level=600.0,
            smoke_density=0.88,
            hazard_level=HazardLevel.CRITICAL,
        )
        channel = generate_environmental_channel(zone, hazard, has_victim=False)
        self.assertAlmostEqual(channel["temperature"], 130.0)
        self.assertAlmostEqual(channel["co_level"], 600.0)


if __name__ == "__main__":
    unittest.main()
