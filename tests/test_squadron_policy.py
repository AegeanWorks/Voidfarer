"""The post-story captain builds and staffs a squadron (ADR-435)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(
    commissions=1,
    assigned=1,
    ships=(),
    crew=(),
    credits=50000,
    docked=True,
    story=True,
    done=False,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.squadron_done = done
    captain.state = {
        "story_status": {"completed": story},
        "orbiting_body": {"id": "b1", "station_dockable": docked},
        "current_system": {"id": "sol"},
        "stats": {
            "escort_commissions_corvette": commissions,
            "escort_captains_assigned": assigned,
        },
        "ship": {"credits": credits, "away_missions": []},
        "crew": list(crew),
        "outposts": [],
        "fleet_manager": {
            "ships": list(ships),
            "catalog": {
                "corvette": {"cost": 2200, "name": "Corvette"},
                "frigate": {"cost": 4200, "name": "Frigate"},
            },
        },
    }
    return captain


def _ship(ship_id="escort_corvette_1", hull=90, captain_id=""):
    return {"id": ship_id, "hull": hull, "captain_id": captain_id}


def _crew(member_id="crew_engineer_6", role="engineer", station=""):
    return {
        "id": member_id, "role": role, "status": "active",
        "injury_ticks": 0, "station": station, "skill": 4,
    }


class SquadronPolicyTest(unittest.TestCase):
    def test_an_unstaffed_escort_gets_a_captain_first(self):
        captain = _captain(
            ships=[_ship()],
            crew=[_crew()],
        )
        self.assertEqual(
            captain._squadron_action(),
            ("/api/fleet/escort/captain",
             {"ship_id": "escort_corvette_1", "crew_id": "crew_engineer_6",
              "action": "assign"}, "escort_captain"),
        )

    def test_a_second_escort_is_commissioned_once_every_hull_is_staffed(self):
        captain = _captain(
            commissions=2,
            assigned=1,
            ships=[_ship(captain_id="crew_engineer_1")],
            crew=[_crew()],
        )
        self.assertEqual(
            captain._squadron_action(),
            ("/api/fleet/escort/buy",
             {"escort_type": "corvette", "system_id": "sol"}, "fleet"),
        )

    def test_nothing_runs_before_the_campaign(self):
        captain = _captain(ships=[_ship()], crew=[_crew()], story=False)
        self.assertIsNone(captain._squadron_action())

    def test_nothing_is_bought_away_from_a_dock(self):
        captain = _captain(commissions=1, assigned=1, docked=False)
        self.assertIsNone(captain._squadron_action())

    def test_the_credit_reserve_blocks_a_purchase(self):
        captain = _captain(commissions=1, assigned=1, credits=2300)
        self.assertIsNone(captain._squadron_action())

    def test_both_targets_stop_the_policy(self):
        captain = _captain(commissions=3, assigned=3)
        self.assertIsNone(captain._squadron_action())
        self.assertTrue(captain.squadron_done)

    def test_a_refused_pair_falls_through_to_the_next_crew(self):
        captain = _captain(
            ships=[_ship()],
            crew=[_crew("crew_engineer_6"), _crew("crew_engineer_7")],
        )
        captain.squadron_tried.add(("escort_corvette_1", "crew_engineer_6"))
        self.assertEqual(
            captain._squadron_action()[1]["crew_id"], "crew_engineer_7"
        )

    def test_a_stationed_or_injured_member_is_not_a_captain(self):
        captain = _captain(
            ships=[_ship()],
            crew=[
                _crew("crew_engineer_1", station="engineering"),
                {**_crew("crew_engineer_2"), "injury_ticks": 2},
                {**_crew("crew_engineer_3"), "status": "dead"},
            ],
        )
        self.assertIsNone(
            captain._squadron_action(),
            "no eligible crew means no assignment",
        )

    def test_a_destroyed_hull_is_not_staffed(self):
        captain = _captain(
            commissions=3,
            assigned=1,
            ships=[_ship(hull=0)],
            crew=[_crew()],
        )
        self.assertIsNone(captain._squadron_action())

    def test_the_targets_match_the_codex_milestones(self):
        self.assertEqual(
            AiCaptain.SQUADRON_TARGET, CODEX_MAP["squadron"].target
        )
        self.assertEqual(
            AiCaptain.CAPTAIN_CORPS_TARGET, CODEX_MAP["captain_corps"].target
        )


if __name__ == "__main__":
    unittest.main()
