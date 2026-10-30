"""Outpost specialization: level-3 production focus and logistics crew slot."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import GameState, Outpost
from voidfarer.outposts import (
    OUTPOST_SPECIALIZATIONS,
    outpost_crew_capacity,
    outpost_tick_production,
)


def _outpost(level=3, specialization="", outpost_type="mining"):
    return Outpost(
        id="o1",
        name="Test Outpost",
        system_id="sol",
        body_id="b1",
        outpost_type=outpost_type,
        level=level,
        specialization=specialization,
    )


class OutpostSpecializationMathTest(unittest.TestCase):
    def test_industry_and_research_trade_outputs(self):
        base = outpost_tick_production(_outpost(outpost_type="research"))
        industry = outpost_tick_production(
            _outpost(specialization="industry", outpost_type="research")
        )
        research = outpost_tick_production(
            _outpost(specialization="research", outpost_type="research")
        )
        self.assertGreater(industry["credits"], base["credits"])
        self.assertLess(research["credits"], base["credits"])
        self.assertGreater(research["research"], base["research"])
        self.assertEqual(industry["research"], base["research"])

    def test_logistics_adds_a_crew_slot(self):
        self.assertEqual(outpost_crew_capacity(_outpost()), 3)
        self.assertEqual(outpost_crew_capacity(_outpost(specialization="logistics")), 4)
        self.assertEqual(
            outpost_tick_production(_outpost(specialization="logistics"))["credits"],
            round(outpost_tick_production(_outpost())["credits"] * 1.10, 2),
        )

    def test_catalog_has_four_specializations(self):
        self.assertEqual(
            set(OUTPOST_SPECIALIZATIONS),
            {"industry", "research", "commerce", "logistics"},
        )


class OutpostSpecializationEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=5000),
            outposts=(_outpost(level=1),),
        )

    def test_specialization_requires_level_three(self):
        ok, message = self.engine.specialize_outpost("o1", "industry")
        self.assertFalse(ok)
        self.assertIn("level 3", message.lower())

    def test_specialization_charges_and_persists(self):
        self.engine.state = self.engine._clone_state(outposts=(_outpost(level=3),))
        ok, message = self.engine.specialize_outpost("o1", "industry")
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.outposts[0].specialization, "industry")
        self.assertEqual(self.engine.state.ship.credits, 4400)
        report = self.engine.get_outpost_report()["outposts"][0]
        self.assertEqual(report["specialization_label"], "Industry")
        self.assertEqual(report["crew_capacity"], 3)

        ok, message = self.engine.specialize_outpost("o1", "logistics")
        self.assertTrue(ok, message)
        report = self.engine.get_outpost_report()["outposts"][0]
        self.assertEqual(report["crew_capacity"], 4)
        self.assertIn("Logistics", message)

    def test_specialization_rejects_unknown_and_duplicate(self):
        self.engine.state = self.engine._clone_state(outposts=(_outpost(level=3),))
        ok, message = self.engine.specialize_outpost("o1", "bogus")
        self.assertFalse(ok)
        self.assertIn("industry", message.lower())
        ok, _ = self.engine.specialize_outpost("o1", "commerce")
        self.assertTrue(ok)
        ok, message = self.engine.specialize_outpost("o1", "commerce")
        self.assertFalse(ok)
        self.assertIn("already", message.lower())

    def test_save_round_trip_keeps_specialization(self):
        self.engine.state = self.engine._clone_state(
            outposts=(_outpost(level=3, specialization="research"),)
        )
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.outposts[0].specialization, "research")


if __name__ == "__main__":
    unittest.main()
