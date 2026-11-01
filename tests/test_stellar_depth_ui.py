"""Unit tests for Stellar Depth, Officer Station Assignments, and Distress Beacons."""

import unittest
from pathlib import Path

from voidfarer.crew import calculate_crew_bonuses, recruit_crew_member
from voidfarer.engine import SimulationEngine
from voidfarer.galaxy import ANOMALIES_CATALOG, GalaxyGenerator
from voidfarer.models import CrewMember


class StellarDepthAndOfficerTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_crew_member_station_property_and_serialization(self):
        member = CrewMember(
            id="officer_01",
            name="Commander Tane",
            role="pilot",
            skill=4,
            station="helm",
        )
        self.assertEqual(member.station, "helm")
        data = member.to_dict()
        self.assertEqual(data["station"], "helm")
        restored = CrewMember.from_dict(data)
        self.assertEqual(restored.station, "helm")

    def test_assign_crew_station_lifecycle(self):
        # Recruit a pilot and an engineer
        pilot = recruit_crew_member("pilot", seed=10, current_count=0)
        engineer = recruit_crew_member("engineer", seed=10, current_count=1)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(crew=(pilot, engineer))
        )

        # 1. Assign pilot to helm
        ok, msg = self.engine.assign_crew_station(pilot.id, "helm")
        self.assertTrue(ok)
        self.assertIn("assigned to the HELM station", msg)
        active_pilot = next(c for c in self.engine.state.ship.crew if c.id == pilot.id)
        self.assertEqual(active_pilot.station, "helm")

        # 2. Reject invalid station
        ok, msg = self.engine.assign_crew_station(pilot.id, "kitchen_deck")
        self.assertFalse(ok)
        self.assertIn("Unknown station", msg)

        # 3. Unseat previous occupant when assigning another crew member to helm
        ok, msg = self.engine.assign_crew_station(engineer.id, "helm")
        self.assertTrue(ok)
        crew_by_id = {c.id: c for c in self.engine.state.ship.crew}
        self.assertEqual(crew_by_id[engineer.id].station, "helm")
        self.assertEqual(crew_by_id[pilot.id].station, "")

        # 4. Relieve engineer from station
        ok, msg = self.engine.assign_crew_station(engineer.id, "unassigned")
        self.assertTrue(ok)
        self.assertIn("relieved from station duties", msg)
        crew_by_id = {c.id: c for c in self.engine.state.ship.crew}
        self.assertEqual(crew_by_id[engineer.id].station, "")

    def test_station_department_synergy_multipliers(self):
        # Pilot without station
        unassigned_pilot = CrewMember(id="p1", name="Flyer", role="pilot", skill=5, morale=100.0, station="")
        bonuses_unassigned = calculate_crew_bonuses((unassigned_pilot,))

        # Pilot with matching 'helm' station (+40% synergy)
        assigned_pilot = CrewMember(id="p2", name="Flyer", role="pilot", skill=5, morale=100.0, station="helm")
        bonuses_assigned = calculate_crew_bonuses((assigned_pilot,))

        # Evasion bonus should be significantly higher with helm assignment
        self.assertGreater(bonuses_assigned["evasion"], bonuses_unassigned["evasion"])

    def test_distress_beacon_and_precursor_crypt_in_catalog(self):
        anomaly_ids = {a["id"] for a in ANOMALIES_CATALOG}
        self.assertIn("distress_beacon_prospector", anomaly_ids)
        self.assertIn("precursor_crypt_vault", anomaly_ids)

        prospector = next(a for a in ANOMALIES_CATALOG if a["id"] == "distress_beacon_prospector")
        self.assertEqual(len(prospector["choices"]), 3)
        choice_ids = {c["choice_id"] for c in prospector["choices"]}
        self.assertIn("tow_to_orbit", choice_ids)
        self.assertIn("transfer_fuel", choice_ids)

    def test_celestial_and_particle_js_enhancements(self):
        static_dir = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
        celestial_js = (static_dir / "celestial.js").read_text(encoding="utf-8")
        particles_js = (static_dir / "particles.js").read_text(encoding="utf-8")
        index_html = (static_dir / "index.html").read_text(encoding="utf-8")
        app_js = (static_dir / "app.js").read_text(encoding="utf-8")

        self.assertIn("drawSolarProminences", celestial_js)
        self.assertIn("drawBinaryStar", celestial_js)
        self.assertIn("drawNightsideCityLights", celestial_js)
        self.assertIn("drawJumpGateSingularity", celestial_js)

        self.assertIn("shieldRipple", particles_js)
        self.assertIn("hexShieldImpact", particles_js)
        self.assertIn('kind === "hex"', particles_js)

        self.assertIn("btnCombatPdc", index_html)
        self.assertIn("btnCombatPdc", app_js)
        self.assertIn("point_defense", app_js)

    def test_point_defense_cannon_countermeasure(self):
        from voidfarer.models import CombatEncounter

        # Setup an active combat encounter
        combat = CombatEncounter(
            id="combat_pirate_pdc",
            enemy_name="Corsair Frigate",
            enemy_class="Frigate",
            enemy_hull=50,
            enemy_max_hull=50,
            enemy_damage=30,
            bounty_credits=300,
            salvage_commodity="ore",
            enemy_shield=20,
            enemy_max_shield=20,
            enemy_intent="fire",
        )
        self.engine.state = self.engine._clone_state(active_combat=combat)

        # 1. Test PDC execution with normal power allocation
        ok, msg = self.engine.combat_action("point_defense")
        self.assertTrue(ok)
        self.assertIn("Point Defense Cannons engaged", msg)

        # 2. Test PDC heat accumulation (+3.0)
        self.assertGreater(self.engine.state.ship.reactor.heat, 0.0)

        # 3. Test PDC rejection when both Weapons and Engines have < 15% power
        from voidfarer.models import ShipPower
        low_pwr = ShipPower(engines=10, weapons=10, shields=50, sensors=30)
        combat2 = CombatEncounter(
            id="combat_pirate_pdc_low",
            enemy_name="Corsair Scout",
            enemy_class="Scout",
            enemy_hull=30,
            enemy_max_hull=30,
            enemy_damage=10,
            bounty_credits=100,
            salvage_commodity="ore",
            enemy_shield=0,
            enemy_max_shield=0,
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(power=low_pwr),
            active_combat=combat2,
        )
        ok, msg = self.engine.combat_action("point_defense")
        self.assertFalse(ok)
        self.assertIn("at least 15% power", msg)

    def test_combat_reactor_vent_heat(self):
        from dataclasses import replace
        from voidfarer.models import CombatEncounter

        combat = CombatEncounter(
            id="combat_vent_test",
            enemy_name="Corsair Raider",
            enemy_class="Raider",
            enemy_hull=40,
            enemy_max_hull=40,
            enemy_damage=15,
            bounty_credits=150,
            salvage_commodity="ore",
            enemy_shield=10,
            enemy_max_shield=10,
        )
        # Charge heat to 60.0
        hot_reactor = replace(self.engine.state.ship.reactor, heat=60.0, last_vent_tick=-10)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(reactor=hot_reactor),
            active_combat=combat,
        )

        ok, msg = self.engine.combat_action("vent_heat")
        self.assertTrue(ok)
        self.assertIn("Tactical Coolant Vent", msg)
        self.assertLess(self.engine.state.ship.reactor.heat, 60.0)

    def test_cockpit_advanced_telemetry_and_oscilloscope(self):
        static_dir = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
        celestial_js = (static_dir / "celestial.js").read_text(encoding="utf-8")
        particles_js = (static_dir / "particles.js").read_text(encoding="utf-8")
        index_html = (static_dir / "index.html").read_text(encoding="utf-8")
        app_js = (static_dir / "app.js").read_text(encoding="utf-8")
        style_css = (static_dir / "style.css").read_text(encoding="utf-8")

        self.assertIn("drawComet", celestial_js)
        self.assertIn("limbGlow", celestial_js)
        self.assertIn("rcsPuff", particles_js)
        self.assertIn("flakBurst", particles_js)
        self.assertIn("ionArc", particles_js)
        self.assertIn("quantumFlash", particles_js)
        self.assertIn("cadetStepPips", index_html)
        self.assertIn("cadetStepPips", app_js)
        self.assertIn("commsOscilloscope", index_html)
        self.assertIn("drawCommsOscilloscope", app_js)
        self.assertIn("dustFilament", app_js)
        self.assertIn("compassR", app_js)
        self.assertIn("marketCategoryFilters", index_html)
        self.assertIn("syncMarketCategoryFilters", app_js)
        self.assertIn(".log-line .log-tag.tag-combat", style_css)
        self.assertIn(".log-line .log-tag.tag-transit", style_css)
        self.assertIn("RANGE SCALE", app_js)
        self.assertIn("panVx", app_js)
        self.assertIn("targetPanX", app_js)
        self.assertIn("bgParallax", app_js)
        self.assertIn("handleCanvasDblClick", app_js)
        self.assertIn("playDock()", app_js)
        self.assertIn("playWarp()", app_js)
        self.assertIn("playFlak()", app_js)
        self.assertIn(".character-abilities .ability-row", style_css)
        self.assertIn(".character-abilities .ability-row.ready", style_css)
        self.assertIn("solar array", celestial_js)


if __name__ == "__main__":
    unittest.main()

