"""The browser review tool drives customs through the engine, not a stale client-side key."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.ui_browser import _prepare_customs
from voidfarer.encounters import encounter_report
from voidfarer.engine import SimulationEngine

TOOL = Path(__file__).resolve().parent.parent / "tools" / "ui_browser.py"


class TestCustomsScenario(unittest.TestCase):
    def test_prepared_customs_surfaces_in_the_unified_encounter_report(self) -> None:
        engine = SimulationEngine(seed=42)
        self.assertTrue(_prepare_customs(engine))
        report = encounter_report(engine.state)
        self.assertTrue(report["active"])
        self.assertEqual(report["kind"], "customs")
        self.assertEqual([a["id"] for a in report["encounter"]["actions"]],
                         ["bribe", "jettison", "confiscate", "flee"])

    def test_scenario_no_longer_injects_the_retired_client_key(self) -> None:
        self.assertNotIn("state.active_customs = {", TOOL.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
