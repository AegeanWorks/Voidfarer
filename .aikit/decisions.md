# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.


### ADR-001: Architecture, Storage Schema, and Zero-Dependency Simulation Engine for VoidFarer
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: Autonomous deep-space exploration and fleet simulations require deterministic procedural generation, fast state transitions, crash-safe persistence, and multi-interface usability (both CLI and Web HUD) without third-party runtime package dependencies.
- **Decision**:
  1. Build core engine using Python 3.10+ standard library exclusively (`math`, `random`, `dataclasses`, `http.server`, `json`, `pathlib`).
  2. Implement frozen immutable DTO models (`models.py`) with explicit schema validation.
  3. Ensure power-loss safe atomic disk persistence with shadow backup (`.bak`), quarantine on corruption, and fsync flushing (`storage.py`).
  4. Provide dual interfaces: an ANSI-colored CLI terminal REPL (`cli.py`) and a zero-dependency local HTTP REST daemon with an HTML5 Canvas holographic cockpit Web HUD (`server.py`, `static/`).
- **Consequences**: Zero external pip dependencies required; instant cold-start startup; sub-second test execution; full multi-platform compatibility across Windows, Linux, and macOS.

### ADR-002: Autonomous Fleet Assets, Modular Arsenal Upgrades, and Hostile Tactical Intercepts
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: The simulation engine lacked long-term player progression, modular equipment slots, autonomous fleet scaling, and interactive combat encounters during low-security star system transit.
- **Decision**:
  1. Introduce `FleetDrone` models allowing players to commission, deploy, and harvest yield from autonomous mining, recon, and escort drones across star systems.
  2. Implement `ShipUpgrade` modular hardware slots (engines, shields, sensors, weapons, cargo) with concrete mathematical stat bonuses to fuel efficiency, shield capacitance, scan bounties, and hold capacity.
  3. Add `CombatEncounter` mechanics with tactical choices (laser strike, shield absorption, evasive burn, emergency jump) governed by power routing.
  4. Enhance REPL with multi-threaded `serve` daemon launch, command aliases, and tolerant input handling.
- **Consequences**: Fulfills the deep-space fleet simulator vision with layered meta-progression, rich tactical gameplay, and seamless concurrent web and terminal operation without introducing any external dependencies.

### ADR-003: Behavioral Attention Mechanics, Variable-Ratio Reinforcement, Zeigarnik Task Loops, and Loss Aversion
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: Following an academic literature review on addiction and attentional psychology (Reward Prediction Error, operant conditioning schedules, near-miss effects, Zeigarnik cognitive tension, loss aversion, and self-determination theory), the core simulation needed retention loops that create genuine engagement and agency without deceptive dark patterns.
- **Decision**:
  1. Integrate Variable-Ratio Precursor Relic drops with Near-Miss sensor detection: Scans roll for ancient artifacts across 4 rarity tiers. Near-miss rolls generate distinct acoustic resonance and a persistent scanner boost for the subsequent sweep (Schultz 1997, Clark et al. 2009).
  2. Implement an active Sector Bounties board leveraging the Zeigarnik Effect (1927) and Goal-Gradient hypothesis: Fulfilling an active task immediately draws a new assignment, ensuring an incomplete progress bar remains active in the player's cognitive queue.
  3. Introduce Expedition Jump Streaks leveraging Prospect Theory Loss Aversion (Kahneman & Tversky 1979): Each safe hyperlane jump grants a cumulative +15% multiplier (up to x2.50) to rewards, but fleeing from hostile combat resets the streak to 1, raising physiological arousal and decision weight.
  4. Implement Pilot Mastery and Specialization Trees grounded in Self-Determination Theory (Ryan & Deci 2000): Career XP unlocks talent perk trees (`void_cartographer`, `dreadnought_tactics`, `swarm_commander`, `quantum_smuggler`) satisfying player competence and autonomy.
  5. Add Tactical Combat Combo Counters and Critical Overcharge to induce Flow State (Csikszentmihalyi 1990) with procedural Web Audio synthesis for kinesthetic juice (Swink 2008).
- **Consequences**: Player engagement is deeply reinforced through cognitive resonance, tangible meta-progression, and responsive sensory feedback while maintaining 100% standard library compliance and test execution in <1.0s.

### ADR-004: Cognitive Scaffolding, Situated Cadet Flight Academy, and Narrative Transportation Space Opera Campaign
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: The game's multi-layered simulation systems (orbital flight, sensor scanning, reactor power distribution, station commerce, autonomous fleet drones, tactical corsair encounters, pilot talents) presented an intimidating cognitive barrier to entry for novice players, risking early drop-off (Sweller's Cognitive Load Theory). Furthermore, purely mechanical systems lacked emotional immersion and extrinsic-to-intrinsic meaning (Green & Brock's Narrative Transportation Theory, Loewenstein's Information Gap Theory).
- **Decision**:
  1. Implement a 6-step non-intrusive Cadet Flight Academy (`models.py`, `story.py`, `engine.py`) grounded in Vygotsky's Zone of Proximal Development (ZPD) and Gee's Situated Learning principles. The academy passively monitors natural player actions (`orbit`, `scan`, `power`, `trade`, `drone`, `jump`) rather than imposing modal tutorial prisons, granting incremental credits and XP upon completion, culminating in graduation honors and the `relic_cadet_wings` artifact.
  2. Embed "The Precursor Cipher" space opera campaign (`story.py`, `engine.py`), featuring a 3-act episodic mystery spanning Sol, Sirius, and the Vega Gateway. Each act introduces rich character dispatches across an encrypted subspace radio array (Admiral Vance of the Sol Coalition, Cipher of the Free Spacers Syndicate, and Archon Prime of the Precursor Watch) and presents high-stakes moral dilemmas altering faction standings, economy, and unique story relics.
  3. Expand the Web Cockpit HUD (`index.html`, `style.css`, `app.js`) with an always-visible Cadet Flight Academy progress ribbon and a dedicated COMMS LOG interface complete with faction reputation chips, animated speaker avatars, and Web Audio synthesized subspace transmissions.
  4. Provide full CLI and REPL parity (`voidfarer tutorial [skip|reset]` and `voidfarer story [choose <id>]`).
  5. Preserve strict architectural decoupling between data DTOs (`models.py`) and story content templates (`story.py`), maintaining zero circular dependencies, backward compatibility with legacy save states, and sub-second test execution.
- **Consequences**: Radically flattens player onboarding friction, establishes compelling narrative stakes, maximizes player attention and retention through parasocial agency and narrative transportation, and maintains 100% standard library compliance across all platforms.

### ADR-005: Deep Hardening of Narrative Engine, Web Cockpit State Resolution, and Relic Stat Integration
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: A comprehensive post-implementation audit of the Cadet Flight Academy and Precursor Cipher narrative campaign revealed several operational gaps: (1) In Web Cockpit JS, `story_chapters` was serialized as an array, but accessed as an object dictionary by chapter ID string, causing `curChap` to evaluate to `undefined` and preventing the story tab from rendering; (2) In `engine.py`, story choices lacked target system validation, allowing players to resolve remote acts (Sirius and Vega) without traveling to their target star systems; (3) Passive stat multipliers in `retention.py` omitted support for `max_hull` and `trade_margin`, leaving story relics like `relic_cipher_key` and `relic_cadet_wings` inert; (4) The Web HUD and CLI lacked distinct victorious visual states for completed campaigns and graduation ceremonies.
- **Decision**:
  1. Update `retention.py` `calculate_passive_multipliers` to fully calculate `max_hull`, `trade_margin`, and dual-syntax `scanner_bounty`/`scan_bounty`, and wire effective maximum hull and shield expansion directly into `engine.py` when story relics are awarded.
  2. Implement strict geographical star-system validation in `SimulationEngine.make_story_choice()`, requiring the flagship to be physically present in `current_chapter.target_system_id` to resolve narrative decisions.
  3. Harden Web Cockpit `app.js` and `server.py` with dual `story_chapters` array and `story_chapters_map` dictionary lookups, safe null-checking for chapter system coordinates, graduation celebration ribbons, and retake-academy controls.
  4. Enrich CLI `cmd_story` and `cmd_status` with prominent celebratory campaign epilogue views once all acts are resolved.
  5. Expand automated regression test coverage to 58 tests across all edge cases.
- **Consequences**: Guarantees zero UI rendering failures, aligns narrative progression with spatial flight mechanics, activates all passive story relic mechanics, and provides celebratory feedback across both web and terminal interfaces.
### ADR-006: Sovereign Factions, Megacorporations, and Advanced Dual-Layer Tactical Combat Archetypes
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: Voidfarer's procedural galaxy lacked geopolitical depth, sovereign territorial borders, corporate commerce incentives, and tactical enemy depth beyond basic pirate skirmishes. Players required persistent diplomatic standing, ideological alliances, market price tariffs/discounts, and engaging tactical combat with deflector shields, telegraphed abilities, and subsystem targeting.
- **Decision**:
  1. Implement `Faction` and `Corporation` domain models (`factions.py`) featuring 5 canonical sovereign factions (Sol Coalition, Free Spacers Syndicate, Precursor Watch, Nebula Mining Collective, Orion Ascendancy) and 4 canonical megacorporations (Omnicorp Mining, Hyperion Dynamics, Astral Logistics, CyberneX Labs).
  2. Implement dynamic Standing Tiers (-100 to +100: Hostile, Unfriendly, Neutral, Friendly, Allied) with geopolitical market purchase modifiers (-15% discount for Allied down to +25% punitive tariff for Hostile) and corporate specialty trade margin bonuses (+15% to +22% margin on specialty commodities).
  3. Introduce star system territorial affiliation and emergent naval interdictions: hyperlane transit into systems controlled by Hostile factions (standing <= -50) triggers high-probability naval patrol interceptions.
  4. Create `EnemyArchetype` procedural generation (`enemies.py`) with 5 tactical archetypes (Corsair Interceptor, Syndicate Marauder, Corporate Enforcer, Precursor Sentinel, Warlord Dreadnought), deflector shield capacitance, telegraphed special abilities (`shield_drain`, `emp_overload`, `nanite_regen`, `tachyon_lance`), and precision subsystem targeting (`target weapons`, `target shields`).
  5. Add kinetic armor-piercing Drone Strike attacks that bypass deflector shields to directly damage enemy hulls, granting deployed fleet drone assets high-value tactical combat utility.
  6. Deliver full CLI REPL and Web Cockpit parity, including interactive Factions & Corps tabs, dual Shield/Hull telemetry meters, pulsing telegraph warning banners, and victory reputation shifts.
- **Consequences**: Deepens the galaxy with emergent geopolitical consequence, trade specialization, and high-stakes tactical space battles while preserving 100% Python standard library purity, backward compatibility for legacy save files, and sub-second test execution across 68 automated unit tests.

### ADR-007: Zero-Friction 1-Click Game Launchers and Embedded Browser Auto-Launch
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: Voidfarer required players to execute terminal commands (`python -m voidfarer.cli serve` or `repl`) from command prompts, creating friction for users who expect a 1-click startup experience directly from Windows Explorer.
- **Decision**:
  1. Implement `play.bat` with automated multi-tier Python discovery (`py -3`, `python`, `python3`, and standard installation paths), an interactive ASCII mission menu defaulting to the Web Cockpit, and transparent CLI argument passthrough.
  2. Implement `voidfarer.bat` as a fast passthrough batch launcher in both project root and workspace root.
  3. Enhance `server.py` and `cli.py` with an `--open` flag that utilizes the standard `webbrowser` module via a non-blocking timer thread to automatically launch the default browser upon server readiness.
- **Consequences**: Enables instantaneous 1-click game startup on Windows without any external pip packages, preserving 100% standard library compliance and sub-second automated test execution.

### ADR-008: Cosmic Stardate, Simulation Ticks, and Universal Time Control Architecture
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: Voidfarer's galaxy simulation previously relied partly on asynchronous wall-clock intervals or static turns, lacking an explicit universal simulation clock, orbital angular velocity updates for celestial bodies, autonomous fleet drone time-based yield accumulation, passive shield capacitance recharge, and player temporal control mechanics (pause, speed acceleration, manual discrete tick stepping).
- **Decision**:
  1. Introduce `TimeState` immutable DTO in `models.py` tracking `tick: int`, `stardate: float`, `speed: float`, `is_paused: bool`, `time_scale: str`, and `elapsed_days: float`, serialized with backward-compatible defaults in `GameState`.
  2. Implement `SimulationEngine.tick(num_ticks: int = 1)` advancing:
     - Cosmic stardate and elapsed days (1 tick = 0.25 days = 6 hours; stardate = 3042.0 + elapsed_days / 365.25).
     - Circular/Keplerian orbital positions (`current_angle = (current_angle + orbit_speed * 0.05 * num_ticks) % (2*pi)`) across all celestial bodies in the galaxy.
     - Autonomous fleet drone harvest yield cycles across star systems.
     - Passive deflector shield capacitor regeneration out of combat.
     - Combat ability cooldown decay during active tactical encounters.
  3. Implement temporal control primitives: `pause_time()`, `resume_time()`, `set_time_speed(speed: float)` (0x, 1x, 2x, 5x, 10x), and `step_time(num_ticks: int)`.
  4. Implement REST API endpoints in `server.py`: `GET /api/time`, `POST /api/time/step`, `POST /api/time/speed`, `POST /api/time/pause`, and `POST /api/time/resume`, accompanied by a background `SimulationTicker` daemon loop scaling tick sleep intervals by `1.0 / speed` when unpaused.
  5. Provide terminal CLI and REPL parity: `voidfarer time [status|pause|resume|speed <val>|step [n]]` and interactive REPL aliases (`chrono`, `tick`, `wait`).
  6. Provide Web Cockpit HUD parity: sleek cybernetic `hud-time-deck` with glowing live stardate and tick badge, interactive pause/speed/step buttons, Spacebar/1-4/T hotkeys, and synchronized canvas radar planet orbital positions.
  7. Maintain thread safety via re-entrant engine locking and sub-second test execution across 84 automated unit tests.
- **Consequences**: Gives players full god-like temporal command over cosmic simulation flow, deepens orbital and fleet autonomy dynamics, aligns canvas radar motion with physics state, and preserves zero third-party dependencies.

### ADR-009: Universal State Preservation, Temporal Speed Memory, and Hyperspace Transit Dynamics
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: In-depth audit of recent temporal mechanics and simulation state updates revealed critical gaps and regressions:
  1. Manual `GameState(...)` instantiation across 25 engine operations (orbit, scan, trade, refuel, repair, route_power, combat, anomaly resolution, upgrades, drones, contracts, talents, story choices, tutorial controls) omitted the `time` field, silently resetting cosmic ticks and stardate back to `tick=0, stardate=3042.0` on every action.
  2. Temporal speed memory was lost when pausing: resuming the clock defaulted to 1.0x even if the commander previously set 5.0x or 10.0x.
  3. Hyperspace jumps took instantaneous zero cosmic time, failing to advance planetary orbital revolutions or fleet drone harvest cycles during long interstellar transit.
  4. Server ticker daemon loop utilized non-interruptible `time.sleep()`, causing delay during server shutdown and missing RAII socket cleanup on Windows.
  5. Rapid keyboard repeat on Spacebar/hotkeys caused uncontrolled HTTP request stampedes to the temporal control endpoints.
- **Decision**:
  1. Introduce `_clone_state(**kwargs) -> GameState` in `SimulationEngine` that preserves `time` and `stats` fields unless explicitly overwritten, and refactor all 25 methods across `engine.py` to use `_clone_state(...)`.
  2. Upgrade `pause_time()`, `resume_time()`, and `set_time_speed()` to store and remember configured playback speed rate across pause/resume cycles.
  3. Advance cosmic time by 2 ticks (12 hours / 0.5 days transit) on interstellar hyperspace jumps, updating planetary orbits across all systems and persisting realistic transit duration.
  4. Refactor `_ticker_loop` to use `ticker_stop.wait(interval)` for instant thread termination, and add a `finally:` block in `run_server` ensuring `server.server_close()` is always invoked.
  5. Add hotkey repeat suppression (`if (e.repeat) return;`) and drone harvest yield telemetry logging in Web Cockpit `app.js`.
  6. Expand automated test coverage with regression tests for state preservation, speed memory, and hyperspace transit time.
- **Consequences**: Guarantees zero simulation clock resets across any player action, realistic cosmic transit time during interstellar jumps, smooth temporal control UX, instant clean server shutdown, and 100% test pass rate across all automated suites.

### ADR-010: V10 Economy & Inventory Stabilization: Combat Tick Rebuild, Volume Cargo Gate, Chassis Listing, Consumable Terminal, and Housekeeping
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: An independent review of the in-flight V10 economy/trading/inventory work (`economy.py`, `inventory.py`, engine hooks, REST/CLI surfaces) confirmed several defects blocking the feature:
  1. `tick()` rebuilt the active combat encounter with non-existent fields (`enemy_type`, `enemy_weapons`, `threat_level`, `tactical_turn`, `combat_log`), raising `TypeError` whenever a special-ability enemy had an active `ability_cooldown`; the Web Cockpit background ticker thread died on the first such tick.
  2. The buy-side cargo gate compared raw unit counts against a volume requirement, silently overselling hold space for multi-volume commodities (titanium, xenoliths).
  3. `get_available_chassis` was called with the ship's class name instead of the chassis id, so the current hull always appeared purchasable in the REST shipyard payload and Web HUD; the zero-cost starter hull could also be re-bought for free hull/shield/fuel refreshes.
  4. `sell_upgrade` cleared the equipped slot but left the module name in `ship.upgrades`, producing ghost modules in the HUD.
  5. The item catalog defined four usable consumables, but no purchase path existed: the CLI hint pointed at a non-existent `inventory buy`, and the REST API offered `use`/`jettison` without a buy endpoint.
  6. Bare `int()` conversions in `inventory jettison`, `repair`, `refuel` (CLI/REPL) and `/api/inventory/jettison` (REST) crashed on non-numeric input.
  7. `cmd_market` displayed legacy static prices while `trade()` charged dynamic stock/event/faction-adjusted prices.
  8. The hygiene gate flagged three Google Fonts links and four silent `except Exception: pass` blocks (browser launch, server teardown, console reconfigure).
- **Decision**:
  1. Rebuild the combat encounter via `dataclasses.replace(...)` for ability-cooldown decay.
  2. Centralize hold math in `inventory.calculate_cargo_volume` and use it in `trade()` and the new `buy_item()`.
  3. Resolve the current chassis through `SimulationEngine.current_chassis_id` for `get_available_chassis` (state snapshot + REST shipyard) and reject zero-cost starter hull purchases in `buy_ship_chassis`.
  4. Remove the sold module's display name from `ship.upgrades` on sale.
  5. Add `SimulationEngine.buy_item` with CLI `inventory buy <id> [qty]` (including top-level argparse parity) and `POST /api/inventory/buy`; malformed REST quantities answer `400`.
  6. Guard CLI/REPL numeric conversions and REST quantity parsing with clean messages.
  7. Render `calculate_dynamic_market_quote` values plus the faction trade modifier in `cmd_market`, matching what `trade()` actually charges.
  8. Drop the Google Fonts links, extend the CSS font variables with local fallback stacks, and narrow the exception handlers while keeping best-effort teardown (browser launch reports a manual-visit hint instead of failing silently).
- **Consequences**: The V10 economy/inventory feature is stable, documented, and covered by 33 new tests (`test_economy.py`, `test_inventory.py`, and regressions) -- 120 tests total, 100% green in about 2 seconds. Cargo math, chassis listings, market prices, and the advertised consumable terminal now match what the player experiences in CLI, REST, and the Web Cockpit, which also renders fully offline. Deferred to a future milestone: wiring the inert `stat_bonus` effects of the newer hardware modules and chassis perks, restoring the unreachable web mini-games, and completing the phishing panel.

### ADR-011: Windows Launcher Crash Repair: Escaped Banner Pipes, CRLF Endings, and Launcher Regression Tests
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: Double-clicking `play.bat` on Windows appeared to do nothing: the console window flashed and closed before any menu. Reproduction showed `cmd /c play.bat` exiting with code 255 after printing only the first banner lines, with `'_' is not recognized as an internal or external command`. Root causes: (1) two unescaped `|` groups in the ASCII banner (`\|_` and `_||`) made cmd treat the rest of the echo as a piped command line, aborting the script before the menu; (2) both launchers shipped LF-only line endings, which cmd parses unreliably and editors easily reintroduce; (3) the banner's bottom line rendered `\_|\______` instead of the canonical `\_\|______` art used by the Python status banner in `cli.py`; (4) the menu hard-coded "68 Unit Tests", long stale.
- **Decision**:
  1. Escape every literal pipe in the banner (`\|` -&gt; `\^|` and `||` -&gt; `^|^|`) so the art renders without cmd interpreting it as a pipeline.
  2. Convert `play.bat` and `voidfarer.bat` to CRLF line endings.
  3. Align the banner's final line with the canonical art in `cli.py`.
  4. Replace the stale "68 Unit Tests" menu label with "Automated Test Suite" so it cannot drift from the real count again.
  5. Add `tests/test_batch_launchers.py`: a CRLF policy unit test for both launchers plus a Windows-only integration test that runs the real menu path (choice `0`) and requires a clean exit 0 with the menu rendered.
- **Consequences**: Double-click launch works again from Explorer, argument passthrough (`play.bat status`, `voidfarer.bat status`) still exits 0, and launcher regressions now fail the suite -- 123 tests total, 100% green in about 2 seconds.

### ADR-012: Relics Command API Repair and Test Isolation from the Live Save
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: The Phase 4 gate failed on `test_cli_relics` once the save contained a relic: `cmd_relics` called `calculate_passive_multipliers(relics, specializations)` although the function takes only `ship`, and then printed key names (`scanner_bounty_mult`, `laser_damage_mult`, ...) the returned dict never contains. Both defects had been masked because the CLI test suite ran against the player's real save in `%LOCALAPPDATA%\.voidfarer`: `TestCLI` calls `main()` with no isolation, so mutating test commands (for example `power`) persisted into live player progress, and the tests only exercised the relics path while the live save happened to have no relics.
- **Decision**:
  1. Call `calculate_passive_multipliers(engine.state.ship)` in `cmd_relics` and map the canonical keys: `scan_bounty`, `trade_margin`, `laser_dmg` and `drone_yield` as delta percentages, `shield_cap` and `max_hull` as absolute bonuses, and `fuel_efficiency` as savings.
  2. Isolate every test that reaches `main()`/`_get_engine` from the live save: `tests/test_cli.py` gains an `_IsolatedCliTestCase` base that patches `LOCALAPPDATA`, `HOME`, and `USERPROFILE` into a per-test temp directory, and `tests/test_story.py::test_cli_main_entrypoint` wraps its `main()` calls the same way.
  3. Add `TestCLIRelicsWithRecoveredRelics`, which seeds a save containing all six story relics and asserts the vault and modifier block render with exit 0.
- **Consequences**: The relics command works for any save, the automated suite can no longer read or write the player's live save (`%LOCALAPPDATA%\.voidfarer` verified untouched by hashing it before and after full-suite runs), and total coverage is 124 tests, 100% green in about 2 seconds.

### ADR-013: Cockpit Layout Rules: Lower-Right Telemetry Log with Hide Button, Top-Right Chrono Deck, Left Vertical Terminal Rail
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: The user stated three cockpit layout rules, now recorded as project guidelines G-001..G-003: (1) the TELEMETRY / Tactical Flight Log belongs in the lower-right corner and must carry a hide button; (2) the Chrono tick and time settings deck belongs in the right upper corner; (3) the Commerce/Arsenal/Fleet terminal runs vertically (up to down) on the left side with the active tab's content beside it. The old cockpit held the log in the center deck, the chrono deck mid-bar, and the terminal as a horizontal tab strip in the right deck. Clarification answers: the chrono deck stays inside the top status bar but is pinned to its far right edge; the lower-right deck holds only the telemetry log; the radar moves above the reactor in the center column, with the context alerts on top.
- **Decision**:
  1. Restructure `index.html` (blocks moved verbatim by a balanced-tag span extraction -- no markup retyped): `#panelRight` holds only the log panel (`#logPanel`, with `#btnToggleLog` + `#clearLogBtn` in a `log-header-actions` group); `#panelCenter` stacks the combat/anomaly alert cards, the NAV-radar sub-panel (`#panelNav`) and the reactor matrix (`#panelReactor`); the new `#panelLeft` deck carries the vertical tab rail (`#deckTabsHeader`) plus a `terminal-content-stack` with all seven tab contents; the chrono deck is the last block of `#hudTopBar`.
  2. `style.css`: `.cockpit-grid` columns become `1.5fr 1.15fr 0.9fr`; `.panel-left` turns into a two-column grid (170px rail + content) and its `.deck-tabs-header` stacks vertically; `.panel-right` pins its content to the corner with `justify-content: flex-end`; `.hud-time-deck` gains `margin-left: auto`; `.log-panel.log-collapsed` hides the stream; below 1200px the rail collapses into a wrapping row.
  3. `app.js`: cache `#logPanel`/`#btnToggleLog` and bind a click handler that toggles `log-collapsed` and swaps the HIDE/SHOW label; the collapse state is view-only and persists nothing.
  4. Add `tests/test_cockpit_layout.py`: eleven structural tests (stdlib `html.parser` element tree over the real assets) pinning deck membership, document order, the CSS rules, and the JS wiring -- written failing-first (11/11 red before the restructure, 11/11 green after).
- **Consequences**: The terminal rail now runs down the left side, the center column shows alerts above the radar and the reactor, the chrono controls sit in the top-right corner, and the telemetry log is anchored at the lower-right corner where it can be collapsed to reclaim space. Known limitation (unchanged): the radar click mapping assumes 1:1 canvas scaling; growing the radar container was deliberately avoided to keep pointer behaviour identical. Total coverage 135 tests, 100% green in about 2 seconds.


### ADR-014: Effective Hardware Module Bonuses, Chassis Perks, and a Portable Launcher Test
- **Date**: 2026-10-18
- **Status**: Accepted
- **Context**: ADR-010 deferred wiring the inert `stat_bonus` entries of the newer hardware modules and the chassis perks. An audit confirmed the gaps: only `warp_booster_mk2` and `deep_core_scanner` had hard-coded effects; fuel savings on MK-I/MK-III, evasion, shield regeneration, scan multipliers, relic-find, combat damage, and ECM were advertised in the arsenal but never read; and the Orion, Solaris, Chronos, and Archon chassis perks existed only as display strings. Separately, the full suite was red on this Windows host because `NoDefaultCurrentDirectoryInExePath=1` makes `cmd /c play.bat` fail to resolve the script from the project directory, even though double-click and `.\play.bat` work.
- **Decision**:
  1. Extend `ShipChassis` with a `stat_bonus` mapping and populate it from the advertised perks: Orion `+15%` trade margin, Solaris `+20` combat damage, Chronos `x1.5` scan yield, Archon `+35` combat damage; the starter Vanguard stays neutral.
  2. Add `calculate_equipment_bonuses(ship)` in `upgrades.py` as the single aggregation point. Fuel savings multiply as `(1 - value)`, scan yields multiply, and combat damage, evasion, shield regeneration, relic-find, ECM, trade margin, and passive repair sum; fuel is floored at `0.10x` and evasion/ECM at `0.90`.
  3. Consume the aggregate in the engine: jump fuel burn (replacing the `warp_booster_mk2` hard-code), hostile and low-security encounter rolls (`pirate_evasion`), scan bounties and relic chance (replacing the `deep_core_scanner` hard-code), sale margins, laser damage (replacing the `pulse_cannon_array` hard-code), evasive-burn and counter-battery dodge chance, and tick shield regeneration plus repair-bay healing.
  4. Expose `equipment_bonuses` in the status snapshot for HUD/telemetry consumers without changing the save schema or catalog ids.
  5. Add `tests/test_equipment_bonuses.py` (11 tests, failing-first) covering the aggregation rules and each engine surface, and make the Windows launcher integration test invoke the absolute `play.bat` path so hardened hosts with `NoDefaultCurrentDirectoryInExePath=1` can still run it.
- **Consequences**: Every advertised hardware effect and chassis perk now changes gameplay through one test-pinned calculation path; purchases no longer promise inert stats. Coverage is 146 tests, 100% green in about 2 seconds, with the launcher regression test portable across hardened Windows configurations. No save migration was needed because chassis identity continues to resolve from the stored ship class and bonuses are derived at read time.

### ADR-015: Audit-Driven Hardening: Service Guards, Relic Stats, Storage/Server Resilience, CLI Parity, and Cockpit Runtime Contracts
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: A full-project audit found defects spanning four layers. Engine: negative repair/refuel amounts minted credits and removed hull/fuel; buying an upgrade or chassis recomputed maximum hull/shield from chassis plus modules only, discarding permanent relic maxima; random max-stat relics were inert; `scan()` and `step_orbits()` dropped `StarSystem.dominant_corp`; occupied upgrade slots left ghost modules; drone harvest bypassed cargo volume; the victory path discarded a streak decrement; a zero `next_level_xp` could hang the engine; story choices updated a separate reputation store; invalid drone systems were accepted; repeat scans paid full bounties forever. Storage: failed atomic replacements returned success, temp names could collide, and schema-invalid saves skipped backup recovery. Server: malformed JSON silently became `{}` (triggering default mutations), unguarded integer conversions reset connections, `/api/step` did not save, and `/api/reset` bypassed the engine lock and RNG reset. CLI: documented combat actions, shipyard subcommands, `corporations`, and positional repair/refuel amounts were unreachable behind argparse. Cockpit: pointer hit tests used CSS pixels against intrinsic canvas pixels, state was dereferenced before load, power sliders overwrote authoritative power, cargo showed unit counts instead of volume, scan audio read non-existent response fields, and canvas colors used invalid CSS variables.
- **Decision**:
  1. Guard repair/refuel with positive-integer validation; preserve relic/talent `max_hull`/`shield_cap` when buying or selling modules and chassis; apply newly acquired max-stat relics immediately through `_apply_relic_stat_bonuses`; cap `_award_pilot_xp` at `next_level_xp >= 1`; preserve `dominant_corp`; reject occupied-slot replacement until the old module is sold; reject drone harvest when the incoming titanium volume exceeds free hold space; map story alignments into `faction_standings`; validate drone target systems; gate repeat scans on `scan_completed`; and share `MIN_STOCK`/`MAX_STOCK` between trade and the economy tick.
  2. Harden storage with a write lock, `uuid4` temp names, an atomic backup path, a raised `OSError` after failed replacements, invalid-UTF-8 handling, and schema-invalid primary quarantine plus backup fallback.
  3. Harden the HTTP server with bounded body parsing, dict-only JSON, typed `_int_field`/`_float_field`/`_bool_field` helpers, 400 responses for malformed input, a lock-protected `SimulationEngine.reset(seed)` with a fresh RNG, persisted `/api/step`, bind-error guidance, ticker save-error reporting, and a final save plus ticker join on shutdown.
  4. Restore CLI parity: full combat action set with subsystem target, `shipyard chassis|sell`, a `corporations` alias, and positional repair/refuel amounts.
  5. Fix cockpit runtime contracts: CSS-to-canvas pointer scaling, drag/click suppression, null-state guards, dirty-aware power-slider sync, manifest volume for the cargo meter, `discovery.relic`/`near_miss` audio, literal canvas colors, selected-target refresh after polling, market-tab rendering, and story auto-scroll only when new messages arrive.
- **Consequences**: All 179 tests pass in about 2.5 seconds and `aikit check voidfarer` remains the gate. The changes close economy-corrupting inputs, silent save failures, malformed-request crashes, permanent-stat loss, and several cockpit state mismatches. Trade-offs: occupied-slot replacement is now a two-step action (sell, then buy) to avoid surprising automatic resale; drone harvest fails rather than partially collecting when the hold is full; repeat scans no longer pay bounties; and failed saves surface as 500 responses instead of silent success. Deferred with rationale: faction tier perks and archetype `rep_rewards` remain descriptive data (implementing them changes balance and needs explicit tuning); multi-stat relic descriptions still exceed the single-passive relic model; combat/anomaly cargo grants still do not enforce hold capacity; the REPL-launched server still lacks the CLI ticker; and cockpit HTML interpolation remains unescaped for tampered local saves. These are recorded as known gaps rather than silently claimed as fixed.

### ADR-016: Adaptive Enemy AI, Expanded Star Systems, and In-Game Calendar Dates
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: Hostile encounters used fixed special-ability cooldowns and did not react to the player's tactical state; star systems generated only 2-3 planets; and the chronometer exposed a fictional stardate (`3042.xx`) that was hard to read as a date. The requested additions had to preserve existing combat, economy, save, CLI, and HUD contracts.
- **Decision**:
  1. Add `ai_profile` and `enemy_intent` to `CombatEncounter` with safe defaults for old saves. Assign profiles to all five hostile archetypes (`aggressive`, `defensive`, `opportunist`, `adaptive`, `warlord`) and add `choose_enemy_intent()` in `enemies.py`. The policy reads enemy hull/shield ratios, player hull/shield ratios, tactical combo, special-ability readiness, and profile, then chooses `fire`, `brace`, `evade`, `execute`, or `ability` and emits a matching telegraph.
  2. Apply intents in `combat_action`: `brace` reduces incoming player strike damage to 55%, `evade` gives a 35% chance to make a damaging player action miss, `execute` increases counter-battery (and shield-absorb) damage by 50%, and `ability` gates the existing special abilities. The next intent is recomputed after every exchange and persisted, so combat telemetry predicts the AI's next move.
  3. Expand each system to 5-6 planets (6 in Sol and Betelgeuse, 5 elsewhere) and add desert, ice, lava, ringed-giant, and research-outpost archetypes. Guarantee at least one dockable station per system via a deterministic fallback conversion, preserving `sol_body_1` and existing body IDs.
  4. Add `TimeState.current_date` as `DD.MM.YYYY`, derived from `elapsed_days` with a 01.01.3042 epoch, and include `date` in time payloads while retaining `stardate` for compatibility. CLI status/time, server startup, and the web chronometer now show the calendar date with the tick badge.
- **Consequences**: New games get 52 planets across 10 systems with guaranteed stations, and hostile captains visibly adapt to player behavior. Existing saves remain loadable because new combat fields default and time payloads are additive; however, existing saves keep their stored 2-3-body galaxy until the player starts a new game or resets, since systems are persisted. The AI is an explainable deterministic policy rather than an ML model, so it is testable and predictable; profile and intent strings are open-ended but validated through defaults. Calendar dates use the game epoch, not the host machine's real date, so they remain stable across systems and saves.

### ADR-017: Frontier Command Expansion: Main Menu, AI Captains, Depots, Messages, Landing, Fleets/Allies, and a Branching Perks Window
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: The cockpit had no startup/save-management surface, the radar controls lived outside the map, the Mastery page was a passive tab, and the galaxy lacked AI traffic, cargo depots, intergalactic messaging, landing, mercenaries, allies, and persistent unit statistics. The expansion had to remain save-compatible and keep the 222-test suite and existing REST/CLI contracts intact.
- **Decision**:
  1. Add persistent `AICaptain`, `Depot`, `QuantumMessage`, `Moon`, and expanded body metadata (`gravity`, `atmosphere`, `temperature_c`, `resources`, `moons`, `landable`). Extend `FleetDrone` with level/efficiency/integrity/sorties/specialty and `ShipState` with allies/landed body. All new save fields default safely.
  2. Add `frontier.py` with a deterministic five-captain roster, one depot per system, onboarding messages, a mercenary catalog, and an AI trader simulation that moves captains between systems and mutates stockpiles each tick. Player trades already mutate the same markets, so both actors drive prices.
  3. Add engine actions for AI hail/buy/sell/hire/ally, depot deposit/withdraw/direct-sale, quantum send/read, surface landing, mercenary hire/refit/dismiss, fleet-unit dismissal, and unified quest snapshots. AI allies add trade margin and combat support; mercenaries add damage, evasion, or post-victory repair.
  4. Expand procedural generation to 15 systems with 5-6 bodies each, new star spectral types (B/O/red giant/binary), savanna/tundra/toxic/barren/super-Earth/ice-giant worlds, generated moons, asteroid belts, guaranteed habitable landing sites, and a guaranteed station per system.
  5. Add a startup main-menu overlay (Continue/Save/Load/Delete/New/Settings), a closable settings window with localStorage persistence, a centered black NAV-radar with overlaid ORBITS/GALAXY and GRID/LABELS controls, a flagship transit animation, planet/system inspector fields, landing controls, Quest/AI/Depot/Messages tabs, fleet stats/refit/dismiss, mercenary contracts, and a branching Pilot Perks window with tier-2 prerequisites.
- **Consequences**: New games start with AI traffic, depots, messages, moons, and 80+ planets; existing saves receive the frontier roster/depots/messages via a bootstrap pass while keeping their stored systems. Compact UI controls moved onto the radar so the map remains the visual center, and the former Perks tab now opens a modal tree. Trade-offs: AI trade is a deterministic stockpile-flow model rather than price-optimizing agents; depots store units rather than volume; landing rewards are one-shot survey bonuses; and the main menu is web-only while the CLI retains its existing command surface. Residual: combat/anomaly cargo grants still bypass hold capacity, and cockpit HTML interpolation remains unescaped for tampered local saves (ADR-015).

### ADR-018: Capacity-Safe Reward Cargo and CLI Frontier Parity
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: ADR-017 left two follow-ups: combat salvage and anomaly cargo rewards could push cargo volume above the hold capacity, and the new AI/depot/message/landing/mercenary/alliance systems were reachable only through the web cockpit.
- **Decision**:
  1. Add `_grant_cargo(cargo, commodity_id, quantity)` as the single capacity-aware grant helper. It computes free volume from `calculate_cargo_volume`, grants whole units that fit, and returns `(granted, overflow)`.
  2. Use the helper for combat salvage and anomaly cargo rewards. Combat messages now report the actual salvaged count and any jettisoned overflow; anomaly logs report overflow explicitly. Direct buys, drone harvest, deposits, and withdrawals already had capacity guards.
  3. Add CLI commands `quests`, `ai list|hail|buy|sell|hire|ally`, `messages list|send|read`, `depot status|deposit|withdraw|sell`, `land`, `mercs list|hire|dismiss|refit`, and `allies list|form`, reusing the same engine methods as the REST/cockpit paths.
- **Consequences**: The cargo-volume invariant now holds for all reward paths, with explicit overflow reporting instead of silent over-capacity storage. The new frontier systems are testable and usable from the terminal without changing REST or save contracts. Trade-off: overflow cargo is jettisoned rather than stored elsewhere; future depot auto-routing could recover it.

### ADR-019: Closing Advertised Faction Perks, Reputation Rewards, Multi-Stat Relics, Cockpit Escaping, and REPL Server Lifecycle Gaps
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: ADR-015/017 recorded five remaining gaps: faction perks were descriptive only, enemy archetype `rep_rewards` were dead data, relics advertised secondary effects that the single-passive model could not apply, cockpit HTML interpolated server data without escaping, and the REPL-launched server had no ticker or stop lifecycle.
- **Decision**:
  1. Add `get_faction_service_perks(faction_id, standing)` and consume it in repair, refuel, trade margins, scan XP, drone yields, and jump encounter evasion. Friendly factions grant 10% trade margin and 15% repair discounts; allied factions grant 20% margin, free refuel, and naval escort evasion; Syndicate adds 15% sale margin, Precursor Watch adds 25% scan XP, and Nebula Collective adds 30% drone yield.
  2. Persist `archetype_id` on `CombatEncounter` and apply `EnemyArchetype.rep_rewards` on victory to both `faction_standings` and `corp_standings`, with the old faction fallback retained for legacy/test encounters.
  3. Add `PrecursorRelic.bonuses` as a secondary stat map, round-trip it through saves and random drops, apply it in `calculate_passive_multipliers` and `_apply_relic_stat_bonuses`, and populate secondary effects for story relics (`Cadet Wings`, `Core Matrix`, `Archon Crest`, `Sentinel Matrix`).
  4. Escape all dynamic market/arsenal/contract/story/talent/relic/faction/corporation strings before `innerHTML` and whitelist faction colors through `safeColor`.
  5. Add `BackgroundServer` and `start_background_server()` with a concurrent simulation ticker and guarded `stop()` (final save, ticker join, shutdown, close); wire REPL `serve`, `serve stop`, actual port reporting, and shutdown on exit.
- **Consequences**: Advertised perks and relic descriptions now match simulation behavior, reputation rewards are data-driven, tampered save/API strings cannot inject markup, and the REPL-hosted cockpit advances time and saves like the standalone server. Trade-offs: faction perks are simple tier thresholds rather than per-faction bespoke rules; `void_eye` retains its existing special-case scan bonus instead of double-counting a bonuses map; naval escort is modeled as encounter evasion rather than a visible escort unit. These are intentional simplifications with regression coverage.

### ADR-020: In-System Sublight/Quantum Transit, Planetary Civilization Metadata, and Dismissible Cockpit Popup Events
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: Players and automated clients needed tick-based in-system transit (`sublight` and `quantum` modes) alongside immediate orbital capture (`orbit`), planetary civilization telemetry (`faction`, `population`, `government`) on inhabited bodies, and structured dismissible cockpit popup alerts (`GameEvent`) for arrivals and simulation events without breaking legacy save compatibility or the existing 238 unit tests.
- **Decision**:
  1. Add frozen `TravelState` and `GameEvent` DTOs in `voidfarer/models.py`, extend `CelestialBody` with `faction`, `population`, and `government`, add `travel: TravelState | None = None` to `ShipState`, and serialize `events: tuple[GameEvent, ...] = ()` in `GameState.to_dict()` / `from_dict()`.
  2. Populate deterministic civilization metadata (`faction`, `population`, `government`) on inhabited planets and stations in `GalaxyGenerator._generate_bodies` without consuming RNG calls, and backfill legacy saves in `SimulationEngine._bootstrap_frontier`.
  3. Add `start_travel(body_id, mode="sublight")`, `emit_event(kind, title, message)`, and `dismiss_event(event_id)` in `SimulationEngine`, advance and complete active `TravelState` on `tick()`, and include `undismissed_events` in `get_status_snapshot()` while preserving immediate `orbit(body_id)`.
  4. Expose `/api/travel` and `/api/events/dismiss` in `voidfarer/server.py`, add CLI `travel` and `events` subcommands in `voidfarer/cli.py`, and render planetary civilization fields, sublight/quantum transit buttons, and escaped popup event cards in `voidfarer/static/index.html` and `voidfarer/static/app.js`.
- **Consequences**: In-system navigation supports both instant orbital capture (`orbit`) and timed sublight/quantum transit (`start_travel`), inhabited worlds expose rich civilization telemetry, and cockpit alerts can be inspected and dismissed from both the web HUD and CLI with full save round-trip compatibility.

### ADR-021: ESC Menu Hotkey, Multi-Slot Atomic Saves, and Full-Viewport Background NAV-Radar Orbital Map (G-004)
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: The user requested three enhancements: (1) pressing `ESC` opens/closes the Main Menu (or dismisses open modal windows first), (2) multiple save slots so players can create, list, load, and delete independent saves from the Main Menu, REST API, and CLI without losing default-slot compatibility, and (3) making the NAV-Radar orbital map the full-viewport background layer of the game with all HUD decks and panels rendered on top of it (`G-004`).
- **Decision**:
  1. Extend `StorageManager` (`voidfarer/storage.py`) with `resolve_slot(slot)`, `get_save_path(slot)`, `list_saves()`, and optional `slot: str | None = None` parameters on `save()`, `load()`, and `clear()` / `delete_save()`. Slot `"default"` (or `None`/`""`) maps to `self.save_file` (`voidfarer_save.json`) for 100% backward compatibility; named slots (`^[A-Za-z0-9_-]{1,40}$`) map to `voidfarer_save_<slot>.json` with the same atomic temp+fsync+replace and `.bak` shadow backup recovery.
  2. Add `GET /api/saves` and extend `POST /api/save`, `POST /api/load`, and `POST /api/delete-save` in `voidfarer/server.py` to accept an optional `slot` field, returning the resolved slot and updated save metadata list. Add `voidfarer saves [list|save|load|delete] [slot]` in `voidfarer/cli.py`.
  3. Wire `Escape` in `voidfarer/static/app.js` to close `#settingsOverlay` or `#perksOverlay` if open, or toggle `#mainMenuOverlay` (`toggleMainMenu()`), and add a multi-save slot manager (`#saveSlotInput`, `#saveSlotsList`, quick slot buttons, per-slot load/save/delete) inside `#mainMenuOverlay`.
  4. Enforce layout guideline `G-004` in `voidfarer/static/style.css` and `voidfarer/static/app.js` while keeping `#panelNav` above `#panelReactor` inside `#panelCenter` in the DOM: style `.canvas-radar-container` as `position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 0;`, clear `backdrop-filter` on `#panelCenter`/`#panelNav` so `position: fixed` anchors to the viewport, set `pointer-events: none` on transparent layout containers and `pointer-events: auto` on interactive HUD panels (`z-index >= 2`) and the radar canvas, and dynamically resize `#radarCanvas` to viewport dimensions.
- **Consequences**: Players can toggle the Main Menu or close dialogs with `ESC`, manage multiple independent save slots with rich metadata across web and CLI, and interact directly with the full-screen background orbital/galaxy radar behind all HUD panels while all existing layout and storage regression tests continue to pass.

### ADR-022: Scientifically Accurate Planetary Physics, 2D Euclidean Sublight Transit Distance/Ticks, and Persistent Tick-Synchronized Radar Transit Animation
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: The user reported two simulation and HUD accuracy issues: (1) clicking transit in the cockpit ended the flagship transit animation prematurely after 1.3 seconds while `ship.travel` was still in progress across multiple ticks, and sublight transit only used `abs(r2 - r1)` instead of true 2D orbital distance; (2) planetary `atmosphere`, `gravity`, `temperature_c`, and `habitability` were assigned from independent random ranges rather than physically consistent stellar flux, bulk density, radius, atmospheric greenhouse/composition, and Earth Similarity habitability equations.
- **Decision**:
  1. Add `compute_scientific_planet_properties()` and `compute_habitability_index()` in `voidfarer/galaxy.py` and extend `CelestialBody` (`voidfarer/models.py`) with `habitability: float = 0.0` (0.0 to 100.0%). Derive planetary `radius_km`, bulk density, and surface `gravity` ($g = (R/R_\oplus)(\rho/\rho_\oplus)$) by planetary class, compute surface `temperature_c` from stellar spectral luminosity ($L/L_\odot$), orbital radius ($T_{\text{eq}} \propto L^{1/4}/\sqrt{r}$), Bond albedo, and atmospheric greenhouse forcing, assign realistic chemical composition and pressure strings for `atmosphere`, and compute `habitability` from surface solidity, breathable/pressurized atmosphere, temperature, gravity, and orbital hazards while preserving the exact RNG call count in `GalaxyGenerator._generate_bodies`. Backfill legacy saves deterministically in `SimulationEngine._bootstrap_frontier`.
  2. Update `SimulationEngine.start_travel()` (`voidfarer/engine.py`) to compute true 2D Euclidean orbital distance $d_{\text{AU}} = \sqrt{(r_2\cos\theta_2 - r_1\cos\theta_1)^2 + (r_2\sin\theta_2 - r_1\sin\theta_1)^2}$ between origin and destination bodies, scale sublight `duration_ticks` proportionally to $d_{\text{AU}}$ and reactor engine power allocation (`speed_au_per_tick`), and automatically unpause `TimeState` when initiating transit so ticks advance across the transit window.
  3. Update `voidfarer/static/app.js` and `voidfarer/static/index.html` to display `#targetHabitability` and true 2D Euclidean distance in the Target Inspector, hide the static orbiting `VF-FLAGSHIP` marker while `ship.travel` is active, and synchronize `drawTravelAnimation()` continuously with `state.ship.travel` (`started_tick` to `arrival_tick` plus smooth intra-tick interpolation and trajectory vector line) so the transit animation never terminates until orbital capture completes on `arrival_tick`.
- **Consequences**: Planetary telemetry (`gravity`, `atmosphere`, `temperature_c`, `radius_km`, `habitability`) is astrophysically self-consistent across all 15 star systems and legacy saves, sublight transit duration reflects real 2D orbital geometry and engine power, and the flagship transit animation glides continuously across the background radar for the full tick duration of the voyage.

### ADR-023: Decluttered Sleek Map HUD: Transparent On-Map Radar Title, Collapsible Right-Expanding Left Terminal Drawer, and Boxless Lower-Right Tactical Flight Log (G-005)
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: While the NAV-Radar orbital map was successfully converted into the background layer under ADR-021, bulky UI boxes still occluded critical radar space. Specifically: (1) `#radarTitle` and its containing header sat in an opaque panel box directly over the center radar; (2) the left terminal deck (`#panelLeft`) stayed permanently open with market/arsenal tables taking up wide horizontal space; (3) the lower-right Tactical Flight Log (`#panelRight` / `#logPanel`) sat inside double background-box frames (`deck-panel` and `sub-panel`) with blur filters and borders; and (4) center target/power cards occupied excessive vertical area when idle.
- **Decision**:
  1. Make the NAV-radar header (`.nav-panel > .panel-header`) boxless and transparent (`background: transparent`, `border: none`, `backdrop-filter: none`, `pointer-events: none`, `opacity: 0.45`), floating subtly as a sleek watermark title directly over the radar below the top controls without blocking clicks.
  2. Implement a collapsible right-expanding terminal drawer on the left (`#panelLeft`): by default (and whenever toggled closed), `#panelLeft` takes the `.drawer-collapsed` state, hiding `.terminal-content-stack` (`display: none`) and rendering only the slim vertical button rail (`COMMERCE`, `ARSENAL`, `FLEET`, etc.). Clicking any tab button expands `.terminal-content-stack` to the right beside the rail; clicking the active tab button again toggles the drawer closed.
  3. Strip background boxes, borders, and backdrop filters from `.panel-right`, `#logPanel`, and `.flight-log-stream` (`background: transparent`, `border: none`, `box-shadow: none`), rendering the Tactical Flight Log and its HIDE/CLEAR controls directly on top of the orbital map with crisp readable text-shadows.
  4. Keep `.nav-target-card` and `.reactor-panel` compact and anchored at the bottom of the viewport so the orbital center and star trajectories remain completely unobstructed.
  5. Add unit and structural regression tests in `tests/test_cockpit_layout.py` ensuring G-001 through G-005 invariants remain permanently green.
- **Consequences**: The orbital background radar is completely clear and visually dominant. Terminal content only expands when commanded and tucks neatly away into a slim left rail, the radar title floats as an unobtrusive semi-transparent watermark, and flight telemetry streams directly over space without boxed borders.

### ADR-024: Expandable Reactor Power Routing Panel, Top-Bar Action/Vitals Reordering, and Equal-Sized Vital Telemetry Cards (G-006)
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: The user requested three specific cockpit HUD improvements: (1) making the reactor power distribution panel expandable/collapsible with a HIDE/SHOW toggle button identical to the Tactical Flight Log, allowing the player to collapse power routing controls to reclaim bottom-center radar space; (2) swapping the position of the vital telemetry row (`.vitals-row`) with the quick action and sound controls (`.hud-top-actions`) so controls follow Brand -> Actions -> Vitals -> Chrono Clock; and (3) standardizing all vital telemetry stat cards (`vitalHullCard`, `vitalShieldCard`, `vitalFuelCard`, `vitalCreditsCard`, `vitalStreakCard`, `vitalMasteryCard`) to identical width and height dimensions for visual symmetry.
- **Decision**:
  1. Add `#btnToggleReactor` to `#panelReactor > .panel-header`, wire it in `voidfarer/static/app.js` to toggle the `.reactor-collapsed` class on `#panelReactor`, and hide `.power-matrix` and `.power-action-row` when `.reactor-collapsed` is active (`display: none`).
  2. In `voidfarer/static/index.html`, swap the DOM order of `.hud-top-actions` and `.vitals-row` within `#hudTopBar` while ensuring `#hudTimeDeck` remains the pinned right-most child.
  3. In `voidfarer/static/style.css`, standardize `.vital-card` with equal flex distribution (`flex: 1 1 0`), identical height (`height: 52px; box-sizing: border-box;`), identical min-width (`128px`), and vertical flex alignment (`display: flex; flex-direction: column; justify-content: space-between;`), so all 6 stat cards have the exact same rectangular dimensions across both full and compact viewports.
  4. Add structural regression tests in `tests/test_cockpit_layout.py` (`TestExpandableReactorAndVitalsAlignment`) verifying the reactor toggle wiring, `.reactor-collapsed` CSS rule, topbar child ordering, and equal-dimension CSS rules.
- **Consequences**: The player can collapse the reactor matrix at will to maximize radar visibility, the top bar follows a cleaner workflow hierarchy, and all vital status cards are symmetrically aligned with matching widths and heights.

### ADR-025: Shared 2D Polar Distance Calculation for Orbit and Transit, Single-Line Top-Bar Vitals/Chrono Symmetry (G-007), and Dynamic Demographic Population Mechanics
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: The user requested three complementary enhancements: (1) ensuring "ENTER ORBIT" and "SUBLIGHT TRANSIT" adhere strictly to the exact same 2D polar Euclidean distance calculation $d_{\text{AU}} = \sqrt{(r_2\cos\theta_2 - r_1\cos\theta_1)^2 + (r_2\sin\theta_2 - r_1\sin\theta_1)^2}$ across the simulation engine, flight log, and Target Card; (2) guaranteeing that all top-bar vital stat cards (`vitalHullCard`, `vitalShieldCard`, etc.) and the Chrono date box (`hudTimeDeck`) have the exact same height (`52px; box-sizing: border-box;`) and remain strictly on the same non-wrapping line (`flex-wrap: nowrap;`); and (3) implementing dynamic planetary population mechanics, including tick-based demographic growth scaling with habitability, demographic colony tiers (`Outpost`, `Colony`, `Settlement`, `Metropolis`, `Mega-Ecumenopolis`), and population-scaled market consumption.
- **Decision**:
  1. Add `compute_body_distance_au(target_body, origin_body=None)` in `voidfarer/engine.py` and consume it in both `orbit(body_id)` and `start_travel(body_id, mode)`. Update `orbit` flight logging and returned messages to report the true 2D Euclidean distance, and update `updateTargetCard()` in `voidfarer/static/app.js` so both the "ENTER ORBIT" and "SUBLIGHT TRANSIT" buttons display and use identical distance calculations.
  2. In `voidfarer/static/style.css`, enforce `flex-wrap: nowrap; overflow-x: auto;` on `.hud-topbar` and `.vitals-row`, and set `height: 52px; box-sizing: border-box;` on `.hud-time-deck` matching `.vital-card`, ensuring all stat cards and the chrono deck sit on a unified single line with matching vertical dimension.
  3. Add `step_population_dynamics(body, num_ticks)` in `voidfarer/galaxy.py` and `get_colony_tier(population)`. On simulation `tick()`, advance inhabited body populations based on habitability ($g \approx 0.00025 \times (\text{habitability}/100)$) or life-support station steady migration, and integrate population-tier reporting into the planet inspector and CLI status.
  4. Write failing-first tests in `tests/test_cockpit_layout.py` and `tests/test_galaxy.py` to pin the distance parity, single-line CSS, and population demographic simulation.
- **Consequences**: Navigation distances are astrophysically uniform across immediate orbital capture and timed transit, the cockpit top bar displays a clean, symmetrical, single-line layout matching the chrono clock, and star systems feature living planetary populations that evolve dynamically over time.





### ADR-026: Reactor Thermal Simulation, Procedural Sector Map Modifiers, and Structural Ship Modification Section
- **Date**: 2026-10-20
- **Status**: Accepted
- **Context**: The user asked to make VoidFarer more simulation-like, add more game functions, add map modifiers, revamp reactor mechanics, and add a ship modification section. The existing reactor was a static four-slider allocation with no thermal state, star systems had no persistent environmental conditions, and ship progression was limited to catalog upgrades and chassis purchases.
- **Decision**:
  1. Add `ReactorState` (`heat`, `max_heat`, `integrity`, `max_integrity`, `mode`, `last_vent_tick`) and `voidfarer/reactor.py` with `balanced`, `economy`, `overdrive`, and `silent` doctrines, heat generation proportional to allocation, sector/cooling modifiers, thermal derating above 70 heat, critical hull/core damage above 92 heat, an emergency coolant purge with cooldown, and drydock repair. Apply reactor output efficiency to engines, shields, sensors, weapons, anomaly checks, and telemetry while preserving the existing `ShipPower` 100% allocation contract.
  2. Add `MapModifier` and `StarSystem.modifiers` plus `voidfarer/mapmods.py` with deterministic per-system generation (independent RNG stream), ten environmental conditions, and aggregated effects on jump fuel, scan yield, sensor range, encounter risk, trade margin, evasion, relic discovery, hull hazard, and reactor heat/cooling.
  3. Add `ShipState.ship_mods` and `voidfarer/shipmods.py` with five structural slots (`frame`, `reactor_core`, `thermal`, `drive`, `ops`) and twelve trade-off refits. Installing/removing refits recomputes max hull, shields, cargo, and fuel through the shared `_recompute_caps` helper, so later upgrade or chassis purchases preserve structural bonuses and maluses.
  4. Add CLI commands `reactor`, `mapmods`, `refit`, and `simulation`; REST endpoints under `/api/reactor*`, `/api/mapmods`, `/api/shipmods*`, `/api/simulation`; and cockpit controls for heat, doctrine, coolant purge, sector modifier chips, and the SHIP MODS terminal section.
- **Consequences**: Reactor management becomes an active thermal trade-off, star systems gain persistent environmental identities that alter route planning and economy choices, and ship building gains a second structural progression layer. Legacy saves backfill map modifiers deterministically and default to a cold balanced reactor without changing existing RNG streams or save compatibility.

### ADR-027: Commander, Empire, Faction, Fleet, and Travel Systems Expansion
- **Date**: 2026-10-20
- **Status**: Accepted
- **Context**: The user requested a more simulation-like game with a player character (age, skills, abilities), research and outpost mechanics, faction leaders and behaviors, diplomacy and war elimination, a fleet manager with escort ships and battle mechanics, improved travel, smaller ship stat boxes, fading orbital trajectories, black holes, solar panels, and ring worlds.
- **Decision**:
  1. Add `PlayerCharacter`, `ResearchState`, `Outpost`, `FleetShip`, `FactionLeader`, and `WarState` models. Legacy saves receive defaults without changing RNG streams.
  2. Add `character.py` (six skills, six cooldown abilities, aging and XP), `research.py` (prerequisite projects with aggregated bonuses), and `outposts.py` (five outpost types, module production, upgrades).
  3. Add `faction_state.py` with deterministic leaders, behavior archetypes, war declaration/resolution, territory capture, and faction elimination. Player diplomacy supports improve, aid, alliance, ceasefire, and war declaration.
  4. Add `fleet.py` and `navigation.py` for escort classes, formation damage/screening, casualty distribution, BFS multi-jump routing, and black-hole hazard fuel costs. Integrate escorts into combat volleys, damage absorption, evasion, and battle stances.
  5. Add black-hole bodies and ring worlds to galaxy generation, a solar-panel ship upgrade and outpost type, a 44px compact vital-card layout, and radial alpha fade for orbital rings toward the black void.
  6. Surface everything through CLI commands (`character`, `research`, `outpost`, `diplomacy`, `fleet ships`, `route`, `navigate`, `combat stance`), REST endpoints, and cockpit COMMANDER/EMPIRE/fleet-manager panels.
- **Consequences**: The game gains a persistent character/empire layer, dynamic NPC faction wars that can erase factions, escorted fleet combat, and navigation planning. Save-size and per-tick work grow modestly; all new state remains stdlib-only and backward compatible.

### ADR-028: Branching Messages, Quantum Tech, Crew, Weapons, and Megastructures
- **Date**: 2026-10-20
- **Status**: Accepted
- **Context**: The user requested a messaging revamp with branching message trees whose branches produce different outcomes, Dyson spheres, quantum technologies, varied weapons, crew recruiting with character images, a fitting in-game date, and more themed objects.
- **Decision**:
  1. Add `MessageChoice` and tree metadata (`tree_id`, `node_id`, `choices`, `resolved_choice`) to `QuantumMessage`, with `messaging.py` providing three multi-node trees and persistent outcomes (credits, research, crew, standings, weapons, reactor, fuel, cargo).
  2. Add `CrewMember` and `crew.py` with six roles, recruiting, wages, morale, skill-derived bonuses, and procedural SVG portrait IDs. Crew upkeep and morale are simulated each tick.
  3. Add `weapons.py` with laser, kinetic, missile, plasma, ion, quantum, and drone weapons. Combat now uses the selected primary weapon's damage, shield/hull multipliers, and accuracy.
  4. Add quantum research projects (`quantum_entanglement`, `quantum_drive`, `quantum_shielding`, `quantum_weapons`).
  5. Add Dyson spheres, quantum relays, solar-collector swarms, and wormholes as generated celestial objects with science properties, scanning, landing/docking rules, and radar rendering.
  6. Formalize the setting date as 01.01.3042, era "Quantum Age (31st Century)", matching Dyson-scale engineering, quantum drives, ring worlds, and black-hole navigation.
  7. Expose message branching, crew, and weapon management through CLI (`messages tree|choose`, `crew`, `weapons`), REST endpoints, and cockpit message/crew/portrait UI.
- **Consequences**: Messages become a decision system with persistent consequences; crew and weapons add build depth; megastructures and quantum objects give the galaxy a coherent late-quantum-age identity. Legacy saves backfill crew and default weapons without RNG drift.

### ADR-029: Resolution-Adaptive Cockpit, DPR-Correct Radar, Derelict Salvage, Fuel Scooping, and Crew Drills
- **Date**: 2026-10-20
- **Status**: Accepted
- **Context**: The user asked for a VoidFarer UI that adapts to the screen resolution, more mechanics, and bug fixes/improvements. The cockpit used a single 1200px breakpoint, fixed minimum canvas dimensions, no device-pixel-ratio backing store, mouse-only radar input, an unguarded 1s polling loop, and hotkeys that fired behind overlays. Exploration also lacked a high-risk salvage loop, fuel recovery from gas giants/stars, and crew progression beyond recruiting.
- **Decision**:
  1. Add a viewport profile layer (`data-density`, `--ui-scale`) with ultrawide (2200px+), desktop, tablet (1200px), phone (760px/480px), short-height (720px), reduced-motion, and safe-area rules. Base G-001..G-010 rules remain untouched; media queries only adapt spacing and overflow. Settings gain automatic/compact/standard/comfortable density, 85-125% HUD scale, and a live viewport readout.
  2. Make the radar DPR-correct: size the backing store from the CSS rect times `devicePixelRatio`, draw in CSS-pixel coordinates via `setTransform`, debounce resize through `ResizeObserver`/rotation, pause the render loop while hidden, and add one-finger pan plus two-finger pinch zoom with pointer coordinates divided by DPR.
  3. Add `voidfarer/exploration.py` and `CelestialBody.salvage_claimed`, generating one deterministic salvage site per eligible body. `salvage_derelict()` applies sensor/crew-modified risk, credits, cargo, hull damage, reactor heat, and pilot XP, and marks the site stripped permanently.
  4. Add `scoop_fuel()` profiles for stars, gas giants, ringed giants, and ice bodies. Scooping converts sensor power and science skill into fuel while adding reactor heat, creating a thermal-vs-range trade-off.
  5. Add `train_crew_member()` drills with escalating credit cost, skill cap 10, and morale recovery.
  6. Expose all three mechanics through CLI (`salvage`, `scoop`, `crew train`), REST (`/api/salvage`, `/api/scoop`, `/api/crew/train`), and cockpit actions (BOARD DERELICT, SCOOP FUEL, crew DRILL).
  7. Harden client runtime behavior: single-flight 1s state polling, skip polling when hidden, hotkey suppression while overlays/typing targets are active, and modifier-key guards.
- **Consequences**: The cockpit remains usable from small phones to 4K/ultrawide displays with crisp radar rendering and touch input, exploration gains a repeatable risk/reward loop, fuel has an in-space recovery path with reactor heat pressure, crew gain a credit sink and skill progression, and several runtime bugs are removed. Legacy saves default `salvage_claimed=False`; no RNG stream is consumed during model backfill.

### ADR-030: Captain's Log, Discovery Codex, Career Statistics, and Milestone Rewards
- **Date**: 2026-10-20
- **Status**: Accepted
- **Context**: Players had no central discovery journal, persistent career statistics overview, or structured long-term milestone goals spanning exploration, fleet command, commerce, tactical combat, diplomacy, and galactic lore. The simulation already tracked rich metrics (jumps, systems, scans, landings, derelict salvages, fuel scoops, trade volume, earnings, combat victories, anomalies, story progress) but only exposed a subset in disjointed screens.
- **Decision**:
  1. Add `CodexState` model with `claimed: tuple[str, ...]` and `claimed_dates: dict[str, str]`, defaulting cleanly on legacy saves inside `GameState.codex` without consuming any RNG stream.
  2. Add `voidfarer/codex.py` with six thematic categories (`exploration`, `command`, `commerce`, `combat`, `diplomacy`, `legacy`), 28 discovery milestone entries, and 28 deterministic metrics derived directly from the saved universe. Milestones unlock retroactively without separate tracking.
  3. Implement `claim_codex_reward(entry_id)` in `SimulationEngine`, awarding credits and pilot XP, logging to flight log, updating career stats (`scoops`), and atomically updating `CodexState`.
  4. Expose CLI commands `python -m voidfarer.cli log`, `python -m voidfarer.cli codex`, and `python -m voidfarer.cli codex claim <entry_id>`.
  5. Add REST endpoint `/api/codex/claim` in `voidfarer/server.py` and integrate the full codex report in status snapshots.
  6. Add the CAPTAIN'S LOG tab in the cockpit's left vertical terminal rail (`G-003`, `G-008`), featuring a career statistics grid, four-metric summary strip, category filters, animated progress bars, claim buttons, ready notification badge, and milestone chronological flight log.
  7. Add full regression test suite in `tests/test_captains_log_codex.py` and REST integration test in `tests/test_server.py`.
- **Consequences**: Long-term player motivation is reinforced through retroactive achievement rewards and visible career stats across all playstyles. CLI, REST, and cockpit UI maintain full functional parity. Legacy save compatibility is guaranteed by defaulted frozen dataclasses.

### ADR-031: Economy Arbitrage Guards, Hold Overflow Validation, Transit Fuel Efficiency, Combat Polish, and Web Cockpit Arsenal Parity
- **Date**: 2026-10-20
- **Status**: Accepted
- **Context**: An economic exploit permitted same-station buy/sell arbitrage loops when stacking trade margin bonuses (chassis, corp perks, relics). Faction standing discounts/tariffs were missing from raw dynamic market quotes. Depot sales relied on legacy static quotes without mutating local market stockpiles. Ships could downsize chassis, sell cargo modules, or remove cargo bay mods without hold capacity checks, resulting in cargo volume exceeding total capacity. Quantum transit ignored engine fuel efficiency bonuses. Fuel scooping had a fractional skill bug where science skill had zero effect on yield. Combat telemetry masked weapon misfire behind enemy evasion and ignored battle stance modifiers on escort wing volleys. The Web Cockpit also lacked UI for commissioning shipyard chassis, installing weapons, and performing bulk depot transfers.
- **Decision**:
  1. Add local dock purchase tracking (`_local_dock_purchases`) in `SimulationEngine`, clearing on jump or orbit change. Reselling locally purchased goods caps the unit return below buy price, eliminating immediate arbitrage while preserving full trade margin bonuses on imported cargo.
  2. Factor faction standing (-100 to +100) directly into `calculate_dynamic_market_quote` with diplomatic discounts or hostile tariffs, and pass standing in status snapshot quotes.
  3. Wire dynamic market pricing, trade margin bonuses, and local stockpile mutation into `sell_from_depot`.
  4. Enforce strict cargo volume checks in `buy_ship_chassis`, `sell_upgrade`, `install_ship_mod`, and `remove_ship_mod`, rejecting refits if existing cargo volume exceeds the new capacity.
  5. Apply equipment, research, passive, and piloting fuel efficiency bonuses to quantum in-system micro-jumps in `start_travel`.
  6. Support fractional science skill bonuses in `scoop_yield`, making pilot science training properly amplify fuel recovery.
  7. Preserve weapon-specific misfire telemetry in `combat_action` and log stance-modified escort volley damage with active stance annotations.
  8. Upgrade the Web Cockpit ARSENAL tab with a Shipyard Chassis Showroom (`/api/shipyard/chassis`) and Weapons & Ordnance Bay (`/api/weapons/install`, `/api/weapons/set`), add "DEPOSIT ALL" / "WITHDRAW ALL" / "SELL ALL" bulk controls to the Cargo Depot, and style with glassmorphic cards.
- **Consequences**: Economic exploits and inventory bugs are eradicated. Market dynamics, shipyard physics, cargo hold capacity, fuel math, and combat logging are realistic, coherent, and fully verified across 374 unit and regression tests.
### ADR-032: Cockpit Tab Redesign, Visual Ship Configuration, Commander Creation, and Death Flow
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: The holographic cockpit still grouped the commander sheet, ship refits, crew roster, and map controls into crowded legacy tabs. An in-flight redesign split the left terminal into PLAYER, SKILLS, CREW, and SHIP tabs, moved radar settings into the lower-right deck, and added commander creation and death overlays. The first pass was disconnected from the simulation: `app.js` did not parse, ship modules were read from a non-existent array with invented catalog IDs, the crew tab called an unimplemented `/api/crew/assign`, and no server route existed for `/api/ship/module`.
- **Decision**:
  1. Keep the split terminal tabs and map-control relocation, but bind every panel to the authoritative status snapshot: `state.character`, `state.crew`/`crew_bonuses`/`crew_roles`, and `state.ship_mods`.
  2. Render the SHIP tab from the five real structural slots (`frame`, `reactor_core`, `thermal`, `drive`, `ops`) and the `CATALOG_SHIP_MODS` catalogue, with chassis silhouettes, drydock and credit gating, and live capacity/stat telemetry.
  3. Add `POST /api/ship/module` (`module_id`, `action: install|uninstall`) as the cockpit-facing adapter over the existing `install_ship_mod`/`remove_ship_mod` engine methods; keep the legacy `/api/shipmods/*` routes.
  4. Replace the cosmetic crew-assignment prototype with a read-only ACTIVE CREW BONUSES and AVAILABLE ROLES summary derived from `calculate_crew_bonuses` and `crew_catalog`; drills and dismissals remain the only crew mutations.
  5. Extend `SimulationEngine.reset` with an optional commander profile (name, age, background, starting skills) and pass it from `/api/new-game`, so creation choices persist; drop the unsupported gender/race/perk steps rather than storing inert data.
  6. Fix the JavaScript parse error in `charStep`, restore the missing `renderStory` header, and make `checkDeath` idempotent so the death overlay opens once and only at zero hull.
  7. Update the layout regression expectations that encode the old contract: the right deck now also holds map controls, the left drawer starts expanded, the top bar wraps on narrow viewports, and the new PLAYER/SKILLS/CREW/SHIP DOM markers replace COMMANDER/SHIP MODS.
- **Consequences**: The redesign is functional and truthful: every button reaches a real endpoint, every panel reads a persisted field, and all 375 tests pass. The cockpit exposes commander creation and death flows without inventing unsupported attributes or perks. Layout tests now assert the new tab contract instead of the previous single-purpose deck.

### ADR-033: Post-Redesign Correctness Hardening
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: A review of ADR-031 and ADR-032 found five defects: non-laser combat actions crashed with `UnboundLocalError` when the enemy evaded; faction standing was applied twice to purchases because the new quote and the legacy tier multiplier both scaled the price; the same double application let local resale beat the purchase price under friendly standing, reopening the arbitrage loop; `_local_dock_purchases` was cleared by a same-station orbit and leaked across reset/load; and `/api/ship/module` uninstalled by slot, so a mismatched module id could remove a different installed module. The cockpit also bound the sensor scan click twice and rendered ship cargo as unit count instead of hold volume.
- **Decision**:
  1. Define `faction_standing_price_factor` in the economy module as the single source for quote-level standing pricing; engine trade and the CLI market view consume that value without reapplying `calculate_faction_market_modifier`.
  2. Track local dock purchases as `(quantity, total_cost)` and cap resale of local lots at the actual cost basis, not the current quote, so no price movement or margin stack can profit from a same-station round trip.
  3. Move the dock-purchase reset to successful hyperspace execution, clear it on reset and load, and stop clearing it on same-station orbit.
  4. Initialize `weapon_miss = False` before combat branches so drone and subsystem strikes can report enemy evasion safely.
  5. Accept an optional `expected_mod_id` on `remove_ship_mod` and pass the requested module from `/api/ship/module`, rejecting a slot/id mismatch.
  6. Bind quick scan once, reset commander creation between attempts, render the new state immediately, show cargo volume in the ship and depot panels, remove the dead refit panel, and escape portrait initials.
  7. Document the dual legacy rank / fractional bonus contract of `scoop_yield` without changing its call sites.
  8. Persist dock purchase cost basis in `GameState` with a backward-compatible empty default, so save/load cannot clear the guard and reopen same-station arbitrage.
  9. Enforce the cockpit's starting-skill ceiling server-side via `MAX_STARTING_SKILL_TOTAL` (six skills at base 5 plus 20 creation points = 50), rejecting over-budget `/api/new-game` profiles before any state mutation.
  10. Publish the creation budget in the status snapshot (`character_creation`) so the cockpit renders the same base, point pool, max rank, and skill list as the server instead of duplicating constants.
- **Consequences**: Combat no longer crashes on evasive enemies, market quotes and charges agree, the arbitrage guard survives re-orbit and save/load, module uninstall cannot remove the wrong hardware, the cockpit performs one scan per click, and commander creation cannot bypass its budget through the API. The regression suite grows to 386 tests.

### ADR-034: Top Command Strip Layout & Skills Relocation
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: The user requires a single bottom command row between the left terminal and the right corner: reactor distribution on the left, skills in the middle, and radar settings above the tactical flight log on the right. The PLAYER tab still duplicated a skills summary, and the log was too tall. The user also asked for icons, hotkeys, working radar buttons, vertical zoom controls, and for the layout to be recorded in the guide.
- **Decision**:
  1. Place `#hudCommandStrip` as the bottom row of `.cockpit-grid`, spanning columns 2-3 with three equal columns: `panelReactor`, `hudSkillsPanel`, and `hudStripRight`; the left deck spans both rows, so the strip starts beside it and ends at the right corner.
  2. Remove the old right deck. Stack a separate `mapControlsPanel` above `logPanel` inside `hudStripRight`; remove the PLAYER tab's `characterSkills` summary.
  3. Render six icon-bearing quick-skill chips with visible hotkeys (`SHIFT+1..6`), skill points, and a DETAILS link to the full SKILLS tab. Clicking a chip trains it.
  4. Add panel hotkeys (`P` reactor, `K` skills, `L` log) and reactor channel hotkeys (`Q/W/E/R` bump a channel by 5% and rebalance the other channels to keep 100%).
  5. Reduce the strip flight log to 96px and keep its HIDE/SHOW and CLEAR controls. Add circular +, center, and − zoom buttons in a vertical stack with CENTER in the middle; remove the duplicate overlay buttons and the duplicate GRID/LABELS listeners that made those toggles cancel themselves. Use themed SVG cursors for default, pointer, and radar crosshair.
  6. Record the layout in `G-001`, `G-005`, `G-006`, new guideline `G-013`, and README section 19.
- **Consequences**: The map owns the center, the PLAYER tab is a pure dossier, skills are one hotkey away in the bottom strip, radar settings sit above the compact log, and all radar toggles respond once per click. Existing layout tests were updated to the new user-approved contract (PRINCIPLE-014 R2 approval recorded here). The regression suite grows to 393 tests.

### ADR-035: Proper Story Mechanics & the Hollow Between Void Traversal
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: The narrative campaign was a static three-act chain whose choices only granted rewards and reputation: no gating beyond "be in system X", no persistent consequences, no endings, and nothing to do after completion. Meanwhile the game named VoidFarer had no mechanics for traversing the void between stars, despite two black-hole systems existing with only a fuel-hazard role. The user asked for proper story mechanics and void traversing mechanics.
- **Decision**:
  1. Add `StoryRequirements` (required/forbidden flags, minimum reputation, required relics, orbit body) gating both chapters and choices; every locked choice exposes a branch-resolvable reason (G-010) via `engine.story_status()`, `GET /api/story`, and the cockpit.
  2. Persist choice `sets_flags` on `StoryState.flags`; choices can require flags from any earlier act (the Act V title claim requires the Act IV oath; selling the echoes requires the Act I Syndicate leak), and chapter advancement skips flag-ineligible chapters deterministically.
  3. Extend the campaign to five acts (Act IV at the Cygnus Void Gate requires orbiting its event horizon; Act V at The Dark Abyss), append follow-up transmissions per choice, and resolve one of three endings (`ending_first_voidfarer`, `ending_sentinel`, `ending_shadow_broker`) from the flag state; `migrate_story_state` reopens a completed legacy 3-act save into the extended campaign on engine init and load.
  4. Derive a deterministic void-lane graph from the galaxy seed (`generate_void_lanes`): black-hole anchors fully meshed plus two seeded far spokes each, with lane fuel/duration metrics and multi-lane route planning in `navigation.py`.
  5. Add `VoidTraversalState` on `ShipState` (None default, serialized): `void_dive` requires a black-hole orbit, lane reachability, route fuel, and 25% shields; each tick in the Hollow rolls seeded storms that drain stability, shields, and hull; stability collapse force-ejects the hull at the origin horizon; `void_emerge` offers a damaging emergency return that restores origin orbit; arrival grants pilot XP, a first-visit cartography bounty, and stats keys `void_dives`/`void_arrivals`.
  6. Calm the Hollow through story state: the `gateways_open` flag reduces storm chance by 25%, and a new `void_stability` relic passive (Void Compass +20, Crown of Echoes +10) raises starting stability through `calculate_passive_multipliers`.
  7. Expose full CLI/REST/cockpit parity (G-012): `void [status|lanes|dive|emerge]`, `GET /api/void`, `POST /api/void/dive`, `POST /api/void/emerge`, snapshot `void` and `story_status` payloads, a story-tab objectives checklist with locked choice cards, a void traversal panel with dive/emerge controls, and a radar hue overlay while in transit. The engine lock becomes an `RLock` so nested status reads inside `get_status_snapshot` stay safe.
- **Consequences**: Story choices now carry durable consequences that gate later content, the campaign resolves distinct endings, and black holes become traversal gates into a risk-reward void layer. The old three-act completed-campaign test contract changed (campaign now completes at act five with an ending id; the wrong-system rejection message reads "Objectives unmet ... Travel to X System"); those tests were updated to the new user-approved contract (PRINCIPLE-014 R2 approval recorded here). Old saves load unchanged except their story migrates open at Act IV and `_bootstrap_frontier` backfills the Cygnus/Golconda event horizons for saves predating void gates. The regression suite grows to 435 tests.

### ADR-036: Living Crew Morale, Volume-Aware Markets & Cash-Flow Telemetry
- **Date**: 2026-10-21
- **Status**: Accepted
- **Context**: A simulation-mechanics audit found three retention and depth gaps. Crew morale moved only through wages (+0.1/tick paid, -0.8/tick unpaid) with no event reactions, no consequences and no player agency, making the crew a dead stat. Bulk commodity orders executed at a single pre-trade quote while the stockpile shifted only afterwards, so dumping or loading large volumes had zero in-order price impact and bypassed market simulation. The negative baseline wage burn (65 cr/tick against roughly 19 cr of passive income) was invisible in every interface.
- **Decision**:
  1. Crew morale becomes event-driven: combat victory +5, hull breach under fire -4, void storm shear -3, arrival in hostile territory -2, campaign milestone +6 (all clamped 0..100 and logged). Inactive members no longer drift (bugfix).
  2. Unpaid wages below morale 20 can trigger desertion per wage tick (seeded rng, 8% base, capped 50%), with a critical-morale warning at 35. Paid crews never resign.
  3. Paid shore leave at any docked station restores up to 35 morale per active member; cost is 25 cr plus 6 cr per restored morale point, discounted by faction standing repair perks.
  4. Market execution becomes volume-aware: orders execute in slices of roughly an eighth of the local stockpile, recomputing the quote as stock depletes (buys walk the price up) or floods (sells walk it down), reporting average unit price and impact percentage when at least 1%. The existing cost-basis arbitrage guard still caps same-station round trips; single-unit orders keep the legacy message shape.
  5. Cash-flow telemetry surfaces upkeep per tick, passive income (scout drones and outpost credit production) and net flow in the status snapshot, the CLI status deck, and the crew tab.
- **Consequences**: Crew management now has stakes (desertion), a credit sink with agency (shore leave), and feedback from combat, void traversal, hostile travel and story beats; markets punish bulk orders and reward order sizing; players can see and manage their burn rate. No save-schema changes (morale, crew, stockpiles and stats were already serialized); resignation only removes existing entries, and the new snapshot keys are additive. The regression suite grows to 464 tests.

### ADR-037: Progression-Scaled Combat Threat, Honest Disengagement, and Hollow Resonance Risk/Reward
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: A simulation-depth audit of the combat and void-traversal loops found four issues. (1) Procedural intercepts used fixed archetype hull, shield, damage and bounty regardless of Pilot Mastery, so a late-game commander trivialized the same pirates that threatened the starting hull (skill outran challenge, breaking the flow channel). (2) A 30% anarchy roll could spawn a 200-hull Void Warlord Dreadnought against a level-1 100-hull corvette, an unfair early-game spike. (3) `evasive_burn` succeeded without fuel cost and did not reset the expedition streak or tactical combo, so players could escape combat while preserving the 2.5x loss-aversion multiplier the README and ADR-003 promise to reset on disengagement. (4) The Hollow Between only punished storms: it had no variable reward, no reason to push a long lane versus surfacing early, and no partial credit for the risk already taken.
- **Decision**:
  1. Add `enemies.threat_multiplier(level)`: level 1 is flat (1.00x), each later Pilot Mastery level adds 5% hull/shields/damage, capped at +75%. `generate_system_enemy` accepts an optional `threat_level=1`, scales generated stats, scales bounty at 80% of the stat curve, and gates the `warlord_dreadnought` ambush behind level 4. All jump-generated intercepts pass the live mastery level; direct callers without the parameter keep the legacy balance.
  2. Make evasive burn a real disengagement: it costs 3 fuel on success or failure, rejects the action with a clear message below 3 fuel, and on success resets `streak` to 1 and `tactical_combo` to 0. The guaranteed `flee` still costs 8 fuel; the cheaper burn retains its 50-95% failure risk.
  3. Extend `VoidTraversalState` with a backward-compatible `resonance: float = 0.0`. Each storm adds +1 resonance, doubled (an extra +1) while stability is below 30%, rewarding deliberate risk-taking. Safe arrival pays 120 cr and 15 XP per resonance point on top of the fixed arrival XP and first-visit bounty.
  4. Emergency `void_emerge` pays a prorated half-share of accumulated resonance based on traversal progress, so bailing out banks partial value instead of zero; a stability collapse still loses all resonance. `void_status` exposes `resonance`, `projected_resonance_credits` and `projected_resonance_xp`, surfaced in the CLI status/void decks, the story-tab cockpit panel, and the REST snapshot. `stats.void_resonance` accumulates the resonance actually banked (full on arrival, prorated on emergency emergence).
- **Consequences**: Combat now follows the player's growing competence without ambushing new commanders with capital ships, and the streak multiplier is honest about disengagement. Void traversal gains a transparent risk/reward loop: storms are both a threat and the currency of a better payout, long lanes compete with early surfacing, and a partial payout makes the bail-out decision meaningful. Existing saves load unchanged because resonance defaults to 0.0; generated-enemy default balance is unchanged; no third-party dependency was added. The regression suite grows to 476 tests, and the new balance rules are documented in README sections 6 and 13b.

### ADR-038: Survey Completion, Scan Discipline, Salvage Contract Truth, and Finite Volatile Reservoirs
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: A second mechanics audit found four exploration/economy gaps. (1) A scan attempted with zero sensor power still marked the body surveyed and paid no bounty, permanently wasting a one-shot scan; there was no minimum sensor requirement. (2) Scanning every body in a system produced only the individual bounties, with no completion payoff or codex progress, so the exploration loop lacked a natural Zeigarnik goal. (3) The mining contract description promised progress "from fleet drones or salvage", but `salvage_derelict` never advanced it. (4) Fuel scooping was unlimited at every star/gas/ice body: a single body could refill the tanks forever, bypassing station fuel, trade routes, and jump-range planning.
- **Decision**:
  1. `scan()` requires at least 5 MW of effective sensor power before it marks a body. A zero-power attempt returns a routing hint and leaves `scan_completed` false, so no scan is wasted.
  2. Completing every body in a system now awards `SURVEY_COMPLETION_CREDITS` (300 cr) and `SURVEY_COMPLETION_XP` (120 XP), logs `SYSTEM SURVEY COMPLETE`, increments `stats.systems_surveyed`, and exposes `survey` progress (`scanned`, `total`, `complete`) in the status snapshot. The codex gains the `systems_surveyed` metric plus System Surveyor (1 system) and Sector Cartographer (3 systems) milestones.
  3. Successful titanium derelict salvage now calls `_progress_contracts("mining", granted)`, matching the existing mining-contract wording. Non-titanium salvage does not advance that specific contract.
  4. `CelestialBody.volatile_tapped` is an additive serialized counter (legacy default 0). `scoop_reserve(body)` deterministically derives a 3-8 tap reservoir from body type and id. A scoop increments the counter and reports `volatiles n/reserve`; a depleted body rejects scooping with a recharge hint. The tick loop restores one tap per 6 ticks across all bodies. The snapshot scoop payload gains `tapped` and `reserve`, and the cockpit button distinguishes `RESERVOIR DEPLETED` from `TANKS FULL`.
- **Consequences**: Scans can no longer be burned by misrouted power, full-system surveys add a clear completion goal and codex progression, mining contracts now honor their salvage promise, and fuel becomes a local, replenishing resource instead of an infinite free tap. Existing saves load unchanged because `volatile_tapped` defaults to 0; a full reservoir is the pre-ADR behavior until the player begins scooping. First-scoop and existing salvage tests remain valid. The regression suite grows to 483 tests.

### ADR-039: Exact Per-Body Volatile Recharge Scheduling and Corrupt-Counter Clamping
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: Verification of ADR-038 found two residual correctness gaps. (1) Recharge used absolute tick boundaries (`new_tick // 6` vs `old_tick // 6`), so a tap could return anywhere from 1 to 6 ticks after use depending on tick phase. (2) `CelestialBody.from_dict` accepted negative `volatile_tapped` and did not know a per-body recharge timer, so a malformed save could bypass depletion.
- **Decision**:
  1. Add `CelestialBody.volatile_recharge_tick` (default 0, clamped non-negative) as the absolute tick of the next due recharge. The pure `recharge_volatile_reserve(tapped, recharge_tick, current_tick)` helper applies every elapsed interval, including large tick jumps, and clears the schedule when the reservoir is full.
  2. `scoop_fuel` first settles any due recharge, then adds one tap; the first tap schedules `current_tick + SCOOP_RECHARGE_TICKS`, while existing taps keep the oldest pending schedule. The tick loop calls the same helper for every body.
  3. The snapshot scoop payload gains `next_tap_in` (ticks until the next returned tap, 0 when full). Save loading clamps both volatile counters to `>= 0`.
- **Consequences**: Recharge is now exact per body and invariant to absolute tick boundaries; large time steps return the correct number of taps; corrupt negative counters load as full reservoirs instead of permanently depleted ones. The 3-8 tap balance is unchanged. Regressions grow to 486 tests. Existing saves load with `volatile_recharge_tick = 0`, which schedules a fresh interval on the next scoop.

### ADR-040: Cap Corrupt Far-Future Volatile Recharge Timestamps
- **Date**: 2026-10-22
- **Status**: Accepted
- **Context**: ADR-039 added `volatile_recharge_tick` and clamped negative counters on load. Verification then identified the opposite corrupt-save case: a far-future timestamp would keep a body locked for an unbounded time. A legitimate next recharge can never be more than one interval (`SCOOP_RECHARGE_TICKS`) ahead of the current tick.
- **Decision**: `recharge_volatile_reserve` caps any `recharge_tick` greater than `current_tick + SCOOP_RECHARGE_TICKS` to exactly that value before scheduling. Normal schedules are unchanged. A pure-helper regression covers the corrupted far-future case.
- **Consequences**: Corrupt timestamps can no longer lock a volatile reservoir indefinitely; negative and far-future values are both bounded. No schema, balance, or normal-path behavior changes. Regressions grow to 487 tests.

### ADR-041: Opt-In Cockpit UI Guard With a Parsed Inventory Proof
- **Date**: 2026-10-23
- **Status**: Accepted
- **Context**: The cockpit's layout tests pin the HUD structure, but nothing bounded a UI edit to the static surface and its server adapter or proved that controls, handlers, REST calls, routes, hotkeys and theme tokens survived the edit. AIKit already ships an opt-in UI guard (`aikit ui begin/verify/finish`) whose snapshot proof is project-owned and deterministic.
- **Decision**:
  1. Add `.aikit/ui.json` with one `cockpit` surface over `voidfarer/static/**` and `voidfarer/server.py`, protecting tests, tools, docs, memory, launchers and the core simulation modules, with `python -m unittest discover` as the fast proof, `python tools/ui_inventory.py` as the snapshot, `style.css`, `app.js` and the cursor SVGs as theme paths, and 12-file/300-line limits.
  2. Add `tools/ui_inventory.py`: a stdlib-only parser that prints one sorted line per element id, handler, static DOM binding, API call, server route, hotkey, theme token and static asset. It never starts a server or browser, so the proof works offline and on every host.
  3. Add `tests/test_ui_inventory.py` (failing-first coverage of controls, handlers, routes, theme tokens, sorting and deduplication).
  4. Keep `ui_required: false` until the first reviewed cockpit task records surface evidence in `.aikit/ui_history.json`; then flip it so `check --strict` and `publish` enforce the contract. Document the commands and proof in the README.
- **Consequences**: A cockpit task can now be bounded to one surface with a deterministic before/after inventory, a dropped control or handler becomes a hard finding even while the layout tests stay green, and the guard remains opt-in with zero new dependencies. A purely visual regression that keeps the inventory intact is still not caught; human `--reviewed` remains the closing gate.

### ADR-042: Headless Visual Audit and Screenshot Harness
- **Date**: 2026-10-23
- **Status**: Accepted
- **Context**: The UI guard proves scope and inventory, not rendered layout. Contrast, target size, responsive overflow and console errors can regress while the 490-test suite and the inventory stay green, and screenshots alone are not measurable evidence.
- **Decision**:
  1. Add `tools/ui_audit.py`: a stdlib-only developer tool that starts the real cockpit server in-process, copies the static surface into a temporary same-origin wrapper with an error collector and an iframe sized to an exact viewport, then runs headless Edge/Chrome.
  2. Report console errors, horizontal scroll, offscreen/clipped text, text contrast, tap targets below 24px and 44px, missing accessible names, interactive overlaps, fonts, colors, media state and key panel rectangles. Write JSON plus Markdown plus PNG screenshots for `desktop`, `ultrawide`, `tablet`, `phone` and `short`.
  3. Keep it optional: it is not a runtime dependency, not part of the fast proof and not a hard gate. `--check` is opt-in; human `ui finish --reviewed` remains the closing visual gate.
  4. Support two scenarios: `cockpit` closes the startup menu and marks the game started, while `menu` audits the startup menu. Add helper tests for viewport math, wrapper injection and report parsing.
- **Consequences**: Layout, contrast, accessibility and responsive regressions become repeatable measured findings, and screenshots remain available for human review. Without Edge or Chrome the tool exits with `Why:`/`Fix:` guidance. The regression suite grows to 496 tests; the audit is deliberately kept outside the fast proof.

### ADR-043: Windows-Only Command Console UI
- **Date**: 2026-10-23
- **Status**: Accepted
- **Context**: The user directed VoidFarer to be a Windows-only game and rejected the previous neon, multi-device cockpit as poor. G-011 still required tablet, phone, touch, safe-area and cross-device behavior, the package metadata claimed OS independence, and the UI used 8-11px text, mobile breakpoints and a tablet/phone responsive layout that does not serve the Windows target. ADR-042's tablet/phone audit viewports are superseded here.
- **Decision**:
  1. Make the target explicit: rewrite G-011 for Windows desktop 1280x720 through 4K at 100-200% scaling, add G-014 for Windows-only runtime and documentation, change the package classifier to Microsoft Windows, remove the platform branch from console UTF-8 setup, delete touch pan/pinch and mobile/tablet/safe-area CSS, and keep only Windows desktop breakpoints.
  2. Replace the neon skin with a command-console design system: near-black navy panels, ivory text, brass rules and accents, Palatino display headings, Segoe UI interface text, Cascadia Mono data, 12px minimum readable labels, keyboard focus rings and measured tooltips.
  3. Restructure the cockpit for desktop: two-column terminal/radar area with a full-width three-column command dock below it, a fixed target dossier on the radar, a compact chrono deck, a mission-dossier main menu, 28px range hit areas and a 24px minimum interactive target. Move the radar background out of the center panel so fixed positioning fills the Windows viewport without horizontal overflow.
  4. Keep the layout guidelines: the command dock remains three equal columns from the left edge to the right corner, reactor channels stay Q/W/E/R, skills stay SHIFT+1..6, panel toggles stay P/K/L, and the PLAYER tab does not duplicate the skills strip.
  5. Point the visual audit at Windows resolutions only: desktop, laptop, short, ultrawide and 4K. Add clipping/overlay-aware overlap detection and composite translucent backgrounds for contrast so the report measures what the player sees. Update the adaptive UI tests to require desktop markers and forbid touch/mobile markers.
  6. Govern visual review with G-015: `gemma-4-31b` on provider `evren2` (fallback `qwen3-vl-30b`) inspects the Windows screenshots, proves visibility by quoting on-screen text, ranks defects and approves or rejects each pass before any UI work is called complete.
- **Consequences**: The project no longer supports Linux, macOS, phones, tablets, touch gestures or safe-area layouts. The Windows cockpit is readable, fits 1280x720 without page scroll, and the five-viewport audit reports zero errors, horizontal scroll, clipping, offscreen panels, tiny text, small targets, contrast failures, unlabeled controls or overlaps for the cockpit and the desktop menu. The regression suite remains 496 tests; touch and mobile behavior is intentionally gone.

### ADR-044: In-Game Terminal Dossier Redesign
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: Per-tab capture exposed that the in-game terminal, not the menu, was the weak surface. The contracts tab rendered as a narrow right-aligned strip because `.tab-content` had no explicit flex direction, market trade buttons were 23px tall, ship modules and skills used 8-11px copy, arsenal/ship prices failed contrast, crew morale text clipped, and the first in-game vision pass was rejected for a large empty contract void.
- **Decision**:
  1. Make every `.tab-content` an explicit column, keep `.ship-panel` as the one row-wrap exception, give grid containers `width: 100%`, and make tab dossiers sticky with a brass rule.
  2. Turn market into a ledger: sticky headers, zebra rows, compact ghost BUY/SELL actions (26px), cargo/service blocks, and a 12px category line.
  3. Turn arsenal, chassis, weapons, contracts, skills and fleet into responsive card grids that fill the terminal column. Contracts become a two-column gallery at 1920 and a single column at 1366/1280.
  4. Split ship into schematic + statistics + module cards, add breathing room to stat cells, and remove nested scrollboxes so the terminal itself scrolls.
  5. Raise all panel copy to a 12px minimum, fix semantic contrasts, make crew morale bars 16px with 12px text, enlarge portrait initials to 12px, and remove inline font sizes from the cadet reset row.
  6. Verify every tab at 1920 and the key tabs at 1366/1280: zero console, overflow, clipping, offscreen, tiny-text, target, contrast, label and overlap findings. The vision reviewer approved market, arsenal, ship, contracts, quests, factions, codex and messages; the remaining tabs and the perks overlay pass the same measured audit.
- **Consequences**: The in-game terminal now matches the command-console shell in density, hierarchy and controls. Contracts no longer leak outside their column, every panel is readable at Windows laptop and 720p sizes, and the terminal uses one scroll surface instead of nested list scrollboxes. The simulation and test count are unchanged at 496 tests.

### ADR-045: Overlay Dossier Polish and Scenario Capture
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: After the terminal and cockpit redesign, the settings, character-creation and perks overlays still looked like generic dark modals. Per-tab capture also exposed two defects: the audit opened the perks window before `refreshState` finished, and `renderPerksWindow` lacked the catalog fallback used by the mastery tab, leaving the overlay body empty.
- **Decision**:
  1. Give every `.game-window` a brass top rule, layered navy chrome, stronger header band and 18px body inset.
  2. Replace native form controls in settings with 24px custom checkboxes, a custom select arrow, 28px range hit areas, gold/cyan tracks and a readable viewport readout. Raise character labels to 12px and inputs to 32px; raise perk labels and points to 12px.
  3. Make the perks window a 980px three-column branch layout with filled 230px branch cards.
  4. Add `settings` and `character` scenarios to the visual audit and delay scenario/tab opening by 700ms so the async state is ready. Add the same talent-catalog fallback to `renderPerksWindow` that the mastery tab already uses.
  5. Verify settings, character and perks with zero measured findings; the vision reviewer approved all three overlays after the populated perks window was recaptured.
- **Consequences**: The overlays now match the command-console shell, native browser controls no longer break the theme, and the audit can review overlays as well as tabs. The simulation is untouched and the suite remains 496 tests.

### ADR-046: Stellaris Administration Skin
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: The user asked for a proper Stellaris-style UI. The prior Windows command console was readable and stable, but the vision reviewer still saw a generic sci-fi terminal: warm parchment over cyan map, soft geometry and equal-weight panels. Stellaris reads as an imperial administration map: deep void navy, cold ivory data, imperial gold hairlines, a dominant map, a recessed outliner, a selected-object dossier and a segmented command ribbon.
- **Decision**:
  1. Shift the palette to void navy `#040913`, slate panels `#0a1424`/`#0e1a2e`, imperial gold `#c9a35a`, cold ivory `#e9f0f7`, cool text `#c6d4e2`, muted blue-grey `#9fb2c6` and cyan data `#6fc3d7`; use Palatino display, Segoe UI data and Cascadia Mono telemetry.
  2. Replace the top bar with one flat administrative resource strip: brand, actions, six icon/label/value/gauge vitals and chrono as segments divided by gold hairlines.
  3. Make the left terminal a recessed 150px Imperial Outliner rail with a 28px tab rhythm, gold active rule and a sharp panel. Keep the vertical rail, drawer behaviour and every existing tab.
  4. Rebuild the selected-object dossier with a watermark glyph, cold data grid and framed action buttons; turn the bottom strip into a segmented dark ribbon with framed HIDE/CLEAR and beveled BUY/SELL actions.
  5. Add restrained materiality: gold corner brackets, 2px module shells, 1px internal rules, soft black shadows, inner top highlights, a low-opacity starfield/nebula/grid over the radar and a subtle film-grain scanline. No neon bloom.
  6. Preserve every layout and control rule: full-viewport radar, vertical terminal, chrono upper-right, 44px vital cells, three-column command strip, Q/W/E/R, SHIFT+1..6 and P/K/L.
- **Consequences**: The cockpit now reads as a Stellaris-inspired grand-strategy interface and the vision reviewer approved the final cockpit, resource strip, map, market, ship, contracts and menu. Layout and mechanics are unchanged; all 16 terminal tabs and the overlays still report zero measured findings, and the suite remains 496 tests.

### ADR-047: Real Browser Review Driver and Radar Reveal
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: The iframe audit was not a proper visual review: it wrapped the game in a synthetic viewport, its 1-second live poll wiped event popups before capture, and the Stellaris `.deck-panel` gradient was applied to `.panel-center`, covering the full-viewport radar and making the map look like a dead vacuum. Playwright is available with system Edge, so the review can use the real page.
- **Decision**:
  1. Add `tools/ui_browser.py`: Playwright with the system Edge channel, an in-process real server, exact viewports, true page screenshots, console/page/HTTP-error capture, tiny-text and scroll metrics, and cockpit states for target, event and combat. Freeze live polling after injecting event/combat states so the overlay remains visible for evidence.
  2. Keep `tools/ui_audit.py` for iframe layout metrics and inventory proof, but use the browser driver for visual review. Update G-015 to require the real browser, with gemma-4-31b on evren2-5 or NVIDIA Nemotron 3.5 Super VL (free) on Kilo as the vision fallback.
  3. Declare Playwright as a development-only optional extra. The shipped game remains stdlib-only.
  4. Restore a transparent `.panel-center` so the full-viewport radar is visible, then add visible nebula/dust/starfield layers, outliner glyphs, Stellaris-framed event and combat cards, 12.5px target values, roomier market rows, and an empty favicon link to remove the browser 404.
- **Consequences**: Visual review now uses true Edge frames and all review states are reproducible; the central map shows a starfield instead of a covered panel; event and combat overlays are measurable and reviewable. The final real-browser pass reports zero console errors, horizontal scroll or tiny text at all Windows sizes. The suite remains 496 tests and all layout rules remain intact.

### ADR-048: Fit and Sharpen the Galaxy Map
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: Galaxy mode changed the map-mode label but appeared as a blurred empty field. The actual causes were `.panel-center` inheriting `backdrop-filter: blur(16px)` from `.deck-panel`, which blurred the full-viewport radar, plus a fixed galaxy scale and a different scale in the click hit test. The atmosphere overlay also washed out the system nodes.
- **Decision**:
  1. Remove all backdrop filters from `.panel-center` so the full-viewport radar is composited without blur.
  2. Add one `galaxyTransform` used by drawing, hover hit testing and click hit testing. It fits the complete galaxy bounds into 78% width and 68% height at zoom 1, centers the bounds, and scales node radius, labels and hit radius with the radar scale.
  3. Add a `galaxy-view` body class on the GALAXY button and remove it on ORBITS. Galaxy mode hides the extra atmosphere overlay, lowers the grid/scanline opacity, and brightens the canvas.
  4. Draw a dark backing behind each system label so names remain readable over the nebula, and add a Playwright `galaxy` scenario for repeatable evidence.
- **Consequences**: The galaxy map now shows all 15 system nodes, hyperlane connections and labels at desktop, laptop, 720p, ultrawide and 4K; orbital mode is crisp instead of blurred; hit testing and drawing share one transform. The free vision reviewer approved both maps. Runtime remains zero-dependency and all 496 tests pass.

### ADR-049: Categorized Settings Console
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: The vision reviewer called settings the weakest overlay: a sparse single list of toggles and sliders that did not carry the layered console language of the cockpit, menu, character creation or perks.
- **Decision**:
  1. Restructure the settings body into a 150px category rail (DISPLAY / AUDIO / GAMEPLAY / SYSTEM) plus a grouped, scrollable content pane with gold section rules and `//` subtitles.
  2. Keep every existing control ID and binding, but group radar grid/labels, starfield density, HUD density and HUD scale under DISPLAY; sound under AUDIO; travel animation under GAMEPLAY; viewport readout under SYSTEM.
  3. Widen the window to 760px, add an active gold rail marker, reset the active category and scroll position when opening, and add a local-profile status footer.
  4. Verify the overlay with the Playwright browser driver at desktop, laptop and 720p; the free vision reviewer approved the grouped console after quoting its labels and groups.
- **Consequences**: Settings now matches the Stellaris-inspired command console, all controls keep their behavior, and the overlay reports zero console, horizontal-scroll or tiny-text findings. The suite remains 496 tests.

### ADR-050: Defeat Screen Console Treatment
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: The defeat overlay was the last unreviewed surface. It still used a pulsing neon-red card, rounded stat box, 9.6px labels, an emoji icon and a generic modal composition that did not match the Stellaris-inspired command console.
- **Decision**:
  1. Rebuild the defeat window as a sharp 560px console card: red/gold top rule, dark emergency gradient, serif header, red text glyph, 13px message, framed actions and no pulse or glow.
  2. Present six expedition statistics in a bordered 2x3 ledger with 12px uppercase labels and 14px gold monospace values.
  3. Preserve the randomized title/message, all stat sources and the New Commander / Load Save / Main Menu actions.
  4. Add a Playwright `death` scenario and verify the overlay at desktop, laptop and 720p. The free vision reviewer approved the final screen after quoting the title, stat labels and actions.
- **Consequences**: The defeat screen now closes the game in the same visual language as the cockpit, menus and settings; navigation behavior is unchanged and the browser pass reports zero console, horizontal-scroll or tiny-text findings. The suite remains 496 tests.

### ADR-051: Unified Left-Terminal Row Ledger
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: The market was already a scannable ledger, but crew, contracts and fleet mixed cards, role rows, active rows and procurement offers. The vision reviewer rejected the split and asked for one shared row grammar across the left terminal.
- **Decision**:
  1. Use one four-column ledger grid for every left-panel record: leading icon/portrait, title/subtitle, right-aligned value, action. Desktop columns are 40px / 1fr / 100px / 110px; compact Windows columns are 32px / 1fr / 80px / 96px.
  2. Convert contracts to rows with a category glyph, title, description, progress and reward/action column; convert drones, escorts, mercenaries and commissions to the same grid; keep the market table's fixed columns and add numeric alignment and hover.
  3. Wrap active crew buttons into the action column, move morale into the value column, and add a RECRUIT action to available crew roles using the existing `/api/crew/recruit` endpoint.
  4. Standardize row chrome: no cards, left accent by record type, one-pixel separators, 56px target height, hover tint, and consistent icon/label/badge tab rail rows.
- **Consequences**: The left terminal now scans as one system: crew roles and crew members, contracts, active fleet assets, mercenary offers, escort wings and commissions all align to the same columns. Browser audits are zero at desktop, laptop and 720p, the free vision reviewer approved the unified rows, and the suite remains 496 tests.

### ADR-052: Radar Input, Unified Skills Dossier and Bounded Ship Panel
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: The radar settings appeared dead because the command strip is `pointer-events:none`, the map-controls panel was not re-enabled for input, and the full-viewport canvas intercepted clicks. The Skills tab still framed itself as training while a top PERKS button and a left PILOT PERKS tab both opened a duplicate perks overlay. The ship visual expanded to over 2200px because the visual and module grid were laid out outside the 454px terminal column.
- **Decision**:
  1. Raise the top bar, left panel, command strip and footer above the radar (`z-index: 5`), re-enable the map controls and strip panels for pointer input, and sync GRID/LABELS active state and settings checkboxes on load and on every change. All radar controls were then exercised in Playwright, including zoom, reset, map modes, scan and map click-through.
  2. Remove the top PERKS button and left PILOT PERKS tab. Inline pilot perks, talent points and the Precursor Relics vault into the Skills tab; keep six quick-train actions in the bottom strip; make Skills a read-only rank/perk/relic dossier. Delete the duplicate overlay/mastery wiring and update the layout tests and browser tab lists.
  3. Bound the ship panel to its terminal column with a `ship-top-row` grid: a 240px schematic and compact stats card, followed by a full-width module catalog ledger with name/slot, effects/cost and install/remove actions.
  4. Verify the merged Skills tab, the ship panel and all radar controls in the real browser. The vision reviewer approved Skills and the rebuilt ship dossier; Playwright confirmed every radar control changes state and the central map still receives clicks.
- **Consequences**: The radar controls are now usable and visibly stateful; there is one player skill/perk/relic surface with no duplicate entry points; and the ship panel no longer overflows its terminal. Browser audits are zero at desktop, laptop and 720p, and the suite remains 496 tests.

### ADR-053: Unified Transit, Faster Chrono and Cached Radar
- **Date**: 2026-10-24
- **Status**: Accepted
- **Context**: The target card exposed both ENTER ORBIT (an instant `/api/orbit` teleport) and SUBLIGHT TRANSIT (a timed `/api/travel`), so the former bypassed travel and the latter duplicated it. The chrono advanced only one tick per second at 1x, while autosave ran every 10 ticks and could hitch high-speed play. The radar redrew 1,100 stars, nebula gradients and dust every frame, and HUD backdrop filters composited the moving map.
- **Decision**:
  1. Repurpose the orbit action as `TRANSIT & ORBIT`, remove the separate `SUBLIGHT TRANSIT` button, and delete the instant-orbit client path. `start_travel` now rejects same-body trips and second transit orders while a trip is active; arrival automatically establishes orbit.
  2. Keep quantum transit as the premium one-tick option, raise its minimum fuel cost to 2 and its distance rate to 1.0 fuel/AU; sublight remains free but slower.
  3. Set the ticker base to 0.5s and the minimum interval to 0.05s, so 1x is 2 ticks/s and 10x is 20 ticks/s. Autosave is time-based every 15 seconds instead of every 10 ticks.
  4. Cache the static radar backdrop (map gradient, nebula, dust, starfield) in an offscreen canvas, skip drawing while the page is hidden, and remove backdrop blur from the HUD panels that overlay the moving map.
- **Consequences**: The web UI no longer teleports into orbit and exposes one clear transit choice; the chrono is twice as fast at every preset with a meaningful quantum fuel trade-off; radar draw time drops to ~0.08ms with 60 FPS in the real browser. The suite grows to 499 tests.

### ADR-054: In-System Transit Hazards, Course Plotting and Pre-Flight Risk Preview
- **Date**: 2026-10-25
- **Status**: Accepted
- **Context**: Following the timed transit unification in ADR-053, navigation lacked situational awareness prior to launching: players could not preview travel duration or fuel requirements before clicking, environmental hazards from sector modifiers were uncalculated during travel, and the radar lacked visual vector cues connecting destination bodies.
- **Decision**:
  1. Add `SimulationEngine.preview_travel()` and `_transit_risk()` computing duration, fuel expenditure, hazard names and bounded risk percentage (3% to 45%) mitigated by piloting skill, evasion stats and quantum transit.
  2. Integrate transit hazards into `SimulationEngine.start_travel()`: hazard impacts inflict deflector and hull abrasion, cause arrival delays (+1 tick), and spawn persistent `GameEvent` notifications and flight log entries.
  3. Implement `POST /api/travel/preview` in `server.py` exposing sublight and quantum calculations.
  4. Render an interactive `#transitPlan` card in the target dossier with color-coded risk indicators, ETA and fuel metrics, and hazard descriptors, alongside a dashed `COURSE PLOT` transit vector on the orbital radar canvas.
  5. Tighten dossier vertical dimensions and resource tag typography (>=12px) for DPR-correct, unclipped rendering across 720p, laptop and 4K viewports with zero console findings.
- **Consequences**: Navigation delivers tactical depth, transparent travel economics, and emergent sector hazard tension; real-browser automated audits verify zero console, horizontal overflow or sub-12px text defects; the test suite expands to 502 automated tests.

### ADR-055: Left Terminal Ledger, Trade Cost Basis with Max Orders, and Settings QoL
- **Date**: 2026-10-25
- **Status**: Accepted
- **Context**: In the left terminal, the outliner label wrapped over PLAYER, the market and player tabs both showed on load, and the four-column ledger grid left ~150px for record names in the ~450px drawer, so contract titles ran into progress bars and mercenary names wrapped word by word. Trading moved one unit per click with no record of what cargo cost, and settings exposed only seven options with no key reference or reset.
- **Decision**:
  1. Only the PLAYER tab is visible before scripts run; `[`/`]` cycle `TERMINAL_TABS`, `\` toggles the drawer, and the last tab is remembered (`rememberTab`, `lastTab`).
  2. A final style layer gives contract, drone, mercenary, escort and procurement rows a three-column `--ledger-record-cols` grid (icon | name over detail | value over action); crew rows keep `--ledger-cols`. Contract descriptions move to a tooltip; FACTIONS & CORPS is labelled FACTIONS.
  3. `ShipState.cargo_cost` records credits paid for the units still held (empty default for old saves). Buys add to it, a buy into an emptied hold resets it, and sells release cost pro rata and append `P/L +/-N cr`.
  4. `SimulationEngine.max_trade_quantity()` binary-searches the slice-priced buy cost (`_bulk_buy_cost`, shared with `trade`) against credits and free volume, or returns all held units for sells; `trade_max()` executes it. Parity: REST `/api/trade` `max: true`, CLI `buy <id> max` / `sell <id> all`, REPL `max`/`all`, snapshot `max_buy` per quote and `cargo_avg_cost`.
  5. The commerce tab gets an x1/x5/x10/MAX order lot bar (persisted), clamped `BUY n`/`SELL n` labels, Shift+click for max, `@avg` cost and green/red sell margins.
  6. Settings move to a `SETTINGS_DEFAULTS` table with RESET DEFAULTS, and add master volume (one master gain node for every voice), auto-pause on a new hostile intercept or event, auto-claim of finished contracts, default order lot, the remembered-tab toggle, and a CONTROLS key reference.
- **Consequences**: Left-terminal records no longer collide at 1920x1080; bulk trading is one click with honest profit feedback across REST, CLI and cockpit; settings persist in `voidfarer_settings` with backward-compatible keys. The suite grows to 524 tests (31 suites); a real-Edge smoke run passed 13/13 runtime checks.

### ADR-056: Cached Catalogs, Chrono-Paced Polling and a Command Strip That Fits
- **Date**: 2026-10-25
- **Status**: Accepted
- **Context**: Every 1 s poll shipped a 133 KB snapshot, ~40 KB of it code-constant catalogs, while 10x speed runs 20 ticks/s, so the HUD jumped 20 ticks per update. Each poll rebuilt the open terminal tab, which could swap a button between pointerdown and pointerup and drop the click. Every strip panel was capped at `max-height: 210px`, clipping the SENSORS/WEAPONS sliders, presets and APPLY ROUTE at every resolution; sliders only applied through that hidden button, so mouse power routing did nothing. Below 1600px the strip spanned the full width under the terminal (~320px tall), leaving the terminal 153px at 1280x720 against G-005 and G-013.
- **Decision**:
  1. `STATIC_SNAPSHOT_KEYS` and an `lru_cache` `static_catalogs()` hold the 14 code-constant catalogs; `get_status_snapshot(include_static=True)` merges them, `GET /api/catalogs` serves them, and a request carrying `X-VoidFarer-Catalogs` gets every `state`/`data` snapshot without them. The default payload is unchanged.
  2. The cockpit loads catalogs once, routes all 34 API calls through `apiFetch`, and its `state` setter merges the cache back. A `schedulePoll` cadence replaces the fixed interval: 1000 ms paused, 500 ms at 1x, 333 ms at 2x, 250 ms from 5x.
  3. `terminalBusy()` skips the open tab's rebuild while a pointer is pressed in the terminal or a control there has focus; the story tab renders the void panel once per poll.
  4. The strip sits beside a full-height terminal at every width, panels are uncapped, and sliders and presets commit on release when the total is at most 100% (APPLY ROUTE remains as a retry). Below 1600px the strip compacts: short titles, VENT on the heat row, single-column skills, stacked market trade buttons and fixed market columns.
  5. The streak card shows the count with the multiplier in its subline; sector chips sit top-left of the radar; the PLAYER XP label is 12px.
- **Consequences**: Lite polls are 86 KB instead of 133 KB and full snapshots build in ~1.1 ms instead of ~2.1 ms; at 10x the HUD refreshes ~3.5 times a second at 60 FPS with no long tasks. The terminal grows from 153 to 480px at 1280x720 and from 201 to 528px at 1366x768, and no strip control is clipped at 720p, laptop, desktop or 4K. Real-Edge runs pass 5/5 power-routing checks at 1080p and 720p and 8/8 polling checks. The suite grows to 538 tests (32 suites).

### ADR-057: Grand-Strategy Layer: Fronts, Territory, Celestial Models and a Monthly Treasury
- **Date**: 2026-10-25
- **Status**: Accepted
- **Context**: The user asked for a Stellaris-like grand strategy feel with simulation mechanics. Wars were coin flips (score +/- uniform(-3, 5)) that, once past 12, captured a system every tick because the score never reset; captures ignored geography; wars never ended; population dominated faction strength. Over 3,000 ticks Sol Coalition took all 15 systems on every seed. The galaxy map showed no ownership, worlds were flat dots, outposts had no UI, and crew wages were charged in full every 0.25-day tick, bankrupting a new commander (2,000 cr, 65 cr wage bill) in 40 ticks, 20 seconds at 1x.
- **Decision**:
  1. War resolution: score = score x (1 - 0.05 attrition) + momentum + uniform(+/-2.5). Momentum = 3 x (effort difference / sum) with containment (-1.2 against a 40%+ hegemon) and last stand (0.6 per missing core system). War effort = (100 x systems + 60 x log10(1 + population in millions)) / (1 + 0.35 x systems beyond 3). Reaching 12 captures one hyperlane front system (`frontier_systems`) and spends 12; capitals need 24 and fall last; no shared border stalls the offensive. Treaties end wars after 240 ticks or 3 captures; a 600-tick truce follows; a defending faction cannot be attacked a second time; declarations roll at 2.5% per tick.
  2. `WarState` gains `captured_systems`, `ended_tick` and `support` (backward-compatible defaults). `support_war` lets the player pledge credits (minimum 100; shift up to 6 at 400 cr per point; standing up with the backed side, down with its enemy) via REST `/api/war/support`, CLI `war list|support` and cockpit BACK buttons. `galactic_politics` exposes owners, borders, fronts and powers in the snapshot.
  3. The galaxy map renders cached, quarter-resolution Voronoi faction territory with blurred borders, border-crossing lanes, pulsing red front lanes, owner rings and a powers legend, fitted to the visible map area via a shared `mapRect`/`mapCenter`.
  4. New `static/celestial.js` (`CelestialRenderer`) paints seeded, cached models for all 21 body types, star coronas, asteroid belt bands, moons, a star-facing terminator and the flagship silhouette; body display size is logarithmic in radius and shared with hit tests.
  5. Crew wages are a monthly rate accrued on the calendar (`wages_due`, 30-day months); a MONTH END report logs payroll and treasury; `cash_flow` reports per-month keys (the existing cash-flow test now asserts the same values under `*_per_month`). The Empire tab founds outposts for the orbited world, and the credits card shows net cr/month.
- **Consequences**: Over 3,000 ticks on six seeds wars capture 13-26 systems with no eliminations and no faction above 4 of 15 systems; the map reads as a living political map; worlds and stations are recognisable at a glance; a new commander pays 65 cr/month. Known follow-up: outposts still yield per tick (a mining outpost earns ~1,200 cr/month against an 1,800 cr cost) and want a monthly rebalance. Territory rebuild costs 4.6 ms at 1080p and 7.9 ms at 4K; frames stay at 0.1-0.3 ms. The suite grows to 565 tests (34 suites).

### ADR-058: Ability Bar, Ability Progression and a Measured Balance Pass
- **Date**: 2026-10-25
- **Status**: Accepted
- **Context**: The bottom strip trained passive skill ranks with SHIFT+1..6 although the design calls for the commander's activatable powers there. Two of six abilities (`charm_offensive`, `trade_instinct`) were unreachable from any save, Reactor Overclock only switched to a reactor mode the player could already select, and measured play showed a degenerate economy: outposts repaid their cost in 1.0-1.5 months against a 65 cr/month wage bill, while a fresh corvette destroyed a corsair in three shots without losing hull.
- **Decision**:
  1. The bottom strip becomes an ability bar: the six powers render in `SHIFT+1..6` order with icon, READY / CD n / LOCKED state and a cooldown bar; clicking or pressing the hotkey uses the power. Tagged powers target the current system's sovereign faction. Skill training stays in the SKILLS tab, `character train` and the dossier.
  2. `charm_offensive` unlocks at Diplomacy rank 7 and `trade_instinct` at Trade rank 7; the base four remain innate. `reconcile_abilities` runs on creation and load as well as in `train_skill`, so commanders created or saved above the threshold receive the unlock instead of being stranded at max rank.
  3. Reactor Overclock is a timed surge: +25% subsystem output for 8 ticks on a 20-tick cooldown at +12 heat, carried by defaulted `ReactorState.surge_ticks`/`surge_bonus` fields instead of switching mode. Ability yields are rebalanced to `trade 20+6*rank` (620 cr/month at rank 7), `science 6+2*rank` (240 points/month), `emergency repair 10+3*rank` (372 hull/month) and `charm 3+rank` (100 standing/month).
  4. Outpost credit yields fall to 3.0 (mining), 2.0 (research), 3.0 (solar), 3.0 (shipyard) and 4.0 (colony) whole credits per tick with 1.0-2.0 secondary goods; payback is 3.9-9.2 months. Upgrades cost `450 x level` and add 25% effective production through level scaling instead of compounding into stored yields, so old saves receive the new catalog too and single-tick yields no longer truncate.
  5. Early hostiles gain real threat: Corsair 70 hull / 25 shield / 24 damage, Marauder 105 / 50 / 30, Enforcer 125 / 65 / 30, Sentinel 150 / 90 / 40, Dreadnought 240 / 120 / 48. A fresh corvette using only lasers now finishes a marauder at 25-45 hull, while a hostile-territory Enforcer can be lethal.
  6. Reaching 0 hull is terminal on every path: `fire_lasers`, `shield_absorb` and `evasive_burn` end combat through one `_combat_defeat` helper that keeps escorts, breach crew and streak, awards no bounty, and pauses time; `tick()` refuses to advance and abilities refuse to fire while the hull is 0. The cockpit acknowledges death once, pauses the server clock, blocks hotkeys behind the death/creation overlays, shows failures in the un-collapsed `aria-live` log, and skips ability/skills rebuilds while a control holds focus or a pointer is down. Reactor surge decays once per combat action so paused fights cannot keep it forever, and `reconcile_abilities` also runs for state passed to the engine constructor (CLI and tools).
- **Consequences**: The most-used strip is a tactical ability bar instead of a second trainer; all six powers are reachable through play and old rank-7 saves reconcile on load; overclock is a burst rather than a mode shortcut; outposts are a 3.9-9.2 month investment with non-truncating whole-credit yields; early combat costs hull, 0 hull is a defeat without bounty, and preparation matters. Skill training remains in the SKILLS tab with per-skill TRAIN buttons, because the strip no longer trains. The suite grows to 586 tests, adding unlock reconciliation in creation/load/constructor, old-save outpost yields, effective upgrade scaling, cooldown-safe failures, lethal defensive actions, terminal death, and per-turn surge decay.

### ADR-059: Away-Team Expeditions, Crew Injuries and Field Progression
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: Crew were passive bonus sources: recruiting and drilling were the only decisions, morale only drifted, and a body's exploration ended after one scan, landing or salvage. The user asked for more depth and new mechanics that complement the existing loops. The game needed a repeatable but non-farmable risk/reward activity that turns orbital position and specialist composition into choices, and uses the existing morale, wages, contracts, research, cargo, faction and codex systems.
- **Decision**:
  1. New `voidfarer/away.py` defines five body-gated expeditions: Geological Survey (1 science, 6 ticks, low risk), Salvage Sweep (2 engineering, 8 ticks), Xenobiology Study (2 science, 10 ticks), Colony Relief (2 medical, 5 ticks, population-gated) and Distress Sweep (3 combat, 7 ticks). Risk is base + body hazard + gravity deviation - team fit, clamped 3-70%; fit rewards matching specialty and role, and injured crew contribute zero.
  2. `CrewMember` gains defaulted `xp` and `injury_ticks`; `ShipState` gains defaulted `away_missions` and `away_completed`. Old saves load unchanged. A successful expedition marks `body_id:mission_type` as worked, so a site cannot be farmed by repeating the same mission and players are pushed to fresh bodies; failed sites can be retried.
  3. `launch_away_mission` accepts an optional explicit team but defaults to the deterministic best-fit team, rejects combat, transit, void, injured, assigned and insufficient crews, caps two simultaneous teams, and `recall_away_mission` returns a team without reward. Assigned crew stop contributing ship bonuses while away.
  4. Tick resolution is deterministic from the save seed, mission id, body, crew ids and start tick. Outcomes award credits, research, cargo (using display names), faction standing, morale, contract progress and crew XP; failures injure 1-2 specialists for 8-16 ticks and cost morale. Expedition XP promotes skill at `skill x 40`, and an active medic doubles injury recovery.
  5. Parity is complete: snapshot `away_report`, GET `/api/away`, POST `/api/away/launch` and `/api/away/recall`, CLI `away list|launch|recall`, crew rows show XP and injury status, and the CREW tab splits into ROSTER and AWAY TEAMS sub-views so the roster stays primary. Blocked missions show why; a worked site reads `Site already worked`.
  6. The codex gains the `away_missions` metric and the Field Team milestone (5 expeditions).
- **Consequences**: Crew composition, body position and expedition timing now matter beyond passive bonuses; injuries create a real medbay/time trade-off; specialists can rank up in the field; and successful sites deplete so the loop rewards exploration instead of idling. REST, CLI and cockpit share one report. Real-Edge captures at 1920x1080, 1366x768 and 1280x720 pass with 0 errors, 0 horizontal scroll and 0 sub-12px text; navy-and-gold styling is preserved, and the vision review forced full title wrapping, compact two-column mission rows, display-name cargo, `ETA nT`, and an `N/A` risk pill when no healthy team exists. The suite grows to 602 tests (35 suites).

### ADR-060: Frontier Depth: Pirates, Blocking Decisions, Quantum Freight, Surface Ops and War Devastation
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: The user asked for more systems and factions, pirates and pirate encounters, more anomalies and anomaly encounters, more counters and missions, a deeper quest-mission loop, quantum trading with delivery time and fees, real landing mechanics, blocking real-time decision events (>=25), an outliner that ends at its last row, and realistic population death plus war devastation.
- **Decision**:
  1. **Galaxy**: eight frontier systems (Kepler, Helios, Ashen, Meridian, Vela, Lyra, Draco, Phoenix) join the map at 23 total; four factions (Kepler Concord, Helios Compact, Ashen Choir, Iron Meridian) and two corporations join at 9 factions total. Legacy markets keep the original RNG stream; frontier markets use a separate derived RNG so old balance tests and saves stay stable.
  2. **Pirates**: `pirates.py` defines five bands and a deterministic toll encounter with pay/fight/evade actions. Risk rises in pirate havens, corsair territory, low-security systems, hostile standing and falls with escorts/evasion. The encounter is savable, blocks flight until resolved, starts normal combat on FIGHT, and feeds the new `pirates` contract category.
  3. **Anomalies**: six new catalog entries (ghost ship, helium storm, precursor library, pirate lure, crystal bloom, Meridian convoy) bring the catalog to nine. Any successful scan has a stable 10% contact chance; contact uses the existing choice resolver.
  4. **Decisions**: `decisions.py` defines 35 conditional blocking events across tick, jump, scan, orbit, trade and land triggers. Only one may be pending; `tick`, flight and server POST actions return conflict until `resolve_decision` applies credits, fuel, hull, cargo, morale, research, standing, heat or injury effects. The cockpit shows an uncloseable modal with the lock line.
  5. **Missions & counters**: contract templates cover pirates, delivery, surface, anomaly and diplomacy; the starter board has five contracts and `refresh_contracts` rerolls all five across every category for 120 cr. New HUD counters and codex metrics cover pirates, decisions, deliveries and surface ops.
  6. **Quantum freight**: `TradeOrder` moves owned cargo to a destination market for a fee, reserves the freight slot, and pays the arrival market price after 2-12 ticks. Delivery marks stock, credits the ship, and advances delivery contracts. The commerce tab places the board above the local market; it shows six best lanes with fee/net/SHIP.
  7. **Surface ops**: landing opens five deterministic choices (survey, deep core, ruins, wreck salvage, field rest). Each branch is one-time per body, costs credits/heat or hull risk, and feeds surface contracts. Population generation now scales core worlds to billions and stations to hundreds of thousands; `devastation` raises mortality, suppresses growth and decays over time. War captures kill 1.8-5.2% of civilians and add 14-28 devastation.
  8. **Outliner**: short viewports use 24px tab rows so all 16 tabs, including CAPTAIN'S LOG, reach the last row; the rail uses `height: auto; max-height: 100%` so it ends at its last row instead of stretching beyond it.
- **Consequences**: The map, encounter texture, economic logistics and war consequences now have substantially more depth. Decisions enforce attention without deadlocking: REST conflict, CLI guard, and the modal all agree; `/api/decision/resolve` and CLI `decision choose` are the only escape. The mission board exposes the new categories instead of hiding them behind same-category replacement. The suite grows to 621 tests (36 suites). Real Edge captures at 1920/1366/1280 report zero console errors, zero horizontal scroll and zero sub-12px text; focused vision reviews approved the quantum board, surface ops, pirate toll, decision modal and compact outliner after moving the freight board above the local market and compacting short-viewport tab rows.

### ADR-061: Frontier Depth Post-Review Hardening
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: A review of the uncommitted frontier changes found interaction gaps beyond the feature work: pirate encounters could be overwritten by a second jump, direct API/CLI actions could slip past an active encounter, surface cargo showed raw item ids, and the quantum-freight board could be taller than a 1366x768 terminal when scrolled into the center of the viewport.
- **Decision**:
  1. Pirate generation is gated by the same gameplay-events flag as decisions, so deterministic unit tests and legacy direct-engine callers keep the old jump stream. The live server, REPL and cockpit still enable it.
  2. `active_pirate` now freezes `tick`, `jump`, `orbit`, `start_travel`, `scan`, `trade`, `scoop_fuel`, `land_on_body`, `salvage_derelict`, away launches and surface operations until pay/fight/evade. The HTTP layer returns 409 for all other POSTs, the CLI guard blocks one-shot commands, and the cockpit keyboard handler treats both decision and pirate cards as blocking overlays.
  3. Surface operation cargo rows use inventory display names in both the report and the grant log; the UI no longer leaks ids such as `microchips`.
  4. The quantum board is rendered above the local commodity table and limits to four best routes below 1500px width, so its header stays visible at 1366x768. Natural (unscrolled) Edge captures were used for final review; the earlier cropped laptop image was a capture-scroll artifact, not a layout bug.
- **Consequences**: Encounter state can no longer be bypassed by another action, item names remain consistent across away/surface/freight surfaces, and the freight board stays readable at the smallest supported desktop. Suite: 623 tests (36 suites). Final graphical review approved the natural 1920/1366 freight board, surface operations, pirate card, decision modal and compact outliner.

### ADR-062: Post-Push Audit Hardening
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: A second audit of the pushed frontier work checked interaction gaps and graphical placement. It found that HTTP conflict responses lacked a `message` and returned no state, several new cockpit handlers assigned that absent state, the REPL bypassed the decision/pirate guard, landing double-counted the surface contract, benign field-rest rolls could still be hazardous, and unpopulated bodies accumulated devastation.
- **Decision**:
  1. `_send_error_json` now returns both `message` and `error`; blocked decision/pirate responses also include the current state snapshot, so legacy handlers and new handlers stay coherent.
  2. Quantum freight, surface operations, pirate choices and decision choices only replace cockpit state when the response contains one.
  3. The REPL now honors the same decision/pirate lock as the HTTP API, except for status, decision, pirate, save, serve, time, help and quit.
  4. Landing no longer advances the surface contract; only an actual surface operation does. Field Rest is risk-free, and unpopulated bodies no longer gain devastation from a capture.
  5. Initial faction and corporation standings now include the four frontier factions and two frontier corporations. The unused Sol population special case was removed.
  6. Contract cards expose the full title plus description on hover so ledger ellipsis does not hide intent.
- **Consequences**: The new encounters cannot be bypassed through a second UI path or REPL command, state stays valid on 409 responses, and surface contracts reflect real operations. Graphical review confirmed the 23-system galaxy view is readable at 1920/1366/1280, all nine faction cards are present and scrollable, the freight board and surface panel fit the gold/navy console, and the apparent clipped rows were normal panel scrolling. Suite: 623 tests (36 suites).

### ADR-063: Guaranteed Anomaly Exit and Long-Run Stress Verification
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: A 1,200-tick simulation with live decisions, jumps, pirates, anomalies and combat exposed three older anomalies whose every choice required a reactor power threshold. A later audit also needed a guard against future additions repeating that pattern.
- **Decision**:
  1. Every anomaly catalog entry now includes a `required_power: none` retreat/withdraw choice. Derelict Dreadnought, Tachyon Rift and Pirate Lure Beacon received explicit escape branches.
  2. A catalog test enforces one power-free escape per anomaly, so a future anomaly cannot strand a low-power ship.
  3. A 1,200-tick deterministic stress run with live encounter events produced no invariant violations: credits/fuel/hull stayed non-negative, populations stayed non-negative, and all 23 systems remained present through 16 wars and repeated decisions.
- **Consequences**: Active anomalies cannot deadlock flight through unmet power gates; failed checks still cause their intended hull damage and clear the encounter. Suite: 623 tests (36 suites).

### ADR-064: Last-Ten-Commit Audit and Source Encoding Cleanup
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: The user asked for a commit-by-commit verification of the last ten pushes. The audit covered the frontier feature commit, the freight-label fix, the UI evidence/map/task bookkeeping commits, the post-push hardening commit, the accessibility commit, the anomaly-escape fix and its bookkeeping. Besides logic checks, a text scan found mojibake introduced in the crew morale labels and older cockpit/server banner strings.
- **Decision**:
  1. Replace corrupted `⚠`/`|`/emoji sequences in `cli.py`, `static/app.js` and `server.py` with ASCII-safe labels (`!! NEAR DESERTION`, ` / `, `[COSMIC TIME]` text).
  2. Add a source-encoding regression test that scans all Python modules and the three cockpit static files for common mojibake markers. Generated ADR history is deliberately excluded.
  3. Reconfirm the feature and hardening commits: 623 tests pass, 4/4 gates pass, the 1,200-tick live-encounter stress pass remains clean, all 23 systems stay connected, all 9 factions are present in the roster, all 9 anomalies have a power-free exit, and cockpit panels match the gold/navy theme at 1920/1366/1280.
- **Consequences**: Player-visible text no longer contains encoding damage, and future source edits that reintroduce it fail the suite. The last ten commits are audited as feature, UI evidence, map/ledger, hardening, accessibility, anomaly-escape and bookkeeping changes with no remaining invariant failures. Suite: 624 tests (36 suites).

### ADR-065: Frontier State Serialization Round-Trip Coverage
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: The last-ten audit verified the individual mechanics and UI, but the combined persistence path for the new blocking decision, pirate encounter, away mission, quantum freight and surface-operation fields was not covered by one regression test.
- **Decision**: Add a single save/load round-trip test that constructs an engine state with a pending decision, active pirate toll, decision history, away mission and completed site, in-transit trade order, and worked surface branch, then reconstructs the `GameState` and asserts every field survives.
- **Consequences**: The new state surface is verified as JSON-safe and backward-compatible with the existing `from_dict` paths. Suite: 625 tests (36 suites).

### ADR-066: Legacy ADR Register Encoding Normalization
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: The encoding audit found old ADR lines with double-encoded dashes, arrows and ellipses. The new source test covered code and static assets but only required the ADR register to decode, not to be marker-free.
- **Decision**: Normalize the legacy ADR punctuation to ASCII (`--`, `->`, `...`), add the ADR register to the mojibake-marker assertion, and verify the low-morale crew label in a real Edge capture (`10 !! NEAR DESERTION`, no corrupted glyphs).
- **Consequences**: Documentation is consistently UTF-8 and free of the known mojibake markers; the encoding regression test now covers the full source tree and ADR register. Suite: 625 tests (36 suites).

### ADR-067: Cockpit Layout Corrections from Image Review
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: Natural 1366x768 and 1280x720 captures showed the crew morale line competing with the role/XP line, and quantum freight route metadata squeezing FEE/NET/SHIP into narrow columns. The crew roster also sat below shore leave and role recruitment, hiding the actual people first.
- **Decision**:
  1. Give each crew row a dedicated second line for the morale bar, keep the portrait spanning both rows and the action column aligned, and allow the role/XP/status line to wrap instead of clipping.
  2. Order the roster as cash flow, roster, shore leave, then assignments/roles, so the people lead the tab.
  3. At widths below 1500px, stack quantum route metadata under the commodity/destination line and keep SHIP plus NET on the second row.
- **Consequences**: Natural captures at 1366 and 1280 show `engineer | SKILL 3 | XP 0/120` and `!! NEAR DESERTION` in full, with aligned portraits/actions, and readable freight rows (`Titanium Alloy x8`, destination, `3J / 9T`, FEE, NET, SHIP). The free vision reviewer approved both panels and the gold/navy theme. Suite: 625 tests (36 suites).

### ADR-068: Deterministic Browser Surface Captures, Stacked Narrow Contract Headers, Proportional Reactor Strip, and Center-Bounded Target Dossier
- **Date**: 2026-10-26
- **Status**: Accepted
- **Context**: Post-push visual inspection at 1920x1080, 1366x768, and 1280x720 exposed four cockpit polish issues: (1) automated Playwright Edge screenshots could be interrupted by random tick decision modals and lacked a landed `--scenario surface` state; (2) below 1600px width, contract category pills competed horizontally with contract titles and clipped mission names; (3) the compact reactor strip clipped `OVERDRIVE`/`SILENT` and the `100% ALLOCATED` header at 1366x768 and 1280x720; and (4) `position: fixed` on `.nav-target-card` allowed the expanded surface-operations dossier to collide with the onboarding banner above and the command strip below, while 3-line surface operation rows overflowed vertically at 1280x720.
- **Decision**:
  1. Extend `tools/ui_browser.py` with `--scenario surface` (`_prepare_surface`), pause server simulation time and disable random decision events during automated captures, and dismiss arrival events via `engine.dismiss_event(event.id)`.
  2. Render both full and 3-letter category codes (`EXP`, `COM`, `MIN`, `TRD`, `DLV`, `PIR`, `SRF`, `ANO`, `DIP`, `FLT`) in contract badges, stack `.contract-card > .contract-header` vertically below 1600px, and unclamp `.contract-title` so contract names never truncate.
  3. Give the compact reactor strip proportional 4-column doctrine tracks (`1.12fr 1.12fr 1.22fr 0.82fr`), hide `.pwr-icon` and `.hud-command-strip .skill-quick-icon`, and prevent `.panel-title` from shrinking so `REACTOR [P] 100% ALLOCATED [HIDE]`, all four doctrines, `VENT`, and `Battle Focus` render intact across all viewports.
  4. Anchor `.nav-target-card` with `position: absolute` inside `#panelCenter`, move the `NAV-RADAR` watermark header to the top-left of `#panelCenter`, lay out `.surface-op-main` as a 2-line flex row (title + reward on line 1, description on line 2), and scroll `.nav-target-card` directly when `#surfaceOps` opens.
- **Consequences**: Real-browser Edge captures at 1920x1080, 1366x768, and 1280x720 across `contracts` and `surface` scenarios pass with zero errors, zero horizontal scroll, zero tiny text, zero cross-panel overlap, and full legibility of all five surface operations and contract titles; approved by G-015 vision review. Suite: 628 tests (36 suites).

## Licensing migration (2026-10-26)

- New versions use the Aegean Game License 1.1 (AGL-1.1).
- Rights holder: AegeanWorks; commercial use under ACL-1.0.
- Counsel review of the 1.1 texts remains pending.

### ADR-069: Area-and-Tech Demographics, Wartime Attrition, Faction Treasuries, and a Dyson Swarm
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: World populations were hard-coded per system index, so a 149-million-kilometre Dyson sphere carried 2.4 billion people while an Earth-sized colony carried a similar figure, and nothing stopped growth or linked it to habitability or technology. War only displaced people at the instant of capture. Factions had standing and strength but no treasury, income or upkeep. The Sol megastructure rendered as an opaque wireframe globe and sat on a planetary orbit.
- **Decision**:
  1. Add `demographics.py`: capacity derives from body surface area (or artificial habitat volume), a body-type land factor, habitability^1.8, and a faction tech multiplier; every world stores `population_capacity` and `tech_level`. Opening population is a faction occupancy share of that capacity.
  2. Replace per-tick growth with closed-form logistic growth, so large `tick(n)` batches converge on capacity instead of overshooting; deaths from devastation reduce the effective ceiling and add a mortality term.
  3. Apply continuous front attrition in `apply_war_devastation`, compounding both strike chance and civilian loss for batched ticks; only legacy saves with an unset capacity are seeded with population, so a world emptied by war stays empty after reload.
  4. Add `faction_economy.py`: population, worlds, tech, stability, tax, trade, industry, military upkeep, war burden, net income and treasury per canonical faction, persisted in `GameState` and surfaced through `galactic_politics`.
  5. Render the Sol megastructure as a partial Dyson swarm (stellar core, five collector bands, dark panels with gold edges) with a maintenance population and a shell radius of 0.25 AU at 0.06 AU visual orbit; add population capacity and world tech to the target dossier and economy rows to faction cards.
  6. Bound the absolute target dossier with `overflow-y: auto` so the expanded rows scroll at 1280x720 instead of spilling into the command strip; align package `__version__`, CLI banner, README test counts and project metadata at 0.2.0.
- **Consequences**: Generated populations are area- and habitability-scaled (Sol ring world ~10.5B, Dyson swarm maintenance ~21.6M of 44.1M, small stations under 4M), no body exceeds capacity after 2000 batched ticks, front worlds lose population and gain devastation, war-killed worlds stay empty, and every surviving faction reports a treasury and cash flow. Full suite: 642 tests (37 suites); Edge DOM/pixel audit at 1280x720, 1920x1080 and 2560x1440 shows no label, card, or page overflow. Automated audit only: this model rejects image input, so the captures were inspected through pixels and DOM geometry, not human vision.

### ADR-070: Batched War Declarations Compound Per-Tick Odds
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: The follow-up audit simulated `tick(2000)` and found zero wars, while 400 single ticks produced nine wars and 35 devastated worlds. War declarations used one linear roll per call (`WAR_DECLARATION_RATE * num_ticks`), so a batched tick was as peaceful as a single tick and the new devastation, attrition and war-burden mechanics were unreachable in batch gameplay and tests.
- **Decision**: Compute the declaration chance as `1 - (1 - WAR_DECLARATION_RATE) ** num_ticks`, matching the compounding already used for front attrition, and cover it with a regression test that `tick(50)` declares a war and scars at least one world.
- **Consequences**: Batched and real-time play now agree on war frequency; seed 42 declares a war within 50 ticks and leaves devastated worlds and wartime upkeep visible. Suite: 643 tests (37 suites).

### ADR-071: Treasuries, Civil Order and War Costs Feed Back Into Population and Peace
- **Date**: 2026-10-27
- **Status**: Accepted
- **Context**: The new faction economy was cosmetic. Treasuries only grew, peacetime upkeep was a few hundred credits against thousands of income, so no faction could ever go broke, and stability was computed but influenced nothing outside its own display. Population growth ignored civil order, and devastated worlds recovered at a fixed rate regardless of who owned them or how advanced they were.
- **Decision**:
  1. Price wartime upkeep as a share of gross income (`0.50` per active war plus `0.20` per 100% population-weighted devastation, capped at `0.95`), keeping peacetime garrisons cheap. One war is affordable; two simultaneous fronts drive a large faction's net income negative.
  2. End active wars for a faction whose treasury is empty and whose net income is negative, with an explicit `BANKRUPT PEACE` log, so the economy can force a treaty.
  3. Feed faction stability into population growth (`0.70 + 0.60 * stability`) and into devastation recovery (`0.030 * (0.60 + tech/20) * (0.40 + 0.60 * stability)`), threading stability from the stored economies into `step_population_dynamics`.
  4. Show `WAR BURDEN` on faction cards and colour treasury/net rows when a faction is broke.
- **Consequences**: War now has a budget: two-front wars turn net income negative, stability falls, growth slows, worlds rebuild slower, and an exhausted treasury ends the war. Seed 42 after 1500 ticks shows one treaty, eight devastated worlds and a broke corsair faction. Suite: 647 tests (37 suites); Edge faction-panel audit at 1280x720 reports nine cards, no card or panel overflow and zero console errors.
