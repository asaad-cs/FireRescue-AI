"""Tests: Real perception modules — HazardClassifier, VictimEstimator, AlertGenerator."""
import unittest

from backend.models.mission_state import HazardLevel
from backend.models.alert import AlertLevel, AlertType
from perception.hazard import HazardClassifier
from perception.victim import VictimEstimator
from perception.alerts import AlertGenerator
from perception.engine import ZoneHistory


class TestHazardClassifier(unittest.TestCase):

    def setUp(self):
        self.classifier = HazardClassifier()

    def test_empty_channel_returns_clear(self):
        self.assertEqual(self.classifier.classify({}), HazardLevel.CLEAR)

    def test_baseline_values_are_clear(self):
        env = {"temperature": 22.0, "co_level": 5.0, "smoke_density": 0.03}
        self.assertEqual(self.classifier.classify(env), HazardLevel.CLEAR)

    def test_low_hazard_temperature(self):
        env = {"temperature": 40.0, "co_level": 5.0, "smoke_density": 0.03}
        self.assertEqual(self.classifier.classify(env), HazardLevel.LOW)

    def test_moderate_hazard_co(self):
        env = {"temperature": 22.0, "co_level": 175.0, "smoke_density": 0.03}
        self.assertEqual(self.classifier.classify(env), HazardLevel.MODERATE)

    def test_high_hazard_smoke(self):
        env = {"temperature": 22.0, "co_level": 5.0, "smoke_density": 0.70}
        self.assertEqual(self.classifier.classify(env), HazardLevel.HIGH)

    def test_critical_hazard_high_temp(self):
        env = {"temperature": 145.0, "co_level": 5.0, "smoke_density": 0.03}
        self.assertEqual(self.classifier.classify(env), HazardLevel.CRITICAL)

    def test_critical_hazard_high_co(self):
        env = {"temperature": 22.0, "co_level": 680.0, "smoke_density": 0.03}
        self.assertEqual(self.classifier.classify(env), HazardLevel.CRITICAL)

    def test_critical_hazard_high_smoke(self):
        env = {"temperature": 22.0, "co_level": 5.0, "smoke_density": 0.92}
        self.assertEqual(self.classifier.classify(env), HazardLevel.CRITICAL)

    def test_takes_maximum_of_all_sensors(self):
        # temp → CLEAR, co → MODERATE, smoke → LOW → result MODERATE
        env = {"temperature": 22.0, "co_level": 175.0, "smoke_density": 0.15}
        self.assertEqual(self.classifier.classify(env), HazardLevel.MODERATE)

    def test_fire_zone_scenario_values(self):
        # Values matching default scenario CRITICAL zone
        env = {"temperature": 145.0, "co_level": 680.0, "smoke_density": 0.92}
        self.assertEqual(self.classifier.classify(env), HazardLevel.CRITICAL)

    def test_high_hazard_scenario_zone(self):
        # Default scenario Storage B (HIGH)
        env = {"temperature": 88.0, "co_level": 390.0, "smoke_density": 0.68}
        self.assertEqual(self.classifier.classify(env), HazardLevel.HIGH)

    def test_moderate_hazard_scenario_zone(self):
        # Default scenario Stairwell E (MODERATE)
        env = {"temperature": 62.0, "co_level": 175.0, "smoke_density": 0.42}
        self.assertEqual(self.classifier.classify(env), HazardLevel.MODERATE)


class TestVictimEstimator(unittest.TestCase):

    def setUp(self):
        self.estimator = VictimEstimator()
        self.history = ZoneHistory(zone_id="z1")

    def test_empty_channel_returns_zero(self):
        self.assertEqual(self.estimator.estimate({}, self.history), 0.0)

    def test_baseline_values_return_zero(self):
        env = {"temperature": 22.0, "co_level": 5.0, "smoke_density": 0.03}
        prob = self.estimator.estimate(env, self.history)
        self.assertEqual(prob, 0.0)

    def test_victim_zone_values_return_nonzero(self):
        # Office A with victim: baseline + 30 CO, +5 temp
        env = {"temperature": 27.0, "co_level": 35.0, "smoke_density": 0.03}
        prob = self.estimator.estimate(env, self.history)
        self.assertGreater(prob, 0.0)

    def test_victim_zone_values_above_threshold(self):
        env = {"temperature": 27.0, "co_level": 35.0, "smoke_density": 0.03}
        prob = self.estimator.estimate(env, self.history)
        self.assertGreater(prob, 0.10)

    def test_high_co_returns_high_probability(self):
        env = {"temperature": 32.0, "co_level": 135.0, "smoke_density": 0.03}
        prob = self.estimator.estimate(env, self.history)
        self.assertGreater(prob, 0.5)

    def test_probability_capped_at_max(self):
        env = {"temperature": 100.0, "co_level": 1000.0, "smoke_density": 0.9}
        prob = self.estimator.estimate(env, self.history)
        self.assertLessEqual(prob, 0.92)

    def test_probability_between_zero_and_one(self):
        for co in [0, 5, 50, 200, 500, 1000]:
            env = {"temperature": 22.0, "co_level": float(co), "smoke_density": 0.0}
            prob = self.estimator.estimate(env, self.history)
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)


class TestAlertGenerator(unittest.TestCase):

    def setUp(self):
        self.generator = AlertGenerator()
        self.mission_id = "m1"
        self.zone_id = "z1"

    def test_clear_zone_generates_no_alerts(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.CLEAR,
            victim_probability=0.0,
            active_alert_ids=set(),
        )
        self.assertEqual(alerts, [])

    def test_moderate_hazard_generates_warning(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.MODERATE,
            victim_probability=0.0,
            active_alert_ids=set(),
        )
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].level, AlertLevel.WARNING)
        self.assertEqual(alerts[0].alert_type, AlertType.HAZARD_ELEVATED)

    def test_high_hazard_generates_critical_alert(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.HIGH,
            victim_probability=0.0,
            active_alert_ids=set(),
        )
        self.assertEqual(alerts[0].level, AlertLevel.CRITICAL)

    def test_critical_hazard_generates_emergency(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.CRITICAL,
            victim_probability=0.0,
            active_alert_ids=set(),
        )
        self.assertEqual(alerts[0].level, AlertLevel.EMERGENCY)

    def test_victim_above_50_generates_warning(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.CLEAR,
            victim_probability=0.60,
            active_alert_ids=set(),
        )
        victim_alerts = [a for a in alerts if a.alert_type == AlertType.VICTIM_DETECTED]
        self.assertEqual(len(victim_alerts), 1)
        self.assertEqual(victim_alerts[0].level, AlertLevel.WARNING)

    def test_victim_above_80_generates_critical(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.CLEAR,
            victim_probability=0.85,
            active_alert_ids=set(),
        )
        victim_alerts = [a for a in alerts if a.alert_type == AlertType.VICTIM_DETECTED]
        self.assertEqual(victim_alerts[0].level, AlertLevel.CRITICAL)

    def test_duplicate_suppression(self):
        key = f"{self.zone_id}:{AlertType.HAZARD_ELEVATED}"
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.HIGH,
            victim_probability=0.0,
            active_alert_ids={key},  # already active
        )
        self.assertEqual(alerts, [])

    def test_alert_has_correct_zone_id(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.HIGH,
            victim_probability=0.0,
            active_alert_ids=set(),
        )
        self.assertEqual(alerts[0].zone_id, self.zone_id)

    def test_alert_has_correct_mission_id(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.HIGH,
            victim_probability=0.0,
            active_alert_ids=set(),
        )
        self.assertEqual(alerts[0].mission_id, self.mission_id)

    def test_both_hazard_and_victim_alerts_generated(self):
        alerts = self.generator.generate(
            mission_id=self.mission_id,
            zone_id=self.zone_id,
            hazard_level=HazardLevel.HIGH,
            victim_probability=0.85,
            active_alert_ids=set(),
        )
        types = {a.alert_type for a in alerts}
        self.assertIn(AlertType.HAZARD_ELEVATED, types)
        self.assertIn(AlertType.VICTIM_DETECTED, types)


if __name__ == "__main__":
    unittest.main()
