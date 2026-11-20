"""The post-story captain keeps away teams deployed (ADR-433)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(
    available=(),
    missions=(),
    stat=0,
    story=True,
    done=False,
    body="b1",
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.away_rotation_done = done
    captain.state = {
        "story_status": {"completed": story},
        "stats": {"away_missions": stat},
        "orbiting_body": {"id": body, "station_dockable": False},
        "ship": {"hull": 100, "away_missions": list(missions)},
        "away_report": {"available": list(available)},
    }
    return captain


def _mission(mission_id="geological_survey", **fields):
    row = {
        "id": mission_id,
        "mission_type": mission_id,
        "worked": False,
        "available": True,
        "missing_crew": 0,
    }
    row.update(fields)
    return row


class AwayRotationPolicyTest(unittest.TestCase):
    def test_an_available_mission_is_launched_after_the_campaign(self):
        captain = _captain(available=[_mission()])
        self.assertEqual(
            captain._away_rotation_action(),
            ("/api/away/launch", {"mission_type": "geological_survey"}, "away"),
        )

    def test_the_first_available_mission_wins(self):
        captain = _captain(available=[
            _mission("xenobiology_survey"),
            _mission("salvage_sweep"),
        ])
        self.assertEqual(
            captain._away_rotation_action()[1]["mission_type"],
            "xenobiology_survey",
        )

    def test_nothing_launches_before_the_campaign(self):
        captain = _captain(available=[_mission()], story=False)
        self.assertIsNone(captain._away_rotation_action())

    def test_an_active_mission_is_waited_on(self):
        captain = _captain(
            available=[_mission()],
            missions=[{"id": "away_1", "mission_type": "geological_survey"}],
        )
        self.assertIsNone(captain._away_rotation_action())

    def test_the_target_stops_the_rotation(self):
        captain = _captain(available=[_mission()], stat=5)
        self.assertIsNone(captain._away_rotation_action())
        self.assertTrue(captain.away_rotation_done)

    def test_a_worked_or_unstaffable_mission_is_skipped(self):
        captain = _captain(available=[
            _mission(worked=True),
            _mission("salvage_sweep", available=False, missing_crew=1),
        ])
        self.assertIsNone(captain._away_rotation_action())

    def test_a_refused_pair_is_not_retried(self):
        captain = _captain(available=[
            _mission("geological_survey"),
            _mission("salvage_sweep"),
        ])
        captain.away_launch_tried.add(("geological_survey", "b1"))
        self.assertEqual(
            captain._away_rotation_action()[1]["mission_type"], "salvage_sweep"
        )

    def test_the_target_matches_the_codex_milestone(self):
        self.assertEqual(
            AiCaptain.AWAY_MISSION_TARGET, CODEX_MAP["field_team"].target
        )


class AwayRecallGuardTest(unittest.TestCase):
    def test_the_rotation_protects_its_single_mission_from_recall(self):
        captain = _captain(
            missions=[{"id": "away_1", "mission_type": "geological_survey"}]
        )
        captain.away_protected_mission = "away_old"
        self.assertIsNone(captain._away_recall_action())
        self.assertEqual(captain.away_protected_mission, "away_1")

    def test_a_second_mission_is_still_recalled(self):
        captain = _captain(
            missions=[
                {"id": "away_1", "mission_type": "geological_survey"},
                {"id": "away_2", "mission_type": "salvage_sweep"},
            ]
        )
        captain.away_protected_mission = "away_1"
        self.assertEqual(
            captain._away_recall_action()[1]["mission_id"], "away_2"
        )


if __name__ == "__main__":
    unittest.main()
