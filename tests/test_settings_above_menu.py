"""Settings opens above the main menu that launches it (ADR-284)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "style.css"


def _last_z(css: str, selector: str) -> int:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    values = [
        int(match.group(1))
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if selector in [part.strip() for part in sel.split(",")]
        for match in [re.search(r"z-index:\s*(\d+)", body)]
        if match
    ]
    return values[-1] if values else -1


class SettingsAboveMenuTests(unittest.TestCase):
    def test_settings_overlay_outranks_the_main_menu(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        menu = _last_z(css, ".main-menu-overlay")
        settings = _last_z(css, "#settingsOverlay")
        self.assertGreater(menu, 0, "main menu z-index must be declared")
        self.assertGreater(settings, menu, "settings must open above the menu that launches it")


if __name__ == "__main__":
    unittest.main()
