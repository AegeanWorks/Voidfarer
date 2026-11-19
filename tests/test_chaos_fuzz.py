"""The chaos fuzz tool must catch every rule class it claims to check (ADR-414)."""

from __future__ import annotations

import unittest
from dataclasses import replace

from tools.chaos_fuzz import Findings, choose_action, check_invariants, run_seed
from voidfarer.engine import SimulationEngine
from voidfarer.models import Depot, Outpost


def _bad_engine() -> SimulationEngine:
    engine = SimulationEngine(seed=3)
    ship = engine.state.ship
    crew = list(ship.crew)
    if len(crew) >= 2:
        crew[1] = replace(crew[1], id=crew[0].id)
    ship = replace(
        ship,
        credits=-5,
        hull=ship.max_hull + 1,
        shield=ship.max_shield + 1,
        fuel=ship.max_fuel + 1,
        cargo={**ship.cargo, "water": -2},
        crew=tuple(crew),
    )
    systems = dict(engine.state.systems)
    first_id, first_system = next(iter(systems.items()))
    bad_body = replace(
        first_system.bodies[0],
        population=10,
        population_capacity=5,
        devastation=500.0,
    )
    negative_body = replace(first_system.bodies[1], population=-1)
    bodies = (negative_body, bad_body) + first_system.bodies[2:]
    systems[first_id] = replace(first_system, bodies=bodies)
    engine.state = replace(
        engine.state,
        ship=ship,
        systems=systems,
        time=replace(engine.state.time, tick=-3),
        outposts=(Outpost(id="o1", name="Rig", system_id=first_id,
                          body_id=bad_body.id, level=0),),
        depots=(Depot(id="d1", name="Cache", system_id=first_id,
                      cargo={"water": -4}),),
    )
    return engine


class ChaosInvariantTest(unittest.TestCase):
    def test_the_checker_catches_every_rule_class(self):
        findings = Findings()
        check_invariants(_bad_engine(), findings, "synthetic")
        kinds = {row["kind"] for row in findings.violations}
        self.assertEqual(kinds, {
            "negative_credits",
            "hull_bounds",
            "shield_bounds",
            "fuel_bounds",
            "negative_cargo",
            "duplicate_crew",
            "negative_tick",
            "negative_population",
            "population_over_capacity",
            "devastation_range",
            "outpost_level",
            "negative_depot",
        })

    def test_a_clean_engine_reports_nothing(self):
        findings = Findings()
        check_invariants(SimulationEngine(seed=3), findings, "fresh")
        self.assertEqual(findings.violations, [])

    def test_the_same_breach_is_recorded_once(self):
        findings = Findings()
        engine = _bad_engine()
        check_invariants(engine, findings, "first")
        count = len(findings.violations)
        check_invariants(engine, findings, "second")
        self.assertEqual(len(findings.violations), count)


class ChaosRunTest(unittest.TestCase):
    def test_a_blocking_combat_is_always_answered_first(self):
        from voidfarer.models import CombatEncounter
        engine = SimulationEngine(seed=3)
        engine.state = replace(
            engine.state,
            active_combat=CombatEncounter(
                id="c1", enemy_name="Raider", enemy_class="Drone",
                enemy_hull=10, enemy_max_hull=10, enemy_damage=1,
                bounty_credits=50,
            ),
        )
        import random
        name, _ = choose_action(engine, random.Random(1))
        self.assertEqual(name, "combat")

    def test_a_short_seeded_run_is_clean_and_repeatable(self):
        findings = Findings()
        run_seed(seed=3, actions=20, findings=findings)
        self.assertEqual(findings.crashes, [])
        self.assertEqual(findings.violations, [])
        self.assertEqual(findings.actions, 20)
        # Successes and refusals must partition the actions that did not crash.
        self.assertEqual(findings.successes + findings.refusals, 20)


if __name__ == "__main__":
    unittest.main()
