"""The headless cockpit audit has deterministic viewport, parsing and wrapper helpers."""

import html
import json
import tempfile
import unittest
from pathlib import Path

from tools.ui_audit import (ERROR_COLLECTOR, WRAPPER_JS, audit_timeout, browser_command, outer_window,
                            parse_audit, prepare_static, seed_audit_state, severe_findings,
                            summary_line)


class _RecordingEngine:
    def __init__(self, mastery_level=1, xp=0):
        from types import SimpleNamespace
        from voidfarer.models import PilotMastery
        self.skipped = 0
        self.cloned = {}
        self.state = SimpleNamespace(ship=SimpleNamespace(mastery=PilotMastery(level=mastery_level, xp=xp)))

    def skip_tutorial(self):
        self.skipped += 1

    def _clone_ship(self, **kwargs):
        self.cloned["ship"] = kwargs
        return kwargs

    def _clone_state(self, **kwargs):
        from types import SimpleNamespace
        return SimpleNamespace(**kwargs)


class AuditStateTest(unittest.TestCase):

    def test_a_fresh_save_keeps_the_cadet_academy(self):
        engine = _RecordingEngine()
        seed_audit_state(engine, False)
        self.assertEqual(engine.skipped, 0)

    def test_post_tutorial_uses_the_engine_skip_action(self):
        engine = _RecordingEngine()
        seed_audit_state(engine, True)
        self.assertEqual(engine.skipped, 1, "the advanced tabs only exist after graduation")

    def test_mastery_seed_raises_the_level_and_keeps_progress(self):
        engine = _RecordingEngine(mastery_level=1, xp=140)
        seed_audit_state(engine, True, 3)
        mastery = engine.state.ship["mastery"]
        self.assertEqual(mastery.level, 3)
        self.assertEqual(mastery.xp, 140, "a seeded audit must keep the save's progress fields")

    def test_mastery_seed_is_a_no_op_at_the_same_level(self):
        engine = _RecordingEngine(mastery_level=3)
        seed_audit_state(engine, True, 3)
        self.assertEqual(engine.cloned, {})


class AuditHelpersTest(unittest.TestCase):

    def test_wide_viewports_get_only_window_chrome(self):
        self.assertEqual(outer_window((1920, 1080)), (1944, 1172))
        self.assertEqual(outer_window((1280, 720)), (1304, 812))

    def test_laptop_keeps_an_exact_iframe(self):
        self.assertEqual(outer_window((1366, 768)), (1390, 860))

    def test_parse_audit_reads_an_escaped_payload(self):
        report = {"name": "desktop", "scroll": {"horizontal": False}, "errors": []}
        dom = f'<pre id="__ui_audit__">{html.escape(json.dumps(report))}</pre>'
        self.assertEqual(parse_audit(dom), report)

    def test_parse_audit_refuses_a_missing_payload(self):
        with self.assertRaises(ValueError):
            parse_audit("<html><body>no report</body></html>")

    def test_prepare_static_injects_the_collector_and_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            (source / "index.html").write_text("<html><head></head><body></body></html>",
                                               encoding="utf-8")
            prepared = prepare_static(source, Path(directory))
            page = (prepared / "index.html").read_text(encoding="utf-8")
            self.assertIn(ERROR_COLLECTOR, page)
            self.assertTrue((prepared / "__ui_audit__.html").is_file())
            self.assertTrue((prepared / "__ui_audit__.js").is_file())

    def test_severe_findings_name_the_blocking_categories(self):
        report = {"errors": ["boom"], "scroll": {"horizontal": True},
                  "tinyText": [{"el": "span"}], "smallTargets": [{"el": "button"}],
                  "contrast": []}
        self.assertEqual(severe_findings(report), ["console", "hscroll", "tinyText", "smallTargets"])

    def test_modal_layers_are_not_reported_as_hud_collisions(self):
        self.assertIn('parseInt(style.zIndex || "0", 10) >= 50', WRAPPER_JS)
        self.assertNotIn('parseInt(style.zIndex || "0", 10) >= 500', WRAPPER_JS)

    def test_browser_command_emulates_windows_scaling(self):
        command = browser_command(Path("msedge.exe"), (1920, 1080), Path("p"),
                                  Path("shot.png"), "http://127.0.0.1:1/", 2)
        self.assertIn("--force-device-scale-factor=2", command)
        self.assertIn("--window-size=1944,1172", command)
        default = browser_command(Path("msedge.exe"), (1280, 720), Path("p"),
                                  Path("shot.png"), "http://127.0.0.1:1/")
        self.assertIn("--force-device-scale-factor=1", default)

    def test_a_blurry_radar_backing_store_is_a_severe_finding(self):
        report = {"errors": [], "scroll": {"horizontal": False},
                  "radar": {"dprCorrect": False, "dpr": 2}}
        self.assertEqual(severe_findings(report), ["radarDpr"])
        self.assertEqual(severe_findings({"radar": {"dprCorrect": True}}), [])
    def test_summary_line_reports_the_radar_state(self):
        line = summary_line({"name": "desktop@2x", "viewport": {"width": 1920, "height": 1080},
                             "radar": {"dprCorrect": True}})
        self.assertIn("radar ok", line)
        blurry = summary_line({"name": "desktop", "viewport": {"width": 1920, "height": 1080},
                               "radar": {"dprCorrect": False}})
        self.assertIn("radar BLURRY", blurry)

    def test_dpr_timeout_scaling_matches_documented_capture_cost(self):
        self.assertEqual(audit_timeout(120, 1), 120)
        self.assertEqual(audit_timeout(120, 1.5), 270)
        self.assertEqual(audit_timeout(120, 2.0), 480)


if __name__ == "__main__":
    unittest.main()
