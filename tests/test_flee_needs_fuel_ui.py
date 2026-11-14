"""The Flee button says when there is too little fuel to use it (ADR-283)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "voidfarer" / "static" / "app.js"
ENGINE = ROOT / "voidfarer" / "engine.py"


class FleeNeedsFuelUiTests(unittest.TestCase):
    def test_button_disables_below_the_engine_fuel_cost(self) -> None:
        engine = ENGINE.read_text(encoding="utf-8")
        cost = int(re.search(r'if self\.state\.ship\.fuel < (\d+):\n\s+return False, "Insufficient fuel for emergency jump', engine).group(1))
        app = APP.read_text(encoding="utf-8")
        self.assertTrue("this.btnCombatFlee.disabled" in app, "the Flee button must manage its disabled state")
        block = app[app.index("this.btnCombatFlee.disabled") - 400:][:900]
        self.assertTrue(f"< {cost}" in block, "fuel threshold must match the engine")
        self.assertTrue("this.btnCombatFlee.title" in block, "a reason must be given")
        self.assertTrue(f"NEED {cost} FUEL" in block, "label must name the need")


if __name__ == "__main__":
    unittest.main()
