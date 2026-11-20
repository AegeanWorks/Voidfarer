"""The endurance checker's comparison helpers must catch every drift shape (ADR-418)."""

from __future__ import annotations

import unittest

from tools.endurance_check import diff, strip_clock


class EnduranceDiffTest(unittest.TestCase):
    def test_identical_states_have_no_diff(self):
        state = {"ship": {"credits": 100, "cargo": {"water": 2}}, "tick": 5}
        self.assertEqual(diff(state, state), [])

    def test_a_changed_leaf_is_reported_with_its_path(self):
        rows = diff({"ship": {"credits": 100}}, {"ship": {"credits": 90}})
        self.assertEqual(len(rows), 1)
        path, before, after = rows[0]
        self.assertEqual(path, ("ship", "credits"))
        self.assertEqual((before, after), (100, 90))

    def test_a_missing_key_is_reported(self):
        rows = diff({"ship": {"credits": 1}}, {"ship": {}})
        self.assertEqual(rows[0][0], ("ship", "credits"))
        self.assertEqual(rows[0][2], "<missing>")

    def test_list_length_changes_are_reported(self):
        rows = diff({"crew": [1, 2]}, {"crew": [1]})
        self.assertEqual(rows[0][1], "len 2")

    def test_a_type_change_is_reported(self):
        rows = diff({"tick": 5}, {"tick": "5"})
        self.assertEqual(rows[0][0], ("tick",))

    def test_wall_clock_fields_are_ignored_at_any_depth(self):
        a = {"quests": [{"id": "q", "completed_at": 1.0}], "saved_at": 2.0}
        b = {"quests": [{"id": "q", "completed_at": 9.0}], "saved_at": 8.0}
        self.assertEqual(diff(strip_clock(a), strip_clock(b)), [])

    def test_strip_clock_keeps_play_clock_fields(self):
        stripped = strip_clock({"tick": 5, "completed_at": 1.0, "nested": {"created_at": 2}})
        self.assertEqual(stripped["tick"], 5)
        self.assertEqual(stripped["completed_at"], "<clock>")
        self.assertEqual(stripped["nested"]["created_at"], "<clock>")


if __name__ == "__main__":
    unittest.main()
