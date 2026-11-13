"""Cockpit SHIP tab: the fuel-cell burn button sits beside field fabrication."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


class TestCockpitButton(unittest.TestCase):
    def test_ship_tab_offers_the_burn_beside_fabrication(self) -> None:
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="btnBurnCells"', html)
        self.assertLess(html.index('id="btnFabricateFuel"'), html.index('id="btnBurnCells"'))
        self.assertIn('action: "burn_cells"', js)


if __name__ == "__main__":
    unittest.main()
