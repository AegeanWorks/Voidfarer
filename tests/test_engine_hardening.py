"""Regression tests for audit-driven engine hardening.

Each test pins a defect found in the project audit: invalid service amounts,
relic maximum-stat preservation, system metadata loss, upgrade slot ghosts,
cargo-capacity bypass, faction-standing divergence, and invalid drone targets.
"""

import unittest
from unittest.mock import patch

from voidfarer.engine import SimulationEngine
from voidfarer.inventory import calculate_cargo_volume
from voidfarer.models import FleetDrone, PrecursorRelic
from voidfarer.story import STORY_RELICS


class EngineHardeningTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def _set_ship(self, **kwargs):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(**kwargs))

    def _orbit_station(self):
        ok, _ = self.engine.orbit("sol_body_1")
        self.assertTrue(ok)

    def test_repair_rejects_zero_and_negative_amounts(self):
        self._orbit_station()
        self._set_ship(hull=50, credits=1000)
        before = self.engine.state.ship

        for amount in (0, -25):
            ok, _ = self.engine.repair_hull(amount)
            self.assertFalse(ok)
            self.assertEqual(self.engine.state.ship.hull, before.hull)
            self.assertEqual(self.engine.state.ship.credits, before.credits)

    def test_refuel_rejects_zero_and_negative_amounts(self):
        self._orbit_station()
        self._set_ship(fuel=20, credits=1000)
        before = self.engine.state.ship

        for amount in (0, -25):
            ok, _ = self.engine.refuel(amount)
            self.assertFalse(ok)
            self.assertEqual(self.engine.state.ship.fuel, before.fuel)
            self.assertEqual(self.engine.state.ship.credits, before.credits)

    def test_upgrade_recompute_preserves_relic_max_hull(self):
        self._orbit_station()
        relic = STORY_RELICS["relic_cadet_wings"]
        self._set_ship(max_hull=115, hull=115, relics=(relic,), credits=5000)

        ok, _ = self.engine.buy_upgrade("composite_armor_mk1")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.max_hull, 140)
        self.assertEqual(self.engine.state.ship.hull, 140)

    def test_chassis_purchase_preserves_relic_max_shield(self):
        self._orbit_station()
        relic = STORY_RELICS["relic_humanitarian_medal"]
        self._set_ship(max_shield=135, shield=135, relics=(relic,), credits=20000)

        ok, _ = self.engine.buy_ship_chassis("chronos_explorer")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.max_shield, 175)

    def test_scan_awards_random_max_hull_relic_immediately(self):
        relic = PrecursorRelic(
            id="relic_test_hull",
            name="Test Hull Relic",
            rarity="rare",
            description="+15 maximum hull.",
            passive_stat="max_hull",
            stat_multiplier=15.0,
        )
        self._orbit_station()
        with patch("voidfarer.engine.roll_relic_drop", return_value=(relic, False)):
            ok, _, _ = self.engine.scan()
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.max_hull, 115)
        self.assertEqual(self.engine.state.ship.hull, 115)

    def test_scan_and_step_preserve_dominant_corp(self):
        self._orbit_station()
        before = self.engine.state.systems["sol"].dominant_corp
        self.assertIsNotNone(before)

        self.engine.scan()
        self.assertEqual(self.engine.state.systems["sol"].dominant_corp, before)

        self.engine.step_orbits(1.0)
        self.assertEqual(self.engine.state.systems["sol"].dominant_corp, before)

    def test_replacing_an_occupied_upgrade_slot_is_rejected(self):
        self._orbit_station()
        ok, _ = self.engine.buy_upgrade("deflector_array_mk1")
        self.assertTrue(ok)
        before = self.engine.state.ship

        ok_replace, msg = self.engine.buy_upgrade("tachyon_shield_matrix")
        self.assertFalse(ok_replace)
        self.assertIn("slot", msg.lower())
        self.assertEqual(self.engine.state.ship.equipped_upgrades["shields"], "deflector_array_mk1")
        self.assertEqual(self.engine.state.ship.upgrades, before.upgrades)
        self.assertEqual(self.engine.state.ship.credits, before.credits)

    def test_drone_harvest_rejects_when_cargo_hold_is_full(self):
        cargo = {"titanium": 20}
        self.assertEqual(calculate_cargo_volume(cargo), 40)
        drone = FleetDrone(
            id="drone_mining_99",
            name="Mining Drone",
            drone_type="mining",
            assigned_system_id="sol",
            cargo_accumulated=5,
            credits_accumulated=100,
        )
        self._set_ship(cargo=cargo, cargo_capacity=40, fleet_drones=(drone,))
        before = self.engine.state.ship

        ok, _, info = self.engine.collect_drone_yield("drone_mining_99")
        self.assertFalse(ok)
        self.assertEqual(info["cargo"], 0)
        self.assertEqual(self.engine.state.ship.cargo, before.cargo)
        self.assertEqual(self.engine.state.ship.fleet_drones[0].cargo_accumulated, 5)

    def test_repeat_scan_of_surveyed_body_awards_no_bounty(self):
        self._orbit_station()
        ok, _, _ = self.engine.scan()
        self.assertTrue(ok)
        credits = self.engine.state.ship.credits

        ok_again, msg, info = self.engine.scan()
        self.assertFalse(ok_again)
        self.assertIn("already", msg)
        self.assertEqual(info, {})
        self.assertEqual(self.engine.state.ship.credits, credits)

    def test_story_choice_updates_faction_standing(self):
        before = self.engine.state.ship.faction_standings.get("sol_coalition", 0)
        ok, _ = self.engine.make_story_choice("choice_vance_telemetry")
        self.assertTrue(ok)
        self.assertGreater(
            self.engine.state.ship.faction_standings.get("sol_coalition", 0), before
        )

    def test_buy_drone_rejects_unknown_system(self):
        self._orbit_station()
        credits = self.engine.state.ship.credits
        drones = len(self.engine.state.ship.fleet_drones)

        ok, _ = self.engine.buy_drone("mining", "not_a_system")
        self.assertFalse(ok)
        self.assertEqual(self.engine.state.ship.credits, credits)
        self.assertEqual(len(self.engine.state.ship.fleet_drones), drones)

    def test_cargo_grant_clamps_to_free_volume(self):
        cargo = {"titanium": 19}
        granted, overflow = self.engine._grant_cargo(cargo, "fuel_cells", 3)
        self.assertEqual(granted, 2)
        self.assertEqual(overflow, 1)
        self.assertEqual(cargo["fuel_cells"], 2)

    def test_combat_salvage_respects_full_cargo_hold(self):
        from voidfarer.models import CombatEncounter
        combat = CombatEncounter(
            id="full_hold_combat", enemy_name="Wreck", enemy_class="Drone",
            enemy_hull=1, enemy_max_hull=1, enemy_damage=0, bounty_credits=5,
            salvage_commodity="titanium",
        )
        self._set_ship(cargo={"titanium": 20}, cargo_capacity=40)
        self.engine.state = self.engine._clone_state(active_combat=combat)
        ok, msg = self.engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.cargo.get("titanium"), 20)
        self.assertIn("jettisoned", msg)
