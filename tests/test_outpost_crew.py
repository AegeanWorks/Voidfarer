"""Outpost crew: specialist bonuses, assignment rules and persistence."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import CrewMember, GameState, Outpost
from voidfarer.outposts import (
    OUTPOST_CREW_MAX_MULTIPLIER,
    outpost_crew_multiplier,
    outpost_tick_production,
)


def _crew(crew_id, role="engineer", skill=3, status="active"):
    return CrewMember(
        id=crew_id,
        name=f"Crew {crew_id}",
        role=role,
        skill=skill,
        status=status,
    )


class OutpostCrewMathTest(unittest.TestCase):
    def test_preferred_specialists_lift_output_and_cap(self):
        outpost = Outpost(
            id="o1", name="Mine", system_id="sol", body_id="b1",
            outpost_type="mining", assigned_crew=("c1",),
        )
        crew = {"c1": _crew("c1")}
        self.assertAlmostEqual(outpost_crew_multiplier(outpost, crew), 1.20)

        outpost = Outpost(
            id="o1", name="Mine", system_id="sol", body_id="b1",
            outpost_type="mining", assigned_crew=("c1", "c2", "c3"),
        )
        crew = {cid: _crew(cid) for cid in ("c1", "c2", "c3")}
        self.assertEqual(
            outpost_crew_multiplier(outpost, crew), OUTPOST_CREW_MAX_MULTIPLIER
        )

    def test_non_preferred_and_inactive_crew_are_weaker_or_ignored(self):
        outpost = Outpost(
            id="o1", name="Mine", system_id="sol", body_id="b1",
            outpost_type="mining", assigned_crew=("c1", "c2"),
        )
        crew = {"c1": _crew("c1", role="medic"), "c2": _crew("c2", status="inactive")}
        self.assertAlmostEqual(outpost_crew_multiplier(outpost, crew), 1.14)

    def test_production_uses_the_crew_multiplier(self):
        outpost = Outpost(
            id="o1", name="Mine", system_id="sol", body_id="b1",
            outpost_type="mining", assigned_crew=("c1",),
        )
        plain = outpost_tick_production(outpost)
        boosted = outpost_tick_production(outpost, crew_multiplier=1.20)
        self.assertGreater(boosted["credits"], plain["credits"])
        self.assertGreater(boosted["titanium"], plain["titanium"])


class OutpostCrewEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        charter, _ = self.engine._award_pilot_xp(500, self.engine.state.ship.mastery)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=10000, orbiting_body_id="sol_body_1", mastery=charter)
        )
        ok, message = self.engine.build_outpost("sol_body_1", "shipyard")
        self.assertTrue(ok, message)
        self.outpost = self.engine.state.outposts[0]

    def test_assign_and_recall_a_specialist(self):
        crew = self.engine.state.ship.crew[0]
        ok, message = self.engine.assign_outpost_crew(self.outpost.id, crew.id)
        self.assertTrue(ok, message)
        self.assertIn(crew.id, self.engine.state.outposts[0].assigned_crew)
        self.assertGreater(
            self.engine.get_outpost_report()["outposts"][0]["crew_multiplier"], 1.0
        )
        self.assertIn("OUTPOST CREW", message)

        report = self.engine.get_crew_report()
        assigned = next(member for member in report["crew"] if member["id"] == crew.id)
        self.assertEqual(assigned["outpost_id"], self.outpost.id)

        ok, message = self.engine.recall_outpost_crew(self.outpost.id, crew.id)
        self.assertTrue(ok, message)
        self.assertNotIn(crew.id, self.engine.state.outposts[0].assigned_crew)
        self.assertIn("recalled", message.lower())

    def test_duplicate_capacity_and_dismissal_rules(self):
        crew = self.engine.state.ship.crew
        ok, message = self.engine.assign_outpost_crew(self.outpost.id, crew[0].id)
        self.assertTrue(ok, message)
        ok, message = self.engine.assign_outpost_crew(self.outpost.id, crew[0].id)
        self.assertFalse(ok)
        self.assertIn("already", message.lower())

        ok, message = self.engine.dismiss_crew(crew[0].id)
        self.assertFalse(ok)
        self.assertIn("stationed", message.lower())

        extra = CrewMember(
            id="extra_1", name="Extra One", role="engineer", skill=2
        )
        extra_two = CrewMember(
            id="extra_2", name="Extra Two", role="scientist", skill=2
        )
        extra_three = CrewMember(
            id="extra_3", name="Extra Three", role="quartermaster", skill=2
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                crew=self.engine.state.ship.crew + (extra, extra_two, extra_three)
            )
        )
        ok, message = self.engine.assign_outpost_crew(self.outpost.id, "extra_1")
        self.assertTrue(ok, message)
        ok, message = self.engine.assign_outpost_crew(self.outpost.id, "extra_2")
        self.assertTrue(ok, message)
        ok, message = self.engine.assign_outpost_crew(self.outpost.id, "extra_3")
        self.assertFalse(ok)
        self.assertIn("specialists", message.lower())

    def test_save_round_trip_keeps_assigned_crew(self):
        crew = self.engine.state.ship.crew[0]
        ok, message = self.engine.assign_outpost_crew(self.outpost.id, crew.id)
        self.assertTrue(ok, message)
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.outposts[0].assigned_crew, (crew.id,))


if __name__ == "__main__":
    unittest.main()
