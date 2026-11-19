"""Independent save slots each keep their own deterministic stream (ADR-409)."""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory

from voidfarer.engine import SimulationEngine
from voidfarer.storage import StorageManager


def _drive(engine: SimulationEngine, actions: int, offset: int = 0) -> None:
    """A deterministic hop-and-scan tour that advances ticks and draws randomness."""
    for index in range(offset, offset + actions):
        connections = engine.current_system.connections
        if connections:
            engine.jump(connections[index % len(connections)])
        body = engine.current_system.bodies[index % len(engine.current_system.bodies)]
        engine.orbit(body.id)
        engine.scan()
        engine.tick(3)


class SaveSlotDeterminismTest(unittest.TestCase):
    def test_each_slot_resumes_its_own_stream_and_state(self):
        engine = SimulationEngine(seed=11)
        _drive(engine, 5)
        first_stream = engine.rng.getstate()
        first_tick = engine.state.time.tick
        first_credits = engine.state.ship.credits

        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(engine.state, slot="alpha")

            _drive(engine, 5, offset=5)
            second_stream = engine.rng.getstate()
            second_tick = engine.state.time.tick
            second_credits = engine.state.ship.credits
            storage.save(engine.state, slot="beta")

            self.assertNotEqual(first_stream, second_stream)

            alpha = SimulationEngine(state=storage.load(slot="alpha"))
            self.assertEqual(alpha.rng.getstate(), first_stream)
            self.assertEqual(alpha.state.time.tick, first_tick)
            self.assertEqual(alpha.state.ship.credits, first_credits)

            beta = SimulationEngine(state=storage.load(slot="beta"))
            self.assertEqual(beta.rng.getstate(), second_stream)
            self.assertEqual(beta.state.time.tick, second_tick)
            self.assertEqual(beta.state.ship.credits, second_credits)

    def test_each_slot_listing_reports_its_own_save(self):
        engine = SimulationEngine(seed=7)
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(engine.state, slot="alpha")
            _drive(engine, 3)
            storage.save(engine.state, slot="beta")
            slots = {row["slot"] for row in storage.list_saves()}
        self.assertIn("alpha", slots)
        self.assertIn("beta", slots)

    def test_loading_a_slot_does_not_touch_the_other_file(self):
        engine = SimulationEngine(seed=7)
        _drive(engine, 3)
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(engine.state, slot="alpha")
            _drive(engine, 3, offset=3)
            storage.save(engine.state, slot="beta")
            beta_before = storage.load(slot="beta")
            storage.load(slot="alpha")
            beta_after = storage.load(slot="beta")
        self.assertEqual(beta_after.to_dict(), beta_before.to_dict())


if __name__ == "__main__":
    unittest.main()
