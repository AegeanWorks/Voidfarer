"""The headless AI captain must be able to reach and exercise the game without a human."""

import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.agent_api import build_action_catalog
from voidfarer.agent_play import AiCaptain, ApiClient, coverage_gaps
from voidfarer.engine import SimulationEngine
from voidfarer.exploration import DERELICT_EXCLUDED_TYPES, SCOOP_PROFILES
from voidfarer.megastructures import MEGASTRUCTURE_RESTORATION
from voidfarer.outposts import OUTPOST_TYPES
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
        self.assertEqual(AiCaptain.OUTPOST_CHARTER_LEVEL,
                         SimulationEngine.OUTPOST_CHARTER_MASTERY_LEVEL)
        self.assertEqual(AiCaptain.OUTPOST_COSTS,
                         {outpost.id: outpost.cost for outpost in OUTPOST_TYPES})
        self.assertEqual(AiCaptain.MEGASTRUCTURE_TYPES,
                         frozenset(MEGASTRUCTURE_RESTORATION))
        self.assertEqual(AiCaptain.RECONSTRUCTION_COST,
                         SimulationEngine.RECONSTRUCTION_CREDIT_COST)

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

    def post(self, path, body, headers=None):
        return 200, {"ok": True, "state": self.state}


class _RefusingClient(_StubClient):
    def post(self, path, body, headers=None):
        return 200, {"ok": False, "message": "nope", "state": self.state}


class _FailingClient(_StubClient):
    def post(self, path, body, headers=None):
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

    def test_total_steps_accumulate_across_play_calls(self):
        # The retry cooldown must survive a second play() call on the same campaign;
        # measuring it with the per-call counter made late retries permanent (ADR-345).
        captain = AiCaptain(_StubClient(), seed=42)
        captain.play(steps=3)
        self.assertEqual(captain.total_steps, 3)
        captain.play(steps=3)
        self.assertEqual(captain.total_steps, 6)

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
        captain = self._captain({"cargo": {"titanium": 40}, "cargo_capacity": 40})
        self.assertEqual(captain._trade_choice(4)[2], "trade")
        self.assertFalse(captain._trade_choice(4)[1]["is_buy"])

    def test_unquoted_cargo_is_not_offered_to_the_market(self):
        captain = self._captain({"cargo": {"ore": 40}, "cargo_capacity": 40})
        self.assertIsNone(captain._trade_choice(4))


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
        captain.total_steps = 30
        self.assertTrue(captain._tour_action_attempted(*signature[:1], {}))
        captain.total_steps = 60
        self.assertFalse(captain._tour_action_attempted("/api/fleet/escort/buy", {}))

    def test_fallback_trades_are_capped(self):
        captain = self._captain({
            "ship": {"cargo": {}, "cargo_capacity": 40, "cargo_free_volume": 5},
            "market_quotes": {"titanium": {"commodity_id": "titanium", "buy_price": 50}},
        })
        taken = [captain._trade_choice(4) for _ in range(captain.MAX_FALLBACK_TRADES)]
        self.assertTrue(all(action is not None for action in taken))
        self.assertIsNone(captain._trade_choice(4))

    def test_a_gate_that_opens_late_is_retried_on_a_slow_horizon(self):
        captain = self._captain()
        signature = ("/api/fleet/escort/buy", "")
        message = "Insufficient credits: 3200 cr required."
        captain.total_steps = 100
        captain._note_refusal(signature, message)
        self.assertEqual(captain.retry_at[signature], 100 + captain.REFUSAL_RETRY_STEPS)
        captain.total_steps = 200
        captain._note_refusal(signature, message)
        captain.total_steps = 300
        captain._note_refusal(signature, message)
        self.assertEqual(captain.retry_at[signature], 300 + captain.SLOW_RETRY_STEPS,
                         "the third attempt must fall back to the slow horizon")
        captain.attempted.add(signature[0])
        captain.total_steps = 300 + captain.SLOW_RETRY_STEPS - 1
        self.assertTrue(captain._tour_action_attempted(signature[0], {}))
        captain.total_steps = 300 + captain.SLOW_RETRY_STEPS
        self.assertFalse(captain._tour_action_attempted(signature[0], {}),
                         "a released gate stays available until the action is attempted")

    def test_a_never_opening_gate_is_still_bounded(self):
        captain = self._captain()
        signature = ("/api/fleet/escort/buy", "")
        message = "Insufficient credits: 3200 cr required."
        for attempt in range(1, captain.SLOW_RETRY_LIMIT + 1):
            captain.total_steps = attempt * 100
            captain._note_refusal(signature, message)
        self.assertNotIn(signature, captain.retry_at,
                         "the slow budget must end, not extend forever")
        captain.attempted.add(signature[0])
        self.assertTrue(captain._tour_action_attempted(signature[0], {}))

    def test_a_hard_refusal_never_schedules_a_retry(self):
        captain = self._captain()
        signature = ("/api/reactor/mode", "balanced")
        for attempt in range(3):
            captain.total_steps = attempt * 100
            captain._note_refusal(signature, "Reactor already operating in balanced mode.")
        self.assertNotIn(signature, captain.retry_at)

    def test_a_success_clears_the_retry_budget(self):
        captain = self._captain()
        signature = ("/api/fleet/escort/buy", "buy")
        captain._note_refusal(signature, "Insufficient credits: 3200 cr required.")
        self.assertIn(signature, captain.retry_at)
        captain.retry_at.pop(signature, None)
        captain.refusal_attempts.pop(signature, None)
        self.assertNotIn(signature, captain.refusal_attempts)


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


class OutpostTierTourTest(unittest.TestCase):
    """A founded outpost exposes upgrade, module, crew, repair and specialize steps (ADR-346)."""

    def _captain(self, *, credits=5000, outposts=None, crew=None, ships=None):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "ship": {"credits": credits},
            "outposts": outposts or [],
            "outpost_catalog": [{"id": "research", "cost": 2200}],
            "outpost_options": ["research"],
            "outpost_modules": {"laboratory": {"cost": 500}, "solar_array": {"cost": 300}},
            "crew": crew or [],
            "fleet_manager": {"ships": ships or []},
            "orbiting_body": {"id": "mars_body_1"},
        }
        return captain

    def _outpost(self, **fields):
        outpost = {"id": "o1", "level": 1, "modules": {"laboratory": 1}, "assigned_crew": [],
                   "crew_capacity": 3, "integrity": 100.0, "repair_cost": 100,
                   "specialization": "", "specialization_cost": 600}
        outpost.update(fields)
        return outpost

    def test_upgrade_cost_matches_the_engine_scale(self):
        from voidfarer.models import Outpost
        from voidfarer.outposts import upgrade_outpost
        outpost = Outpost(id="o1", name="Test", system_id="sol", body_id="b1", level=2)
        ok, _upgraded, cost, _msg = upgrade_outpost(outpost)
        self.assertTrue(ok)
        self.assertEqual(cost, AiCaptain.OUTPOST_UPGRADE_COST_PER_LEVEL * 2)

    def test_build_is_attempted_at_a_buildable_site_even_when_broke(self):
        # Affordability is a gameplay gate: the attempt must still happen once so the
        # mechanics gate covers the endpoint; the retry policy re-tries it later (ADR-346).
        poor = self._captain(credits=0)
        self.assertEqual(poor._tour_outpost()[2], "outpost")

    def test_upgrade_gates_on_level_and_credits(self):
        captain = self._captain(outposts=[self._outpost(level=1)])
        self.assertEqual(captain._tour_outpost_upgrade()[2], "outpost_upgrade")
        self.assertIsNone(self._captain(credits=100, outposts=[self._outpost(level=1)])._tour_outpost_upgrade())
        self.assertIsNone(self._captain(outposts=[self._outpost(level=5)])._tour_outpost_upgrade())

    def test_each_upgrade_level_is_its_own_action(self):
        captain = self._captain(outposts=[self._outpost(level=1)])
        captain.attempted.add("/api/outpost/upgrade")
        captain.attempted_signatures.add(("/api/outpost/upgrade", "1"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/outpost/upgrade", {"outpost_id": "o1", "level": 1}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/outpost/upgrade", {"outpost_id": "o1", "level": 2}),
            "a level-2 upgrade must stay available after level 1")

    def test_module_picks_the_cheapest_stack_below_three(self):
        captain = self._captain(outposts=[self._outpost(modules={"laboratory": 3})])
        action = captain._tour_outpost_module()
        self.assertEqual(action[1]["module_id"], "solar_array")
        full = self._captain(outposts=[self._outpost(modules={"laboratory": 3, "solar_array": 3})])
        self.assertIsNone(full._tour_outpost_module())

    def test_crew_needs_an_active_free_specialist_and_capacity(self):
        crew = [{"id": "c1", "status": "active", "injury_ticks": 0, "station": ""}]
        captain = self._captain(crew=crew, outposts=[self._outpost()])
        self.assertEqual(captain._tour_outpost_crew()[1]["crew_id"], "c1")
        stationed = self._captain(crew=crew, outposts=[self._outpost(assigned_crew=["c1"])])
        self.assertIsNone(stationed._tour_outpost_crew())
        full = self._captain(crew=crew, outposts=[self._outpost(assigned_crew=["a", "b", "d"])])
        self.assertIsNone(full._tour_outpost_crew())
        captain_with_escort = self._captain(
            crew=crew, outposts=[self._outpost()],
            ships=[{"id": "e1", "captain_id": "c1"}])
        self.assertIsNone(captain_with_escort._tour_outpost_crew())

    def test_repair_needs_damage_and_credits(self):
        damaged = self._outpost(integrity=40.0)
        self.assertEqual(self._captain(outposts=[damaged])._tour_outpost_repair()[2], "outpost_repair")
        self.assertIsNone(self._captain(outposts=[self._outpost()])._tour_outpost_repair())
        self.assertIsNone(self._captain(credits=50, outposts=[damaged])._tour_outpost_repair())

    def test_specialize_needs_level_three_and_credits(self):
        level3 = self._outpost(level=3)
        self.assertEqual(self._captain(outposts=[level3])._tour_outpost_specialize()[1]["specialization"], "industry")
        self.assertIsNone(self._captain(outposts=[self._outpost(level=2)])._tour_outpost_specialize())
        self.assertIsNone(self._captain(credits=100, outposts=[level3])._tour_outpost_specialize())


class CampaignPhaseTest(unittest.TestCase):
    """play() resumes the campaign clock and never jumps on an empty tank (ADR-347)."""

    def _captain(self, fuel=10):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "ship": {"hull": 100, "fuel": fuel, "cargo": {}, "cargo_capacity": 40,
                     "cargo_free_volume": 40},
            "current_system": {"id": "sol", "connections": ["altair"]},
            "market_quotes": {},
        }
        return captain

    def test_batched_play_calls_continue_the_global_phase(self):
        seen = []

        class Recording(AiCaptain):
            def _choose(inner_self, step):
                seen.append(step)
                return "/api/time/step", {"ticks": 1}, "time"

        captain = Recording(_StubClient(), seed=42)
        captain.state = self._captain().state
        captain.play(steps=2)
        captain.play(steps=2)
        self.assertEqual(seen, [0, 1, 2, 3])

    def test_a_jump_is_attempted_with_fuel(self):
        action = self._captain(fuel=10)._choose(5)
        self.assertEqual(action[0], "/api/jump")

    def test_an_empty_tank_does_not_attempt_a_jump(self):
        action = self._captain(fuel=0)._choose(5)
        self.assertNotEqual(action[0], "/api/jump")

    def test_the_published_hop_cost_decides_the_attempt(self):
        captain = self._captain(fuel=1)
        captain.state["jump_fuel_costs"] = {"altair": 4}
        self.assertNotEqual(captain._choose(5)[0], "/api/jump")
        captain.state["ship"]["fuel"] = 4
        self.assertEqual(captain._choose(5)[0], "/api/jump")


class OutpostTierEndToEndTest(unittest.TestCase):
    """A seeded outpost really is upgraded, fitted, crewed and specialized via the API (ADR-347)."""

    @classmethod
    def setUpClass(cls):
        from voidfarer.models import Outpost
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.engine = SimulationEngine(seed=42)
        cls.engine.allow_decision_events = True
        cls.engine.state = cls.engine._clone_state(
            ship=cls.engine._clone_ship(credits=9000),
            outposts=(
                Outpost(
                    id="outpost_test_1", name="Test Anchor", system_id="sol",
                    body_id="sol_body_1", outpost_type="mining", level=3,
                    modules={"extractor": 1}, integrity=100.0,
                ),
                Outpost(
                    id="outpost_test_2", name="Test Redoubt", system_id="sol",
                    body_id="sol_body_2", outpost_type="shipyard", level=5,
                    modules={"drydock": 1}, integrity=55.0,
                ),
            ),
        )
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

    def test_the_captain_manages_the_seeded_outpost(self):
        captain = AiCaptain(ApiClient(port=self.server.server_port), seed=42)
        report = captain.play(steps=90)
        self.assertEqual(report["errors"], [], report["errors"])
        families = report["families"]
        for expected in ("outpost_upgrade", "outpost_module", "outpost_repair",
                         "outpost_specialize"):
            self.assertIn(expected, families, families)
        outpost = next(o for o in captain.state["outposts"] if o["id"] == "outpost_test_1")
        self.assertGreaterEqual(outpost["level"], 4)
        self.assertGreaterEqual(sum(outpost["modules"].values()), 2)
        self.assertTrue(outpost["specialization"])
        repaired = next(o for o in captain.state["outposts"] if o["id"] == "outpost_test_2")
        self.assertEqual(repaired["integrity"], 100.0)


class RepeatableUpkeepTest(unittest.TestCase):
    """Refuelling is upkeep, not a once-per-run achievement (ADR-349)."""

    def test_refuel_repeats_only_after_its_cooldown(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        signature = ("/api/refuel", "")
        captain.total_steps = 100
        captain.repeat_last[signature] = 100
        captain.total_steps = 120
        self.assertTrue(captain._tour_action_attempted("/api/refuel", {}))
        captain.total_steps = 160
        self.assertFalse(captain._tour_action_attempted("/api/refuel", {}))

    def test_it_still_needs_a_first_attempt(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        self.assertFalse(captain._tour_action_attempted("/api/refuel", {}))

    def test_ordinary_routes_keep_one_shot_behaviour(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.total_steps = 500
        captain.attempted.add("/api/scan")
        self.assertTrue(captain._tour_action_attempted("/api/scan", {}))


class PausedClockTest(unittest.TestCase):
    """A paused campaign clock is resumed before anything else (ADR-349)."""

    def _captain(self, paused):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "ship": {"hull": 100, "fuel": 10, "cargo": {}, "cargo_capacity": 40,
                     "cargo_free_volume": 40},
            "time": {"tick": 10, "is_paused": paused},
            "current_system": {"id": "sol", "connections": []},
            "market_quotes": {},
        }
        return captain

    def test_a_paused_clock_is_resumed(self):
        self.assertEqual(self._captain(True)._choose(0)[0], "/api/time/resume")

    def test_a_running_clock_is_left_alone(self):
        self.assertNotEqual(self._captain(False)._choose(0)[0], "/api/time/resume")


class DestroyedHullTest(unittest.TestCase):
    """A destroyed hull stops the clock, so the captain claims insurance first (ADR-349)."""

    def test_insurance_is_claimed_before_anything_else(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "ship": {"hull": 0, "fuel": 10, "cargo": {}, "cargo_capacity": 40,
                     "cargo_free_volume": 40},
            "time": {"tick": 10, "is_paused": True},
            "current_system": {"id": "sol", "connections": []},
            "market_quotes": {},
        }
        self.assertEqual(captain._choose(0)[0], "/api/engineering/action")
        self.assertEqual(captain._choose(0)[1], {"action": "insurance"})

    def test_a_living_hull_does_not_claim_insurance(self):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "ship": {"hull": 40, "fuel": 10, "cargo": {}, "cargo_capacity": 40,
                     "cargo_free_volume": 40},
            "time": {"tick": 10, "is_paused": False},
            "current_system": {"id": "sol", "connections": []},
            "market_quotes": {},
        }
        self.assertNotEqual(captain._choose(0)[0], "/api/engineering/action")


class DroneCollectTourTest(unittest.TestCase):
    """Drone haul is banked when it exists, and selling to unjam the hold is never capped (ADR-350)."""

    def _captain(self, drones, credits=0, cargo=None, free=None):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "ship": {"hull": 100, "credits": credits,
                     "fleet_drones": drones,
                     "cargo": cargo if cargo is not None else {},
                     "cargo_capacity": 40,
                     "cargo_free_volume": free if free is not None else 40},
            "market_quotes": {"titanium": {"commodity_id": "titanium", "buy_price": 50}},
        }
        return captain

    def _drone(self, cargo=0, credits=0):
        return {"id": "d1", "drone_type": "mining", "cargo_accumulated": cargo,
                "credits_accumulated": credits}

    def test_yield_is_collected(self):
        captain = self._captain([self._drone(cargo=3)])
        self.assertEqual(captain._tour_drone_collect()[2], "drone_collect")

    def test_no_yield_means_no_collect(self):
        self.assertIsNone(self._captain([self._drone()])._tour_drone_collect())

    def test_a_full_hold_blocks_indivisible_cargo_but_not_credits(self):
        self.assertIsNone(self._captain([self._drone(cargo=3)], free=0)._tour_drone_collect())
        self.assertIsNone(self._captain([self._drone(cargo=3)], free=1)._tour_drone_collect())
        self.assertEqual(self._captain([self._drone(credits=80)], free=0)._tour_drone_collect()[2],
                         "drone_collect")

    def test_the_volume_constant_matches_the_catalog(self):
        from voidfarer.inventory import get_item_info
        self.assertEqual(AiCaptain.TITANIUM_VOLUME, get_item_info("titanium").volume)

    def test_a_destroyed_hull_collects_nothing(self):
        captain = self._captain([self._drone(cargo=3)])
        captain.state["ship"]["hull"] = 0
        self.assertIsNone(captain._tour_drone_collect())

    def test_selling_out_of_a_full_hold_ignores_the_buy_cap(self):
        captain = self._captain([], cargo={"titanium": 20}, free=0)
        captain.fallback_trades = captain.MAX_FALLBACK_TRADES
        action = captain._trade_choice(4)
        self.assertEqual(action[2], "trade")
        self.assertFalse(action[1]["is_buy"])


class ShipModInstallTourTest(unittest.TestCase):
    """The captain fits a structural mod, not just removes one (ADR-352)."""

    def _captain(self, *, docked=True, credits=5000, installed=None, used=0):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "orbiting_body": {"station_dockable": True} if docked else {},
            "ship": {"credits": credits, "cargo_capacity": 40, "cargo_used_volume": used},
            "ship_mods": {
                "installed": installed or {},
                "catalog": [
                    {"id": "cheap", "slot": "ops", "cost": 300, "effects": {}},
                    {"id": "hangar", "slot": "frame", "cost": 1600,
                     "effects": {"cargo_capacity": 30}},
                    {"id": "tight", "slot": "thermal", "cost": 900,
                     "effects": {"cargo_capacity": -20}},
                ],
            },
        }
        return captain

    def test_a_free_slot_is_fitted_with_the_cheapest_affordable_mod(self):
        action = self._captain()._tour_shipmods()
        self.assertEqual(action[0], "/api/shipmods/install")
        self.assertEqual(action[1]["mod_id"], "cheap")

    def test_it_needs_a_dock_and_credits(self):
        self.assertIsNone(self._captain(docked=False)._tour_shipmods())
        self.assertIsNone(self._captain(credits=0)._tour_shipmods())

    def test_a_mod_that_would_overflow_cargo_is_skipped(self):
        # 35 volume used + -20 capacity would overflow the 40-volume hold.
        action = self._captain(credits=1000, used=35)._tour_shipmods()
        self.assertEqual(action[1]["mod_id"], "cheap", "the cheap ops mod has no capacity cost")

    def test_an_occupied_slot_is_left_alone(self):
        action = self._captain(installed={"ops": "cheap"})._tour_shipmods()
        self.assertNotEqual(action[1]["mod_id"], "cheap")
        self.assertIn(action[1]["mod_id"], ("hangar", "tight"))


    def test_a_capacity_shedding_mod_is_not_chosen_for_a_full_hold(self):
        # 19 titanium = 38 of 40 volume; the cheapest mods shed capacity, so the neutral
        # salvage processor must be preferred or every attempt overflows (ADR-352).
        captain = self._captain(credits=5000, used=38)
        captain.state["ship_mods"]["catalog"] = [
            {"id": "shunt", "slot": "thermal", "cost": 900, "effects": {"cargo_capacity": -15}},
            {"id": "salvage", "slot": "ops", "cost": 1300, "effects": {}},
        ]
        self.assertEqual(captain._tour_shipmods()[1]["mod_id"], "salvage")

    def test_each_mod_id_gets_its_own_attempt_slot(self):
        # Keying installs on the path meant one refusal locked every later mod (ADR-352).
        captain = self._captain()
        signature = captain._tour_signature("/api/shipmods/install", {"mod_id": "cheap"})
        self.assertEqual(signature, ("/api/shipmods/install", "cheap"))
        captain.attempted.add("/api/shipmods/install")
        captain.attempted_signatures.add(signature)
        self.assertTrue(captain._tour_action_attempted("/api/shipmods/install", {"mod_id": "cheap"}))
        self.assertFalse(captain._tour_action_attempted("/api/shipmods/install", {"mod_id": "hangar"}))


class ReachableMechanicsTourTest(unittest.TestCase):
    """Depot, research, fabrication and crew stations stay on the guided tour (ADR-353)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "orbiting_body": {"station_dockable": True},
            "current_system": {"id": "sol", "connections": []},
            "ship": {"hull": 100, "max_hull": 100, "fuel": 60, "max_fuel": 60,
                     "credits": 500, "cargo": {}, "cargo_free_volume": 40},
            "depots": [{"system_id": "sol", "cargo": {}}],
            "research": {"available": [], "completed": [], "queue": [],
                         "active_project_id": None},
            "crew": [],
            "outposts": [],
            "fleet_manager": {"ships": []},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_deposit_stock_allows_withdraw_and_sell(self):
        depot = {"system_id": "sol", "cargo": {"titanium": 4}}
        captain = self._captain(depots=[depot])
        self.assertEqual(captain._tour_depot_withdraw()[2], "depot_withdraw")
        self.assertEqual(captain._tour_depot_sell()[2], "depot_sell")

    def test_withdraw_needs_room_and_stock(self):
        captain = self._captain(depots=[{"system_id": "sol", "cargo": {"titanium": 2}}])
        captain.state["ship"]["cargo_free_volume"] = 1
        self.assertIsNone(captain._tour_depot_withdraw())
        empty = self._captain(depots=[{"system_id": "sol", "cargo": {}}])
        self.assertIsNone(empty._tour_depot_sell())

    def test_deposit_moves_three_when_stock_allows(self):
        captain = self._captain(inventory_manifest=[{"id": "titanium", "quantity": 5}])
        self.assertEqual(captain._tour_depot()[1]["quantity"], 3)
        captain.state["inventory_manifest"] = [{"id": "titanium", "quantity": 1}]
        self.assertEqual(captain._tour_depot()[1]["quantity"], 1)

    def test_research_queue_skips_active_queued_and_completed(self):
        captain = self._captain(research={
            "available": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
            "completed": ["a"], "queue": ["b"], "active_project_id": None,
        })
        self.assertEqual(captain._tour_research_queue()[1]["project_id"], "c")

    def test_research_cancel_needs_a_queued_project(self):
        self.assertIsNone(self._captain()._tour_research_cancel())
        queued = self._captain(research={"available": [], "completed": [], "queue": ["x"],
                                         "active_project_id": None})
        self.assertEqual(queued._tour_research_cancel()[1]["project_id"], "x")

    def test_fabrication_targets_hull_then_fuel(self):
        damaged = self._captain(ship={"hull": 40})
        damaged.state["ship"]["cargo"] = {"titanium": 2}
        self.assertEqual(damaged._tour_fabricate()[1]["munitions_type"], "patch_kit")
        low_fuel = self._captain(ship={"fuel": 10})
        low_fuel.state["ship"]["cargo"] = {"titanium": 2}
        self.assertEqual(low_fuel._tour_fabricate()[1]["munitions_type"], "fuel_cell")
        full = self._captain()
        full.state["ship"]["cargo"] = {"titanium": 2}
        self.assertIsNone(full._tour_fabricate())

    def test_crew_station_maps_the_role_and_skips_committed_specialists(self):
        crew = [{"id": "c1", "role": "engineer", "status": "active",
                 "injury_ticks": 0, "station": ""}]
        captain = self._captain(crew=crew)
        self.assertEqual(captain._tour_crew_station()[1]["station"], "engineering")
        stationed = self._captain(crew=[dict(crew[0], station="engineering")])
        self.assertIsNone(stationed._tour_crew_station())
        on_escort = self._captain(crew=crew,
                                  fleet_manager={"ships": [{"id": "e1", "captain_id": "c1"}]})
        self.assertIsNone(on_escort._tour_crew_station())

    def test_overhaul_needs_wear_a_dock_and_credits(self):
        worn = {"wear": 8.0}
        quote = {"overhaul_cost": 160}
        captain = self._captain(ship=worn, drydock=quote)
        self.assertEqual(captain._tour_overhaul()[2], "overhaul")
        self.assertIsNone(self._captain(ship={"wear": 0.0}, drydock={"overhaul_cost": 0})
                          ._tour_overhaul())
        undocked = self._captain(ship=worn, drydock=quote)
        undocked.state["orbiting_body"] = {}
        self.assertIsNone(undocked._tour_overhaul())
        poor = self._captain(ship={"wear": 8.0, "credits": 10}, drydock=quote)
        self.assertIsNone(poor._tour_overhaul())


class NarrativeAndCrewTourTest(unittest.TestCase):
    """Story choices, messaging, shore leave and away recall are reachable (ADR-354)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "orbiting_body": {"station_dockable": True},
            "ship": {"hull": 100, "max_hull": 100, "fuel": 60, "max_fuel": 60,
                     "credits": 500, "cargo": {}, "cargo_free_volume": 40,
                     "landed_body_id": None, "away_missions": []},
            "crew": [], "messages": [], "story_status": {}, "surface_report": {},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_a_ready_chapter_choice_is_taken(self):
        captain = self._captain(story_status={
            "ready": True, "completed": False,
            "choices": [{"id": "locked_one", "locked": True},
                        {"id": "open_one", "locked": False}],
        })
        self.assertEqual(captain._tour_story_choice()[1]["choice_id"], "open_one")

    def test_a_completed_or_unready_story_is_left_alone(self):
        self.assertIsNone(self._captain(story_status={"ready": False, "completed": False,
                                                      "choices": [{"id": "c", "locked": False}]})
                          ._tour_story_choice())
        self.assertIsNone(self._captain(story_status={"ready": True, "completed": True,
                                                      "choices": [{"id": "c", "locked": False}]})
                          ._tour_story_choice())

    def test_a_message_is_sent_to_the_first_correspondent(self):
        captain = self._captain(messages=[{"sender": "Admiral Vance"}])
        self.assertEqual(captain._tour_message_send()[1]["recipient"], "Admiral Vance")
        self.assertIsNone(self._captain()._tour_message_send())

    def test_shore_leave_waits_for_morale_to_drop(self):
        peak = [{"id": "c1", "status": "active", "morale": 100.0}]
        tired = [{"id": "c1", "status": "active", "morale": 62.0}]
        self.assertIsNone(self._captain(crew=peak)._tour_shore_leave())
        self.assertEqual(self._captain(crew=tired)._tour_shore_leave()[2], "crew_shore")

    def test_away_recall_needs_an_active_mission(self):
        self.assertIsNone(self._captain()._away_recall_action())
        captain = self._captain(ship={"away_missions": [{"id": "m1"}, {"id": "m2"}]})
        captain.away_protected_mission = "m1"
        self.assertEqual(captain._away_recall_action()[1]["mission_id"], "m2")

    def test_surface_operation_follows_landing_directly(self):
        captain = self._captain(
            ship={"landed_body_id": "b1"},
            orbiting_body={"id": "b1", "scan_completed": True},
            surface_report={"landed": True, "operations": [
                {"id": "survey", "available": True, "used": False},
            ]},
        )
        action = captain._choose(7)
        self.assertEqual(action[0], "/api/surface/op")
        self.assertEqual(action[1]["operation_id"], "survey")

    def test_a_used_surface_operation_is_not_repeated(self):
        captain = self._captain(
            ship={"landed_body_id": "b1"},
            orbiting_body={"id": "b1", "scan_completed": True},
            surface_report={"landed": True, "operations": [
                {"id": "survey", "available": True, "used": True},
            ]},
        )
        self.assertNotEqual(captain._choose(7)[0], "/api/surface/op")


class CombatPolicyTest(unittest.TestCase):
    """Combat is chosen by state, so survival actions and the tactical surface are used (ADR-362)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "ship": {
                "hull": 100, "max_hull": 100, "shield": 60, "max_shield": 60, "fuel": 40,
                "reactor": {"heat": 10.0, "max_heat": 100.0, "heat_pct": 10.0,
                            "last_vent_tick": -999},
                "power": {"engines": 25, "shields": 25, "sensors": 25, "weapons": 25},
                "fleet_drones": [], "cargo": {},
            },
            "active_combat": {
                "id": "c1", "enemy_hull": 100, "enemy_max_hull": 100,
                "enemy_shield": 0, "enemy_max_shield": 0, "enemy_damage": 15,
                "enemy_intent": "fire", "enemy_engines_disabled": False,
            },
            "crew": [],
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def _action(self, **state):
        return self._captain(**state)._choose(7)

    def test_a_plain_fight_fires_lasers(self):
        self.assertEqual(self._action()[1]["action"], "fire_lasers")

    def test_a_critical_hull_flees_when_the_tank_allows(self):
        self.assertEqual(self._action(ship={"hull": 20, "fuel": 30})[1]["action"], "flee")
        short = self._action(ship={"hull": 20, "fuel": 5})
        self.assertNotEqual(short[1]["action"], "flee")
        self.assertEqual(short[1]["action"], "evasive_burn")

    def test_a_damaged_hull_burns_once(self):
        captain = self._captain(ship={"hull": 35, "fuel": 40})
        self.assertEqual(captain._choose(7)[1]["action"], "evasive_burn")
        self.assertNotEqual(captain._choose(7)[1]["action"], "evasive_burn")

    def test_a_hot_reactor_vents_once(self):
        captain = self._captain(ship={"reactor": {
            "heat": 90.0, "max_heat": 100.0, "heat_pct": 90.0, "last_vent_tick": -999,
        }})
        self.assertEqual(captain._choose(7)[1]["action"], "vent_heat")
        self.assertNotEqual(captain._choose(7)[1]["action"], "vent_heat")

    def test_low_shields_absorb_the_barrage(self):
        captain = self._captain(ship={"hull": 60, "shield": 10})
        self.assertEqual(captain._choose(7)[1]["action"], "shield_absorb")
        self.assertNotEqual(captain._choose(7)[1]["action"], "shield_absorb",
                            "absorbing forever would never damage the enemy")

    def test_enemy_engines_are_targeted_when_it_tries_to_evade(self):
        captain = self._captain(active_combat={"enemy_intent": "evade"})
        self.assertEqual(captain._choose(7)[1]["action"], "target_engines")
        self.assertNotEqual(captain._choose(7)[1]["action"], "target_engines")

    def test_high_enemy_damage_targets_weapons_once(self):
        captain = self._captain(active_combat={"enemy_damage": 30})
        self.assertEqual(captain._choose(7)[1]["action"], "target_weapons")
        self.assertNotEqual(captain._choose(7)[1]["action"], "target_weapons")

    def test_high_enemy_shields_are_ion_pulsed_once(self):
        captain = self._captain(active_combat={"enemy_shield": 60, "enemy_max_shield": 60})
        self.assertEqual(captain._choose(7)[1]["action"], "target_shields")
        self.assertNotEqual(captain._choose(7)[1]["action"], "target_shields")

    def test_a_crippled_enemy_is_boarded_with_a_healthy_marine(self):
        marine = [{"id": "m1", "role": "marine", "status": "active", "injury_ticks": 0}]
        captain = self._captain(active_combat={"enemy_hull": 20}, crew=marine)
        self.assertEqual(captain._choose(7)[1]["action"], "board_enemy")
        hurt = [{"id": "m1", "role": "marine", "status": "active", "injury_ticks": 3}]
        self.assertNotEqual(self._action(active_combat={"enemy_hull": 20}, crew=hurt)[1]["action"],
                            "board_enemy")

    def test_a_tactical_drone_strikes(self):
        captain = self._captain(ship={"fleet_drones": [{"drone_type": "combat_escort"}]})
        self.assertEqual(captain._choose(7)[1]["action"], "drone_strike")

    def test_a_fuel_less_fight_uses_a_held_decoy(self):
        captain = self._captain(ship={
            "hull": 25, "fuel": 2, "cargo": {"decoy_countermeasure": 1},
        })
        action = captain._choose(7)
        self.assertEqual(action[0], "/api/inventory/use")
        self.assertEqual(action[1], {"item_id": "decoy_countermeasure"})
        self.assertNotEqual(captain._choose(7)[1].get("item_id"), "decoy_countermeasure",
                            "one decoy buys one escape, not a loop")

    def test_the_decoy_finishes_an_escape_after_the_burn_is_spent(self):
        captain = self._captain(ship={
            "hull": 25, "fuel": 5, "cargo": {"decoy_countermeasure": 1},
        })
        captain.combat_used.setdefault("c1", set()).add("evasive_burn")
        action = captain._choose(7)
        self.assertEqual(action[0], "/api/inventory/use")
        self.assertEqual(action[1], {"item_id": "decoy_countermeasure"})

    def test_the_decoy_waits_while_fuel_can_still_escape(self):
        fueled = self._captain(ship={
            "hull": 20, "fuel": 5, "cargo": {"decoy_countermeasure": 1},
        })
        self.assertEqual(fueled._choose(7)[1]["action"], "evasive_burn")
        healthy = self._captain(ship={
            "hull": 60, "fuel": 2, "cargo": {"decoy_countermeasure": 1},
        })
        self.assertNotEqual(healthy._choose(7)[0], "/api/inventory/use")
        empty = self._captain(ship={"hull": 25, "fuel": 2})
        self.assertNotEqual(empty._choose(7)[0], "/api/inventory/use")

    def test_a_hot_but_safe_reactor_uses_point_defense(self):
        captain = self._captain(ship={"reactor": {
            "heat": 70.0, "max_heat": 100.0, "heat_pct": 70.0, "last_vent_tick": -999,
        }})
        self.assertEqual(captain._choose(7)[1]["action"], "point_defense")
        self.assertNotEqual(captain._choose(7)[1]["action"], "point_defense")

    def test_a_threatened_hull_attempts_a_bridge_strike(self):
        captain = self._captain(ship={"hull": 50})
        self.assertEqual(captain._choose(7)[1]["action"], "target_bridge")


class CombatGambitPolicyTest(unittest.TestCase):
    """The captain recalls an armed escort and spends its once-per-battle gambit (ADR-397)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "ship": {
                "hull": 100, "max_hull": 100, "shield": 60, "max_shield": 60,
                "fuel": 40,
                "reactor": {"heat": 10.0, "max_heat": 100.0, "heat_pct": 10.0,
                            "last_vent_tick": -999},
                "power": {"engines": 25, "shields": 25, "sensors": 25, "weapons": 25},
                "fleet_drones": [], "cargo": {},
            },
            "active_combat": {
                "id": "c1", "enemy_hull": 100, "enemy_max_hull": 100,
                "enemy_shield": 40, "enemy_max_shield": 40, "enemy_damage": 15,
                "enemy_intent": "fire", "enemy_engines_disabled": False,
                "captain_gambit_used": False, "captain_evasion_bonus": 0.0,
            },
            "current_system": {"id": "ashen"},
            "crew": [
                {"id": "crew_engineer_4", "role": "engineer", "status": "active",
                 "injury_ticks": 0},
            ],
            "fleet_manager": {"ships": [
                {"id": "escort_1", "hull": 90, "max_hull": 90, "shield": 60,
                 "max_shield": 60, "assigned_system_id": "ashen",
                 "captain_id": "crew_engineer_4"},
            ]},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_an_armed_local_escort_spends_a_ready_gambit(self):
        captain = self._captain(ship={"hull": 60})
        self.assertEqual(captain._gambit_action(),
                         ("/api/combat/gambit", {}, "combat_gambit"))

    def test_a_remote_armed_escort_is_recalled_first(self):
        captain = self._captain(
            fleet_manager={"ships": [
                {"id": "escort_1", "hull": 90, "max_hull": 90, "shield": 60,
                 "max_shield": 60, "assigned_system_id": "cyclops",
                 "captain_id": "crew_engineer_4"},
            ]})
        self.assertEqual(
            captain._gambit_action(),
            ("/api/fleet/escort/assign",
             {"ship_id": "escort_1", "system_id": "ashen"}, "escort_assign"),
        )

    def test_a_failed_recall_is_not_retried(self):
        captain = self._captain(
            fleet_manager={"ships": [
                {"id": "escort_1", "hull": 90, "max_hull": 90, "shield": 60,
                 "max_shield": 60, "assigned_system_id": "cyclops",
                 "captain_id": "crew_engineer_4"},
            ]})
        self.assertEqual(captain._gambit_action()[0], "/api/fleet/escort/assign")
        self.assertIsNone(captain._gambit_action())

    def test_a_spent_battle_gambit_is_not_repeated(self):
        captain = self._captain(active_combat={"captain_gambit_used": True})
        self.assertIsNone(captain._gambit_action())

    def test_the_campaign_spends_the_gambit_once(self):
        captain = self._captain()
        captain.attempted.add("/api/combat/gambit")
        self.assertIsNone(captain._gambit_action())

    def test_an_unarmed_escort_has_no_gambit(self):
        captain = self._captain(
            fleet_manager={"ships": [
                {"id": "escort_1", "hull": 90, "max_hull": 90, "shield": 60,
                 "max_shield": 60, "assigned_system_id": "ashen", "captain_id": ""},
            ]},
            crew=[])
        self.assertIsNone(captain._gambit_action())

    def test_an_engineer_waits_for_hull_damage(self):
        self.assertIsNone(self._captain()._gambit_action())

    def test_a_pilot_gambit_is_ready_at_the_start_of_a_flight(self):
        captain = self._captain(
            crew=[{"id": "crew_pilot_1", "role": "pilot", "status": "active",
                   "injury_ticks": 0}],
            fleet_manager={"ships": [
                {"id": "escort_1", "hull": 90, "max_hull": 90, "shield": 60,
                 "max_shield": 60, "assigned_system_id": "ashen",
                 "captain_id": "crew_pilot_1"},
            ]})
        self.assertEqual(captain._gambit_action()[0], "/api/combat/gambit")
        capped = self._captain(
            active_combat={"captain_evasion_bonus": 0.35},
            crew=[{"id": "crew_pilot_1", "role": "pilot", "status": "active",
                   "injury_ticks": 0}],
            fleet_manager={"ships": [
                {"id": "escort_1", "hull": 90, "max_hull": 90, "shield": 60,
                 "max_shield": 60, "assigned_system_id": "ashen",
                 "captain_id": "crew_pilot_1"},
            ]})
        self.assertIsNone(capped._gambit_action())

    def test_a_scientist_needs_enemy_shields(self):
        def build(enemy_shield):
            return self._captain(
                active_combat={"enemy_shield": enemy_shield},
                crew=[{"id": "crew_scientist_1", "role": "scientist",
                       "status": "active", "injury_ticks": 0}],
                fleet_manager={"ships": [
                    {"id": "escort_1", "hull": 90, "max_hull": 90, "shield": 60,
                     "max_shield": 60, "assigned_system_id": "ashen",
                     "captain_id": "crew_scientist_1"},
                ]})
        self.assertEqual(build(40)._gambit_action()[0], "/api/combat/gambit")
        self.assertIsNone(build(0)._gambit_action())

    def test_the_choice_uses_the_gambit_before_routine_fire(self):
        captain = self._captain(ship={"hull": 60})
        self.assertEqual(captain._choose(7), ("/api/combat/gambit", {}, "combat_gambit"))


class ReactorDoctrineTest(unittest.TestCase):
    """The post-campaign core switches doctrine once instead of reposting its mode (ADR-398)."""

    def _captain(self, modes, current="balanced", completed=True):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "story_status": {"completed": completed},
            "reactor": {"mode": current, "modes": modes},
        }
        return captain

    def test_a_balanced_core_is_moved_to_economy(self):
        captain = self._captain({"balanced": {}, "economy": {}, "overdrive": {}})
        self.assertEqual(captain._reactor_mode_action(),
                         ("/api/reactor/mode", {"mode": "economy"}, "reactor"))

    def test_an_economy_core_moves_to_balanced(self):
        captain = self._captain({"balanced": {}, "economy": {}, "overdrive": {}},
                                current="economy")
        self.assertEqual(captain._reactor_mode_action()[1], {"mode": "balanced"})

    def test_a_legacy_list_catalog_still_switches(self):
        captain = self._captain([{"id": "balanced"}, {"id": "silent"}])
        self.assertEqual(captain._reactor_mode_action()[1], {"mode": "silent"})

    def test_a_single_mode_catalog_stays_quiet(self):
        self.assertIsNone(self._captain({"balanced": {}})._reactor_mode_action())

    def test_a_missing_catalog_stays_quiet(self):
        self.assertIsNone(self._captain(None)._reactor_mode_action())

    def test_the_short_gate_keeps_its_balanced_core(self):
        self.assertIsNone(
            self._captain({"balanced": {}, "economy": {}}, completed=False)
            ._reactor_mode_action())

    def test_the_doctrine_changes_once(self):
        captain = self._captain({"balanced": {}, "economy": {}})
        self.assertEqual(captain._reactor_mode_action()[0], "/api/reactor/mode")
        self.assertIsNone(captain._reactor_mode_action())


class ReactorHeatChainTest(unittest.TestCase):
    """A post-story heat spike is vented and the purge damage repaired (ADR-404)."""

    def _captain(self, heat=16.0, integrity=100.0, tick=400, last_vent=-999,
                 docked=True, credits=5000, completed=True):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "story_status": {"completed": completed},
            "reactor": {
                "heat": heat, "max_heat": 100.0, "heat_pct": heat,
                "integrity": integrity, "max_integrity": 100.0,
                "last_vent_tick": last_vent, "mode": "economy",
            },
            "time": {"tick": tick},
            "orbiting_body": ({"id": "sol_station", "station_dockable": True}
                              if docked else {"id": "sol_rock"}),
            "ship": {"credits": credits, "fuel": 60, "max_fuel": 80,
                     "hull": 90, "max_hull": 100},
        }
        return captain

    def test_a_hot_core_is_vented_after_the_campaign(self):
        self.assertEqual(self._captain()._reactor_vent_action(),
                         ("/api/reactor/vent", {}, "reactor_vent"))

    def test_a_cool_core_is_never_vented(self):
        self.assertIsNone(self._captain(heat=4.0)._reactor_vent_action())

    def test_a_recharging_coolant_waits(self):
        self.assertIsNone(
            self._captain(tick=400, last_vent=397)._reactor_vent_action())

    def test_the_short_gate_never_vents(self):
        self.assertIsNone(
            self._captain(completed=False)._reactor_vent_action())

    def test_purge_damage_is_repaired_at_a_dock(self):
        self.assertEqual(self._captain(integrity=99.0)._reactor_repair_action(),
                         ("/api/reactor/repair", {}, "reactor_repair"))

    def test_a_hot_core_is_serviced_at_a_dock(self):
        self.assertEqual(self._captain(heat=16.0)._reactor_repair_action()[0],
                         "/api/reactor/repair")

    def test_an_intact_cool_core_is_not_serviced(self):
        self.assertIsNone(self._captain(heat=2.0)._reactor_repair_action())

    def test_the_service_needs_a_dock_and_credits(self):
        self.assertIsNone(
            self._captain(integrity=90.0, docked=False)._reactor_repair_action())
        self.assertIsNone(
            self._captain(integrity=90.0, credits=50)._reactor_repair_action())

    def test_the_vent_fires_before_the_tour(self):
        self.assertEqual(self._captain()._choose(2)[0], "/api/reactor/vent")

    def test_the_repair_fires_after_the_purge(self):
        self.assertEqual(self._captain(heat=2.0, integrity=99.0)._choose(2)[0],
                         "/api/reactor/repair")


class PrizeSalePolicyTest(unittest.TestCase):
    """A captured prize is sold at a drydock, never the bought escort (ADR-399)."""

    def _captain(self, ships, docked=True, completed=True, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": completed},
            "current_system": {
                "id": "ashen",
                "bodies": [
                    {"id": "ashen_station", "station_dockable": True},
                    {"id": "ashen_rock", "station_dockable": False},
                ],
            },
            "orbiting_body": ({"id": "ashen_station", "station_dockable": True}
                              if docked else {"id": "ashen_rock"}),
            "fleet_manager": {"ships": ships},
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_a_docked_prize_is_sold(self):
        captain = self._captain([
            {"id": "escort_corvette_1", "role": "escort", "hull": 40},
            {"id": "prize_134_1", "role": "prize", "hull": 0},
        ])
        self.assertEqual(
            captain._prize_sale_action(),
            ("/api/fleet/escort/sell", {"ship_id": "prize_134_1"}, "fleet_sell"),
        )

    def test_an_undocked_captain_reaches_a_station_first(self):
        captain = self._captain(
            [{"id": "prize_134_1", "role": "prize", "hull": 0}], docked=False)
        self.assertEqual(
            captain._prize_sale_action(),
            ("/api/travel", {"body_id": "ashen_station", "mode": "sublight"}, "dock"),
        )

    def test_the_bought_escort_is_never_sold(self):
        captain = self._captain([
            {"id": "escort_corvette_1", "role": "escort", "hull": 90},
        ])
        self.assertIsNone(captain._prize_sale_action())

    def test_the_sale_happens_once(self):
        captain = self._captain([
            {"id": "prize_134_1", "role": "prize", "hull": 0},
        ])
        captain.succeeded.add("/api/fleet/escort/sell")
        self.assertIsNone(captain._prize_sale_action())

    def test_nothing_sells_before_the_campaign(self):
        captain = self._captain(
            [{"id": "prize_134_1", "role": "prize", "hull": 0}], completed=False)
        self.assertIsNone(captain._prize_sale_action())


class SmuggleCordonPolicyTest(unittest.TestCase):
    """The post-story captain runs one real contraband cordon (ADR-400)."""

    def _captain(self, cargo=None, docked=True, completed=True, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": completed},
            "current_system": {
                "id": "sol",
                "security": 1.0,
                "connections": ["alpha_centauri", "procyon"],
                "bodies": [
                    {"id": "sol_station", "station_dockable": True},
                    {"id": "sol_rock", "station_dockable": False},
                ],
            },
            "orbiting_body": ({"id": "sol_station", "station_dockable": True}
                              if docked else {"id": "sol_rock"}),
            "ship": {"credits": 50000, "fuel": 60, "max_fuel": 80,
                     "hull": 100, "max_hull": 100,
                     "cargo": cargo or {}, "cargo_free_volume": 30},
            "market_quotes": [
                {"commodity_id": "xenoliths", "category": "contraband",
                 "buy_price": 1111, "max_buy": 1},
                {"commodity_id": "medicines", "category": "medicine",
                 "buy_price": 209, "max_buy": 8},
            ],
            "customs_risk": None,
            "jump_fuel_costs": {"alpha_centauri": 7, "procyon": 7},
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_the_cheapest_contraband_lot_is_bought_at_a_dock(self):
        self.assertEqual(
            self._captain()._smuggle_action(),
            ("/api/trade",
             {"commodity_id": "xenoliths", "quantity": 1, "is_buy": True},
             "trade"),
        )

    def test_an_undocked_captain_does_not_buy(self):
        self.assertIsNone(self._captain(docked=False)._smuggle_action())

    def test_nothing_is_bought_before_the_campaign(self):
        self.assertIsNone(self._captain(completed=False)._smuggle_action())

    def test_a_held_lot_jumps_at_the_quoted_cordon(self):
        captain = self._captain(
            cargo={"xenoliths": 1},
            customs_risk={"units": 1, "chance": 0.5,
                          "system_id": "procyon", "system_name": "Procyon"})
        captain.smuggling_item = "xenoliths"
        self.assertEqual(captain._smuggle_action(),
                         ("/api/jump", {"target": "procyon"}, "jump"))

    def test_a_short_tank_refuels_before_the_cordon_run(self):
        captain = self._captain(
            cargo={"xenoliths": 1},
            ship={"credits": 50000, "fuel": 3, "max_fuel": 80,
                  "cargo": {"xenoliths": 1}, "cargo_free_volume": 30},
            customs_risk={"units": 1, "chance": 0.5,
                          "system_id": "procyon", "system_name": "Procyon"})
        captain.smuggling_item = "xenoliths"
        self.assertEqual(captain._smuggle_action(),
                         ("/api/refuel", {"amount": 10}, "refuel"))

    def test_a_cordon_with_no_adjacent_quotes_repositions_out(self):
        captain = self._captain(
            cargo={"xenoliths": 1},
            customs_risk={"units": 1, "chance": 0.0,
                          "system_id": "", "system_name": ""})
        captain.smuggling_item = "xenoliths"
        self.assertEqual(captain._smuggle_action(),
                         ("/api/jump", {"target": "alpha_centauri"}, "jump"))

    def test_the_run_is_capped(self):
        captain = self._captain(
            cargo={"xenoliths": 1},
            customs_risk={"units": 1, "chance": 0.5,
                          "system_id": "procyon", "system_name": "Procyon"})
        captain.smuggling_item = "xenoliths"
        captain.smuggling_jumps = AiCaptain.SMUGGLE_JUMP_LIMIT
        self.assertIsNone(captain._smuggle_action())

    def test_a_resolved_interdiction_ends_the_run(self):
        captain = self._captain(cargo={"xenoliths": 1})
        captain.smuggling_item = "xenoliths"
        captain.succeeded.add("/api/customs/resolve")
        self.assertIsNone(captain._smuggle_action())

    def test_a_lost_lot_ends_the_run(self):
        captain = self._captain(cargo={})
        captain.smuggling_item = "xenoliths"
        self.assertIsNone(captain._smuggle_action())

    def test_the_lookout_picks_the_risk_cordon_before_a_generic_jump(self):
        captain = self._captain(
            cargo={"xenoliths": 1},
            customs_risk={"units": 1, "chance": 0.5,
                          "system_id": "procyon", "system_name": "Procyon"})
        captain.smuggling_item = "xenoliths"
        captain.succeeded.add("/api/salvage")
        self.assertEqual(captain._choose(25)[0], "/api/jump")


class FallbackJumpRotationTest(unittest.TestCase):
    """The off-objective jump rotates across lanes instead of ping-ponging (ADR-401)."""

    def _captain(self, connections, costs, fuel=60, completed=True):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "story_status": {"completed": completed},
            "current_system": {"connections": connections},
            "jump_fuel_costs": costs,
            "ship": {"fuel": fuel, "max_fuel": 80},
        }
        return captain

    def test_three_cadence_jumps_use_three_lanes(self):
        captain = self._captain(["a", "b", "c"], {"a": 7, "b": 7, "c": 7})
        targets = [captain._fallback_jump(step)[1]["target"]
                   for step in (5, 25, 45)]
        self.assertEqual(sorted(targets), ["a", "b", "c"])

    def test_the_first_jump_keeps_its_historic_slot(self):
        captain = self._captain(["a", "b"], {"a": 7, "b": 7})
        self.assertEqual(captain._fallback_jump(5)[1], {"target": "b"})

    def test_the_short_gate_keeps_the_frozen_slot(self):
        captain = self._captain(["a", "b"], {"a": 7, "b": 7}, completed=False)
        targets = [captain._fallback_jump(step)[1]["target"]
                   for step in (5, 25, 45)]
        self.assertEqual(targets, ["b", "b", "b"])

    def test_unaffordable_lanes_are_skipped(self):
        captain = self._captain(["a", "b"], {"a": 7, "b": 3}, fuel=5)
        self.assertEqual(captain._fallback_jump(5)[1], {"target": "b"})

    def test_off_cadence_steps_do_not_jump(self):
        captain = self._captain(["a", "b"], {"a": 7, "b": 7})
        self.assertIsNone(captain._fallback_jump(6))
        self.assertIsNone(captain._fallback_jump(7))


class WreckDismissalPolicyTest(unittest.TestCase):
    """A destroyed escort is decommissioned so its officer is released (ADR-402)."""

    def _captain(self, ships, completed=True):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "story_status": {"completed": completed},
            "fleet_manager": {"ships": ships},
        }
        return captain

    def test_a_destroyed_escort_is_decommissioned(self):
        captain = self._captain([
            {"id": "escort_corvette_1", "role": "escort", "hull": 0,
             "captain_id": "crew_engineer_4"},
        ])
        self.assertEqual(
            captain._wreck_dismiss_action(),
            ("/api/fleet/escort/dismiss", {"ship_id": "escort_corvette_1"},
             "fleet_dismiss"),
        )

    def test_a_live_escort_is_kept(self):
        captain = self._captain([
            {"id": "escort_corvette_1", "role": "escort", "hull": 90,
             "captain_id": "crew_engineer_4"},
        ])
        self.assertIsNone(captain._wreck_dismiss_action())

    def test_a_destroyed_prize_is_left_to_the_sale(self):
        captain = self._captain([
            {"id": "prize_134_1", "role": "prize", "hull": 0},
        ])
        self.assertIsNone(captain._wreck_dismiss_action())

    def test_the_decommission_happens_once(self):
        captain = self._captain([
            {"id": "escort_corvette_1", "role": "escort", "hull": 0},
        ])
        captain.succeeded.add("/api/fleet/escort/dismiss")
        self.assertIsNone(captain._wreck_dismiss_action())

    def test_nothing_is_dismissed_before_the_campaign(self):
        captain = self._captain(
            [{"id": "escort_corvette_1", "role": "escort", "hull": 0}],
            completed=False)
        self.assertIsNone(captain._wreck_dismiss_action())


class StoryTravelTourTest(unittest.TestCase):
    """Story-directed travel and orbit survive the stay-until-resolved hold (ADR-360)."""

    CHAPTER = "act4_hollow_between"
    SYSTEM = "cygnus_x1"
    BODY = "cygnus_x1_black_hole"

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "current_system": {
                "id": self.SYSTEM,
                "connections": ["sol"],
                "bodies": [{"id": self.BODY}, {"id": "cygnus_x1_body_1", "station_dockable": True}],
            },
            "orbiting_body": {"id": "cygnus_x1_body_1", "station_dockable": True},
            "ship": {"hull": 100, "max_hull": 100, "fuel": 40, "max_fuel": 60,
                     "travel": None, "orbiting_body_id": "cygnus_x1_body_1"},
            "story_status": {
                "completed": False, "ready": False, "target_system_id": self.SYSTEM,
                "chapter_id": self.CHAPTER, "unmet_requirements": [], "choices": [],
            },
            "story_chapters_map": {
                self.CHAPTER: {"requirements": {"orbit_body_id": self.BODY}},
            },
            "jump_fuel_costs": {"sol": 4},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_a_ready_chapter_is_resolved_before_a_dock_trip(self):
        captain = self._captain(
            orbiting_body={"station_dockable": False},
            story_status={"ready": True, "choices": [{"id": "choice_first_dive", "locked": False}]},
        )
        action = captain._choose(3)
        self.assertEqual(action[0], "/api/story/choice")
        self.assertEqual(action[1]["choice_id"], "choice_first_dive")

    def test_an_orbit_chapter_re_orbits_a_body_it_left(self):
        captain = self._captain(story_status={
            "unmet_requirements": ["Establish orbit around Cygnus Void Gate Event Horizon"],
        })
        captain.attempted_signatures.add(("/api/orbit", self.BODY))
        action = captain._choose(25)
        self.assertEqual(action[0], "/api/orbit")
        self.assertEqual(action[1]["target"], self.BODY)

    def test_story_travel_needs_the_whole_route_plus_a_reserve(self):
        status = {"target_system_id": "sirius", "route": {"reachable": True, "fuel_estimate": 20}}
        current = {"id": self.SYSTEM}
        short = self._captain(current_system=current, story_status=status, ship={"fuel": 24})
        self.assertIsNone(short._tour_story_travel())
        ready = self._captain(current_system=current, story_status=status, ship={"fuel": 25})
        self.assertEqual(ready._tour_story_travel()[1]["system_id"], "sirius")
        unreachable = self._captain(
            current_system=current,
            story_status={"target_system_id": "sirius", "route": {"reachable": False}},
        )
        self.assertIsNone(unreachable._tour_story_travel())

    def test_story_travel_waits_for_combat_transit_and_anomalies(self):
        status = {"target_system_id": "sirius", "route": {"reachable": True, "fuel_estimate": 10}}
        current = {"id": self.SYSTEM}
        for blocked in ({"active_combat": {"id": "c"}}, {"active_anomaly": {"id": "a"}},
                        {"ship": {"travel": {"body_id": "b"}}}):
            captain = self._captain(current_system=current, story_status=status, **blocked)
            self.assertIsNone(captain._tour_story_travel())

    def test_story_navigation_retries_but_generic_navigation_stays_one_shot(self):
        captain = self._captain(
            current_system={"id": "sol", "connections": ["sirius"]},
            story_status={"target_system_id": "sirius"},
        )
        target = {"system_id": "sirius"}
        captain.attempted.add("/api/navigate")
        captain.repeat_last[("/api/navigate", "")] = 10
        captain.total_steps = 20
        self.assertTrue(captain._tour_action_attempted("/api/navigate", target))
        captain.total_steps = 40
        self.assertFalse(captain._tour_action_attempted("/api/navigate", target))
        self.assertTrue(captain._tour_action_attempted("/api/navigate", {"system_id": "vega"}))

    def test_shared_routes_key_de_duplication_on_the_sub_action(self):
        captain = self._captain()
        self.assertEqual(captain._tour_signature("/api/story/choice", {"choice_id": "c1"}),
                         ("/api/story/choice", "c1"))
        self.assertNotEqual(captain._tour_signature("/api/story/choice", {"choice_id": "c1"}),
                            captain._tour_signature("/api/story/choice", {"choice_id": "c2"}))
        self.assertEqual(captain._tour_signature("/api/orbit", {"target": self.BODY}),
                         ("/api/orbit", self.BODY))


class VoidTraversalTourTest(unittest.TestCase):
    """The Act IV void beat dives, emerges and still resolves the chapter (ADR-366)."""

    CHAPTER = "act4_hollow_between"
    SYSTEM = "cygnus_x1"
    HORIZON = "cygnus_x1_black_hole"

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "current_system": {"id": self.SYSTEM},
            "ship": {
                "hull": 75, "max_hull": 115, "shield": 125, "max_shield": 125,
                "fuel": 35, "orbiting_body_id": self.HORIZON, "void_traversal": None,
            },
            "void": {
                "dive_ready": True, "blockers": [],
                "destinations": [
                    {"system_id": "capella", "fuel_estimate": 17, "duration_ticks": 6},
                    {"system_id": "golconda", "fuel_estimate": 12, "duration_ticks": 4},
                ],
            },
            "story_status": {
                "completed": False, "ready": True, "target_system_id": self.SYSTEM,
                "chapter_id": self.CHAPTER, "unmet_requirements": [],
                "choices": [{"id": "choice_horizon_witness", "locked": False}],
            },
            "story_chapters_map": {
                self.CHAPTER: {"requirements": {"orbit_body_id": self.HORIZON}},
            },
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_the_oath_beat_dives_to_the_cheapest_lane_once(self):
        captain = self._captain()
        action = captain._choose(3)
        self.assertEqual(action[0], "/api/void/dive")
        self.assertEqual(action[1]["target_system_id"], "golconda")
        self.assertNotEqual(captain._choose(3)[0], "/api/void/dive")

    def test_no_dive_off_the_required_horizon(self):
        off_horizon = self._captain(ship={"orbiting_body_id": "cygnus_x1_body_1"})
        self.assertEqual(off_horizon._choose(3)[0], "/api/story/choice")
        other_chapter = self._captain(
            story_chapters_map={self.CHAPTER: {"requirements": {"orbit_body_id": "elsewhere"}}})
        self.assertEqual(other_chapter._choose(3)[0], "/api/story/choice")

    def test_no_dive_with_thin_shields_hull_or_tank(self):
        for weak in ({"shield": 20}, {"hull": 30}, {"fuel": 16}):
            captain = self._captain(ship=weak)
            self.assertEqual(captain._choose(3)[0], "/api/story/choice", weak)

    def test_a_traversal_time_steps_then_emerges(self):
        traversal = {"destination_system_id": "golconda", "arrival_tick": 10,
                     "duration_ticks": 4, "started_tick": 5}
        captain = self._captain(
            ship={"void_traversal": traversal},
            void={"traversal": traversal, "traversal_progress": 0.1},
        )
        self.assertEqual(captain._choose(4)[0], "/api/time/step")
        captain.state["void"]["traversal_progress"] = 0.3
        self.assertEqual(captain._choose(4)[0], "/api/void/emerge")
        captain.state["void"]["traversal_progress"] = 0.5
        self.assertEqual(captain._choose(4)[0], "/api/time/step")

    def test_the_chapter_resolves_after_emergence(self):
        captain = self._captain()
        captain.void_attempted = True
        self.assertEqual(captain._choose(3)[0], "/api/story/choice")


class SupplyTourTest(unittest.TestCase):
    """The captain buys a station consumable and uses it when hurt (ADR-367)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "current_system": {"id": "sol"},
            "orbiting_body": {"id": "sol_body_1", "station_dockable": True},
            "ship": {
                "hull": 100, "max_hull": 100, "credits": 2000,
                "cargo": {}, "cargo_capacity": 40, "cargo_free_volume": 40,
            },
            "inventory_manifest": [],
            "catalog_items": [
                {"id": "nanite_repair_paste", "category": "consumable",
                 "is_usable": True, "base_price": 250, "volume": 1},
            ],
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_a_docked_captain_buys_one_repair_paste(self):
        action = self._captain()._tour_supply()
        self.assertEqual(action[0], "/api/inventory/buy")
        self.assertEqual(action[1], {"item_id": "nanite_repair_paste", "quantity": 1})

    def test_the_purchase_uses_the_published_catalog_price(self):
        expensive = [{"id": "nanite_repair_paste", "category": "consumable",
                      "is_usable": True, "base_price": 900, "volume": 1}]
        self.assertIsNone(self._captain(
            ship={"credits": 300}, catalog_items=expensive)._tour_supply())
        self.assertIsNotNone(self._captain(
            ship={"credits": 500})._tour_supply())

    def test_the_decoy_is_bought_at_a_late_dock_after_the_tour(self):
        captain = self._captain(
            ship={"credits": 500, "cargo": {"nanite_repair_paste": 1}},
        )
        captain.tour_exhausted = True
        action = captain._choose(3)
        self.assertEqual(action[0], "/api/inventory/buy")
        self.assertEqual(action[1]["item_id"], "decoy_countermeasure")

    def test_a_refused_refill_waits_for_its_cooldown(self):
        captain = self._captain(
            ship={"credits": 500, "cargo": {"nanite_repair_paste": 1}},
        )
        captain.tour_exhausted = True
        signature = ("/api/inventory/buy", "decoy_countermeasure")
        captain.retry_at[signature] = captain.total_steps + captain.REFUSAL_RETRY_STEPS
        self.assertNotEqual(captain._choose(3)[0], "/api/inventory/buy")
        captain.total_steps = captain.retry_at[signature]
        self.assertEqual(captain._choose(3)[0], "/api/inventory/buy")

    def test_a_consumable_is_never_traded_as_a_commodity(self):
        captain = self._captain(
            ship={"cargo": {"decoy_countermeasure": 1}, "cargo_free_volume": 0,
                  "cargo_capacity": 40},
            market_quotes={"titanium": {"price": 10}},
        )
        self.assertIsNone(captain._trade_choice(5),
                          "a held decoy has no market quote and must not be sold")
        both = self._captain(
            ship={"cargo": {"decoy_countermeasure": 1, "titanium": 2},
                  "cargo_free_volume": 0, "cargo_capacity": 40},
            market_quotes={"titanium": {"price": 10}},
        )
        action = both._trade_choice(5)
        self.assertEqual(action[1]["commodity_id"], "titanium")

    def test_the_second_purchase_is_a_decoy(self):
        captain = self._captain(
            ship={"credits": 500, "cargo": {"nanite_repair_paste": 1}},
        )
        action = captain._tour_supply_decoy()
        self.assertEqual(action[0], "/api/inventory/buy")
        self.assertEqual(action[1], {"item_id": "decoy_countermeasure", "quantity": 1})
        self.assertIsNone(captain._tour_supply(), "the paste is still held")
        held = self._captain(ship={
            "credits": 500,
            "cargo": {"nanite_repair_paste": 1, "decoy_countermeasure": 1},
        })
        self.assertIsNone(held._tour_supply_decoy())

    def test_each_supply_item_has_its_own_purchase_signature(self):
        captain = self._captain()
        captain.attempted.add("/api/inventory/buy")
        captain.attempted_signatures.add(("/api/inventory/buy", "nanite_repair_paste"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/inventory/buy", {"item_id": "nanite_repair_paste"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/inventory/buy", {"item_id": "decoy_countermeasure"}),
            "a second item must stay buyable after the first")

    def test_an_unaffordable_decoy_is_skipped(self):
        captain = self._captain(
            ship={"credits": 349, "cargo": {"nanite_repair_paste": 1}},
        )
        self.assertIsNone(captain._tour_supply_decoy())
        affordable = self._captain(
            ship={"credits": 350, "cargo": {"nanite_repair_paste": 1}},
        )
        self.assertEqual(affordable._tour_supply_decoy()[1]["item_id"], "decoy_countermeasure")

    def test_no_purchase_without_a_dock_credits_or_hold_space(self):
        self.assertIsNone(self._captain(orbiting_body=None)._tour_supply())
        self.assertIsNone(self._captain(ship={"credits": 100})._tour_supply())
        self.assertIsNone(self._captain(ship={"cargo_free_volume": 0})._tour_supply())

    def test_a_hurt_captain_uses_the_held_paste(self):
        captain = self._captain(
            orbiting_body=None,
            ship={"hull": 40, "cargo": {"nanite_repair_paste": 1}},
        )
        action = captain._supply_action()
        self.assertEqual(action[0], "/api/inventory/use")
        self.assertEqual(action[1], {"item_id": "nanite_repair_paste"})

    def test_no_use_when_healthy_empty_or_in_combat(self):
        self.assertIsNone(self._captain(
            ship={"cargo": {"nanite_repair_paste": 1}})._supply_action())
        self.assertIsNone(self._captain(
            orbiting_body=None, ship={"hull": 40})._supply_action())
        captain = self._captain(
            ship={"hull": 40, "cargo": {"nanite_repair_paste": 1}},
            active_combat={"id": "c1"},
        )
        self.assertNotEqual(captain._choose(3)[0], "/api/inventory/use")


class MarineCrewTest(unittest.TestCase):
    """The captain hires a marine so boarding is reachable (ADR-375)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "current_system": {"id": "sol"},
            "orbiting_body": {"id": "sol_body_1", "station_dockable": True},
            "ship": {"credits": 5000, "cargo": {}},
            "crew": [],
            "crew_roles": [
                {"id": "pilot", "cost": 900},
                {"id": "marine", "cost": 1000},
            ],
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_one_builder_hires_the_pilot_then_the_marine(self):
        captain = self._captain()
        self.assertEqual(captain._tour_crew()[1], {"role_id": "pilot"})
        captain.state["crew"] = [{"role": "pilot", "status": "active"}]
        self.assertEqual(captain._tour_crew()[1], {"role_id": "marine"})
        captain.state["crew"].append({"role": "marine", "status": "active"})
        self.assertIsNone(captain._tour_crew())

    def test_no_crew_hire_when_both_are_aboard_undocked_or_poor(self):
        both = [{"role": "pilot", "status": "active"},
                {"role": "marine", "status": "active"}]
        self.assertIsNone(self._captain(crew=both)._tour_crew())
        self.assertIsNone(self._captain(orbiting_body=None)._tour_crew())
        self.assertIsNone(self._captain(ship={"credits": 500})._tour_crew())

    def test_the_recruit_route_is_keyed_by_role(self):
        captain = self._captain()
        captain.attempted.add("/api/crew/recruit")
        captain.attempted_signatures.add(("/api/crew/recruit", "pilot"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/crew/recruit", {"role_id": "pilot"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/crew/recruit", {"role_id": "marine"}),
            "the marine must stay hireable after the pilot")


class MessageTreePolicyTest(unittest.TestCase):
    """The captain resolves a live message-tree branch instead of only reading it (ADR-378)."""

    def _captain(self, messages):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {"messages": messages}
        return captain

    def test_the_first_pending_branch_is_chosen(self):
        captain = self._captain([
            {"id": "tree_precursor_signal_0", "read": False, "resolved_choice": None,
             "choices": [{"id": "decode"}, {"id": "sell"}]},
        ])
        self.assertEqual(
            captain._tour_messages(),
            ("/api/messages/choose",
             {"message_id": "tree_precursor_signal_0", "choice_id": "decode"},
             "messages_choose"),
        )

    def test_a_read_but_unresolved_branch_is_still_chosen(self):
        captain = self._captain([
            {"id": "tree_refugee_fleet_74", "read": True, "resolved_choice": None,
             "choices": [{"id": "accept_crew"}]},
        ])
        self.assertEqual(captain._tour_messages()[0], "/api/messages/choose")

    def test_plain_mail_is_read_by_state_without_starving_the_branch(self):
        captain = self._captain([
            {"id": "msg_depot", "read": False, "choices": []},
            {"id": "tree_one", "read": False, "resolved_choice": None,
             "choices": [{"id": "decode"}]},
        ])
        self.assertEqual(captain._unread_message_action()[1]["message_id"], "msg_depot")
        self.assertEqual(captain._tour_messages()[1]["message_id"], "tree_one")
        captain.state["messages"][0]["read"] = True
        self.assertIsNone(captain._unread_message_action())

    def test_a_plain_message_is_still_marked_read(self):
        captain = self._captain([{"id": "msg_depot", "read": False, "choices": []}])
        self.assertEqual(
            captain._tour_messages(),
            ("/api/messages/read", {"message_id": "msg_depot"}, "messages"),
        )

    def test_the_mail_followup_reads_before_it_sends(self):
        captain = self._captain([
            {"id": "msg_welcome", "sender": "Admiral Vance", "read": True, "choices": []},
            {"id": "msg_depot", "read": False, "choices": []},
        ])
        self.assertEqual(captain._tour_message_send()[0], "/api/messages/read")
        captain.state["messages"][1]["read"] = True
        self.assertEqual(captain._tour_message_send()[0], "/api/messages/send")

    def test_a_resolved_branch_is_not_chosen_again(self):
        captain = self._captain([
            {"id": "tree_one", "read": True, "resolved_choice": "decode",
             "choices": [{"id": "decode"}]},
        ])
        self.assertIsNone(captain._tour_messages())

    def test_each_tree_node_is_keyed_by_its_message_id(self):
        captain = self._captain([])
        captain.attempted.add("/api/messages/choose")
        captain.attempted_signatures.add(("/api/messages/choose", "tree_one"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/messages/choose", {"message_id": "tree_one"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/messages/choose", {"message_id": "tree_one_decoded"}),
            "a follow-up node must stay reachable after its parent")


class ShipyardChassisTourTest(unittest.TestCase):
    """The captain commissions a fitting hull once the treasury can afford one (ADR-379)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "orbiting_body": {"id": "b1", "station_dockable": True},
            "story_status": {"completed": True},
            "ship": {"credits": 6000, "cargo_used_volume": 10, "cargo": {}},
            "available_chassis": [
                {"id": "orion_hauler", "ship_class": "Bulk Merchant Hauler",
                 "cost": 4500, "cargo_capacity": 120},
                {"id": "archon_dreadnought", "ship_class": "Command Battlecruiser",
                 "cost": 12000, "cargo_capacity": 80},
            ],
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_a_fitting_affordable_hull_is_commissioned(self):
        self.assertEqual(
            self._captain()._chassis_action(),
            ("/api/shipyard/chassis", {"chassis_id": "orion_hauler"}, "chassis"),
        )

    def test_the_cheapest_fitting_hull_wins(self):
        captain = self._captain(
            ship={"credits": 7000, "cargo_used_volume": 10},
            available_chassis=[
                {"id": "big", "cost": 5200, "cargo_capacity": 120},
                {"id": "cheap", "cost": 4500, "cargo_capacity": 120},
            ])
        self.assertEqual(captain._chassis_action()[1]["chassis_id"], "cheap")

    def test_a_cheap_hull_that_cannot_fit_the_hold_is_skipped(self):
        captain = self._captain(
            ship={"credits": 6500, "cargo_used_volume": 10},
            available_chassis=[
                {"id": "tiny", "cost": 4500, "cargo_capacity": 5},
                {"id": "roomy", "cost": 5000, "cargo_capacity": 120},
            ])
        self.assertEqual(captain._chassis_action()[1]["chassis_id"], "roomy")

    def test_it_waits_for_the_campaign_to_complete(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._chassis_action())

    def test_it_needs_a_dock_credits_reserve_and_hold_space(self):
        self.assertIsNone(self._captain(orbiting_body=None)._chassis_action())
        self.assertIsNone(self._captain(
            ship={"credits": 5000, "cargo_used_volume": 10})._chassis_action())
        self.assertIsNone(self._captain(
            ship={"credits": 6000, "cargo_used_volume": 121})._chassis_action())

    def test_the_current_class_is_not_rebought(self):
        captain = self._captain(
            ship={"credits": 6000, "cargo_used_volume": 10,
                  "ship_class": "Bulk Merchant Hauler"})
        self.assertIsNone(captain._chassis_action())

    def test_the_commission_is_one_shot(self):
        captain = self._captain()
        captain.attempted.add("/api/shipyard/chassis")
        self.assertIsNone(captain._chassis_action())


class TradeAutomationPolicyTest(unittest.TestCase):
    """The captain arms the docked broker, lets it trade, then stands it down (ADR-380)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "orbiting_body": {"id": "b1", "station_dockable": True},
            "market_quotes": {
                "titanium": {"commodity_id": "titanium", "buy_price": 10.0,
                             "sell_price": 8.0},
                "water": {"commodity_id": "water", "buy_price": 4.0, "sell_price": 3.0},
            },
            "ship": {"credits": 5000, "cargo": {}, "cargo_free_volume": 40},
            "trade_automation": {"enabled": False, "commodity_id": "", "trades": 0},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_the_cheapest_quote_is_armed_at_a_post_story_dock(self):
        action = self._captain()._automation_action()
        self.assertEqual(action[0], "/api/trade/automation")
        self.assertEqual(action[2], "automation")
        self.assertEqual(action[1]["commodity_id"], "water")
        self.assertEqual(action[1]["quantity"], 1)
        self.assertTrue(action[1]["enabled"])
        self.assertGreaterEqual(action[1]["buy_below"], 4.0)

    def test_no_arming_before_act_vi_without_a_dock_quote_or_credits(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._automation_action())
        self.assertIsNone(self._captain(orbiting_body=None)._automation_action())
        self.assertIsNone(self._captain(market_quotes=None)._automation_action())
        self.assertIsNone(self._captain(
            ship={"credits": 1, "cargo": {}, "cargo_free_volume": 40})._automation_action())

    def test_a_traded_broker_is_stood_down(self):
        captain = self._captain(trade_automation={
            "enabled": True, "commodity_id": "water", "trades": 1})
        self.assertEqual(
            captain._automation_action(),
            ("/api/trade/automation", {"enabled": False}, "automation"),
        )

    def test_an_armed_broker_gets_one_tick_and_then_stands_down(self):
        captain = self._captain(trade_automation={
            "enabled": True, "commodity_id": "water", "trades": 0})
        self.assertEqual(
            captain._automation_action(),
            ("/api/time/step", {"ticks": 1}, "time"),
        )
        self.assertTrue(captain.automation_waited)
        self.assertEqual(
            captain._automation_action(),
            ("/api/trade/automation", {"enabled": False}, "automation"),
        )

    def test_a_full_hold_waits_for_the_sell_fallback(self):
        captain = self._captain(
            ship={"cargo_free_volume": 0},
            trade_automation={"enabled": True, "commodity_id": "water", "trades": 0})
        self.assertIsNone(captain._automation_action())

    def test_both_switch_directions_are_separate_signatures(self):
        captain = self._captain()
        captain.attempted_signatures.add(("/api/trade/automation", "True"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/trade/automation", {"enabled": True}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/trade/automation", {"enabled": False}),
            "standing the broker down must stay reachable after arming it")


class QuantumFreightTourTest(unittest.TestCase):
    """The captain ships cargo down the quantum lane and arms auto-freight (ADR-381)."""

    class StubClient:
        def __init__(self, report):
            self.report = report

        def get(self, path):
            if path == "/api/trade/quantum":
                return 200, {"ok": True, "quantum": self.report}
            return 404, {}

    def _captain(self, report, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.client = self.StubClient(report)
        base = {
            "story_status": {"completed": True},
            "orbiting_body": {"id": "b1", "station_dockable": True},
            "ship": {"credits": 5000, "cargo": {"titanium": 20}},
            "quantum_automation": {"enabled": False, "min_net": 100, "orders": 0},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    @staticmethod
    def _report(routes):
        return {"docked": True, "routes": routes, "max_orders": 4}

    def test_the_best_positive_route_is_placed(self):
        report = self._report([
            {"commodity_id": "titanium", "quantity": 20,
             "destination_system_id": "vega", "fee": 50, "net": 300},
            {"commodity_id": "titanium", "quantity": 20,
             "destination_system_id": "sol", "fee": 10, "net": 900},
        ])
        action = self._captain(report)._quantum_manual_action()
        self.assertEqual(action[0], "/api/trade/quantum/place")
        self.assertEqual(action[1], {"commodity_id": "titanium", "quantity": 1,
                                     "destination_system_id": "sol"})
        self.assertEqual(action[2], "quantum_place")

    def test_no_lane_without_a_dock_story_or_positive_route(self):
        report = self._report([
            {"commodity_id": "titanium", "quantity": 20,
             "destination_system_id": "vega", "fee": 500, "net": -20},
        ])
        self.assertIsNone(self._captain(report)._quantum_manual_action())
        good = self._report([
            {"commodity_id": "titanium", "quantity": 20,
             "destination_system_id": "vega", "fee": 10, "net": 500},
        ])
        self.assertIsNone(self._captain(good, orbiting_body=None)._quantum_manual_action())
        self.assertIsNone(self._captain(
            good, story_status={"completed": False})._quantum_manual_action())

    def test_a_refused_or_unaffordable_fee_is_skipped(self):
        report = self._report([
            {"commodity_id": "titanium", "quantity": 20,
             "destination_system_id": "vega", "fee": 900, "net": 500},
        ])
        self.assertIsNone(self._captain(
            report, ship={"credits": 500, "cargo": {"titanium": 20}})._quantum_manual_action())

    def test_the_automation_is_armed_after_the_manual_order(self):
        report = self._report([
            {"commodity_id": "titanium", "quantity": 20,
             "destination_system_id": "vega", "fee": 10, "net": 500},
        ])
        captain = self._captain(report)
        captain.attempted_signatures.add(("/api/trade/quantum/place", "titanium"))
        action = captain._quantum_manual_action()
        self.assertEqual(action[0], "/api/trade/quantum/automation")
        self.assertEqual(action[1], {"enabled": True, "min_net": 0})
        self.assertEqual(action[2], "quantum_automation")

    def test_the_automation_is_stood_down_after_an_order_or_its_window(self):
        report = self._report([])
        traded = self._captain(report, quantum_automation={
            "enabled": True, "min_net": 0, "orders": 1})
        self.assertEqual(
            traded._quantum_manual_action(),
            ("/api/trade/quantum/automation", {"enabled": False}, "quantum_automation"),
        )
        idle = self._captain(report, quantum_automation={
            "enabled": True, "min_net": 0, "orders": 0})
        idle.quantum_armed_at = 1
        idle.total_steps = 99
        self.assertEqual(idle._quantum_manual_action()[1], {"enabled": False})

    def test_both_quantum_routes_are_keyed(self):
        captain = self._captain(self._report([]))
        captain.attempted_signatures.add(("/api/trade/quantum/place", "titanium"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/trade/quantum/place", {"commodity_id": "titanium"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/trade/quantum/place", {"commodity_id": "medicines"}))
        captain.attempted_signatures.add(("/api/trade/quantum/automation", "True"))
        self.assertFalse(captain._tour_action_attempted(
            "/api/trade/quantum/automation", {"enabled": False}),
            "standing auto-freight down must stay reachable after arming it")


class FleetPatrolTourTest(unittest.TestCase):
    """The captain patrols an escort on a connected lane and recalls it (ADR-382)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "current_system": {"id": "sol", "connections": ["vega", "orion"]},
            "fleet_manager": {"ships": [
                {"id": "escort_1", "hull": 90, "max_hull": 120,
                 "assigned_system_id": "sol", "status": "escorting"},
            ]},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_a_local_escort_patrols_the_first_connection(self):
        self.assertEqual(
            self._captain()._patrol_action(),
            ("/api/fleet/escort/assign",
             {"ship_id": "escort_1", "system_id": "vega"}, "escort_assign"),
        )

    def test_a_detached_escort_is_recalled_first(self):
        captain = self._captain(fleet_manager={"ships": [
            {"id": "escort_1", "hull": 90, "max_hull": 120,
             "assigned_system_id": "kepler", "status": "escorting"},
        ]})
        self.assertEqual(
            captain._patrol_action(),
            ("/api/fleet/escort/assign",
             {"ship_id": "escort_1", "system_id": "sol"}, "escort_assign"),
        )

    def test_a_destroyed_or_absent_escort_is_ignored(self):
        destroyed = self._captain(fleet_manager={"ships": [
            {"id": "hulk", "hull": 0, "max_hull": 120, "assigned_system_id": "sol"},
        ]})
        self.assertIsNone(destroyed._patrol_action())
        self.assertIsNone(self._captain(fleet_manager={"ships": []})._patrol_action())
        self.assertIsNone(self._captain(
            current_system={"id": "sol", "connections": []})._patrol_action())

    def test_no_patrol_before_act_vi(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._patrol_action())

    def test_patrol_and_recall_are_separate_signatures(self):
        captain = self._captain()
        captain.attempted_signatures.add(("/api/fleet/escort/assign", "vega"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/fleet/escort/assign", {"ship_id": "escort_1", "system_id": "vega"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/fleet/escort/assign", {"ship_id": "escort_1", "system_id": "sol"}),
            "the recall direction must stay reachable after the patrol")


class AwayRecallPolicyTest(unittest.TestCase):
    """An active expedition is recalled before a transit tick can resolve it (ADR-384)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {"ship": {"hull": 100, "away_missions": []}}
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_the_first_expedition_is_protected_so_it_can_finish(self):
        captain = self._captain(ship={
            "hull": 100,
            "away_missions": [{"id": "away_1", "mission_type": "geological_survey"}],
        })
        self.assertIsNone(captain._away_recall_action())
        self.assertEqual(captain.away_protected_mission, "away_1")

    def test_a_later_expedition_is_recalled_before_transit(self):
        captain = self._captain(ship={
            "hull": 100,
            "travel": {"target": "b2"},
            "away_missions": [
                {"id": "away_1", "mission_type": "geological_survey"},
                {"id": "away_2", "mission_type": "salvage_sweep"},
            ],
        })
        captain.away_protected_mission = "away_1"
        self.assertEqual(
            captain._choose(7),
            ("/api/away/recall", {"mission_id": "away_2"}, "away_recall"),
        )

    def test_no_recall_without_an_active_mission(self):
        self.assertIsNone(self._captain()._away_recall_action())

    def test_recall_is_one_shot_per_mission(self):
        captain = self._captain(ship={
            "hull": 100,
            "away_missions": [
                {"id": "away_1", "mission_type": "geological_survey"},
                {"id": "away_2", "mission_type": "salvage_sweep"},
            ],
        })
        captain.away_protected_mission = "away_1"
        captain.attempted.add("/api/away/recall")
        captain.attempted_signatures.add(("/api/away/recall", "away_2"))
        self.assertIsNone(captain._away_recall_action())

    def test_each_mission_is_keyed_by_its_id(self):
        captain = self._captain(ship={
            "hull": 100,
            "away_missions": [
                {"id": "away_1", "mission_type": "geological_survey"},
                {"id": "away_2", "mission_type": "salvage_sweep"},
                {"id": "away_3", "mission_type": "xenobiology"},
            ],
        })
        captain.away_protected_mission = "away_1"
        captain.attempted_signatures.add(("/api/away/recall", "away_2"))
        self.assertEqual(captain._away_recall_action()[1]["mission_id"], "away_3")


class AllyFormationPolicyTest(unittest.TestCase):
    """The captain hails a captain to trust 50 and forms the alliance (ADR-385)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "ai_captains": [
                {"id": "vance", "name": "Admiral Vance", "trust": 10, "ally": False},
                {"id": "rook", "name": "Captain Rook", "trust": 44, "ally": False},
                {"id": "old_ally", "name": "Captain Grey", "trust": 80, "ally": True},
            ],
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_the_most_trusted_non_ally_is_hailed_until_fifty(self):
        self.assertEqual(
            self._captain()._ally_action(),
            ("/api/ai/interact", {"captain_id": "rook", "action": "hail"}, "ai"),
        )

    def test_trust_fifty_forms_the_alliance(self):
        captain = self._captain(ai_captains=[
            {"id": "rook", "trust": 50, "ally": False},
        ])
        self.assertEqual(
            captain._ally_action(),
            ("/api/ally/form", {"captain_id": "rook"}, "ally"),
        )

    def test_an_already_allied_captain_is_skipped(self):
        captain = self._captain(ai_captains=[
            {"id": "old_ally", "trust": 90, "ally": True},
        ])
        self.assertIsNone(captain._ally_action())

    def test_no_hailing_before_act_vi(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._ally_action())

    def test_each_captain_is_keyed_by_its_id(self):
        captain = self._captain(ai_captains=[])
        captain.attempted_signatures.add(("/api/ally/form", "rook"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/ally/form", {"captain_id": "rook"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/ally/form", {"captain_id": "vance"}),
            "a second captain must stay reachable after the first alliance")


class MessagesSendPolicyTest(unittest.TestCase):
    """The captain sends one quantum report after the campaign (ADR-386)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "messages": [{"id": "m1", "sender": "Admiral Vance", "subject": "Welcome"}],
            "ai_captains": [{"id": "rook", "name": "Captain Rook"}],
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_the_first_correspondent_receives_a_report(self):
        action = self._captain()._send_action()
        self.assertEqual(action[0], "/api/messages/send")
        self.assertEqual(action[1]["recipient"], "Admiral Vance")
        self.assertEqual(action[2], "messages_send")

    def test_a_captain_name_is_the_fallback_recipient(self):
        action = self._captain(messages=[
            {"id": "m1", "sender": "", "subject": "System notice"},
        ])._send_action()
        self.assertEqual(action[1]["recipient"], "Captain Rook")

    def test_no_recipient_or_pre_story_run_sends_nothing(self):
        self.assertIsNone(self._captain(
            messages=[], ai_captains=[])._send_action())
        self.assertIsNone(self._captain(
            story_status={"completed": False})._send_action())

    def test_the_report_is_sent_once(self):
        captain = self._captain()
        captain.attempted.add("/api/messages/send")
        self.assertIsNone(captain._send_action())


class ShipyardSellPolicyTest(unittest.TestCase):
    """The captain trades in a safe equipped upgrade after the campaign (ADR-387)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "orbiting_body": {"id": "b1", "station_dockable": True},
            "ship": {
                "credits": 5000, "fuel": 60, "max_fuel": 80,
                "equipped_upgrades": {"engines": "warp_booster_mk1"},
            },
            "catalog_upgrades": [
                {"id": "warp_booster_mk1", "slot": "engines",
                 "stat_bonus": {"fuel_efficiency": 0.20}},
                {"id": "cargo_bay_mk1", "slot": "utility",
                 "stat_bonus": {"cargo_capacity": 20.0}},
            ],
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_a_safe_equipped_upgrade_is_traded_in(self):
        self.assertEqual(
            self._captain()._shipyard_sell_action(),
            ("/api/shipyard/sell", {"slot": "engines"}, "shipyard_sell"),
        )

    def test_cargo_and_fuel_capacity_upgrades_are_kept(self):
        captain = self._captain(ship={
            "credits": 5000, "fuel": 60, "max_fuel": 80,
            "equipped_upgrades": {"utility": "cargo_bay_mk1"},
        })
        self.assertIsNone(captain._shipyard_sell_action())

    def test_a_low_tank_waits_for_the_refuel(self):
        captain = self._captain(ship={
            "credits": 5000, "fuel": 10, "max_fuel": 80,
            "equipped_upgrades": {"engines": "warp_booster_mk1"},
        })
        self.assertIsNone(captain._shipyard_sell_action())

    def test_it_needs_a_dock_and_the_campaign_to_be_finished(self):
        self.assertIsNone(self._captain(orbiting_body=None)._shipyard_sell_action())
        self.assertIsNone(self._captain(
            story_status={"completed": False})._shipyard_sell_action())

    def test_the_trade_in_is_one_shot_per_slot(self):
        captain = self._captain()
        captain.attempted.add("/api/shipyard/sell")
        captain.attempted_signatures.add(("/api/shipyard/sell", "engines"))
        self.assertIsNone(captain._shipyard_sell_action())

    def test_each_slot_is_keyed_by_its_name(self):
        captain = self._captain()
        captain.attempted_signatures.add(("/api/shipyard/sell", "engines"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/shipyard/sell", {"slot": "engines"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/shipyard/sell", {"slot": "shields"}),
            "a second slot must stay reachable after the first trade-in")


class CrewDismissPolicyTest(unittest.TestCase):
    """The captain trims redundant unassigned crew after the campaign (ADR-388)."""

    def _captain(self, crew, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "crew": crew,
            "outposts": [],
            "fleet_manager": {"ships": []},
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    @staticmethod
    def _member(crew_id, skill, station="", role="engineer", specialty="engineering"):
        return {"id": crew_id, "role": role, "specialty": specialty,
                "skill": skill, "station": station, "status": "active"}

    def test_the_weakest_duplicate_is_dismissed_first(self):
        captain = self._captain([
            self._member("e1", 5),
            self._member("e2", 4),
            self._member("e3", 2),
            self._member("e4", 1),
        ])
        self.assertEqual(
            captain._crew_dismiss_action(),
            ("/api/crew/dismiss", {"crew_id": "e4"}, "crew_dismiss"),
        )

    def test_two_of_each_role_are_kept(self):
        captain = self._captain([
            self._member("e1", 5), self._member("e2", 4),
            self._member("p1", 5, role="pilot", specialty="evasion"),
            self._member("p2", 4, role="pilot", specialty="evasion"),
        ])
        self.assertIsNone(captain._crew_dismiss_action())

    def test_stationed_and_assigned_crew_are_never_dismissed(self):
        captain = self._captain(
            crew=[
                self._member("e1", 5), self._member("e2", 4),
                self._member("e3", 1), self._member("e4", 1),
                self._member("e5", 1, station="engineering"),
                self._member("e6", 1),
            ],
            outposts=[{"assigned_crew": ["e3"]}],
            fleet_manager={"ships": [{"captain_id": "e4"}]},
            ship={"away_missions": [{"id": "away_1", "crew_ids": ["e6"]}]},
        )
        self.assertIsNone(captain._crew_dismiss_action())

    def test_it_needs_the_campaign_finished(self):
        self.assertIsNone(self._captain(
            [self._member("e1", 5), self._member("e2", 4), self._member("e3", 1)],
            story_status={"completed": False})._crew_dismiss_action())

    def test_each_crew_member_is_keyed_by_id(self):
        captain = self._captain([self._member("e1", 5), self._member("e2", 4),
                                 self._member("e3", 1)])
        captain.attempted_signatures.add(("/api/crew/dismiss", "e3"))
        self.assertTrue(captain._tour_action_attempted(
            "/api/crew/dismiss", {"crew_id": "e3"}))
        self.assertFalse(captain._tour_action_attempted(
            "/api/crew/dismiss", {"crew_id": "e2"}),
            "a second trim must stay reachable after the first dismissal")


class OutpostSupplyLinkPolicyTest(unittest.TestCase):
    """The captain founds a second outpost and links its supply (ADR-390)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "current_system": {
                "id": "ashen", "name": "Ashen Choir",
                "bodies": [
                    {"id": "ashen_body_5", "body_type": "research_outpost",
                     "station_dockable": True},
                    {"id": "ashen_body_1", "body_type": "desert_world",
                     "station_dockable": True},
                    {"id": "ashen_body_2", "body_type": "ice_world",
                     "station_dockable": True},
                ],
            },
            "orbiting_body": {"id": "ashen_body_5", "body_type": "research_outpost",
                              "station_dockable": True},
            "outpost_options": ["research", "shipyard"],
            "outpost_body_occupied": False,
            "ship": {"credits": 20000, "mastery": {"level": 5}},
            "outposts": [],
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_the_current_eligible_body_is_built_first(self):
        self.assertEqual(
            self._captain()._outpost_link_action(),
            ("/api/outpost/build",
             {"body_id": "ashen_body_5", "outpost_type": "research"}, "outpost_build"),
        )

    def test_an_ineligible_body_is_orbited_next(self):
        self.assertEqual(
            self._captain(outpost_options=[])._outpost_link_action(),
            ("/api/orbit", {"target": "ashen_body_1"}, "orbit"),
        )

    def test_the_second_body_is_orbited_after_the_first_build(self):
        captain = self._captain(
            outpost_body_occupied=True,
            outposts=[{"id": "o1", "system_id": "ashen", "body_id": "ashen_body_5",
                       "supply_hub_id": ""}],
        )
        self.assertEqual(
            captain._outpost_link_action(),
            ("/api/orbit", {"target": "ashen_body_1"}, "orbit"),
        )

    def test_two_unlinked_outposts_are_linked(self):
        captain = self._captain(outposts=[
            {"id": "o1", "system_id": "ashen", "body_id": "ashen_body_5",
             "supply_hub_id": ""},
            {"id": "o2", "system_id": "ashen", "body_id": "ashen_body_1",
             "supply_hub_id": ""},
        ])
        self.assertEqual(
            captain._outpost_link_action(),
            ("/api/outpost/link", {"outpost_id": "o2", "hub_id": "o1"}, "outpost_link"),
        )

    def test_the_link_is_one_shot(self):
        captain = self._captain(outposts=[
            {"id": "o1", "system_id": "ashen", "body_id": "ashen_body_5",
             "supply_hub_id": ""},
            {"id": "o2", "system_id": "ashen", "body_id": "ashen_body_1",
             "supply_hub_id": ""},
        ])
        captain.attempted.add("/api/outpost/link")
        self.assertIsNone(captain._outpost_link_action())

    def test_it_needs_the_campaign_credits_and_mastery(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._outpost_link_action())
        self.assertIsNone(self._captain(
            ship={"credits": 1000, "mastery": {"level": 5}})._outpost_link_action())
        self.assertIsNone(self._captain(
            ship={"credits": 20000, "mastery": {"level": 1}})._outpost_link_action())

    def test_another_systems_outpost_does_not_count(self):
        captain = self._captain(outposts=[
            {"id": "old", "system_id": "sol", "body_id": "sol_body_7",
             "supply_hub_id": ""},
        ])
        self.assertEqual(captain._outpost_link_action()[0], "/api/outpost/build")


class MegastructureRestorePolicyTest(unittest.TestCase):
    """The captain restores an ancient structure after the campaign (ADR-391)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "current_system": {
                "id": "sol", "name": "Sol System",
                "bodies": [
                    {"id": "sol_body_7", "body_type": "research_outpost"},
                    {"id": "sol_ring_world", "body_type": "ring_world"},
                    {"id": "sol_dyson_sphere", "body_type": "dyson_sphere"},
                ],
            },
            "orbiting_body": {"id": "sol_body_7", "body_type": "research_outpost"},
            "megastructure": {"restorable": False, "body_id": "sol_body_7",
                              "body_name": "Sol VII", "complete": False,
                              "cost": 0, "orbiting": True},
            "ship": {"credits": 30000},
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_a_restorable_orbited_structure_is_restored(self):
        captain = self._captain(
            orbiting_body={"id": "sol_ring_world", "body_type": "ring_world"},
            megastructure={
                "restorable": True, "body_id": "sol_ring_world",
                "body_name": "Sol Ring", "complete": False, "cost": 10000,
                "orbiting": True,
            })
        self.assertEqual(
            captain._megastructure_action(),
            ("/api/megastructure/restore", {"body_id": "sol_ring_world"},
             "megastructure"),
        )

    def test_a_completed_structure_is_skipped_for_the_next_candidate(self):
        captain = self._captain(
            orbiting_body={"id": "sol_ring_world", "body_type": "ring_world"},
            megastructure={
                "restorable": True, "body_id": "sol_ring_world",
                "body_name": "Sol Ring", "complete": True, "cost": 10000,
                "orbiting": True,
            })
        self.assertEqual(
            captain._megastructure_action(),
            ("/api/orbit", {"target": "sol_dyson_sphere"}, "orbit"),
        )

    def test_a_plain_body_orbits_the_first_restorable_type(self):
        self.assertEqual(
            self._captain()._megastructure_action(),
            ("/api/orbit", {"target": "sol_ring_world"}, "orbit"),
        )

    def test_a_probed_body_is_not_orbited_twice(self):
        captain = self._captain(current_system={
            "id": "sol", "name": "Sol System",
            "bodies": [
                {"id": "sol_body_7", "body_type": "research_outpost"},
                {"id": "sol_ring_world", "body_type": "ring_world"},
            ],
        })
        self.assertEqual(
            captain._megastructure_action(),
            ("/api/orbit", {"target": "sol_ring_world"}, "orbit"),
        )
        self.assertIsNone(
            captain._megastructure_action(),
            "a body whose structure is not restorable must not be orbited again",
        )

    def test_the_probe_budget_bounds_an_exhausted_system(self):
        captain = self._captain(current_system={
            "id": "sol", "name": "Sol System",
            "bodies": [
                {"id": "sol_body_7", "body_type": "research_outpost"},
                {"id": "sol_ring_world", "body_type": "ring_world"},
                {"id": "sol_dyson_sphere", "body_type": "dyson_sphere"},
            ],
        })
        self.assertEqual(
            captain._megastructure_action()[1]["target"], "sol_ring_world"
        )
        self.assertEqual(
            captain._megastructure_action()[1]["target"], "sol_dyson_sphere"
        )
        self.assertIsNone(
            captain._megastructure_action(),
            "every candidate probed once, then the errand ends",
        )

    def test_an_unaffordable_restore_waits(self):
        captain = self._captain(
            ship={"credits": 500},
            orbiting_body={"id": "sol_ring_world", "body_type": "ring_world"},
            megastructure={
                "restorable": True, "body_id": "sol_ring_world",
                "body_name": "Sol Ring", "complete": False, "cost": 10000,
                "orbiting": True,
            },
        )
        self.assertIsNone(captain._megastructure_action())

    def test_it_needs_the_campaign_and_a_candidate(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._megastructure_action())
        self.assertIsNone(self._captain(
            current_system={"id": "a", "bodies": [
                {"id": "a1", "body_type": "terrestrial"}]},
            orbiting_body={"id": "a1", "body_type": "terrestrial"},
        )._megastructure_action())

    def test_the_restore_is_one_shot(self):
        captain = self._captain(megastructure={
            "restorable": True, "body_id": "sol_ring_world",
            "body_name": "Sol Ring", "complete": False, "cost": 10000,
            "orbiting": True,
        })
        captain.attempted.add("/api/megastructure/restore")
        self.assertIsNone(captain._megastructure_action())


class RelicFusionPolicyTest(unittest.TestCase):
    """The captain fuses the lowest complete relic set after the campaign (ADR-392)."""

    def _captain(self, relics, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "ship": {"relics": relics},
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    @staticmethod
    def _relics(rarity, count):
        return [{"id": f"{rarity}_{index}", "rarity": rarity}
                for index in range(count)]

    def test_three_commons_are_fused(self):
        captain = self._captain(self._relics("common", 3))
        self.assertEqual(
            captain._relic_fuse_action(),
            ("/api/relics/fuse", {"rarity": "common"}, "relic_fuse"),
        )

    def test_the_lowest_complete_rarity_wins(self):
        captain = self._captain(
            self._relics("common", 2) + self._relics("rare", 4)
            + self._relics("epic", 3))
        self.assertEqual(captain._relic_fuse_action()[1], {"rarity": "rare"})

    def test_legendary_relics_never_fuse(self):
        captain = self._captain(
            self._relics("legendary", 5) + self._relics("common", 2))
        self.assertIsNone(captain._relic_fuse_action())

    def test_no_fusion_before_the_campaign_or_without_a_set(self):
        self.assertIsNone(self._captain(
            self._relics("common", 6),
            story_status={"completed": False})._relic_fuse_action())
        self.assertIsNone(self._captain(
            self._relics("common", 2) + self._relics("rare", 2))._relic_fuse_action())

    def test_the_fusion_is_one_shot(self):
        captain = self._captain(self._relics("common", 9))
        captain.attempted.add("/api/relics/fuse")
        self.assertIsNone(captain._relic_fuse_action())


class OverhaulServicePolicyTest(unittest.TestCase):
    """The captain scrubs frame wear at a drydock after the campaign (ADR-393)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "orbiting_body": {"id": "b1", "station_dockable": True},
            "drydock": {"docked": True, "wear": 73.0, "overhaul_cost": 328},
            "ship": {"credits": 5000, "wear": 73.0},
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_a_worn_docked_frame_is_overhauled(self):
        self.assertEqual(
            self._captain()._overhaul_action(),
            ("/api/overhaul", {}, "overhaul"),
        )

    def test_a_pristine_frame_needs_no_service(self):
        self.assertIsNone(self._captain(
            ship={"credits": 5000, "wear": 0.0},
            drydock={"docked": True, "wear": 0.0, "overhaul_cost": 0},
        )._overhaul_action())

    def test_it_needs_a_dock_and_the_service_fee(self):
        self.assertIsNone(self._captain(orbiting_body=None)._overhaul_action())
        self.assertIsNone(self._captain(
            ship={"credits": 100, "wear": 73.0})._overhaul_action())

    def test_it_waits_for_the_campaign_to_complete(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._overhaul_action())

    def test_the_overhaul_is_one_shot(self):
        captain = self._captain()
        captain.attempted.add("/api/overhaul")
        self.assertIsNone(captain._overhaul_action())


class FabricateFieldRepairPolicyTest(unittest.TestCase):
    """The captain fabricates field repairs from titanium after the campaign (ADR-394)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "ship": {"hull": 50, "max_hull": 100, "fuel": 30, "max_fuel": 80,
                     "cargo": {"titanium": 3}},
        }
        for key, value in state.items():
            if isinstance(base.get(key), dict) and isinstance(value, dict):
                base[key].update(value)
            else:
                base[key] = value
        captain.state = base
        return captain

    def test_a_hurt_hull_gets_a_patch_kit(self):
        self.assertEqual(
            self._captain()._fabricate_action(),
            ("/api/fabricate", {"munitions_type": "patch_kit"}, "fabricate"),
        )

    def test_a_low_tank_gets_a_fuel_cell_when_the_hull_is_whole(self):
        captain = self._captain(ship={
            "hull": 100, "max_hull": 100, "fuel": 10, "max_fuel": 80,
            "cargo": {"titanium": 3}})
        self.assertEqual(
            captain._fabricate_action(),
            ("/api/fabricate", {"munitions_type": "fuel_cell"}, "fabricate"),
        )

    def test_a_full_ship_or_empty_hold_fabricates_nothing(self):
        self.assertIsNone(self._captain(ship={
            "hull": 100, "max_hull": 100, "fuel": 80, "max_fuel": 80,
            "cargo": {"titanium": 3}})._fabricate_action())
        self.assertIsNone(self._captain(ship={
            "hull": 50, "max_hull": 100, "fuel": 30, "max_fuel": 80,
            "cargo": {}})._fabricate_action())

    def test_it_waits_for_the_campaign(self):
        self.assertIsNone(self._captain(
            story_status={"completed": False})._fabricate_action())

    def test_one_success_per_campaign_is_enough(self):
        captain = self._captain()
        captain.succeeded.add("/api/fabricate")
        self.assertIsNone(captain._fabricate_action())


class ReconstructWarRecoveryTest(unittest.TestCase):
    """The captain rebuilds a devastated inhabited world in the current system (ADR-395)."""

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "current_system": {
                "id": "ashen", "name": "Ashen Choir",
                "bodies": [
                    {"id": "ashen_body_5", "body_type": "research_outpost",
                     "population": 644268, "devastation": 0.2},
                    {"id": "ashen_body_6", "body_type": "savanna",
                     "population": 617803935, "devastation": 0.3},
                    {"id": "ashen_rock", "body_type": "barren",
                     "population": 0, "devastation": 0.8},
                ],
            },
            "orbiting_body": {"id": "ashen_body_1", "body_type": "ice_world"},
            "ship": {"credits": 5000, "landed_body_id": ""},
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_the_worst_devastated_world_is_orbited(self):
        self.assertEqual(
            self._captain()._reconstruct_action(),
            ("/api/orbit", {"target": "ashen_body_6"}, "orbit"),
        )

    def test_an_orbited_world_is_rebuilt_with_credits(self):
        captain = self._captain(
            orbiting_body={"id": "ashen_body_6", "body_type": "savanna"})
        self.assertEqual(
            captain._reconstruct_action(),
            ("/api/reconstruct",
             {"body_id": "ashen_body_6", "mode": "credits"}, "reconstruct"),
        )

    def test_a_landed_world_is_rebuilt_in_place(self):
        captain = self._captain(
            orbiting_body={"id": "ashen_body_6", "body_type": "savanna"},
            ship={"credits": 5000, "landed_body_id": "ashen_body_6"})
        self.assertEqual(captain._reconstruct_action()[0], "/api/reconstruct")

    def test_uninhabited_or_whole_worlds_are_ignored(self):
        captain = self._captain(current_system={
            "id": "ashen", "bodies": [
                {"id": "ashen_rock", "body_type": "barren",
                 "population": 0, "devastation": 0.9},
                {"id": "ashen_whole", "body_type": "savanna",
                 "population": 1000, "devastation": 0.0},
            ]})
        self.assertIsNone(captain._reconstruct_action())

    def test_it_needs_the_reconstruction_fee(self):
        captain = self._captain(
            orbiting_body={"id": "ashen_body_6", "body_type": "savanna"},
            ship={"credits": 100, "landed_body_id": ""})
        self.assertIsNone(captain._reconstruct_action())

    def test_the_rebuild_is_one_shot(self):
        captain = self._captain(
            orbiting_body={"id": "ashen_body_6", "body_type": "savanna"})
        captain.attempted.add("/api/reconstruct")
        self.assertIsNone(captain._reconstruct_action())


class SalvageScoopProspectingTest(unittest.TestCase):
    """The captain prospects a derelict and scoops fuel after the campaign (ADR-396)."""

    BODIES = [
        {"id": "kepler_station", "body_type": "orbital_station",
         "station_dockable": True},
        {"id": "kepler_ice", "body_type": "ice_world"},
        {"id": "kepler_star", "body_type": "star"},
        {"id": "kepler_rock", "body_type": "barren"},
    ]

    def _captain(self, **state):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        base = {
            "story_status": {"completed": True},
            "current_system": {"id": "kepler", "bodies": list(self.BODIES)},
            "orbiting_body": {"id": "kepler_station", "body_type": "orbital_station",
                              "station_dockable": True},
            "ship": {"credits": 5000, "fuel": 60, "max_fuel": 80,
                     "landed_body_id": ""},
            "scoop": None,
            "salvage_site": None,
        }
        for key, value in state.items():
            base[key] = value
        captain.state = base
        return captain

    def test_the_mirrored_body_type_sets_match_the_engine(self):
        self.assertEqual(AiCaptain.SCOOP_BODY_TYPES, frozenset(SCOOP_PROFILES))
        self.assertEqual(AiCaptain.DERELICT_EXCLUDED_TYPES,
                         DERELICT_EXCLUDED_TYPES)

    def test_a_derelict_candidate_is_probed_after_the_campaign(self):
        self.assertEqual(
            self._captain()._salvage_action(),
            ("/api/orbit", {"target": "kepler_ice"}, "orbit"),
        )

    def test_excluded_and_dockable_bodies_are_never_probed(self):
        captain = self._captain(current_system={
            "id": "kepler", "bodies": [
                {"id": "kepler_station", "body_type": "orbital_station",
                 "station_dockable": True},
                {"id": "kepler_star", "body_type": "star"},
                {"id": "kepler_relay", "body_type": "quantum_relay"},
            ]})
        self.assertIsNone(captain._salvage_action())

    def test_a_probed_derelict_moves_to_the_next_candidate(self):
        captain = self._captain()
        captain.salvage_probed.add("kepler_ice")
        self.assertEqual(captain._salvage_action()[1], {"target": "kepler_rock"})

    def test_the_probe_is_capped(self):
        captain = self._captain()
        captain.salvage_probes = AiCaptain.SALVAGE_PROBE_LIMIT
        self.assertIsNone(captain._salvage_action())

    def test_a_claimed_derelict_is_not_probed_again(self):
        captain = self._captain()
        captain.succeeded.add("/api/salvage")
        self.assertIsNone(captain._salvage_action())

    def test_a_detected_site_is_claimed_even_after_a_salvage(self):
        captain = self._captain(
            orbiting_body={"id": "kepler_ice", "body_type": "ice_world"},
            salvage_site={"body_id": "kepler_ice", "name": "Freighter Wreck"})
        captain.succeeded.add("/api/salvage")
        self.assertEqual(captain._salvage_action(),
                         ("/api/salvage", {}, "salvage"))

    def test_a_detected_site_is_left_alone_once_the_milestone_is_banked(self):
        captain = self._captain(
            orbiting_body={"id": "kepler_ice", "body_type": "ice_world"},
            salvage_site={"body_id": "kepler_ice", "name": "Freighter Wreck"})
        captain.succeeded.add("/api/salvage")
        captain.state["stats"] = {"salvage": AiCaptain.WRECK_TARGET}
        self.assertIsNone(captain._salvage_action())

    def test_a_low_tank_orbits_a_scoopable_body(self):
        captain = self._captain(
            ship={"credits": 5000, "fuel": 20, "max_fuel": 80,
                  "landed_body_id": ""})
        self.assertEqual(
            captain._scoop_action(),
            ("/api/orbit", {"target": "kepler_ice"}, "orbit"),
        )

    def test_a_healthy_tank_does_not_scoop(self):
        self.assertIsNone(self._captain()._scoop_action())

    def test_an_available_scoop_here_is_claimed_directly(self):
        captain = self._captain(
            orbiting_body={"id": "kepler_ice", "body_type": "ice_world"},
            scoop={"available": True},
            ship={"credits": 5000, "fuel": 20, "max_fuel": 80,
                  "landed_body_id": ""})
        self.assertEqual(captain._scoop_action(), ("/api/scoop", {}, "scoop"))

    def test_a_derelict_under_the_ship_is_claimed(self):
        captain = self._captain(
            orbiting_body={"id": "kepler_ice", "body_type": "ice_world"},
            salvage_site={"body_id": "kepler_ice", "name": "Freighter Wreck"})
        self.assertEqual(captain._salvage_action(),
                         ("/api/salvage", {}, "salvage"))

    def test_the_last_probe_is_still_claimed_at_the_limit(self):
        captain = self._captain(
            orbiting_body={"id": "kepler_ice", "body_type": "ice_world"},
            salvage_site={"body_id": "kepler_ice", "name": "Freighter Wreck"})
        captain.salvage_probes = AiCaptain.SALVAGE_PROBE_LIMIT
        self.assertEqual(captain._salvage_action()[0], "/api/salvage")

    def test_the_scoop_is_one_shot_once_it_succeeds(self):
        captain = self._captain(
            ship={"credits": 5000, "fuel": 20, "max_fuel": 80,
                  "landed_body_id": ""})
        captain.succeeded.add("/api/scoop")
        self.assertIsNone(captain._scoop_action())

    def test_nothing_prospects_before_the_campaign(self):
        captain = self._captain(story_status={"completed": False})
        self.assertIsNone(captain._salvage_action())
        self.assertIsNone(captain._scoop_action())


class AnomalyPolicyTest(unittest.TestCase):
    """The captain picks an anomaly check that passes (ADR-372)."""

    def _captain(self, choices, encounter_actions=None):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        state = {
            "ship": {"hull": 100, "max_hull": 100, "fuel": 40, "max_fuel": 60},
            "active_anomaly": {"id": "a1", "title": "Rift", "choices": choices},
        }
        if encounter_actions is not None:
            state["encounter"] = {
                "encounter": {"kind": "anomaly", "actions": encounter_actions}
            }
        captain.state = state
        return captain

    def test_a_ready_check_beats_the_first_failing_choice(self):
        captain = self._captain(
            [
                {"choice_id": "deep", "required_power": "sensors", "min_power_threshold": 45},
                {"choice_id": "sweep", "required_power": "sensors", "min_power_threshold": 20},
            ],
            encounter_actions=[
                {"id": "deep", "ready": False},
                {"id": "sweep", "ready": True},
            ],
        )
        self.assertEqual(captain._choose(7)[1]["choice_id"], "sweep")
        self.assertEqual(captain._choose(7)[2], "anomaly")

    def test_without_a_ready_check_the_lowest_threshold_wins(self):
        captain = self._captain(
            [
                {"choice_id": "deep", "required_power": "sensors", "min_power_threshold": 45},
                {"choice_id": "safe", "required_power": "none", "min_power_threshold": 0},
                {"choice_id": "sweep", "required_power": "engines", "min_power_threshold": 20},
            ],
            encounter_actions=[{"id": "deep", "ready": False},
                               {"id": "safe", "ready": False},
                               {"id": "sweep", "ready": False}],
        )
        self.assertEqual(captain._choose(7)[1]["choice_id"], "safe")

    def test_without_the_payload_the_lowest_threshold_is_used(self):
        captain = self._captain([
            {"choice_id": "deep", "required_power": "sensors", "min_power_threshold": 45},
            {"choice_id": "sweep", "required_power": "engines", "min_power_threshold": 20},
        ])
        self.assertEqual(captain._choose(7)[1]["choice_id"], "sweep")

    def test_no_choices_does_not_post_an_anomaly(self):
        captain = self._captain([])
        self.assertNotEqual(captain._choose(7)[0], "/api/anomaly")


class WarSupportStateTest(unittest.TestCase):
    """A live war is supported from state, not from a tour slot that can miss (ADR-371)."""

    def _captain(self, wars, attempted=False):
        captain = AiCaptain(ApiClient(port=1), seed=42)
        captain.state = {
            "wars": wars,
            "ship": {
                "credits": 5000, "hull": 100, "max_hull": 100,
                "fuel": 40, "max_fuel": 60,
                "power": {"engines": 25, "shields": 25, "sensors": 25, "weapons": 25},
                "reactor": {"heat": 10.0, "max_heat": 100.0, "heat_pct": 10.0,
                            "last_vent_tick": -999},
            },
            "current_system": {"id": "sol"},
        }
        if attempted:
            captain.attempted.add("/api/war/support")
        return captain

    def test_an_active_war_is_supported_immediately(self):
        captain = self._captain([
            {"id": "w1", "active": True, "defender_id": "coalition"},
        ])
        action = captain._choose(3)
        self.assertEqual(action[0], "/api/war/support")
        self.assertEqual(action[1]["faction_id"], "coalition")
        self.assertEqual(action[1]["credits"], 100)

    def test_a_supported_war_is_not_supported_twice(self):
        captain = self._captain([
            {"id": "w1", "active": True, "defender_id": "coalition"},
        ], attempted=True)
        self.assertNotEqual(captain._choose(3)[0], "/api/war/support")

    def test_a_finished_war_is_ignored(self):
        captain = self._captain([
            {"id": "w1", "active": False, "defender_id": "coalition"},
        ])
        self.assertNotEqual(captain._choose(3)[0], "/api/war/support")


class AiPlayToolArgsTest(unittest.TestCase):
    def test_rejects_non_positive_steps(self):
        from tools.ai_play import main as ai_play_main
        for bad in ("0", "-5"):
            with self.assertRaises(SystemExit) as ctx:
                ai_play_main(["--steps", bad])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
