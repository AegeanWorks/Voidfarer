"""Unified surface report/action, REST and CLI tests."""

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
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager
from voidfarer.surface_ops import surface_action, surface_report, surface_summary


def _base(orbiting: str = "sol_body_5") -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.state = engine._clone_state(
        ship=engine._clone_ship(orbiting_body_id=orbiting, travel=None, credits=50000)
    )
    return engine


class TestSurfaceReport(unittest.TestCase):
    def test_report_has_every_section(self):
        report = surface_report(_base())
        for key in ("surface", "body", "reconstruction", "counts"):
            self.assertIn(key, report)
        self.assertEqual(
            set(report["counts"]),
            {
                "landed", "operations", "ready_operations",
                "can_land", "can_reconstruct",
            },
        )

    def test_body_and_operations(self):
        report = surface_report(_base())
        self.assertFalse(report["surface"]["landed"])
        self.assertTrue(report["body"]["landable"])
        self.assertTrue(report["counts"]["can_land"])

    def test_summary_and_snapshot(self):
        engine = _base()
        summary = surface_summary(engine.state)
        self.assertFalse(summary["landed"])
        self.assertEqual(summary["body"], "sol_body_5")
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertIn("surface", snapshot)


class TestSurfaceActions(unittest.TestCase):
    def test_land_and_run_operation(self):
        engine = _base()
        ok, message = surface_action(engine, "land", body_id="sol_body_5")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.landed_body_id, "sol_body_5")
        report = engine.get_surface_report()
        self.assertTrue(report["landed"])
        operation = next(op for op in report["operations"] if not op["used"])
        ok, message = surface_action(engine, "operation", operation_id=operation["id"])
        self.assertTrue(ok, message)

    def test_reconstruct_devastated_world(self):
        engine = _base()
        system = engine.current_system
        body = next(b for b in system.bodies if b.id == "sol_body_5")
        damaged = replace(body, devastation=40.0, population=max(1, body.population))
        updated_system = replace(
            system,
            bodies=tuple(damaged if b.id == body.id else b for b in system.bodies),
        )
        engine.state = engine._clone_state(
            systems={**engine.state.systems, system.id: updated_system},
            ship=engine._clone_ship(orbiting_body_id=body.id, travel=None, credits=50000),
        )
        ok, message = surface_action(
            engine, "reconstruct", body_id=body.id, mode="credits"
        )
        self.assertTrue(ok, message)

    def test_invalid_action_is_rejected(self):
        ok, message = surface_action(_base(), "dig")
        self.assertFalse(ok)
        self.assertIn("Unknown surface action", message)


class TestSurfaceSurfaces(unittest.TestCase):
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
        status, payload = self._get("/api/surface")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("report", payload)
        self.assertIn("surface", payload["report"])
        self.assertIn("reconstruction", payload["report"])

    def test_action_endpoint_lands(self):
        status, payload = self._post(
            "/api/surface/action", {"action": "land", "body_id": "sol_body_5"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(self.engine.state.ship.landed_body_id, "sol_body_5")

    def test_cli_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "surface"])
            self.assertEqual(code, 0)
            self.assertTrue(buffer.getvalue().strip())
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main([
                    "--save-path", temp, "surface", "land", "sol_body_5",
                ])
            self.assertEqual(code, 0)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "surface"])
            self.assertEqual(code, 0)
            self.assertIn("SURFACE OPERATIONS", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
