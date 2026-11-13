"""REFIT upgrade list: slot filter chips keep the long catalogue navigable."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


class TestRefitSlotFilters(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.css = (STATIC / "style.css").read_text(encoding="utf-8")

    def test_filter_bar_lives_inside_the_upgrade_disclosure(self) -> None:
        details = self.html.index('id="arsenalUpgradeDetails"')
        bar = self.html.index('id="arsenalFilters"')
        listing = self.html.index('id="arsenalList"')
        self.assertLess(details, bar)
        self.assertLess(bar, listing)

    def test_chips_cover_all_affordable_and_every_slot(self) -> None:
        self.assertIn('["all", `ALL (', self.js)
        self.assertIn('["affordable", `AFFORDABLE (', self.js)
        self.assertIn("slots.map(slot =>", self.js)
        self.assertIn('data-arsenal-filter="', self.js)

    def test_filtering_never_drops_the_equipped_state(self) -> None:
        match = re.search(r"upgrades\.filter\(u => filter === \"all\"(.*?)\)\.forEach\(u => \{\s*const isEquipped",
                          self.js, re.S)
        self.assertIsNotNone(match, "the filter must run before the per-card equipped check")

    def test_chips_wrap_instead_of_clipping(self) -> None:
        self.assertRegex(self.css, r"\.arsenal-filters \{[^}]*flex-wrap: wrap")


if __name__ == "__main__":
    unittest.main()
