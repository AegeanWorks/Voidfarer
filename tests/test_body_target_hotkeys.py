"""Keyboard targeting: comma and period cycle the selected radar body, and the reference lists them."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


class TestBodyTargetHotkeys(unittest.TestCase):
    def test_hotkeys_call_the_cycler_with_a_direction(self) -> None:
        self.assertIn('e.code === "Comma" || e.code === "Period"', JS)
        self.assertIn('this.cycleBodyTarget(e.code === "Period" ? 1 : -1);', JS)

    def test_cycler_orders_bodies_by_orbit_and_wraps(self) -> None:
        body = JS.split("    cycleBodyTarget(step) {", 1)[1][:1100]
        self.assertIn("(a.orbit_radius || 0) - (b.orbit_radius || 0)", body)
        self.assertIn("% bodies.length", body)
        self.assertIn('this.selectedType = "body";', body)
        self.assertIn("this.updateTargetCard();", body)

    def test_only_the_orbit_view_is_affected(self) -> None:
        body = JS.split("    cycleBodyTarget(step) {", 1)[1][:300]
        self.assertIn('this.viewMode !== "ORBITS"', body)

    def test_the_controls_reference_documents_the_keys(self) -> None:
        self.assertIn("<dt>, .</dt><dd>Previous / next body target on the radar</dd>", HTML)


if __name__ == "__main__":
    unittest.main()
