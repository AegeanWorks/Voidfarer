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

    def test_a_never_opening_gate_is_retried_but_not_forever(self):
        captain = self._captain()
        signature = ("/api/fleet/escort/buy", "buy")
        message = "Insufficient credits: 3200 cr required."
        scheduled = []
        for attempt in range(1, captain.REFUSAL_RETRY_LIMIT + 1):
            captain.total_steps = attempt * 100
            captain._note_refusal(signature, message)
            scheduled.append(signature in captain.retry_at)
        self.assertEqual(scheduled, [True] * (captain.REFUSAL_RETRY_LIMIT - 1) + [False],
                         "the last attempt must drop the cooldown, not extend it")
        captain.attempted.add(signature[0])
        captain.attempted_signatures.add(signature)
        self.assertTrue(captain._tour_action_attempted(signature[0], {"action": "buy"}),
                        "an exhausted gate must stay suppressed")

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
        self.assertIsNone(self._captain()._tour_away_recall())
        captain = self._captain(ship={"away_missions": [{"id": "m1"}]})
        self.assertEqual(captain._tour_away_recall()[1]["mission_id"], "m1")

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


class AiPlayToolArgsTest(unittest.TestCase):
    def test_rejects_non_positive_steps(self):
        from tools.ai_play import main as ai_play_main
        for bad in ("0", "-5"):
            with self.assertRaises(SystemExit) as ctx:
                ai_play_main(["--steps", bad])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
