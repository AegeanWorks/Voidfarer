"""The headless cockpit audit has deterministic viewport, parsing and wrapper helpers."""

import html
import json
import tempfile
import unittest
from pathlib import Path

from tools.ui_audit import (ERROR_COLLECTOR, WRAPPER_JS, outer_window, parse_audit,
                            prepare_static, severe_findings)


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


if __name__ == "__main__":
    unittest.main()
