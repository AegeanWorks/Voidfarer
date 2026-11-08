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
| 9 | UI readability re-sweep (Commander vs Pilot Mastery labels) | fixed, proven |
| 10 | Saving/load re-sweep (legacy landable migration) | fixed, proven |
| 11 | Economy re-sweep (one-time landing survey reward) | fixed, proven |
| 12 | Final re-sweep | zero verified improvements |

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

---

## Cycle 9 — UI readability re-sweep: Commander vs Pilot Mastery labels

**Find.** After a Pilot Mastery promotion the PLAYER card still showed `LEVEL 1 0/400 XP`
while the HUD showed `★ LVL 2 40/750 XP`; both are separate tracks (Commander character
XP vs Pilot Mastery) but the card labeled both the same. Evidence:
`ui-review/cycle08-after/02-after-promotion.png`.

**Analyze.** `renderPlayer` read `state.character.level/xp` (Commander) while the HUD read
`ship.mastery.level/xp` (Pilot Mastery). This is not a data bug; it is a labeling gap.
Killed: syncing the two values (they are intentionally independent). Survivor: label both
tracks and show them together in the PLAYER card.

**Fix.** `app.js`: `COMMANDER LVL n` with its XP/bar plus a `PILOT MASTERY LVL n` row with
mastery XP and TP, read from `ship.mastery`. `style.css`: full-width commander bar and a
wrapping mastery row. Test: `TestProgressionTrackLabels`. The first CSS draft wrapped
mid-word and was re-captured after the fix.

**Visual proof (same promotion state, 1280x720).**
- Before: `ui-review/cycle08-after/02-after-promotion.png` — `LEVEL 1` + `0/400 XP`, no
  mastery line in the PLAYER card.
- After: `ui-review/cycle09-after/02-after-promotion.png` — `COMMANDER LVL 1` / `0/400 XP`
  and `PILOT MASTERY LVL 2` / `40/750 XP · 1 TP`, cleanly inside the card.
- Vision review: `opencode-go/gemini-4-argon` quoted both tracks and found no clipping or
  mid-word wrapping; the card grows and the scrollable ability list shifts, no structural
  break.

**Play report.** Same real browser promotion play (`play_cycle8.py cycle09-after`): scan
from 490 XP, level 1 -> 2, `levelUpSounds=1`, 24 frames/411ms, zero errors; the PLAYER card
and HUD now agree on two named tracks.

**Gates.** `python -m unittest discover` -> `Ran 1259 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5. UI task verified/finished; no game-logic or save-schema change.

**Commands.**
```text
python ui-review/play_cycle8.py cycle09-after                                # ok true
python -m unittest tests.test_cockpit_layout.TestProgressionTrackLabels       # OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py ui begin/verify/finish voidfarer --surface cockpit            # OK
python -m unittest discover                                                    # Ran 1259 OK
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 10 — Saves re-sweep: legacy saves gain the new surface landings

**Find.** A real legacy save (474 KB, seed 42, `sol_body_6` ringed giant)
persisted `landable=false`; the cockpit showed no `LAND ON SURFACE` action and no surface
operations even though generation now supports gas-world landings. Evidence:
`ui-review/cycle10-before/01-legacy-target-bottom.png`.

**Analyze.** Cycle 5 changed `GalaxyGenerator` only; `landable` is a stored body field, so
existing saves kept the old flag. The landable policy was also duplicated between galaxy
generation and any future migration. Killed: recomputing the whole galaxy (would rewrite
ownership/population). Survivor: one shared `SURFACE_LANDING_TYPES` set plus a narrow
load-time flag normalization that leaves faction/government untouched.

**Fix.** `surface.py` owns `SURFACE_LANDING_TYPES`; `galaxy.py` reads it; `engine.py` load
migration sets `landable=True` for those body types after the population backfill. Test:
legacy gas body becomes landable with its stored faction/government unchanged.

**Visual proof (same legacy save, same 1280x720 view).**
- Before: `ui-review/cycle10-before/01-legacy-target-bottom.png` — 5 action buttons, no
  `LAND ON SURFACE`.
- After: `ui-review/cycle10-after/01-legacy-target-bottom.png` — 6 buttons including
  `LAND ON SURFACE`; clean 3x2 grid.
- After landing/running: `cycle10-after/02-legacy-surface-ops.png` (`2 SITES`, ringed giant)
  and `cycle10-after/03-legacy-cloud-scoop.png` (`S2 Cloud Scoop` WORKED, +3 fuel cells).
- Vision review: `opencode-go/gemini-4-argon` quoted the added button, site count and Cloud
  Scoop state; no new clipping.

**Play report.** `python ui-review/play_cycle10.py cycle10-after` (real Edge, 1280x720,
legacy 474 KB save): loaded with `landable=true`, landed for +450 cr, ran Cloud Scoop for
+3 fuel cells (hold 15 -> 18). 25 frames/407ms, zero errors. Before run:
`cycle10-before/play-report.json` — `loadedLandable=false`, no landing action, `ok=false`.

**Gates.** `python -m unittest discover` -> `Ran 1260 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5. No schema change; the normalized flag persists on the next save.

**Commands.**
```text
python ui-review/make_legacy_save.py                                          # 474 KB seed-42 save, landable=false
python ui-review/play_cycle10.py cycle10-before                               # in HEAD worktree, no LAND
python ui-review/play_cycle10.py cycle10-after                                # LAND + Cloud Scoop, ok true
python -m unittest tests.test_frontier_depth.SurfaceOperationTest             # OK
python -m unittest discover                                                    # Ran 1260 OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 11 — Economy re-sweep: the landing survey reward is one-time

**Find.** `land_on_body` paid +450 cr on every landing at Sol F; a headless probe paid it
three times in a row, and a real leave-and-return play paid a second +450. This is a
repeatable credit farm.

**Analyze.** The landing reward was based only on body radius and had no per-body history.
Killed: a cooldown (still farmable) or blocking repeat landings (surface operations need
them). Survivor: persist a surveyed-body set on the ship, pay once, and keep repeat landings
for operations.

**Fix.** `ShipState.surveyed_bodies` (additive, default empty) with `to_dict`/`from_dict`
and `_clone_ship` support. `land_on_body` pays only on the first survey, adds the id once,
and logs `Already surveyed; no new survey reward.` on repeats. Tests: repeat reward zero,
save round-trip, legacy payload default.

**Played proof (real Edge, 1280x720, same leave-and-return sequence).**
- Before: `ui-review/cycle11-before/play-report.json` — first +450, second +450,
  credits `2,897 CR`; `ok=false`.
- After: `ui-review/cycle11-after/play-report.json` — first +450, second 0, credits
  `2,447 CR`, log `Already surveyed; no new survey reward.`; `ok=true`.
- Screenshots: `01-first-landing.png` and `02-second-landing.png` in both folders; vision
  review quoted the logs/credits and found no new clipping.
- This is a mechanics claim; the played runs and credit deltas are the proof.

**Gates.** `python -m unittest discover` -> `Ran 1261 tests ... OK`; `python aikit.py check
voidfarer` -> 5/5. Additive save field with a backward-compatible default.

**Commands.**
```text
python ui-review/probe_landing_reward.py                                      # 3x +450 before
python ui-review/play_cycle11.py cycle11-before                               # in HEAD worktree, +450 repeat
python ui-review/play_cycle11.py cycle11-after                                # +0 repeat, ok true
python -m unittest tests.test_frontier_depth.SurfaceOperationTest tests.test_models.TestModels.test_game_state_roundtrip  # OK
python -m unittest discover                                                    # Ran 1261 OK
python scripts/update_knowledge_base.py --workspace projects/voidfarer
python aikit.py check voidfarer                                                # 5/5
```

---

## Cycle 12 — Final re-sweep: zero verified improvements

No code changed. Every candidate was checked and killed on the record:

- **Flight-log top line partially clipped at 720p** — the log is a deliberately scrollable
  viewport; all visible lines are readable, older lines remain reachable, and no state or
  action is hidden. Terminal scroll behavior, not a defect.
- **Surface-operations list starts below the fold at 720p** — clicking a site marker
  auto-scrolls the selected operation row into view; the played Cloud Scoop run proves the
  path. Intended scroll behavior.
- **Faint radar axis tick text behind a body label** — decorative backdrop; body labels
  carry opaque backplates and remain legible. Cosmetic, not an information defect.
- **Dead audio cues** — a definition/call sweep finds every `play*` method has a call site;
  jump/dock/warp use optional chaining. No remaining silent cue.
- **Surface-operation reachability** — all 13 operations are offered on the seed-42 galaxy;
  old saves normalize the landable flag and the reward is one-time. No gap.
- **Combat/AI persistence** — engines disable, intent shifts and enemy telegraphs pass the
  two-turn tests and the played runs; no contradictory state found.

Final gates: `python -m unittest discover` -> `Ran 1261 tests ... OK`; `python aikit.py
check voidfarer` -> 5/5 (test, mechanics, hygiene, guidelines, secrets). Campaign complete
under the zero-verified-improvement stop rule.

## Push-window verification (origin 699379d -> HEAD)

| Window | Tip | Verification | Push |
|---|---|---|---|
| 1 -> 3 | `0f436ff` | 93 targeted tests OK; diff clean | `699379d..0f436ff` |
| 1 -> 6 | `54bf04e` | 79 targeted tests OK; diff clean | `0f436ff..54bf04e` |
| 1 -> 9 | `f979bd7` | 72 targeted tests OK; diff clean | `54bf04e..f979bd7` |
| 1 -> 12 | `f3a7f9b` | 223 targeted tests OK; one EOF blank line found | `f979bd7..f3a7f9b` |
| 1 -> 15 | `c57261f` | 106 targeted tests OK; EOF blank line carried | `f3a7f9b..c57261f` |
| 1 -> 18 | `f3e9d8a` | 193 targeted tests OK; diff clean | `c57261f..f3e9d8a` |
| 1 -> 21 | `98306d5` | 249 targeted tests OK; diff clean | `f3e9d8a..98306d5` |
| 1 -> End | `9250326` + EOF fix | 56 targeted tests OK; full suite + gate | `98306d5..HEAD` |

After the End push, the base window is re-checked read-only from the pushed origin; the
final suite and gate are green. The only code-review survivor across the windows was the
trailing blank line at EOF in this campaign file, fixed in the End window.

---

## Mechanics condensation — five-tab focus rail

**Find.** 16 first-level terminal tabs were visible at once; the rail consumed 463px and
buried the core loop among advanced systems. `condense-before/01-focus-rail.png` records the
full list.

**Fix.** Mark 11 advanced tabs `data-advanced`; default to PLAYER, SHIP, COMMERCE, FLEET,
CONTRACTS plus one `MORE SYSTEMS 11 ▾` disclosure. Deep links and `[`/`]` cycling reveal the
advanced set; collapsing an advanced tab returns to PLAYER. The 720p rail is 1px tighter per
tab and the disclosure/no-wrap footer fit.

**Proof.** `play_condense.py` before: 16 visible, no disclosure. After: 5 visible, rail
216px; MORE shows 16; FACTIONS opens `GEOPOLITICS / GALACTIC FACTIONS & CORPORATIONS`;
FEWER restores 5 and PLAYER. 25 frames/414ms, zero errors. Click-map: 163 controls
(53 visible), 0 missing, 0 duplicate; `ui_inventory.py` 1150 lines. Vision review found no
new clipping; expanded rail `scrollHeight 471 <= 473`. Suite `Ran 1262 OK`; gate 5/5.

### Second condensation — remove the duplicated PLAYER ability set

The PLAYER tab carried six ability cards with USE buttons while the bottom strip already
owned all six. `play_abilities.py` before: 6 duplicate buttons, PLAYER height 1,156px;
after: 0, height 581px, six command chips still present, Overclock fires from the strip
(surge 8, `+12 heat`). Click-map 157/47/0/0; suite `Ran 1263 OK`; gate 5/5.
Screenshots: `abilities-before/01-player-tab.png` vs `abilities-after/01-player-tab.png`
and `02-command-strip-ability.png`.

### Third condensation — SHIP rooms and module catalog

SHIP was the largest core tab at 2,390px, with the room grid and 12-row module catalog
always open. Default collapse both behind full-width `SHOW ROOMS` / `SHOW MODULES`
disclosures; open rooms to 360px so all six cards show; use a narrow two-line module row so
names keep whole words. Measured: initial SHIP 2,390px -> 932px; rooms open 1,200px with six
cards; modules open 2,521px with no horizontal overflow. Click-map 159/47/0/0;
`ui_inventory.py` 1158 lines; suite `Ran 1264 OK`; gate 5/5. Screenshots:
`ship-before/01-ship-collapsed.png` vs `ship-after/01-ship-collapsed.png`,
`02-ship-rooms-open.png`, `03-ship-modules-open.png`.

### Fourth condensation — COMMERCE broker and quantum freight

COMMERCE was 2,076px with the auto-trade broker and quantum freight expanded between the
services row and the exchange, so the first screen never showed a price row. Move both below
the market table and default-collapse them behind `SHOW AUTO-TRADE` / `SHOW QUANTUM
FREIGHT`. At narrow width the services become one compact three-card row, the broker uses a
three-column grid, the category filters wrap, and market rows drop the decorative sparkline
and category word while keeping prices, holds and trade actions.

Measured: initial COMMERCE 2,076px -> 1,004px; market table 477px with 6 rows and a visible
first row; broker open 1,154px; freight open 1,914px; both collapse back to 1,004px. Widths
291/291 content and 295/295 stack (no horizontal overflow). Click-map 161/47/0/0;
`ui_inventory.py` 1167 lines; suite `Ran 1266 OK`; gate 5/5. Screenshots:
`commerce-before/01-commerce-collapsed.png` vs `commerce-after/01-commerce-collapsed.png`,
`02-auto-trade-open.png`, `03-quantum-freight-open.png`; vision review quoted
`SHOW AUTO-TRADE`, `SHOW QUANTUM FREIGHT`, the six-row market table and the broker/freight
reveals, with no horizontal clipping. The disclosure controls sit below the market by design
and are reachable by scrolling.

### Fifth condensation — FLEET contracts and procurement

FLEET was 1,271px with mercenary contracts and the commission catalog always expanded, so
the escort manager sat below the fold. Collapse both behind `SHOW MERCENARY CONTRACTS` /
`SHOW COMMISSION`, with a live contract count. Also fixed a gap found while wiring them:
`renderFleet` returned early with zero drones, which hid the mercenary contracts even though
hiring does not require owning a drone. The mercenary rows now show the price once, use a
verb-only HIRE button, and wrap names/descriptions at whole words inside the disclosure;
the always-on escort shop keeps its compact rows.

Measured: initial FLEET 1,271px -> 957px; mercenaries open 1,295px; commission open
1,486px; collapse returns to 957px. Real Edge play dismisses the only drone: the drawer
stays open and `MERCENARY CONTRACTS 3 CONTRACTS` remains with all rows rendered. 25
frames/410ms, zero errors; no element crosses the panel edge (stack 295/295). Click-map
163/47/0/0; `ui_inventory.py` 1176 lines; suite `Ran 1268 OK`; gate 5/5. Screenshots:
`fleet-before/01-fleet-collapsed.png` vs `fleet-after/01-fleet-collapsed.png`,
`02-mercenaries-open.png`, `03-commission-open.png`, `04-zero-drones.png`; vision review
quoted the sections, readable rows, single cost and the zero-drone contracts, with no
horizontal break.

### Sixth pass — left-terminal uniformity

Measured all 16 left tabs at 1280x720. Headers ranged **46–136px**: 17px titles wrapped to
two lines, FLEET's action fell to a third row, and COMMERCE's dynamic exchange name could
make the header 128px. DEPOT squeezed item names into one word per line, EMPIRE research
names into ~80px beside cost/actions, and STORY clipped `PRECURSOR WATCH`.

Now every tab starts with the same **56px header** (tag/action row plus a one-line 13.5px
title), one 12px gold section heading, and narrow list rows that stack instead of squeezing.
DEPOT holds show full names with buttons below; EMPIRE research shows the full name and a
two-line description with cost/START/QUEUE underneath; the three story alignment chips are
full-width rows; the skills banner is compact; main intros are a complete two-line block.
The story title drops the duplicated `ACT 1: ACT I:` prefix.

Measured: headers `[56 x 16]`, spread 0; titles one line 16/16, fit 16/16. Content heights:
SHIP 932→917, COMMERCE 1,004→932, FLEET 957→831, DEPOT 359→299, CONTRACTS 654→578,
SKILLS 2,575→2,453. Play: 23 frames/412ms, zero errors, no clipped intro. Click-map
163/47/0/0; `ui_inventory.py` 1176 lines; suite `Ran 1273 OK`; gate 5/5. Screenshots:
`left-tabs-before/*.png` vs `left-tabs-after/*.png`; vision review quoted the uniform
headers, readable DEPOT/EMPIRE/STORY rows and complete intros.

### Seventh pass — advanced tabs become summary-first

The three largest left surfaces were ARSENAL 6,509px (23 upgrades + 5 chassis + 8
weapons), FACTIONS 4,594px (9 faction dossiers + 7 corporations) and CODEX 10,683px (62
milestones). Each now keeps its counts and section headers visible and hides the catalog
behind `SHOW UPGRADES` / `SHOW CHASSIS` / `SHOW ORDNANCE`, `SHOW FACTIONS` /
`SHOW CORPORATIONS`, or `SHOW MILESTONES`. CODEX also moves its category filters inside
the milestone disclosure so the button stays above the fold.

Measured initial heights: ARSENAL 6,509→473px, FACTIONS 4,594→380px, CODEX 10,683→580px.
Open states: upgrades 3,783; chassis 5,219; ordnance 6,599; factions 3,325; corporations
4,669; milestones 10,787. All re-collapse exactly. Quests/AI/messages cards share 96/200/168
minimum heights; message choice descriptions clamp to two lines. CODEX summary is a 2×2 grid
and career stats show three full rows (144px scroll box). Play: 23 frames/401ms, zero
errors. Click-map 169/47/0/0; `ui_inventory.py` 1195 lines; suite `Ran 1277 OK`; gate 5/5.
Screenshots: `advanced-after/*.png`; vision review approved the collapsed/open states and
the card rhythm, and the codex stats row fix was re-reviewed.

### Eighth pass — HUD label polish

Two known 1280x720 defects remained after the left-panel work: the radar scale label was
centered over a short bar and started under the left drawer (rendering `ANGE SCALE`), and
the Battle Focus chip ellipsized to `Battle Fo...` in its 70px name column. The label center
is now clamped to the map inset plus half the text width, and the chip displays the short
`Focus` label while its title keeps `Battle Focus`.

Measured: label left edge 500.3px vs map inset 478.3px; all six chip names 70/70px with
`clipped: false`; 24 frames/410ms, zero errors. The 16-tab sweep still reports 16/16 56px
headers and one-line titles, ok true. Suite `Ran 1279 OK`; click-map 169/47/0/0;
`ui_inventory.py` 1195 lines; gate 5/5. Screenshots:
`polish-before/01-cockpit-before.png` vs `polish-after/01-cockpit.png`; vision review quoted
`ANGE SCALE`/`Battle Fo...` before and `RANGE SCALE [ 10 AU ]`/`Focus` after, with no new
clipping.

### Ninth pass — preset-first reactor and one-click academy power step

The always-visible reactor strip was the densest mechanic: four manual sliders, four
doctrine buttons, a second BALANCED/SPEED/SCIENCE row and an APPLY ROUTE button that was
not visible at 1280×720. The academy's power step told players to adjust the sliders, but
only `route_power` advanced it — choosing a doctrine preset did nothing. The strip now
keeps heat, the four doctrine presets and the output line visible; the sliders and
secondary presets sit behind `SHOW FINE TUNE`. `set_reactor_mode` now advances the power
step once with its credits/XP, and the hint names `ECONOMY` or `OVERDRIVE`.

Measured: default panel 275→242px; visible sliders 4→0; FINE TUNE opens to 305px and
closes back to 242px. Play: academy 3/6, click ECONOMY → 4/6, credits 2,550→2,750 (+200),
XP 230→310 (+80), one academy log; a second mode change paid nothing. 25 frames/408ms,
zero errors. Suite `Ran 1282 OK`; click-map 170/40/0/0; `ui_inventory.py` 1198 lines; gate
5/5. Screenshots: `reactor-before/01-reactor.png` vs `reactor-play-after/01-preset-first.png`
and `03-fine-tune-open.png`; vision review called the after state meaningfully simpler with
no layout break.

### Tenth pass — four core combat actions

The hostile-intercept card exposed nine main actions plus four subsystem-target buttons at
once (13 controls) and reached 713px at 1920×1080; at 1280×720 the capped card pushed the
lower controls, including the new disclosure, below its scroll edge. The card now keeps
`FIRE LASER ARRAY`, `SHIELD OVERCHARGE`, `EVASIVE BURN` and `FLEE SECTOR` visible; drone,
PDC, boarding, gambit and subsystem targeting sit behind `SHOW MORE TACTICS`. The duplicate
generic `TARGET SUBSYSTEM` button is removed (the engine action remains). At heights under
800px the decorative combat canvas is hidden so the core controls fit.

Measured: 1920 card 713→564px, visible controls 13→5; 1280×720 card 500→442px with no
offscreen actions; `SHOW MORE TACTICS` reveals 148px of secondary controls. Fire still hits
(enemy hull 200→183); 25 frames/~403ms, zero errors. Suite `Ran 1284 OK`; click-map
170/40/0/0; `ui_inventory.py` 1199 lines; gate 5/5. Screenshots:
`combat-before/01-combat-collapsed.png` vs `combat-after/01-combat-collapsed.png`,
`02-combat-more-tactics.png`, and `combat-after-720/01-combat-collapsed.png`; vision review
quoted the before 13 controls and the after four core actions + disclosure, confirmed the
720p fit, and noted only a pre-existing canvas label collision.

### Eleventh pass — unlocked-first abilities and a full academy play

The powers strip still showed six chips while two were locked, and the onboarding path had
not been played end to end after the reactor/combat work. The strip now renders four
unlocked chips (`Overclock`, `Repair`, `Focus`, `Science`) plus `SHOW LOCKED 2`; opening it
reveals `Diplomacy` and `Trade` and becomes `HIDE LOCKED 2`. Arrival and anomaly cards were
also moved below the cadet ribbon so they cannot cover the hint or graduation text.

A fresh save was played through all six academy steps with real Edge controls:

| Step | Control | Result |
|---|---|---|
| 1 | `TRANSIT & ORBIT` Sol B | 0→1, +197 cr, 80 XP |
| 2 | `SCAN` | 1→2, +350 cr, 230 XP |
| 3 | `ECONOMY` preset | 2→3, +200 cr, 310 XP |
| 4 | `BUY 1` at Sol A | 3→4, +240 cr, 455 XP |
| 5 | `COMMISSION SCOUT` | 4→5, 105 XP |
| 6 | `HYPERSPACE JUMP` | 5→6, graduated, +1,900 cr, 740 XP |

Final: all six steps completed, `ACADEMY GRADUATION: Flight Wings Conferred!`, +2,737
credits, +740 XP, 24-26 frames/~407-417ms, zero errors. Suite `Ran 1286 OK`; click-map
171/39/0/0; `ui_inventory.py` 1203 lines; gate 5/5. Screenshots:
`academy-play/00-academy-start.png` through `07-step-jump.png`; vision review quoted the
four chips, the two locked chips and each milestone through graduation, and the arrival/
anomaly overlap it flagged was fixed by the top offset and re-captured.

### Twelfth pass — the target dossier looks before it tells

The radar's selected-target card always showed the 11-field stat grid first, then resources
and salvage, then up to 11 actions. At 1280×720 the card is 249px tall but its content was
314–507px, so every state clipped mid-grid and the primary actions (including `BOARD
DERELICT`) sat below the internal scroll edge. System, captain and open-space targets also
rendered eight or more empty `--` fields.

The dossier now keeps identity, distance, description, four summary chips and the primary
actions above the fold. Full statistics, resources, salvage strategy and the transit plan
move behind `SHOW DETAILS`; scoop/rebuild/relief/restore move behind `SHOW MORE ACTIONS`,
which appears only when one of them applies. The distance line drops the target's own orbit
radius to a tooltip so long names no longer collide with it.

Measured: every collapsed state now fits exactly (card scrollHeight 246 = client height,
zero offscreen actions). Summary examples: station `GRAV 0.50 g / TEMP 21 C / HAB 82%
OPTIMAL / POP 3.2M` with `IN ORBIT / QUANTUM TRANSIT / CLEAR`; system `CLASS K-type / SEC
90% / LINKS 4 / FACTION Sol Coalition` with `EXECUTE HYPERSPACE JUMP`; captain `HULL
120/120 / DMG 10 / CREDITS 3554 cr / STATUS independent` with `HAIL SHIP`. SHOW DETAILS
reveals 11 stats and the derelict panel (risk 38%→19% on CAUTIOUS); the scoop giant exposes
`SHOW MORE ACTIONS` → `SCOOP FUEL`. Quantum transit still executes (fuel 60→54, orbit
`sol_body_5`). Play: 25 frames/403ms, zero errors. Suite `Ran 1289 OK`; click-map
173/39/0/0; `ui_inventory.py` 1210 lines; gate 5/5. Screenshots:
`target-before/01-station.png`, `target-before/03-derelict.png` vs
`target-after/01-station.png`, `03-derelict.png`, `03b-derelict-details.png`,
`04-system.png`, `08b-scoop-more.png`; vision review confirmed the actions are above the
fold and flagged only the long-name/distance collision, fixed before the final play.

### Thirteenth pass — surface operations stop burying the action

Landing used to open a 714px surface panel inside the 246px target card: a 205px map
first, then nine 46–51px operation rows. The map filled the card viewport, so **no
operation name, reward or RUN button was visible without scrolling**, and the card grew to
921px of scroll content.

The surface panel now leads with a compact `S1`–`S9` site strip and one selected-operation
card: name, two-line description, risk, rewards and `RUN`/`WORKED`. The map and the full
catalog sit behind `SHOW SURFACE MAP` and `SHOW ALL OPERATIONS (9)`; both preserve their
open state across refreshes, and opening one scrolls its HIDE control plus the revealed
content into view. The first unworked operation is selected automatically, used sites are
marked, and the panel is signature-guarded so polling does not rebuild it under a click.

Measured: default surface panel **714 → 188px**, fully inside the 246px card with `S1
Surface Survey`, `10%`, `+180 CR · +30 RES` and an enabled RUN. Map open 396px with the
full 159px canvas, `SURFACE SCAN // LAVA WORLD · 9 SITES` and the RUN ABOVE hint visible;
catalog open 644px with HIDE ALL OPERATIONS and four complete S1–S4 rows usable without
scrolling. Real play: survey succeeded for +180 credits (2,385→2,565), `1/9 WORKED`, S1
marked worked, `WORKED` disabled, S2 restores an enabled RUN; 24 frames/415ms, zero
errors. Suite `Ran 1292 OK`; click-map 173/39/0/0; `ui_inventory.py` 1214 lines; gate 5/5.
Screenshots: `surface-before/01-surface-ops.png` vs `surface-after/01-surface-ops.png`,
`surface-play/02-ruin-selected.png`, `03-map-open.png`, `04-all-operations.png`,
`05-after-run.png`, `06-next-site.png`; vision review found no new clipping, only the
pre-existing radar-label and flight-log top-line slices.

### Fourteenth pass — EMPIRE becomes a headline deck

EMPIRE was 2,665px: research 573px, outposts 210px and faction leaders 1,733px, all open at
once. The nine leader rows each carried six or seven diplomacy buttons, squeezing names
into a 60px column and breaking descriptions into 6–11-character lines. The tab now opens
with three section headlines and live counts (`5 PROJECTS`, `NONE`, `9 LEADERS`), a
one-line status summary, and `SHOW RESEARCH` / `SHOW OUTPOSTS` / `SHOW FACTIONS`
disclosures. Diplomacy rows became two-column cards (identity + standing, actions wrapped
below), and outpost build yields wrap whole-word.

Measured: EMPIRE **2,665 → 402px**, fitting the 473px left-terminal viewport with no
scroll. Research opens to 958px with five readable rows; START sets `Advanced Coolant
Loops — 0/120 points` with `Banked: 500` and logs the research action. Outposts open to
540px with the full `+3 credits · +1 titanium per tick` Mining Outpost yield. Factions open
to 2,169px with nine readable leader cards and six actions each. Play: 25 frames/407ms,
zero errors. Suite `Ran 1295 OK`; click-map 176/39/0/0; `ui_inventory.py` 1224 lines; gate
5/5. Screenshots: `left-tabs-before/empire.png` vs
`empire-play/01-empire-default.png`, `02-research-open.png`, `03-research-started.png`,
`04-outposts-open.png`, `05-factions-open.png`; vision review confirmed the default fits and
the reveals are readable, with no new layout breaks.

### Fifteenth pass — SKILLS becomes six training rows

SKILLS was 2,471px: six large skill cards (922px), eight perk nodes (1,108px) and a relic
section, with only the first TRAIN action reachable without scrolling. The tab now shows
six one-line rows (`name`, `RANK 1/10`, `TRAIN 1 SP`) with progress bars, plus two headline
cards: `PERKS` (`1 TP`, `8 perks · 0 taken`) and `RELICS` (`0 RELICS`, `Fleet bonuses`).
Perk branches and the relic grid sit behind `SHOW PERKS` / `SHOW RELICS`; descriptions stay
on the training-row tooltips. Perk nodes stack their title, description and unlock button
at the docked width.

Measured: SKILLS **2,471 → 481px**, fitting the 482px viewport exactly with no scroll and
all six TRAIN buttons visible. Training Piloting with 3 points updates `RANK 1/10` →
`RANK 2/10`, points `3` → `2`, and logs `Trained Piloting to rank 2.`; 25 frames/401ms,
zero errors. Perks open to 1,635px with eight readable nodes; relics open to 568px with
the empty-state message. Suite `Ran 1299 OK`; click-map 178/39/0/0; `ui_inventory.py`
1230 lines; gate 5/5. Screenshots: `left-tabs-before/skills.png` vs
`skills-play/01-skills-default.png`, `02-after-train.png`, `03-perks-open.png`,
`04-relics-open.png`; vision review confirmed the fit, the rank/points update and readable
perk/relic reveals.

### Sixteenth pass — CREW becomes cash flow plus officer headlines

CREW was 1,319px, almost all in a roster view whose two 200px officer cards squeezed names
into one-word columns, flattened morale bars into slivers and pushed the second officer
below the fold. The tab now keeps the cash-flow row, an `ACTIVE CREW` count and one
headline row per officer (`Imani Vale · engineer · S3 · NO STATION`) plus
`SHOW ROSTER (2)` and `SHOW RECRUIT & ROLES (6)` disclosures. The full roster and shore
leave sit behind the first; bonuses and recruitment roles behind the second. Detailed
officer cards stack identity, a full-width morale bar and the station/actions row; role
rows give the description the full width with cost and RECRUIT beneath.

Measured: CREW **1,319 → 343px**, fitting the 473px viewport with both headlines and both
disclosures visible. Roster open 784px with two readable cards; drilling Rook Calder
raises skill 2→3, spends 2,000→1,600 credits and logs the drill. Roles open 1,006px with
six readable rows. Away teams stay behind the `AWAY TEAMS` view tab (709px). Play: 24
frames/417ms, zero errors. Suite `Ran 1302 OK`; click-map 180/39/0/0; `ui_inventory.py`
1237 lines; gate 5/5. Screenshots: `skills-verify-tabs/crew.png` vs
`crew-play/01-crew-default.png`, `02-roster-open.png`, `03-after-drill.png`,
`04-roles-open.png`, `05-away-view.png`; vision review confirmed the default fit and
readable roster/role reveals.

### Seventeenth pass — QUESTS counts and claimable rewards lead the tab

QUESTS was the tallest right-terminal tab at 1,172px: a roughly 920px active-quest
section with seven full cards (44–165px) followed by a 77px completed section. At
1280×720 the 473px viewport showed one card and a clipped second card; a completed
contract's `CLAIM REWARD` button could sit below the fold with no count or shortcut above
it. The tab now opens with three live counts (`6 ACTIVE`, `0 COMPLETED`, `0 READY TO
CLAIM`), a `READY TO CLAIM` headline and one compact claim card per completed contract
(title, reward, progress, `CLAIM REWARD`). The full active and completed logs sit behind
`SHOW ACTIVE QUESTS (n)` / `SHOW COMPLETED QUESTS (n)`, whose labels and `aria-expanded`
stay in sync with live counts.

Measured with the same harness, save and 1280×720 viewport: QUESTS **1,172 → 308px**
(339px with one ready-to-claim card), fitting the 473px viewport with both disclosures
visible; all other 15 tabs unchanged. Active log open 1,246px with six readable cards and
`HIDE ACTIVE QUESTS (6)`; completed log open 445px with the empty-state message. Real
play: claiming `Cartographic Stellar Sweep` paid +1,100 cr (2,000 → 3,100), moved the
summary to `6 ACTIVE 1 COMPLETED 0 READY TO CLAIM`, showed the empty claim hint, logged
`Claimed Cartographic Stellar Sweep: +1100 cr, +320 XP`, and the completed log then showed
the relic; 25 frames/402ms, zero errors. Suite `Ran 1304 OK`; click-map 182/39/0/0;
`ui_inventory.py` 1245 lines; gate 5/5. Screenshots: `quests-unified-before/quests.png` vs
`quests-unified-after/quests.png`, `quests-play/02-active-quests.png`,
`03-completed-empty.png`, `04-after-claim.png`, `05-completed-after.png`; vision review
confirmed the two-card before stack versus the counts/claim surface and both readable
reveals, with no new clipping or overlap.

### Eighteenth pass — AI CAPTAINS becomes a count strip plus captain headlines

AI CAPTAINS was 1,131px: five roughly 200px cards, each carrying description, system/trust/
standing, cargo and up to five action buttons. At 1280×720 only the first card and part of
the second fit, so trust/standing for three captains and their HAIL/BUY/SELL/HIRE/ALLY
paths sat below the fold. The tab now opens with a `CAPTAINS IN RANGE` head and live count
(`5 CAPTAINS · 0 HIRED · 0 ALLIED`), one two-line headline per captain (name + archetype,
then system · trust · standing · status), and `SHOW CAPTAIN DOSSIERS (5)`. The full
dossiers and actions sit behind the disclosure, whose label and `aria-expanded` track the
live count; the toggle hides when no captains are in range.

Measured with the same harness, save and 1280×720 viewport: AI CAPTAINS **1,131 → 474px**,
fitting the 474px viewport with all five headlines and the disclosure; all other 15 tabs
unchanged. Dossiers open 1,532px with five cards and 21 visible actions. Real play: HAIL
raised Captain Vega's trust 37 → 39 and standing 9 → 10, the headline changed to `TRUST
39`, the log recorded `Quantum link trust increased.`, and the dossiers stayed open; 25
frames/413ms, zero errors. Suite `Ran 1306 OK`; click-map 183/39/0/0; `ui_inventory.py`
1250 lines; gate 5/5. Screenshots: `ai-unified-before/ai.png` vs `ai-unified-after/ai.png`,
`ai-play/01-ai-default.png`, `02-dossiers-open.png`, `03-after-hail.png`; vision review
confirmed the count/headline deck, the readable five-card reveal, the live trust update,
and no new clipping or overlap.

### Nineteenth pass — MESSAGES becomes an inbox count plus message headlines

MESSAGES was 842px: three cards of 168–406px each rendered the full body and branch
choices at once, so the 473px viewport showed only the first message and the other
senders/choices sat below the fold. The tab now opens with an `INBOX` head and live count
(`3 MESSAGES · 3 UNREAD`), one two-line headline per message (subject, then sender · tick ·
status), and `SHOW MESSAGE ARCHIVE (3)`. Full bodies, `MARK READ` and branch choices live
behind the disclosure; unread rows carry the amber accent and the label/`aria-expanded`
track the live count.

Measured with the same harness, save and 1280×720 viewport: MESSAGES **842 → 321px**,
fitting the 473px viewport with all three headlines and the toggle; all other 15 tabs
unchanged. Archive open 1,089px with three cards, three choice buttons and three `MARK
READ` controls. Real play: choosing `Decode the signal` resolved the Precursor tree
message (read + `RESOLVED`), appended the `Decryption complete` follow-up (4 messages, 3
unread), logged `Branch chosen: Decode the signal...`, kept the archive open, and the
badge tracked live unread; 25 frames/402ms, zero errors. Suite `Ran 1308 OK`; click-map
184/39/0/0; `ui_inventory.py` 1255 lines; gate 5/5. Screenshots:
`messages-unified-before/messages.png` vs `messages-unified-after/messages.png`,
`messages-play/01-messages-default.png`, `02-archive-open.png`, `03-after-choice.png`;
vision review confirmed the inbox deck, the readable archive reveal, the live
resolved/unread update, and no new clipping or overlap.

### Twentieth pass — header badges reach the 12px readability floor

A fresh story capture at 1280×720 reported `tiny 1`: `TARGET: SOL` measured 11px. The
shared header rule `.tab-content > .panel-header > button, … > .badge-arch` set 11px, so
market `HIGH_TECH` and codex `0 / 62 CLAIMED (0%)` shared the same sub-floor size. The
rule now uses 12px while keeping `min-height: 22px`, padding and the 56px header layout.

Measured: story, market and codex captures move from `tiny 1` to `tiny 0` with `hscroll 0`
and zero errors; all three badges remain on the tag row with no wrap or overflow. Suite
`Ran 1309 OK`; `ui_inventory.py` 1255 lines; gate 5/5. Screenshots:
`story-check/short-story.png` (before) vs `badge-after-story/short-story.png`,
`badge-before-market/short-market.png` vs `badge-after-market/short-market.png`,
`badge-before-codex/short-codex.png` vs `badge-after-codex/short-codex.png`; vision
review confirmed the larger badges stay legible with no layout shift.

### Twenty-first pass — FLEET docked drone and escort text stops clipping

A 16-tab sweep at 1280×720 (one browser session, default save) found nine clipped text
nodes, all in FLEET. The drone card's three-column ledger grid left about a 103px text
column, so `Mining Drone Alpha`, `MINING // SOL [HARVESTING]` and the stats line ellipsized;
the always-on escort shop rendered `Aegis Escort Co...` and truncated descriptions. The
docked drone card now stacks its name, sub, stats and yield full width with `REFIT` and
`DISMISS` on a final row, and `#escortShopGrid` joins the wrapping procurement override.

Measured: the sweep moves from **9 clipped text nodes -> 0** across all 16 tabs with
`tiny 0`, `hscroll 0` and zero errors. FLEET grows 831 → 877px because the drone identity
and actions stack, but every line is readable and both actions stay visible; the >1599px
layout is unchanged. Suite `Ran 1311 OK`; `ui_inventory.py` 1255 lines; gate 5/5.
Screenshots: `fleet-clip-check/short-fleet.png` vs `fleet-drone-after/short-fleet.png`,
`fleet-bottom-check/short-fleet-bottom.png` vs `fleet-bottom-after/short-fleet-bottom.png`;
vision review confirmed the full drone card and wrapped escort rows, with no new clipping.

### Twenty-second pass — SHIP status wraps and the viewport matrix goes clean

The 16-tab sweep was extended to the rest of the G-011 matrix: 1280×720@1,
1280×720@2 (200% scaling), 1920×1080@1 and 3840×2160@1. At 1920 and 4K the SHIP interior
header rendered `CORVETTE SCOUT //...`, hiding `3/6 STAFFED`, because
`.ship-interior-status` capped at `12em` with nowrap and an ellipsis (1280 hides the line
entirely, which is why the minimum viewport never showed it). The status now wraps
naturally with no cap, so the header grows a second line instead of dropping information.

Measured across all 16 tabs: **1280×720@1 — none; 1280×720@2 — none; 3840×2160@1 —
none; 1920×1080@1 — SHIP 1 → 0**, with the only remaining findings being three intentional
FLEET ellipses (the secondary drone stats line and two tooltip-backed escort
descriptions). `tiny 0`, `hscroll 0` and zero page/console errors at every size. Suite
`Ran 1312 OK`; `ui_inventory.py` 1255 lines; gate 5/5. Screenshots:
`ship-desktop-check/desktop-ship.png` vs `ship-status-after/desktop-ship.png`; vision
review quoted `CORVETTE SCOUT // 3/6 STAFFED` on its own line with no header collision.
