"""Quantum auto-freight: policy, route selection, cooldown and persistence."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import GameState, QuantumAutomation


class QuantumAutomationTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=5000,
                cargo={"titanium": 10},
                cargo_cost={"titanium": 100},
                orbiting_body_id="sol_body_1",
            )
        )

    def test_policy_requires_a_dock_and_valid_minimum(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id=None)
        )
        ok, message = self.engine.set_quantum_automation(True, 100)
        self.assertFalse(ok)
        self.assertIn("dock", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id="sol_body_1")
        )
        ok, message = self.engine.set_quantum_automation(True, 100)
        self.assertTrue(ok, message)
        self.assertTrue(self.engine.state.quantum_automation.enabled)
        self.assertEqual(self.engine.state.quantum_automation.min_net, 100)
        ok, message = self.engine.set_quantum_automation(False)
        self.assertTrue(ok, message)
        self.assertFalse(self.engine.state.quantum_automation.enabled)

    def test_auto_freight_places_the_best_route(self):
        ok, message = self.engine.set_quantum_automation(True, 0)
        self.assertTrue(ok, message)
        self.engine._run_quantum_automation()
        auto = self.engine.state.quantum_automation
        self.assertEqual(auto.orders, 1)
        self.assertTrue(auto.last_commodity)
        self.assertTrue(auto.last_destination)
        self.assertEqual(len(self.engine.state.ship.trade_orders), 1)
        self.assertIn("QUANTUM AUTO-FREIGHT", self.engine.state.ship.flight_log[-1])

    def test_cooldown_and_minimum_block_orders(self):
        self.engine.set_quantum_automation(True, 0)
        self.engine._run_quantum_automation()
        self.assertEqual(self.engine.state.quantum_automation.orders, 1)
        self.engine._run_quantum_automation()
        self.assertEqual(self.engine.state.quantum_automation.orders, 1)

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=5000,
                cargo={"titanium": 10},
                orbiting_body_id="sol_body_1",
            ),
            quantum_automation=QuantumAutomation(enabled=True, min_net=999999),
        )
        self.engine._run_quantum_automation()
        self.assertEqual(self.engine.state.quantum_automation.orders, 0)

    def test_policy_round_trips(self):
        policy = QuantumAutomation(
            enabled=True,
            min_net=250,
            orders=3,
            last_net=400,
            last_commodity="titanium",
            last_destination="vega",
        )
        self.engine.state = self.engine._clone_state(quantum_automation=policy)
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertTrue(restored.quantum_automation.enabled)
        self.assertEqual(restored.quantum_automation.min_net, 250)
        self.assertEqual(restored.quantum_automation.orders, 3)
        self.assertEqual(restored.quantum_automation.last_destination, "vega")

    def test_legacy_payload_defaults_to_off(self):
        payload = self.engine.state.to_dict()
        payload.pop("quantum_automation", None)
        restored = GameState.from_dict(payload)
        self.assertFalse(restored.quantum_automation.enabled)
        self.assertEqual(restored.quantum_automation.min_net, 100)


if __name__ == "__main__":
    unittest.main()
