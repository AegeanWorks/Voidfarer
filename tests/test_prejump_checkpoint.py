"""A rolling 'checkpoint' save slot is written before a risky jump or a void dive."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer.engine import SimulationEngine
from voidfarer.storage import CHECKPOINT_SLOT, StorageManager


def _engine_with_neighbour_security(security: float):
    tmp = tempfile.TemporaryDirectory()
    storage = StorageManager(Path(tmp.name))
    engine = SimulationEngine(seed=42)
    target_id = engine.current_system.connections[0]
    systems = dict(engine.state.systems)
    systems[target_id] = replace(systems[target_id], security=security)
    engine.state = engine._clone_state(
        systems=systems, ship=engine._clone_ship(fuel=engine.state.ship.max_fuel)
    )
    engine.checkpoint_hook = storage.checkpoint_writer()
    return tmp, storage, engine, target_id


class PreJumpCheckpointTest(unittest.TestCase):
    def test_a_low_security_jump_writes_the_pre_jump_state(self):
        tmp, storage, engine, target = _engine_with_neighbour_security(0.2)
        self.addCleanup(tmp.cleanup)
        origin = engine.state.ship.current_system_id
        ok, message = engine.jump(target)
        self.assertTrue(ok, message)
        saved = storage.load(CHECKPOINT_SLOT)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.ship.current_system_id, origin)
        self.assertEqual(engine.state.ship.current_system_id, target)

    def test_a_secure_jump_writes_no_checkpoint(self):
        tmp, storage, engine, target = _engine_with_neighbour_security(0.9)
        self.addCleanup(tmp.cleanup)
        ok, message = engine.jump(target)
        self.assertTrue(ok, message)
        self.assertIsNone(storage.load(CHECKPOINT_SLOT))

    def test_the_hook_defaults_to_none_so_a_bare_engine_never_writes(self):
        engine = SimulationEngine(seed=42)
        self.assertIsNone(engine.checkpoint_hook)


class CheckpointWiringTest(unittest.TestCase):
    def test_the_cli_and_the_server_install_the_checkpoint_hook(self):
        from voidfarer import cli, server
        import inspect
        self.assertIn("engine.checkpoint_hook = storage.checkpoint_writer()", inspect.getsource(cli))
        self.assertIn("engine.checkpoint_hook = storage.checkpoint_writer()", inspect.getsource(server))


if __name__ == "__main__":
    unittest.main()
