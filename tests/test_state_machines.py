"""Canonical state-machine registry, inspector, gate and surface tests."""

from __future__ import annotations

import contextlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer import cli
from voidfarer.engine import SimulationEngine
from voidfarer.models import (
    AICaptain,
    AnomalyChoice,
    AnomalyEncounter,
    CombatEncounter,
    CrewMember,
    CustomsEncounter,
    DecisionChoice,
    DecisionEvent,
    GameEvent,
    PirateEncounter,
    ReactorState,
    ResearchState,
    TradeOrder,
    TravelState,
    VoidTraversalState,
)
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.state_machines import MACHINES, catalog, inspect_state, situation
from voidfarer.storage import StorageManager


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


def _combat(hull: int = 60, shield: int = 0) -> CombatEncounter:
    return CombatEncounter(
        id="combat_1",
        enemy_name="Void Raider",
        enemy_class="Raider",
        enemy_hull=hull,
        enemy_max_hull=200,
        enemy_damage=8,
        bounty_credits=120,
        enemy_shield=shield,
        enemy_max_shield=80,
        enemy_intent="fire",
    )


def _anomaly() -> AnomalyEncounter:
    return AnomalyEncounter(
        id="anomaly_1",
        title="Gravitic Rift",
        description="A tear in local space.",
        severity="minor",
        choices=(
            AnomalyChoice(
                choice_id="harvest",
                text="Harvest the rift",
                required_power="none",
                min_power_threshold=0,
                outcome_text="The rift yields salvage.",
            ),
        ),
    )


def _pirate() -> PirateEncounter:
    return PirateEncounter(
        id="pirate_1",
        band_name="Crimson Corsairs",
        ship_class="Raider",
        system_id="sol",
        system_name="Sol System",
        toll_credits=150,
        threat=2,
        description="A raider blocks the lane.",
    )


def _customs() -> CustomsEncounter:
    return CustomsEncounter(
        id="customs_1",
        faction="Sol Coalition",
        system_id="sol",
        system_name="Sol System",
        patrol_vessel="Patrol Cutter",
        contraband_found={"slaves": 2},
        fine_amount=300,
        bribe_amount=120,
        description="Scanners locked on illicit cargo.",
    )


def _decision() -> DecisionEvent:
    return DecisionEvent(
        id="decision_1",
        definition_id="test_decision",
        title="Distress Signal",
        description="A civilian transport is drifting.",
        severity="major",
        trigger="tick",
        choices=(DecisionChoice(id="help", label="Help"),),
        tick=12,
    )


class TestRegistryContract(unittest.TestCase):
    def test_machines_are_unique_and_well_formed(self):
        ids = [machine.id for machine in MACHINES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 20)
        for machine in MACHINES:
            self.assertTrue(machine.states, machine.id)
            self.assertIn(machine.initial, machine.states, machine.id)
            self.assertTrue(set(machine.terminal) <= set(machine.states), machine.id)
            self.assertTrue(machine.evidence, machine.id)
            for transition in machine.transitions:
                self.assertIn(transition.source, machine.states, machine.id)
                self.assertIn(transition.target, machine.states, machine.id)
                self.assertTrue(transition.event, machine.id)

    def test_surface_gates_match_the_wired_layers(self):
        gates = catalog()["surface_gates"]
        self.assertEqual(
            gates["engine_flight"],
            ["anomaly", "combat", "customs", "decision", "pirate", "void"],
        )
        self.assertEqual(gates["engine_time"], ["decision", "pirate", "simulation"])
        self.assertEqual(gates["http_post"], ["customs", "decision", "pirate"])
        self.assertEqual(gates["cli"], ["customs", "decision", "pirate"])

    def test_catalog_serializes_every_machine(self):
        payload = catalog()
        self.assertEqual(payload["schema"], 1)
        self.assertEqual(len(payload["machines"]), len(MACHINES))
        self.assertTrue(payload["notes"])
        for machine in payload["machines"]:
            self.assertIn("transitions", machine)
            self.assertIn("blocks_flight", machine)


class TestInspector(unittest.TestCase):
    def test_default_state_is_onboarding(self):
        state = inspect_state(_engine().state)
        self.assertEqual(state["simulation"]["state"], "running")
        self.assertEqual(state["travel"]["state"], "idle")
        self.assertEqual(state["void"]["state"], "idle")
        self.assertEqual(state["combat"]["state"], "idle")
        self.assertEqual(state["anomaly"]["state"], "idle")
        self.assertEqual(situation(_engine().state)["primary"], "onboarding")

    def test_combat_blocks_flight_and_exposes_boarding(self):
        engine = _engine()
        marine = CrewMember(id="marine_1", name="Marine", role="marine", skill=4)
        engine.state = engine._clone_state(
            active_combat=_combat(hull=40, shield=0),
            ship=engine._clone_ship(crew=(marine,)),
        )
        state = inspect_state(engine.state)
        self.assertEqual(state["combat"]["state"], "engaged")
        self.assertTrue(state["combat"]["blocks_flight"])
        self.assertTrue(state["combat"]["detail"]["boardable"])
        self.assertEqual(state["boarding"]["state"], "available")
        summary = situation(engine.state)
        self.assertEqual(summary["primary"], "combat")
        self.assertIn("combat", summary["blocking_flight"])

    def test_anomaly_blocks_flight_and_has_priority(self):
        engine = _engine()
        engine.state = engine._clone_state(active_anomaly=_anomaly())
        state = inspect_state(engine.state)
        self.assertEqual(state["anomaly"]["state"], "pending")
        self.assertTrue(state["anomaly"]["blocks_flight"])
        summary = situation(engine.state)
        self.assertEqual(summary["primary"], "anomaly")
        self.assertIn("anomaly", summary["blocking_flight"])

    def test_decision_blocks_time_and_outranks_combat(self):
        engine = _engine()
        engine.state = engine._clone_state(
            pending_decision=_decision(),
            active_combat=_combat(),
            active_anomaly=_anomaly(),
        )
        state = inspect_state(engine.state)
        self.assertEqual(state["simulation"]["state"], "blocked_decision")
        self.assertEqual(state["decision"]["state"], "pending")
        summary = situation(engine.state)
        self.assertEqual(summary["primary"], "decision")
        self.assertIn("simulation", summary["blocking_time"])
        self.assertIn("decision", summary["blocking_time"])
        self.assertIn("combat", summary["blocking_flight"])
        self.assertIn("anomaly", summary["blocking_flight"])

    def test_pirate_blocks_time_and_flight(self):
        engine = _engine()
        engine.state = engine._clone_state(active_pirate=_pirate())
        state = inspect_state(engine.state)
        self.assertEqual(state["simulation"]["state"], "blocked_pirate")
        self.assertTrue(state["pirate"]["blocks_time"])
        summary = situation(engine.state)
        self.assertEqual(summary["primary"], "pirate")
        self.assertIn("pirate", summary["blocking_time"])

    def test_travel_and_void_states(self):
        engine = _engine()
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                travel=TravelState(
                    origin_body_id="sol_body_1",
                    destination_body_id="sol_body_5",
                    mode="quantum",
                    started_tick=0,
                    arrival_tick=6,
                    duration_ticks=6,
                )
            )
        )
        travel = inspect_state(engine.state)["travel"]
        self.assertEqual(travel["state"], "quantum")
        self.assertEqual(travel["detail"]["destination"], "sol_body_5")
        self.assertEqual(situation(engine.state)["primary"], "travel")

        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                travel=None,
                void_traversal=VoidTraversalState(
                    origin_system_id="cygnus_x1",
                    destination_system_id="golconda",
                    started_tick=0,
                    arrival_tick=8,
                    duration_ticks=8,
                ),
            )
        )
        void = inspect_state(engine.state)["void"]
        self.assertEqual(void["state"], "traversing")
        self.assertEqual(situation(engine.state)["primary"], "void")

    def test_reactor_thresholds(self):
        engine = _engine()
        for heat, expected in ((10.0, "nominal"), (75.0, "overheated"), (95.0, "critical")):
            engine.state = engine._clone_state(
                ship=engine._clone_ship(reactor=ReactorState(heat=heat))
            )
            self.assertEqual(inspect_state(engine.state)["reactor"]["state"], expected)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(reactor=ReactorState(integrity=0.0))
        )
        self.assertEqual(inspect_state(engine.state)["reactor"]["state"], "breached")

    def test_research_states(self):
        engine = _engine()
        engine.state = engine._clone_state(
            research=ResearchState(active_project_id="advanced_cooling", progress=12)
        )
        self.assertEqual(inspect_state(engine.state)["research"]["state"], "active")
        engine.state = engine._clone_state(
            research=ResearchState(queue=("advanced_cooling",))
        )
        self.assertEqual(inspect_state(engine.state)["research"]["state"], "queued")

    def test_secondary_lifecycles_are_inspected(self):
        engine = _engine()
        order = TradeOrder(
            id="order_1",
            commodity_id="titanium",
            quantity=4,
            origin_system_id="sol",
            destination_system_id="altair",
            destination_body_id="altair_body_1",
            destination_name="Altair Station",
            fee_paid=50,
            created_tick=0,
            arrival_tick=5,
            unit_price_at_launch=90,
        )
        captain = AICaptain(
            id="captain_1", name="Vega", archetype="trader",
            system_id="sol", credits=1000, hired=True,
        )
        event = GameEvent(id="event_1", kind="hazard", title="Warning", message="")
        engine.state = engine._clone_state(
            ship=engine._clone_ship(trade_orders=(order,)),
            ai_captains=(captain,),
            events=(event,),
        )
        state = inspect_state(engine.state)
        self.assertEqual(state["quantum_freight"]["state"], "in_transit")
        self.assertEqual(state["quantum_freight"]["detail"]["next_arrival_tick"], 5)
        self.assertEqual(state["ai_captain"]["state"], "hired")
        self.assertEqual(state["event"]["state"], "visible")
        self.assertIn(state["megastructure"]["state"], ("dormant", "restored"))

    def test_snapshot_carries_the_situation(self):
        snapshot = _engine().get_status_snapshot(include_static=False)
        self.assertIn("state_machines", snapshot)
        self.assertIn("summary", snapshot["state_machines"])
        self.assertIn("blocking_flight", snapshot["state_machines"])


class TestActionGate(unittest.TestCase):
    """The engine's flight gate covers every blocking machine."""

    def _assert_locked(self, result, needle: str):
        ok, message = result
        self.assertFalse(ok, message)
        self.assertIn(needle, message)

    def test_combat_blocks_orbit_travel_point_and_landing(self):
        engine = _engine()
        engine.state = engine._clone_state(active_combat=_combat())
        self._assert_locked(engine.orbit("sol_body_2"), "Hostile combat active")
        self._assert_locked(engine.start_travel("sol_body_2"), "Hostile combat active")
        self._assert_locked(engine.start_travel_to_point(4.4, 1.0), "Hostile combat active")

        engine.state = engine._clone_state(
            active_combat=_combat(),
            ship=engine._clone_ship(orbiting_body_id="sol_body_5", travel=None),
        )
        self._assert_locked(engine.land_on_body("sol_body_5"), "Hostile combat active")

    def test_anomaly_blocks_orbit_travel_and_landing(self):
        engine = _engine()
        engine.state = engine._clone_state(active_anomaly=_anomaly())
        self._assert_locked(engine.orbit("sol_body_2"), "Unresolved spatial anomaly")
        self._assert_locked(engine.start_travel("sol_body_2"), "Unresolved spatial anomaly")
        engine.state = engine._clone_state(
            active_anomaly=_anomaly(),
            ship=engine._clone_ship(orbiting_body_id="sol_body_5", travel=None),
        )
        self._assert_locked(engine.land_on_body("sol_body_5"), "Unresolved spatial anomaly")

    def test_customs_still_blocks_flight(self):
        engine = _engine()
        engine.state = engine._clone_state(active_customs=_customs())
        self._assert_locked(engine.orbit("sol_body_2"), "Customs interdiction unresolved")

    def test_void_dive_respects_the_remaining_blockers(self):
        for setup, needle in (
            ({"pending_decision": _decision()}, "Decision required"),
            ({"active_pirate": _pirate()}, "Pirate intercept unresolved"),
            ({"active_customs": _customs()}, "Customs interdiction unresolved"),
        ):
            engine = _engine()
            engine.state = engine._clone_state(**setup)
            self._assert_locked(engine.void_dive("golconda"), needle)

    def test_combat_actions_stay_available(self):
        engine = _engine()
        engine.state = engine._clone_state(active_combat=_combat(hull=120))
        ok, message = engine.combat_action("fire_lasers")
        self.assertTrue(ok, message)
        self.assertNotIn("before other flight actions", message)


class TestResearchTransitionMessage(unittest.TestCase):
    def test_switching_reports_discarded_points(self):
        engine = _engine()
        engine.state = engine._clone_state(
            research=ResearchState(active_project_id="advanced_cooling", progress=40)
        )
        ok, message = engine.choose_research("deep_survey_arrays")
        self.assertTrue(ok, message)
        self.assertIn("Discarded 40 banked points", message)
        self.assertEqual(engine.state.research.progress, 0)


class TestStateMachineSurfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.storage = StorageManager(cls.temp_dir.name)
        cls.engine = SimulationEngine(seed=42)
        VoidFarerHandler.engine = cls.engine
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

    def _get(self, path: str):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body.decode("utf-8"))

    def test_rest_endpoint_lists_registry_and_current_state(self):
        status, payload = self._get("/api/state-machines")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["machines"]), len(MACHINES))
        self.assertEqual(len(payload["current"]), len(MACHINES))
        self.assertIn("summary", payload["situation"])
        self.assertIn("surface_gates", payload)

    def test_state_snapshot_carries_the_compact_situation(self):
        status, payload = self._get("/api/state")
        self.assertEqual(status, 200)
        situation_payload = payload["data"]["state_machines"]
        self.assertIn("summary", situation_payload)
        self.assertIn("primary", situation_payload)

    def test_cli_prints_json_and_stays_available_when_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            engine = SimulationEngine(seed=42)
            engine.state = engine._clone_state(pending_decision=_decision())
            StorageManager(temp).save(engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "state-machines", "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(len(payload["machines"]), len(MACHINES))
            self.assertEqual(payload["situation"]["primary"], "decision")
            self.assertIn("decision", payload["situation"]["blocking_time"])


if __name__ == "__main__":
    unittest.main()
