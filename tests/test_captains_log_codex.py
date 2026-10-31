"""Regression tests for the captain's log, discovery codex, statistics, and rewards."""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.cli import main
from voidfarer.codex import (
    CODEX_CATEGORIES,
    CODEX_ENTRIES,
    CODEX_MAP,
    CODEX_METRICS,
    build_codex_report,
    get_codex_entry,
    metric_value,
)
from voidfarer.engine import SimulationEngine
from voidfarer.models import CodexState, GameState
from voidfarer.storage import StorageManager

STATIC_DIR = Path(__file__).parent.parent / "voidfarer" / "static"


class TestCodexCatalog(unittest.TestCase):
    def test_entry_ids_are_unique_and_resolvable(self):
        ids = [entry.id for entry in CODEX_ENTRIES]
        self.assertEqual(len(ids), len(set(ids)))
        for entry in CODEX_ENTRIES:
            self.assertIs(get_codex_entry(entry.id), entry)
            self.assertIn(entry.metric, CODEX_METRICS)

    def test_entries_have_positive_targets_and_valid_categories(self):
        category_ids = {category.id for category in CODEX_CATEGORIES}
        for entry in CODEX_ENTRIES:
            self.assertGreater(entry.target, 0, entry.id)
            self.assertIn(entry.category, category_ids, entry.id)
            self.assertGreaterEqual(entry.reward_credits, 0, entry.id)
            self.assertGreaterEqual(entry.reward_xp, 0, entry.id)
            self.assertTrue(entry.title and entry.hint, entry.id)

    def test_report_covers_every_entry_and_starts_unclaimed(self):
        engine = SimulationEngine(seed=42)
        report = build_codex_report(engine.state)
        self.assertEqual(report["totals"]["entries"], len(CODEX_ENTRIES))
        self.assertEqual(report["totals"]["claimed"], 0)
        self.assertEqual(report["totals"]["ready"], 0)
        self.assertEqual(len(report["entries"]), len(CODEX_ENTRIES))
        self.assertEqual(report["totals"]["categories"], len(CODEX_CATEGORIES))
        self.assertTrue(report["stats"])
        self.assertEqual(report["log"], [])

    def test_fresh_engine_has_no_completed_milestones(self):
        engine = SimulationEngine(seed=42)
        report = build_codex_report(engine.state)
        completed = [entry["id"] for entry in report["entries"] if entry["completed"]]
        self.assertEqual(completed, [])

    def test_unknown_metric_is_rejected(self):
        engine = SimulationEngine(seed=42)
        with self.assertRaises(ValueError):
            metric_value(engine.state, "not_a_metric")


class TestCodexState(unittest.TestCase):
    def test_round_trip_preserves_claims_and_dates(self):
        state = CodexState(
            claimed=("first_light", "first_trade"),
            claimed_dates={"first_light": "01.01.3042", "first_trade": "03.01.3042"},
        )
        restored = CodexState.from_dict(state.to_dict())
        self.assertEqual(restored.claimed, state.claimed)
        self.assertEqual(restored.claimed_dates, state.claimed_dates)

    def test_legacy_game_payload_defaults_codex(self):
        engine = SimulationEngine(seed=42)
        payload = engine.state.to_dict()
        payload.pop("codex", None)
        restored = GameState.from_dict(payload)
        self.assertEqual(restored.codex.claimed, ())
        self.assertEqual(restored.codex.claimed_dates, {})


class TestCodexEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def _entry(self, entry_id):
        report = build_codex_report(self.engine.state)
        return next(entry for entry in report["entries"] if entry["id"] == entry_id)

    def test_jump_progresses_jump_and_system_metrics(self):
        before = metric_value(self.engine.state, "systems_visited")
        ok, _ = self.engine.jump("alpha_centauri")
        self.assertTrue(ok)
        self.assertEqual(metric_value(self.engine.state, "jumps"), 1)
        self.assertEqual(metric_value(self.engine.state, "systems_visited"), before + 1)
        self.assertTrue(self._entry("first_light")["completed"])
        self.assertTrue(self._entry("first_light")["ready"])

    def test_claim_grants_credits_xp_and_persists_once(self):
        ok, _ = self.engine.jump("alpha_centauri")
        self.assertTrue(ok)
        entry = self._entry("first_light")
        credits_before = self.engine.state.ship.credits
        xp_before = self.engine.state.ship.mastery.xp

        claimed, message = self.engine.claim_codex_reward("first_light")
        self.assertTrue(claimed, message)
        self.assertIn(entry["title"], message)
        self.assertEqual(self.engine.state.ship.credits, credits_before + entry["reward_credits"])
        self.assertEqual(self.engine.state.ship.mastery.xp, xp_before + entry["reward_xp"])
        self.assertIn("first_light", self.engine.state.codex.claimed)
        self.assertTrue(self.engine.state.codex.claimed_dates["first_light"])

        report = build_codex_report(self.engine.state)
        record = next(item for item in report["entries"] if item["id"] == "first_light")
        self.assertTrue(record["claimed"])
        self.assertFalse(record["ready"])
        self.assertEqual(report["totals"]["claimed"], 1)
        self.assertEqual(report["log"][0]["id"], "first_light")

        again, message = self.engine.claim_codex_reward("first_light")
        self.assertFalse(again)
        self.assertIn("already claimed", message.lower())

    def test_locked_and_unknown_claims_are_rejected_without_side_effects(self):
        credits_before = self.engine.state.ship.credits
        ok, message = self.engine.claim_codex_reward("warlord")
        self.assertFalse(ok)
        self.assertIn("Locked", message)
        self.assertEqual(self.engine.state.ship.credits, credits_before)

        ok, message = self.engine.claim_codex_reward("no_such_entry")
        self.assertFalse(ok)
        self.assertIn("Unknown", message)
        self.assertEqual(self.engine.state.codex.claimed, ())

    def test_scoop_increments_the_statistic(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fuel=10)
        )
        body = next(
            body for body in self.engine.current_system.bodies
            if body.body_type in ("star", "gas_giant", "ringed_giant", "ice_world")
        )
        ok, _ = self.engine.orbit(body.id)
        self.assertTrue(ok)
        ok, message = self.engine.scoop_fuel()
        self.assertTrue(ok, message)
        self.assertEqual(metric_value(self.engine.state, "scoops"), 1)

    def test_status_snapshot_exposes_the_codex(self):
        snapshot = self.engine.get_status_snapshot()
        self.assertIn("codex", snapshot)
        self.assertEqual(snapshot["codex"]["totals"]["entries"], len(CODEX_ENTRIES))
        self.assertIn("entries", snapshot["codex"])
        self.assertIn("stats", snapshot["codex"])

    def test_claims_survive_save_and_load(self):
        self.engine.jump("alpha_centauri")
        ok, message = self.engine.claim_codex_reward("first_light")
        self.assertTrue(ok, message)
        with tempfile.TemporaryDirectory() as tmp:
            storage = StorageManager(tmp)
            storage.save(self.engine.state)
            loaded = SimulationEngine(state=storage.load())
        self.assertIn("first_light", loaded.state.codex.claimed)
        self.assertTrue(loaded.state.codex.claimed_dates["first_light"])


class TestCodexCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def _run(self, argv):
        output = io.StringIO()
        with patch("sys.stdout", output):
            code = main(["--save-path", self._tmp.name] + argv)
        return code, output.getvalue()

    def test_log_and_codex_commands_render(self):
        code, output = self._run(["log"])
        self.assertEqual(code, 0)
        self.assertIn("CAPTAIN'S LOG", output)
        self.assertIn("MILESTONE LOG", output)

        code, output = self._run(["codex"])
        self.assertEqual(code, 0)
        self.assertIn("DISCOVERY CODEX", output)
        self.assertIn("first_light", output)

    def test_codex_claim_after_jump(self):
        code, _ = self._run(["jump", "alpha_centauri"])
        self.assertEqual(code, 0)
        code, output = self._run(["codex", "claim", "first_light"])
        self.assertEqual(code, 0)
        self.assertIn("claimed", output.lower())
        code, output = self._run(["codex", "claim", "first_light"])
        self.assertEqual(code, 1)
        self.assertIn("already claimed", output.lower())


class TestCodexCockpitAssets(unittest.TestCase):
    def test_index_declares_the_captains_log_tab(self):
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        for marker in ("tabBtnCodex", "tabContentCodex", "codexEntryList", "codexLog"):
            self.assertIn(f'id="{marker}"', html)

    def test_javascript_renders_and_claims_codex_entries(self):
        script = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
        for marker in ("renderCodex", "/api/codex/claim", "switchRightTab(\"codex\")", "codexBadge"):
            self.assertIn(marker, script)

    def test_styles_cover_codex_cards(self):
        css = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
        for marker in (".codex-entry", ".codex-progress-track", ".codex-log-line"):
            self.assertIn(marker, css)


if __name__ == "__main__":
    unittest.main()
