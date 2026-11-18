"""Unified comms report/action, REST and CLI tests."""

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
from voidfarer.comms import comms_action, comms_report, comms_summary
from voidfarer.engine import SimulationEngine
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _base() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


class TestCommsReport(unittest.TestCase):
    def test_report_has_every_section(self):
        report = comms_report(_base())
        for key in ("captains", "messages", "trees", "counts"):
            self.assertIn(key, report)
        self.assertEqual(
            set(report["counts"]),
            {
                "captains", "allies", "messages",
                "unread", "unresolved", "trees",
            },
        )

    def test_captains_and_inbox_are_populated(self):
        report = comms_report(_base())
        self.assertTrue(report["captains"])
        self.assertTrue(report["messages"])
        self.assertTrue(report["trees"])
        self.assertIn("trust", report["captains"][0])

    def test_summary_and_snapshot(self):
        engine = _base()
        summary = comms_summary(engine.state)
        self.assertIn("allied_captains", summary)
        self.assertIn("unread", summary)
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertIn("comms", snapshot)


class TestCommsActions(unittest.TestCase):
    def test_hail_captain(self):
        engine = _base()
        captain = engine.state.ai_captains[0]
        before = captain.trust
        ok, message = comms_action(engine, "hail", captain_id=captain.id)
        self.assertTrue(ok, message)
        updated = next(c for c in engine.state.ai_captains if c.id == captain.id)
        self.assertGreater(updated.trust, before)

    def test_send_and_read_message(self):
        engine = _base()
        ok, message = comms_action(
            engine, "send",
            recipient="Captain Vega", subject="Route", body="Meet at Sol.",
        )
        self.assertTrue(ok, message)
        sent = next(m for m in engine.state.messages if m.subject == "Route")
        ok, message = comms_action(engine, "read", message_id=sent.id)
        self.assertTrue(ok, message)
        self.assertTrue(next(m for m in engine.state.messages if m.id == sent.id).read)

    def test_choose_message_branch(self):
        engine = _base()
        message = next(m for m in engine.state.messages if m.choices)
        ok, response = comms_action(
            engine, "choose",
            message_id=message.id, choice_id=message.choices[0].id,
        )
        self.assertTrue(ok, response)
        resolved = next(m for m in engine.state.messages if m.id == message.id)
        self.assertEqual(resolved.resolved_choice, message.choices[0].id)

    def test_invalid_action_is_rejected(self):
        ok, message = comms_action(_base(), "jam")
        self.assertFalse(ok)
        self.assertIn("Unknown comms action", message)


class TestCommsSurfaces(unittest.TestCase):
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
        status, payload = self._get("/api/comms")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("captains", payload)
        self.assertIn("messages", payload)
        self.assertIn("trees", payload)

    def test_action_endpoint_hails(self):
        captain_id = self.engine.state.ai_captains[0].id
        status, payload = self._post(
            "/api/comms/action", {"action": "hail", "captain_id": captain_id}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)

    def test_cli_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            for section in ("status", "captains", "inbox", "trees"):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = cli.main(["--save-path", temp, "comms", section])
                self.assertEqual(code, 0, section)
                self.assertTrue(buffer.getvalue().strip(), section)


if __name__ == "__main__":
    unittest.main()
