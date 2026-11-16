"""The headless AI captain must be able to reach and exercise the game without a human."""

import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.agent_api import build_action_catalog
from voidfarer.agent_play import AiCaptain, ApiClient, coverage_gaps
from voidfarer.engine import SimulationEngine
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


class AgentApiCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build_action_catalog(VoidFarerHandler)

    def test_catalog_describes_every_post_route(self):
        self.assertTrue(self.catalog["ok"])
        paths = {entry["path"] for entry in self.catalog["actions"]}
        self.assertGreaterEqual(len(paths), 60)
        for required in (
            "/api/travel", "/api/travel/point", "/api/trade", "/api/scan", "/api/orbit",
            "/api/jump", "/api/diplomacy", "/api/war/support", "/api/settings/decisions",
            "/api/decision/resolve", "/api/pirate/resolve", "/api/combat",
        ):
            self.assertIn(required, paths)

    def test_catalog_fields_match_the_endpoint_contract(self):
        by_path = {entry["path"]: entry for entry in self.catalog["actions"]}
        self.assertEqual(by_path["/api/travel"]["method"], "POST")
        self.assertEqual(set(by_path["/api/travel"]["fields"]), {"body_id", "mode"})
        self.assertIn("faction_id", by_path["/api/diplomacy"]["fields"])
        self.assertIn("action", by_path["/api/diplomacy"]["fields"])
        self.assertIn("distance_au", by_path["/api/travel/point"]["fields"])
        self.assertIn("angle", by_path["/api/travel/point"]["fields"])
        self.assertIn("strategy", by_path["/api/salvage"].get("fields", []))
        self.assertIn("action", by_path["/api/customs/resolve"].get("fields", []))
        self.assertIn("rarity", by_path["/api/relics/fuse"].get("fields", []))

    def test_save_family_catalog_includes_slot(self):
        by_path = {entry["path"]: entry for entry in self.catalog["actions"]}
        for path in ("/api/save", "/api/load", "/api/delete-save", "/api/new-game"):
            self.assertIn("slot", by_path[path].get("fields", []), path)

    def test_step_is_documented_as_orbit_only(self):
        from voidfarer.agent_play import CONTEXT_ACTIONS
        self.assertIn("/api/step", CONTEXT_ACTIONS)
        self.assertNotIn("alias", CONTEXT_ACTIONS["/api/step"])
        by_path = {entry["path"]: entry for entry in self.catalog["actions"]}
        self.assertIn("delta_time", by_path["/api/step"].get("fields", []))
        self.assertIn("ticks", by_path["/api/time/step"].get("fields", []))

    def test_observations_include_state(self):
        paths = {entry["path"] for entry in self.catalog["observations"]}
        self.assertIn("/api/state", paths)
        self.assertIn("/api/agent/actions", paths)


class AgentPlayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.engine = SimulationEngine(seed=42)
        cls.engine.allow_decision_events = True
        VoidFarerHandler.engine = cls.engine
        VoidFarerHandler.storage = StorageManager(cls.temp_dir.name)
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"
        cls.server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2.0)
        cls.temp_dir.cleanup()

    def test_catalog_is_served_over_rest(self):
        client = ApiClient(port=self.server.server_port)
        status, payload = client.get("/api/agent/actions")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["actions"])

    def test_ai_captain_plays_without_a_human(self):
        client = ApiClient(port=self.server.server_port)
        report = AiCaptain(client, seed=42).play(steps=50)
        self.assertEqual(report["errors"], [])
        self.assertGreaterEqual(report["family_count"], 6, report["families"])
        self.assertTrue({"travel", "dock", "navigate"} & set(report["families"]))
        self.assertIn("time", report["families"])
        self.assertGreater(report["steps"], 10)
        final = report["final"]
        self.assertGreater(int(final["hull"] or 0), 0)
        self.assertGreaterEqual(int(final["credits"] or 0), 0)
        self.assertIsNotNone(final["tick"])

    def test_every_catalog_action_is_attempted_or_documented(self):
        VoidFarerHandler.engine = SimulationEngine(seed=42)
        VoidFarerHandler.engine.allow_decision_events = True
        client = ApiClient(port=self.server.server_port)
        report = AiCaptain(client, seed=42).play(steps=180)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["coverage_gaps"], [], "every action needs an AI path or a reason")
        self.assertGreaterEqual(report["succeeded_count"], 35, report["succeeded"])
        self.assertGreaterEqual(report["attempted_count"], 45, report["attempted"])
        self.assertGreaterEqual(report["family_count"], 22, report["families"])

    def test_coverage_gap_detection(self):
        self.assertEqual(coverage_gaps(["/api/scan"], {"/api/scan"}), [])
        self.assertEqual(coverage_gaps(["/api/nope"], set()), ["/api/nope"])
        self.assertEqual(coverage_gaps(["/api/save"], set()), [])

    def test_the_engine_state_stays_loadable_after_play(self):
        snapshot = self.engine.get_status_snapshot()
        restored = type(self.engine.state).from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.time.tick, snapshot["time"]["tick"])
        self.assertIsNotNone(restored.ship)


class AiCaptainTourCoverageTest(unittest.TestCase):
    """The fleet and crew alias sub-actions stay reachable from the AI captain."""

    def _captain(self, state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = state
        return captain

    def test_station_map_and_wear_mark_match_the_engine(self):
        self.assertEqual(AiCaptain.STATION_BY_ROLE, SimulationEngine.STATION_BY_ROLE)
        self.assertEqual(AiCaptain.REFIT_WORN_INTEGRITY, SimulationEngine.REFIT_WORN_INTEGRITY)

    def test_autostaff_tour_fires_only_when_the_seating_is_not_optimal(self):
        crew = [{"id": "c1", "role": "pilot", "status": "active", "skill": 4, "xp": 0, "station": ""}]
        self.assertEqual(
            self._captain({"crew": crew})._tour_crew_autostaff(),
            ("/api/crew/action", {"action": "autostaff"}, "crew_autostaff"),
        )
        seated = [dict(crew[0], station="helm")]
        self.assertIsNone(self._captain({"crew": seated})._tour_crew_autostaff())

    def test_refit_tour_needs_a_dock_a_worn_drone_and_credits(self):
        docked = {"orbiting_body": {"station_dockable": True}}
        worn = {"id": "d1", "integrity": 20}

        def action(state):
            return self._captain(state)._tour_fleet_refit_damaged()

        self.assertEqual(
            action({**docked, "ship": {"credits": 300, "fleet_drones": [worn]}}),
            ("/api/fleet/action", {"action": "refit_damaged"}, "fleet_refit"),
        )
        self.assertIsNone(action({"ship": {"credits": 300, "fleet_drones": [worn]}}))
        self.assertIsNone(action({**docked, "ship": {"credits": 300, "fleet_drones": [dict(worn, integrity=80)]}}))
        self.assertIsNone(action({**docked, "ship": {"credits": 299, "fleet_drones": [worn]}}))

    def test_two_alias_subactions_can_fire_in_one_run(self):
        captain = self._captain({
            "orbiting_body": {"station_dockable": True},
            "ship": {"credits": 600, "fleet_drones": [{"id": "d1", "integrity": 20}]},
            "crew": [{"id": "c1", "role": "pilot", "status": "active", "skill": 4, "xp": 0, "station": ""}],
        })
        families = []
        for _ in range(500):
            action = captain._next_tour_action()
            if action is None:
                break
            path, body, family = action
            families.append(family)
            captain.attempted.add(path)
            captain.attempted_signatures.add((path, str((body or {}).get("action") or "")))
        self.assertIn("fleet_refit", families)
        self.assertIn("crew_autostaff", families)


class _StubClient:
    """Minimal API stand-in so play() can be exercised without a server."""

    def __init__(self, state=None):
        self.state = state or {"ship": {"credits": 1000}, "time": {"tick": 0}}

    def get(self, path):
        if path == "/api/agent/actions":
            return 200, {"ok": True, "actions": [{"path": "/api/time/step"}]}
        return 200, {"ok": True, "state": self.state}

    def post(self, path, body):
        return 200, {"ok": True, "state": self.state}


class _RefusingClient(_StubClient):
    def post(self, path, body):
        return 200, {"ok": False, "message": "nope", "state": self.state}


class _FailingClient(_StubClient):
    def post(self, path, body):
        return 500, {"ok": False, "message": "boom", "state": self.state}


class PlayStepCapTest(unittest.TestCase):
    """The CLI honours --steps and says when the runaway guard clamps it (ADR-341)."""

    def test_a_request_beyond_the_guard_is_clamped_and_reported(self):
        captain = AiCaptain(_StubClient(), seed=42)
        captain.MAX_STEPS = 3
        report = captain.play(steps=10)
        self.assertEqual(report["steps"], 3)
        self.assertEqual(report["steps_requested"], 10)
        self.assertTrue(report["steps_capped"])

    def test_a_request_inside_the_guard_runs_in_full_and_is_not_flagged(self):
        captain = AiCaptain(_StubClient(), seed=42)
        report = captain.play(steps=3)
        self.assertEqual(report["steps"], 3)
        self.assertEqual(report["steps_requested"], 3)
        self.assertFalse(report["steps_capped"])

    def test_refusal_count_is_not_truncated_by_the_sample(self):
        report = AiCaptain(_RefusingClient(), seed=42).play(steps=20)
        self.assertEqual(report["refusal_count"], 20)
        self.assertEqual(len(report["refusals"]), 12)
        self.assertGreater(report["refusal_count"], len(report["refusals"]))

    def test_error_count_is_not_truncated_by_the_sample(self):
        report = AiCaptain(_FailingClient(), seed=42).play(steps=20)
        self.assertEqual(report["error_count"], 20)
        self.assertEqual(len(report["errors"]), 12)


class TradeVolumeChoiceTest(unittest.TestCase):
    """Cargo capacity is volume, so the captain must not buy into a full hold (ADR-343)."""

    def _captain(self, ship, quotes=None):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "ship": ship,
            "market_quotes": quotes if quotes is not None else {
                "titanium": {"commodity_id": "titanium", "buy_price": 50}},
        }
        return captain

    def test_a_volume_full_hold_sells_one_unit(self):
        captain = self._captain({
            "cargo": {"titanium": 4}, "cargo_capacity": 40, "cargo_free_volume": 0})
        self.assertEqual(
            captain._trade_choice(4),
            ("/api/trade", {"commodity_id": "titanium", "quantity": 1, "is_buy": False}, "trade"),
        )

    def test_a_volume_full_empty_hold_does_not_attempt_a_buy(self):
        captain = self._captain({
            "cargo": {}, "cargo_capacity": 40, "cargo_free_volume": 0})
        self.assertIsNone(captain._trade_choice(4))

    def test_free_volume_buys_on_even_steps_only(self):
        captain = self._captain({
            "cargo": {}, "cargo_capacity": 40, "cargo_free_volume": 3})
        self.assertTrue(captain._trade_choice(4)[1]["is_buy"])
        self.assertIsNone(captain._trade_choice(5))

    def test_missing_free_volume_falls_back_without_buying_into_a_full_hold(self):
        captain = self._captain({"cargo": {"ore": 40}, "cargo_capacity": 40})
        self.assertEqual(captain._trade_choice(4)[2], "trade")
        self.assertFalse(captain._trade_choice(4)[1]["is_buy"])


class ContractClaimTourTest(unittest.TestCase):
    """Finished contracts are banked, and each contract is claimed at most once (ADR-344)."""

    def _captain(self, contracts):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {"ship": {"active_contracts": contracts}}
        return captain

    def test_a_completed_contract_is_offered_for_claim(self):
        captain = self._captain([
            {"id": "c_open", "completed": False},
            {"id": "c_done", "completed": True},
        ])
        self.assertEqual(
            captain._tour_contract_claim(),
            ("/api/contract/claim", {"contract_id": "c_done"}, "contract_claim"),
        )

    def test_no_completed_contract_means_no_claim(self):
        self.assertIsNone(self._captain([{"id": "c_open", "completed": False}])._tour_contract_claim())

    def test_each_completed_contract_is_claimable_once(self):
        captain = self._captain([
            {"id": "c_done_a", "completed": True},
            {"id": "c_done_b", "completed": True},
        ])
        first = captain._tour_contract_claim()
        self.assertEqual(first[1]["contract_id"], "c_done_a")
        self.assertFalse(captain._tour_action_attempted(first[0], first[1]))
        captain.attempted.add(first[0])
        captain.attempted_signatures.add(captain._tour_signature(first[0], first[1]))
        self.assertTrue(captain._tour_action_attempted(first[0], first[1]))
        second = captain._tour_contract_claim()
        self.assertEqual(second[1]["contract_id"], "c_done_b")
        self.assertFalse(captain._tour_action_attempted(first[0], second[1]))

    def test_the_claim_signature_keys_on_the_contract_id(self):
        captain = self._captain([])
        self.assertEqual(
            captain._tour_signature("/api/contract/claim", {"contract_id": "c1"}),
            ("/api/contract/claim", "c1"),
        )
        self.assertEqual(captain._tour_signature("/api/fleet/action", {"action": "autostaff"}),
                         ("/api/fleet/action", "autostaff"))


class RefusalRetryTest(unittest.TestCase):
    """Affordability refusals are retried after a cooldown; hard refusals are not (ADR-345)."""

    def _captain(self, state=None):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = state or {"ship": {}, "market_quotes": {}}
        return captain

    def test_a_credit_gate_may_pass_later(self):
        captain = self._captain()
        self.assertTrue(captain._refusal_may_pass("Insufficient credits: Aegis Escort Corvette costs 2200 cr."))
        self.assertTrue(captain._refusal_may_pass("Outpost charters require Pilot Mastery level 2"))
        self.assertTrue(captain._refusal_may_pass("No skill points available. Level up the commander first."))

    def test_a_hard_refusal_is_not_retried(self):
        captain = self._captain()
        self.assertFalse(captain._refusal_may_pass("Reactor already operating in balanced mode."))
        self.assertFalse(captain._refusal_may_pass("No derelict salvage is detected here."))

    def test_a_retry_stays_suppressed_until_the_cooldown_passes(self):
        captain = self._captain()
        signature = ("/api/fleet/escort/buy", "")
        captain.attempted.add("/api/fleet/escort/buy")
        captain.attempted_signatures.add(signature)
        captain.retry_at[signature] = 60
        captain.steps_taken = 30
        self.assertTrue(captain._tour_action_attempted(*signature[:1], {}))
        captain.steps_taken = 60
        self.assertFalse(captain._tour_action_attempted("/api/fleet/escort/buy", {}))

    def test_fallback_trades_are_capped(self):
        captain = self._captain({
            "ship": {"cargo": {}, "cargo_capacity": 40, "cargo_free_volume": 5},
            "market_quotes": {"titanium": {"commodity_id": "titanium", "buy_price": 50}},
        })
        taken = [captain._trade_choice(4) for _ in range(captain.MAX_FALLBACK_TRADES)]
        self.assertTrue(all(action is not None for action in taken))
        self.assertIsNone(captain._trade_choice(4))


class EscortTierTourTest(unittest.TestCase):
    """Once an escort is purchased, its role, training, captain and repair are tour steps."""

    def _captain(self, *, docked=True, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "orbiting_body": {"station_dockable": True} if docked else {},
            "ship": {"credits": 1000},
            "fleet_manager": {"ships": []},
            "crew": [],
        }
        base.update(state)
        captain.state = base
        return captain

    def _ship(self, **fields):
        ship = {"id": "e1", "hull": 90, "max_hull": 90, "experience": 10,
                "experience_max": 300, "training_cost": 250,
                "tactical_role": "screen", "captain_id": ""}
        ship.update(fields)
        return ship

    def test_role_flips_between_screen_and_strike(self):
        captain = self._captain(fleet_manager={"ships": [self._ship()]})
        self.assertEqual(captain._tour_escort_role()[1]["role"], "strike")
        captain.state["fleet_manager"]["ships"][0]["tactical_role"] = "strike"
        self.assertEqual(captain._tour_escort_role()[1]["role"], "screen")

    def test_a_destroyed_escort_blocks_every_escort_step(self):
        captain = self._captain(fleet_manager={"ships": [self._ship(hull=0)]})
        self.assertIsNone(captain._tour_escort_role())
        self.assertIsNone(captain._tour_escort_train())
        self.assertIsNone(captain._tour_escort_repair())
        self.assertIsNone(captain._tour_escort_captain())

    def test_training_needs_a_dock_credits_and_room_to_grow(self):
        ship = self._ship()
        self.assertTrue(self._captain(fleet_manager={"ships": [ship]})._tour_escort_train())
        self.assertIsNone(self._captain(docked=False, fleet_manager={"ships": [ship]})._tour_escort_train())
        self.assertIsNone(self._captain(fleet_manager={"ships": [ship]}, ship={"credits": 10})._tour_escort_train())
        ace = self._ship(experience=300)
        self.assertIsNone(self._captain(fleet_manager={"ships": [ace]})._tour_escort_train())

    def test_a_captain_is_assigned_only_to_an_unstaffed_living_escort(self):
        crew = [{"id": "c1", "status": "active", "injury_ticks": 0, "station": ""}]
        captain = self._captain(fleet_manager={"ships": [self._ship()]}, crew=crew)
        self.assertEqual(captain._tour_escort_captain()[1]["crew_id"], "c1")
        staffed = self._captain(fleet_manager={"ships": [self._ship(captain_id="c1")]}, crew=crew)
        self.assertIsNone(staffed._tour_escort_captain())
        assigned_elsewhere = self._captain(
            fleet_manager={"ships": [self._ship(captain_id="c1"), self._ship(id="e2")]}, crew=crew)
        self.assertIsNone(assigned_elsewhere._tour_escort_captain())

    def test_repair_needs_a_dock_and_real_damage(self):
        damaged = self._ship(hull=40)
        self.assertTrue(self._captain(fleet_manager={"ships": [damaged]})._tour_escort_repair())
        self.assertIsNone(self._captain(docked=False, fleet_manager={"ships": [damaged]})._tour_escort_repair())
        self.assertIsNone(self._captain(fleet_manager={"ships": [self._ship()]})._tour_escort_repair())


class AiPlayToolArgsTest(unittest.TestCase):
    def test_rejects_non_positive_steps(self):
        from tools.ai_play import main as ai_play_main
        for bad in ("0", "-5"):
            with self.assertRaises(SystemExit) as ctx:
                ai_play_main(["--steps", bad])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
