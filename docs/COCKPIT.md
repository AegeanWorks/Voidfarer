# VoidFarer Windows Cockpit

## 19. Stellaris-Style Windows Cockpit
Launch the Stellaris-inspired Windows command console:
```bash
python -m voidfarer.cli serve --port 8080
```
Open **`http://127.0.0.1:8080`** in Edge or Chrome on Windows to access:
- **Top Status Bar & Chronometer (`G-007`, `G-011`)**: Vitals plus the chrono deck, sized for 1280x720 through 4K.
- **Background Radar HUD (`G-004`, `G-005`, `G-013`)**: Map, left terminal, and a two-column bottom strip: one combined reactor+abilities panel beside radar settings above the log. The imperial outliner ends with its sections instead of stretching to the footer.
- **Menu, Settings & Saves (`ESC`)**: volume, auto-pause on intercepts/events, auto-claim, order lot, key list, reset; saves.
- **Left Terminal & Commerce**: `[`/`]` cycle tabs, `\` hides the drawer; order lots, cost and margins.
- **Planet Inspector**: Gravity, atmosphere, habitability, orbit, moons, resources, colony tiers.
- **Transit, Landing & Fleet**: Timed transit, quantum jumps, surveys and drones.
- **Living Galaxy**: Procedural worlds, AI traders, dynamic markets and reputation.
- **Strategic Map**: faction territories, borders, war fronts and powers legend.
- **Mission Panels**: Quests, contracts, diplomacy, depots, messages, COMMS, factions and combat.
- **Space-Opera Campaign**: five acts, live objectives, three endings.
- **Hollow Between**: readiness, lane dives, stability, emergency emerge.
- **REPL Server Lifecycle**: `serve` runs the HTTP server and ticker; `serve stop` saves and shuts down.
- **Reactor Matrix**: four sliders, presets, `Q/W/E/R`, heat, modes and VENT.
- **Sector Map Modifiers**: radar chips alter fuel, scans, encounters, trade and reactor heat.
- **Player, Skills & Crew Tabs**: PLAYER is a dossier; the combined bottom command panel holds reactor routing beside the six-power ability matrix (`SHIFT+1..6`), while SKILLS holds training, talents and relics. Crew splits into ROSTER (morale, XP, drills) and AWAY TEAMS (body expeditions, risk pills, deployment and recall).
- **Ship Configuration Tab**: Fixed-height silhouette, compact stats, and a full-width module ledger; refits require a docked drydock or station.
- **Commander Creation & Death**: creation and death overlay with run summary.
- **Stellaris-Style HUD**: gold-on-navy, 720p-4K, density/HUD scale, DPR radar.
- **Derelict Boarding & Fuel Scooping**: salvage and finite fuel taps.
- **Captain's Log & Discovery Codex**: career stats, milestones, rewards, filters and log.
- **Notification Toasts & Minimum Targets**: event cards anchor between the left terminal and target dossier below 1600px so they never cover the deck at 1280x720; the SCROLL cue is 12px and compact command-strip controls keep a 24px target height.
- **Ship Dossier Legibility**: the five silhouette cases show short codes (FRM, CORE, THM, DRV, OPS) with the full slot label and installed module in the tooltip; catalog names wrap rather than ellipsize; research rows keep cost and START on fixed columns.
- **Display-Scaling Proof**: `python tools/ui_audit.py --dpr 1.5` (or `--dpr 2`) emulates Windows 150%/200% scaling and records whether the radar backing store scales with the CSS box; the per-viewport timeout scales with DPR because a 2x 1080p capture measured about 350 s.
- **Galactic War News**: captures, peace treaties and faction eliminations raise at most one dismissable cockpit notification per tick, with a 12-tick cooldown between headlines; the flight log keeps the newest ten lines plus the most recent war headlines, and AI trade is summarized once every five ticks.
- **Captain's Limits & Ceasefire Petition**: the Factions war card offers PETITION CEASEFIRE / 500 only for a war your own polity is in, and states plainly that sovereign wars end without you; a captain cannot declare war. The envoy fee is charged only if the enemy accepts, and odds rise with standing, diplomacy and enemy war pressure.
- **Empty-Space Vectors**: clicking empty space on the orbital radar selects a vector; a reticle and dashed course mark the chosen position, the target card labels MOVE TO VECTOR, the same transit animation flies the ship there, and the destination reticle remains visible during the trip.
- **Post-War Reconstruction**: orbit or land on an inhabited devastated world to see REBUILD WORLD (600 CR) and DELIVER RELIEF on the target card. Credits remove 20 devastation and earn +2 standing; 2 medicines + 2 hydroponics + 1 fuel cell remove 40, earn +5 standing and lift crew morale. Bombed markets pay a relief premium for those goods, and the Rebuilder / Relief Runner codex milestones track the work.
- **Boarding & Prize Capture**: `BOARD & CAPTURE` appears in the combat card and enables only when enemy shields are down, enemy hull is at or below 30%, and an active marine is aboard. Success takes the crippled hull as a fleet prize; failure injures the marine, costs morale and exposes the ship to the enemy counter-battery. The fleet manager lists each escort's resale value and adds a SELL button beside REPAIR and DISMISS; the Shipbreaker milestone tracks three sales.
- **Fleet Deployment**: each fleet card shows `SYS <id>` and `LOCAL`/`PATROL`; only local escorts join combat, screen damage and gain battle XP. Patrol escorts instead cut pirate risk in their assigned system, and the fleet report separates total from local damage and evasion.
- **Fleet Upkeep**: living escorts cost 30/55/90/110 cr/month by role. The fleet header and crew cash-flow panel show fleet upkeep separately from crew payroll; a month-end shortfall marks living escorts `DAMAGED` until repaired.
- **Squadron Roles**: click the role badge on a fleet card to cycle `SCREEN` (+50% evasion, -25% damage), `STRIKE` (+25% damage, -25% evasion) or `SUPPORT` (repairs 4 integrity per exchange, -45% damage). Roles default by hull class and cannot change under fire.
- **Fleet Service Records**: each escort card shows `SVC <battles>B / <kills>K / <patrol contacts>P / <bounty>CR`; the CLI fleet ledger shows the same B/K/P counters. Training sessions are stored as well.
- **Fleet Veterancy**: each fleet card shows a rank badge (Green/Regular/Veteran/Elite/Ace), an XP progress bar and a TRAIN button priced at 200 cr + 5 cr per current XP. Training grants 10 XP, stops at Ace (300 XP), and promotions appear in the flight log. Ranks add damage and screen-evasion bonuses.
- **Patrol Sweeps**: remote escorts show `PATROL 6T` and resolve a sweep every 6 ticks. Quiet tours grant 1 XP; contact pays a security-scaled bounty, 3 XP and can damage the patrol.
- **Outpost Modules**: each outpost row has a module picker and INSTALL MODULE button. Modules cost their catalog price times the next stack number, stack up to three times, and feed the existing outpost production multiplier.
- **Outpost Crew**: each outpost hosts up to three specialists. The crew picker and ASSIGN button station them; a chip recalls each one. Stationed crew stop contributing ship bonuses, but add 8% + 2% per skill and another 6% in a preferred role, capped at x1.60 output. The crew roster marks `OUTPOST: <name>`, and stationed crew cannot deploy on away teams or be dismissed until recalled.
- **Frontier Shipyard Services**: a shipyard outpost in the current system shows `SERVICES ONLINE` and unlocks hull repair, refueling, escort construction/training/repair, weapon and module work, and fleet refits without a station dock. The fleet header shows `SHIPYARD LINK`; remote shipyards do not help.
- **Outpost Specialization**: level-3 outposts choose Industry (+30% credits), Research (+40% research), Commerce (+20% credits/+5% other) or Logistics (+10% all, +1 crew slot). A select and SET control appear on the outpost row; switching costs 600 cr.
- **Auto-Trade Broker**: the Commerce tab carries commodity, BUY ≤, SELL ≥, QTY and ENABLE/DISABLE controls. While docked, it executes at most one qualifying trade every 3 ticks, sells first at the sell threshold, otherwise buys below the buy threshold, and reports trade count plus realized credits.
- **Faction Diplomacy**: each Empire-tab faction row shows IMPROVE, GIFT 300, PACT, ALLY and, during your own war, PETITION 500. PACT enables at standing 40, improves buy and sell prices by 6%, and is suspended by war. ALLY enables at standing 70 and is refused once already allied; the row marks `ALLIED`, `PACT` and `WAR`, and allied territory reduces pirate risk by 28%.
- **NPC Traffic on the Map**: AI captains render as coloured hull glyphs on the system radar and as orbiting cluster markers on the galaxy map; select one to see trust, standing, hull, damage and hold, then HAIL SHIP.
- **Decision Cadence**: Settings -> GAMEPLAY -> Quick-time decision cadence (relaxed / normal / frequent) mirrors the server cadence; relaxed is the default and evaluates at most once per 36 ticks, normal once per 18, frequent once per 6. A failed roll still consumes its window. settings decisions and POST /api/settings/decisions do the same from CLI/API.
- **AIKit Link & Agent Surface**: the header shows AIKIT LINK // AGENT API; GET /api/agent/actions lists every POST action with its fields, window.voidfarerClickMap() enumerates every control with a stable data-testid, and python tools/ai_play.py plays headlessly.
- **AIKit Link & Agent Surface**: the header shows `AIKIT LINK // AGENT API`; `GET /api/agent/actions` lists every POST action with its fields, `window.voidfarerClickMap()` enumerates every control with a stable `data-testid`, and `python tools/ai_play.py --steps 180` plays headlessly with zero coverage gaps (44 mechanic families, 43 endpoints succeeded).
