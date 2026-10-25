"""Monthly economy: crew wages are a monthly rate accrued on the calendar, not a per-tick charge."""

import random
import unittest

from voidfarer.crew import DAYS_PER_MONTH, crew_upkeep, tick_crew
from voidfarer.engine import SimulationEngine


class TestMonthlyWages(unittest.TestCase):
    def test_tick_crew_charges_exactly_the_wage_due(self):
        engine = SimulationEngine(seed=42)
        _, paid, logs = tick_crew(engine.state.ship.crew, 4, 10_000, rng=random.Random(1), wage_due=7)
        self.assertEqual(paid, 7)
        self.assertFalse(any("UNPAID" in line for line in logs))

    def test_a_new_commander_pays_one_month_of_wages_per_month(self):
        engine = SimulationEngine(seed=42)
        upkeep = crew_upkeep(engine.state.ship.crew)
        ticks_per_month = int(DAYS_PER_MONTH / 0.25)
        start = engine.state.ship.credits
        for _ in range(ticks_per_month):
            engine.tick(1)
        spent = start - engine.state.ship.credits
        # Wages are the only standing cost; allow for small seeded event payouts either way.
        self.assertGreater(engine.state.ship.credits, start - 3 * upkeep)
        self.assertLess(abs(spent - upkeep), 2 * upkeep)

    def test_cash_flow_reports_monthly_rates(self):
        flow = SimulationEngine(seed=42).cash_flow()
        self.assertEqual(flow["upkeep_per_month"], 65)
        self.assertAlmostEqual(flow["net_per_month"], round(flow["passive_per_month"] - 65, 1))

    def test_month_end_report_is_logged_once_per_month(self):
        engine = SimulationEngine(seed=42)
        for _ in range(int(DAYS_PER_MONTH / 0.25) + 2):
            engine.tick(1)
        reports = [line for line in engine.state.ship.flight_log if line.startswith("MONTH END")]
        self.assertEqual(len(reports), 1)


if __name__ == "__main__":
    unittest.main()
