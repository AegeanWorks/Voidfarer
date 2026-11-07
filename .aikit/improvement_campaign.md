# VoidFarer Continuous Improvement Campaign

Proof rules: every visual claim ships a before/after pair captured by the same harness,
seed, save and viewport; every mechanics claim ships a played run. Areas rotate so a cycle
does not repeat one.

## Covered areas

| Cycle | Area | Result |
|---|---|---|
| 1 | UI readability (1280x720 onboarding ribbon) | fixed, proven |

Queue after Cycle 1: combat feel, enemies/bosses, levels, graphics and effects, audio cues,
progression and saves. Known candidate: transit arrival does not advance the academy step.

---

## Cycle 1 — UI readability: onboarding ribbon at 1280x720

**Find.** At the minimum supported viewport the CADET FLIGHT ACADEMY ribbon crossed the top
bar and its six milestone pips were clipped. Evidence: `ui-review/cycle00-baseline/short.png`.

**Analyze.** Edge measurements at 1280x720: ribbon height 38px, badge height 59px, overflow
10px above and 10px below. Cause: `.cockpit-frame` is a flex column and the ribbon kept
`flex-shrink: 1`, so the ribbon was compressed below its badge. Killed: none (the defect was
reproducible in one capture). Survivor: opt the ribbon out of flex shrink and keep the grid
as the flexible row.

**Fix.** `voidfarer/static/style.css`: `flex-shrink: 0` on `.cadet-academy-banner`.
Regression: `tests/test_cockpit_layout.py::TestCadetRibbonAtMinimumViewport`.
The failing-first contract failed on the baseline and passed after the rule.

**Visual proof (same harness, same default save, same 1280x720 viewport).**
- Before: `ui-review/cycle00-baseline/short.png` — ribbon 38px, badge 59px, pips clipped.
- After: `ui-review/cycle01-after/short.png` — ribbon 69px, badge 59px, pips fully visible,
  grid starts below; `errors 0 hscroll 0 tiny 0` in both reports.
- Vision review: `opencode/nemotron-3.5-super-vl-free` via the `reviewer` subagent quoted
  `HULL 100/100`, `SHIELD 100/100`, `CREDITS 2.000 CR`, `Milestone 1/6: Orbital Insertion`
  and `SKIP TUTORIAL`, and reported the pips restored with no new overlap or clipping.

**Play report.** `python ui-review/play_cycle1.py` (real Edge, 1280x720, default save):
selected Sol B, clicked `TRANSIT & ORBIT (4T)`, advanced four ticks with the real `+1`
control, arrived at `sol_body_2` (tick 6, `IN ORBIT`, credit balance 1,997), 26 frames in
417ms, zero console/page/HTTP errors, then `SKIP TUTORIAL` hid the ribbon (display `none`).
Finding kept for the next cycle: the orbit arrival did not advance the academy step (still
step 0); the hint's CLI `orbit` action does advance it.

**Gates.** `python -m unittest discover` -> `Ran 1244 tests ... OK`; `ui_inventory.py` ->
1145 lines (unchanged); `aikit ui begin/verify/finish` -> OK; `python aikit.py check
voidfarer` -> 5/5 (test, mechanics, hygiene, guidelines, secrets). No save-schema change.

**Commands.**
```text
python tools/ui_browser.py --viewports short --scenario cockpit --out ui-review/cycle00-baseline
python -m unittest tests.test_cockpit_layout.TestCadetRibbonAtMinimumViewport   # fails first
python tools/ui_browser.py --viewports short --scenario cockpit --out ui-review/cycle01-after
python ui-review/play_cycle1.py                                                # exit 0
python -m unittest discover                                                    # Ran 1244 OK
python tools/ui_inventory.py                                                   # 1145 lines
python aikit.py ui begin voidfarer --surface cockpit                           # OK
python aikit.py ui verify voidfarer                                            # OK
python aikit.py ui finish voidfarer --reviewed --reviewer ...                  # OK
python aikit.py check voidfarer                                                # 5/5
```
