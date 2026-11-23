"""A relief bag short of fuel cells harvests them from a surface site (ADR-455)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient


def _operations(fuel_used=False, fuel_available=True):
    return [
        {"id": "surface_survey", "available": True, "used": False, "cargo": []},
        {
            "id": "geothermal_tap",
            "available": fuel_available,
            "used": fuel_used,
            "cargo": [{"id": "fuel_cells", "quantity": 3}],
        },
    ]


def _captain(
    cargo=None,
    landed=False,
    relief=0,
    completed=True,
    attempts=0,
    operations=None,
    orbiting=None,
    orbiting_id="",
    travel=None,
):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.relief_fuel_attempts = attempts
    captain.state = {
        "story_status": {"completed": completed},
        "stats": {"relief_deliveries": relief, "worlds_rebuilt": 1},
        "ship": {
            "cargo": cargo if cargo is not None else {},
            "landed_body_id": "site" if landed else "",
            "orbiting_body_id": orbiting_id,
            "travel": travel,
        },
        "orbiting_body": orbiting,
        "current_system": {
            "id": "sol",
            "bodies": [
                {"id": "site", "name": "Site", "landable": True},
                {"id": "station", "name": "Station", "station_dockable": True},
            ],
        },
        "surface_report": {
            "landed": landed,
            "operations": operations if operations is not None else _operations(),
        },
    }
    return captain


class ReliefFuelTest(unittest.TestCase):
    def test_a_landed_site_runs_the_fuel_operation_not_the_first_one(self):
        self.assertEqual(
            _captain(landed=True)._relief_fuel_action(),
            ("/api/surface/op", {"operation_id": "geothermal_tap"}, "surface"),
        )

    def test_a_used_fuel_operation_is_skipped(self):
        self.assertIsNone(
            _captain(landed=True, operations=_operations(fuel_used=True))._relief_fuel_action()
        )

    def test_an_unavailable_fuel_operation_is_skipped(self):
        self.assertIsNone(
            _captain(landed=True, operations=_operations(fuel_available=False))._relief_fuel_action()
        )

    def test_a_held_fuel_cell_stops_the_harvest(self):
        self.assertIsNone(
            _captain(landed=True, cargo={"fuel_cells": 1})._relief_fuel_action()
        )

    def test_nothing_harvests_before_the_campaign(self):
        self.assertIsNone(_captain(landed=True, completed=False)._relief_fuel_action())

    def test_a_banked_relief_target_stops_the_harvest(self):
        self.assertIsNone(_captain(landed=True, relief=3)._relief_fuel_action())

    def test_the_attempt_budget_stops_the_harvest(self):
        self.assertIsNone(
            _captain(landed=True, attempts=AiCaptain.RELIEF_FUEL_LIMIT)._relief_fuel_action()
        )

    def test_a_worked_operation_increments_the_attempt_budget(self):
        captain = _captain(landed=True)
        captain._relief_fuel_action()
        self.assertEqual(captain.relief_fuel_attempts, 1)

    def test_an_orbiting_ship_keeps_its_route(self):
        self.assertIsNone(
            _captain(orbiting={"id": "site", "landable": True})._relief_fuel_action(),
            "landing for fuel starved the other late errands in a measured campaign",
        )

    def test_a_ship_away_from_a_site_keeps_its_route(self):
        self.assertIsNone(_captain()._relief_fuel_action())

    def test_a_ship_in_transit_does_not_land(self):
        self.assertIsNone(
            _captain(travel={"arrival_tick": 12})._relief_fuel_action()
        )


class FullHoldSaleTest(unittest.TestCase):
    def _captain(self, cargo=None, quotes=None, relief=0, completed=True, free_volume=0):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "story_status": {"completed": completed},
            "stats": {"relief_deliveries": relief, "worlds_rebuilt": 1},
            "ship": {
                "cargo": cargo if cargo is not None else {"titanium": 5, "medicines": 2},
                "cargo_capacity": 20,
                "cargo_free_volume": free_volume,
            },
            "market_quotes": quotes if quotes is not None else [
                {"commodity_id": "titanium", "buy_price": 100},
                {"commodity_id": "medicines", "buy_price": 200},
            ],
        }
        return captain

    def test_a_full_hold_sells_ore_not_the_relief_bag(self):
        self.assertEqual(
            self._captain()._trade_choice(1),
            ("/api/trade", {"commodity_id": "titanium", "quantity": 1,
                            "is_buy": False}, "trade"),
        )

    def test_the_sale_also_works_for_map_shaped_quotes(self):
        captain = self._captain(quotes={
            "titanium": {"commodity_id": "titanium", "buy_price": 100},
            "medicines": {"commodity_id": "medicines", "buy_price": 200},
        })
        self.assertEqual(captain._trade_choice(1)[1]["commodity_id"], "titanium")

    def test_relief_ingredients_are_sellable_once_the_milestone_is_banked(self):
        captain = self._captain(relief=3, cargo={"medicines": 2})
        self.assertEqual(captain._trade_choice(1)[1]["commodity_id"], "medicines")

    def test_a_hold_with_space_does_not_dump_cargo(self):
        self.assertIsNone(self._captain(free_volume=5)._trade_choice(1))


if __name__ == "__main__":
    unittest.main()
