"""Actionable vital cards (burn cell, patch hull) are real keyboard controls, not mouse-only divs."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestVitalCardKeyboard(unittest.TestCase):
    def test_a_shared_helper_makes_a_card_a_button_only_when_actionable(self) -> None:
        self.assertIn("setVitalAction(card, actionable, handler)", JS)
        self.assertIn('card.setAttribute("role", "button")', JS)
        self.assertIn("card.tabIndex = 0", JS)
        self.assertIn('card.removeAttribute("role")', JS)
        self.assertIn('card.removeAttribute("tabindex")', JS)

    def test_enter_and_space_activate_the_card(self) -> None:
        self.assertIn('event.key === "Enter" || event.key === " "', JS)
        self.assertIn("event.preventDefault();", JS)

    def test_both_gauges_use_the_helper(self) -> None:
        self.assertIn("this.setVitalAction(fuelCard, lowFuel && cells > 0, () => this.handleBurnCells());", JS)
        self.assertIn('this.setVitalAction(hullCard, lowHull && titanium > 0, () => this.handleFabricate("patch_kit"));', JS)

    def test_old_click_only_bindings_are_gone(self) -> None:
        self.assertNotIn("dataset.burnBound", JS)
        self.assertNotIn("dataset.patchBound", JS)


if __name__ == "__main__":
    unittest.main()
