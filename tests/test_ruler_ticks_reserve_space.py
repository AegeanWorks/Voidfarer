"""Orbit-view names route around the AU ruler marks (ADR-287)."""

from __future__ import annotations

import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "app.js"


class RulerTicksReserveSpaceTests(unittest.TestCase):
    def test_each_tick_label_registers_its_box_before_names_are_placed(self) -> None:
        app = APP.read_text(encoding="utf-8")
        start = app.index("ctx.fillText(`${auDist.toFixed(1)} AU`")
        window = app[start - 300:start + 700]
        self.assertTrue("_radarLabelBoxes.push(" in window, "tick labels must reserve their rectangle")
        self.assertTrue("measureText" in window, "the reserved width must be measured, not guessed")
        place = app.index("labels.forEach(label => this.placeRadarLabel(")
        self.assertTrue(start < place, "ticks are drawn and reserved before the names are placed")


if __name__ == "__main__":
    unittest.main()
