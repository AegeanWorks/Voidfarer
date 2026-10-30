"""Fleet squadron roles: screen/strike/support combat tradeoffs."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import (
    build_fleet_ship,
    fleet_damage,
    fleet_evasion_bonus,
    fleet_support_repair,
    normalize_fleet_role,
)
from voidfarer.models import FleetShip


class FleetRoleMathTest(unittest.TestCase):
    def test_default_roles_follow_hull_class(self):
        self.assertEqual(build_fleet_ship("corvette", "sol", 0).tactical_role, "screen")
        self.assertEqual(build_fleet_ship("frigate", "sol", 1).tactical_role, "strike")
        self.assertEqual(build_fleet_ship("cruiser", "sol", 2).tactical_role, "strike")
        self.assertEqual(build_fleet_ship("carrier", "sol", 3).tactical_role, "support")
        self.assertEqual(normalize_fleet_role("nonsense"), "screen")

    def test_roles_trade_damage_against_evasion(self):
        base = build_fleet_ship("corvette", "sol", 0)
        screen = replace(base, tactical_role="screen")
        strike = replace(base, tactical_role="strike")
        support = replace(base, tactical_role="support")
        self.assertGreater(fleet_damage((strike,)), fleet_damage((screen,)))
        self.assertGreater(fleet_damage((screen,)), fleet_damage((support,)))
        self.assertGreater(fleet_evasion_bonus((screen,)), fleet_evasion_bonus((support,)))
        self.assertGreater(fleet_evasion_bonus((support,)), fleet_evasion_bonus((strike,)))

    def test_support_repair_scales_and_ignores_wrecks(self):
        support = replace(
            build_fleet_ship("carrier", "sol", 0), tactical_role="support"
        )
        second = replace(support, id="support_2")
        wreck = replace(support, id="support_3", hull=0, status="destroyed")
        self.assertEqual(fleet_support_repair((support,)), 4)
        self.assertEqual(fleet_support_repair((support, second)), 8)
        self.assertEqual(fleet_support_repair((support, wreck)), 4)


class FleetRoleEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.ship = build_fleet_ship("corvette", "sol", 0)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fleet_ships=(self.ship,))
        )

    def test_set_role_and_report(self):
        ok, message = self.engine.set_fleet_role(self.ship.id, "strike")
        self.assertTrue(ok, message)
        updated = self.engine.state.ship.fleet_ships[0]
        self.assertEqual(updated.tactical_role, "strike")
        self.assertIn("SQUADRON ROLE", message)
        report = self.engine.get_fleet_manager_report()
        self.assertEqual(report["ships"][0]["tactical_role"], "strike")
        self.assertEqual(report["ships"][0]["role_label"], "Strike")

    def test_role_rejects_unknown_and_destroyed(self):
        ok, message = self.engine.set_fleet_role(self.ship.id, "bogus")
        self.assertFalse(ok)
        self.assertIn("screen", message.lower())

        wreck = replace(self.ship, hull=0, status="destroyed")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fleet_ships=(wreck,))
        )
        ok, message = self.engine.set_fleet_role(self.ship.id, "support")
        self.assertFalse(ok)
        self.assertIn("destroyed", message.lower())

    def test_role_change_is_blocked_in_combat(self):
        from voidfarer.models import CombatEncounter

        combat = CombatEncounter(
            id="role_combat",
            enemy_name="Marauder",
            enemy_class="Frigate",
            enemy_hull=100,
            enemy_max_hull=100,
            enemy_damage=10,
            bounty_credits=50,
        )
        self.engine.state = self.engine._clone_state(active_combat=combat)
        ok, message = self.engine.set_fleet_role(self.ship.id, "support")
        self.assertFalse(ok)
        self.assertIn("fire", message.lower())

    def test_legacy_ship_defaults_to_screen(self):
        payload = self.ship.to_dict()
        payload.pop("tactical_role", None)
        restored = FleetShip.from_dict(payload)
        self.assertEqual(restored.tactical_role, "screen")
        payload["tactical_role"] = "bogus"
        self.assertEqual(FleetShip.from_dict(payload).tactical_role, "screen")


if __name__ == "__main__":
    unittest.main()
