"""Tests for in-system transit (TravelState), planetary civilization metadata, and cockpit GameEvents."""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from voidfarer.cli import main as cli_main
from voidfarer.engine import SimulationEngine
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import CelestialBody, GameEvent, GameState, TravelState
from voidfarer.server import ThreadedHTTPServer, VoidFarerHTTPHandler
from voidfarer.storage import StorageManager


class TestTransitCivEvents(unittest.TestCase):
    """Verify TravelState, planetary faction/population/government, and GameEvent lifecycles."""

    def setUp(self) -> None:
        self.engine = SimulationEngine(seed=42)

    def test_gamestate_roundtrip_preserves_events_travel_and_civ_metadata(self) -> None:
        travel = TravelState(
            origin_body_id="sol_body_1",
            destination_body_id="sol_body_2",
            mode="sublight",
            started_tick=2,
            arrival_tick=5,
            distance_au=2.7,
            duration_ticks=3,
        )
        self.assertAlmostEqual(travel.progress(2), 0.0)
        self.assertAlmostEqual(travel.progress(5), 1.0)

        evt = GameEvent(
            id="evt_2_1",
            kind="arrival",
            title="Orbital Capture",
            message="Arrived at Sol B.",
            tick=2,
            dismissed=False,
        )
        ship = self.engine._clone_ship(travel=travel)
        state = self.engine._clone_state(ship=ship, events=(evt,))
        restored = GameState.from_dict(state.to_dict())

        self.assertIsNotNone(restored.ship.travel)
        self.assertEqual(restored.ship.travel.destination_body_id, "sol_body_2")
        self.assertEqual(restored.ship.travel.mode, "sublight")
        self.assertEqual(len(restored.events), 1)
        self.assertEqual(restored.events[0].id, "evt_2_1")
        self.assertEqual(restored.events[0].title, "Orbital Capture")

    def test_galaxy_generates_planetary_civilization_metadata(self) -> None:
        systems = GalaxyGenerator(seed=42).generate_galaxy()
        sol = systems["sol"]
        star = sol.bodies[0]
        self.assertEqual(star.body_type, "star")
        self.assertEqual(star.population, 0)
        self.assertEqual(star.government, "None")

        inhabited = [b for b in sol.bodies[1:] if b.station_dockable or b.landable]
        self.assertTrue(len(inhabited) >= 1)
        for body in inhabited:
            self.assertGreater(body.population, 0)
            self.assertNotEqual(body.government, "None")
            self.assertNotEqual(body.faction, "Unclaimed")

    def test_sublight_transit_progresses_and_completes_on_tick(self) -> None:
        self.engine.orbit("sol_body_1")
        target_id = "sol_body_3"
        fuel_before = self.engine.state.ship.fuel

        ok, msg = self.engine.start_travel(target_id, mode="sublight")
        self.assertTrue(ok, msg)
        self.assertEqual(self.engine.state.ship.fuel, fuel_before)
        travel = self.engine.state.ship.travel
        self.assertIsNotNone(travel)
        self.assertEqual(travel.destination_body_id, target_id)
        self.assertEqual(travel.mode, "sublight")
        self.assertGreaterEqual(travel.duration_ticks, 1)

        # Advance ticks to arrival
        self.engine.tick(travel.duration_ticks)
        self.assertIsNone(self.engine.state.ship.travel)
        self.assertEqual(self.engine.state.ship.orbiting_body_id, target_id)
        self.assertTrue(any(e.kind == "arrival" for e in self.engine.state.events))

    def test_quantum_in_system_transit_consumes_fuel_and_arrives_next_tick(self) -> None:
        self.engine.orbit("sol_body_1")
        target_id = "sol_body_4"
        fuel_before = self.engine.state.ship.fuel

        ok, msg = self.engine.start_travel(target_id, mode="quantum")
        self.assertTrue(ok, msg)
        self.assertGreaterEqual(fuel_before - self.engine.state.ship.fuel, 2)
        travel = self.engine.state.ship.travel
        self.assertIsNotNone(travel)
        self.assertEqual(travel.mode, "quantum")
        self.assertEqual(travel.duration_ticks, 1)

        self.engine.tick(1)
        self.assertIsNone(self.engine.state.ship.travel)
        self.assertEqual(self.engine.state.ship.orbiting_body_id, target_id)

    def test_start_travel_validation_guards(self) -> None:
        ok_bad_body, _ = self.engine.start_travel("nonexistent_body", mode="sublight")
        self.assertFalse(ok_bad_body)

        ok_bad_mode, _ = self.engine.start_travel("sol_body_2", mode="wormhole")
        self.assertFalse(ok_bad_mode)

        # Insufficient fuel for quantum transit
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fuel=0)
        )
        ok_no_fuel, _ = self.engine.start_travel("sol_body_4", mode="quantum")
        self.assertFalse(ok_no_fuel)

    def test_travel_preview_reports_eta_fuel_and_risk(self) -> None:
        self.engine.orbit("sol_body_1")
        ok_s, sub = self.engine.preview_travel("sol_body_3", mode="sublight")
        self.assertTrue(ok_s)
        self.assertIsInstance(sub, dict)
        self.assertEqual(sub["fuel_cost"], 0)
        self.assertGreaterEqual(sub["duration_ticks"], 1)
        self.assertGreaterEqual(sub["risk"], 0.01)
        self.assertIn("hazards", sub)
        self.assertTrue(sub["can_start"])

        ok_q, quantum = self.engine.preview_travel("sol_body_3", mode="quantum")
        self.assertTrue(ok_q)
        self.assertGreaterEqual(quantum["fuel_cost"], 2)
        self.assertEqual(quantum["duration_ticks"], 1)
        self.assertLessEqual(quantum["risk"], sub["risk"] + 0.001)

        ok_same, same = self.engine.preview_travel("sol_body_1", mode="sublight")
        self.assertTrue(ok_same)
        self.assertFalse(same["can_start"])
        self.assertIn("Already in orbit", same["blocked_reason"])

    def test_transit_hazard_applies_damage_delay_and_event(self) -> None:
        self.engine.orbit("sol_body_1")
        effects = {
            "fuel_mult": 1.0,
            "scan_mult": 1.0,
            "encounter_mult": 1.0,
            "sensor_mult": 1.0,
            "heat_mult": 1.0,
            "cooling_bonus": 0.0,
            "trade_margin": 0.0,
            "relic_find": 0.0,
            "evasion": 0.0,
            "hull_hazard": 1.0,
        }
        with patch.object(self.engine, "_map_effects", return_value=effects), \
                patch.object(self.engine.rng, "random", return_value=0.0):
            ok_plan, plan = self.engine.preview_travel("sol_body_3", mode="sublight")
            before_hull = self.engine.state.ship.hull
            before_shield = self.engine.state.ship.shield
            ok, message = self.engine.start_travel("sol_body_3", mode="sublight")
            travel = self.engine.state.ship.travel
            hull_after = self.engine.state.ship.hull
            shield_after = self.engine.state.ship.shield

        self.assertTrue(ok_plan)
        self.assertTrue(ok, message)
        self.assertIn("TRANSIT HAZARD", message)
        self.assertIsNotNone(travel)
        self.assertEqual(travel.duration_ticks, plan["duration_ticks"] + 1)
        self.assertLessEqual(hull_after, before_hull)
        self.assertLessEqual(shield_after, before_shield)
        self.assertTrue(any(event.kind == "hazard" for event in self.engine.state.events))

    def test_start_travel_rejects_same_body_and_active_transit(self) -> None:
        self.engine.orbit("sol_body_1")
        ok_same, msg_same = self.engine.start_travel("sol_body_1", mode="sublight")
        self.assertFalse(ok_same)
        self.assertIn("Already in orbit", msg_same)

        ok_start, msg_start = self.engine.start_travel("sol_body_3", mode="sublight")
        self.assertTrue(ok_start, msg_start)
        ok_second, msg_second = self.engine.start_travel("sol_body_4", mode="quantum")
        self.assertFalse(ok_second)
        self.assertIn("Already in transit", msg_second)

    def test_event_emission_and_dismissal(self) -> None:
        evt = self.engine.emit_event("alert", "Test Alert", "Hull integrity warning.")
        snap = self.engine.get_status_snapshot()
        self.assertEqual(len(snap["undismissed_events"]), 1)
        self.assertEqual(snap["undismissed_events"][0]["id"], evt.id)

        ok, _ = self.engine.dismiss_event(evt.id)
        self.assertTrue(ok)
        snap_after = self.engine.get_status_snapshot()
        self.assertEqual(len(snap_after["undismissed_events"]), 0)

    def test_cli_and_cockpit_surface_for_travel_and_events(self) -> None:
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        save_path = Path(tmp_dir.name) / "save.json"

        rc_travel = cli_main(["--save-path", str(save_path), "travel", "sol_body_2", "--mode", "sublight"])
        self.assertEqual(rc_travel, 0)

        rc_events = cli_main(["--save-path", str(save_path), "events", "list"])
        self.assertEqual(rc_events, 0)

        static_dir = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
        html = (static_dir / "index.html").read_text(encoding="utf-8")
        js = (static_dir / "app.js").read_text(encoding="utf-8")
        self.assertIn("targetFaction", html)
        self.assertIn("targetPopulation", html)
        self.assertIn("targetGovernment", html)
        self.assertIn("btnOrbitTarget", html)
        self.assertIn("btnQuantumTarget", html)
        self.assertNotIn("btnSublightTarget", html)
        self.assertIn("eventPopupContainer", html)
        self.assertIn("/api/travel", js)
        self.assertNotIn("handleOrbitAction", js)
        self.assertNotIn('fetch("/api/orbit"', js)
        self.assertIn("/api/events/dismiss", js)

    def test_scientifically_accurate_planetary_physics_and_habitability(self) -> None:
        from voidfarer.galaxy import compute_habitability_index, compute_scientific_planet_properties

        systems = GalaxyGenerator(seed=42).generate_galaxy()
        all_planets = [b for s in systems.values() for b in s.bodies[1:]]
        self.assertGreater(len(all_planets), 40)

        for sys_obj in systems.values():
            star = sys_obj.bodies[0]
            self.assertEqual(star.habitability, 0.0)
            for b in sys_obj.bodies[1:]:
                self.assertGreaterEqual(b.habitability, 0.0)
                self.assertLessEqual(b.habitability, 100.0)
                if b.body_type in ("terrestrial", "oceanic", "savanna"):
                    self.assertIn("N2", b.atmosphere)
                    self.assertIn("O2", b.atmosphere)
                    self.assertIn("atm", b.atmosphere)
                    self.assertGreaterEqual(b.gravity, 0.65)
                    self.assertLessEqual(b.gravity, 1.35)
                    self.assertGreaterEqual(b.temperature_c, -15)
                    self.assertLessEqual(b.temperature_c, 55)
                    self.assertGreaterEqual(b.habitability, 65.0)
                elif b.body_type in ("gas_giant", "ringed_giant"):
                    self.assertIn("H2", b.atmosphere)
                    self.assertIn("He", b.atmosphere)
                    self.assertGreaterEqual(b.radius_km, 50000.0)
                    self.assertEqual(b.habitability, 0.0)
                elif b.body_type == "methane_storm":
                    self.assertIn("CH4", b.atmosphere)
                    self.assertGreaterEqual(b.radius_km, 20000.0)
                    self.assertLessEqual(b.radius_km, 30000.0)
                    self.assertEqual(b.habitability, 0.0)
                elif b.body_type == "asteroid_belt":
                    self.assertLessEqual(b.gravity, 0.15)
                    self.assertLessEqual(b.habitability, 5.0)
                elif b.body_type == "lava_world":
                    self.assertGreaterEqual(b.temperature_c, 500)
                    self.assertEqual(b.habitability, 0.0)

        # Closer orbit around an O-type star vs far orbit around an M-type star on airless barren worlds
        hot_barren = compute_scientific_planet_properties("barren", "O", 1.2, 3500.0, 1.0, 0)
        cold_barren = compute_scientific_planet_properties("barren", "M", 6.5, 3500.0, 1.0, 0)
        self.assertGreater(hot_barren["temperature_c"], cold_barren["temperature_c"])
        self.assertGreaterEqual(compute_habitability_index("terrestrial", 1.0, 18, "N2 78%, O2 21% (1.0 atm)", ()), 85.0)

    def test_legacy_save_backfills_scientific_physics_and_habitability(self) -> None:
        from dataclasses import replace

        sol = self.engine.state.systems["sol"]
        legacy_body = replace(
            sol.bodies[1],
            body_type="terrestrial",
            atmosphere="breathable",
            gravity=2.5,
            temperature_c=0,
            habitability=0.0,
        )
        legacy_sol = replace(sol, bodies=(sol.bodies[0], legacy_body, *sol.bodies[2:]))
        legacy_systems = dict(self.engine.state.systems)
        legacy_systems["sol"] = legacy_sol
        legacy_state = self.engine._clone_state(systems=legacy_systems)

        reloaded_engine = SimulationEngine(seed=42, state=legacy_state)
        upgraded_body = reloaded_engine.state.systems["sol"].bodies[1]
        self.assertGreater(upgraded_body.habitability, 65.0)
        self.assertIn("N2", upgraded_body.atmosphere)
        self.assertLessEqual(upgraded_body.gravity, 1.35)

    def test_sublight_transit_calculates_2d_euclidean_distance_and_appropriate_ticks(self) -> None:
        import math
        from dataclasses import replace
        from voidfarer.models import ShipPower

        sol = self.engine.state.systems["sol"]
        b1 = replace(sol.bodies[1], orbit_radius=2.0, current_angle=0.0)
        b2 = replace(sol.bodies[2], orbit_radius=6.0, current_angle=math.pi)
        custom_sol = replace(sol, bodies=(sol.bodies[0], b1, b2, *sol.bodies[3:]))
        systems = dict(self.engine.state.systems)
        systems["sol"] = custom_sol
        paused_time = replace(self.engine.state.time, is_paused=True)
        low_eng_ship = self.engine._clone_ship(
            orbiting_body_id=b1.id,
            power=ShipPower(engines=10, shields=30, sensors=30, weapons=30),
        )
        self.engine.state = self.engine._clone_state(
            systems=systems,
            ship=low_eng_ship,
            time=paused_time,
        )

        ok, _ = self.engine.start_travel(b2.id, mode="sublight")
        self.assertTrue(ok)
        travel_low = self.engine.state.ship.travel
        self.assertIsNotNone(travel_low)
        # 2D Euclidean distance between (r=2, theta=0) and (r=6, theta=pi) is 8.0 AU (not |6-2|=4.0 AU)
        self.assertAlmostEqual(travel_low.distance_au, 8.0, places=1)
        self.assertFalse(self.engine.state.time.is_paused)
        self.assertGreaterEqual(travel_low.duration_ticks, 10)

        # High engine power reduces sublight duration_ticks for the same 8.0 AU distance
        high_eng_ship = self.engine._clone_ship(
            orbiting_body_id=b1.id,
            travel=None,
            power=ShipPower(engines=75, shields=10, sensors=10, weapons=5),
        )
        self.engine.state = self.engine._clone_state(ship=high_eng_ship)
        ok_high, _ = self.engine.start_travel(b2.id, mode="sublight")
        self.assertTrue(ok_high)
        travel_high = self.engine.state.ship.travel
        self.assertIsNotNone(travel_high)
        self.assertAlmostEqual(travel_high.distance_au, 8.0, places=1)
        self.assertLess(travel_high.duration_ticks, travel_low.duration_ticks)

    def test_cockpit_persistent_transit_animation_and_habitability_display(self) -> None:
        static_dir = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
        html = (static_dir / "index.html").read_text(encoding="utf-8")
        js = (static_dir / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="targetHabitability"', html)
        self.assertIn("this.targetHabitability", js)
        self.assertIn("calculateBodyDistanceAu", js)
        self.assertIn("isTickSynced", js)
        self.assertIn("!activeTravel && !this.travelAnimation", js)


if __name__ == "__main__":
    unittest.main()



