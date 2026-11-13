"""J and O press the target card's own jump and transit buttons, so every guard still applies."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


class TestTargetActionHotkeys(unittest.TestCase):
    def test_hotkeys_route_through_one_helper(self) -> None:
        self.assertIn('hotkey === "j"', JS)
        self.assertIn('hotkey === "o"', JS)
        self.assertIn('this.pressTargetAction("btnJumpTarget");', JS)
        self.assertIn('this.pressTargetAction("btnOrbitTarget");', JS)

    def test_the_helper_never_bypasses_a_disabled_or_hidden_button(self) -> None:
        body = JS.split("    pressTargetAction(id) {", 1)[1][:600]
        self.assertIn("button.disabled", body)
        self.assertIn('button.style.display === "none"', body)
        self.assertIn("button.click();", body)

    def test_refusals_are_explained_not_silent(self) -> None:
        body = JS.split("    pressTargetAction(id) {", 1)[1][:900]
        self.assertIn("this.appendLog(", body)
        self.assertIn("button.title", body)

    def test_the_controls_reference_lists_both_keys(self) -> None:
        self.assertIn("<dt>J / O</dt><dd>Jump to / transit to the selected target", HTML)


if __name__ == "__main__":
    unittest.main()
