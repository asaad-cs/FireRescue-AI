"""
Victim Estimator — estimates the probability that a zone contains a victim.

Design (ADR-04: Perception Engine is a pure function):
  - Input:  environmental channel dict + zone history
  - Output: float in [0.0, 1.0]
  - No state. No IO.

Signal model:
  A victim's presence is inferred from anomalous CO and temperature
  readings that are elevated above safe-zone baseline but do not
  necessarily indicate a fire. The simulation adds a fixed victim
  overlay on top of zone hazard values (+5°C, +30 ppm CO).

  CO is the primary signal because CO builds up around unconscious
  victims (reduced air circulation, body metabolic output).
  Temperature is a secondary signal.

Formula:
  1. Compute CO elevation above baseline (5 ppm):
       co_elevation = max(0, co - 5)
  2. Convert to a probability component:
       co_prob = min(1.0, co_elevation / 130.0)
       (CO of 135 ppm → co_prob = 1.0; calibrated to victim overlay + some hazard)
  3. Temperature component:
       temp_elevation = max(0, temp - 22)
       temp_prob = min(1.0, temp_elevation / 50.0)
  4. Combined probability:
       victim_probability = 0.7 * co_prob + 0.3 * temp_prob
  5. In very high-hazard zones (fire), lower confidence slightly:
       if co > 250: apply 0.85 scaling (harder to distinguish victim from fire)

Cap: 0.0 – 0.92 (never fully certain from environmental sensors alone)
"""
from __future__ import annotations

from typing import Any, Dict

from perception.types import ZoneHistory

_BASELINE_CO: float = 5.0
_BASELINE_TEMP: float = 22.0
_CO_RANGE: float = 130.0       # CO elevation for 100% co_prob
_TEMP_RANGE: float = 50.0      # temp elevation for 100% temp_prob
_HIGH_HAZARD_CO_THRESHOLD: float = 250.0
_HIGH_HAZARD_SCALE: float = 0.85
_MAX_PROBABILITY: float = 0.92


class VictimEstimator:
    """Estimates victim presence probability from environmental readings."""

    def estimate(
        self,
        env_channel: Dict[str, Any],
        zone_history: ZoneHistory,
    ) -> float:
        """
        Return the estimated probability (0.0 – 0.92) that a victim is present.

        zone_history is available for future Bayesian updating across ticks.
        In Phase 4, only the current reading is used.
        """
        if not env_channel:
            return 0.0

        co = env_channel.get("co_level", 0.0)
        temp = env_channel.get("temperature", 0.0)

        co_elevation = max(0.0, co - _BASELINE_CO)
        co_prob = min(1.0, co_elevation / _CO_RANGE)

        temp_elevation = max(0.0, temp - _BASELINE_TEMP)
        temp_prob = min(1.0, temp_elevation / _TEMP_RANGE)

        probability = 0.7 * co_prob + 0.3 * temp_prob

        # In very heavy smoke/fire, victim signal is harder to distinguish
        if co > _HIGH_HAZARD_CO_THRESHOLD:
            probability *= _HIGH_HAZARD_SCALE

        return round(min(probability, _MAX_PROBABILITY), 3)
