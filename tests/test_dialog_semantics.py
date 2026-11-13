"""Overlays are real dialogs: labelled, modal, and they take and return keyboard focus."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")

DIALOGS = {
    "mainMenuOverlay": "mainMenuTitle",
    "settingsOverlay": "settingsTitle",
    "characterCreationOverlay": "charCreationTitle",
    "deathOverlay": "deathTitle",
}


class TestDialogSemantics(unittest.TestCase):
    def test_each_overlay_is_a_labelled_modal_dialog(self) -> None:
        for overlay_id, title_id in DIALOGS.items():
            tag = re.search(r"<div[^>]*\bid=\"" + overlay_id + r"\"[^>]*>", HTML)
            self.assertIsNotNone(tag, overlay_id)
            self.assertRegex(tag.group(0), r'role="(alert)?dialog"', overlay_id)
            for needle in ('aria-modal="true"', f'aria-labelledby="{title_id}"'):
                self.assertIn(needle, tag.group(0), f"{overlay_id} {needle}")
            self.assertRegex(HTML, r'<h[12][^>]*\bid="' + title_id + '"')

    def test_one_observer_manages_focus_for_every_open_and_close_path(self) -> None:
        self.assertIn("initDialogFocus()", JS)
        self.assertIn("new MutationObserver", JS.split("initDialogFocus() {", 1)[1][:2500])
        self.assertIn("this.initDialogFocus();", JS)

    def test_focus_moves_in_on_open_and_is_restored_on_close(self) -> None:
        body = JS.split("initDialogFocus() {", 1)[1][:2500]
        self.assertIn("opener = document.activeElement", body)
        self.assertIn("first.focus()", body)
        self.assertIn("opener.focus()", body)


if __name__ == "__main__":
    unittest.main()
