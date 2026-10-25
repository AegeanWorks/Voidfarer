"""Regression tests for character, research, outposts, factions, fleet, and travel additions."""

import contextlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer.character import advance_age, train_skill
from voidfarer.cli import main
from voidfarer.engine import SimulationEngine
from voidfarer.faction_state import generate_faction_leaders, resolve_wars
from voidfarer.fleet import apply_fleet_casualties, build_fleet_ship, fleet_damage
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import FleetShip, GameState, Outpost, PlayerCharacter, ResearchState, WarState
from voidfarer.navigation import route_plan, shortest_route
from voidfarer.outposts import OUTPOST_TYPES, can_build_on


class CharacterResearchOutpostTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_character_state_round_trip_and_age(self):
        character = PlayerCharacter(name="Test", age=30, skills={"piloting": 3})
        restored = PlayerCharacter.from_dict(character.to_dict())
        self.assertEqual(restored.name, "Test")
        self.assertEqual(restored.age, 30)
        self.assertEqual(restored.skills["piloting"], 3)
        aged = advance_age(restored, 0.0, 366.0)
        self.assertEqual(aged.age, 31)

    def test_train_skill_requires_points_and_valid_skill(self):
        character = replace(self.engine.state.character, skill_points=1)
        ok, updated, _ = train_skill(character, "science")
        self.assertTrue(ok)
        self.assertEqual(updated.skills["science"], 2)
        self.assertEqual(updated.skill_points, 0)
        ok, _, msg = train_skill(updated, "science")
        self.assertFalse(ok)
        self.assertIn("No skill points", msg)

    def test_emergency_repair_ability_heals_and_sets_cooldown(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(hull=40)
        )
        ok, msg = self.engine.use_character_ability("emergency_repair")
        self.assertTrue(ok)
        self.assertGreater(self.engine.state.ship.hull, 40)
        self.assertGreater(self.engine.state.character.ability_cooldowns["emergency_repair"], 0)

    def test_research_project_completes_on_tick(self):
        research = ResearchState(points=50, progress=119, active_project_id="advanced_cooling")
        self.engine.state = self.engine._clone_state(research=research)
        self.engine.tick(1)
        self.assertIn("advanced_cooling", self.engine.state.research.completed)
        self.assertIsNone(self.engine.state.research.active_project_id)

    def test_unknown_research_project_rejected(self):
        ok, msg = self.engine.choose_research("not_a_project")
        self.assertFalse(ok)
        self.assertIn("Unknown", msg)

    def test_outpost_builds_and_produces_on_tick(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=5000)
        )
        ok, msg = self.engine.orbit("sol_ring_world")
        self.assertTrue(ok, msg)
        ok, msg = self.engine.build_outpost("sol_ring_world", "solar")
        self.assertTrue(ok, msg)
        self.assertEqual(len(self.engine.state.outposts), 1)
        credits_before = self.engine.state.ship.credits
        self.engine.tick(1)
        self.assertGreaterEqual(self.engine.state.ship.credits, credits_before - 100)
        self.assertGreater(self.engine.state.research.points, 0)
        self.assertEqual(len(self.engine.state.outposts), 1)

    def test_outpost_requires_orbit(self):
        ok, msg = self.engine.build_outpost("sol_ring_world", "solar")
        self.assertFalse(ok)
        self.assertIn("orbit", msg.lower())


class FactionDiplomacyWarTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_leaders_generated_deterministically(self):
        first = generate_faction_leaders(42)
        second = generate_faction_leaders(42)
        self.assertEqual([l.to_dict() for l in first], [l.to_dict() for l in second])
        self.assertEqual(len(first), 5)
        self.assertTrue(all(l.behavior for l in first))

    def test_diplomacy_improve_and_declare_war(self):
        before = self.engine.state.ship.faction_standings.get("vanguard_syndicate", 0)
        ok, _ = self.engine.faction_diplomacy("vanguard_syndicate", "improve")
        self.assertTrue(ok)
        self.assertGreater(self.engine.state.ship.faction_standings["vanguard_syndicate"], before)

        ok, _ = self.engine.faction_diplomacy("vanguard_syndicate", "declare_war")
        self.assertTrue(ok)
        self.assertTrue(any(
            w.active and "vanguard_syndicate" in (w.attacker_id, w.defender_id)
            for w in self.engine.state.wars
        ))

    def test_resolve_wars_captures_and_eliminates_faction(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        nebula_ids = [sid for sid, system in systems.items() if system.faction == "Nebula Collective"]
        target_id = nebula_ids[0]
        for sid in nebula_ids[1:]:
            systems[sid] = replace(systems[sid], faction="Sol Coalition")
        wars = (WarState(id="w1", attacker_id="sol_coalition", defender_id="nebula_collective", started_tick=0),)

        class DeterministicRng:
            def uniform(self, low, high):
                return 20.0

            def choice(self, seq):
                return seq[0]

        resolved, updated_systems, eliminated, logs = resolve_wars(
            wars, systems, DeterministicRng(), 5, ()
        )
        self.assertTrue(resolved[0].active is False)
        self.assertTrue(any("captured" in line for line in logs))
        self.assertIn("nebula_collective", eliminated)


class FleetAndNavigationTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.station = next(b for b in self.engine.current_system.bodies if b.station_dockable)

    def test_escort_purchase_requires_credits_and_dock(self):
        self.engine.orbit(self.station.id)
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=5000))
        ok, msg = self.engine.buy_escort("corvette")
        self.assertTrue(ok, msg)
        self.assertEqual(len(self.engine.state.ship.fleet_ships), 1)
        ok, msg = self.engine.dismiss_escort(self.engine.state.ship.fleet_ships[0].id)
        self.assertTrue(ok)
        self.assertFalse(self.engine.state.ship.fleet_ships)

    def test_fleet_damage_and_casualties(self):
        ships = (build_fleet_ship("frigate", "sol", 1), build_fleet_ship("corvette", "sol", 2))
        self.assertGreater(fleet_damage(ships), 0)
        survivors, absorbed = apply_fleet_casualties(ships, 50)
        self.assertEqual(absorbed, 50)
        self.assertTrue(any(s.shield < s.max_shield or s.hull < s.max_hull for s in survivors))

    def test_battle_stance_and_solar_panel_upgrade(self):
        ok, msg = self.engine.set_battle_stance("aggressive")
        self.assertTrue(ok, msg)
        self.assertEqual(self.engine.state.ship.battle_stance, "aggressive")
        self.assertFalse(self.engine.set_battle_stance("nonsense")[0])
        from voidfarer.upgrades import get_upgrade
        solar = get_upgrade("solar_panel_array")
        self.assertIsNotNone(solar)
        self.assertIn("reactor_output", solar.stat_bonus)

    def test_route_planning(self):
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        path = shortest_route(systems, "sol", "alpha_centauri")
        self.assertEqual(path[0], "sol")
        self.assertEqual(path[-1], "alpha_centauri")
        plan = route_plan(systems, "sol", "alpha_centauri")
        self.assertTrue(plan["reachable"])
        self.assertGreater(plan["jumps"], 0)

    def test_black_holes_and_ring_worlds_exist(self):
        galaxy = GalaxyGenerator(seed=42).generate_galaxy()
        body_types = {b.body_type for s in galaxy.values() for b in s.bodies}
        self.assertIn("black_hole", body_types)
        self.assertIn("ring_world", body_types)


class NewSystemsSerializationAndCLITest(unittest.TestCase):
    def test_snapshot_outpost_options_match_what_the_server_accepts(self):
        galaxy = GalaxyGenerator(seed=42).generate_galaxy()
        system_id, world = next(
            (sid, body)
            for sid, system in galaxy.items()
            for body in system.bodies
            if body.body_type == "terrestrial" and body.station_dockable
        )
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            systems=galaxy,
            ship=engine._clone_ship(
                current_system_id=system_id,
                orbiting_body_id=world.id,
                credits=9000,
                cargo={},
                cargo_cost={},
            ),
        )
        snapshot = engine.get_status_snapshot()
        self.assertEqual(
            snapshot["outpost_options"], [t.id for t in OUTPOST_TYPES if can_build_on(world, t)]
        )
        self.assertNotIn("solar", snapshot["outpost_options"])
        self.assertFalse(snapshot["outpost_body_occupied"])
        ok, message = engine.build_outpost(world.id, "shipyard")
        self.assertTrue(ok, message)
        self.assertTrue(engine.get_status_snapshot()["outpost_body_occupied"])

    def test_game_state_round_trip_preserves_new_fields(self):
        engine = SimulationEngine(seed=42)
        restored = GameState.from_dict(engine.state.to_dict())
        self.assertEqual(restored.character.name, engine.state.character.name)
        self.assertEqual(len(restored.faction_leaders), len(engine.state.faction_leaders))
        self.assertEqual(restored.research.completed, engine.state.research.completed)
        self.assertEqual(restored.outposts, engine.state.outposts)

    def test_new_cli_commands_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = str(Path(temp_dir) / "save.json")
            for argv in (
                ["--save-path", save_path, "character"],
                ["--save-path", save_path, "research"],
                ["--save-path", save_path, "outpost"],
                ["--save-path", save_path, "diplomacy"],
                ["--save-path", save_path, "route", "alpha_centauri"],
                ["--save-path", save_path, "fleet", "ships"],
            ):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(argv)
                self.assertEqual(code, 0, buffer.getvalue())

    def test_cockpit_fleet_character_empire_and_void_fade_wiring(self):
        static = Path(__file__).parent.parent / "voidfarer" / "static"
        html = (static / "index.html").read_text(encoding="utf-8")
        script = (static / "app.js").read_text(encoding="utf-8")
        style = (static / "style.css").read_text(encoding="utf-8")
        for element_id in (
            "fleetShipRoster", "escortShopGrid", "tabContentPlayer", "tabContentCrew",
            "tabContentEmpire", "hudSkillsGrid", "researchProjects", "outpostList", "diplomacyList",
        ):
            self.assertIn(f'id="{element_id}"', html)
        for symbol in ("renderPlayer", "renderCrew", "renderEmpire", "renderFleetManager", "renderSkillsQuickPanel", "orbitFade", "fadeOuter"):
            self.assertIn(symbol, script)
        self.assertIn("height: 44px", style)


if __name__ == "__main__":
    unittest.main()
