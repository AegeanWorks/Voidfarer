"""Unified fleet report/action, REST and CLI tests."""

from __future__ import annotations

import contextlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer import cli
from voidfarer.engine import SimulationEngine
from voidfarer.fleet_command import fleet_action, fleet_report, fleet_summary
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=50000))
    return engine


class TestFleetReport(unittest.TestCase):
    def test_report_normalizes_every_asset_kind(self):
        report = fleet_report(_engine().state)
        for key in ("drones", "mercenaries", "escorts", "alliances", "catalogs"):
            self.assertIn(key, report)
        self.assertEqual(
            set(report["counts"]),
            {"drones", "mercenary_units", "escorts", "allies", "local_escorts"},
        )
        self.assertIn("drones", report["catalogs"])
        self.assertIn("escorts", report["catalogs"])
        self.assertIn("mercenaries", report["catalogs"])

    def test_summary_is_compact(self):
        summary = fleet_summary(_engine().state)
        self.assertEqual(
            set(summary["counts"]),
            {"drones", "mercenary_units", "escorts", "allies", "local_escorts"},
        )
        self.assertIn("upkeep_per_month", summary)
        self.assertIn("battle_stance", summary)
        self.assertNotIn("catalogs", summary)

    def test_snapshot_carries_fleet_counts(self):
        snapshot = _engine().get_status_snapshot(include_static=False)
        self.assertIn("fleet", snapshot)
        self.assertIn("counts", snapshot["fleet"])


class TestFleetActions(unittest.TestCase):
    def test_buy_deploy_collect_refit_and_dismiss_drone(self):
        engine = _engine()
        before = len(engine.state.ship.fleet_drones)
        ok, message = fleet_action(engine, "buy_drone", drone_type="mining")
        self.assertTrue(ok, message)
        self.assertEqual(len(engine.state.ship.fleet_drones), before + 1)
        unit = engine.state.ship.fleet_drones[-1]
        ok, message = fleet_action(engine, "deploy", unit_id=unit.id, system_id="altair")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fleet_drones[-1].assigned_system_id, "altair")
        ok, message = fleet_action(engine, "refit", unit_id=unit.id)
        self.assertTrue(ok, message)
        self.assertGreaterEqual(engine.state.ship.fleet_drones[-1].level, 2)
        ok, message = fleet_action(engine, "dismiss", unit_id=unit.id)
        self.assertTrue(ok, message)
        self.assertEqual(len(engine.state.ship.fleet_drones), before)

    def test_buy_assign_role_train_and_sell_escort(self):
        engine = _engine()
        ok, message = fleet_action(engine, "buy_escort", escort_type="corvette")
        self.assertTrue(ok, message)
        escort = engine.state.ship.fleet_ships[-1]
        ok, message = fleet_action(engine, "assign", ship_id=escort.id, system_id="altair")
        self.assertTrue(ok, message)
        ok, message = fleet_action(engine, "role", ship_id=escort.id, role="strike")
        self.assertTrue(ok, message)
        ok, message = fleet_action(engine, "train", ship_id=escort.id)
        self.assertTrue(ok, message)
        updated = next(ship for ship in engine.state.ship.fleet_ships if ship.id == escort.id)
        self.assertEqual(updated.assigned_system_id, "altair")
        self.assertEqual(updated.tactical_role, "strike")
        self.assertGreater(updated.experience, 0)
        ok, message = fleet_action(engine, "sell", ship_id=escort.id)
        self.assertTrue(ok, message)
        self.assertFalse(any(ship.id == escort.id for ship in engine.state.ship.fleet_ships))

    def test_hire_and_dismiss_mercenary(self):
        engine = _engine()
        ok, message = fleet_action(engine, "hire", merc_id="merc_ghost")
        self.assertTrue(ok, message)
        mercs = [d for d in engine.state.ship.fleet_drones if d.drone_type == "mercenary"]
        self.assertEqual(len(mercs), 1)
        self.assertEqual(mercs[0].specialty, "evasion")
        ok, message = fleet_action(engine, "dismiss", unit_id=mercs[0].id)
        self.assertTrue(ok, message)
        self.assertFalse(any(d.drone_type == "mercenary" for d in engine.state.ship.fleet_drones))

    def test_form_alliance(self):
        engine = _engine()
        captains = list(engine.state.ai_captains)
        first = replace(captains[0], trust=80)
        engine.state = engine._clone_state(ai_captains=(first,) + tuple(captains[1:]))
        ok, message = fleet_action(engine, "ally", captain_id=first.id)
        self.assertTrue(ok, message)
        self.assertIn(first.id, engine.state.ship.allies)

    def test_invalid_action_is_rejected(self):
        ok, message = fleet_action(_engine(), "warp")
        self.assertFalse(ok)
        self.assertIn("Unknown fleet action", message)


class TestFleetSurfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.storage = StorageManager(cls.temp_dir.name)
        cls.engine = SimulationEngine(seed=42)
        VoidFarerHandler.engine = cls.engine
        VoidFarerHandler.storage = cls.storage
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.engine = _engine()
        VoidFarerHandler.engine = self.engine
        VoidFarerHandler.storage = StorageManager(self.temp_dir.name)

    def _get(self, path: str):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body.decode("utf-8"))

    def _post(self, path: str, payload: dict):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        connection.request(
            "POST", path, body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body.decode("utf-8"))

    def test_get_endpoint_returns_the_report(self):
        status, payload = self._get("/api/fleet")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("report", payload)
        self.assertEqual(set(payload["report"]["catalogs"]), {"drones", "escorts", "mercenaries"})

    def test_action_endpoint_buys_a_drone(self):
        before = len(self.engine.state.ship.fleet_drones)
        status, payload = self._post(
            "/api/fleet/action", {"action": "buy_drone", "drone_type": "mining"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(len(self.engine.state.ship.fleet_drones), before + 1)

    def test_cli_overview_and_mercenary_hire(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "fleet", "overview"])
            self.assertEqual(code, 0)
            self.assertIn("FLEET OVERVIEW", buffer.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "fleet", "mercs"])
            self.assertEqual(code, 0)

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "fleet", "allies"])
            self.assertEqual(code, 0)

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "fleet", "hire", "merc_ghost"])
            self.assertEqual(code, 0)
            loaded = StorageManager(temp).load()
            self.assertIsNotNone(loaded)
            self.assertTrue(any(d.drone_type == "mercenary" for d in loaded.ship.fleet_drones))


if __name__ == "__main__":
    unittest.main()
