"""Top-bar fuel gauge: a low-fuel state that offers the hold fuel-cell burn where the problem shows."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")


class TestLowFuelGauge(unittest.TestCase):
    def test_card_carries_a_hidden_burn_chip(self) -> None:
        self.assertIn('id="fuelBurnChip"', HTML)
        self.assertLess(HTML.index('id="fuelVal"'), HTML.index('id="fuelBurnChip"'))

    def test_low_threshold_and_burnable_state_are_computed(self) -> None:
        self.assertIn("const lowFuel = fuelPct <= 25;", JS)
        self.assertIn("const cells = Number((ship.cargo || {}).fuel_cells || 0);", JS)
        self.assertIn('classList.toggle("is-low", lowFuel)', JS)
        self.assertIn('classList.toggle("is-burnable", lowFuel && cells > 0)', JS)

    def test_only_a_burnable_card_triggers_the_burn(self) -> None:
        # Contract: the burn fires only from a card in the burnable state, via handleBurnCells. It is
        # either gated by the class directly or by the keyboard-aware setVitalAction helper (ADR-244).
        gated = ('fuelCard.classList.contains("is-burnable")' in JS
                 or "this.setVitalAction(fuelCard, lowFuel && cells > 0," in JS)
        self.assertTrue(gated)
        self.assertIn("this.handleBurnCells()", JS)

    def test_styles_exist_for_both_states(self) -> None:
        self.assertIn("#vitalFuelCard.is-low", CSS)
        self.assertIn("#vitalFuelCard.is-burnable", CSS)
        self.assertRegex(CSS, r"#fuelBurnChip \{[^}]*display: none")


if __name__ == "__main__":
    unittest.main()
