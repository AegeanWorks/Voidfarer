"""CREW cash-flow strip: a payroll runway warns before wages go unpaid."""

from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


class TestPayrollRunway(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.js = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.css = (STATIC / "style.css").read_text(encoding="utf-8")

    def test_strip_renders_the_runway_after_net(self) -> None:
        net = self.js.index('NET <strong style="color:${netColor}">')
        runway = self.js.index('RUNWAY <strong>${runway.label}</strong>')
        self.assertLess(net, runway)

    def test_runway_levels_are_defined_for_danger_warn_and_ok(self) -> None:
        self.assertIn("payrollRunway(credits, netPerMonth)", self.js)
        self.assertIn('months < 1 ? "danger" : months < 3 ? "warn" : "ok"', self.js)
        self.assertIn("SELF-FUNDING", self.js)
        for level in ("is-ok", "is-warn", "is-danger"):
            self.assertIn(f".cashflow-runway.{level}", self.css)

    def test_tooltip_states_the_consequence(self) -> None:
        self.assertIn("unpaid wages drain crew morale and cause desertion", self.js)


if __name__ == "__main__":
    unittest.main()
