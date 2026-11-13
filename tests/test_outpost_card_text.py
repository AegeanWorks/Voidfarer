"""Outpost build cards use readable names, say where goods are delivered, and explain a credit shortfall."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


def _block() -> str:
    return JS.split("const yields = Object.entries(t.production || {})", 1)[1][:1400]


class TestOutpostCardText(unittest.TestCase):
    def test_commodity_names_are_readable_not_raw_ids(self) -> None:
        self.assertIn('String(k).replace(/_/g, " ")', JS)

    def test_goods_are_labelled_as_delivered_to_the_depot(self) -> None:
        block = _block()
        self.assertIn('k === "credits" || k === "research"', block)
        self.assertIn("(to depot)", block)

    def test_a_disabled_build_button_states_the_shortfall(self) -> None:
        block = _block()
        self.assertIn("Need ${t.cost - credits} more credits.", block)
        self.assertIn("const shortfall = credits < t.cost", block)


if __name__ == "__main__":
    unittest.main()
