"""A fight saved mid-battle resumes the exact same exchange (ADR-411)."""

from __future__ import annotations

import unittest
from dataclasses import replace
from tempfile import TemporaryDirectory

from voidfarer.engine import SimulationEngine
from voidfarer.models import CombatEncounter
from voidfarer.storage import StorageManager

WALL_CLOCK = {"completed_at", "created_at", "started_at", "saved_at", "timestamp", "recorded_at"}


def _strip_clock(value, key=None):
    if key in WALL_CLOCK:
        return "<clock>"
    if isinstance(value, dict):
        return {name: _strip_clock(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [_strip_clock(item) for item in value]
    return value


def _combat_engine(seed: int = 11) -> SimulationEngine:
    engine = SimulationEngine(seed=seed)
    combat = CombatEncounter(
        id="combat_save_test",
        enemy_name="Outlaw Sentry",
        enemy_class="Drone",
        enemy_hull=200,
        enemy_max_hull=200,
        enemy_damage=6,
        bounty_credits=300,
    )
    engine.state = engine._clone_state(active_combat=combat)
    return engine


class CombatSaveParityTest(unittest.TestCase):
    def test_a_saved_fight_resumes_the_exact_exchange(self):
        with TemporaryDirectory() as temp_dir:
            engine = _combat_engine()
            StorageManager(temp_dir).save(engine.state)
            resumed = SimulationEngine(state=StorageManager(temp_dir).load())

        self.assertEqual(resumed.state.active_combat, engine.state.active_combat)

        first = engine.combat_action("fire_lasers")
        second = resumed.combat_action("fire_lasers")
        self.assertEqual(first, second)
        self.assertEqual(_strip_clock(engine.state.to_dict()),
                         _strip_clock(resumed.state.to_dict()))

    def test_two_rounds_stay_in_step_after_a_reload(self):
        with TemporaryDirectory() as temp_dir:
            engine = _combat_engine()
            StorageManager(temp_dir).save(engine.state)
            resumed = SimulationEngine(state=StorageManager(temp_dir).load())

        for action in ("fire_lasers", "brace_for_impact", "fire_lasers"):
            live = engine.combat_action(action)
            saved = resumed.combat_action(action)
            self.assertEqual(live, saved)
        self.assertEqual(_strip_clock(engine.state.to_dict()),
                         _strip_clock(resumed.state.to_dict()))

    def test_the_spent_gambit_and_evasion_bonus_survive_the_save(self):
        engine = _combat_engine()
        engine.state = engine._clone_state(active_combat=replace(
            engine.state.active_combat,
            captain_gambit_used=True,
            captain_evasion_bonus=0.2,
        ))
        with TemporaryDirectory() as temp_dir:
            StorageManager(temp_dir).save(engine.state)
            resumed = SimulationEngine(state=StorageManager(temp_dir).load())
        self.assertTrue(resumed.state.active_combat.captain_gambit_used)
        self.assertAlmostEqual(resumed.state.active_combat.captain_evasion_bonus, 0.2)


if __name__ == "__main__":
    unittest.main()
