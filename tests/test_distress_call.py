"""Distress call: a truly stranded ship can summon a rescue tender, at a price, through every surface."""

from __future__ import annotations

import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.cli import main
from voidfarer.engine import SimulationEngine
from voidfarer.engineering import ENGINEERING_ACTIONS, engineering_action, engineering_report
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


def _stranded(credits: int = 500, fuel: int = 0, cargo: dict | None = None) -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.state = engine._clone_state(
        ship=engine._clone_ship(fuel=fuel, credits=credits, cargo=cargo or {}),
    )
    return engine


class TestDistressCall(unittest.TestCase):
    def test_rescue_delivers_fuel_charges_the_fee_and_costs_time(self) -> None:
        engine = _stranded()
        tick = engine.state.time.tick
        ok, message = engine.distress_call()
        self.assertTrue(ok, message)
        ship = engine.state.ship
        self.assertEqual(ship.fuel, engine.RESCUE_FUEL)
        # The fee is charged, and the wait also runs payroll, so the balance ends at or below 300.
        self.assertLessEqual(ship.credits, 500 - engine.RESCUE_FEE)
        self.assertGreater(ship.credits, 500 - engine.RESCUE_FEE - 50)
        self.assertEqual(engine.state.time.tick, tick + engine.RESCUE_WAIT_TICKS)
        self.assertIn("rescue tender", message.lower())

    def test_fee_never_exceeds_what_the_captain_holds(self) -> None:
        engine = _stranded(credits=50)
        ok, _ = engine.distress_call()
        self.assertTrue(ok)
        self.assertEqual(engine.state.ship.credits, 0)

    def test_a_broke_captain_is_still_rescued(self) -> None:
        engine = _stranded(credits=0)
        ok, _ = engine.distress_call()
        self.assertTrue(ok)
        self.assertGreater(engine.state.ship.fuel, 0)

    def test_guards_refuse_without_changing_state(self) -> None:
        cases = (
            (60, {}, "not stranded"),
            (0, {"fuel_cells": 2}, "fuel cell"),
            (0, {"titanium": 1}, "fabricate"),
        )
        for fuel, cargo, needle in cases:
            engine = _stranded(fuel=fuel, cargo=cargo)
            before = (engine.state.ship.fuel, engine.state.ship.credits, engine.state.time.tick)
            ok, message = engine.distress_call()
            self.assertFalse(ok, message)
            self.assertIn(needle, message.lower())
            self.assertEqual((engine.state.ship.fuel, engine.state.ship.credits, engine.state.time.tick), before)

    def test_it_is_refused_while_an_encounter_freezes_flight(self) -> None:
        engine = _stranded()
        with patch.object(SimulationEngine, "_action_lock_reason", return_value="Pirate intercept unresolved."):
            ok, message = engine.distress_call()
        self.assertFalse(ok)
        self.assertIn("Pirate", message)


class TestSurfaces(unittest.TestCase):
    def test_engineering_action_and_report(self) -> None:
        self.assertIn("distress", ENGINEERING_ACTIONS)
        engine = _stranded()
        rescue = engineering_report(engine)["rescue"]
        self.assertTrue(rescue["available"])
        self.assertEqual(rescue["fuel"], engine.RESCUE_FUEL)
        ok, message = engineering_action(engine, "distress")
        self.assertTrue(ok, message)
        self.assertFalse(engineering_report(engine)["rescue"]["available"])

    def test_cli_engineering_distress_saves(self) -> None:
        engine = _stranded()
        with tempfile.TemporaryDirectory() as save_dir:
            storage = StorageManager(save_dir)
            storage.save(engine.state)
            with patch("voidfarer.cli.StorageManager", return_value=storage), \
                    patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(main(["engineering", "distress"]), 0)
            self.assertIn("rescue", out.getvalue().lower())
            self.assertEqual(storage.load().ship.fuel, engine.RESCUE_FUEL)

    def test_rest_engineering_action(self) -> None:
        engine = _stranded()
        with tempfile.TemporaryDirectory() as save_dir:
            VoidFarerHandler.engine = engine
            VoidFarerHandler.storage = StorageManager(save_dir)
            VoidFarerHandler.static_dir = STATIC
            server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request("POST", "/api/engineering/action", json.dumps({"action": "distress"}),
                             {"Content-Type": "application/json"})
                payload = json.loads(conn.getresponse().read())
                conn.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2.0)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(engine.state.ship.fuel, engine.RESCUE_FUEL)


class TestSnapshotVerdict(unittest.TestCase):
    def test_snapshot_carries_the_engines_verdict_only_when_fuel_is_low(self) -> None:
        stranded = _stranded()
        verdict = stranded.get_status_snapshot()["rescue"]
        self.assertTrue(verdict["available"])
        healthy = SimulationEngine(seed=42)
        self.assertIsNone(healthy.get_status_snapshot()["rescue"])

    def test_a_low_tank_that_can_still_jump_is_not_offered_a_rescue(self) -> None:
        engine = _stranded(fuel=15)  # 25% of 60: gauge is low, but a jump (about 8) is affordable
        verdict = engine.get_status_snapshot()["rescue"]
        self.assertFalse(verdict["available"])
        self.assertIn("not stranded", verdict["reason"])


class TestScoopFirst(unittest.TestCase):
    def test_a_stranded_ship_orbiting_a_scoopable_body_is_told_to_scoop(self) -> None:
        engine = _stranded()
        star = next(b for b in engine.current_system.bodies if b.body_type == "star")
        engine.orbit(star.id)
        engine.state = engine._clone_state(ship=engine._clone_ship(fuel=0, credits=500, cargo={}))
        ok, message = engine.distress_call()
        self.assertFalse(ok)
        self.assertIn("scoop", message.lower())
        self.assertFalse(engine.rescue_status()["available"])

    def test_scooping_is_not_assumed_when_nothing_scoopable_is_in_orbit(self) -> None:
        self.assertTrue(_stranded().rescue_status()["available"])


if __name__ == "__main__":
    unittest.main()
