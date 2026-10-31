"""Unit tests for the dynamic galactic economy, stockpiles, events, and trade routes."""

import random
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.economy import (
    calculate_dynamic_market_quote,
    get_galactic_trade_routes,
    tick_global_economy,
)
from voidfarer.factions import get_faction_id_from_name
from voidfarer.galaxy import COMMODITY_MAP


class TestInitialEconomy(unittest.TestCase):
    """Verify baseline economy generation across the galaxy."""

    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_every_system_has_a_market(self):
        econ = self.engine.state.economy
        self.assertEqual(set(econ.markets.keys()), set(self.engine.state.systems.keys()))

    def test_stockpiles_are_positive(self):
        for market in self.engine.state.economy.markets.values():
            for stock in market.stockpiles.values():
                self.assertGreaterEqual(stock, 10)

    def test_initial_event_is_seeded(self):
        ids = {evt.id for evt in self.engine.state.economy.active_events}
        self.assertIn("evt_medical_crisis_alpha_centauri", ids)


class TestTickGlobalEconomy(unittest.TestCase):
    """Verify production, consumption, event decay, and last-updated tracking."""

    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.econ = self.engine.state.economy
        self.systems = self.engine.state.systems

    def test_production_and_consumption_rates_apply(self):
        before = dict(self.econ.markets["sol"].stockpiles)
        after_econ, _ = tick_global_economy(self.econ, 8, self.systems, random.Random(1))
        after = after_econ.markets["sol"].stockpiles

        # Production is applied first, then consumption, sequentially per market.
        market = self.econ.markets["sol"]
        expected = dict(before)
        for comm_id, rate in market.production_rates.items():
            growth = int((rate * 8) / 4)
            expected[comm_id] = min(300, expected.get(comm_id, 50) + growth)
        for comm_id, rate in market.consumption_rates.items():
            shrink = int((rate * 8) / 4)
            expected[comm_id] = max(5, expected.get(comm_id, 50) - shrink)
        self.assertEqual(after, expected)

    def test_last_updated_tick_advances(self):
        self.assertEqual(self.econ.last_updated_tick, 0)
        updated, _ = tick_global_economy(self.econ, 5, self.systems, random.Random(1))
        self.assertEqual(updated.last_updated_tick, 5)

    def test_events_decay_and_expire(self):
        decayed, _ = tick_global_economy(self.econ, 10, self.systems, random.Random(7))
        event = next((e for e in decayed.active_events if e.id == "evt_medical_crisis_alpha_centauri"), None)
        self.assertIsNotNone(event)
        self.assertEqual(event.duration_ticks, 40)

        expired, logs = tick_global_economy(decayed, 999, self.systems, random.Random(7))
        self.assertFalse(any(e.id == "evt_medical_crisis_alpha_centauri" for e in expired.active_events))
        self.assertTrue(any("MARKET STABILIZED" in line for line in logs))


class TestDynamicMarketQuotes(unittest.TestCase):
    """Verify localized quote computation and profitable route discovery."""

    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_quote_has_positive_spread(self):
        system = self.engine.current_system
        body = next(b for b in system.bodies if b.station_dockable)
        quote = calculate_dynamic_market_quote(system, body, COMMODITY_MAP["titanium"], self.engine.state.economy)
        self.assertGreater(quote.buy_price, quote.sell_price)
        self.assertGreaterEqual(quote.sell_price, 1)

    def test_events_shift_local_prices(self):
        system = self.engine.state.systems["alpha_centauri"]
        body = next(b for b in system.bodies if b.station_dockable)
        quote = calculate_dynamic_market_quote(system, body, COMMODITY_MAP["medicines"], self.engine.state.economy)
        base_price = COMMODITY_MAP["medicines"].base_price
        self.assertGreater(quote.buy_price, base_price)

    def test_trade_routes_are_sorted_and_cross_system(self):
        routes = get_galactic_trade_routes(self.engine.state.systems, self.engine.state.economy)
        self.assertTrue(routes)
        for route in routes:
            self.assertNotEqual(route["buy_system_id"], route["sell_system_id"])
            self.assertGreater(route["profit_per_unit"], 0)
        profits = [route["profit_per_unit"] for route in routes]
        self.assertEqual(profits, sorted(profits, reverse=True))

    def test_faction_standing_influences_quote(self):
        system = self.engine.current_system
        body = next(b for b in system.bodies if b.station_dockable)
        comm = COMMODITY_MAP["titanium"]
        friendly_quote = calculate_dynamic_market_quote(
            system, body, comm, self.engine.state.economy, faction_standing=60
        )
        hostile_quote = calculate_dynamic_market_quote(
            system, body, comm, self.engine.state.economy, faction_standing=-60
        )
        self.assertLess(friendly_quote.buy_price, hostile_quote.buy_price)

    def test_same_station_trade_cannot_arbitrage(self):
        # Set up a ship with heavy trade bonuses
        self.engine.buy_ship_chassis("orion_hauler")
        credits_before = self.engine.state.ship.credits
        ok, _ = self.engine.trade("titanium", 2, is_buy=True)
        self.assertTrue(ok)
        ok, _ = self.engine.trade("titanium", 2, is_buy=False)
        self.assertTrue(ok)
        # Immediate round-trip sale at the same station must not generate a net profit
        self.assertLess(self.engine.state.ship.credits, credits_before)

    def test_same_station_reorbit_keeps_the_arbitrage_guard(self):
        station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(station.id)
        ok, _ = self.engine.trade("titanium", 2, is_buy=True)
        self.assertTrue(ok)
        tag = (self.engine.current_system.id, station.id, "titanium")
        self.assertIn(tag, self.engine._local_dock_purchases)
        guard_before = dict(self.engine._local_dock_purchases)
        self.engine.orbit(station.id)
        self.assertEqual(self.engine._local_dock_purchases, guard_before)

    def test_new_game_clears_and_load_preserves_the_arbitrage_guard(self):
        station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(station.id)
        self.engine.trade("titanium", 1, is_buy=True)
        self.assertTrue(self.engine._local_dock_purchases)
        persisted = dict(self.engine.state.local_dock_purchases)
        self.assertEqual(persisted, self.engine._local_dock_purchases)

        self.engine.load_state(self.engine.state)
        self.assertEqual(self.engine._local_dock_purchases, persisted)

        self.engine.reset(seed=7)
        self.assertEqual(self.engine._local_dock_purchases, {})

    def test_load_does_not_reopen_same_station_arbitrage(self):
        from dataclasses import replace

        self.engine.skip_tutorial()
        station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(station.id)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=100000, cargo={})
        )
        ok, msg = self.engine.buy_ship_chassis("orion_hauler")
        self.assertTrue(ok, msg)
        self.engine.state = self.engine._clone_state(
            character=replace(
                self.engine.state.character,
                skills={**self.engine.state.character.skills, "trade": 10},
            )
        )
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.trade("titanium", 10, is_buy=True)
        self.assertTrue(ok, msg)
        self.engine.load_state(self.engine.state)
        ok, msg = self.engine.trade("titanium", 10, is_buy=False)
        self.assertTrue(ok, msg)
        self.assertLess(self.engine.state.ship.credits, credits_before)

    def test_friendly_standing_is_applied_once_on_purchase(self):
        station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(station.id)
        self.engine.skip_tutorial()
        faction_id = get_faction_id_from_name(self.engine.current_system.faction)
        standings = dict(self.engine.state.ship.faction_standings)
        standings[faction_id] = 60
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=100000, cargo={}, faction_standings=standings)
        )
        quote = calculate_dynamic_market_quote(
            self.engine.current_system,
            station,
            COMMODITY_MAP["titanium"],
            self.engine.state.economy,
            faction_standing=60,
        )
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.trade("titanium", 1, is_buy=True)
        self.assertTrue(ok, msg)
        self.assertEqual(credits_before - self.engine.state.ship.credits, quote.buy_price)

    def test_friendly_standing_cannot_arbitrage_locally(self):
        self.engine.buy_ship_chassis("orion_hauler")
        self.engine.skip_tutorial()
        station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(station.id)
        faction_id = get_faction_id_from_name(self.engine.current_system.faction)
        standings = dict(self.engine.state.ship.faction_standings)
        standings[faction_id] = 60
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=100000, cargo={}, faction_standings=standings)
        )
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.trade("titanium", 10, is_buy=True)
        self.assertTrue(ok, msg)
        ok, msg = self.engine.trade("titanium", 10, is_buy=False)
        self.assertTrue(ok, msg)
        self.assertLess(self.engine.state.ship.credits, credits_before)

    def test_sell_from_depot_uses_dynamic_quote_and_updates_stockpiles(self):
        # Deposit commodity into Sol depot
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(cargo={"titanium": 5})
        )
        ok, msg = self.engine.deposit_cargo("titanium", 3)
        self.assertTrue(ok, msg)
        before_stock = self.engine.state.economy.markets["sol"].stockpiles.get("titanium", 0)
        ok, msg = self.engine.sell_from_depot("titanium", 2)
        self.assertTrue(ok, msg)
        after_stock = self.engine.state.economy.markets["sol"].stockpiles.get("titanium", 0)
        self.assertEqual(after_stock, before_stock + 2)


if __name__ == "__main__":
    unittest.main()
