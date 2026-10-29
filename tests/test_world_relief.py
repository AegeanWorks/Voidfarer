"""Post-war reconstruction, relief cargo and the market premium for bombed worlds."""

from dataclasses import replace
import random
import unittest

from voidfarer.codex import metric_value
from voidfarer.demographics import effective_capacity
from voidfarer.economy import calculate_dynamic_market_quote
from voidfarer.engine import SimulationEngine
from voidfarer.galaxy import COMMODITY_MAP
from voidfarer.faction_state import simulate_faction_behaviors
from voidfarer.models import WarState


class WorldReliefEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.body = next(
            body for body in self.engine.current_system.bodies
            if body.population > 0 and body.faction != "Unclaimed"
        )
        systems = dict(self.engine.state.systems)
        system = systems[self.engine.current_system.id]
        systems[system.id] = replace(
            system,
            bodies=tuple(
                replace(candidate, devastation=60.0) if candidate.id == self.body.id else candidate
                for candidate in system.bodies
            ),
        )
        self.engine.state = self.engine._clone_state(
            systems=systems,
            ship=self.engine._clone_ship(
                orbiting_body_id=self.body.id,
                landed_body_id=None,
                credits=5000,
                cargo={"medicines": 2, "hydroponics": 2, "fuel_cells": 1},
            ),
        )

    def _body(self):
        return next(
            body for body in self.engine.current_system.bodies
            if body.id == self.body.id
        )

    def test_credits_rebuild_reduces_devastation_and_earns_standing(self):
        before_capacity = effective_capacity(self._body().population_capacity, 60.0)
        ok, message = self.engine.reconstruct_world(self.body.id, "credits")
        self.assertTrue(ok, message)
        body = self._body()
        self.assertAlmostEqual(body.devastation, 40.0)
        self.assertGreater(
            effective_capacity(body.population_capacity, body.devastation),
            before_capacity,
        )
        self.assertEqual(self.engine.state.ship.credits, 4400)
        self.assertEqual(self.engine.state.stats.get("worlds_rebuilt"), 1)
        self.assertEqual(metric_value(self.engine.state, "worlds_rebuilt"), 1)
        self.assertTrue(any(event.kind == "reconstruction" for event in self.engine.state.events))
        self.assertTrue(any("REBUILD" in line.upper() for line in self.engine.state.ship.flight_log))

    def test_relief_cargo_reduces_more_devastation_and_lifts_morale(self):
        before_morale = sum(member.morale for member in self.engine.state.ship.crew) / len(self.engine.state.ship.crew)
        ok, message = self.engine.reconstruct_world(self.body.id, "relief")
        self.assertTrue(ok, message)
        self.assertAlmostEqual(self._body().devastation, 20.0)
        self.assertEqual(self.engine.state.ship.cargo, {})
        after_morale = sum(member.morale for member in self.engine.state.ship.crew) / len(self.engine.state.ship.crew)
        self.assertGreater(after_morale, before_morale)
        self.assertEqual(self.engine.state.stats.get("relief_deliveries"), 1)
        self.assertTrue(any(event.kind == "relief" for event in self.engine.state.events))

    def test_reconstruction_requires_orbit_and_damage(self):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(orbiting_body_id=None))
        ok, message = self.engine.reconstruct_world(self.body.id, "credits")
        self.assertFalse(ok)
        self.assertIn("orbit", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id=self.body.id)
        )
        systems = dict(self.engine.state.systems)
        system = systems[self.engine.current_system.id]
        systems[system.id] = replace(
            system,
            bodies=tuple(
                replace(candidate, devastation=0.0) if candidate.id == self.body.id else candidate
                for candidate in system.bodies
            ),
        )
        self.engine.state = self.engine._clone_state(systems=systems)
        ok, message = self.engine.reconstruct_world(self.body.id, "credits")
        self.assertFalse(ok)
        self.assertIn("not devastated", message.lower())

    def test_relief_refuses_when_cargo_is_missing(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                orbiting_body_id=self.body.id,
                credits=5000,
                cargo={"medicines": 1},
            )
        )
        ok, message = self.engine.reconstruct_world(self.body.id, "relief")
        self.assertFalse(ok)
        self.assertIn("medicines", message.lower())
        self.assertAlmostEqual(self._body().devastation, 60.0)

    def test_unknown_mode_is_rejected(self):
        ok, message = self.engine.reconstruct_world(self.body.id, "magic")
        self.assertFalse(ok)
        self.assertIn("credits", message.lower())


class DevastationMarketTest(unittest.TestCase):
    def test_bombed_world_pays_a_relief_premium(self):
        engine = SimulationEngine(seed=42)
        body = next(body for body in engine.current_system.bodies if body.population > 0)
        commodity = COMMODITY_MAP["medicines"]
        healthy = calculate_dynamic_market_quote(
            engine.current_system, replace(body, devastation=0.0), commodity, engine.state.economy
        )
        bombed = calculate_dynamic_market_quote(
            engine.current_system, replace(body, devastation=70.0), commodity, engine.state.economy
        )
        self.assertGreater(bombed.buy_price, healthy.buy_price)
        self.assertGreater(bombed.demand, healthy.demand)


class OrphanedWarCleanupTest(unittest.TestCase):
    def test_a_war_against_a_territory_less_faction_is_closed(self):
        engine = SimulationEngine(seed=42)
        systems = {
            sid: replace(system, faction="Unclaimed") if system.faction == "Precursor Watch" else system
            for sid, system in engine.state.systems.items()
        }
        war = WarState(
            id="w_orphan",
            attacker_id="nebula_collective",
            defender_id="precursor_watch",
            started_tick=10,
            war_score=0.0,
        )
        wars, _, eliminated, logs = simulate_faction_behaviors(
            (), (war,), systems, random.Random(1), 50, ()
        )
        self.assertFalse(wars[0].active)
        self.assertIn("precursor_watch", eliminated)
        self.assertTrue(any("territory" in line.lower() for line in logs))


if __name__ == "__main__":
    unittest.main()
