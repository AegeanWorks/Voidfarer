"""Trade ledger: per-commodity cost basis, realised profit and max-quantity orders."""

import io
import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import http.client

from voidfarer.cli import cmd_repl
from voidfarer.engine import SimulationEngine
from voidfarer.models import ShipState
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _docked_engine(credits: int = 5000, cargo: dict | None = None) -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.orbit("sol_body_1")
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=credits, cargo=dict(cargo or {}), cargo_cost={}))
    return engine


class TestTradeCostBasis(unittest.TestCase):
    def test_buy_records_what_was_paid(self):
        engine = _docked_engine()
        before = engine.state.ship.credits
        ok, _ = engine.trade("fuel_cells", 4, is_buy=True)
        self.assertTrue(ok)
        paid = before - engine.state.ship.credits
        self.assertEqual(engine.state.ship.cargo_cost.get("fuel_cells"), paid)

    def test_sell_reports_profit_and_releases_cost_proportionally(self):
        engine = _docked_engine()
        engine.trade("fuel_cells", 4, is_buy=True)
        paid = engine.state.ship.cargo_cost["fuel_cells"]
        ok, msg = engine.trade("fuel_cells", 2, is_buy=False)
        self.assertTrue(ok)
        self.assertIn("P/L", msg)
        self.assertEqual(engine.state.ship.cargo_cost["fuel_cells"], paid - paid * 2 // 4)
        engine.trade("fuel_cells", 2, is_buy=False)
        self.assertNotIn("fuel_cells", engine.state.ship.cargo_cost)

    def test_stale_cost_is_reset_when_the_hold_was_emptied_elsewhere(self):
        engine = _docked_engine()
        engine.state = engine._clone_state(ship=engine._clone_ship(cargo={}, cargo_cost={"fuel_cells": 999}))
        before = engine.state.ship.credits
        engine.trade("fuel_cells", 1, is_buy=True)
        self.assertEqual(engine.state.ship.cargo_cost["fuel_cells"], before - engine.state.ship.credits)

    def test_jettison_releases_the_cost_basis_proportionally(self):
        engine = _docked_engine()
        engine.trade("fuel_cells", 4, is_buy=True)
        paid = engine.state.ship.cargo_cost["fuel_cells"]
        ok, _ = engine.jettison_cargo("fuel_cells", 2)
        self.assertTrue(ok)
        self.assertEqual(engine.state.ship.cargo_cost["fuel_cells"], paid * 2 // 4)
        engine.jettison_cargo("fuel_cells", 2)
        self.assertNotIn("fuel_cells", engine.state.ship.cargo_cost)

    def test_old_saves_load_with_an_empty_cost_basis(self):
        data = SimulationEngine(seed=42).state.ship.to_dict()
        data.pop("cargo_cost", None)
        self.assertEqual(ShipState.from_dict(data).cargo_cost, {})

    def test_cost_basis_round_trips(self):
        engine = _docked_engine()
        engine.trade("fuel_cells", 3, is_buy=True)
        restored = ShipState.from_dict(engine.state.ship.to_dict())
        self.assertEqual(restored.cargo_cost, engine.state.ship.cargo_cost)


class TestMaxOrders(unittest.TestCase):
    def test_max_buy_is_bounded_by_hold_volume(self):
        engine = _docked_engine(credits=1_000_000)
        qty = engine.max_trade_quantity("titanium", is_buy=True)
        self.assertEqual(qty, engine.state.ship.cargo_capacity // 2)
        ok, _ = engine.trade_max("titanium", is_buy=True)
        self.assertTrue(ok)
        self.assertEqual(engine.state.ship.cargo.get("titanium"), qty)

    def test_max_buy_is_bounded_by_credits(self):
        engine = _docked_engine(credits=300)
        qty = engine.max_trade_quantity("fuel_cells", is_buy=True)
        self.assertGreater(qty, 0)
        ok, _ = engine.trade_max("fuel_cells", is_buy=True)
        self.assertTrue(ok)
        self.assertGreaterEqual(engine.state.ship.credits, 0)
        self.assertFalse(engine.trade("fuel_cells", 1, is_buy=True)[0])

    def test_max_sell_sells_everything_held(self):
        engine = _docked_engine(cargo={"fuel_cells": 7})
        self.assertEqual(engine.max_trade_quantity("fuel_cells", is_buy=False), 7)
        ok, _ = engine.trade_max("fuel_cells", is_buy=False)
        self.assertTrue(ok)
        self.assertNotIn("fuel_cells", engine.state.ship.cargo)

    def test_max_with_nothing_possible_explains_why(self):
        engine = _docked_engine(credits=0)
        ok, msg = engine.trade_max("fuel_cells", is_buy=True)
        self.assertFalse(ok)
        self.assertIn("credits", msg.lower())

    def test_max_buy_names_the_hold_when_a_unit_does_not_fit(self):
        engine = _docked_engine(credits=100_000, cargo={"fuel_cells": 39})
        ok, msg = engine.trade_max("titanium", is_buy=True)
        self.assertFalse(ok)
        self.assertIn("volume", msg.lower())

    def test_snapshot_exposes_max_buy_and_average_cost(self):
        engine = _docked_engine()
        engine.trade("fuel_cells", 2, is_buy=True)
        snap = engine.get_status_snapshot()
        quote = next(q for q in snap["market_quotes"] if q["commodity_id"] == "fuel_cells")
        self.assertEqual(quote["max_buy"], engine.max_trade_quantity("fuel_cells", is_buy=True))
        self.assertEqual(snap["cargo_avg_cost"]["fuel_cells"], engine.state.ship.cargo_cost["fuel_cells"] // 2)


class TestMaxOrderParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = TemporaryDirectory()
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def setUp(self):
        self.storage = StorageManager(self.temp_dir.name)
        VoidFarerHandler.storage = self.storage

    def test_rest_trade_accepts_max_flag(self):
        VoidFarerHandler.engine = _docked_engine(cargo={"fuel_cells": 5})
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        body = json.dumps({"commodity_id": "fuel_cells", "is_buy": False, "max": True})
        conn.request("POST", "/api/trade", body=body, headers={"Content-Type": "application/json"})
        payload = json.loads(conn.getresponse().read())
        conn.close()
        self.assertTrue(payload["ok"], payload["message"])
        self.assertNotIn("fuel_cells", payload["state"]["ship"]["cargo"])

    def test_repl_sell_all(self):
        engine = _docked_engine(cargo={"fuel_cells": 3})
        with patch("builtins.input", side_effect=["sell fuel_cells all", "exit"]):
            with patch("sys.stdout", new_callable=io.StringIO) as out:
                cmd_repl(engine, self.storage)
        self.assertIn("Sold 3x", out.getvalue())
        self.assertNotIn("fuel_cells", engine.state.ship.cargo)


if __name__ == "__main__":
    unittest.main()
