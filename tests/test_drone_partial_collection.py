"""Drone haul collection fills the hold in part instead of refusing an oversized harvest."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import FleetDrone


def _engine(cargo, capacity, accumulated, credits_accumulated=0, efficiency=1.0):
    engine = SimulationEngine(seed=42)
    engine.state = engine._clone_state(
        ship=engine._clone_ship(
            cargo=cargo,
            cargo_capacity=capacity,
            credits=100,
            fleet_drones=(FleetDrone(
                id="d1", name="Miner", drone_type="mining", assigned_system_id="sol",
                integrity=100, cargo_accumulated=accumulated,
                credits_accumulated=credits_accumulated, efficiency=efficiency,
            ),),
        ),
    )
    return engine


class PartialDroneCollectionTest(unittest.TestCase):
    def test_an_oversized_haul_fills_the_free_volume_and_keeps_the_rest(self):
        engine = _engine({"titanium": 0}, capacity=10, accumulated=100)
        ok, message, info = engine.collect_drone_yield()
        self.assertTrue(ok, message)
        self.assertEqual(info["cargo"], 5, "titanium volume is 2, so 10 volume fits 5 units")
        self.assertEqual(info["remaining"], 95)
        self.assertIn("95 units remain on the drones", message)
        ship = engine.state.ship
        self.assertEqual(ship.cargo["titanium"], 5)
        self.assertEqual(ship.fleet_drones[0].cargo_accumulated, 95)

    def test_xp_scales_with_the_units_actually_hauled(self):
        engine = _engine({"titanium": 0}, capacity=10, accumulated=100)
        before = engine.state.ship.mastery.xp
        ok, _message, info = engine.collect_drone_yield()
        self.assertTrue(ok)
        gained = engine.state.ship.mastery.xp - before
        self.assertLessEqual(
            gained, info["cargo"],
            "a five-unit partial haul must not pay the same XP as a full hold",
        )

    def test_a_haul_that_fits_is_collected_whole(self):
        engine = _engine({}, capacity=40, accumulated=3)
        ok, _message, info = engine.collect_drone_yield()
        self.assertTrue(ok)
        self.assertEqual(info["cargo"], 3)
        self.assertEqual(engine.state.ship.fleet_drones[0].cargo_accumulated, 0)

    def test_a_full_hold_still_banks_credits(self):
        engine = _engine({"titanium": 20}, capacity=40, accumulated=50, credits_accumulated=120)
        ok, _message, info = engine.collect_drone_yield()
        self.assertTrue(ok, "credits need no volume")
        self.assertEqual(info["credits"], 120)
        self.assertEqual(engine.state.ship.credits, 220)
        self.assertEqual(engine.state.ship.fleet_drones[0].cargo_accumulated, 50)

    def test_no_room_and_no_credits_is_refused(self):
        engine = _engine({"titanium": 20}, capacity=40, accumulated=50)
        ok, message, _info = engine.collect_drone_yield()
        self.assertFalse(ok)
        self.assertIn("Jettison cargo or expand the hold", message)

    def test_singular_amounts_read_naturally(self):
        engine = _engine({"titanium": 19}, capacity=40, accumulated=2)
        ok, message, info = engine.collect_drone_yield()
        self.assertTrue(ok)
        self.assertEqual(info["cargo"], 1)
        self.assertEqual(info["remaining"], 1)
        self.assertIn("1 unit from fleet", message)
        self.assertIn("1 unit remains on the drones", message)


if __name__ == "__main__":
    unittest.main()
