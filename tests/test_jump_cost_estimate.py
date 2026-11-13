"""The route planner's fuel estimate equals what a jump really spends, so cockpit, CLI and rescue logic can trust it."""

from __future__ import annotations

import unittest

from voidfarer.engine import SimulationEngine

POWERS = ((30, 25, 25, 20), (60, 15, 15, 10), (10, 30, 30, 30), (40, 20, 20, 20))


def _engine(seed: int, power: tuple[int, int, int, int], fuel: int = 60) -> SimulationEngine:
    engine = SimulationEngine(seed=seed)
    engine.allow_decision_events = False
    engine.pause_time()
    engine.route_power(*power)
    engine.state = engine._clone_state(ship=engine._clone_ship(fuel=fuel))
    return engine


class TestJumpCostEstimate(unittest.TestCase):
    def test_single_hop_estimate_equals_the_fuel_a_jump_spends(self) -> None:
        for seed in (1, 5, 42):
            for power in POWERS:
                probe = _engine(seed, power)
                for target in list(probe.current_system.connections):
                    estimate = probe.plan_route(target)["fuel_estimate"]
                    engine = _engine(seed, power)
                    before = engine.state.ship.fuel
                    ok, message = engine.jump(target)
                    self.assertTrue(ok, message)
                    self.assertEqual(estimate, before - engine.state.ship.fuel, (seed, power, target))

    def test_public_cost_helper_matches_the_estimate_for_a_direct_lane(self) -> None:
        engine = _engine(42, (60, 15, 15, 10))
        target = engine.current_system.connections[0]
        self.assertEqual(engine.jump_fuel_cost(target), engine.plan_route(target)["fuel_estimate"])

    def test_multi_hop_estimate_is_the_sum_of_its_hops(self) -> None:
        engine = _engine(42, (40, 20, 20, 20))
        far = next(
            sid for sid in engine.state.systems
            if engine.plan_route(sid).get("reachable") and engine.plan_route(sid)["jumps"] >= 2
        )
        plan = engine.plan_route(far)
        systems = engine.state.systems
        hops = sum(
            engine._hop_fuel_cost(systems[a], systems[b]) for a, b in zip(plan["path"], plan["path"][1:])
        )
        self.assertEqual(plan["fuel_estimate"], max(1, hops))

    def test_rescue_verdict_uses_the_true_cost(self) -> None:
        engine = _engine(42, (30, 25, 25, 20))
        cheapest = min(engine.jump_fuel_cost(t) for t in engine.current_system.connections)
        affordable = _engine(42, (30, 25, 25, 20), fuel=cheapest)
        affordable.state = affordable._clone_state(ship=affordable._clone_ship(fuel=cheapest, cargo={}))
        self.assertFalse(affordable.rescue_status()["available"])
        short = _engine(42, (30, 25, 25, 20), fuel=cheapest - 1)
        short.state = short._clone_state(ship=short._clone_ship(fuel=cheapest - 1, cargo={}))
        self.assertTrue(short.rescue_status()["available"])


if __name__ == "__main__":
    unittest.main()
