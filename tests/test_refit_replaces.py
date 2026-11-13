"""REFIT upgrade cards say which installed upgrade a purchase would replace."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")


class TestRefitReplaces(unittest.TestCase):
    def test_installed_name_is_looked_up_per_slot(self) -> None:
        self.assertIn("const installed = upgrades.find(x => x.id === equipped[u.slot]);", JS)
        self.assertIn("!isEquipped && installed", JS)

    def test_card_renders_a_replaces_line(self) -> None:
        self.assertIn('class="arsenal-replaces"', JS)
        self.assertIn("REPLACES ${this.escapeHtml(installed.name)}", JS)

    def test_line_is_styled_and_meets_the_12px_floor(self) -> None:
        self.assertRegex(CSS, r"\.arsenal-replaces \{[^}]*font-size: 12px")


if __name__ == "__main__":
    unittest.main()
