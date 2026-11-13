"""System target card: the jump button states its fuel cost and refuses a jump the tank cannot cover."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


class TestJumpFuelCost(unittest.TestCase):
    def test_lane_fuel_comes_from_the_flight_report_and_is_cached(self) -> None:
        self.assertIn("laneFuelFor(systemId)", JS)
        self.assertIn('apiFetch("/api/flight")', JS)
        self.assertIn("connection.fuel_estimate", JS)
        self.assertIn("Date.now() - cache.at > 2000", JS)

    def test_button_shows_the_cost_and_blocks_an_unaffordable_jump(self) -> None:
        self.assertIn("EXECUTE HYPERSPACE JUMP (${lane} FUEL)", JS)
        self.assertIn("NEED ${lane} FUEL (HAVE ${fuel})", JS)
        self.assertIn("this.btnJumpTarget.disabled = short;", JS)

    def test_an_unknown_cost_keeps_the_original_label(self) -> None:
        self.assertIn('"EXECUTE HYPERSPACE JUMP"', JS)

    def test_out_of_range_and_current_location_labels_are_unchanged(self) -> None:
        self.assertIn('"OUT OF HYPERLANE RANGE"', JS)
        self.assertIn('"CURRENT LOCATION"', JS)


if __name__ == "__main__":
    unittest.main()
