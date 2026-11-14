"""A failed menu action does not read as a success (ADR-285)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "voidfarer" / "static"


class MenuStatusErrorTests(unittest.TestCase):
    def test_error_state_is_styled_announced_and_set(self) -> None:
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        app = (STATIC / "app.js").read_text(encoding="utf-8")
        rule = re.search(r"\.main-menu-status\.is-error\s*\{([^}]*)\}", css)
        self.assertTrue(rule is not None, "an error style for the menu status is required")
        self.assertTrue("--console-red" in rule.group(1), "errors use the red console token")
        self.assertTrue('id="mainMenuStatus"' in html and 'role="status"' in html.split('id="mainMenuStatus"')[1][:60],
                        "the status line must be a live region")
        action = app[app.index("async menuAction("):][:2400]
        self.assertGreaterEqual(action.count('classList.toggle("is-error"'), 2, "both the failure reply and the network error set it")


if __name__ == "__main__":
    unittest.main()
