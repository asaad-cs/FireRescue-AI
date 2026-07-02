"""
Digital Twin — Building Environment.

Represents the physical environment as a graph of Zones.
This is the ground-truth model of the building; the simulation reads it,
the drone traverses it, and sensors derive their values from it.

Hierarchy:
    Building → Floor → Zone

The building graph (zones + adjacency) is the data structure the drone's
BFS explorer navigates. Zones are nodes; shared walls that can be passed
through are edges (neighbor_ids).

No physics. No graphics. Pure Python data model.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class ZoneType(str, Enum):
    ROOM = "ROOM"
    HALLWAY = "HALLWAY"
    STAIRWELL = "STAIRWELL"
    ENTRY = "ENTRY"


@dataclass
class Zone:
    """
    A single navigable cell in the building grid.

    zone_id format: "{x}_{y}_{floor}" — matches the enricher's zone_id derivation
    so Frames from this zone resolve to the correct zone_id in the pipeline.
    """

    zone_id: str          # e.g., "2_3_1"
    label: str            # human-readable, e.g., "Office B"
    x: int
    y: int
    floor: int
    zone_type: ZoneType
    neighbor_ids: List[str] = field(default_factory=list)

    # Ground-truth state (updated by scenario, not derived from perception)
    visited: bool = False
    victim_ids: List[str] = field(default_factory=list)


@dataclass
class Floor:
    """One level of the building."""

    floor_number: int     # 1-indexed
    label: str
    width: int            # grid columns
    height: int           # grid rows
    zones: Dict[str, Zone] = field(default_factory=dict)  # keyed by zone_id


@dataclass
class Building:
    """
    The complete Digital Twin of the building environment.

    Zones are stored in a flat dict for O(1) lookup by zone_id.
    Adjacency is represented as neighbor_ids on each Zone.
    """

    name: str
    floors: Dict[int, Floor] = field(default_factory=dict)   # keyed by floor number
    zones: Dict[str, Zone] = field(default_factory=dict)     # all zones, all floors

    # ------------------------------------------------------------------ #
    # Graph navigation                                                     #
    # ------------------------------------------------------------------ #

    def get_neighbors(self, zone_id: str) -> List[Zone]:
        """Return the list of zones adjacent to the given zone."""
        zone = self.zones.get(zone_id)
        if zone is None:
            return []
        return [self.zones[nid] for nid in zone.neighbor_ids if nid in self.zones]

    def get_zone_at(self, x: int, y: int, floor: int) -> Optional[Zone]:
        """Return the zone at grid coordinates (x, y, floor), or None."""
        zone_id = f"{x}_{y}_{floor}"
        return self.zones.get(zone_id)

    def reachable_from(self, start_zone_id: str) -> Set[str]:
        """BFS to find all zone_ids reachable from start_zone_id."""
        visited: Set[str] = set()
        queue: deque[str] = deque([start_zone_id])
        while queue:
            zid = queue.popleft()
            if zid in visited:
                continue
            visited.add(zid)
            for neighbor in self.get_neighbors(zid):
                if neighbor.zone_id not in visited:
                    queue.append(neighbor.zone_id)
        return visited

    def total_zones(self) -> int:
        return len(self.zones)


# ------------------------------------------------------------------ #
# Building factory                                                     #
# ------------------------------------------------------------------ #

def _zone_id(x: int, y: int, floor: int) -> str:
    return f"{x}_{y}_{floor}"


def build_warehouse_alpha() -> Building:
    """
    Factory for 'Warehouse Alpha' — a 5 × 4 single-floor building.

    Grid layout (x=column, y=row, origin top-left):

        x:  0           1           2           3           4
    y=0: Entry       Corridor    Hallway     Corridor    Fire Exit
    y=1: Corridor    Office A    Office B    Office C    Corridor
    y=2: Stairwell   Main Hall   Control Rm  Server Rm   Stairwell
    y=3: Garage      Break Room  Meeting Rm  Storage B   Loading Dock

    All orthogonal neighbors (N/S/E/W) are connected unless they share
    a wall that was sealed. For MVP all connections are open.
    """
    FLOOR = 1
    WIDTH = 5
    HEIGHT = 4

    labels = {
        (0, 0): ("Entry Lobby",    ZoneType.ENTRY),
        (1, 0): ("Corridor N1",    ZoneType.HALLWAY),
        (2, 0): ("North Hallway",  ZoneType.HALLWAY),
        (3, 0): ("Corridor N2",    ZoneType.HALLWAY),
        (4, 0): ("Fire Exit",      ZoneType.ENTRY),
        (0, 1): ("Corridor W1",    ZoneType.HALLWAY),
        (1, 1): ("Office A",       ZoneType.ROOM),
        (2, 1): ("Office B",       ZoneType.ROOM),
        (3, 1): ("Office C",       ZoneType.ROOM),
        (4, 1): ("Corridor E1",    ZoneType.HALLWAY),
        (0, 2): ("Stairwell W",    ZoneType.STAIRWELL),
        (1, 2): ("Main Hall",      ZoneType.HALLWAY),
        (2, 2): ("Control Room",   ZoneType.ROOM),
        (3, 2): ("Server Room",    ZoneType.ROOM),
        (4, 2): ("Stairwell E",    ZoneType.STAIRWELL),
        (0, 3): ("Garage",         ZoneType.ROOM),
        (1, 3): ("Break Room",     ZoneType.ROOM),
        (2, 3): ("Meeting Room",   ZoneType.ROOM),
        (3, 3): ("Storage B",      ZoneType.ROOM),
        (4, 3): ("Loading Dock",   ZoneType.ROOM),
    }

    floor = Floor(floor_number=FLOOR, label="Floor 1", width=WIDTH, height=HEIGHT)
    building = Building(name="Warehouse Alpha")

    # Create all zones
    for (x, y), (label, ztype) in labels.items():
        zid = _zone_id(x, y, FLOOR)
        zone = Zone(
            zone_id=zid,
            label=label,
            x=x,
            y=y,
            floor=FLOOR,
            zone_type=ztype,
        )
        floor.zones[zid] = zone
        building.zones[zid] = zone

    building.floors[FLOOR] = floor

    # Wire adjacency — orthogonal neighbors only
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # N, S, W, E
    for zone in list(building.zones.values()):
        for dx, dy in directions:
            nx, ny = zone.x + dx, zone.y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                nid = _zone_id(nx, ny, FLOOR)
                if nid in building.zones:
                    zone.neighbor_ids.append(nid)

    return building


def build_office_building() -> Building:
    """
    Factory for 'Office Building' — a 4 × 3 single-floor building.

    Grid layout (x=column, y=row, origin top-left):

        x:  0           1             2            3
    y=0: Reception   Corridor N    Hallway N    Emergency Exit
    y=1: Office 1    Open Plan     Kitchen      Office 2
    y=2: Conference  Server Room   Storeroom    Fire Escape
    """
    FLOOR = 1
    WIDTH = 4
    HEIGHT = 3

    labels = {
        (0, 0): ("Reception",       ZoneType.ENTRY),
        (1, 0): ("Corridor N",      ZoneType.HALLWAY),
        (2, 0): ("Hallway N",       ZoneType.HALLWAY),
        (3, 0): ("Emergency Exit",  ZoneType.ENTRY),
        (0, 1): ("Office 1",        ZoneType.ROOM),
        (1, 1): ("Open Plan",       ZoneType.ROOM),
        (2, 1): ("Kitchen",         ZoneType.ROOM),
        (3, 1): ("Office 2",        ZoneType.ROOM),
        (0, 2): ("Conference Room", ZoneType.ROOM),
        (1, 2): ("Server Room",     ZoneType.ROOM),
        (2, 2): ("Storeroom",       ZoneType.ROOM),
        (3, 2): ("Fire Escape",     ZoneType.ENTRY),
    }

    floor = Floor(floor_number=FLOOR, label="Floor 1", width=WIDTH, height=HEIGHT)
    building = Building(name="Office Building")

    for (x, y), (label, ztype) in labels.items():
        zid = _zone_id(x, y, FLOOR)
        zone = Zone(zone_id=zid, label=label, x=x, y=y, floor=FLOOR, zone_type=ztype)
        floor.zones[zid] = zone
        building.zones[zid] = zone

    building.floors[FLOOR] = floor

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for zone in list(building.zones.values()):
        for dx, dy in directions:
            nx, ny = zone.x + dx, zone.y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                nid = _zone_id(nx, ny, FLOOR)
                if nid in building.zones:
                    zone.neighbor_ids.append(nid)

    return building


def build_hospital() -> Building:
    """
    Factory for 'Hospital' — a 4 × 4 single-floor building.

    Grid layout (x=column, y=row, origin top-left):

        x:  0           1              2             3
    y=0: Entrance   Waiting Room   Reception     Emergency Exit
    y=1: Triage     Corridor       Pharmacy      Emergency Bay
    y=2: Ward A     ICU            Ward B        Stairwell
    y=3: Morgue     Maintenance    Boiler Room   Storage
    """
    FLOOR = 1
    WIDTH = 4
    HEIGHT = 4

    labels = {
        (0, 0): ("Entrance",        ZoneType.ENTRY),
        (1, 0): ("Waiting Room",    ZoneType.HALLWAY),
        (2, 0): ("Reception",       ZoneType.HALLWAY),
        (3, 0): ("Emergency Exit",  ZoneType.ENTRY),
        (0, 1): ("Triage",          ZoneType.ROOM),
        (1, 1): ("Corridor",        ZoneType.HALLWAY),
        (2, 1): ("Pharmacy",        ZoneType.ROOM),
        (3, 1): ("Emergency Bay",   ZoneType.ROOM),
        (0, 2): ("Ward A",          ZoneType.ROOM),
        (1, 2): ("ICU",             ZoneType.ROOM),
        (2, 2): ("Ward B",          ZoneType.ROOM),
        (3, 2): ("Stairwell",       ZoneType.STAIRWELL),
        (0, 3): ("Morgue",          ZoneType.ROOM),
        (1, 3): ("Maintenance",     ZoneType.ROOM),
        (2, 3): ("Boiler Room",     ZoneType.ROOM),
        (3, 3): ("Storage",         ZoneType.ROOM),
    }

    floor = Floor(floor_number=FLOOR, label="Floor 1", width=WIDTH, height=HEIGHT)
    building = Building(name="Hospital")

    for (x, y), (label, ztype) in labels.items():
        zid = _zone_id(x, y, FLOOR)
        zone = Zone(zone_id=zid, label=label, x=x, y=y, floor=FLOOR, zone_type=ztype)
        floor.zones[zid] = zone
        building.zones[zid] = zone

    building.floors[FLOOR] = floor

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for zone in list(building.zones.values()):
        for dx, dy in directions:
            nx, ny = zone.x + dx, zone.y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                nid = _zone_id(nx, ny, FLOOR)
                if nid in building.zones:
                    zone.neighbor_ids.append(nid)

    return building


def build_shopping_mall() -> Building:
    """
    Factory for 'Shopping Mall' — a 5 × 3 single-floor building.

    Grid layout (x=column, y=row, origin top-left):

        x:  0            1              2              3            4
    y=0: Food Court   Corridor W    Central Hall   Corridor E   Food Court B
    y=1: Shop A       Shop B        Atrium         Shop C       Shop D
    y=2: Parking A    Service Bay A Utility Room   Service Bay B Emergency Exit
    """
    FLOOR = 1
    WIDTH = 5
    HEIGHT = 3

    labels = {
        (0, 0): ("Food Court A",    ZoneType.ROOM),
        (1, 0): ("Corridor W",      ZoneType.HALLWAY),
        (2, 0): ("Central Hall",    ZoneType.HALLWAY),
        (3, 0): ("Corridor E",      ZoneType.HALLWAY),
        (4, 0): ("Food Court B",    ZoneType.ROOM),
        (0, 1): ("Shop A",          ZoneType.ROOM),
        (1, 1): ("Shop B",          ZoneType.ROOM),
        (2, 1): ("Atrium",          ZoneType.HALLWAY),
        (3, 1): ("Shop C",          ZoneType.ROOM),
        (4, 1): ("Shop D",          ZoneType.ROOM),
        (0, 2): ("Parking A",       ZoneType.ENTRY),
        (1, 2): ("Service Bay A",   ZoneType.ROOM),
        (2, 2): ("Utility Room",    ZoneType.ROOM),
        (3, 2): ("Service Bay B",   ZoneType.ROOM),
        (4, 2): ("Emergency Exit",  ZoneType.ENTRY),
    }

    floor = Floor(floor_number=FLOOR, label="Floor 1", width=WIDTH, height=HEIGHT)
    building = Building(name="Shopping Mall")

    for (x, y), (label, ztype) in labels.items():
        zid = _zone_id(x, y, FLOOR)
        zone = Zone(zone_id=zid, label=label, x=x, y=y, floor=FLOOR, zone_type=ztype)
        floor.zones[zid] = zone
        building.zones[zid] = zone

    building.floors[FLOOR] = floor

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for zone in list(building.zones.values()):
        for dx, dy in directions:
            nx, ny = zone.x + dx, zone.y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                nid = _zone_id(nx, ny, FLOOR)
                if nid in building.zones:
                    zone.neighbor_ids.append(nid)

    return building


def build_school() -> Building:
    """
    Factory for 'School' — a 4 × 4 single-floor building.

    Grid layout (x=column, y=row, origin top-left):

        x:  0               1             2             3
    y=0: Main Entrance   Main Hall     Library       Fire Exit
    y=1: Classroom 1     Corridor      Classroom 2   East Hallway
    y=2: Cafeteria       Science Lab   Art Room      Gymnasium
    y=3: Boiler Room     Storage       Utility Room  Fire Escape
    """
    FLOOR = 1
    WIDTH = 4
    HEIGHT = 4

    labels = {
        (0, 0): ("Main Entrance",   ZoneType.ENTRY),
        (1, 0): ("Main Hall",       ZoneType.HALLWAY),
        (2, 0): ("Library",         ZoneType.ROOM),
        (3, 0): ("Fire Exit",       ZoneType.ENTRY),
        (0, 1): ("Classroom 1",     ZoneType.ROOM),
        (1, 1): ("Corridor",        ZoneType.HALLWAY),
        (2, 1): ("Classroom 2",     ZoneType.ROOM),
        (3, 1): ("East Hallway",    ZoneType.HALLWAY),
        (0, 2): ("Cafeteria",       ZoneType.ROOM),
        (1, 2): ("Science Lab",     ZoneType.ROOM),
        (2, 2): ("Art Room",        ZoneType.ROOM),
        (3, 2): ("Gymnasium",       ZoneType.ROOM),
        (0, 3): ("Boiler Room",     ZoneType.ROOM),
        (1, 3): ("Storage",         ZoneType.ROOM),
        (2, 3): ("Utility Room",    ZoneType.ROOM),
        (3, 3): ("Fire Escape",     ZoneType.ENTRY),
    }

    floor = Floor(floor_number=FLOOR, label="Floor 1", width=WIDTH, height=HEIGHT)
    building = Building(name="School")

    for (x, y), (label, ztype) in labels.items():
        zid = _zone_id(x, y, FLOOR)
        zone = Zone(zone_id=zid, label=label, x=x, y=y, floor=FLOOR, zone_type=ztype)
        floor.zones[zid] = zone
        building.zones[zid] = zone

    building.floors[FLOOR] = floor

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for zone in list(building.zones.values()):
        for dx, dy in directions:
            nx, ny = zone.x + dx, zone.y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                nid = _zone_id(nx, ny, FLOOR)
                if nid in building.zones:
                    zone.neighbor_ids.append(nid)

    return building
