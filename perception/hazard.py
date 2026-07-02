"""
Hazard Classifier — maps environmental sensor readings to a HazardLevel.

Design (ADR-04: Perception Engine is a pure function):
  - Input:  environmental channel dict from a Frame
  - Output: HazardLevel enum value
  - No state. No IO. Same inputs → same output always.

Classification logic:
  Each sensor independently votes for a hazard level.
  The final result is the MAXIMUM (most severe) vote.
  This is conservative: any single sensor in a danger range
  triggers the corresponding hazard level.

Thresholds (based on fire-safety research baselines):

  Temperature (°C):
    < 30   → CLEAR
    < 45   → LOW
    < 70   → MODERATE
    < 100  → HIGH
    ≥ 100  → CRITICAL

  CO level (ppm):
    < 20   → CLEAR
    < 100  → LOW
    < 250  → MODERATE
    < 500  → HIGH
    ≥ 500  → CRITICAL

  Smoke density (0.0 – 1.0):
    < 0.10 → CLEAR
    < 0.30 → LOW
    < 0.55 → MODERATE
    < 0.75 → HIGH
    ≥ 0.75 → CRITICAL

If the environmental channel is missing or empty, returns CLEAR (safe default).
"""
from __future__ import annotations

from typing import Any, Dict

from backend.models.mission_state import HazardLevel

# Severity rank for ordering — higher index = more severe
_SEVERITY: list[HazardLevel] = [
    HazardLevel.UNOBSERVED,
    HazardLevel.CLEAR,
    HazardLevel.LOW,
    HazardLevel.MODERATE,
    HazardLevel.HIGH,
    HazardLevel.CRITICAL,
]


def _max_hazard(*levels: HazardLevel) -> HazardLevel:
    return max(levels, key=lambda h: _SEVERITY.index(h))


def _classify_temperature(temp: float) -> HazardLevel:
    if temp < 30.0:
        return HazardLevel.CLEAR
    if temp < 45.0:
        return HazardLevel.LOW
    if temp < 70.0:
        return HazardLevel.MODERATE
    if temp < 100.0:
        return HazardLevel.HIGH
    return HazardLevel.CRITICAL


def _classify_co(co: float) -> HazardLevel:
    if co < 20.0:
        return HazardLevel.CLEAR
    if co < 100.0:
        return HazardLevel.LOW
    if co < 250.0:
        return HazardLevel.MODERATE
    if co < 500.0:
        return HazardLevel.HIGH
    return HazardLevel.CRITICAL


def _classify_smoke(smoke: float) -> HazardLevel:
    if smoke < 0.10:
        return HazardLevel.CLEAR
    if smoke < 0.30:
        return HazardLevel.LOW
    if smoke < 0.55:
        return HazardLevel.MODERATE
    if smoke < 0.75:
        return HazardLevel.HIGH
    return HazardLevel.CRITICAL


class HazardClassifier:
    """Classifies the hazard level of a zone from its environmental readings."""

    def classify(self, env_channel: Dict[str, Any]) -> HazardLevel:
        """
        Return the HazardLevel for the given environmental channel.

        Takes the most severe vote across all three sensors.
        Returns CLEAR if the channel is missing or empty.
        """
        if not env_channel:
            return HazardLevel.CLEAR

        temp = env_channel.get("temperature", 0.0)
        co = env_channel.get("co_level", 0.0)
        smoke = env_channel.get("smoke_density", 0.0)

        return _max_hazard(
            _classify_temperature(temp),
            _classify_co(co),
            _classify_smoke(smoke),
        )
