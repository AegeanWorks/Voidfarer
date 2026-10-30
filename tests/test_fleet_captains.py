"""Escort captains: assignment rules, role bonuses and persistence."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import (
    build_fleet_ship,
    fleet_damage,
    fleet_evasion_bonus,
    fleet_upkeep,
)
from voidfarer.models import FleetShip, GameState, Outpost


class FleetCaptainMathTest(unittest.TestCase):
    def test_captain_roles_add_damage_evasion_or_upkeep_discount(self):
        base = build_fleet_ship("frigate", "sol", 0)
        marine = replace(base, captain_role="marine")
        pilot = replace(base, captain_role="pilot")
        quartermaster = replace(base, captain_role="quartermaster")
        self.assertGreater(fleet_damage((marine,)), fleet_damage((base,)))
        self.assertGreater(fleet_evasion_bonus((pilot,)), fleet_evasion_bonus((base,)))
        self.assertLess(fleet_upkeep((quartermaster,)), fleet_upkeep((base,)))

    def test_legacy_ship_defaults_to_no_captain(self):
        ship = build_fleet_ship("corvette", "sol", 0)
        payload = ship.to_dict()
        payload.pop("captain_id", None)
        payload.pop("captain_role", None)
        restored = FleetShip.from_dict(payload)
        self.assertEqual(restored.captain_id, "")
        self.assertEqual(restored.captain_role, "")


class FleetCaptainEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.ship = build_fleet_ship("corvette", "sol", 0)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fleet_ships=(self.ship,))
        )

    def test_assign_and_recall_a_captain(self):
        crew = self.engine.state.ship.crew[0]
        ok, message = self.engine.assign_fleet_captain(self.ship.id, crew.id)
        self.assertTrue(ok, message)
        updated = self.engine.state.ship.fleet_ships[0]
        self.assertEqual(updated.captain_id, crew.id)
        self.assertEqual(updated.captain_role, crew.role)
        self.assertIn("ESCORT CAPTAIN", message)
        report = self.engine.get_fleet_manager_report()["ships"][0]
        self.assertEqual(report["captain_name"], crew.name)

        ok, message = self.engine.recall_fleet_captain(self.ship.id)
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.ship.fleet_ships[0].captain_id, "")

    def test_duplicate_and_destroyed_captains_are_refused(self):
        crew = self.engine.state.ship.crew[0]
        self.engine.assign_fleet_captain(self.ship.id, crew.id)
        ok, message = self.engine.assign_fleet_captain(self.ship.id, crew.id)
        self.assertFalse(ok)
        self.assertIn("already has", message.lower())

        wreck = replace(self.ship, hull=0, status="destroyed")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fleet_ships=(wreck,))
        )
        ok, message = self.engine.assign_fleet_captain(self.ship.id, crew.id)
        self.assertFalse(ok)
        self.assertIn("destroyed", message.lower())

    def test_outpost_and_away_crew_cannot_command(self):
        crew = self.engine.state.ship.crew[0]
        outpost = Outpost(
            id="captain_outpost",
            name="Captain Test Outpost",
            system_id="sol",
            body_id="sol_body_1",
            outpost_type="mining",
            assigned_crew=(crew.id,),
        )
        self.engine.state = self.engine._clone_state(outposts=(outpost,))
        ok, message = self.engine.assign_fleet_captain(self.ship.id, crew.id)
        self.assertFalse(ok)
        self.assertIn("outpost", message.lower())

    def test_captain_is_excluded_from_ship_bonuses(self):
        crew = self.engine.state.ship.crew[0]
        before = self.engine._crew_bonuses()
        self.engine.assign_fleet_captain(self.ship.id, crew.id)
        after = self.engine._crew_bonuses()
        self.assertNotEqual(before, after)
        report = self.engine.get_crew_report()
        assigned = next(m for m in report["crew"] if m["id"] == crew.id)
        self.assertEqual(assigned["ship_id"], self.ship.id)

    def test_captain_state_round_trips(self):
        crew = self.engine.state.ship.crew[0]
        self.engine.assign_fleet_captain(self.ship.id, crew.id)
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.ship.fleet_ships[0].captain_id, crew.id)
        self.assertEqual(restored.ship.fleet_ships[0].captain_role, crew.role)


if __name__ == "__main__":
    unittest.main()
