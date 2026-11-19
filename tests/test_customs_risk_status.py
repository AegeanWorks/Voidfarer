"""The status snapshot warns about customs risk while contraband is in the hold."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.smuggling import is_contraband
from voidfarer.galaxy import COMMODITY_MAP


def _engine(cargo):
    engine = SimulationEngine(seed=42)
    engine.state = engine._clone_state(ship=engine._clone_ship(cargo=cargo))
    return engine


class CustomsRiskStatusTest(unittest.TestCase):
    def test_clean_hold_has_no_warning(self):
        self.assertIsNone(_engine({"fuel_cells": 5}).get_status_snapshot()["customs_risk"])

    def test_contraband_quotes_the_worst_adjacent_high_security_cordon(self):
        contraband = next(c for c in COMMODITY_MAP if is_contraband(c))
        engine = _engine({contraband: 4})
        risk = engine.get_status_snapshot()["customs_risk"]
        self.assertEqual(risk["units"], 4)
        self.assertGreater(risk["chance"], 0.0)
        self.assertLessEqual(risk["chance"], 1.0)
        self.assertTrue(risk["system_name"])
        self.assertIn("sensor", risk["hint"].lower())
        self.assertIn(risk["system_id"], engine.current_system.connections)
        self.assertEqual(engine.state.systems[risk["system_id"]].name, risk["system_name"])

    def test_routing_power_to_the_sensors_lowers_the_quote(self):
        contraband = next(c for c in COMMODITY_MAP if is_contraband(c))
        engine = _engine({contraband: 4})
        engine.route_power(40, 10, 10, 40)
        low_sensors = engine.get_status_snapshot()["customs_risk"]["chance"]
        engine.route_power(10, 10, 60, 20)
        high_sensors = engine.get_status_snapshot()["customs_risk"]["chance"]
        self.assertLess(high_sensors, low_sensors)

if __name__ == "__main__":
    unittest.main()
