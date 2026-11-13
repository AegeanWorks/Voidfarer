"""Settings overlay controls: real checkmarks and themed sliders instead of browser defaults."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "style.css").read_text(
    encoding="utf-8").replace("\r\n", "\n")


def _last_rule(selector: str) -> str:
    matches = re.findall(re.escape(selector) + r" \{([^}]*)\}", CSS)
    return matches[-1] if matches else ""


class TestSettingsControls(unittest.TestCase):
    def test_range_inputs_drop_native_appearance_so_the_theme_applies(self) -> None:
        self.assertIn("appearance: none", _last_rule('#settingsOverlay input[type="range"]'))
        thumb = _last_rule('#settingsOverlay input[type="range"]::-webkit-slider-thumb')
        self.assertIn("-webkit-appearance: none", thumb)
        self.assertIn("appearance: none", thumb)

    def test_checked_box_draws_a_checkmark_not_crossed_diagonals(self) -> None:
        checked = _last_rule('#settingsOverlay input[type="checkbox"]:checked')
        self.assertIn("data:image/svg+xml", checked)
        self.assertNotIn("42%", checked)

    def test_keyboard_focus_is_visible_on_both_controls(self) -> None:
        self.assertRegex(CSS, r'#settingsOverlay input\[type="checkbox"\]:focus-visible')
        self.assertRegex(CSS, r'#settingsOverlay input\[type="range"\]:focus-visible')


if __name__ == "__main__":
    unittest.main()
