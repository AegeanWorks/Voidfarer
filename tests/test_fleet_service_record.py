"""Fleet service records: battles, kills, patrol bounties and training counts."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship, resolve_patrol_sweep
from voidfarer.models import CombatEncounter, FleetShip, GameState


class FleetServiceRecordTest(unittest.TestCase):
    def test_legacy_ship_defaults_to_zero_service(self):
        ship = build_fleet_ship("corvette", "sol", 0)
        payload = ship.to_dict()
        for key in (
            "battles",
            "kills",
            "patrol_credits",
            "patrol_contacts",
            "training_sessions",
        ):
            payload.pop(key, None)
        restored = FleetShip.from_dict(payload)
        self.assertEqual(restored.battles, 0)
        self.assertEqual(restored.kills, 0)
        self.assertEqual(restored.patrol_credits, 0)
        self.assertEqual(restored.patrol_contacts, 0)
        self.assertEqual(restored.training_sessions, 0)

    def test_training_increments_the_session_count(self):
        engine = SimulationEngine(seed=42)
        ship = build_fleet_ship("corvette", "sol", 0)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                credits=2000,
                orbiting_body_id="sol_body_1",
                fleet_ships=(ship,),
            )
        )
        ok, message = engine.train_fleet_ship(ship.id)
        self.assertTrue(ok, message)
        self.assertEqual(engine.state.ship.fleet_ships[0].training_sessions, 1)

    def test_patrol_contact_records_bounty_and_battle(self):
        engine = SimulationEngine(seed=42)
        engine.allow_decision_events = False
        system = engine.state.systems["cygnus_x1"]
        ship = build_fleet_ship("corvette", "cygnus_x1", 0)
        contact_tick = None
        for tick in range(6, 100, 6):
            sweep = resolve_patrol_sweep(ship, system, tick, engine.state.galaxy_seed)
            if sweep["contacted"]:
                contact_tick = tick
                break
        self.assertIsNotNone(contact_tick)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(
                credits=1000,
                current_system_id="sol",
                fleet_ships=(ship,),
            ),
            time=replace(engine.state.time, tick=contact_tick - 1),
        )
        engine.tick(1)
        updated = engine.state.ship.fleet_ships[0]
        self.assertEqual(updated.patrol_contacts, 1)
        self.assertGreater(updated.patrol_credits, 0)
        self.assertEqual(updated.battles, 1)

    def test_combat_victory_counts_battle_and_kill_for_local_survivor(self):
        engine = SimulationEngine(seed=42)
        ship = build_fleet_ship("corvette", "sol", 0)
        combat = CombatEncounter(
            id="service_victory",
            enemy_name="Target",
            enemy_class="Scout",
            enemy_hull=1,
            enemy_max_hull=1,
            enemy_damage=0,
            bounty_credits=10,
            enemy_shield=0,
            enemy_max_shield=0,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(fleet_ships=(ship,)),
            active_combat=combat,
        )
        engine.rng.random = lambda: 0.5
        ok, message = engine.combat_action("fire_lasers")
        self.assertTrue(ok, message)
        updated = engine.state.ship.fleet_ships[0]
        self.assertEqual(updated.battles, 1)
        self.assertEqual(updated.kills, 1)

    def test_save_round_trip_keeps_service(self):
        engine = SimulationEngine(seed=42)
        ship = replace(
            build_fleet_ship("corvette", "sol", 0),
            battles=3,
            kills=2,
            patrol_credits=140,
            patrol_contacts=1,
            training_sessions=4,
        )
        engine.state = engine._clone_state(ship=engine._clone_ship(fleet_ships=(ship,)))
        restored = GameState.from_dict(engine.state.to_dict())
        self.assertEqual(restored.ship.fleet_ships[0].battles, 3)
        self.assertEqual(restored.ship.fleet_ships[0].kills, 2)
        self.assertEqual(restored.ship.fleet_ships[0].patrol_credits, 140)
        self.assertEqual(restored.ship.fleet_ships[0].patrol_contacts, 1)
        self.assertEqual(restored.ship.fleet_ships[0].training_sessions, 4)


if __name__ == "__main__":
    unittest.main()
