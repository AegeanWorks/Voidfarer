"""The post-graduation objective hand-off stays on the HUD, not in a hidden tab."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


class ObjectiveHandoffContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")

    def test_objective_strip_is_outside_the_contracts_tab(self):
        self.assertIn('id="objectiveStrip"', self.html)
        self.assertIn('data-testid="objective-strip"', self.html)
        self.assertLess(
            self.html.index('id="objectiveStrip"'),
            self.html.index('id="tabContentContracts"'),
            "the next objective must not live inside a tab the academy leaves hidden",
        )

    def test_comms_pill_lives_in_top_actions(self):
        start = self.html.index('<div class="hud-top-actions">')
        end = self.html.index("<!-- Vital Telemetry Meters -->")
        block = self.html[start:end]
        self.assertIn('id="btnCommsPill"', block)
        self.assertIn('data-testid="comms-pill"', block)

    def test_render_mission_pins_populates_the_strip(self):
        self.assertIn("this.objectiveStrip.hidden = !showObjective", self.js)
        self.assertIn("this.objectiveText.textContent", self.js)
        self.assertIn("const showObjective = !inAcademy", self.js)

    def test_comms_pill_tracks_unread_messages(self):
        self.assertIn("this.commsPillCount.textContent = String(unread)", self.js)
        self.assertIn('this.commsPill?.addEventListener("click"', self.js)

    def test_strip_has_a_compact_css_contract(self):
        css = (STATIC / "style.css").read_text(encoding="utf-8")
        self.assertIn(".objective-strip {", css)
        self.assertIn("min-height: 28px", css)


if __name__ == "__main__":
    unittest.main()
