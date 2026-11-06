"""Unit tests for command-line arguments and subcommands."""

import io
import os
import runpy
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from voidfarer.cli import cmd_inventory, cmd_repl, cmd_status, main
from voidfarer.engine import SimulationEngine
from voidfarer.models import CombatEncounter, CustomsEncounter, PrecursorRelic
from voidfarer.storage import StorageManager
from voidfarer.story import STORY_RELICS


class _IsolatedCliTestCase(unittest.TestCase):
    """Base for CLI tests: redirect default storage away from the player's live save."""

    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        env_patcher = patch.dict(
            os.environ,
            {"LOCALAPPDATA": self._tmp.name, "HOME": self._tmp.name, "USERPROFILE": self._tmp.name},
        )
        env_patcher.start()
        self.addCleanup(env_patcher.stop)


class TestCLI(_IsolatedCliTestCase):
    def test_cli_help(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main([])
            self.assertEqual(code, 0)
            self.assertIn("voidfarer", mock_out.getvalue().lower())

    def test_cli_status(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["status"])
            self.assertEqual(code, 0)
            output = mock_out.getvalue()
            self.assertIn("Astraea", output)
            self.assertIn("VF-Vanguard", output)

    def test_cli_status_shows_cargo_volume_not_units(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(cargo={"titanium": 20})
        )
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = cmd_status(engine)
            self.assertEqual(code, 0)
            output = mock_out.getvalue()
            self.assertIn("40/40", output)
            self.assertIn("volume", output)

    def test_cli_chart(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["chart"])
            self.assertEqual(code, 0)
            output = mock_out.getvalue()
            self.assertIn("GALAXY SECTOR", output)
            self.assertIn("Sol System", output)

    def test_cli_power(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["power", "25", "25", "25", "25"])
            self.assertEqual(code, 0)

    def test_cli_quantum_autotrade_status_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["autotrade", "quantum", "status"])
            self.assertEqual(code, 0)
            self.assertIn("quantum auto-freight", mock_out.getvalue().lower())

    def test_cli_autotrade_status_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["autotrade", "status"])
            self.assertEqual(code, 0)
            self.assertIn("auto-trade broker", mock_out.getvalue().lower())

    def test_cli_research_queue_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["research", "queue", "missing_project"])
            self.assertEqual(code, 1)
            self.assertIn("unknown research project", mock_out.getvalue().lower())

    def test_cli_outpost_repair_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["outpost", "repair", "missing_outpost"])
            self.assertEqual(code, 1)
            self.assertIn("unknown outpost", mock_out.getvalue().lower())

    def test_cli_outpost_specialize_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["outpost", "specialize", "missing_outpost", "industry"])
            self.assertEqual(code, 1)
            self.assertIn("unknown outpost", mock_out.getvalue().lower())

    def test_cli_outpost_crew_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["outpost", "crew", "missing_outpost", "missing_crew"])
            self.assertEqual(code, 1)
            self.assertIn("unknown outpost", mock_out.getvalue().lower())

    def test_cli_outpost_module_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["outpost", "module", "missing_outpost", "laboratory"])
            self.assertEqual(code, 1)
            self.assertIn("unknown outpost", mock_out.getvalue().lower())

    def test_cli_outpost_link_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["outpost", "link", "missing_source", "missing_hub"])
            self.assertEqual(code, 1)
            self.assertIn("unknown outpost", mock_out.getvalue().lower())

    def test_cli_megastructure_status_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["megastructure", "status"])
            self.assertEqual(code, 0)
            self.assertTrue(mock_out.getvalue())

    def test_cli_megastructure_restore_reports_unknown_body(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["megastructure", "restore", "missing_body"])
            self.assertEqual(code, 1)
            self.assertIn("unknown body", mock_out.getvalue().lower())

    def test_cli_fleet_sell_escort_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["fleet", "sell_escort", "missing_prize"])
            self.assertEqual(code, 1)
            self.assertIn("unknown escort", mock_out.getvalue().lower())

    def test_cli_non_aggression_pact_reports_the_standing_gate(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["diplomacy", "non_aggression", "nebula_collective"])
            self.assertEqual(code, 1)
            self.assertIn("standing", mock_out.getvalue().lower())

    def test_cli_research_pact_parses_and_reports_the_standing_gate(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["diplomacy", "research_pact", "sol_coalition"])
            self.assertEqual(code, 1)
            self.assertIn("standing", mock_out.getvalue().lower())

    def test_cli_trade_pact_parses_and_reports_the_standing_gate(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["diplomacy", "trade_pact", "sol_coalition"])
            self.assertEqual(code, 1)
            self.assertIn("standing", mock_out.getvalue().lower())

    def test_cli_fleet_captain_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["fleet", "captain", "missing_escort", "missing_crew"])
            self.assertEqual(code, 1)
            self.assertIn("unknown escort", mock_out.getvalue().lower())

    def test_cli_fleet_role_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["fleet", "role", "missing_escort", "support"])
            self.assertEqual(code, 1)
            self.assertIn("unknown escort", mock_out.getvalue().lower())

    def test_cli_fleet_train_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["fleet", "train", "missing_escort"])
            self.assertEqual(code, 1)
            self.assertIn("unknown escort", mock_out.getvalue().lower())

    def test_cli_reconstruct_parses_and_refuses_an_intact_world(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["reconstruct", "sol_body_1"])
            self.assertEqual(code, 1)
            self.assertIn("not devastated", mock_out.getvalue().lower())

    def test_cli_combat_accepts_documented_actions(self):
        for argv in (
            ["combat", "drone"],
            ["combat", "board"],
            ["combat", "target", "weapons"],
            ["combat", "target", "shields"],
        ):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = main(argv)
                self.assertEqual(code, 0)
                self.assertIn("No active combat", mock_out.getvalue())

    def test_cli_combat_gambit_reports_outside_combat(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["combat", "gambit"])
            self.assertEqual(code, 1)
            self.assertIn("No active combat", mock_out.getvalue())

    def test_cli_combat_stance_is_reachable(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["combat", "stance", "aggressive"])
            self.assertEqual(code, 0)
            self.assertIn("AGGRESSIVE", mock_out.getvalue())

    def test_cli_shipyard_subcommands_parse(self):
        for argv in (["shipyard", "chassis", "orion_hauler"], ["shipyard", "sell", "shields"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = main(argv)
                self.assertNotEqual(code, 2, argv)
                self.assertNotIn("invalid choice", mock_out.getvalue().lower())

    def test_cli_corporations_alias(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["corporations"])
            self.assertEqual(code, 0)
            self.assertIn("MEGACORPORATIONS", mock_out.getvalue())

    def test_cli_repair_and_refuel_accept_positional_amounts(self):
        for argv in (["repair", "10"], ["refuel", "10"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = main(argv)
                self.assertNotEqual(code, 2, argv)
                self.assertNotIn("unrecognized arguments", mock_out.getvalue().lower())

    def test_cli_fleet_list(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["fleet", "list"])
            self.assertEqual(code, 0)
            self.assertIn("FLEET COMMAND", mock_out.getvalue())

    def test_cli_fleet_ships_shows_upkeep(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["fleet", "ships"])
            self.assertEqual(code, 0)
            self.assertIn("upkeep", mock_out.getvalue().lower())

    def test_cli_upgrades_list(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["upgrades", "list"])
            self.assertEqual(code, 0)
            self.assertIn("STATION ARSENAL", mock_out.getvalue())

    def test_cli_contracts_list(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["contracts", "list"])
            self.assertEqual(code, 0)
            self.assertIn("ACTIVE SECTOR BOUNTIES", mock_out.getvalue())

    def test_cli_mastery_status(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["mastery", "status"])
            self.assertEqual(code, 0)
            self.assertIn("PILOT MASTERY", mock_out.getvalue())
            self.assertIn("Void Cartographer", mock_out.getvalue())

    def test_cli_relics(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["relics"])
            self.assertEqual(code, 0)
            self.assertIn("PRECURSOR RELICS VAULT", mock_out.getvalue())

    def test_cli_streak(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["streak"])
            self.assertEqual(code, 0)
            self.assertIn("EXPEDITION JUMP STREAK", mock_out.getvalue())


class TestCLIStabilization(_IsolatedCliTestCase):
    """Regression tests for numeric guards and the station consumable terminal."""

    def setUp(self):
        super().setUp()
        self.storage = StorageManager(self._tmp.name)

    def test_inventory_jettison_non_numeric_quantity_is_handled(self):
        engine = SimulationEngine(seed=42)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = cmd_inventory(engine, self.storage, ["inventory", "jettison", "titanium", "abc"])
        self.assertEqual(code, 1)
        self.assertIn("integer", mock_out.getvalue().lower())

    def test_inventory_buy_usage_without_item_id(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["inventory", "buy"])
        self.assertEqual(code, 1)
        self.assertIn("usage", mock_out.getvalue().lower())

    def test_inventory_buy_consumable_at_station(self):
        engine = SimulationEngine(seed=42)
        engine.orbit("sol_body_1")
        engine.state = engine._clone_state(ship=engine._clone_ship(credits=5000))
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = cmd_inventory(engine, self.storage, ["inventory", "buy", "nanite_repair_paste"])
        self.assertEqual(code, 0)
        self.assertIn("Purchased", mock_out.getvalue())
        self.assertEqual(engine.state.ship.cargo.get("nanite_repair_paste"), 1)

    def test_repl_repair_and_refuel_reject_non_numeric_amounts(self):
        engine = SimulationEngine(seed=42)
        with patch("builtins.input", side_effect=["repair abc", "refuel xyz", "exit"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = cmd_repl(engine, self.storage)
        self.assertEqual(code, 0)
        output = mock_out.getvalue().lower()
        self.assertEqual(output.count("must be an integer"), 2)
        self.assertNotIn("traceback", output)


class TestCLIRelicsWithRecoveredRelics(_IsolatedCliTestCase):
    """A save that already has relics must render the vault and modifiers (regression)."""

    def test_relics_command_with_recovered_relics(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(relics=tuple(STORY_RELICS.values())))
        StorageManager(Path(self._tmp.name) / ".voidfarer").save(engine.state)

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["relics"])

        output = mock_out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("PRECURSOR RELICS VAULT", output)
        self.assertIn("Active Passive Fleet Modifiers", output)
        self.assertIn("Scan Bounty Boost", output)
        self.assertIn("Hull Reinforcement", output)

    def test_relics_fuse_persists_the_fused_relic(self):
        common = tuple(
            PrecursorRelic(
                id=f"fuse_test_{index}",
                name=f"Fuse Test {index}",
                rarity="common",
                description="test relic",
                passive_stat="scan_bounty",
                stat_multiplier=0.01,
            )
            for index in range(3)
        )
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(relics=common))
        save_dir = Path(self._tmp.name) / ".voidfarer"
        StorageManager(save_dir).save(engine.state)

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["relics", "fuse", "common"])

        self.assertEqual(code, 0)
        self.assertIn("Fused 3 common relics", mock_out.getvalue())
        relics = StorageManager(save_dir).load().ship.relics
        self.assertEqual(len(relics), 1)
        self.assertEqual(relics[0].rarity, "rare")

    def test_cli_runs_as_module_and_reaches_the_fuse_handler(self):
        argv = [
            "voidfarer", "--save-path", str(Path(self._tmp.name) / ".voidfarer"),
            "relics", "fuse", "common",
        ]
        with patch.object(sys, "argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as raised:
                runpy.run_module("voidfarer.cli", run_name="__main__")
        self.assertIn(raised.exception.code, (0, 1))

    def test_cli_frontier_commands(self):
        cases = [
            (["quests"], "QUEST PANEL"),
            (["ai", "list"], "AI CAPTAINS"),
            (["messages", "list"], "QUANTUM INBOX"),
            (["depot", "status"], None),
            (["mercs", "list"], "MERCENARY CONTRACTS"),
            (["allies", "list"], "ALLIANCES"),
        ]
        for argv, expected in cases:
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = main(argv)
                self.assertNotEqual(code, 2, argv)
                if expected:
                    self.assertIn(expected, mock_out.getvalue())

class TestCLIMaxTrades(_IsolatedCliTestCase):
    """`buy <id> max` and `sell <id> all` match the REST max flag and the REPL."""

    def test_sell_all_and_buy_max(self):
        engine = SimulationEngine(seed=42)
        engine.orbit("sol_body_1")
        engine.state = engine._clone_state(ship=engine._clone_ship(cargo={"fuel_cells": 4}))
        save_dir = Path(self._tmp.name) / ".voidfarer"
        StorageManager(save_dir).save(engine.state)

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            self.assertEqual(main(["sell", "fuel_cells", "all"]), 0)
            self.assertEqual(main(["buy", "fuel_cells", "max"]), 0)
        self.assertIn("Sold 4x", mock_out.getvalue())
        ship = StorageManager(save_dir).load().ship
        self.assertGreater(ship.cargo.get("fuel_cells", 0), 0)
        self.assertIn("fuel_cells", ship.cargo_cost)

    def test_non_numeric_quantity_is_rejected(self):
        with patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit) as raised:
                main(["buy", "fuel_cells", "lots"])
        self.assertEqual(raised.exception.code, 2)


class TestCLINewMechanicsParity(_IsolatedCliTestCase):
    """Smuggling, overhaul, fabrication and salvage strategies need CLI parity with REST."""

    def _saved(self, engine: SimulationEngine) -> tuple[StorageManager, Path]:
        save_dir = Path(self._tmp.name) / ".voidfarer"
        storage = StorageManager(save_dir)
        storage.save(engine.state)
        return storage, save_dir

    def test_customs_status_and_jettison(self):
        encounter = CustomsEncounter(
            id="cli_customs", faction="Sol Coalition", system_id="sol", system_name="Sol System",
            patrol_vessel="Sol Cutter", contraband_found={"xenoliths": 2},
            fine_amount=1200, bribe_amount=600, description="Patrol intercept",
        )
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(credits=2000, cargo={"xenoliths": 2, "titanium": 4}),
            active_customs=encounter,
        )
        _, save_dir = self._saved(engine)

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            self.assertEqual(main(["customs"]), 0)
        self.assertIn("CUSTOMS INTERDICTION", mock_out.getvalue())
        self.assertIn("xenoliths", mock_out.getvalue())

        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(main(["customs", "jettison"]), 0)
        state = StorageManager(save_dir).load()
        self.assertIsNone(state.active_customs)
        self.assertNotIn("xenoliths", state.ship.cargo)
        self.assertEqual(state.ship.cargo.get("titanium"), 4)

    def test_overhaul_command_scrubs_wear_and_persists(self):
        engine = SimulationEngine(seed=42)
        body = next(b.id for b in engine.current_system.bodies if b.station_dockable)
        engine.orbit(body)
        engine.state = engine._clone_state(ship=engine._clone_ship(wear=20.0, credits=5000))
        _, save_dir = self._saved(engine)

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            self.assertEqual(main(["overhaul"]), 0)
        self.assertIn("overhaul completed", mock_out.getvalue().lower())
        ship = StorageManager(save_dir).load().ship
        self.assertEqual(ship.wear, 0.0)
        self.assertLess(ship.credits, 5000)

    def test_fabricate_command_consumes_titanium(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(hull=50, cargo={"titanium": 2}))
        _, save_dir = self._saved(engine)

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            self.assertEqual(main(["fabricate", "patch_kit"]), 0)
        self.assertIn("+25 Hull", mock_out.getvalue())
        ship = StorageManager(save_dir).load().ship
        self.assertEqual(ship.hull, 75)
        self.assertEqual(ship.cargo.get("titanium"), 1)

    def test_salvage_strategy_is_forwarded_to_the_engine(self):
        with patch.object(SimulationEngine, "salvage_derelict", return_value=(True, "ok", {})) as called:
            with patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(main(["salvage", "aggressive"]), 0)
        called.assert_called_once_with(strategy="aggressive")


class TestCLICombatAndCrewParity(_IsolatedCliTestCase):
    """New combat subsystems and bridge stations must be reachable from the terminal."""

    def _combat_action_for(self, argv):
        with patch.object(SimulationEngine, "combat_action", return_value=(True, "ok")) as called:
            with patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(main(argv), 0)
        return called.call_args.args[0]

    def test_new_combat_maneuvers_map_to_engine_actions(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            active_combat=CombatEncounter(
                id="cli_combat", enemy_name="Raider", enemy_class="Frigate",
                enemy_hull=100, enemy_max_hull=100, enemy_damage=10, bounty_credits=100,
            )
        )
        StorageManager(Path(self._tmp.name) / ".voidfarer").save(engine.state)
        cases = {
            ("combat", "target", "engines"): "target_engines",
            ("combat", "target", "drive"): "target_engines",
            ("combat", "target", "bridge"): "target_bridge",
            ("combat", "target", "shields"): "target_shields",
            ("combat", "target", "weapons"): "target_weapons",
            ("combat", "target"): "target_weapons",
            ("combat", "pdc"): "point_defense",
            ("combat", "vent"): "vent_heat",
        }
        for argv, expected in cases.items():
            with self.subTest(argv=argv):
                self.assertEqual(self._combat_action_for(list(argv)), expected)

    def test_crew_station_assignment_persists(self):
        engine = SimulationEngine(seed=42)
        crew = next(c for c in engine.state.ship.crew if c.status == "active")
        save_dir = Path(self._tmp.name) / ".voidfarer"
        StorageManager(save_dir).save(engine.state)

        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            self.assertEqual(main(["crew", "station", crew.id, "helm"]), 0)
        self.assertIn("HELM station", mock_out.getvalue())
        reloaded = StorageManager(save_dir).load()
        self.assertEqual(next(c for c in reloaded.ship.crew if c.id == crew.id).station, "helm")

        with patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(main(["crew", "station", crew.id, "unassigned"]), 0)
        reloaded = StorageManager(save_dir).load()
        self.assertEqual(next(c for c in reloaded.ship.crew if c.id == crew.id).station, "")


class TestCLIDiplomacyHelpParity(_IsolatedCliTestCase):
    def test_diplomacy_help_matches_parser_choices(self):
        from voidfarer.cli import cmd_diplomacy
        engine = SimulationEngine(seed=42)
        storage = StorageManager(self._tmp.name)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            cmd_diplomacy(engine, storage, ["diplomacy"])
        text = mock_out.getvalue()
        self.assertIn("ceasefire", text)
        self.assertNotIn("declare_war", text)
        self.assertNotIn("|peace ", text)

    def test_diplomacy_without_faction_shows_usage(self):
        from voidfarer.cli import cmd_diplomacy
        engine = SimulationEngine(seed=42)
        storage = StorageManager(self._tmp.name)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            rc = cmd_diplomacy(engine, storage, ["diplomacy", "improve"])
        self.assertEqual(rc, 1)
        self.assertIn("Usage", mock_out.getvalue())


class TestCLIQuantityGuards(_IsolatedCliTestCase):
    def test_depot_non_integer_quantity_rejected(self):
        from voidfarer.cli import cmd_depot
        engine = SimulationEngine(seed=42)
        storage = StorageManager(self._tmp.name)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            rc = cmd_depot(engine, storage, ["depot", "deposit", "titanium", "abc"])
        self.assertEqual(rc, 1)
        self.assertIn("integer", mock_out.getvalue().lower())

    def test_fleet_repair_non_integer_amount_rejected(self):
        from voidfarer.cli import cmd_fleet
        engine = SimulationEngine(seed=42)
        storage = StorageManager(self._tmp.name)
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            rc = cmd_fleet(engine, storage, ["fleet", "repair_escorts", "abc"])
        self.assertEqual(rc, 1)
        self.assertIn("integer", mock_out.getvalue().lower())


class TestCLIAiHailParity(_IsolatedCliTestCase):
    def test_ai_hail_forwards_no_spurious_commodity(self):
        from voidfarer import engine as engine_mod
        seen = {}
        def fake_interact(self, captain_id, action, commodity=None, quantity=1):
            seen.update(captain_id=captain_id, action=action, commodity=commodity, quantity=quantity)
            return True, "ok"
        with patch.object(engine_mod.SimulationEngine, "interact_ai", fake_interact):
            with patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(main(["ai", "hail", "captain_vega"]), 0)
        self.assertEqual(seen["captain_id"], "captain_vega")
        self.assertEqual(seen["action"], "hail")
        self.assertIsNone(seen["commodity"])
        self.assertEqual(seen["quantity"], 1)


class TestCLIReplRelicsFuse(_IsolatedCliTestCase):
    def test_repl_relics_fuse(self):
        from dataclasses import replace
        from voidfarer.cli import cmd_repl
        from voidfarer.retention import CATALOG_RELICS
        commons = [r for r in CATALOG_RELICS if r.rarity == "common"][:2]
        extra = replace(commons[0], id="relic_common_extra")
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(relics=tuple(commons + [extra])))
        storage = StorageManager(Path(self._tmp.name) / ".voidfarer")
        storage.save(engine.state)
        with patch("builtins.input", side_effect=["relics fuse common", "exit"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                self.assertEqual(cmd_repl(engine, storage), 0)
        self.assertIn("Fused", mock_out.getvalue())

    def test_repl_relics_fuse_does_not_exit(self):
        from dataclasses import replace
        from voidfarer.cli import cmd_repl
        from voidfarer.retention import CATALOG_RELICS
        commons = [r for r in CATALOG_RELICS if r.rarity == "common"][:2]
        extra = replace(commons[0], id="relic_common_extra")
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(relics=tuple(commons + [extra])))
        storage = StorageManager(Path(self._tmp.name) / ".voidfarer")
        storage.save(engine.state)
        with patch("builtins.input", side_effect=["relics fuse common", "status", "exit"]):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                self.assertEqual(cmd_repl(engine, storage), 0)
        out = mock_out.getvalue()
        self.assertIn("Fused", out)
        self.assertIn("VITAL TELEMETRY", out)


if __name__ == "__main__":
    unittest.main()

