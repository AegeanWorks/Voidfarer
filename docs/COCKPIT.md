# VoidFarer Windows Cockpit

## 19. Stellaris-Style Windows Cockpit
Launch the Stellaris-inspired Windows command console:
```bash
python -m voidfarer.cli serve --port 8080
```
Open **`http://127.0.0.1:8080`** in Edge or Chrome on Windows to access:
- **Top Status Bar & Chronometer (`G-007`, `G-011`)**: Vitals plus the chrono deck, sized for 1280x720 through 4K.
- **Background Radar HUD (`G-004`, `G-005`, `G-013`)**: Map, left terminal, and a three-column bottom strip (reactor, abilities, radar settings above the log).
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
- **Player, Skills & Crew Tabs**: PLAYER is a dossier; the bottom strip is the six-power ability bar (`SHIFT+1..6`), while SKILLS holds training, talents and relics. Crew splits into ROSTER (morale, XP, drills) and AWAY TEAMS (body expeditions, risk pills, deployment and recall).
- **Ship Configuration Tab**: Fixed-height silhouette, compact stats, and a full-width module ledger; refits require a docked drydock or station.
- **Commander Creation & Death**: creation and death overlay with run summary.
- **Stellaris-Style HUD**: gold-on-navy, 720p-4K, density/HUD scale, DPR radar.
- **Derelict Boarding & Fuel Scooping**: salvage and finite fuel taps.
- **Captain's Log & Discovery Codex**: career stats, milestones, rewards, filters and log.
- **Notification Toasts & Minimum Targets**: event cards anchor between the left terminal and target dossier below 1600px so they never cover the deck at 1280x720; the SCROLL cue is 12px and compact command-strip controls keep a 24px target height.
- **Ship Dossier Legibility**: the five silhouette cases show short codes (FRM, CORE, THM, DRV, OPS) with the full slot label and installed module in the tooltip; catalog names wrap rather than ellipsize; research rows keep cost and START on fixed columns.
- **Display-Scaling Proof**: `python tools/ui_audit.py --dpr 1.5` (or `--dpr 2`) emulates Windows 150%/200% scaling and records whether the radar backing store scales with the CSS box; the per-viewport timeout scales with DPR because a 2x 1080p capture measured about 350 s.
- **Galactic War News**: captures, peace treaties and faction eliminations raise dismissable cockpit notifications (at most two per tick); the flight log keeps the newest ten lines plus the most recent war headlines, and AI trade is summarized once every five ticks.
- **Captain's Limits & Ceasefire Petition**: the Factions war card offers PETITION CEASEFIRE / 500 only for a war your own polity is in, and states plainly that sovereign wars end without you; a captain cannot declare war. The envoy fee is charged only if the enemy accepts, and odds rise with standing, diplomacy and enemy war pressure.
- **Empty-Space Vectors**: clicking empty space on the orbital radar selects a vector; the target card labels MOVE TO VECTOR, and arrival holds station in the void with no body in orbit.
- **NPC Traffic on the Map**: AI captains render as coloured hull glyphs on the system radar and as orbiting cluster markers on the galaxy map; select one to see trust, standing, hull, damage and hold, then HAIL SHIP.
- **Decision Cadence**: Settings -> GAMEPLAY -> Quick-time decision cadence (relaxed / normal / frequent) mirrors the server cadence; normal permits at most one blocking prompt per 14 ticks. settings decisions and POST /api/settings/decisions do the same from CLI/API.
- **AIKit Link & Agent Surface**: the header shows AIKIT LINK // AGENT API; GET /api/agent/actions lists every POST action with its fields, window.voidfarerClickMap() enumerates every control with a stable data-testid, and python tools/ai_play.py plays headlessly.
- **AIKit Link & Agent Surface**: the header shows `AIKIT LINK // AGENT API`; `GET /api/agent/actions` lists every POST action with its fields, `window.voidfarerClickMap()` enumerates every control with a stable `data-testid`, and `python tools/ai_play.py --steps 180` plays headlessly with zero coverage gaps (44 mechanic families, 43 endpoints succeeded).
