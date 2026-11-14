"""Neighbouring markets never pay absurd arbitrage, and trading still pays (ADR-289)."""

from __future__ import annotations

import unittest

from voidfarer.economy import calculate_dynamic_market_quote
from voidfarer.engine import CANONICAL_COMMODITIES, SimulationEngine


def _lane_ratios(seed: int) -> list[float]:
    engine = SimulationEngine(seed=seed)
    market = engine._destination_market_body
    ratios: list[float] = []
    for system in engine.state.systems.values():
        source = market(system)
        if source is None:
            continue
        for neighbour_id in system.connections:
            neighbour = engine.state.systems[neighbour_id]
            target = market(neighbour)
            if target is None:
                continue
            for commodity in CANONICAL_COMMODITIES:
                buy = calculate_dynamic_market_quote(system, source, commodity, engine.state.economy).buy_price
                sell = calculate_dynamic_market_quote(neighbour, target, commodity, engine.state.economy).sell_price
                ratios.append(sell / max(1, buy))
    return sorted(ratios)


class MarketPriceGapTests(unittest.TestCase):
    def test_the_best_lane_is_bounded_and_trading_still_pays(self) -> None:
        for seed in (1, 2):
            ratios = _lane_ratios(seed)
            p99 = ratios[int(len(ratios) * 0.99)]
            self.assertLessEqual(ratios[-1], 2.0, f"seed {seed}: best lane pays {ratios[-1]:.2f}x")
            self.assertLessEqual(p99, 1.6, f"seed {seed}: p99 lane pays {p99:.2f}x")
            profitable = sum(ratio >= 1.1 for ratio in ratios) / len(ratios)
            self.assertGreater(profitable, 0.07, f"seed {seed}: only {profitable:.1%} of lanes pay 10% or more")


if __name__ == "__main__":
    unittest.main()
