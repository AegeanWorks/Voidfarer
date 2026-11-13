"""The terminal tab rail exposes its active tab to assistive technology, not only through a CSS class."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestTabRailState(unittest.TestCase):
    def test_switching_tabs_sets_aria_current_on_the_active_button(self) -> None:
        body = JS.split("    switchRightTab(tabName, options = {}) {", 1)[1][:4600]
        self.assertIn('button.setAttribute("aria-current", "true")', body)
        self.assertIn('button.removeAttribute("aria-current")', body)

    def test_collapsing_the_drawer_clears_the_current_marker(self) -> None:
        body = JS.split("    switchRightTab(tabName, options = {}) {", 1)[1][:2400]
        collapse = body.split("this.activeRightTab = null;", 1)[1][:600]
        self.assertIn('removeAttribute("aria-current")', collapse)


if __name__ == "__main__":
    unittest.main()
