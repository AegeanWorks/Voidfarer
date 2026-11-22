"""The post-story captain trains one specialist to rank five (ADR-448)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _member(member_id, skill=2, **fields):
    row = {"id": member_id, "role": "engineer", "status": "active",
           "injury_ticks": 0, "skill": skill}
    row.update(fields)
    return row


def _captain(crew=None, docked=True, credits=50000, completed=True, done=False,
             attempts=0):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.veteran_done = done
    captain.veteran_attempts = attempts
    captain.state = {
        "story_status": {"completed": completed},
        "orbiting_body": {"id": "sol_station", "station_dockable": docked},
        "ship": {"credits": credits},
        "crew": crew if crew is not None else [_member("crew_1", skill=2)],
    }
    return captain


class VeteranCrewTest(unittest.TestCase):
    def test_the_best_specialist_is_trained(self):
        captain = _captain([
            _member("crew_1", skill=2),
            _member("crew_2", skill=4),
        ])
        self.assertEqual(
            captain._veteran_crew_action(),
            ("/api/crew/train", {"crew_id": "crew_2"}, "crew_train"),
        )
        self.assertEqual(captain.veteran_attempts, 1)

    def test_a_rank_five_specialist_ends_the_training(self):
        captain = _captain([_member("crew_1", skill=5)])
        self.assertIsNone(captain._veteran_crew_action())
        self.assertTrue(captain.veteran_done)

    def test_higher_ranks_beyond_the_milestone_are_left_alone(self):
        captain = _captain([_member("crew_1", skill=7)])
        self.assertIsNone(captain._veteran_crew_action())

    def test_nothing_trains_before_the_campaign(self):
        captain = _captain(completed=False)
        self.assertIsNone(captain._veteran_crew_action())

    def test_a_dock_is_required(self):
        captain = _captain(docked=False)
        self.assertIsNone(captain._veteran_crew_action())

    def test_the_attempt_budget_bounds_a_refused_drill(self):
        captain = _captain(attempts=AiCaptain.VETERAN_TRAIN_LIMIT)
        self.assertIsNone(captain._veteran_crew_action())

    def test_a_broke_captain_skips_the_drill(self):
        captain = _captain(credits=100)
        self.assertIsNone(captain._veteran_crew_action())

    def test_an_injured_specialist_still_trains(self):
        captain = _captain([_member("crew_1", skill=4, injury_ticks=3)])
        self.assertEqual(
            captain._veteran_crew_action()[1]["crew_id"], "crew_1",
            "the drill is bedside-safe; the engine only checks skill and credits",
        )

    def test_no_crew_means_no_drill(self):
        self.assertIsNone(_captain(crew=[])._veteran_crew_action())

    def test_the_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.VETERAN_TARGET, CODEX_MAP["veteran_crew"].target
        )


if __name__ == "__main__":
    unittest.main()
