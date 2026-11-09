"""Unified flight report/action, REST and CLI tests."""

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
from voidfarer.flight import flight_action, flight_report, flight_summary
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _base() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


class TestFlightReport(unittest.TestCase):
    def test_report_has_every_section(self):
        report = flight_report(_base())
        for key in ("system", "bodies", "connections", "ship", "counts"):
            self.assertIn(key, report)
        self.assertEqual(
            set(report["counts"]),
            {
                "connections", "reachable", "bodies",
                "landable_bodies", "scanned_bodies",
            },
        )

    def test_system_bodies_and_routes(self):
        report = flight_report(_base())
        self.assertEqual(report["system"]["id"], "sol")
        self.assertTrue(report["bodies"])
        self.assertTrue(report["connections"])
        self.assertTrue(all(route["reachable"] for route in report["connections"]))

    def test_summary_and_snapshot(self):
        engine = _base()
        summary = flight_summary(engine.state)
        self.assertEqual(summary["current_system"], "sol")
        self.assertFalse(summary["traveling"])
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertIn("flight", snapshot)


class TestFlightActions(unittest.TestCase):
    def test_plot_route(self):
        ok, message = flight_action(_base(), "plot", target="alpha_centauri")
        self.assertTrue(ok, message)
        self.assertIn("alpha_centauri", message)
        self.assertIn("jumps", message)

    def test_plot_unknown_target(self):
        ok, message = flight_action(_base(), "plot", target="nowhere")
        self.assertFalse(ok)
        self.assertIn("No hyperlane route", message)

    def test_orbit_and_travel(self):
        engine = _base()
        ok, message = flight_action(engine, "orbit", body_id="sol_body_2")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.orbiting_body_id, "sol_body_2")
        ok, message = flight_action(
            engine, "travel", body_id="sol_body_3", mode="sublight"
        )
        self.assertTrue(ok, message)
        self.assertIsNotNone(engine.state.ship.travel)

    def test_jump(self):
        engine = _base()
        ok, message = flight_action(engine, "jump", system_id="alpha_centauri")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.current_system_id, "alpha_centauri")

    def test_invalid_action_is_rejected(self):
        ok, message = flight_action(_base(), "warp")
        self.assertFalse(ok)
        self.assertIn("Unknown flight action", message)


class TestFlightSurfaces(unittest.TestCase):
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
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body.decode("utf-8"))

    def _post(self, path: str, payload: dict):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request(
            "POST", path, body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body.decode("utf-8"))

    def test_get_endpoint_returns_report(self):
        status, payload = self._get("/api/flight")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("system", payload)
        self.assertIn("bodies", payload)
        self.assertIn("connections", payload)

    def test_action_endpoint_orbits(self):
        status, payload = self._post(
            "/api/flight/action", {"action": "orbit", "body_id": "sol_body_2"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(self.engine.state.ship.orbiting_body_id, "sol_body_2")

    def test_cli_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            for section in ("status", "system", "routes"):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = cli.main(["--save-path", temp, "flight", section])
                self.assertEqual(code, 0, section)
                self.assertTrue(buffer.getvalue().strip(), section)


if __name__ == "__main__":
    unittest.main()
