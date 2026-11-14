"""SELL ALL PROFITABLE sells every held commodity that beats its cost basis and keeps the rest."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.logistics import LOGISTICS_ACTIONS, logistics_action


def _engine(cost_basis: dict[str, int]) -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.state = engine._clone_state(ship=engine._clone_ship(
        cargo={"fuel_cells": 5, "hydroponics": 10}, cargo_cost=cost_basis,
    ))
    return engine


class SellAllProfitableTest(unittest.TestCase):
    def test_sells_the_profitable_row_and_keeps_the_one_that_would_lose(self):
        # Fuel cells were bought absurdly dear (a loss at any local price); hydroponics have no basis.
        engine = _engine({"fuel_cells": 100000})
        credits = engine.state.ship.credits
        ok, message = engine.sell_all_profitable()
        self.assertTrue(ok, message)
        ship = engine.state.ship
        self.assertNotIn("hydroponics", ship.cargo)
        self.assertEqual(ship.cargo.get("fuel_cells"), 5)
        self.assertEqual(ship.cargo_cost.get("fuel_cells"), 100000)
        self.assertGreater(ship.credits, credits)
        self.assertIn("kept", message.lower())

    def test_nothing_profitable_changes_nothing(self):
        engine = _engine({"fuel_cells": 100000, "hydroponics": 100000})
        before = engine.state.ship
        ok, message = engine.sell_all_profitable()
        self.assertFalse(ok)
        self.assertEqual(engine.state.ship, before)
        self.assertIn("profitable", message.lower())

    def test_undocked_ship_is_refused(self):
        engine = _engine({})
        engine.state = engine._clone_state(ship=engine._clone_ship(orbiting_body_id=None))
        ok, _ = engine.sell_all_profitable()
        self.assertFalse(ok)

    def test_it_is_reachable_as_a_logistics_action(self):
        self.assertIn("sell_all", LOGISTICS_ACTIONS)
        ok, _ = logistics_action(_engine({}), "sell_all")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
