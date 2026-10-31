"""Regression tests for the Windows high-DPI cockpit, derelict salvage,
fuel scooping, and crew training drills."""

import unittest
from dataclasses import replace
from pathlib import Path

from voidfarer.engine import SimulationEngine
from voidfarer.exploration import (
    crew_training_cost,
    derive_derelict,
    scoop_profile,
    scoop_yield,
)
from voidfarer.models import CelestialBody

STATIC_DIR = Path(__file__).parent.parent / "voidfarer" / "static"
INDEX_HTML = STATIC_DIR / "index.html"
STYLE_CSS = STATIC_DIR / "style.css"
APP_JS = STATIC_DIR / "app.js"


class TestAdaptiveCockpitAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_css_declares_windows_desktop_profiles(self):
        for marker in (
            "@media (min-width: 2200px)",
            "@media (max-width: 1599px)",
            "@media (max-height: 720px)",
            "prefers-reduced-motion",
            "data-density",
        ):
            self.assertIn(marker, self.css, f"missing desktop CSS marker: {marker}")
        for forbidden in ("@media (max-width: 760px)", "@media (max-width: 480px)",
                          "env(safe-area-inset"):
            self.assertNotIn(forbidden, self.css, f"mobile CSS path returned: {forbidden}")

    def test_settings_expose_density_and_scale(self):
        for marker in ("settingDensity", "settingUiScale", "viewportReadout"):
            self.assertIn(f'id="{marker}"', self.html)

    def test_radar_is_dpi_aware_and_mouse_ready(self):
        for marker in (
            "devicePixelRatio",
            "ResizeObserver",
            "wheel",
            "mousedown",
            "this.viewW",
        ):
            self.assertIn(marker, self.js, f"missing desktop radar marker: {marker}")
        for forbidden in ("touchstart", "touchmove", "pinch"):
            self.assertNotIn(forbidden, self.js, f"touch path returned: {forbidden}")

    def test_polling_and_hotkeys_are_guarded(self):
        for marker in ("refreshInFlight", "visibilitychange", "document.hidden", "isTypingTarget"):
            self.assertIn(marker, self.js, f"missing runtime guard: {marker}")


class TestSalvageModelsAndCatalog(unittest.TestCase):
    def test_legacy_body_payload_defaults_salvage_flag(self):
        legacy = CelestialBody(id="b1", name="B", body_type="ice_world", orbit_radius=1.0).to_dict()
        legacy.pop("salvage_claimed", None)
        restored = CelestialBody.from_dict(legacy)
        self.assertFalse(restored.salvage_claimed)

    def test_derelict_generation_is_deterministic(self):
        engine = SimulationEngine(seed=42)
        system = engine.current_system
        body = next(b for b in system.bodies if b.id == "sol_body_2")
        first = derive_derelict(system.id, system.seed, body)
        second = derive_derelict(system.id, system.seed, body)
        self.assertEqual(first, second)

    def test_stations_never_generate_derelicts(self):
        engine = SimulationEngine(seed=42)
        system = engine.current_system
        station = next(b for b in system.bodies if b.station_dockable)
        self.assertIsNone(derive_derelict(system.id, system.seed, station))

    def test_sol_has_at_least_one_salvage_site(self):
        engine = SimulationEngine(seed=42)
        system = engine.current_system
        sites = [derive_derelict(system.id, system.seed, b) for b in system.bodies]
        self.assertTrue(any(site is not None for site in sites))


class TestExplorationMechanics(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def _derelict_body(self):
        system = self.engine.current_system
        for body in system.bodies:
            if derive_derelict(system.id, system.seed, body):
                return body
        self.skipTest("seed produced no salvage site")

    def test_salvage_rewards_cargo_and_claims_site(self):
        body = self._derelict_body()
        self.engine.orbit(body.id)
        site = derive_derelict(self.engine.current_system.id, self.engine.current_system.seed, body)
        credits_before = self.engine.state.ship.credits
        ok, msg, report = self.engine.salvage_derelict()
        self.assertTrue(ok, msg)
        self.assertEqual(report["site"]["body_id"], body.id)
        self.assertGreaterEqual(self.engine.state.ship.credits, credits_before + site.credits)
        claimed = next(b for b in self.engine.current_system.bodies if b.id == body.id)
        self.assertTrue(claimed.salvage_claimed)
        self.assertEqual(self.engine.state.stats.get("salvage", 0), 1)
        ok, _, _ = self.engine.salvage_derelict()
        self.assertFalse(ok)

    def test_salvage_requires_a_derelict(self):
        body = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(body.id)
        ok, msg, _ = self.engine.salvage_derelict()
        self.assertFalse(ok)
        self.assertIn("derelict", msg.lower())

    def test_fuel_scoop_refuels_and_heats_reactor(self):
        star = next(b for b in self.engine.current_system.bodies if b.body_type == "star")
        self.engine.orbit(star.id)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fuel=1)
        )
        heat_before = self.engine.state.ship.reactor.heat
        ok, msg = self.engine.scoop_fuel()
        self.assertTrue(ok, msg)
        self.assertGreater(self.engine.state.ship.fuel, 1)
        self.assertGreater(self.engine.state.ship.reactor.heat, heat_before)
        self.assertGreater(scoop_yield(star, 25, 1), 0)

    def test_fuel_scoop_requires_a_scoopable_body(self):
        station = next(b for b in self.engine.current_system.bodies if b.station_dockable)
        self.engine.orbit(station.id)
        self.assertIsNone(scoop_profile(station))
        ok, _ = self.engine.scoop_fuel()
        self.assertFalse(ok)

    def test_scoop_yield_scales_with_science_skill(self):
        star = next(b for b in self.engine.current_system.bodies if b.body_type == "star")
        base_yield = scoop_yield(star, 25.0, 0.0)
        trained_yield = scoop_yield(star, 25.0, 0.35)
        self.assertGreater(trained_yield, base_yield)

    def test_snapshot_exposes_salvage_and_scoop_hints(self):
        body = self._derelict_body()
        self.engine.orbit(body.id)
        snapshot = self.engine.get_status_snapshot()
        self.assertIsNotNone(snapshot["salvage_site"])
        self.assertEqual(snapshot["salvage_site"]["body_id"], body.id)
        star = next(b for b in self.engine.current_system.bodies if b.body_type == "star")
        self.engine.orbit(star.id)
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(fuel=1))
        self.assertIsNotNone(self.engine.get_status_snapshot()["scoop"])
        self.assertTrue(self.engine.get_status_snapshot()["scoop"]["available"])

    def test_crew_drill_raises_skill_and_spends_credits(self):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=5000))
        member = self.engine.state.ship.crew[0]
        cost = crew_training_cost(member)
        credits_before = self.engine.state.ship.credits
        ok, msg = self.engine.train_crew_member(member.id)
        self.assertTrue(ok, msg)
        raised = next(c for c in self.engine.state.ship.crew if c.id == member.id)
        self.assertEqual(raised.skill, member.skill + 1)
        self.assertEqual(self.engine.state.ship.credits, credits_before - cost)

    def test_crew_drill_caps_skill(self):
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(credits=99999))
        member = self.engine.state.ship.crew[0]
        crew = tuple(
            c if c.id != member.id else replace(c, skill=10)
            for c in self.engine.state.ship.crew
        )
        self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(crew=crew))
        ok, msg = self.engine.train_crew_member(member.id)
        self.assertFalse(ok)
        self.assertIn("maximum", msg.lower())


class TestNewMechanicWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.server = (STATIC_DIR.parent / "server.py").read_text(encoding="utf-8")
        cls.cli = (STATIC_DIR.parent / "cli.py").read_text(encoding="utf-8")

    def test_api_and_cli_expose_the_new_mechanics(self):
        for path in ("/api/salvage", "/api/scoop", "/api/crew/train"):
            self.assertIn(path, self.server)
        for command in ("salvage", "scoop"):
            self.assertIn(f'"{command}"', self.cli)

    def test_cockpit_exposes_new_action_buttons(self):
        for marker in ("btnSalvageTarget", "btnScoopFuel", "data-train-crew"):
            self.assertTrue(marker in self.html or marker in self.js, f"missing cockpit hook: {marker}")


if __name__ == "__main__":
    unittest.main()
