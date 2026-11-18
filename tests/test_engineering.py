"""Unified engineering report/action, REST and CLI tests."""

from __future__ import annotations

import contextlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer import cli
from voidfarer.engine import SimulationEngine
from voidfarer.engineering import (
    engineering_action,
    engineering_report,
    engineering_summary,
)
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _base() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


def _damaged() -> SimulationEngine:
    engine = _base()
    engine.state = engine._clone_state(
        ship=engine._clone_ship(hull=50, fuel=20, cargo={"titanium": 2}),
    )
    return engine


class TestEngineeringReport(unittest.TestCase):
    def test_report_has_every_section(self):
        report = engineering_report(_base())
        for key in (
            "reactor", "power", "hull", "fuel", "credits",
            "salvage", "scoop", "fabrication", "counts",
        ):
            self.assertIn(key, report)
        self.assertIn("blueprints", report["fabrication"])
        self.assertIn("heat_percent", report["counts"])

    def test_counts_track_hull_and_power(self):
        report = engineering_report(_damaged())
        self.assertEqual(report["hull"]["current"], 50)
        self.assertEqual(report["counts"]["power_total"], 100)
        self.assertEqual(report["counts"]["hull_percent"], 50.0)

    def test_summary_and_snapshot(self):
        engine = _base()
        summary = engineering_summary(engine.state)
        self.assertEqual(summary["power"], engine.state.ship.power.to_dict())
        self.assertIn("reactor_mode", summary)
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertIn("engineering", snapshot)


class TestEngineeringActions(unittest.TestCase):
    def test_power_routing(self):
        engine = _base()
        ok, message = engineering_action(
            engine, "power", engines=40, shields=30, sensors=20, weapons=10
        )
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.power.engines, 40)

    def test_reactor_mode(self):
        engine = _base()
        ok, message = engineering_action(engine, "reactor_mode", mode="overdrive")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.reactor.mode, "overdrive")

    def test_repair_and_refuel(self):
        engine = _damaged()
        ok, message = engineering_action(engine, "repair", amount=10)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.hull, 60)
        ok, message = engineering_action(engine, "refuel", amount=10)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fuel, 30)

    def test_fabricate_patch_kit(self):
        engine = _damaged()
        ok, message = engineering_action(engine, "fabricate", blueprint="patch_kit")
        self.assertTrue(ok, message)
        self.assertGreater(engine.state.ship.hull, 50)

    def test_invalid_action_is_rejected(self):
        ok, message = engineering_action(_base(), "teleport")
        self.assertFalse(ok)
        self.assertIn("Unknown engineering action", message)


class TestEngineeringSurfaces(unittest.TestCase):
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
        self.engine = _base()
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

    def test_get_endpoint_returns_report(self):
        status, payload = self._get("/api/engineering")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("reactor", payload)
        self.assertIn("power", payload)
        self.assertIn("fabrication", payload)

    def test_action_endpoint_routes_power(self):
        status, payload = self._post(
            "/api/engineering/action",
            {"action": "power", "engines": 40, "shields": 30, "sensors": 20, "weapons": 10},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(self.engine.state.ship.power.engines, 40)

    def test_cli_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            for section in ("status", "reactor", "power", "hull", "salvage", "fabrication"):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = cli.main(["--save-path", temp, "engineering", section])
                self.assertEqual(code, 0, section)
                self.assertTrue(buffer.getvalue().strip(), section)


if __name__ == "__main__":
    unittest.main()
