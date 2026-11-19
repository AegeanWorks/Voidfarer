"""Reactor heat follows the live capacity, not a stale base cap (ADR-417)."""

from __future__ import annotations

import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory

from voidfarer.engine import SimulationEngine
from voidfarer.reactor import reactor_heat_capacity
from voidfarer.storage import StorageManager


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=7)
    engine.state = engine._clone_state(ship=engine._clone_ship(credits=50000))
    return engine


def _heat(engine: SimulationEngine) -> float:
    return engine.state.ship.reactor.heat


def _capacity(engine: SimulationEngine) -> float:
    return reactor_heat_capacity(
        engine.state.ship.reactor, engine._combined_equipment()
    )


class ThermalCapacityTest(unittest.TestCase):
    def test_a_thermal_mod_raises_the_capacity(self):
        engine = _engine()
        base = _capacity(engine)
        ok, message = engine.install_ship_mod("cryo_loop")
        self.assertTrue(ok, message)
        self.assertGreater(_capacity(engine), base)

    def test_heat_above_the_base_cap_survives_a_save(self):
        engine = _engine()
        ok, message = engine.install_ship_mod("cryo_loop")
        self.assertTrue(ok, message)
        self.assertGreaterEqual(_capacity(engine), 120.0)
        engine.state = engine._clone_state(
            ship=replace(engine.state.ship,
                         reactor=replace(engine.state.ship.reactor, heat=120.0))
        )
        with TemporaryDirectory() as temp_dir:
            StorageManager(temp_dir).save(engine.state)
            resumed = SimulationEngine(state=StorageManager(temp_dir).load())
        self.assertEqual(_heat(resumed), 120.0)

    def test_removing_a_thermal_mod_clamps_the_core(self):
        engine = _engine()
        ok, message = engine.install_ship_mod("cryo_loop")
        self.assertTrue(ok, message)
        engine.state = engine._clone_state(
            ship=replace(engine.state.ship,
                         reactor=replace(engine.state.ship.reactor, heat=120.0))
        )
        ok, message = engine.remove_ship_mod("thermal")
        self.assertTrue(ok, message)
        self.assertLessEqual(_heat(engine), _capacity(engine))

    def test_negative_heat_is_still_repaired_on_load(self):
        engine = _engine()
        payload = engine.state.to_dict()
        payload["ship"]["reactor"]["heat"] = -5.0
        restored = type(engine.state).from_dict(payload)
        self.assertEqual(restored.ship.reactor.heat, 0.0)

    def test_integrity_is_still_clamped_to_its_own_max(self):
        engine = _engine()
        payload = engine.state.to_dict()
        payload["ship"]["reactor"]["integrity"] = 250.0
        restored = type(engine.state).from_dict(payload)
        self.assertEqual(restored.ship.reactor.integrity,
                         restored.ship.reactor.max_integrity)


if __name__ == "__main__":
    unittest.main()
