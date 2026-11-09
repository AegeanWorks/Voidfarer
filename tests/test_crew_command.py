"""Unified crew/away report and action tests."""

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
from voidfarer.crew_command import crew_action, crew_report, crew_summary
from voidfarer.engine import SimulationEngine
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _base() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


class TestCrewReport(unittest.TestCase):
    def test_report_has_roster_and_away(self):
        report = crew_report(_base())
        self.assertIn("roster", report)
        self.assertIn("away", report)
        self.assertEqual(
            set(report["counts"]),
            {
                "crew", "active", "capacity", "away_missions",
                "available_missions", "injured",
            },
        )
        self.assertIn("roles", report["roster"])
        self.assertIn("available", report["away"])

    def test_summary_and_snapshot(self):
        engine = _base()
        summary = crew_summary(engine.state)
        self.assertEqual(summary["capacity"], 8)
        self.assertIn("average_morale", summary)
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertIn("crew_overview", snapshot)
        self.assertIn("crew", snapshot)


class TestCrewActions(unittest.TestCase):
    def test_recruit_train_and_dismiss(self):
        engine = _base()
        role_id = engine.get_crew_report()["roles"][0]["id"]
        before = len(engine.state.ship.crew)
        ok, message = crew_action(engine, "recruit", role_id=role_id)
        self.assertTrue(ok, message)
        self.assertEqual(len(engine.state.ship.crew), before + 1)
        newcomer = engine.state.ship.crew[-1]
        ok, message = crew_action(engine, "train", crew_id=newcomer.id)
        self.assertTrue(ok, message)
        ok, message = crew_action(engine, "dismiss", crew_id=newcomer.id)
        self.assertTrue(ok, message)
        self.assertEqual(len(engine.state.ship.crew), before)

    def test_station_assign_and_clear(self):
        engine = _base()
        crew_id = engine.state.ship.crew[0].id
        ok, message = crew_action(
            engine, "station", crew_id=crew_id, station="unassigned"
        )
        self.assertTrue(ok, message)
        ok, message = crew_action(engine, "station", crew_id=crew_id, station="helm")
        self.assertTrue(ok, message)
        member = next(c for c in engine.state.ship.crew if c.id == crew_id)
        self.assertEqual(member.station, "helm")

    def test_shore_leave_reports_something(self):
        engine = _base()
        ok, message = crew_action(engine, "shore")
        self.assertIsInstance(ok, bool)
        self.assertTrue(message)

    def test_away_launch_and_recall(self):
        engine = _base()
        away = engine.get_away_report()
        mission = next(m for m in away["available"] if m["available"])
        ok, message = crew_action(engine, "away_launch", mission_type=mission["id"])
        self.assertTrue(ok, message)
        self.assertTrue(engine.state.ship.away_missions)
        mission_id = engine.state.ship.away_missions[0].id
        ok, message = crew_action(engine, "away_recall", mission_id=mission_id)
        self.assertTrue(ok, message)

    def test_invalid_action_is_rejected(self):
        ok, message = crew_action(_base(), "mutiny")
        self.assertFalse(ok)
        self.assertIn("Unknown crew action", message)


class TestCrewSurfaces(unittest.TestCase):
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
        status, payload = self._get("/api/crew")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("report", payload)
        self.assertIn("roster", payload["report"])
        self.assertIn("away", payload["report"])

    def test_action_endpoint_assigns_station(self):
        crew_id = self.engine.state.ship.crew[0].id
        status, payload = self._post(
            "/api/crew/action",
            {"action": "station", "crew_id": crew_id, "station": "helm"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)

    def test_cli_overview_and_away_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            for args in (["crew", "overview"], ["crew", "away"]):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = cli.main(["--save-path", temp, *args])
                self.assertEqual(code, 0, args)
                self.assertTrue(buffer.getvalue().strip())


if __name__ == "__main__":
    unittest.main()
