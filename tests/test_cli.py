"""Unit tests for command-line arguments and subcommands."""

import io
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from voidfarer.cli import cmd_inventory, cmd_repl, main
from voidfarer.engine import SimulationEngine
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

    def test_cli_fleet_sell_escort_parses(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["fleet", "sell_escort", "missing_prize"])
            self.assertEqual(code, 1)
            self.assertIn("unknown escort", mock_out.getvalue().lower())

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

if __name__ == "__main__":
    unittest.main()


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
