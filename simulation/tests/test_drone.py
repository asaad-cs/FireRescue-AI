"""Tests: Drone movement, BFS exploration order, completion detection."""
import unittest

from simulation.drone import Drone
from simulation.environment import build_warehouse_alpha


class TestDroneInitialisation(unittest.TestCase):

    def setUp(self):
        self.building = build_warehouse_alpha()
        self.drone = Drone(
            drone_id="test-drone",
            building=self.building,
            start_zone_id="0_0_1",
        )

    def test_drone_starts_with_full_battery(self):
        self.assertEqual(self.drone.battery_level, 100.0)

    def test_drone_starts_connected(self):
        self.assertEqual(self.drone.connection_status, "CONNECTED")

    def test_drone_has_no_current_zone_before_first_move(self):
        self.assertIsNone(self.drone.current_zone_id)

    def test_drone_has_empty_movement_history(self):
        self.assertEqual(self.drone.movement_history, [])

    def test_zones_visited_is_zero_before_first_move(self):
        self.assertEqual(self.drone.zones_visited, 0)


class TestDroneBFSMovement(unittest.TestCase):

    def setUp(self):
        self.building = build_warehouse_alpha()
        self.drone = Drone(
            drone_id="test-drone",
            building=self.building,
            start_zone_id="0_0_1",
        )

    def test_first_move_visits_start_zone(self):
        zone = self.drone.next_zone()
        self.assertIsNotNone(zone)
        self.assertEqual(zone.zone_id, "0_0_1")

    def test_first_move_marks_zone_as_visited(self):
        zone = self.drone.next_zone()
        self.assertTrue(zone.visited)

    def test_current_zone_id_set_after_move(self):
        zone = self.drone.next_zone()
        self.assertEqual(self.drone.current_zone_id, zone.zone_id)

    def test_movement_history_grows_per_tick(self):
        for _ in range(5):
            self.drone.next_zone()
        self.assertEqual(len(self.drone.movement_history), 5)

    def test_no_zone_visited_twice(self):
        visited = []
        while True:
            zone = self.drone.next_zone()
            if zone is None:
                break
            visited.append(zone.zone_id)
        self.assertEqual(len(visited), len(set(visited)))

    def test_all_zones_visited_on_completion(self):
        visited = set()
        while True:
            zone = self.drone.next_zone()
            if zone is None:
                break
            visited.add(zone.zone_id)
        self.assertEqual(visited, set(self.building.zones.keys()))

    def test_returns_none_after_all_zones_explored(self):
        # Exhaust all zones
        while True:
            zone = self.drone.next_zone()
            if zone is None:
                break
        # Next call should also return None
        self.assertIsNone(self.drone.next_zone())

    def test_zones_visited_count_matches_building_size(self):
        while True:
            zone = self.drone.next_zone()
            if zone is None:
                break
        self.assertEqual(self.drone.zones_visited, self.building.total_zones())

    def test_bfs_visits_start_zone_neighbors_early(self):
        """Start zone's direct neighbors should be visited before distant zones."""
        visited_order = []
        while True:
            zone = self.drone.next_zone()
            if zone is None:
                break
            visited_order.append(zone.zone_id)

        start_zone = self.building.get_zone_at(0, 0, 1)
        neighbor_ids = set(start_zone.neighbor_ids)

        # Find positions of start zone and its neighbors in BFS order
        start_pos = visited_order.index("0_0_1")
        for neighbor_id in neighbor_ids:
            neighbor_pos = visited_order.index(neighbor_id)
            # All direct neighbors should appear before zones at distance 2+
            self.assertGreater(neighbor_pos, start_pos)

    def test_all_visited_zones_marked_in_building(self):
        while True:
            zone = self.drone.next_zone()
            if zone is None:
                break
        # Every zone in the building should be marked visited
        for zone in self.building.zones.values():
            self.assertTrue(zone.visited, f"Zone {zone.zone_id} not marked visited")


class TestDroneFromDifferentStart(unittest.TestCase):

    def test_bfs_from_center_visits_all_zones(self):
        building = build_warehouse_alpha()
        drone = Drone(
            drone_id="d1",
            building=building,
            start_zone_id="2_2_1",  # center zone
        )
        visited = set()
        while True:
            zone = drone.next_zone()
            if zone is None:
                break
            visited.add(zone.zone_id)
        self.assertEqual(len(visited), 20)


if __name__ == "__main__":
    unittest.main()
