"""Uncontrolled tick counts cannot crash the clock (ADR-421)."""

from __future__ import annotations

import math
import unittest

from voidfarer.engine import MAX_TICKS_PER_STEP, SimulationEngine
from voidfarer.models import TimeState


class DateClampTest(unittest.TestCase):
    def test_a_huge_elapsed_day_count_renders_a_valid_date(self):
        rendered = TimeState(elapsed_days=10 ** 9).current_date
        self.assertRegex(rendered, r"^\d{2}\.\d{2}\.\d{4}$")
        self.assertEqual(rendered, "31.12.9999")

    def test_an_infinite_elapsed_day_count_renders_the_ceiling(self):
        self.assertEqual(TimeState(elapsed_days=math.inf).current_date, "31.12.9999")

    def test_a_nan_elapsed_day_count_renders_the_start(self):
        self.assertEqual(TimeState(elapsed_days=math.nan).current_date, "01.01.3042")

    def test_a_negative_elapsed_day_count_renders_the_start(self):
        self.assertEqual(TimeState(elapsed_days=-5.0).current_date, "01.01.3042")

    def test_an_ordinary_day_count_is_unchanged(self):
        self.assertEqual(TimeState(elapsed_days=365.0).current_date, "01.01.3043")


class TickCapTest(unittest.TestCase):
    def test_a_step_beyond_the_cap_is_refused(self):
        engine = SimulationEngine(seed=3)
        before = engine.state.time.tick
        ok, message, summary = engine.step_time(MAX_TICKS_PER_STEP + 1)
        self.assertFalse(ok)
        self.assertIn("Why:", message)
        self.assertIn("Fix:", message)
        self.assertEqual(engine.state.time.tick, before)
        self.assertEqual(summary.get("ticks_advanced", 0), 0)

    def test_a_step_at_the_cap_is_allowed(self):
        engine = SimulationEngine(seed=3)
        before = engine.state.time.tick
        ok, message, _ = engine.step_time(MAX_TICKS_PER_STEP)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.time.tick, before + MAX_TICKS_PER_STEP)
        self.assertRegex(engine.state.time.current_date, r"^\d{2}\.\d{2}\.\d{4}$")

    def test_a_billion_ticks_no_longer_raises(self):
        engine = SimulationEngine(seed=3)
        summary = engine.tick(10 ** 9)
        self.assertGreater(summary["ticks_advanced"], 0)
        self.assertEqual(engine.state.time.current_date, "31.12.9999")

    def test_a_normal_step_still_advances(self):
        engine = SimulationEngine(seed=3)
        before = engine.state.time.tick
        ok, message, _ = engine.step_time(3)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.time.tick, before + 3)


if __name__ == "__main__":
    unittest.main()
