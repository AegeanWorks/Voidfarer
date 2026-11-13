"""Radar reference labels (AU ticks, compass, range scale) use a tint that clears 3:1 on the nebula backdrop."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")

IVORY = "236, 228, 212"


def _fill_before(anchor: str) -> str:
    """The fillStyle assigned immediately before the line containing `anchor`."""
    head = JS.split(anchor, 1)[0]
    return re.findall(r'ctx\.fillStyle = "(rgba\([^"]+\))"', head)[-1]


def _alpha(rgba: str) -> float:
    return float(rgba.rsplit(",", 1)[1].strip(" )"))


class TestRadarLabelContrast(unittest.TestCase):
    def test_au_ticks_use_a_light_tint_at_0_6_or_more(self) -> None:
        fill = _fill_before("ctx.fillText(`${auDist.toFixed(1)} AU`")
        self.assertIn(IVORY, fill)
        self.assertGreaterEqual(_alpha(fill), 0.6)

    def test_compass_labels_use_a_light_tint_at_0_6_or_more(self) -> None:
        fill = _fill_before("const cardinals = [")
        self.assertIn(IVORY, fill)
        self.assertGreaterEqual(_alpha(fill), 0.6)

    def test_the_range_scale_label_is_the_brightest_of_the_three(self) -> None:
        fill = _fill_before("const scaleLabel = `RANGE SCALE")
        self.assertIn(IVORY, fill)
        self.assertGreaterEqual(_alpha(fill), 0.75)

    def test_tick_labels_step_around_the_east_compass_label(self) -> None:
        block = JS.split("const auDist = radius / Math.max(1, auScale);", 1)[1][:900]
        self.assertIn("const compassGuard = Math.min(this.viewW, this.viewH) * 0.46;", block)
        self.assertIn("radius + 62 > compassGuard - 12 && radius + 4 < compassGuard + 40", block)
        self.assertIn("if (auDist >= 0.25 && !hitsCompassLabel) {", block)


if __name__ == "__main__":
    unittest.main()
