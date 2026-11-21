"""The rebuild sweep stocks relief to bank the Relief Runner milestone (ADR-438)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_MAP


def _captain(
    cargo=None,
    orbiting="devastated",
    docked=False,
    credits=5000,
    rebuilt=1,
    relief=1,
    succeeded=("/api/reconstruct",),
    completed=True,
    attempts=0,
    stock_attempts=0,
    quotes=None,
    bodies=None,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.succeeded.update(succeeded)
    captain.rebuild_attempts = attempts
    captain.rebuild_stock_attempts = stock_attempts
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"worlds_rebuilt": rebuilt, "relief_deliveries": relief},
        "current_system": {
            "id": "sol",
            "bodies": bodies if bodies is not None else [
                {"id": "devastated", "population": 500000, "devastation": 60.0},
                {"id": "station", "station_dockable": True},
            ],
        },
        "orbiting_body": {
            "id": orbiting,
            "station_dockable": docked,
        },
        "ship": {
            "credits": credits,
            "cargo": cargo or {},
            "landed_body_id": "",
            "cargo_free_volume": 20,
        },
        "market_quotes": quotes if quotes is not None else [
            {"commodity_id": "medicines", "buy_price": 280, "max_buy": 6},
            {"commodity_id": "hydroponics", "buy_price": 60, "max_buy": 8},
            {"commodity_id": "fuel_cells", "buy_price": 90, "max_buy": 4},
        ],
    }
    return captain


class ReliefRunTest(unittest.TestCase):
    def test_a_docked_empty_hold_buys_the_first_missing_bag(self):
        captain = _captain(docked=True)
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/trade",
             {"commodity_id": "medicines", "quantity": 2, "is_buy": True},
             "trade"),
        )
        self.assertEqual(captain.rebuild_stock_attempts, 1)

    def test_the_next_missing_bag_is_bought_in_turn(self):
        captain = _captain(
            docked=True,
            cargo={"medicines": 2, "hydroponics": 1},
        )
        self.assertEqual(
            captain._rebuild_sweep_action()[1]["commodity_id"], "hydroponics"
        )

    def test_a_fully_stocked_hold_delivers_relief(self):
        captain = _captain(
            docked=True,
            cargo={"medicines": 2, "hydroponics": 2, "fuel_cells": 1},
        )
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/reconstruct", {"body_id": "devastated", "mode": "relief"},
             "reconstruct"),
        )

    def test_no_stocking_once_the_relief_target_is_banked(self):
        captain = _captain(
            docked=True,
            relief=AiCaptain.RELIEF_RUNNER_TARGET,
            rebuilt=2,
        )
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_an_exhausted_stock_budget_falls_back_to_credits(self):
        captain = _captain(
            docked=True,
            stock_attempts=AiCaptain.REBUILD_STOCK_LIMIT,
        )
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/reconstruct", {"body_id": "devastated", "mode": "credits"},
             "reconstruct"),
        )

    def test_an_unbuyable_bag_does_not_burn_the_budget(self):
        captain = _captain(
            docked=True,
            quotes=[],
        )
        self.assertEqual(
            captain._rebuild_sweep_action()[1]["mode"], "credits"
        )
        self.assertEqual(captain.rebuild_stock_attempts, 0)

    def test_after_five_rebuilds_only_relief_continues(self):
        captain = _captain(
            rebuilt=4,
            relief=1,
            orbiting="devastated",
        )
        self.assertIsNone(
            captain._rebuild_sweep_action(),
            "no credit rebuild past the rebuilder target; relief needs a dock",
        )

    def test_both_targets_stop_the_sweep(self):
        captain = _captain(
            rebuilt=5,
            relief=AiCaptain.RELIEF_RUNNER_TARGET,
        )
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_the_stock_budget_is_bounded(self):
        self.assertGreater(AiCaptain.REBUILD_STOCK_LIMIT, 0)
        self.assertLess(AiCaptain.REBUILD_STOCK_LIMIT, 20)

    def test_the_relief_target_mirrors_the_codex_entry(self):
        self.assertEqual(
            AiCaptain.RELIEF_RUNNER_TARGET,
            CODEX_MAP["relief_runner"].target,
        )


if __name__ == "__main__":
    unittest.main()
