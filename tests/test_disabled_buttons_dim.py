"""Disabled HUD buttons look disabled (ADR-279)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CSS = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "style.css"


class DisabledButtonsDimTests(unittest.TestCase):
    def test_btn_hud_disabled_is_dimmed_and_blocked(self) -> None:
        css = CSS.read_text(encoding="utf-8")
        blocks = [
            body
            for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
            if re.search(r"\.btn-hud:disabled", selectors)
        ]
        self.assertTrue(blocks, ".btn-hud:disabled must be styled")
        joined = " ".join(blocks)
        opacity = re.search(r"opacity:\s*([\d.]+)", joined)
        self.assertIsNotNone(opacity, "a disabled HUD button must dim")
        # Dim enough to read as off, light enough that 'REQUIRES ...' labels stay legible.
        self.assertTrue(0.4 <= float(opacity.group(1)) <= 0.65)
        self.assertIn("not-allowed", joined)


if __name__ == "__main__":
    unittest.main()
