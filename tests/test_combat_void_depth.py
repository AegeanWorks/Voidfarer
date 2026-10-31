"""Regression tests for progression-scaled combat and Hollow resonance risk/reward."""

import io
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from voidfarer.cli import cmd_void
from voidfarer.engine import SimulationEngine
from voidfarer.enemies import ENEMY_ARCHETYPES, generate_system_enemy, threat_multiplier
from voidfarer.models import CombatEncounter, VoidTraversalState
from voidfarer.storage import StorageManager


class TestProgressionThreatScaling(unittest.TestCase):
    def test_threat_multiplier_starts_flat_and_grows(self):
        self.assertEqual(threat_multiplier(1), 1.0)
        self.assertEqual(threat_multiplier(0), 1.0)
        self.assertGreater(threat_multiplier(6), threat_multiplier(2))
        self.assertLessEqual(threat_multiplier(99), 1.75)

    def test_generated_enemy_scales_with_threat_level(self):
        base = generate_system_enemy("rift_station", 0.05, "Outlaw Haven", seed=0, threat_level=1)
        elite = generate_system_enemy("rift_station", 0.05, "Outlaw Haven", seed=0, threat_level=8)
        self.assertEqual(base.archetype_id, elite.archetype_id)
        self.assertGreater(elite.enemy_hull, base.enemy_hull)
        self.assertGreater(elite.enemy_damage, base.enemy_damage)
        self.assertGreater(elite.bounty_credits, base.bounty_credits)

    def test_dreadnought_boss_is_gated_behind_mastery(self):
        low = generate_system_enemy("rift_station", 0.05, "Outlaw Haven", seed=1, threat_level=1)
        self.assertNotEqual(low.archetype_id, "warlord_dreadnought")

        high = generate_system_enemy("rift_station", 0.05, "Outlaw Haven", seed=1, threat_level=8)
        self.assertEqual(high.archetype_id, "warlord_dreadnought")
        self.assertIsNotNone(ENEMY_ARCHETYPES[high.archetype_id])


class TestEarlyCombatRisk(unittest.TestCase):
    def test_a_marauder_costs_hull_to_a_fresh_corvette(self):
        arch = ENEMY_ARCHETYPES["syndicate_marauder"]
        combat = CombatEncounter(
            id="balance_marauder",
            enemy_name=arch.name,
            enemy_class=arch.enemy_class,
            enemy_hull=arch.base_hull,
            enemy_max_hull=arch.base_hull,
            enemy_damage=arch.base_damage,
            bounty_credits=arch.bounty_credits,
            salvage_commodity=arch.salvage_commodity,
            enemy_shield=arch.base_shield,
            enemy_max_shield=arch.base_shield,
            faction_id=arch.faction_id,
            special_ability=arch.special_ability,
        )
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(hull=100, shield=100),
            active_combat=combat,
        )
        start_hull = engine.state.ship.hull
        for _ in range(20):
            if engine.state.active_combat is None:
                break
            engine.combat_action("fire_lasers")
        self.assertIsNone(engine.state.active_combat)
        self.assertLess(engine.state.ship.hull, start_hull,
                        "a marauder fight must cost hull without abilities")
        self.assertGreater(engine.state.ship.hull, 0,
                           "the baseline marauder must remain survivable")

    def test_defensive_actions_also_end_in_defeat(self):
        for action in ("shield_absorb", "evasive_burn"):
            combat = CombatEncounter(
                id=f"lethal_{action}", enemy_name="Lethal Frame", enemy_class="Dreadnought",
                enemy_hull=999, enemy_max_hull=999, enemy_damage=500, bounty_credits=750,
                salvage_commodity="titanium", enemy_shield=0, enemy_max_shield=0,
                faction_id="void_corsairs", special_ability="none",
            )
            engine = SimulationEngine(seed=4)
            engine.state = engine._clone_state(
                ship=engine._clone_ship(hull=5, shield=0, fuel=20, credits=100),
                active_combat=combat,
            )
            engine.rng.random = lambda: 0.99
            ok, msg = engine.combat_action(action)
            self.assertTrue(ok)
            self.assertIn("DEFEAT", msg)
            self.assertIsNone(engine.state.active_combat, action)
            self.assertEqual(engine.state.ship.hull, 0)
            self.assertEqual(engine.state.ship.credits, 100)
            self.assertEqual(engine.state.ship.fuel, 17 if action == "evasive_burn" else 20)
            self.assertTrue(engine.state.time.is_paused)

    def test_a_destroyed_ship_cannot_tick_back_to_life(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(hull=0))
        report = engine.tick(5)
        self.assertTrue(report.get("destroyed"))
        self.assertEqual(engine.state.ship.hull, 0)
        ok, msg = engine.use_character_ability("emergency_repair")
        self.assertFalse(ok)
        self.assertIn("destroyed", msg.lower())

    def test_zero_hull_ends_combat_as_a_defeat_without_bounty(self):
        combat = CombatEncounter(
            id="balance_lethal", enemy_name="Lethal Test Frame", enemy_class="Dreadnought",
            enemy_hull=999, enemy_max_hull=999, enemy_damage=500, bounty_credits=2500,
            salvage_commodity="titanium", enemy_shield=0, enemy_max_shield=0,
            faction_id="void_corsairs", special_ability="none",
        )
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(hull=100, shield=0, credits=0),
            active_combat=combat,
        )
        ok, msg = engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertIn("DEFEAT", msg)
        self.assertIsNone(engine.state.active_combat)
        self.assertEqual(engine.state.ship.hull, 0)
        self.assertEqual(engine.state.ship.credits, 0)


class TestEvasiveBurnDiscipline(unittest.TestCase):
    def _engine(self, fuel=20, streak=5, combo=3):
        engine = SimulationEngine(seed=42)
        combat = CombatEncounter(
            id="disengage_test",
            enemy_name="Corsair Interceptor",
            enemy_class="Light Raider",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=12,
            bounty_credits=400,
            salvage_commodity="fuel_cells",
            enemy_shield=40,
            enemy_max_shield=40,
            faction_id="outlaw_corsairs",
            special_ability="none",
        )
        with engine.lock:
            engine.state = engine._clone_state(
                ship=engine._clone_ship(fuel=fuel, streak=streak, tactical_combo=combo),
                active_combat=combat,
            )
        return engine

    def test_successful_evasive_burn_costs_fuel_and_resets_streak(self):
        engine = self._engine()
        with patch.object(engine.rng, "random", return_value=0.0):
            ok, msg = engine.combat_action("evasive_burn")
        self.assertTrue(ok, msg)
        self.assertIsNone(engine.state.active_combat)
        self.assertEqual(engine.state.ship.fuel, 17)
        self.assertEqual(engine.state.ship.streak, 1)
        self.assertEqual(engine.state.ship.tactical_combo, 0)
        self.assertIn("streak", msg.lower())

    def test_failed_evasive_burn_still_burns_fuel_and_keeps_combat(self):
        engine = self._engine()
        with patch.object(engine.rng, "random", return_value=0.99):
            ok, _msg = engine.combat_action("evasive_burn")
        self.assertTrue(ok)
        self.assertIsNotNone(engine.state.active_combat)
        self.assertEqual(engine.state.ship.fuel, 17)

    def test_evasive_burn_requires_fuel(self):
        engine = self._engine(fuel=2)
        ok, msg = engine.combat_action("evasive_burn")
        self.assertFalse(ok)
        self.assertIn("fuel", msg.lower())
        self.assertIsNotNone(engine.state.active_combat)
        self.assertEqual(engine.state.ship.fuel, 2)


class TestVoidResonance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _traversal(started, arrival, resonance=0.0, stability=100.0):
        return VoidTraversalState(
            origin_system_id="cygnus_x1",
            destination_system_id="golconda",
            started_tick=started,
            arrival_tick=arrival,
            duration_ticks=max(1, arrival - started),
            stability=stability,
            resonance=resonance,
        )

    def _set_void_ship(self, traversal, credits=10_000, visited=("sol",)):
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(
                    credits=credits,
                    crew=(),
                    fleet_drones=(),
                    void_traversal=traversal,
                ),
                visited_systems=visited,
            )

    def test_resonance_defaults_and_roundtrips(self):
        legacy = {
            "origin_system_id": "cygnus_x1",
            "destination_system_id": "golconda",
            "started_tick": 0,
            "arrival_tick": 4,
            "duration_ticks": 4,
            "stability": 90.0,
            "storms_weathered": 2,
        }
        self.assertEqual(VoidTraversalState.from_dict(legacy).resonance, 0.0)

        traversal = self._traversal(2, 7, resonance=3.5)
        self.assertEqual(VoidTraversalState.from_dict(traversal.to_dict()), traversal)
        self.assertIn("resonance", traversal.to_dict())

    def test_storm_accumulates_resonance_with_low_stability_premium(self):
        tick = self.engine.state.time.tick
        self._set_void_ship(self._traversal(tick, tick + 3, stability=80.0))
        with patch.object(self.engine.rng, "random", return_value=0.0):
            self.engine.tick(1)
        self.assertEqual(self.engine.state.ship.void_traversal.resonance, 1.0)

        self._set_void_ship(self._traversal(tick, tick + 3, stability=25.0))
        with patch.object(self.engine.rng, "random", return_value=0.0):
            self.engine.tick(1)
        self.assertEqual(self.engine.state.ship.void_traversal.resonance, 2.0)

    def test_status_projects_resonance_payout(self):
        tick = self.engine.state.time.tick
        self._set_void_ship(self._traversal(tick - 1, tick + 3, resonance=3.0))
        status = self.engine.void_status()
        self.assertEqual(status["resonance"], 3.0)
        self.assertEqual(status["projected_resonance_credits"], 360)
        self.assertEqual(status["projected_resonance_xp"], 45)

    def test_arrival_pays_resonance_credits_and_xp(self):
        tick = self.engine.state.time.tick
        self._set_void_ship(
            self._traversal(tick, tick + 2, resonance=4.0, stability=130.0),
            visited=("sol", "golconda"),
        )
        credits_before = self.engine.state.ship.credits
        with patch.object(self.engine.rng, "random", return_value=0.99):
            self.engine.tick(2)
        self.assertIsNone(self.engine.state.ship.void_traversal)
        self.assertEqual(self.engine.state.ship.credits - credits_before, 480)
        self.assertTrue(any("resonance" in line.lower() for line in self.engine.state.ship.flight_log))

    def test_emergency_emerge_pays_only_prorated_resonance(self):
        tick = self.engine.state.time.tick
        self._set_void_ship(self._traversal(tick - 2, tick + 2, resonance=4.0))
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.void_emerge()
        self.assertTrue(ok, msg)
        self.assertEqual(self.engine.state.ship.credits - credits_before, 120)
        self.assertIn("resonance", msg.lower())
        self.assertIsNone(self.engine.state.ship.void_traversal)

    def test_cli_and_cockpit_expose_resonance(self):
        tick = self.engine.state.time.tick
        self._set_void_ship(self._traversal(tick - 1, tick + 3, resonance=2.0))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(cmd_void(self.engine, self.storage, ["void"]), 0)
        self.assertIn("Resonance", buffer.getvalue())

        app_js = (Path(__file__).parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("RESONANCE", app_js)
        self.assertIn("traversal.resonance", app_js)


if __name__ == "__main__":
    unittest.main()
