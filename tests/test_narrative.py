"""Unified narrative report/action, REST and CLI tests."""

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
from voidfarer.models import GameEvent
from voidfarer.narrative import (
    narrative_action,
    narrative_report,
    narrative_summary,
)
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _base() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


class TestNarrativeReport(unittest.TestCase):
    def test_report_has_every_section(self):
        report = narrative_report(_base())
        for key in (
            "story", "tutorial", "quests", "contracts",
            "contract_offers", "events", "active_events", "counts",
        ):
            self.assertIn(key, report)
        self.assertEqual(
            set(report["counts"]),
            {
                "quests", "contracts", "contract_offers", "events",
                "tutorial_steps", "tutorial_completed",
            },
        )

    def test_story_and_tutorial_rows(self):
        report = narrative_report(_base())
        self.assertFalse(report["story"]["completed"])
        self.assertIn("choices", report["story"])
        self.assertTrue(report["tutorial"]["steps"])
        self.assertIsNotNone(report["tutorial"]["current_step"])

    def test_summary_and_snapshot(self):
        engine = _base()
        summary = narrative_summary(engine.state)
        self.assertIn("story_act", summary)
        self.assertIn("tutorial_step", summary)
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertIn("narrative", snapshot)


class TestNarrativeActions(unittest.TestCase):
    def test_story_choice(self):
        engine = _base()
        choice = engine.story_status()["choices"][0]
        ok, message = narrative_action(engine, "story_choose", choice_id=choice["id"])
        self.assertTrue(ok, message)

    def test_tutorial_skip_and_reset(self):
        engine = _base()
        ok, message = narrative_action(engine, "tutorial_skip")
        self.assertTrue(ok, message)
        self.assertTrue(engine.state.ship.tutorial.skipped)
        ok, message = narrative_action(engine, "tutorial_reset")
        self.assertTrue(ok, message)
        self.assertFalse(engine.state.ship.tutorial.skipped)

    def test_contract_refresh(self):
        engine = _base()
        ok, message = narrative_action(engine, "contract_refresh")
        self.assertTrue(ok, message)
        self.assertTrue(engine.state.ship.active_contracts)

    def test_event_dismiss(self):
        engine = _base()
        engine.state = engine._clone_state(events=(
            GameEvent(id="evt_test", kind="system", title="Test", message="Test event"),
        ))
        ok, message = narrative_action(engine, "event_dismiss", event_id="evt_test")
        self.assertTrue(ok, message)
        self.assertTrue(engine.state.events[0].dismissed)

    def test_invalid_action_is_rejected(self):
        ok, message = narrative_action(_base(), "retcon")
        self.assertFalse(ok)
        self.assertIn("Unknown narrative action", message)


class TestNarrativeSurfaces(unittest.TestCase):
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
        status, payload = self._get("/api/narrative")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("story", payload)
        self.assertIn("tutorial", payload)
        self.assertIn("contracts", payload)

    def test_action_endpoint_skips_tutorial(self):
        status, payload = self._post(
            "/api/narrative/action", {"action": "tutorial_skip"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(self.engine.state.ship.tutorial.skipped)

    def test_cli_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            for section in ("story", "tutorial", "quests", "contracts", "events"):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = cli.main(["--save-path", temp, "narrative", section])
                self.assertEqual(code, 0, section)
                self.assertTrue(buffer.getvalue().strip(), section)


if __name__ == "__main__":
    unittest.main()
