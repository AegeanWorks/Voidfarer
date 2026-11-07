# VoidFarer Continuous Improvement Campaign

Proof rules: every visual claim ships a before/after pair captured by the same harness,
seed, save and viewport; every mechanics claim ships a played run. Areas rotate so a cycle
does not repeat one.

## Covered areas

| Cycle | Area | Result |
|---|---|---|
| 1 | UI readability (1280x720 onboarding ribbon) | fixed, proven |
| 2 | Progression and saves (transit academy step) | fixed, proven |
| 3 | Combat feel (engines collapse + DRIVES gauge) | fixed, proven |
| 4 | Enemies/bosses (legacy rep sign + dead nanite telegraph) | fixed, proven |

Queue after Cycle 4: levels, graphics and effects, audio cues.

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

---

## Cycle 2 — Progression and saves: transit arrival completes Orbital Insertion

**Find.** Cycle 1's played arrival at Sol B (via `TRANSIT & ORBIT`) left the academy on
milestone 1, while the hint's CLI `orbit` verb advanced it. Evidence:
`ui-review/cycle01-play/03-orbit-establishing.png` shows `Milestone 1/6` after arrival.

**Analyze.** `engine.orbit()` calls `_progress_tutorial("orbit")`; the tick arrival branch
(`engine.py:9700`) only set `orbiting_body_id` and queued the arrival event. The milestone
hints also named `ENTER ORBIT` / `SENSOR SCAN`, controls that do not exist. Killed: no
alternative arrival path (quantum and sublight share this branch). Survivor: call the same
tutorial hook on body arrival, thread tutorial/credits/XP through the tick state, and point
the hints at the live controls.

**Fix.** `voidfarer/engine.py`: body arrival advances `_progress_tutorial("orbit")`, appends
its logs, adds credits to `gross_credits`, and awards XP after mastery initialisation; the
final ship receives `tutorial=new_tutorial`. `voidfarer/story.py`: hints now say
`TRANSIT & ORBIT` and `SCAN`. Tests: `test_transit_arrival_advances_orbit_milestone`
(one award across an extra tick) and `test_tutorial_hints_name_live_cockpit_controls`.
The transit test failed-first with `0 != 1` on the baseline.

**Visual proof (same 1280x720 play, same default save, same action sequence).**
- Before: `ui-review/cycle01-play/03-orbit-establishing.png` — arrived at Sol B, ribbon
  still `Milestone 1/6: Orbital Insertion`, academy log absent.
- After: `ui-review/cycle02-play/03b-after-arrival-clean.png` — arrived at Sol B, ribbon
  `Milestone 2/6: Planetary Sensor Sweep`, pip 1 checked, credits `2.197 CR`, `80/500 XP`,
  hint `Run 'scan' or click 'SCAN' in the radar map controls.`
- Hint pair: `ui-review/cycle02-play/01-before-transit.png` shows the new
  `TRANSIT & ORBIT` hint; the old `ENTER ORBIT` hint is in `cycle01-play/01-cockpit-start.png`.
- Vision review: `opencode/nemotron-3.5-super-vl-free` quoted both ribbons, confirmed the
  step advanced, the pips changed, and no new clipping/overlap at 1280x720.

**Play report.** `python ui-review/play_cycle2.py` (real Edge, 1280x720, default save):
selected Sol B, clicked `TRANSIT & ORBIT (4T)`, advanced with the real `+1` control to tick
6. Arrival: `sol_body_2`, milestone 2/6, credits 2,000 -> 2,197, XP 0 -> 80, exactly one
`ACADEMY STEP COMPLETE: [Orbital Insertion] (+200 cr, +80 XP)`; one extra tick kept one
award. Clicked the real `SCAN` control: milestone 3/6, credits 2,546, XP 230, second academy
log (`Planetary Sensor Sweep +250 cr, +100 XP`). 25 frames/414ms, zero console/page/HTTP
errors.

**Gates.** `python -m unittest discover` -> `Ran 1246 tests ... OK`; mechanics captain
stays green inside `aikit check`; `python aikit.py check voidfarer` -> 5/5. No save-schema
change.

**Commands.**
```text
python -m unittest tests.test_story.TestStoryAndTutorial.test_transit_arrival_advances_orbit_milestone  # fails first: 0 != 1
python -m unittest tests.test_story.TestStoryAndTutorial.test_transit_arrival_advances_orbit_milestone tests.test_story.TestStoryAndTutorial.test_tutorial_hints_name_live_cockpit_controls  # OK
python ui-review/play_cycle2.py                                                # exit 0, ok true
python -m unittest discover                                                    # Ran 1246 OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer         # map + README
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 3 — Combat feel: engines strikes collapse evasion and the DRIVES gauge tells the truth

**Find.** A `[ ENGINES ]` strike logs "Disabled impulse thrusters (collapsed enemy evasion)",
but the adaptive enemy immediately telegraphs `evade` again and the next damaging action can
miss. The DRIVES gauge also showed `CRIPPLED` whenever the enemy braced, and `NOMINAL` while
the engines were actually disabled.

**Analyze.** `CombatEncounter` had no persistent engine state; `choose_enemy_intent` only
looked at hull/profile, so the adaptive `enemy_hp < 0.30 -> evade` path re-armed after every
strike. The gauge keyed off `enemy_intent === "brace"`, the wrong signal. Killed: a
one-turn brace flag (does not survive the AI recompute). Survivor: an additive
`enemy_engines_disabled` field, forwarded through every combat rebuild, plus a gauge that
reads it.

**Fix.** `models.py`: additive field with `from_dict` default. `enemies.py`:
`choose_enemy_intent(..., engines_disabled)` suppresses adaptive evade. `engine.py`:
persist the flag on a successful engines strike, ignore stale evade intent and the 35%
evade miss while disabled, and forward the flag through the shield-absorb and standard
rebuilds. `app.js`: DRIVES gauge reads `enemy_engines_disabled`. Tests: two-turn engine
test, legacy-save default, static gauge contract. Before reproducer saved at
`ui-review/cycle03-before-engine/probe.out`.

**Visual proof (same 1280x720 state: Archon Sentinel hull 32/200 after the same strike).**
- Before: `ui-review/cycle03-before-ui/02-after-engines.png` — log says disabled thrusters,
  gauge `DRIVES ● NOMINAL`.
- After: `ui-review/cycle03-after-ui/02-after-engines.png` — gauge `DRIVES ✗ CRIPPLED`,
  bar at 25%; no new clipping or layout break.
- Vision review: `opencode/nemotron-3.5-super-vl-free` quoted all four gauges, called the
  before NOMINAL untruthful, and confirmed the after CRIPPLED state.

**Play report.** `python ui-review/play_cycle3.py cycle03-after-ui` (real Edge, 1280x720,
seeded Archon Sentinel): clicked `[ ENGINES ]`; state showed `engines_disabled=true`,
`enemy_intent=fire` (not evade), gauge `✕ CRIPPLED`; clicked `FIRE LASER ARRAY` and the
enemy died with a victory log, no "jinked" miss. 25 frames/406ms, zero console/page/HTTP
errors. Before-ui run: same click sequence, gauge stayed `● NOMINAL`, proving the perceptible
defect.

**Gates.** `python -m unittest discover` -> `Ran 1249 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5; UI task verified and finished on cockpit. Save schema additive only.

**Commands.**
```text
python ui-review/probe_combat_engines.py                                       # pre-fix: AFTER intent evade, strike missed
python -m unittest tests.test_combat_tactics tests.test_cockpit_layout.TestCombatGaugeHonesty  # OK
python ui-review/play_cycle3.py cycle03-before-ui                              # gauge NOMINAL
python ui-review/play_cycle3.py cycle03-after-ui                               # gauge CRIPPLED, ok true
python -m unittest discover                                                    # Ran 1249 OK
python aikit.py ui begin/verify/finish voidfarer --surface cockpit             # OK
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 4 — Enemies/bosses: legacy precursor rep sign and dead nanite telegraphs

**Find.** A legacy/custom Precursor Sentinel (no `archetype_id`) awarded `Precursor Watch
(+8)` on victory. The Warlord AI telegraphed `Nanite repair matrix deployed in automated
standby` with its shields at `0/100`, where the repair branch cannot fire.

**Analyze.** The faction fallback at the end of the victory path was never updated when
ADR-173 fixed the archetype payload; it kept the old `+8` sign and omitted the rival gain.
The boss policy treated `nanite_regen` as always usable; `combat_action` requires
`enemy_shield > 0`, so the telegraph was a dead ability. Killed: a UI-only fix (the state
was already wrong). Survivors: align the fallback with `precursor_sentinel.rep_rewards`, and
gate nanite out of `has_ability` when shields are zero.

**Fix.** `engine.py`: precursor fallback is `-8` Precursor / `+4` Void Corsairs with a
two-sided note. `enemies.py`: `has_ability` is false for `nanite_regen` when `enemy_sh <= 0`,
so all profile branches fall through. Tests: legacy payload rep delta, shields-down warlord
intent. Pre-fix probes saved in `ui-review/probe_enemies.py` output and in the before plays.

**Visual proof (same 1280x720 state and action).**
- Boss before: `ui-review/cycle04-before-boss/02-after-action.png` — telegraph
  `Nanite repair matrix deployed in automated standby`, shields `✕ OFFLINE`.
- Boss after: `ui-review/cycle04-after-boss/02-after-action.png` — telegraph
  `Weapons locked; charging main batteries`.
- Rep before: `ui-review/cycle04-before-rep/02-after-action.png` — flight log
  `[Faction Standing: Precursor Watch (+8)]`.
- Rep after: `ui-review/cycle04-after-rep/02-after-action.png` — flight log
  `[Faction Standing: Precursor Watch (-8), Void Corsairs (+4)]`.
- Vision review: `opencode-go/gemini-4-argon` quoted both pairs and found no new clipping.

**Play report.** `python ui-review/play_cycle4.py boss ...` (real Edge, seeded Void Warlord,
40/200 hull, 0 shields): clicked `SHIELD OVERCHARGE`; before intent `ability` / nanite
telegraph, after intent `fire` / weapon telegraph. `... rep ...` (seeded legacy Sentinel,
1 hull): clicked `FIRE LASER ARRAY`; before victory `+8`, after `-8` Precursor and `+4`
Void Corsairs, standing 0 -> -8 and -15 -> -11. Both 25 frames/~413ms, zero errors.

**Gates.** `python -m unittest discover` -> `Ran 1251 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5. No save-schema change.

**Commands.**
```text
python ui-review/probe_enemies.py                                             # pre-fix: precursor +8, warlord ability with 0 shields
python ui-review/play_cycle4.py boss cycle04-before-boss                      # in HEAD worktree, ok false as expected
python ui-review/play_cycle4.py rep cycle04-before-rep                        # in HEAD worktree, ok false as expected
python ui-review/play_cycle4.py boss cycle04-after-boss                       # ok true
python ui-review/play_cycle4.py rep cycle04-after-rep                         # ok true
python -m unittest discover                                                    # Ran 1251 OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py check voidfarer                                                # 5/5
```



