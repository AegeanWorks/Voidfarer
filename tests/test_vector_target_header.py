"""Open-space target card: the header carries the transit distance only (bearing lives in the stat chips)."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestVectorTargetHeader(unittest.TestCase):
    def test_header_distance_does_not_repeat_the_bearing(self) -> None:
        self.assertIn("this.targetDist.textContent = `${distAu.toFixed(2)} AU TRANSIT`;", JS)
        self.assertNotIn("AU TRANSIT // BEARING", JS)

    def test_bearing_is_still_shown_as_a_stat_chip(self) -> None:
        vector_block = JS.split("this.targetName.textContent = `VECTOR ", 1)[1][:900]
        self.assertIn('["BEARING", `${(p.angle * 180 / Math.PI).toFixed(0)} DEG`]', vector_block)


if __name__ == "__main__":
    unittest.main()
