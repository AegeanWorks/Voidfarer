"""Emergency fuel-cell burn: hold fuel cells refill the tank through every surface."""

from __future__ import annotations

import contextlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.cli import main
from voidfarer.engine import SimulationEngine
from voidfarer.engineering import ENGINEERING_ACTIONS, engineering_action, engineering_report
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"


def _engine(fuel: int = 10, cells: int = 5) -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    cargo = {"fuel_cells": cells} if cells else {}
    engine.state = engine._clone_state(ship=engine._clone_ship(fuel=fuel, cargo=cargo))
    return engine


class TestBurnFuelCells(unittest.TestCase):
    def test_one_cell_yields_four_fuel_and_leaves_the_rest(self) -> None:
        engine = _engine(fuel=10, cells=5)
        ok, message = engine.burn_fuel_cells(1)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fuel, 14)
        self.assertEqual(engine.state.ship.cargo["fuel_cells"], 4)
        self.assertIn("+4 Fuel", message)

    def test_burn_is_capped_by_free_tank_space_and_never_wastes_cells(self) -> None:
        engine = _engine(fuel=58, cells=5)  # max_fuel 60: needs 2 fuel, so exactly one cell
        ok, message = engine.burn_fuel_cells(5)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fuel, engine.state.ship.max_fuel)
        self.assertEqual(engine.state.ship.cargo["fuel_cells"], 4)

    def test_last_cell_removes_the_cargo_entry(self) -> None:
        engine = _engine(fuel=10, cells=1)
        ok, _ = engine.burn_fuel_cells(1)
        self.assertTrue(ok)
        self.assertNotIn("fuel_cells", engine.state.ship.cargo)

    def test_guards_refuse_without_changing_state(self) -> None:
        for fuel, cells, quantity, needle in (
            (10, 0, 1, "No Quantum Fuel Cells"),
            (60, 3, 1, "already at maximum"),
            (10, 3, 0, "positive integer"),
            (10, 3, True, "positive integer"),
        ):
            engine = _engine(fuel=fuel, cells=cells)
            before = engine.state.ship
            ok, message = engine.burn_fuel_cells(quantity)
            self.assertFalse(ok)
            self.assertIn(needle, message)
            self.assertEqual(engine.state.ship.fuel, before.fuel)
            self.assertEqual(engine.state.ship.cargo, before.cargo)

    def test_burn_works_mid_encounter_like_field_fabrication(self) -> None:
        engine = _engine(fuel=5, cells=2)
        with patch.object(SimulationEngine, "_action_lock_reason", return_value="locked"):
            ok, _ = engine.burn_fuel_cells(1)
        self.assertTrue(ok)


class TestEngineeringSurface(unittest.TestCase):
    def test_action_is_listed_and_routes_quantity(self) -> None:
        self.assertIn("burn_cells", ENGINEERING_ACTIONS)
        engine = _engine(fuel=10, cells=5)
        ok, message = engineering_action(engine, "burn_cells", quantity="2")
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fuel, 18)

    def test_report_exposes_cells_and_burnability(self) -> None:
        report = engineering_report(_engine(fuel=10, cells=5))["fabrication"]
        self.assertEqual(report["fuel_cells"], 5)
        self.assertTrue(report["can_burn_cells"])
        report = engineering_report(_engine(fuel=60, cells=5))["fabrication"]
        self.assertFalse(report["can_burn_cells"])


class TestCliAndRest(unittest.TestCase):
    def test_cli_engineering_burn_cells_saves(self) -> None:
        engine = _engine(fuel=10, cells=5)
        with tempfile.TemporaryDirectory() as save_dir:
            storage = StorageManager(save_dir)
            storage.save(engine.state)
            with patch("voidfarer.cli.StorageManager", return_value=storage), \
                    patch("sys.stdout", new_callable=io.StringIO) as out:
                self.assertEqual(main(["engineering", "burn_cells", "2"]), 0)
            self.assertIn("+8 Fuel", out.getvalue())
            self.assertEqual(storage.load().ship.fuel, 18)

    def test_rest_engineering_action_burns_cells(self) -> None:
        engine = _engine(fuel=10, cells=5)
        with tempfile.TemporaryDirectory() as save_dir:
            VoidFarerHandler.engine = engine
            VoidFarerHandler.storage = StorageManager(save_dir)
            VoidFarerHandler.static_dir = STATIC
            server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                conn.request("POST", "/api/engineering/action",
                             json.dumps({"action": "burn_cells", "quantity": 1}),
                             {"Content-Type": "application/json"})
                payload = json.loads(conn.getresponse().read())
                conn.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2.0)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(engine.state.ship.fuel, 14)


if __name__ == "__main__":
    unittest.main()
