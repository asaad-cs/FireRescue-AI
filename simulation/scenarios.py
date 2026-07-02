"""
Scenario definitions — ground truth for a simulation run.

A Scenario bundles:
  - A building factory (returns a fresh Building)
  - Hazard definitions per zone (ground-truth environmental readings)
  - Victim placements (ground-truth victim positions)

Hazard and victim values are FIXED for MVP (static, no spread).
The simulation generates sensor readings by looking up the zone's hazard
definition. If a zone has no definition it is safe (baseline readings).

This separation enforces the core principle: the environment holds the
truth; the Perception Engine must discover it from sensor data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from backend.models.mission_state import HazardLevel
from simulation.environment import (
    Building,
    build_warehouse_alpha,
    build_office_building,
    build_hospital,
    build_shopping_mall,
    build_school,
)


@dataclass
class HazardDefinition:
    """
    Ground-truth environmental state for one zone.

    The simulation reads these values to generate sensor channels.
    The Perception Engine must infer HazardLevel from those readings.
    """

    zone_id: str
    fire_intensity: float        # 0.0 – 1.0
    temperature: float           # Celsius (ground truth)
    co_level: float              # ppm (ground truth)
    smoke_density: float         # 0.0 – 1.0 (ground truth)
    hazard_level: HazardLevel    # ground-truth label (NOT sent to perception)
    accessible: bool = True      # drone can enter this zone


@dataclass
class VictimEntity:
    """
    A person inside the building at the start of the scenario.

    The Perception Engine must ESTIMATE victim presence from sensor readings.
    victim_ids on the Zone is ground truth (only visible inside simulation).
    """

    victim_id: str
    zone_id: str
    state: str = "UNKNOWN"           # UNKNOWN, CONSCIOUS, UNCONSCIOUS
    visibility: float = 1.0          # 0.0 – 1.0 (affects sensor signal strength)
    detection_probability: float = 0.8  # probability perception could detect this victim


@dataclass
class Scenario:
    """
    Complete initial conditions for one simulation run.

    building_factory: called once to produce the Building for this run.
    hazard_zones: ground-truth hazard state per zone_id.
    victims: all victims in this scenario.
    start_zone_id: zone where the drone begins.
    """

    name: str
    building_factory: Callable[[], Building]
    hazard_zones: Dict[str, HazardDefinition] = field(default_factory=dict)
    victims: List[VictimEntity] = field(default_factory=list)
    start_zone_id: str = "0_0_1"


def default_scenario() -> Scenario:
    """
    'Warehouse Alpha — Fire in Loading Dock'

    A fire has broken out in the loading dock (4,3), spreading heat and
    smoke into adjacent zones. Two victims are trapped inside.

    Hazard zones:
      (4,3) Loading Dock — CRITICAL  (active fire)
      (3,3) Storage B    — HIGH      (heavy smoke, hot)
      (4,2) Stairwell E  — MODERATE  (smoke ingress)

    Victims:
      V-001  Office A (1,1)       — conscious, easy to detect
      V-002  Meeting Room (2,3)   — unconscious, harder to detect
    """
    hazard_zones = {
        "4_3_1": HazardDefinition(
            zone_id="4_3_1",
            fire_intensity=0.95,
            temperature=145.0,
            co_level=680.0,
            smoke_density=0.92,
            hazard_level=HazardLevel.CRITICAL,
            accessible=True,     # drone can enter (at risk)
        ),
        "3_3_1": HazardDefinition(
            zone_id="3_3_1",
            fire_intensity=0.40,
            temperature=88.0,
            co_level=390.0,
            smoke_density=0.68,
            hazard_level=HazardLevel.HIGH,
            accessible=True,
        ),
        "4_2_1": HazardDefinition(
            zone_id="4_2_1",
            fire_intensity=0.10,
            temperature=62.0,
            co_level=175.0,
            smoke_density=0.42,
            hazard_level=HazardLevel.MODERATE,
            accessible=True,
        ),
    }

    victims = [
        VictimEntity(
            victim_id="V-001",
            zone_id="1_1_1",
            state="CONSCIOUS",
            visibility=1.0,
            detection_probability=0.85,
        ),
        VictimEntity(
            victim_id="V-002",
            zone_id="2_3_1",
            state="UNCONSCIOUS",
            visibility=0.6,
            detection_probability=0.70,
        ),
    ]

    return Scenario(
        name="Warehouse Alpha — Fire in Loading Dock",
        building_factory=build_warehouse_alpha,
        hazard_zones=hazard_zones,
        victims=victims,
        start_zone_id="0_0_1",
    )


def office_building_scenario() -> Scenario:
    """
    'Office Building — Electrical Fire in Server Room'

    An electrical fire has erupted in the server room (1,2), venting heat and
    toxic smoke through the adjacent storeroom and upward into Office 2.

    Hazard zones:
      (1,2) Server Room    — CRITICAL  (active electrical fire)
      (3,1) Office 2       — HIGH      (heavy smoke from corridor route)
      (2,2) Storeroom      — MODERATE  (smoke ingress, heat spread)

    Victims:
      V-001  Conference Room (0,2)  — UNCONSCIOUS, harder to detect
      V-002  Open Plan (1,1)        — CONSCIOUS, easy to detect
    """
    hazard_zones = {
        "1_2_1": HazardDefinition(
            zone_id="1_2_1",
            fire_intensity=0.90,
            temperature=155.0,
            co_level=720.0,
            smoke_density=0.88,
            hazard_level=HazardLevel.CRITICAL,
            accessible=True,
        ),
        "3_1_1": HazardDefinition(
            zone_id="3_1_1",
            fire_intensity=0.30,
            temperature=78.0,
            co_level=340.0,
            smoke_density=0.62,
            hazard_level=HazardLevel.HIGH,
            accessible=True,
        ),
        "2_2_1": HazardDefinition(
            zone_id="2_2_1",
            fire_intensity=0.05,
            temperature=55.0,
            co_level=150.0,
            smoke_density=0.38,
            hazard_level=HazardLevel.MODERATE,
            accessible=True,
        ),
    }

    victims = [
        VictimEntity(
            victim_id="V-001",
            zone_id="0_2_1",
            state="UNCONSCIOUS",
            visibility=0.7,
            detection_probability=0.75,
        ),
        VictimEntity(
            victim_id="V-002",
            zone_id="1_1_1",
            state="CONSCIOUS",
            visibility=1.0,
            detection_probability=0.85,
        ),
    ]

    return Scenario(
        name="Office Building — Electrical Fire in Server Room",
        building_factory=build_office_building,
        hazard_zones=hazard_zones,
        victims=victims,
        start_zone_id="0_0_1",
    )


def hospital_scenario() -> Scenario:
    """
    'Hospital — Chemical Fire in Boiler Room'

    A chemical fire in the basement boiler room (2,3) is spreading toxic fumes
    through the maintenance corridor and up into the ICU ward.

    Hazard zones:
      (2,3) Boiler Room  — CRITICAL  (chemical fire, intense CO)
      (1,3) Maintenance  — HIGH      (heavy smoke, heat spread)
      (1,2) ICU          — MODERATE  (smoke ingress from below)
      (1,1) Corridor     — LOW       (early smoke indicators)

    Victims:
      V-001  ICU (1,2)    — UNCONSCIOUS (patient), hard to detect
      V-002  Ward B (2,2) — CONSCIOUS (patient), easier to detect
    """
    hazard_zones = {
        "2_3_1": HazardDefinition(
            zone_id="2_3_1",
            fire_intensity=0.85,
            temperature=140.0,
            co_level=620.0,
            smoke_density=0.85,
            hazard_level=HazardLevel.CRITICAL,
            accessible=True,
        ),
        "1_3_1": HazardDefinition(
            zone_id="1_3_1",
            fire_intensity=0.35,
            temperature=85.0,
            co_level=380.0,
            smoke_density=0.65,
            hazard_level=HazardLevel.HIGH,
            accessible=True,
        ),
        "1_2_1": HazardDefinition(
            zone_id="1_2_1",
            fire_intensity=0.05,
            temperature=45.0,
            co_level=120.0,
            smoke_density=0.35,
            hazard_level=HazardLevel.MODERATE,
            accessible=True,
        ),
        "1_1_1": HazardDefinition(
            zone_id="1_1_1",
            fire_intensity=0.00,
            temperature=32.0,
            co_level=65.0,
            smoke_density=0.18,
            hazard_level=HazardLevel.LOW,
            accessible=True,
        ),
    }

    victims = [
        VictimEntity(
            victim_id="V-001",
            zone_id="1_2_1",
            state="UNCONSCIOUS",
            visibility=0.6,
            detection_probability=0.70,
        ),
        VictimEntity(
            victim_id="V-002",
            zone_id="2_2_1",
            state="CONSCIOUS",
            visibility=0.9,
            detection_probability=0.80,
        ),
    ]

    return Scenario(
        name="Hospital — Chemical Fire in Boiler Room",
        building_factory=build_hospital,
        hazard_zones=hazard_zones,
        victims=victims,
        start_zone_id="0_0_1",
    )


def shopping_mall_scenario() -> Scenario:
    """
    'Shopping Mall — Gas Leak Fire in Utility Room'

    A ruptured gas line in the utility room (2,2) has ignited, sending
    explosive heat and CO through both service bays and rising into the atrium.

    Hazard zones:
      (2,2) Utility Room   — CRITICAL  (gas fire, explosive heat)
      (1,2) Service Bay A  — HIGH      (adjacent to fire origin)
      (3,2) Service Bay B  — HIGH      (adjacent to fire origin)
      (2,1) Atrium         — MODERATE  (rising smoke from below)

    Victims:
      V-001  Atrium (2,1)  — UNCONSCIOUS, low visibility in smoke
      V-002  Shop C (3,1)  — CONSCIOUS, easy to detect
    """
    hazard_zones = {
        "2_2_1": HazardDefinition(
            zone_id="2_2_1",
            fire_intensity=0.88,
            temperature=135.0,
            co_level=590.0,
            smoke_density=0.82,
            hazard_level=HazardLevel.CRITICAL,
            accessible=True,
        ),
        "1_2_1": HazardDefinition(
            zone_id="1_2_1",
            fire_intensity=0.32,
            temperature=82.0,
            co_level=360.0,
            smoke_density=0.60,
            hazard_level=HazardLevel.HIGH,
            accessible=True,
        ),
        "3_2_1": HazardDefinition(
            zone_id="3_2_1",
            fire_intensity=0.28,
            temperature=79.0,
            co_level=340.0,
            smoke_density=0.58,
            hazard_level=HazardLevel.HIGH,
            accessible=True,
        ),
        "2_1_1": HazardDefinition(
            zone_id="2_1_1",
            fire_intensity=0.02,
            temperature=52.0,
            co_level=140.0,
            smoke_density=0.32,
            hazard_level=HazardLevel.MODERATE,
            accessible=True,
        ),
    }

    victims = [
        VictimEntity(
            victim_id="V-001",
            zone_id="2_1_1",
            state="UNCONSCIOUS",
            visibility=0.5,
            detection_probability=0.65,
        ),
        VictimEntity(
            victim_id="V-002",
            zone_id="3_1_1",
            state="CONSCIOUS",
            visibility=1.0,
            detection_probability=0.82,
        ),
    ]

    return Scenario(
        name="Shopping Mall — Gas Leak Fire in Utility Room",
        building_factory=build_shopping_mall,
        hazard_zones=hazard_zones,
        victims=victims,
        start_zone_id="2_0_1",
    )


def school_scenario() -> Scenario:
    """
    'School — Fire in Science Lab'

    A chemical reaction in the science lab (1,2) has started a fire, rapidly
    spreading toxic fumes into the art room and down through storage.

    Hazard zones:
      (1,2) Science Lab  — CRITICAL  (chemical fire)
      (2,2) Art Room     — HIGH      (heavy smoke from adjacent lab)
      (1,3) Storage      — MODERATE  (smoke through shared wall)
      (1,1) Corridor     — LOW       (early smoke indicators)

    Victims:
      V-001  Cafeteria (0,2)  — CONSCIOUS (student)
      V-002  Library (2,0)    — UNCONSCIOUS (student), harder to detect
    """
    hazard_zones = {
        "1_2_1": HazardDefinition(
            zone_id="1_2_1",
            fire_intensity=0.92,
            temperature=150.0,
            co_level=700.0,
            smoke_density=0.90,
            hazard_level=HazardLevel.CRITICAL,
            accessible=True,
        ),
        "2_2_1": HazardDefinition(
            zone_id="2_2_1",
            fire_intensity=0.40,
            temperature=90.0,
            co_level=400.0,
            smoke_density=0.70,
            hazard_level=HazardLevel.HIGH,
            accessible=True,
        ),
        "1_3_1": HazardDefinition(
            zone_id="1_3_1",
            fire_intensity=0.08,
            temperature=58.0,
            co_level=160.0,
            smoke_density=0.40,
            hazard_level=HazardLevel.MODERATE,
            accessible=True,
        ),
        "1_1_1": HazardDefinition(
            zone_id="1_1_1",
            fire_intensity=0.00,
            temperature=30.0,
            co_level=55.0,
            smoke_density=0.15,
            hazard_level=HazardLevel.LOW,
            accessible=True,
        ),
    }

    victims = [
        VictimEntity(
            victim_id="V-001",
            zone_id="0_2_1",
            state="CONSCIOUS",
            visibility=1.0,
            detection_probability=0.85,
        ),
        VictimEntity(
            victim_id="V-002",
            zone_id="2_0_1",
            state="UNCONSCIOUS",
            visibility=0.6,
            detection_probability=0.70,
        ),
    ]

    return Scenario(
        name="School — Fire in Science Lab",
        building_factory=build_school,
        hazard_zones=hazard_zones,
        victims=victims,
        start_zone_id="0_0_1",
    )
