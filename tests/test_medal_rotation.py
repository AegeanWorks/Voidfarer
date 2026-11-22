"""The away rotation pins a medal candidate so two medals bank (ADR-447)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _member(member_id, medals=(), missions=0, battles=0, **fields):
    row = {
        "id": member_id,
        "name": member_id,
        "role": "engineer",
        "status": "active",
        "injury_ticks": 0,
        "station": "",
        "medals": list(medals),
        "away_missions": missions,
        "battles": battles,
        "assigned_mission_id": None,
    }
    row.update(fields)
    return row


def _mission(mission_id="geological_survey", team_size=1, **fields):
    row = {
        "id": mission_id,
        "mission_type": mission_id,
        "team_size": team_size,
        "worked": False,
        "available": True,
        "missing_crew": 0,
    }
    row.update(fields)
    return row


def _captain(
    crew=(),
    available=(),
    ships=(),
    medals=0,
    stat=5,
    completed=True,
    medal_missions=0,
    tried=(),
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.medal_missions = medal_missions
    captain.away_launch_tried = set(tried)
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"away_missions": stat},
        "orbiting_body": {"id": "b1", "station_dockable": False},
        "ship": {"hull": 100, "away_missions": []},
        "crew": list(crew),
        "fleet_manager": {"ships": list(ships)},
        "away_report": {"body": {"id": "b1"}, "available": list(available)},
    }
    return captain


class MedalCandidateTest(unittest.TestCase):
    def test_a_mission_candidate_with_a_medal_is_passed(self):
        captain = _captain(
            crew=[_member("crew_1")],
            available=[_mission()],
        )
        self.assertEqual(
            captain._away_rotation_action(),
            ("/api/away/launch",
             {"mission_type": "geological_survey", "crew_ids": ["crew_1"]},
             "away"),
        )

    def test_the_most_experienced_unmedalled_member_leads(self):
        captain = _captain(
            crew=[_member("crew_1", missions=1), _member("crew_2", missions=4)],
            available=[_mission(team_size=2)],
        )
        self.assertEqual(
            captain._away_rotation_action()[1]["crew_ids"],
            ["crew_2", "crew_1"],
        )

    def test_a_member_who_already_has_the_explorer_medal_steps_back(self):
        deep = AiCaptain.DEEP_EXPLORER_MEDAL
        captain = _captain(
            crew=[
                _member("crew_1", medals=(deep,), missions=6),
                _member("crew_2", missions=0),
            ],
            available=[_mission(team_size=2)],
        )
        self.assertEqual(
            captain._away_rotation_action()[1]["crew_ids"],
            ["crew_2", "crew_1"],
        )

    def test_an_escort_commander_is_not_deployed(self):
        captain = _captain(
            crew=[_member("crew_1"), _member("crew_2")],
            ships=[{"id": "escort_1", "hull": 90, "captain_id": "crew_1"}],
            available=[_mission()],
        )
        self.assertEqual(
            captain._away_rotation_action()[1]["crew_ids"], ["crew_2"]
        )

    def test_an_injured_or_deployed_member_is_skipped(self):
        captain = _captain(
            crew=[
                _member("crew_1", injury_ticks=3),
                _member("crew_2", assigned_mission_id="away_1"),
                _member("crew_4"),
            ],
            available=[_mission()],
        )
        self.assertEqual(
            captain._away_rotation_action()[1]["crew_ids"], ["crew_4"]
        )

    def test_a_bridge_station_does_not_block_deployment(self):
        captain = _captain(
            crew=[_member("crew_1", station="engineering")],
            available=[_mission()],
        )
        self.assertEqual(
            captain._away_rotation_action()[1]["crew_ids"], ["crew_1"],
            "the engine lets a bridge member deploy and simply drops their bonus",
        )

    def test_an_outpost_crew_member_is_not_deployed(self):
        captain = _captain(
            crew=[_member("crew_1"), _member("crew_2")],
            available=[_mission()],
        )
        captain.state["outposts"] = [
            {"id": "outpost_1", "assigned_crew": ["crew_1"]},
        ]
        self.assertEqual(
            captain._away_rotation_action()[1]["crew_ids"], ["crew_2"],
            "an outpost member cannot leave the colony, so the engine would refuse",
        )

    def test_a_member_on_an_active_mission_is_not_deployed(self):
        captain = _captain(
            crew=[_member("crew_1"), _member("crew_2")],
            available=[_mission()],
        )
        captain.state["away_report"]["active"] = [
            {"id": "away_1", "crew_ids": ["crew_1"]},
        ]
        self.assertEqual(
            captain._away_rotation_action()[1]["crew_ids"], ["crew_2"]
        )

    def test_a_mission_that_needs_more_crew_than_are_free_is_skipped(self):
        captain = _captain(
            crew=[_member("crew_1")],
            available=[
                _mission("distress_sweep", team_size=3),
                _mission("geological_survey", team_size=1),
            ],
        )
        self.assertEqual(
            captain._away_rotation_action()[1]["mission_type"],
            "geological_survey",
        )

    def test_the_track_stops_at_two_medals(self):
        captain = _captain(crew=[_member("crew_1")], available=[_mission()])
        captain.state["crew"] = [
            _member("crew_1", medals=("Deep Explorer", "Combat Veteran"))
        ]
        self.assertIsNone(captain._away_rotation_action())
        self.assertTrue(captain.away_rotation_done)

    def test_the_track_stops_at_the_mission_budget(self):
        captain = _captain(
            crew=[_member("crew_1")],
            available=[_mission()],
            medal_missions=AiCaptain.MEDAL_MISSION_LIMIT,
        )
        self.assertIsNone(captain._away_rotation_action())

    def test_a_medal_mission_after_the_field_target_is_counted(self):
        captain = _captain(crew=[_member("crew_1")], available=[_mission()])
        captain._away_rotation_action()
        self.assertEqual(captain.medal_missions, 1)

    def test_the_field_target_still_drives_the_first_missions(self):
        captain = _captain(
            crew=[_member("crew_1")],
            available=[_mission()],
            stat=0,
        )
        self.assertEqual(captain._away_rotation_action()[0], "/api/away/launch")

    def test_the_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.DECORATED_TARGET, CODEX_MAP["decorated_crew"].target
        )


if __name__ == "__main__":
    unittest.main()
