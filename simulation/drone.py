"""
Drone entity — the single moving agent inside the Digital Twin.

The drone's only behaviour in Phase 4 is autonomous BFS exploration.
It visits every reachable zone in breadth-first order, starting from
the scenario's designated entry point.

Movement is LOGICAL, not physical:
  - Each tick the drone moves to the next zone in BFS order.
  - No flight dynamics, no battery drain calculation, no obstacle physics.

Battery level and connection status are tracked as display fields for
the dashboard but are not used for decision logic in Phase 4.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Set

from simulation.environment import Building, Zone


@dataclass
class Drone:
    """
    The virtual drone navigating the building.

    Maintains its own BFS state so the runner only calls next_zone()
    each tick — the drone encapsulates all movement logic.
    """

    drone_id: str
    building: Building
    start_zone_id: str
    battery_level: float = 100.0     # 0.0 – 100.0 (display only in Phase 4)
    connection_status: str = "CONNECTED"
    movement_history: List[str] = field(default_factory=list)

    # BFS internal state — initialised by __post_init__
    _bfs_queue: Deque[str] = field(default_factory=deque, init=False, repr=False)
    _bfs_visited: Set[str] = field(default_factory=set, init=False, repr=False)
    _current_zone_id: Optional[str] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        # Seed BFS with the starting zone
        self._bfs_visited.add(self.start_zone_id)
        self._bfs_queue.append(self.start_zone_id)

    # ------------------------------------------------------------------ #
    # Movement                                                             #
    # ------------------------------------------------------------------ #

    def next_zone(self) -> Optional[Zone]:
        """
        Advance to the next BFS zone and return it.

        Returns None when all reachable zones have been visited.
        On each call the drone:
          1. Dequeues the next zone.
          2. Marks it visited in the building model.
          3. Enqueues its unvisited neighbours.
          4. Updates current_zone_id and movement_history.
        """
        if not self._bfs_queue:
            return None

        zone_id = self._bfs_queue.popleft()
        zone = self.building.zones.get(zone_id)
        if zone is None:
            return None

        # Mark visited in the digital twin
        zone.visited = True
        self._current_zone_id = zone_id
        self.movement_history.append(zone_id)

        # Expand BFS to unvisited neighbours
        for neighbor_id in zone.neighbor_ids:
            if neighbor_id not in self._bfs_visited:
                self._bfs_visited.add(neighbor_id)
                self._bfs_queue.append(neighbor_id)

        return zone

    @property
    def current_zone_id(self) -> Optional[str]:
        return self._current_zone_id

    @property
    def zones_visited(self) -> int:
        return len(self.movement_history)

    @property
    def exploration_complete(self) -> bool:
        return len(self._bfs_queue) == 0 and self._current_zone_id is not None
