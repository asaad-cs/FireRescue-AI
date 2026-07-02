"""
Tests: all registered scenarios load and execute correctly.

Verifies for each scenario:
  - Scenario object can be created from its factory
  - Building is fully connected (BFS from start zone reaches every zone)
  - All victim zone_ids exist in the building
  - All hazard zone_ids exist in the building
  - SimulationRunner can be created with the scenario
  - SimulationRunner visits every zone exactly once in a complete run
"""
import asyncio
import unittest

from backend.models.frame import Frame
from simulation.runner import SimulationRunner
from simulation.scenario_registry import (
    SCENARIO_REGISTRY,
    DEFAULT_SCENARIO_KEY,
    get_scenario,
    list_scenarios,
)
from simulation.scenarios import (
    default_scenario,
    office_building_scenario,
    hospital_scenario,
    shopping_mall_scenario,
    school_scenario,
)
from simulation.environment import (
    build_warehouse_alpha,
    build_office_building,
    build_hospital,
    build_shopping_mall,
    build_school,
)


# ── Shared helpers ─────────────────────────────────────────────────────────────

def run_full_mission(scenario_factory):
    """Run a complete simulation and return the list of frames produced."""
    runner = SimulationRunner(scenario=scenario_factory(), tick_interval=0.0)
    frames: list[Frame] = []

    async def collect(frame: Frame):
        frames.append(frame)

    asyncio.run(runner.run("test-mission", collect))
    return runner, frames


# ── Registry tests ─────────────────────────────────────────────────────────────

class TestScenarioRegistry(unittest.TestCase):

    def test_registry_has_five_entries(self):
        self.assertEqual(len(SCENARIO_REGISTRY), 5)

    def test_registry_contains_all_keys(self):
        expected = {
            "warehouse_alpha", "office_building", "hospital",
            "shopping_mall", "school",
        }
        self.assertEqual(set(SCENARIO_REGISTRY), expected)

    def test_default_key_is_warehouse_alpha(self):
        self.assertEqual(DEFAULT_SCENARIO_KEY, "warehouse_alpha")

    def test_get_scenario_returns_scenario(self):
        for key in SCENARIO_REGISTRY:
            with self.subTest(key=key):
                scenario = get_scenario(key)
                self.assertIsNotNone(scenario)
                self.assertTrue(len(scenario.name) > 0)

    def test_get_scenario_raises_for_unknown_key(self):
        with self.assertRaises(KeyError):
            get_scenario("nonexistent_scenario")

    def test_get_scenario_returns_independent_instances(self):
        a = get_scenario("warehouse_alpha")
        b = get_scenario("warehouse_alpha")
        self.assertIsNot(a, b)

    def test_list_scenarios_returns_five_items(self):
        items = list_scenarios()
        self.assertEqual(len(items), 5)

    def test_list_scenarios_items_have_required_fields(self):
        for item in list_scenarios():
            with self.subTest(key=item.get("key")):
                self.assertIn("key", item)
                self.assertIn("display_name", item)
                self.assertIn("description", item)
                self.assertIn("zone_count", item)

    def test_list_scenarios_zone_counts_match_buildings(self):
        expected_counts = {
            "warehouse_alpha": 20,
            "office_building": 12,
            "hospital":        16,
            "shopping_mall":   15,
            "school":          16,
        }
        for item in list_scenarios():
            key = item["key"]
            self.assertEqual(
                item["zone_count"],
                expected_counts[key],
                msg=f"{key}: metadata zone_count mismatch",
            )


# ── Per-building factory tests ─────────────────────────────────────────────────

class TestBuildingFactories(unittest.TestCase):

    def _assert_building_valid(self, building, expected_zone_count: int, start_zone_id: str):
        self.assertEqual(len(building.zones), expected_zone_count)
        reachable = building.reachable_from(start_zone_id)
        self.assertEqual(
            len(reachable),
            expected_zone_count,
            msg=f"Not all zones reachable from {start_zone_id}: "
                f"{expected_zone_count - len(reachable)} unreachable",
        )
        for zone_id, zone in building.zones.items():
            self.assertEqual(zone_id, f"{zone.x}_{zone.y}_{zone.floor}")

    def test_warehouse_alpha_has_20_connected_zones(self):
        self._assert_building_valid(build_warehouse_alpha(), 20, "0_0_1")

    def test_office_building_has_12_connected_zones(self):
        self._assert_building_valid(build_office_building(), 12, "0_0_1")

    def test_hospital_has_16_connected_zones(self):
        self._assert_building_valid(build_hospital(), 16, "0_0_1")

    def test_shopping_mall_has_15_connected_zones(self):
        self._assert_building_valid(build_shopping_mall(), 15, "2_0_1")

    def test_school_has_16_connected_zones(self):
        self._assert_building_valid(build_school(), 16, "0_0_1")

    def test_adjacency_is_symmetric_all_buildings(self):
        factories = [
            build_warehouse_alpha, build_office_building,
            build_hospital, build_shopping_mall, build_school,
        ]
        for factory in factories:
            building = factory()
            with self.subTest(building=building.name):
                for zone in building.zones.values():
                    for nid in zone.neighbor_ids:
                        neighbor = building.zones[nid]
                        self.assertIn(
                            zone.zone_id, neighbor.neighbor_ids,
                            msg=f"{building.name}: adjacency not symmetric between "
                                f"{zone.zone_id} and {nid}",
                        )


# ── Per-scenario integrity tests ───────────────────────────────────────────────

class TestScenarioIntegrity(unittest.TestCase):
    """
    Verify that every scenario's victim and hazard zone_ids exist
    in the building the scenario produces.
    """

    def _assert_scenario_valid(self, scenario):
        building = scenario.building_factory()

        # Victims must reference real zones
        for victim in scenario.victims:
            self.assertIn(
                victim.zone_id, building.zones,
                msg=f"{scenario.name}: victim {victim.victim_id} "
                    f"references non-existent zone {victim.zone_id}",
            )

        # Hazard definitions must reference real zones
        for zone_id in scenario.hazard_zones:
            self.assertIn(
                zone_id, building.zones,
                msg=f"{scenario.name}: hazard_zone {zone_id} "
                    f"does not exist in building",
            )

        # Start zone must exist
        self.assertIn(
            scenario.start_zone_id, building.zones,
            msg=f"{scenario.name}: start_zone_id {scenario.start_zone_id} not in building",
        )

    def test_warehouse_alpha_scenario_is_valid(self):
        self._assert_scenario_valid(default_scenario())

    def test_office_building_scenario_is_valid(self):
        self._assert_scenario_valid(office_building_scenario())

    def test_hospital_scenario_is_valid(self):
        self._assert_scenario_valid(hospital_scenario())

    def test_shopping_mall_scenario_is_valid(self):
        self._assert_scenario_valid(shopping_mall_scenario())

    def test_school_scenario_is_valid(self):
        self._assert_scenario_valid(school_scenario())


# ── End-to-end runner tests for all scenarios ──────────────────────────────────

class TestRunnerAllScenarios(unittest.TestCase):
    """
    For every registered scenario: run a complete simulation and verify
    the runner visits every zone exactly once.
    """

    def _run_and_assert_complete(self, key: str, expected_zone_count: int):
        runner, frames = run_full_mission(SCENARIO_REGISTRY[key])
        self.assertEqual(
            len(frames),
            expected_zone_count,
            msg=f"Scenario '{key}': expected {expected_zone_count} frames, "
                f"got {len(frames)}",
        )
        # Every frame zone_id must be valid in the building
        zone_ids_visited = set()
        for frame in frames:
            zid = f"{frame.pose.x}_{frame.pose.y}_{frame.pose.floor}"
            self.assertIn(
                zid, runner.building.zones,
                msg=f"Scenario '{key}': frame zone_id {zid} not in building",
            )
            zone_ids_visited.add(zid)

        # Every zone must be visited exactly once
        self.assertEqual(
            len(zone_ids_visited),
            expected_zone_count,
            msg=f"Scenario '{key}': {expected_zone_count - len(zone_ids_visited)} "
                f"zones not visited",
        )

    def test_warehouse_alpha_visits_all_20_zones(self):
        self._run_and_assert_complete("warehouse_alpha", 20)

    def test_office_building_visits_all_12_zones(self):
        self._run_and_assert_complete("office_building", 12)

    def test_hospital_visits_all_16_zones(self):
        self._run_and_assert_complete("hospital", 16)

    def test_shopping_mall_visits_all_15_zones(self):
        self._run_and_assert_complete("shopping_mall", 15)

    def test_school_visits_all_16_zones(self):
        self._run_and_assert_complete("school", 16)

    def test_all_scenarios_generate_valid_frames(self):
        for key in SCENARIO_REGISTRY:
            with self.subTest(scenario=key):
                _, frames = run_full_mission(SCENARIO_REGISTRY[key])
                for frame in frames:
                    self.assertIn("environmental", frame.channels)
                    env = frame.channels["environmental"]
                    self.assertIn("temperature", env)
                    self.assertIn("co_level", env)
                    self.assertIn("smoke_density", env)

    def test_all_scenarios_call_on_complete(self):
        for key in SCENARIO_REGISTRY:
            with self.subTest(scenario=key):
                runner = SimulationRunner(
                    scenario=SCENARIO_REGISTRY[key](), tick_interval=0.0
                )
                completed = []

                async def collect(frame):
                    pass

                asyncio.run(
                    runner.run("m1", collect, on_complete=lambda: completed.append(True))
                )
                self.assertEqual(len(completed), 1)

    def test_hazard_zones_produce_elevated_readings(self):
        """Critical zones in every scenario must have temperature > 100°C."""
        for key in SCENARIO_REGISTRY:
            scenario = get_scenario(key)
            runner = SimulationRunner(scenario=scenario, tick_interval=0.0)
            critical_zones = [
                zid for zid, h in scenario.hazard_zones.items()
                if h.hazard_level.value == "CRITICAL"
            ]
            for zid in critical_zones:
                zone = runner.building.zones[zid]
                frame = runner._generate_frame("test", zone, tick=0)
                env = frame.channels["environmental"]
                with self.subTest(scenario=key, zone=zid):
                    self.assertGreater(
                        env["temperature"], 100.0,
                        msg=f"Scenario '{key}', zone {zid}: "
                            f"CRITICAL zone temp should exceed 100°C",
                    )


if __name__ == "__main__":
    unittest.main()
