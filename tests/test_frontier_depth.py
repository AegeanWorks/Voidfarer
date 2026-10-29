"""Frontier depth: pirates, decisions, quantum freight, surface ops, populations, and UI affordances."""

from dataclasses import replace
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.decisions import DECISION_DEFINITIONS, eligible_decisions, make_decision_event
from voidfarer.engine import SimulationEngine
from voidfarer.faction_state import _devastate_system
from voidfarer.factions import CANONICAL_FACTIONS
from voidfarer.galaxy import ANOMALIES_CATALOG, GalaxyGenerator, step_population_dynamics
from voidfarer.models import AwayMission, GameState, TradeOrder
from voidfarer.pirates import generate_pirate_encounter, pirate_risk
from voidfarer.retention import generate_contract
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


class FrontierContentTest(unittest.TestCase):
    def test_galaxy_has_more_systems_factions_and_anomalies(self):
        systems = GalaxyGenerator(42).generate_galaxy()
        self.assertGreaterEqual(len(systems), 23)
        self.assertGreaterEqual(len(CANONICAL_FACTIONS), 9)
        self.assertGreaterEqual(len(ANOMALIES_CATALOG), 9)
        for required in ("kepler", "helios", "ashen", "meridian", "vela", "lyra", "draco", "phoenix"):
            self.assertIn(required, systems)
        self.assertTrue(any(system.faction == "Kepler Concord" for system in systems.values()))

    def test_populations_are_realistic_and_devastation_kills_growth(self):
        systems = GalaxyGenerator(42).generate_galaxy()
        self.assertGreaterEqual(max(body.population for system in systems.values() for body in system.bodies), 1_000_000_000)
        body = next(
            body for system in systems.values() for body in system.bodies
            if body.population > 100_000_000 and body.landable
        )
        healthy = replace(body, population=1_000_000_000, devastation=0.0)
        ruined = replace(body, population=1_000_000_000, devastation=80.0)
        self.assertGreater(step_population_dynamics(healthy, 30), healthy.population)
        self.assertLess(step_population_dynamics(ruined, 30), ruined.population)

    def test_war_capture_devastates_and_displaces_population(self):
        systems = GalaxyGenerator(42).generate_galaxy()
        system = next(
            system for system in systems.values()
            if any(body.population > 0 for body in system.bodies)
        )
        before = sum(body.population for body in system.bodies)
        import random
        devastated, lost = _devastate_system(system, random.Random(7), severity=2.0)
        after = sum(body.population for body in devastated.bodies)
        self.assertGreater(lost, 0)
        self.assertLess(after, before)
        self.assertTrue(any(body.devastation > 0 for body in devastated.bodies))

    def test_every_anomaly_has_a_power_free_escape(self):
        for anomaly in ANOMALIES_CATALOG:
            escape = [
                choice for choice in anomaly["choices"]
                if choice.get("required_power") == "none"
                and int(choice.get("min_power_threshold", 0)) <= 0
            ]
            self.assertTrue(escape, anomaly["id"])

    def test_new_state_fields_survive_save_round_trip(self):
        engine = SimulationEngine(seed=42)
        event = make_decision_event(DECISION_DEFINITIONS[0], 4, "tick")
        pirate = generate_pirate_encounter(engine.current_system, seed=7, threat_level=2)
        order = TradeOrder(
            id="freight_4_1", commodity_id="titanium", quantity=2,
            origin_system_id="sol", destination_system_id="alpha_centauri",
            destination_body_id="alpha_centauri_body_1", destination_name="Alpha Centauri A",
            fee_paid=120, created_tick=4, arrival_tick=12, unit_price_at_launch=500,
        )
        mission = AwayMission(
            id="away_4_1", mission_type="salvage_sweep", system_id="sol",
            body_id="sol_dyson_sphere", body_name="Dyson Sphere Helios",
            crew_ids=("crew_1",), started_tick=4, duration_ticks=8, risk=20,
        )
        state = engine._clone_state(
            ship=engine._clone_ship(
                away_missions=(mission,), away_completed=("sol:salvage_sweep",),
                trade_orders=(order,), surface_used=("sol_dyson_sphere:surface_survey",),
            ),
            pending_decision=event, active_pirate=pirate,
            decision_history=("colony_distress",),
        )
        restored = GameState.from_dict(state.to_dict())
        self.assertEqual(restored.pending_decision.id, event.id)
        self.assertEqual(restored.active_pirate.id, pirate.id)
        self.assertEqual(restored.decision_history, ("colony_distress",))
        self.assertEqual(restored.ship.away_missions[0].id, mission.id)
        self.assertEqual(restored.ship.away_completed, ("sol:salvage_sweep",))
        self.assertEqual(restored.ship.trade_orders[0].arrival_tick, 12)
        self.assertEqual(restored.ship.surface_used, ("sol_dyson_sphere:surface_survey",))

    def test_initial_standings_include_frontier_powers(self):
        engine = SimulationEngine(seed=42)
        for faction_id in ("kepler_concord", "helios_compact", "ashen_choir", "iron_meridian"):
            self.assertIn(faction_id, engine.state.ship.faction_standings)
            self.assertEqual(engine.state.ship.faction_standings[faction_id], 0)
        for corp_id in ("helios_forge", "choir_reliquary"):
            self.assertIn(corp_id, engine.state.ship.corp_standings)

    def test_contract_board_has_new_categories(self):
        for category in ("pirates", "delivery", "surface", "anomaly", "diplomacy"):
            contract = generate_contract(__import__("random").Random(3), category=category)
            self.assertEqual(contract.category, category)
        engine = SimulationEngine(seed=42)
        categories = {contract.category for contract in engine.state.ship.active_contracts}
        self.assertIn("trade", categories)
        self.assertIn("delivery", categories)
        self.assertEqual(len(engine.state.ship.active_contracts), 5)


class PirateEncounterTest(unittest.TestCase):
    def test_risk_rises_in_havens(self):
        system = GalaxyGenerator(42).generate_galaxy()["sol"]
        haven = GalaxyGenerator(42).generate_galaxy()["rift_station"]
        self.assertGreater(pirate_risk(haven, 0).chance, pirate_risk(system, 0).chance)

    def test_pay_fight_and_evade_paths(self):
        engine = SimulationEngine(seed=42)
        pirate = generate_pirate_encounter(engine.current_system, seed=7, threat_level=2)
        engine.state = engine._clone_state(active_pirate=pirate)
        credits = engine.state.ship.credits
        ok, msg = engine.resolve_pirate_encounter("pay")
        self.assertTrue(ok, msg)
        self.assertIsNone(engine.state.active_pirate)
        self.assertEqual(engine.state.ship.credits, credits - pirate.toll_credits)

        engine = SimulationEngine(seed=42)
        pirate = generate_pirate_encounter(engine.current_system, seed=9, threat_level=2)
        engine.state = engine._clone_state(active_pirate=pirate)
        ok, msg = engine.resolve_pirate_encounter("fight")
        self.assertTrue(ok, msg)
        self.assertIsNotNone(engine.state.active_combat)
        self.assertIsNone(engine.state.active_pirate)

        engine = SimulationEngine(seed=42)
        pirate = generate_pirate_encounter(engine.current_system, seed=11, threat_level=2)
        engine.state = engine._clone_state(active_pirate=pirate)
        ok, msg = engine.resolve_pirate_encounter("evade")
        self.assertTrue(ok, msg)
        self.assertIsNone(engine.state.active_pirate)
        self.assertLess(engine.state.ship.fuel, engine.state.ship.max_fuel + 1)


class DecisionEventTest(unittest.TestCase):
    def test_at_least_twenty_five_conditional_events(self):
        self.assertGreaterEqual(len(DECISION_DEFINITIONS), 25)
        self.assertEqual(len({definition.id for definition in DECISION_DEFINITIONS}), len(DECISION_DEFINITIONS))

    def test_pending_decision_blocks_time_until_resolved(self):
        engine = SimulationEngine(seed=42)
        definition = next(d for d in DECISION_DEFINITIONS if d.id == "colony_distress")
        event = make_decision_event(definition, 0, "tick")
        engine.state = engine._clone_state(pending_decision=event)
        tick = engine.tick(1)
        self.assertTrue(tick["blocked_by_decision"])
        self.assertEqual(tick["ticks_advanced"], 0)
        credits = engine.state.ship.credits
        choice = definition.choices[0]
        ok, msg = engine.resolve_decision(choice.id)
        self.assertTrue(ok, msg)
        self.assertIsNone(engine.state.pending_decision)
        self.assertEqual(engine.state.ship.credits, credits - 300)
        self.assertIn(definition.id, engine.state.decision_history)

    def test_decisions_are_rate_limited_by_the_cadence_window(self):
        engine = SimulationEngine(seed=42)
        engine.allow_decision_events = True
        engine.set_decision_cadence("relaxed")
        self.assertEqual(engine._decision_cooldown(), 36)
        tick = engine.state.time.tick
        engine.state = engine._clone_state(
            stats={**engine.state.stats, "last_decision_tick": tick},
        )
        self.assertEqual(engine.decisions_ready_in(), 36)
        self.assertIsNone(engine.maybe_trigger_decision("tick"), "inside the window no prompt may open")
        engine.state = engine._clone_state(
            stats={**engine.state.stats, "last_decision_tick": tick - 40},
        )
        self.assertEqual(engine.decisions_ready_in(), 0)

    def test_cadence_choices_and_snapshot(self):
        engine = SimulationEngine(seed=42)
        ok, msg = engine.set_decision_cadence("frequent")
        self.assertTrue(ok, msg)
        self.assertTrue(engine.set_decision_cadence("normal")[0])
        self.assertFalse(engine.set_decision_cadence("always")[0])
        settings = engine.get_status_snapshot()["settings"]
        self.assertEqual(settings["decision_cadence"], "normal")
        self.assertIn("relaxed", settings["decision_cadences"])

    def test_cadence_is_persisted_with_the_save(self):
        engine = SimulationEngine(seed=42)
        self.assertTrue(engine.set_decision_cadence("relaxed")[0])
        self.assertEqual(engine.state.stats.get("decision_cadence"), "relaxed")
        reloaded = SimulationEngine(state=type(engine.state).from_dict(engine.state.to_dict()))
        self.assertEqual(reloaded.decision_cadence, "relaxed")
        self.assertEqual(reloaded._decision_cooldown(), 36)
        # An unknown saved value falls back to the default instead of breaking the run.
        engine.state = engine._clone_state(stats={**engine.state.stats, "decision_cadence": "warp"})
        self.assertEqual(SimulationEngine(state=engine.state).decision_cadence, "normal")

    def test_low_hull_event_is_eligible(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(ship=engine._clone_ship(hull=10))
        eligible = eligible_decisions(engine.state, "tick")
        self.assertIn("hull_breach", {definition.id for definition in eligible})


class QuantumFreightTest(unittest.TestCase):
    def test_freight_costs_fee_arrives_later_and_progresses_delivery_contract(self):
        engine = SimulationEngine(seed=42)
        start = engine.orbiting_body
        self.assertIsNotNone(start)
        destination = next(
            system for system in engine.state.systems.values()
            if system.id != engine.current_system.id and any(body.station_dockable for body in system.bodies)
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                cargo={"titanium": 4},
                cargo_cost={"titanium": 200},
            )
        )
        credits = engine.state.ship.credits
        ok, msg = engine.place_quantum_order("titanium", 2, destination.id)
        self.assertTrue(ok, msg)
        self.assertEqual(engine.state.ship.cargo.get("titanium"), 2)
        self.assertLess(engine.state.ship.credits, credits)
        order = engine.state.ship.trade_orders[0]
        before_delivery = next(
            c for c in engine.state.ship.active_contracts if c.category == "delivery"
        )
        engine.tick(order.arrival_tick + 1)
        self.assertFalse(engine.state.ship.trade_orders)
        self.assertEqual(engine.state.stats.get("deliveries"), 1)
        after_delivery = next(
            c for c in engine.state.ship.active_contracts if c.id == before_delivery.id
        )
        self.assertGreaterEqual(after_delivery.current_count, before_delivery.current_count)

    def test_quantum_report_lists_lanes(self):
        engine = SimulationEngine(seed=42)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(cargo={"titanium": 2}, cargo_cost={"titanium": 100})
        )
        report = engine.get_quantum_trade_report()
        self.assertTrue(report["docked"])
        self.assertTrue(report["routes"])
        self.assertIn("fee", report["routes"][0])


class SurfaceOperationTest(unittest.TestCase):
    def test_landing_opens_choices_and_marks_site_branch_worked(self):
        engine = SimulationEngine(seed=42)
        body = next(body for body in engine.current_system.bodies if body.landable)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(orbiting_body_id=body.id, landed_body_id=body.id)
        )
        report = engine.get_surface_report()
        self.assertTrue(report["landed"])
        self.assertEqual(len(report["operations"]), 5)
        ok, msg = engine.perform_surface_operation("surface_survey")
        self.assertTrue(ok, msg)
        self.assertIn(f"{body.id}:surface_survey", engine.state.ship.surface_used)
        report = engine.get_surface_report()
        survey = next(op for op in report["operations"] if op["id"] == "surface_survey")
        self.assertTrue(survey["used"])
        ok, _ = engine.perform_surface_operation("surface_survey")
        self.assertFalse(ok)


class FrontierUiContractTest(unittest.TestCase):
    def test_cockpit_has_new_mechanics_surfaces(self):
        root = Path(__file__).parent.parent
        html = (root / "voidfarer" / "static" / "index.html").read_text(encoding="utf-8")
        js = (root / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")
        css = (root / "voidfarer" / "static" / "style.css").read_text(encoding="utf-8")
        for element in ("pirateCard", "decisionOverlay", "quantumFreight", "surfaceOps", "targetDevastation"):
            self.assertIn(element, html)
        for handler in ("handlePirateAction", "handleDecisionChoice", "handleQuantumOrder", "handleSurfaceOp", "renderSurfaceOps"):
            self.assertIn(handler, js)
        self.assertIn("height: auto", css)
        self.assertIn("#targetDevastation.is-devastated", css)

    def test_source_files_have_no_mojibake(self):
        root = Path(__file__).parent.parent
        paths = list((root / "voidfarer").glob("*.py"))
        paths.extend([
            root / "voidfarer" / "static" / "app.js",
            root / "voidfarer" / "static" / "index.html",
            root / "voidfarer" / "static" / "style.css",
        ])
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for marker in ("â", "Â", "Ã", "ð"):
                self.assertNotIn(marker, text, f"mojibake {marker!r} in {path.name}")
        decisions = (root / ".aikit" / "decisions.md").read_text(encoding="utf-8")
        for marker in ("â", "Â", "Ã", "ð"):
            self.assertNotIn(marker, decisions, f"mojibake {marker!r} in decisions.md")


class FrontierApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.storage = StorageManager(cls.temp_dir.name)
        VoidFarerHandler.engine = SimulationEngine(seed=42)
        VoidFarerHandler.storage = cls.storage
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def setUp(self):
        VoidFarerHandler.engine = SimulationEngine(seed=42)
        VoidFarerHandler.engine.allow_decision_events = False
        VoidFarerHandler.storage = StorageManager(self.temp_dir.name)

    def _request(self, method, path, payload=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        body = json.dumps(payload) if payload is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, json.loads(data.decode("utf-8"))

    def test_get_quantum_and_surface_report(self):
        status, data = self._request("GET", "/api/trade/quantum")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("routes", data["quantum"])
        status, data = self._request("GET", "/api/surface")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("landed", data["surface"])

    def test_refresh_contracts_endpoint(self):
        status, data = self._request("POST", "/api/contracts/refresh", {})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"], data)
        self.assertEqual(len(data["state"]["ship"]["active_contracts"]), 5)

    def test_pending_decision_blocks_and_resolves_over_rest(self):
        engine = VoidFarerHandler.engine
        definition = next(d for d in DECISION_DEFINITIONS if d.id == "colony_distress")
        event = make_decision_event(definition, 0, "tick")
        engine.state = engine._clone_state(pending_decision=event)
        status, data = self._request("POST", "/api/contracts/refresh", {})
        self.assertEqual(status, 409)
        self.assertFalse(data["ok"])
        self.assertIn("Decision required", data["message"])
        self.assertIn("pending_decision", data["state"])
        status, data = self._request("POST", "/api/decision/resolve", {"choice_id": definition.choices[0].id})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIsNone(data["state"]["pending_decision"])

    def test_pirate_resolve_endpoint(self):
        engine = VoidFarerHandler.engine
        pirate = generate_pirate_encounter(engine.current_system, seed=7, threat_level=1)
        engine.state = engine._clone_state(active_pirate=pirate)
        status, data = self._request("POST", "/api/trade", {"commodity_id": "titanium", "quantity": 1, "is_buy": True})
        self.assertEqual(status, 409)
        self.assertIn("Pirate intercept", data["message"])
        self.assertIn("active_pirate", data["state"])
        status, data = self._request("POST", "/api/pirate/resolve", {"action": "pay"})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"], data)
        self.assertIsNone(data["state"]["active_pirate"])


class PirateLockTest(unittest.TestCase):
    def test_active_pirate_blocks_tick_flight_and_trade_until_resolved(self):
        engine = SimulationEngine(seed=42)
        pirate = generate_pirate_encounter(engine.current_system, seed=13, threat_level=1)
        engine.state = engine._clone_state(active_pirate=pirate)
        blocked_tick = engine.tick(1)
        self.assertTrue(blocked_tick.get("blocked_by_encounter"))
        self.assertEqual(blocked_tick["ticks_advanced"], 0)
        ok, msg = engine.jump("alpha_centauri")
        self.assertFalse(ok)
        self.assertIn("Pirate intercept", msg)
        ok, msg = engine.start_travel("sol_body_2", mode="sublight")
        self.assertFalse(ok)
        self.assertIn("Pirate intercept", msg)
        ok, msg = engine.trade("titanium", 1, True)
        self.assertFalse(ok)
        self.assertIn("Pirate intercept", msg)
        ok, msg = engine.resolve_pirate_encounter("pay")
        self.assertTrue(ok, msg)
        self.assertIsNone(engine.state.active_pirate)
        self.assertTrue(engine.tick(1)["ticks_advanced"] > 0)

    def test_surface_cargo_reports_display_names(self):
        engine = SimulationEngine(seed=42)
        body = next(body for body in engine.current_system.bodies if body.landable)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(orbiting_body_id=body.id, landed_body_id=body.id)
        )
        report = engine.get_surface_report()
        core = next(op for op in report["operations"] if op["id"] == "core_sample")
        self.assertTrue(core["cargo"][0]["name"])
        self.assertNotEqual(core["cargo"][0]["name"], core["cargo"][0]["id"])


if __name__ == "__main__":
    unittest.main()
