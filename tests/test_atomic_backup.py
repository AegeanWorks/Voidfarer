"""The shadow backup is an atomic rename, not a second file copy (ADR-419)."""

from __future__ import annotations

import json
import os
import unittest
from tempfile import TemporaryDirectory
from unittest import mock

import voidfarer.storage as storage_module
from voidfarer.engine import SimulationEngine
from voidfarer.storage import StorageManager


def _engine(seed: int, credits: int) -> SimulationEngine:
    engine = SimulationEngine(seed=seed)
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=credits))
    return engine


class AtomicBackupTest(unittest.TestCase):
    def test_save_does_not_copy_the_previous_file(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            first = _engine(seed=1, credits=111)
            second = _engine(seed=2, credits=222)
            storage.save(first.state)

            with mock.patch.object(storage_module.shutil, "copy2", side_effect=AssertionError("copied")):
                storage.save(second.state)

            self.assertEqual(storage.load().ship.credits, 222)
            backup = json.loads(storage.save_file.with_suffix(".bak").read_text(encoding="utf-8"))
            self.assertEqual(backup["ship"]["credits"], 111)

    def test_the_backup_holds_the_previous_save(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)
            storage.save(_engine(seed=2, credits=222).state)
            storage.save(_engine(seed=3, credits=333).state)

            self.assertEqual(storage.load().ship.credits, 333)
            backup = json.loads(storage.save_file.with_suffix(".bak").read_text(encoding="utf-8"))
            self.assertEqual(backup["ship"]["credits"], 222)

    def test_a_first_save_writes_no_backup(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)
            self.assertFalse(storage.save_file.with_suffix(".bak").exists())

    def test_a_failed_install_leaves_the_previous_state_recoverable(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)

            real_replace = os.replace
            calls = {"n": 0}

            def flaky_replace(src, dst):
                calls["n"] += 1
                # First replace moves the current save to the backup; every install
                # attempt after that fails, exercising the retry exhaustion path.
                if calls["n"] >= 2:
                    raise OSError("simulated install failure")
                return real_replace(src, dst)

            with mock.patch.object(storage_module.os, "replace", side_effect=flaky_replace):
                with self.assertRaises(OSError):
                    storage.save(_engine(seed=2, credits=222).state)

            restored = StorageManager(temp_dir).load()
            self.assertIsNotNone(restored)
            self.assertEqual(restored.ship.credits, 111)
            leftovers = [name for name in os.listdir(temp_dir) if name.startswith(".tmp_")]
            self.assertEqual(leftovers, [])

    def test_the_save_round_trips_named_slots(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state, slot="alpha")
            storage.save(_engine(seed=2, credits=222).state, slot="beta")
            self.assertEqual(storage.load(slot="alpha").ship.credits, 111)
            self.assertEqual(storage.load(slot="beta").ship.credits, 222)


if __name__ == "__main__":
    unittest.main()
