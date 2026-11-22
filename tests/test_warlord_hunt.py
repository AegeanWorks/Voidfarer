"""The post-story captain hunts pirates in the riskiest lane for Warlord (ADR-451)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _system(system_id, security=0.5, faction="Independent", connections=(),
            **extra):
    row = {
        "id": system_id,
        "name": system_id,
        "seed": 7,
        "x": 0.0,
        "y": 0.0,
        "spectral_type": "G",
        "color": "#ffffff",
        "security": security,
        "faction": faction,
        "bodies": [],
        "connections": list(connections),
    }
    row.update(extra)
    return row


def _captain(victories=0, pirates=5, current="sol", connections=("haven",),
             galaxy=None, fuel=40, hull=100, completed=True,
             jumps=0, budget=None):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.warlord_jumps = jumps
    captain.galaxy_cache = galaxy if galaxy is not None else {
        "sol": _system("sol", 0.8, connections=connections),
        "haven": _system("haven", 0.15, connections=("sol",)),
        "safe": _system("safe", 0.9, connections=("sol",)),
    }
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"combat_victories": victories, "pirates_fought": pirates},
        "current_system": {"id": current, "connections": list(connections)},
        "jump_fuel_costs": {name: 3 for name in connections},
        "ship": {
            "hull": hull, "max_hull": 100, "fuel": fuel, "max_fuel": 60,
            "fleet_drones": [],
        },
    }
    return captain


class WarlordHuntTest(unittest.TestCase):
    def test_the_riskiest_neighbour_is_chosen(self):
        captain = _captain(
            connections=("safe", "haven"),
            galaxy={
                "sol": _system("sol", 0.8, connections=("safe", "haven")),
                "haven": _system("haven", 0.12, connections=("sol",)),
                "safe": _system("safe", 0.95, connections=("sol",)),
            },
        )
        self.assertEqual(
            captain._warlord_hunt_action(),
            ("/api/jump", {"target": "haven"}, "jump"),
        )

    def test_a_pirate_haven_outranks_a_calm_system(self):
        captain = _captain(
            connections=("safe", "golconda"),
            galaxy={
                "sol": _system("sol", 0.8, connections=("safe", "golconda")),
                # golconda is a real haven id, so it carries the haven bonus even at
                # high security (the engine's own PIRATE_HAVENS set drives this).
                "golconda": _system("golconda", 0.9, connections=("sol",)),
                "safe": _system("safe", 0.85, connections=("sol",)),
            },
        )
        self.assertEqual(
            captain._warlord_hunt_action()[1]["target"], "golconda"
        )

    def test_the_jump_marks_progress(self):
        captain = _captain()
        captain._warlord_hunt_action()
        self.assertEqual(captain.warlord_jumps, 1)

    def test_the_target_ends_the_hunt(self):
        captain = _captain(victories=AiCaptain.WARLORD_TARGET)
        self.assertIsNone(captain._warlord_hunt_action())

    def test_the_corsair_milestone_is_banked_first(self):
        captain = _captain(pirates=AiCaptain.CORSAIR_TARGET - 1)
        self.assertIsNone(
            captain._warlord_hunt_action(),
            "the hunt's jumps shift the toll rolls, so the corsair fights come first",
        )
        captain.state["stats"]["pirates_fought"] = AiCaptain.CORSAIR_TARGET
        self.assertIsNotNone(captain._warlord_hunt_action())

    def test_nothing_hunts_before_the_campaign(self):
        captain = _captain(completed=False)
        self.assertIsNone(captain._warlord_hunt_action())

    def test_a_damaged_hull_stops_the_hunt(self):
        captain = _captain(hull=40)
        self.assertIsNone(captain._warlord_hunt_action())

    def test_a_dry_tank_stops_the_hunt(self):
        captain = _captain(fuel=2)
        self.assertIsNone(captain._warlord_hunt_action())

    def test_the_jump_budget_bounds_the_hunt(self):
        captain = _captain(jumps=AiCaptain.WARLORD_JUMP_LIMIT)
        self.assertIsNone(captain._warlord_hunt_action())

    def test_an_isolated_system_has_no_lane(self):
        captain = _captain(connections=())
        self.assertIsNone(captain._warlord_hunt_action())

    def test_a_lane_without_a_published_cost_is_not_taken(self):
        captain = _captain()
        captain.state["jump_fuel_costs"] = {}
        self.assertIsNone(captain._warlord_hunt_action())

    def test_an_unreachable_galaxy_map_hunts_nothing(self):
        captain = _captain(galaxy={})
        self.assertIsNone(captain._warlord_hunt_action())

    def test_the_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.WARLORD_TARGET, CODEX_MAP["warlord"].target
        )


if __name__ == "__main__":
    unittest.main()
