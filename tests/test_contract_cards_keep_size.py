"""Contract cards keep their content height inside the scrolling list (ADR-280)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "style.css"


class ContractCardsKeepSizeTests(unittest.TestCase):
    def test_cards_do_not_shrink_in_the_fixed_height_list(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        blocks = [
            body
            for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
            if re.search(r"#contractsList\s*>\s*\.contract-card|\.contract-card\s*\{", selectors)
            and "flex-shrink" in body
        ]
        self.assertTrue(blocks, "contract cards need an explicit flex-shrink rule")
        self.assertIn("flex-shrink: 0", " ".join(blocks))


if __name__ == "__main__":
    unittest.main()
