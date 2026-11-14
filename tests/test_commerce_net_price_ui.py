"""The Commerce table shows, and judges profit by, the net sell price (ADR-282)."""

from __future__ import annotations

import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "app.js"


class CommerceNetPriceUiTests(unittest.TestCase):
    def test_table_and_winners_use_the_net_price(self) -> None:
        source = APP.read_text(encoding="utf-8")
        self.assertIn('<td class="td-sell ${margin}"', source)
        cell = source[source.index('<td class="td-sell ${margin}"'):][:200]
        self.assertIn("sellNet", cell)
        self.assertIn("const sellNet = Number(q.sell_price_net ?? q.sell_price)", source)
        self.assertIn("sellNet >= avg", source)
        self.assertIn("(sellNet - avg)", source)
        self.assertNotIn("Number(q.sell_price || 0) > avg", source)
        self.assertIn("Number(q.sell_price_net ?? q.sell_price) > avg", source)


if __name__ == "__main__":
    unittest.main()
