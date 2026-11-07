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
| 5 | Levels (gas/lava landings + full surface catalog) | fixed, proven |
| 6 | Graphics and effects (NPC radar label collision) | fixed, proven |
| 7 | Audio cues (SOUND FX mute persistence + master gain) | fixed, proven |
| 8 | Audio cues re-sweep (pilot level-up cue) | fixed, proven |

Queue after Cycle 8: re-sweep all areas for new verified findings. Candidate: PLAYER card
level/XP vs HUD Mastery level consistency (needs confirmation of intended semantics).

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

---

## Cycle 5 — Levels: gas/lava landings and a fully reachable surface catalog

**Find.** A generated-galaxy reachability sweep found `cloud_scoop` and `magma_tap` on zero
of 70 landable bodies, although the README advertises both. Evidence:
`ui-review/cycle05-before/01b-gas-target-card-bottom.png` has no landing action for Sol F.

**Analyze.** `GalaxyGenerator` marked only habitable worlds landable, excluding the gas,
ringed, ice and lava biomes that own those operations. A landable gas world would also
inherit rover operations that make no sense in a cloud deck, and the load migration would
assign it a government despite zero population. Killed: changing only the operation body
lists (still no landable host). Survivors: landable surface types, gas-only operation
gating, and a population guard on the migration.

**Fix.** `galaxy.py`: lava/volcanic/gas/ringed/ice/methane worlds join the landable set.
`surface.py`: additive `exclude_types`; seven rover ops exclude gas types, cryo drill drops
ice giants, cloud scoop covers all four gas types. `engine.py`: government is seeded only
when population > 0. Tests: all operations reachable, ringed-giant cloud scoop, lava magma
tap, uninhabited gas migration; the obsolete "landable means inhabited" test was corrected
to the new contract and extended.

**Visual proof (same 1280x720 Sol F ringed giant, target card scrolled to its actions).**
- Before: `ui-review/cycle05-before/01b-gas-target-card-bottom.png` — no `LAND ON SURFACE`.
- After: `ui-review/cycle05-after/01b-gas-target-card-bottom.png` — `LAND ON SURFACE`
  appears; `POPULATION Uninhabited`, `GOVERNMENT None`.
- After landing: `ui-review/cycle05-after/02-gas-surface-ops.png` — `SURFACE SCAN //
  RINGED GIANT`, `2 SITES`.
- After running: `ui-review/cycle05-after/03-cloud-scoop-run.png` — `S2 Cloud Scoop` row,
  `+3 Quantum Fuel Cells`, `WORKED`, hold 15 -> 18.
- Vision review: `opencode-go/gemini-4-argon` quoted the action rows, site count and Cloud
  Scoop state, and found no new clipping.

**Play report.** `python ui-review/play_cycle5.py cycle05-after` (real Edge, 1280x720,
seed-42 Sol F): the target card gained `LAND ON SURFACE`, landing paid +450 cr, the gas map
offered `field_rest` + `cloud_scoop`, and clicking `Cloud Scoop` succeeded for +3 fuel
cells. 25 frames/407ms, zero console/page/HTTP errors. The before worktree run shows
`landButton.display = none` and is recorded in `cycle05-before/run.out`.

**Gates.** `python -m unittest discover` -> `Ran 1255 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5. No new save field; old saves keep their stored landable flags until a
new game/reset.

**Commands.**
```text
python ui-review/probe_cloud_scoop.py                                         # before: cloud_scoop NOWHERE
python ui-review/play_cycle5.py cycle05-before                                # in HEAD worktree, ok false
python ui-review/play_cycle5.py cycle05-after                                 # ok true
python -m unittest tests.test_frontier_depth.SurfaceOperationTest             # OK
python -m unittest discover                                                    # Ran 1255 OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 6 — Graphics and effects: NPC radar names join the label collision map

**Find.** `Rorik Ironjaw` was painted directly over `VF-FLAGSHIP` at a deterministic
1920x1080 radar frame, making both strings unreadable. Evidence:
`ui-review/cycle06-before/01-radar-labels.png`.

**Analyze.** `drawSystemTraffic` used a raw `ctx.fillText` after the body/flagship labels
had already been placed through `placeRadarLabel`, so the NPC name bypassed the collision
map. Killed: hiding all NPC names (they carry selection and trade information). Survivor:
route traffic names through the same placement helper, dropping only unselected names when
the map is genuinely full.

**Fix.** `app.js`: `drawSystemTraffic` calls `placeRadarLabel` (priority 0, selected 4)
instead of raw text. Test: `TestRadarTrafficLabels` pins the call and forbids the raw
`ctx.fillText(captain.name, ...)`.

**Visual proof (same default save, frozen clock 54,000 ms, 1920x1080).**
- Before: `ui-review/cycle06-before/01-radar-labels.png` — `Rorik Ironjaw` sits on
  `VF-FLAGSHIP`.
- After: `ui-review/cycle06-after/01-radar-labels.png` — `Rorik Ironjaw` is boxed on its
  own row; all body labels remain present and legible.
- Vision review: `opencode-go/gemini-4-argon` called the before pair unreadable and quoted
  the clear after placement; no new clipping or missing labels.

**Play report.** `python ui-review/play_cycle6.py cycle06-after` (real Edge, frozen clock):
loaded the cockpit, clicked the deterministic `Rorik Ironjaw` marker; `selectedType` became
`captain`, the target card showed `TARGET: MERCENARY HULL // Rorik Ironjaw // SOL // TRUST
11 // STANDING 23`. 25 frames/409ms, zero console/page/HTTP errors. Before run:
`ui-review/cycle06-before/play-report.json` with the same successful click and the overlap
capture.

**Gates.** `python -m unittest discover` -> `Ran 1256 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5. UI task verified/finished on cockpit. The UI fast-proof timeout was
raised to 300s in `chore(ui): allow the full suite to finish under host load` because other
agents were loading the host.

**Commands.**
```text
python ui-review/play_cycle6.py cycle06-before                               # overlap capture, click ok
python ui-review/play_cycle6.py cycle06-after                                # no overlap, click ok
python -m unittest tests.test_cockpit_layout.TestRadarTrafficLabels           # OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py ui begin/verify/finish voidfarer --surface cockpit            # OK
python -m unittest discover                                                    # Ran 1256 OK
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 7 — Audio cues: SOUND FX mute persists and silences the master gain

**Find.** The top-bar `SOUND FX` toggle changed the flag/icon but not the master gain or
saved settings. A real browser play showed `enabled=false` with `masterGain=0.8` and no
stored setting; after reload the button reverted to `◉ SOUND FX`.

**Analyze.** `SoundController.toggle()` only flipped a boolean; the audio toggle handler
never called `saveSettings()`, and `setVolume()` kept the master gain live while muted.
Killed: a UI-only icon change (audio kept playing and the state reset). Survivor:
`setEnabled()` owns the flag and master gain, the toggle saves, and both settings paths go
through the same setter.

**Fix.** `app.js`: `setEnabled(on)` drives `master` to `volume`/`0`; `init` creates the gain
at the correct level; `setVolume` respects mute; the top-bar handler saves settings and
syncs the checkbox; load fixes icon/opacity. Test: `TestAudioMuteControl`.

**Visual proof (same 1920x1080 default save, mute then reload).**
- Before: `ui-review/cycle07-before/02-after-reload.png` — `◉ SOUND FX` after reload.
- After: `ui-review/cycle07-after/02-after-reload.png` — `MUTED SOUND FX` after reload.
- Immediate mute: `ui-review/cycle07-after/01-muted-now.png` — `○ SOUND FX`.
- Vision review: `opencode-go/gemini-4-argon` quoted both reload states and confirmed no
  header overlap or clipping.

**Play report.** `python ui-review/play_cycle7.py cycle07-after` (real Edge, 1920x1080):
clicked SOUND FX; `masterGain` went 0.8 -> 0 and `storedSound` became false; reload kept
`enabled=false` and icon `MUTED`; clicking again restored `masterGain≈0.8` and
`storedSound=true`. 25 frames/408ms, zero console/page/HTTP errors. Before run:
`ui-review/cycle07-before/play-report.json` shows the reset.

**Gates.** `python -m unittest discover` -> `Ran 1257 tests ... OK` (a transient host-load
run had 5 socket-timeout errors and a 205s fast proof; an immediate rerun was green with no
code change); `python aikit.py check voidfarer` -> 5/5. UI task verified/finished.

**Commands.**
```text
python ui-review/play_cycle7.py cycle07-before                               # muted state lost on reload
python ui-review/play_cycle7.py cycle07-after                                # ok true, mute persists
python -m unittest tests.test_cockpit_layout.TestAudioMuteControl             # OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py ui begin/verify/finish voidfarer --surface cockpit            # OK
python -m unittest discover                                                    # Ran 1257 OK
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 8 — Audio re-sweep: pilot promotions fire the unused level-up cue

**Find.** `SoundController.playLevelUp()` had no call site. A scan from 490/500 XP to
level 2 rendered `★ PILOT PROMOTION` and `★ LVL 2` in silence; instrumented browser play
counted zero level-up calls.

**Analyze.** The HUD updated `mastery.level` but nothing compared the old and new level.
Killed: firing the cue on every render (it would repeat on refresh). Survivor: remember the
last rendered level, cue only on an increase, and skip the first render so a loaded save
does not fire.

**Fix.** `app.js`: `_lastMasteryLevel` tracker in the constructor and a guarded
`this.sound.playLevelUp()` in `renderHUD`. Test: `TestAudioLevelUpCue`.

**Proof (real browser play, 1280x720, Sol B scan from 490 XP).**
- Before: `cycle08-before/play-report.json` — level 1 -> 2, `levelUpSounds: 0`, no cue.
- After: `cycle08-after/play-report.json` — level 1 -> 2, `levelUpSounds: 1`,
  `★ LVL 2`, `40/750 XP · +1P`, 25 frames/402ms, zero errors.
- Screenshot context: `ui-review/cycle08-after/02-after-promotion.png`; vision review found
  no layout break.
- This is an audio claim, so the played run and instrumented call count are the proof.

**Gates.** `python -m unittest discover` -> `Ran 1258 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5. UI task verified/finished. No save-schema change.

**Commands.**
```text
python ui-review/play_cycle8.py cycle08-before                               # levelUpSounds: 0
python ui-review/play_cycle8.py cycle08-after                                # levelUpSounds: 1
python -m unittest tests.test_cockpit_layout.TestAudioLevelUpCue              # OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py ui begin/verify/finish voidfarer --surface cockpit            # OK
python -m unittest discover                                                    # Ran 1258 OK
python aikit.py check voidfarer                                                # 5/5
```



