"""Unit tests for the item catalog, cargo manifest, and consumable usage."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.inventory import (
    ITEM_CATALOG,
    calculate_cargo_volume,
    get_inventory_manifest,
    get_item_info,
)
from voidfarer.models import CombatEncounter


class TestItemCatalog(unittest.TestCase):
    """Verify catalog integrity, consumable metadata, and fallbacks."""

    def test_catalog_keys_match_item_ids(self):
        for key, item in ITEM_CATALOG.items():
            self.assertEqual(key, item.id)

    def test_consumables_are_usable_with_effects(self):
        consumables = [item for item in ITEM_CATALOG.values() if item.category == "consumable"]
        self.assertGreaterEqual(len(consumables), 4)
        for item in consumables:
            self.assertTrue(item.is_usable)
            self.assertIsNotNone(item.effect_type)
            self.assertGreater(item.effect_amount, 0)

    def test_commodities_are_not_usable(self):
        for item in ITEM_CATALOG.values():
            if item.category == "commodity":
                self.assertFalse(item.is_usable)

    def test_unknown_item_falls_back_to_generic_commodity(self):
        info = get_item_info("mystery_salvage")
        self.assertEqual(info.id, "mystery_salvage")
        self.assertFalse(info.is_usable)

    def test_manifest_skips_empty_stacks_and_computes_volume(self):
        manifest = get_inventory_manifest({"titanium": 3, "fuel_cells": 0})
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["total_volume"], 6)

    def test_cargo_volume_sums_item_footprints(self):
        self.assertEqual(calculate_cargo_volume({"titanium": 3, "fuel_cells": 0}), 6)
        self.assertEqual(calculate_cargo_volume({}), 0)


class TestUseItem(unittest.TestCase):
    """Verify consumable effects, clamping, and cargo bookkeeping."""

    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def _with_cargo(self, cargo, **ship_kwargs):
        ship = self.engine._clone_ship(cargo=cargo, **ship_kwargs)
        self.engine.state = self.engine._clone_state(ship=ship)

    def test_repair_paste_restores_hull_and_consumes_one(self):
        self._with_cargo({"nanite_repair_paste": 2}, hull=10)
        ok, _ = self.engine.use_item("nanite_repair_paste")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.hull, 45)
        self.assertEqual(self.engine.state.ship.cargo["nanite_repair_paste"], 1)

    def test_last_repair_paste_leaves_cargo(self):
        self._with_cargo({"nanite_repair_paste": 1}, hull=10)
        ok, _ = self.engine.use_item("nanite_repair_paste")
        self.assertTrue(ok)
        self.assertNotIn("nanite_repair_paste", self.engine.state.ship.cargo)

    def test_repair_paste_clamps_to_max_hull(self):
        self._with_cargo({"nanite_repair_paste": 1}, hull=95)
        ok, _ = self.engine.use_item("nanite_repair_paste")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.hull, self.engine.state.ship.max_hull)

    def test_use_missing_item_fails(self):
        ok, _ = self.engine.use_item("nanite_repair_paste")
        self.assertFalse(ok)

    def test_commodity_cannot_be_consumed(self):
        self._with_cargo({"titanium": 1})
        ok, _ = self.engine.use_item("titanium")
        self.assertFalse(ok)

    def test_decoy_requires_active_combat(self):
        self._with_cargo({"decoy_countermeasure": 1})
        ok, _ = self.engine.use_item("decoy_countermeasure")
        self.assertFalse(ok)

        combat = CombatEncounter(
            id="decoy_test",
            enemy_name="Corsair Raider",
            enemy_class="Corsair",
            enemy_hull=30,
            enemy_max_hull=30,
            enemy_damage=8,
            bounty_credits=250,
        )
        self.engine.state = self.engine._clone_state(active_combat=combat)
        ok, _ = self.engine.use_item("decoy_countermeasure")
        self.assertTrue(ok)
        self.assertIsNone(self.engine.state.active_combat)


if __name__ == "__main__":
    unittest.main()
