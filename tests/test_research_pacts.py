"""Research pacts: standing gate, war suspension and passive research bonus."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import GameState, WarState


class ResearchPactTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def _set_standing(self, faction_id, standing):
        standings = dict(self.engine.state.ship.faction_standings)
        standings[faction_id] = standing
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(faction_standings=standings)
        )

    def test_pact_requires_standing_60_and_forms_once(self):
        ok, message = self.engine.faction_diplomacy("sol_coalition", "research_pact")
        self.assertFalse(ok)
        self.assertIn("standing", message.lower())

        self._set_standing("sol_coalition", 60)
        ok, message = self.engine.faction_diplomacy("sol_coalition", "research_pact")
        self.assertTrue(ok, message)
        self.assertIn("sol_coalition", self.engine.state.ship.research_pacts)
        self.assertIn("RESEARCH PACT", message)
        ok, message = self.engine.faction_diplomacy("sol_coalition", "research_pact")
        self.assertFalse(ok)
        self.assertIn("already", message.lower())

    def test_war_blocks_and_suspends_the_pact(self):
        self._set_standing("sol_coalition", 60)
        war = WarState(
            id="research_war",
            attacker_id="sol_coalition",
            defender_id="nebula_collective",
            started_tick=0,
        )
        self.engine.state = self.engine._clone_state(wars=(war,))
        ok, message = self.engine.faction_diplomacy("sol_coalition", "research_pact")
        self.assertFalse(ok)
        self.assertIn("war", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(research_pacts=("sol_coalition",))
        )
        self.assertFalse(self.engine.research_pact_active("sol_coalition"))
        self.assertEqual(self.engine.research_pact_multiplier(), 1.0)

    def test_multiplier_scales_with_active_pacts(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                research_pacts=("sol_coalition", "nebula_collective")
            )
        )
        self.assertAlmostEqual(self.engine.research_pact_multiplier(), 1.10)

    def test_report_and_snapshot_expose_pacts(self):
        self._set_standing("sol_coalition", 60)
        self.engine.faction_diplomacy("sol_coalition", "research_pact")
        report = self.engine.get_research_report()
        self.assertIn("sol_coalition", report["research_pacts"])
        self.assertEqual(report["active_research_pacts"], 1)
        self.assertEqual(report["pact_bonus"], 0.05)
        snapshot = self.engine.get_status_snapshot()
        self.assertIn("sol_coalition", snapshot["research"]["research_pacts"])
        self.assertEqual(snapshot["research"]["pact_bonus"], 0.05)

    def test_save_round_trip_keeps_pacts(self):
        self._set_standing("sol_coalition", 60)
        self.engine.faction_diplomacy("sol_coalition", "research_pact")
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.ship.research_pacts, ("sol_coalition",))

    def test_legacy_payload_defaults_to_no_pacts(self):
        payload = self.engine.state.to_dict()
        payload["ship"].pop("research_pacts", None)
        restored = GameState.from_dict(payload)
        self.assertEqual(restored.ship.research_pacts, ())


if __name__ == "__main__":
    unittest.main()
