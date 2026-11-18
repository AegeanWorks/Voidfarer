"""Unified empire report/action, REST and CLI tests."""

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
from voidfarer.empire import empire_action, empire_report, empire_summary
from voidfarer.engine import SimulationEngine
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _base() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.state = engine._clone_state(
        ship=engine._clone_ship(
            credits=50000,
            mastery=replace(engine.state.ship.mastery, level=2),
        ),
    )
    return engine


class TestEmpireReport(unittest.TestCase):
    def test_report_has_every_empire_section(self):
        report = empire_report(_base())
        for key in ("research", "outposts", "megastructure", "diplomacy", "corporations", "counts"):
            self.assertIn(key, report)
        self.assertEqual(
            set(report["counts"]),
            {
                "research_available", "research_completed", "outposts",
                "leaders", "active_wars", "corporations",
            },
        )
        self.assertIn("leaders", report["diplomacy"])
        self.assertIn("wars", report["diplomacy"])

    def test_summary_and_snapshot(self):
        summary = empire_summary(_base().state)
        self.assertIn("research_active", summary)
        self.assertIn("outposts", summary)
        self.assertIn("active_wars", summary)
        snapshot = _base().get_status_snapshot(include_static=False)
        self.assertIn("empire", snapshot)
        self.assertIn("leaders", snapshot["empire"])


class TestEmpireActions(unittest.TestCase):
    def test_research_start_queue_and_cancel(self):
        engine = _base()
        ok, message = empire_action(engine, "research_start", project_id="advanced_cooling")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.research.active_project_id, "advanced_cooling")
        ok, message = empire_action(engine, "research_queue", project_id="deep_survey_arrays")
        self.assertTrue(ok, message)
        self.assertIn("deep_survey_arrays", engine.state.research.queue)
        ok, message = empire_action(engine, "research_cancel", project_id="deep_survey_arrays")
        self.assertTrue(ok, message)
        self.assertNotIn("deep_survey_arrays", engine.state.research.queue)

    def test_build_and_upgrade_outpost(self):
        engine = _base()
        engine.state = engine._clone_state(
            ship=engine._clone_ship(orbiting_body_id="sol_body_5", travel=None, landed_body_id=None)
        )
        ok, message = empire_action(
            engine, "outpost_build", outpost_type_id="mining", body_id="sol_body_5"
        )
        self.assertTrue(ok, message)
        self.assertTrue(engine.state.outposts)
        outpost = engine.state.outposts[0]
        ok, message = empire_action(engine, "outpost_upgrade", outpost_id=outpost.id)
        self.assertTrue(ok, message)
        upgraded = next(o for o in engine.state.outposts if o.id == outpost.id)
        self.assertGreaterEqual(upgraded.level, 2)

    def test_restore_megastructure(self):
        engine = _base()
        engine.state = engine._clone_state(
            ship=engine._clone_ship(orbiting_body_id="sol_ring_world", travel=None, landed_body_id=None)
        )
        ok, message = empire_action(engine, "megastructure_restore", body_id="sol_ring_world")
        self.assertTrue(ok, message)
        body = next(b for b in engine.current_system.bodies if b.id == "sol_ring_world")
        self.assertTrue(body.restoration_complete)

    def test_diplomacy_gift(self):
        engine = _base()
        before = engine.state.ship.faction_standings.get("sol_coalition", 0)
        ok, message = empire_action(
            engine, "diplomacy",
            faction_id="sol_coalition", diplomacy_action="gift", amount=100,
        )
        self.assertTrue(ok, message)
        self.assertGreater(engine.state.ship.faction_standings.get("sol_coalition", 0), before)

    def test_invalid_action_is_rejected(self):
        ok, message = empire_action(_base(), "conquer")
        self.assertFalse(ok)
        self.assertIn("Unknown empire action", message)


class TestEmpireSurfaces(unittest.TestCase):
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

    def test_get_endpoint_returns_the_report(self):
        status, payload = self._get("/api/empire")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("research", payload)
        self.assertIn("diplomacy", payload)
        self.assertIn("outposts", payload)

    def test_action_endpoint_starts_research(self):
        status, payload = self._post(
            "/api/empire/action",
            {"action": "research_start", "project_id": "advanced_cooling"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(self.engine.state.research.active_project_id, "advanced_cooling")

    def test_cli_status_and_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "empire"])
            self.assertEqual(code, 0)
            self.assertIn("EMPIRE", buffer.getvalue())
            for section in ("research", "outposts", "megastructure", "diplomacy", "war"):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = cli.main(["--save-path", temp, "empire", section])
                self.assertEqual(code, 0, section)


if __name__ == "__main__":
    unittest.main()
