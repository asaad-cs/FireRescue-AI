"""
Scenario Registry — central lookup for all named simulation scenarios.

Usage:
    from simulation.scenario_registry import get_scenario, list_scenarios, SCENARIO_REGISTRY

    scenario = get_scenario("hospital")          # returns a fresh Scenario
    available = list_scenarios()                 # returns metadata list for UI
    all_keys = list(SCENARIO_REGISTRY)           # ["warehouse_alpha", "office_building", ...]
"""
from __future__ import annotations

from typing import Callable, Dict, List

from simulation.scenarios import (
    Scenario,
    default_scenario,
    office_building_scenario,
    hospital_scenario,
    shopping_mall_scenario,
    school_scenario,
)

# ── Registry ──────────────────────────────────────────────────────────────────
# Maps scenario key → zero-argument factory function that returns a fresh Scenario.
# Each call to the factory produces an independent Scenario instance; scenarios
# are never shared between missions.

SCENARIO_REGISTRY: Dict[str, Callable[[], Scenario]] = {
    "warehouse_alpha":  default_scenario,
    "office_building":  office_building_scenario,
    "hospital":         hospital_scenario,
    "shopping_mall":    shopping_mall_scenario,
    "school":           school_scenario,
}

# ── Display metadata (zone counts match the building factories) ───────────────

SCENARIO_METADATA: Dict[str, Dict] = {
    "warehouse_alpha": {
        "key":          "warehouse_alpha",
        "display_name": "Warehouse Alpha",
        "description":  "Fire in Loading Dock — 5×4 grid, 20 zones",
        "zone_count":   20,
    },
    "office_building": {
        "key":          "office_building",
        "display_name": "Office Building",
        "description":  "Electrical Fire in Server Room — 4×3 grid, 12 zones",
        "zone_count":   12,
    },
    "hospital": {
        "key":          "hospital",
        "display_name": "Hospital",
        "description":  "Chemical Fire in Boiler Room — 4×4 grid, 16 zones",
        "zone_count":   16,
    },
    "shopping_mall": {
        "key":          "shopping_mall",
        "display_name": "Shopping Mall",
        "description":  "Gas Leak Fire in Utility Room — 5×3 grid, 15 zones",
        "zone_count":   15,
    },
    "school": {
        "key":          "school",
        "display_name": "School",
        "description":  "Fire in Science Lab — 4×4 grid, 16 zones",
        "zone_count":   16,
    },
}

DEFAULT_SCENARIO_KEY = "warehouse_alpha"


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_scenario(key: str) -> Scenario:
    """
    Return a fresh Scenario for the given registry key.

    Each call returns a new independent instance — never cached.

    Raises KeyError if the key is not registered.
    """
    factory = SCENARIO_REGISTRY.get(key)
    if factory is None:
        raise KeyError(
            f"Unknown scenario: '{key}'. "
            f"Available: {list(SCENARIO_REGISTRY)}"
        )
    return factory()


def list_scenarios() -> List[Dict]:
    """Return display metadata for all registered scenarios, in registry order."""
    return list(SCENARIO_METADATA.values())
