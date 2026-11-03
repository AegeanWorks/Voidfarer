"""Regression: trade/buy/jettison reject non-int quantities like repair_hull does.

Wave audit 0,10,20,30 (first 30 commits): economy paths in ce6d513/f7497ec
guard only ``quantity <= 0`` while repair_hull/repair_escorts/refuel enforce
``not isinstance(int) or bool or <= 0``. bool/float slipped through and minted
fractional cargo (trade 1.5 -> 6.5 units, 79.5 cr) or ``Truex`` messages.
"""

import unittest

from voidfarer.engine import SimulationEngine


class TradeQuantityGuardsTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        ok, _ = self.engine.orbit("sol_body_1")
        self.assertTrue(ok)

    def _snapshot(self):
        ship = self.engine.state.ship
        return (dict(ship.cargo), ship.credits, ship.fuel, ship.hull)

    def test_trade_rejects_bool_float_and_str(self):
        before = self._snapshot()
        for bad in (True, False, 1.5, 0.5, "2", None):
            ok, _ = self.engine.trade("fuel_cells", bad, True)
            self.assertFalse(ok, f"trade accepted {bad!r}")
            self.assertEqual(self._snapshot(), before)

    def test_buy_item_rejects_bool_float_and_str(self):
        before = self._snapshot()
        for bad in (True, False, 1.5, "2", None):
            ok, _ = self.engine.buy_item("nanite_repair_paste", bad)
            self.assertFalse(ok, f"buy_item accepted {bad!r}")
            self.assertEqual(self._snapshot(), before)

    def test_jettison_rejects_bool_float_and_str(self):
        before = self._snapshot()
        for bad in (True, False, 1.5, "1", None):
            ok, _ = self.engine.jettison_cargo("fuel_cells", bad)
            self.assertFalse(ok, f"jettison accepted {bad!r}")
            self.assertEqual(self._snapshot(), before)


if __name__ == "__main__":
    unittest.main()
