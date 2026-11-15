"""REFIT DAMAGED refits every worn drone, worst first, as far as credits stretch."""

import unittest
from dataclasses import replace

from voidfarer.engine import SimulationEngine
from voidfarer.fleet_command import FLEET_ACTIONS, fleet_action
from voidfarer.models import FleetDrone


def _drone(i, integrity):
    return FleetDrone(id=f"d{i}", name=f"Drone {i}", drone_type="mining", assigned_system_id="sol", integrity=integrity)


def _engine(credits, *integrities):
    engine = SimulationEngine(seed=42)
    drones = tuple(_drone(i, v) for i, v in enumerate(integrities, start=1))
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=credits, fleet_drones=drones))
    return engine


class RefitDamagedDronesTest(unittest.TestCase):
    def test_refits_only_worn_drones_and_charges_each(self):
        engine = _engine(2000, 20, 90, 35)
        ok, message = engine.refit_damaged_drones()
        self.assertTrue(ok, message)
        by_id = {d.id: d for d in engine.state.ship.fleet_drones}
        self.assertEqual(by_id["d1"].integrity, 100)
        self.assertEqual(by_id["d3"].integrity, 100)
        self.assertEqual(by_id["d2"].integrity, 90)
        self.assertEqual(engine.state.ship.credits, 2000 - 600)
        self.assertIn("2 drones", message)

    def test_worst_first_when_credits_run_short(self):
        engine = _engine(350, 35, 10)
        ok, message = engine.refit_damaged_drones()
        self.assertTrue(ok, message)
        by_id = {d.id: d.integrity for d in engine.state.ship.fleet_drones}
        self.assertEqual(by_id["d2"], 100)
        self.assertEqual(by_id["d1"], 35)
        self.assertIn("short", message.lower())

    def test_nothing_worn_or_nothing_affordable_changes_nothing(self):
        healthy = _engine(2000, 100, 80)
        before = healthy.state
        ok, message = healthy.refit_damaged_drones()
        self.assertFalse(ok)
        self.assertEqual(healthy.state, before)
        poor = _engine(100, 10)
        self.assertFalse(poor.refit_damaged_drones()[0])
        self.assertEqual(poor.state.ship.fleet_drones[0].integrity, 10)

    def test_it_is_reachable_as_a_fleet_action(self):
        self.assertIn("refit_damaged", FLEET_ACTIONS)
        ok, _ = fleet_action(_engine(2000, 10), "refit_damaged")
        self.assertTrue(ok)


class RefitDamagedCliTest(unittest.TestCase):
    def test_fleet_refit_damaged_refits_and_persists(self):
        import contextlib
        import io
        import tempfile
        from pathlib import Path

        from voidfarer.cli import cmd_fleet
        from voidfarer.storage import StorageManager

        engine = _engine(2000, 10)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        storage = StorageManager(Path(tmp.name))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = cmd_fleet(engine, storage, ["fleet", "refit_damaged"])
        self.assertEqual(code, 0)
        self.assertIn("FLEET REFIT", out.getvalue())
        self.assertEqual(storage.load().ship.fleet_drones[0].integrity, 100)


if __name__ == "__main__":
    unittest.main()
