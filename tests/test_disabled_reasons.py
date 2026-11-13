"""Disabled perk and upgrade buttons explain themselves instead of failing silently."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestDisabledReasons(unittest.TestCase):
    def test_perk_button_names_the_missing_point_or_prerequisite(self) -> None:
        self.assertIn("perkReason", JS)
        self.assertIn("Needs a talent point to unlock.", JS)
        self.assertIn("Unlock ${requires", JS)
        self.assertIn('title="${this.escapeHtml(perkReason)}"', JS)

    def test_upgrade_button_states_the_credit_shortfall_or_installed_state(self) -> None:
        self.assertIn("Already installed in the ${u.slot} slot.", JS)
        self.assertIn("Need ${u.cost - credits} more credits.", JS)
        self.assertIn("btn.title = reason;", JS)

    def test_a_reason_is_only_set_when_the_button_is_disabled(self) -> None:
        self.assertIn("const reason = isEquipped", JS)
        self.assertIn(": (credits < u.cost ?", JS)

    def test_training_weapons_modules_and_chassis_explain_a_disabled_state(self) -> None:
        for text in ("Needs a skill point: level up to earn one.",
                     "Weapons are bought at a drydock: dock at a station first.",
                     "Structural refits need a station: dock first.",
                     "That slot is occupied: remove the installed module first.",
                     "Dock at a station to commission a chassis."):
            self.assertIn(text, JS)


if __name__ == "__main__":
    unittest.main()
