"""Frontier shipyards service hulls, escorts and weapons without a station dock."""

from dataclasses import replace
import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.fleet import build_fleet_ship
from voidfarer.models import Outpost


class FrontierShipyardTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.allow_decision_events = False
        self.corvette = build_fleet_ship("corvette", "sol", 0)
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(
                credits=10000,
                hull=50,
                fuel=10,
                orbiting_body_id=None,
                fleet_ships=(replace(self.corvette, hull=40),),
            )
        )

    def _shipyard(self, system_id="sol"):
        return Outpost(
            id=f"shipyard_{system_id}",
            name="Frontier Shipyard",
            system_id=system_id,
            body_id="sol_body_1",
            outpost_type="shipyard",
        )

    def test_escort_repair_rejects_non_positive_amounts(self):
        self.engine.state = self.engine._clone_state(
            outposts=(self._shipyard(),)
        )
        before = self.engine.state.ship.credits
        for amount in (-60, 0):
            ok, msg = self.engine.repair_escorts(amount)
            self.assertFalse(ok, msg)
            self.assertIn("positive", msg.lower())
        self.assertEqual(self.engine.state.ship.credits, before)
        self.assertEqual(self.engine.state.ship.fleet_ships[0].hull, 40)

    def test_local_shipyard_services_hull_fuel_and_escorts(self):
        self.engine.state = self.engine._clone_state(
            outposts=(self._shipyard(),)
        )
        ok, message = self.engine.repair_hull(10)
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.ship.hull, 60)

        ok, message = self.engine.refuel(10)
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.ship.fuel, 20)

        ok, message = self.engine.repair_escorts(20)
        self.assertTrue(ok, message)
        self.assertGreater(self.engine.state.ship.fleet_ships[0].hull, 40)

        ok, message = self.engine.train_fleet_ship(self.engine.state.ship.fleet_ships[0].id)
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.ship.fleet_ships[0].experience, 10)

        ok, message = self.engine.buy_escort("corvette")
        self.assertTrue(ok, message)
        self.assertEqual(len(self.engine.state.ship.fleet_ships), 2)

    def test_without_a_shipyard_undocked_services_are_refused(self):
        for call in (
            lambda: self.engine.repair_hull(10),
            lambda: self.engine.refuel(10),
            lambda: self.engine.repair_escorts(20),
            lambda: self.engine.train_fleet_ship(self.corvette.id),
            lambda: self.engine.buy_escort("corvette"),
        ):
            ok, message = call()
            self.assertFalse(ok)
            self.assertIn("shipyard", message.lower())

    def test_remote_shipyard_does_not_service_the_current_system(self):
        self.engine.state = self.engine._clone_state(
            outposts=(self._shipyard("vega"),)
        )
        ok, message = self.engine.repair_hull(10)
        self.assertFalse(ok)
        self.assertIn("shipyard", message.lower())

    def test_report_marks_the_local_shipyard(self):
        self.engine.state = self.engine._clone_state(
            outposts=(self._shipyard(),)
        )
        report = self.engine.get_outpost_report()
        self.assertEqual(report["outposts"][0]["outpost_type"], "shipyard")
        self.assertEqual(report["outposts"][0]["system_id"], "sol")

    def test_recommissioned_escort_ids_stay_unique(self):
        self.engine.orbit("sol_body_1")
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(credits=20000)
        )
        self.assertTrue(self.engine.buy_escort("corvette")[0])
        self.assertTrue(self.engine.buy_escort("corvette")[0])
        first_id = self.engine.state.ship.fleet_ships[0].id
        self.assertTrue(self.engine.sell_escort(first_id)[0])
        self.assertTrue(self.engine.buy_escort("corvette")[0])
        ids = [s.id for s in self.engine.state.ship.fleet_ships]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
