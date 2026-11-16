"""navigate_to must not claim success when an encounter cuts the route short (ADR-359)."""

import unittest
from types import SimpleNamespace

from voidfarer.engine import SimulationEngine


class NavigateContractTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.targets = [
            system_id for system_id in self.engine.state.systems
            if self.engine.plan_route(system_id).get("reachable")
            and len(self.engine.plan_route(system_id)["path"]) > 2
        ]
        self.assertGreaterEqual(len(self.targets), 1)

    def _patch_jump(self, encounter_after_first=False):
        calls = []

        def jump(system_id):
            calls.append(system_id)
            if encounter_after_first and len(calls) == 1:
                self.engine.state = self.engine._clone_state(
                    active_anomaly=SimpleNamespace())
            return True, f"Jumped to {system_id}."

        self.engine.jump = jump
        return calls

    def test_a_completed_route_reports_success_and_reaches_the_target(self):
        target = self.targets[0]
        calls = self._patch_jump()
        ok, message = self.engine.navigate_to(target)
        self.assertTrue(ok, message)
        self.assertEqual(len(calls), len(self.engine.plan_route(target)["path"]) - 1)

    def test_an_interrupted_route_reports_failure(self):
        target = self.targets[0]
        self._patch_jump(encounter_after_first=True)
        ok, message = self.engine.navigate_to(target)
        self.assertFalse(ok, "a route cut short by an encounter is not a successful arrival")
        self.assertIn("interrupt", message.lower())

    def test_an_unreachable_target_still_reports_failure(self):
        ok, message = self.engine.navigate_to("not_a_real_system")
        self.assertFalse(ok)
        self.assertIn("No hyperlane route", message)


if __name__ == "__main__":
    unittest.main()
