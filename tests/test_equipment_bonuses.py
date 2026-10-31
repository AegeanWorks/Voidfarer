"""Regression tests for hardware module stat bonuses and chassis specialty perks.

ADR-010 deferred wiring the inert ``stat_bonus`` entries of the newer hardware
modules and the chassis perks. These tests pin both the pure aggregation helper
and the engine surfaces that must consume it: jump fuel, sensor bounties, trade
margins, combat damage, passive shield regeneration, and pirate encounter ECM.
"""

import unittest
from unittest.mock import patch

from voidfarer.engine import SimulationEngine
from voidfarer.models import CombatEncounter
from voidfarer.upgrades import calculate_equipment_bonuses


class TestEquipmentBonusAggregation(unittest.TestCase):
    """Verify the pure aggregation rules without touching engine state."""

    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def _bonuses(self, **ship_kwargs):
        ship = self.engine._clone_ship(**ship_kwargs)
        return calculate_equipment_bonuses(ship)

    def test_bare_starter_ship_has_neutral_bonuses(self):
        bonuses = self._bonuses()
        self.assertEqual(bonuses["fuel_efficiency"], 1.0)
        self.assertEqual(bonuses["scan_mult"], 1.0)
        self.assertEqual(bonuses["relic_find"], 0.0)
        self.assertEqual(bonuses["combat_damage"], 0.0)
        self.assertEqual(bonuses["evasion"], 0.0)
        self.assertEqual(bonuses["shield_regen"], 0.0)
        self.assertEqual(bonuses["pirate_evasion"], 0.0)
        self.assertEqual(bonuses["trade_margin"], 0.0)

    def test_engine_module_reduces_fuel_multiplier(self):
        bonuses = self._bonuses(equipped_upgrades={"engines": "warp_booster_mk2"})
        self.assertAlmostEqual(bonuses["fuel_efficiency"], 0.65)

    def test_sensor_modules_add_scan_and_relic_bonuses(self):
        deep_core = self._bonuses(equipped_upgrades={"sensors": "deep_core_scanner"})
        self.assertAlmostEqual(deep_core["scan_mult"], 1.5)

        tachyon = self._bonuses(equipped_upgrades={"sensors": "tachyon_resonance_suite_mk3"})
        self.assertAlmostEqual(tachyon["scan_mult"], 2.2)
        self.assertAlmostEqual(tachyon["relic_find"], 0.15)

    def test_utility_modules_expose_shield_and_ecm_bonuses(self):
        regen = self._bonuses(equipped_upgrades={"shields": "reactive_shield_booster"})
        self.assertAlmostEqual(regen["shield_regen"], 5.0)

        ecm = self._bonuses(equipped_upgrades={"utility": "ecm_scrambler_suite"})
        self.assertAlmostEqual(ecm["pirate_evasion"], 0.40)

        afterburners = self._bonuses(equipped_upgrades={"engines": "sublight_afterburners"})
        self.assertAlmostEqual(afterburners["evasion"], 0.15)

    def test_chassis_specialty_perks_are_mapped(self):
        orion = self._bonuses(ship_class="Bulk Merchant Hauler")
        self.assertAlmostEqual(orion["trade_margin"], 0.15)

        chronos = self._bonuses(ship_class="Long-Range Science Vessel")
        self.assertAlmostEqual(chronos["scan_mult"], 1.5)

        solaris = self._bonuses(ship_class="Tactical Missile Gunship")
        self.assertAlmostEqual(solaris["combat_damage"], 20.0)

        archon = self._bonuses(ship_class="Command Battlecruiser")
        self.assertAlmostEqual(archon["combat_damage"], 35.0)


class TestEngineEquipmentIntegration(unittest.TestCase):
    """Verify the engine actually consumes the aggregated bonuses."""

    def _jump_fuel_used(self, equipped):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(equipped_upgrades=equipped))
        target = engine.current_system.connections[0]
        before = engine.state.ship.fuel
        ok, _ = engine.jump(target)
        self.assertTrue(ok)
        return before - engine.state.ship.fuel

    def test_warp_booster_reduces_jump_fuel_burn(self):
        baseline = self._jump_fuel_used({})
        boosted = self._jump_fuel_used({"engines": "warp_booster_mk2"})
        self.assertLess(boosted, baseline)

    def _scan_bounty(self, equipped):
        engine = SimulationEngine(seed=42)
        engine.orbit("sol_body_1")
        engine.state = engine._clone_state(ship=engine._clone_ship(equipped_upgrades=equipped))
        ok, _, info = engine.scan()
        self.assertTrue(ok)
        return info["bounty"]

    def test_deep_core_scanner_increases_scan_bounty(self):
        baseline = self._scan_bounty({})
        boosted = self._scan_bounty({"sensors": "deep_core_scanner"})
        self.assertEqual(boosted, int(baseline * 1.5))

    def _sell_revenue(self, ship_class):
        engine = SimulationEngine(seed=42)
        engine.orbit("sol_body_1")
        engine.state = engine._clone_state(
            ship=engine._clone_ship(ship_class=ship_class, cargo={"titanium": 5})
        )
        before = engine.state.ship.credits
        ok, _ = engine.trade("titanium", 1, is_buy=False)
        self.assertTrue(ok)
        return engine.state.ship.credits - before

    def test_freighter_chassis_boosts_trade_margin(self):
        baseline = self._sell_revenue("Corvette Scout")
        boosted = self._sell_revenue("Bulk Merchant Hauler")
        self.assertGreater(boosted, baseline)
        self.assertAlmostEqual(boosted / baseline, 1.15, delta=0.01)

    def _enemy_hull_after_shot(self, equipped, ship_class):
        engine = SimulationEngine(seed=42)
        combat = CombatEncounter(
            id="combat_bonus_test",
            enemy_name="Target Drone",
            enemy_class="Drone",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=0,
            bounty_credits=10,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(equipped_upgrades=equipped, ship_class=ship_class),
            active_combat=combat,
        )
        ok, _ = engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertIsNotNone(engine.state.active_combat)
        return engine.state.active_combat.enemy_hull

    def test_weapon_module_and_gunship_chassis_add_combat_damage(self):
        baseline = self._enemy_hull_after_shot({}, "Corvette Scout")
        module = self._enemy_hull_after_shot({"weapons": "plasma_torpedo_mk2"}, "Corvette Scout")
        chassis = self._enemy_hull_after_shot({}, "Tactical Missile Gunship")

        self.assertEqual(baseline - module, 30)
        self.assertEqual(baseline - chassis, 20)

    def _shield_recharged(self, equipped):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(shield=50, equipped_upgrades=equipped)
        )
        return engine.tick(1)["shield_recharged"]

    def test_reactive_shield_regenerator_adds_tick_recharge(self):
        baseline = self._shield_recharged({})
        boosted = self._shield_recharged({"shields": "reactive_shield_booster"})
        self.assertEqual(boosted - baseline, 5)

    def _combat_after_jump(self, equipped):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(current_system_id="cygnus_x1", orbiting_body_id=None, equipped_upgrades=equipped)
        )
        with patch.object(engine.rng, "random", return_value=0.30):
            ok, _ = engine.jump("pulsar_psr")
        self.assertTrue(ok)
        return engine.state.active_combat is not None

    def test_ecm_scrambler_reduces_pirate_encounter_chance(self):
        self.assertTrue(self._combat_after_jump({}))
        self.assertFalse(self._combat_after_jump({"utility": "ecm_scrambler_suite"}))
