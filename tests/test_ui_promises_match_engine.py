"""The numbers the cockpit advertises equal what the engine does: preview, quote, threshold, price and yield."""

from __future__ import annotations

import unittest
from dataclasses import replace

from voidfarer.engine import SimulationEngine
from voidfarer.outposts import OUTPOST_TYPES, can_build_on


def _engine(seed: int = 42, **ship) -> SimulationEngine:
    engine = SimulationEngine(seed=seed)
    engine.allow_decision_events = False
    engine.pause_time()
    if ship:
        engine.state = engine._clone_state(ship=engine._clone_ship(**ship))
    return engine


class TestTransitPreviewIsExact(unittest.TestCase):
    def test_preview_duration_and_fuel_equal_a_real_transit(self) -> None:
        for power in ((30, 25, 25, 20), (60, 15, 15, 10)):
            for mode in ("sublight", "quantum"):
                probe = _engine()
                probe.route_power(*power)
                bodies = [b.id for b in probe.current_system.bodies if b.id != probe.state.ship.orbiting_body_id][:3]
                for body_id in bodies:
                    engine = _engine()
                    engine.route_power(*power)
                    ok, preview = engine.preview_travel(body_id, mode=mode)
                    if not ok:
                        continue
                    before = engine.state.ship.fuel
                    started, message = engine.start_travel(body_id, mode=mode)
                    self.assertTrue(started, message)
                    ticks = 0
                    while engine.state.ship.travel and ticks < 80:
                        engine.tick(1)
                        ticks += 1
                    self.assertEqual(preview["duration_ticks"], ticks, (power, mode, body_id))
                    self.assertEqual(preview["fuel_cost"], before - engine.state.ship.fuel, (power, mode, body_id))


class TestDrydockQuotesAreExact(unittest.TestCase):
    def test_repair_refuel_and_overhaul_charge_exactly_the_quote(self) -> None:
        engine = _engine()
        station = next(b.id for b in engine.current_system.bodies if b.station_dockable)
        engine.orbit(station)
        engine.state = engine._clone_state(ship=engine._clone_ship(hull=40, fuel=10, wear=35.0, credits=9000))
        quote = engine.get_status_snapshot()["drydock"]
        before = engine.state.ship.credits
        engine.repair_hull(quote["repair_hp"])
        self.assertEqual(before - engine.state.ship.credits, quote["repair_cost"])
        quote = engine.get_status_snapshot()["drydock"]
        before = engine.state.ship.credits
        engine.refuel(quote["fuel_units"])
        if not quote["free_refuel"]:
            self.assertEqual(before - engine.state.ship.credits, quote["refuel_cost"])
        quote = engine.get_status_snapshot()["drydock"]
        before = engine.state.ship.credits
        engine.overhaul_ship()
        self.assertEqual(before - engine.state.ship.credits, quote["overhaul_cost"])


class TestDiplomacyThresholdsMatchTheTooltips(unittest.TestCase):
    CLAIMS = {"non_aggression": 30, "trade_pact": 40, "research_pact": 60, "alliance": 70}

    def _accepts(self, action: str, standing: int) -> bool:
        engine = _engine()
        standings = dict(engine.state.ship.faction_standings)
        standings["kepler_concord"] = standing
        engine.state = engine._clone_state(ship=engine._clone_ship(faction_standings=standings, credits=9000))
        return engine.faction_diplomacy("kepler_concord", action)[0]

    def test_each_action_is_refused_one_point_below_and_accepted_at_the_stated_standing(self) -> None:
        for action, claim in self.CLAIMS.items():
            self.assertFalse(self._accepts(action, claim - 1), f"{action} at {claim - 1}")
            self.assertTrue(self._accepts(action, claim), f"{action} at {claim}")

    def test_non_aggression_lasts_the_advertised_90_ticks_and_a_gift_costs_300(self) -> None:
        engine = _engine()
        standings = dict(engine.state.ship.faction_standings)
        standings["kepler_concord"] = 80
        engine.state = engine._clone_state(ship=engine._clone_ship(faction_standings=standings, credits=9000))
        engine.faction_diplomacy("kepler_concord", "non_aggression")
        self.assertEqual(engine.non_aggression_remaining("kepler_concord"), 90)
        before = engine.state.ship.credits
        engine.faction_diplomacy("kepler_concord", "gift", 300)
        self.assertEqual(before - engine.state.ship.credits, 300)


class TestOutpostPromises(unittest.TestCase):
    def _chartered(self) -> SimulationEngine:
        engine = _engine()
        engine.state = engine._clone_state(ship=engine._clone_ship(
            credits=50000, mastery=replace(engine.state.ship.mastery, level=2)))
        return engine

    def test_price_is_charged_and_credit_yield_matches_the_card(self) -> None:
        kind = next(t for t in OUTPOST_TYPES if t.id == "mining")
        with_outpost, without = self._chartered(), self._chartered()
        body = next(b for b in with_outpost.current_system.bodies
                    if b.body_type != "star" and can_build_on(b, kind))
        for engine in (with_outpost, without):
            engine.orbit(body.id)
        before = with_outpost.state.ship.credits
        ok, message = with_outpost.build_outpost(body.id, "mining")
        self.assertTrue(ok, message)
        self.assertEqual(before - with_outpost.state.ship.credits, kind.cost)
        start_with, start_without = with_outpost.state.ship.credits, without.state.ship.credits
        with_outpost.tick(30)
        without.tick(30)
        gained = (with_outpost.state.ship.credits - start_with) - (without.state.ship.credits - start_without)
        self.assertEqual(gained, int(kind.production["credits"] * 30))

    def test_goods_are_delivered_to_the_local_depot_at_the_card_rate(self) -> None:
        kind = next(t for t in OUTPOST_TYPES if t.id == "mining")
        engine = self._chartered()
        body = next(b for b in engine.current_system.bodies if b.body_type != "star" and can_build_on(b, kind))
        engine.orbit(body.id)
        engine.build_outpost(body.id, "mining")
        depot = next(d for d in engine.state.depots if d.system_id == engine.current_system.id)
        before = depot.cargo.get("titanium", 0)
        engine.tick(30)
        depot = next(d for d in engine.state.depots if d.system_id == engine.current_system.id)
        self.assertEqual(depot.cargo.get("titanium", 0) - before, int(kind.production["titanium"] * 30))


if __name__ == "__main__":
    unittest.main()
