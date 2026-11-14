"""Character creation works on a first launch, before any game state has loaded (ADR-286)."""

from __future__ import annotations

import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "voidfarer" / "static" / "app.js"


class CreationFirstLaunchTests(unittest.TestCase):
    def test_origin_catalog_falls_back_to_the_cached_catalogs(self) -> None:
        app = APP.read_text(encoding="utf-8")
        self.assertTrue("this.catalogs = function(key)" in app, "a catalog accessor is required")
        body = app[app.index("this.catalogs = function(key)"):][:300]
        self.assertTrue("catalogCache" in body, "it must fall back to the cached /api/catalogs payload")
        for needle in ("syncBackgroundHint", "renderAttrGrid"):
            start = app.index("this." + needle + " = function")
            self.assertTrue('this.catalogs("character_background_catalog")' in app[start:start + 900],
                            needle + " must read the origins through the accessor")


if __name__ == "__main__":
    unittest.main()
