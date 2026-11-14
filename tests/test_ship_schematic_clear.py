"""The ship schematic's caption stays clear of the module chips (ADR-278)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "app.js"


class ShipSchematicClearTests(unittest.TestCase):
    def test_caption_is_a_short_corner_tag(self) -> None:
        source = APP.read_text(encoding="utf-8")
        svgs = re.findall(r'<svg viewBox="0 0 300 120" class="ship-silhouette">.*?</svg>', source, re.S)
        self.assertEqual(len(svgs), 5)
        for svg in svgs:
            texts = re.findall(r'<text x="(\d+)" y="(\d+)"[^>]*>([^<]*)</text>', svg)
            self.assertEqual(len(texts), 1)
            x, y, label = texts[0]
            # Module chips cover the lower hull; only the top-left corner stays free.
            self.assertLessEqual(int(x), 12)
            self.assertLessEqual(int(y), 16)
            self.assertLessEqual(len(label), 6)


if __name__ == "__main__":
    unittest.main()
