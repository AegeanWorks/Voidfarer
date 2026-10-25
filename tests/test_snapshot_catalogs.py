"""Static catalogs: built once, served by /api/catalogs, and left out of polls that cache them."""

import http.client
import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from voidfarer.engine import STATIC_SNAPSHOT_KEYS, SimulationEngine, static_catalogs
from voidfarer.server import CATALOG_CACHE_HEADER, ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


class TestStaticCatalogs(unittest.TestCase):
    def test_catalogs_cover_exactly_the_static_keys(self):
        self.assertEqual(set(static_catalogs()), set(STATIC_SNAPSHOT_KEYS))

    def test_catalogs_are_built_once(self):
        self.assertIs(static_catalogs(), static_catalogs())

    def test_full_snapshot_still_carries_every_catalog(self):
        snapshot = SimulationEngine(seed=42).get_status_snapshot()
        for key, value in static_catalogs().items():
            self.assertEqual(snapshot[key], value, key)

    def test_lite_snapshot_omits_catalogs_and_keeps_live_state(self):
        snapshot = SimulationEngine(seed=42).get_status_snapshot(include_static=False)
        self.assertFalse(set(STATIC_SNAPSHOT_KEYS) & set(snapshot))
        for key in ("ship", "time", "character_abilities", "corporations"):
            self.assertIn(key, snapshot)


class TestCatalogEndpoints(unittest.TestCase):
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
        VoidFarerHandler.engine = SimulationEngine(seed=42)
        VoidFarerHandler.storage = StorageManager(self.temp_dir.name)

    def _request(self, method, path, body=None, cached=False):
        headers = {"Content-Type": "application/json"}
        if cached:
            headers[CATALOG_CACHE_HEADER] = "1"
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        payload = json.loads(conn.getresponse().read())
        conn.close()
        return payload

    def test_catalog_endpoint_serves_every_static_key(self):
        payload = self._request("GET", "/api/catalogs")
        self.assertTrue(payload["ok"])
        self.assertEqual(set(payload["data"]), set(STATIC_SNAPSHOT_KEYS))

    def test_catalog_endpoint_ignores_the_cache_header(self):
        payload = self._request("GET", "/api/catalogs", cached=True)
        self.assertEqual(set(payload["data"]), set(STATIC_SNAPSHOT_KEYS))

    def test_state_poll_is_full_by_default_and_lite_when_cached(self):
        full = self._request("GET", "/api/state")["data"]
        lite = self._request("GET", "/api/state", cached=True)["data"]
        self.assertTrue(set(STATIC_SNAPSHOT_KEYS) <= set(full))
        self.assertFalse(set(STATIC_SNAPSHOT_KEYS) & set(lite))
        self.assertEqual(lite["ship"]["credits"], full["ship"]["credits"])

    def test_action_responses_honour_the_cache_header(self):
        body = {"commodity_id": "fuel_cells", "quantity": 1, "is_buy": True}
        state = self._request("POST", "/api/trade", body, cached=True)["state"]
        self.assertIn("ship", state)
        self.assertFalse(set(STATIC_SNAPSHOT_KEYS) & set(state))


if __name__ == "__main__":
    unittest.main()
