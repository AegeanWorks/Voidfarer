"""The headless AI captain must be able to reach and exercise the game without a human."""

import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.agent_api import build_action_catalog
from voidfarer.agent_play import AiCaptain, ApiClient, coverage_gaps
from voidfarer.engine import SimulationEngine
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


class AgentApiCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build_action_catalog(VoidFarerHandler)

    def test_catalog_describes_every_post_route(self):
        self.assertTrue(self.catalog["ok"])
        paths = {entry["path"] for entry in self.catalog["actions"]}
        self.assertGreaterEqual(len(paths), 60)
        for required in (
            "/api/travel", "/api/travel/point", "/api/trade", "/api/scan", "/api/orbit",
            "/api/jump", "/api/diplomacy", "/api/war/support", "/api/settings/decisions",
            "/api/decision/resolve", "/api/pirate/resolve", "/api/combat",
        ):
            self.assertIn(required, paths)

    def test_catalog_fields_match_the_endpoint_contract(self):
        by_path = {entry["path"]: entry for entry in self.catalog["actions"]}
        self.assertEqual(by_path["/api/travel"]["method"], "POST")
        self.assertEqual(set(by_path["/api/travel"]["fields"]), {"body_id", "mode"})
        self.assertIn("faction_id", by_path["/api/diplomacy"]["fields"])
        self.assertIn("action", by_path["/api/diplomacy"]["fields"])
        self.assertIn("distance_au", by_path["/api/travel/point"]["fields"])
        self.assertIn("angle", by_path["/api/travel/point"]["fields"])
        self.assertIn("strategy", by_path["/api/salvage"].get("fields", []))
        self.assertIn("action", by_path["/api/customs/resolve"].get("fields", []))
        self.assertIn("rarity", by_path["/api/relics/fuse"].get("fields", []))

    def test_save_family_catalog_includes_slot(self):
        by_path = {entry["path"]: entry for entry in self.catalog["actions"]}
        for path in ("/api/save", "/api/load", "/api/delete-save", "/api/new-game"):
            self.assertIn("slot", by_path[path].get("fields", []), path)

    def test_step_is_documented_as_orbit_only(self):
        from voidfarer.agent_play import CONTEXT_ACTIONS
        self.assertIn("/api/step", CONTEXT_ACTIONS)
        self.assertNotIn("alias", CONTEXT_ACTIONS["/api/step"])
        by_path = {entry["path"]: entry for entry in self.catalog["actions"]}
        self.assertIn("delta_time", by_path["/api/step"].get("fields", []))
        self.assertIn("ticks", by_path["/api/time/step"].get("fields", []))

    def test_observations_include_state(self):
        paths = {entry["path"] for entry in self.catalog["observations"]}
        self.assertIn("/api/state", paths)
        self.assertIn("/api/agent/actions", paths)


class AgentPlayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.engine = SimulationEngine(seed=42)
        cls.engine.allow_decision_events = True
        VoidFarerHandler.engine = cls.engine
        VoidFarerHandler.storage = StorageManager(cls.temp_dir.name)
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2.0)
        cls.temp_dir.cleanup()

    def test_catalog_is_served_over_rest(self):
        client = ApiClient(port=self.server.server_port)
        status, payload = client.get("/api/agent/actions")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["actions"])

    def test_ai_captain_plays_without_a_human(self):
        client = ApiClient(port=self.server.server_port)
        report = AiCaptain(client, seed=42).play(steps=50)
        self.assertEqual(report["errors"], [])
        self.assertGreaterEqual(report["family_count"], 6, report["families"])
        self.assertTrue({"travel", "dock", "navigate"} & set(report["families"]))
        self.assertIn("time", report["families"])
        self.assertGreater(report["steps"], 10)
        final = report["final"]
        self.assertGreater(int(final["hull"] or 0), 0)
        self.assertGreaterEqual(int(final["credits"] or 0), 0)
        self.assertIsNotNone(final["tick"])

    def test_every_catalog_action_is_attempted_or_documented(self):
        VoidFarerHandler.engine = SimulationEngine(seed=42)
        VoidFarerHandler.engine.allow_decision_events = True
        client = ApiClient(port=self.server.server_port)
        report = AiCaptain(client, seed=42).play(steps=180)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["coverage_gaps"], [], "every action needs an AI path or a reason")
        self.assertGreaterEqual(report["succeeded_count"], 35, report["succeeded"])
        self.assertGreaterEqual(report["attempted_count"], 45, report["attempted"])
        self.assertGreaterEqual(report["family_count"], 22, report["families"])

    def test_coverage_gap_detection(self):
        self.assertEqual(coverage_gaps(["/api/scan"], {"/api/scan"}), [])
        self.assertEqual(coverage_gaps(["/api/nope"], set()), ["/api/nope"])
        self.assertEqual(coverage_gaps(["/api/save"], set()), [])

    def test_the_engine_state_stays_loadable_after_play(self):
        snapshot = self.engine.get_status_snapshot()
        restored = type(self.engine.state).from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.time.tick, snapshot["time"]["tick"])
        self.assertIsNotNone(restored.ship)


class AiCaptainTourCoverageTest(unittest.TestCase):
    """The fleet and crew alias sub-actions stay reachable from the AI captain."""

    def _captain(self, state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = state
        return captain

    def test_station_map_and_wear_mark_match_the_engine(self):
        self.assertEqual(AiCaptain.STATION_BY_ROLE, SimulationEngine.STATION_BY_ROLE)
        self.assertEqual(AiCaptain.REFIT_WORN_INTEGRITY, SimulationEngine.REFIT_WORN_INTEGRITY)

    def test_autostaff_tour_fires_only_when_the_seating_is_not_optimal(self):
        crew = [{"id": "c1", "role": "pilot", "status": "active", "skill": 4, "xp": 0, "station": ""}]
        self.assertEqual(
            self._captain({"crew": crew})._tour_crew_autostaff(),
            ("/api/crew/action", {"action": "autostaff"}, "crew_autostaff"),
        )
        seated = [dict(crew[0], station="helm")]
        self.assertIsNone(self._captain({"crew": seated})._tour_crew_autostaff())

    def test_refit_tour_needs_a_dock_a_worn_drone_and_credits(self):
        docked = {"orbiting_body": {"station_dockable": True}}
        worn = {"id": "d1", "integrity": 20}

        def action(state):
            return self._captain(state)._tour_fleet_refit_damaged()

        self.assertEqual(
            action({**docked, "ship": {"credits": 300, "fleet_drones": [worn]}}),
            ("/api/fleet/action", {"action": "refit_damaged"}, "fleet_refit"),
        )
        self.assertIsNone(action({"ship": {"credits": 300, "fleet_drones": [worn]}}))
        self.assertIsNone(action({**docked, "ship": {"credits": 300, "fleet_drones": [dict(worn, integrity=80)]}}))
        self.assertIsNone(action({**docked, "ship": {"credits": 299, "fleet_drones": [worn]}}))

    def test_two_alias_subactions_can_fire_in_one_run(self):
        captain = self._captain({
            "orbiting_body": {"station_dockable": True},
            "ship": {"credits": 600, "fleet_drones": [{"id": "d1", "integrity": 20}]},
            "crew": [{"id": "c1", "role": "pilot", "status": "active", "skill": 4, "xp": 0, "station": ""}],
        })
        families = []
        for _ in range(500):
            action = captain._next_tour_action()
            if action is None:
                break
            path, body, family = action
            families.append(family)
            captain.attempted.add(path)
            captain.attempted_signatures.add((path, str((body or {}).get("action") or "")))
        self.assertIn("fleet_refit", families)
        self.assertIn("crew_autostaff", families)


class _StubClient:
    """Minimal API stand-in so play() can be exercised without a server."""

    def __init__(self, state=None):
        self.state = state or {"ship": {"credits": 1000}, "time": {"tick": 0}}

    def get(self, path):
        if path == "/api/agent/actions":
            return 200, {"ok": True, "actions": [{"path": "/api/time/step"}]}
        return 200, {"ok": True, "state": self.state}

    def post(self, path, body):
        return 200, {"ok": True, "state": self.state}


class PlayStepCapTest(unittest.TestCase):
    """The CLI honours --steps and says when the runaway guard clamps it (ADR-341)."""

    def test_a_request_beyond_the_guard_is_clamped_and_reported(self):
        captain = AiCaptain(_StubClient(), seed=42)
        captain.MAX_STEPS = 3
        report = captain.play(steps=10)
        self.assertEqual(report["steps"], 3)
        self.assertEqual(report["steps_requested"], 10)
        self.assertTrue(report["steps_capped"])

    def test_a_request_inside_the_guard_runs_in_full_and_is_not_flagged(self):
        captain = AiCaptain(_StubClient(), seed=42)
        report = captain.play(steps=3)
        self.assertEqual(report["steps"], 3)
        self.assertEqual(report["steps_requested"], 3)
        self.assertFalse(report["steps_capped"])


class AiPlayToolArgsTest(unittest.TestCase):
    def test_rejects_non_positive_steps(self):
        from tools.ai_play import main as ai_play_main
        for bad in ("0", "-5"):
            with self.assertRaises(SystemExit) as ctx:
                ai_play_main(["--steps", bad])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
