"""Text that a clamp or ellipsis can shorten (at 120% HUD scale) is always reachable through a title."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestClippedTextTitles(unittest.TestCase):
    def test_message_choice_buttons_carry_their_full_text(self) -> None:
        block = JS.split('<button class="message-choice-btn"', 1)[1][:420]
        self.assertIn('title="${this.escapeHtml(choice.label)}', block)
        self.assertIn("choice.description", block.split("title=", 1)[1].split(">", 1)[0])

    def test_faction_names_carry_a_title(self) -> None:
        self.assertIn('<span class="faction-name" title="${this.escapeHtml(f.name)}"', JS)


if __name__ == "__main__":
    unittest.main()
