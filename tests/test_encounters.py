"""Unified blocking-encounter payload, resolver, REST and CLI tests."""

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
from voidfarer.encounters import active_encounter, encounter_report, resolve
from voidfarer.engine import SimulationEngine
from voidfarer.models import (
    AnomalyChoice,
    AnomalyEncounter,
    CustomsEncounter,
    DecisionChoice,
    DecisionEvent,
    PirateEncounter,
    TravelState,
)
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _engine() -> SimulationEngine:
    engine = SimulationEngine(seed=42)
    engine.allow_decision_events = False
    engine.pause_time()
    return engine


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


class TestEncounterPayload(unittest.TestCase):
    def test_no_active_encounter(self):
        report = encounter_report(_engine().state)
        self.assertFalse(report["active"])
        self.assertIsNone(report["encounter"])
        self.assertIsNone(active_encounter(_engine().state))

    def test_decision_has_priority(self):
        engine = _engine()
        engine.state = engine._clone_state(
            pending_decision=_decision(),
            active_pirate=_pirate(),
            active_customs=_customs(),
            active_anomaly=_anomaly(),
        )
        encounter = active_encounter(engine.state)
        self.assertEqual(encounter["kind"], "decision")
        self.assertEqual([a["id"] for a in encounter["actions"]], ["help"])

    def test_pirate_payload_reports_costs_and_disabled_actions(self):
        engine = _engine()
        engine.state = engine._clone_state(active_pirate=_pirate())
        encounter = active_encounter(engine.state)
        self.assertEqual(encounter["kind"], "pirate")
        actions = {action["id"]: action for action in encounter["actions"]}
        self.assertEqual(set(actions), {"pay", "fight", "evade"})
        self.assertEqual(actions["pay"]["cost"], 150)
        self.assertFalse(actions["pay"]["disabled"])
        engine.state = engine._clone_state(
            active_pirate=_pirate(),
            ship=engine._clone_ship(credits=10),
        )
        pay = {a["id"]: a for a in active_encounter(engine.state)["actions"]}["pay"]
        self.assertTrue(pay["disabled"])
        self.assertIn("Needs 150 cr", pay["reason"])

    def test_customs_payload_reports_fine_bribe_and_fuel(self):
        engine = _engine()
        engine.state = engine._clone_state(
            active_customs=_customs(),
            ship=engine._clone_ship(fuel=2),
        )
        encounter = active_encounter(engine.state)
        actions = {action["id"]: action for action in encounter["actions"]}
        self.assertEqual(set(actions), {"bribe", "jettison", "confiscate", "flee"})
        self.assertEqual(actions["bribe"]["cost"], 120)
        self.assertTrue(actions["flee"]["disabled"])
        self.assertIn("2 units", encounter["detail"])

    def test_anomaly_and_decision_expose_their_choices(self):
        engine = _engine()
        engine.state = engine._clone_state(active_anomaly=_anomaly())
        anomaly = active_encounter(engine.state)
        self.assertEqual(anomaly["kind"], "anomaly")
        self.assertEqual([a["id"] for a in anomaly["actions"]], ["harvest"])
        engine.state = engine._clone_state(
            active_anomaly=None, pending_decision=_decision()
        )
        decision = active_encounter(engine.state)
        self.assertEqual(decision["kind"], "decision")
        self.assertEqual([a["id"] for a in decision["actions"]], ["help"])


class TestEncounterResolver(unittest.TestCase):
    def test_pirate_pay_matches_the_legacy_resolver(self):
        engine = _engine()
        before = engine.state.ship.credits
        engine.state = engine._clone_state(active_pirate=_pirate())
        ok, message = resolve(engine, None, "pay")
        self.assertTrue(ok, message)
        self.assertIsNone(engine.state.active_pirate)
        self.assertEqual(engine.state.ship.credits, before - 150)

    def test_customs_bribe_matches_the_legacy_resolver(self):
        engine = _engine()
        before = engine.state.ship.credits
        engine.state = engine._clone_state(active_customs=_customs())
        ok, message = resolve(engine, "customs", "bribe")
        self.assertTrue(ok, message)
        self.assertIsNone(engine.state.active_customs)
        self.assertEqual(engine.state.ship.credits, before - 120)

    def test_anomaly_and_decision_clear_through_the_facade(self):
        engine = _engine()
        engine.state = engine._clone_state(active_anomaly=_anomaly())
        ok, message = resolve(engine, "anomaly", "harvest")
        self.assertTrue(ok, message)
        self.assertIsNone(engine.state.active_anomaly)

        engine.state = engine._clone_state(
            active_anomaly=None, pending_decision=_decision()
        )
        ok, message = resolve(engine, None, "help")
        self.assertTrue(ok, message)
        self.assertIsNone(engine.state.pending_decision)

    def test_kind_mismatch_and_empty_action_are_rejected(self):
        engine = _engine()
        engine.state = engine._clone_state(active_pirate=_pirate())
        ok, message = resolve(engine, "customs", "bribe")
        self.assertFalse(ok)
        self.assertIn("Active encounter is 'pirate'", message)
        ok, message = resolve(engine, None, "")
        self.assertFalse(ok)
        self.assertIn("action is required", message.lower())

    def test_snapshot_carries_the_encounter(self):
        engine = _engine()
        engine.state = engine._clone_state(active_pirate=_pirate())
        snapshot = engine.get_status_snapshot(include_static=False)
        self.assertTrue(snapshot["encounter"]["active"])
        self.assertEqual(snapshot["encounter"]["kind"], "pirate")


class TestEncounterSurfaces(unittest.TestCase):
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

    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.allow_decision_events = False
        self.engine.pause_time()
        VoidFarerHandler.engine = self.engine
        VoidFarerHandler.storage = StorageManager(self.temp_dir.name)

    def _get(self, path: str):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body.decode("utf-8"))

    def _post(self, path: str, payload: dict):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        connection.request(
            "POST", path, body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        body = response.read()
        connection.close()
        return response.status, json.loads(body.decode("utf-8"))

    def test_get_endpoint_reports_the_active_encounter(self):
        self.engine.state = self.engine._clone_state(active_pirate=_pirate())
        status, payload = self._get("/api/encounter")
        self.assertEqual(status, 200)
        self.assertTrue(payload["active"])
        self.assertEqual(payload["encounter"]["kind"], "pirate")

    def test_resolve_endpoint_works_while_blocked(self):
        before = self.engine.state.ship.credits
        self.engine.state = self.engine._clone_state(active_pirate=_pirate())
        status, payload = self._post(
            "/api/encounter/resolve", {"kind": "pirate", "action": "pay"}
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"], payload)
        self.assertIsNone(self.engine.state.active_pirate)
        self.assertEqual(self.engine.state.ship.credits, before - 150)

    def test_decision_allowlist_accepts_the_unified_route(self):
        self.engine.state = self.engine._clone_state(pending_decision=_decision())
        status, payload = self._post(
            "/api/encounter/resolve", {"kind": "decision", "action": "help"}
        )
        self.assertEqual(status, 200, payload)
        self.assertTrue(payload["ok"], payload)
        self.assertIsNone(self.engine.state.pending_decision)

    def test_cli_inspects_and_resolves_while_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            engine = SimulationEngine(seed=42)
            engine.state = engine._clone_state(
                active_pirate=_pirate(),
                ship=engine._clone_ship(credits=500),
            )
            StorageManager(temp).save(engine.state)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = cli.main(["--save-path", temp, "encounter"])
            self.assertEqual(code, 0)
            self.assertIn("PIRATE INTERCEPT", buffer.getvalue())
            self.assertIn("pay", buffer.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["--save-path", temp, "encounter", "pay"])
            self.assertEqual(code, 0)
            loaded = StorageManager(temp).load()
            self.assertIsNotNone(loaded)
            self.assertIsNone(loaded.active_pirate)
            self.assertEqual(loaded.ship.credits, 350)


if __name__ == "__main__":
    unittest.main()
