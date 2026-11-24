"""The chaos fuzz tool must catch every rule class it claims to check (ADR-414)."""

from __future__ import annotations

import unittest
from dataclasses import replace

from tools.chaos_fuzz import COMBAT_ACTIONS, Findings, choose_action, check_invariants, run_seed
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
        reactor=replace(ship.reactor, heat=500.0, integrity=250.0),
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


class FuzzActionCatalogTest(unittest.TestCase):
    def test_every_fuzz_combat_action_is_a_real_engine_verb(self):
        engine = SimulationEngine(seed=42)
        from tests.test_combat_save_parity import _combat_engine
        combat = _combat_engine()
        for action in COMBAT_ACTIONS:
            ok, message = combat.combat_action(action)
            self.assertFalse(
                str(message).startswith("Unknown combat action"),
                f"fuzz action '{action}' never reaches combat logic: {message}",
            )


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
            "heat_over_capacity",
            "core_integrity_bounds",
            "negative_population",
            "population_over_capacity",
            "devastation_range",
            "outpost_level",
            "negative_depot",
        })

    def test_the_checker_catches_negative_heat(self):
        engine = SimulationEngine(seed=3)
        engine.state = replace(
            engine.state,
            ship=replace(
                engine.state.ship,
                reactor=replace(engine.state.ship.reactor, heat=-1.0),
            ),
        )
        findings = Findings()
        check_invariants(engine, findings, "synthetic")
        self.assertIn("negative_heat", {row["kind"] for row in findings.violations})

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

    def test_save_interleaving_round_trips_without_drift(self):
        findings = Findings()
        run_seed(seed=3, actions=20, findings=findings, save_every=5)
        self.assertEqual(findings.crashes, [])
        self.assertEqual(findings.violations, [])
        self.assertEqual(findings.reloads, 4)

    def test_round_trip_returns_an_engine_at_the_same_tick(self):
        from tempfile import TemporaryDirectory
        from tools.chaos_fuzz import round_trip
        engine = SimulationEngine(seed=3)
        engine.tick(3)
        tick = engine.state.time.tick
        with TemporaryDirectory() as temp_dir:
            findings = Findings()
            resumed = round_trip(engine, temp_dir, findings, "tick@test")
        self.assertEqual(findings.reloads, 1)
        self.assertEqual(findings.violations, [])
        self.assertEqual(resumed.state.time.tick, tick)


if __name__ == "__main__":
    unittest.main()
