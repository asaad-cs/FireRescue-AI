"""
Sensor value generation — environmental channel per zone.

Given a Zone and the scenario's hazard definitions, generates the
environmental channel payload that will be embedded in a Frame.

Design:
  - Pure function: (zone, hazard_defs, victim_zone_ids) → dict
  - Deterministic: same zone always yields same values
  - Realistic: values reflect the zone's ground-truth hazard state

Baseline (safe zone):
    temperature:   22.0 °C
    co_level:       5.0 ppm
    smoke_density:  0.03

Victim signal overlay (if a victim is in the zone):
    temperature:  + 5.0 °C    (body heat / nearby thermal event)
    co_level:    +30.0 ppm    (elevated CO near unconscious victim)

Hazard zone values come directly from the HazardDefinition; they are the
ground truth that the Perception Engine must classify from sensor data.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from simulation.environment import Zone
from simulation.scenarios import HazardDefinition

# Baseline readings for safe, unaffected zones
_BASELINE_TEMPERATURE: float = 22.0
_BASELINE_CO_LEVEL: float = 5.0
_BASELINE_SMOKE_DENSITY: float = 0.03

# Victim signal overlay added on top of zone baseline/hazard values
_VICTIM_TEMP_OFFSET: float = 5.0
_VICTIM_CO_OFFSET: float = 30.0


def generate_environmental_channel(
    zone: Zone,
    hazard_def: Optional[HazardDefinition],
    has_victim: bool,
) -> Dict[str, Any]:
    """
    Generate the 'environmental' channel payload for one Frame.

    Parameters
    ----------
    zone:        The zone the drone is currently in.
    hazard_def:  Scenario hazard definition for this zone, or None if safe.
    has_victim:  True if at least one victim is located in this zone.

    Returns
    -------
    dict with keys: temperature, co_level, smoke_density
    """
    if hazard_def is not None:
        temp = hazard_def.temperature
        co = hazard_def.co_level
        smoke = hazard_def.smoke_density
    else:
        temp = _BASELINE_TEMPERATURE
        co = _BASELINE_CO_LEVEL
        smoke = _BASELINE_SMOKE_DENSITY

    # Victim signal overlay — elevates readings slightly to give perception
    # engine a signal even in otherwise safe zones
    if has_victim:
        temp += _VICTIM_TEMP_OFFSET
        co += _VICTIM_CO_OFFSET

    return {
        "temperature": round(temp, 1),
        "co_level": round(co, 1),
        "smoke_density": round(smoke, 3),
    }
