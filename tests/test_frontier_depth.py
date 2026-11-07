"""Frontier depth: pirates, decisions, quantum freight, surface ops, populations, and UI affordances."""

from dataclasses import replace
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

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
from voidfarer.surface import SURFACE_OPERATIONS, SURFACE_OPERATION_MAP, surface_report


class FrontierContentTest(unittest.TestCase):
    def test_galaxy_has_more_systems_factions_and_anomalies(self):
        systems = GalaxyGenerator(42).generate_galaxy()
        self.assertGreaterEqual(len(systems), 31)
        self.assertGreaterEqual(len(CANONICAL_FACTIONS), 9)
        self.assertGreaterEqual(len(ANOMALIES_CATALOG), 9)
        for required in (
            "kepler", "helios", "ashen", "meridian", "vela", "lyra", "draco", "phoenix",
            "altair", "deneb", "rigel", "capella", "tau_ceti", "epsilon_eridani", "luyten", "pollux",
        ):
            self.assertIn(required, systems)
        self.assertTrue(any(system.faction == "Kepler Concord" for system in systems.values()))

    def test_every_system_has_a_deeper_planet_roster(self):
        systems = GalaxyGenerator(42).generate_galaxy()
        for system_id, system in systems.items():
            self.assertGreaterEqual(
                len(system.bodies), 7,
                f"{system_id} must keep at least seven celestial bodies",
            )
        self.assertGreaterEqual(len(systems["sol"].bodies), 8)

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

    def test_colonial_offer_triggers_at_mastery_2_without_outposts(self):
        engine = SimulationEngine(seed=42)
        mastery, _ = engine._award_pilot_xp(500, engine.state.ship.mastery)
        engine.state = engine._clone_state(ship=engine._clone_ship(mastery=mastery))
        ids = [d.id for d in eligible_decisions(engine.state, "tick")]
        self.assertIn("colonial_offer", ids)

    def test_colonial_offer_hidden_below_mastery_2(self):
        engine = SimulationEngine(seed=42)
        ids = [d.id for d in eligible_decisions(engine.state, "tick")]
        self.assertNotIn("colonial_offer", ids)

    def test_colonial_offer_hidden_once_founded(self):
        from voidfarer.models import Outpost
        engine = SimulationEngine(seed=42)
        mastery, _ = engine._award_pilot_xp(500, engine.state.ship.mastery)
        claimed = Outpost(
            id="o1", name="Mine", system_id="sol", body_id="sol_body_2",
            outpost_type="mining",
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(mastery=mastery), outposts=(claimed,)
        )
        ids = [d.id for d in eligible_decisions(engine.state, "tick")]
        self.assertNotIn("colonial_offer", ids)

    def test_accepting_colonial_offer_grants_a_colonial_contract(self):
        engine = SimulationEngine(seed=42)
        definition = next(d for d in DECISION_DEFINITIONS if d.id == "colonial_offer")
        event = make_decision_event(definition, 0, "tick")
        engine.state = engine._clone_state(pending_decision=event)
        before = len(engine.state.ship.active_contracts)
        accept = next(c for c in definition.choices if c.id == "accept")
        ok, msg = engine.resolve_decision(accept.id)
        self.assertTrue(ok, msg)
        after = engine.state.ship.active_contracts
        self.assertEqual(len(after), before + 1)
        self.assertEqual(after[-1].category, "colonial")
        self.assertGreater(
            engine.state.ship.faction_standings.get("sol_coalition", 0), 0
        )

    def test_declining_colonial_offer_grants_nothing(self):
        engine = SimulationEngine(seed=42)
        definition = next(d for d in DECISION_DEFINITIONS if d.id == "colonial_offer")
        event = make_decision_event(definition, 0, "tick")
        engine.state = engine._clone_state(pending_decision=event)
        before = len(engine.state.ship.active_contracts)
        decline = next(c for c in definition.choices if c.id == "decline")
        ok, msg = engine.resolve_decision(decline.id)
        self.assertTrue(ok, msg)
        self.assertEqual(len(engine.state.ship.active_contracts), before)
        self.assertIn(definition.id, engine.state.decision_history)

    def test_colonial_offer_opens_through_the_live_tick_path(self):
        engine = SimulationEngine(seed=42)
        engine.allow_decision_events = True
        mastery, _ = engine._award_pilot_xp(500, engine.state.ship.mastery)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(mastery=mastery),
            stats=dict(engine.state.stats, last_decision_tick=-10000),
        )
        engine.tick(1)
        pending = engine.state.pending_decision
        self.assertIsNotNone(pending, "the colonial offer must open on the live tick path")
        self.assertEqual(pending.definition_id, "colonial_offer")

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

    def test_first_decision_waits_for_the_initial_relaxed_window(self):
        engine = SimulationEngine(seed=42)
        engine.allow_decision_events = True
        definition = DECISION_DEFINITIONS[0]
        self.assertEqual(engine.decision_cadence, "relaxed")
        self.assertEqual(engine.decisions_ready_in(), 36)
        with patch("voidfarer.engine.eligible_decisions", return_value=[definition]), \
                patch.object(engine, "_stable_unit", return_value=0.0):
            self.assertIsNone(engine.maybe_trigger_decision("tick"), "tick 0 must stay quiet")
            engine.state = engine._clone_state(time=replace(engine.state.time, tick=35))
            self.assertIsNone(engine.maybe_trigger_decision("tick"), "tick 35 is still the grace window")
            engine.state = engine._clone_state(time=replace(engine.state.time, tick=36))
            self.assertIsNotNone(engine.maybe_trigger_decision("tick"),
                                 "the first prompt may open after the relaxed window")

    def test_a_failed_roll_still_consumes_the_cadence_window(self):
        engine = SimulationEngine(seed=42)
        engine.allow_decision_events = True
        definition = DECISION_DEFINITIONS[0]
        engine.state = engine._clone_state(time=replace(engine.state.time, tick=36))
        with patch("voidfarer.engine.eligible_decisions", return_value=[definition]), \
                patch.object(engine, "_stable_unit", return_value=1.0):
            self.assertIsNone(engine.maybe_trigger_decision("tick"),
                              "a failed roll must not open a prompt")
        self.assertEqual(engine.state.stats.get("last_decision_eval_tick"), 36)
        self.assertEqual(engine.decisions_ready_in(), 36,
                         "the next evaluation waits for the next relaxed window")

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
        self.assertEqual(SimulationEngine(state=engine.state).decision_cadence, "relaxed")

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
        self.assertGreaterEqual(len(report["operations"]), 8)
        ok, msg = engine.perform_surface_operation("surface_survey")
        self.assertTrue(ok, msg)
        self.assertIn(f"{body.id}:surface_survey", engine.state.ship.surface_used)
        report = engine.get_surface_report()
        survey = next(op for op in report["operations"] if op["id"] == "surface_survey")
        self.assertTrue(survey["used"])
        ok, _ = engine.perform_surface_operation("surface_survey")
        self.assertFalse(ok)

    def test_surface_catalog_is_deeper_and_body_specific(self):
        self.assertGreaterEqual(len(SURFACE_OPERATIONS), 12)
        op = SURFACE_OPERATION_MAP["cryo_drill"]
        body = next(body for body in SimulationEngine(seed=42).current_system.bodies if body.landable)
        self.assertTrue(op.available_on(replace(body, body_type="ice_world")))
        self.assertFalse(op.available_on(replace(body, body_type="lava_world")))
        self.assertTrue(any(operation.body_types for operation in SURFACE_OPERATIONS),
                        "at least one operation must be tied to a surface environment")

    def test_every_surface_operation_is_reachable_on_a_generated_world(self):
        engine = SimulationEngine(seed=42)
        reachable = set()
        for system in engine.state.systems.values():
            for body in system.bodies:
                if not body.landable:
                    continue
                ship = engine._clone_ship(landed_body_id=body.id)
                reachable.update(
                    row["id"] for row in surface_report(ship, body)["operations"]
                )
        self.assertEqual({operation.id for operation in SURFACE_OPERATIONS} - reachable, set())

    def test_ringed_giant_landing_offers_cloud_scoop_without_rover_ops(self):
        engine = SimulationEngine(seed=42)
        body = next(
            body for body in engine.current_system.bodies
            if body.body_type in ("gas_giant", "ringed_giant", "ice_giant", "methane_storm")
        )
        self.assertTrue(body.landable)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(orbiting_body_id=body.id, landed_body_id=None)
        )
        ok, message = engine.land_on_body(body.id)
        self.assertTrue(ok, message)
        ids = {row["id"] for row in engine.get_surface_report()["operations"]}
        self.assertIn("cloud_scoop", ids)
        self.assertNotIn("surface_survey", ids)

    def test_lava_world_surface_offers_magma_tap(self):
        engine = SimulationEngine(seed=42)
        body = next(
            body for system in engine.state.systems.values() for body in system.bodies
            if body.body_type in ("lava_world", "volcanic")
        )
        self.assertTrue(body.landable)
        ship = engine._clone_ship(landed_body_id=body.id)
        ids = {row["id"] for row in surface_report(ship, body)["operations"]}
        self.assertIn("magma_tap", ids)

    def test_uninhabited_gas_world_keeps_no_government_after_load_migration(self):
        engine = SimulationEngine(seed=42)
        system = engine.current_system
        body = next(
            body for body in system.bodies
            if body.body_type in ("gas_giant", "ringed_giant", "ice_giant", "methane_storm")
        )
        body = replace(
            body,
            landable=True,
            population=0,
            population_capacity=0,
            government="None",
            faction="Unclaimed",
        )
        systems = dict(engine.state.systems)
        systems[system.id] = replace(
            system,
            bodies=tuple(body if candidate.id == body.id else candidate for candidate in system.bodies),
        )
        engine.state = engine._clone_state(systems=systems)
        reloaded = SimulationEngine(state=engine.state)
        migrated = next(
            candidate for candidate in reloaded.current_system.bodies
            if candidate.id == body.id
        )
        self.assertEqual(migrated.population, 0)
        self.assertEqual(migrated.government, "None")

    def test_an_operation_for_another_environment_is_refused(self):
        engine = SimulationEngine(seed=42)
        body = next(body for body in engine.current_system.bodies if body.landable)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(orbiting_body_id=body.id, landed_body_id=body.id)
        )
        incompatible = next(
            operation for operation in SURFACE_OPERATIONS
            if operation.body_types and not operation.available_on(body)
        )
        ok, message = engine.perform_surface_operation(incompatible.id)
        self.assertFalse(ok)
        self.assertIn("not available", message)


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
