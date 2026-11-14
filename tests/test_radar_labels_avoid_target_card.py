"""Orbit-view labels route around the open target card (ADR-281)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "app.js"


class RadarLabelsAvoidTargetCardTests(unittest.TestCase):
    def test_label_collision_list_starts_with_the_card_rect(self) -> None:
        source = APP.read_text(encoding="utf-8")
        match = re.search(r"this\._radarLabelBoxes = (\[\]|this\.targetCardObstacle\(\));", source)
        self.assertIsNotNone(match)
        self.assertIn("targetCardObstacle()", match.group(0), "the card must seed the collision list")
        method = re.search(r"    targetCardObstacle\(\) \{(.*?)\n    \}\n", source, re.S)
        self.assertIsNotNone(method, "targetCardObstacle must exist")
        body = method.group(1)
        self.assertIn("navTargetCard", body)
        self.assertIn("getBoundingClientRect", body)
        self.assertIn("display", body, "a hidden card must not reserve space")


if __name__ == "__main__":
    unittest.main()
