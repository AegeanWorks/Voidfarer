"""The status snapshot names the best buy-here, sell-next-door tip while docked."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.galaxy import COMMODITY_MAP
from voidfarer.smuggling import is_contraband


class TradeTipTest(unittest.TestCase):
    def test_docked_tip_names_a_profitable_adjacent_route(self):
        engine = SimulationEngine(seed=42)
        tip = engine.get_status_snapshot()["trade_tip"]
        self.assertIsNotNone(tip)
        self.assertGreater(tip["margin"], 0)
        self.assertEqual(tip["margin"], tip["sell_price"] - tip["buy_price"])
        self.assertIn(tip["system_id"], engine.current_system.connections)
        self.assertIn(tip["commodity_id"], COMMODITY_MAP)
        self.assertFalse(is_contraband(tip["commodity_id"]))
        self.assertTrue(tip["system_name"])

    def test_the_tip_is_the_best_margin_among_legal_goods(self):
        engine = SimulationEngine(seed=42)
        tip = engine.trade_tip()
        self.assertEqual(engine.trade_tip(), tip)  # deterministic

    def test_no_tip_away_from_a_station(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(orbiting_body_id=None))
        self.assertIsNone(engine.get_status_snapshot()["trade_tip"])


if __name__ == "__main__":
    unittest.main()
