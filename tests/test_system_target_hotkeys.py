"""On the galaxy map, comma and period cycle the star systems linked to the current one."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


class TestSystemTargetHotkeys(unittest.TestCase):
    def test_the_cycler_hands_the_galaxy_view_to_a_system_cycler(self) -> None:
        body = JS.split("    cycleBodyTarget(step) {", 1)[1][:400]
        self.assertIn('if (this.viewMode === "GALAXY") {', body)
        self.assertIn("this.cycleSystemTarget(step);", body)

    def test_only_linked_systems_are_cycled_nearest_first_and_wrap(self) -> None:
        body = JS.split("    cycleSystemTarget(step) {", 1)[1][:1100]
        self.assertIn("(current.connections || []).map(id => this.galaxySystems[id])", body)
        self.assertIn("Math.hypot(a.x - current.x, a.y - current.y) - Math.hypot(b.x - current.x, b.y - current.y)", body)
        self.assertIn("% links.length", body)
        self.assertIn('this.selectedType = "system";', body)
        self.assertIn("this.updateTargetCard();", body)

    def test_the_controls_reference_documents_the_galaxy_behaviour(self) -> None:
        self.assertIn("<dt>, . (galaxy map)</dt><dd>Previous / next linked star system</dd>", HTML)


if __name__ == "__main__":
    unittest.main()
