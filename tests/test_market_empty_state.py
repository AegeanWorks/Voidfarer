"""With no exchange the Commerce tab hides its dead controls, shows the explanation up top and names the stations."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "voidfarer" / "static"
JS = (STATIC / "app.js").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8").replace("\r\n", "\n")


class TestMarketEmptyState(unittest.TestCase):
    def test_the_tab_gets_a_no_exchange_state_that_the_station_branch_clears(self) -> None:
        self.assertIn('this.tabContentMarket.classList.add("no-exchange");', JS)
        self.assertIn('this.tabContentMarket.classList.remove("no-exchange");', JS)

    def test_the_dead_controls_are_hidden_while_there_is_no_exchange(self) -> None:
        rule = re.search(r"#tabContentMarket\.no-exchange ([^{]*)\{([^}]*)\}", CSS)
        self.assertIsNotNone(rule)
        for selector in (".market-lot-bar", ".market-category-filters", ".commodity-table-container",
                         ".trade-automation", ".quantum-freight-shell"):
            self.assertIn(selector, rule.group(1), selector)
        self.assertIn("display: none", rule.group(2))

    def test_the_message_names_up_to_three_stations_in_orbit_order(self) -> None:
        self.assertIn('id="noMarketStations"', HTML)
        block = JS.split("this.noMarketMsg.style.display = \"flex\";", 1)[1][:1400]
        self.assertIn("station_dockable", block)
        self.assertIn("(a.orbit_radius || 0) - (b.orbit_radius || 0)", block)
        self.assertIn("Stations in this system:", block)
        self.assertIn("slice(0, 3)", block)

    def test_an_empty_category_filter_is_told_apart_from_having_no_exchange(self) -> None:
        block = JS.split("    renderMarketTable() {", 1)[1][:7400]
        self.assertIn("if (!quotes.length && allQuotes.length) {", block)
        self.assertIn("No goods in this category here.", block)

    def test_the_new_text_styles_meet_the_12px_floor(self) -> None:
        self.assertRegex(CSS, r"\.market-empty \{[^}]*font-size: 12px")
        self.assertRegex(CSS, r"\.no-market-message \.no-market-stations \{[^}]*font-size: 12px")


if __name__ == "__main__":
    unittest.main()
