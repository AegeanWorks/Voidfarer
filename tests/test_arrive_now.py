"""ARRIVE NOW steps a sublight transit to its arrival tick and stops at the first interruption."""

import unittest
from unittest import mock

from voidfarer.engine import SimulationEngine
from voidfarer.flight import FLIGHT_ACTIONS, flight_action


def _in_transit():
    engine = SimulationEngine(seed=42)
    target = next(b for b in engine.current_system.bodies
                  if b.orbit_radius > 0 and b.body_type != "star"
                  and b.id != engine.state.ship.orbiting_body_id)
    ok, message = engine.start_travel(target.id, "sublight")
    assert ok, message
    return engine, target


class ArriveNowTest(unittest.TestCase):
    def test_steps_to_arrival_and_enters_orbit(self):
        engine, target = _in_transit()
        arrival = engine.state.ship.travel.arrival_tick
        start = engine.state.time.tick
        ok, message = engine.arrive_now()
        self.assertTrue(ok, message)
        self.assertIsNone(engine.state.ship.travel)
        self.assertEqual(engine.state.ship.orbiting_body_id, target.id)
        self.assertGreaterEqual(engine.state.time.tick, arrival)
        self.assertIn(str(engine.state.time.tick - start), message)

    def test_stops_after_one_tick_when_an_encounter_locks_flight(self):
        engine, _ = _in_transit()
        with mock.patch.object(engine, "_action_lock_reason", return_value="Pirate intercept unresolved."):
            ok, message = engine.arrive_now()
        self.assertFalse(ok)
        self.assertIsNotNone(engine.state.ship.travel)
        self.assertIn("Pirate intercept", message)

    def test_refused_when_not_in_transit(self):
        engine = SimulationEngine(seed=42)
        before = engine.state
        ok, message = engine.arrive_now()
        self.assertFalse(ok)
        self.assertIn("transit", message.lower())
        self.assertEqual(engine.state, before)

    def test_it_is_reachable_as_a_flight_action(self):
        self.assertIn("arrive", FLIGHT_ACTIONS)
        engine, _ = _in_transit()
        ok, _ = flight_action(engine, "arrive")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
