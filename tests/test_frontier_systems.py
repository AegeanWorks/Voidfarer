"""Coverage for frontier systems: AI captains, depots, messages, landing, and fleets."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.frontier import generate_ai_captains, generate_depots, simulate_ai_trade
from voidfarer.galaxy import GalaxyGenerator
from voidfarer.models import AICaptain, Depot, FleetDrone, GameState, Moon, QuantumMessage
from voidfarer.retention import PILOT_TALENTS


class FrontierBootstrapTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_initial_state_has_captains_depots_and_messages(self):
        self.assertEqual(len(self.engine.state.ai_captains), 5)
        self.assertEqual(len(self.engine.state.depots), len(self.engine.state.systems))
        self.assertGreaterEqual(len(self.engine.state.messages), 2)

    def test_save_round_trip_preserves_frontier_state(self):
        state = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(len(state.ai_captains), len(self.engine.state.ai_captains))
        self.assertEqual(len(state.depots), len(self.engine.state.depots))
        self.assertEqual(len(state.messages), len(self.engine.state.messages))

    def test_quest_panel_contains_story_and_contracts(self):
        quests = self.engine.get_quests()
        self.assertTrue(any(q["kind"] == "story" for q in quests))
        self.assertTrue(any(q["kind"] == "contract" for q in quests))


class AICaptainTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_ai_trade_moves_captains_and_changes_stockpiles(self):
        before = {c.id: c.system_id for c in self.engine.state.ai_captains}
        before_stock = sum(
            sum(m.stockpiles.values()) for m in self.engine.state.economy.markets.values()
        )
        self.engine.tick(4)
        after = {c.id: c.system_id for c in self.engine.state.ai_captains}
        after_stock = sum(
            sum(m.stockpiles.values()) for m in self.engine.state.economy.markets.values()
        )
        self.assertNotEqual(before, after)
        self.assertNotEqual(before_stock, after_stock)

    def test_hail_increases_trust(self):
        captain = self.engine.state.ai_captains[0]
        ok, msg = self.engine.interact_ai(captain.id, "hail")
        self.assertTrue(ok)
        updated = next(c for c in self.engine.state.ai_captains if c.id == captain.id)
        self.assertGreater(updated.trust, captain.trust)

    def test_alliance_requires_trust_then_adds_ally(self):
        captain = self.engine.state.ai_captains[0]
        ok, _ = self.engine.interact_ai(captain.id, "ally")
        self.assertFalse(ok)

        trusted = AICaptain.from_dict({**captain.to_dict(), "trust": 60})
        self.engine.state = self.engine._clone_state(
            ai_captains=tuple(trusted if c.id == captain.id else c for c in self.engine.state.ai_captains)
        )
        ok, _ = self.engine.form_alliance(captain.id)
        self.assertTrue(ok)
        self.assertIn(captain.id, self.engine.state.ship.allies)

    def test_ai_trade_with_captain_changes_both_cargo_holds(self):
        captain = self.engine.state.ai_captains[0]
        captain = AICaptain.from_dict({**captain.to_dict(), "cargo": {"fuel_cells": 3}})
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(cargo={}),
            ai_captains=tuple(captain if c.id == captain.id else c for c in self.engine.state.ai_captains),
        )
        ok, _ = self.engine.interact_ai(captain.id, "buy", "fuel_cells", 2)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.cargo.get("fuel_cells"), 2)
        updated = next(c for c in self.engine.state.ai_captains if c.id == captain.id)
        self.assertEqual(updated.cargo.get("fuel_cells"), 1)


class DepotTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.orbit("sol_body_1")

    def test_deposit_withdraw_and_sell_from_depot(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(cargo={"titanium": 5}, credits=100)
        )
        ok, _ = self.engine.deposit_cargo("titanium", 3)
        self.assertTrue(ok)
        depot = next(d for d in self.engine.state.depots if d.system_id == "sol")
        self.assertEqual(depot.cargo.get("titanium"), 3)

        ok, _ = self.engine.withdraw_cargo("titanium", 1)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.cargo.get("titanium"), 3)

        credits = self.engine.state.ship.credits
        ok, _ = self.engine.sell_from_depot("titanium", 2)
        self.assertTrue(ok)
        self.assertGreater(self.engine.state.ship.credits, credits)
        depot = next(d for d in self.engine.state.depots if d.system_id == "sol")
        self.assertEqual(depot.cargo.get("titanium", 0), 0)

    def test_snapshot_reports_depot_used_volume(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(cargo={"titanium": 5}, credits=100)
        )
        ok, msg = self.engine.deposit_cargo("titanium", 3)
        self.assertTrue(ok, msg)
        snapshot = self.engine.get_status_snapshot()
        depot = next(d for d in snapshot["depots"] if d["system_id"] == "sol")
        self.assertEqual(depot["used_volume"], 6)
        self.assertEqual(depot["capacity"], 200)


class QuantumMessageTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_send_and_read_message(self):
        before = len(self.engine.state.messages)
        ok, _ = self.engine.send_quantum_message("Captain Vega", "Test", "Encrypted hello.")
        self.assertTrue(ok)
        self.assertEqual(len(self.engine.state.messages), before + 1)
        message = next(m for m in self.engine.state.messages if m.subject == "Test")
        self.assertFalse(message.read)
        ok, _ = self.engine.mark_message_read(message.id)
        self.assertTrue(ok)
        message = next(m for m in self.engine.state.messages if m.id == message.id)
        self.assertTrue(message.read)


class LandingAndFleetTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)

    def test_landing_on_habitable_body(self):
        body = next(b for b in self.engine.current_system.bodies if b.landable)
        self.engine.orbit(body.id)
        credits = self.engine.state.ship.credits
        ok, _ = self.engine.land_on_body(body.id)
        self.assertTrue(ok)
        self.assertEqual(self.engine.state.ship.landed_body_id, body.id)
        self.assertGreater(self.engine.state.ship.credits, credits)

    def test_landing_rejected_on_uninhabitable_body(self):
        body = next(b for b in self.engine.current_system.bodies if not b.landable and b.body_type != "star")
        self.engine.orbit(body.id)
        ok, _ = self.engine.land_on_body(body.id)
        self.assertFalse(ok)

    def test_hire_refit_and_dismiss_mercenary(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=10000)
        )
        ok, _ = self.engine.hire_mercenary("merc_ironclad")
        self.assertTrue(ok)
        merc = next(d for d in self.engine.state.ship.fleet_drones if d.drone_type == "mercenary")
        self.assertEqual(merc.specialty, "assault")

        ok, _ = self.engine.refit_fleet_unit(merc.id)
        self.assertTrue(ok)
        refit = next(d for d in self.engine.state.ship.fleet_drones if d.id == merc.id)
        self.assertEqual(refit.level, 2)
        self.assertGreater(refit.efficiency, 1.0)

        ok, _ = self.engine.dismiss_fleet_unit(merc.id)
        self.assertTrue(ok)
        self.assertFalse(any(d.id == merc.id for d in self.engine.state.ship.fleet_drones))

    def test_drone_stats_survive_ticks_and_deploy(self):
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                fleet_drones=(
                    FleetDrone(
                        id="drone_stats",
                        name="Stat Miner",
                        drone_type="mining",
                        assigned_system_id="sol",
                        level=4,
                        efficiency=1.5,
                        integrity=90,
                        sorties=12,
                    ),
                )
            )
        )
        self.engine.tick(4)
        drone = self.engine.state.ship.fleet_drones[0]
        self.assertEqual(drone.level, 4)
        self.assertEqual(drone.efficiency, 1.5)
        self.assertGreater(drone.sorties, 12)

        ok, _ = self.engine.deploy_drone("drone_stats", "alpha_centauri")
        self.assertTrue(ok)
        drone = self.engine.state.ship.fleet_drones[0]
        self.assertEqual(drone.efficiency, 1.5)
        self.assertEqual(drone.level, 4)


class TalentBranchTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                mastery=type(self.engine.state.ship.mastery)(
                    level=5, xp=0, next_level_xp=500, talent_points=3, specializations=()
                )
            )
        )

    def test_tier_two_requires_branch_root(self):
        ok, msg = self.engine.unlock_talent("deep_space_arrays")
        self.assertFalse(ok)
        self.assertIn("Prerequisite", msg)

        ok, _ = self.engine.unlock_talent("void_cartographer")
        self.assertTrue(ok)
        ok, _ = self.engine.unlock_talent("deep_space_arrays")
        self.assertTrue(ok)

    def test_every_talent_declares_branch_and_tier(self):
        for talent in PILOT_TALENTS.values():
            self.assertIn("branch", talent)
            self.assertIn("tier", talent)
            self.assertIn("requires", talent)


class ProceduralGalaxyTest(unittest.TestCase):
    def test_new_star_types_moons_and_planet_types(self):
        galaxy = GalaxyGenerator(seed=42).generate_galaxy()
        spectral = {s.spectral_type for s in galaxy.values()}
        self.assertTrue({"B", "O", "RedGiant", "Binary"}.issubset(spectral))
        self.assertGreaterEqual(len(galaxy), 15)

        body_types = {b.body_type for s in galaxy.values() for b in s.bodies}
        self.assertTrue({"savanna", "tundra", "toxic", "barren", "super_earth", "ice_giant"}.issubset(body_types))

        landable = [b for s in galaxy.values() for b in s.bodies if b.landable]
        self.assertTrue(landable)
        self.assertTrue(any(b.moons for s in galaxy.values() for b in s.bodies))
        self.assertTrue(any(b.atmosphere != "none" for s in galaxy.values() for b in s.bodies[1:]))

    def test_moon_model_round_trip(self):
        moon = Moon(id="m1", name="Moon 1", orbit_radius=0.2, radius_km=800, color="#fff", landable=True)
        self.assertEqual(Moon.from_dict(moon.to_dict()), moon)

    def test_depot_model_round_trip(self):
        depot = Depot(id="d1", name="Depot", system_id="sol", cargo={"titanium": 2})
        self.assertEqual(Depot.from_dict(depot.to_dict()), depot)

    def test_quantum_message_model_round_trip(self):
        message = QuantumMessage(id="m1", sender="A", recipient="B", subject="S", body="Body")
        self.assertEqual(QuantumMessage.from_dict(message.to_dict()), message)


if __name__ == "__main__":
    unittest.main()
