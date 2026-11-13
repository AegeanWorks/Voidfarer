"""Crowded radar: a body keeps a name by trying a shorter wording and more positions."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestRadarLabelFallback(unittest.TestCase):
    def test_variants_drop_only_a_trailing_parenthetical(self) -> None:
        self.assertIn(r'.replace(/\s*\([^)]*\)\s*$/, "")', JS)
        self.assertIn("radarLabelVariants(text)", JS)
        self.assertIn("for (const label of variants)", JS)

    def test_full_text_is_tried_before_the_short_form(self) -> None:
        self.assertIn("short && short !== text ? [text, short] : [text]", JS)

    def test_extra_rows_exist_beyond_the_four_original_positions(self) -> None:
        body = JS.split("placeRadarLabel(ctx, text, x, y, radius, color", 1)[1][:2600]
        self.assertGreaterEqual(body.count("{ x: "), 10)

    def test_priority_labels_still_force_the_full_text(self) -> None:
        tail = JS.split("if (priority >= 4) {", 1)[1][:700]
        self.assertIn("place(box, text);", tail)


if __name__ == "__main__":
    unittest.main()
