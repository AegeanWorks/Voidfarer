"""Quantum freight routes report real profit against what the cargo cost (ADR-290)."""

from __future__ import annotations

import unittest

from voidfarer.engine import SimulationEngine


def _docked_with_cargo() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.orbit("sol_body_1")
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=9000, cargo={}, cargo_cost={}))
    ok, msg = engine.trade("titanium", 6, is_buy=True)
    assert ok, msg
    return engine


class FreightProfitTests(unittest.TestCase):
    def test_routes_carry_the_cost_basis_and_profit(self) -> None:
        engine = _docked_with_cargo()
        paid = engine.state.ship.cargo_cost["titanium"]
        routes = engine.get_quantum_trade_report()["routes"]
        self.assertTrue(routes)
        for route in routes:
            self.assertEqual(route["cost_basis"], paid)
            self.assertEqual(route["profit"], route["net"] - paid)
            self.assertEqual(route["net"], route["payout"] - route["fee"], "net keeps its meaning: payout minus fee")

    def test_cargo_without_a_recorded_cost_has_profit_equal_to_net(self) -> None:
        engine = SimulationEngine(seed=42)
        engine.orbit("sol_body_1")
        engine.state = engine._clone_state(ship=engine._clone_ship(cargo={"titanium": 3}, cargo_cost={}))
        for route in engine.get_quantum_trade_report()["routes"]:
            self.assertEqual(route["cost_basis"], 0)
            self.assertEqual(route["profit"], route["net"])


if __name__ == "__main__":
    unittest.main()
