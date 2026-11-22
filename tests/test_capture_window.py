"""A healthy marine holds fire to open a boarding window (ADR-450)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _marine(**fields):
    row = {"id": "m1", "role": "marine", "status": "active", "injury_ticks": 0}
    row.update(fields)
    return row


def _captain(enemy_hull=32, enemy_max_hull=100, enemy_shield=0, crew=None,
             enemy_damage=15, enemy_intent="fire", hull=100):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.state = {
        "ship": {
            "hull": hull, "max_hull": 100, "shield": 60, "max_shield": 60, "fuel": 40,
            "reactor": {"heat": 10.0, "max_heat": 100.0, "heat_pct": 10.0,
                        "last_vent_tick": -999},
            "power": {"engines": 25, "shields": 25, "sensors": 25, "weapons": 25},
            "fleet_drones": [], "cargo": {},
        },
        "active_combat": {
            "id": "c1",
            "enemy_hull": enemy_hull,
            "enemy_max_hull": enemy_max_hull,
            "enemy_shield": enemy_shield,
            "enemy_max_shield": 0,
            "enemy_damage": enemy_damage,
            "enemy_intent": enemy_intent,
            "enemy_engines_disabled": False,
        },
        "crew": crew if crew is not None else [_marine()],
    }
    return captain


class CaptureWindowTest(unittest.TestCase):
    def test_a_marine_chips_instead_of_risking_a_kill_shot(self):
        # 32 of 100 hull: above the 30% boarding line.
        self.assertEqual(_captain()._choose(7)[1]["action"], "target_weapons")

    def test_the_chip_is_repeatable_after_the_weapon_cut(self):
        captain = _captain()
        actions = [captain._choose(7)[1]["action"] for _ in range(3)]
        self.assertEqual(
            actions,
            ["target_weapons", "target_subsystem", "target_subsystem"],
        )

    def test_a_full_health_enemy_is_chipped_too(self):
        self.assertEqual(
            _captain(enemy_hull=80)._choose(7)[1]["action"], "target_weapons",
            "a measured fight died from full hull in one laser, so no hull is safe",
        )

    def test_no_marine_means_no_holding_fire(self):
        self.assertEqual(
            _captain(crew=[])._choose(7)[1]["action"], "fire_lasers"
        )

    def test_an_injured_marine_means_no_holding_fire(self):
        self.assertEqual(
            _captain(crew=[_marine(injury_ticks=2)])._choose(7)[1]["action"],
            "fire_lasers",
        )

    def test_live_shields_still_get_the_ion_pulse(self):
        captain = _captain(enemy_shield=40, enemy_hull=32)
        self.assertEqual(captain._choose(7)[1]["action"], "target_shields")

    def test_the_chip_budget_runs_out(self):
        captain = _captain()
        for _ in range(AiCaptain.CAPTURE_CHIP_LIMIT):
            self.assertIn(
                captain._choose(7)[1]["action"],
                ("target_weapons", "target_subsystem"),
            )
        self.assertEqual(captain._choose(7)[1]["action"], "fire_lasers")

    def test_a_crippled_enemy_is_boarded_not_chipped(self):
        captain = _captain(enemy_hull=20)
        self.assertEqual(captain._choose(7)[1]["action"], "board_enemy")

    def test_survival_outranks_capture(self):
        captain = _captain(enemy_hull=32, hull=20)
        self.assertEqual(captain._choose(7)[1]["action"], "flee")

    def test_the_capture_milestones_are_unchanged(self):
        self.assertEqual(AiCaptain.CAPTURE_TARGET, CODEX_MAP["privateer"].target)
        self.assertEqual(AiCaptain.WARLORD_TARGET, CODEX_MAP["warlord"].target)


if __name__ == "__main__":
    unittest.main()
