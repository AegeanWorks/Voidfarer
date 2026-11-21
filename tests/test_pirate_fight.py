"""The captain fights pirates while the hull is healthy, up to the milestone (ADR-441)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _captain(hull=400, max_hull=400, completed=True, fought=0):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.state = {
        "story_status": {"completed": completed},
        "active_pirate": {"name": "Corsair", "demand": 120},
        "stats": {"pirates_fought": fought},
        "ship": {"hull": hull, "max_hull": max_hull, "credits": 50000},
    }
    return captain


class PirateFightPolicyTest(unittest.TestCase):
    def test_a_strong_post_story_ship_fights(self):
        self.assertEqual(
            _captain()._pirate_resolution(),
            ("/api/pirate/resolve", {"action": "fight"}, "pirate"),
        )

    def test_a_damaged_ship_still_evades(self):
        self.assertEqual(
            _captain(hull=100)._pirate_resolution(),
            ("/api/pirate/resolve", {"action": "evade"}, "pirate"),
        )

    def test_the_short_gate_always_evades(self):
        self.assertEqual(
            _captain(completed=False)._pirate_resolution()[1], {"action": "evade"}
        )

    def test_the_milestone_ends_the_fights(self):
        self.assertEqual(
            _captain(fought=AiCaptain.CORSAIR_TARGET)._pirate_resolution()[1],
            {"action": "evade"},
        )

    def test_the_threshold_is_half_the_hull(self):
        self.assertEqual(_captain(hull=200, max_hull=400)._pirate_resolution()[1],
                         {"action": "fight"})
        self.assertEqual(_captain(hull=199, max_hull=400)._pirate_resolution()[1],
                         {"action": "evade"})

    def test_no_pirate_resolves_nothing(self):
        captain = _captain()
        captain.state.pop("active_pirate")
        self.assertIsNone(captain._pirate_resolution())


if __name__ == "__main__":
    unittest.main()
