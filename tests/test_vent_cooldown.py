"""The vent policy must honour the coolant recharge it can read (ADR-425)."""

from __future__ import annotations

import unittest
from dataclasses import replace

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.engine import SimulationEngine


def _captain(heat: float, last_vent: int, tick: int) -> AiCaptain:
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.state = {
        "story_status": {"completed": True},
        "reactor": {"heat": heat, "last_vent_tick": last_vent},
        "time": {"tick": tick},
    }
    return captain


class VentCooldownTest(unittest.TestCase):
    def test_the_snapshot_exposes_the_vent_tick(self):
        report = SimulationEngine(seed=1).get_status_snapshot()["reactor"]
        self.assertIn("last_vent_tick", report)
        self.assertIn("can_vent", report)

    def test_a_hot_core_with_a_fresh_vent_is_not_posted(self):
        self.assertIsNone(_captain(heat=60.0, last_vent=100, tick=104)._reactor_vent_action())

    def test_a_hot_core_with_a_recharged_loop_is_posted(self):
        self.assertEqual(
            _captain(heat=60.0, last_vent=100, tick=105)._reactor_vent_action()[0],
            "/api/reactor/vent",
        )

    def test_a_core_never_vented_is_posted_once(self):
        self.assertEqual(_captain(heat=60.0, last_vent=-999, tick=10)._reactor_vent_action()[0],
                         "/api/reactor/vent")

    def test_the_engine_reports_the_cooldown_after_a_real_vent(self):
        engine = SimulationEngine(seed=1)
        engine.state = engine._clone_state(
            ship=replace(
                engine.state.ship,
                reactor=replace(engine.state.ship.reactor, heat=60.0),
            )
        )
        ok, message = engine.vent_reactor_coolant()
        self.assertTrue(ok, message)
        report = engine.get_status_snapshot()["reactor"]
        self.assertFalse(report["can_vent"])
        self.assertGreaterEqual(report["last_vent_tick"], 0)


if __name__ == "__main__":
    unittest.main()
