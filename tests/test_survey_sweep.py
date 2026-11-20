"""The post-story captain finishes one full system survey (ADR-427)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _captain(bodies, orbiting="a", completed=True, done=False, scans=0):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.survey_done = done
    captain.survey_scans = scans
    captain.state = {
        "story_status": {"completed": completed},
        "current_system": {"id": "sol", "bodies": bodies},
        "orbiting_body": {"id": orbiting, "station_dockable": False},
        "ship": {"landed_body_id": ""},
    }
    return captain


class SurveySweepTest(unittest.TestCase):
    def test_an_unscanned_body_is_orbited_first(self):
        captain = _captain([
            {"id": "a", "scan_completed": True},
            {"id": "b", "scan_completed": False},
        ])
        self.assertEqual(captain._survey_action(),
                         ("/api/orbit", {"target": "b"}, "orbit"))

    def test_an_orbited_unscanned_body_is_scanned(self):
        captain = _captain([
            {"id": "a", "scan_completed": True},
            {"id": "b", "scan_completed": False},
        ], orbiting="b")
        self.assertEqual(captain._survey_action(), ("/api/scan", {}, "scan"))

    def test_a_fully_scanned_system_marks_the_survey_done(self):
        captain = _captain([{"id": "a", "scan_completed": True}])
        self.assertIsNone(captain._survey_action())
        self.assertTrue(captain.survey_done)

    def test_the_sweep_runs_once(self):
        captain = _captain([{"id": "b", "scan_completed": False}], done=True)
        self.assertIsNone(captain._survey_action())

    def test_the_sweep_is_capped(self):
        captain = _captain(
            [{"id": "b", "scan_completed": False}],
            scans=AiCaptain.SURVEY_SCAN_LIMIT,
        )
        self.assertIsNone(captain._survey_action())

    def test_nothing_surveys_before_the_campaign(self):
        captain = _captain([{"id": "b", "scan_completed": False}], completed=False)
        self.assertIsNone(captain._survey_action())

    def test_the_sweep_counts_each_step(self):
        captain = _captain([
            {"id": "a", "scan_completed": True},
            {"id": "b", "scan_completed": False},
        ], orbiting="b")
        self.assertEqual(captain._survey_action()[0], "/api/scan")
        self.assertEqual(captain.survey_scans, 1)


if __name__ == "__main__":
    unittest.main()
