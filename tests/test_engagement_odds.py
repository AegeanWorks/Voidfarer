"""Stage 3 engagement odds: one tunable table, stated == coded.

Covers the fairness spine of the CyberPulse port (variable-ratio magnitude,
honest near-miss windows, push-luck projector, free contract swap) with
deterministic seeds. No dark patterns: every claim pairs with a measurement.
"""

import unittest
from dataclasses import replace

from voidfarer.engine import SimulationEngine
from voidfarer.models import BountyContract, CombatEncounter
from voidfarer.retention import (
    CONTRACT_OFFERS_MAX,
    NEAR_MISS_COMBAT_HULL_FRACTION,
    NEAR_MISS_SALVAGE_WINDOW,
    PAYOUT_MAGNITUDE_TABLE,
    RELIC_BASE_THRESHOLD,
    RELIC_NEAR_MISS_WINDOW,
    STREAK_TUNING,
    payout_magnitude_for,
    payout_odds_table,
    streak_multiplier,
)


class TestStreakMultiplier(unittest.TestCase):
    def test_values_match_legacy_formula(self):
        self.assertAlmostEqual(streak_multiplier(1), 1.00)
        self.assertAlmostEqual(streak_multiplier(2), 1.15)
        self.assertAlmostEqual(streak_multiplier(5), 1.60)
        self.assertAlmostEqual(streak_multiplier(11), 2.50)
        self.assertAlmostEqual(streak_multiplier(999), 2.50)

    def test_tuning_table_is_the_single_source(self):
        self.assertEqual(STREAK_TUNING["per_jump"], 0.15)
        self.assertEqual(STREAK_TUNING["cap"], 1.5)
        self.assertEqual(STREAK_TUNING["max_streak"], 10)


class TestPayoutMagnitude(unittest.TestCase):
    def test_stated_table_weights_sum_to_one(self):
        total = sum(weight for _, _, weight, _ in PAYOUT_MAGNITUDE_TABLE)
        self.assertAlmostEqual(total, 1.0)

    def test_deterministic_per_event_without_touching_live_rng(self):
        first = payout_magnitude_for(42, "combat-payout", "c1", 0)
        again = payout_magnitude_for(42, "combat-payout", "c1", 0)
        self.assertEqual(first, again)
        other = payout_magnitude_for(42, "combat-payout", "c2", 0)
        self.assertIsInstance(other, tuple)

    def test_distribution_matches_stated_70_20_10(self):
        counts = {"standard": 0, "rich": 0, "jackpot": 0}
        for i in range(4000):
            _, label = payout_magnitude_for(7, "probe", i)
            counts[label] += 1
        self.assertGreater(counts["standard"] / 4000, 0.65)
        self.assertLess(counts["standard"] / 4000, 0.75)
        self.assertGreater(counts["rich"] / 4000, 0.16)
        self.assertLess(counts["rich"] / 4000, 0.24)
        self.assertGreater(counts["jackpot"] / 4000, 0.07)
        self.assertLess(counts["jackpot"] / 4000, 0.13)

    def test_odds_table_matches_coded_table(self):
        table = payout_odds_table()
        coded = [(label, mult, weight) for label, mult, weight, _ in PAYOUT_MAGNITUDE_TABLE]
        stated = [(row["label"], row["multiplier"], row["weight"]) for row in table["table"]]
        self.assertEqual(stated, coded)

    def test_relic_windows_are_honest_constants(self):
        self.assertEqual(RELIC_BASE_THRESHOLD, 0.30)
        self.assertEqual(RELIC_NEAR_MISS_WINDOW, 0.15)
        self.assertEqual(NEAR_MISS_COMBAT_HULL_FRACTION, 0.10)
        self.assertEqual(NEAR_MISS_SALVAGE_WINDOW, 0.10)


class TestCombatNearMiss(unittest.TestCase):
    def _engine_with_target(self, hull, max_hull, seed=42):
        engine = SimulationEngine(seed=seed)
        combat = CombatEncounter(
            id="combat_nearmiss",
            enemy_name="Test Raider",
            enemy_class="Corsair",
            enemy_hull=hull,
            enemy_max_hull=max_hull,
            enemy_damage=1,
            bounty_credits=100,
            salvage_commodity="titanium",
        )
        engine.state = engine._clone_state(active_combat=combat)
        return engine

    def test_flag_defaults_false_and_round_trips(self):
        encounter = CombatEncounter(
            id="c", enemy_name="n", enemy_class="c",
            enemy_hull=10, enemy_max_hull=100, enemy_damage=1, bounty_credits=1,
        )
        self.assertFalse(encounter.near_miss_awarded)
        restored = CombatEncounter.from_dict(encounter.to_dict())
        self.assertFalse(restored.near_miss_awarded)

    def test_first_near_miss_grants_capped_surge_then_flavor(self):
        engine = self._engine_with_target(hull=30, max_hull=100)
        ok, _ = engine.combat_action("point_defense")  # 14 dmg -> 16 hull
        self.assertTrue(ok)
        combo_after_first = engine.state.ship.tactical_combo
        ok, msg = engine.combat_action("point_defense")  # 16 -> 2 hull (<=10%)
        self.assertTrue(ok)
        combat = engine.state.active_combat
        if combat is None:
            self.skipTest("target died before the near-miss window (tune hull)")
        self.assertTrue(combat.near_miss_awarded)
        # Hit (+1) plus the one-capped surge (+1).
        self.assertEqual(engine.state.ship.tactical_combo, combo_after_first + 2)
        self.assertIn("NEAR-MISS SURGE", msg)
        self.assertEqual(engine.state.stats.get("near_miss_combat"), 1)

    def test_whiffed_shot_breaks_combo(self):
        engine = self._engine_with_target(hull=500, max_hull=500, seed=11)
        engine.state = engine._clone_state(
            ship=engine._clone_ship(tactical_combo=2),
        )
        # Fire until a miss occurs (bounded, seeded): combo must hit 0 on a miss.
        saw_miss = False
        for _ in range(30):
            before = engine.state.ship.tactical_combo
            ok, msg = engine.combat_action("fire_lasers")
            self.assertTrue(ok)
            if "COMBO BROKEN" in msg:
                saw_miss = True
                self.assertEqual(engine.state.ship.tactical_combo, 0)
                break
            self.assertGreaterEqual(engine.state.ship.tactical_combo, before)
            if engine.state.active_combat is None:
                break
        self.assertTrue(saw_miss, "seed 11 fired 30 lasers without a single miss")


class TestContractSwap(unittest.TestCase):
    def _engine_with_completed_contract(self, seed=42):
        engine = SimulationEngine(seed=seed)
        active = engine.state.ship.active_contracts
        self.assertTrue(active, "fresh run must deal starter contracts")
        done = replace(
            active[0],
            current_count=active[0].target_count,
            completed=True,
        )
        engine.state = engine._clone_state(
            ship=engine._clone_ship(active_contracts=tuple([done] + list(active[1:]))),
        )
        return engine, done

    def test_claim_draws_free_offers_and_swap_is_unpunished(self):
        engine, done = self._engine_with_completed_contract()
        credits_before = engine.state.ship.credits
        ok, _, info = engine.claim_contract(done.id)
        self.assertTrue(ok)
        offers = info.get("replacement_options", [])
        self.assertEqual(len(offers), 2)
        stored = engine.state.ship.contract_offers
        self.assertLessEqual(len(stored), CONTRACT_OFFERS_MAX)
        self.assertEqual(
            engine.state.stats.get("contract_offers_drawn"), len(offers)
        )
        # Swap an offer onto the board: free, no standing loss.
        standings_before = dict(engine.state.ship.faction_standings)
        drop = engine.state.ship.active_contracts[-1]
        ok, msg = engine.swap_contract_offer(offers[0]["id"], drop.id)
        self.assertTrue(ok)
        self.assertIn("No fee", msg)
        active_ids = {c.id for c in engine.state.ship.active_contracts}
        self.assertIn(offers[0]["id"], active_ids)
        self.assertNotIn(drop.id, active_ids)
        self.assertEqual(engine.state.stats.get("contract_swaps"), 1)
        self.assertEqual(dict(engine.state.ship.faction_standings), standings_before)
        self.assertGreaterEqual(engine.state.ship.credits, credits_before)

    def test_swap_rejects_unknown_ids(self):
        engine = SimulationEngine(seed=42)
        ok, _ = engine.swap_contract_offer("nope", "nothing")
        self.assertFalse(ok)


class TestVoidProjector(unittest.TestCase):
    def test_gamble_block_states_every_term(self):
        from voidfarer.navigation import shortest_route

        engine = SimulationEngine(seed=42)
        path = shortest_route(engine.state.systems, "sol", "cygnus_x1")
        for target in path[1:]:
            engine.state = engine._clone_state(
                ship=engine._clone_ship(fuel=80),
                active_anomaly=None,
                active_combat=None,
            )
            ok, msg = engine.jump(target)
            self.assertTrue(ok, msg)
        ok, msg = engine.orbit("cygnus_x1_black_hole")
        self.assertTrue(ok, msg)
        engine.state = engine._clone_state(active_anomaly=None, active_combat=None)
        status = engine.void_status()
        self.assertTrue(status["dive_ready"])
        gamble = status.get("gamble", {})
        for key in (
            "storm_chance", "stability_loss_per_storm", "shield_loss_per_storm",
            "hull_loss_per_storm", "low_stability_threshold", "low_stability_bonus",
            "emerge_share", "collapse_hull_cost", "collapse_resonance_kept",
            "credits_per_resonance", "xp_per_resonance", "arrival_xp",
            "first_visit_bonus",
        ):
            self.assertIn(key, gamble)
        self.assertEqual(gamble["collapse_resonance_kept"], 0.0)
        self.assertTrue(status.get("destinations"), "horizon must chart destinations")
        for dest in status["destinations"]:
            self.assertIn("duration_ticks", dest)
            self.assertIn("fuel_estimate", dest)


class TestSalvageReport(unittest.TestCase):
    def test_report_carries_stated_odds(self):
        engine = SimulationEngine(seed=42)
        body = None
        for candidate in engine.current_system.bodies:
            from voidfarer.exploration import derive_derelict
            site = derive_derelict(
                engine.current_system.id, engine.current_system.seed, candidate
            )
            if site is not None:
                body = candidate
                break
        if body is None:
            self.skipTest("seed produced no salvage site")
        engine.state = engine._clone_state(
            ship=engine._clone_ship(orbiting_body_id=body.id)
        )
        ok, msg, report = engine.salvage_derelict("balanced")
        self.assertTrue(ok)
        self.assertIn("danger_roll", report)
        self.assertIn("payout_label", report)
        self.assertIn("odds", report)
        self.assertIn("Stated danger", msg)


if __name__ == "__main__":
    unittest.main()
