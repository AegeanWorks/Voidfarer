"""The post-story captain keeps rebuilding devastated worlds (ADR-437)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(
    bodies=None,
    orbiting="devastated",
    credits=5000,
    cargo=None,
    rebuilt=1,
    relief=0,
    succeeded=("/api/reconstruct",),
    completed=True,
    attempts=0,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.succeeded.update(succeeded)
    captain.rebuild_attempts = attempts
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"worlds_rebuilt": rebuilt, "relief_deliveries": relief},
        "current_system": {
            "id": "sol",
            "bodies": bodies if bodies is not None else [
                {"id": "devastated", "population": 500000, "devastation": 60.0},
                {"id": "other", "population": 900000, "devastation": 30.0},
            ],
        },
        "orbiting_body": {"id": orbiting, "station_dockable": False},
        "ship": {
            "credits": credits,
            "cargo": cargo or {},
            "landed_body_id": "",
            "cargo_free_volume": 20,
        },
    }
    return captain


class RebuildSweepTest(unittest.TestCase):
    def test_the_worst_world_is_rebuilt_with_credits(self):
        captain = _captain()
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/reconstruct", {"body_id": "devastated", "mode": "credits"},
             "reconstruct"),
        )
        self.assertEqual(captain.rebuild_attempts, 1)

    def test_a_stocked_hold_still_prefers_relief(self):
        captain = _captain(
            cargo={"medicines": 2, "hydroponics": 2, "fuel_cells": 1})
        self.assertEqual(
            captain._rebuild_sweep_action()[1]["mode"], "relief"
        )

    def test_a_distant_world_is_orbited_first(self):
        captain = _captain(orbiting="elsewhere")
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/orbit", {"target": "devastated"}, "orbit"),
        )
        self.assertEqual(captain.rebuild_attempts, 0)

    def test_the_target_counts_both_modes(self):
        captain = _captain(rebuilt=3, relief=2)
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_nothing_runs_before_the_campaign(self):
        captain = _captain(completed=False)
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_nothing_continues_before_the_first_rebuild_succeeded(self):
        captain = _captain(succeeded=())
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_the_attempt_bound_stops_a_refused_route(self):
        captain = _captain(attempts=AiCaptain.REBUILD_ATTEMPT_LIMIT)
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_a_broke_captain_without_supplies_stays_quiet(self):
        captain = _captain(credits=100)
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_an_intact_system_has_no_target(self):
        captain = _captain(bodies=[
            {"id": "a", "population": 10, "devastation": 0.0},
            {"id": "b", "population": 0, "devastation": 40.0},
        ])
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_the_target_mirrors_the_codex_milestone(self):
        self.assertEqual(
            AiCaptain.REBUILD_TARGET, CODEX_MAP["rebuilder"].target
        )


if __name__ == "__main__":
    unittest.main()
