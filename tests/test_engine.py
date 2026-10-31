"""Unit tests for simulation engine state transitions, flight, upgrades, fleet, and combat."""

import unittest
from voidfarer.engine import SimulationEngine
from voidfarer.models import AnomalyChoice, AnomalyEncounter, CombatEncounter, FleetDrone
from voidfarer.upgrades import get_upgrade


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_initial_state(self):
        self.assertEqual(self.engine.state.ship.current_system_id, "sol")
        self.assertEqual(self.engine.state.ship.hull, 100)
        self.assertEqual(self.engine.state.ship.fuel, 60)
        self.assertEqual(self.engine.state.ship.credits, 2000)
        self.assertGreaterEqual(len(self.engine.state.ship.fleet_drones), 1)

    def test_jump_valid_and_invalid(self):
        cur_sys = self.engine.current_system
        linked_target = cur_sys.connections[0]

        fuel_before = self.engine.state.ship.fuel
        ok, msg = self.engine.jump(linked_target)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.current_system_id, linked_target)
        self.assertLess(self.engine.state.ship.fuel, fuel_before)
        self.assertEqual(self.engine.state.stats["jumps"], 1)

        ok2, msg2 = self.engine.jump("non_existent_void_system")
        self.assertFalse(ok2)

    def test_orbit_and_scan(self):
        body_id = "sol_body_1"
        ok, msg = self.engine.orbit(body_id)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.orbiting_body_id, body_id)

        credits_before = self.engine.state.ship.credits
        ok_scan, msg_scan, info = self.engine.scan()
        self.assertTrue(ok_scan)
        self.assertGreater(self.engine.state.ship.credits, credits_before)
        self.assertEqual(self.engine.state.stats["scans"], 1)

    def test_power_routing(self):
        ok, msg = self.engine.route_power(40, 20, 20, 20)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.power.engines, 40)

        ok_fail, _ = self.engine.route_power(50, 50, 10, 0)
        self.assertFalse(ok_fail)

    def test_trade_buy_and_sell(self):
        self.engine.orbit("sol_body_1")
        credits_start = self.engine.state.ship.credits

        ok, msg = self.engine.trade("fuel_cells", 2, is_buy=True)
        self.assertTrue(ok)
        self.assertLess(self.engine.state.ship.credits, credits_start)

        credits_after_buy = self.engine.state.ship.credits
        ok_sell, msg_sell = self.engine.trade("fuel_cells", 1, is_buy=False)
        self.assertTrue(ok_sell)
        self.assertGreater(self.engine.state.ship.credits, credits_after_buy)

    def test_upgrades_purchase_and_bonus(self):
        self.engine.orbit("sol_body_1")
        start_cap = self.engine.state.ship.cargo_capacity

        ok, msg = self.engine.buy_upgrade("subspace_cargo_pods")
        self.assertTrue(ok)
        self.assertIn("subspace_cargo_pods", self.engine.state.ship.equipped_upgrades.values())
        self.assertEqual(self.engine.state.ship.cargo_capacity, start_cap + 20)

    def test_fleet_drone_operations(self):
        self.engine.orbit("sol_body_1")
        credits_before = self.engine.state.ship.credits

        # Buy scout drone
        ok, msg = self.engine.buy_drone("scout", "alpha_centauri")
        self.assertTrue(ok)
        self.assertLess(self.engine.state.ship.credits, credits_before)

        # Deploy drone
        scout = next(d for d in self.engine.state.ship.fleet_drones if d.drone_type == "scout")
        ok_dep, msg_dep = self.engine.deploy_drone(scout.id, "sirius")
        self.assertTrue(ok_dep)

        # Harvest yield test with simulated accumulation
        updated_drones = [
            FleetDrone(id=scout.id, name=scout.name, drone_type="scout", assigned_system_id="sirius", credits_accumulated=250)
        ]
        self.engine.state = self.engine.state.__class__(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=self.engine.state.ship.__class__(
                commander_name=self.engine.state.ship.commander_name,
                callsign=self.engine.state.ship.callsign,
                ship_class=self.engine.state.ship.ship_class,
                hull=self.engine.state.ship.hull,
                max_hull=self.engine.state.ship.max_hull,
                shield=self.engine.state.ship.shield,
                max_shield=self.engine.state.ship.max_shield,
                fuel=self.engine.state.ship.fuel,
                max_fuel=self.engine.state.ship.max_fuel,
                credits=self.engine.state.ship.credits,
                cargo=self.engine.state.ship.cargo,
                cargo_capacity=self.engine.state.ship.cargo_capacity,
                current_system_id=self.engine.state.ship.current_system_id,
                orbiting_body_id=self.engine.state.ship.orbiting_body_id,
                power=self.engine.state.ship.power,
                upgrades=self.engine.state.ship.upgrades,
                equipped_upgrades=self.engine.state.ship.equipped_upgrades,
                fleet_drones=tuple(updated_drones),
                flight_log=self.engine.state.ship.flight_log,
            ),
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=None,
            active_combat=None,
            stats=self.engine.state.stats,
        )

        ok_h, msg_h, info = self.engine.collect_drone_yield(scout.id)
        self.assertTrue(ok_h)
        self.assertEqual(info["credits"], 250)

    def test_combat_resolution_victory_and_flee(self):
        # Set active combat
        combat = CombatEncounter(
            id="combat_test",
            enemy_name="Outlaw Sentry",
            enemy_class="Drone",
            enemy_hull=25,
            enemy_max_hull=25,
            enemy_damage=10,
            bounty_credits=400,
        )
        self.engine.state = self.engine.state.__class__(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=self.engine.state.ship,
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=None,
            active_combat=combat,
            stats=self.engine.state.stats,
        )

        # Firing lasers deals >= 20 dmg, destroying 25 HP enemy
        ok, msg = self.engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertIn("VICTORY", msg)
        self.assertIsNone(self.engine.state.active_combat)
        self.assertEqual(self.engine.state.stats["combat_victories"], 1)

    def test_contracts_progression_and_claiming(self):
        self.assertGreaterEqual(len(self.engine.state.ship.active_contracts), 1)
        contract = self.engine.state.ship.active_contracts[0]

        # Artificially set contract as fulfilled
        fulfilled = contract.__class__(
            id=contract.id,
            title=contract.title,
            description=contract.description,
            category=contract.category,
            target_count=contract.target_count,
            current_count=contract.target_count,
            reward_credits=500,
            reward_xp=150,
            reward_relic_tier="common",
            completed=True,
        )
        remaining = [c for c in self.engine.state.ship.active_contracts if c.id != contract.id] + [fulfilled]
        self.engine.state = self.engine.state.__class__(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=self.engine._clone_ship(active_contracts=tuple(remaining)),
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=None,
            active_combat=None,
            stats=self.engine.state.stats,
        )

        creds_before = self.engine.state.ship.credits
        xp_before = self.engine.state.ship.mastery.xp
        ok, msg, info = self.engine.claim_contract(fulfilled.id)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.credits, creds_before + 500)
        self.assertEqual(self.engine.state.ship.mastery.xp, xp_before + 150)
        self.assertIn("new_contract", info)
        self.assertIsNotNone(info["relic"])
        self.assertEqual(len(self.engine.state.ship.active_contracts), 5)

    def test_pilot_mastery_and_talents(self):
        # Promote pilot by granting talent point
        promoted_mastery = self.engine.state.ship.mastery.__class__(
            level=2,
            xp=200,
            next_level_xp=750,
            talent_points=1,
            specializations=(),
        )
        self.engine.state = self.engine.state.__class__(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=self.engine._clone_ship(mastery=promoted_mastery),
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=None,
            active_combat=None,
            stats=self.engine.state.stats,
        )

        # Unlock talent
        ok, msg = self.engine.unlock_talent("void_cartographer")
        self.assertTrue(ok)
        self.assertIn("void_cartographer", self.engine.state.ship.mastery.specializations)
        self.assertEqual(self.engine.state.ship.mastery.talent_points, 0)

        # Fail when 0 points remaining
        ok_fail, _ = self.engine.unlock_talent("dreadnought_tactics")
        self.assertFalse(ok_fail)

    def test_expedition_streak_and_combos(self):
        # Consecutive jump increments streak
        conn = self.engine.current_system.connections[0]
        self.engine.jump(conn)
        self.assertGreaterEqual(self.engine.state.ship.streak, 2)

        # Initiate combat and test combo overcharge
        combat = CombatEncounter(
            id="combat_boss",
            enemy_name="Dread Raider",
            enemy_class="Cruiser",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=5,
            bounty_credits=1000,
        )
        self.engine.state = self.engine.state.__class__(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=self.engine._clone_ship(shield=100),
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=None,
            active_combat=combat,
            stats=self.engine.state.stats,
        )

        # Fire 1
        self.engine.combat_action("fire_lasers")
        self.assertEqual(self.engine.state.ship.tactical_combo, 1)

        # Fire 2
        self.engine.combat_action("fire_lasers")
        self.assertEqual(self.engine.state.ship.tactical_combo, 2)

        # Fire 3 triggers overcharge crit
        ok3, msg3 = self.engine.combat_action("fire_lasers")
        self.assertTrue(ok3)
        self.assertIn("TACTICAL OVERCHARGE", msg3)

        # Fleeing resets streak and combo
        ok_flee, _ = self.engine.combat_action("flee")
        self.assertTrue(ok_flee)
        self.assertEqual(self.engine.state.ship.streak, 1)
        self.assertEqual(self.engine.state.ship.tactical_combo, 0)

    def test_tick_decays_combat_ability_cooldown(self):
        combat = CombatEncounter(
            id="combat_tick",
            enemy_name="Apex Raider",
            enemy_class="Corsair",
            enemy_hull=80,
            enemy_max_hull=80,
            enemy_damage=12,
            bounty_credits=650,
            special_ability="alpha_strike",
            ability_cooldown=2,
            telegraphed_action="Charging alpha strike",
        )
        self.engine.state = self.engine._clone_state(active_combat=combat)

        # Old code rebuilt the encounter with non-existent fields and raised TypeError on any tick.
        self.engine.tick(1)
        self.assertEqual(self.engine.state.active_combat.ability_cooldown, 1)
        self.assertEqual(self.engine.state.active_combat.enemy_name, "Apex Raider")
        self.assertEqual(self.engine.state.active_combat.enemy_hull, 80)

        self.engine.tick(5)
        self.assertEqual(self.engine.state.active_combat.ability_cooldown, 0)

    def test_trade_respects_cargo_volume_not_just_units(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=100000, cargo={})
        )

        # Titanium occupies 2 hold units each: 21 units (42 volume) exceed the 40-unit hold.
        ok, msg = self.engine.trade("titanium", 21, is_buy=True)
        self.assertFalse(ok)
        self.assertIn("capacity", msg.lower())

        ok, _ = self.engine.trade("titanium", 15, is_buy=True)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.cargo.get("titanium"), 15)

    def test_available_chassis_excludes_current_ship(self):
        snapshot = self.engine.get_status_snapshot()
        available_ids = {c["id"] for c in snapshot["available_chassis"]}
        self.assertNotIn("vanguard_scout", available_ids)
        self.assertIn("orion_hauler", available_ids)

    def test_starter_chassis_cannot_be_repurchased(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=100000))

        ok, _ = self.engine.buy_ship_chassis("orion_hauler")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.ship_class, "Bulk Merchant Hauler")

        # The zero-cost starter hull must never be "purchased" for free repairs/refuels.
        ok, msg = self.engine.buy_ship_chassis("vanguard_scout")
        self.assertFalse(ok)
        self.assertIn("starter", msg.lower())

    def test_sell_upgrade_removes_module_name_from_manifest(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=100000))

        module_name = get_upgrade("subspace_cargo_pods").name
        ok, _ = self.engine.buy_upgrade("subspace_cargo_pods")
        self.assertTrue(ok)
        self.assertIn(module_name, self.engine.state.ship.upgrades)

        ok, _ = self.engine.sell_upgrade("cargo")
        self.assertTrue(ok)
        self.assertNotIn(module_name, self.engine.state.ship.upgrades)

    def test_buy_item_requires_station_and_consumable(self):
        # Undocked: rejected cleanly.
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id=None)
        )
        ok, _ = self.engine.buy_item("nanite_repair_paste")
        self.assertFalse(ok)

        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=100000))

        # Commodities are not sold at the consumable terminal.
        ok, _ = self.engine.buy_item("titanium")
        self.assertFalse(ok)

        credits_before = self.engine.state.ship.credits
        ok, _ = self.engine.buy_item("nanite_repair_paste", 2)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.cargo.get("nanite_repair_paste"), 2)
        self.assertEqual(self.engine.state.ship.credits, credits_before - 500)

    def test_buy_ship_chassis_rejects_if_cargo_exceeds_new_capacity(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                ship_class="Bulk Merchant Hauler",
                cargo_capacity=160,
                cargo={"titanium": 70},
                credits=100000,
            )
        )
        ok, msg = self.engine.buy_ship_chassis("solaris_gunship")
        self.assertFalse(ok)
        self.assertIn("overflow", msg.lower())

    def test_sell_upgrade_rejects_if_cargo_exceeds_reduced_capacity(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=100000,
                equipped_upgrades={"cargo": "subspace_cargo_pods"},
                upgrades=("Subspace Cargo Pods",),
                cargo_capacity=60,
                cargo={"titanium": 25},
            )
        )
        ok, msg = self.engine.sell_upgrade("cargo")
        self.assertFalse(ok)
        self.assertIn("overflow", msg.lower())

    def test_remove_ship_mod_rejects_if_cargo_exceeds_reduced_capacity(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=100000,
                ship_mods={"cargo_bay": "mod_expanded_cargo_bay"},
                cargo_capacity=65,
                cargo={"titanium": 28},
            )
        )
        ok, msg = self.engine.remove_ship_mod("cargo_bay")
        self.assertFalse(ok)
        self.assertIn("overflow", msg.lower())

    def test_quantum_travel_fuel_cost_applies_fuel_efficiency_bonuses(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fuel=100, max_fuel=100, equipped_upgrades={})
        )
        ok, _ = self.engine.start_travel("sol_body_2", mode="quantum")
        self.assertTrue(ok)
        base_burn = 100 - self.engine.state.ship.fuel

        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fuel=100, max_fuel=100, equipped_upgrades={"engines": "warp_booster_mk1"})
        )
        ok, _ = self.engine.start_travel("sol_body_2", mode="quantum")
        self.assertTrue(ok)
        boosted_burn = 100 - self.engine.state.ship.fuel
        self.assertLess(boosted_burn, base_burn)


if __name__ == "__main__":
    unittest.main()
