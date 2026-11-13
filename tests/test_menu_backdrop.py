"""Main menu backdrop: orbital rings fill the empty side only where there is room."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "style.css").read_text(encoding="utf-8")


class TestMenuBackdrop(unittest.TestCase):
    def test_motif_is_gated_to_roomy_windows(self) -> None:
        self.assertIn("@media (min-width: 1600px) and (min-height: 800px) {\n    .main-menu-overlay::before,",
                      CSS.replace("\r\n", "\n"))

    def test_motif_never_blocks_the_menu(self) -> None:
        block = CSS.split("@media (min-width: 1600px) and (min-height: 800px) {", 1)[1].split("}", 1)[0]
        self.assertIn("pointer-events: none", block)
        self.assertIn("z-index: -1", block)

    def test_only_the_planet_animates_and_reduced_motion_stops_it(self) -> None:
        self.assertRegex(CSS, r"\.main-menu-overlay::after \{[^}]*animation: menu-orbit-drift")
        self.assertNotRegex(CSS, r"\.main-menu-overlay::before \{[^}]*animation:")
        self.assertRegex(CSS, r"prefers-reduced-motion: reduce\) \{\s*\.main-menu-overlay::after \{ animation: none; \}")


if __name__ == "__main__":
    unittest.main()
