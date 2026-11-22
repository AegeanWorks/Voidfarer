"""The post-story captain pledges a decisive war bond for Bondholder (ADR-449)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _war(war_id="war_1", score=0.0, support=None, active=True, **fields):
    row = {
        "id": war_id,
        "attacker_id": "sol_coalition",
        "defender_id": "kuper_belt",
        "war_score": score,
        "active": active,
        "support": dict(support or {}),
    }
    row.update(fields)
    return row


def _captain(wars=None, payouts=80, credits=120000, completed=True, done=False,
             pledged=(), reserve=None):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.war_bond_done = done
    captain.war_bond_pledged = set(pledged)
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"war_bond_payouts": payouts},
        "ship": {"credits": credits},
        "wars": list(wars or []),
    }
    return captain


class WarBondTest(unittest.TestCase):
    def test_a_leading_attacker_gets_the_pledge(self):
        captain = _captain([_war(score=8.0)])
        action = captain._war_bond_action()
        self.assertEqual(action[0], "/api/war/support")
        self.assertEqual(action[1]["faction_id"], "sol_coalition")
        self.assertEqual(action[1]["war_id"], "war_1")

    def test_a_leading_defender_gets_the_pledge(self):
        captain = _captain([_war(score=-9.0)])
        self.assertEqual(
            captain._war_bond_action()[1]["faction_id"], "kuper_belt"
        )

    def test_a_tied_front_pledges_the_defender(self):
        captain = _captain([_war(score=0.0)])
        self.assertEqual(
            captain._war_bond_action()[1]["faction_id"], "kuper_belt"
        )

    def test_the_pledge_covers_a_stalemate_payout(self):
        captain = _captain([_war(score=5.0)])
        pledge = captain._war_bond_action()[1]["credits"]
        self.assertGreaterEqual(
            int(pledge * 0.8), AiCaptain.BONDHOLDER_TARGET - 80,
            "an 0.8x settlement must still bank the milestone from here",
        )

    def test_the_pledge_respects_the_per_war_cap(self):
        captain = _captain([_war(
            score=5.0, support={"sol_coalition": 5900}
        )])
        self.assertEqual(captain._war_bond_action()[1]["credits"], 100)

    def test_a_fully_pledged_side_is_skipped(self):
        captain = _captain([_war(
            score=5.0, support={"sol_coalition": 6000}
        )])
        self.assertIsNone(captain._war_bond_action())

    def test_a_pledged_war_is_not_pledged_again(self):
        captain = _captain([_war(score=5.0)], pledged=("war_1",))
        self.assertIsNone(captain._war_bond_action())

    def test_the_next_war_is_pledged_after_one_is_spent(self):
        captain = _captain(
            [_war("war_1", score=5.0), _war("war_2", score=-4.0)],
            pledged=("war_1",),
        )
        self.assertEqual(captain._war_bond_action()[1]["war_id"], "war_2")

    def test_the_milestone_ends_the_pledging(self):
        captain = _captain(
            [_war(score=5.0)], payouts=AiCaptain.BONDHOLDER_TARGET
        )
        self.assertIsNone(captain._war_bond_action())
        self.assertTrue(captain.war_bond_done)

    def test_a_thin_treasury_keeps_the_repair_reserve(self):
        captain = _captain(
            [_war(score=5.0)], credits=AiCaptain.WAR_BOND_RESERVE + 50
        )
        self.assertIsNone(captain._war_bond_action())

    def test_nothing_is_pledged_before_the_campaign(self):
        captain = _captain([_war(score=5.0)], completed=False)
        self.assertIsNone(captain._war_bond_action())

    def test_a_concluded_war_is_ignored(self):
        captain = _captain([_war(score=5.0, active=False)])
        self.assertIsNone(captain._war_bond_action())

    def test_an_early_payout_asks_for_a_smaller_pledge(self):
        captain = _captain([_war(score=5.0)], payouts=1800)
        self.assertLessEqual(
            captain._war_bond_action()[1]["credits"], 400,
            "only the remaining shortfall needs covering",
        )

    def test_the_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.BONDHOLDER_TARGET, CODEX_MAP["bondholder"].target
        )


if __name__ == "__main__":
    unittest.main()
