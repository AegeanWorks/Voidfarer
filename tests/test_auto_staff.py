"""AUTO-STAFF seats the best matching officer at every bridge station in one action."""

import unittest
from dataclasses import replace

from voidfarer.crew import recruit_crew_member
from voidfarer.crew_command import CREW_ACTIONS, crew_action
from voidfarer.engine import SimulationEngine


def _crew(role, index, skill, status="active", station=""):
    member = recruit_crew_member(role, 42, index)
    return replace(member, skill=skill, status=status, station=station)


def _engine(*crew):
    engine = SimulationEngine(seed=42)
    engine.state = engine._clone_state(ship=engine._clone_ship(crew=tuple(crew)))
    return engine


def _stations(engine):
    return {c.station: c.id for c in engine.state.ship.crew if c.station}


class AutoStaffTest(unittest.TestCase):
    def test_each_role_takes_its_station(self):
        pilot, marine = _crew("pilot", 1, 3), _crew("marine", 2, 3)
        engineer, scientist, medic = _crew("engineer", 3, 3), _crew("scientist", 4, 3), _crew("medic", 5, 3)
        engine = _engine(pilot, marine, engineer, scientist, medic)
        ok, message = engine.auto_staff_stations()
        self.assertTrue(ok, message)
        self.assertEqual(_stations(engine), {
            "helm": pilot.id, "tactical": marine.id, "engineering": engineer.id,
            "science": scientist.id, "medical": medic.id,
        })

    def test_the_most_skilled_matching_officer_wins_and_the_injured_are_skipped(self):
        rookie, ace = _crew("engineer", 1, 2), _crew("engineer", 2, 6)
        hurt = _crew("engineer", 3, 9, status="injured")
        engine = _engine(rookie, ace, hurt)
        engine.auto_staff_stations()
        self.assertEqual(_stations(engine), {"engineering": ace.id})

    def test_a_worse_manual_assignment_is_replaced_and_a_quartermaster_has_no_station(self):
        engineer, quartermaster = _crew("engineer", 1, 5), _crew("quartermaster", 2, 5, station="helm")
        engine = _engine(engineer, quartermaster)
        ok, _ = engine.auto_staff_stations()
        self.assertTrue(ok)
        by_id = {c.id: c.station for c in engine.state.ship.crew}
        self.assertEqual(by_id[engineer.id], "engineering")
        self.assertEqual(by_id[quartermaster.id], "")

    def test_already_optimal_changes_nothing_and_says_so(self):
        engineer = _crew("engineer", 1, 5, station="engineering")
        engine = _engine(engineer)
        before = engine.state
        ok, message = engine.auto_staff_stations()
        self.assertFalse(ok)
        self.assertIn("already", message.lower())
        self.assertEqual(engine.state, before)

    def test_it_is_reachable_as_a_crew_action(self):
        self.assertIn("autostaff", CREW_ACTIONS)
        ok, _ = crew_action(_engine(_crew("pilot", 1, 4)), "autostaff")
        self.assertTrue(ok)


class AutoStaffCliTest(unittest.TestCase):
    def test_crew_autostaff_seats_officers_and_persists(self):
        import contextlib
        import io
        import tempfile
        from pathlib import Path

        from voidfarer.cli import cmd_crew
        from voidfarer.storage import StorageManager

        engine = _engine(_crew("pilot", 1, 4), _crew("engineer", 2, 5))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        storage = StorageManager(Path(tmp.name))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = cmd_crew(engine, storage, ["crew", "autostaff"])
        self.assertEqual(code, 0)
        self.assertIn("AUTO-STAFF", out.getvalue())
        saved = storage.load()
        self.assertEqual({c.station for c in saved.ship.crew}, {"helm", "engineering"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_crew(engine, storage, ["crew", "autostaff"]), 1)  # already optimal


if __name__ == "__main__":
    unittest.main()
