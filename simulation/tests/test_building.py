"""Tests: Building creation, zone graph, adjacency, BFS reachability."""
import unittest

from simulation.environment import (
    Building,
    Zone,
    ZoneType,
    build_warehouse_alpha,
)


class TestBuildingCreation(unittest.TestCase):

    def setUp(self):
        self.building = build_warehouse_alpha()

    def test_building_has_correct_name(self):
        self.assertEqual(self.building.name, "Warehouse Alpha")

    def test_building_has_one_floor(self):
        self.assertEqual(len(self.building.floors), 1)
        self.assertIn(1, self.building.floors)

    def test_building_has_twenty_zones(self):
        self.assertEqual(len(self.building.zones), 20)

    def test_all_zones_have_valid_ids(self):
        for zone_id, zone in self.building.zones.items():
            self.assertEqual(zone_id, f"{zone.x}_{zone.y}_{zone.floor}")

    def test_zone_ids_match_enricher_format(self):
        # The enricher produces zone_id = f"{x}_{y}_{floor}"
        # Every building zone must follow this format
        for zone_id in self.building.zones:
            parts = zone_id.split("_")
            self.assertEqual(len(parts), 3)
            x, y, floor = int(parts[0]), int(parts[1]), int(parts[2])
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertGreaterEqual(floor, 1)


class TestZoneGraph(unittest.TestCase):

    def setUp(self):
        self.building = build_warehouse_alpha()

    def test_interior_zone_has_four_neighbors(self):
        # (2,2) is surrounded on all sides
        center = self.building.get_zone_at(2, 2, 1)
        self.assertIsNotNone(center)
        self.assertEqual(len(center.neighbor_ids), 4)

    def test_corner_zone_has_two_neighbors(self):
        # (0,0) is a corner
        corner = self.building.get_zone_at(0, 0, 1)
        self.assertIsNotNone(corner)
        self.assertEqual(len(corner.neighbor_ids), 2)

    def test_edge_zone_has_three_neighbors(self):
        # (1,0) is on the top edge (not corner)
        edge = self.building.get_zone_at(1, 0, 1)
        self.assertIsNotNone(edge)
        self.assertEqual(len(edge.neighbor_ids), 3)

    def test_neighbors_are_orthogonal_only(self):
        zone = self.building.get_zone_at(2, 2, 1)
        neighbors = self.building.get_neighbors(zone.zone_id)
        for n in neighbors:
            dx = abs(n.x - zone.x)
            dy = abs(n.y - zone.y)
            # Only one of dx, dy should be 1 (orthogonal movement)
            self.assertEqual(dx + dy, 1)

    def test_get_zone_at_returns_none_for_out_of_bounds(self):
        self.assertIsNone(self.building.get_zone_at(99, 99, 1))
        self.assertIsNone(self.building.get_zone_at(-1, 0, 1))

    def test_reachable_from_start_covers_all_zones(self):
        reachable = self.building.reachable_from("0_0_1")
        self.assertEqual(len(reachable), 20)  # all zones reachable

    def test_reachable_returns_set_of_zone_ids(self):
        reachable = self.building.reachable_from("0_0_1")
        for zone_id in reachable:
            self.assertIn(zone_id, self.building.zones)

    def test_adjacency_is_symmetric(self):
        for zone in self.building.zones.values():
            for neighbor_id in zone.neighbor_ids:
                neighbor = self.building.zones[neighbor_id]
                self.assertIn(zone.zone_id, neighbor.neighbor_ids,
                              msg=f"{zone.zone_id} is neighbor of {neighbor_id} but not vice versa")


class TestZoneProperties(unittest.TestCase):

    def setUp(self):
        self.building = build_warehouse_alpha()

    def test_entry_zone_is_entry_type(self):
        entry = self.building.get_zone_at(0, 0, 1)
        self.assertEqual(entry.zone_type, ZoneType.ENTRY)

    def test_stairwell_zone_type(self):
        stairwell = self.building.get_zone_at(0, 2, 1)
        self.assertEqual(stairwell.zone_type, ZoneType.STAIRWELL)

    def test_zones_start_unvisited(self):
        for zone in self.building.zones.values():
            self.assertFalse(zone.visited)

    def test_zones_start_with_no_victims(self):
        for zone in self.building.zones.values():
            self.assertEqual(zone.victim_ids, [])

    def test_total_zones(self):
        self.assertEqual(self.building.total_zones(), 20)


if __name__ == "__main__":
    unittest.main()
