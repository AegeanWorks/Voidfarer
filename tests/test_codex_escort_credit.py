"""Escort achievements credit the commission, not the current roster (ADR-424)."""

from __future__ import annotations

import unittest
from dataclasses import replace

from voidfarer.codex import build_codex_report, metric_value
from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=200000))
    return engine


def _member_id(engine: SimulationEngine) -> str:
    return next(member.id for member in engine.state.ship.crew if member.status == "active")


def _dock(engine: SimulationEngine) -> None:
    body = next(body for body in engine.current_system.bodies if body.station_dockable)
    engine.orbit(body.id)


class EscortLifetimeCreditTest(unittest.TestCase):
    def test_commissioning_an_escort_credits_the_achievement(self):
        engine = _engine()
        _dock(engine)
        ok, message = engine.buy_escort("corvette")
        self.assertTrue(ok, message)
        self.assertEqual(metric_value(engine.state, "escorts"), 1)
        by_id = {entry["id"]: entry for entry in build_codex_report(engine.state)["entries"]}
        self.assertTrue(by_id["escort"]["completed"])

    def test_selling_the_only_escort_keeps_the_achievement(self):
        engine = _engine()
        _dock(engine)
        ok, message = engine.buy_escort("corvette")
        self.assertTrue(ok, message)
        ship_id = engine.state.ship.fleet_ships[-1].id
        ok, message = engine.sell_escort(ship_id)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fleet_ships, ())
        self.assertEqual(metric_value(engine.state, "escorts"), 1)
        by_id = {entry["id"]: entry for entry in build_codex_report(engine.state)["entries"]}
        self.assertTrue(by_id["escort"]["completed"], "the achievement must not be lost")

    def test_dismissing_the_only_escort_keeps_the_achievement(self):
        engine = _engine()
        _dock(engine)
        ok, message = engine.buy_escort("corvette")
        self.assertTrue(ok, message)
        ship_id = engine.state.ship.fleet_ships[-1].id
        ok, message = engine.dismiss_escort(ship_id)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fleet_ships, ())
        self.assertEqual(metric_value(engine.state, "escorts"), 1)

    def test_giving_a_captain_keeps_the_credit_after_a_recall(self):
        engine = _engine()
        _dock(engine)
        ok, message = engine.buy_escort("corvette")
        self.assertTrue(ok, message)
        ship_id = engine.state.ship.fleet_ships[-1].id
        ok, message = engine.assign_fleet_captain(ship_id, _member_id(engine))
        self.assertTrue(ok, message)
        self.assertEqual(metric_value(engine.state, "escort_captains"), 1)
        ok, message = engine.recall_fleet_captain(ship_id)
        self.assertTrue(ok, message)
        self.assertEqual(metric_value(engine.state, "escort_captains"), 1)
        by_id = {entry["id"]: entry for entry in build_codex_report(engine.state)["entries"]}
        self.assertTrue(by_id["fleet_captain"]["completed"])

    def test_three_commissions_count_even_one_at_a_time(self):
        engine = _engine()
        _dock(engine)
        for _ in range(3):
            ok, message = engine.buy_escort("corvette")
            self.assertTrue(ok, message)
            ship_id = engine.state.ship.fleet_ships[-1].id
            ok, message = engine.sell_escort(ship_id)
            self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fleet_ships, ())
        self.assertGreaterEqual(metric_value(engine.state, "escorts"), 3)
        by_id = {entry["id"]: entry for entry in build_codex_report(engine.state)["entries"]}
        self.assertTrue(by_id["squadron"]["completed"])

    def test_a_legacy_save_still_counts_the_current_roster(self):
        engine = _engine()
        escort = replace(build_fleet_ship("corvette", "sol", 0), captain_id="crew_engineer_1")
        engine.state = engine._clone_state(
            ship=engine._clone_ship(fleet_ships=(escort,), stats={})
        )
        self.assertEqual(metric_value(engine.state, "escorts"), 1)
        self.assertEqual(metric_value(engine.state, "escort_captains"), 1)

    def test_the_higher_of_roster_and_commissions_wins(self):
        engine = _engine()
        _dock(engine)
        for _ in range(2):
            ok, message = engine.buy_escort("corvette")
            self.assertTrue(ok, message)
        self.assertEqual(metric_value(engine.state, "escorts"), 2)


if __name__ == "__main__":
    unittest.main()
