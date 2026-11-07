"""Wave 8 fix-batch: failing-first regressions for swarm-verified defects."""

import io
import os
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from voidfarer.cli import main
from voidfarer.engine import SimulationEngine


class _IsolatedCli(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        p = patch.dict(
            os.environ,
            {"LOCALAPPDATA": self._tmp.name, "HOME": self._tmp.name, "USERPROFILE": self._tmp.name},
        )
        p.start()
        self.addCleanup(p.stop)


class TestPirateFleeShellParses(_IsolatedCli):
    def test_pirate_flee_reaches_engine_not_argparse(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            rc = main(["pirate", "flee"])
        self.assertEqual(rc, 1)


class TestResetRejectsNegativeSeed(unittest.TestCase):
    def test_reset_negative_seed_rejected(self):
        engine = SimulationEngine(seed=42)
        ok, msg = engine.reset(-5)
        self.assertFalse(ok)
        self.assertIn("non-negative", msg.lower())


class TestDroneIdsNeverReused(unittest.TestCase):
    def test_drone_ids_unique_after_dismiss(self):
        engine = SimulationEngine(seed=42)
        ok, msg = engine.orbit("sol_body_1")
        self.assertTrue(ok, msg)
        self.assertTrue(engine.buy_drone("mining")[0])
        self.assertTrue(engine.buy_drone("mining")[0])
        first = engine.state.ship.fleet_drones[0].id
        self.assertTrue(engine.dismiss_fleet_unit(first)[0])
        self.assertTrue(engine.buy_drone("mining")[0])
        ids = [d.id for d in engine.state.ship.fleet_drones]
        self.assertEqual(len(ids), len(set(ids)))


class TestEvasionCapped(unittest.TestCase):
    def test_stacked_evasion_still_misses_sometimes(self):
        from voidfarer import engine as engine_mod
        from voidfarer.models import CombatEncounter, FleetDrone, ShipPower

        engine = SimulationEngine(seed=42)
        power = ShipPower(engines=25, shields=25, sensors=25, weapons=25)
        combat = CombatEncounter(
            id="evade_cap_test",
            enemy_name="Corsair",
            enemy_class="Frigate",
            enemy_hull=100,
            enemy_max_hull=100,
            enemy_damage=25,
            bounty_credits=300,
            salvage_commodity="titanium",
            enemy_shield=0,
            enemy_max_shield=50,
            enemy_intent="fire",
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                hull=100,
                max_hull=100,
                shield=100,
                max_shield=100,
                fuel=60,
                max_fuel=60,
                power=power,
                fleet_drones=(
                    FleetDrone(
                        id="merc_evade_1",
                        name="Evasion Merc",
                        drone_type="mercenary",
                        assigned_system_id="sol",
                        specialty="evasion",
                    ),
                ),
            ),
            active_combat=combat,
        )
        real_calc = engine_mod.calculate_equipment_bonuses

        def boosted(ship):
            bonuses = dict(real_calc(ship))
            bonuses["evasion"] = 0.90
            return bonuses

        engine.rng.random = lambda: 0.96
        with patch.object(engine_mod, "calculate_equipment_bonuses", side_effect=boosted):
            ok, msg = engine.combat_action("fire_lasers")
        self.assertTrue(ok)
        self.assertNotIn("evaded incoming fire", msg)
