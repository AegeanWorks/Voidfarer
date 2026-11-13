"""Every origin name the creation screen has ever offered grants its origin training."""

from __future__ import annotations

import unittest

from voidfarer.character import COMMANDER_BACKGROUNDS, apply_background_bonus, match_background

BASE = {"piloting": 3, "engineering": 3, "science": 3, "combat": 3, "diplomacy": 3, "trade": 3}


class TestBackgroundAliases(unittest.TestCase):
    def test_legacy_dropdown_names_resolve_to_their_catalog_origins(self) -> None:
        self.assertEqual(match_background("Scientist"), "prospector")
        self.assertEqual(match_background("Trader"), "merchant")
        self.assertEqual(match_background("  trader "), "merchant")

    def test_aliases_grant_the_same_training_as_the_catalog_name(self) -> None:
        self.assertEqual(
            apply_background_bonus(BASE, match_background("Scientist")),
            apply_background_bonus(BASE, "prospector"),
        )
        self.assertEqual(
            apply_background_bonus(BASE, match_background("Trader")),
            apply_background_bonus(BASE, "merchant"),
        )

    def test_every_catalog_origin_still_resolves_by_id_and_by_display_name(self) -> None:
        for background_id, info in COMMANDER_BACKGROUNDS.items():
            self.assertEqual(match_background(background_id), background_id)
            self.assertEqual(match_background(info["name"]), background_id)

    def test_a_genuinely_custom_origin_still_grants_nothing(self) -> None:
        self.assertIsNone(match_background("Smuggler"))
        self.assertEqual(apply_background_bonus(BASE, "smuggler"), BASE)


if __name__ == "__main__":
    unittest.main()
