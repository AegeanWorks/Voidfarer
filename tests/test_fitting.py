"""Unified ship-fitting report, install/remove, REST and CLI tests."""

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
from voidfarer.fitting import fitting_report, fitting_summary, install, remove
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=50000))
    return engine


class TestFittingReport(unittest.TestCase):
    def test_report_covers_all_four_categories(self):
        report = fitting_report(_engine().state)
        self.assertTrue(report["service_dock"])
        self.assertEqual(report["ship_class"], "Corvette Scout")
        self.assertEqual(
            set(report["categories"]),
            {"upgrades", "modules", "weapons", "chassis"},
        )
        for name, category in report["categories"].items():
            self.assertIn("installed", category, name)
            self.assertIn("available", category, name)
            self.assertIn("installed_count", category, name)
            self.assertIn("available_count", category, name)

    def test_summary_is_compact_and_counts_are_named(self):
        summary = fitting_summary(_engine().state)
        self.assertTrue(summary["service_dock"])
        self.assertEqual(set(summary["categories"]), {"upgrades", "modules", "weapons", "chassis"})
        self.assertIn("upgrades_installed_count", summary["counts"])
        self.assertIn("weapons_available_count", summary["counts"])
        self.assertNotIn("weapons_primary", summary["counts"])

    def test_snapshot_carries_fitting_counts(self):
        snapshot = _engine().get_status_snapshot(include_static=False)
        self.assertIn("fitting", snapshot)
        self.assertIn("categories", snapshot["fitting"])


class TestFittingOperations(unittest.TestCase):
    def test_install_and_remove_upgrade(self):
        engine = _engine()
        report = fitting_report(engine.state)
        upgrade = report["categories"]["upgrades"]["available"][0]
        credits = engine.state.ship.credits
        ok, message = install(engine, "upgrades", upgrade["id"])
        self.assertTrue(ok, message)
        self.assertIn(upgrade["slot"], engine.state.ship.equipped_upgrades)
        self.assertEqual(engine.state.ship.credits, credits - upgrade["cost"])
        ok, message = remove(engine, "upgrades", upgrade["slot"])
        self.assertTrue(ok, message)
        self.assertNotIn(upgrade["slot"], engine.state.ship.equipped_upgrades)
        self.assertGreater(engine.state.ship.credits, credits - upgrade["cost"])

    def test_install_and_remove_structural_module(self):
        engine = _engine()
        report = fitting_report(engine.state)
        module = next(
            row for row in report["categories"]["modules"]["available"]
            if not row["slot_occupied"]
        )
        ok, message = install(engine, "modules", module["id"])
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.ship_mods[module["slot"]], module["id"])
        credits = engine.state.ship.credits
        ok, message = remove(engine, "modules", module["slot"])
        self.assertTrue(ok, message)
        self.assertNotIn(module["slot"], engine.state.ship.ship_mods)
        self.assertGreater(engine.state.ship.credits, credits)

    def test_install_weapon_sets_primary(self):
        engine = _engine()
        report = fitting_report(engine.state)
        weapon = next(
            row for row in report["categories"]["weapons"]["available"]
            if not row["installed"]
        )
        ok, message = install(engine, "weapons", weapon["id"])
        self.assertTrue(ok, message)
        self.assertIn(weapon["id"], engine.state.ship.weapons)
        self.assertEqual(engine.state.ship.primary_weapon, weapon["id"])

    def test_buy_chassis_changes_ship_class(self):
        engine = _engine()
        report = fitting_report(engine.state)
        chassis = report["categories"]["chassis"]["available"][0]
        ok, message = install(engine, "chassis", chassis["id"])
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.ship_class, chassis["ship_class"])

    def test_invalid_requests_are_rejected(self):
        engine = _engine()
        ok, message = install(engine, "nope", "x")
        self.assertFalse(ok)
        self.assertIn("Unknown fitting category", message)
        ok, message = install(engine, "upgrades", "")
        self.assertFalse(ok)
        self.assertIn("required", message)
        ok, message = remove(engine, "weapons", "pulse_laser")
        self.assertFalse(ok)
        self.assertIn("cannot be removed", message)


class TestFittingSurfaces(unittest.TestCase):
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

    def test_get_endpoint_returns_the_report(self):
        status, payload = self._get("/api/fitting")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["service_dock"])
        self.assertEqual(set(payload["categories"]), {"upgrades", "modules", "weapons", "chassis"})

    def test_install_endpoint_uses_the_facade(self):
        upgrade = fitting_report(self.engine.state)["categories"]["upgrades"]["available"][0]
        status, payload = self._post(
            "/api/fitting/install",
            {"category": "upgrades", "item_id": upgrade["id"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertIn(upgrade["slot"], self.engine.state.ship.equipped_upgrades)

    def test_cli_status_category_and_install(self):
        upgrade = fitting_report(self.engine.state)["categories"]["upgrades"]["available"][0]
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "fitting"])
            self.assertEqual(code, 0)
            self.assertIn("SHIP FITTING", buffer.getvalue())
            self.assertIn("upgrades", buffer.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "fitting", "upgrades"])
            self.assertEqual(code, 0)

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main([
                    "--save-path", temp, "fitting", "install", "upgrades", upgrade["id"],
                ])
            self.assertEqual(code, 0)
            loaded = StorageManager(temp).load()
            self.assertIsNotNone(loaded)
            self.assertIn(upgrade["slot"], loaded.ship.equipped_upgrades)


if __name__ == "__main__":
    unittest.main()
