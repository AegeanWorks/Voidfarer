"""Every ready codex entry stays claimable, not just the first (ADR-426)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _captain(entries) -> AiCaptain:
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.state = {"codex": {"entries": entries}}
    return captain


class CodexClaimTourTest(unittest.TestCase):
    def test_the_first_ready_entry_is_claimed(self):
        captain = _captain([
            {"id": "first", "ready": True, "claimed": False},
            {"id": "second", "ready": True, "claimed": False},
        ])
        self.assertEqual(captain._tour_codex(),
                         ("/api/codex/claim", {"entry_id": "first"}, "codex"))

    def test_a_second_ready_entry_is_claimable_after_the_first(self):
        captain = _captain([
            {"id": "first", "ready": True, "claimed": True},
            {"id": "second", "ready": True, "claimed": False},
        ])
        action = captain._tour_codex()
        self.assertEqual(action, ("/api/codex/claim", {"entry_id": "second"}, "codex"))
        # The one-shot guard must treat the second entry as a new action even though
        # the route was already used for the first claim (ADR-426).
        captain.attempted.add("/api/codex/claim")
        captain.attempted_signatures.add(("/api/codex/claim", "first"))
        captain.repeat_last[("/api/codex/claim", "first")] = 0
        self.assertFalse(captain._tour_action_attempted(*action[:2]))

    def test_the_same_entry_is_not_claimed_twice(self):
        captain = _captain([
            {"id": "first", "ready": True, "claimed": False},
        ])
        action = captain._tour_codex()
        captain.attempted.add("/api/codex/claim")
        captain.attempted_signatures.add(("/api/codex/claim", "first"))
        self.assertTrue(captain._tour_action_attempted(*action[:2]))

    def test_nothing_ready_claims_nothing(self):
        captain = _captain([
            {"id": "first", "ready": False, "claimed": False},
            {"id": "second", "ready": True, "claimed": True},
        ])
        self.assertIsNone(captain._tour_codex())

    def test_the_signature_is_keyed_on_the_entry(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        self.assertEqual(
            captain._tour_signature("/api/codex/claim", {"entry_id": "first_light"}),
            ("/api/codex/claim", "first_light"),
        )


if __name__ == "__main__":
    unittest.main()
