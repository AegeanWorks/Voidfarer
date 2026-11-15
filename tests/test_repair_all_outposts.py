"""REPAIR ALL OUTPOSTS restores every damaged outpost, worst first, as far as credits stretch."""

import unittest
from dataclasses import replace

from voidfarer.empire import EMPIRE_ACTIONS, empire_action
from voidfarer.engine import SimulationEngine
from voidfarer.models import Outpost


def _outpost(oid, integrity):
    return Outpost(
        id=oid, name=f"Outpost {oid}", system_id="sol", body_id=f"b{oid}",
        outpost_type="mining", integrity=integrity, modules={"extractor": 1}, assigned_crew=(),
    )


def _engine(credits, *integrities):
    engine = SimulationEngine(seed=42)
    outposts = tuple(_outpost(str(i), v) for i, v in enumerate(integrities, start=1))
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=credits), outposts=outposts)
    return engine


class RepairAllOutpostsTest(unittest.TestCase):
    def test_repairs_every_damaged_outpost_and_charges_the_sum(self):
        engine = _engine(2000, 40.0, 70.0, 100.0)
        ok, message = engine.repair_all_outposts()
        self.assertTrue(ok, message)
        self.assertTrue(all(o.integrity == 100.0 for o in engine.state.outposts))
        self.assertEqual(engine.state.ship.credits, 2000 - 480 - 240)
        self.assertIn("2 outposts", message)

    def test_worst_damage_is_repaired_first_when_credits_run_short(self):
        engine = _engine(500, 70.0, 40.0)  # costs: 240 for the 70%, 480 for the 40%
        ok, message = engine.repair_all_outposts()
        self.assertTrue(ok, message)
        by_id = {o.id: o.integrity for o in engine.state.outposts}
        self.assertEqual(by_id["2"], 100.0)   # the 40% outpost went first
        self.assertEqual(by_id["1"], 70.0)    # not enough left for the other
        self.assertEqual(engine.state.ship.credits, 20)
        self.assertIn("short", message.lower())

    def test_nothing_damaged_or_nothing_affordable_changes_nothing(self):
        engine = _engine(2000, 100.0)
        before = engine.state
        ok, message = engine.repair_all_outposts()
        self.assertFalse(ok)
        self.assertIn("full integrity", message.lower())
        self.assertEqual(engine.state, before)
        poor = _engine(50, 40.0)
        ok, message = poor.repair_all_outposts()
        self.assertFalse(ok)
        self.assertEqual(poor.state.outposts[0].integrity, 40.0)

    def test_it_is_reachable_as_an_empire_action(self):
        self.assertIn("outpost_repair_all", EMPIRE_ACTIONS)
        ok, _ = empire_action(_engine(2000, 40.0), "outpost_repair_all")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
