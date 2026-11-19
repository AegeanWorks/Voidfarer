"""Crew ids stay unique when the roster shrinks and refills (ADR-403)."""

import unittest

from voidfarer.crew import recruit_crew_member, recruit_unique_crew_member
from voidfarer.engine import SimulationEngine


class UniqueCrewIdTest(unittest.TestCase):
    def test_the_helper_skips_a_reused_suffix(self):
        existing = recruit_crew_member("engineer", 42, 3)
        fresh = recruit_unique_crew_member("engineer", 42, (existing,))
        self.assertIsNotNone(fresh)
        self.assertNotEqual(fresh.id, existing.id)
        self.assertEqual(fresh.role, "engineer")

    def test_the_helper_keeps_the_natural_index_when_it_is_free(self):
        existing = recruit_crew_member("pilot", 42, 0)
        fresh = recruit_unique_crew_member("engineer", 42, (existing,))
        self.assertEqual(fresh.id, "crew_engineer_2")

    def test_the_helper_reports_a_missing_role(self):
        self.assertIsNone(recruit_unique_crew_member("no_such_role", 42, ()))


class RecruitAfterDismissTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=50000))

    def test_a_recruit_after_a_dismissal_never_reuses_an_id(self):
        ok, msg = self.engine.recruit_crew("engineer")
        self.assertTrue(ok, msg)
        ok, msg = self.engine.dismiss_crew(self.engine.state.ship.crew[0].id)
        self.assertTrue(ok, msg)
        ok, msg = self.engine.recruit_crew("engineer")
        self.assertTrue(ok, msg)
        ids = [member.id for member in self.engine.state.ship.crew]
        self.assertEqual(len(ids), len(set(ids)), ids)


if __name__ == "__main__":
    unittest.main()
