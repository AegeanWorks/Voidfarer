"""Cockpit: the low-fuel gauge offers the rescue when no cell or titanium remains."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestCockpit(unittest.TestCase):
    def test_low_fuel_gauge_offers_the_rescue_when_nothing_else_remains(self) -> None:
        self.assertIn("CALL RESCUE", JS)
        self.assertIn('action: "distress"', JS)
        self.assertIn("handleDistress()", JS)
        self.assertIn("this.setVitalAction(fuelCard, true, () => this.handleDistress());", JS)

    def test_the_offer_follows_the_engines_verdict_not_a_client_guess(self) -> None:
        self.assertIn("this.state.rescue && this.state.rescue.available", JS)

    def test_the_chip_text_returns_to_burn_cell_when_cells_exist(self) -> None:
        self.assertIn('chip.textContent = rescuable ? "CALL RESCUE" : "BURN CELL";', JS)


if __name__ == "__main__":
    unittest.main()
