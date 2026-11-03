"""Stage 3 balance tuning proofs (M3-M6): DATA tables the game reads.

M3: execute x1.25 (was 1.5), tachyon 10 hull (was 15).
M4: low-sec combat 0.25 (was 0.40), anomaly 0.20 (was 0.35); hostile 0.65 unchanged.
M5: haven bonus +0.20 (was +0.30), threat-1 toll cap 220.
M6: research base gain 2 RP/tick (was 1).
"""

import unittest

from voidfarer import enemies, pirates, research
from voidfarer.navigation import JUMP_ENCOUNTER_TUNING


class BalanceTuningStage3Test(unittest.TestCase):
    def test_execute_multiplier_tuned(self):
        self.assertEqual(enemies.EXECUTE_DAMAGE_MULTIPLIER, 1.25)

    def test_tachyon_damage_tuned(self):
        self.assertEqual(enemies.TACHYON_LANCE_HULL_DAMAGE, 10)

    def test_jump_encounter_rates_tuned(self):
        self.assertEqual(JUMP_ENCOUNTER_TUNING["hostile_sec_combat"], 0.65)
        self.assertEqual(JUMP_ENCOUNTER_TUNING["low_sec_combat"], 0.25)
        self.assertEqual(JUMP_ENCOUNTER_TUNING["anomaly"], 0.20)

    def test_pirate_haven_bonus_tuned(self):
        self.assertEqual(pirates.PIRATE_HAVEN_BONUS, 0.20)

    def test_threat_one_toll_capped(self):
        from voidfarer.models import StarSystem

        rng_seed = 7
        tolls = [
            pirates.generate_pirate_encounter(
                StarSystem(
                    id="haventest",
                    name="Haven Test",
                    seed=42,
                    x=0.0,
                    y=0.0,
                    spectral_type="M",
                    color="#ffffff",
                    security=0.10,
                    faction="Void Corsairs",
                    bodies=(),
                    connections=(),
                ),
                seed=rng_seed + i,
                threat_level=1,
                standing=0,
            ).toll_credits
            for i in range(50)
        ]
        self.assertTrue(tolls)
        self.assertLessEqual(max(tolls), 220)

    def test_research_base_gain_tuned(self):
        self.assertEqual(research.RESEARCH_BASE_GAIN_PER_TICK, 2)


if __name__ == "__main__":
    unittest.main()
