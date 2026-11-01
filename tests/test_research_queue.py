"""Research queue: validation, ordering, auto-start and persistence."""

import unittest

from voidfarer.engine import SimulationEngine
from voidfarer.models import GameState, ResearchState


class ResearchQueueEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = SimulationEngine(seed=42)
        self.engine.allow_decision_events = False

    def test_queue_validates_and_orders_projects(self):
        ok, message = self.engine.queue_research("advanced_cooling")
        self.assertTrue(ok, message)
        ok, message = self.engine.queue_research("deep_survey_arrays")
        self.assertTrue(ok, message)
        self.assertEqual(
            self.engine.state.research.queue,
            ("advanced_cooling", "deep_survey_arrays"),
        )
        ok, message = self.engine.queue_research("advanced_cooling")
        self.assertFalse(ok)
        self.assertIn("already queued", message.lower())
        ok, message = self.engine.queue_research("bogus")
        self.assertFalse(ok)
        self.assertIn("unknown", message.lower())

    def test_cancel_removes_only_the_named_project(self):
        self.engine.queue_research("advanced_cooling")
        self.engine.queue_research("deep_survey_arrays")
        ok, message = self.engine.cancel_queued_research("advanced_cooling")
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.research.queue, ("deep_survey_arrays",))
        ok, message = self.engine.cancel_queued_research("missing")
        self.assertFalse(ok)
        self.assertIn("not in", message.lower())

    def test_starting_a_queued_project_removes_it_from_the_queue(self):
        self.engine.queue_research("advanced_cooling")
        ok, message = self.engine.choose_research("advanced_cooling")
        self.assertTrue(ok, message)
        self.assertEqual(self.engine.state.research.queue, ())
        self.assertEqual(
            self.engine.state.research.active_project_id, "advanced_cooling"
        )

    def test_completion_starts_the_next_queued_project(self):
        self.engine.state = self.engine._clone_state(
            research=ResearchState(
                points=0,
                progress=119,
                active_project_id="advanced_cooling",
                completed=(),
                queue=("deep_survey_arrays",),
            )
        )
        payload = self.engine.tick(1)
        research = self.engine.state.research
        self.assertIn("advanced_cooling", research.completed)
        self.assertEqual(research.active_project_id, "deep_survey_arrays")
        self.assertEqual(research.queue, ())
        self.assertEqual(payload["ticks_advanced"], 1)

    def test_blocked_queued_projects_are_kept_until_their_prerequisite_finishes(self):
        # automated_hull_repair needs efficient_fusion, which is not complete yet.
        self.engine.state = self.engine._clone_state(
            research=ResearchState(
                points=0,
                progress=0,
                active_project_id=None,
                completed=(),
                queue=("automated_hull_repair", "plasma_weapons"),
            )
        )
        self.engine.tick(1)
        research = self.engine.state.research
        self.assertEqual(research.active_project_id, "plasma_weapons")
        self.assertEqual(research.queue, ("automated_hull_repair",))

        # Once the prerequisite finishes, the retained entry starts automatically.
        self.engine.state = self.engine._clone_state(
            research=ResearchState(
                points=0,
                progress=0,
                active_project_id=None,
                completed=("efficient_fusion",),
                queue=("automated_hull_repair",),
            )
        )
        self.engine.tick(1)
        research = self.engine.state.research
        self.assertEqual(research.active_project_id, "automated_hull_repair")
        self.assertEqual(research.queue, ())

    def test_queue_persists_across_saves(self):
        self.engine.queue_research("advanced_cooling")
        restored = GameState.from_dict(self.engine.state.to_dict())
        self.assertEqual(restored.research.queue, ("advanced_cooling",))

    def test_legacy_research_defaults_to_empty_queue(self):
        payload = self.engine.state.to_dict()
        payload["research"].pop("queue", None)
        restored = GameState.from_dict(payload)
        self.assertEqual(restored.research.queue, ())


if __name__ == "__main__":
    unittest.main()
