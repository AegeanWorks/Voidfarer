"""Fleet upkeep: monthly escort payroll, cash flow and shortfall readiness."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship, fleet_upkeep


class FleetUpkeepMathTest(unittest.TestCase):
    def test_upkeep_scales_with_living_roles(self):
        corvette = build_fleet_ship("corvette", "sol", 0)
        frigate = build_fleet_ship("frigate", "sol", 1)
        cruiser = build_fleet_ship("cruiser", "sol", 2)
        carrier = build_fleet_ship("carrier", "sol", 3)
        self.assertEqual(fleet_upkeep((corvette,)), 30)
        self.assertEqual(fleet_upkeep((frigate,)), 55)
        self.assertEqual(fleet_upkeep((cruiser,)), 90)
        self.assertEqual(fleet_upkeep((carrier,)), 110)
        self.assertEqual(
            fleet_upkeep((corvette, frigate, cruiser, carrier)), 285
        )
        wreck = replace(corvette, hull=0, status="destroyed")
        self.assertEqual(fleet_upkeep((wreck,)), 0)

    def test_prize_upkeep_scales_with_captured_firepower(self):
        corvette = build_fleet_ship("corvette", "sol", 0)
        skiff = replace(corvette, role="prize", damage=8)
        self.assertEqual(fleet_upkeep((skiff,)), 25)
        gunboat = replace(corvette, role="prize", damage=12)
        self.assertEqual(fleet_upkeep((gunboat,)), 27)
        elite = replace(corvette, role="prize", damage=30)
        self.assertEqual(fleet_upkeep((elite,)), 45)
        dreadnought = replace(corvette, role="prize", damage=40)
        self.assertEqual(fleet_upkeep((dreadnought,)), 55)


class FleetUpkeepEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.allow_decision_events = False
        self.corvette = build_fleet_ship("corvette", "sol", 0)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=1000,
                fleet_ships=(self.corvette,),
            ),
            time=replace(self.engine.state.time, elapsed_days=29.9),
        )

    def test_cash_flow_separates_crew_and_fleet_upkeep(self):
        flow = self.engine.cash_flow()
        self.assertEqual(flow["fleet_upkeep_per_month"], 30)
        self.assertEqual(flow["crew_upkeep_per_month"], 65)
        self.assertEqual(flow["upkeep_per_month"], 95)
        self.assertEqual(flow["net_per_month"], -95.0)

    def test_month_rollover_charges_fleet_upkeep(self):
        payload = self.engine.tick(1)
        self.assertEqual(payload["fleet_upkeep_cost"], 30)
        self.assertTrue(payload["fleet_upkeep_paid"])
        self.assertLess(self.engine.state.ship.credits, 1000 - 30)
        self.assertEqual(self.engine.state.ship.fleet_ships[0].status, "escorting")

    def test_shortfall_marks_living_escorts_damaged(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=10)
        )
        payload = self.engine.tick(1)
        self.assertEqual(payload["fleet_upkeep_cost"], 30)
        self.assertFalse(payload["fleet_upkeep_paid"])
        self.assertEqual(self.engine.state.ship.fleet_ships[0].status, "damaged")

    def test_report_exposes_upkeep(self):
        report = self.engine.get_fleet_manager_report()
        self.assertEqual(report["upkeep_per_month"], 30)


if __name__ == "__main__":
    unittest.main()
