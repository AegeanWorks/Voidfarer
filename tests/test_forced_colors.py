"""Windows High Contrast (forced colors): meter fills must stay visible, not vanish with their backgrounds."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "style.css").read_text(
    encoding="utf-8").replace("\r\n", "\n")


def _block() -> str:
    match = re.search(r"@media \(forced-colors: active\) \{(.*)\n\}\n", CSS, re.S)
    return match.group(1) if match else ""


class TestForcedColors(unittest.TestCase):
    def test_a_forced_colors_block_exists(self) -> None:
        self.assertTrue(_block().strip())

    def test_every_meter_fill_class_is_opted_out_and_painted_with_a_system_color(self) -> None:
        block = _block()
        for cls in (".meter-fill", ".hull-fill", ".shield-fill", ".fuel-fill", ".reactor-heat-fill",
                    ".crew-morale-fill", ".cargo-meter-fill", ".contract-progress-fill",
                    ".skill-bar-fill", ".codex-progress-fill", ".mastery-fill", ".combat-meter-fill",
                    ".standing-bar-fill", ".character-xp-fill", ".fleet-xp-fill"):
            self.assertIn(cls, block, cls)
        self.assertIn("forced-color-adjust: none", block)
        self.assertIn("background: Highlight", block)

    def test_actionable_vital_cards_keep_a_visible_boundary(self) -> None:
        block = _block()
        self.assertIn("#vitalHullCard.is-low", block)
        self.assertIn("#vitalFuelCard.is-low", block)
        self.assertIn("border-color: Mark", block)


if __name__ == "__main__":
    unittest.main()
