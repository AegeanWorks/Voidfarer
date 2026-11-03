"""Unit tests for contraband smuggling, security scans, and customs interdiction."""

from __future__ import annotations

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import CustomsEncounter, StarSystem
from voidfarer.smuggling import (
    calculate_customs_scan_risk,
    generate_customs_encounter,
    get_contraband_in_cargo,
    is_contraband,
)


class TestSmugglingSecurity(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_contraband_classification(self):
        self.assertTrue(is_contraband("xenoliths"))
        self.assertFalse(is_contraband("titanium"))
        self.assertFalse(is_contraband("fuel_cells"))
        self.assertFalse(is_contraband("hydroponics"))

    def test_get_contraband_in_cargo(self):
        cargo = {"titanium": 5, "xenoliths": 3, "fuel_cells": 10}
        contraband = get_contraband_in_cargo(cargo)
        self.assertEqual(contraband, {"xenoliths": 3})

        empty_cargo = {"titanium": 5}
        self.assertEqual(get_contraband_in_cargo(empty_cargo), {})

    def test_customs_scan_risk_clean_or_low_security(self):
        cur_sys = self.engine.current_system
        # Clean cargo -> 0.0 risk
        risk, reasons = calculate_customs_scan_risk(
            cur_sys, {}, self.engine.state.ship, self.engine.state.ship.power
        )
        self.assertEqual(risk, 0.0)

        # Low security system -> 0.0 risk even with contraband
        low_sec_sys = StarSystem(
            id="anarchy", name="Anarchy Outpost", seed=1, x=0, y=0,
            spectral_type="M", color="#ff0000", security=0.20, faction="Void Corsairs",
            bodies=(), connections=(), dominant_corp=None, modifiers=()
        )
        risk_low, _ = calculate_customs_scan_risk(
            low_sec_sys, {"xenoliths": 5}, self.engine.state.ship, self.engine.state.ship.power
        )
        self.assertEqual(risk_low, 0.0)

    def test_customs_scan_risk_with_contraband_and_evasion(self):
        cur_sys = self.engine.current_system  # Sol: security 1.0
        cargo = {"xenoliths": 4}

        # Baseline risk
        risk_base, reasons_base = calculate_customs_scan_risk(
            cur_sys, cargo, self.engine.state.ship, self.engine.state.ship.power
        )
        self.assertGreater(risk_base, 0.20)

        # Evasion via stealth chassis
        stealth_ship = self.engine._clone_ship(ship_class="stealth_recon")
        risk_stealth, reasons_stealth = calculate_customs_scan_risk(
            cur_sys, cargo, stealth_ship, self.engine.state.ship.power
        )
        self.assertLess(risk_stealth, risk_base)
        self.assertTrue(any("Stealth" in r for r in reasons_stealth))

        # Evasion via sensor ECM power
        from voidfarer.models import ShipPower
        sensor_power = ShipPower(engines=20, shields=20, sensors=45, weapons=15)
        risk_sensor, reasons_sensor = calculate_customs_scan_risk(
            cur_sys, cargo, self.engine.state.ship, sensor_power
        )
        self.assertLess(risk_sensor, risk_base)
        self.assertTrue(any("ECM" in r for r in reasons_sensor))

    def test_stealth_upgrade_values_not_keys(self):
        cur_sys = self.engine.current_system  # Sol: security 1.0
        cargo = {"xenoliths": 4}
        ship_with_stealth_value = self.engine._clone_ship(
            equipped_upgrades={"slot1": "stealth_coating"}
        )
        _, reasons_value = calculate_customs_scan_risk(
            cur_sys, cargo, ship_with_stealth_value, self.engine.state.ship.power
        )
        self.assertTrue(any("Stealth" in r for r in reasons_value))

        ship_with_stealth_key = self.engine._clone_ship(
            equipped_upgrades={"stealth_slot": "basic_sensor"}
        )
        _, reasons_key = calculate_customs_scan_risk(
            cur_sys, cargo, ship_with_stealth_key, self.engine.state.ship.power
        )
        self.assertFalse(any("Stealth" in r for r in reasons_key))

    def test_generate_customs_encounter(self):
        cur_sys = self.engine.current_system
        cargo = {"xenoliths": 2}
        encounter = generate_customs_encounter(cur_sys, cargo, self.engine.state.ship, seed=123)
        self.assertIsInstance(encounter, CustomsEncounter)
        self.assertEqual(encounter.contraband_found, {"xenoliths": 2})
        self.assertGreater(encounter.fine_amount, 1000)
        self.assertGreater(encounter.bribe_amount, 500)
        self.assertLess(encounter.bribe_amount, encounter.fine_amount)
        self.assertTrue(encounter.patrol_vessel)

    def test_resolve_customs_bribe(self):
        encounter = CustomsEncounter(
            id="c1", faction="Sol Coalition", system_id="sol", system_name="Sol System",
            patrol_vessel="Sol Cutter", contraband_found={"xenoliths": 2},
            fine_amount=1500, bribe_amount=800, description="Hailed by patrol",
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=3000, cargo={"xenoliths": 2, "titanium": 10}),
            active_customs=encounter,
        )
        # Cannot jump while under customs lock
        ok, msg = self.engine.jump(self.engine.current_system.connections[0])
        self.assertFalse(ok)
        self.assertIn("Customs interdiction unresolved", msg)

        # Resolve via bribe
        ok_bribe, msg_bribe = self.engine.resolve_customs("bribe")
        self.assertTrue(ok_bribe)
        self.assertIsNone(self.engine.state.active_customs)
        self.assertEqual(self.engine.state.ship.credits, 2200)
        self.assertEqual(self.engine.state.ship.cargo.get("xenoliths"), 2)
        self.assertEqual(self.engine.state.stats.get("bribes_paid"), 1)

    def test_resolve_customs_jettison(self):
        encounter = CustomsEncounter(
            id="c2", faction="Sol Coalition", system_id="sol", system_name="Sol System",
            patrol_vessel="Sol Cutter", contraband_found={"xenoliths": 3},
            fine_amount=2000, bribe_amount=1000, description="Hailed by patrol",
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=1000, cargo={"xenoliths": 3, "titanium": 5}),
            active_customs=encounter,
        )
        ok, msg = self.engine.resolve_customs("jettison")
        self.assertTrue(ok)
        self.assertIsNone(self.engine.state.active_customs)
        self.assertNotIn("xenoliths", self.engine.state.ship.cargo)
        self.assertEqual(self.engine.state.ship.cargo.get("titanium"), 5)
        self.assertEqual(self.engine.state.stats.get("smuggling_evaded"), 1)

    def test_resolve_customs_confiscate(self):
        encounter = CustomsEncounter(
            id="c3", faction="Sol Coalition", system_id="sol", system_name="Sol System",
            patrol_vessel="Sol Cutter", contraband_found={"xenoliths": 1},
            fine_amount=1200, bribe_amount=600, description="Hailed by patrol",
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=1500, cargo={"xenoliths": 1}),
            active_customs=encounter,
        )
        ok, msg = self.engine.resolve_customs("confiscate")
        self.assertTrue(ok)
        self.assertIsNone(self.engine.state.active_customs)
        self.assertNotIn("xenoliths", self.engine.state.ship.cargo)
        self.assertEqual(self.engine.state.ship.credits, 300)
        self.assertEqual(self.engine.state.stats.get("contraband_seized"), 1)

    def test_resolve_customs_flee(self):
        encounter = CustomsEncounter(
            id="c4", faction="Sol Coalition", system_id="sol", system_name="Sol System",
            patrol_vessel="Sol Cutter", contraband_found={"xenoliths": 1},
            fine_amount=1000, bribe_amount=500, description="Hailed by patrol",
        )
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fuel=20, cargo={"xenoliths": 1}),
            active_customs=encounter,
        )
        ok, msg = self.engine.resolve_customs("flee")
        self.assertTrue(ok)
        self.assertIsNone(self.engine.state.active_customs)
        self.assertEqual(self.engine.state.ship.fuel, 15)  # 5 fuel burned


if __name__ == "__main__":
    unittest.main()
