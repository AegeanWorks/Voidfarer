"""The creation origin tag shows the gain the rank-10 cap leaves (ADR-288)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "voidfarer" / "static" / "app.js"
CHARACTER = ROOT / "voidfarer" / "character.py"


class OriginTagCapTests(unittest.TestCase):
    def test_engine_caps_origin_training_at_rank_ten(self) -> None:
        source = CHARACTER.read_text(encoding="utf-8")
        self.assertTrue("capped at rank 10" in source, "the engine rule this tag mirrors")

    def test_tag_uses_the_capped_gain(self) -> None:
        app = APP.read_text(encoding="utf-8")
        start = app.index("this.renderAttrGrid = function")
        body = app[start:start + 3200]
        self.assertTrue("Math.min(bonus, Math.max(0, maxSkill - val))" in body, "gain must be capped by the remaining headroom")
        self.assertTrue("ORIGIN MAXED" in body, "a skill with no headroom must say so")
        self.assertTrue('class="attr-origin' in body)
        self.assertTrue(re.search(r"rank\s*\$\{maxSkill\}|stop at \$\{maxSkill\}", body) is not None, "the tooltip must explain the cap")


if __name__ == "__main__":
    unittest.main()
