"""Canvas text meets the same 12px readability floor the DOM audit enforces."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


def _sizes(name: str) -> list[float]:
    text = (STATIC / name).read_text(encoding="utf-8")
    return [float(m.group(1)) for m in re.finditer(r"""font = ["`](\d+(?:\.\d+)?)px""", text)]


class TestCanvasFontFloor(unittest.TestCase):
    def test_no_canvas_font_in_the_cockpit_script_is_below_12px(self) -> None:
        small = [size for size in _sizes("app.js") if size < 12]
        self.assertEqual(small, [], "canvas fonts under 12px in app.js")

    def test_no_canvas_font_in_the_surface_map_is_below_12px(self) -> None:
        small = [size for size in _sizes("surfacemap.js") if size < 12]
        self.assertEqual(small, [], "canvas fonts under 12px in surfacemap.js")

    def test_the_surface_callout_box_is_tall_enough_for_two_12px_lines(self) -> None:
        text = (STATIC / "surfacemap.js").read_text(encoding="utf-8")
        self.assertIn("ctx.fillRect(lx, ly, width, 34);", text)
        self.assertIn("ctx.strokeRect(lx, ly, width, 34);", text)
        self.assertIn("ctx.fillText(line2, lx + 6, ly + 27);", text)


if __name__ == "__main__":
    unittest.main()
