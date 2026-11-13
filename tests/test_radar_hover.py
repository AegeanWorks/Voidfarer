"""System radar: the hovered body gets a ring and a forced name, even with labels switched off."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestRadarHover(unittest.TestCase):
    def test_hovered_body_is_detected_by_id(self) -> None:
        self.assertIn("const hoveredBody = Boolean(this.hoveredItem && this.hoveredItem.id === b.id);", JS)

    def test_a_ring_is_drawn_around_the_hovered_body(self) -> None:
        block = JS.split("const hoveredBody = Boolean(", 1)[1][:700]
        self.assertIn("if (hoveredBody) {", block)
        self.assertIn("ctx.arc(bx, by, bodyRadius + 5, 0, Math.PI * 2);", block)

    def test_the_label_is_forced_on_and_prioritised_while_hovered(self) -> None:
        self.assertIn("if (this.radarLabels || hoveredBody) {", JS)
        self.assertIn("this.selectedTarget && this.selectedTarget.id === b.id) || hoveredBody ? 4 : 1", JS)


if __name__ == "__main__":
    unittest.main()
