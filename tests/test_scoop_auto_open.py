"""With a low tank and a scoop available, the target card opens its more-actions panel once so the scoop is visible."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


def _block() -> str:
    return JS.split("    syncTargetActionDisclosure() {", 1)[1][:2600]


class TestScoopAutoOpen(unittest.TestCase):
    def test_it_requires_a_low_tank_and_an_enabled_scoop(self) -> None:
        block = _block()
        self.assertIn("fuelFraction <= 0.25", block)
        self.assertIn("!this.btnScoopFuel.disabled", block)

    def test_it_opens_once_per_target_through_the_normal_disclosure(self) -> None:
        block = _block()
        self.assertIn("this._scoopAutoOpen !== autoKey", block)
        self.assertIn("this.applyDisclosure(this.btnToggleTargetActions, this.targetMoreActions, null);", block)
        self.assertIn("this._scoopAutoOpen = autoKey;", block)

    def test_the_marker_resets_when_the_need_ends_so_it_can_open_again(self) -> None:
        self.assertIn("this._scoopAutoOpen = null;", _block())

    def test_it_never_forces_the_panel_open_after_the_player_closed_it(self) -> None:
        self.assertIn("this.targetMoreActions.hidden", _block())


if __name__ == "__main__":
    unittest.main()
