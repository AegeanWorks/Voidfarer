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


if __name__ == "__main__":
    unittest.main()
