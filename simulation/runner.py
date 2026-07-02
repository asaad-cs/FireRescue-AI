"""
Simulation Runner — the tick loop that drives the Digital Twin.

Responsibilities:
  1. Load scenario → initialise building, drone, and victims.
  2. Run an async tick loop at a fixed interval.
  3. Each tick: advance drone → generate Frame → call on_frame callback.
  4. When BFS exploration is complete, call on_complete callback.
  5. Honour stop() by exiting the tick loop cleanly.

The runner does NOT know about the Mission Manager, Pipeline, or
Broadcaster. It only knows how to produce Frames and deliver them via
the callback registered at start time.

Determinism guarantee:
  - Sensor values are pure functions of zone state (no random).
  - BFS traversal order is fixed by zone_id string order of neighbours.
  - Running the same scenario twice produces the exact same Frame sequence.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable, Optional

from backend.models.frame import Frame, Pose
from backend.utils.logger import logger
from simulation.drone import Drone
from simulation.environment import Building, Zone
from simulation.scenarios import Scenario, VictimEntity
from simulation.sensors import generate_environmental_channel

OnCompleteCallback = Callable[[], None]


class SimulationRunner:
    """
    Executes one simulation mission.

    A single SimulationRunner is used for one mission only.
    To run another mission, create a new instance.
    """

    DRONE_ID = "sim-drone-alpha"

    def __init__(self, scenario: Scenario, tick_interval: float = 1.0) -> None:
        self._scenario = scenario
        self._tick_interval = tick_interval
        self._running = False

        # Initialise building and entities from the scenario
        self.building: Building = scenario.building_factory()
        self._drone: Optional[Drone] = None
        self._victim_zone_ids: set[str] = set()

        self._spawn_victims()

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    def total_zones(self) -> int:
        return self.building.total_zones()

    async def run(
        self,
        mission_id: str,
        on_frame: Callable,
        on_complete: Optional[OnCompleteCallback] = None,
    ) -> None:
        """
        Async tick loop. Runs until all zones are explored or stop() is called.

        Intended to be launched as an asyncio.Task by the SimAdapter.
        """
        self._running = True
        self._drone = Drone(
            drone_id=self.DRONE_ID,
            building=self.building,
            start_zone_id=self._scenario.start_zone_id,
        )

        logger.info(
            "SimulationRunner | mission=%s  building=%s  zones=%d  tick=%.1fs",
            mission_id,
            self.building.name,
            self.building.total_zones(),
            self._tick_interval,
        )
        self._log_victims()

        tick = 0
        while self._running:
            zone = self._drone.next_zone()
            if zone is None:
                logger.info(
                    "SimulationRunner | all %d zones explored — mission complete",
                    self._drone.zones_visited,
                )
                if on_complete:
                    on_complete()
                break

            frame = self._generate_frame(mission_id, zone, tick)
            logger.info(
                "SimulationRunner | tick=%d  zone=%s (%s)  drone_pos=(%d,%d)",
                tick,
                zone.zone_id,
                zone.label,
                zone.x,
                zone.y,
            )
            if zone.victim_ids:
                logger.info(
                    "SimulationRunner | victim signal in zone %s — victims: %s",
                    zone.zone_id,
                    zone.victim_ids,
                )

            await on_frame(frame)
            tick += 1

            if self._running:
                await asyncio.sleep(self._tick_interval)

        self._running = False

    def stop(self) -> None:
        """Signal the tick loop to exit after the current tick."""
        self._running = False
        logger.info("SimulationRunner | stop requested")

    # ------------------------------------------------------------------ #
    # Frame assembly                                                        #
    # ------------------------------------------------------------------ #

    def _generate_frame(self, mission_id: str, zone: Zone, tick: int) -> Frame:
        hazard_def = self._scenario.hazard_zones.get(zone.zone_id)
        has_victim = bool(zone.victim_ids)

        env_channel = generate_environmental_channel(zone, hazard_def, has_victim)

        return Frame(
            mission_id=mission_id,
            drone_id=self.DRONE_ID,
            pose=Pose(x=zone.x, y=zone.y, floor=zone.floor),
            channels={"environmental": env_channel},
            timestamp=datetime.now(timezone.utc),
            metadata={
                "zone_label": zone.label,
                "zone_type": zone.zone_type.value,
                "tick": tick,
                "has_victim_ground_truth": has_victim,
            },
        )

    # ------------------------------------------------------------------ #
    # Victim initialisation                                                #
    # ------------------------------------------------------------------ #

    def _spawn_victims(self) -> None:
        for victim in self._scenario.victims:
            zone = self.building.zones.get(victim.zone_id)
            if zone is None:
                logger.warning(
                    "SimulationRunner | victim %s zone %s not found — skipping",
                    victim.victim_id,
                    victim.zone_id,
                )
                continue
            zone.victim_ids.append(victim.victim_id)
            self._victim_zone_ids.add(victim.zone_id)
            logger.info(
                "SimulationRunner | spawned victim %s in %s (%s)",
                victim.victim_id,
                zone.zone_id,
                zone.label,
            )

    def _log_victims(self) -> None:
        logger.info(
            "SimulationRunner | %d victim(s) placed: %s",
            len(self._scenario.victims),
            [v.victim_id for v in self._scenario.victims],
        )
