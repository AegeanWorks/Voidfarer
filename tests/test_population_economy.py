"""Population capacity, technology limits, wartime devastation and faction treasuries."""

import random
import unittest
from dataclasses import replace

from voidfarer.demographics import compute_population_capacity, step_population
from voidfarer.engine import SimulationEngine
from voidfarer.faction_economy import compute_faction_economy, tick_faction_economies
from voidfarer.faction_state import apply_war_devastation
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import GameState, WarState


class FixedZeroRng(random.Random):
    """Random source that always fires the attrition roll and returns zero noise."""

    def random(self) -> float:
        return 0.0

    def uniform(self, low: float, high: float) -> float:
        return 0.0


class TestPopulationCapacity(unittest.TestCase):
    def test_generated_worlds_are_normalized_to_their_capacity(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        for system in systems.values():
            for body in system.bodies:
                self.assertGreaterEqual(body.tech_level, 1)
                self.assertLessEqual(body.tech_level, 10)
                if body.population > 0:
                    self.assertGreater(body.population_capacity, 0, body.name)
                    self.assertLessEqual(body.population, body.population_capacity, body.name)

    def test_technology_and_habitability_raise_capacity(self):
        low = compute_population_capacity("terrestrial", 6371.0, 90.0, 2)
        high = compute_population_capacity("terrestrial", 6371.0, 90.0, 9)
        hostile = compute_population_capacity("terrestrial", 6371.0, 25.0, 9)
        self.assertGreater(high, low)
        self.assertGreater(low, hostile)

    def test_batched_ticks_never_overshoot_capacity(self):
        cap = 8_000_000_000
        for ticks in (1, 30, 500, 2000):
            grown = step_population(1_000_000_000, cap, 95.0, 8, 0.0, ticks)
            self.assertLessEqual(grown, cap)
            self.assertGreaterEqual(grown, 1_000_000_000)

    def test_growth_stops_at_capacity_and_devastation_reverses_it(self):
        full = step_population(1_000_000, 1_000_000, 90.0, 8, 0.0, 20)
        self.assertGreaterEqual(full, 1_000_000)
        self.assertLessEqual(full, 1_000_000 + 1)
        healthy = step_population(100_000, 10_000_000, 90.0, 8, 0.0, 20)
        ruined = step_population(100_000, 10_000_000, 90.0, 8, 90.0, 20)
        self.assertGreater(healthy, 100_000)
        self.assertLess(ruined, healthy)

    def test_dyson_swarm_is_a_small_maintenance_population_not_a_planet(self):
        sol = GalaxyGenerator(seed=42).generate_galaxy()["sol"]
        swarm = next(body for body in sol.bodies if body.body_type == "dyson_sphere")
        self.assertIn("Swarm", swarm.name)
        self.assertLess(swarm.population, 1_000_000_000)
        self.assertLess(swarm.population_capacity, 1_000_000_000)
        self.assertEqual(swarm.tech_level, 10)


class TestWarDevastation(unittest.TestCase):
    def test_front_worlds_lose_people_and_gain_devastation(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        war = WarState(
            id="w_front",
            attacker_id="sol_coalition",
            defender_id="nebula_collective",
            started_tick=0,
            war_score=6.0,
        )
        from voidfarer.faction_state import frontier_systems

        front = frontier_systems("Sol Coalition", "Nebula Collective", systems)
        if not front:
            self.skipTest("seed 42 has no Sol/Nebula border")
        target = next(
            (sid for sid in front if any(body.population > 0 for body in systems[sid].bodies)),
            None,
        )
        if target is None:
            self.skipTest("front systems are uninhabited")
        before_pop = sum(body.population for body in systems[target].bodies)
        before_dev = sum(body.devastation for body in systems[target].bodies)
        updated, logs = apply_war_devastation((war,), systems, FixedZeroRng(), 5)
        after_pop = sum(body.population for body in updated[target].bodies)
        after_dev = sum(body.devastation for body in updated[target].bodies)
        self.assertLess(after_pop, before_pop)
        self.assertGreater(after_dev, before_dev)
        self.assertTrue(logs)


class TestFactionEconomy(unittest.TestCase):
    def test_every_surviving_faction_has_a_treasury_and_cash_flow(self):
        engine = SimulationEngine(seed=42)
        economies = {e.faction_id: e for e in engine.state.faction_economies}
        self.assertIn("sol_coalition", economies)
        self.assertIn("outlaw_corsairs", economies)
        for economy in economies.values():
            self.assertGreater(economy.treasury, 0)
            self.assertGreater(economy.population, 0)
            self.assertGreater(economy.worlds, 0)
            self.assertGreaterEqual(economy.net_income, -100_000)

    def test_war_adds_upkeep_and_reduces_net_income(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        peace = compute_faction_economy("sol_coalition", systems, (), treasury=100_000)
        war = WarState(
            id="w_econ",
            attacker_id="sol_coalition",
            defender_id="nebula_collective",
            started_tick=0,
        )
        wartime = compute_faction_economy("sol_coalition", systems, (war,), treasury=100_000)
        self.assertGreater(wartime.military_upkeep, peace.military_upkeep)
        self.assertGreater(wartime.war_burden, 0.0)
        self.assertLess(wartime.net_income, peace.net_income)

    def test_tick_pays_income_into_the_treasury(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        engine = SimulationEngine(seed=42)
        start = next(e for e in engine.state.faction_economies if e.faction_id == "sol_coalition")
        updated, _ = tick_faction_economies(
            (start,), systems, (), (), num_ticks=10
        )
        self.assertGreater(updated[0].treasury, start.treasury)
        self.assertAlmostEqual(updated[0].treasury, start.treasury + start.net_income * 10, delta=1000)

    def test_faction_economies_survive_a_game_state_round_trip(self):
        engine = SimulationEngine(seed=42)
        data = engine.state.to_dict()
        restored = GameState.from_dict(data)
        self.assertEqual(restored.faction_economies, engine.state.faction_economies)

    def test_batched_tick_still_declares_wars_and_scars_worlds(self):
        engine = SimulationEngine(seed=42)
        engine.tick(50)
        self.assertTrue(engine.state.wars)
        self.assertTrue(
            any(body.devastation > 0 for system in engine.state.systems.values() for body in system.bodies)
        )

    def test_reload_does_not_repopulate_a_war_killed_world(self):
        engine = SimulationEngine(seed=42)
        sol = engine.state.systems["sol"]
        index = next(i for i, body in enumerate(sol.bodies) if body.body_type == "ring_world")
        dead = replace(sol.bodies[index], population=0, devastation=60.0)
        bodies = sol.bodies[:index] + (dead,) + sol.bodies[index + 1:]
        engine.state = engine._clone_state(
            systems={**engine.state.systems, "sol": replace(sol, bodies=bodies)}
        )
        restored = SimulationEngine(state=GameState.from_dict(engine.state.to_dict()))
        body = next(b for b in restored.state.systems["sol"].bodies if b.body_type == "ring_world")
        self.assertEqual(body.population, 0)
        self.assertEqual(body.devastation, 60.0)

    def test_war_tick_lowers_front_population(self):
        engine = SimulationEngine(seed=42)
        from voidfarer.faction_state import frontier_systems

        front = frontier_systems("Sol Coalition", "Nebula Collective", engine.state.systems)
        if not front:
            self.skipTest("seed 42 has no Sol/Nebula border")
        war = WarState(
            id="w_live",
            attacker_id="sol_coalition",
            defender_id="nebula_collective",
            started_tick=0,
        )
        engine.state = engine._clone_state(wars=(war,))
        before = sum(
            sum(body.population for body in engine.state.systems[sid].bodies)
            for sid in front
        )
        engine.tick(10)
        after = sum(
            sum(body.population for body in engine.state.systems[sid].bodies)
            for sid in front
        )
        self.assertLess(after, before)
        self.assertTrue(any(body.devastation > 0 for sid in front for body in engine.state.systems[sid].bodies))


if __name__ == "__main__":
    unittest.main()
