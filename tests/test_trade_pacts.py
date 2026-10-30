"""Faction trade pacts: standing gate, war suspension and market benefit."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.economy import calculate_dynamic_market_quote
from voidfarer.galaxy import COMMODITY_MAP
from voidfarer.models import GameState, WarState


class TradePactTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.faction_id = "sol_coalition"

    def _set_standing(self, standing):
        standings = dict(self.engine.state.ship.faction_standings)
        standings[self.faction_id] = standing
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(faction_standings=standings)
        )

    def test_pact_requires_standing_and_forms_once(self):
        ok, message = self.engine.faction_diplomacy(self.faction_id, "trade_pact")
        self.assertFalse(ok)
        self.assertIn("standing", message.lower())

        self._set_standing(45)
        ok, message = self.engine.faction_diplomacy(self.faction_id, "trade_pact")
        self.assertTrue(ok, message)
        self.assertIn(self.faction_id, self.engine.state.ship.trade_pacts)
        self.assertIn("TRADE PACT", message)
        ok, message = self.engine.faction_diplomacy(self.faction_id, "trade_pact")
        self.assertFalse(ok)
        self.assertIn("already", message.lower())

    def test_pact_is_refused_during_war_and_suspended_if_signed(self):
        self._set_standing(50)
        war = WarState(
            id="pact_war",
            attacker_id="sol_coalition",
            defender_id=self.faction_id,
            started_tick=0,
        )
        self.engine.state = self.engine._clone_state(wars=(war,))
        ok, message = self.engine.faction_diplomacy(self.faction_id, "trade_pact")
        self.assertFalse(ok)
        self.assertIn("war", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(trade_pacts=(self.faction_id,))
        )
        self.assertFalse(self.engine.trade_pact_active(self.faction_id))

    def test_pact_improves_both_sides_of_the_quote(self):
        system = self.engine.current_system
        body = self.engine.docked_body
        self.assertIsNotNone(body)
        commodity = COMMODITY_MAP["titanium"]
        normal = calculate_dynamic_market_quote(
            system, body, commodity, self.engine.state.economy, faction_standing=50
        )
        pacted = calculate_dynamic_market_quote(
            system,
            body,
            commodity,
            self.engine.state.economy,
            faction_standing=50,
            trade_pact=True,
        )
        self.assertLess(pacted.buy_price, normal.buy_price)
        self.assertGreater(pacted.sell_price, normal.sell_price)

    def test_trade_uses_the_pact_and_reports_it(self):
        self._set_standing(50)
        ok, message = self.engine.faction_diplomacy(self.faction_id, "trade_pact")
        self.assertTrue(ok, message)
        before = self.engine.state.ship.credits
        ok, message = self.engine.trade("titanium", 1, True)
        self.assertTrue(ok, message)
        self.assertIn("trade pact", message.lower())
        self.assertLess(self.engine.state.ship.credits, before)

    def test_snapshot_and_save_round_trip_keep_pacts(self):
        self._set_standing(50)
        ok, _ = self.engine.faction_diplomacy(self.faction_id, "trade_pact")
        self.assertTrue(ok)
        snapshot = self.engine.get_status_snapshot()
        self.assertIn(self.faction_id, snapshot["ship"]["trade_pacts"])
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.ship.trade_pacts, (self.faction_id,))


class TradePactLegacyTest(unittest.TestCase):
    def test_legacy_payload_defaults_to_no_pacts(self):
        state = SimulationEngine(seed=42).state
        payload = state.to_dict()
        payload.pop("trade_pacts", None)
        restored = GameState.from_dict(payload)
        self.assertEqual(restored.ship.trade_pacts, ())


if __name__ == "__main__":
    unittest.main()
