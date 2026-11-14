"""Every sidebar tab label must fit beside its notification badge (ADR-276)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

INDEX = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "index.html"
# The rail is 138px wide: CONTRACTS (9) is the longest label measured to fit beside a badge.
MAX_LABEL = 9


class RailLabelsFitTests(unittest.TestCase):
    def test_labels_fit_beside_badges(self) -> None:
        html = INDEX.read_text(encoding="utf-8")
        labels = re.findall(r'<button class="deck-tab-btn"[^>]*>\s*([^<]+?)\s*(?:<span|</button>)', html)
        self.assertGreaterEqual(len(labels), 15)
        too_long = [label for label in labels if len(label) > MAX_LABEL]
        self.assertEqual(too_long, [], "these labels overflow the rail when a badge shows")


if __name__ == "__main__":
    unittest.main()
