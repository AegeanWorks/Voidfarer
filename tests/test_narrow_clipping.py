"""At 1280px the REFIT module descriptions and war pledge buttons wrap instead of being cut off."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "style.css").read_text(
    encoding="utf-8").replace("\r\n", "\n")


def _last(selector: str) -> str:
    found = re.findall(r"(?m)^" + re.escape(selector) + r" \{([^}]*)\}", CSS)
    return found[-1] if found else ""


class TestNarrowClipping(unittest.TestCase):
    def test_module_descriptions_wrap_in_full_because_they_state_the_trade_off(self) -> None:
        rule = _last(".ship-module-info small")
        self.assertIn("white-space: normal", rule)
        self.assertIn("overflow: visible", rule)
        self.assertNotIn("line-clamp", rule)

    def test_war_pledge_buttons_wrap_instead_of_ellipsizing(self) -> None:
        rule = _last(".war-actions .btn-hud")
        self.assertIn("white-space: normal", rule)
        self.assertNotIn("text-overflow: ellipsis", rule)

    def test_exchange_title_wraps_for_long_station_names(self) -> None:
        self.assertIn("#tabContentMarket > .panel-header .panel-title { white-space: normal;", CSS)

    def test_narrow_service_cards_stack_icon_over_text(self) -> None:
        self.assertIn(".station-services-bar .btn-service { flex-direction: column;", CSS)


if __name__ == "__main__":
    unittest.main()
