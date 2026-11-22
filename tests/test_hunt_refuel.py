"""The hunt refuels its own tank once the helium track is spent (ADR-452)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _captain(
    fuel=2,
    max_fuel=80,
    victories=10,
    pirates=5,
    hull=280,
    max_hull=310,
    scoop=None,
    orbiting="rock",
    bodies=None,
    completed=True,
    refuels=0,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.warlord_refuels = refuels
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"combat_victories": victories, "pirates_fought": pirates},
        "current_system": {
            "id": "sol",
            "bodies": bodies if bodies is not None else [
                {"id": "star", "body_type": "star"},
                {"id": "rock", "body_type": "asteroid"},
                {"id": "ice", "body_type": "ice_world"},
            ],
            "connections": ["haven"],
        },
        "orbiting_body": {"id": orbiting} if orbiting else None,
        "scoop": scoop,
        "jump_fuel_costs": {"haven": 4},
        "ship": {"fuel": fuel, "max_fuel": max_fuel, "hull": hull,
                 "max_hull": max_hull},
    }
    return captain


class HuntRefuelTest(unittest.TestCase):
    def test_a_live_tap_is_scooped_during_the_hunt(self):
        captain = _captain(scoop={"available": True, "tapped": 1, "reserve": 6})
        self.assertEqual(
            captain._hunt_fuel_action(), ("/api/scoop", {}, "scoop")
        )

    def test_a_dry_hunt_orbits_the_next_volatile_body(self):
        commission = _captain(scoop={"available": False, "tapped": 0, "reserve": 0})
        self.assertEqual(
            commission._hunt_fuel_action(),
            ("/api/orbit", {"target": "star"}, "orbit"),
        )
        self.assertEqual(commission.warlord_refuels, 1)

    def test_an_affordable_hop_needs_no_refuel(self):
        captain = _captain(fuel=70, scoop={"available": True, "tapped": 1})
        self.assertIsNone(captain._hunt_fuel_action())

    def test_the_refuel_stops_once_warlord_is_banked(self):
        captain = _captain(
            victories=AiCaptain.WARLORD_TARGET,
            scoop={"available": True, "tapped": 1},
        )
        self.assertIsNone(captain._hunt_fuel_action())

    def test_the_refuel_waits_for_the_corsair_milestone(self):
        captain = _captain(pirates=0, scoop={"available": True, "tapped": 1})
        self.assertIsNone(captain._hunt_fuel_action())

    def test_a_damaged_hull_does_not_refuel(self):
        captain = _captain(hull=100, scoop={"available": True, "tapped": 1})
        self.assertIsNone(
            captain._hunt_fuel_action(),
            "the hunt will not jump below half hull, so fuel would be wasted",
        )

    def test_nothing_refuels_before_the_campaign(self):
        captain = _captain(completed=False, scoop={"available": True, "tapped": 1})
        self.assertIsNone(captain._hunt_fuel_action())

    def test_a_system_without_volatiles_cannot_refuel(self):
        captain = _captain(
            scoop={"available": False, "tapped": 0, "reserve": 0},
            bodies=[{"id": "rock", "body_type": "asteroid"}],
            orbiting="rock",
        )
        self.assertIsNone(captain._hunt_fuel_action())

    def test_the_refuel_budget_bounds_a_refused_orbit(self):
        captain = _captain(
            scoop={"available": False, "tapped": 0, "reserve": 0},
            refuels=AiCaptain.HUNT_REFUEL_LIMIT,
        )
        self.assertIsNone(captain._hunt_fuel_action())

    def test_a_spent_hunt_budget_stops_refuelling(self):
        captain = _captain(
            scoop={"available": True, "tapped": 1},
            refuels=0,
        )
        captain.warlord_jumps = AiCaptain.WARLORD_JUMP_LIMIT
        self.assertIsNone(captain._hunt_fuel_action())


if __name__ == "__main__":
    unittest.main()
