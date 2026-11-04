"""Captain's Gambit: once-per-battle role actions scaled by captain skill."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship
from voidfarer.models import CombatEncounter, CrewMember


class CaptainGambitTest(unittest.TestCase):
    def _engine(self, role: str, skill: int = 5):
        engine = SimulationEngine(seed=42)
        captain = CrewMember(
            id="captain_test",
            name="Test Captain",
            role=role,
            skill=skill,
            specialty=role,
            status="active",
        )
        escort = replace(
            build_fleet_ship("corvette", "sol", 0),
            captain_id=captain.id,
            captain_role=role,
            captain_skill=skill,
            hull=40,
            shield=10,
        )
        combat = CombatEncounter(
            id="gambit_test",
            enemy_name="Test Target",
            enemy_class="Corvette",
            enemy_hull=100,
            enemy_max_hull=100,
            enemy_damage=30,
            bounty_credits=0,
            salvage_commodity="titanium",
            enemy_shield=40,
            enemy_max_shield=40,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                hull=50,
                shield=50,
                crew=(captain,),
                fleet_ships=(escort,),
            ),
            active_combat=combat,
        )
        return engine

    def test_gambit_effects_scale_with_captain_skill(self):
        low = self._engine("engineer", skill=2)
        high = self._engine("engineer", skill=8)
        self.assertTrue(low.captain_gambit()[0])
        self.assertTrue(high.captain_gambit()[0])
        self.assertGreater(high.state.ship.hull, low.state.ship.hull)

    def test_engineer_repairs_the_flagship_hull(self):
        engine = self._engine("engineer")
        ok, message = engine.captain_gambit()
        self.assertTrue(ok, message)
        self.assertIn("CAPTAIN'S GAMBIT", message)
        self.assertEqual(engine.state.ship.hull, 77)
        self.assertTrue(engine.state.active_combat.captain_gambit_used)

    def test_medic_repairs_the_local_escort_wing(self):
        engine = self._engine("medic")
        ok, message = engine.captain_gambit()
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fleet_ships[0].hull, 56)

    def test_quartermaster_restores_escort_shields(self):
        engine = self._engine("quartermaster")
        ok, message = engine.captain_gambit()
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fleet_ships[0].shield, 30)

    def test_pilot_adds_evasion_for_the_battle(self):
        engine = self._engine("pilot")
        ok, message = engine.captain_gambit()
        self.assertTrue(ok, message)
        self.assertGreater(engine.state.active_combat.captain_evasion_bonus, 0.0)

    def test_scientist_drains_enemy_shields(self):
        engine = self._engine("scientist")
        ok, message = engine.captain_gambit()
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.active_combat.enemy_shield, 5)

    def test_marine_cuts_enemy_firepower(self):
        engine = self._engine("marine")
        ok, message = engine.captain_gambit()
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.active_combat.enemy_damage, 12)

    def test_gambit_is_once_per_battle(self):
        engine = self._engine("engineer")
        self.assertTrue(engine.captain_gambit()[0])
        ok, message = engine.captain_gambit()
        self.assertFalse(ok)
        self.assertIn("already spent", message.lower())

    def test_gambit_state_survives_combat_action(self):
        engine = self._engine("pilot")
        self.assertTrue(engine.captain_gambit()[0])
        bonus = engine.state.active_combat.captain_evasion_bonus
        self.assertGreater(bonus, 0.0)
        engine.combat_action("fire_lasers")
        self.assertTrue(engine.state.active_combat.captain_gambit_used)
        self.assertAlmostEqual(engine.state.active_combat.captain_evasion_bonus, bonus)
        ok, message = engine.captain_gambit()
        self.assertFalse(ok)
        self.assertIn("already spent", message.lower())

    def test_gambit_requires_a_local_captain(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            active_combat=CombatEncounter(
                id="no_captain",
                enemy_name="Test Target",
                enemy_class="Corvette",
                enemy_hull=100,
                enemy_max_hull=100,
                enemy_damage=30,
                bounty_credits=0,
            )
        )
        ok, message = engine.captain_gambit()
        self.assertFalse(ok)
        self.assertIn("no living escort captain", message.lower())

    def test_gambit_fields_round_trip_and_legacy_defaults(self):
        engine = self._engine("pilot")
        self.assertTrue(engine.captain_gambit()[0])
        payload = engine.state.to_dict()
        payload["active_combat"].pop("captain_gambit_used", None)
        payload["active_combat"].pop("captain_evasion_bonus", None)
        restored = CombatEncounter.from_dict(payload["active_combat"])
        self.assertFalse(restored.captain_gambit_used)
        self.assertEqual(restored.captain_evasion_bonus, 0.0)


if __name__ == "__main__":
    unittest.main()
