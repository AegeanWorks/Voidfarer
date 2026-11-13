"""Encounter cards: action descriptions meet the cockpit's 12px readability floor."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "style.css").read_text(
    encoding="utf-8").replace("\r\n", "\n")


class TestEncounterReadability(unittest.TestCase):
    def test_choice_check_is_at_least_12px(self) -> None:
        rule = re.search(r"\n\.choice-check \{([^}]*)\}", CSS)
        self.assertIsNotNone(rule)
        size = re.search(r"font-size:\s*([\d.]+)(px|rem)", rule.group(1))
        self.assertIsNotNone(size)
        px = float(size.group(1)) * (16 if size.group(2) == "rem" else 1)
        self.assertGreaterEqual(px, 12.0)


if __name__ == "__main__":
    unittest.main()
