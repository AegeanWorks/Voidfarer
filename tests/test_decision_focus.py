"""The decision popup takes keyboard focus on a new decision, keeps it across rebuilds and returns it."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")


def _block() -> str:
    return JS.split("const pendingDecision = this.state.pending_decision;", 1)[1][:2800]


class TestDecisionFocus(unittest.TestCase):
    def test_a_new_decision_remembers_the_opener_and_focuses_a_choice_once(self) -> None:
        block = _block()
        self.assertIn("const newDecision = this._lastDecisionId !== pendingDecision.id;", block)
        self.assertIn("this._decisionOpener = document.activeElement;", block)
        self.assertIn("first.focus()", block)

    def test_a_rebuild_keeps_focus_on_the_same_choice(self) -> None:
        block = _block()
        self.assertIn("button.dataset.decisionChoice = choice.id;", block)
        self.assertIn("(document.activeElement.dataset || {}).decisionChoice", block)
        self.assertIn("kept.focus();", block)

    def test_resolving_returns_focus_to_the_opener(self) -> None:
        block = _block()
        hidden = block.split('this.decisionOverlay.style.display = "none";', 1)[1][:500]
        self.assertIn("this._decisionOpener.focus()", hidden)
        self.assertIn("this._lastDecisionId = null;", hidden)


if __name__ == "__main__":
    unittest.main()
