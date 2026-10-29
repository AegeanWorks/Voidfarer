"""Docked trade automation: configure thresholds, buy low, sell high, persist."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import GameState, TradeAutomation


class TradeAutomationTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.allow_decision_events = False
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=5000, cargo={}, cargo_cost={}),
        )

    def test_configuration_requires_a_dock_and_valid_thresholds(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id=None)
        )
        ok, message = self.engine.set_trade_automation("titanium", 20, 30, 1)
        self.assertFalse(ok)
        self.assertIn("dock", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id="sol_body_1")
        )
        ok, message = self.engine.set_trade_automation("titanium", 0, 0, 1)
        self.assertFalse(ok)
        self.assertIn("threshold", message.lower())
        ok, message = self.engine.set_trade_automation("titanium", 30, 20, 1)
        self.assertFalse(ok)
        self.assertIn("below", message.lower())

    def test_buy_low_executes_on_tick_and_respects_cooldown(self):
        ok, message = self.engine.set_trade_automation("titanium", 9999, 0, 1)
        self.assertTrue(ok, message)
        before_credits = self.engine.state.ship.credits
        self.engine.tick(1)
        self.assertEqual(self.engine.state.ship.cargo.get("titanium"), 1)
        self.assertLess(self.engine.state.ship.credits, before_credits)
        self.assertEqual(self.engine.state.trade_automation.trades, 1)
        tick_after_buy = self.engine.state.time.tick
        self.engine.tick(1)
        self.assertEqual(self.engine.state.ship.cargo.get("titanium"), 1,
                         "the broker must wait for its cooldown")
        self.assertEqual(self.engine.state.time.tick, tick_after_buy + 1)

    def test_sell_high_executes_and_records_realized_credits(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=1000,
                cargo={"titanium": 2},
                cargo_cost={"titanium": 200},
            ),
        )
        ok, message = self.engine.set_trade_automation("titanium", 0, 1, 1)
        self.assertTrue(ok, message)
        self.engine.tick(1)
        self.assertEqual(self.engine.state.ship.cargo.get("titanium"), 1)
        self.assertGreater(self.engine.state.ship.credits, 1000)
        self.assertEqual(self.engine.state.trade_automation.trades, 1)
        self.assertGreater(self.engine.state.trade_automation.realized_credits, 0)

    def test_disabled_automation_does_not_trade(self):
        ok, message = self.engine.set_trade_automation(enabled=False)
        self.assertTrue(ok, message)
        self.engine.tick(1)
        self.assertNotIn("titanium", self.engine.state.ship.cargo)


class TradeAutomationPersistenceTest(unittest.TestCase):
    def test_round_trip_preserves_the_policy(self):
        state = SimulationEngine(seed=42).state
        state = replace(
            state,
            trade_automation=TradeAutomation(
                enabled=True,
                commodity_id="titanium",
                buy_below=40,
                sell_above=70,
                quantity=3,
                trades=2,
                realized_credits=500,
            ),
        )
        restored = GameState.from_dict(state.to_dict())
        self.assertTrue(restored.trade_automation.enabled)
        self.assertEqual(restored.trade_automation.commodity_id, "titanium")
        self.assertEqual(restored.trade_automation.buy_below, 40)
        self.assertEqual(restored.trade_automation.sell_above, 70)
        self.assertEqual(restored.trade_automation.quantity, 3)
        self.assertEqual(restored.trade_automation.trades, 2)
        self.assertEqual(restored.trade_automation.realized_credits, 500)

    def test_legacy_payload_defaults_to_off(self):
        state = SimulationEngine(seed=42).state
        payload = state.to_dict()
        payload.pop("trade_automation", None)
        restored = GameState.from_dict(payload)
        self.assertFalse(restored.trade_automation.enabled)
        self.assertEqual(restored.trade_automation.quantity, 1)


if __name__ == "__main__":
    unittest.main()
