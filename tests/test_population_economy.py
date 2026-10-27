"""Population capacity, technology limits, wartime devastation and faction treasuries."""

import random
import re
import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer.demographics import (
    DEVASTATION_CAPACITY_LOSS,
    compute_population_capacity,
    devastation_recovery,
    step_population,
)
from voidfarer.engine import SimulationEngine
from voidfarer.faction_economy import compute_faction_economy, tick_faction_economies
from voidfarer.faction_state import (
    _apply_owner_technology,
    apply_war_devastation,
    force_peace_for_broke_factions,
    frontier_systems,
    generate_faction_leaders,
    resolve_wars,
    simulate_faction_behaviors,
)
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import FactionEconomy, GameState, WarState
from voidfarer.outposts import (
    build_outpost,
    get_outpost_type,
    grow_outpost_population,
    upgrade_outpost,
)


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

    def test_civil_order_changes_population_growth(self):
        stable = step_population(1_000_000, 10_000_000, 80.0, 8, 0.0, 40, 90.0)
        unstable = step_population(1_000_000, 10_000_000, 80.0, 8, 0.0, 40, 10.0)
        self.assertGreater(stable, unstable)

    def test_devastation_recovery_scales_with_tech_and_order(self):
        self.assertGreater(devastation_recovery(9, 90.0), devastation_recovery(9, 20.0))
        self.assertGreater(devastation_recovery(9, 90.0), devastation_recovery(3, 90.0))

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
    def test_capture_retunes_worlds_to_the_new_owner_technology(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        system = next(
            s for s in systems.values()
            if any(b.body_type == "savanna" and b.population > 0 for b in s.bodies)
        )
        before = next(b for b in system.bodies if b.body_type == "savanna")
        retuned = _apply_owner_technology(system, "Void Corsairs")
        after = next(b for b in retuned.bodies if b.body_type == "savanna")
        self.assertLess(after.tech_level, before.tech_level)
        self.assertLess(after.population_capacity, before.population_capacity)
        self.assertLessEqual(after.population, after.population_capacity)
        self.assertEqual(after.faction, "Void Corsairs")
        self.assertEqual(after.government, "Pirate Warlordship")

    def test_broke_faction_cannot_open_a_new_front(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        leaders = generate_faction_leaders(seed=42)
        wars, _, _, logs = simulate_faction_behaviors(
            leaders,
            (),
            systems,
            FixedZeroRng(),
            10,
            (),
            1,
            frozenset(leader.faction_id for leader in leaders),
        )
        self.assertEqual(wars, ())
        self.assertFalse(any("WAR DECLARED" in line for line in logs))

    def test_outposts_grow_to_their_housing_ceiling_and_stop(self):
        body = GalaxyGenerator(seed=42).generate_galaxy()["sol"].bodies[2]
        outpost = build_outpost(get_outpost_type("mining"), "sol", body, 0, 0)
        self.assertEqual(outpost.population_capacity, 6_000)
        late = grow_outpost_population(outpost, 10_000_000)
        self.assertEqual(late, outpost.population_capacity)
        upgraded = upgrade_outpost(outpost)[1]
        self.assertEqual(upgraded.population_capacity, 12_000)
        self.assertLessEqual(upgraded.population, upgraded.population_capacity)

    def test_cockpit_capacity_constant_matches_python(self):
        app_js = (Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "app.js").read_text(
            encoding="utf-8"
        )
        match = re.search(r"const DEVASTATION_CAPACITY_LOSS = ([0-9.]+);", app_js)
        self.assertIsNotNone(match)
        self.assertAlmostEqual(float(match.group(1)), DEVASTATION_CAPACITY_LOSS)

    def test_batched_resolution_advances_wars_across_the_batch(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        war = WarState(
            id="w_batch",
            attacker_id="sol_coalition",
            defender_id="nebula_collective",
            started_tick=50,
            war_score=40.0,
        )
        single, _, _, _ = resolve_wars((war,), systems, FixedZeroRng(), 100, (), 1)
        batched, _, _, _ = resolve_wars((war,), systems, FixedZeroRng(), 100, (), 25)
        single_captures = len(single[0].captured_systems)
        batched_captures = len(batched[0].captured_systems)
        if not frontier_systems("Sol Coalition", "Nebula Collective", systems):
            self.skipTest("seed 42 has no Sol/Nebula border")
        self.assertGreater(batched_captures, single_captures)

    def test_bankrupt_faction_sues_for_peace(self):
        war = WarState(
            id="w_broke",
            attacker_id="sol_coalition",
            defender_id="nebula_collective",
            started_tick=0,
        )
        broken = FactionEconomy(
            faction_id="sol_coalition", treasury=0, net_income=-500, stability=20.0
        )
        solvent = FactionEconomy(
            faction_id="nebula_collective", treasury=5_000, net_income=400, stability=60.0
        )
        wars, logs = force_peace_for_broke_factions((war,), (broken, solvent), 120)
        self.assertFalse(wars[0].active)
        self.assertEqual(wars[0].ended_tick, 120)
        self.assertTrue(any("BANKRUPT PEACE" in line for line in logs))

    def test_solvent_factions_keep_fighting(self):
        war = WarState(
            id="w_solvent",
            attacker_id="sol_coalition",
            defender_id="nebula_collective",
            started_tick=0,
        )
        rich = FactionEconomy(
            faction_id="sol_coalition", treasury=10_000, net_income=300, stability=60.0
        )
        wars, logs = force_peace_for_broke_factions((war,), (rich,), 120)
        self.assertTrue(wars[0].active)
        self.assertEqual(logs, [])

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
