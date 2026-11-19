"""A pre-jump checkpoint replays the same risky jump (ADR-410)."""

from __future__ import annotations

import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory

from voidfarer.engine import SimulationEngine
from voidfarer.storage import StorageManager

WALL_CLOCK = {"completed_at", "created_at", "started_at", "saved_at", "timestamp", "recorded_at"}


def _strip_clock(value, key=None):
    if key in WALL_CLOCK:
        return "<clock>"
    if isinstance(value, dict):
        return {name: _strip_clock(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_strip_clock(item) for item in value]
    return value


def _lower_security(engine: SimulationEngine, target_id: str) -> None:
    system = engine.state.systems[target_id]
    engine.state = engine._clone_state(
        systems={**engine.state.systems, target_id: replace(system, security=0.1)}
    )


class CheckpointResumeTest(unittest.TestCase):
    def test_the_checkpoint_slot_replays_the_same_risky_jump(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            engine = SimulationEngine(seed=7)
            engine.checkpoint_hook = storage.checkpoint_writer()
            target = engine.current_system.connections[0]
            _lower_security(engine, target)

            ok, message = engine.jump(target)
            self.assertTrue(ok, message)
            self.assertTrue((storage.data_dir / "voidfarer_save_checkpoint.json").exists())
            live = engine.state.to_dict()

            checkpoint = storage.load(slot="checkpoint")
            self.assertIsNotNone(checkpoint)
            replay = SimulationEngine(state=checkpoint)
            ok, message = replay.jump(target)
            self.assertTrue(ok, message)

        self.assertEqual(_strip_clock(replay.state.to_dict()), _strip_clock(live))

    def test_a_secure_jump_writes_no_checkpoint(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            engine = SimulationEngine(seed=7)
            engine.checkpoint_hook = storage.checkpoint_writer()
            target = engine.current_system.connections[0]
            system = engine.state.systems[target]
            engine.state = engine._clone_state(
                systems={**engine.state.systems, target: replace(system, security=0.9)}
            )
            ok, message = engine.jump(target)
            self.assertTrue(ok, message)
            self.assertIsNone(storage.load(slot="checkpoint"))


if __name__ == "__main__":
    unittest.main()
