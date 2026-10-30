"""Outpost integrity: defense, capture damage, production loss and repair."""

from types import SimpleNamespace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import CrewMember, Outpost
from voidfarer.outposts import (
    outpost_defense,
    outpost_repair_cost,
    outpost_tick_production,
)


def _outpost(integrity=100.0, modules=None, assigned=()):
    return Outpost(
        id="o1",
        name="Test Outpost",
        system_id="sol",
        body_id="b1",
        outpost_type="mining",
        integrity=integrity,
        modules=modules or {"extractor": 1},
        assigned_crew=tuple(assigned),
    )


class OutpostDefenseMathTest(unittest.TestCase):
    def test_defense_scales_with_sentry_grids_and_marines(self):
        self.assertEqual(outpost_defense(_outpost(), {}), 10)
        grid = _outpost(modules={"extractor": 1, "sentry_grid": 2})
        self.assertEqual(outpost_defense(grid, {}), 34)
        marine = CrewMember(id="m1", name="Marine", role="marine", skill=3)
        guarded = _outpost(modules={"extractor": 1, "sentry_grid": 1}, assigned=("m1",))
        self.assertEqual(outpost_defense(guarded, {"m1": marine}), 26)

    def test_production_scales_with_integrity(self):
        full = outpost_tick_production(_outpost(integrity=100.0))
        half = outpost_tick_production(_outpost(integrity=50.0))
        dead = outpost_tick_production(_outpost(integrity=0.0))
        self.assertAlmostEqual(half["credits"], round(full["credits"] * 0.5, 2))
        self.assertEqual(dead["credits"], 0.0)
        self.assertEqual(dead["titanium"], 0.0)

    def test_sentry_grid_does_not_inflate_production(self):
        plain = outpost_tick_production(_outpost())
        guarded = outpost_tick_production(
            _outpost(modules={"extractor": 1, "sentry_grid": 2})
        )
        self.assertEqual(guarded["credits"], plain["credits"])

    def test_repair_cost_rises_with_damage(self):
        self.assertEqual(outpost_repair_cost(_outpost(integrity=100.0)), 100)
        self.assertEqual(outpost_repair_cost(_outpost(integrity=50.0)), 400)
        self.assertEqual(outpost_repair_cost(_outpost(integrity=0.0)), 800)


class OutpostDefenseEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=1000),
            outposts=(_outpost(integrity=40.0),),
        )

    def test_repair_restores_integrity_and_charges_credits(self):
        ok, message = self.engine.repair_outpost("o1")
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.outposts[0].integrity, 100.0)
        self.assertEqual(self.engine.state.ship.credits, 520)
        ok, message = self.engine.repair_outpost("o1")
        self.assertFalse(ok)
        self.assertIn("full integrity", message.lower())

    def test_capture_damage_uses_defense_and_ignores_friendly_capture(self):
        outpost = self.engine.state.outposts[0]
        old = SimpleNamespace(faction="Sol Coalition", name="Old")
        enemy = SimpleNamespace(faction="Void Corsairs", name="Enemy")
        friendly = SimpleNamespace(faction="Sol Coalition", name="Friendly")
        self.assertEqual(
            self.engine._outpost_capture_damage(outpost, old, enemy, {}), 25
        )
        self.assertEqual(
            self.engine._outpost_capture_damage(outpost, old, friendly, {}), 0
        )
        guarded = _outpost(
            integrity=40.0, modules={"extractor": 1, "sentry_grid": 1}
        )
        self.assertEqual(
            self.engine._outpost_capture_damage(guarded, old, enemy, {}), 13
        )

    def test_sentry_grid_can_be_installed(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=2000)
        )
        ok, message = self.engine.install_outpost_module("o1", "sentry_grid")
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.outposts[0].modules["sentry_grid"], 1)
        self.assertEqual(self.engine.state.outposts[0].integrity, 40.0)


if __name__ == "__main__":
    unittest.main()
