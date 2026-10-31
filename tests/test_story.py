"""Unit and integration tests for Cadet Flight Academy and The Precursor Cipher story campaign."""

import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from voidfarer.cli import cmd_status, cmd_story, cmd_tutorial, main
from voidfarer.engine import SimulationEngine
from voidfarer.models import (
    ShipState,
    StoryChapter,
    StoryChoice,
    StoryRequirements,
    StoryState,
    StoryTransmission,
    TutorialState,
)
from voidfarer.retention import calculate_passive_multipliers
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager
from voidfarer.story import (
    CAMPAIGN_CHAPTERS,
    INITIAL_TUTORIAL_STEPS,
    STORY_RELICS,
    create_initial_story_state,
    create_initial_tutorial_state,
    migrate_story_state,
    resolve_story_ending,
)


class TestStoryAndTutorial(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_tutorial_initial_state(self):
        tut = self.engine.state.ship.tutorial
        self.assertFalse(tut.completed)
        self.assertFalse(tut.skipped)
        self.assertTrue(tut.is_active)
        self.assertEqual(tut.current_step_index, 0)
        self.assertEqual(tut.current_step.action_target, "orbit")
        self.assertEqual(len(tut.steps), 6)

    def test_tutorial_progressive_milestones(self):
        start_credits = self.engine.state.ship.credits
        start_xp = self.engine.state.ship.mastery.xp

        # Step 0: Orbit
        first_body = self.engine.current_system.bodies[1]  # planet
        ok, msg = self.engine.orbit(first_body.id)
        self.assertTrue(ok)
        tut = self.engine.state.ship.tutorial
        self.assertEqual(tut.current_step_index, 1)
        self.assertTrue(tut.steps[0].completed)
        self.assertGreater(self.engine.state.ship.credits, start_credits)
        self.assertGreater(self.engine.state.ship.mastery.xp, start_xp)

        # Step 1: Scan
        step1_credits = self.engine.state.ship.credits
        ok, msg, _ = self.engine.scan()
        self.assertTrue(ok)
        tut = self.engine.state.ship.tutorial
        self.assertEqual(tut.current_step_index, 2)
        self.assertTrue(tut.steps[1].completed)
        self.assertGreater(self.engine.state.ship.credits, step1_credits)

        # Step 2: Power Routing
        ok, msg = self.engine.route_power(30, 30, 20, 20)
        self.assertTrue(ok)
        tut = self.engine.state.ship.tutorial
        self.assertEqual(tut.current_step_index, 3)
        self.assertTrue(tut.steps[2].completed)

        # Step 3: Trade (must orbit station first)
        station = [b for b in self.engine.current_system.bodies if b.station_dockable][0]
        self.engine.orbit(station.id)
        from voidfarer.galaxy import GalaxyGenerator
        quotes = GalaxyGenerator.get_market_quotes(self.engine.current_system, station)
        ok, msg = self.engine.trade(quotes[0].commodity_id, 1, is_buy=True)
        self.assertTrue(ok)
        tut = self.engine.state.ship.tutorial
        self.assertEqual(tut.current_step_index, 4)
        self.assertTrue(tut.steps[3].completed)

        # Step 4: Fleet Drone
        with self.engine.lock:
            from voidfarer.models import GameState
            self.engine.state = GameState(
                version=self.engine.state.version,
                galaxy_seed=self.engine.state.galaxy_seed,
                ship=self.engine._clone_ship(credits=self.engine.state.ship.credits + 1000),
                systems=self.engine.state.systems,
                visited_systems=self.engine.state.visited_systems,
                active_anomaly=self.engine.state.active_anomaly,
                active_combat=self.engine.state.active_combat,
                stats=self.engine.state.stats,
            )
        ok, msg = self.engine.buy_drone("scout")
        self.assertTrue(ok)
        tut = self.engine.state.ship.tutorial
        self.assertEqual(tut.current_step_index, 5)
        self.assertTrue(tut.steps[4].completed)

        # Step 5: Jump & Graduation
        pre_grad_credits = self.engine.state.ship.credits
        target_sys = self.engine.current_system.connections[0]
        ok, msg = self.engine.jump(target_sys)
        self.assertTrue(ok)
        tut = self.engine.state.ship.tutorial
        self.assertTrue(tut.completed)
        self.assertFalse(tut.is_active)
        self.assertGreaterEqual(self.engine.state.ship.credits, pre_grad_credits + 1500)

        # Check Cadet Wings relic and max hull expansion
        relic_ids = [r.id for r in self.engine.state.ship.relics]
        self.assertIn("relic_cadet_wings", relic_ids)
        self.assertEqual(self.engine.state.ship.max_hull, 115)
        self.assertEqual(self.engine.state.ship.hull, 115)

    def test_tutorial_skip_and_reset(self):
        self.assertTrue(self.engine.state.ship.tutorial.is_active)

        ok, msg = self.engine.skip_tutorial()
        self.assertTrue(ok)
        self.assertTrue(self.engine.state.ship.tutorial.skipped)
        self.assertFalse(self.engine.state.ship.tutorial.is_active)

        # Reset tutorial
        ok, msg = self.engine.reset_tutorial()
        self.assertTrue(ok)
        tut = self.engine.state.ship.tutorial
        self.assertFalse(tut.skipped)
        self.assertFalse(tut.completed)
        self.assertEqual(tut.current_step_index, 0)
        self.assertTrue(tut.is_active)

    def test_story_initialization_and_first_chapter(self):
        story = self.engine.state.ship.story
        self.assertEqual(story.active_act, 1)
        self.assertEqual(story.current_chapter_id, "act1_ghost_signal")
        chap = story.current_chapter
        self.assertEqual(chap.target_system_id, "sol")
        self.assertFalse(chap.completed)
        self.assertGreater(len(story.transmission_log), 0)

    def test_story_arrival_transmissions(self):
        initial_log_len = len(self.engine.state.ship.story.transmission_log)
        self.assertEqual(initial_log_len, 1)

        # Resolve Act 1 first to unlock Act 2 (Sirius)
        ok, msg = self.engine.make_story_choice("choice_vance_telemetry")
        self.assertTrue(ok)
        self.assertGreater(len(self.engine.state.ship.story.transmission_log), initial_log_len)

        # Jump to sirius (Act 2 target)
        ok, msg = self.engine.jump("sirius")
        self.assertTrue(ok)
        new_story = self.engine.state.ship.story
        speakers = [tx.speaker for tx in new_story.transmission_log]
        self.assertTrue(any("Cipher" in s for s in speakers))

    def test_story_choices_and_factions(self):
        story = self.engine.state.ship.story
        ship = self.engine.state.ship

        # Invalid choice test
        ok, msg = self.engine.make_story_choice("invalid_choice_999")
        self.assertFalse(ok)

        # Valid choice: choice_cipher_leak
        ok, msg = self.engine.make_story_choice("choice_cipher_leak")
        self.assertTrue(ok)
        self.assertIn("Decryption Key", msg)

        # Faction reputation verified
        updated_ship = self.engine.state.ship
        self.assertGreater(updated_ship.story.faction_reputation["syndicate"], 0)
        self.assertEqual(updated_ship.story.active_act, 2)
        self.assertEqual(updated_ship.story.current_chapter_id, "act2_sirius_forge")

        # Check Relic award
        relic_ids = [r.id for r in updated_ship.relics]
        self.assertIn("relic_cipher_key", relic_ids)

    def test_story_serialization_roundtrip(self):
        ship = self.engine.state.ship
        data = ship.to_dict()
        restored_ship = ShipState.from_dict(data)

        self.assertEqual(restored_ship.tutorial.current_step_index, ship.tutorial.current_step_index)
        self.assertEqual(restored_ship.story.active_act, ship.story.active_act)
        self.assertEqual(len(restored_ship.story.transmission_log), len(ship.story.transmission_log))

    def test_story_target_system_enforcement_and_full_campaign(self):
        # Act I in Sol
        ok, msg = self.engine.make_story_choice("choice_vance_telemetry")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.story.active_act, 2)

        # Act II target is Sirius; attempting choice in Sol must be rejected
        ok, msg = self.engine.make_story_choice("choice_salvage_core")
        self.assertFalse(ok)
        self.assertIn("Travel to Sirius System", msg)

        # Jump to Sirius
        ok, msg = self.engine.jump("sirius")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.current_system_id, "sirius")

        # Now choice_salvage_core succeeds in Sirius
        ok, msg = self.engine.make_story_choice("choice_salvage_core")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.story.active_act, 3)

        # Act III target is Vega; attempting choice in Sirius must be rejected
        ok, msg = self.engine.make_story_choice("choice_unleash_gateways")
        self.assertFalse(ok)
        self.assertIn("Travel to Vega System", msg)

        # Ensure sufficient fuel for jump to Vega
        with self.engine.lock:
            self.engine.state = self.engine.state.__class__(
                version=self.engine.state.version,
                galaxy_seed=self.engine.state.galaxy_seed,
                ship=self.engine._clone_ship(fuel=50),
                systems=self.engine.state.systems,
                visited_systems=self.engine.state.visited_systems,
                active_anomaly=None,
                active_combat=None,
                stats=self.engine.state.stats,
            )

        # Jump to Vega
        ok, msg = self.engine.jump("vega")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.current_system_id, "vega")

        # Resolve Act III choice: campaign extends into the new acts
        ok, msg = self.engine.make_story_choice("choice_unleash_gateways")
        self.assertTrue(ok)
        self.assertFalse(self.engine.state.ship.story.completed)
        self.assertEqual(self.engine.state.ship.story.active_act, 4)
        self.assertTrue(self.engine.state.ship.story.flags.get("gateways_open"))

        # Act IV requires orbiting the Cygnus event horizon
        ok, msg = self.engine.make_story_choice("choice_first_dive")
        self.assertFalse(ok)
        self.assertIn("Objectives unmet", msg)
        self.assertIn("orbit", msg.lower())

        from voidfarer.navigation import shortest_route

        def travel_to(destination: str) -> None:
            path = shortest_route(self.engine.state.systems, self.engine.state.ship.current_system_id, destination)
            for target in path[1:]:
                with self.engine.lock:
                    self.engine.state = self.engine.state.__class__(
                        version=self.engine.state.version,
                        galaxy_seed=self.engine.state.galaxy_seed,
                        ship=self.engine._clone_ship(fuel=60),
                        systems=self.engine.state.systems,
                        visited_systems=self.engine.state.visited_systems,
                        active_anomaly=None,
                        active_combat=None,
                        stats=self.engine.state.stats,
                    )
                ok, msg = self.engine.jump(target)
                self.assertTrue(ok, msg)

        travel_to("cygnus_x1")
        ok, msg = self.engine.orbit("cygnus_x1_black_hole")
        self.assertTrue(ok)
        ok, msg = self.engine.make_story_choice("choice_first_dive")
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.story.active_act, 5)
        self.assertTrue(self.engine.state.ship.story.flags.get("voidfarer_oath"))
        self.assertIn("relic_void_compass", [r.id for r in self.engine.state.ship.relics])

        # Act V finale: the claim-title choice stays unlocked for the oath path
        travel_to("rift_station")
        status = self.engine.story_status()
        self.assertTrue(status["ready"])
        by_id = {c["id"]: c for c in status["choices"]}
        self.assertFalse(by_id["choice_claim_title"]["locked"])
        self.assertTrue(by_id["choice_sell_echoes"]["locked"])

        ok, msg = self.engine.make_story_choice("choice_claim_title")
        self.assertTrue(ok)
        self.assertIn("CAMPAIGN FINALE", msg)
        story = self.engine.state.ship.story
        self.assertTrue(story.completed)
        self.assertEqual(story.ending_id, "ending_first_voidfarer")
        self.assertTrue(any(t.callsign == "Campaign-Epilogue" for t in story.transmission_log))

        # Further choices after completion are cleanly rejected
        ok, msg = self.engine.make_story_choice("choice_archive_echoes")
        self.assertFalse(ok)
        self.assertIn("already complete", msg)

        # Verify CLI displays completed campaign epilogue gracefully
        res = cmd_story(self.engine, self.storage, ["story"])
        self.assertEqual(res, 0)
        res_status = cmd_status(self.engine)
        self.assertEqual(res_status, 0)

    def test_relic_passive_multipliers_integration(self):
        cadet_wings = STORY_RELICS["relic_cadet_wings"]
        cipher_key = STORY_RELICS["relic_cipher_key"]
        humanitarian = STORY_RELICS["relic_humanitarian_medal"]

        ship = self.engine._clone_ship(relics=(cadet_wings, cipher_key, humanitarian))
        passives = calculate_passive_multipliers(ship)

        self.assertGreaterEqual(passives["max_hull"], 15.0)
        self.assertGreater(passives["trade_margin"], 1.0)
        self.assertGreaterEqual(passives["shield_cap"], 35.0)

    def test_cli_tutorial_and_story_commands(self):
        # cmd_tutorial status
        res = cmd_tutorial(self.engine, self.storage, ["tutorial"])
        self.assertEqual(res, 0)

        # cmd_tutorial skip
        res = cmd_tutorial(self.engine, self.storage, ["tutorial", "skip"])
        self.assertEqual(res, 0)
        self.assertTrue(self.engine.state.ship.tutorial.skipped)

        # cmd_tutorial reset
        res = cmd_tutorial(self.engine, self.storage, ["tutorial", "reset"])
        self.assertEqual(res, 0)
        self.assertFalse(self.engine.state.ship.tutorial.skipped)

        # cmd_story status
        res = cmd_story(self.engine, self.storage, ["story"])
        self.assertEqual(res, 0)

        # Choose via CLI
        res = cmd_story(self.engine, self.storage, ["story", "choose", "choice_vance_telemetry"])
        self.assertEqual(res, 0)
        self.assertGreater(self.engine.state.ship.story.faction_reputation["coalition"], 0)

    def test_cli_main_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {"LOCALAPPDATA": tmp, "HOME": tmp, "USERPROFILE": tmp},
        ):
            res = main(["tutorial", "status"])
            self.assertEqual(res, 0)

            res = main(["story", "status"])
            self.assertEqual(res, 0)


class TestServerStoryAndTutorial(unittest.TestCase):
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

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.temp_dir.cleanup()

    def _get(self, path: str):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, data

    def _post(self, path: str, body: dict):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        payload = json.dumps(body)
        conn.request("POST", path, body=payload, headers={"Content-Type": "application/json"})
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, data

    def test_server_tutorial_endpoints(self):
        # GET /api/tutorial
        status, data = self._get("/api/tutorial")
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])
        self.assertEqual(json_data["tutorial"]["current_step_index"], 0)

        # POST /api/tutorial/skip
        status, data = self._post("/api/tutorial/skip", {})
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])

        # POST /api/tutorial/reset
        status, data = self._post("/api/tutorial/reset", {})
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])

    def test_server_story_endpoints(self):
        # GET /api/story
        status, data = self._get("/api/story")
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])
        self.assertEqual(json_data["story"]["active_act"], 1)

        # POST /api/story/choice (invalid)
        status, data = self._post("/api/story/choice", {"choice_id": "nonexistent"})
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertFalse(json_data["ok"])

        # POST /api/story/choice (valid)
        status, data = self._post("/api/story/choice", {"choice_id": "choice_vance_telemetry"})
        self.assertEqual(status, 200)
        json_data = json.loads(data.decode("utf-8"))
        self.assertTrue(json_data["ok"])


class TestStoryBranchingMechanics(unittest.TestCase):
    """Requirement-gated choices, persistent flags, endings, and legacy-save migration."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = StorageManager(self.temp_dir.name)
        self.engine = SimulationEngine(seed=42)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _travel_to(self, destination: str) -> None:
        from voidfarer.navigation import shortest_route

        path = shortest_route(self.engine.state.systems, self.engine.state.ship.current_system_id, destination)
        for target in path[1:]:
            with self.engine.lock:
                self.engine.state = self.engine.state.__class__(
                    version=self.engine.state.version,
                    galaxy_seed=self.engine.state.galaxy_seed,
                    ship=self.engine._clone_ship(fuel=60),
                    systems=self.engine.state.systems,
                    visited_systems=self.engine.state.visited_systems,
                    active_anomaly=None,
                    active_combat=None,
                    stats=self.engine.state.stats,
                )
            ok, msg = self.engine.jump(target)
            self.assertTrue(ok, msg)

    def test_story_status_reports_objectives_and_locks(self):
        status = self.engine.story_status()
        self.assertEqual(status["campaign_title"], "The Precursor Cipher")
        self.assertEqual(status["active_act"], 1)
        self.assertTrue(status["ready"])
        self.assertEqual(status["unmet_requirements"], [])
        self.assertTrue(any(c["id"] == "choice_vance_telemetry" for c in status["choices"]))
        self.assertTrue(all(not c["locked"] for c in status["choices"]))

    def test_act_iv_requires_black_hole_orbit(self):
        self.engine.make_story_choice("choice_vance_telemetry")
        self._travel_to("sirius")
        self.engine.make_story_choice("choice_colony_power")
        self._travel_to("vega")
        self.engine.make_story_choice("choice_safeguard_lock")
        self._travel_to("cygnus_x1")

        status = self.engine.story_status()
        self.assertFalse(status["ready"])
        self.assertTrue(any("orbit" in r.lower() for r in status["unmet_requirements"]))

        ok, msg = self.engine.make_story_choice("choice_first_dive")
        self.assertFalse(ok)
        self.assertIn("Objectives unmet", msg)

        ok, msg = self.engine.orbit("cygnus_x1_black_hole")
        self.assertTrue(ok)
        self.assertTrue(self.engine.story_status()["ready"])

    def test_locked_choices_report_branch_resolvable_reasons(self):
        # Coalition path: neither the oath flag nor the leaked-intel flag is set
        self.engine.make_story_choice("choice_vance_telemetry")
        self._travel_to("sirius")
        self.engine.make_story_choice("choice_colony_power")
        self._travel_to("vega")
        self.engine.make_story_choice("choice_safeguard_lock")
        self._travel_to("cygnus_x1")
        self.engine.orbit("cygnus_x1_black_hole")
        self.engine.make_story_choice("choice_horizon_witness")
        self._travel_to("rift_station")

        status = self.engine.story_status()
        by_id = {c["id"]: c for c in status["choices"]}
        self.assertTrue(by_id["choice_claim_title"]["locked"])
        self.assertIn("Voidfarer's Oath", by_id["choice_claim_title"]["lock_reason"])
        self.assertTrue(by_id["choice_sell_echoes"]["locked"])
        self.assertIn("Act I", by_id["choice_sell_echoes"]["lock_reason"])

        ok, msg = self.engine.make_story_choice("choice_claim_title")
        self.assertFalse(ok)
        self.assertIn("locked", msg)

    def test_persistent_flags_drive_distinct_endings(self):
        # Oath path ends as First VoidFarer
        self.engine.make_story_choice("choice_cipher_leak")
        self._travel_to("sirius")
        self.engine.make_story_choice("choice_salvage_core")
        self._travel_to("vega")
        self.engine.make_story_choice("choice_unleash_gateways")
        self._travel_to("cygnus_x1")
        self.engine.orbit("cygnus_x1_black_hole")
        self.engine.make_story_choice("choice_first_dive")
        self._travel_to("rift_station")

        ok, msg = self.engine.make_story_choice("choice_sell_echoes")
        self.assertTrue(ok, msg)
        story = self.engine.state.ship.story
        self.assertTrue(story.completed)
        self.assertEqual(story.ending_id, "ending_shadow_broker")
        self.assertEqual(story.flags.get("echoes_sold"), True)

    def test_follow_up_transmissions_persist(self):
        self.engine.make_story_choice("choice_cipher_leak")
        story = self.engine.state.ship.story
        speakers = [(t.speaker, t.message) for t in story.transmission_log]
        self.assertTrue(any(speaker == "Cipher" and "profitable exchange" in message for speaker, message in speakers))

    def test_resolve_story_ending_variants(self):
        def story_with_flags(flags):
            return StoryState(
                current_chapter_index=5,
                chapters=CAMPAIGN_CHAPTERS,
                transmission_log=(),
                completed=True,
                flags=flags,
            )

        self.assertEqual(resolve_story_ending(story_with_flags({"echoes_sold": True})), "ending_shadow_broker")
        self.assertEqual(resolve_story_ending(story_with_flags({"title_claimed": True})), "ending_first_voidfarer")
        self.assertEqual(resolve_story_ending(story_with_flags({"echoes_archived": True})), "ending_sentinel")
        self.assertEqual(resolve_story_ending(story_with_flags({})), "ending_sentinel")

    def test_chapter_flag_gating_skips_ineligible_chapters(self):
        def chapter(idx, title, requirements=None):
            return StoryChapter(
                chapter_index=idx,
                title=title,
                target_system_id=None,
                objective="",
                transmission=StoryTransmission("A", "a", "c", "m"),
                choices=(StoryChoice(id=f"c_{idx}", text="Proceed", faction_alignment="independent"),),
                requirements=requirements,
            )

        custom = StoryState(
            current_chapter_index=0,
            chapters=(
                chapter(0, "Gate"),
                chapter(1, "Sealed Branch", StoryRequirements(required_flags=("never_earned",))),
                chapter(2, "Open Branch"),
            ),
            transmission_log=(),
        )
        with self.engine.lock:
            self.engine.state = self.engine._clone_state(ship=self.engine._clone_ship(story=custom))

        ok, msg = self.engine.make_story_choice("c_0")
        self.assertTrue(ok)
        story = self.engine.state.ship.story
        self.assertTrue(story.chapters[1].skipped)
        self.assertEqual(story.current_chapter_index, 2)
        self.assertEqual(story.current_chapter_id, "act3_eternity_gate")

    def test_migrate_story_state_variants(self):
        # Completed legacy campaign reopens at the first new act
        legacy = StoryState(
            current_chapter_index=3,
            chapters=CAMPAIGN_CHAPTERS[:3],
            transmission_log=(CAMPAIGN_CHAPTERS[0].transmission,),
            reputation={"coalition": 25},
            completed=True,
        )
        migrated = migrate_story_state(legacy)
        self.assertEqual(len(migrated.chapters), 5)
        self.assertFalse(migrated.completed)
        self.assertEqual(migrated.current_chapter_index, 3)
        self.assertTrue(any("Cygnus gate" in t.message for t in migrated.transmission_log))
        self.assertEqual(migrated.reputation, {"coalition": 25})

        # Mid-campaign legacy save resumes where it was, without the awakening transmission
        mid = StoryState(
            current_chapter_index=1,
            chapters=CAMPAIGN_CHAPTERS[:3],
            transmission_log=(CAMPAIGN_CHAPTERS[0].transmission,),
        )
        migrated_mid = migrate_story_state(mid)
        self.assertEqual(len(migrated_mid.chapters), 5)
        self.assertEqual(migrated_mid.current_chapter_index, 1)
        self.assertFalse(migrated_mid.completed)
        self.assertEqual(len(migrated_mid.transmission_log), 1)

        # Already-current campaign passes through untouched
        current = StoryState(current_chapter_index=5, chapters=CAMPAIGN_CHAPTERS, completed=True)
        self.assertIs(migrate_story_state(current), current)

    def test_engine_load_state_migrates_legacy_campaign(self):
        legacy_story = StoryState(
            current_chapter_index=3,
            chapters=CAMPAIGN_CHAPTERS[:3],
            transmission_log=(CAMPAIGN_CHAPTERS[0].transmission,),
            completed=True,
        )
        with self.engine.lock:
            legacy_state = self.engine._clone_state(
                ship=self.engine._clone_ship(story=legacy_story)
            )
        ok, msg = self.engine.load_state(legacy_state)
        self.assertTrue(ok)
        story = self.engine.state.ship.story
        self.assertEqual(len(story.chapters), 5)
        self.assertFalse(story.completed)
        self.assertEqual(story.current_chapter_index, 3)
        self.assertEqual(story.current_chapter_id, "act4_hollow_between")

        # Story status exposes the reopened objective
        status = self.engine.story_status()
        self.assertEqual(status["chapter_id"], "act4_hollow_between")

    def test_serialization_roundtrip_preserves_flags_and_ending(self):
        self.engine.make_story_choice("choice_cipher_leak")
        story = self.engine.state.ship.story
        self.assertEqual(story.flags.get("intel_leaked_syndicate"), True)

        restored = ShipState.from_dict(self.engine.state.ship.to_dict())
        self.assertEqual(restored.story.flags, story.flags)
        self.assertIsNone(restored.story.ending_id)

        # Requirements and follow-ups survive the roundtrip
        act5 = [c for c in restored.story.chapters if c.id == "act5_first_voidfarers"][0]
        claim = [c for c in act5.choices if c.id == "choice_claim_title"][0]
        self.assertEqual(claim.requirements.required_flags, ("voidfarer_oath",))
        act1 = [c for c in restored.story.chapters if c.id == "act1_ghost_signal"][0]
        leak = [c for c in act1.choices if c.id == "choice_cipher_leak"][0]
        self.assertIsNotNone(leak.follow_up)
        self.assertIn("skipped", act5.to_dict())


if __name__ == "__main__":
    unittest.main()
