"""Escort captain progression: stored skill, scaling bonuses and battle XP."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import (
    build_fleet_ship,
    captain_skill_multiplier,
    fleet_damage,
    fleet_evasion_bonus,
    fleet_upkeep,
)
from voidfarer.models import CombatEncounter, FleetShip, GameState


class CaptainSkillMathTest(unittest.TestCase):
    def test_skill_zero_is_legacy_neutral_and_ten_is_capped(self):
        self.assertEqual(captain_skill_multiplier(0), 1.0)
        self.assertEqual(captain_skill_multiplier(1), 1.0)
        self.assertAlmostEqual(captain_skill_multiplier(10), 1.45)

    def test_skill_scales_damage_evasion_and_upkeep_discount(self):
        base = build_fleet_ship("frigate", "sol", 0)
        marine_low = replace(base, captain_role="marine", captain_skill=2)
        marine_high = replace(base, captain_role="marine", captain_skill=8)
        self.assertGreater(fleet_damage((marine_high,)), fleet_damage((marine_low,)))

        pilot_low = replace(base, captain_role="pilot", captain_skill=2)
        pilot_high = replace(base, captain_role="pilot", captain_skill=8)
        self.assertGreater(
            fleet_evasion_bonus((pilot_high,)),
            fleet_evasion_bonus((pilot_low,)),
        )

        quartermaster_low = replace(base, captain_role="quartermaster", captain_skill=2)
        quartermaster_high = replace(base, captain_role="quartermaster", captain_skill=8)
        self.assertLess(
            fleet_upkeep((quartermaster_high,)),
            fleet_upkeep((quartermaster_low,)),
        )

    def test_legacy_ship_defaults_to_zero_captain_skill(self):
        ship = build_fleet_ship("corvette", "sol", 0)
        payload = ship.to_dict()
        payload.pop("captain_skill", None)
        restored = FleetShip.from_dict(payload)
        self.assertEqual(restored.captain_skill, 0)


class CaptainProgressionEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.ship = build_fleet_ship("corvette", "sol", 0)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=5000, fleet_ships=(self.ship,))
        )
        self.crew = self.engine.state.ship.crew[0]

    def _assign(self):
        ok, message = self.engine.assign_fleet_captain(self.ship.id, self.crew.id)
        self.assertTrue(ok, message)
        return self.engine.state.ship.fleet_ships[0]

    def test_assignment_records_skill_in_state_and_report(self):
        assigned = self._assign()
        self.assertEqual(assigned.captain_skill, self.crew.skill)
        report = self.engine.get_fleet_manager_report()["ships"][0]
        self.assertEqual(report["captain_skill"], self.crew.skill)
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(
            restored.ship.fleet_ships[0].captain_skill, self.crew.skill
        )

    def test_training_a_captain_updates_the_ship_bonus(self):
        assigned = self._assign()
        before = assigned.captain_skill
        ok, message = self.engine.train_crew_member(self.crew.id)
        self.assertTrue(ok, message)
        updated = self.engine.state.ship.fleet_ships[0]
        self.assertEqual(updated.captain_skill, before + 1)

    def test_rewarded_victory_awards_captain_xp_and_syncs_promotion(self):
        self._assign()
        crew = tuple(
            replace(member, xp=100) if member.id == self.crew.id else member
            for member in self.engine.state.ship.crew
        )
        combat = CombatEncounter(
            id="captain_victory",
            enemy_name="Training Drone",
            enemy_class="Corvette",
            enemy_hull=1,
            enemy_max_hull=1,
            enemy_damage=0,
            bounty_credits=0,
            salvage_commodity="titanium",
            enemy_shield=0,
            enemy_max_shield=0,
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(crew=crew, credits=5000),
            active_combat=combat,
        )
        self.engine.rng.random = lambda: 0.0
        ok, message = self.engine.combat_action("fire_lasers")
        self.assertTrue(ok, message)
        self.assertIsNone(self.engine.state.active_combat)
        self.assertIn("CAPTAIN PROMOTION", message)
        captain = next(
            member
            for member in self.engine.state.ship.crew
            if member.id == self.crew.id
        )
        self.assertEqual(captain.skill, 4)
        self.assertEqual(self.engine.state.ship.fleet_ships[0].captain_skill, 4)


if __name__ == "__main__":
    unittest.main()
