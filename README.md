# VoidFarer

[![Built with AIKit](https://img.shields.io/badge/built%20with-AIKit-6f42c1)](https://github.com/Aegean-E/AIKit)

> **Autonomous Deep-Space Fleet, Procedural Galaxy & Windows Cockpit Simulator.**

VoidFarer is a zero-dependency, local-first space flight, fleet management, and exploration simulation engine. Navigate procedural star systems, establish orbits, route reactor power, board derelicts, scoop fuel, drill crew, commission autonomous drones, purchase hardware upgrades, fight adaptive hostile AI, trade commodities, and pilot your flagship via an ANSI REPL or a Windows desktop HTML5 Canvas cockpit.

---

## ⚡ 30-Second Cold-Start Quick Reference

### 🎮 1-Click Instant Game Launch (Windows)
Double-click or run either batch launcher directly from Windows Explorer or Terminal:
```cmd
play.bat        # Interactive Mission Launcher (defaults to Windows Cockpit & auto-opens browser)
voidfarer.bat   # CLI passthrough launcher (e.g. `voidfarer.bat status`, `voidfarer.bat repl`)
```

- **Runtime Prerequisites**: Windows 10/11 and Python 3.10+ (Standard Library only; zero third-party packages required).
- **Canonical Regression Shield Gate**:
  ```bash
  python aikit.py check voidfarer
  ```
- **UI inventory proof**: `python tools/ui_inventory.py`

### 🛠️ AIKit Commands (run from the AIKit folder)
| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status voidfarer` |
| Phase 4: every gate | `python aikit.py check voidfarer` |
| Repair memory and map, then check | `python aikit.py fix voidfarer` |
| Resume an interrupted task | `python aikit.py resume voidfarer` |
| Bounded cockpit UI task | `python aikit.py ui begin voidfarer --surface cockpit` (then `ui verify`) |

---

## 📦 What's Inside

```text
voidfarer/
├── .aikit/                   <- project memory: record, ledger, decisions
│   ├── codebase_map.md       <- AST-generated symbol map
│   ├── decisions.md          <- monotonic ADR register
│   ├── guidelines.md         <- project-specific guidelines
│   ├── project.json          <- stack and gate configuration
│   ├── ui.json               <- committed cockpit UI surface contract
│   ├── ui_history.json       <- append-only UI task evidence
│   └── task_ledger.json      <- power-loss safe task state
├── docs/                     <- comprehensive system design & research
│   ├── ATTENTION_MECHANICS_LITERATURE_REVIEW.md <- behavioral psychology review
│   └── NARRATIVE_AND_TUTORIAL_LITERATURE_REVIEW.md <- cognitive load & narrative review
├── .gitignore                <- transient state & python caches excluded
├── LICENSE                   <- GNU AGPL-3.0 license
├── pyproject.toml            <- build and package configuration
├── play.bat                  <- 1-click interactive Windows launcher (default: Windows Cockpit)
├── voidfarer.bat             <- 1-click Windows CLI passthrough launcher
├── README.md                 <- living documentation
├── voidfarer/                <- core simulation package
│   ├── __init__.py           <- package metadata
│   ├── models.py             <- frozen dataclass DTOs and schema validators
│   ├── factions.py           <- sovereign factions, megacorps & standing tiers
│   ├── enemies.py            <- tactical enemy archetypes, abilities & generator
│   ├── galaxy.py             <- procedural star system & hyperlane generator
│   ├── engine.py             <- deterministic state machine & coordinator
│   ├── reactor.py            <- reactor modes, heat, cooling & derating
│   ├── mapmods.py            <- procedural sector map modifiers
│   ├── shipmods.py           <- structural ship modification catalog
│   ├── character.py          <- commander age, skills & abilities
│   ├── research.py           <- research projects & technology bonuses
│   ├── outposts.py           <- outpost catalogs & tick production
│   ├── faction_state.py      <- faction leaders, behaviors, wars & elimination
│   ├── fleet.py              <- escort warships, formations & battle support
│   ├── navigation.py         <- multi-jump routing, void lanes & black-hole hazards
│   ├── messaging.py          <- branching quantum message trees
│   ├── crew.py               <- crew roles, recruiting & portraits
│   ├── weapons.py            <- weapon types & combat modifiers
│   ├── retention.py          <- relics, dynamic contracts & pilot mastery
│   ├── story.py              <- cadet academy, cipher campaign flags & endings
│   ├── upgrades.py           <- hardware upgrades catalog & drone templates
│   ├── economy.py            <- dynamic galactic economy, stockpiles & trade routes
│   ├── frontier.py           <- AI captains, depots, mercenaries & quantum messages
│   ├── exploration.py        <- derelict salvage, fuel scooping & crew drills
│   ├── codex.py              <- discovery codex, career statistics & milestones
│   ├── inventory.py          <- item catalog, consumables & cargo manifest
│   ├── storage.py            <- crash-safe atomic persistence & shadow backup
│   ├── server.py             <- zero-dependency HTTP REST & cockpit server
│   ├── cli.py                <- ANSI terminal interface & interactive REPL
│   └── static/               <- Stellaris-style command console UI
│       ├── index.html        <- semantic HUD structure & radar canvas
│       ├── style.css         <- sci-fi glassmorphism design system
│       ├── app.js            <- radar math, Web Audio synth & REST link
│       ├── cursor-default.svg <- themed default cockpit cursor
│       ├── cursor-pointer.svg <- themed pointer cursor for controls
│       └── cursor-crosshair.svg <- themed radar crosshair cursor
├── tools/                    <- developer proofs
│   ├── __init__.py           <- package marker
│   ├── ui_audit.py           <- layout metrics
│   ├── ui_browser.py         <- real browser review
│   └── ui_inventory.py       <- cockpit inventory proof
└── tests/                    <- unit & integration test suite (30 suites)
```

---

## 🚀 Quick Start & CLI Usage

VoidFarer requires only Python 3.10+ and standard library modules.

### 1. Flagship Telemetry Status
```bash
python -m voidfarer.cli status
```
Displays commander dossier, vital telemetry (hull, shields, fuel), reactor power distribution, installed modules, fleet drone count, current system coordinates, and proximity hazard alerts.

### 2. Galaxy Starmap & Celestial Radar
```bash
python -m voidfarer.cli chart
```
Prints the sector hyperlane network, visited flags, security ratings, and every body in the local system. Each system hosts 5-6 planets, moons, ice/lava worlds, ringed giants, and research outposts, with a guaranteed dockable station.

### 3. Navigation & Spaceflight
```bash
# Enter orbit around a planet or space station
python -m voidfarer.cli orbit sol_body_1

# Initiate timed sublight or quantum in-system transit
python -m voidfarer.cli travel sol_body_2 --mode sublight
python -m voidfarer.cli travel sol_body_4 --mode quantum

# Inspect or dismiss cockpit popup events
python -m voidfarer.cli events list
python -m voidfarer.cli events dismiss evt_2_1

# Perform sensor sweep of orbiting body (earns research bounty)
python -m voidfarer.cli scan

# Hyperspace jump to an adjacent star system
python -m voidfarer.cli jump alpha_centauri

# Strip the deterministic derelict at the current body (risk/reward boarding)
python -m voidfarer.cli salvage

# Recover fuel from a star, gas giant, or ice body (adds reactor heat)
python -m voidfarer.cli scoop
```
Scans need 5 MW of sensor power; a failed zero-power attempt no longer consumes the body. Full-system surveys pay a bonus and advance `systems_surveyed`; titanium salvage advances mining contracts; each scoopable body has a finite 3-8 tap reserve that recharges one tap every 6 ticks.

### 4. Hardware Upgrades & Station Arsenal
```bash
# Inspect available hardware modules and equipped status
python -m voidfarer.cli upgrades

# Purchase and equip an upgrade module
python -m voidfarer.cli upgrades buy warp_booster_mk2
python -m voidfarer.cli upgrades buy subspace_cargo_pods
```

### 5. Autonomous Fleet & Drones
```bash
# List active fleet drones and accumulated harvest yield
python -m voidfarer.cli fleet

# Commission a new drone (mining, scout, or combat_escort)
python -m voidfarer.cli fleet buy mining sol

# Redeploy a drone to another system
python -m voidfarer.cli fleet deploy drone_mining_1 alpha_centauri

# Harvest accumulated resources and credits from fleet
python -m voidfarer.cli fleet harvest
```

### 6. Tactical Combat Maneuvers
When intercepted by hostile corsairs, syndicate marauders, or faction enforcers in low-security space:
```bash
# Tactical maneuvers
python -m voidfarer.cli combat fire             # Laser battery barrage (depletes deflector shields, overflows to hull)
python -m voidfarer.cli combat drone            # Kinetic drone torpedo strike (armor-piercing; bypasses deflector shields)
python -m voidfarer.cli combat target weapons   # Precision strike to disable enemy offensive arrays
python -m voidfarer.cli combat target shields   # Precision strike to destabilize shield harmonic generators
python -m voidfarer.cli combat absorb           # Overcharge deflector shield capacitors
python -m voidfarer.cli combat evade            # High-G thruster burn to dodge telegraphed attacks
python -m voidfarer.cli combat flee             # Emergency hyperspace micro-jump
```

Hostile captains use adaptive AI profiles (`aggressive`, `defensive`, `opportunist`, `adaptive`, `warlord`) that read your hull, shields and tactical combo; the telemetry line shows the next predicted maneuver.

Hostile strength scales +5% hull, shields, damage and bounty per Pilot Mastery level above 1 (capped +75%); Dreadnoughts only ambush level-4+ commanders. Evasive burns cost 3 fuel and reset the combo and streak.

### 7. Dynamic Sector Bounties & Contracts (Zeigarnik Loop)
```bash
# View active contracts, progress bars, and rewards
python -m voidfarer.cli contracts

# Claim completed contract reward and draw replacement assignment
python -m voidfarer.cli contracts claim contract_explore_alpha_centauri
```

### 8. Pilot Mastery & Specializations (Self-Determination)
```bash
# Display Pilot rank, XP progress, and available talent perks
python -m voidfarer.cli mastery

# Unlock specialization perk using earned Talent Points
python -m voidfarer.cli mastery unlock void_cartographer
python -m voidfarer.cli mastery unlock dreadnought_tactics
```

### 9. Ancient Precursor Relics Vault (Variable-Ratio)
```bash
# Inspect recovered alien artifacts and active passive fleet modifiers
python -m voidfarer.cli relics
```

### 10. Expedition Jump Streaks (Loss Aversion)
```bash
# Check current jump streak and cumulative multiplier (+15% up to x2.50)
python -m voidfarer.cli streak
```

### 11. Commodity Commerce & Drydock Services
```bash
# Inspect local exchange prices
python -m voidfarer.cli market

# Purchase and sell commodities
python -m voidfarer.cli buy fuel_cells 5
python -m voidfarer.cli sell titanium 3

# Repair hull damage and refuel
python -m voidfarer.cli repair --amount 25
python -m voidfarer.cli refuel --amount 20

# Inspect the living galactic economy: stockpiles, market shocks, and best trade routes
python -m voidfarer.cli economy

# Inspect the cargo manifest, buy station consumables, and use them in space
python -m voidfarer.cli inventory
python -m voidfarer.cli inventory buy nanite_repair_paste 2
python -m voidfarer.cli inventory use nanite_repair_paste
```

### 12. Cadet Flight Academy (Situated Scaffolding)
```bash
# Check current tutorial milestone and curriculum progress
python -m voidfarer.cli tutorial

# Skip tutorial prompts or reset onboarding curriculum
python -m voidfarer.cli tutorial skip
python -m voidfarer.cli tutorial reset
```

### 13. The Precursor Cipher Narrative Campaign (Space Opera)
```bash
# Display active chapter synopsis, objectives, transmissions log, and moral choices
python -m voidfarer.cli story

# Resolve an episodic narrative dilemma
python -m voidfarer.cli story choose choice_vance_telemetry
```
The five-act campaign tracks persistent story flags: later choices can require earlier decisions (Act V's title needs the Act IV Oath; selling the echoes needs the Act I Syndicate leak), locked choices show their reasons, and the finale resolves First VoidFarer, Sentinel, or Shadow Broker. Legacy saves migrate on load.

### 13b. The Hollow Between (Void Lane Traversal)
```bash
# Void drive readiness, storm risk, and charted destinations
python -m voidfarer.cli void

# Full deterministic void lane chart for this save seed
python -m voidfarer.cli void lanes

# Slip beyond a black-hole event horizon toward a lane-linked system
python -m voidfarer.cli void dive golconda

# Emergency surfacing back through the entry horizon (costs hull and shields)
python -m voidfarer.cli void emerge
```
Black-hole anchors mesh into a seeded void-lane graph. Diving needs a horizon orbit, route fuel, and 25% shields; storms drain stability, shields and hull. Each storm adds resonance (+1, doubled below 30% stability) worth 120 cr and 15 XP on arrival; `void emerge` banks half, collapse loses all. `gateways_open` calms storms 25%, and the Void Compass and Crown of Echoes raise starting stability.

### 14. Geopolitical Factions & Megacorporations
```bash
# View all sovereign galactic factions, ideologies, territorial HQs, and standing
python -m voidfarer.cli factions

# View galactic megacorporations, commercial specialties, and trade perks
python -m voidfarer.cli corporations
```

### 15. Cosmic Calendar & Temporal Clock Controls
```bash
# Check the in-game calendar date, stardate, and active simulation tick
python -m voidfarer.cli time status

# Pause or resume the cosmic simulation clock
python -m voidfarer.cli time pause
python -m voidfarer.cli time resume

# Adjust simulation speed multiplier (1x normal, 2x fast, 5x sub-warp, 10x hyper-warp)
python -m voidfarer.cli time speed 5

# Advance cosmic simulation by a discrete number of ticks (+1, +4, +10)
python -m voidfarer.cli time step 4
```

### 16. Interactive Terminal Cockpit REPL
```bash
python -m voidfarer.cli repl
```
Inside the interactive REPL, all commands work (`status`, `chart`, `time`, `contracts`, `combat`, `story`, `void`, ...); type **`serve`** to launch the concurrent background Web HUD!

Frontier commands are also available directly:
```bash
python -m voidfarer.cli quests
python -m voidfarer.cli ai list
python -m voidfarer.cli ai hail captain_vega
python -m voidfarer.cli messages list
python -m voidfarer.cli messages send "Captain Vega" "Trade lane" "Meeting at Sol."
python -m voidfarer.cli depot status
python -m voidfarer.cli depot deposit titanium 2
python -m voidfarer.cli depot sell titanium 1
python -m voidfarer.cli land sol_body_2
python -m voidfarer.cli mercs list
python -m voidfarer.cli mercs hire merc_ironclad
python -m voidfarer.cli allies list
python -m voidfarer.cli allies form captain_sable
python -m voidfarer.cli saves list
python -m voidfarer.cli saves save slot_1
python -m voidfarer.cli saves load slot_1
```

### 17. Reactor, Map Modifiers & Ship Modifications
```bash
# Reactor thermal simulation: heat, cooling, integrity and operating doctrine
python -m voidfarer.cli reactor status
python -m voidfarer.cli reactor mode overdrive
python -m voidfarer.cli reactor vent
python -m voidfarer.cli reactor repair

# Active sector map modifiers and their economy/combat/thermal effects
python -m voidfarer.cli mapmods

# Structural refit bay: install with credits, remove for salvage value
python -m voidfarer.cli refit list
python -m voidfarer.cli refit install overcharged_core
python -m voidfarer.cli refit remove thermal

# Unified simulation telemetry report
python -m voidfarer.cli simulation
```
Reactor modes trade output against heat: `balanced`, `economy`, `overdrive`, and `silent`.
Heat above 70% derates subsystem power; critical heat damages hull and core integrity.
Sector modifiers (`ion_storm`, `nebula_drift`, `quantum_tide`, etc.) alter jump fuel,
scan yield, encounter risk, trade margins and reactor cooling. Structural refits use five
slots (`frame`, `reactor_core`, `thermal`, `drive`, `ops`) and apply explicit trade-offs.

### 18. Commander, Empire, Diplomacy & Fleet Manager
```bash
python -m voidfarer.cli character status
python -m voidfarer.cli character train science
python -m voidfarer.cli character use emergency_repair

python -m voidfarer.cli research start advanced_cooling
python -m voidfarer.cli outpost list
python -m voidfarer.cli outpost build solar sol_ring_world

python -m voidfarer.cli diplomacy list
python -m voidfarer.cli fleet ships
python -m voidfarer.cli fleet buy_escort frigate
python -m voidfarer.cli route alpha_centauri
python -m voidfarer.cli navigate alpha_centauri
python -m voidfarer.cli combat stance aggressive
python -m voidfarer.cli messages tree
python -m voidfarer.cli messages choose <message_id> <choice_id>
python -m voidfarer.cli crew recruit scientist
python -m voidfarer.cli crew train <crew_id>
python -m voidfarer.cli crew shore
python -m voidfarer.cli weapons install railgun
```
The commander ages, earns XP, and trains six skills with active cooldown abilities. Research
unlocks reactor, scan, combat, outpost, repair, and fuel tech. Outposts produce resources each tick.
Faction leaders wage wars, capture systems, and face elimination. Escort warships coordinate volleys,
screen damage, and adopt battle stances. Multi-jump routing handles black holes. Message trees branch
into lasting outcomes. Crew feature roles, morale, wages, and SVG portraits; morale reacts to
battles, hull breaches, void storms, hostile arrivals, and campaign beats, unpaid crews below
morale 20 risk resignation, and docked stations offer paid shore leave. Bulk orders walk the
local stockpile price, and the status deck, CLI, and crew tab show per-tick cash flow. The
setting begins 01.01.3042 in the Quantum Age with Dyson spheres, wormholes, and ring worlds.

### 19. Stellaris-Style Windows Cockpit
Launch the Stellaris-inspired Windows command console:
```bash
python -m voidfarer.cli serve --port 8080
```
Open **`http://127.0.0.1:8080`** in Edge or Chrome on Windows to access:
- **Top Status Bar & Chronometer (`G-007`, `G-011`)**: Vitals plus the chrono deck, sized for 1280x720 through 4K.
- **Background Radar HUD (`G-004`, `G-005`, `G-013`)**: Map, left terminal, and a three-column bottom strip: reactor, skills, separate radar settings above the compact log; circular zoom icons and themed cursors.
- **Main Menu & Saves (`ESC`)**: Categorized settings console plus create, load, list and delete saves.
- **Planet Inspector**: Gravity, atmosphere, temperature, habitability, orbit distance, moons, resources, and colony tiers.
- **Transit, Landing & Fleet**: Timed transit-and-orbit, fuel-priced quantum micro-jumps, surface surveys and drone fleets.
- **Living Galaxy**: Procedural worlds, AI traders, dynamic markets, faction perks, and reputation.
- **Mission Panels**: Quests, contracts, diplomacy, depots, messages, COMMS, factions and combat.
- **Space-Opera Campaign Tab**: Five acts with a live objective checklist, locked choices that show their requirements, transmissions, and one of three endings with epilogue.
- **The Hollow Between Panel**: Void drive readiness, lane dive buttons, traversal progress/stability, emergency emerge, and a hue-shifted radar overlay.
- **REPL Server Lifecycle**: `serve` runs the HTTP server and ticker; `serve stop` saves and shuts down.
- **Reactor Power Matrix (`G-006`, `G-013`)**: Bottom-left strip with sliders, `Q/W/E/R` hotkeys, thermal telemetry, four modes and VENT.
- **Sector Map Modifiers**: Generated conditions shown as radar chips and applied to fuel, scans, encounters, trade and reactor heat.
- **Player, Skills & Crew Tabs**: PLAYER is a dossier; six quick-train skills live in the bottom strip (`SHIFT+1..6`), while SKILLS holds ranks, pilot perks and relics. Crew holds bonuses and drills.
- **Ship Configuration Tab**: Fixed-height silhouette, compact stats, and a full-width module ledger; refits require a docked drydock or station.
- **Commander Creation & Death Flow**: Name, age, background, and starting-skill allocation wired into new games; a death overlay summarizes the run and offers a fresh commander or save load.
- **Stellaris-Style Windows HUD**: deep-navy panels, gold rules, 1280x720-4K/ultrawide, density/HUD scale, DPR radar, keyboard/mouse and reduced motion.
- **Derelict Boarding & Fuel Scooping**: once-per-body salvage feeds titanium contracts; star/gas/ice scoops trade reactor heat for fuel from finite, recharging reservoirs; paid crew drills.
- **Captain's Log & Discovery Codex**: career statistics grid, discovery milestones, claim rewards, category filters, and persistent flight log.

### 20. Captain's Log & Discovery Codex
```bash
# Career statistics, discovery overview, and claimed milestone log
python -m voidfarer.cli log

# Discovery codex milestones with category filters
python -m voidfarer.cli codex

# Claim credits and pilot XP for a completed milestone
python -m voidfarer.cli codex claim first_light
```
New System Surveyor and Sector Cartographer milestones track full-system sweeps, and the log reports `systems_surveyed`.

### 21. UI Guard & Visual Audit
`.aikit/ui.json` bounds cockpit work to `voidfarer/static/**` and `voidfarer/server.py`.
`ui_required` is true: tests are the fast proof, `tools/ui_inventory.py` is the snapshot,
`tools/ui_audit.py` measures layout, and `tools/ui_browser.py` drives real Edge screenshots.
See ADR-041, ADR-042 and ADR-047.

---

## 🛡️ Architecture & Resilience Guarantees

1. **Zero External Dependencies**: Built entirely on standard Python modules (`math`, `random`, `dataclasses`, `http.server`, `json`, `pathlib`).
2. **Power-Loss Recovery (PRINCIPLE-013)**: State saves use atomic replacement with file descriptor `fsync`, shadow `.bak` backups, and automatic quarantine of corrupt payloads.
3. **Fast Test Verification**: Comprehensive 499-test suite runs in about 7 seconds (`python -m unittest discover`).
4. **Windows Only**: Windows 10/11, batch launchers, PowerShell-aware console UTF-8, and Windows paths; no Linux/macOS branches or OS-independent claims.
5. **Realistic Mechanics & Economic Integrity**: Anti-arbitrage dock guards, faction tariffs, cargo-volume refit gates, quantum fuel efficiency and cockpit parity.
