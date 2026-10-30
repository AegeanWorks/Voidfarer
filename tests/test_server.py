"""Unit and integration tests for embedded HTTP server REST endpoints."""

from dataclasses import replace
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.decisions import DECISION_DEFINITIONS, make_decision_event
from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship
from voidfarer.models import FleetShip, Outpost
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.storage = StorageManager(cls.temp_dir.name)
        cls.engine = SimulationEngine(seed=42)

        VoidFarerHandler.engine = cls.engine
        VoidFarerHandler.storage = cls.storage
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"

        # Bind to port 0 (dynamic available port)
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        cls.port = cls.server.server_port

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def setUp(self):
        VoidFarerHandler.engine = SimulationEngine(seed=42)
        VoidFarerHandler.storage = StorageManager(self.temp_dir.name)

    def _get(self, path: str):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, data

    def _post(self, path: str, body: dict):
        return self._post_raw(path, json.dumps(body))

    def _post_raw(self, path: str, payload: str, content_type: str = "application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("POST", path, body=payload, headers={"Content-Type": content_type})
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, data

    def test_get_static_index(self):
        status, data = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn(b"VOIDFARER", data)

    def test_get_api_state(self):
        status, data = self._get("/api/state")
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])
        self.assertEqual(json_data["data"]["ship"]["commander_name"], "Astraea")
        creation = json_data["data"]["character_creation"]
        self.assertEqual(creation["skill_base"], 5)
        self.assertEqual(creation["skill_points"], 20)
        self.assertEqual(creation["max_skill"], 10)
        self.assertEqual(len(creation["skills"]), 6)

    def test_get_api_galaxy(self):
        status, data = self._get("/api/galaxy")
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])
        self.assertIn("sol", json_data["systems"])

    def test_reactor_map_and_shipmod_endpoints(self):
        for path in ("/api/reactor", "/api/mapmods", "/api/shipmods", "/api/simulation"):
            status, data = self._get(path)
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        status, data = self._post("/api/reactor/mode", {"mode": "economy"})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["state"]["ship"]["reactor"]["mode"], "economy")

        status, data = self._post("/api/reactor/vent", {})
        self.assertEqual(status, 200)

        status, data = self._post("/api/shipmods/install", {"mod_id": "reinforced_spine"})
        self.assertEqual(status, 200)
        status, data = self._post("/api/shipmods/remove", {"slot": "frame"})
        self.assertEqual(status, 200)

        status, data = self._post("/api/ship/module", {"module_id": "salvage_processor", "action": "install"})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["state"]["ship"]["ship_mods"]["ops"], "salvage_processor")

        status, data = self._post("/api/ship/module", {"module_id": "salvage_processor", "action": "uninstall"})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertNotIn("ops", payload["state"]["ship"]["ship_mods"])

    def test_new_game_applies_commander_profile(self):
        status, data = self._post("/api/new-game", {
            "seed": 7,
            "profile": {
                "name": "Nova",
                "age": 41,
                "background": "Engineer",
                "skills": {"engineering": 9, "combat": 2},
            },
        })
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"])
        character = payload["state"]["character"]
        self.assertEqual(character["name"], "Nova")
        self.assertEqual(character["age"], 41)
        self.assertEqual(character["background"], "Engineer")
        self.assertEqual(character["skills"]["engineering"], 9)
        self.assertEqual(character["skills"]["combat"], 2)
        self.assertEqual(payload["state"]["ship"]["commander_name"], "Nova")

    def test_new_game_rejects_over_budget_commander_profile(self):
        skills = {skill: 10 for skill in ("piloting", "engineering", "science", "combat", "diplomacy", "trade")}
        status, data = self._post("/api/new-game", {"seed": 7, "profile": {"skills": skills}})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertIn("budget", payload["message"])

    def test_load_is_allowed_while_a_decision_is_pending(self):
        engine = VoidFarerHandler.engine
        VoidFarerHandler.storage.save(engine.state)
        engine.state = engine._clone_state(
            pending_decision=make_decision_event(
                DECISION_DEFINITIONS[0], engine.state.time.tick, "tick"
            )
        )

        status, data = self._post("/api/load", {"slot": "default"})

        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertIsNone(VoidFarerHandler.engine.state.pending_decision)

    def test_invalid_save_slot_returns_400(self):
        status, data = self._post("/api/save", {"slot": "bad slot!"})
        self.assertEqual(status, 400)
        payload = json.loads(data.decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertIn("Invalid save slot", payload["message"])

    def test_character_research_fleet_diplomacy_endpoints(self):
        for path in ("/api/character", "/api/research", "/api/outposts", "/api/diplomacy", "/api/fleet/ships"):
            status, data = self._get(path)
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        status, data = self._post("/api/research/start", {"project_id": "advanced_cooling"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        status, data = self._post("/api/diplomacy", {"faction_id": "vanguard_syndicate", "action": "improve"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        status, data = self._post("/api/route", {"system_id": "alpha_centauri"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

    def test_crew_weapon_and_message_tree_endpoints(self):
        for path in ("/api/crew", "/api/weapons", "/api/messages/trees"):
            status, data = self._get(path)
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        status, data = self._get("/api/messages")
        messages = json.loads(data.decode("utf-8"))["messages"]
        root = next(m for m in messages if m.get("tree_id") == "precursor_signal")
        status, data = self._post("/api/messages/choose", {"message_id": root["id"], "choice_id": "decode"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

    def test_post_power(self):
        status, data = self._post("/api/power", {"engines": 35, "shields": 25, "sensors": 20, "weapons": 20})
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])
        self.assertEqual(json_data["state"]["ship"]["power"]["engines"], 35)

    def test_post_travel_preview(self):
        status, data = self._post("/api/travel/preview", {"body_id": "sol_body_3"})
        self.assertEqual(status, 200)
        parsed = json.loads(data.decode("utf-8"))
        self.assertTrue(parsed["ok"])
        sublight = parsed["previews"]["sublight"]
        quantum = parsed["previews"]["quantum"]
        self.assertIn("duration_ticks", sublight)
        self.assertIn("risk", sublight)
        self.assertIn("hazards", sublight)
        self.assertGreaterEqual(quantum["fuel_cost"], 2)

    def test_post_orbit_and_scan(self):
        status, data = self._post("/api/orbit", {"target": "sol_body_1"})
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])

        # Scan
        status_s, data_s = self._post("/api/scan", {})
        self.assertEqual(status_s, 200)
        json_scan = json.loads(data_s.decode("utf-8"))
        self.assertTrue(json_scan["ok"])

    def test_post_drone_and_upgrade_endpoints(self):
        # Orbit station first
        self._post("/api/orbit", {"target": "sol_body_1"})

        # Buy drone
        st_d, data_d = self._post("/api/drone/buy", {"drone_type": "mining", "system_id": "sol"})
        self.assertEqual(st_d, 200)
        json_d = json.loads(data_d.decode("utf-8"))
        self.assertTrue(json_d["ok"])

        # Buy upgrade
        st_u, data_u = self._post("/api/upgrade", {"upgrade_id": "warp_booster_mk2"})
        self.assertEqual(st_u, 200)
        json_u = json.loads(data_u.decode("utf-8"))
        self.assertTrue(json_u["ok"])

    def test_contracts_and_relics_endpoints(self):
        # GET /api/contracts
        st_c, data_c = self._get("/api/contracts")
        self.assertEqual(st_c, 200)
        json_c = json.loads(data_c.decode("utf-8"))
        self.assertTrue(json_c["ok"])
        self.assertGreaterEqual(len(json_c["contracts"]), 1)

        # GET /api/relics
        st_r, data_r = self._get("/api/relics")
        self.assertEqual(st_r, 200)
        json_r = json.loads(data_r.decode("utf-8"))
        self.assertTrue(json_r["ok"])

        # POST /api/mastery/unlock (should fail with zero talent points)
        st_m, data_m = self._post("/api/mastery/unlock", {"talent_id": "void_cartographer"})
        self.assertEqual(st_m, 200)
        json_m = json.loads(data_m.decode("utf-8"))
        self.assertFalse(json_m["ok"])

    def test_malformed_json_is_rejected(self):
        status, data = self._post_raw("/api/orbit", "{not json")
        self.assertEqual(status, 400)
        self.assertFalse(json.loads(data.decode("utf-8"))["ok"])

    def test_non_object_json_is_rejected(self):
        status, data = self._post_raw("/api/orbit", "[1, 2, 3]")
        self.assertEqual(status, 400)
        self.assertFalse(json.loads(data.decode("utf-8"))["ok"])

    def test_wrong_field_type_is_rejected(self):
        status, data = self._post("/api/power", {"engines": "many"})
        self.assertEqual(status, 400)
        self.assertFalse(json.loads(data.decode("utf-8"))["ok"])

    def test_negative_repair_and_refuel_are_rejected(self):
        for endpoint in ("/api/repair", "/api/refuel"):
            status, _ = self._post(endpoint, {"amount": -25})
            self.assertEqual(status, 400, endpoint)

    def test_trade_rejects_non_boolean_is_buy(self):
        status, _ = self._post("/api/trade", {"commodity_id": "fuel_cells", "quantity": 1, "is_buy": "yes"})
        self.assertEqual(status, 400)

    def test_step_rejects_negative_and_non_finite_delta(self):
        for payload in ('{"delta_time": -1}', '{"delta_time": NaN}'):
            status, _ = self._post_raw("/api/step", payload)
            self.assertEqual(status, 400, payload)

    def test_scan_response_exposes_relic_and_near_miss(self):
        self._post("/api/orbit", {"target": "sol_body_1"})
        status, data = self._post("/api/scan", {})
        self.assertEqual(status, 200)
        discovery = json.loads(data.decode("utf-8"))["discovery"]
        self.assertIn("relic", discovery)
        self.assertIn("near_miss", discovery)

    def test_reset_is_deterministic_for_a_seed(self):
        first = self._post("/api/reset", {"seed": 7})
        second = self._post("/api/reset", {"seed": 7})
        self.assertEqual(first[0], 200)
        self.assertEqual(second[0], 200)
        first_state = json.loads(first[1].decode("utf-8"))["state"]
        second_state = json.loads(second[1].decode("utf-8"))["state"]
        self.assertEqual(first_state["stats"], second_state["stats"])
        self.assertEqual(first_state["ship"]["credits"], second_state["ship"]["credits"])

    def test_get_api_shipyard_excludes_current_chassis(self):
        status, data = self._get("/api/shipyard")
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        available = {c["id"] for c in json_data["available_chassis"]}
        self.assertNotIn("vanguard_scout", available)

    def test_post_inventory_buy_rejects_non_numeric_quantity(self):
        status, data = self._post("/api/inventory/buy", {"item_id": "nanite_repair_paste", "quantity": "many"})
        self.assertEqual(status, 400)
        json_data = json.loads(data.decode("utf-8"))
        self.assertFalse(json_data["ok"])

    def test_frontier_endpoints(self):
        status, data = self._get("/api/quests")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        status, data = self._get("/api/ai")
        self.assertEqual(status, 200)
        captain = json.loads(data.decode("utf-8"))["captains"][0]
        status, data = self._post("/api/ai/interact", {"captain_id": captain["id"], "action": "hail"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        status, data = self._post("/api/messages/send", {"recipient": captain["name"], "subject": "Hello", "body": "Quantum test"})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

    def test_landing_and_depot_endpoints(self):
        status, data = self._get("/api/state")
        state = json.loads(data.decode("utf-8"))["data"]
        landable = next(b for b in state["current_system"]["bodies"] if b["landable"])
        self._post("/api/orbit", {"target": landable["id"]})
        status, data = self._post("/api/land", {"target": landable["id"]})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

        self._post("/api/orbit", {"target": "sol_body_1"})
        status, data = self._post("/api/depot/deposit", {"item_id": "fuel_cells", "quantity": 1})
        self.assertEqual(status, 200)
        self.assertIn("Deposited", json.loads(data.decode("utf-8"))["message"])

    def test_reconstruct_endpoint_restores_a_devastated_world(self):
        engine = VoidFarerHandler.engine
        body = next(candidate for candidate in engine.current_system.bodies if candidate.population > 0)
        systems = dict(engine.state.systems)
        system = systems[engine.current_system.id]
        systems[system.id] = replace(
            system,
            bodies=tuple(
                replace(candidate, devastation=60.0) if candidate.id == body.id else candidate
                for candidate in system.bodies
            ),
        )
        engine.state = engine._clone_state(
            systems=systems,
            ship=engine._clone_ship(orbiting_body_id=body.id, credits=5000),
        )
        status, data = self._post("/api/reconstruct", {"body_id": body.id, "mode": "credits"})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        updated = next(
            candidate for candidate in payload["state"]["current_system"]["bodies"]
            if candidate["id"] == body.id
        )
        self.assertAlmostEqual(updated["devastation"], 40.0)
        self.assertEqual(payload["state"]["ship"]["credits"], 4400)

    def test_fleet_sell_endpoint_converts_a_prize_to_credits(self):
        engine = VoidFarerHandler.engine
        prize = FleetShip(
            id="http_prize",
            name="Prize: Test Corsair",
            ship_class="Frigate",
            role="prize",
            hull=40,
            max_hull=100,
            shield=0,
            max_shield=0,
            damage=6,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(fleet_ships=(prize,), credits=1000),
        )
        status, data = self._post("/api/fleet/escort/sell", {"ship_id": prize.id})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertGreater(payload["state"]["ship"]["credits"], 1000)
        self.assertEqual(payload["state"]["ship"]["fleet_ships"], [])
        self.assertEqual(payload["state"]["stats"]["ships_sold"], 1)

    def test_research_pact_endpoint_forms_a_pact(self):
        engine = VoidFarerHandler.engine
        standings = dict(engine.state.ship.faction_standings)
        standings["sol_coalition"] = 60
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                faction_standings=standings,
                research_pacts=(),
            )
        )
        status, data = self._post(
            "/api/diplomacy",
            {"faction_id": "sol_coalition", "action": "research_pact"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertIn("sol_coalition", payload["state"]["ship"]["research_pacts"])

    def test_trade_pact_endpoint_forms_a_pact(self):
        engine = VoidFarerHandler.engine
        standings = dict(engine.state.ship.faction_standings)
        standings["sol_coalition"] = 50
        engine.state = engine._clone_state(
            ship=engine._clone_ship(faction_standings=standings)
        )
        status, data = self._post(
            "/api/diplomacy",
            {"faction_id": "sol_coalition", "action": "trade_pact"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertIn("sol_coalition", payload["state"]["ship"]["trade_pacts"])

    def test_fleet_captain_endpoint_assigns_and_recalls(self):
        engine = VoidFarerHandler.engine
        ship = build_fleet_ship("corvette", "sol", 0)
        crew = engine.state.ship.crew[0]
        engine.state = engine._clone_state(
            ship=engine._clone_ship(fleet_ships=(ship,), crew=engine.state.ship.crew),
        )
        status, data = self._post(
            "/api/fleet/escort/captain",
            {"ship_id": ship.id, "crew_id": crew.id, "action": "assign"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        updated = payload["state"]["fleet_manager"]["ships"][0]
        self.assertEqual(updated["captain_id"], crew.id)
        self.assertEqual(updated["captain_name"], crew.name)

        status, data = self._post(
            "/api/fleet/escort/captain",
            {"ship_id": ship.id, "action": "recall"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertEqual(
            payload["state"]["fleet_manager"]["ships"][0]["captain_id"], ""
        )

    def test_fleet_role_endpoint_sets_squadron_role(self):
        engine = VoidFarerHandler.engine
        ship = build_fleet_ship("corvette", "sol", 0)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(fleet_ships=(ship,)),
            active_combat=None,
        )
        status, data = self._post(
            "/api/fleet/escort/role",
            {"ship_id": ship.id, "role": "support"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        updated = payload["state"]["fleet_manager"]["ships"][0]
        self.assertEqual(updated["tactical_role"], "support")
        self.assertEqual(updated["role_label"], "Support")

    def test_fleet_train_endpoint_buys_experience(self):
        engine = VoidFarerHandler.engine
        ship = build_fleet_ship("corvette", "sol", 0)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                fleet_ships=(ship,),
                credits=1000,
                orbiting_body_id="sol_body_1",
            ),
        )
        status, data = self._post("/api/fleet/escort/train", {"ship_id": ship.id})
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        trained = payload["state"]["fleet_manager"]["ships"][0]
        self.assertEqual(trained["experience"], 10)
        self.assertEqual(trained["rank"], "Green")
        self.assertEqual(payload["state"]["ship"]["credits"], 800)

    def test_quantum_automation_endpoints_configure_and_report(self):
        status, data = self._post(
            "/api/trade/quantum/automation",
            {"enabled": True, "min_net": 150},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertTrue(payload["state"]["quantum_automation"]["enabled"])
        self.assertEqual(payload["state"]["quantum_automation"]["min_net"], 150)

    def test_trade_automation_endpoints_configure_and_report(self):
        status, data = self._get("/api/trade/automation")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])
        status, data = self._post(
            "/api/trade/automation",
            {"enabled": True, "commodity_id": "titanium", "buy_below": 40, "sell_above": 80, "quantity": 2},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        automation = payload["state"]["trade_automation"]
        self.assertTrue(automation["enabled"])
        self.assertEqual(automation["commodity_id"], "titanium")
        self.assertEqual(automation["quantity"], 2)

    def test_research_queue_endpoints_queue_and_cancel(self):
        engine = VoidFarerHandler.engine
        engine.state = engine._clone_state(
            research=replace(engine.state.research, queue=())
        )
        status, data = self._post(
            "/api/research/queue", {"project_id": "advanced_cooling"}
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertEqual(
            payload["state"]["research"]["queue"], ["advanced_cooling"]
        )

        status, data = self._post(
            "/api/research/cancel", {"project_id": "advanced_cooling"}
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertEqual(payload["state"]["research"]["queue"], [])

    def test_outpost_repair_endpoint_restores_integrity(self):
        engine = VoidFarerHandler.engine
        outpost = Outpost(
            id="http_repair_outpost",
            name="Repair Test Outpost",
            system_id="sol",
            body_id="sol_body_1",
            outpost_type="mining",
            integrity=40.0,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(credits=1000),
            outposts=(outpost,),
        )
        status, data = self._post(
            "/api/outpost/repair", {"outpost_id": outpost.id}
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertEqual(payload["state"]["outposts"][0]["integrity"], 100.0)

    def test_outpost_specialize_endpoint_sets_a_focus(self):
        engine = VoidFarerHandler.engine
        outpost = Outpost(
            id="http_spec_outpost",
            name="Specialization Test Outpost",
            system_id="sol",
            body_id="sol_body_1",
            outpost_type="mining",
            level=3,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(credits=5000),
            outposts=(outpost,),
        )
        status, data = self._post(
            "/api/outpost/specialize",
            {"outpost_id": outpost.id, "specialization": "industry"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        updated = payload["state"]["outposts"][0]
        self.assertEqual(updated["specialization"], "industry")
        self.assertEqual(updated["specialization_label"], "Industry")

    def test_outpost_crew_endpoint_assigns_and_recalls(self):
        engine = VoidFarerHandler.engine
        outpost = Outpost(
            id="http_crew_outpost",
            name="Crew Test Outpost",
            system_id="sol",
            body_id="sol_body_1",
            outpost_type="mining",
            assigned_crew=(),
        )
        crew = engine.state.ship.crew[0]
        engine.state = engine._clone_state(
            ship=engine._clone_ship(crew=engine.state.ship.crew),
            outposts=(outpost,),
        )
        status, data = self._post(
            "/api/outpost/crew",
            {"outpost_id": outpost.id, "crew_id": crew.id, "action": "assign"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertIn(crew.id, payload["state"]["outposts"][0]["assigned_crew"])
        self.assertGreater(payload["state"]["outposts"][0]["crew_multiplier"], 1.0)

        status, data = self._post(
            "/api/outpost/crew",
            {"outpost_id": outpost.id, "crew_id": crew.id, "action": "recall"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertEqual(payload["state"]["outposts"][0]["assigned_crew"], [])

    def test_outpost_module_endpoint_installs_a_stack(self):
        engine = VoidFarerHandler.engine
        outpost = Outpost(
            id="http_outpost",
            name="HTTP Outpost",
            system_id="sol",
            body_id="sol_body_2",
            outpost_type="mining",
            modules={"extractor": 1},
            production={"credits": 3.0},
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(credits=5000),
            outposts=(outpost,),
        )
        status, data = self._post(
            "/api/outpost/module",
            {"outpost_id": outpost.id, "module_id": "laboratory"},
        )
        self.assertEqual(status, 200)
        payload = json.loads(data.decode("utf-8"))
        self.assertTrue(payload["ok"], payload.get("message"))
        self.assertEqual(payload["state"]["outposts"][0]["modules"]["laboratory"], 1)
        self.assertEqual(payload["state"]["ship"]["credits"], 4500)

    def test_save_load_delete_endpoints(self):
        status, _ = self._post("/api/save", {})
        self.assertEqual(status, 200)
        status, data = self._post("/api/delete-save", {})
        self.assertEqual(status, 200)
        status, data = self._post("/api/load", {})
        self.assertEqual(status, 404)
        status, data = self._post("/api/new-game", {"seed": 7})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(data.decode("utf-8"))["ok"])

    def test_multiple_save_slots_endpoints_and_listing(self):
        st_s1, data_s1 = self._post("/api/save", {"slot": "slot_1"})
        self.assertEqual(st_s1, 200)
        payload_s1 = json.loads(data_s1.decode("utf-8"))
        self.assertTrue(payload_s1["ok"])
        self.assertEqual(payload_s1["slot"], "slot_1")

        self._post("/api/new-game", {"seed": 19})
        st_s2, _ = self._post("/api/save", {"slot": "slot_2"})
        self.assertEqual(st_s2, 200)

        st_list, data_list = self._get("/api/saves")
        self.assertEqual(st_list, 200)
        saves_payload = json.loads(data_list.decode("utf-8"))
        self.assertTrue(saves_payload["ok"])
        slot_names = {entry["slot"] for entry in saves_payload["saves"]}
        self.assertIn("slot_1", slot_names)
        self.assertIn("slot_2", slot_names)

        st_load, data_load = self._post("/api/load", {"slot": "slot_1"})
        self.assertEqual(st_load, 200)
        loaded_payload = json.loads(data_load.decode("utf-8"))
        self.assertTrue(loaded_payload["ok"])
        self.assertEqual(loaded_payload["slot"], "slot_1")

        st_del, data_del = self._post("/api/delete-save", {"slot": "slot_1"})
        self.assertEqual(st_del, 200)
        self.assertTrue(json.loads(data_del.decode("utf-8"))["ok"])
        st_missing, _ = self._post("/api/load", {"slot": "slot_1"})
        self.assertEqual(st_missing, 404)

        st_bad, _ = self._post("/api/save", {"slot": "../bad"})
        self.assertEqual(st_bad, 400)

    def test_codex_claim_endpoint(self):
        st_jump, data_jump = self._post("/api/jump", {"target": "alpha_centauri"})
        self.assertEqual(st_jump, 200)

        st_claim, data_claim = self._post("/api/codex/claim", {"entry_id": "first_light"})
        self.assertEqual(st_claim, 200)
        payload = json.loads(data_claim.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("First Light", payload["message"])
        self.assertEqual(payload["state"]["codex"]["totals"]["claimed"], 1)

        # Claiming again fails
        st_again, data_again = self._post("/api/codex/claim", {"entry_id": "first_light"})
        self.assertEqual(st_again, 200)
        again_payload = json.loads(data_again.decode("utf-8"))
        self.assertFalse(again_payload["ok"])
        self.assertIn("already claimed", again_payload["message"].lower())

        # Locked entry fails
        st_locked, data_locked = self._post("/api/codex/claim", {"entry_id": "warlord"})
        self.assertEqual(st_locked, 200)
        locked_payload = json.loads(data_locked.decode("utf-8"))
        self.assertFalse(locked_payload["ok"])

        # Missing entry_id fails with 400
        st_missing, _ = self._post("/api/codex/claim", {})
        self.assertEqual(st_missing, 400)


if __name__ == "__main__":
    unittest.main()
