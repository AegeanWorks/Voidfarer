"""Cadet protection: secure systems stay calm while the academy is active."""

import unittest
from unittest import mock

from voidfarer.engine import SimulationEngine
from voidfarer.pirates import PirateRisk


def _jump(skip_academy: bool):
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = True
    if skip_academy:
        engine.skip_tutorial()
    engine.state = engine._clone_state(ship=engine._clone_ship(fuel=200))
    target = engine.current_system.connections[0]
    with mock.patch("voidfarer.engine.pirate_risk", return_value=PirateRisk(1.0, "test")):
        ok, msg = engine.jump(target)
    assert ok, msg
    return engine


class CadetProtectionTest(unittest.TestCase):
    def test_secure_system_raises_no_pirates_while_the_academy_runs(self):
        engine = _jump(skip_academy=False)
        self.assertIsNone(engine.state.active_pirate)

    def test_the_same_jump_meets_pirates_once_the_academy_is_skipped(self):
        engine = _jump(skip_academy=True)
        self.assertIsNotNone(engine.state.active_pirate)


if __name__ == "__main__":
    unittest.main()
