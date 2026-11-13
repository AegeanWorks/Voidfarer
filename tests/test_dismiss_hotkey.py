"""X dismisses the visible event notifications through their own DISMISS buttons."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")


class TestDismissHotkey(unittest.TestCase):
    def test_x_calls_the_dismisser(self) -> None:
        self.assertIn('hotkey === "x"', JS)
        self.assertIn("this.dismissEventPopups();", JS)

    def test_the_dismisser_clicks_each_real_button_so_server_state_updates(self) -> None:
        body = JS.split("    dismissEventPopups() {", 1)[1][:700]
        self.assertIn("[data-dismiss-event]", body)
        self.assertIn("button.click()", body)

    def test_it_does_nothing_without_notifications(self) -> None:
        body = JS.split("    dismissEventPopups() {", 1)[1][:700]
        self.assertIn("if (!buttons.length) return;", body)

    def test_the_controls_reference_lists_the_key(self) -> None:
        self.assertIn("<dt>X</dt><dd>Dismiss the visible notifications</dd>", HTML)


if __name__ == "__main__":
    unittest.main()
