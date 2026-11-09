"""Unified intel report/action, REST and CLI tests."""

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
from voidfarer.intel import intel_action, intel_report, intel_summary
from voidfarer.models import WarState
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _base() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


class TestIntelReport(unittest.TestCase):
    def test_report_has_every_section(self):
        report = intel_report(_base())
        for key in ("chart", "economy", "factions", "wars", "corporations", "counts"):
            self.assertIn(key, report)
        self.assertIn("systems", report["chart"])
        self.assertIn("bodies", report["chart"])
        self.assertIn("trade_routes", report["economy"])
        self.assertEqual(
            set(report["counts"]),
            {
                "systems", "visited", "scanned_bodies", "factions",
                "active_wars", "corporations", "trade_routes",
            },
        )

    def test_chart_points_at_the_current_system(self):
        engine = _base()
        report = intel_report(engine)
        current = next(s for s in report["chart"]["systems"] if s["current"])
        self.assertEqual(current["id"], engine.current_system.id)
        self.assertTrue(report["chart"]["bodies"])

    def test_factions_and_corporations_are_rated(self):
        report = intel_report(_base())
        self.assertTrue(report["factions"])
        self.assertTrue(report["corporations"])
        self.assertIn("tier", report["factions"][0])
        self.assertIn("perk", report["corporations"][0])

    def test_summary_and_snapshot(self):
        engine = _base()
        summary = intel_summary(engine.state)
        self.assertEqual(summary["current_system"], engine.current_system.name)
        self.assertIn("active_wars", summary)
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertIn("intel", snapshot)

    def test_scan_records_the_body(self):
        engine = _base()
        body = engine.orbiting_body
        self.assertIsNotNone(body)
        ok, message = intel_action(engine, "scan")
        self.assertTrue(ok, message)
        self.assertTrue(engine.orbiting_body.scan_completed)


class TestIntelActions(unittest.TestCase):
    def test_war_support_routes_to_engine(self):
        engine = _base()
        engine.state = engine._clone_state(wars=(
            WarState(
                id="war_test",
                attacker_id="sol_coalition",
                defender_id="outlaw_corsairs",
                started_tick=0,
            ),
        ))
        war = engine.galactic_politics()["wars"][0]
        ok, message = intel_action(
            engine, "war_support",
            war_id=war["id"], faction_id=war["attacker_id"], credits=100,
        )
        self.assertTrue(ok, message)

    def test_invalid_action_is_rejected(self):
        ok, message = intel_action(_base(), "spy")
        self.assertFalse(ok)
        self.assertIn("Unknown intel action", message)


class TestIntelSurfaces(unittest.TestCase):
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
        status, payload = self._get("/api/intel")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("chart", payload)
        self.assertIn("factions", payload)
        self.assertIn("corporations", payload)

    def test_action_endpoint_scans(self):
        status, payload = self._post("/api/intel/action", {"action": "scan"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)

    def test_cli_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            for section in ("chart", "economy", "factions", "war", "corps"):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = cli.main(["--save-path", temp, "intel", section])
                self.assertEqual(code, 0, section)
                self.assertTrue(buffer.getvalue().strip(), section)


if __name__ == "__main__":
    unittest.main()
