"""A save resumes the same random stream instead of replaying earlier rolls (ADR-405)."""

from __future__ import annotations

import random
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from voidfarer.engine import SimulationEngine
from voidfarer.storage import StorageManager

WALL_CLOCK = {"completed_at", "created_at", "started_at", "saved_at", "timestamp", "recorded_at"}


def _strip_clock(value, key=None):
    if key in WALL_CLOCK:
        return "<clock>"
    if isinstance(value, dict):
        return {k: _strip_clock(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_strip_clock(item) for item in value]
    return value


def _drive(engine: SimulationEngine, actions: int) -> None:
    """A deterministic hop-and-scan tour that draws from the RNG."""
    for _ in range(actions):
        connections = engine.current_system.connections
        if connections:
            engine.jump(connections[_ % len(connections)])
        body = engine.current_system.bodies[_ % len(engine.current_system.bodies)]
        engine.orbit(body.id)
        engine.scan()
        engine.tick(3)


class RngCheckpointTest(unittest.TestCase):
    def test_a_mutation_captures_the_live_rng_stream(self):
        engine = SimulationEngine(seed=7)
        engine.jump(engine.current_system.connections[0])
        self.assertEqual(engine.state.rng_state, engine.rng.getstate())

    def test_the_save_round_trips_the_stream(self):
        with TemporaryDirectory() as temp_dir:
            engine = SimulationEngine(seed=7)
            _drive(engine, 6)
            StorageManager(temp_dir).save(engine.state)
            loaded = StorageManager(temp_dir).load()
            self.assertEqual(loaded.rng_state, engine.rng.getstate())

    def test_a_loaded_engine_resumes_the_stream(self):
        with TemporaryDirectory() as temp_dir:
            engine = SimulationEngine(seed=7)
            _drive(engine, 6)
            StorageManager(temp_dir).save(engine.state)
            resumed = SimulationEngine(state=StorageManager(temp_dir).load())
            self.assertEqual(resumed.rng.getstate(), engine.rng.getstate())
            self.assertEqual(resumed.rng.random(), engine.rng.random())

    def test_a_legacy_save_without_the_field_seeds_a_fresh_stream(self):
        engine = SimulationEngine(seed=7)
        payload = engine.state.to_dict()
        payload.pop("rng_state")
        restored = type(engine.state).from_dict(payload)
        self.assertIsNone(restored.rng_state)
        resumed = SimulationEngine(state=restored)
        self.assertEqual(resumed.seed, 7)
        self.assertEqual(resumed.rng.getstate(), random.Random(7).getstate())

    def test_a_malformed_stream_falls_back_to_the_seed(self):
        engine = SimulationEngine(seed=7)
        payload = engine.state.to_dict()
        payload["rng_state"] = [3, [1, 2], None]
        restored = type(engine.state).from_dict(payload)
        self.assertIsNone(restored.rng_state)

    def test_a_saved_campaign_continues_like_the_uninterrupted_one(self):
        seed = 11
        straight = SimulationEngine(seed=seed)
        _drive(straight, 12)

        with TemporaryDirectory() as temp_dir:
            split = SimulationEngine(seed=seed)
            _drive(split, 6)
            StorageManager(temp_dir).save(split.state)
            resumed = SimulationEngine(state=StorageManager(temp_dir).load())
            _drive(resumed, 6)

        self.assertEqual(
            _strip_clock(straight.state.to_dict()),
            _strip_clock(resumed.state.to_dict()),
        )


if __name__ == "__main__":
    unittest.main()
