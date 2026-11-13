"""Particle FX honor the OS reduce-motion preference: continuous decoration stops, event feedback stays."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "particles.js").read_text(encoding="utf-8")


def _method(name: str) -> str:
    match = re.search(r"\n    " + name + r"\([^\n]*\) \{\n(.*?)\n    \}\n", JS, re.S)
    return match.group(1) if match else ""


class TestReducedMotion(unittest.TestCase):
    def test_preference_is_read_and_tracked_live(self) -> None:
        self.assertIn('window.matchMedia("(prefers-reduced-motion: reduce)")', JS)
        self.assertIn("this.reduced =", JS)
        self.assertIn('addEventListener("change"', JS)

    def test_continuous_emitters_return_early_when_reduced(self) -> None:
        for name in ("trail", "thrustPlume", "warp", "rcsPuff", "ion"):
            self.assertIn("if (this.reduced) return;", _method(name), name)

    def test_event_feedback_is_not_suppressed(self) -> None:
        for name in ("burst", "shieldRipple", "hexShieldImpact", "flakBurst", "ring"):
            self.assertNotIn("this.reduced", _method(name), name)


if __name__ == "__main__":
    unittest.main()
