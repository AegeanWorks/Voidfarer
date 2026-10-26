"""The cockpit inventory proof covers controls, handlers, routes, hotkeys and theme tokens."""

import unittest
from pathlib import Path

from tools.ui_inventory import inventory

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


class InventoryTest(unittest.TestCase):

    def test_the_inventory_names_the_core_controls_and_handlers(self):
        entries = inventory(STATIC)
        for expected in ("element button#btnMainMenu", "element canvas#radarCanvas",
                         "element div#awaySection", "binding btnMainMenu click", "handler handleCombat",
                         "handler createCharacter", "handler renderAway"):
            self.assertIn(expected, entries)
        self.assertGreaterEqual(len(entries), 650)

    def test_the_inventory_names_the_ui_routes_and_theme_surface(self):
        entries = inventory(STATIC)
        for expected in ("api /api/state", "api /api/away/launch", "route /api/state",
                         "route /api/away/launch", "hotkey key:escape",
                         "hotkey code:KeyQ", "token --neon-cyan",
                         "asset cursor-default.svg"):
            self.assertIn(expected, entries)

    def test_the_inventory_is_sorted_and_deduplicated(self):
        entries = inventory(STATIC)
        self.assertEqual(entries, sorted(set(entries)))


if __name__ == "__main__":
    unittest.main()
