"""Unit tests for procedural galaxy generation, hyperlane mesh, and market quotes."""

import unittest
from voidfarer.galaxy import CANONICAL_COMMODITIES, GalaxyGenerator


class TestGalaxy(unittest.TestCase):
    def test_galaxy_generation_determinism(self):
        gen1 = GalaxyGenerator(seed=1337)
        g1 = gen1.generate_galaxy()

        gen2 = GalaxyGenerator(seed=1337)
        g2 = gen2.generate_galaxy()

        self.assertEqual(len(g1), len(g2))
        self.assertIn("sol", g1)
        self.assertEqual(g1["sol"].connections, g2["sol"].connections)

    def test_hyperlane_connectivity(self):
        gen = GalaxyGenerator(seed=42)
        galaxy = gen.generate_galaxy()

        # Verify that all systems have at least 2 connections
        for sid, system in galaxy.items():
            self.assertGreaterEqual(len(system.connections), 2, f"System {sid} has insufficient links")
            for conn_id in system.connections:
                self.assertIn(conn_id, galaxy)
                # Symmetrical link
                self.assertIn(sid, galaxy[conn_id].connections)

    def test_market_quotes_calculation(self):
        gen = GalaxyGenerator(seed=42)
        galaxy = gen.generate_galaxy()
        sol = galaxy["sol"]
        station = next(b for b in sol.bodies if b.station_dockable)

        quotes = GalaxyGenerator.get_market_quotes(sol, station)
        self.assertEqual(len(quotes), len(CANONICAL_COMMODITIES))
        for q in quotes:
            self.assertGreater(q.buy_price, q.sell_price)
            self.assertGreater(q.sell_price, 0)
            self.assertGreater(q.supply, 0)
            self.assertGreater(q.demand, 0)

    def test_random_anomaly_generation(self):
        anomaly = GalaxyGenerator.get_random_anomaly(seed=999)
        self.assertTrue(anomaly.title)
        self.assertGreaterEqual(len(anomaly.choices), 2)


    def test_population_mechanics_and_colony_tiers(self):
        from voidfarer.galaxy import step_population_dynamics, get_colony_tier
        from voidfarer.models import CelestialBody

        b0 = CelestialBody(id="b0", name="Barren", body_type="barren", color="#aaa", radius_km=3000, orbit_radius=2.0, orbit_speed=0.01, hazards=(), population=0, habitability=5.0)
        self.assertEqual(get_colony_tier(b0.population), "Uninhabited")
        self.assertEqual(step_population_dynamics(b0, 10), 0)

        b1 = CelestialBody(id="b1", name="Terra", body_type="terrestrial", color="#0f0", radius_km=6371, orbit_radius=1.0, orbit_speed=0.02, hazards=(), population=1_000_000, habitability=95.0, landable=True)
        self.assertEqual(get_colony_tier(b1.population), "Settlement")
        new_pop = step_population_dynamics(b1, 10)
        self.assertGreater(new_pop, b1.population)

        self.assertEqual(get_colony_tier(5_000), "Outpost")
        self.assertEqual(get_colony_tier(250_000), "Colony")
        self.assertEqual(get_colony_tier(15_000_000), "Settlement")
        self.assertEqual(get_colony_tier(200_000_000), "Metropolis")
        self.assertEqual(get_colony_tier(2_000_000_000), "Mega-Ecumenopolis")

    def test_orbit_and_sublight_distance_parity(self):
        from voidfarer.engine import SimulationEngine
        engine = SimulationEngine()
        sol = engine.current_system
        b1 = sol.bodies[1]
        b2 = sol.bodies[2]
        dist1 = engine.compute_body_distance_au(b2, b1)
        ok, msg = engine.orbit(b1.id)
        self.assertTrue(ok)
        ok2, msg2 = engine.start_travel(b2.id, mode="sublight")
        self.assertTrue(ok2)
        travel = engine.state.ship.travel
        self.assertIsNotNone(travel)
        self.assertAlmostEqual(travel.distance_au, dist1, places=1)


if __name__ == "__main__":
    unittest.main()

