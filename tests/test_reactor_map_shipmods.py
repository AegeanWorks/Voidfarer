"""Regression tests for reactor simulation, sector map modifiers, and ship modifications."""

import contextlib
import io
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer.cli import main
from voidfarer.engine import SimulationEngine
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.storage import StorageManager
from voidfarer.mapmods import (
    MAP_MODIFIER_MAP,
    aggregate_map_modifiers,
    generate_map_modifiers,
)
from voidfarer.models import MapModifier, ReactorState, ShipState, StarSystem
from voidfarer.reactor import reactor_output_efficiency
from voidfarer.shipmods import CATALOG_SHIP_MODS, SHIP_MOD_SLOTS, slot_code, slot_label


class ReactorSimulationTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_reactor_state_round_trip(self):
        reactor = ReactorState(heat=42.5, integrity=88.0, mode="overdrive", last_vent_tick=7)
        restored = ReactorState.from_dict(reactor.to_dict())
        self.assertEqual(restored.heat, 42.5)
        self.assertEqual(restored.integrity, 88.0)
        self.assertEqual(restored.mode, "overdrive")
        self.assertEqual(restored.last_vent_tick, 7)

    def test_ship_state_round_trip_preserves_reactor_and_mods(self):
        ship = self.engine.state.ship
        updated = replace(
            ship,
            reactor=ReactorState(heat=30.0, integrity=90.0, mode="economy"),
            ship_mods={"frame": "reinforced_spine"},
        )
        restored = ShipState.from_dict(updated.to_dict())
        self.assertEqual(restored.reactor.mode, "economy")
        self.assertEqual(restored.reactor.heat, 30.0)
        self.assertEqual(restored.ship_mods, {"frame": "reinforced_spine"})

    def test_overdrive_heats_core_and_economy_recovers(self):
        ok, _ = self.engine.set_reactor_mode("overdrive")
        self.assertTrue(ok)
        for _ in range(10):
            self.engine.tick(1)
        hot = self.engine.state.ship.reactor.heat
        self.assertGreater(hot, 10.0)

        self.engine.set_reactor_mode("economy")
        for _ in range(15):
            self.engine.tick(1)
        self.assertLess(self.engine.state.ship.reactor.heat, hot)

    def test_vent_purges_heat_and_enforces_cooldown(self):
        self.engine.set_reactor_mode("overdrive")
        for _ in range(8):
            self.engine.tick(1)
        before = self.engine.state.ship.reactor.heat
        ok, _ = self.engine.vent_reactor_coolant()
        self.assertTrue(ok)
        self.assertLess(self.engine.state.ship.reactor.heat, before)

        ok_again, msg = self.engine.vent_reactor_coolant()
        self.assertFalse(ok_again)
        self.assertIn("recharging", msg)

    def test_heat_derates_effective_subsystem_power(self):
        ship = self.engine.state.ship
        nominal = self.engine._effective_power("weapons", ship)
        hot_ship = replace(ship, reactor=replace(ship.reactor, heat=95.0))
        derated = self.engine._effective_power("weapons", hot_ship)
        self.assertLess(derated, nominal)
        self.assertLess(reactor_output_efficiency(hot_ship.reactor), 1.0)

    def test_reactor_repair_requires_dock(self):
        undocked = self.engine._clone_ship(orbiting_body_id=None)
        self.engine.state = self.engine._clone_state(ship=undocked)
        ok, msg = self.engine.repair_reactor()
        self.assertFalse(ok)
        self.assertIn("Dock", msg)

    def test_reactor_report_exposes_modes_and_cooling(self):
        report = self.engine.get_reactor_report()
        self.assertIn("balanced", report["modes"])
        self.assertIn("overdrive", report["modes"])
        self.assertGreater(report["cooling"], 0.0)


class MapModifierTest(unittest.TestCase):
    def test_map_modifier_round_trip(self):
        modifier = MAP_MODIFIER_MAP["ion_storm"]
        restored = MapModifier.from_dict(modifier.to_dict())
        self.assertEqual(restored.id, "ion_storm")
        self.assertEqual(restored.effects, modifier.effects)

    def test_star_system_round_trip_preserves_modifiers(self):
        star = MapModifier(id="test", name="Test", category="hazard", description="Test", effects={})
        body = self.engine_body()
        system = StarSystem(
            id="sys", name="Sys", seed=1, x=0.0, y=0.0, spectral_type="G",
            color="#fff", security=0.5, faction="Test", bodies=(body,), modifiers=(star,),
        )
        restored = StarSystem.from_dict(system.to_dict())
        self.assertEqual(len(restored.modifiers), 1)
        self.assertEqual(restored.modifiers[0].id, "test")

    @staticmethod
    def engine_body():
        engine = SimulationEngine(seed=42)
        return engine.current_system.bodies[0]

    def test_generation_is_deterministic_and_non_empty(self):
        first = GalaxyGenerator(seed=42).generate_galaxy()
        second = GalaxyGenerator(seed=42).generate_galaxy()
        first_mods = {sid: tuple(m.id for m in s.modifiers) for sid, s in first.items()}
        second_mods = {sid: tuple(m.id for m in s.modifiers) for sid, s in second.items()}
        self.assertEqual(first_mods, second_mods)
        self.assertTrue(any(first_mods.values()))

    def test_aggregate_combines_multiplicative_and_additive_effects(self):
        ion = MAP_MODIFIER_MAP["ion_storm"]
        nebula = MAP_MODIFIER_MAP["nebula_drift"]
        system = StarSystem(
            id="sys", name="Sys", seed=1, x=0.0, y=0.0, spectral_type="G",
            color="#fff", security=0.2, faction="Test", bodies=(), modifiers=(ion, nebula),
        )
        effects = aggregate_map_modifiers(system)
        self.assertAlmostEqual(effects["scan_mult"], ion.effects["scan_mult"] * nebula.effects["scan_mult"])
        self.assertAlmostEqual(effects["cooling_bonus"], ion.effects["cooling_bonus"] + nebula.effects["cooling_bonus"])

    def test_map_modifier_generation_uses_seed(self):
        a = generate_map_modifiers(42, "sol", 1.0, 0)
        b = generate_map_modifiers(42, "sol", 1.0, 0)
        c = generate_map_modifiers(43, "sol", 1.0, 0)
        self.assertEqual(tuple(m.id for m in a), tuple(m.id for m in b))
        self.assertNotEqual(tuple(m.id for m in a), tuple(m.id for m in c))


class ShipModificationTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(self.station.id)
        self.baseline_hull = self.engine.state.ship.max_hull
        self.baseline_cargo = self.engine.state.ship.cargo_capacity

    def test_catalog_declares_valid_slots_and_effects(self):
        self.assertGreaterEqual(len(CATALOG_SHIP_MODS), 8)
        for mod in CATALOG_SHIP_MODS:
            self.assertIn(mod.slot, {"frame", "reactor_core", "thermal", "drive", "ops"})
            self.assertTrue(mod.effects)

    def test_install_and_remove_mod_recomputes_capacities(self):
        ok, _ = self.engine.install_ship_mod("reinforced_spine")
        self.assertTrue(ok)
        ship = self.engine.state.ship
        self.assertEqual(ship.ship_mods["frame"], "reinforced_spine")
        self.assertEqual(ship.max_hull, self.baseline_hull + 60)
        self.assertEqual(ship.cargo_capacity, self.baseline_cargo - 10)

        ok, _ = self.engine.remove_ship_mod("frame")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.max_hull, self.baseline_hull)
        self.assertEqual(self.engine.state.ship.cargo_capacity, self.baseline_cargo)

    def test_remove_rejects_module_id_that_is_not_installed(self):
        ok, _ = self.engine.install_ship_mod("reinforced_spine")
        self.assertTrue(ok)
        ok, msg = self.engine.remove_ship_mod("frame", expected_mod_id="expanded_hangar")
        self.assertFalse(ok)
        self.assertIn("not installed", msg.lower())
        self.assertEqual(self.engine.state.ship.ship_mods["frame"], "reinforced_spine")

    def test_slot_conflict_rejected(self):
        self.assertTrue(self.engine.install_ship_mod("reinforced_spine")[0])
        ok, msg = self.engine.install_ship_mod("expanded_hangar")
        self.assertFalse(ok)
        self.assertIn("already contains", msg)

    def test_overcharged_core_raises_reactor_output(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=10000)
        )
        ok, _ = self.engine.install_ship_mod("overcharged_core")
        self.assertTrue(ok)
        report = self.engine.get_reactor_report()
        self.assertGreater(report["efficiency"], 1.0)

    def test_ship_mods_require_dock(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id=None)
        )
        ok, msg = self.engine.install_ship_mod("reinforced_spine")
        self.assertFalse(ok)
        self.assertIn("Dock", msg)

    def test_ship_mod_report_lists_catalog_and_bonuses(self):
        report = self.engine.get_ship_mod_report()
        self.assertEqual(report["installed"], {})
        self.assertTrue(report["catalog"])
        self.assertIn("frame", report["slots"])

    def test_upgrade_recompute_preserves_ship_mod_capacities(self):
        self.assertTrue(self.engine.install_ship_mod("reinforced_spine")[0])
        hull_with_mod = self.engine.state.ship.max_hull
        cargo_with_mod = self.engine.state.ship.cargo_capacity
        ok, _ = self.engine.buy_upgrade("cargo_expansion_mk1")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.max_hull, hull_with_mod)
        self.assertEqual(self.engine.state.ship.cargo_capacity, cargo_with_mod + 10)

    def test_snapshot_exposes_reactor_map_and_ship_mods(self):
        snapshot = self.engine.get_status_snapshot()
        self.assertIn("reactor", snapshot)
        self.assertIn("modes", snapshot["reactor"])
        self.assertIn("map_modifiers", snapshot)
        self.assertIn("ship_mods", snapshot)
        self.assertIn("catalog", snapshot["ship_mods"])


class NewCLIAndCockpitWiringTest(unittest.TestCase):
    def test_cli_runs_new_simulation_commands(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = str(Path(temp_dir) / "save.json")
            for argv in (
                ["--save-path", save_path, "reactor", "status"],
                ["--save-path", save_path, "mapmods"],
                ["--save-path", save_path, "refit", "list"],
                ["--save-path", save_path, "simulation"],
            ):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(argv)
                self.assertEqual(code, 0, buffer.getvalue())

    def test_cockpit_contains_ship_mod_and_reactor_controls(self):
        static = Path(__file__).parent.parent / "voidfarer" / "static"
        html = (static / "index.html").read_text(encoding="utf-8")
        script = (static / "app.js").read_text(encoding="utf-8")
        for element_id in (
            "tabBtnShip",
            "tabContentShip",
            "shipVisual",
            "shipModulesGrid",
            "shipStatsPanel",
            "reactorHeatFill",
            "reactorOutputLabel",
            "reactorModeRow",
            "btnVentReactor",
            "sectorModsStrip",
        ):
            self.assertIn(f'id="{element_id}"', html)
        for symbol in (
            "renderShip",
            "/api/ship/module",
            "/api/reactor/mode",
            "/api/reactor/vent",
        ):
            self.assertIn(symbol, script)


class ShipDossierLegibilityTest(unittest.TestCase):
    """The 48px silhouette cases and the narrow catalog rows must stay readable."""

    @classmethod
    def setUpClass(cls):
        cls.static = Path(__file__).parent.parent / "voidfarer" / "static"
        cls.css = (cls.static / "style.css").read_text(encoding="utf-8")
        cls.js = (cls.static / "app.js").read_text(encoding="utf-8")

    def test_every_slot_has_a_code_that_fits_the_case(self):
        for slot in SHIP_MOD_SLOTS:
            code = slot_code(slot)
            self.assertTrue(code)
            self.assertLessEqual(len(code), 4)
            self.assertEqual(code, code.upper())
            self.assertNotIn("_", code)
        self.assertEqual(slot_code("reactor_core"), "CORE")
        self.assertEqual(slot_label("thermal"), "Thermal Control")

    def test_report_ships_slot_codes_to_the_cockpit(self):
        engine = SimulationEngine(state=StorageManager(Path(tempfile.mkdtemp()) / "save").load())
        report = engine.get_ship_mod_report()
        self.assertEqual(set(report["slot_codes"]), set(SHIP_MOD_SLOTS))
        self.assertEqual(report["slot_codes"]["ops"], "OPS")

    def test_status_snapshot_also_carries_the_slot_codes(self):
        engine = SimulationEngine(state=StorageManager(Path(tempfile.mkdtemp()) / "save").load())
        snapshot = engine.get_status_snapshot()
        self.assertEqual(snapshot["ship_mods"]["slot_codes"]["reactor_core"], "CORE")

    def test_silhouette_cases_show_the_code_and_a_real_wrench_glyph(self):
        self.assertIn("const codes = report.slot_codes || {};", self.js)
        self.assertIn("this.escapeHtml(code)", self.js)
        self.assertNotIn('<span class="ship-module-icon">?</span>', self.js)
        self.assertIn('<span class="ship-module-icon">🛠</span>', self.js)
        self.assertIn('slotDiv.setAttribute("aria-label"', self.js)

    def test_catalog_names_wrap_instead_of_losing_words(self):
        self.assertRegex(
            self.css,
            r"\.ship-module-info strong \{[^}]*white-space: normal[^}]*overflow-wrap: anywhere",
            re.S,
        )
        self.assertRegex(
            self.css,
            r"\.ship-module-name \{[^}]*font-size: 11px[^}]*text-overflow: clip",
            re.S,
        )

    def test_research_rows_align_their_cost_and_start_button(self):
        self.assertRegex(
            self.css,
            r"\.research-projects \.research-row \{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) 54px auto",
            re.S,
        )
        self.assertIn(".research-projects .research-row > button { justify-self: end;", self.css)



if __name__ == "__main__":
    unittest.main()
