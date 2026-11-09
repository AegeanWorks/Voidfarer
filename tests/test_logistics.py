"""Unified logistics report/action, REST and CLI tests."""

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
from voidfarer.logistics import logistics_action, logistics_report, logistics_summary
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=50000))
    return engine


class TestLogisticsReport(unittest.TestCase):
    def test_report_has_market_cargo_depot_and_automation(self):
        report = logistics_report(_engine())
        self.assertGreater(report["counts"]["market_lines"], 0)
        self.assertIn("hold", report["cargo"])
        self.assertIn("manifest", report["cargo"])
        self.assertIsNotNone(report["depot"])
        self.assertIn("trade", report["automation"])
        self.assertIn("quantum", report["automation"])
        self.assertIn("orders", report["freight"])

    def test_summary_is_compact(self):
        summary = logistics_summary(_engine().state)
        self.assertIn("cargo_volume", summary)
        self.assertIn("trade_automation", summary)
        self.assertIn("freight_orders", summary)
        self.assertNotIn("market", summary)

    def test_snapshot_carries_logistics_summary(self):
        snapshot = _engine().get_status_snapshot(include_static=False)
        self.assertIn("logistics", snapshot)
        self.assertIn("cargo_capacity", snapshot["logistics"])


class TestLogisticsActions(unittest.TestCase):
    def test_buy_sell_deposit_and_withdraw(self):
        engine = _engine()
        ok, message = logistics_action(
            engine, "buy", commodity_id="titanium", quantity=1
        )
        self.assertTrue(ok, message)
        self.assertGreaterEqual(engine.state.ship.cargo.get("titanium", 0), 1)
        ok, message = logistics_action(
            engine, "deposit", item_id="titanium", quantity=1
        )
        self.assertTrue(ok, message)
        depot = next(d for d in engine.state.depots if d.system_id == "sol")
        self.assertGreaterEqual(depot.cargo.get("titanium", 0), 1)
        ok, message = logistics_action(
            engine, "withdraw", item_id="titanium", quantity=1
        )
        self.assertTrue(ok, message)
        depot = next(d for d in engine.state.depots if d.system_id == "sol")
        self.assertEqual(depot.cargo.get("titanium", 0), 0)
        ok, message = logistics_action(
            engine, "sell", commodity_id="titanium", quantity=1
        )
        self.assertTrue(ok, message)

    def test_trade_and_quantum_automation_toggle(self):
        engine = _engine()
        ok, message = logistics_action(
            engine, "automation_on",
            commodity_id="titanium", buy_below=40, sell_above=999, quantity=1,
        )
        self.assertTrue(ok, message)
        self.assertTrue(engine.state.trade_automation.enabled)
        ok, message = logistics_action(engine, "automation_off")
        self.assertTrue(ok, message)
        self.assertFalse(engine.state.trade_automation.enabled)

        ok, message = logistics_action(engine, "quantum_automation_on", min_net=120)
        self.assertTrue(ok, message)
        self.assertTrue(engine.state.quantum_automation.enabled)
        ok, message = logistics_action(engine, "quantum_automation_off")
        self.assertTrue(ok, message)
        self.assertFalse(engine.state.quantum_automation.enabled)

    def test_quantum_freight_order(self):
        engine = _engine()
        ok, message = logistics_action(
            engine, "buy", commodity_id="titanium", quantity=2
        )
        self.assertTrue(ok, message)
        ok, message = logistics_action(
            engine, "quantum_order",
            commodity_id="titanium", quantity=1, destination_system_id="altair",
        )
        self.assertTrue(ok, message)
        self.assertEqual(len(engine.state.ship.trade_orders), 1)

    def test_invalid_action_is_rejected(self):
        ok, message = logistics_action(_engine(), "teleport")
        self.assertFalse(ok)
        self.assertIn("Unknown logistics action", message)


class TestLogisticsSurfaces(unittest.TestCase):
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
        status, payload = self._get("/api/logistics")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertGreater(payload["counts"]["market_lines"], 0)
        self.assertIn("depot", payload)

    def test_action_endpoint_buys_cargo(self):
        status, payload = self._post(
            "/api/logistics/action",
            {"action": "buy", "commodity_id": "titanium", "quantity": 1},
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertGreaterEqual(self.engine.state.ship.cargo.get("titanium", 0), 1)

    def test_cli_status_and_buy(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "logistics"])
            self.assertEqual(code, 0)
            self.assertIn("LOGISTICS", buffer.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "logistics", "market"])
            self.assertEqual(code, 0)

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main([
                    "--save-path", temp, "logistics", "buy", "titanium", "1",
                ])
            self.assertEqual(code, 0)
            loaded = StorageManager(temp).load()
            self.assertIsNotNone(loaded)
            self.assertGreaterEqual(loaded.ship.cargo.get("titanium", 0), 1)

    def test_hidden_trade_verbs_still_trade(self):
        with tempfile.TemporaryDirectory() as temp:
            StorageManager(temp).save(self.engine.state)
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "buy", "titanium", "1"])
            self.assertEqual(code, 0)
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "sell", "titanium", "1"])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
