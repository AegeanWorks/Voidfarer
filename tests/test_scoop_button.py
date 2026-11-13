"""The scoop button states its remaining taps, expected yield and reactor heat."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestScoopButton(unittest.TestCase):
    def test_label_shows_taps_left_out_of_the_reservoir(self) -> None:
        self.assertIn("const tapsLeft = Math.max(0, scoop.reserve - scoop.tapped);", JS)
        self.assertIn("`SCOOP FUEL (${tapsLeft}/${scoop.reserve} TAPS)`", JS)

    def test_tooltip_states_yield_and_heat_and_the_recharge_wait(self) -> None:
        self.assertIn("about ${scoop.base} fuel", JS)
        self.assertIn("+${scoop.heat} reactor heat", JS)
        self.assertIn("Next volatile tap in ${scoop.next_tap_in} ticks", JS)

    def test_unavailable_states_keep_their_original_labels(self) -> None:
        self.assertIn('"RESERVOIR DEPLETED"', JS)
        self.assertIn('"TANKS FULL"', JS)


if __name__ == "__main__":
    unittest.main()
