"""Codex milestones for pacts, captains, outposts and auto-freight."""

from dataclasses import replace
import unittest

from voidfarer.codex import build_codex_report, metric_value
from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship
from voidfarer.models import Outpost, QuantumAutomation


class CodexProgressionTest(unittest.TestCase):
    def _state(self):
        engine = SimulationEngine(seed=42)
        outpost = Outpost(
            id="codex_outpost",
            name="Codex Outpost",
            system_id="sol",
            body_id="sol_body_1",
            outpost_type="mining",
            level=3,
            specialization="industry",
        )
        escort = replace(
            build_fleet_ship("corvette", "sol", 0),
            captain_id="crew_engineer_1",
            captain_role="engineer",
        )
        return engine._clone_state(
            ship=engine._clone_ship(
                trade_pacts=("sol_coalition",),
                research_pacts=("nebula_collective",),
                fleet_ships=(escort,),
            ),
            outposts=(outpost,),
            quantum_automation=QuantumAutomation(orders=5),
            stats={"outposts_repaired": 1},
        )

    def test_new_metrics_read_state(self):
        state = self._state()
        self.assertEqual(metric_value(state, "trade_pacts"), 1)
        self.assertEqual(metric_value(state, "research_pacts"), 1)
        self.assertEqual(metric_value(state, "escort_captains"), 1)
        self.assertEqual(metric_value(state, "outposts_specialized"), 1)
        self.assertEqual(metric_value(state, "outposts_repaired"), 1)
        self.assertEqual(metric_value(state, "quantum_auto_orders"), 5)

    def test_new_milestones_complete_and_are_listed(self):
        report = build_codex_report(self._state())
        by_id = {entry["id"]: entry for entry in report["entries"]}
        for entry_id in (
            "trade_envoy",
            "science_envoy",
            "fleet_captain",
            "outpost_specialist",
            "outpost_warden",
            "quantum_broker",
        ):
            self.assertIn(entry_id, by_id)
            self.assertTrue(by_id[entry_id]["completed"], entry_id)

    def test_repair_outpost_increments_the_codex_stat(self):
        engine = SimulationEngine(seed=42)
        outpost = Outpost(
            id="repair_codex",
            name="Repair Codex",
            system_id="sol",
            body_id="sol_body_1",
            outpost_type="mining",
            integrity=40.0,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(credits=1000),
            outposts=(outpost,),
        )
        ok, message = engine.repair_outpost(outpost.id)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.stats["outposts_repaired"], 1)


if __name__ == "__main__":
    unittest.main()
