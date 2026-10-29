"""Regressions pinned by the post-implementation review pass."""

import random
import socket
import unittest
from dataclasses import replace
from unittest.mock import patch

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.decisions import DECISION_DEFINITIONS
from voidfarer.economy import MIN_STOCK
from voidfarer.engine import SimulationEngine
from voidfarer.factions import get_faction_id_from_name
from voidfarer.frontier import simulate_ai_trade
from voidfarer.logbook import is_notable, trim_log
from voidfarer.models import VoidTraversalState


class FlightSafetyTest(unittest.TestCase):
    def test_void_traversal_locks_flight_and_body_actions(self):
        engine = SimulationEngine(seed=42)
        traversal = VoidTraversalState(
            origin_system_id="sol",
            destination_system_id="alpha_centauri",
            started_tick=0,
            arrival_tick=5,
            duration_ticks=5,
            stability=100.0,
        )
        engine.state = engine._clone_state(ship=engine._clone_ship(void_traversal=traversal))
        checks = [
            engine.jump("alpha_centauri"),
            engine.orbit("sol_body_1"),
            engine.start_travel("sol_body_1", "sublight"),
            engine.start_travel_to_point(3.0, 0.5),
            engine.scan()[:2],
        ]
        for ok, message in checks:
            self.assertFalse(ok, message)
            self.assertIn("Void traversal", message)

    def test_transit_blocks_body_services_until_arrival_or_origin_abort(self):
        engine = SimulationEngine(seed=42)
        self.assertTrue(engine.orbit("sol_body_1")[0])
        self.assertTrue(engine.start_travel("sol_body_2", "sublight")[0])

        ok, message, _ = engine.scan()
        self.assertFalse(ok)
        self.assertIn("In transit", message)
        ok, message = engine.land_on_body("sol_body_1")
        self.assertFalse(ok)
        self.assertIn("In transit", message)
        ok, message = engine.orbit("sol_body_2")
        self.assertFalse(ok, "cannot snap into a new orbit mid-flight")
        self.assertIn("origin body to abort", message)

        ok, message = engine.orbit("sol_body_1")
        self.assertTrue(ok, "orbiting the origin aborts the trip")
        self.assertIsNone(engine.state.ship.travel)
        self.assertTrue(engine.scan()[0])

    def test_waypoint_extremes_are_rejected_without_raising(self):
        engine = SimulationEngine(seed=42)
        for distance, angle in ((2.0, 10**400), (float("inf"), 0.0), (2.0, float("nan"))):
            ok, message = engine.start_travel_to_point(distance, angle)
            self.assertFalse(ok, (distance, angle))
            self.assertTrue(message, (distance, angle))
        self.assertIsNone(engine.state.ship.travel)

    def test_home_traffic_survives_the_first_tick(self):
        engine = SimulationEngine(seed=42)
        self.assertTrue(any(c.system_id == "sol" for c in engine.state.ai_captains))
        engine.tick(1)
        self.assertTrue(
            any(c.system_id == "sol" for c in engine.state.ai_captains),
            "Sol must keep at least one hull so local space is never empty",
        )


class EconomyIntegrityTest(unittest.TestCase):
    def test_ai_trade_cannot_mint_stock_at_the_floor(self):
        engine = SimulationEngine(seed=42)
        trader = next(c for c in engine.state.ai_captains if c.archetype == "trader")
        trader = replace(trader, system_id="sol", credits=1000)
        markets = dict(engine.state.economy.markets)
        origin = markets["sol"]
        # Every commodity at the floor, so whichever one the trader picks has nothing movable.
        origin = replace(origin, stockpiles={cid: MIN_STOCK for cid in origin.stockpiles})
        markets["sol"] = origin
        economy = replace(engine.state.economy, markets=markets)
        before = {
            cid: sum(m.stockpiles.get(cid, 0) for m in markets.values())
            for cid in origin.stockpiles
        }

        updated_captains, updated_economy, _ = simulate_ai_trade(
            (trader,), economy, engine.state.systems, random.Random(3)
        )
        after = {
            cid: sum(m.stockpiles.get(cid, 0) for m in updated_economy.markets.values())
            for cid in origin.stockpiles
        }
        self.assertEqual(after, before, "stock must be conserved, never minted from the floor")
        self.assertEqual(updated_captains[0].system_id, "sol")


class CadenceLifecycleTest(unittest.TestCase):
    def test_cadence_is_restored_on_load_and_reset_to_default(self):
        engine = SimulationEngine(seed=42)
        self.assertTrue(engine.set_decision_cadence("relaxed")[0])
        saved = type(engine.state).from_dict(engine.state.to_dict())
        loaded = SimulationEngine(seed=7)
        self.assertTrue(loaded.load_state(saved)[0])
        self.assertEqual(loaded.decision_cadence, "relaxed")
        self.assertEqual(loaded._decision_cooldown(), 36)
        loaded.reset(seed=7)
        self.assertEqual(loaded.decision_cadence, "normal")

    def test_a_batched_tick_compounds_the_decision_windows(self):
        engine = SimulationEngine(seed=42)
        engine.allow_decision_events = True
        engine.set_decision_cadence("normal")
        definition = DECISION_DEFINITIONS[0]
        with patch("voidfarer.engine.eligible_decisions", return_value=[definition]), \
                patch.object(engine, "_stable_unit", return_value=0.5):
            self.assertIsNone(engine.maybe_trigger_decision("tick", 1))
            self.assertIsNotNone(
                engine.maybe_trigger_decision("tick", 200),
                "200 batched ticks must roll the crossed cadence windows",
            )


class WarNewsTest(unittest.TestCase):
    def test_bankrupt_peace_is_notable_and_becomes_a_headline(self):
        line = (
            "BANKRUPT PEACE: Void Corsairs cannot pay its fleets, "
            "and Sol Coalition and Void Corsairs sign a treaty."
        )
        self.assertTrue(is_notable(line))
        events = SimulationEngine.war_news_events([line], 12, [])
        self.assertEqual([event.title for event in events], ["Peace Treaty Signed"])
        chatter = [f"AI TRADE: captain moved 1x water to Sol." for _ in range(30)]
        kept = trim_log(chatter[:3] + [line] + chatter[3:])
        self.assertIn(line, kept, "a notable treaty must survive log churn")

    def test_jump_keeps_hostile_arrival_morale_even_with_economy_news(self):
        engine = SimulationEngine(seed=42)
        target = "alpha_centauri"
        faction_id = get_faction_id_from_name(engine.state.systems[target].faction)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                credits=20000,
                fuel=60,
                faction_standings={faction_id: -100},
            ),
        )
        before = {member.id: member.morale for member in engine.state.ship.crew}
        with patch(
            "voidfarer.engine.tick_global_economy",
            return_value=(engine.state.economy, ["ECON: a market event expired."]),
        ):
            ok, message = engine.jump(target)
        self.assertTrue(ok, message)
        after = {member.id: member.morale for member in engine.state.ship.crew}
        self.assertTrue(
            any(after[cid] < before[cid] for cid in before),
            "hostile-arrival morale loss must not be reverted by the economy log clone",
        )


class AgentTransportTest(unittest.TestCase):
    def test_transport_failure_returns_a_reportable_error(self):
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        status, payload = ApiClient(port=port, timeout=0.4).get("/api/state")
        self.assertEqual(status, 0)
        self.assertFalse(payload["ok"])

    def test_malformed_json_is_a_protocol_error(self):
        class BrokenResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                return False

            def read(self):
                return b"not json"

        with patch(
            "voidfarer.agent_play.urllib.request.urlopen",
            return_value=BrokenResponse(),
        ):
            status, payload = ApiClient(port=1, timeout=0.1).get("/api/state")
        self.assertEqual(status, 0)
        self.assertFalse(payload["ok"])
        self.assertIn("invalid JSON", payload["message"])

    def test_blocked_actions_are_not_counted_as_attempted(self):
        class BlockedClient:
            def get(self, path):
                if path == "/api/agent/actions":
                    return 200, {"ok": True, "actions": [{"path": "/api/settings/decisions"}]}
                return 200, {"ok": True, "data": {"ship": {}, "time": {"tick": 0}}}

            def post(self, path, payload=None):
                return 409, {"ok": False, "state": {"ship": {}, "time": {"tick": 0}}}

        report = AiCaptain(BlockedClient()).play(steps=1)
        self.assertEqual(report["attempted"], [])
        self.assertFalse(report["ok"])

    def test_missing_catalog_is_an_error_not_silent_coverage(self):
        class FakeClient:
            def get(self, path):
                if path == "/api/agent/actions":
                    return 500, {"ok": False}
                return 200, {"ok": True, "data": {"ship": {}, "time": {"tick": 0}}}

            def post(self, path, payload=None):
                return 200, {"ok": True, "state": {"ship": {}, "time": {"tick": 0}}}

        report = AiCaptain(FakeClient()).play(steps=2)
        self.assertTrue(any("action catalog" in error for error in report["errors"]), report["errors"])


if __name__ == "__main__":
    unittest.main()
