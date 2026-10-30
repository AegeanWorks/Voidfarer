"""Crew service medals: thresholds, morale, battle credit and persistence."""

from dataclasses import replace
import unittest

from voidfarer.codex import metric_value
from voidfarer.crew import (
    COMBAT_VETERAN_MEDAL,
    DEEP_EXPLORER_MEDAL,
    award_service_medals,
)
from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship
from voidfarer.models import CombatEncounter, CrewMember, GameState


class CrewMedalThresholdTest(unittest.TestCase):
    def test_battle_medal_is_awarded_once_and_lifts_morale(self):
        member = CrewMember(
            id="medal_marine", name="Medal Marine", role="marine",
            skill=4, morale=70.0, battles=3,
        )
        updated, earned = award_service_medals(member)
        self.assertEqual(earned, (COMBAT_VETERAN_MEDAL,))
        self.assertIn(COMBAT_VETERAN_MEDAL, updated.medals)
        self.assertEqual(updated.morale, 75.0)
        again, earned_again = award_service_medals(updated)
        self.assertEqual(earned_again, ())
        self.assertEqual(again.medals, updated.medals)

    def test_away_medal_is_awarded_at_five_missions(self):
        member = CrewMember(
            id="medal_scientist", name="Medal Scientist", role="scientist",
            skill=4, morale=80.0, away_missions=5,
        )
        updated, earned = award_service_medals(member)
        self.assertEqual(earned, (DEEP_EXPLORER_MEDAL,))
        self.assertIn(DEEP_EXPLORER_MEDAL, updated.medals)

    def test_legacy_crew_defaults_to_no_medals(self):
        member = CrewMember(id="legacy", name="Legacy", role="pilot")
        payload = member.to_dict()
        payload.pop("medals", None)
        payload.pop("battles", None)
        payload.pop("away_missions", None)
        restored = CrewMember.from_dict(payload)
        self.assertEqual(restored.medals, ())
        self.assertEqual(restored.battles, 0)
        self.assertEqual(restored.away_missions, 0)


class CrewMedalEngineTest(unittest.TestCase):
    def _engine(self):
        engine = SimulationEngine(seed=42)
        captain = CrewMember(
            id="captain_medal", name="Captain Medal", role="engineer",
            skill=5, morale=80.0, specialty="engineering", status="active",
        )
        escort = build_fleet_ship("corvette", "sol", 0)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                crew=(captain,),
                fleet_ships=(escort,),
                credits=5000,
            )
        )
        self.assertTrue(
            engine.assign_fleet_captain(escort.id, captain.id)[0]
        )
        return engine

    def _victory(self, engine):
        engine.state = engine._clone_state(
            active_combat=CombatEncounter(
                id="medal_victory",
                enemy_name="Medal Target",
                enemy_class="Corvette",
                enemy_hull=1,
                enemy_max_hull=1,
                enemy_damage=0,
                bounty_credits=0,
            )
        )
        engine.rng.random = lambda: 0.0
        ok, message = engine.combat_action("fire_lasers")
        self.assertTrue(ok, message)

    def test_three_victories_award_the_combat_medal(self):
        engine = self._engine()
        for _ in range(3):
            self._victory(engine)
        captain = next(
            member for member in engine.state.ship.crew
            if member.id == "captain_medal"
        )
        self.assertEqual(captain.battles, 3)
        self.assertIn(COMBAT_VETERAN_MEDAL, captain.medals)
        restored = GameState.from_dict(engine.state.to_dict())
        restored_captain = next(
            member for member in restored.ship.crew
            if member.id == "captain_medal"
        )
        self.assertIn(COMBAT_VETERAN_MEDAL, restored_captain.medals)

    def test_away_mission_awards_the_explorer_medal(self):
        engine = SimulationEngine(seed=42)
        crew = tuple(
            replace(member, away_missions=4)
            for member in engine.state.ship.crew
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(crew=crew)
        )
        mission_type = engine.get_away_report()["available"][0]["id"]
        ok, message = engine.launch_away_mission(mission_type)
        self.assertTrue(ok, message)
        mission = engine.state.ship.away_missions[0]
        forced = replace(mission, risk=0, duration_ticks=1)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(away_missions=(forced,))
        )
        engine.tick(1)
        for crew_id in forced.crew_ids:
            member = next(
                member for member in engine.state.ship.crew
                if member.id == crew_id
            )
            self.assertGreaterEqual(member.away_missions, 5)
            self.assertIn(DEEP_EXPLORER_MEDAL, member.medals)

    def test_codex_counts_all_crew_medals(self):
        engine = self._engine()
        crew = tuple(
            replace(member, medals=(COMBAT_VETERAN_MEDAL, DEEP_EXPLORER_MEDAL))
            if member.id == "captain_medal" else member
            for member in engine.state.ship.crew
        )
        state = engine._clone_state(ship=engine._clone_ship(crew=crew))
        self.assertEqual(metric_value(state, "crew_medals"), 2)


if __name__ == "__main__":
    unittest.main()
