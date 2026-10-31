"""Regression tests for adaptive enemy AI, expanded systems, and calendar dates."""

import unittest
from unittest.mock import patch

from voidfarer.engine import SimulationEngine
from voidfarer.enemies import ENEMY_ARCHETYPES, choose_enemy_intent, generate_system_enemy
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import CombatEncounter, TimeState


class TestAdaptiveEnemyAI(unittest.TestCase):
    def test_defensive_profile_braces_against_player_combo(self):
        intent, telegraph = choose_enemy_intent(
            profile="defensive",
            special_ability="emp_overload",
            ability_ready=True,
            enemy_hull=90,
            enemy_max_hull=100,
            enemy_shield=30,
            enemy_max_shield=60,
            player_hull=100,
            player_max_hull=100,
            player_shield=100,
            player_max_shield=100,
            player_combo=3,
        )
        self.assertEqual(intent, "brace")
        self.assertIn("plating", telegraph.lower())

    def test_opportunist_executes_wounded_player(self):
        intent, _ = choose_enemy_intent(
            profile="opportunist",
            special_ability="shield_drain",
            ability_ready=False,
            enemy_hull=80,
            enemy_max_hull=100,
            enemy_shield=40,
            enemy_max_shield=60,
            player_hull=25,
            player_max_hull=100,
            player_shield=0,
            player_max_shield=100,
            player_combo=0,
        )
        self.assertEqual(intent, "execute")

    def test_adaptive_profile_disrupts_high_combo(self):
        intent, _ = choose_enemy_intent(
            profile="adaptive",
            special_ability="emp_overload",
            ability_ready=True,
            enemy_hull=80,
            enemy_max_hull=100,
            enemy_shield=40,
            enemy_max_shield=60,
            player_hull=100,
            player_max_hull=100,
            player_shield=60,
            player_max_shield=100,
            player_combo=3,
        )
        self.assertEqual(intent, "ability")

    def test_warlord_regenerates_when_wounded(self):
        intent, _ = choose_enemy_intent(
            profile="warlord",
            special_ability="nanite_regen",
            ability_ready=True,
            enemy_hull=40,
            enemy_max_hull=200,
            enemy_shield=20,
            enemy_max_shield=100,
            player_hull=100,
            player_max_hull=100,
            player_shield=50,
            player_max_shield=100,
            player_combo=0,
        )
        self.assertEqual(intent, "ability")

    def test_generated_enemies_carry_ai_profile_and_intent(self):
        encounter = generate_system_enemy("rift_station", 0.05, "Void Corsairs", seed=42)
        self.assertIn(encounter.ai_profile, {a.ai_profile for a in ENEMY_ARCHETYPES.values()})
        self.assertIn(encounter.enemy_intent, {"fire", "brace", "evade", "execute", "ability"})

    def test_ai_fields_round_trip_through_save_data(self):
        encounter = CombatEncounter(
            id="ai_roundtrip",
            enemy_name="AI Test",
            enemy_class="Test",
            enemy_hull=50,
            enemy_max_hull=50,
            enemy_damage=10,
            bounty_credits=10,
            ai_profile="adaptive",
            enemy_intent="brace",
        )
        restored = CombatEncounter.from_dict(encounter.to_dict())
        self.assertEqual(restored.ai_profile, "adaptive")
        self.assertEqual(restored.enemy_intent, "brace")

    def _combat_engine(self, intent, profile="aggressive", player_combo=0):
        engine = SimulationEngine(seed=42)
        combat = CombatEncounter(
            id="ai_combat",
            enemy_name="AI Combat Drone",
            enemy_class="Drone",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=20,
            bounty_credits=10,
            enemy_shield=50,
            enemy_max_shield=50,
            special_ability="none",
            ability_cooldown=9,
            ai_profile=profile,
            enemy_intent=intent,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(shield=100, max_shield=100, tactical_combo=player_combo),
            active_combat=combat,
        )
        return engine

    def test_brace_reduces_player_strike_damage(self):
        baseline = self._combat_engine("fire")
        braced = self._combat_engine("brace")
        baseline.combat_action("fire_lasers")
        braced.combat_action("fire_lasers")
        self.assertGreater(
            braced.state.active_combat.enemy_shield,
            baseline.state.active_combat.enemy_shield,
        )

    def test_execute_increases_counter_battery_damage(self):
        baseline = self._combat_engine("fire")
        executing = self._combat_engine("execute")
        baseline.combat_action("fire_lasers")
        executing.combat_action("fire_lasers")
        self.assertLess(executing.state.ship.shield, baseline.state.ship.shield)

    def test_evade_can_make_player_strike_miss(self):
        engine = self._combat_engine("evade")
        before = engine.state.active_combat.enemy_shield
        with patch.object(engine.rng, "random", return_value=0.0):
            ok, msg = engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertIn("miss", msg.lower())
        self.assertEqual(engine.state.active_combat.enemy_shield, before)

    def test_ai_chooses_next_intent_from_player_combo(self):
        engine = self._combat_engine("fire", profile="defensive", player_combo=2)
        engine.combat_action("fire_lasers")
        self.assertEqual(engine.state.active_combat.enemy_intent, "brace")


class TestExpandedGalaxy(unittest.TestCase):
    def test_every_system_has_at_least_five_planets_and_a_station(self):
        galaxy = GalaxyGenerator(seed=42).generate_galaxy()
        total_planets = 0
        for system in galaxy.values():
            planets = [b for b in system.bodies if b.body_type != "star"]
            total_planets += len(planets)
            self.assertGreaterEqual(len(planets), 5, system.id)
            self.assertTrue(any(b.station_dockable for b in planets), system.id)
            body_ids = [b.id for b in system.bodies]
            self.assertEqual(len(body_ids), len(set(body_ids)), system.id)
        self.assertGreaterEqual(total_planets, 50)

    def test_sol_station_id_remains_stable(self):
        galaxy = GalaxyGenerator(seed=42).generate_galaxy()
        station = next(b for b in galaxy["sol"].bodies if b.id == "sol_body_1")
        self.assertTrue(station.station_dockable)
        self.assertGreaterEqual(len(galaxy["sol"].bodies), 6)


class TestCalendarDate(unittest.TestCase):
    def test_initial_calendar_date(self):
        self.assertEqual(TimeState().current_date, "01.01.3042")

    def test_calendar_date_advances_and_rolls_over_months(self):
        self.assertEqual(TimeState(elapsed_days=31).current_date, "01.02.3042")
        self.assertEqual(TimeState(elapsed_days=365).current_date, "01.01.3043")

    def test_time_payload_exposes_date(self):
        self.assertEqual(TimeState(elapsed_days=1).to_dict()["date"], "02.01.3042")

    def test_engine_tick_updates_calendar_date(self):
        engine = SimulationEngine(seed=42)
        self.assertEqual(engine.get_status_snapshot()["time"]["date"], "01.01.3042")
        engine.tick(4)
        self.assertEqual(engine.get_status_snapshot()["time"]["date"], "02.01.3042")


if __name__ == "__main__":
    unittest.main()
