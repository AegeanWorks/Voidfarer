"""The combat card is an alert dialog that takes keyboard focus on a new fight and returns it afterwards."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


class TestCombatFocus(unittest.TestCase):
    def test_the_card_is_declared_an_alert_dialog(self) -> None:
        tag = re.search(r"<div[^>]*\bid=\"combatCard\"[^>]*>", HTML)
        self.assertIsNotNone(tag)
        self.assertIn('role="alertdialog"', tag.group(0))
        self.assertIn("aria-label=", tag.group(0))

    def test_a_new_fight_focuses_the_first_enabled_action_once(self) -> None:
        block = JS.split("// Render Combat Intercept Alert", 1)[1][:900]
        self.assertIn("const newCombat = this._lastCombatId !== c.id;", block)
        self.assertIn("this._combatOpener = document.activeElement;", block)
        self.assertIn('document.getElementById("btnCombatFire")', block)
        self.assertIn("fire.focus()", block)

    def test_the_end_of_combat_restores_the_previous_focus(self) -> None:
        block = JS.split("// Render Combat Intercept Alert", 1)[1][:9000]
        hidden = block.split('this.combatCard.style.display = "none";', 1)[1][:500]
        self.assertIn("this._combatOpener.focus()", hidden)
        self.assertIn("this._lastCombatId = null;", hidden)


if __name__ == "__main__":
    unittest.main()
