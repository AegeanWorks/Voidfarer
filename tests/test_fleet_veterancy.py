"""Fleet veterancy: rank thresholds, combat scaling and drydock training."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import (
    FLEET_MAX_EXPERIENCE,
    build_fleet_ship,
    fleet_damage,
    fleet_evasion_bonus,
    fleet_rank,
    fleet_training_cost,
    fleet_victory_experience,
)


class FleetRankTest(unittest.TestCase):
    def test_rank_thresholds_and_progress(self):
        self.assertEqual(fleet_rank(0)["name"], "Green")
        self.assertEqual(fleet_rank(24)["name"], "Green")
        self.assertEqual(fleet_rank(25)["name"], "Regular")
        self.assertEqual(fleet_rank(75)["name"], "Veteran")
        self.assertEqual(fleet_rank(150)["name"], "Elite")
        self.assertEqual(fleet_rank(300)["name"], "Ace")
        self.assertEqual(fleet_rank(999)["name"], "Ace")
        regular = fleet_rank(50)
        self.assertEqual(regular["name"], "Regular")
        self.assertEqual(regular["next_rank"], "Veteran")
        self.assertAlmostEqual(regular["progress"], 0.5)
        self.assertEqual(fleet_rank(FLEET_MAX_EXPERIENCE)["progress"], 1.0)

    def test_ranks_raise_damage_and_screen_evasion(self):
        green = build_fleet_ship("corvette", "sol", 0)
        ace = build_fleet_ship("corvette", "sol", 0)
        ace = replace(ace, experience=FLEET_MAX_EXPERIENCE)
        self.assertGreater(fleet_damage((ace,)), fleet_damage((green,)))
        self.assertGreater(
            fleet_evasion_bonus((ace,)), fleet_evasion_bonus((green,))
        )

    def test_training_cost_and_victory_experience_scale(self):
        self.assertEqual(fleet_training_cost(0), 200)
        self.assertEqual(fleet_training_cost(100), 700)
        self.assertEqual(fleet_victory_experience(0), 3)
        self.assertEqual(fleet_victory_experience(80), 5)
        self.assertEqual(fleet_victory_experience(400), 9)


class FleetTrainingTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.allow_decision_events = False
        ship = build_fleet_ship("corvette", "sol", 0)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=2000,
                orbiting_body_id="sol_body_1",
                fleet_ships=(ship,),
            )
        )

    def test_training_buys_xp_and_promotes(self):
        ship_id = self.engine.state.ship.fleet_ships[0].id
        ok, message = self.engine.train_fleet_ship(ship_id)
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.ship.fleet_ships[0].experience, 10)
        self.assertEqual(self.engine.state.ship.credits, 1800)
        self.assertIn("+10 XP", message)

        ok, _ = self.engine.train_fleet_ship(ship_id)
        self.assertTrue(ok)
        ok, message = self.engine.train_fleet_ship(ship_id)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.fleet_ships[0].experience, 30)
        self.assertEqual(fleet_rank(30)["name"], "Regular")
        self.assertIn("Promoted Green -> Regular", message)

    def test_training_requires_a_dock_and_a_live_ship(self):
        ship_id = self.engine.state.ship.fleet_ships[0].id
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id=None)
        )
        ok, message = self.engine.train_fleet_ship(ship_id)
        self.assertFalse(ok)
        self.assertIn("dock", message.lower())

        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(orbiting_body_id="sol_body_1")
        )
        ok, message = self.engine.train_fleet_ship("missing")
        self.assertFalse(ok)
        self.assertIn("unknown", message.lower())

    def test_training_refuses_a_destroyed_or_maxed_escort(self):
        ship_id = self.engine.state.ship.fleet_ships[0].id
        broken = replace(self.engine.state.ship.fleet_ships[0], hull=0)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fleet_ships=(broken,))
        )
        ok, message = self.engine.train_fleet_ship(ship_id)
        self.assertFalse(ok)
        self.assertIn("destroyed", message.lower())

        maxed = replace(broken, hull=90, experience=FLEET_MAX_EXPERIENCE)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(fleet_ships=(maxed,))
        )
        ok, message = self.engine.train_fleet_ship(ship_id)
        self.assertFalse(ok)
        self.assertIn("ace", message.lower())

    def test_training_refuses_when_credits_are_short(self):
        ship_id = self.engine.state.ship.fleet_ships[0].id
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=10)
        )
        ok, message = self.engine.train_fleet_ship(ship_id)
        self.assertFalse(ok)
        self.assertIn("credits", message.lower())

    def test_report_exposes_rank_fields(self):
        report = self.engine.get_fleet_manager_report()
        ship = report["ships"][0]
        self.assertEqual(ship["rank"], "Green")
        self.assertEqual(ship["experience_max"], FLEET_MAX_EXPERIENCE)
        self.assertEqual(ship["training_cost"], 200)
        self.assertEqual(ship["training_gain"], 10)


if __name__ == "__main__":
    unittest.main()
