"""The post-story captain sweeps fuel to the helium-harvester milestone (ADR-444)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(
    fuel=60,
    max_fuel=60,
    scoops=1,
    completed=True,
    done=False,
    orbiting="star",
    scoop=None,
    bodies=None,
    connections=("vega",),
    tried=(),
    jumps=0,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.helium_done = done
    captain.helium_jumps = jumps
    captain.helium_systems_tried = set(tried)
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"scoops": scoops},
        "current_system": {
            "id": "sol",
            "bodies": bodies if bodies is not None else [
                {"id": "star", "body_type": "star"},
                {"id": "rock", "body_type": "asteroid"},
                {"id": "ice", "body_type": "ice_world"},
            ],
            "connections": list(connections),
        },
        "orbiting_body": {"id": orbiting} if orbiting else None,
        "scoop": scoop,
        "ship": {"fuel": fuel, "max_fuel": max_fuel},
    }
    return captain


class HeliumTapTest(unittest.TestCase):
    def test_an_available_tap_is_scooped(self):
        captain = _captain(fuel=30, scoop={"available": True, "tapped": 1, "reserve": 7})
        self.assertEqual(
            captain._helium_tap_action(),
            ("/api/scoop", {}, "scoop"),
        )

    def test_a_low_tank_orbits_the_next_scoopable_body(self):
        captain = _captain(
            fuel=20,
            orbiting="rock",
            scoop={"available": False, "tapped": 0, "reserve": 0},
        )
        self.assertEqual(
            captain._helium_tap_action(),
            ("/api/orbit", {"target": "star"}, "orbit"),
        )

    def test_a_dedicated_burn_jump_lets_the_tap_orbit_above_half(self):
        captain = _captain(
            fuel=58,
            orbiting="rock",
            scoop={"available": False, "tapped": 0, "reserve": 0},
        )
        captain.helium_room_pending = True
        self.assertEqual(
            captain._helium_tap_action(),
            ("/api/orbit", {"target": "star"}, "orbit"),
        )
        self.assertFalse(captain.helium_room_pending)

    def test_above_half_without_a_burn_jump_the_tap_stays_quiet(self):
        captain = _captain(
            fuel=58,
            orbiting="rock",
            scoop={"available": False, "tapped": 0, "reserve": 0},
        )
        self.assertIsNone(captain._helium_tap_action())

    def test_a_star_beats_an_ice_world(self):
        captain = _captain(
            fuel=20,
            orbiting="",
            bodies=[
                {"id": "ice", "body_type": "ice_world"},
                {"id": "star", "body_type": "star"},
            ],
        )
        self.assertEqual(
            captain._helium_tap_action()[1]["target"], "star"
        )

    def test_a_full_tank_taps_nothing(self):
        self.assertIsNone(_captain(fuel=60)._helium_tap_action())

    def test_the_target_ends_the_taps(self):
        captain = _captain(fuel=20, scoops=AiCaptain.HELIUM_TARGET)
        self.assertIsNone(captain._helium_tap_action())
        self.assertTrue(captain.helium_done)

    def test_nothing_runs_before_the_campaign(self):
        captain = _captain(completed=False, fuel=20)
        self.assertIsNone(captain._helium_tap_action())

    def test_a_system_without_volatiles_taps_nothing(self):
        captain = _captain(
            fuel=20,
            orbiting="",
            bodies=[{"id": "rock", "body_type": "asteroid"}],
        )
        self.assertIsNone(captain._helium_tap_action())


class HeliumBurnTest(unittest.TestCase):
    def test_a_full_tank_burns_fuel_on_a_jump(self):
        captain = _captain(fuel=60)
        self.assertEqual(
            captain._helium_sweep_action(),
            ("/api/navigate", {"system_id": "vega"}, "navigate"),
        )
        self.assertEqual(captain.helium_jumps, 1)
        self.assertIn("vega", captain.helium_systems_tried)

    def test_an_untried_connection_is_preferred(self):
        captain = _captain(connections=("vega", "altair"), tried=("vega",))
        self.assertEqual(
            captain._helium_sweep_action()[1]["system_id"], "altair"
        )

    def test_a_spent_map_falls_back_to_a_known_lane(self):
        captain = _captain(connections=("vega",), tried=("vega",))
        self.assertEqual(
            captain._helium_sweep_action()[1]["system_id"], "vega"
        )

    def test_a_tank_with_room_needs_no_jump(self):
        self.assertIsNone(_captain(fuel=20)._helium_sweep_action())

    def test_the_jump_budget_ends_the_sweep(self):
        captain = _captain(jumps=AiCaptain.HELIUM_JUMP_LIMIT)
        self.assertIsNone(captain._helium_sweep_action())
        self.assertTrue(captain.helium_done)

    def test_the_target_ends_the_sweep(self):
        captain = _captain(scoops=AiCaptain.HELIUM_TARGET)
        self.assertIsNone(captain._helium_sweep_action())
        self.assertTrue(captain.helium_done)

    def test_nothing_runs_before_the_campaign(self):
        captain = _captain(completed=False)
        self.assertIsNone(captain._helium_sweep_action())

    def test_an_isolated_full_tank_stays_quiet(self):
        captain = _captain(fuel=60, connections=())
        self.assertIsNone(captain._helium_sweep_action())

    def test_the_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.HELIUM_TARGET, CODEX_MAP["helium_harvester"].target
        )


if __name__ == "__main__":
    unittest.main()
