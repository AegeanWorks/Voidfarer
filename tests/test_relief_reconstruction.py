"""Rebuilds prefer relief supplies, then fall back to credits (ADR-425)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.engine import SimulationEngine


class ReliefReconstructionTest(unittest.TestCase):
    def _captain(self, cargo=None, credits=5000, docked=True, orbiting="devastated",
                 attempted=(), stock_attempts=0, quotes=None):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.attempted.update(attempted)
        captain.relief_stock_attempts = stock_attempts
        bodies = [
            {"id": "devastated", "population": 500000, "devastation": 60.0,
             "station_dockable": False},
            {"id": "station", "station_dockable": True},
        ]
        captain.state = {
            "current_system": {"id": "sol", "bodies": bodies},
            "orbiting_body": {"id": orbiting, "station_dockable": orbiting == "station"},
            "ship": {"credits": credits, "cargo": cargo or {},
                     "landed_body_id": "", "cargo_free_volume": 20},
            "market_quotes": quotes if quotes is not None else [
                {"commodity_id": "medicines", "category": "medicine",
                 "buy_price": 280, "max_buy": 6},
                {"commodity_id": "hydroponics", "category": "food",
                 "buy_price": 60, "max_buy": 8},
                {"commodity_id": "fuel_cells", "category": "fuel",
                 "buy_price": 90, "max_buy": 4},
            ],
        }
        return captain

    def test_a_supplied_hold_rebuilds_with_relief(self):
        captain = self._captain(
            cargo={"medicines": 2, "hydroponics": 2, "fuel_cells": 1})
        self.assertEqual(
            captain._reconstruct_action(),
            ("/api/reconstruct", {"body_id": "devastated", "mode": "relief"},
             "reconstruct"),
        )

    def test_a_missing_bag_is_bought_at_a_dock_first(self):
        captain = self._captain(cargo={"medicines": 1}, orbiting="station")
        self.assertEqual(
            captain._reconstruct_action(),
            ("/api/trade",
             {"commodity_id": "medicines", "quantity": 1, "is_buy": True},
             "trade"),
        )

    def test_the_next_missing_bag_is_bought_in_turn(self):
        captain = self._captain(cargo={"medicines": 2, "hydroponics": 1}, orbiting="station")
        self.assertEqual(captain._reconstruct_action()[1]["commodity_id"],
                         "hydroponics")

    def test_an_undocked_captain_takes_the_credit_rebuild(self):
        captain = self._captain(cargo={}, docked=False, orbiting="devastated")
        self.assertEqual(
            captain._reconstruct_action(),
            ("/api/reconstruct", {"body_id": "devastated", "mode": "credits"},
             "reconstruct"),
        )

    def test_exhausted_stocking_falls_back_to_credits(self):
        captain = self._captain(
            cargo={}, orbiting="devastated",
            stock_attempts=AiCaptain.RELIEF_STOCK_LIMIT)
        self.assertEqual(captain._reconstruct_action(),
                         ("/api/reconstruct",
                          {"body_id": "devastated", "mode": "credits"},
                          "reconstruct"))

    def test_no_stock_and_no_credits_stays_quiet(self):
        captain = self._captain(
            cargo={}, credits=100, orbiting="devastated",
            stock_attempts=AiCaptain.RELIEF_STOCK_LIMIT)
        self.assertIsNone(captain._reconstruct_action())

    def test_an_already_attempted_rebuild_stays_quiet(self):
        captain = self._captain(
            cargo={"medicines": 2, "hydroponics": 2, "fuel_cells": 1},
            attempted={"/api/reconstruct"})
        self.assertIsNone(captain._reconstruct_action())

    def test_an_intact_system_has_no_target(self):
        captain = self._captain(
            cargo={"medicines": 2, "hydroponics": 2, "fuel_cells": 1})
        captain.state["current_system"] = {"id": "sol", "bodies": [
            {"id": "a", "population": 10, "devastation": 0.0},
        ]}
        self.assertIsNone(captain._reconstruct_action())

    def test_the_stocking_limit_mirrors_the_engine_recipe(self):
        self.assertEqual(AiCaptain.RELIEF_CARGO, SimulationEngine.RELIEF_CARGO)


if __name__ == "__main__":
    unittest.main()
