"""Unslotted saves follow the active slot instead of clobbering default (ADR-413)."""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory

from voidfarer.engine import SimulationEngine
from voidfarer.storage import StorageManager


def _engine(seed: int, credits: int) -> SimulationEngine:
    engine = SimulationEngine(seed=seed)
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=credits))
    return engine


class ActiveSlotTest(unittest.TestCase):
    def test_an_autosave_after_loading_a_slot_keeps_that_slot_current(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)          # default
            storage.save(_engine(seed=2, credits=222).state, slot="alpha")
            loaded = storage.load(slot="alpha")
            self.assertEqual(loaded.ship.credits, 222)

            storage.save(loaded)  # an autosave passes no slot

            self.assertEqual(storage.load(slot="default").ship.credits, 111)
            self.assertEqual(storage.load(slot="alpha").ship.credits, 222)

    def test_an_autosave_after_loading_the_default_slot_updates_default(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)
            storage.save(_engine(seed=2, credits=222).state, slot="alpha")
            loaded = storage.load(slot="default")
            self.assertEqual(loaded.ship.credits, 111)

            storage.save(_engine(seed=3, credits=333).state)

            self.assertEqual(storage.load(slot="default").ship.credits, 333)
            self.assertEqual(storage.load(slot="alpha").ship.credits, 222)

    def test_an_explicit_save_switches_the_active_slot(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)
            storage.save(_engine(seed=2, credits=222).state, slot="alpha")

            storage.save(_engine(seed=4, credits=444).state)

            self.assertEqual(storage.load(slot="alpha").ship.credits, 444)
            self.assertEqual(storage.load(slot="default").ship.credits, 111)

    def test_a_plain_load_uses_the_active_slot(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)
            storage.save(_engine(seed=2, credits=222).state, slot="alpha")
            storage.load(slot="alpha")
            self.assertEqual(storage.load().ship.credits, 222)

    def test_deleting_the_active_slot_falls_back_to_default(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)
            storage.save(_engine(seed=2, credits=222).state, slot="alpha")
            storage.load(slot="alpha")
            self.assertTrue(storage.delete_save())

            storage.save(_engine(seed=5, credits=555).state)

            self.assertEqual(storage.load(slot="default").ship.credits, 555)


    def test_a_checkpoint_save_does_not_steal_the_active_slot(self):
        with TemporaryDirectory() as temp_dir:
            storage = StorageManager(temp_dir)
            storage.save(_engine(seed=1, credits=111).state)
            storage.save(_engine(seed=2, credits=222).state, slot="alpha")
            storage.load(slot="alpha")

            storage.checkpoint_writer()(_engine(seed=6, credits=666).state)
            self.assertEqual(storage.active_slot, "alpha")

            storage.save(_engine(seed=7, credits=777).state)
            self.assertEqual(storage.load(slot="alpha").ship.credits, 777)
            self.assertEqual(storage.load(slot="default").ship.credits, 111)
            self.assertEqual(storage.load(slot="checkpoint").ship.credits, 666)


if __name__ == "__main__":
    unittest.main()
