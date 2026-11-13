"""A blocking encounter card is an alert dialog that takes keyboard focus when it appears and returns it when it resolves."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


class TestEncounterFocus(unittest.TestCase):
    def test_the_card_is_declared_an_alert_dialog(self) -> None:
        tag = re.search(r"<div[^>]*\bid=\"anomalyCard\"[^>]*>", HTML)
        self.assertIsNotNone(tag)
        self.assertIn('role="alertdialog"', tag.group(0))

    def test_a_new_encounter_moves_focus_to_its_first_enabled_action(self) -> None:
        body = JS.split("    renderEncounter() {", 1)[1][:4600]
        self.assertIn("const isNewEncounter = this._lastEncounterId !== payload.id;", body)
        self.assertIn("this._encounterOpener = document.activeElement;", body)
        self.assertIn(".anomaly-choice-btn:not(:disabled)", body)
        self.assertIn("first.focus()", body)

    def test_resolving_the_encounter_restores_the_previous_focus(self) -> None:
        body = JS.split("    renderEncounter() {", 1)[1][:1400]
        hidden = body.split('this.anomalyCard.style.display = "none";', 1)[1][:600]
        self.assertIn("this._encounterOpener.focus()", hidden)

    def test_a_rebuild_keeps_focus_on_the_same_action(self) -> None:
        body = JS.split("    renderEncounter() {", 1)[1][:4600]
        self.assertIn("(document.activeElement.dataset || {}).encounterAction", body)
        self.assertIn("btn.dataset.encounterAction === focusedAction", body)
        self.assertIn("kept.focus();", body)

    def test_focus_is_only_stolen_once_per_encounter(self) -> None:
        body = JS.split("    renderEncounter() {", 1)[1][:4600]
        self.assertIn("if (isNewEncounter)", body)


if __name__ == "__main__":
    unittest.main()
