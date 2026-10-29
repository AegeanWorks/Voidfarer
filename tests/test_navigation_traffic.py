"""Open-space transit vectors and the NPC traffic that shares the map."""

import math
import unittest

from voidfarer.engine import SimulationEngine


class EmptySpaceTransitTest(unittest.TestCase):
    def test_waypoint_transit_does_not_promise_an_orbit(self):
        engine = SimulationEngine(seed=42)
        ok, msg = engine.start_travel_to_point(3.5, 1.1, "sublight")
        self.assertTrue(ok, msg)
        travel = engine.state.ship.travel
        self.assertIsNotNone(travel)
        self.assertIsNone(travel.destination_body_id)
        self.assertAlmostEqual(travel.waypoint_au, 3.5, places=3)
        self.assertAlmostEqual(travel.waypoint_angle, 1.1, places=4)
        self.assertGreater(travel.distance_au, 0.0)
        self.assertGreater(travel.arrival_tick, engine.state.time.tick)

    def test_arrival_holds_station_in_open_space(self):
        engine = SimulationEngine(seed=42)
        ok, msg = engine.start_travel_to_point(2.0, 0.5, "quantum")
        self.assertTrue(ok, msg)
        travel = engine.state.ship.travel
        for _ in range(travel.duration_ticks + 1):
            engine.tick(1)
        self.assertIsNone(engine.state.ship.travel)
        self.assertIsNone(engine.state.ship.orbiting_body_id)
        self.assertAlmostEqual(engine.state.ship.waypoint_au, 2.0, places=3)
        self.assertAlmostEqual(engine.state.ship.waypoint_angle, 0.5, places=4)
        arrivals = [e for e in engine.state.events if e.kind == "arrival"]
        self.assertTrue(arrivals, "an open-space arrival must still be announced")
        self.assertTrue(arrivals[-1].title.startswith("Holding Station"))

    def test_leaving_open_space_prices_the_transit_from_the_anchor(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(credits=20000, fuel=60))
        self.assertTrue(engine.start_travel_to_point(5.0, 0.0, "quantum")[0])
        for _ in range(2):
            engine.tick(1)
        self.assertIsNone(engine.state.ship.orbiting_body_id)

        target = next(b for b in engine.current_system.bodies if b.orbit_radius > 0 and b.body_type != "star")
        star_distance = target.orbit_radius
        origin_au = engine.state.ship.waypoint_au
        origin_angle = engine.state.ship.waypoint_angle
        dx = target.orbit_radius * math.cos(target.current_angle) - origin_au * math.cos(origin_angle)
        dy = target.orbit_radius * math.sin(target.current_angle) - origin_au * math.sin(origin_angle)
        expected = max(0.25, math.hypot(dx, dy))
        ok, plan = engine.preview_travel(target.id, "sublight")
        self.assertTrue(ok, plan)
        self.assertAlmostEqual(plan["distance_au"], round(expected, 2), places=2)
        self.assertNotAlmostEqual(plan["distance_au"], round(star_distance, 2), places=1)

    def test_orbiting_a_body_clears_the_open_space_anchor(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(credits=20000, fuel=60))
        self.assertTrue(engine.start_travel_to_point(3.0, 1.0, "quantum")[0])
        for _ in range(2):
            engine.tick(1)
        self.assertGreater(engine.state.ship.waypoint_au, 0)
        target = next(b for b in engine.current_system.bodies if b.orbit_radius > 0 and b.body_type != "star")
        ok, msg = engine.start_travel(target.id, "quantum")
        self.assertTrue(ok, msg)
        for _ in range(2):
            engine.tick(1)
        self.assertEqual(engine.state.ship.orbiting_body_id, target.id)
        self.assertEqual(engine.state.ship.waypoint_au, 0.0)

    def test_waypoint_is_refused_outside_the_transit_envelope(self):
        engine = SimulationEngine(seed=42)
        ok, msg = engine.start_travel_to_point(999.0, 0.0)
        self.assertFalse(ok)
        self.assertIn("envelope", msg)
        self.assertIsNone(engine.state.ship.travel)
        ok, msg = engine.start_travel_to_point(2.0, float("nan"))
        self.assertFalse(ok)
        self.assertIn("bearing", msg)

    def test_a_second_vector_cannot_be_plotted_mid_flight(self):
        engine = SimulationEngine(seed=42)
        self.assertTrue(engine.start_travel_to_point(4.0, 0.2, "sublight")[0])
        ok, msg = engine.start_travel_to_point(1.0, 0.9, "sublight")
        self.assertFalse(ok)
        self.assertIn("Already in transit", msg)

    def test_survey_and_orbit_actions_need_a_body(self):
        engine = SimulationEngine(seed=42)
        engine.start_travel_to_point(2.0, 0.0, "quantum")
        for _ in range(2):
            engine.tick(1)
        self.assertIsNone(engine.state.ship.orbiting_body_id)
        ok, msg, _ = engine.scan()
        self.assertFalse(ok)
        self.assertIn("orbit", msg)

    def test_waypoint_survives_a_save_round_trip(self):
        engine = SimulationEngine(seed=42)
        engine.start_travel_to_point(5.25, 2.5, "sublight")
        restored = type(engine.state).from_dict(engine.state.to_dict())
        travel = restored.ship.travel
        self.assertIsNone(travel.destination_body_id)
        self.assertAlmostEqual(travel.waypoint_au, 5.25, places=3)
        self.assertAlmostEqual(travel.waypoint_angle, 2.5, places=4)


class NpcTrafficTest(unittest.TestCase):
    def test_every_captain_has_a_place_on_the_map(self):
        engine = SimulationEngine(seed=42)
        captains = engine.state.ai_captains
        self.assertTrue(captains, "the galaxy must carry NPC traffic")
        systems = engine.state.systems
        for captain in captains:
            self.assertIn(captain.system_id, systems)
            self.assertTrue(captain.name)
            self.assertTrue(captain.archetype)


if __name__ == "__main__":
    unittest.main()
