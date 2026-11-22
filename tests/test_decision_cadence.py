"""The captain runs decisions at the frequent cadence for the decision milestone (ADR-445)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP
from voidfarer.engine import SimulationEngine


def _captain():
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.state = {
        "story_status": {"completed": False},
        "time": {"is_paused": False},
        "ship": {"hull": 100, "max_hull": 100, "fuel": 60, "max_fuel": 60},
    }
    return captain


class DecisionCadenceTest(unittest.TestCase):
    def test_the_first_step_sets_the_frequent_cadence(self):
        self.assertEqual(
            _captain()._choose(0),
            ("/api/settings/decisions", {"cadence": "frequent"}, "settings"),
        )

    def test_a_pending_decision_resolves_with_the_first_choice(self):
        captain = _captain()
        captain.state["pending_decision"] = {
            "id": "d1",
            "choices": [{"id": "accept"}, {"id": "decline"}],
        }
        self.assertEqual(
            captain._choose(5),
            ("/api/decision/resolve", {"choice_id": "accept"}, "decision"),
        )

    def test_the_frequent_cadence_widens_the_decision_windows(self):
        relaxed_ticks, relaxed_chance = SimulationEngine.DECISION_CADENCE["relaxed"]
        frequent_ticks, frequent_chance = SimulationEngine.DECISION_CADENCE["frequent"]
        self.assertLess(frequent_ticks, relaxed_ticks)
        self.assertGreater(frequent_chance, relaxed_chance)

    def test_the_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.DECISION_TARGET, CODEX_MAP["decision_maker"].target
        )


if __name__ == "__main__":
    unittest.main()
