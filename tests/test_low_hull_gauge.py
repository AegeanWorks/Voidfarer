"""Top-bar hull gauge: a critical-hull state that offers the titanium patch kit where the problem shows."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")


class TestLowHullGauge(unittest.TestCase):
    def test_card_carries_a_hidden_patch_chip(self) -> None:
        self.assertIn('id="hullPatchChip"', HTML)
        self.assertLess(HTML.index('id="hullVal"'), HTML.index('id="hullPatchChip"'))

    def test_critical_threshold_and_patchable_state_are_computed(self) -> None:
        self.assertIn("const lowHull = hullPct <= 30;", JS)
        self.assertIn("const titanium = Number((ship.cargo || {}).titanium || 0);", JS)
        self.assertIn('classList.toggle("is-low", lowHull)', JS)
        self.assertIn('classList.toggle("is-patchable", lowHull && titanium > 0)', JS)

    def test_only_a_patchable_card_fabricates(self) -> None:
        # Contract: the patch fires only from a card in the patchable state, via handleFabricate. It is
        # either gated by the class directly or by the keyboard-aware setVitalAction helper (ADR-244).
        gated = ('hullCard.classList.contains("is-patchable")' in JS
                 or "this.setVitalAction(hullCard, lowHull && titanium > 0," in JS)
        self.assertTrue(gated)
        self.assertIn('this.handleFabricate("patch_kit")', JS)

    def test_styles_exist_for_both_states(self) -> None:
        self.assertIn("#vitalHullCard.is-low", CSS)
        self.assertIn("#vitalHullCard.is-patchable", CSS)
        self.assertRegex(CSS, r"#hullPatchChip \{[^}]*display: none")


if __name__ == "__main__":
    unittest.main()
