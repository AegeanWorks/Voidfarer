"""Strict positive-integer guards on the residual economy entry points (ADR-162 residual)."""

import unittest
from dataclasses import replace

from voidfarer.engine import SimulationEngine

BAD_QUANTITIES = (True, False, 0, -3, 1.5, "2", None)


class StrictQuantityResidualTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(cargo={"titanium": 5}, credits=500))

    def assert_refused(self, call, message_part="positive"):
        before = self.engine.state.to_dict()
        for bad in BAD_QUANTITIES:
            ok, message = call(bad)
            self.assertFalse(ok, f"{bad!r} was accepted")
            self.assertIn(message_part, message.lower())
            self.assertEqual(self.engine.state.to_dict(), before,
                             f"{bad!r} changed state on refusal")

    def test_deposit_rejects_bool_float_string_zero_and_negative(self):
        self.assert_refused(lambda q: self.engine.deposit_cargo("titanium", q))

    def test_withdraw_rejects_bool_float_string_zero_and_negative(self):
        self.assertTrue(self.engine.deposit_cargo("titanium", 3)[0])
        self.assert_refused(lambda q: self.engine.withdraw_cargo("titanium", q))

    def test_sell_from_depot_rejects_bool_float_string_zero_and_negative(self):
        self.assertTrue(self.engine.deposit_cargo("titanium", 3)[0])
        self.assert_refused(lambda q: self.engine.sell_from_depot("titanium", q))

    def test_quantum_order_rejects_bool_float_string_zero_and_negative(self):
        systems = list(self.engine.state.systems)
        destination = next((sid for sid in systems if sid != "sol"), systems[0])
        self.assert_refused(lambda q: self.engine.place_quantum_order("titanium", q, destination))

    def test_ai_trade_rejects_bool_float_string_zero_and_negative(self):
        captain = self.engine.state.ai_captains[0]
        self.engine.state = self.engine._clone_state(
            ai_captains=tuple(replace(c, cargo={"fuel_cells": 2}) if c.id == captain.id else c
                              for c in self.engine.state.ai_captains))
        self.assert_refused(
            lambda q: self.engine.interact_ai(captain.id, "buy", "fuel_cells", q))

    def test_positive_ints_still_work(self):
        self.assertTrue(self.engine.deposit_cargo("titanium", 2)[0])
        self.assertTrue(self.engine.withdraw_cargo("titanium", 1)[0])
        self.assertTrue(self.engine.deposit_cargo("titanium", 1)[0])
        self.assertTrue(self.engine.sell_from_depot("titanium", 1)[0])


if __name__ == "__main__":
    unittest.main()
