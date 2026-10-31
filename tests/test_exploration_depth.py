"""Regression tests for exploration depth: survey completion, scan discipline, salvage contracts, and scoop reserves."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.codex import metric_value
from voidfarer.engine import SimulationEngine
from voidfarer.exploration import SCOOP_RECHARGE_TICKS, recharge_volatile_reserve, scoop_reserve
from voidfarer.models import CelestialBody
from voidfarer.storage import StorageManager


class TestScanDiscipline(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_zero_sensor_power_does_not_consume_a_scan(self):
        ok, msg = self.engine.route_power(40, 40, 0, 20)
        self.assertTrue(ok, msg)
        ok, msg = self.engine.orbit("sol_body_2")
        self.assertTrue(ok, msg)

        ok, msg, _info = self.engine.scan()
        self.assertFalse(ok)
        self.assertIn("sensor", msg.lower())
        self.assertFalse(self.engine.orbiting_body.scan_completed)

    def test_full_system_survey_awards_bonus_and_codex_progress(self):
        unscanned = [body for body in self.engine.current_system.bodies if not body.scan_completed]
        self.assertGreaterEqual(len(unscanned), 2)

        info = {}
        for body in unscanned:
            ok, msg = self.engine.orbit(body.id)
            self.assertTrue(ok, msg)
            ok, msg, info = self.engine.scan()
            self.assertTrue(ok, msg)

        self.assertTrue(info["survey_complete"])
        self.assertGreater(info["survey_bonus"], 0)
        self.assertEqual(self.engine.state.stats.get("systems_surveyed"), 1)
        self.assertEqual(metric_value(self.engine.state, "systems_surveyed"), 1)
        survey = self.engine.get_status_snapshot()["survey"]
        self.assertTrue(survey["complete"])
        self.assertEqual(survey["scanned"], survey["total"])
        self.assertTrue(any("SURVEY COMPLETE" in line for line in self.engine.state.ship.flight_log))


class TestSalvageContractSynergy(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_titanium_salvage_advances_mining_contract(self):
        ok, msg = self.engine.orbit("sol_body_2")
        self.assertTrue(ok, msg)
        contract = next(c for c in self.engine.state.ship.active_contracts if c.category == "mining")
        before = contract.current_count

        with patch.object(self.engine.rng, "random", return_value=1.0):
            ok, msg, report = self.engine.salvage_derelict()
        self.assertTrue(ok, msg)
        self.assertEqual(report["cargo_item"], "titanium")
        self.assertGreater(report["cargo_quantity"], 0)

        updated = next(c for c in self.engine.state.ship.active_contracts if c.id == contract.id)
        self.assertEqual(
            updated.current_count,
            min(updated.target_count, before + report["cargo_quantity"]),
        )


class TestVolatileReserve(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _star(self):
        return next(body for body in self.engine.current_system.bodies if body.body_type == "star")

    def test_reserve_is_deterministic_and_type_limited(self):
        star = self._star()
        self.assertEqual(scoop_reserve(star), scoop_reserve(star))
        self.assertGreaterEqual(scoop_reserve(star), 6)
        station = next(body for body in self.engine.current_system.bodies if body.body_type == "orbital_station")
        self.assertEqual(scoop_reserve(station), 0)

    def test_legacy_body_defaults_to_untapped(self):
        payload = self._star().to_dict()
        payload.pop("volatile_tapped", None)
        payload.pop("volatile_recharge_tick", None)
        body = CelestialBody.from_dict(payload)
        self.assertEqual(body.volatile_tapped, 0)
        self.assertEqual(body.volatile_recharge_tick, 0)

    def test_negative_volatile_counters_are_clamped_on_load(self):
        payload = self._star().to_dict()
        payload["volatile_tapped"] = -4
        payload["volatile_recharge_tick"] = -9
        body = CelestialBody.from_dict(payload)
        self.assertEqual(body.volatile_tapped, 0)
        self.assertEqual(body.volatile_recharge_tick, 0)

    def test_far_future_recharge_tick_is_capped_to_one_interval(self):
        self.assertEqual(
            recharge_volatile_reserve(2, 9999, 10),
            (2, 10 + SCOOP_RECHARGE_TICKS),
        )

    def test_recharge_schedule_is_exact_and_not_boundary_aligned(self):
        ok, msg = self.engine.orbit("sol_star")
        self.assertTrue(ok, msg)
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(fuel=0, max_fuel=1000)
            )
        ok, msg = self.engine.scoop_fuel()
        self.assertTrue(ok, msg)
        tapped = self.engine.orbiting_body.volatile_tapped
        recharge_tick = self.engine.orbiting_body.volatile_recharge_tick
        self.assertEqual(tapped, 1)
        self.assertEqual(recharge_tick, self.engine.state.time.tick + SCOOP_RECHARGE_TICKS)
        self.assertEqual(self.engine.get_status_snapshot()["scoop"]["next_tap_in"], SCOOP_RECHARGE_TICKS)

        self.engine.tick(1)
        self.assertEqual(self.engine.orbiting_body.volatile_tapped, 1)
        self.engine.tick(SCOOP_RECHARGE_TICKS - 2)
        self.assertEqual(self.engine.orbiting_body.volatile_tapped, 1)
        self.engine.tick(1)
        self.assertEqual(self.engine.orbiting_body.volatile_tapped, 0)
        self.assertEqual(self.engine.orbiting_body.volatile_recharge_tick, 0)

    def test_large_tick_jump_recharges_multiple_pending_taps(self):
        ok, msg = self.engine.orbit("sol_star")
        self.assertTrue(ok, msg)
        tick = self.engine.state.time.tick
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                systems=self.engine._replace_system_body(
                    "sol_star",
                    volatile_tapped=3,
                    volatile_recharge_tick=tick + SCOOP_RECHARGE_TICKS,
                )
            )
        self.engine.tick(SCOOP_RECHARGE_TICKS * 3)
        body = next(b for b in self.engine.current_system.bodies if b.id == "sol_star")
        self.assertEqual(body.volatile_tapped, 0)
        self.assertEqual(body.volatile_recharge_tick, 0)

    def test_scoop_depletes_reservoir_then_recharges(self):
        ok, msg = self.engine.orbit("sol_star")
        self.assertTrue(ok, msg)
        reserve = scoop_reserve(self.engine.orbiting_body)
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(fuel=0, max_fuel=1000)
            )

        for _ in range(reserve):
            ok, msg = self.engine.scoop_fuel()
            self.assertTrue(ok, msg)
        self.assertEqual(self.engine.orbiting_body.volatile_tapped, reserve)

        ok, msg = self.engine.scoop_fuel()
        self.assertFalse(ok)
        self.assertIn("depleted", msg.lower())

        self.engine.tick(SCOOP_RECHARGE_TICKS)
        self.assertLess(self.engine.orbiting_body.volatile_tapped, reserve)
        ok, msg = self.engine.scoop_fuel()
        self.assertTrue(ok, msg)

    def test_snapshot_exposes_reserve_and_depletion(self):
        ok, msg = self.engine.orbit("sol_star")
        self.assertTrue(ok, msg)
        with self.engine.lock:
            body = self.engine.orbiting_body
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(fuel=0, max_fuel=1000)
            )
        scoop = self.engine.get_status_snapshot()["scoop"]
        self.assertIsNotNone(scoop)
        self.assertIn("tapped", scoop)
        self.assertIn("reserve", scoop)
        self.assertTrue(scoop["available"])

        reserve = scoop_reserve(body)
        for _ in range(reserve):
            ok, _msg = self.engine.scoop_fuel()
            self.assertTrue(ok)
        scoop = self.engine.get_status_snapshot()["scoop"]
        self.assertFalse(scoop["available"])
        self.assertEqual(scoop["tapped"], reserve)

        app_js = (Path(__file__).parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("RESERVOIR DEPLETED", app_js)
        self.assertIn("next_tap_in", app_js)
        self.assertIn("SURVEY ${survey.scanned}", app_js)


if __name__ == "__main__":
    unittest.main()
