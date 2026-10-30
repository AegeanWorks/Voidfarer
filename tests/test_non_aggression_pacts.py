"""Non-aggression pacts: standing gate, expiry and war exclusion."""

from dataclasses import replace
import random
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.faction_state import simulate_faction_behaviors
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import FactionLeader, WarState


class NonAggressionPactTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        standings = dict(self.engine.state.ship.faction_standings)
        standings["nebula_collective"] = 30
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(faction_standings=standings)
        )

    def test_pact_requires_standing_30_and_forms_once(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                faction_standings={"nebula_collective": 0}
            )
        )
        ok, message = self.engine.faction_diplomacy("nebula_collective", "non_aggression")
        self.assertFalse(ok)
        self.assertIn("standing", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                faction_standings={"nebula_collective": 30}
            )
        )
        ok, message = self.engine.faction_diplomacy("nebula_collective", "non_aggression")
        self.assertTrue(ok, message)
        self.assertIn("NON-AGGRESSION PACT", message)
        self.assertTrue(self.engine.non_aggression_active("nebula_collective"))
        self.assertGreater(self.engine.non_aggression_remaining("nebula_collective"), 0)

        ok, message = self.engine.faction_diplomacy("nebula_collective", "non_aggression")
        self.assertFalse(ok)
        self.assertIn("already hold", message.lower())

    def test_own_faction_and_war_are_rejected(self):
        ok, message = self.engine.faction_diplomacy("sol_coalition", "non_aggression")
        self.assertFalse(ok)
        self.assertIn("own polity", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                faction_standings={"nebula_collective": 30}
            ),
            wars=(
                WarState(
                    id="nap_war",
                    attacker_id="nebula_collective",
                    defender_id="sol_coalition",
                    started_tick=0,
                ),
            ),
        )
        ok, message = self.engine.faction_diplomacy("nebula_collective", "non_aggression")
        self.assertFalse(ok)
        self.assertIn("war", message.lower())

    def test_expiry_removes_protection(self):
        self.assertTrue(
            self.engine.faction_diplomacy("nebula_collective", "non_aggression")[0]
        )
        until = self.engine.state.ship.non_aggression_until["nebula_collective"]
        self.assertEqual(
            self.engine.non_aggression_remaining("nebula_collective"),
            self.engine.NON_AGGRESSION_TICKS,
        )
        self.engine.state = self.engine._clone_state(
            time=replace(self.engine.state.time, tick=until)
        )
        self.assertFalse(self.engine.non_aggression_active("nebula_collective"))
        self.assertEqual(self.engine.non_aggression_remaining("nebula_collective"), 0)

    def test_pacts_round_trip_and_legacy_default(self):
        self.assertTrue(
            self.engine.faction_diplomacy("nebula_collective", "non_aggression")[0]
        )
        restored = type(self.engine.state).from_dict(self.engine.state.to_dict())
        self.assertIn("nebula_collective", restored.ship.non_aggression_until)
        payload = self.engine.state.to_dict()
        payload["ship"].pop("non_aggression_until", None)
        legacy = type(self.engine.state).from_dict(payload)
        self.assertEqual(legacy.ship.non_aggression_until, {})


class NonAggressionWarTest(unittest.TestCase):
    def _systems_and_leaders(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        sol = next(s for s in systems.values() if s.faction == "Sol Coalition")
        nebula = next(s for s in systems.values() if s.faction == "Nebula Collective")
        leaders = (
            FactionLeader(
                id="leader_sol", faction_id="sol_coalition", name="Vance",
                title="Admiral", behavior="militarist", aggression=1.0,
            ),
            FactionLeader(
                id="leader_nebula", faction_id="nebula_collective", name="Nyx",
                title="Speaker", behavior="militarist", aggression=1.0,
            ),
        )
        return {sol.id: sol, nebula.id: nebula}, leaders

    def test_active_pact_blocks_a_new_sol_coalition_war(self):
        systems, leaders = self._systems_and_leaders()
        baseline_rng = random.Random(9)
        baseline_rng.random = lambda: 0.0
        baseline, _, _, _ = simulate_faction_behaviors(
            leaders, (), systems, baseline_rng, 10, ()
        )
        self.assertEqual(len(baseline), 1, baseline)

        protected_rng = random.Random(9)
        protected_rng.random = lambda: 0.0
        protected, _, _, _ = simulate_faction_behaviors(
            leaders,
            (),
            systems,
            protected_rng,
            10,
            (),
            non_aggression_pairs=frozenset(
                {frozenset(("sol_coalition", "nebula_collective"))}
            ),
        )
        self.assertEqual(len(protected), 0, protected)


if __name__ == "__main__":
    unittest.main()
