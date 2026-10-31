"""Unit tests for Factions, Corporations, and Enhanced Combat Enemies."""

import unittest
from voidfarer.models import CombatEncounter, ShipState, StarSystem
from voidfarer.factions import (
    CANONICAL_FACTIONS,
    CANONICAL_CORPORATIONS,
    get_faction,
    get_corporation,
    get_faction_standing_tier,
    calculate_faction_market_modifier,
)
from voidfarer.enemies import (
    ENEMY_ARCHETYPES,
    generate_system_enemy,
)


class TestFactionsAndCorporations(unittest.TestCase):
    """Test faction registries, corporations, standing calculations, and market modifiers."""

    def test_canonical_factions_exist(self):
        expected = ["sol_coalition", "vanguard_syndicate", "precursor_watch", "nebula_collective", "outlaw_corsairs"]
        for fid in expected:
            self.assertIn(fid, CANONICAL_FACTIONS)
            faction = get_faction(fid)
            self.assertIsNotNone(faction)
            self.assertTrue(len(faction.name) > 0)
            self.assertTrue(len(faction.description) > 0)
            self.assertTrue(len(faction.headquarters_system) > 0)

    def test_canonical_corporations_exist(self):
        expected = ["hyperion_dynamics", "astraea_pharma", "omnicorp_mining", "nexus_cybernetics", "vortex_fuel"]
        for cid in expected:
            self.assertIn(cid, CANONICAL_CORPORATIONS)
            corp = get_corporation(cid)
            self.assertIsNotNone(corp)
            self.assertTrue(len(corp.name) > 0)
            self.assertTrue(len(corp.specialty_commodity) > 0)

    def test_faction_standing_tiers(self):
        tier_hostile, perk_hostile = get_faction_standing_tier(-60)
        self.assertEqual(tier_hostile, "Hostile")
        self.assertIn("Tariff", perk_hostile)

        tier_unfriendly, _ = get_faction_standing_tier(-20)
        self.assertEqual(tier_unfriendly, "Unfriendly")

        tier_neutral, _ = get_faction_standing_tier(10)
        self.assertEqual(tier_neutral, "Neutral")

        tier_friendly, perk_friendly = get_faction_standing_tier(40)
        self.assertEqual(tier_friendly, "Friendly")

        tier_allied, perk_allied = get_faction_standing_tier(85)
        self.assertEqual(tier_allied, "Allied")

    def test_market_modifiers(self):
        mod_hostile = calculate_faction_market_modifier("sol_coalition", -60)
        self.assertGreater(mod_hostile, 1.0)  # Tariff increases prices

        mod_neutral = calculate_faction_market_modifier("sol_coalition", 0)
        self.assertEqual(mod_neutral, 1.0)

        mod_allied = calculate_faction_market_modifier("sol_coalition", 80)
        self.assertLess(mod_allied, 1.0)  # Allied discount reduces purchase price


class TestEnemiesAndCombatModels(unittest.TestCase):
    """Test enemy archetypes, generation, and extended CombatEncounter model."""

    def test_enemy_archetypes(self):
        self.assertIn("corsair_interceptor", ENEMY_ARCHETYPES)
        self.assertIn("syndicate_marauder", ENEMY_ARCHETYPES)
        self.assertIn("corporate_enforcer", ENEMY_ARCHETYPES)
        self.assertIn("precursor_sentinel", ENEMY_ARCHETYPES)
        self.assertIn("warlord_dreadnought", ENEMY_ARCHETYPES)

    def test_generate_system_enemy(self):
        # Sol (high security)
        sol_enemy = generate_system_enemy(system_id="sol", security=1.0, faction="Sol Coalition", seed=42)
        self.assertIsNotNone(sol_enemy)
        self.assertIn(sol_enemy.faction_id, ["hyperion_dynamics", "sol_coalition", "outlaw_corsairs"])

        # Low security system
        pirate_enemy = generate_system_enemy(system_id="rift_station", security=0.05, faction="Outlaw Haven", seed=99)
        self.assertIsNotNone(pirate_enemy)
        self.assertGreaterEqual(pirate_enemy.enemy_hull, 50)
        self.assertGreaterEqual(pirate_enemy.enemy_damage, 10)

    def test_combat_encounter_backward_compatibility(self):
        # Legacy dict without enemy_shield, faction_id, special_ability
        legacy_data = {
            "id": "combat_legacy_123",
            "enemy_name": "Old Pirate Raider",
            "enemy_class": "Pirate Raider",
            "enemy_hull": 75,
            "enemy_max_hull": 75,
            "enemy_damage": 15,
            "bounty_credits": 500,
            "salvage_commodity": "titanium",
        }
        encounter = CombatEncounter.from_dict(legacy_data)
        self.assertEqual(encounter.id, "combat_legacy_123")
        self.assertEqual(encounter.enemy_shield, 0)
        self.assertEqual(encounter.special_ability, "none")
        self.assertEqual(encounter.faction_id, "outlaw_corsairs")

        # Serialization includes new fields
        as_dict = encounter.to_dict()
        self.assertIn("enemy_shield", as_dict)
        self.assertIn("special_ability", as_dict)
        self.assertIn("faction_id", as_dict)

    def test_ship_state_faction_standings_migration(self):
        legacy_ship_data = {
            "commander_name": "Valerius",
            "callsign": "Aegis-7",
            "ship_class": "Vanguard Explorer",
            "hull": 100,
            "max_hull": 100,
            "shield": 100,
            "max_shield": 100,
            "fuel": 50,
            "max_fuel": 50,
            "credits": 1500,
            "cargo": {},
            "cargo_capacity": 30,
            "current_system_id": "sol",
            "story": {
                "campaign_title": "The Precursor Cipher",
                "current_chapter_index": 1,
                "chapters": [],
                "transmission_log": [],
                "reputation": {"coalition": 25, "syndicate": -10, "precursor": 40},
                "completed": False,
            },
        }
        ship = ShipState.from_dict(legacy_ship_data)
        self.assertIn("sol_coalition", ship.faction_standings)
        self.assertEqual(ship.faction_standings["sol_coalition"], 25)
        self.assertEqual(ship.faction_standings["vanguard_syndicate"], -10)
        self.assertEqual(ship.faction_standings["precursor_watch"], 40)
        self.assertIn("hyperion_dynamics", ship.corp_standings)

    def test_tactical_combat_shield_and_actions(self):
        from voidfarer.engine import SimulationEngine
        engine = SimulationEngine(seed=42)

        # Inject an active combat encounter with shields and special ability
        encounter = CombatEncounter(
            id="test_combat_1",
            enemy_name="Test Syndicate Marauder",
            enemy_class="Assault Frigate",
            enemy_hull=80,
            enemy_max_hull=80,
            enemy_damage=15,
            bounty_credits=500,
            salvage_commodity="titanium",
            enemy_shield=30,
            enemy_max_shield=30,
            faction_id="vanguard_syndicate",
            special_ability="shield_drain",
            ability_cooldown=0,
            telegraphed_action="Energy siphon locked",
        )
        engine.state = engine.state.__class__(
            version=engine.state.version,
            galaxy_seed=engine.state.galaxy_seed,
            ship=engine.state.ship,
            systems=engine.state.systems,
            visited_systems=engine.state.visited_systems,
            active_anomaly=None,
            active_combat=encounter,
            stats=engine.state.stats,
        )

        # 1. Targeted subsystem attack on weapons
        ok, msg = engine.combat_action("target_weapons")
        self.assertTrue(ok)
        self.assertIn("Disabled fire-control", msg)
        self.assertIsNotNone(engine.state.active_combat)
        # Enemy damage reduced
        self.assertLess(engine.state.active_combat.enemy_damage, 15)

        # 2. Fire lasers to deplete remaining shield
        ok, msg = engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertIsNotNone(engine.state.active_combat)

        # 3. Deploy Combat Escort drone for direct kinetic armor-piercing strike
        from voidfarer.models import FleetDrone
        escort_drone = FleetDrone(
            id="drone_escort_test",
            name="Combat Escort Beta",
            drone_type="combat_escort",
            assigned_system_id="sol",
            status="combat_ready",
        )
        engine.state = engine.state.__class__(
            version=engine.state.version,
            galaxy_seed=engine.state.galaxy_seed,
            ship=engine._clone_ship(fleet_drones=(escort_drone,)),
            systems=engine.state.systems,
            visited_systems=engine.state.visited_systems,
            active_anomaly=None,
            active_combat=engine.state.active_combat,
            stats=engine.state.stats,
        )
        ok, msg = engine.combat_action("drone_strike")
        self.assertTrue(ok)
        self.assertIn("kinetic torpedo", msg)

    def test_combat_victory_faction_standing_shift(self):
        from voidfarer.engine import SimulationEngine
        engine = SimulationEngine(seed=42)
        initial_sol_rep = engine.state.ship.faction_standings["sol_coalition"]

        # Weak corsair enemy
        corsair = CombatEncounter(
            id="test_corsair_weak",
            enemy_name="Weak Corsair",
            enemy_class="Light Raider",
            enemy_hull=10,
            enemy_max_hull=10,
            enemy_damage=5,
            bounty_credits=300,
            salvage_commodity="fuel_cells",
            enemy_shield=0,
            enemy_max_shield=0,
            faction_id="outlaw_corsairs",
            special_ability="none",
        )
        engine.state = engine.state.__class__(
            version=engine.state.version,
            galaxy_seed=engine.state.galaxy_seed,
            ship=engine.state.ship,
            systems=engine.state.systems,
            visited_systems=engine.state.visited_systems,
            active_anomaly=None,
            active_combat=corsair,
            stats=engine.state.stats,
        )

        ok, msg = engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertIn("VICTORY", msg)
        self.assertIsNone(engine.state.active_combat)
        # Rep with Sol Coalition should increase
        self.assertGreater(engine.state.ship.faction_standings["sol_coalition"], initial_sol_rep)


if __name__ == "__main__":
    unittest.main()

