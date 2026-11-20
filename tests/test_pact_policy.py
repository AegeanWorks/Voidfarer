"""The post-story captain signs a trade and a research pact (ADR-428)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _captain(standings, trade=(), research=(), wars=(), completed=True):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.state = {
        "story_status": {"completed": completed},
        "ship": {
            "faction_standings": dict(standings),
            "trade_pacts": list(trade),
            "research_pacts": list(research),
        },
        "wars": list(wars),
    }
    return captain


def _war(attacker, defender):
    return {"id": f"war_{attacker}_{defender}", "attacker_id": attacker,
            "defender_id": defender, "active": True}


class PactPolicyTest(unittest.TestCase):
    def test_a_trade_pact_goes_to_the_highest_standing_friend(self):
        captain = _captain({"sol_coalition": 100, "precursor_watch": 80,
                            "nebula_collective": 40})
        self.assertEqual(
            captain._pact_action(),
            ("/api/diplomacy",
             {"faction_id": "sol_coalition", "action": "trade_pact"}, "diplomacy"),
        )

    def test_a_faction_at_war_with_the_player_is_skipped(self):
        captain = _captain(
            {"sol_coalition": 100, "nebula_collective": 95, "precursor_watch": 90},
            wars=(_war("sol_coalition", "nebula_collective"),),
        )
        # Sol is the player's own polity and Nebula is its belligerent; the pact goes
        # to the highest-standing faction that is not at war with the player.
        self.assertEqual(captain._pact_action()[1]["faction_id"], "precursor_watch")

    def test_a_war_between_other_factions_does_not_block(self):
        captain = _captain(
            {"precursor_watch": 90},
            wars=(_war("nebula_collective", "kepler_concord"),),
        )
        self.assertEqual(captain._pact_action()[1]["faction_id"], "precursor_watch")

    def test_a_research_pact_follows_the_trade_pact(self):
        captain = _captain({"precursor_watch": 90}, trade=("precursor_watch",))
        self.assertEqual(
            captain._pact_action(),
            ("/api/diplomacy",
             {"faction_id": "precursor_watch", "action": "research_pact"}, "diplomacy"),
        )

    def test_low_standing_signs_nothing(self):
        self.assertIsNone(_captain({"precursor_watch": 30})._pact_action())

    def test_research_still_signs_when_trade_is_held_elsewhere(self):
        captain = _captain(
            {"precursor_watch": 90, "helios_compact": 20},
            trade=("precursor_watch",),
        )
        self.assertEqual(captain._pact_action()[1]["action"], "research_pact")

    def test_nothing_signs_before_the_campaign(self):
        self.assertIsNone(_captain({"precursor_watch": 90}, completed=False)._pact_action())

    def test_a_refused_pact_is_not_retried(self):
        captain = _captain({"precursor_watch": 90})
        action = captain._pact_action()
        self.assertEqual(action[0], "/api/diplomacy")
        self.assertEqual(action[1]["action"], "trade_pact")
        captain._note_pact_attempt(action[1]["action"], action[1]["faction_id"])
        # The refused trade signature is not retried; the research pact is next.
        follow_up = captain._pact_action()
        self.assertEqual(follow_up[1]["action"], "research_pact")

    def test_both_pacts_held_signs_nothing(self):
        captain = _captain(
            {"precursor_watch": 90},
            trade=("precursor_watch",),
            research=("precursor_watch",),
        )
        self.assertIsNone(captain._pact_action())


if __name__ == "__main__":
    unittest.main()
