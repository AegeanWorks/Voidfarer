# VoidFarer: Implicit State Machines

This document is the audit, verification, decision record and operator guide for the
state machines that VoidFarer encodes in fields, presence checks and branch conditions.
The canonical machine data lives in [`voidfarer/state_machines.py`](../voidfarer/state_machines.py);
this page explains what was found and why the registry exists.

## Method

1. Read the domain models (`voidfarer/models.py`) and the transition functions in
   `voidfarer/engine.py`, `server.py`, `cli.py`, `storage.py` and `reactor.py`.
2. Probed the suspect gates against a live engine (`ui-review/probe_gates.py`) instead
   of trusting the docstrings.
3. Cross-checked the three enforcement layers: engine action gate, HTTP POST allowlist,
   CLI/REPL allowlist.
4. Added failing-first tests in `tests/test_state_machines.py` for every changed rule.

## Inventory

`blocks` is the machine's own contract: `time` = holds the simulation tick, `flight` =
holds flight/exploration actions, `http`/`cli` = the outer surface gate. Presence in the
owner field is often the state (for example, `active_combat` being set means "engaged").

| # | Machine | Owner | States | Blocks | Evidence |
|---|---|---|---|---|---|
| 1 | `clock` | `time.is_paused` | running, paused | — | models.py:2127, engine.py:10334 |
| 2 | `simulation` | `tick` precedence | running, blocked_decision, blocked_pirate, destroyed | time | engine.py:9363 |
| 3 | `onboarding` | `ship.tutorial` | active, completed, skipped, inactive | — | models.py:739, engine.py:957 |
| 4 | `campaign` | `ship.story` | chapter_active, chapter_skipped, completed | — | models.py:960, engine.py:7495 |
| 5 | `travel` | `ship.travel` | idle, sublight, quantum | flight (body services) | models.py:1037, engine.py:2297 |
| 6 | `void` | `ship.void_traversal` | idle, traversing | flight | models.py:1075, engine.py:1358 |
| 7 | `combat` | `active_combat` | idle, engaged, defeated | flight | models.py:503, engine.py:5977 |
| 8 | `boarding` | derived from combat + crew | unavailable, available, resolved | — | engine.py:6168 |
| 9 | `anomaly` | `active_anomaly` | idle, pending | flight | models.py:281, engine.py:6753 |
| 10 | `pirate` | `active_pirate` | idle, pending | time, flight, http, cli | models.py:1176, engine.py:6830 |
| 11 | `customs` | `active_customs` | idle, pending | flight, http, cli | models.py:1209, engine.py:6906 |
| 12 | `decision` | `pending_decision` | idle, pending | time, flight, http, cli | models.py:1137, engine.py:9259 |
| 13 | `research` | `GameState.research` | idle, active, queued, finished | — | models.py:1378, engine.py:2948 |
| 14 | `contracts` | offers/active/completed | offer, active, ready_to_claim, claimed | — | models.py:561, engine.py:7242 |
| 15 | `away` | `ship.away_missions` | idle, outbound | — | models.py:1785, engine.py:4318 |
| 16 | `outpost` | `GameState.outposts` | operational, damaged, ruined | — | models.py:1408, engine.py:3310 |
| 17 | `reactor` | `ship.reactor` | nominal, overheated, critical, breached | — | models.py:1280, reactor.py:49 |
| 18 | `messages` | `GameState.messages` | unread, read, resolved | — | models.py:439, engine.py:4509 |
| 19 | `fleet` | drones/escorts | harvesting, patrolling, idle, escorting, destroyed | — | models.py:311, models.py:1456 |
| 20 | `crew` | `ship.crew` | active, injured, away, assigned | — | models.py:1647, crew.py:263 |
| 21 | `save` | `StorageManager` | clean, backup_recovered, corrupt_quarantined, missing | — | storage.py:80-119 |
| 22 | `automation` | trade/quantum automation | off, armed, cooldown | — | models.py:1727, models.py:1757 |
| 23 | `diplomacy` | `wars` + pacts | peace, war, ended | — | models.py:1549, engine.py:7968 |
| 24 | `codex` | `GameState.codex` | unclaimed, claimed | — | models.py:2265, engine.py:2826 |

### Cross-machine precedence

- `tick()`: `pending_decision` → `active_pirate` → `hull <= 0` → simulation.
- `_action_lock_reason()` before ADR-214: decision → pirate → customs → void.
- HTTP POST: decision → customs → pirate (each has its own path allowlist).
- CLI: decision → pirate → customs (each has its own command allowlist).
- REPL: the same three sets in terminal vocabulary.

## Findings (verified)

### F1 — Flight actions bypass combat and anomaly (high)

`_action_lock_reason()` did not mention combat or anomaly. Live probe:

```
combat orbit:  (True, 'Now in orbit around Sol System B ...')
combat travel: (True, 'Engaged sublight drive ...')
anomaly orbit: (True, 'Now in orbit around Sol System C ...')
anomaly travel:(True, 'Engaged sublight drive ...')
```

`jump()` already blocked both explicitly, so the same state produced different answers
depending on the action. This is the clearest UX/DX/AX defect: an agent can "escape" a
fight or an anomaly by using `orbit`/`travel` instead of `flee`.

### F2 — `void_dive` bypasses the outer blockers (high)

`void_dive()` checked combat, anomaly, travel and void, but not `pending_decision`,
`active_pirate` or `active_customs`, and did not call `_action_lock_reason()`. A decision,
toll or customs stop could therefore be skipped by diving into the Hollow Between.

### F3 — Three hand-maintained gate copies (medium)

The engine, HTTP server and CLI each encode the decision/pirate/customs gates, with
different strictness (the engine blocks flight; HTTP/CLI block nearly everything). There
was no single list to update and no test that the three agree. Server and CLI sets are
intentionally stricter, so the fix is a canonical registry plus tests, not a forced merge.

### F4 — Current state is scattered (medium, AX)

An agent that wants to know "what is happening now?" must know about `active_combat`,
`active_pirate`, `active_customs`, `active_anomaly`, `pending_decision`, `ship.travel`,
`ship.void_traversal`, `tutorial`, `story`, `research`, `away_missions`, `wars`,
`trade_automation`, `quantum_automation` and the hull check. `/api/state` exposed the raw
fields but no canonical summary or transition contract.

### F5 — Research switches silently discard progress (low, UX)

`choose_research()` reset `progress` to 0 when switching projects and returned only
"Research directed toward X". The player lost banked points without being told.

### F6 — Tick blocking is narrower than flight blocking (documented, deferred)

Decision and pirate block `tick()`; customs, anomaly and combat do not. This is now
recorded per machine (`blocks_time`) and in `simulation`'s note. Changing it would alter
gameplay pacing and combat cooldown behavior, so it is a product decision, not a bug fix
in this pass.

### F7 — Save recovery is invisible (documented, deferred)

`StorageManager.load()` silently falls back to `.bak` and quarantines corrupt primaries.
The caller cannot tell which path ran. A `load_report` would help DX/AX but changes the
storage API; proposed for a later pass.

## Proposals and decisions

| ID | Proposal | UX | DX | AX | Risk | Decision |
|---|---|---|---|---|---|---|
| P1 | Canonical machine registry + runtime inspector | consistent vocabulary | one contract, tested | query states/transitions | low | **implemented** |
| P2 | `GET /api/state-machines`, snapshot `state_machines`, CLI `state-machines [--json]` | one situation line | discoverable | machine-readable | low | **implemented** |
| P3 | Put combat + anomaly in the engine flight gate; make `void_dive` use it | no nonsensical escapes | one gate | predictable allowed actions | medium | **implemented** |
| P4 | Report discarded research points on switch | no silent loss | honest transition | accurate result | low | **implemented** |
| P5 | Align `tick` with customs/anomaly/combat | a pause is a pause | one precedence rule | fewer exceptions | high (pacing) | deferred |
| P6 | `StorageManager.load_report()` | recovery is visible | debuggable saves | can detect fallback | medium (API) | deferred |
| P7 | Cockpit situation chip | always-visible mode | one consumer | same payload | medium (layout) | deferred; snapshot already carries it |

The selected proposals are the ones that remove verified incorrect behavior or add a
read-only contract. P5-P7 are recorded so the next pass does not re-discover them.

## Implementation

### Registry and inspector

`voidfarer/state_machines.py` exposes:

```python
from voidfarer.state_machines import catalog, inspect_state, situation

catalog()          # static registry + surface_gates + notes
inspect_state(s)   # every derivable machine's current state/detail/flags
situation(s)       # {summary, primary, blocking_flight, blocking_time, states}
```

The inspector is read-only and never mutates state.

### REST

```text
GET /api/state-machines
  -> {ok, schema, machines[], surface_gates, notes, current{}, situation{}}
GET /api/state
  -> data.state_machines: {summary, primary, blocking_flight, blocking_time, states}
```

### CLI

```text
python -m voidfarer.cli state-machines
python -m voidfarer.cli state-machines --json
```

`state-machines` is in the always-allowed set, so it still works while a decision,
pirate or customs gate is blocking everything else.

### Engine gate

`_action_lock_reason()` now covers decision, pirate, customs, **combat**, **anomaly** and
void. `void_dive()` calls it after its own specific checks. `combat_action()` is unchanged,
so combat maneuvers remain available during an engagement.

## Verification

- `python -m unittest tests.test_state_machines -v` → **21 tests, OK**.
- `python -m unittest discover` → **1333 tests, OK** (see the delivery commit).
- `python aikit.py check voidfarer` → **5/5** gates.
- Live gate probe before the fix: combat/anomaly `orbit` and `travel` returned `True`;
  after the fix the same calls return `False` with the machine-specific message.
- Existing decision/pirate/customs server and CLI gates are unchanged.
- The cockpit is untouched; `python tools/ui_browser.py --viewports short --scenario
  cockpit` remains clean (no static files changed).

## Deferred follow-ups

1. **Tick precedence (P5).** Decide whether customs/anomaly/combat should freeze time.
   If yes, add the blockers to `tick()` and retune combat cooldowns/tests in one change.
2. **Save diagnostics (P6).** Add `load_report` without changing `load()`'s return type,
   then surface "backup recovered" in the cockpit and CLI.
3. **Cockpit chip (P7).** If the snapshot `situation` proves insufficient, render one
   status chip from it; the payload is already stable.
