"""Quick-start archetypes: one choice gives a coherent skill spread and starting loadout."""

import unittest

from voidfarer.archetypes import ARCHETYPES
from voidfarer.character import MAX_STARTING_SKILL_TOTAL, SKILL_CATALOG
from voidfarer.engine import SimulationEngine
from voidfarer.smuggling import get_contraband_in_cargo


def _start(archetype):
    engine = SimulationEngine(seed=42)
    profile = {"name": "Test", "archetype": archetype}
    if archetype in ARCHETYPES:
        profile["background"] = ARCHETYPES[archetype]["background"]
        profile["skills"] = dict(ARCHETYPES[archetype]["skills"])
    ok, message = engine.reset(42, profile=profile)
    return engine, ok, message


class ArchetypeCatalogTest(unittest.TestCase):
    def test_every_archetype_spends_exactly_the_creation_budget(self):
        self.assertEqual(set(ARCHETYPES), {"vanguard", "merchant", "smuggler"})
        for key, entry in ARCHETYPES.items():
            self.assertEqual(set(entry["skills"]), set(SKILL_CATALOG), key)
            self.assertEqual(sum(entry["skills"].values()), MAX_STARTING_SKILL_TOTAL, key)
            self.assertTrue(all(1 <= v <= 10 for v in entry["skills"].values()), key)
            self.assertTrue(entry["name"] and entry["summary"] and entry["background"], key)

    def test_the_snapshot_lists_the_archetypes_for_the_creation_screen(self):
        meta = SimulationEngine(seed=42).get_status_snapshot()["character_creation"]
        self.assertEqual([a["id"] for a in meta["archetypes"]], ["vanguard", "merchant", "smuggler"])
        self.assertEqual(meta["archetypes"][0]["skills"], ARCHETYPES["vanguard"]["skills"])


class ArchetypeLoadoutTest(unittest.TestCase):
    def test_vanguard_keeps_the_academy_and_the_default_ship(self):
        engine, ok, message = _start("vanguard")
        self.assertTrue(ok, message)
        ship = engine.state.ship
        self.assertTrue(ship.tutorial.is_active)
        self.assertEqual(ship.cargo_capacity, 40)
        self.assertEqual(ship.trade_pacts, ())

    def test_merchant_gets_a_bigger_hold_a_trade_pact_and_skips_the_academy(self):
        engine, ok, message = _start("merchant")
        self.assertTrue(ok, message)
        ship = engine.state.ship
        self.assertEqual(ship.cargo_capacity, 60)
        self.assertIn("vanguard_syndicate", ship.trade_pacts)
        self.assertTrue(ship.tutorial.skipped)

    def test_smuggler_runs_silent_with_sensor_heavy_power_and_one_contraband_unit(self):
        engine, ok, message = _start("smuggler")
        self.assertTrue(ok, message)
        ship = engine.state.ship
        self.assertEqual(ship.reactor.mode, "silent")
        self.assertGreaterEqual(ship.power.sensors, 35)
        self.assertEqual(sum(get_contraband_in_cargo(ship.cargo).values()), 1)
        self.assertTrue(ship.tutorial.skipped)

    def test_an_unknown_archetype_is_refused(self):
        _, ok, message = _start("pirate_king")
        self.assertFalse(ok)
        self.assertIn("archetype", message.lower())

    def test_no_archetype_is_unchanged_default_start(self):
        engine = SimulationEngine(seed=42)
        ok, _ = engine.reset(42, profile={"name": "Plain"})
        self.assertTrue(ok)
        self.assertTrue(engine.state.ship.tutorial.is_active)
        self.assertEqual(engine.state.ship.cargo_capacity, 40)


if __name__ == "__main__":
    unittest.main()
