"""A survey sweep revisits unfinished neighbours instead of quitting (ADR-456)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _system(system_id, bodies=(), connections=()):
    return {
        "id": system_id, "name": system_id, "connections": list(connections),
        "bodies": [
            {"id": body_id, "scan_completed": scanned}
            for body_id, scanned in bodies
        ],
    }


def _captain(current, galaxy, tried=(), jumps=0, revisits=0, surveyed=1):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.survey_done = False
    captain.survey_scans = 0
    captain.survey_jumps = jumps
    captain.survey_revisits = revisits
    captain.survey_systems_tried = set(tried)
    captain.galaxy_cache = galaxy
    captain.state = {
        "story_status": {"completed": True},
        "stats": {"systems_surveyed": surveyed},
        "current_system": current,
    }
    return captain


class SurveyRevisitTest(unittest.TestCase):
    def _captains(self, **kwargs):
        galaxy = {
            "sol": _system("sol", connections=["a", "b"]),
            "a": _system("a", [("a1", True)]),
            "b": _system("b", [("b1", False), ("b2", False), ("b3", False)]),
        }
        current = galaxy["sol"]
        return _captain(current, galaxy, **kwargs)

    def test_a_fresh_lane_is_still_preferred(self):
        self.assertEqual(
            self._captains(tried=["sol"])._survey_action(),
            ("/api/navigate", {"system_id": "a"}, "navigate"),
        )

    def test_an_exhausted_lane_revisits_the_most_unscanned_neighbour(self):
        self.assertEqual(
            self._captains(tried=["sol", "a", "b"])._survey_action(),
            ("/api/navigate", {"system_id": "b"}, "navigate"),
        )

    def test_a_revisit_increments_the_bounded_counter(self):
        captain = self._captains(tried=["sol", "a", "b"])
        captain._survey_action()
        self.assertEqual(captain.survey_revisits, 1)

    def test_the_revisit_budget_stops_the_sweep(self):
        captain = self._captains(
            tried=["sol", "a", "b"], revisits=AiCaptain.SURVEY_REVISIT_LIMIT,
        )
        self.assertIsNone(captain._survey_action())
        self.assertTrue(captain.survey_done)

    def test_a_fully_scanned_neighbour_is_not_revisited(self):
        galaxy = {
            "sol": _system("sol", connections=["a"]),
            "a": _system("a", [("a1", True)]),
        }
        captain = _captain(galaxy["sol"], galaxy, tried=["sol", "a"])
        self.assertIsNone(captain._survey_action())

    def test_the_jump_budget_still_bounds_the_sweep(self):
        captain = self._captains(
            tried=["sol", "a", "b"], jumps=AiCaptain.SURVEY_JUMP_LIMIT,
        )
        self.assertIsNone(captain._survey_action())

    def test_the_survey_target_still_stops_the_sweep(self):
        self.assertIsNone(self._captains(surveyed=3)._survey_action())

    def test_a_landed_ship_does_not_burn_the_scan_budget(self):
        captain = self._captains()
        captain.state["ship"] = {"landed_body_id": "sol_body_1"}
        self.assertIsNone(captain._survey_action(), "orbit is refused while landed")
        self.assertEqual(captain.survey_scans, 0)

    def test_a_ship_in_transit_does_not_burn_the_scan_budget(self):
        captain = self._captains()
        captain.state["ship"] = {"travel": {"arrival_tick": 9}}
        self.assertIsNone(captain._survey_action(), "scan is refused in transit")
        self.assertEqual(captain.survey_scans, 0)

    def test_a_stale_revisit_is_replaced_by_fresh_scan_state(self):
        class FreshClient:
            def get(self, path):
                return 200, {"systems": {
                    "sol": _system("sol", connections=["a", "b"]),
                    "a": _system("a", [("a1", False), ("a2", False)]),
                    "b": _system("b", [("b1", True)]),
                }}

        captain = self._captains(tried=["sol", "a", "b"])
        captain.client = FreshClient()
        self.assertEqual(
            captain._survey_action(),
            ("/api/navigate", {"system_id": "a"}, "navigate"),
            "the revisit must target a body still pending in the refreshed catalogue",
        )


if __name__ == "__main__":
    unittest.main()
