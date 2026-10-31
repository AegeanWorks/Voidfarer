"""War news must survive a real save/load cycle, like every other game state."""

import tempfile
import unittest
from pathlib import Path

from voidfarer.engine import SimulationEngine
from voidfarer.storage import StorageManager


class WarNewsPersistenceTest(unittest.TestCase):
    def test_war_notifications_and_trimmed_log_survive_a_disk_round_trip(self):
        work = Path(tempfile.mkdtemp(prefix="vf_news_save_"))
        storage = StorageManager(work)
        engine = SimulationEngine(seed=42, state=storage.load())
        before_events = []
        for _ in range(1200):
            engine.tick(1)
            before_events = [e for e in engine.state.events if e.kind == "war"]
            if before_events:
                break
        self.assertTrue(before_events, "the campaign produced no war news to persist")
        before_log = tuple(engine.state.ship.flight_log)

        storage.save(engine.state)
        reloaded = SimulationEngine(state=storage.load())

        after_events = [e for e in reloaded.state.events if e.kind == "war"]
        self.assertEqual([e.id for e in after_events], [e.id for e in before_events])
        self.assertEqual([e.title for e in after_events], [e.title for e in before_events])
        self.assertEqual(tuple(reloaded.state.ship.flight_log), before_log)

    def test_a_reloaded_campaign_keeps_announcing_new_wars(self):
        work = Path(tempfile.mkdtemp(prefix="vf_news_save2_"))
        storage = StorageManager(work)
        engine = SimulationEngine(seed=42, state=storage.load())
        for _ in range(1200):
            engine.tick(1)
            if any(e.kind == "war" for e in engine.state.events):
                break
        storage.save(engine.state)
        reloaded = SimulationEngine(state=storage.load())
        first_tick = reloaded.state.time.tick
        new_events = []
        for _ in range(1200):
            reloaded.tick(1)
            new_events = [
                e for e in reloaded.state.events if e.kind == "war" and e.tick > first_tick
            ]
            if new_events:
                break
        self.assertTrue(new_events, "a reloaded campaign stopped reporting war news")
        ids = [e.id for e in reloaded.state.events]
        self.assertEqual(len(ids), len(set(ids)), "event ids collided after reload")


if __name__ == "__main__":
    unittest.main()
