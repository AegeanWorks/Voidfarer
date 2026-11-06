"""Regression tests for faction perks, enemy reputation rewards, and multi-stat relics."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.enemies import ENEMY_ARCHETYPES
from voidfarer.factions import get_faction_service_perks
from voidfarer.models import CombatEncounter, PrecursorRelic
from voidfarer.retention import (
    CATALOG_RELICS,
    RELIC_SET_THRESHOLDS,
    calculate_passive_multipliers,
    relic_completed_sets,
    relic_set_bonuses,
)


class RelicSetBonusTest(unittest.TestCase):
    def _relic(self, rid, rarity):
        return PrecursorRelic(
            id=rid, name=rid, rarity=rarity, description="",
            passive_stat="scan_bounty", stat_multiplier=0.0,
        )

    def test_no_set_bonus_below_threshold(self):
        relics = (self._relic("a", "common"), self._relic("b", "common"))
        self.assertEqual(relic_set_bonuses(relics), {})

    def test_common_set_grants_scan_bonus(self):
        relics = tuple(self._relic(f"c{i}", "common") for i in range(3))
        b = relic_set_bonuses(relics)
        self.assertAlmostEqual(b.get("scan_bounty", 0.0), 0.05)

    def test_rare_set_grants_scan_and_trade(self):
        relics = tuple(self._relic(f"r{i}", "rare") for i in range(3))
        b = relic_set_bonuses(relics)
        self.assertAlmostEqual(b.get("scan_bounty", 0.0), 0.10)
        self.assertAlmostEqual(b.get("trade_margin", 0.0), 0.05)

    def test_epic_set_grants_combat_and_shield(self):
        relics = tuple(self._relic(f"e{i}", "epic") for i in range(2))
        b = relic_set_bonuses(relics)
        self.assertAlmostEqual(b.get("laser_dmg", 0.0), 0.15)
        self.assertAlmostEqual(b.get("shield_cap", 0.0), 10.0)

    def test_legendary_set_grants_all(self):
        relics = (self._relic("l1", "legendary"),)
        b = relic_set_bonuses(relics)
        self.assertAlmostEqual(b.get("scan_bounty", 0.0), 0.25)
        self.assertAlmostEqual(b.get("trade_margin", 0.0), 0.25)
        self.assertAlmostEqual(b.get("laser_dmg", 0.0), 0.25)

    def test_set_bonus_applied_in_passive_multipliers(self):
        ship = SimulationEngine(seed=1).state.ship
        relics = tuple(self._relic(f"c{i}", "common") for i in range(3))
        ship = ship.__class__(**{**ship.__dict__, "relics": relics})
        mults = calculate_passive_multipliers(ship)
        # base scan_bounty 1.0 * streak(1) + 0.05 set bonus = 1.05
        self.assertAlmostEqual(mults["scan_bounty"], 1.05, places=2)

    def test_completed_sets_follow_the_shared_thresholds(self):
        full = tuple(
            self._relic(f"{rarity}_{index}", rarity)
            for rarity, count in RELIC_SET_THRESHOLDS.items()
            for index in range(count)
        )
        self.assertEqual(relic_completed_sets(full), len(RELIC_SET_THRESHOLDS))
        self.assertEqual(
            relic_completed_sets(full[:-1]), len(RELIC_SET_THRESHOLDS) - 1
        )
from voidfarer.server import start_background_server
from voidfarer.storage import StorageManager
from voidfarer.story import STORY_RELICS


class FactionPerkTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.orbit("sol_body_1")

    def _set_standing(self, faction_id, standing):
        standings = dict(self.engine.state.ship.faction_standings)
        standings[faction_id] = standing
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(faction_standings=standings)
        )

    def test_friendly_faction_grants_repair_discount(self):
        self._set_standing("sol_coalition", 25)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(hull=50, credits=1000)
        )
        ok, _ = self.engine.repair_hull(10)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.credits, 966)

    def test_allied_faction_grants_free_refuel(self):
        self._set_standing("sol_coalition", 70)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fuel=50, credits=1000)
        )
        ok, _ = self.engine.refuel(10)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.credits, 1000)

    def test_syndicate_standing_adds_trade_margin(self):
        baseline = get_faction_service_perks("vanguard_syndicate", 0)["trade_margin"]
        friendly = get_faction_service_perks("vanguard_syndicate", 25)["trade_margin"]
        self.assertGreater(friendly, baseline)

    def test_faction_specific_tier_perks(self):
        self.assertEqual(get_faction_service_perks("precursor_watch", 25)["scan_xp_bonus"], 0.25)
        self.assertEqual(get_faction_service_perks("nebula_collective", 25)["drone_yield_bonus"], 0.30)
        self.assertTrue(get_faction_service_perks("sol_coalition", 70)["free_refuel"])


class EnemyRepRewardTest(unittest.TestCase):
    def _victory(self, archetype_id: str):
        engine = SimulationEngine(seed=42)
        archetype = ENEMY_ARCHETYPES[archetype_id]
        combat = CombatEncounter(
            id=f"test_{archetype_id}",
            enemy_name=archetype.name,
            enemy_class=archetype.enemy_class,
            enemy_hull=1,
            enemy_max_hull=1,
            enemy_damage=0,
            bounty_credits=10,
            salvage_commodity=archetype.salvage_commodity,
            faction_id=archetype.faction_id,
            special_ability="none",
            archetype_id=archetype_id,
        )
        engine.state = engine._clone_state(active_combat=combat)
        return engine, engine.combat_action("fire_lasers")

    def test_warlord_rep_rewards_are_applied(self):
        engine, (ok, _) = self._victory("warlord_dreadnought")
        self.assertTrue(ok)
        self.assertGreater(engine.state.ship.faction_standings.get("nebula_collective", 0), 0)
        self.assertGreater(engine.state.ship.faction_standings.get("vanguard_syndicate", 0), 0)
        self.assertLess(engine.state.ship.faction_standings.get("outlaw_corsairs", 0), 0)

    def test_corporate_rep_rewards_update_corp_standings(self):
        engine, (ok, _) = self._victory("corporate_enforcer")
        self.assertTrue(ok)
        self.assertLess(engine.state.ship.corp_standings.get("hyperion_dynamics", 0), 0)

    def test_precursor_kill_reduces_precursor_standing(self):
        engine, (ok, _) = self._victory("precursor_sentinel")
        self.assertTrue(ok)
        self.assertLess(engine.state.ship.faction_standings.get("precursor_watch", 0), 0)


class Tier2TalentTest(unittest.TestCase):
    def _mults(self, specs):
        from dataclasses import replace
        engine = SimulationEngine(seed=42)
        ship = replace(engine.state.ship, mastery=replace(engine.state.ship.mastery, specializations=specs))
        return calculate_passive_multipliers(ship)

    def test_tier2_talents_apply_to_passives(self):
        base = self._mults(("void_cartographer",))
        full = self._mults(("void_cartographer", "deep_space_arrays", "overcharge_capacitors", "drone_armada", "black_market_contacts"))
        self.assertGreater(full["scan_bounty"], base["scan_bounty"])
        self.assertGreater(full["relic_find"], base["relic_find"])
        self.assertGreater(full["laser_dmg"], base["laser_dmg"])
        self.assertGreater(full["shield_cap"], base["shield_cap"])
        self.assertGreater(full["drone_yield"], base["drone_yield"])
        self.assertGreater(full["trade_margin"], base["trade_margin"])


class MultiStatRelicTest(unittest.TestCase):
    def test_relic_bonuses_round_trip(self):
        relic = PrecursorRelic(
            id="multi", name="Multi", rarity="legendary", description="Two effects.",
            passive_stat="laser_dmg", stat_multiplier=0.20, bonuses={"scan_bounty": 0.10},
        )
        restored = PrecursorRelic.from_dict(relic.to_dict())
        self.assertEqual(restored.bonuses, {"scan_bounty": 0.10})

    def test_eye_of_void_boosts_laser_and_scan(self):
        engine = SimulationEngine(seed=42)
        relic = next(r for r in CATALOG_RELICS if r.id == "relic_eye_of_void")
        ship = engine._clone_ship(relics=(relic,))
        multipliers = calculate_passive_multipliers(ship)
        self.assertAlmostEqual(multipliers["laser_dmg"], 1.6)
        self.assertAlmostEqual(multipliers["scan_bounty"], 1.6)

    def test_core_matrix_boosts_fuel_and_laser(self):
        engine = SimulationEngine(seed=42)
        ship = engine._clone_ship(relics=(STORY_RELICS["relic_core_matrix"],))
        multipliers = calculate_passive_multipliers(ship)
        self.assertLess(multipliers["fuel_efficiency"], 1.0)
        self.assertGreater(multipliers["laser_dmg"], 1.0)

    def test_sentinel_matrix_applies_hull_and_shield(self):
        engine = SimulationEngine(seed=42)
        hull, max_hull, shield, max_shield = engine._apply_relic_stat_bonuses(
            100, 100, 100, 100, [STORY_RELICS["relic_sentinel_matrix"]]
        )
        self.assertEqual((hull, max_hull), (150, 150))
        self.assertEqual((shield, max_shield), (140, 140))


class BackgroundServerTest(unittest.TestCase):
    def test_background_server_starts_and_stops(self):
        engine = SimulationEngine(seed=42)
        temp = __import__("tempfile").TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        storage = StorageManager(temp.name)
        server = start_background_server(engine, storage, port=0)
        self.assertIsNotNone(server)
        self.assertGreater(server.port, 0)
        server.stop()


if __name__ == "__main__":
    unittest.main()
