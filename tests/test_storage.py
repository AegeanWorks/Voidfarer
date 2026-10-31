"""Unit tests for atomic persistence, crash safety, and shadow backup recovery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.engine import SimulationEngine
from voidfarer.storage import StorageManager


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def test_save_and_load(self):
        saved_path = self.storage.save(self.engine.state)
        self.assertTrue(saved_path.exists())

        loaded_state = self.storage.load()
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state.ship.commander_name, self.engine.state.ship.commander_name)
        self.assertEqual(loaded_state.ship.credits, self.engine.state.ship.credits)

    def test_dock_purchase_cost_basis_round_trips(self):
        station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(station.id)
        ok, msg = self.engine.trade("titanium", 2, is_buy=True)
        self.assertTrue(ok, msg)
        lots = dict(self.engine.state.local_dock_purchases)
        self.assertTrue(lots)

        self.storage.save(self.engine.state)
        loaded = self.storage.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.local_dock_purchases, lots)

        reloaded_engine = SimulationEngine(state=loaded)
        self.assertEqual(reloaded_engine._local_dock_purchases, lots)

    def test_corrupt_file_quarantine_and_backup_recovery(self):
        # 1. Save valid state
        self.storage.save(self.engine.state)

        # 2. Modify state and save again to create shadow .bak
        new_ship = self.engine.state.ship.__class__(
            commander_name="Astraea-Prime",
            callsign=self.engine.state.ship.callsign,
            ship_class=self.engine.state.ship.ship_class,
            hull=self.engine.state.ship.hull,
            max_hull=self.engine.state.ship.max_hull,
            shield=self.engine.state.ship.shield,
            max_shield=self.engine.state.ship.max_shield,
            fuel=self.engine.state.ship.fuel,
            max_fuel=self.engine.state.ship.max_fuel,
            credits=self.engine.state.ship.credits,
            cargo=self.engine.state.ship.cargo,
            cargo_capacity=self.engine.state.ship.cargo_capacity,
            current_system_id=self.engine.state.ship.current_system_id,
            orbiting_body_id=self.engine.state.ship.orbiting_body_id,
            power=self.engine.state.ship.power,
            upgrades=self.engine.state.ship.upgrades,
            flight_log=self.engine.state.ship.flight_log,
        )
        self.engine.state = self.engine.state.__class__(
            version=self.engine.state.version,
            galaxy_seed=self.engine.state.galaxy_seed,
            ship=new_ship,
            systems=self.engine.state.systems,
            visited_systems=self.engine.state.visited_systems,
            active_anomaly=self.engine.state.active_anomaly,
            stats=self.engine.state.stats,
        )
        self.storage.save(self.engine.state)


        # 3. Corrupt primary save file
        with open(self.storage.save_file, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON CORRUPTION ...")

        # 4. Loading should quarantine corrupt file and recover from .bak
        recovered = self.storage.load()
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.ship.callsign, self.engine.state.ship.callsign)

        # Check quarantine file was generated
        corrupt_files = list(Path(self.temp_dir.name).glob("*.corrupt_*"))
        self.assertEqual(len(corrupt_files), 1)


    def test_failed_atomic_replace_raises_and_preserves_previous_save(self):
        self.storage.save(self.engine.state)
        original = self.storage.save_file.read_bytes()

        with patch("voidfarer.storage.os.replace", side_effect=OSError("file locked")):
            with self.assertRaises(OSError):
                self.storage.save(self.engine.state)

        self.assertEqual(self.storage.save_file.read_bytes(), original)

    def test_schema_invalid_primary_falls_back_to_backup(self):
        self.storage.save(self.engine.state)
        self.storage.save(self.engine.state)
        self.assertTrue(self.storage.save_file.with_suffix(".bak").exists())

        self.storage.save_file.write_text('{"version": 1}', encoding="utf-8")
        recovered = self.storage.load()

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.ship.commander_name, self.engine.state.ship.commander_name)
        self.assertEqual(len(list(Path(self.temp_dir.name).glob("*.corrupt_*"))), 1)

    def test_invalid_utf8_does_not_crash_loading(self):
        self.storage.save_file.write_bytes(b"\xff\xfe\x00broken")
        self.assertIsNone(self.storage.load())

    def test_multiple_save_slots_persist_list_and_delete_independently(self):
        self.storage.save(self.engine.state)
        alt_engine = SimulationEngine(seed=99)
        alt_engine.tick(3)
        slot_path = self.storage.save(alt_engine.state, slot="slot_1")
        self.assertTrue(slot_path.exists())
        self.assertEqual(slot_path.name, "voidfarer_save_slot_1.json")

        saves = self.storage.list_saves()
        slots = {entry["slot"]: entry for entry in saves}
        self.assertIn("default", slots)
        self.assertIn("slot_1", slots)
        self.assertEqual(slots["slot_1"]["tick"], 3)
        self.assertIn("credits", slots["slot_1"])

        loaded_default = self.storage.load("default")
        loaded_slot1 = self.storage.load("slot_1")
        self.assertIsNotNone(loaded_default)
        self.assertIsNotNone(loaded_slot1)
        self.assertEqual(loaded_default.galaxy_seed, 42)
        self.assertEqual(loaded_slot1.galaxy_seed, 99)

        self.assertTrue(self.storage.delete_save("slot_1"))
        self.assertIsNone(self.storage.load("slot_1"))
        self.assertIsNotNone(self.storage.load("default"))

    def test_invalid_save_slot_name_raises_value_error(self):
        for bad_slot in ("../escape", "slot/2", "slot with spaces", "a" * 45):
            with self.assertRaises(ValueError):
                self.storage.save(self.engine.state, slot=bad_slot)


if __name__ == "__main__":
    unittest.main()
