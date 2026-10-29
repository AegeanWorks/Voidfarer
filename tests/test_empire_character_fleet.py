"""Regression tests for character, research, outposts, factions, fleet, and travel additions."""

import contextlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer.character import advance_age, train_skill
from voidfarer.cli import main
from voidfarer.crew import DAYS_PER_MONTH
from voidfarer.engine import SimulationEngine
from voidfarer.factions import CANONICAL_FACTIONS
from voidfarer.faction_state import generate_faction_leaders, resolve_wars
from voidfarer.fleet import apply_fleet_casualties, build_fleet_ship, fleet_damage
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import CombatEncounter, FleetShip, GameState, Outpost, PlayerCharacter, ReactorState, ResearchState, WarState
from voidfarer.navigation import route_plan, shortest_route
from voidfarer.outposts import OUTPOST_TYPES, can_build_on, outpost_tick_production
from voidfarer.reactor import reactor_output_efficiency


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

    def test_high_skill_unlocks_the_late_abilities(self):
        character = self.engine.state.character
        character = replace(
            character,
            skills={**character.skills, "diplomacy": 6, "trade": 6},
            skill_points=4,
        )
        self.engine.state = self.engine._clone_state(character=character)
        self.assertNotIn("charm_offensive", self.engine.state.character.abilities)
        ok, msg = self.engine.train_character_skill("diplomacy")
        self.assertTrue(ok)
        self.assertIn("charm_offensive", self.engine.state.character.abilities)
        self.assertIn("Unlocked", msg)
        ok, _ = self.engine.train_character_skill("trade")
        self.assertTrue(ok)
        self.assertIn("trade_instinct", self.engine.state.character.abilities)

    def test_overclock_is_a_timed_reactor_surge(self):
        base = reactor_output_efficiency(self.engine.state.ship.reactor)
        ok, _ = self.engine.use_character_ability("overclock")
        self.assertTrue(ok)
        reactor = self.engine.state.ship.reactor
        self.assertEqual(reactor.surge_ticks, 8)
        self.assertGreater(reactor_output_efficiency(reactor), base)
        self.engine.tick(8)
        self.assertEqual(self.engine.state.ship.reactor.surge_ticks, 0)
        self.assertEqual(self.engine.state.ship.reactor.surge_bonus, 0.0)

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

    def test_outposts_pay_back_over_multiple_months(self):
        ticks_per_month = int(DAYS_PER_MONTH / 0.25)
        for outpost in OUTPOST_TYPES:
            for value in outpost.production.values():
                self.assertEqual(value, int(value), f"{outpost.id} yields must not truncate per tick")
            monthly = outpost.production.get("credits", 0.0) * ticks_per_month
            self.assertLess(monthly, outpost.cost, f"{outpost.id} must not repay its cost in a month")
        mining = next(outpost for outpost in OUTPOST_TYPES if outpost.id == "mining")
        monthly = mining.production["credits"] * ticks_per_month
        self.assertGreaterEqual(monthly, 300)
        self.assertLessEqual(monthly, 400)

    def test_outpost_upgrade_costs_less_than_building_and_adds_quarter_output(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=5000)
        )
        self.engine.orbit("sol_body_2")
        ok, _ = self.engine.build_outpost("sol_body_2", "mining")
        self.assertTrue(ok)
        outpost = self.engine.state.outposts[0]
        before = outpost_tick_production(outpost)["credits"]
        ok, _ = self.engine.upgrade_outpost(outpost.id)
        self.assertTrue(ok)
        upgraded = self.engine.state.outposts[0]
        self.assertEqual(upgraded.level, 2)
        self.assertEqual(outpost_tick_production(upgraded)["credits"], round(before * 1.25, 2))

    def test_old_outposts_use_the_current_catalog_yields(self):
        legacy = Outpost(
            id="legacy", name="Legacy Mine", system_id="sol", body_id="sol_body_2",
            outpost_type="mining", level=1, production={"credits": 10.0, "titanium": 2.0},
        )
        self.assertEqual(outpost_tick_production(legacy)["credits"], 3.0)

    def test_commander_creation_reconciles_rank_seven_unlocks(self):
        ok, msg = self.engine.reset(seed=42, profile={
            "name": "Ace", "age": 30, "background": "Navigator",
            "skills": {"diplomacy": 7, "trade": 7},
        })
        self.assertTrue(ok, msg)
        self.assertIn("charm_offensive", self.engine.state.character.abilities)
        self.assertIn("trade_instinct", self.engine.state.character.abilities)

    def test_constructor_reconciles_rank_seven_unlocks(self):
        engine = SimulationEngine(seed=42)
        character = replace(
            engine.state.character,
            skills={**engine.state.character.skills, "trade": 7},
            abilities=(),
        )
        restored = SimulationEngine(seed=42, state=replace(engine.state, character=character))
        self.assertIn("trade_instinct", restored.state.character.abilities)

    def test_overclock_surge_decays_once_per_combat_turn(self):
        combat = CombatEncounter(
            id="surge_drill", enemy_name="Drill Frame", enemy_class="Corvette",
            enemy_hull=999, enemy_max_hull=999, enemy_damage=1, bounty_credits=0,
            salvage_commodity="titanium", enemy_shield=0, enemy_max_shield=0,
            faction_id="void_corsairs", special_ability="none",
        )
        self.engine.state = self.engine._clone_state(active_combat=combat)
        ok, _ = self.engine.use_character_ability("overclock")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.reactor.surge_ticks, 8)
        self.engine.combat_action("scan")
        self.assertEqual(self.engine.state.ship.reactor.surge_ticks, 7)

    def test_loading_an_old_save_reconciles_rank_seven_unlocks(self):
        engine = SimulationEngine(seed=42)
        character = replace(
            engine.state.character,
            skills={**engine.state.character.skills, "diplomacy": 7},
            abilities=(),
            skill_points=0,
        )
        state = replace(engine.state, character=character)
        ok, msg = engine.load_state(state)
        self.assertTrue(ok, msg)
        self.assertIn("charm_offensive", engine.state.character.abilities)

    def test_failed_ability_checks_do_not_burn_the_cooldown(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(hull=self.engine.state.ship.max_hull)
        )
        ok, _ = self.engine.use_character_ability("emergency_repair")
        self.assertFalse(ok)
        self.assertEqual(self.engine.state.character.ability_cooldowns.get("emergency_repair", 0), 0)
        character = replace(
            self.engine.state.character,
            abilities=tuple(self.engine.state.character.abilities) + ("charm_offensive",),
        )
        self.engine.state = self.engine._clone_state(character=character)
        ok, _ = self.engine.use_character_ability("charm_offensive", "no_such_faction")
        self.assertFalse(ok)
        self.assertEqual(self.engine.state.character.ability_cooldowns.get("charm_offensive", 0), 0)

    def test_snapshot_exposes_ability_cooldown_totals(self):
        snapshot = self.engine.get_status_snapshot()
        self.assertEqual(snapshot["character_abilities"]["overclock"]["cooldown_total"], 20)

    def test_old_reactor_saves_default_the_surge_fields(self):
        data = SimulationEngine(seed=42).state.ship.reactor.to_dict()
        data.pop("surge_ticks")
        data.pop("surge_bonus")
        restored = ReactorState.from_dict(data)
        self.assertEqual(restored.surge_ticks, 0)
        self.assertEqual(restored.surge_bonus, 0.0)


class FactionDiplomacyWarTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_leaders_generated_deterministically(self):
        first = generate_faction_leaders(42)
        second = generate_faction_leaders(42)
        self.assertEqual([l.to_dict() for l in first], [l.to_dict() for l in second])
        self.assertEqual(len(first), len(CANONICAL_FACTIONS))
        self.assertTrue(all(l.behavior for l in first))

    def test_diplomacy_improve_and_no_captain_declared_war(self):
        before = self.engine.state.ship.faction_standings.get("vanguard_syndicate", 0)
        ok, _ = self.engine.faction_diplomacy("vanguard_syndicate", "improve")
        self.assertTrue(ok)
        self.assertGreater(self.engine.state.ship.faction_standings["vanguard_syndicate"], before)

        ok, msg = self.engine.faction_diplomacy("vanguard_syndicate", "declare_war")
        self.assertFalse(ok, "a captain has no authority to declare war")
        self.assertIn("captain", msg)
        self.assertFalse(any(
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
