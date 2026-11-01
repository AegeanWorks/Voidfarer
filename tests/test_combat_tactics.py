"""Comprehensive unit tests for Tactical Subsystem Targeting, Combat Heat, and Field Munition Fabrication."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import CombatEncounter, ShipPower, StarSystem


class WeatherTestEngine(SimulationEngine):
    def _stable_unit(self, *args, **kwargs) -> float:
        return 0.1


class CombatTacticsAndMunitionsTest(unittest.TestCase):
    def _engine(self, wep_power: int = 20, reactor_mode: str = "balanced") -> SimulationEngine:
        engine = SimulationEngine(seed=42)
        rem = 100 - wep_power
        eng = rem // 3
        shd = rem // 3
        sns = rem - eng - shd
        power = ShipPower(engines=eng, shields=shd, sensors=sns, weapons=wep_power)
        combat = CombatEncounter(
            id="tactics_test",
            enemy_name="Corsair Marauder",
            enemy_class="Frigate",
            enemy_hull=100,
            enemy_max_hull=100,
            enemy_damage=25,
            bounty_credits=300,
            salvage_commodity="titanium",
            enemy_shield=20,
            enemy_max_shield=50,
            enemy_intent="fire",
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                hull=60,
                max_hull=100,
                shield=50,
                max_shield=100,
                fuel=30,
                max_fuel=60,
                power=power,
                cargo={"titanium": 3},
                reactor=replace(engine.state.ship.reactor, heat=0.0, mode=reactor_mode),
            ),
            active_combat=combat,
        )
        return engine

    def test_target_engines_cripples_drive_manifolds(self):
        engine = self._engine()
        # Set enemy intent to evade so we test evasion collapse
        engine.state = engine._clone_state(
            active_combat=replace(engine.state.active_combat, enemy_intent="evade")
        )
        ok, msg = engine.combat_action("target_engines")
        self.assertTrue(ok)
        self.assertIn("drive manifolds", msg)
        self.assertIn("Disabled impulse thrusters", msg)
        # Enemy took 18 damage (enemy_shield was 20, so shield drops to 2)
        combat = engine.state.active_combat
        self.assertEqual(combat.enemy_shield, 2)
        # Verify heat was generated (+5 heat)
        self.assertGreaterEqual(engine.state.ship.reactor.heat, 5.0)

    def test_target_bridge_requires_sufficient_weapon_power(self):
        engine = self._engine(wep_power=10)
        ok, msg = engine.combat_action("target_bridge")
        self.assertFalse(ok)
        self.assertIn("at least 15% Weapons reactor power", msg)

    def test_target_bridge_critical_strike_and_command_panic(self):
        engine = self._engine(wep_power=25)
        # Force RNG to succeed hit
        engine.rng.random = lambda: 0.1
        ok, msg = engine.combat_action("target_bridge")
        self.assertTrue(ok)
        self.assertIn("Bridge strike pierced the command deck", msg)
        self.assertIn("counter-battery cancelled", msg)
        # 50 critical damage dealt (20 to shield, 30 to hull -> enemy_hull drops to 70)
        combat = engine.state.active_combat
        self.assertEqual(combat.enemy_shield, 0)
        self.assertEqual(combat.enemy_hull, 70)
        # Player took 0 inbound damage because counter-battery was cancelled!
        self.assertEqual(engine.state.ship.shield, 50)
        # Bridge attack generated +10 heat
        self.assertGreaterEqual(engine.state.ship.reactor.heat, 10.0)

    def test_point_defense_reports_the_intercepted_counter_battery(self):
        engine = self._engine(wep_power=20)
        ok, msg = engine.combat_action("point_defense")
        self.assertTrue(ok)
        self.assertIn("Point Defense Cannons engaged", msg)
        self.assertIn("PDC flak screen intercepted 70%", msg)
        self.assertIn("Inbound counter-battery dealt 7 damage", msg)

    def test_combat_reactor_thermal_curve(self):
        # Balanced mode: laser generates +6.0 heat
        engine_bal = self._engine(reactor_mode="balanced")
        engine_bal.combat_action("fire_lasers")
        self.assertAlmostEqual(engine_bal.state.ship.reactor.heat, 6.0, places=1)

        # Overclock mode: laser generates 6.0 * 1.5 = +9.0 heat
        engine_oc = self._engine(reactor_mode="overclock")
        engine_oc.combat_action("fire_lasers")
        self.assertAlmostEqual(engine_oc.state.ship.reactor.heat, 9.0, places=1)

        # Eco mode: laser generates 6.0 * 0.7 = +4.2 heat
        engine_eco = self._engine(reactor_mode="eco")
        engine_eco.combat_action("fire_lasers")
        self.assertAlmostEqual(engine_eco.state.ship.reactor.heat, 4.2, places=1)

    def test_fabricate_patch_kit_success_and_guards(self):
        engine = self._engine()
        # Initial hull: 60/100, cargo: 3 titanium
        ok, msg = engine.fabricate_munitions("patch_kit")
        self.assertTrue(ok)
        self.assertIn("+25 Hull restored", msg)
        self.assertEqual(engine.state.ship.hull, 85)
        self.assertEqual(engine.state.ship.cargo["titanium"], 2)

        # Second patch kit tops up to max 100
        ok, msg = engine.fabricate_munitions("patch_kit")
        self.assertTrue(ok)
        self.assertEqual(engine.state.ship.hull, 100)
        self.assertEqual(engine.state.ship.cargo["titanium"], 1)

        # Rejects when hull is already full
        ok, msg = engine.fabricate_munitions("patch_kit")
        self.assertFalse(ok)
        self.assertIn("already at maximum capacity", msg)
        self.assertEqual(engine.state.ship.cargo["titanium"], 1)

        # Rejects when out of titanium
        engine.state = engine._clone_state(
            ship=engine._clone_ship(hull=50, cargo={})
        )
        ok, msg = engine.fabricate_munitions("patch_kit")
        self.assertFalse(ok)
        self.assertIn("Insufficient titanium alloy", msg)

    def test_fabricate_fuel_cell_success_and_guards(self):
        engine = self._engine()
        # Initial fuel: 30/60, cargo: 3 titanium
        ok, msg = engine.fabricate_munitions("fuel_cell")
        self.assertTrue(ok)
        self.assertIn("+25 Fuel restored", msg)
        self.assertEqual(engine.state.ship.fuel, 55)
        self.assertEqual(engine.state.ship.cargo["titanium"], 2)

        # Rejects unknown blueprint
        ok, msg = engine.fabricate_munitions("unknown_gizmo")
        self.assertFalse(ok)
        self.assertIn("Unknown fabrication blueprint", msg)

    def test_solar_weather_telemetry_and_hazard(self):
        engine = self._engine()
        # Telemetry in standard G-class system has no hazard
        telemetry = engine.check_solar_weather()
        self.assertIn("active_hazard", telemetry)
        self.assertIn("recommended_shields", telemetry)

        # In O-class high energy system
        o_sys = StarSystem(
            id="system_rigel",
            name="Rigel Primary",
            seed=1234,
            x=10.0,
            y=10.0,
            spectral_type="O",
            color="#9bb0ff",
            security=0.5,
            faction="Sol Coalition",
            bodies=(),
            connections=(),
        )
        o_telemetry = engine.check_solar_weather(o_sys)
        self.assertTrue(o_telemetry["active_hazard"])
        self.assertEqual(o_telemetry["hazard_chance"], 0.35)

    def test_solar_weather_jump_deflection_and_surge(self):
        # 1. Deflection with power.shields >= 35
        engine_safe = WeatherTestEngine(seed=10)
        # Create an adjacent O-class system linked to sol
        rigel = StarSystem(
            id="rigel_o",
            name="Rigel Prime",
            seed=5555,
            x=20.0,
            y=20.0,
            spectral_type="O",
            color="#9bb0ff",
            security=0.4,
            faction="Sol Coalition",
            bodies=(),
            connections=("sol",),
        )
        engine_safe.state.systems["rigel_o"] = rigel
        cur = engine_safe.state.systems["sol"]
        engine_safe.state.systems["sol"] = replace(cur, connections=tuple(list(cur.connections) + ["rigel_o"]))
        # Set shields power to 40%
        engine_safe.state = engine_safe._clone_state(
            ship=engine_safe._clone_ship(
                fuel=50,
                power=ShipPower(engines=20, shields=40, sensors=20, weapons=20),
            )
        )
        ok, msg = engine_safe.jump("rigel_o")
        self.assertTrue(ok)
        self.assertTrue(any("SPACE WEATHER DEFLECTION" in entry for entry in engine_safe.state.ship.flight_log))

        # 2. Surge drain with power.shields < 35
        engine_vulnerable = WeatherTestEngine(seed=10)
        engine_vulnerable.state.systems["rigel_o"] = rigel
        engine_vulnerable.state.systems["sol"] = replace(cur, connections=tuple(list(cur.connections) + ["rigel_o"]))
        engine_vulnerable.state = engine_vulnerable._clone_state(
            ship=engine_vulnerable._clone_ship(
                fuel=50,
                shield=30,
                power=ShipPower(engines=30, shields=20, sensors=30, weapons=20),
            )
        )
        ok, msg = engine_vulnerable.jump("rigel_o")
        self.assertTrue(ok)
        self.assertTrue(any("SPACE WEATHER HAZARD" in entry for entry in engine_vulnerable.state.ship.flight_log))
        # Shield drained by 15 MW (from 30 down to 15)
        self.assertEqual(engine_vulnerable.state.ship.shield, 15)
        # Reactor heated by +8.0
        self.assertAlmostEqual(engine_vulnerable.state.ship.reactor.heat, 8.0, places=1)


if __name__ == "__main__":
    unittest.main()
