"""Outpost modules: spend credits to stack production modules on an installation."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import Outpost
from voidfarer.outposts import outpost_tick_production


class OutpostModuleTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.outpost = Outpost(
            id="outpost_test",
            name="Test Mining Outpost",
            system_id="sol",
            body_id="sol_body_2",
            outpost_type="mining",
            level=1,
            modules={"extractor": 1},
            production={"credits": 3.0, "titanium": 1.0},
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=5000),
            outposts=(self.outpost,),
        )

    def test_installing_a_module_adds_it_and_raises_production(self):
        before = outpost_tick_production(self.engine.state.outposts[0])
        ok, message = self.engine.install_outpost_module(self.outpost.id, "laboratory")
        self.assertTrue(ok, message)
        outpost = self.engine.state.outposts[0]
        self.assertEqual(outpost.modules.get("laboratory"), 1)
        self.assertEqual(self.engine.state.ship.credits, 4500)
        after = outpost_tick_production(outpost)
        self.assertGreater(after["credits"], before["credits"])

    def test_module_stacks_are_capped(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=5000),
            outposts=(self.outpost.__class__(
                **{**self.outpost.__dict__, "modules": {"laboratory": 3}}
            ),),
        )
        ok, message = self.engine.install_outpost_module(self.outpost.id, "laboratory")
        self.assertFalse(ok)
        self.assertIn("maximum", message.lower())

    def test_module_requires_credits_and_a_known_module(self):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=10))
        ok, message = self.engine.install_outpost_module(self.outpost.id, "laboratory")
        self.assertFalse(ok)
        self.assertIn("insufficient", message.lower())

        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=5000))
        ok, message = self.engine.install_outpost_module(self.outpost.id, "magic")
        self.assertFalse(ok)
        self.assertIn("unknown", message.lower())

    def test_report_exposes_module_catalog(self):
        report = self.engine.get_outpost_report()
        self.assertIn("laboratory", report["modules"])
        self.assertIn("extractor", report["outposts"][0]["modules"])


if __name__ == "__main__":
    unittest.main()
