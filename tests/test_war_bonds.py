"""War bonds: pledges pay out on victory, partially on stalemate, never twice."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import GameState, WarState


def _war(score=0.0, active=False, support=None, resolved=False):
    return WarState(
        id="w_bonds",
        attacker_id="sol_coalition",
        defender_id="nebula_collective",
        started_tick=0,
        war_score=score,
        active=active,
        support=support or {},
        bonds_resolved=resolved,
    )


class WarBondResolutionTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_active_war_does_not_pay(self):
        wars, credits, logs = self.engine._resolve_war_bonds(
            (_war(active=True, support={"sol_coalition": 500}),)
        )
        self.assertEqual(credits, 0)
        self.assertEqual(logs, [])
        self.assertFalse(wars[0].bonds_resolved)

    def test_winner_pays_one_and_a_half(self):
        wars, credits, logs = self.engine._resolve_war_bonds(
            (
                _war(
                    score=30.0,
                    support={"sol_coalition": 500, "nebula_collective": 300},
                ),
            )
        )
        self.assertEqual(credits, 750)
        self.assertTrue(wars[0].bonds_resolved)
        self.assertTrue(any("paid 750" in line for line in logs))
        self.assertTrue(any("LOST" in line for line in logs))

    def test_defender_win_pays_the_defender(self):
        _, credits, _ = self.engine._resolve_war_bonds(
            (_war(score=-30.0, support={"nebula_collective": 400}),)
        )
        self.assertEqual(credits, 600)

    def test_stalemate_returns_eighty_percent_to_both(self):
        _, credits, _ = self.engine._resolve_war_bonds(
            (
                _war(
                    score=0.0,
                    support={"sol_coalition": 500, "nebula_collective": 500},
                ),
            )
        )
        self.assertEqual(credits, 800)

    def test_already_resolved_war_never_pays_twice(self):
        _, credits, logs = self.engine._resolve_war_bonds(
            (_war(score=30.0, support={"sol_coalition": 500}, resolved=True),)
        )
        self.assertEqual(credits, 0)
        self.assertEqual(logs, [])

    def test_no_support_still_marks_the_war_resolved(self):
        wars, credits, _ = self.engine._resolve_war_bonds((_war(score=30.0),))
        self.assertEqual(credits, 0)
        self.assertTrue(wars[0].bonds_resolved)


class WarBondPledgeTest(unittest.TestCase):
    def test_support_war_records_a_pledge_and_mentions_terms(self):
        engine = SimulationEngine(seed=42)
        war = _war(active=True)
        engine.state = engine._clone_state(wars=(war,))
        before = engine.state.ship.credits
        ok, message = engine.support_war(war.id, "sol_coalition", 500)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.wars[0].support["sol_coalition"], 500)
        self.assertIn("1.5x", message)
        self.assertLess(engine.state.ship.credits, before)

    def test_bond_state_round_trips(self):
        war = _war(score=30.0, support={"sol_coalition": 500}, resolved=True)
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(wars=(war,))
        restored = GameState.from_dict(engine.state.to_dict())
        self.assertTrue(restored.wars[0].bonds_resolved)
        self.assertEqual(restored.wars[0].support["sol_coalition"], 500)


if __name__ == "__main__":
    unittest.main()
