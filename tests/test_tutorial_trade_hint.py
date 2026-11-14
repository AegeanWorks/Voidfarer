"""The trade milestone tells the player they need a station, so a player parked at a wilderness body is not stranded."""

from __future__ import annotations

import unittest

from voidfarer.story import INITIAL_TUTORIAL_STEPS


class TestTutorialTradeHint(unittest.TestCase):
    def _step(self, step_id: str):
        return next(step for step in INITIAL_TUTORIAL_STEPS if step.id == step_id)

    def test_the_trade_hint_says_a_station_is_required_and_names_the_start_station(self) -> None:
        hint = self._step("step_trade").hint
        self.assertIn("station", hint.lower())
        self.assertIn("Citadel", hint)

    def test_the_trade_hint_still_names_the_live_controls(self) -> None:
        hint = self._step("step_trade").hint
        self.assertIn("BUY", hint)
        self.assertIn("Commerce", hint)

    def test_the_other_milestone_hints_are_unchanged(self) -> None:
        self.assertIn("TRANSIT & ORBIT", self._step("step_orbit").hint)
        self.assertIn("SCAN", self._step("step_scan").hint)
        self.assertIn("ECONOMY", self._step("step_power").hint)


if __name__ == "__main__":
    unittest.main()
