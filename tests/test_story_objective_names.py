"""Story objectives name systems the way the galaxy map does (ADR-277)."""

from __future__ import annotations

import unittest

from voidfarer.engine import SimulationEngine


class StoryObjectiveNamesTests(unittest.TestCase):
    def test_travel_objective_uses_display_names(self) -> None:
        engine = SimulationEngine(seed=42)
        ok, _ = engine.jump("alpha_centauri")
        self.assertTrue(ok)
        ok, text = engine.make_story_choice("choice_vance_telemetry")
        self.assertFalse(ok)
        self.assertNotIn("_", text)
        self.assertIn("currently in Alpha Centauri", text)
        self.assertIn("Travel to Sol System (", text)


if __name__ == "__main__":
    unittest.main()
