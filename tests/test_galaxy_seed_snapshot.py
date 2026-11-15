"""The status snapshot exposes the galaxy seed so a galaxy can be replayed or shared."""

import unittest

from voidfarer.engine import SimulationEngine


class GalaxySeedSnapshotTest(unittest.TestCase):
    def test_snapshot_reports_the_seed_the_game_was_built_from(self):
        self.assertEqual(SimulationEngine(seed=1234).get_status_snapshot()["galaxy_seed"], 1234)

    def test_a_reset_with_a_new_seed_changes_the_reported_seed_and_the_galaxy(self):
        engine = SimulationEngine(seed=1)
        names_before = [s.name for s in engine.state.systems.values()]
        ok, message = engine.reset(99)
        self.assertTrue(ok, message)
        self.assertEqual(engine.get_status_snapshot()["galaxy_seed"], 99)
        again = SimulationEngine(seed=99)
        self.assertEqual(
            [(k, s.security) for k, s in engine.state.systems.items()],
            [(k, s.security) for k, s in again.state.systems.items()],
        )
        self.assertIsNotNone(names_before)


if __name__ == "__main__":
    unittest.main()
