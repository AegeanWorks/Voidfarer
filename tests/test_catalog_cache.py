"""The captain caches static catalogs and asks for slim action payloads (ADR-420)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.engine import CATALOG_CACHE_HEADER


class _RecordingClient:
    """Stand-in for ApiClient that records headers and returns canned payloads."""

    def __init__(self) -> None:
        self.get_headers: list[dict] = []
        self.post_headers: list[dict] = []
        self.posts: list[str] = []

    def get(self, path: str, headers: dict | None = None):
        self.get_headers.append(headers or {})
        if path == "/api/agent/actions":
            return 200, {"actions": [{"path": "/api/time/resume"}]}
        return 200, {"state": {
            "ship": {"hull": 100, "max_hull": 100},
            "time": {"is_paused": True, "tick": 5},
            "current_system": {"id": "sol", "connections": [], "bodies": []},
            "catalog_upgrades": [{"id": "coil"}],
            "story_chapters": [{"id": "act_1"}],
        }}

    def post(self, path: str, payload=None, headers: dict | None = None):
        self.posts.append(path)
        self.post_headers.append(headers or {})
        return 200, {"ok": True, "message": "resumed", "state": {
            "ship": {"hull": 100, "max_hull": 100},
            "time": {"is_paused": False, "tick": 6},
            "current_system": {"id": "sol", "connections": [], "bodies": []},
        }}


class CatalogCacheTest(unittest.TestCase):
    def test_the_first_snapshot_seeds_the_cache(self):
        client = _RecordingClient()
        captain = AiCaptain(client, seed=42)
        captain.play(steps=1)
        self.assertEqual(captain.catalogs["catalog_upgrades"], [{"id": "coil"}])
        self.assertEqual(captain.catalogs["story_chapters"], [{"id": "act_1"}])

    def test_every_action_post_requests_the_slim_payload(self):
        client = _RecordingClient()
        captain = AiCaptain(client, seed=42)
        captain.play(steps=1)
        self.assertEqual(client.posts, ["/api/time/resume"])
        self.assertEqual(client.post_headers[0], {CATALOG_CACHE_HEADER: "1"})

    def test_the_initial_snapshot_is_fetched_in_full(self):
        client = _RecordingClient()
        captain = AiCaptain(client, seed=42)
        captain.play(steps=1)
        self.assertEqual(client.get_headers[-1], {})

    def test_a_slim_response_is_rehydrated_from_the_cache(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.catalogs = {"catalog_upgrades": [{"id": "coil"}], "weapons": ["laser"]}
        captain._adopt_state({"ship": {"hull": 10}})
        self.assertEqual(captain.state["catalog_upgrades"], [{"id": "coil"}])
        self.assertEqual(captain.state["weapons"], ["laser"])
        self.assertEqual(captain.state["ship"], {"hull": 10})

    def test_a_fresh_catalog_value_wins_over_the_cache(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.catalogs = {"catalog_upgrades": [{"id": "coil"}]}
        captain._adopt_state({"catalog_upgrades": [{"id": "new"}]})
        self.assertEqual(captain.state["catalog_upgrades"], [{"id": "new"}])

    def test_an_empty_snapshot_is_ignored(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {"kept": True}
        captain._adopt_state(None)
        self.assertEqual(captain.state, {"kept": True})


if __name__ == "__main__":
    unittest.main()
