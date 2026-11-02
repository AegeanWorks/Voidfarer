"""Half-simulation tick proofs: economy, factions, and crew drift with zero player input.

Each test advances the world through seeded RNG only -- no trades, no jumps,
no combat, no decisions -- and asserts the world state moved. Determinism is
pinned by running two identically seeded engines and comparing snapshots.
"""

import random
import unittest

from voidfarer.crew import tick_crew
from voidfarer.economy import tick_global_economy
from voidfarer.engine import SimulationEngine
from voidfarer.models import CrewMember


def _member(member_id="c1", morale=80.0, wage=30):
    return CrewMember(
        id=member_id,
        name=f"Crew {member_id}",
        role="pilot",
        skill=3,
        morale=morale,
        wage=wage,
        portrait="crew_01",
        specialty="evasion",
        status="active",
    )


def _world_snapshot(engine):
    """Comparable snapshot of the ticking world state."""
    econ = engine.state.economy
    return {
        "tick": engine.state.time.tick,
        "stardate": round(engine.state.time.stardate, 4),
        "stocks": {
            sys_id: dict(market.stockpiles)
            for sys_id, market in econ.markets.items()
        },
        "treasuries": tuple(
            (eco.faction_id, round(eco.treasury, 2))
            for eco in engine.state.faction_economies
        ),
        "morale": tuple(round(m.morale, 1) for m in engine.state.ship.crew),
        "credits": engine.state.ship.credits,
    }


class TestHalfSimEconomyDrift(unittest.TestCase):
    def test_stockpiles_drift_with_no_player_input(self):
        engine = SimulationEngine(seed=7)
        before = _world_snapshot(engine)
        engine.tick(12)
        after = _world_snapshot(engine)
        self.assertEqual(after["tick"], before["tick"] + 12)
        self.assertNotEqual(after["stardate"], before["stardate"])
        self.assertNotEqual(after["stocks"], before["stocks"])

    def test_economy_tick_is_deterministic_for_seed(self):
        first = SimulationEngine(seed=7)
        second = SimulationEngine(seed=7)
        first.tick(12)
        second.tick(12)
        self.assertEqual(_world_snapshot(first), _world_snapshot(second))

    def test_pure_economy_tick_is_deterministic_for_seed(self):
        engine = SimulationEngine(seed=7)
        left, _ = tick_global_economy(
            engine.state.economy, 8, engine.state.systems, random.Random(11)
        )
        right, _ = tick_global_economy(
            engine.state.economy, 8, engine.state.systems, random.Random(11)
        )
        self.assertEqual(left.markets["sol"].stockpiles, right.markets["sol"].stockpiles)


class TestHalfSimFactionDrift(unittest.TestCase):
    def test_faction_treasuries_move_with_no_player_input(self):
        engine = SimulationEngine(seed=7)
        before = _world_snapshot(engine)
        engine.tick(24)
        after = _world_snapshot(engine)
        self.assertEqual(after["tick"], before["tick"] + 24)
        self.assertNotEqual(after["treasuries"], before["treasuries"])

    def test_faction_tick_is_deterministic_for_seed(self):
        first = SimulationEngine(seed=9)
        second = SimulationEngine(seed=9)
        first.tick(24)
        second.tick(24)
        self.assertEqual(_world_snapshot(first), _world_snapshot(second))


class TestHalfSimCrewNeeds(unittest.TestCase):
    def test_unpaid_crew_morale_falls_without_player_input(self):
        crew = (_member("c1", morale=80.0),)
        updated, paid, logs = tick_crew(crew, 10, 0, rng=random.Random(5))
        self.assertEqual(paid, 0)
        self.assertLess(updated[0].morale, 80.0)
        self.assertTrue(any("UNPAID" in line for line in logs))

    def test_paid_crew_morale_recovers_without_player_input(self):
        crew = (_member("c1", morale=50.0),)
        updated, paid, logs = tick_crew(crew, 10, 10_000, rng=random.Random(5))
        self.assertGreater(updated[0].morale, 50.0)
        self.assertFalse(any("resigned" in line.lower() for line in logs))

    def test_crew_tick_is_deterministic_for_seed(self):
        crew = (_member("c1", morale=20.0),)
        left, _, _ = tick_crew(crew, 5, 0, rng=random.Random(5))
        right, _, _ = tick_crew(crew, 5, 0, rng=random.Random(5))
        self.assertEqual([m.morale for m in left], [m.morale for m in right])

    def test_engine_tick_moves_crew_state_with_no_player_input(self):
        first = SimulationEngine(seed=7)
        second = SimulationEngine(seed=7)
        first.tick(20)
        second.tick(20)
        self.assertEqual(_world_snapshot(first)["morale"], _world_snapshot(second)["morale"])


if __name__ == "__main__":
    unittest.main()
