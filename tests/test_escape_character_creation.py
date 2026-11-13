"""Escape closes Character Creation instead of stacking the main menu on top of it."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestEscapeCharacterCreation(unittest.TestCase):
    def test_escape_handler_closes_character_creation_before_toggling_the_menu(self) -> None:
        handler = JS.split('if (e.key === "Escape") {', 1)[1][:1200]
        creation = handler.index("this.closeCharacterCreation();")
        menu = handler.index("this.toggleMainMenu();")
        self.assertLess(creation, menu)

    def test_the_check_reads_the_overlay_visibility(self) -> None:
        handler = JS.split('if (e.key === "Escape") {', 1)[1][:1200]
        self.assertIn('getElementById("characterCreationOverlay")', handler)


if __name__ == "__main__":
    unittest.main()
