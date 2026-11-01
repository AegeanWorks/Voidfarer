"""Tests for ship wear and drydock repair mechanics."""

import unittest

from voidfarer.engine import SimulationEngine


class TestShipWear(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_wear_starts_at_zero(self):
        self.assertEqual(self.engine.state.ship.wear, 0.0)

    def test_jump_increases_wear(self):
        cur_sys = self.engine.current_system
        target = cur_sys.connections[0]
        ok, _ = self.engine.jump(target)
        self.assertTrue(ok)
        self.assertGreater(self.engine.state.ship.wear, 0.0)

    def test_wear_caps_at_100(self):
        # Simulate many jumps by repeatedly jumping back and forth.
        a = self.engine.current_system.id
        b = self.engine.current_system.connections[0]
        for _ in range(200):
            self.engine.jump(b)
            self.engine.jump(a)
        self.assertLessEqual(self.engine.state.ship.wear, 100.0)

    def test_wear_reduces_passive_efficiency(self):
        from voidfarer.retention import calculate_passive_multipliers
        ship = self.engine.state.ship
        # zero wear baseline
        m0 = calculate_passive_multipliers(ship)
        # high wear
        worn = self.engine._clone_ship(wear=100.0)
        mw = calculate_passive_multipliers(worn)
        self.assertLess(mw["scan_bounty"], m0["scan_bounty"])
        self.assertLess(mw["trade_margin"], m0["trade_margin"])

    def test_repair_reduces_wear_at_station(self):
        # Give ship wear and hull damage, dock at a station.
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(wear=50.0, hull=80, credits=10000)
        )
        # orbit a station body
        body_id = None
        for b in self.engine.current_system.bodies:
            if getattr(b, "station_dockable", False):
                body_id = b.id
                break
        if body_id is None:
            self.skipTest("no station in starting system")
        ok, _ = self.engine.orbit(body_id)
        self.assertTrue(ok)
        wear_before = self.engine.state.ship.wear
        ok2, _ = self.engine.repair_hull(20)
        self.assertTrue(ok2)
        self.assertLess(self.engine.state.ship.wear, wear_before)

    def test_wear_persists_roundtrip(self):
        ship = self.engine._clone_ship(wear=42.5)
        d = ship.to_dict()
        from voidfarer.models import ShipState
        restored = ShipState.from_dict(d)
        self.assertAlmostEqual(restored.wear, 42.5)