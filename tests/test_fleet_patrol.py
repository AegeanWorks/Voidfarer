"""Fleet assignment: only local escorts fight, while remote patrols cut piracy."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import fleet_ships_in_system
from voidfarer.models import CombatEncounter, FleetShip
from voidfarer.pirates import pirate_risk


def _escort(ship_id, system_id, hull=90, shield=60):
    return FleetShip(
        id=ship_id,
        name=f"Escort {ship_id}",
        ship_class="Escort Corvette",
        role="escort",
        hull=hull,
        max_hull=hull,
        shield=shield,
        max_shield=shield,
        damage=18,
        evasion=0.0,
        assigned_system_id=system_id,
    )


class FleetAssignmentTest(unittest.TestCase):
    def test_only_local_escorts_are_selected_for_battle(self):
        ships = (_escort("local", "sol"), _escort("remote", "vega"))
        self.assertEqual([ship.id for ship in fleet_ships_in_system(ships, "sol")], ["local"])

    def test_remote_escort_takes_no_damage_and_adds_no_local_damage(self):
        combat = CombatEncounter(
            id="patrol_test",
            enemy_name="Marauder",
            enemy_class="Frigate",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=100,
            bounty_credits=100,
            salvage_commodity="titanium",
            enemy_shield=0,
            enemy_max_shield=0,
            faction_id="outlaw_corsairs",
            special_ability="none",
        )
        engine = SimulationEngine(seed=42)
        local = _escort("local", "sol")
        remote = _escort("remote", "vega")
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                hull=100,
                shield=100,
                fleet_ships=(local, remote),
            ),
            active_combat=combat,
        )
        engine.rng.random = lambda: 0.5
        before_enemy = engine.state.active_combat.enemy_hull
        ok, message = engine.combat_action("fire_lasers")
        self.assertTrue(ok, message)
        self.assertLess(engine.state.active_combat.enemy_hull, before_enemy,
                        "the local escort must add coordinated damage")
        by_id = {ship.id: ship for ship in engine.state.ship.fleet_ships}
        self.assertEqual(by_id["remote"], remote,
                         "a ship assigned elsewhere must not take local battle damage")
        self.assertLess(
            by_id["local"].shield + by_id["local"].hull,
            local.shield + local.hull,
            "the local escort must screen incoming fire",
        )

    def test_remote_escort_contributes_no_damage(self):
        combat = CombatEncounter(
            id="remote_only",
            enemy_name="Marauder",
            enemy_class="Frigate",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=10,
            bounty_credits=100,
            salvage_commodity="titanium",
            enemy_shield=0,
            enemy_max_shield=0,
            faction_id="outlaw_corsairs",
            special_ability="none",
        )
        engine = SimulationEngine(seed=42)
        remote = _escort("remote", "vega")
        engine.state = engine._clone_state(
            ship=engine._clone_ship(fleet_ships=(remote,)),
            active_combat=combat,
        )
        engine.rng.random = lambda: 0.5
        ok, message = engine.combat_action("fire_lasers")
        self.assertTrue(ok, message)
        self.assertNotIn("Escort wing added", message)
        self.assertEqual(engine.state.ship.fleet_ships[0], remote)
        self.assertEqual(engine.state.ship.fleet_ships[0].experience, remote.experience)

    def test_assigned_patrols_reduce_pirate_risk(self):
        engine = SimulationEngine(seed=42)
        system = engine.current_system
        unpatrolled = pirate_risk(system, 0)
        patrolled = pirate_risk(system, 0, patrol_escorts=2)
        self.assertLess(patrolled.chance, unpatrolled.chance)
        self.assertIn("patrol", patrolled.reason)

    def test_fleet_report_separates_local_and_total_damage(self):
        engine = SimulationEngine(seed=42)
        local = _escort("local", engine.state.ship.current_system_id)
        remote = _escort("remote", "vega")
        engine.state = engine._clone_state(
            ship=engine._clone_ship(fleet_ships=(local, remote))
        )
        report = engine.get_fleet_manager_report()
        self.assertEqual(report["local_damage"], local.damage)
        self.assertGreater(report["total_damage"], report["local_damage"])


if __name__ == "__main__":
    unittest.main()
