"""Unit and integration tests for the Hollow Between void traversal mechanics."""

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.cli import cmd_status, cmd_void, main
from voidfarer.engine import SimulationEngine
from voidfarer.models import GameState, ShipState, VoidTraversalState
from voidfarer.navigation import (
    generate_void_lanes,
    shortest_route,
    void_anchor_systems,
    void_route_plan,
    void_shortest_route,
)
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


class TestVoidLanes(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_anchors_are_black_hole_systems(self):
        self.assertEqual(void_anchor_systems(self.engine.state.systems), ["cygnus_x1", "golconda"])

    def test_lane_determinism_per_seed(self):
        systems = self.engine.state.systems
        self.assertEqual(generate_void_lanes(systems, 42), generate_void_lanes(systems, 42))
        self.assertNotEqual(generate_void_lanes(systems, 42), generate_void_lanes(systems, 7))

    def test_anchor_mesh_connectivity(self):
        lanes = generate_void_lanes(self.engine.state.systems, 42)
        self.assertIn("golconda", lanes["cygnus_x1"])
        self.assertIn("cygnus_x1", lanes["golconda"])

    def test_void_route_plan_metrics(self):
        plan = void_route_plan(self.engine.state.systems, 42, "cygnus_x1", "golconda")
        self.assertTrue(plan["reachable"])
        self.assertEqual(plan["path"], ["cygnus_x1", "golconda"])
        self.assertEqual(plan["lanes"], 1)
        self.assertGreater(plan["fuel_estimate"], 0)
        self.assertGreaterEqual(plan["duration_ticks"], 3)
        self.assertLessEqual(plan["duration_ticks"], 8)

        unreachable = void_route_plan(self.engine.state.systems, 42, "sol", "vega")
        if "sol" not in generate_void_lanes(self.engine.state.systems, 42):
            self.assertFalse(unreachable["reachable"])

    def test_void_shortest_route_symmetry(self):
        lanes = generate_void_lanes(self.engine.state.systems, 42)
        for start in lanes:
            for target in lanes:
                if start == target:
                    continue
                forward = void_shortest_route(lanes, start, target)
                self.assertTrue(forward, f"no route {start} -> {target}")
                self.assertEqual(forward[0], start)
                self.assertEqual(forward[-1], target)


class TestVoidTraversalState(unittest.TestCase):
    def test_roundtrip_and_progress(self):
        vt = VoidTraversalState(
            origin_system_id="cygnus_x1",
            destination_system_id="golconda",
            started_tick=10,
            arrival_tick=15,
            duration_ticks=5,
            stability=88.0,
            storms_weathered=2,
        )
        restored = VoidTraversalState.from_dict(vt.to_dict())
        self.assertEqual(restored, vt)
        self.assertAlmostEqual(restored.progress(10), 0.0)
        self.assertAlmostEqual(restored.progress(12), 0.4)
        self.assertAlmostEqual(restored.progress(99), 1.0)

    def test_ship_state_serialization(self):
        engine = SimulationEngine(seed=42)
        self.assertIsNone(ShipState.from_dict(engine.state.ship.to_dict()).void_traversal)

        vt = VoidTraversalState(
            origin_system_id="cygnus_x1",
            destination_system_id="golconda",
            started_tick=0,
            arrival_tick=4,
            duration_ticks=4,
        )
        engine.state = engine._clone_state(ship=engine._clone_ship(void_traversal=vt))
        restored = ShipState.from_dict(engine.state.ship.to_dict())
        self.assertEqual(restored.void_traversal, vt)

        restored_game = GameState.from_dict(engine.state.to_dict())
        self.assertEqual(restored_game.ship.void_traversal, vt)


class TestVoidDiveAndTraversal(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _goto_cygnus_horizon(self):
        path = shortest_route(self.engine.state.systems, "sol", "cygnus_x1")
        for target in path[1:]:
            with self.engine.lock:
                self.engine.state = self.engine._clone_state(
                    ship=self.engine._clone_ship(fuel=80),
                    active_anomaly=None,
                    active_combat=None,
                )
            ok, msg = self.engine.jump(target)
            self.assertTrue(ok, msg)
        ok, msg = self.engine.orbit("cygnus_x1_black_hole")
        self.assertTrue(ok, msg)
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(active_anomaly=None, active_combat=None)

    def test_dive_requires_black_hole_orbit(self):
        status = self.engine.void_status()
        self.assertFalse(status["dive_ready"])
        self.assertTrue(any("event horizon" in b for b in status["blockers"]))

        ok, msg = self.engine.void_dive("golconda")
        self.assertFalse(ok)
        self.assertIn("event horizon", msg)

    def test_dive_validation_errors(self):
        self._goto_cygnus_horizon()
        ok, msg = self.engine.void_dive("sol")
        self.assertFalse(ok)
        self.assertIn("No void lane", msg)

        ok, msg = self.engine.void_dive("nonexistent_system")
        self.assertFalse(ok)
        self.assertIn("Unknown system", msg)

        with self.engine.lock:
            self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(fuel=1))
        ok, msg = self.engine.void_dive("golconda")
        self.assertFalse(ok)
        self.assertIn("Insufficient Quantum Fuel", msg)

        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(fuel=80, shield=5, max_shield=100)
            )
        ok, msg = self.engine.void_dive("golconda")
        self.assertFalse(ok)
        self.assertIn("shields", msg)

    def test_dive_initializes_traversal(self):
        self._goto_cygnus_horizon()
        ok, msg = self.engine.void_dive("golconda")
        self.assertTrue(ok, msg)

        traversal = self.engine.state.ship.void_traversal
        self.assertIsNotNone(traversal)
        self.assertEqual(traversal.origin_system_id, "cygnus_x1")
        self.assertEqual(traversal.destination_system_id, "golconda")
        self.assertEqual(traversal.arrival_tick - traversal.started_tick, traversal.duration_ticks)
        self.assertGreaterEqual(traversal.stability, 100.0)
        self.assertIsNone(self.engine.state.ship.orbiting_body_id)
        self.assertEqual(self.engine.state.stats.get("void_dives"), 1)

        ok, msg = self.engine.void_dive("golconda")
        self.assertFalse(ok)
        self.assertIn("Already traversing", msg)

    def test_relic_grants_starting_stability(self):
        self._goto_cygnus_horizon()
        from voidfarer.story import STORY_RELICS

        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(relics=(STORY_RELICS["relic_void_compass"],))
            )
        ok, msg = self.engine.void_dive("golconda")
        self.assertTrue(ok, msg)
        self.assertAlmostEqual(self.engine.state.ship.void_traversal.stability, 120.0)

    def test_emergency_emergence_restores_horizon_orbit(self):
        self._goto_cygnus_horizon()
        self.engine.void_dive("golconda")

        ok, msg = self.engine.void_emerge()
        self.assertTrue(ok)
        self.assertIsNone(self.engine.state.ship.void_traversal)
        self.assertEqual(self.engine.state.ship.current_system_id, "cygnus_x1")
        self.assertEqual(self.engine.state.ship.orbiting_body_id, "cygnus_x1_black_hole")
        self.assertLess(self.engine.state.ship.shield, 100)

        ok, msg = self.engine.void_emerge()
        self.assertFalse(ok)
        self.assertIn("Not currently traversing", msg)

    def test_tick_advances_to_arrival(self):
        self._goto_cygnus_horizon()
        self.engine.void_dive("golconda")
        traversal = self.engine.state.ship.void_traversal

        xp_before = self.engine.state.ship.mastery.xp
        for _ in range(traversal.duration_ticks + 1):
            self.engine.tick(1)

        self.assertIsNone(self.engine.state.ship.void_traversal)
        self.assertEqual(self.engine.state.ship.current_system_id, "golconda")
        self.assertEqual(self.engine.state.stats.get("void_arrivals"), 1)
        self.assertIn("golconda", set(self.engine.state.visited_systems))
        self.assertGreater(self.engine.state.ship.mastery.xp, xp_before)
        self.assertTrue(any("VOID ARRIVAL" in line for line in self.engine.state.ship.flight_log))

    def test_first_visit_cartography_bounty(self):
        self._goto_cygnus_horizon()
        # golconda must be unvisited for the first-visit bonus
        self.assertNotIn("golconda", set(self.engine.state.visited_systems))
        self.engine.void_dive("golconda")
        traversal = self.engine.state.ship.void_traversal
        for _ in range(traversal.duration_ticks + 1):
            self.engine.tick(1)
        self.assertTrue(
            any("Cartography bounty +400" in line for line in self.engine.state.ship.flight_log)
        )

    def test_storms_damage_and_are_recorded(self):
        self._goto_cygnus_horizon()
        self.engine.void_dive("golconda")
        traversal = self.engine.state.ship.void_traversal
        shield_before = self.engine.state.ship.shield

        with patch.object(self.engine.rng, "random", return_value=0.0):
            self.engine.tick(1)

        updated = self.engine.state.ship.void_traversal
        self.assertIsNotNone(updated)
        self.assertGreaterEqual(updated.storms_weathered, 1)
        self.assertLess(updated.stability, traversal.stability)
        self.assertLessEqual(self.engine.state.ship.shield, shield_before)
        self.assertTrue(any("VOID STORM" in line for line in self.engine.state.ship.flight_log))

    def test_stability_collapse_forces_emergence(self):
        self._goto_cygnus_horizon()
        self.engine.void_dive("golconda")
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(
                    void_traversal=VoidTraversalState(
                        origin_system_id="cygnus_x1",
                        destination_system_id="golconda",
                        started_tick=self.engine.state.time.tick,
                        arrival_tick=self.engine.state.time.tick + 6,
                        duration_ticks=6,
                        stability=10.0,
                    )
                )
            )
        hull_before = self.engine.state.ship.hull

        with patch.object(self.engine.rng, "random", return_value=0.0):
            self.engine.tick(1)

        self.assertIsNone(self.engine.state.ship.void_traversal)
        self.assertEqual(self.engine.state.ship.current_system_id, "cygnus_x1")
        self.assertEqual(self.engine.state.ship.orbiting_body_id, "cygnus_x1_black_hole")
        self.assertLess(self.engine.state.ship.hull, hull_before)
        self.assertTrue(any("VOID COLLAPSE" in line for line in self.engine.state.ship.flight_log))

    def test_gateways_open_calms_storms(self):
        self.assertEqual(self.engine._void_storm_chance(), 0.20)
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(
                ship=self.engine._clone_ship(
                    story=self.engine.state.ship.story.__class__(
                        campaign_title=self.engine.state.ship.story.campaign_title,
                        current_chapter_index=self.engine.state.ship.story.current_chapter_index,
                        chapters=self.engine.state.ship.story.chapters,
                        transmission_log=self.engine.state.ship.story.transmission_log,
                        reputation=dict(self.engine.state.ship.story.reputation),
                        flags={"gateways_open": True},
                    )
                )
            )
        self.assertAlmostEqual(self.engine._void_storm_chance(), 0.15)

    def test_void_status_parity_fields(self):
        status = self.engine.void_status()
        for key in (
            "current_system_id",
            "anchors",
            "lanes",
            "traversal",
            "destination_name",
            "traversal_progress",
            "dive_ready",
            "blockers",
            "destinations",
            "storm_chance",
            "shield",
            "fuel",
        ):
            self.assertIn(key, status)

    def test_void_status_reports_destination_name_in_transit(self):
        self._goto_cygnus_horizon()
        self.engine.void_dive("golconda")
        status = self.engine.void_status()
        self.assertEqual(status["destination_name"], "Golconda Rift")
        self.assertIsNotNone(status["traversal"])

    def test_snapshot_includes_void_and_story_status(self):
        snapshot = self.engine.get_status_snapshot()
        self.assertIn("void", snapshot)
        self.assertIn("story_status", snapshot)
        self.assertIn("dive_ready", snapshot["void"])
        self.assertIn("choices", snapshot["story_status"])

    def test_cli_void_commands(self):
        res = cmd_void(self.engine, self.storage, ["void"])
        self.assertEqual(res, 0)

        res = cmd_void(self.engine, self.storage, ["void", "lanes"])
        self.assertEqual(res, 0)

        res = cmd_void(self.engine, self.storage, ["void", "dive"])
        self.assertEqual(res, 1)

        res = cmd_void(self.engine, self.storage, ["void", "dive", "golconda"])
        self.assertEqual(res, 1)
        self.assertIsNone(self.engine.state.ship.void_traversal)

        res = cmd_void(self.engine, self.storage, ["void", "emerge"])
        self.assertEqual(res, 1)

        # Status header shows the void transit line while traversing
        self._goto_cygnus_horizon()
        ok, msg = self.engine.void_dive("golconda")
        self.assertTrue(ok, msg)
        res = cmd_status(self.engine)
        self.assertEqual(res, 0)
        res = cmd_void(self.engine, self.storage, ["void"])
        self.assertEqual(res, 0)
        self.assertIsNotNone(self.engine.state.ship.void_traversal)

    def test_legacy_save_backfills_black_hole_horizons(self):
        # A save predating void gates has no black-hole bodies anywhere
        from dataclasses import replace as dc_replace

        systems = {}
        for sid, sys_obj in self.engine.state.systems.items():
            bodies = tuple(b for b in sys_obj.bodies if b.body_type != "black_hole")
            systems[sid] = dc_replace(sys_obj, bodies=bodies)
        legacy = self.engine._clone_state(systems=systems)
        self.assertEqual(void_anchor_systems(legacy.systems), [])

        restored = SimulationEngine(state=legacy)
        self.assertEqual(void_anchor_systems(restored.state.systems), ["cygnus_x1", "golconda"])
        status = restored.void_status()
        self.assertTrue(status["lanes"], "void lanes must exist after the legacy backfill")
        self.assertTrue(any("event horizon" in b for b in status["blockers"]))

    def test_cli_main_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            __import__("os").environ,
            {"LOCALAPPDATA": tmp, "HOME": tmp, "USERPROFILE": tmp},
        ):
            res = main(["void", "status"])
            self.assertEqual(res, 0)
            res = main(["void", "lanes"])
            self.assertEqual(res, 0)


class TestServerVoidEndpoints(unittest.TestCase):
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

    def test_get_api_void(self):
        status, data = self._get("/api/void")
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("dive_ready", payload["void"])
        self.assertIn("lanes", payload["void"])

    def test_post_api_void_dive_rejected_without_horizon(self):
        status, data = self._post("/api/void/dive", {"target_system_id": "golconda"})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertIn("event horizon", payload["message"])

    def test_post_api_void_emerge_rejected_when_not_traversing(self):
        status, data = self._post("/api/void/emerge", {})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertFalse(payload["ok"])

    def test_story_endpoint_includes_status(self):
        status, data = self._get("/api/story")
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("status", payload)
        self.assertIn("unmet_requirements", payload["status"])


if __name__ == "__main__":
    unittest.main()
