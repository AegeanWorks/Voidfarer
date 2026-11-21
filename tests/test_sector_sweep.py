"""The post-story captain sweeps three systems for the sector milestone (ADR-436)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(
    bodies,
    connections=(),
    orbiting="a",
    surveyed=1,
    completed=True,
    done=False,
    scans=0,
    tried=(),
    jumps=0,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.survey_done = done
    captain.survey_scans = scans
    captain.survey_jumps = jumps
    captain.survey_systems_tried = set(tried)
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"systems_surveyed": surveyed},
        "current_system": {
            "id": "sol",
            "bodies": bodies,
            "connections": list(connections),
        },
        "orbiting_body": {"id": orbiting, "station_dockable": False},
        "ship": {"landed_body_id": ""},
    }
    return captain


class SectorSweepTest(unittest.TestCase):
    def test_a_fully_scanned_system_jumps_to_the_next_connection(self):
        captain = _captain(
            [{"id": "a", "scan_completed": True}],
            connections=["vega", "altair"],
        )
        self.assertEqual(
            captain._survey_action(),
            ("/api/navigate", {"system_id": "vega"}, "navigate"),
        )

    def test_a_tried_connection_is_skipped(self):
        captain = _captain(
            [{"id": "a", "scan_completed": True}],
            connections=["vega", "altair"],
            tried=["sol", "vega"],
        )
        self.assertEqual(
            captain._survey_action()[1]["system_id"], "altair"
        )

    def test_the_jump_marks_the_target_as_tried(self):
        captain = _captain(
            [{"id": "a", "scan_completed": True}],
            connections=["vega"],
        )
        captain._survey_action()
        self.assertIn("vega", captain.survey_systems_tried)
        self.assertEqual(captain.survey_jumps, 1)

    def test_the_completed_system_is_marked_tried(self):
        captain = _captain(
            [{"id": "a", "scan_completed": True}],
            connections=["vega"],
        )
        captain._survey_action()
        self.assertIn("sol", captain.survey_systems_tried)

    def test_an_exhausted_system_is_abandoned_for_the_next_one(self):
        captain = _captain(
            [{"id": "a", "scan_completed": False}],
            connections=["vega"],
            scans=AiCaptain.SURVEY_SCAN_LIMIT,
        )
        self.assertEqual(
            captain._survey_action(),
            ("/api/navigate", {"system_id": "vega"}, "navigate"),
        )
        self.assertIn("sol", captain.survey_systems_tried)

    def test_no_untried_connection_ends_the_sweep(self):
        captain = _captain(
            [{"id": "a", "scan_completed": True}],
            connections=["vega"],
            tried=["sol", "vega"],
        )
        self.assertIsNone(captain._survey_action())
        self.assertTrue(captain.survey_done)

    def test_an_isolated_system_ends_the_sweep(self):
        captain = _captain([{"id": "a", "scan_completed": True}])
        self.assertIsNone(captain._survey_action())
        self.assertTrue(captain.survey_done)

    def test_the_target_stops_the_sweep(self):
        captain = _captain(
            [{"id": "a", "scan_completed": False}],
            connections=["vega"],
            surveyed=AiCaptain.SURVEY_SYSTEM_TARGET,
        )
        self.assertIsNone(captain._survey_action())
        self.assertTrue(captain.survey_done)

    def test_the_jump_budget_bounds_a_refused_course(self):
        captain = _captain(
            [{"id": "a", "scan_completed": True}],
            connections=["vega"],
            jumps=AiCaptain.SURVEY_JUMP_LIMIT,
        )
        self.assertIsNone(captain._survey_action())
        self.assertTrue(captain.survey_done)

    def test_the_target_matches_the_codex_milestone(self):
        self.assertEqual(
            AiCaptain.SURVEY_SYSTEM_TARGET,
            CODEX_MAP["sector_cartographer"].target,
        )


if __name__ == "__main__":
    unittest.main()
