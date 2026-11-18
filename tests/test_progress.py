"""Unified progression report/action, REST and CLI tests."""

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
from voidfarer.progress import progress_action, progress_report, progress_summary
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.state = engine._clone_state(
        character=replace(engine.state.character, skill_points=5),
    )
    return engine


class TestProgressReport(unittest.TestCase):
    def test_report_covers_every_track(self):
        report = progress_report(_engine())
        for key in ("commander", "skills", "abilities", "pilot", "relics", "codex", "streak"):
            self.assertIn(key, report)
        self.assertEqual(
            set(report["counts"]),
            {"skills", "abilities_unlocked", "relics", "codex_claimed"},
        )
        self.assertIn("multiplier", report["streak"])

    def test_summary_is_compact(self):
        summary = progress_summary(_engine().state)
        self.assertIn("commander_level", summary)
        self.assertIn("pilot_level", summary)
        self.assertIn("talent_points", summary)
        self.assertIn("codex_claimed", summary)
        self.assertNotIn("abilities", summary)

    def test_snapshot_carries_progress_summary(self):
        snapshot = _engine().get_status_snapshot(include_static=False)
        self.assertIn("progress", snapshot)
        self.assertIn("commander_level", snapshot["progress"])


class TestProgressActions(unittest.TestCase):
    def test_train_skill_spends_a_point(self):
        engine = _engine()
        before = engine.state.character.skills["piloting"]
        points = engine.state.character.skill_points
        ok, message = progress_action(engine, "train", skill="piloting")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.character.skills["piloting"], before + 1)
        self.assertEqual(engine.state.character.skill_points, points - 1)

    def test_use_ability_overclocks_the_reactor(self):
        engine = _engine()
        ok, message = progress_action(engine, "use", ability_id="overclock")
        self.assertTrue(ok, message)
        self.assertGreater(engine.state.ship.reactor.heat, 0)
        self.assertGreater(engine.state.ship.reactor.surge_ticks, 0)

    def test_invalid_action_is_rejected(self):
        ok, message = progress_action(_engine(), "ascend")
        self.assertFalse(ok)
        self.assertIn("Unknown progress action", message)


class TestProgressSurfaces(unittest.TestCase):
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
        status, payload = self._get("/api/progress")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("commander", payload)
        self.assertIn("abilities", payload)
        self.assertIn("codex", payload)

    def test_action_endpoint_uses_the_skill_trainer(self):
        before = self.engine.state.character.skills["piloting"]
        status, payload = self._post(
            "/api/progress/action", {"action": "train", "skill": "piloting"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(self.engine.state.character.skills["piloting"], before + 1)

    def test_cli_status_and_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "progress"])
            self.assertEqual(code, 0)
            self.assertIn("PROGRESSION", buffer.getvalue())

            for section in ("commander", "pilot", "skills", "abilities", "relics", "codex", "streak"):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = cli.main(["--save-path", temp, "progress", section])
                self.assertEqual(code, 0, section)


if __name__ == "__main__":
    unittest.main()
