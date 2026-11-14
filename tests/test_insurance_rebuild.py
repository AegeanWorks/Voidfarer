"""Coalition insurance: a destroyed hull can be rebuilt at a safe station for a deductible."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.engineering import ENGINEERING_ACTIONS, engineering_action
from voidfarer.story import STORY_RELICS


def _destroyed(credits: int = 1000) -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    wings = STORY_RELICS["relic_cadet_wings"]
    engine.state = engine._clone_state(ship=engine._clone_ship(
        hull=0, shield=0, credits=credits, cargo={"titanium": 3, "fuel_cells": 2},
        relics=(wings,),
    ))
    return engine


class InsuranceRebuildTest(unittest.TestCase):
    def test_rebuild_keeps_story_and_relics_and_loses_cargo_and_a_deductible(self):
        engine = _destroyed(1000)
        story = engine.state.ship.story
        ok, message = engine.insurance_rebuild()
        self.assertTrue(ok, message)
        ship = engine.state.ship
        self.assertGreater(ship.hull, 0)
        self.assertEqual(ship.credits, 750)
        self.assertEqual(sum(ship.cargo.values()), 0)
        self.assertEqual([r.id for r in ship.relics], ["relic_cadet_wings"])
        self.assertEqual(ship.story, story)
        body = engine.docked_body
        self.assertIsNotNone(body)
        self.assertTrue(body.station_dockable)
        self.assertGreaterEqual(engine.current_system.security, 0.5)
        self.assertGreaterEqual(ship.fuel, ship.max_fuel // 3)

    def test_a_living_hull_is_refused_and_nothing_changes(self):
        engine = SimulationEngine(seed=42)
        before = engine.state.ship
        ok, message = engine.insurance_rebuild()
        self.assertFalse(ok)
        self.assertIn("destroyed", message)
        self.assertEqual(engine.state.ship, before)

    def test_the_snapshot_quotes_the_policy_only_for_a_destroyed_hull(self):
        self.assertIsNone(SimulationEngine(seed=42).get_status_snapshot()["insurance"])
        quote = _destroyed(1000).get_status_snapshot()["insurance"]
        self.assertTrue(quote["available"])
        self.assertEqual(quote["deductible"], 250)
        self.assertTrue(quote["destination"])

    def test_it_is_reachable_as_an_engineering_action(self):
        self.assertIn("insurance", ENGINEERING_ACTIONS)
        ok, _ = engineering_action(_destroyed(), "insurance")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
