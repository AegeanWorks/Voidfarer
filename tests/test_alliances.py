"""Faction alliances: formation rules, allied patrols and the command-card wiring."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.pirates import pirate_risk


class FactionAllianceTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.faction_id = "sol_coalition"

    def test_alliance_requires_standing_and_forms_once(self):
        ok, message = self.engine.faction_diplomacy(self.faction_id, "alliance")
        self.assertFalse(ok)
        self.assertIn("standing", message.lower())

        standings = dict(self.engine.state.ship.faction_standings)
        standings[self.faction_id] = 80
        self.engine.state = self.engine._clone_state(
            ship=self.engine._clone_ship(faction_standings=standings)
        )
        ok, message = self.engine.faction_diplomacy(self.faction_id, "alliance")
        self.assertTrue(ok, message)
        self.assertIn(self.faction_id, self.engine.state.ship.allies)
        ok, message = self.engine.faction_diplomacy(self.faction_id, "alliance")
        self.assertFalse(ok)
        self.assertIn("already", message.lower())

    def test_allied_territory_reduces_pirate_risk(self):
        system = self.engine.current_system
        normal = pirate_risk(system, 0)
        allied = pirate_risk(system, 0, allied=True)
        self.assertLess(allied.chance, normal.chance)
        self.assertIn("allied", allied.reason)


if __name__ == "__main__":
    unittest.main()
