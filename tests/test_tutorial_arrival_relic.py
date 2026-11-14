"""A relic won by the orbit step on a transit arrival is kept and applied."""

import unittest
from unittest import mock

from voidfarer.engine import SimulationEngine
from voidfarer.story import STORY_RELICS


class TutorialArrivalRelicTest(unittest.TestCase):
    def test_transit_arrival_keeps_the_tutorial_relic_and_its_hull_bonus(self):
        engine = SimulationEngine(seed=42)
        wings = STORY_RELICS["relic_cadet_wings"]
        real = engine._progress_tutorial

        def award(action):
            tut, cr, xp, relics, logs = real(action)
            return tut, cr, xp, ([wings] if action == "orbit" else relics), logs

        target = next(b for b in engine.current_system.bodies
                      if b.orbit_radius > 0 and b.body_type != "star"
                      and b.id != engine.state.ship.orbiting_body_id)
        ok, msg = engine.start_travel(target.id, "sublight")
        self.assertTrue(ok, msg)
        before = engine.state.ship
        arrival = before.travel.arrival_tick
        with mock.patch.object(engine, "_progress_tutorial", side_effect=award):
            engine.tick(arrival - engine.state.time.tick + 1)
        after = engine.state.ship
        self.assertEqual(after.orbiting_body_id, target.id)
        self.assertIn(wings.id, [r.id for r in after.relics])
        self.assertEqual(after.max_hull, before.max_hull + 15)


if __name__ == "__main__":
    unittest.main()
