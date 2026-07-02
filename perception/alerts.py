"""
Alert Generator — produces Alert objects when thresholds are crossed.

Design (ADR-04: Perception Engine is a pure function):
  - Input:  zone_id, HazardLevel, victim_probability, existing active alerts
  - Output: list of new Alert objects (may be empty)
  - No state. No IO.

Alert rules:

  HAZARD_ELEVATED:
    hazard_level >= MODERATE → WARNING
    hazard_level >= HIGH     → CRITICAL
    hazard_level == CRITICAL → EMERGENCY

  VICTIM_DETECTED:
    victim_probability >= 0.50 → WARNING
    victim_probability >= 0.80 → CRITICAL

Duplicate suppression:
  An alert is only generated if the same (zone_id, alert_type) pair
  is not already in active_alert_ids. This prevents flooding the
  dashboard with repeated alerts for a persistent hazard.
"""
from __future__ import annotations

from typing import List, Set

from backend.models.alert import Alert, AlertLevel, AlertType
from backend.models.mission_state import HazardLevel


class AlertGenerator:
    """Generates new Alert objects when perception thresholds are crossed."""

    def generate(
        self,
        mission_id: str,
        zone_id: str,
        hazard_level: HazardLevel,
        victim_probability: float,
        active_alert_ids: Set[str],  # set of "zone_id:alert_type" keys
    ) -> List[Alert]:
        """
        Return any new alerts triggered by the current perception result.

        active_alert_ids is used for duplicate suppression.
        The caller is responsible for maintaining this set.
        """
        new_alerts: List[Alert] = []

        # Hazard alerts
        hazard_level_alert = self._hazard_alert_level(hazard_level)
        if hazard_level_alert is not None:
            key = f"{zone_id}:{AlertType.HAZARD_ELEVATED}"
            if key not in active_alert_ids:
                new_alerts.append(Alert(
                    mission_id=mission_id,
                    zone_id=zone_id,
                    alert_type=AlertType.HAZARD_ELEVATED,
                    level=hazard_level_alert,
                    message=(
                        f"Hazard level {hazard_level.value} detected in zone {zone_id}. "
                        f"Proceed with extreme caution."
                    ),
                ))

        # Victim alerts
        victim_alert_level = self._victim_alert_level(victim_probability)
        if victim_alert_level is not None:
            key = f"{zone_id}:{AlertType.VICTIM_DETECTED}"
            if key not in active_alert_ids:
                new_alerts.append(Alert(
                    mission_id=mission_id,
                    zone_id=zone_id,
                    alert_type=AlertType.VICTIM_DETECTED,
                    level=victim_alert_level,
                    message=(
                        f"Possible victim signal in zone {zone_id}. "
                        f"Confidence: {int(victim_probability * 100)}%."
                    ),
                ))

        return new_alerts

    def _hazard_alert_level(self, hazard_level: HazardLevel) -> AlertLevel | None:
        if hazard_level == HazardLevel.CRITICAL:
            return AlertLevel.EMERGENCY
        if hazard_level == HazardLevel.HIGH:
            return AlertLevel.CRITICAL
        if hazard_level == HazardLevel.MODERATE:
            return AlertLevel.WARNING
        return None

    def _victim_alert_level(self, probability: float) -> AlertLevel | None:
        if probability >= 0.80:
            return AlertLevel.CRITICAL
        if probability >= 0.50:
            return AlertLevel.WARNING
        return None
