"""Regression tests for message trees, crew, portraits, weapons, quantum tech, and megastructures."""

import contextlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer.cli import main
from voidfarer.crew import CREW_ROLES, calculate_crew_bonuses, recruit_crew_member
from voidfarer.engine import SimulationEngine
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.messaging import TREE_MAP, tree_root_message
from voidfarer.models import CombatEncounter, CrewMember, FleetShip, MessageChoice, QuantumMessage
from voidfarer.research import RESEARCH_MAP
from voidfarer.weapons import WEAPON_CATALOG, get_weapon


class MessageTreeTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_tree_root_is_seeded_and_has_branches(self):
        roots = [m for m in self.engine.state.messages if m.tree_id == "precursor_signal"]
        self.assertTrue(roots)
        root = roots[0]
        self.assertGreaterEqual(len(root.choices), 2)
        self.assertIsNone(root.resolved_choice)

    def test_decode_branch_grants_research_and_follow_up(self):
        root = next(m for m in self.engine.state.messages if m.tree_id == "precursor_signal")
        research_before = self.engine.state.research.points
        ok, msg = self.engine.resolve_message_choice(root.id, "decode")
        self.assertTrue(ok, msg)
        self.assertGreaterEqual(self.engine.state.research.points, research_before + 60)
        resolved = next(m for m in self.engine.state.messages if m.id == root.id)
        self.assertEqual(resolved.resolved_choice, "decode")
        self.assertTrue(any(m.node_id == "decoded" for m in self.engine.state.messages))

    def test_sell_branch_grants_credits(self):
        root = next(m for m in self.engine.state.messages if m.tree_id == "precursor_signal")
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.resolve_message_choice(root.id, "sell")
        self.assertTrue(ok, msg)
        self.assertGreater(self.engine.state.ship.credits, credits_before)

    def test_choice_cannot_be_replayed(self):
        root = next(m for m in self.engine.state.messages if m.tree_id == "precursor_signal")
        self.engine.resolve_message_choice(root.id, "decode")
        ok, msg = self.engine.resolve_message_choice(root.id, "decode")
        self.assertFalse(ok)
        self.assertIn("already", msg)

    def test_message_model_round_trip_with_choices(self):
        message = QuantumMessage(
            id="m1", sender="A", recipient="B", subject="S", body="Body",
            tree_id="precursor_signal", node_id="root",
            choices=(MessageChoice(id="c1", label="Choice", outcome={"credits": 10}),),
        )
        restored = QuantumMessage.from_dict(message.to_dict())
        self.assertEqual(restored.choices[0].id, "c1")
        self.assertEqual(restored.choices[0].outcome["credits"], 10)

    def test_tree_catalog_has_multiple_trees(self):
        self.assertIn("precursor_signal", TREE_MAP)
        self.assertIn("quantum_offer", TREE_MAP)
        self.assertIn("refugee_fleet", TREE_MAP)


class CrewWeaponTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(self.station.id)

    def test_starting_crew_and_bonuses(self):
        self.assertGreaterEqual(len(self.engine.state.ship.crew), 2)
        bonuses = calculate_crew_bonuses(self.engine.state.ship.crew)
        self.assertGreater(bonuses["reactor_cooling"], 0)
        self.assertGreater(bonuses["fuel_efficiency"], 0)

    def test_recruit_and_dismiss_crew(self):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=5000))
        before = len(self.engine.state.ship.crew)
        ok, msg = self.engine.recruit_crew("scientist")
        self.assertTrue(ok, msg)
        self.assertEqual(len(self.engine.state.ship.crew), before + 1)
        recruited = self.engine.state.ship.crew[-1]
        self.assertEqual(recruited.role, "scientist")
        self.assertTrue(recruited.portrait.startswith("crew_"))
        ok, _ = self.engine.dismiss_crew(recruited.id)
        self.assertTrue(ok)
        self.assertEqual(len(self.engine.state.ship.crew), before)

    def test_crew_round_trip_and_catalog(self):
        member = CrewMember(id="c1", name="Test", role="medic", skill=4, morale=88.0, wage=30, portrait="crew_03")
        self.assertEqual(CrewMember.from_dict(member.to_dict()), member)
        roles = {r.id for r in CREW_ROLES}
        self.assertIn("pilot", roles)
        self.assertIn("marine", roles)
        self.assertEqual(recruit_crew_member("pilot", 42, 0).role, "pilot")

    def test_weapon_variety_and_install(self):
        weapon_types = {w.weapon_type for w in WEAPON_CATALOG}
        self.assertTrue({"laser", "kinetic", "missile", "plasma", "ion", "quantum"}.issubset(weapon_types))
        self.assertIsNotNone(get_weapon("quantum_lance"))
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=10000))
        ok, msg = self.engine.install_weapon("railgun")
        self.assertTrue(ok, msg)
        self.assertEqual(self.engine.state.ship.primary_weapon, "railgun")
        self.assertIn("railgun", self.engine.state.ship.weapons)

    def test_weapon_requires_credits(self):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=10))
        ok, msg = self.engine.install_weapon("quantum_lance")
        self.assertFalse(ok)
        self.assertIn("Insufficient", msg)

    def test_combat_misfire_telemetry_preserves_weapon_misfire_description(self):
        combat = CombatEncounter(
            id="combat_telemetry",
            enemy_name="Rogue Pirate",
            enemy_class="Raider",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=5,
            bounty_credits=100,
            enemy_shield=50,
            enemy_max_shield=50,
        )
        self.engine.state = self.engine._clone_state(
            active_combat=combat,
            ship=self.engine._clone_ship(
                primary_weapon="pulse_laser",
                fleet_ships=(FleetShip(id="fs_1", name="Wingmate 1", ship_class="Interceptor", role="escort", hull=100, max_hull=100, shield=50, max_shield=50, damage=20),),
                battle_stance="aggressive",
            ),
        )
        self.engine.rng.random = lambda: 0.99
        ok, msg = self.engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertIn("firing solution failed", msg)
        self.assertNotIn("Enemy AI jinked", msg)

        self.engine.rng.random = lambda: 0.10
        ok2, msg2 = self.engine.combat_action("fire_lasers")
        self.assertTrue(ok2)
        self.assertIn("aggressive stance", msg2)

    def test_non_weapon_strike_reports_enemy_evasion(self):
        combat = CombatEncounter(
            id="combat_evade",
            enemy_name="Rogue Pirate",
            enemy_class="Raider",
            enemy_hull=200,
            enemy_max_hull=200,
            enemy_damage=5,
            bounty_credits=100,
            enemy_shield=50,
            enemy_max_shield=50,
            enemy_intent="evade",
        )
        self.engine.state = self.engine._clone_state(active_combat=combat)
        self.engine.rng.random = lambda: 0.0
        ok, msg = self.engine.combat_action("target_subsystem")
        self.assertTrue(ok)
        self.assertIn("Enemy AI jinked", msg)


class QuantumAndObjectsTest(unittest.TestCase):
    def test_quantum_research_projects_exist(self):
        for project_id in ("quantum_entanglement", "quantum_drive", "quantum_shielding", "quantum_weapons"):
            self.assertIn(project_id, RESEARCH_MAP)
            self.assertEqual(RESEARCH_MAP[project_id].category, "quantum")

    def test_dyson_sphere_relay_wormhole_and_collector_exist(self):
        galaxy = GalaxyGenerator(seed=42).generate_galaxy()
        body_types = {b.body_type for s in galaxy.values() for b in s.bodies}
        self.assertIn("dyson_sphere", body_types)
        self.assertIn("quantum_relay", body_types)
        self.assertIn("wormhole", body_types)
        self.assertIn("solar_collector", body_types)

    def test_character_portrait_and_era(self):
        engine = SimulationEngine(seed=42)
        self.assertTrue(engine.state.character.portrait.startswith("commander_"))
        self.assertEqual(engine.state.time.current_date, "01.01.3042")
        self.assertIn("Quantum Age", engine.state.time.era)

    def test_cli_new_systems_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = str(Path(temp_dir) / "save.json")
            for argv in (
                ["--save-path", save_path, "crew"],
                ["--save-path", save_path, "weapons"],
                ["--save-path", save_path, "messages", "tree"],
            ):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(argv)
                self.assertEqual(code, 0, buffer.getvalue())

    def test_cockpit_message_choices_crew_portrait_wiring(self):
        static = Path(__file__).parent.parent / "voidfarer" / "static"
        html = (static / "index.html").read_text(encoding="utf-8")
        script = (static / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="crewRoster"', html)
        for symbol in ("portraitAvatar", "message-choice-btn", "data-msg-choice", "crew-row"):
            self.assertIn(symbol, script + html)
        self.assertIn("/api/messages/choose", script)


if __name__ == "__main__":
    unittest.main()
