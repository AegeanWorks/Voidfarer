"""At laptop widths the freight row gives the net line its own full-width row (ADR-290)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "style.css"


class FreightRowNarrowTests(unittest.TestCase):
    def test_net_line_does_not_share_the_button_column(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        match = re.search(r"@media \(max-width: 1500px\) \{\s*\.quantum-route-row \{([^}]*)\}", css)
        self.assertTrue(match is not None, "the narrow freight rule must exist")
        rule = match.group(1)
        self.assertTrue('"net net"' in rule, "the net line spans the full width so its text cannot widen the button column")
        self.assertTrue('"main action"' in rule, "the button stays beside the route name")


if __name__ == "__main__":
    unittest.main()
