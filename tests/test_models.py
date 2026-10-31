"""Unit tests for domain state models and frozen DTO serialization."""

import unittest
from voidfarer.models import (
    BountyContract,
    CelestialBody,
    CombatEncounter,
    FleetDrone,
    GameState,
    PilotMastery,
    PrecursorRelic,
    ShipPower,
    ShipState,
    ShipUpgrade,
    StarSystem,
    StoryChapter,
    StoryChoice,
    StoryState,
    StoryTransmission,
    TutorialState,
    TutorialStep,
)


class TestModels(unittest.TestCase):
    def test_ship_power_validation(self):
        p = ShipPower(engines=30, shields=30, sensors=20, weapons=20)
        self.assertEqual(p.engines + p.shields + p.sensors + p.weapons, 100)

        with self.assertRaises(ValueError):
            ShipPower(engines=50, shields=50, sensors=10, weapons=0)

        with self.assertRaises(ValueError):
            ShipPower(engines=-5, shields=30, sensors=30, weapons=20)

    def test_celestial_body_serialization(self):
        body = CelestialBody(
            id="sol_body_1",
            name="Earth Citadel",
            body_type="orbital_station",
            orbit_radius=1.0,
            orbit_speed=0.05,
            current_angle=0.25,
            radius_km=6371.0,
            color="#00f0ff",
            hazards=("space_debris",),
            station_dockable=True,
            market_archetype="high_tech",
            scan_completed=True,
            scan_discovery="Automated orbital fabricators.",
        )
        d = body.to_dict()
        restored = CelestialBody.from_dict(d)
        self.assertEqual(restored.id, body.id)
        self.assertEqual(restored.name, body.name)
        self.assertTrue(restored.station_dockable)
        self.assertEqual(restored.market_archetype, "high_tech")

    def test_star_system_serialization(self):
        body = CelestialBody(
            id="test_star",
            name="Test Star",
            body_type="star",
            orbit_radius=0.0,
            orbit_speed=0.0,
            current_angle=0.0,
            radius_km=696340.0,
            color="#ffd700",
        )
        system = StarSystem(
            id="test_sys",
            name="Test System",
            seed=1234,
            x=10.5,
            y=-20.5,
            spectral_type="G",
            color="#ffd700",
            security=0.85,
            faction="Test Faction",
            bodies=(body,),
            connections=("sol", "vega"),
        )
        d = system.to_dict()
        restored = StarSystem.from_dict(d)
        self.assertEqual(restored.id, "test_sys")
        self.assertEqual(len(restored.bodies), 1)
        self.assertEqual(restored.connections, ("sol", "vega"))

    def test_fleet_drone_serialization(self):
        drone = FleetDrone(
            id="drone_mining_1",
            name="Mining Sentry Alpha",
            drone_type="mining",
            assigned_system_id="sol",
            status="harvesting",
            cargo_accumulated=8,
            credits_accumulated=150,
        )
        d = drone.to_dict()
        restored = FleetDrone.from_dict(d)
        self.assertEqual(restored.id, drone.id)
        self.assertEqual(restored.drone_type, "mining")
        self.assertEqual(restored.cargo_accumulated, 8)

    def test_ship_upgrade_serialization(self):
        upg = ShipUpgrade(
            id="warp_booster_mk2",
            name="Hyperdrive Booster MK-II",
            slot="engines",
            cost=850,
            description="Quantum field accelerator.",
            stat_bonus={"fuel_efficiency": 0.35},
        )
        d = upg.to_dict()
        restored = ShipUpgrade.from_dict(d)
        self.assertEqual(restored.id, "warp_booster_mk2")
        self.assertEqual(restored.slot, "engines")
        self.assertEqual(restored.cost, 850)

    def test_combat_encounter_serialization(self):
        combat = CombatEncounter(
            id="combat_123",
            enemy_name="Outlaw Raider",
            enemy_class="Corsair",
            enemy_hull=75,
            enemy_max_hull=80,
            enemy_damage=15,
            bounty_credits=500,
        )
        d = combat.to_dict()
        restored = CombatEncounter.from_dict(d)
        self.assertEqual(restored.id, "combat_123")
        self.assertEqual(restored.enemy_name, "Outlaw Raider")
        self.assertEqual(restored.bounty_credits, 500)

    def test_bounty_contract_serialization(self):
        contract = BountyContract(
            id="contract_1",
            title="Pirate Sweep",
            description="Eliminate 2 corsairs",
            category="combat",
            target_count=2,
            current_count=1,
            reward_credits=800,
            reward_xp=200,
            reward_relic_tier="rare",
            completed=False,
        )
        d = contract.to_dict()
        restored = BountyContract.from_dict(d)
        self.assertEqual(restored.id, "contract_1")
        self.assertEqual(restored.category, "combat")
        self.assertEqual(restored.reward_relic_tier, "rare")
        self.assertEqual(restored.current_count, 1)

    def test_precursor_relic_serialization(self):
        relic = PrecursorRelic(
            id="relic_void_eye",
            name="Eye of the Void",
            rarity="legendary",
            description="Precursor tachyon resonator",
            passive_stat="laser_dmg",
            stat_multiplier=0.25,
            discovered_at_system="sol",
        )
        d = relic.to_dict()
        restored = PrecursorRelic.from_dict(d)
        self.assertEqual(restored.id, "relic_void_eye")
        self.assertEqual(restored.rarity, "legendary")
        self.assertEqual(restored.stat_multiplier, 0.25)

    def test_pilot_mastery_serialization(self):
        mastery = PilotMastery(
            level=3,
            xp=1250,
            next_level_xp=1500,
            talent_points=1,
            specializations=("void_cartographer",),
        )
        d = mastery.to_dict()
        restored = PilotMastery.from_dict(d)
        self.assertEqual(restored.level, 3)
        self.assertEqual(restored.talent_points, 1)
        self.assertEqual(restored.specializations, ("void_cartographer",))

    def test_game_state_roundtrip(self):
        contract = BountyContract(
            id="c1",
            title="Scan Vega",
            description="Scan planets",
            category="exploration",
            target_count=1,
            current_count=0,
            reward_credits=500,
        )
        relic = PrecursorRelic(
            id="r1",
            name="Dark Core",
            rarity="rare",
            description="Dark matter diode",
            passive_stat="shield_cap",
            stat_multiplier=0.15,
        )
        mastery = PilotMastery(level=2, xp=600, next_level_xp=1000, talent_points=1)
        ship = ShipState(
            commander_name="Astraea",
            callsign="VF-Vanguard",
            ship_class="Corvette",
            hull=100,
            max_hull=100,
            shield=90,
            max_shield=100,
            fuel=45,
            max_fuel=50,
            credits=3500,
            cargo={"fuel_cells": 3},
            cargo_capacity=30,
            current_system_id="sol",
            orbiting_body_id=None,
            equipped_upgrades={"cargo": "subspace_cargo_pods"},
            fleet_drones=(
                FleetDrone(
                    id="d1",
                    name="Drone 1",
                    drone_type="scout",
                    assigned_system_id="sol",
                ),
            ),
            streak=3,
            relics=(relic,),
            mastery=mastery,
            active_contracts=(contract,),
            tactical_combo=2,
            near_miss_scanner_bonus=0.25,
        )
        state = GameState(
            version=1,
            galaxy_seed=42,
            ship=ship,
            systems={},
            visited_systems=("sol",),
        )
        d = state.to_dict()
        restored = GameState.from_dict(d)
        self.assertEqual(restored.version, 1)
        self.assertEqual(restored.ship.commander_name, "Astraea")
        self.assertEqual(restored.ship.credits, 3500)
        self.assertEqual(len(restored.ship.fleet_drones), 1)
        self.assertEqual(restored.ship.streak, 3)
        self.assertEqual(len(restored.ship.relics), 1)
        self.assertEqual(restored.ship.relics[0].name, "Dark Core")
        self.assertEqual(restored.ship.mastery.level, 2)
        self.assertEqual(len(restored.ship.active_contracts), 1)
        self.assertEqual(restored.ship.tactical_combo, 2)
        self.assertAlmostEqual(restored.ship.near_miss_scanner_bonus, 0.25)

    def test_tutorial_and_story_models_serialization(self):
        step = TutorialStep(
            id="step_test",
            title="Test Step",
            instruction="Test instructions.",
            hint="Test hint.",
            reward_credits=500,
            reward_xp=150,
        )
        step_d = step.to_dict()
        step_restored = TutorialStep.from_dict(step_d)
        self.assertEqual(step_restored.id, "step_test")
        self.assertEqual(step_restored.action_target, "test")
        self.assertEqual(step_restored.reward_credits, 500)

        tut_state = TutorialState(
            active=True,
            current_step_index=0,
            steps=(step,),
            completed=False,
            skipped=False,
        )
        self.assertTrue(tut_state.is_active)
        self.assertEqual(tut_state.current_step.id, "step_test")
        tut_d = tut_state.to_dict()
        tut_restored = TutorialState.from_dict(tut_d)
        self.assertTrue(tut_restored.is_active)
        self.assertEqual(len(tut_restored.steps), 1)

        choice = StoryChoice(
            id="c1",
            text="Make a stand",
            faction_alignment="coalition",
            reward_credits=1000,
            outcome_text="Loyalty proven.",
        )
        tx = StoryTransmission(
            speaker="Admiral",
            callsign="Command",
            channel="Secure",
            message="Stand by.",
        )
        chapter = StoryChapter(
            chapter_index=0,
            title="Act 1",
            target_system_id="sol",
            objective="Meet contact.",
            transmission=tx,
            choices=(choice,),
        )
        story_state = StoryState(
            campaign_title="Test Campaign",
            current_chapter_index=0,
            chapters=(chapter,),
            transmission_log=(tx,),
            reputation={"coalition": 10},
        )
        story_d = story_state.to_dict()
        story_restored = StoryState.from_dict(story_d)
        self.assertEqual(story_restored.active_act, 1)
        self.assertEqual(story_restored.current_chapter.title, "Act 1")
        self.assertEqual(story_restored.reputation["coalition"], 10)
        self.assertEqual(len(story_restored.transmission_log), 1)


if __name__ == "__main__":
    unittest.main()
