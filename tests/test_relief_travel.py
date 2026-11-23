"""The relief sweep travels to a devastated world instead of loitering (ADR-454)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _body(body_id, population=1000, devastation=50.0, **extra):
    row = {"id": body_id, "body_type": "colony", "population": population,
           "devastation": devastation}
    row.update(extra)
    return row


def _system(system_id, bodies=(), connections=(), **extra):
    row = {
        "id": system_id, "name": system_id, "seed": 7, "x": 0.0, "y": 0.0,
        "spectral_type": "G", "color": "#ffffff", "security": 0.6,
        "faction": "Independent", "bodies": list(bodies),
        "connections": list(connections),
    }
    row.update(extra)
    return row


def _captain(
    galaxy,
    current="sol",
    orbiting="",
    cargo=None,
    credits=50000,
    rebuilt=5,
    relief=0,
    completed=True,
    attempts=0,
    jumps=0,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.succeeded.add("/api/reconstruct")
    captain.galaxy_cache = galaxy
    captain.rebuild_attempts = attempts
    captain.relief_jumps = jumps
    system = galaxy.get(current) or _system(current)
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"worlds_rebuilt": rebuilt, "relief_deliveries": relief},
        "current_system": system,
        "orbiting_body": {"id": orbiting} if orbiting else None,
        "ship": {
            "credits": credits,
            "fuel": 40,
            "cargo": cargo if cargo is not None else {},
            "landed_body_id": "",
        },
        "jump_fuel_costs": {name: 3 for name in system.get("connections") or []},
        "market_quotes": [],
    }
    return captain


STOCKED = {"medicines": 2, "hydroponics": 2, "fuel_cells": 1}


class ReliefStockTest(unittest.TestCase):
    def _captain(self, relief=0, docked=True, cargo=None, quotes=None,
                 stock_attempts=0, completed=True):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.rebuild_stock_attempts = stock_attempts
        captain.state = {
            "story_status": {"completed": completed},
            "stats": {"worlds_rebuilt": 0, "relief_deliveries": relief},
            "orbiting_body": {"id": "dock", "station_dockable": docked},
            "ship": {"credits": 50000, "cargo": cargo if cargo is not None else {},
                     "landed_body_id": ""},
            "market_quotes": quotes if quotes is not None else [
                {"commodity_id": "medicines", "buy_price": 216, "max_buy": 49},
                {"commodity_id": "hydroponics", "buy_price": 44, "max_buy": 106},
                {"commodity_id": "fuel_cells", "buy_price": 69, "max_buy": 106},
            ],
        }
        return captain

    def test_a_dock_restocks_the_first_missing_bag(self):
        self.assertEqual(
            self._captain()._relief_stock_action(),
            ("/api/trade", {"commodity_id": "medicines", "quantity": 2,
                            "is_buy": True}, "trade"),
        )

    def test_stocking_runs_before_the_one_shot_rebuild_succeeds(self):
        captain = self._captain()
        self.assertNotIn("/api/reconstruct", captain.succeeded)
        self.assertEqual(captain._relief_stock_action()[0], "/api/trade")

    def test_a_partial_dock_sells_what_it_has(self):
        captain = self._captain(quotes=[
            {"commodity_id": "medicines", "buy_price": 216, "max_buy": 1},
        ])
        self.assertEqual(
            captain._relief_stock_action()[1]["quantity"], 1,
            "one bag now is better than waiting for a dock with two",
        )

    def test_an_out_of_stock_dock_buys_nothing(self):
        captain = self._captain(quotes=[
            {"commodity_id": "medicines", "buy_price": 216, "max_buy": 0},
        ])
        self.assertIsNone(captain._relief_stock_action())

    def test_a_stocked_hold_does_not_buy(self):
        captain = self._captain(cargo=dict(STOCKED))
        self.assertIsNone(captain._relief_stock_action())

    def test_an_undocked_ship_does_not_buy(self):
        self.assertIsNone(self._captain(docked=False)._relief_stock_action())

    def test_the_banked_target_stops_the_stocking(self):
        captain = self._captain(relief=3)
        self.assertIsNone(captain._relief_stock_action())

    def test_the_purchase_budget_bounds_the_stocking(self):
        captain = self._captain(stock_attempts=AiCaptain.REBUILD_STOCK_LIMIT)
        self.assertIsNone(captain._relief_stock_action())

    def test_nothing_stocks_before_the_campaign(self):
        captain = self._captain(completed=False)
        self.assertIsNone(captain._relief_stock_action())


class ReliefTravelTest(unittest.TestCase):
    def test_a_stocked_hold_jumps_toward_a_devastated_world(self):
        galaxy = {
            "sol": _system("sol", connections=["vega"]),
            "vega": _system("vega", bodies=[_body("vega_colony")], connections=["sol"]),
        }
        captain = _captain(galaxy, cargo=dict(STOCKED))
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/jump", {"target": "vega"}, "jump"),
        )
        self.assertEqual(captain.relief_jumps, 1)

    def test_a_multi_hop_destination_takes_the_first_hop(self):
        galaxy = {
            "sol": _system("sol", connections=["mid"]),
            "mid": _system("mid", connections=["sol", "deep"]),
            "deep": _system("deep", bodies=[_body("deep_colony")],
                            connections=["mid"]),
        }
        captain = _captain(galaxy, cargo=dict(STOCKED))
        self.assertEqual(
            captain._rebuild_sweep_action()[1]["target"], "mid"
        )

    def test_the_nearest_destination_wins(self):
        galaxy = {
            "sol": _system("sol", connections=["far", "near"]),
            "near": _system("near", bodies=[_body("near_colony")],
                            connections=["sol"]),
            "far": _system("far", bodies=[_body("far_colony")], connections=["sol"]),
        }
        captain = _captain(galaxy, cargo=dict(STOCKED))
        self.assertIn(captain._rebuild_sweep_action()[1]["target"], ("near", "far"))

    def test_an_empty_hold_still_travels_toward_a_devastated_world(self):
        galaxy = {
            "sol": _system("sol", connections=["vega"]),
            "vega": _system("vega", bodies=[_body("vega_colony")], connections=["sol"]),
        }
        captain = _captain(galaxy, cargo={})
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/jump", {"target": "vega"}, "jump"),
            "waiting for a full bag deadlocked a measured campaign: sail with a "
            "partial hold and stock at the next dock",
        )

    def test_the_travel_budget_bounds_the_search(self):
        galaxy = {
            "sol": _system("sol", connections=["vega"]),
            "vega": _system("vega", bodies=[_body("vega_colony")], connections=["sol"]),
        }
        captain = _captain(galaxy, cargo=dict(STOCKED),
                           jumps=AiCaptain.RELIEF_JUMP_LIMIT)
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_a_banked_relief_target_stops_the_travel(self):
        galaxy = {
            "sol": _system("sol", connections=["vega"]),
            "vega": _system("vega", bodies=[_body("vega_colony")], connections=["sol"]),
        }
        captain = _captain(galaxy, cargo=dict(STOCKED), relief=3, rebuilt=5)
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_a_docked_sold_out_market_waits_for_refresh(self):
        galaxy = {
            "sol": _system("sol", connections=["vega"]),
            "vega": _system("vega", bodies=[_body("vega_colony")], connections=["sol"]),
        }
        captain = _captain(galaxy, cargo={})
        captain.state["orbiting_body"] = {"id": "dock", "station_dockable": True}
        captain.state["market_quotes"] = [
            {"commodity_id": "medicines", "buy_price": 216, "max_buy": 0},
        ]
        self.assertIsNone(
            captain._rebuild_sweep_action(),
            "a docked ship waits for a sold-out quote instead of burning jump budget",
        )

    def test_no_destination_means_no_travel(self):
        galaxy = {
            "sol": _system("sol", connections=["quiet"]),
            "quiet": _system("quiet", bodies=[_body("intact", devastation=0.0)],
                             connections=["sol"]),
        }
        captain = _captain(galaxy, cargo=dict(STOCKED))
        self.assertIsNone(captain._rebuild_sweep_action())


class NoThrashTest(unittest.TestCase):
    def test_an_unstocked_hold_does_not_orbit_a_target_it_cannot_rebuild(self):
        galaxy = {
            "sol": _system("sol", bodies=[_body("colony")]),
        }
        captain = _captain(
            galaxy, orbiting="elsewhere", cargo={}, rebuilt=5, relief=0,
        )
        self.assertIsNone(
            captain._rebuild_sweep_action(),
            "with the rebuild target banked and no relief cargo, orbiting is wasted",
        )

    def test_a_needed_credit_rebuild_still_orbits(self):
        galaxy = {"sol": _system("sol", bodies=[_body("colony")])}
        captain = _captain(
            galaxy, orbiting="elsewhere", cargo={}, rebuilt=1, relief=0,
        )
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/orbit", {"target": "colony"}, "orbit"),
        )

    def test_the_one_shot_gate_still_applies(self):
        galaxy = {"sol": _system("sol", bodies=[_body("colony")])}
        captain = _captain(galaxy, cargo=dict(STOCKED))
        captain.succeeded.discard("/api/reconstruct")
        self.assertIsNone(captain._rebuild_sweep_action())

    def test_a_dock_restocks_for_a_local_target_it_cannot_rebuild(self):
        galaxy = {"sol": _system("sol", bodies=[_body("colony")])}
        captain = _captain(galaxy, cargo={}, rebuilt=5, relief=0)
        captain.state["orbiting_body"] = {"id": "dock", "station_dockable": True}
        captain.state["market_quotes"] = [
            {"commodity_id": "medicines", "buy_price": 216, "max_buy": 49},
            {"commodity_id": "hydroponics", "buy_price": 44, "max_buy": 106},
            {"commodity_id": "fuel_cells", "buy_price": 69, "max_buy": 106},
        ]
        self.assertEqual(
            captain._rebuild_sweep_action(),
            ("/api/trade", {"commodity_id": "medicines", "quantity": 2,
                            "is_buy": True}, "trade"),
            "a local target still worth relieving must restock the hold at this dock",
        )


if __name__ == "__main__":
    unittest.main()
