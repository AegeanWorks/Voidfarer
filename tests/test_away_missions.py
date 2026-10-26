"""Away-team expeditions: catalog, deterministic outcomes, injuries, XP, parity and saves."""

import contextlib
import io
import json
from dataclasses import replace
import tempfile
import threading
import unittest
from pathlib import Path

from voidfarer.away import (
    AWAY_MISSION_MAP,
    AWAY_MISSION_TYPES,
    auto_team,
    mission_risk,
    resolve_away_mission,
    site_key,
)
from voidfarer.cli import main
from voidfarer.crew import (
    award_crew_xp,
    calculate_crew_bonuses,
    recover_crew_injuries,
)
from voidfarer.engine import SimulationEngine
from voidfarer.models import AwayMission, CrewMember, ShipState
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler
from voidfarer.storage import StorageManager


def _crew(member_id="c1", role="scientist", skill=4, specialty="science", injury=0):
    return CrewMember(
        id=member_id,
        name=f"Crew {member_id}",
        role=role,
        skill=skill,
        morale=80.0,
        wage=30,
        portrait="crew_01",
        specialty=specialty,
        injury_ticks=injury,
    )


class AwayCatalogTest(unittest.TestCase):
    def test_catalog_has_multiple_distinct_missions(self):
        self.assertGreaterEqual(len(AWAY_MISSION_TYPES), 5)
        self.assertEqual(len(AWAY_MISSION_MAP), len(AWAY_MISSION_TYPES))
        for mission_type in AWAY_MISSION_TYPES:
            self.assertGreater(mission_type.duration_ticks, 0)
            self.assertGreaterEqual(mission_type.team_size, 1)
            self.assertGreaterEqual(mission_type.base_risk, 0)

    def test_auto_team_prefers_matching_specialty_and_excludes_assigned(self):
        mission_type = AWAY_MISSION_MAP["geological_survey"]
        team = auto_team(
            mission_type,
            (
                _crew("pilot", role="pilot", skill=6, specialty="evasion"),
                _crew("science", role="scientist", skill=3, specialty="science"),
                _crew("busy", role="scientist", skill=10, specialty="science"),
            ),
            assigned_ids={"busy"},
        )
        self.assertEqual([member.id for member in team], ["science"])

    def test_risk_falls_with_specialist_skill_and_rises_with_hazards(self):
        mission_type = AWAY_MISSION_MAP["distress_sweep"]
        body = self._body()
        weak = (_crew("a", skill=1, specialty="pilot"),) * 3
        strong = tuple(
            _crew(f"s{i}", role="marine", skill=8, specialty="combat") for i in range(3)
        )
        self.assertLess(mission_risk(mission_type, body, strong), mission_risk(mission_type, body, weak))
        hazardous = replace(body, hazards=("pirate_activity", "tidal_shear"))
        self.assertGreater(mission_risk(mission_type, hazardous, strong), mission_risk(mission_type, body, strong))

    def test_resolution_is_deterministic_and_reports_outcome(self):
        mission_type = AWAY_MISSION_MAP["geological_survey"]
        body = self._body()
        mission = AwayMission(
            id="away_test_1",
            mission_type=mission_type.id,
            system_id="sol",
            body_id=body.id,
            body_name=body.name,
            crew_ids=("c1",),
            started_tick=10,
            duration_ticks=mission_type.duration_ticks,
            risk=5,
        )
        first = resolve_away_mission(mission, mission_type, body, (_crew("c1"),), galaxy_seed=42)
        second = resolve_away_mission(mission, mission_type, body, (_crew("c1"),), galaxy_seed=42)
        self.assertEqual(first, second)
        self.assertIn("success", first)
        self.assertIn("log", first)
        self.assertGreaterEqual(first["research"], 0)

    def _body(self):
        engine = SimulationEngine(seed=42)
        return engine.orbiting_body or next(iter(engine.current_system.bodies))


class AwayEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def _launch_any(self):
        report = self.engine.get_away_report()
        self.assertTrue(report["available"])
        mission_type = report["available"][0]
        ok, msg = self.engine.launch_away_mission(mission_type["id"])
        self.assertTrue(ok, msg)
        return self.engine.state.ship.away_missions[0]

    def test_report_lists_body_missions_and_crew(self):
        report = self.engine.get_away_report()
        self.assertIsNotNone(report["body"])
        self.assertTrue(report["available"])
        self.assertTrue(report["crew"])
        self.assertGreaterEqual(report["max_active"], 1)
        for mission in report["available"]:
            self.assertIn("risk", mission)
            self.assertIn("team", mission)
            self.assertIn("rewards", mission)

    def test_launch_assigns_an_uninjured_team_and_persists(self):
        mission = self._launch_any()
        self.assertEqual(len(mission.crew_ids), AWAY_MISSION_MAP[mission.mission_type].team_size)
        assigned = {member.id for member in self.engine.state.ship.crew if member.id in mission.crew_ids}
        self.assertEqual(len(assigned), len(mission.crew_ids))
        restored = ShipState.from_dict(self.engine.state.ship.to_dict())
        self.assertEqual(restored.away_missions[0].id, mission.id)
        snapshot = self.engine.get_status_snapshot(include_static=False)
        self.assertTrue(snapshot["away_report"]["active"])

    def test_launch_rejects_injured_team_and_combat(self):
        ship = self.engine._clone_ship(
            crew=tuple(replace(member, injury_ticks=5) for member in self.engine.state.ship.crew)
        )
        self.engine.state = self.engine._clone_state(ship=ship)
        mission_type = self.engine.get_away_report()["available"][0]["id"]
        ok, msg = self.engine.launch_away_mission(mission_type)
        self.assertFalse(ok)
        self.assertIn("injur", msg.lower())

    def test_tick_resolves_success_and_awards_cargo_or_credits(self):
        mission = self._launch_any()
        forced = replace(mission, risk=0, duration_ticks=1)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(away_missions=(forced,))
        )
        credits_before = self.engine.state.ship.credits
        research_before = self.engine.state.research.points
        self.engine.tick(1)
        self.assertEqual(self.engine.state.ship.away_missions, ())
        self.assertEqual(self.engine.state.stats.get("away_missions"), 1)
        self.assertEqual(self.engine.state.stats.get("away_successes"), 1)
        self.assertGreater(
            self.engine.state.ship.credits + self.engine.state.research.points,
            credits_before + research_before,
        )
        self.assertTrue(any("AWAY TEAM" in entry for entry in self.engine.state.ship.flight_log))
        site_marker = site_key(forced.mission_type, forced.body_id)
        self.assertIn(site_marker, self.engine.state.ship.away_completed)
        blocked = next(
            item for item in self.engine.get_away_report()["available"]
            if item["id"] == forced.mission_type
        )
        self.assertTrue(blocked["worked"])
        self.assertFalse(blocked["available"])
        ok, msg = self.engine.launch_away_mission(forced.mission_type)
        self.assertFalse(ok)
        self.assertIn("already worked", msg)

    def test_tick_failure_injures_crew_and_blocks_their_bonus(self):
        mission = self._launch_any()
        forced = replace(mission, risk=100, duration_ticks=1)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(away_missions=(forced,))
        )
        self.engine.tick(1)
        self.assertEqual(self.engine.state.stats.get("away_failures"), 1)
        injured = [member for member in self.engine.state.ship.crew if member.injury_ticks > 0]
        self.assertTrue(injured, "a failed expedition must injure at least one crew member")
        bonuses = calculate_crew_bonuses(self.engine.state.ship.crew)
        uninjured = tuple(member for member in self.engine.state.ship.crew if member.injury_ticks == 0)
        self.assertLessEqual(bonuses["research_per_tick"], calculate_crew_bonuses(uninjured)["research_per_tick"] + 0.001)

    def test_recall_returns_crew_without_reward(self):
        mission = self._launch_any()
        stats_before = dict(self.engine.state.stats)
        ok, msg = self.engine.recall_away_mission(mission.id)
        self.assertTrue(ok, msg)
        self.assertEqual(self.engine.state.ship.away_missions, ())
        self.assertEqual(self.engine.state.stats, stats_before)

    def test_injuries_recover_and_medic_speeds_it(self):
        crew = (_crew("c1", injury=6),)
        recovered, logs = recover_crew_injuries(crew, 2, medic_aboard=False)
        self.assertEqual(recovered[0].injury_ticks, 4)
        self.assertEqual(logs, [])
        recovered, logs = recover_crew_injuries(crew, 2, medic_aboard=True)
        self.assertEqual(recovered[0].injury_ticks, 2)
        self.assertEqual(logs, [])

    def test_crew_xp_promotes_skill_and_keeps_remainder(self):
        member, promoted = award_crew_xp(_crew("c1", skill=2, specialty="science"), 85)
        self.assertTrue(promoted)
        self.assertEqual(member.skill, 3)
        self.assertEqual(member.xp, 5)

    def test_old_saves_default_new_fields(self):
        crew = CrewMember.from_dict({"id": "old", "name": "Old", "role": "pilot"})
        self.assertEqual(crew.xp, 0)
        self.assertEqual(crew.injury_ticks, 0)
        ship_data = self.engine.state.ship.to_dict()
        ship_data.pop("away_missions", None)
        ship_data.pop("away_completed", None)
        restored = ShipState.from_dict(ship_data)
        self.assertEqual(restored.away_missions, ())
        self.assertEqual(restored.away_completed, ())

    def test_mission_round_trip(self):
        mission = AwayMission(
            id="away_1",
            mission_type="salvage_sweep",
            system_id="sol",
            body_id="sol_body_1",
            body_name="Sol A",
            crew_ids=("c1", "c2"),
            started_tick=3,
            duration_ticks=8,
            risk=21,
        )
        self.assertEqual(AwayMission.from_dict(mission.to_dict()), mission)


class AwayParityTest(unittest.TestCase):
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
        VoidFarerHandler.storage = StorageManager(self.temp_dir.name)

    def _get(self, path):
        import http.client

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("GET", path)
        response = conn.getresponse()
        body = response.read()
        conn.close()
        return response.status, json.loads(body.decode("utf-8"))

    def _post(self, path, payload):
        import http.client

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        conn.request("POST", path, body=json.dumps(payload), headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        body = response.read()
        conn.close()
        return response.status, json.loads(body.decode("utf-8"))

    def test_rest_report_and_launch(self):
        status, data = self._get("/api/away")
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        mission_type = data["away"]["available"][0]["id"]
        status, data = self._post("/api/away/launch", {"mission_type": mission_type})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"], data.get("message"))
        self.assertTrue(data["state"]["away_report"]["active"])
        mission_id = data["state"]["away_report"]["active"][0]["id"]
        status, data = self._post("/api/away/recall", {"mission_id": mission_id})
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"], data.get("message"))
        self.assertFalse(data["state"]["away_report"]["active"])

    def test_cli_lists_away_teams(self):
        with tempfile.TemporaryDirectory() as temp:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = main(["--save-path", temp, "away"])
            self.assertEqual(code, 0)
            self.assertIn("AWAY TEAM", output.getvalue().upper())


if __name__ == "__main__":
    unittest.main()
