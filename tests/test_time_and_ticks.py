"""Comprehensive automated test suite for Time, Ticks, and Temporal Controls in VoidFarer."""

import http.client
import json
import math
import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.engine import SimulationEngine
from voidfarer.models import FleetDrone, GameState, TimeState
from voidfarer.server import BASE_TICK_SECONDS, MIN_TICK_SECONDS, ThreadedHTTPServer, VoidFarerHandler, tick_interval
from voidfarer.storage import StorageManager


class TestTimeStateModel(unittest.TestCase):
    """Verify TimeState dataclass serialization, defaults, and legacy migration."""

    def test_default_values(self):
        t = TimeState()
        self.assertEqual(t.tick, 0)
        self.assertEqual(t.stardate, 3042.0)
        self.assertEqual(t.speed, 1.0)
        self.assertFalse(t.is_paused)
        self.assertEqual(t.time_scale, "1x")
        self.assertEqual(t.elapsed_days, 0.0)

    def test_to_dict_and_from_dict(self):
        t1 = TimeState(
            tick=42,
            stardate=3042.42,
            speed=5.0,
            is_paused=True,
            time_scale="5x",
            elapsed_days=4.2,
        )
        d = t1.to_dict()
        t2 = TimeState.from_dict(d)
        self.assertEqual(t1, t2)

    def test_tick_interval_scales_with_chrono_speed(self):
        self.assertEqual(BASE_TICK_SECONDS, 0.5)
        self.assertEqual(tick_interval(1.0), 0.5)
        self.assertEqual(tick_interval(2.0), 0.25)
        self.assertEqual(tick_interval(10.0), 0.05)
        self.assertGreaterEqual(tick_interval(0.1), MIN_TICK_SECONDS)

    def test_gamestate_backward_compatibility(self):
        engine = SimulationEngine(seed=42)
        state_dict = engine.state.to_dict()
        # Remove 'time' key to simulate a legacy save file
        if "time" in state_dict:
            del state_dict["time"]
        restored = GameState.from_dict(state_dict)
        self.assertIsInstance(restored.time, TimeState)
        self.assertEqual(restored.time.tick, 0)
        self.assertEqual(restored.time.stardate, 3042.0)


class TestSimulationEngineTimeAndTicks(unittest.TestCase):
    """Verify time progression, orbital dynamics, shield regen, and drone harvests."""

    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_single_tick(self):
        initial_stardate = self.engine.state.time.stardate
        initial_tick = self.engine.state.time.tick
        self.engine.tick(1)
        self.assertEqual(self.engine.state.time.tick, initial_tick + 1)
        self.assertGreater(self.engine.state.time.stardate, initial_stardate)
        self.assertAlmostEqual(self.engine.state.time.elapsed_days, 0.25, places=2)

    def test_multi_tick(self):
        self.engine.tick(10)
        self.assertEqual(self.engine.state.time.tick, 10)
        self.assertAlmostEqual(self.engine.state.time.elapsed_days, 2.5, places=2)
        expected_stardate = 3042.0 + (2.5 / 365.25)
        self.assertAlmostEqual(self.engine.state.time.stardate, expected_stardate, places=3)

    def test_orbital_angle_progression(self):
        cur_sys = self.engine.current_system
        moving_bodies = [b for b in cur_sys.bodies if b.orbit_speed > 0]
        self.assertTrue(len(moving_bodies) > 0)
        initial_angles = [b.current_angle for b in moving_bodies]

        self.engine.tick(5)

        updated_sys = self.engine.current_system
        updated_bodies = [b for b in updated_sys.bodies if b.orbit_speed > 0]
        for init_angle, body in zip(initial_angles, updated_bodies):
            d_angle = body.orbit_speed * 0.05 * 5
            expected = (init_angle + d_angle) % (2.0 * math.pi)
            self.assertAlmostEqual(body.current_angle, expected, places=3)

    def test_passive_shield_recharge(self):
        # Damage shield on ship
        self.engine.state = GameState(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=self.engine._clone_ship(shield=20),
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=None,
            active_combat=None,
            time=self.engine.state.time,
            stats=self.engine.state.stats,
        )
        max_shield = self.engine.state.ship.max_shield
        self.assertTrue(self.engine.state.ship.shield < max_shield)

        # 1 tick recharges shield
        self.engine.tick(1)
        self.assertGreater(self.engine.state.ship.shield, 20)

        # Multiple ticks recharge toward ceiling
        self.engine.tick(100)
        self.assertEqual(self.engine.state.ship.shield, max_shield)

    def test_fleet_drone_harvest_accumulation(self):
        drone = FleetDrone(
            id="drone-test-1",
            name="Alpha Extractor",
            drone_type="mining",
            assigned_system_id="sol",
            status="harvesting",
            cargo_accumulated=0,
            credits_accumulated=0,
        )
        self.engine.state = GameState(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=self.engine._clone_ship(fleet_drones=(drone,)),
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=None,
            active_combat=None,
            time=self.engine.state.time,
            stats=self.engine.state.stats,
        )

        self.engine.tick(4)
        updated_drone = self.engine.state.ship.fleet_drones[-1]
        self.assertGreater(updated_drone.cargo_accumulated, 0)

    def test_time_control_pause_resume(self):
        self.assertFalse(self.engine.state.time.is_paused)
        ok, msg = self.engine.pause_time()
        self.assertTrue(ok)
        self.assertTrue(self.engine.state.time.is_paused)

        ok, msg = self.engine.resume_time()
        self.assertTrue(ok)
        self.assertFalse(self.engine.state.time.is_paused)

    def test_time_speed_settings(self):
        ok, msg = self.engine.set_time_speed(5.0)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.time.speed, 5.0)

        # Clamping checks
        ok, msg = self.engine.set_time_speed(0.0)
        self.assertTrue(ok)
        self.assertTrue(self.engine.state.time.is_paused)

    def test_step_time(self):
        initial_tick = self.engine.state.time.tick
        ok, msg, summary = self.engine.step_time(3)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.time.tick, initial_tick + 3)
        self.assertEqual(summary["ticks_advanced"], 3)
        self.assertEqual(summary["date"], self.engine.state.time.current_date)

    def test_status_snapshot_contains_time(self):
        snapshot = self.engine.get_status_snapshot()
        self.assertIn("time", snapshot)
        time_data = snapshot["time"]
        self.assertEqual(time_data["tick"], self.engine.state.time.tick)
        self.assertEqual(time_data["stardate"], round(self.engine.state.time.stardate, 2))
        self.assertEqual(time_data["date"], self.engine.state.time.current_date)
        self.assertEqual(time_data["speed"], self.engine.state.time.speed)
        self.assertEqual(time_data["is_paused"], self.engine.state.time.is_paused)

    def test_pause_resume_speed_memory(self):
        """Verify speed rate (e.g. 5x) is retained across pause and resume cycles."""
        ok, _ = self.engine.set_time_speed(5.0)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.time.speed, 5.0)
        self.assertEqual(self.engine.state.time.time_scale, "5x")
        self.assertFalse(self.engine.state.time.is_paused)

        ok, _ = self.engine.pause_time()
        self.assertTrue(ok)
        self.assertTrue(self.engine.state.time.is_paused)
        self.assertEqual(self.engine.state.time.time_scale, "PAUSED")
        self.assertEqual(self.engine.state.time.speed, 5.0)

        ok, _ = self.engine.resume_time()
        self.assertTrue(ok)
        self.assertFalse(self.engine.state.time.is_paused)
        self.assertEqual(self.engine.state.time.speed, 5.0)
        self.assertEqual(self.engine.state.time.time_scale, "5x")

    def test_jump_advances_transit_time(self):
        """Verify interstellar hyperspace jumps advance cosmic time and orbits by 2 ticks (12 hours)."""
        initial_tick = self.engine.state.time.tick
        initial_days = self.engine.state.time.elapsed_days
        initial_stardate = self.engine.state.time.stardate

        # Jump from sol to sirius
        ok, msg = self.engine.jump("sirius")
        self.assertTrue(ok, msg)
        self.assertEqual(self.engine.state.time.tick, initial_tick + 2)
        self.assertAlmostEqual(self.engine.state.time.elapsed_days, initial_days + 0.5, places=2)
        self.assertGreater(self.engine.state.time.stardate, initial_stardate)

    def test_state_preservation_across_operations(self):
        """Verify operations like orbit, scan, and power routing never wipe temporal clock state."""
        self.engine.tick(7)
        self.assertEqual(self.engine.state.time.tick, 7)
        saved_stardate = self.engine.state.time.stardate
        saved_days = self.engine.state.time.elapsed_days

        # Perform orbit
        first_body_id = "sol_body_1"
        ok, _ = self.engine.orbit(first_body_id)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.time.tick, 7)
        self.assertEqual(self.engine.state.time.stardate, saved_stardate)
        self.assertEqual(self.engine.state.time.elapsed_days, saved_days)

        # Perform scan
        ok, _, _ = self.engine.scan()
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.time.tick, 7)
        self.assertEqual(self.engine.state.time.stardate, saved_stardate)

        # Perform power route
        ok, _ = self.engine.route_power(30, 30, 20, 20)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.time.tick, 7)
        self.assertEqual(self.engine.state.time.stardate, saved_stardate)


class TestServerTimeEndpoints(unittest.TestCase):
    """Verify REST API time endpoints: /api/time, /api/time/step, /api/time/speed, etc."""

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
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def _get(self, path: str):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, data

    def _post(self, path: str, body: dict):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        payload = json.dumps(body)
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, data

    def test_get_api_time(self):
        status, data = self._get("/api/time")
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertTrue(parsed["ok"])
        self.assertIn("time", parsed)
        self.assertEqual(parsed["time"]["speed"], 1.0)

    def test_post_api_time_step(self):
        initial_tick = self.engine.state.time.tick
        status, data = self._post("/api/time/step", {"ticks": 4})
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["state"]["time"]["tick"], initial_tick + 4)

    def test_post_api_time_speed(self):
        status, data = self._post("/api/time/speed", {"speed": 2.0})
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["state"]["time"]["speed"], 2.0)

    def test_post_api_time_pause_and_resume(self):
        status, data = self._post("/api/time/pause", {})
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertTrue(parsed["ok"])
        self.assertTrue(parsed["state"]["time"]["is_paused"])

        status, data = self._post("/api/time/resume", {})
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertTrue(parsed["ok"])
        self.assertFalse(parsed["state"]["time"]["is_paused"])


if __name__ == "__main__":
    unittest.main()
