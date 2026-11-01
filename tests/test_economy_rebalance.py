"""Unit tests for economic volatility events, faction trade margins, and drydock wear overhaul."""

from __future__ import annotations

import unittest

from voidfarer.economy import (
    EVENT_TEMPLATES,
    calculate_dynamic_market_quote,
)
from voidfarer.engine import SimulationEngine
from voidfarer.galaxy import COMMODITY_MAP
from voidfarer.models import EconomicEvent, GlobalEconomyState


class TestEconomyRebalance(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_new_dynamic_event_templates_registered(self):
        prefix_ids = {t["id_prefix"] for t in EVENT_TEMPLATES}
        self.assertIn("famine_embargo", prefix_ids)
        self.assertIn("tech_surplus", prefix_ids)
        self.assertIn("energy_deregulation", prefix_ids)
        self.assertIn("defense_mobilization", prefix_ids)

    def test_spread_widens_in_crisis_and_narrows_in_boom(self):
        cur_sys = self.engine.current_system
        body = next(b for b in cur_sys.bodies if b.station_dockable)
        comm = COMMODITY_MAP["hydroponics"]

        # Baseline quote with no active events
        empty_econ = GlobalEconomyState(markets=self.engine.state.economy.markets, active_events=())
        q_baseline = calculate_dynamic_market_quote(cur_sys, body, comm, empty_econ)
        spread_baseline = q_baseline.buy_price - q_baseline.sell_price

        # Crisis event (shortage/panic)
        crisis_evt = EconomicEvent(
            id="e_crisis", title="Famine", description="Blight",
            system_id=cur_sys.id, commodity_id=comm.id, price_multiplier=1.8,
            duration_ticks=20, category="crisis",
        )
        crisis_econ = GlobalEconomyState(markets=self.engine.state.economy.markets, active_events=(crisis_evt,))
        q_crisis = calculate_dynamic_market_quote(cur_sys, body, comm, crisis_econ)
        # In crisis, price is higher AND spread ratio is wider
        self.assertGreater(q_crisis.buy_price, q_baseline.buy_price)

        # Boom event (high liquidity)
        boom_evt = EconomicEvent(
            id="e_boom", title="Surplus", description="Bountiful",
            system_id=cur_sys.id, commodity_id=comm.id, price_multiplier=0.6,
            duration_ticks=20, category="boom",
        )
        boom_econ = GlobalEconomyState(markets=self.engine.state.economy.markets, active_events=(boom_evt,))
        q_boom = calculate_dynamic_market_quote(cur_sys, body, comm, boom_econ)
        self.assertLess(q_boom.buy_price, q_baseline.buy_price)

        # Spread ratios, not just prices: crisis panics widen the bid/ask gap and
        # booms narrow it.
        def spread_ratio(quote):
            return (quote.buy_price - quote.sell_price) / max(1, quote.buy_price)

        baseline_ratio = spread_ratio(q_baseline)
        self.assertGreater(spread_baseline, 0)
        self.assertGreater(spread_ratio(q_crisis), baseline_ratio)
        self.assertLess(spread_ratio(q_boom), baseline_ratio)

    def test_allied_faction_margin_bonus(self):
        cur_sys = self.engine.current_system
        body = next(b for b in cur_sys.bodies if b.station_dockable)
        comm = COMMODITY_MAP["titanium"]
        empty_econ = GlobalEconomyState(markets=self.engine.state.economy.markets, active_events=())

        # Neutral quote (standing = 0)
        q_neutral = calculate_dynamic_market_quote(cur_sys, body, comm, empty_econ, faction_standing=0)
        # Allied quote (standing = 80)
        q_allied = calculate_dynamic_market_quote(cur_sys, body, comm, empty_econ, faction_standing=80)

        # Allied gets cheaper buy price and better sell price relative to neutral base
        self.assertLess(q_allied.buy_price, q_neutral.buy_price)
        # No same-station arbitrage even for allies
        self.assertGreater(q_allied.buy_price, q_allied.sell_price)

    def test_overhaul_ship_drydock_wear(self):
        # Must fail if wear is 0.0
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(wear=0.0, credits=5000)
        )
        ok, msg = self.engine.overhaul_ship()
        self.assertFalse(ok)
        self.assertIn("0% hyperlane wear", msg)

        # Set wear and dock at station
        body_id = None
        for b in self.engine.current_system.bodies:
            if getattr(b, "station_dockable", False):
                body_id = b.id
                break
        self.assertIsNotNone(body_id)
        self.engine.orbit(body_id)

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(wear=35.0, credits=5000)
        )
        ok_overhaul, msg_overhaul = self.engine.overhaul_ship()
        self.assertTrue(ok_overhaul)
        self.assertEqual(self.engine.state.ship.wear, 0.0)
        self.assertLess(self.engine.state.ship.credits, 5000)
        self.assertIn("Structural overhaul completed", msg_overhaul)


if __name__ == "__main__":
    unittest.main()
