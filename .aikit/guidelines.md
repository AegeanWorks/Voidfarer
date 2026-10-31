# Project Guidelines

Rules for this project only, written by people or AI agents. They add to AIKit's principles and
rank below them: a guideline never overrides a principle (PRINCIPLE-000 R6, PRINCIPLE-001 R4).
Add one with `python aikit.py guideline <name> "<rule>" --source <user|ADR-NNN|person>`, or by
hand as one line below in the form `- **G-NNN** (source): rule`; IDs are never reused.

## Rules
- **G-001** (user): Cockpit layout rule 1: the TELEMETRY / Tactical Flight Log panel is anchored on the right of the bottom command strip (G-013) and carries a HIDE/SHOW button.
- **G-002** (user): Cockpit layout rule 2: the Chrono tick and time settings deck is pinned to the upper-right corner, at the far right of the top status bar.
- **G-003** (user): Cockpit layout rule 3: the Commerce/Arsenal/Fleet terminal runs vertically (up to down) on the left side: a vertical tab rail with the active tab's content beside it.
- **G-004** (user): Cockpit layout rule 4: the NAV-Radar orbital map is the full-viewport background layer, with all HUD decks and panels rendered on top of it.
- **G-005** (user): Cockpit layout rule 5: HUD overlays must remain sleek and unbulky over the background radar: NAV-RADAR orbital title is a transparent on-map label, the left terminal rail expands content to the right on demand (collapsible drawer), and the bottom command strip stays compact between the left terminal and the right corner.
- **G-006** (user): Cockpit layout rule 6: the reactor power routing panel is expandable with a HIDE/SHOW button like the flight log, the top-bar actions line sits to the left of the vitals row, and all vital stat cards share equal dimensions.
- **G-007** (user): Cockpit layout & navigation rule 7: Enter orbit and sublight transit adhere to the exact same 2D polar Euclidean distance calculation, and top-bar vital stat cards match the height of the chrono date box on a single non-wrapping line.
- **G-008** (user): Cockpit layout rule 8: the SHIP MODS section lives in the left vertical terminal as a first-class tab and follows the same drawer behavior as COMMERCE, ARSENAL, and FLEET.
- **G-009** (user): Cockpit layout rule 9: vital stat cards are compact 44px equal-height boxes, and orbital rings fade to the black void at the sensor-range edge.
- **G-010** (user): Setting rule 10: the campaign starts on 01.01.3042 in the Quantum Age (31st Century); messaging must remain branch-resolvable and every branch outcome persistent.
- **G-011** (user): This is a Windows desktop game: support 1280x720 through 4K at 100-200% Windows scaling, resizable windows, keyboard/mouse, and DPR-correct radar; density and HUD scale remain user-selectable. Do not add phone, tablet, touch, safe-area, or non-Windows UI paths.
- **G-012** (user): New exploration mechanics must stay deterministic per save seed, stdlib-only, exposed through CLI/REST/cockpit parity, and every permanent change must be serialized with a backward-compatible default.
- **G-013** (user): Cockpit layout 13: bottom strip spans left panel to right corner in three equal columns (reactor | skills | radar/log); zoom stacks +/center/−; panels have icon+hotkey; reactor Q/W/E/R, skills SHIFT+1..6, toggles P/K/L; log compact; PLAYER has no skills duplicate; themed SVG cursors; document layout.
- **G-014** (user): VoidFarer targets Windows only: use Windows launchers, paths, packaging and console handling; do not add or keep Linux/macOS branches, launchers, documentation or OS-independent claims.
- **G-015** (user): UI review uses tools/ui_browser.py (Playwright + Edge) for real screenshots, then a vision subagent: gemma-4-31b on evren2-5, or NVIDIA Nemotron 3.5 Super VL (free) on Kilo when images/quota fail; require on-screen text quotes, implement ranked defects, re-capture and re-review until approved. The text-only agent must not claim visual judgment; audits stay mandatory; screenshots live in ui-review/ (ignored).
