"""The Commerce quote reports what a sale actually pays (ADR-282)."""

from __future__ import annotations

import io
import re
import unittest
from contextlib import redirect_stdout

from voidfarer.cli import cmd_market

from voidfarer.engine import SimulationEngine


def _docked_engine(cargo: dict) -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.orbit("sol_body_1")
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=5000, cargo=dict(cargo), cargo_cost={}))
    return engine


class SellPriceNetTests(unittest.TestCase):
    def test_net_price_matches_a_one_unit_sale_for_every_commodity(self) -> None:
        probe = _docked_engine({})
        quotes = probe.get_status_snapshot()["market_quotes"]
        self.assertGreater(len(quotes), 5)
        for quote in quotes:
            cid = quote["commodity_id"]
            self.assertIn("sell_price_net", quote)
            engine = _docked_engine({cid: 1})
            before = engine.state.ship.credits
            ok, msg = engine.trade(cid, 1, is_buy=False)
            self.assertTrue(ok, msg)
            self.assertEqual(engine.state.ship.credits - before, quote["sell_price_net"], cid)

    def test_cli_market_prints_the_net_price(self) -> None:
        engine = _docked_engine({})
        quotes = {q["name"]: q for q in engine.get_status_snapshot()["market_quotes"]}
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(cmd_market(engine), 0)
        text = re.sub(r"\[[0-9;]*m", "", buffer.getvalue())
        checked = 0
        for name, quote in quotes.items():
            match = re.search(rf"^{re.escape(name)}\s+(\d+) cr\s+(\d+) cr", text, re.M)
            if match:
                self.assertEqual(int(match.group(2)), quote["sell_price_net"], name)
                checked += 1
        self.assertGreater(checked, 5)


if __name__ == "__main__":
    unittest.main()
