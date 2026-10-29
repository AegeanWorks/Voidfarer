"""Prize-ship sale, fleet value reporting and the shipbreaker milestone."""

import unittest

from voidfarer.codex import metric_value
from voidfarer.engine import SimulationEngine
from voidfarer.fleet import escort_sale_value
from voidfarer.models import FleetShip


class FleetPrizeSaleTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.prize = FleetShip(
            id="prize_test_1",
            name="Prize: Crippled Corsair",
            ship_class="Assault Frigate",
            role="prize",
            hull=40,
            max_hull=100,
            shield=0,
            max_shield=0,
            damage=6,
            assigned_system_id="sol",
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fleet_ships=(self.prize,), credits=1000),
            active_combat=None,
        )

    def test_a_prize_can_be_sold_at_a_station(self):
        expected = escort_sale_value(self.prize)
        ok, message = self.engine.sell_escort(self.prize.id)
        self.assertTrue(ok, message)
        self.assertIn(str(expected), message)
        self.assertEqual(self.engine.state.ship.credits, 1000 + expected)
        self.assertEqual(self.engine.state.ship.fleet_ships, ())
        self.assertEqual(self.engine.state.stats.get("ships_sold"), 1)
        self.assertEqual(metric_value(self.engine.state, "ships_sold"), 1)
        self.assertTrue(any("SOLD" in line.upper() for line in self.engine.state.ship.flight_log))

    def test_sale_requires_a_docked_station(self):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(orbiting_body_id=None))
        ok, message = self.engine.sell_escort(self.prize.id)
        self.assertFalse(ok)
        self.assertIn("dock", message.lower())

    def test_sale_rejects_an_unknown_escort(self):
        ok, message = self.engine.sell_escort("missing_ship")
        self.assertFalse(ok)
        self.assertIn("unknown", message.lower())

    def test_fleet_report_exposes_sale_values(self):
        report = self.engine.get_fleet_manager_report()
        self.assertEqual(report["ships"][0]["sale_value"], escort_sale_value(self.prize))


if __name__ == "__main__":
    unittest.main()
