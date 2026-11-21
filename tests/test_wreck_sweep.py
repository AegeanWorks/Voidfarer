"""The post-story captain boards every derelict it can find (ADR-439)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(
    bodies=None,
    orbiting="",
    site=None,
    salvage=1,
    completed=True,
    probes=0,
    probed=(),
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.wreck_probes = probes
    captain.salvage_probed.update(probed)
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"salvage": salvage},
        "current_system": {
            "id": "sol",
            "bodies": bodies if bodies is not None else [
                {"id": "hulk", "body_type": "desert_world"},
                {"id": "rock", "body_type": "asteroid"},
                {"id": "station", "body_type": "orbital_station",
                 "station_dockable": True},
            ],
        },
        "orbiting_body": {"id": orbiting} if orbiting else None,
        "salvage_site": site,
    }
    return captain


class WreckSweepTest(unittest.TestCase):
    def test_a_detected_hulk_is_claimed_cautiously(self):
        captain = _captain(orbiting="hulk", site={"name": "Freighter"})
        self.assertEqual(
            captain._wreck_sweep_action(),
            ("/api/salvage", {"strategy": "cautious"}, "salvage"),
        )

    def test_the_next_body_is_probed_when_no_hulk_is_detected(self):
        captain = _captain()
        self.assertEqual(
            captain._wreck_sweep_action(),
            ("/api/orbit", {"target": "hulk"}, "orbit"),
        )
        self.assertIn("hulk", captain.salvage_probed)

    def test_an_already_probed_or_claimed_body_is_skipped(self):
        captain = _captain(probed=("hulk",))
        self.assertEqual(
            captain._wreck_sweep_action()[1]["target"], "rock"
        )

    def test_the_target_stops_the_sweep(self):
        captain = _captain(salvage=AiCaptain.WRECK_TARGET)
        self.assertIsNone(captain._wreck_sweep_action())

    def test_nothing_runs_before_the_campaign(self):
        captain = _captain(completed=False)
        self.assertIsNone(captain._wreck_sweep_action())

    def test_the_probe_budget_bounds_the_sweep(self):
        captain = _captain(probes=AiCaptain.WRECK_PROBE_LIMIT)
        self.assertIsNone(captain._wreck_sweep_action())

    def test_a_probe_spends_one_budget_step(self):
        captain = _captain()
        captain._wreck_sweep_action()
        self.assertEqual(captain.wreck_probes, 1)

    def test_an_exhausted_system_stays_quiet_for_the_next_one(self):
        captain = _captain(bodies=[
            {"id": "hulk", "body_type": "desert_world"},
        ], probed=("hulk",))
        self.assertIsNone(captain._wreck_sweep_action())
        self.assertLess(captain.wreck_probes, AiCaptain.WRECK_PROBE_LIMIT)

    def test_the_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.WRECK_TARGET, CODEX_MAP["wreck_diver"].target
        )


if __name__ == "__main__":
    unittest.main()
