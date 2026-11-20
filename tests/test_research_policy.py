"""The post-story captain keeps the research bench busy (ADR-432)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(completed=(), active=None, queue=(), available=(), story=True, done=False):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.research_done = done
    captain.state = {
        "story_status": {"completed": story},
        "research": {
            "completed": list(completed),
            "active_project_id": active,
            "queue": list(queue),
            "available": list(available),
        },
    }
    return captain


class ResearchPolicyTest(unittest.TestCase):
    def test_the_next_available_project_starts(self):
        captain = _captain(available=[{"id": "deep_survey_arrays"}])
        self.assertEqual(
            captain._research_action(),
            ("/api/research/start", {"project_id": "deep_survey_arrays"}, "research"),
        )

    def test_the_first_available_project_wins(self):
        captain = _captain(available=[
            {"id": "deep_survey_arrays"},
            {"id": "plasma_weapons"},
        ])
        self.assertEqual(
            captain._research_action()[1]["project_id"], "deep_survey_arrays"
        )

    def test_a_running_project_is_left_alone(self):
        captain = _captain(
            active="advanced_cooling",
            available=[{"id": "deep_survey_arrays"}],
        )
        self.assertIsNone(captain._research_action())

    def test_a_queued_project_is_left_alone(self):
        captain = _captain(
            queue=["plasma_weapons"],
            available=[{"id": "deep_survey_arrays"}],
        )
        self.assertIsNone(captain._research_action())

    def test_nothing_starts_before_the_campaign(self):
        captain = _captain(
            available=[{"id": "deep_survey_arrays"}], story=False
        )
        self.assertIsNone(captain._research_action())

    def test_the_target_stops_the_policy(self):
        completed = ["advanced_cooling", "deep_survey_arrays", "plasma_weapons",
                     "diplomatic_corps"]
        captain = _captain(
            completed=completed,
            available=[{"id": "colonial_administration"}],
        )
        self.assertIsNone(captain._research_action())
        self.assertTrue(captain.research_done)

    def test_a_refused_project_is_not_retried(self):
        captain = _captain(available=[
            {"id": "deep_survey_arrays"},
            {"id": "plasma_weapons"},
        ])
        captain.research_tried.add("deep_survey_arrays")
        self.assertEqual(
            captain._research_action()[1]["project_id"], "plasma_weapons"
        )

    def test_an_empty_catalog_starts_nothing(self):
        self.assertIsNone(_captain()._research_action())

    def test_the_target_matches_the_codex_milestone(self):
        self.assertEqual(
            AiCaptain.RESEARCH_TARGET, CODEX_MAP["technologist"].target
        )


if __name__ == "__main__":
    unittest.main()
