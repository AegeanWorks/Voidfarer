"""Megastructure restoration: orbit/cost gates, bonuses and persistence."""

from dataclasses import replace
import unittest

from voidfarer.codex import metric_value
from voidfarer.engine import SimulationEngine
from voidfarer.megastructures import (
    MEGASTRUCTURE_RESTORATION,
    apply_output_bonus,
    restoration_bonuses,
)
from voidfarer.models import GameState, Outpost


class MegastructureRestorationTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.body = next(
            body
            for body in self.engine.current_system.bodies
            if body.body_type == "dyson_sphere"
        )

    def _orbit_with(self, credits: int):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=credits,
                orbiting_body_id=self.body.id,
            )
        )

    def test_dyson_restoration_charges_once_and_sets_the_flag(self):
        self._orbit_with(20000)
        report = self.engine.get_megastructure_report()
        self.assertTrue(report["restorable"])
        self.assertTrue(report["can_restore"])
        ok, message = self.engine.restore_megastructure(self.body.id)
        self.assertTrue(ok, message)
        self.assertEqual(
            self.engine.state.ship.credits,
            20000 - MEGASTRUCTURE_RESTORATION["dyson_sphere"]["cost"],
        )
        restored = next(
            body
            for body in self.engine.current_system.bodies
            if body.id == self.body.id
        )
        self.assertTrue(restored.restoration_complete)
        self.assertEqual(self.engine.state.stats["megastructures_restored"], 1)
        report = self.engine.get_megastructure_report()
        self.assertTrue(report["complete"])
        self.assertFalse(report["can_restore"])
        ok, message = self.engine.restore_megastructure(self.body.id)
        self.assertFalse(ok)
        self.assertIn("already restored", message.lower())

    def test_restoration_requires_orbit_and_credits(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=20000)
        )
        ok, message = self.engine.restore_megastructure(self.body.id)
        self.assertFalse(ok)
        self.assertIn("orbit", message.lower())

        self._orbit_with(100)
        ok, message = self.engine.restore_megastructure(self.body.id)
        self.assertFalse(ok)
        self.assertIn("insufficient credits", message.lower())
        self.assertEqual(self.engine.state.ship.credits, 100)

    def test_bonus_math_and_outpost_application(self):
        restored = replace(self.body, restoration_complete=True)
        bonuses = restoration_bonuses((restored,))
        self.assertAlmostEqual(bonuses["credits"], 0.15)
        production = apply_output_bonus(
            {"credits": 10.0, "research": 5.0}, bonuses
        )
        self.assertAlmostEqual(production["credits"], 11.5)
        self.assertAlmostEqual(production["research"], 5.0)

        outpost = Outpost(
            id="mega_outpost",
            name="Mega Outpost",
            system_id="sol",
            body_id="sol_body_1",
        )
        before = self.engine._outpost_production(outpost, 1.0, 1.0)["credits"]
        self._orbit_with(20000)
        self.assertTrue(self.engine.restore_megastructure(self.body.id)[0])
        after = self.engine._outpost_production(outpost, 1.0, 1.0)["credits"]
        self.assertGreater(after, before)

    def test_restoration_round_trips_and_legacy_defaults(self):
        self._orbit_with(20000)
        self.assertTrue(self.engine.restore_megastructure(self.body.id)[0])
        restored = GameState.from_dict(self.engine.state.to_dict())
        body = next(
            body
            for body in restored.systems[self.engine.current_system.id].bodies
            if body.id == self.body.id
        )
        self.assertTrue(body.restoration_complete)
        payload = self.engine.state.to_dict()
        system_payload = payload["systems"][self.engine.current_system.id]
        for raw in system_payload["bodies"]:
            raw.pop("restoration_complete", None)
        legacy = GameState.from_dict(payload)
        body = next(
            body
            for body in legacy.systems[self.engine.current_system.id].bodies
            if body.id == self.body.id
        )
        self.assertFalse(body.restoration_complete)

    def test_codex_metric_counts_restored_structures(self):
        self._orbit_with(20000)
        self.assertTrue(self.engine.restore_megastructure(self.body.id)[0])
        self.assertEqual(
            metric_value(self.engine.state, "megastructures_restored"), 1
        )


if __name__ == "__main__":
    unittest.main()
