"""Character Creation step 2: the +/- buttons are wired, re-enable every row, are named, and show the origin bonus."""

from __future__ import annotations

import unittest
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "style.css").read_text(encoding="utf-8")


def _setup() -> str:
    return JS.split("this.setupCharacterCreation = function() {", 1)[1][:1600]


def _render() -> str:
    return JS.split("this.renderAttrGrid = function() {", 1)[1][:2600]


class TestSkillAllocationUi(unittest.TestCase):
    def test_a_single_delegated_listener_drives_every_plus_and_minus_button(self) -> None:
        setup = _setup()
        self.assertIn('document.getElementById("attrGrid")?.addEventListener("click"', setup)
        self.assertIn('event.target.closest("[data-attr-delta]")', setup)
        self.assertIn("this.adjustAttr(button.dataset.attr, Number(button.dataset.attrDelta));", setup)

    def test_buttons_carry_their_skill_and_direction_and_an_accessible_name(self) -> None:
        render = _render()
        self.assertIn('data-attr="${attr}" data-attr-delta="-1"', render)
        self.assertIn('data-attr="${attr}" data-attr-delta="1"', render)
        self.assertIn("aria-label=\"Decrease ${label.toLowerCase()}\"", render)
        self.assertIn("aria-label=\"Increase ${label.toLowerCase()}\"", render)

    def test_a_change_re_renders_every_row_so_freed_points_re_enable_all_plus_buttons(self) -> None:
        adjust = JS.split("this.adjustAttr = function(attr, delta) {", 1)[1][:1600]
        self.assertIn("this.renderAttrGrid();", adjust)
        self.assertIn("focus()", adjust)

    def test_the_selected_origin_bonus_is_shown_on_the_skills_it_boosts(self) -> None:
        render = _render()
        self.assertIn("character_background_catalog", render)
        self.assertIn('class="attr-origin"', render)
        self.assertIn("ORIGIN", render)

    def test_unspent_points_are_called_out_as_lost(self) -> None:
        render = _render()
        self.assertIn("unspent points are lost", render)
        self.assertRegex(CSS, r"\.attr-origin \{")

    def test_changing_the_origin_refreshes_the_bonus_tags(self) -> None:
        self.assertIn("this.renderAttrGrid();", _setup())


if __name__ == "__main__":
    unittest.main()
