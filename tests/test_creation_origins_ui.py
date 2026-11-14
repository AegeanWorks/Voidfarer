"""The Character Creation origin dropdown offers exactly the engine's origins and shows what each grants."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from voidfarer.character import COMMANDER_BACKGROUNDS

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
JS = (STATIC / "app.js").read_text(encoding="utf-8")


def _options() -> list[tuple[str, str]]:
    select = re.search(r'<select id="charBackground"[^>]*>(.*?)</select>', HTML, re.S).group(1)
    return re.findall(r'<option value="([^"]+)">([^<]+)</option>', select)


class TestCreationOrigins(unittest.TestCase):
    def test_the_dropdown_offers_exactly_the_catalog_origins(self) -> None:
        self.assertEqual({value for value, _ in _options()}, {info["name"] for info in COMMANDER_BACKGROUNDS.values()})

    def test_every_option_label_states_its_skill_bonuses(self) -> None:
        by_name = {info["name"]: info for info in COMMANDER_BACKGROUNDS.values()}
        for value, label in _options():
            for skill, bonus in by_name[value]["skills"].items():
                self.assertIn(f"+{bonus} {skill}", label, f"{value}: {label}")

    def test_every_option_value_grants_training_in_the_engine(self) -> None:
        from voidfarer.character import match_background
        for value, _ in _options():
            self.assertIsNotNone(match_background(value), value)

    def test_a_description_line_follows_the_selection(self) -> None:
        self.assertIn('id="charBackgroundHint"', HTML)
        self.assertIn("syncBackgroundHint()", JS)
        self.assertIn("character_background_catalog", JS.split("this.syncBackgroundHint = function", 1)[1][:900])
        self.assertIn('getElementById("charBackground")?.addEventListener("change"', JS)


if __name__ == "__main__":
    unittest.main()
