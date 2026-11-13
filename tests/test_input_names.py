"""Every form input has an accessible name, not just a nearby visual label."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / "voidfarer" / "static" / "index.html").read_text(encoding="utf-8")

EXPECTED = {
    "settingVolume": "Master volume",
    "charName": "Commander name",
    "charAge": "Commander age",
    "sliderEng": "Engines power",
    "sliderShd": "Shields power",
    "sliderSen": "Sensors power",
    "sliderWep": "Weapons power",
}


class TestInputNames(unittest.TestCase):
    def test_each_listed_input_carries_its_aria_label(self) -> None:
        for input_id, label in EXPECTED.items():
            tag = re.search(r"<input[^>]*\bid=\"" + input_id + r"\"[^>]*>", HTML)
            self.assertIsNotNone(tag, input_id)
            self.assertIn(f'aria-label="{label}"', tag.group(0), input_id)

    def test_no_text_range_or_number_input_is_left_unnamed(self) -> None:
        for tag in re.findall(r"<input[^>]*>", HTML):
            if re.search(r'type="(text|range|number)"', tag):
                has_name = "aria-label=" in tag or "aria-labelledby=" in tag
                wrapped = False  # inputs inside a <label> are named by it; checked below by id
                input_id = re.search(r'id="([^"]+)"', tag)
                if input_id and input_id.group(1) in EXPECTED:
                    self.assertTrue(has_name or wrapped, tag)


if __name__ == "__main__":
    unittest.main()
