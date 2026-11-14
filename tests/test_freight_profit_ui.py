"""The freight row shows and colours by real profit (ADR-290)."""

from __future__ import annotations

import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "app.js"


class FreightProfitUiTests(unittest.TestCase):
    def test_row_is_coloured_and_labelled_by_profit(self) -> None:
        app = APP.read_text(encoding="utf-8")
        start = app.index("const routeRows = routes.length")
        block = app[start:start + 1500]
        head = block.split("return `")[0]
        self.assertTrue("route.profit" in head and "netClass = profit >= 0" in head, "the colour must follow profit")
        self.assertTrue("PROFIT" in block, "the row must label the profit")
        self.assertTrue("route.cost_basis" in block, "the tooltip must name what the cargo cost")
        self.assertTrue("<strong>${route.net >= 0" in block, "the net figure stays visible")


if __name__ == "__main__":
    unittest.main()
