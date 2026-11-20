"""The post-story captain runs automated quantum freight (ADR-429)."""

from __future__ import annotations

import unittest

from voidfarer.agent_play import AiCaptain, ApiClient
from voidfarer.codex import CODEX_ENTRIES


def _captain(orders=0, enabled=True, cargo=None, trade_orders=(), docked=True,
             completed=True, credits=50000, done=False, idle=0, last_orders=0):
    captain = AiCaptain(ApiClient(port=1), seed=42)
    captain.quantum_done = done
    captain.quantum_idle = idle
    captain.quantum_last_orders = last_orders
    captain.state = {
        "story_status": {"completed": completed},
        "orbiting_body": {"id": "sol_body_1", "station_dockable": docked},
        "quantum_automation": {
            "enabled": enabled, "orders": orders, "min_net": 0,
            "last_order_tick": -10**9, "last_net": 0,
            "last_commodity": "", "last_destination": "",
        },
        "ship": {
            "credits": credits,
            "cargo": cargo if cargo is not None else {},
            "trade_orders": list(trade_orders),
        },
        "market_quotes": [
            {"commodity_id": "fuel_cells", "buy_price": 52, "max_buy": 9},
            {"commodity_id": "hydroponics", "buy_price": 60, "max_buy": 8},
            {"commodity_id": "titanium", "buy_price": 900, "max_buy": 2},
        ],
    }
    return captain


class QuantumFreightPolicyTest(unittest.TestCase):
    def test_a_dormant_broker_is_armed(self):
        captain = _captain(enabled=False)
        self.assertEqual(
            captain._quantum_freight_action(),
            ("/api/trade/quantum/automation",
             {"enabled": True, "min_net": 0}, "trade_quantum_automation"),
        )

    def test_an_empty_hold_buys_the_cheapest_lot(self):
        captain = _captain(cargo={})
        self.assertEqual(
            captain._quantum_freight_action(),
            ("/api/trade",
             {"commodity_id": "fuel_cells", "quantity": 4, "is_buy": True}, "trade"),
        )

    def test_a_loaded_hold_advances_the_freight_clock(self):
        captain = _captain(cargo={"fuel_cells": 6})
        self.assertEqual(captain._quantum_freight_action(),
                         ("/api/time/step", {"ticks": 6}, "time"))

    def test_a_full_slot_queue_waits(self):
        captain = _captain(cargo={"fuel_cells": 6}, trade_orders=[
            {"id": "freight_1_1"}, {"id": "freight_2_1"},
            {"id": "freight_3_1"}, {"id": "freight_4_1"},
        ])
        self.assertEqual(captain._quantum_freight_action()[0], "/api/time/step")

    def test_the_target_is_met_disarms_and_the_policy_stops(self):
        captain = _captain(orders=AiCaptain.QUANTUM_ORDER_TARGET)
        self.assertEqual(
            captain._quantum_freight_action(),
            ("/api/trade/quantum/automation",
             {"enabled": False}, "trade_quantum_automation"),
        )
        self.assertTrue(captain.quantum_done)
        self.assertIsNone(captain._quantum_freight_action())

    def test_nothing_runs_before_the_campaign(self):
        self.assertIsNone(_captain(completed=False)._quantum_freight_action())

    def test_a_landed_captain_does_not_run_freight(self):
        self.assertIsNone(_captain(docked=False)._quantum_freight_action())

    def test_an_unprofitable_hold_gives_up_after_the_idle_limit(self):
        captain = _captain(
            cargo={"fuel_cells": 6},
            idle=AiCaptain.QUANTUM_IDLE_LIMIT - 1,
        )
        self.assertIsNone(captain._quantum_freight_action())
        self.assertTrue(captain.quantum_done)

    def test_a_delivered_order_resets_the_idle_count(self):
        captain = _captain(cargo={"fuel_cells": 6}, orders=2, idle=5, last_orders=1)
        self.assertEqual(captain._quantum_freight_action()[0], "/api/time/step")
        self.assertEqual(captain.quantum_idle, 1)

    def test_the_target_mirrors_the_codex_entry(self):
        entry = next(row for row in CODEX_ENTRIES if row.id == "quantum_broker")
        self.assertEqual(AiCaptain.QUANTUM_ORDER_TARGET, entry.target)


if __name__ == "__main__":
    unittest.main()
