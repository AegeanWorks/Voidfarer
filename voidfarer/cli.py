"""Command-line interface and interactive terminal REPL for VoidFarer."""

from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path
from typing import Sequence

# Windows consoles default to a legacy code page; force UTF-8 for the cockpit and REPL.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (ValueError, OSError):  # hygiene: allow non-reconfigurable stdio streams in test harnesses
    pass

from voidfarer import __version__
from voidfarer.engine import SimulationEngine
from voidfarer.factions import (
    CANONICAL_CORPORATIONS,
    CANONICAL_FACTIONS,
    get_faction_id_from_name,
    get_faction_standing_tier,
)
from voidfarer.galaxy import COMMODITY_MAP
from voidfarer.character import ABILITY_CATALOG, SKILL_CATALOG
from voidfarer.crew import CREW_ROLES
from voidfarer.weapons import WEAPON_CATALOG, get_weapon
from voidfarer.fleet import ESCORT_CATALOG
from voidfarer.frontier import MERCENARY_CATALOG
from voidfarer.outposts import OUTPOST_TYPES
from voidfarer.research import RESEARCH_PROJECTS
from voidfarer.retention import (
    PILOT_TALENTS,
    calculate_passive_multipliers,
)
from voidfarer.server import BackgroundServer, run_server, start_background_server
from voidfarer.storage import StorageManager
from voidfarer.economy import (
    calculate_dynamic_market_quote,
    faction_standing_price_factor,
    get_galactic_trade_routes,
)
from voidfarer.inventory import (
    ITEM_CATALOG,
    get_inventory_manifest,
    get_item_info,
)
from voidfarer.mapmods import describe_modifier_effects, get_map_modifier
from voidfarer.reactor import REACTOR_MODES
from voidfarer.shipmods import (
    CATALOG_SHIP_MODS,
    get_ship_mod,
    slot_label,
)
from voidfarer.upgrades import (
    CATALOG_CHASSIS,
    CATALOG_DRONE_TEMPLATES,
    CATALOG_UPGRADES,
    CHASSIS_MAP,
    UPGRADE_MAP,
    get_available_chassis,
    get_sell_value,
)

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
WHITE = "\033[97m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
__      __ _____  _____  _____   ______        _____   ______  _____  
\\ \\    / // ___ \\|_   _||  __ \\ |  ____/\\     |  __ \\ |  ____||  __ \\ 
 \\ \\  / /| |   | | | |  | |  | || |__ /  \\    | |__) || |__   | |__) |
  \\ \\/ / | |   | | | |  | |  | ||  __/ /\\ \\   |  _  / |  __|  |  _  / 
   \\  /  | |___| |_| |_ | |__| || | / ____ \\  | | \\ \\ | |____ | | \\ \\ 
    \\/    \\_____/|_____||_____/ |_|/_/    \\_\\ |_|  \\_\\|______||_|  \\_\\
{RESET}
{DIM}Autonomous Deep-Space Fleet & Procedural Galaxy Simulator v{__version__}{RESET}
"""


def _get_engine(storage_dir: Path | None = None) -> tuple[SimulationEngine, StorageManager]:
    """Initialize or restore simulation engine from disk."""
    if storage_dir is None:
        home = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        storage = StorageManager(home / ".voidfarer")
    elif storage_dir.suffix.lower() == ".json":
        storage = StorageManager(storage_dir.parent)
        storage.save_file = storage_dir
    else:
        storage = StorageManager(storage_dir)
    saved_state = storage.load()
    engine = SimulationEngine(state=saved_state)
    return engine, storage


def _bar(current: int, maximum: int, length: int = 20, color: str = GREEN) -> str:
    """Generate ANSI filled progress bar."""
    ratio = max(0.0, min(1.0, current / maximum if maximum > 0 else 0.0))
    filled = int(ratio * length)
    empty = length - filled
    return f"{color}{'█' * filled}{DIM}{'░' * empty}{RESET} {current}/{maximum}"


def cmd_status(engine: SimulationEngine) -> int:
    """Display current flagship telemetry, fleet roster, and star system status."""
    ship = engine.state.ship
    cur_sys = engine.current_system
    body = engine.orbiting_body

    print(BANNER)
    print(f"{BOLD}╔════ COMMANDER DOSSIER ══════════════════════════════════════════════╗{RESET}")
    print(f"║ Commander: {CYAN}{ship.commander_name:<16}{RESET} Callsign: {YELLOW}{ship.callsign:<16}{RESET} Class: {ship.ship_class:<12} ║")
    t = engine.state.time
    print(f"║ Date:      {YELLOW}{t.current_date:<10}{RESET}  (Tick #{t.tick:<5})   Temporal Clock: {GREEN if not t.is_paused else RED}{t.time_scale:<10}{RESET}       ║")
    print(f"║ Credits:   {YELLOW}{ship.credits:>8} cr{RESET}       Cargo:    {sum(ship.cargo.values()):>2}/{ship.cargo_capacity:<2} units                     ║")
    print(f"╠════ VITAL TELEMETRY ════════════════════════════════════════════════╣{RESET}")
    streak_mult = 1.0 + min(1.5, (ship.streak - 1) * 0.15)
    print(f"║ Streak:    {RED}🔥 {ship.streak} jumps (x{streak_mult:.2f}){RESET}   Mastery:  {YELLOW}★ Lvl {ship.mastery.level} [{ship.mastery.xp}/{ship.mastery.next_level_xp} XP]{RESET}           ║")
    print(f"║ Hull:      {_bar(ship.hull, ship.max_hull, 24, RED if ship.hull < 30 else GREEN)}                      ║")
    print(f"║ Shields:   {_bar(ship.shield, ship.max_shield, 24, BLUE)}                      ║")
    print(f"║ Fuel:      {_bar(ship.fuel, ship.max_fuel, 24, YELLOW)}                      ║")
    print(f"╠════ REACTOR POWER ROUTING ══════════════════════════════════════════╣{RESET}")
    p = ship.power
    print(f"║ Engines: {CYAN}{p.engines:>3}%{RESET}   Shields: {BLUE}{p.shields:>3}%{RESET}   Sensors: {MAGENTA}{p.sensors:>3}%{RESET}   Weapons: {RED}{p.weapons:>3}%{RESET}  (Total: {p.engines+p.shields+p.sensors+p.weapons:>3}%)║")
    reactor = engine.get_reactor_report()
    heat_color = RED if reactor["heat_pct"] >= 70 else (YELLOW if reactor["heat_pct"] >= 40 else GREEN)
    print(f"║ Core:      {heat_color}Heat {reactor['heat']:.0f}/{reactor['max_heat']:.0f}{RESET}  Integrity {reactor['integrity']:.0f}%  Mode {CYAN}{reactor['mode']}{RESET}  Output {YELLOW}{reactor['efficiency']*100:.0f}%{RESET} ║")

    # Sector map modifiers
    map_labels = [m.name for m in cur_sys.modifiers] or ["Standard space"]
    print(f"╠════ SECTOR MAP MODIFIERS ═══════════════════════════════════════════╣{RESET}")
    print(f"║ {CYAN}{', '.join(map_labels)[:67]:<67}{RESET} ║")

    # Structural modifications
    mod_labels = [f"{slot}:{mod_id}" for slot, mod_id in ship.ship_mods.items()] or ["No structural refits installed"]
    print(f"╠════ SHIP MODIFICATIONS ═════════════════════════════════════════════╣{RESET}")
    print(f"║ {MAGENTA}{', '.join(mod_labels)[:67]:<67}{RESET} ║")

    # Hardware upgrades summary
    upg_str = ", ".join(ship.upgrades) if ship.upgrades else "Standard Baseline"
    print(f"╠════ INSTALLED HARDWARE MODULES ═════════════════════════════════════╣{RESET}")
    print(f"║ {CYAN}{upg_str:<67}{RESET} ║")

    # Active contracts summary
    ready_cnt = sum(1 for c in ship.active_contracts if c.completed)
    contract_note = f"{len(ship.active_contracts)} active assignments ({ready_cnt} ready to claim!)" if ready_cnt > 0 else f"{len(ship.active_contracts)} active bounty contracts"
    print(f"╠════ SECTOR CONTRACTS & BOUNTIES ════════════════════════════════════╣{RESET}")
    print(f"║ {YELLOW}{contract_note:<67}{RESET} ║")

    # Fleet summary
    num_drones = len(ship.fleet_drones)
    drone_summary = f"{num_drones} active drones / escorts deployed" if num_drones > 0 else "No active drones"
    print(f"╠════ AUTONOMOUS FLEET ASSETS ════════════════════════════════════════╣{RESET}")
    print(f"║ {GREEN}{drone_summary:<67}{RESET} ║")

    # Cash flow telemetry
    flow = engine.cash_flow()
    net = flow["net_per_month"]
    flow_color = GREEN if net >= 0 else RED
    flow_summary = f"Payroll -{flow['upkeep_per_month']} | Passive +{flow['passive_per_month']} | Net {net:+.1f} cr/month"
    print(f"╠════ CASH FLOW TELEMETRY ════════════════════════════════════════════╣{RESET}")
    print(f"║ {flow_color}{flow_summary[:67]:<67}{RESET} ║")

    # Cadet Academy & Story progression
    tut = ship.tutorial
    if tut.is_active:
        step = tut.current_step
        tut_msg = f"Milestone {tut.current_step_index + 1}/{len(tut.steps)}: {step.title} -> {step.hint}"
        print(f"╠════ CADET FLIGHT ACADEMY ═══════════════════════════════════════════╣{RESET}")
        print(f"║ {YELLOW}{tut_msg[:67]:<67}{RESET} ║")
    elif tut.completed:
        tut_msg = "🎓 Graduated: Cadet Honor Wings equipped (+1,500 cr, +400 XP)"
        print(f"╠════ CADET FLIGHT ACADEMY ═══════════════════════════════════════════╣{RESET}")
        print(f"║ {GREEN}{tut_msg[:67]:<67}{RESET} ║")

    story = ship.story
    if story.completed:
        chap_msg = "⭐ Campaign Concluded: The Precursor Cipher [ALL ACTS RESOLVED]"
    else:
        chap = story.current_chapter
        chap_status = "COMPLETED" if chap.completed else f"TARGET: {chap.target_system_id}"
        chap_title = chap.title.split(": ", 1)[-1] if chap.title.startswith("Act ") else chap.title
        chap_msg = f"Act {story.active_act}: {chap_title} [{chap_status}]"
    print(f"╠════ THE PRECURSOR CIPHER (STORY) ════════════════════════════════════╣{RESET}")
    print(f"║ {MAGENTA}{chap_msg[:67]:<67}{RESET} ║")

    if ship.void_traversal is not None:
        vt = ship.void_traversal
        dest_sys = engine.state.systems.get(vt.destination_system_id)
        dest_name = dest_sys.name if dest_sys else vt.destination_system_id
        void_msg = f"In the Hollow Between -> {dest_name} | Stability {vt.stability:.0f}% | Storms {vt.storms_weathered} | Resonance {vt.resonance:.0f}"
        print(f"╠════ VOID TRAVERSAL ══════════════════════════════════════════════════╣{RESET}")
        print(f"║ {MAGENTA}{void_msg[:67]:<67}{RESET} ║")

    print(f"╠════ NAVIGATION COORDINATES ═════════════════════════════════════════╣{RESET}")
    print(f"║ System:    {CYAN}{cur_sys.name:<22}{RESET} Faction:  {cur_sys.faction:<22} ║")
    corp_str = f"Corp HQ:   {cur_sys.dominant_corp.replace('_', ' ').title():<22}" if cur_sys.dominant_corp else f"Corridors: {', '.join(cur_sys.connections)[:22]:<22}"
    print(f"║ Security:  {GREEN if cur_sys.security > 0.5 else RED}{cur_sys.security * 100:>5.1f}% [{('HIGH' if cur_sys.security > 0.7 else ('MED' if cur_sys.security > 0.3 else 'ANARCHY'))}]{RESET}       {corp_str} ║")
    orb_name = f"{body.name} [{body.body_type}]" if body else "Deep Space Transit"
    print(f"║ Orbit:     {orb_name:<57} ║")
    print(f"╚═════════════════════════════════════════════════════════════════════╝{RESET}")

    if engine.state.active_combat:
        c = engine.state.active_combat
        faction_badge = f" [{c.faction_id}]" if c.faction_id else ""
        print(f"\n{RED}{BOLD}⚔️  COMBAT INTERCEPT: {c.enemy_name.upper()} [{c.enemy_class.upper()}]{faction_badge}{RESET}")
        if c.enemy_max_shield > 0:
            print(f"   Enemy Shield: {_bar(c.enemy_shield, c.enemy_max_shield, 20, CYAN)}")
        print(f"   Enemy Hull:   {_bar(c.enemy_hull, c.enemy_max_hull, 20, RED)}")
        if c.telegraphed_action:
            print(f"   Telemetry:    {YELLOW}⚠ {c.telegraphed_action}{RESET}")
        print(f"   Hostile AI:   {CYAN}{c.ai_profile.upper()}{RESET} intent={c.enemy_intent.upper()}")
        if ship.tactical_combo > 0:
            crit_alert = f" {YELLOW}{BOLD}(CRITICAL OVERCHARGE READY!){RESET}" if ship.tactical_combo >= 2 else ""
            print(f"   Tactical Combo: {YELLOW}{BOLD}⚡ x{ship.tactical_combo}{crit_alert}{RESET}")
        print(f"   Tactical Options: {BOLD}combat fire{RESET} | {BOLD}combat drone{RESET} | {BOLD}combat target{RESET} | {BOLD}combat absorb{RESET} | {BOLD}combat evade{RESET} | {BOLD}combat flee{RESET}")

    elif engine.state.active_anomaly:
        anom = engine.state.active_anomaly
        print(f"\n{RED}{BOLD}⚠️  PROXIMITY ALERT: {anom.title}{RESET}")
        print(f"{DIM}{anom.description}{RESET}")
        print(f"{YELLOW}Resolution Choices:{RESET}")
        for ch in anom.choices:
            req = f"[{ch.required_power.upper()} >= {ch.min_power_threshold}%]" if ch.required_power != "none" else "[No Check]"
            print(f"  • {BOLD}{ch.choice_id}{RESET}: {ch.text} {DIM}{req}{RESET}")

    return 0


def cmd_time(engine: SimulationEngine, storage: StorageManager, argv: list[str]) -> int:
    """Manage simulation cosmic time, ticks, and speed controls."""
    if not argv or argv[0].lower() in ("status", "info"):
        t = engine.state.time
        print(f"\n{BOLD}{CYAN}╔════ COSMIC CHRONOMETRY & TEMPORAL MATRIX ════════════════════════════╗{RESET}")
        print(f"║ Date:           {YELLOW}{t.current_date}{RESET}               Epoch Tick:     {CYAN}#{t.tick}{RESET}")
        state_str = "RUNNING" if not t.is_paused else "PAUSED"
        color = GREEN if not t.is_paused else RED
        print(f"║ Temporal Speed: {color}{t.time_scale:<18}{RESET} Temporal State: {color}{state_str:<10}{RESET}")
        print(f"║ Stardate:       {t.stardate:.2f}               Elapsed Time:   {t.elapsed_days:.2f} standard days")
        print(f"╠════ TEMPORAL COMMANDS ═══════════════════════════════════════════════╣{RESET}")
        print(f"║  • {CYAN}time pause{RESET}                 Freeze temporal progression (0x)")
        print(f"║  • {CYAN}time resume{RESET}                Resume normal temporal flow (1.0x)")
        print(f"║  • {CYAN}time speed <x>{RESET}             Set speed multiplier (0.0 to 10.0x)")
        print(f"║  • {CYAN}time step [n]{RESET}              Advance simulation by n ticks immediately")
        print(f"╚══════════════════════════════════════════════════════════════════════╝{RESET}\n")
        return 0

    sub = argv[0].lower()
    if sub == "pause":
        ok, msg = engine.pause_time()
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0

    elif sub in ("resume", "play"):
        ok, msg = engine.resume_time()
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0

    elif sub == "speed":
        if len(argv) < 2:
            print(f"{RED}Usage:{RESET} time speed <0|1|2|5|10>")
            return 1
        try:
            sp = float(argv[1])
        except ValueError:
            print(f"{RED}Invalid speed factor '{argv[1]}'. Must be a numeric value.{RESET}")
            return 1
        ok, msg = engine.set_time_speed(sp)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0

    elif sub in ("step", "wait", "tick"):
        ticks = 1
        if len(argv) >= 2:
            try:
                ticks = max(1, int(argv[1]))
            except ValueError:
                print(f"{RED}Invalid tick count '{argv[1]}'. Must be an integer.{RESET}")
                return 1
        ok, msg, summary = engine.step_time(ticks)
        print((GREEN if ok else RED) + msg + RESET)
        if summary.get("shield_recharged", 0) > 0:
            print(f"{CYAN}⚡ Deflector shields restored +{summary['shield_recharged']} capacitance over time.{RESET}")
        storage.save(engine.state)
        return 0

    print(f"{RED}Unknown time command '{argv[0]}'. Use: time [status|pause|resume|speed <x>|step <n>]{RESET}")
    return 1


def cmd_chart(engine: SimulationEngine) -> int:
    """Print galaxy starmap and celestial bodies within current system."""
    cur_sys = engine.current_system
    print(f"\n{BOLD}{CYAN}=== GALAXY SECTOR HYPERLANE NETWORK ==={RESET}")
    for sid, s in engine.state.systems.items():
        marker = f"{YELLOW}▶ [FLAGSHIP]{RESET}" if sid == cur_sys.id else ("  [VISITED] " if sid in engine.state.visited_systems else "  [UNSEEN]  ")
        conns = ", ".join(s.connections)
        sec = f"{GREEN}SEC {s.security:.1f}{RESET}" if s.security > 0.5 else f"{RED}SEC {s.security:.1f}{RESET}"
        mods = f" | {CYAN}{', '.join(m.name for m in s.modifiers)}{RESET}" if s.modifiers else ""
        print(f"{marker} {BOLD}{s.name:<18}{RESET} ({sid}) | {sec} | Links: {conns}{mods}")

    print(f"\n{BOLD}{CYAN}=== CELESTIAL BODIES IN {cur_sys.name.upper()} ==={RESET}")
    if cur_sys.modifiers:
        print(f"{DIM}Sector modifiers:{RESET} {CYAN}{', '.join(m.name for m in cur_sys.modifiers)}{RESET}")
    for b in cur_sys.bodies:
        is_orb = " [IN ORBIT]" if engine.state.ship.orbiting_body_id == b.id else ""
        dock = f"{GREEN}[DOCKABLE]{RESET}" if b.station_dockable else f"{DIM}[NO DOCK]{RESET}"
        scan = f"{CYAN}[SCANNED]{RESET}" if b.scan_completed else f"{YELLOW}[UNSCANNED]{RESET}"
        print(f"  • {BOLD}{b.name:<24}{RESET} ({b.id}) | {b.body_type:<15} | Dist: {b.orbit_radius:.2f} AU | {dock} {scan}{is_orb}")

    return 0


def cmd_market(engine: SimulationEngine) -> int:
    """Display commodity prices and supply/demand at the current orbital body."""
    body = engine.orbiting_body
    if not body or not body.station_dockable:
        print(f"{RED}Error:{RESET} Ship must establish orbit around a station or colony to access trade network.")
        print(f"{YELLOW}Fix:{RESET} Run `voidfarer orbit <body_id>` to enter orbit first.")
        return 1

    sys_faction_id = get_faction_id_from_name(engine.current_system.faction)
    standing = engine.state.ship.faction_standings.get(sys_faction_id, 0)
    quotes = [
        calculate_dynamic_market_quote(
            engine.current_system, body, comm, engine.state.economy, faction_standing=standing
        )
        for comm in COMMODITY_MAP.values()
    ]
    standing_factor = faction_standing_price_factor(standing)
    print(f"\n{BOLD}{CYAN}=== LOCAL COMMODITY EXCHANGE: {body.name.upper()} ==={RESET}")
    print(f"Market Archetype: {BOLD}{body.market_archetype.upper()}{RESET} | Credits: {YELLOW}{engine.state.ship.credits} cr{RESET} | Standing: {BOLD}x{standing_factor:.2f}{RESET}")
    print(f"{'-' * 70}")
    print(f"{'COMMODITY':<22} {'BUY':>8} {'SELL':>8} {'SUPPLY':>8} {'DEMAND':>8} {'HOLD':>8}")
    print(f"{'-' * 70}")
    cargo = engine.state.ship.cargo
    for q in quotes:
        hold_qty = cargo.get(q.commodity_id, 0)
        print(f"{q.name:<22} {GREEN}{q.buy_price:>6} cr{RESET} {YELLOW}{q.sell_price:>6} cr{RESET} {q.supply:>8} {q.demand:>8} {BOLD}{hold_qty:>8}{RESET}")
    print(f"{'-' * 70}")
    return 0


def cmd_economy(engine: SimulationEngine) -> int:
    """Display galactic macroeconomic conditions, active events, and lucrative trade routes."""
    econ = engine.state.economy
    print(f"\n{BOLD}{CYAN}=== GALACTIC ECONOMY & MACROECONOMIC INTELLIGENCE ==={RESET}")
    print(f"Simulation Tick: {YELLOW}#{engine.state.time.tick}{RESET} | Known Systems: {CYAN}{len(engine.state.systems)}{RESET}\n")

    print(f"{BOLD}Active Macroeconomic Shocks & Galactic News:{RESET}")
    if not econ.active_events:
        print(f"  {DIM}Galaxy is currently in economic equilibrium. No major shortages or crises reported.{RESET}")
    else:
        for evt in econ.active_events:
            sys_name = engine.state.systems[evt.system_id].name if evt.system_id in engine.state.systems else evt.system_id
            badge = f"{RED}[CRISIS]{RESET}" if evt.price_multiplier > 1.2 else f"{GREEN}[BOOM]{RESET}"
            pct = int((evt.price_multiplier - 1.0) * 100)
            sign = f"+{pct}%" if pct > 0 else f"{pct}%"
            print(f"  • {badge} {BOLD}{evt.title}{RESET} ({sys_name})")
            print(f"    Impact: {YELLOW}{evt.commodity_id.upper()}{RESET} prices {YELLOW}{sign}{RESET} | Clocks: {CYAN}{evt.duration_ticks} ticks remaining{RESET}")
            print(f"    {DIM}{evt.description}{RESET}\n")

    print(f"{BOLD}Top Interstellar Trade Routes (Arbitrage Opportunities):{RESET}")
    routes = get_galactic_trade_routes(engine.state.systems, econ)
    if not routes:
        print(f"  {DIM}No trade routes found.{RESET}")
    else:
        print(f"  {'COMMODITY':<20} {'BUY FROM':<22} {'SELL TO':<22} {'PROFIT/U':>10} {'MARGIN':>8}")
        print(f"  {'-' * 86}")
        for r in routes[:6]:
            print(f"  {BOLD}{r['commodity_name']:<20}{RESET} {GREEN}{r['buy_system_name']} ({r['buy_price']} cr){RESET:<22} {YELLOW}{r['sell_system_name']} ({r['sell_price']} cr){RESET:<22} {GREEN}+{r['profit_per_unit']} cr{RESET:>10} {CYAN}{r['profit_margin_pct']}%{RESET:>8}")
        print(f"  {'-' * 86}")
    return 0


def cmd_inventory(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Display and manage ship cargo manifest, usable consumables, and hold capacity."""
    ship = engine.state.ship
    if len(parts) == 1 or parts[1].lower() in ("list", "status", "manifest"):
        print(f"\n{BOLD}{CYAN}=== FLAGSHIP INVENTORY & CARGO MANIFEST ==={RESET}")
        manifest = get_inventory_manifest(ship.cargo)
        used_vol = sum(item['total_volume'] for item in manifest)
        print(f"Hold Capacity: {_bar(used_vol, ship.cargo_capacity, 24, YELLOW if used_vol < ship.cargo_capacity else RED)} units")
        print(f"Credits:       {YELLOW}{ship.credits} cr{RESET}\n")

        if not manifest:
            print(f"{DIM}Cargo hold is currently empty.{RESET}")
            print(f"Purchase commodities at orbital markets (`market`), or buy consumables (`inventory buy`).")
            return 0

        print(f"{'ID':<24} {'NAME':<24} {'CATEGORY':<14} {'QTY':>6} {'TOTAL VOL':>10} {'USABLE':<8}")
        print(f"{'-' * 90}")
        for item in manifest:
            usable_str = f"{GREEN}YES{RESET}" if item['is_usable'] else f"{DIM}NO{RESET}"
            print(f"{item['id']:<24} {BOLD}{item['name']:<24}{RESET} {CYAN}{item['category']:<14}{RESET} {item['quantity']:>6} {item['total_volume']:>10} {usable_str:<8}")
            print(f"  {DIM}└─ {item['description']}{RESET}")
        print(f"{'-' * 90}")
        print(f"Subcommands: {BOLD}inventory buy <item_id> [qty]{RESET} | {BOLD}inventory use <item_id>{RESET} | {BOLD}inventory jettison <item_id> <quantity>{RESET}")
        return 0

    sub = parts[1].lower()
    if sub == "buy":
        if len(parts) < 3:
            consumables = ", ".join(sorted(k for k, v in ITEM_CATALOG.items() if v.category == "consumable"))
            print(f"{RED}Usage:{RESET} inventory buy <item_id> [quantity]")
            print(f"{DIM}Available consumables:{RESET} {consumables}")
            return 1
        item_id = parts[2].lower()
        try:
            qty = int(parts[3]) if len(parts) > 3 else 1
        except ValueError:
            print(f"{RED}Error:{RESET} Quantity must be an integer.")
            return 1
        ok, msg = engine.buy_item(item_id, qty)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if sub == "use":
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} inventory use <item_id>")
            return 1
        item_id = parts[2].lower()
        ok, msg = engine.use_item(item_id)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    elif sub in ("jettison", "drop", "discard"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} inventory jettison <item_id> [quantity]")
            return 1
        item_id = parts[2].lower()
        try:
            qty = int(parts[3]) if len(parts) > 3 else 1
        except ValueError:
            print(f"{RED}Error:{RESET} Quantity must be an integer.")
            return 1
        ok, msg = engine.jettison_cargo(item_id, qty)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    print(f"{RED}Unknown inventory command '{sub}'. Options: list, buy <id> [qty], use <id>, jettison <id> [qty].{RESET}")
    return 1


def cmd_shipyard(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Orbital shipyard: inspect ship chassis upgrades, purchase vessels, and sell modules."""
    ship = engine.state.ship
    body = engine.orbiting_body
    if not body or not body.station_dockable:
        print(f"{RED}Error:{RESET} Ship must dock at an orbital station or colony to access shipyard drydocks.")
        return 1

    if len(parts) == 1 or parts[1].lower() in ("list", "status", "catalog"):
        print(f"\n{BOLD}{CYAN}=== ORBITAL SHIPYARD & CHASSIS SHOWROOM ==={RESET}")
        print(f"Station: {BOLD}{body.name}{RESET} | Commander Vault: {YELLOW}{ship.credits} cr{RESET}")
        print(f"Current Class: {GREEN}{ship.ship_class}{RESET} ({ship.hull}/{ship.max_hull} Hull, {ship.shield}/{ship.max_shield} Shield, {ship.cargo_capacity} Cargo)\n")

        print(f"{BOLD}Available Ship Chassis for Purchase:{RESET}")
        print(f"{'ID':<20} {'NAME':<28} {'CLASS':<22} {'COST':>8} {'HULL':>6} {'SHD':>6} {'CARGO':>6}")
        print(f"{'-' * 100}")
        for c in CATALOG_CHASSIS:
            is_cur = c.ship_class == ship.ship_class
            marker = f"{GREEN}[CURRENT]{RESET}" if is_cur else f"{YELLOW}{c.cost} cr{RESET}"
            print(f"{c.id:<20} {BOLD}{c.name:<28}{RESET} {CYAN}{c.ship_class:<22}{RESET} {marker:>8} {c.max_hull:>6} {c.max_shield:>6} {c.cargo_capacity:>6}")
            print(f"  {DIM}Perk: {c.specialty_perk} - {c.description}{RESET}")
        print(f"{'-' * 100}")
        print(f"Subcommands: {BOLD}shipyard chassis <id>{RESET} | {BOLD}shipyard sell <slot>{RESET} | {BOLD}upgrades{RESET}")
        return 0

    sub = parts[1].lower()
    if sub in ("chassis", "buy_chassis"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} shipyard chassis <chassis_id>")
            return 1
        cid = parts[2].lower()
        ok, msg = engine.buy_ship_chassis(cid)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    elif sub in ("sell", "uninstall"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} shipyard sell <slot>")
            return 1
        slot = parts[2].lower()
        ok, msg = engine.sell_upgrade(slot)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    print(f"{RED}Unknown shipyard command '{sub}'. Options: catalog, chassis <id>, sell <slot>.{RESET}")
    return 1


def cmd_fleet(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Manage autonomous fleet drones, mining escorts, and harvest yields."""
    if len(parts) == 1:
        # Show fleet roster
        drones = engine.state.ship.fleet_drones
        print(f"\n{BOLD}{CYAN}=== AUTONOMOUS FLEET COMMAND ROSTER ==={RESET}")
        if not drones:
            print(f"{DIM}No fleet drones currently commissioned.{RESET}")
            print(f"Purchase drones at orbital drydocks using: {BOLD}fleet buy <mining|scout|combat_escort>{RESET}")
            return 0

        print(f"{'ID':<18} {'NAME':<24} {'TYPE':<14} {'SYSTEM':<16} {'STATUS':<12} {'YIELD':<12}")
        print(f"{'-' * 98}")
        for d in drones:
            yield_str = f"+{d.cargo_accumulated} ore / +{d.credits_accumulated} cr"
            print(f"{d.id:<18} {BOLD}{d.name:<24}{RESET} {CYAN}{d.drone_type:<14}{RESET} {d.assigned_system_id:<16} {GREEN}{d.status:<12}{RESET} {YELLOW}{yield_str:<12}{RESET}")
        print(f"{'-' * 98}")
        print(f"Subcommands: {BOLD}fleet harvest{RESET} | {BOLD}fleet buy <type>{RESET} | {BOLD}fleet deploy <id> <system>{RESET}")
        return 0

    sub = parts[1].lower()
    if sub in ("ships", "escorts", "manager"):
        report = engine.get_fleet_manager_report()
        print(f"\n{BOLD}{CYAN}=== FLEET MANAGER: ESCORT WING ==={RESET}")
        if not report["ships"]:
            print(f"{DIM}No escort warships commissioned. Buy at a drydock: fleet buy_escort <type>{RESET}")
        for ship in report["ships"]:
            status_color = GREEN if ship["status"] == "escorting" else (YELLOW if ship["status"] == "damaged" else RED)
            print(
                f"{ship['id']:<16} {BOLD}{ship['name']:<28}{RESET} {ship['role']:<9} "
                f"HULL {ship['hull']}/{ship['max_hull']} SHIELD {ship['shield']}/{ship['max_shield']} "
                f"DMG {ship['damage']} {status_color}{ship['status']:<10}{RESET} SYS {ship['assigned_system_id']}"
            )
        print(f"\nFormation damage: {report['total_damage']} | Screen evasion: +{report['evasion_bonus']*100:.0f}%")
        print(f"{DIM}Catalog: {', '.join(ESCORT_CATALOG)}. Commands: fleet buy_escort <type> | fleet assign <id> <system> | fleet repair_escorts | fleet dismiss_escort <id>{RESET}")
        return 0
    if sub in ("buy_escort", "recruit_escort"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} fleet buy_escort <{'|'.join(ESCORT_CATALOG)}> [system]")
            return 1
        ok, msg = engine.buy_escort(parts[2], parts[3] if len(parts) > 3 else None)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub == "assign":
        if len(parts) < 4:
            print(f"{RED}Usage:{RESET} fleet assign <escort_id> <system_id>")
            return 1
        ok, msg = engine.assign_escort(parts[2], parts[3])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("repair_escorts", "repair_ships"):
        amount = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 60
        ok, msg = engine.repair_escorts(amount)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("dismiss_escort", "decommission"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} fleet dismiss_escort <escort_id>")
            return 1
        ok, msg = engine.dismiss_escort(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("harvest", "collect"):
        drone_id = parts[2] if len(parts) > 2 else None
        ok, msg, _ = engine.collect_drone_yield(drone_id)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1

    elif sub == "buy":
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} fleet buy <mining|scout|combat_escort> [assigned_system]")
            return 1
        d_type = parts[2].lower()
        sys_id = parts[3] if len(parts) > 3 else None
        ok, msg = engine.buy_drone(d_type, sys_id)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1

    elif sub == "deploy":
        if len(parts) < 4:
            print(f"{RED}Usage:{RESET} fleet deploy <drone_id> <target_system>")
            return 1
        ok, msg = engine.deploy_drone(parts[2], parts[3])
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1

    else:
        print(f"{RED}Unknown fleet command '{sub}'. Options: list, harvest, buy, deploy.{RESET}")
        return 1




def cmd_quests(engine: SimulationEngine) -> int:
    print(f"\n{BOLD}{CYAN}=== QUEST PANEL ==={RESET}")
    for quest in engine.get_quests():
        print(f"{BOLD}{quest['title']}{RESET} [{quest['kind'].upper()}]")
        print(f"  {quest['description']}")
        print(f"  Progress: {quest['progress']}/{quest['target_count']} // Reward: {quest['reward']}")
    print()
    return 0


def cmd_ai(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1] if len(parts) > 1 else "list"
    if action == "list":
        print(f"\n{BOLD}{CYAN}=== AI CAPTAINS ==={RESET}")
        for c in engine.state.ai_captains:
            print(f"{c.id:<18} {BOLD}{c.name:<20}{RESET} {c.archetype:<10} {c.system_id:<14} trust={c.trust:<4} ally={c.ally}")
        return 0
    if len(parts) < 3:
        print(f"{RED}Usage:{RESET} ai <hail|buy|sell|hire|ally> <captain_id> [commodity] [qty]")
        return 1
    captain_id = parts[2]
    commodity = parts[3] if len(parts) > 3 else None
    quantity = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
    ok, msg = engine.interact_ai(captain_id, action, commodity, quantity)
    print((GREEN if ok else RED) + msg + RESET)
    storage.save(engine.state)
    return 0 if ok else 1


def cmd_messages(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1] if len(parts) > 1 else "list"
    if action == "list":
        print(f"\n{BOLD}{CYAN}=== QUANTUM INBOX ==={RESET}")
        for m in engine.state.messages:
            marker = " " if m.read else "*"
            tree_mark = f" {MAGENTA}[TREE {m.tree_id}]{RESET}" if m.tree_id else ""
            resolved = f" {DIM}(resolved: {m.resolved_choice}){RESET}" if m.resolved_choice else ""
            print(f"{marker} {m.id:<24} {m.sender:<18} {m.subject}{tree_mark}{resolved}")
        return 0
    if action == "send":
        if len(parts) < 5:
            print(f"{RED}Usage:{RESET} messages send <recipient> <subject> <body>")
            return 1
        ok, msg = engine.send_quantum_message(parts[2], parts[3], " ".join(parts[4:]))
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    if action == "read":
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} messages read <message_id>")
            return 1
        ok, msg = engine.mark_message_read(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        message = next((m for m in engine.state.messages if m.id == parts[2]), None)
        if message:
            print(f"\n{BOLD}{message.subject}{RESET}\n{message.body}")
            for choice in message.choices:
                print(f"  [{choice.id}] {choice.label} - {DIM}{choice.description}{RESET}")
            if message.choices:
                print(f"{DIM}Choose: messages choose {message.id} <choice_id>{RESET}")
        storage.save(engine.state)
        return 0 if ok else 1
    if action in ("tree", "trees"):
        report = engine.get_message_tree_report()
        print(f"\n{BOLD}{CYAN}=== MESSAGE TREE CATALOG ==={RESET}")
        for tree in report["trees"]:
            print(f"{BOLD}{tree['name']}{RESET} ({tree['id']})")
            for node in tree["nodes"]:
                print(f"  node {node['id']}: {node['subject']} -> {', '.join(c['id'] for c in node['choices'])}")
        return 0
    if action == "choose":
        if len(parts) < 4:
            print(f"{RED}Usage:{RESET} messages choose <message_id> <choice_id>")
            return 1
        ok, msg = engine.resolve_message_choice(parts[2], parts[3])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown messages action '{action}'.{RESET}")
    return 1


def cmd_depot(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1] if len(parts) > 1 else "status"
    depot = next((d for d in engine.state.depots if d.system_id == engine.state.ship.current_system_id), None)
    if action == "status":
        if not depot:
            print(f"{RED}No depot in this system.{RESET}")
            return 1
        print(f"\n{BOLD}{CYAN}{depot.name}{RESET} ({depot.capacity} capacity)")
        for item, qty in sorted(depot.cargo.items()):
            print(f"  {item:<20} x{qty}")
        return 0
    if len(parts) < 3:
        print(f"{RED}Usage:{RESET} depot <deposit|withdraw|sell> <item> [qty]")
        return 1
    qty = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    handlers = {
        "deposit": engine.deposit_cargo,
        "withdraw": engine.withdraw_cargo,
        "sell": engine.sell_from_depot,
    }
    handler = handlers.get(action)
    if not handler:
        print(f"{RED}Unknown depot action '{action}'.{RESET}")
        return 1
    ok, msg = handler(parts[2], qty)
    print((GREEN if ok else RED) + msg + RESET)
    storage.save(engine.state)
    return 0 if ok else 1


def cmd_land(engine: SimulationEngine, storage: StorageManager, body_id: str) -> int:
    ok, msg = engine.land_on_body(body_id)
    print((GREEN if ok else RED) + msg + RESET)
    storage.save(engine.state)
    return 0 if ok else 1


def cmd_saves(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """List, save, load, or delete named save slots."""
    action = parts[1].lower() if len(parts) > 1 else "list"
    slot = parts[2] if len(parts) > 2 else "default"
    if action == "list":
        saves = storage.list_saves()
        print(f"\n{BOLD}{CYAN}=== SAVE SLOTS ==={RESET}")
        if not saves:
            print(f"{DIM}No save slots found.{RESET}")
            return 0
        for s in saves:
            print(
                f"  [{BOLD}{s['slot']:<14}{RESET}] {s['commander_name']} ({s['ship_class']}) | "
                f"System: {s['current_system_id']} | Date: {s['stardate']} (Tick #{s['tick']}) | {YELLOW}{s['credits']} cr{RESET}"
            )
        return 0
    try:
        if action == "save":
            storage.save(engine.state, slot=slot)
            print(f"{GREEN}Saved game state to slot '{slot}'.{RESET}")
            return 0
        if action == "load":
            loaded = storage.load(slot=slot)
            if loaded is None:
                print(f"{RED}No save found in slot '{slot}'.{RESET}")
                return 1
            ok, msg = engine.load_state(loaded)
            storage.save(engine.state)
            print((GREEN if ok else RED) + f"{msg} [{slot}]" + RESET)
            return 0 if ok else 1
        if action == "delete":
            deleted = storage.delete_save(slot=slot)
            if not deleted:
                print(f"{YELLOW}No save file existed for slot '{slot}'.{RESET}")
                return 1
            print(f"{GREEN}Deleted save slot '{slot}'.{RESET}")
            return 0
    except ValueError as exc:
        print(f"{RED}{exc}{RESET}")
        return 1
    print(f"{RED}Usage:{RESET} saves [list|save|load|delete] [slot]")
    return 1


def cmd_mercs(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1] if len(parts) > 1 else "list"
    if action == "list":
        print(f"\n{BOLD}{CYAN}=== MERCENARY CONTRACTS ==={RESET}")
        for merc in MERCENARY_CATALOG.values():
            print(f"{merc['id']:<16} {merc['name']:<20} {merc['cost']:>6} cr  {merc['description']}")
        return 0
    if len(parts) < 3:
        print(f"{RED}Usage:{RESET} mercs <hire> <merc_id> | mercs <dismiss|refit> <drone_id>")
        return 1
    if action == "hire":
        ok, msg = engine.hire_mercenary(parts[2])
    elif action == "dismiss":
        ok, msg = engine.dismiss_fleet_unit(parts[2])
    elif action == "refit":
        ok, msg = engine.refit_fleet_unit(parts[2])
    else:
        print(f"{RED}Unknown mercenary action '{action}'.{RESET}")
        return 1
    print((GREEN if ok else RED) + msg + RESET)
    storage.save(engine.state)
    return 0 if ok else 1


def cmd_allies(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1] if len(parts) > 1 else "list"
    if action == "list":
        print(f"\n{BOLD}{CYAN}=== ALLIANCES ==={RESET}")
        print("Allies:", ", ".join(engine.state.ship.allies) or "none")
        for c in engine.state.ai_captains:
            print(f"  {c.id:<18} {c.name:<20} trust={c.trust:<4} ally={c.ally}")
        return 0
    if action == "form" and len(parts) >= 3:
        ok, msg = engine.form_alliance(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Usage:{RESET} allies form <captain_id>")
    return 1

def cmd_upgrades(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Inspect and purchase hardware modules from station arsenal."""
    if len(parts) == 1:
        installed = engine.state.ship.equipped_upgrades
        print(f"\n{BOLD}{CYAN}=== STATION ARSENAL & HARDWARE UPGRADES ==={RESET}")
        print(f"Commander Balance: {YELLOW}{engine.state.ship.credits} cr{RESET}\n")
        print(f"{'SLOT':<10} {'ID':<24} {'NAME':<28} {'COST':>8} {'STATUS':<12}")
        print(f"{'-' * 84}")
        for u in CATALOG_UPGRADES:
            is_inst = installed.get(u.slot) == u.id
            status = f"{GREEN}[INSTALLED]{RESET}" if is_inst else f"{YELLOW}[AVAILABLE]{RESET}"
            print(f"{u.slot.upper():<10} {u.id:<24} {BOLD}{u.name:<28}{RESET} {u.cost:>6} cr {status}")
            print(f"  {DIM}└─ {u.description}{RESET}")
        print(f"{'-' * 84}")
        print(f"To purchase and equip: {BOLD}upgrades buy <upgrade_id>{RESET}")
        return 0

    sub = parts[1].lower()
    if sub == "buy":
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} upgrades buy <upgrade_id>")
            return 1
        ok, msg = engine.buy_upgrade(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    else:
        print(f"{RED}Unknown upgrades command '{sub}'. Options: list, buy.{RESET}")
        return 1


def cmd_combat(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Execute tactical combat maneuvers during hostile intercepts."""
    if len(parts) > 1 and parts[1].lower() in ("stance", "formation"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} combat stance <balanced|aggressive|defensive>")
            return 1
        ok, msg = engine.set_battle_stance(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if not engine.state.active_combat:
        print(f"{YELLOW}No active combat intercept detected in this sector.{RESET}")
        return 0

    if len(parts) < 2:
        c = engine.state.active_combat
        faction_badge = f"{YELLOW}[Faction: {c.faction_id}]{RESET}" if c.faction_id else ""
        print(f"\n{RED}{BOLD}⚔️  ACTIVE COMBAT: {c.enemy_name} ({c.enemy_class}) {faction_badge}{RESET}")
        if c.enemy_max_shield > 0:
            print(f"Enemy Shield:   {_bar(c.enemy_shield, c.enemy_max_shield, 20, CYAN)}")
        print(f"Enemy Hull:     {_bar(c.enemy_hull, c.enemy_max_hull, 20, RED)}")
        if c.special_ability and c.special_ability != "none":
            print(f"Hostile Tech:   {MAGENTA}{c.special_ability.replace('_', ' ').title()}{RESET}")
        if c.telegraphed_action:
            print(f"Hostile Action: {YELLOW}⚠ {c.telegraphed_action}{RESET}")
        print(f"\n{BOLD}Tactical maneuvers:{RESET}")
        print(f"  {BOLD}combat fire{RESET}    - Fire laser battery strike")
        print(f"  {BOLD}combat drone{RESET}   - Launch kinetic drone strike / sensor burn")
        print(f"  {BOLD}combat target{RESET}  - Target subsystem (e.g. combat target weapons)")
        print(f"  {BOLD}combat absorb{RESET}  - Overcharge shield capacitors")
        print(f"  {BOLD}combat evade{RESET}   - High-G thruster evasion")
        print(f"  {BOLD}combat flee{RESET}    - Emergency hyperspace jump (costs 8 fuel)")
        return 0

    sub = parts[1].lower()
    action_map = {
        "fire": "fire_lasers",
        "laser": "fire_lasers",
        "attack": "fire_lasers",
        "drone": "drone_strike",
        "dronestrike": "drone_strike",
        "strike": "drone_strike",
        "target": "target_weapons" if len(parts) <= 2 else ("target_shields" if "shield" in parts[2].lower() else "target_weapons"),
        "subsystem": "target_weapons",
        "absorb": "shield_absorb",
        "shield": "shield_absorb",
        "defend": "shield_absorb",
        "evade": "evasive_burn",
        "dodge": "evasive_burn",
        "flee": "flee",
        "escape": "flee",
    }
    action = action_map.get(sub, sub)
    ok, msg = engine.combat_action(action)
    print((GREEN if ok else RED) + msg + RESET)
    storage.save(engine.state)
    return 0 if ok else 1


def cmd_war(engine: SimulationEngine, storage: StorageManager, action: str, args: list[str]) -> int:
    """List active wars and their fronts, or pledge credits to one side."""
    if action == "support":
        if len(args) != 3:
            print(f"{RED}Usage:{RESET} war support <war_id> <faction_id> <credits>")
            return 2
        try:
            credits = int(args[2])
        except ValueError:
            print(f"{RED}Error:{RESET} Credits must be an integer.")
            return 2
        ok, msg = engine.support_war(args[0], args[1], credits)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    politics = engine.galactic_politics()
    print(f"\n{BOLD}{CYAN}GALACTIC POWERS{RESET}")
    for f in politics["factions"]:
        foes = ", ".join(f["at_war_with"]) or "at peace"
        print(f"  {f['name']:<26} {f['systems']:>2} systems  strength {f['strength']:>7.1f}  {DIM}{foes}{RESET}")
    if not politics["wars"]:
        print(f"\n  {DIM}No active wars.{RESET}")
        return 0
    print(f"\n{BOLD}{RED}ACTIVE WARS{RESET}")
    for w in politics["wars"]:
        lead = w["attacker"] if w["war_score"] >= 0 else w["defender"]
        print(f"  {w['id']}: {w['attacker']} vs {w['defender']}  score {w['war_score']:+.1f} ({lead} advancing)")
        print(f"    fronts: {len(w['fronts'])} lanes  captured: {', '.join(w['captured_systems']) or 'none'}")
        if w.get("player_party"):
            print(f"    {DIM}Your envoy can petition for a ceasefire: diplomacy ceasefire <faction_id>{RESET}")
    print(f"\n{DIM}Pledge credits: war support <war_id> <faction_id> <credits>{RESET}")
    print(f"{DIM}Sovereign wars end without you: exhaustion, captures or a bankrupt side.{RESET}")
    return 0


def cmd_settings(engine: SimulationEngine, storage: StorageManager, action: str, args: list[str]) -> int:
    """Show or change simulation options, chiefly how often quick-time decisions interrupt."""
    if action == "decisions" and args:
        ok, msg = engine.set_decision_cadence(args[0])
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    cadence = engine.decision_cadence
    cooldown = engine._decision_cooldown()
    ready_in = engine.decisions_ready_in()
    print(f"\n{BOLD}{CYAN}SIMULATION SETTINGS{RESET}")
    print(f"  Decision cadence: {YELLOW}{cadence}{RESET} (one prompt per {cooldown} ticks)")
    print(f"  Next decision possible in {ready_in} tick(s)")
    print(f"{DIM}Change it: settings decisions relaxed|normal|frequent{RESET}")
    return 0


def cmd_factions(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Inspect galactic sovereign factions, standings, active territory, and diplomatic perks."""
    print(f"\n{BOLD}{CYAN}╔════ GALACTIC FACTIONS & SOVEREIGN STANDINGS ═════════════════════════╗{RESET}")
    for fid, faction in CANONICAL_FACTIONS.items():
        standing = engine.state.ship.faction_standings.get(fid, 0)
        tier, perk = get_faction_standing_tier(standing)
        tier_color = RED if tier == "Hostile" else (YELLOW if tier == "Unfriendly" else (GREEN if tier in ("Friendly", "Allied") else WHITE))
        stand_bar = _bar(standing + 100, 200, 16, tier_color)
        print(f"║ {BOLD}{faction.name:<24}{RESET} Status: {tier_color}[{tier.upper()} ({standing:+d})]{RESET}  HQ: {faction.headquarters_system:<10} ║")
        print(f"║   Ideology: {DIM}{faction.ideology}{RESET}")
        print(f"║   Standing: {stand_bar}")
        print(f"║   Active Benefit/Tariff: {CYAN}{perk}{RESET}\n")
    print(f"{CYAN}╚══════════════════════════════════════════════════════════════════════╝{RESET}")
    return 0


def cmd_corporations(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Inspect interstellar megacorporations, commercial specialties, and corporate standing."""
    print(f"\n{BOLD}{YELLOW}╔════ INTERSTELLAR MEGACORPORATIONS & TRADE CONSORTIUMS ═══════════════╗{RESET}")
    for cid, corp in CANONICAL_CORPORATIONS.items():
        standing = engine.state.ship.corp_standings.get(cid, 0)
        stand_bar = _bar(standing + 100, 200, 16, YELLOW)
        print(f"║ {BOLD}{corp.name:<26}{RESET} Standing: {YELLOW}[{standing:+d}]{RESET}  HQ: {corp.headquarters_system:<10} ║")
        print(f"║   Specialty: {GREEN}{corp.specialty_commodity.replace('_', ' ').title()}{RESET} (+{int(corp.bonus_trade_margin*100)}% commercial sale profit)")
        print(f"║   Standing:  {stand_bar}")
        print(f"║   Perk:      {DIM}{corp.corporate_perk}{RESET}\n")
    print(f"{YELLOW}╚══════════════════════════════════════════════════════════════════════╝{RESET}")
    return 0


def cmd_contracts(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Inspect dynamic sector bounties, claim completed contracts, and trigger fresh assignments."""
    if len(parts) == 1 or parts[1].lower() in ("list", "show"):
        contracts = engine.state.ship.active_contracts
        print(f"\n{BOLD}{CYAN}=== ACTIVE SECTOR BOUNTIES & CONTRACTS ==={RESET}")
        if not contracts:
            print(f"{DIM}No active contracts in flight recorder.{RESET}")
            return 0

        for c in contracts:
            status_tag = f"{GREEN}[READY TO CLAIM]{RESET}" if c.completed else f"{YELLOW}[IN PROGRESS]{RESET}"
            prog_bar = _bar(c.current_count, c.target_count, 14, GREEN if c.completed else YELLOW)
            relic_tag = f" + Relic [{c.reward_relic_tier.upper()}]" if c.reward_relic_tier else ""
            print(f"• {BOLD}{c.title}{RESET} ({c.id}) - {CYAN}{c.category.upper()}{RESET} {status_tag}")
            print(f"  {DIM}{c.description}{RESET}")
            print(f"  Progress: {prog_bar} | Reward: {YELLOW}+{c.reward_credits} cr{RESET}, {CYAN}+{c.reward_xp} XP{RESET}{relic_tag}\n")

        ready = [c for c in contracts if c.completed]
        if ready:
            print(f"{GREEN}{BOLD}Claim completed assignment: contracts claim <id>{RESET}")
        else:
            print(f"{DIM}Advance contracts by exploring, scanning, trading, or defeating hostiles.{RESET}")
        return 0

    sub = parts[1].lower()
    if sub in ("refresh", "reroll"):
        ok, msg = engine.refresh_contracts()
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("claim", "complete"):
        if len(parts) < 3:
            ready = [c for c in engine.state.ship.active_contracts if c.completed]
            if len(ready) == 1:
                cid = ready[0].id
            else:
                print(f"{RED}Usage:{RESET} contracts claim <contract_id>")
                return 1
        else:
            cid = parts[2]

        ok, msg, _ = engine.claim_contract(cid)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    print(f"{RED}Unknown contracts command '{sub}'. Options: list, claim <id>, refresh.{RESET}")
    return 1


def cmd_mastery(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Display pilot progression rank, talent tree specializations, and allocate perks."""
    ship = engine.state.ship
    mastery = ship.mastery

    if len(parts) == 1 or parts[1].lower() in ("list", "status"):
        print(f"\n{BOLD}{CYAN}=== PILOT MASTERY & SPECIALIZATION TREE ==={RESET}")
        print(f"Pilot Level: {YELLOW}{BOLD}Rank {mastery.level}{RESET} | Unspent Talent Points: {GREEN}{BOLD}{mastery.talent_points}{RESET}")
        print(f"Career XP:   {_bar(mastery.xp, mastery.next_level_xp, 24, YELLOW)}")
        print(f"{'-' * 70}")

        for tid, t in PILOT_TALENTS.items():
            is_unlocked = tid in mastery.specializations
            status = f"{GREEN}[UNLOCKED]{RESET}" if is_unlocked else f"{YELLOW}[LOCKED - 1 PT]{RESET}"
            print(f"• {BOLD}{t['name']:<24}{RESET} ({tid}) | {CYAN}{t['category'].upper():<12}{RESET} {status}")
            print(f"  {DIM}{t['description']}{RESET}\n")

        print(f"{'-' * 70}")
        if mastery.talent_points > 0:
            print(f"{GREEN}{BOLD}Unlock specialization: mastery unlock <talent_id>{RESET}")
        else:
            print(f"{DIM}Earn Pilot XP through contracts, jump streaks, and combat to earn Talent Points.{RESET}")
        return 0

    sub = parts[1].lower()
    if sub in ("unlock", "learn", "buy"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} mastery unlock <talent_id>")
            return 1

        tid = parts[2].lower()
        ok, msg = engine.unlock_talent(tid)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    print(f"{RED}Unknown mastery command '{sub}'. Options: list, unlock <id>.{RESET}")
    return 1


def cmd_relics(engine: SimulationEngine) -> int:
    """Display recovered ancient Precursor relics and passive fleet bonuses."""
    relics = engine.state.ship.relics
    print(f"\n{BOLD}{CYAN}=== ANCIENT PRECURSOR RELICS VAULT ==={RESET}")
    if not relics:
        print(f"{DIM}No Precursor Relics recovered yet.{RESET}")
        print(f"Relics drop via sensor scans of planets, combat victories, and high-tier bounty contracts.")
        return 0

    rarity_colors = {
        "common": DIM,
        "rare": CYAN,
        "epic": MAGENTA,
        "legendary": YELLOW + BOLD,
    }

    for r in relics:
        color = rarity_colors.get(r.rarity, RESET)
        print(f"• {color}[{r.rarity.upper()}]{RESET} {BOLD}{r.name}{RESET} ({r.id})")
        print(f"  {DIM}{r.description}{RESET}\n")

    multipliers = calculate_passive_multipliers(engine.state.ship)
    print(f"{BOLD}Active Passive Fleet Modifiers:{RESET}")
    print(f"  Scan Bounty Boost:    +{int((multipliers['scan_bounty'] - 1.0) * 100)}%")
    print(f"  Trade Profit Margin:  +{int((multipliers['trade_margin'] - 1.0) * 100)}%")
    print(f"  Laser Strike Power:   +{int((multipliers['laser_dmg'] - 1.0) * 100)}%")
    print(f"  Shield Capacity:      +{int(multipliers['shield_cap'])} MW")
    print(f"  Hull Reinforcement:   +{int(multipliers['max_hull'])} HP")
    print(f"  Jump Fuel Efficiency: +{int((1.0 - multipliers['fuel_efficiency']) * 100)}%")
    print(f"  Fleet Drone Yield:    +{int((multipliers['drone_yield'] - 1.0) * 100)}%")
    return 0


def cmd_log(engine: SimulationEngine) -> int:
    """Display the captain's log: career statistics, milestones, and flight record."""
    report = engine.get_codex_report()
    totals = report["totals"]
    state = engine.state
    print(f"\n{BOLD}{CYAN}=== CAPTAIN'S LOG ==={RESET}")
    print(
        f"{YELLOW}{state.time.current_date}{RESET} | Tick {state.time.tick} | "
        f"{engine.current_system.name} | Commander {state.ship.commander_name}"
    )
    print(
        f"Milestones: {totals['claimed']}/{totals['entries']} claimed | "
        f"{totals['completed']} discovered | {GREEN if totals['ready'] else DIM}{totals['ready']} ready to claim{RESET}"
    )

    print(f"\n{BOLD}CAREER STATISTICS{RESET}")
    stats = report["stats"]
    for index in range(0, len(stats), 2):
        left = stats[index]
        right = stats[index + 1] if index + 1 < len(stats) else None
        line = f"  {left['label']:<24} {left['value']:>10}"
        if right:
            line += f"    {right['label']:<24} {right['value']:>10}"
        print(line)

    print(f"\n{BOLD}MILESTONE LOG{RESET}")
    if report["log"]:
        for entry in report["log"]:
            print(
                f"  {entry['date']:<12} {GREEN}+{RESET} {entry['title']:<28} "
                f"{YELLOW}+{entry['reward_credits']} CR / +{entry['reward_xp']} XP{RESET}"
            )
        if totals["ready"]:
            print(f"\n{YELLOW}Ready to claim: run `codex` to see milestones, then `codex claim <id>`.{RESET}")
    else:
        print(f"  {DIM}No milestones claimed yet. Run `codex` to inspect the discovery register.{RESET}")

    print(f"\n{BOLD}RECENT FLIGHT LOG{RESET}")
    if report["flight_log"]:
        for line in report["flight_log"][-8:]:
            print(f"  {DIM}{line}{RESET}")
    else:
        print(f"  {DIM}No flight entries recorded.{RESET}")
    return 0


def cmd_codex(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Inspect the discovery codex and claim completed milestone rewards."""
    sub = parts[1].lower() if len(parts) > 1 else "list"
    if sub in ("claim", "collect"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} codex claim <entry_id>")
            return 1
        ok, msg = engine.claim_codex_reward(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    report = engine.get_codex_report()
    entries = report["entries"]
    if sub in ("show", "info"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} codex show <entry_id>")
            return 1
        record = next((item for item in entries if item["id"] == parts[2]), None)
        if record is None:
            print(f"{RED}Unknown codex milestone '{parts[2]}'.{RESET}")
            return 1
        status = "CLAIMED" if record["claimed"] else ("READY TO CLAIM" if record["ready"] else "LOCKED")
        print(f"\n{BOLD}{CYAN}{record['title']}{RESET} ({record['id']})")
        print(f"Category: {record['category']} | Status: {status}")
        print(f"{record['description']}")
        print(f"Hint: {record['hint']}")
        print(f"Progress: {record['value']}/{record['target']} | Reward: {record['reward_summary']}")
        if record["claimed"]:
            print(f"Claimed on {record['claimed_date']}.")
        return 0

    category_filter = sub if any(category["id"] == sub for category in report["categories"]) else None
    if sub not in ("list", "status", "all") and category_filter is None:
        print(f"{RED}Unknown codex command '{sub}'. Options: list, show, claim, or a category id.{RESET}")
        return 1

    totals = report["totals"]
    print(f"\n{BOLD}{CYAN}=== DISCOVERY CODEX ==={RESET}")
    print(
        f"{totals['claimed']}/{totals['entries']} rewards claimed | "
        f"{totals['completed']} milestones discovered ({totals['completion_pct']}%) | "
        f"{GREEN if totals['ready'] else DIM}{totals['ready']} ready{RESET}"
    )
    for category in report["categories"]:
        if category_filter and category["id"] != category_filter:
            continue
        print(f"\n{BOLD}[{category['name'].upper()}]{RESET} {DIM}{category['description']}{RESET}")
        for record in entries:
            if record["category"] != category["id"]:
                continue
            if record["claimed"]:
                marker = f"{GREEN}+{RESET}"
                status = f"CLAIMED {record['claimed_date']}"
            elif record["ready"]:
                marker = f"{YELLOW}*{RESET}"
                status = f"READY {record['value']}/{record['target']}"
            elif record["completed"]:
                marker = f"{YELLOW}!{RESET}"
                status = f"{record['value']}/{record['target']}"
            else:
                marker = " "
                status = f"{record['value']}/{record['target']}"
            print(
                f"  [{marker}] {record['title']:<26} {status:<18} "
                f"{YELLOW}+{record['reward_credits']} CR / +{record['reward_xp']} XP{RESET}  {DIM}{record['id']}{RESET}"
            )
    if totals["ready"]:
        print(f"\n{YELLOW}Claim with: codex claim <entry_id>{RESET}")
    return 0


def cmd_streak(engine: SimulationEngine) -> int:
    """Display current expedition jump streak and active loss aversion multiplier."""
    ship = engine.state.ship
    mult = 1.0 + min(1.5, (ship.streak - 1) * 0.15)
    print(f"\n{BOLD}{CYAN}=== EXPEDITION JUMP STREAK ==={RESET}")
    print(f"Current Streak: {RED}{BOLD}🔥 {ship.streak} consecutive jumps{RESET}")
    print(f"Streak Multiplier: {YELLOW}{BOLD}x{mult:.2f}{RESET} (+{int((mult - 1.0) * 100)}% to all trade, scan, and contract rewards)")
    print(f"\n{DIM}Mechanics (Loss Aversion):{RESET}")
    print(f"  • Every successful hyperlane jump increments streak by +1 (capped at x2.50).")
    print(f"  • All scan credits, trade profits, and pilot XP scale with this multiplier.")
    print(f"  • {RED}CAUTION:{RESET} Fleeing from hostile combat resets your streak back to 1!")
    return 0


def cmd_tutorial(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Cadet Flight Academy progressive tutorial system."""
    tut = engine.state.ship.tutorial
    if len(parts) > 1:
        sub = parts[1].lower()
        if sub == "skip":
            ok, msg = engine.skip_tutorial()
            print((GREEN if ok else RED) + msg + RESET)
            if ok:
                storage.save(engine.state)
            return 0 if ok else 1
        elif sub == "reset":
            ok, msg = engine.reset_tutorial()
            print((GREEN if ok else RED) + msg + RESET)
            if ok:
                storage.save(engine.state)
            return 0 if ok else 1
        else:
            print(f"{RED}Unknown tutorial command '{sub}'. Options: skip, reset.{RESET}")
            return 1

    print(f"\n{BOLD}{CYAN}=== CADET FLIGHT ACADEMY: ONBOARDING SCRIPT ==={RESET}")
    if tut.completed:
        print(f"{GREEN}★ Status: GRADUATED{RESET} - All academy milestones mastered.")
        print(f"{DIM}You hold the Cadet Wings relic granting permanent scan and XP bonuses.{RESET}")
        print(f"Type {CYAN}tutorial reset{RESET} if you wish to run through the academy again.")
        return 0

    if tut.skipped:
        print(f"{YELLOW}★ Status: SKIPPED{RESET} - Independent Pilot Protocol active.")
        print(f"Type {CYAN}tutorial reset{RESET} to reactivate Cadet Academy guidance.")
        return 0

    step = tut.current_step
    print(f"Current Milestone: {YELLOW}{tut.current_step_index + 1}/{len(tut.steps)}{RESET} - {BOLD}{step.title}{RESET}")
    print(f"{CYAN}Instruction:{RESET} {step.description}")
    print(f"{DIM}Hint / Goal:{RESET} {step.hint}")
    print(f"Reward on completion: {YELLOW}+{step.reward_credits} cr{RESET}, {CYAN}+{step.reward_xp} XP{RESET}\n")

    print(f"{BOLD}Curriculum Progress:{RESET}")
    for i, s in enumerate(tut.steps):
        marker = f"{GREEN}[✓]{RESET}" if s.completed else (f"{YELLOW}[▶]{RESET}" if i == tut.current_step_index else f"{DIM}[ ]{RESET}")
        print(f"  {marker} {i + 1}. {s.title} ({s.action_target})")
    print(f"\n{DIM}Tip: Perform the required action naturally (e.g. orbit, scan, power, trade, fleet, jump).{RESET}")
    print(f"{DIM}You can skip academy prompts at any time using: tutorial skip{RESET}")
    return 0


def cmd_story(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """The Precursor Cipher: Branching episodic space opera campaign."""
    ship = engine.state.ship
    story = ship.story

    if len(parts) > 1 and parts[1].lower() in ("choose", "choice", "select"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} story choose <choice_id>")
            return 1
        cid = parts[2].lower()
        ok, msg = engine.make_story_choice(cid)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if story.completed:
        print(f"\n{BOLD}{MAGENTA}╔════ THE PRECURSOR CIPHER: NARRATIVE CAMPAIGN ════════════════════════╗{RESET}")
        ending = story.ending_id or "ending_sentinel"
        from voidfarer.story import ENDING_VARIANTS

        variant = ENDING_VARIANTS.get(ending, ENDING_VARIANTS["ending_sentinel"])
        print(f"║ {BOLD}{YELLOW}⭐ CAMPAIGN CONCLUDED: {variant['title'].upper()} ⭐{RESET}")
        print(f"║ Status: {GREEN}{'TRIUMPHANT VICTORY':<18}{RESET} Final Acts: {f'{len(story.chapters)} / {len(story.chapters)} COMPLETED':<26} ║")
        print(f"╠════ FACTION ALIGNMENT & REPUTATION ══════════════════════════════════╣{RESET}")
        rep = story.faction_reputation
        print(f"║ Sol Coalition: {CYAN}{rep.get('coalition', 0):>+4}{RESET}  │  Free Spacers Syndicate: {YELLOW}{rep.get('syndicate', 0):>+4}{RESET}  │  Precursor Watch: {MAGENTA}{rep.get('precursor', 0):>+4}{RESET} ║")
        print(f"╠════ EPILOGUE ════════════════════════════════════════════════════════╣{RESET}")
        print(f"  {variant['epilogue']}")
        print(f"\n{BOLD}Archived Subspace Transmissions ({len(story.transmission_log)} total):{RESET}")
        for tx in story.transmission_log[-3:]:
            speaker_color = CYAN if "Vance" in tx.speaker else (YELLOW if "Cipher" in tx.speaker else MAGENTA)
            print(f"\n  {speaker_color}[{tx.callsign.upper()} // {tx.speaker}]{RESET}")
            print(f"  \"{tx.message}\"")
        return 0

    chap = story.current_chapter
    chap_title = chap.title.split(": ", 1)[-1] if chap.title.startswith("Act ") else chap.title
    print(f"\n{BOLD}{MAGENTA}╔════ THE PRECURSOR CIPHER: NARRATIVE CAMPAIGN ════════════════════════╗{RESET}")
    print(f"║ {BOLD}Act {story.active_act}: {chap_title:<58}{RESET} ║")
    target_str = str(chap.target_system_id or "DEEP SPACE")[:12]
    status_label = "COMPLETED" if chap.completed else f"TARGET: {target_str}"
    print(f"║ Sector Target: {CYAN}{target_str:<12}{RESET} Status: {status_label:<34} ║")
    print(f"╠════ FACTION ALIGNMENT & REPUTATION ══════════════════════════════════╣{RESET}")
    rep = story.faction_reputation
    print(f"║ Sol Coalition: {CYAN}{rep.get('coalition', 0):>+4}{RESET}  │  Free Spacers Syndicate: {YELLOW}{rep.get('syndicate', 0):>+4}{RESET}  │  Precursor Watch: {MAGENTA}{rep.get('precursor', 0):>+4}{RESET} ║")
    print(f"╠════ SYNOPSIS ════════════════════════════════════════════════════════╣{RESET}")
    print(f"  {chap.synopsis}")

    status = engine.story_status()
    if status.get("unmet_requirements"):
        print(f"\n{YELLOW}{BOLD}OBJECTIVES REQUIRED:{RESET}")
        for req in status["unmet_requirements"]:
            print(f"  • {req}")

    print(f"\n{BOLD}Subspace Transmissions Log ({len(story.transmission_log)} recorded):{RESET}")

    recent = story.transmission_log[-3:] if story.transmission_log else []
    for tx in recent:
        speaker_color = CYAN if "Vance" in tx.speaker else (YELLOW if "Cipher" in tx.speaker else MAGENTA)
        print(f"\n  {speaker_color}[{tx.callsign.upper()} // {tx.speaker}]{RESET}")
        print(f"  \"{tx.message}\"")

    if not chap.completed and chap.choices:
        print(f"\n{BOLD}{YELLOW}⚡ CRITICAL MORAL DECISION REQUIRED:{RESET}")
        choice_status = {c["id"]: c for c in status.get("choices", [])}
        for c in chap.choices:
            cost_str = f" [Cost: {c.cost_credits} cr]" if c.cost_credits > 0 else ""
            state = choice_status.get(c.id, {})
            if state.get("locked"):
                reason = state.get("lock_reason") or "Requirements unmet"
                print(f"  • {BOLD}{c.id}{RESET}{cost_str}: {c.label}")
                print(f"    {RED}🔒 LOCKED - {reason}{RESET}")
            else:
                print(f"  • {BOLD}{c.id}{RESET}{cost_str}: {c.label}")
                print(f"    {DIM}{c.consequence_summary}{RESET}")
        print(f"\n{CYAN}Type: story choose <choice_id>{RESET} to resolve this encounter.")
    elif chap.completed:
        print(f"\n{GREEN}Chapter completed.{RESET} Follow navigational beacons to advance.")

    return 0


def cmd_void(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """The Hollow Between: void lane traversal between black-hole anchors."""
    sub = parts[1].lower() if len(parts) > 1 else "status"

    if sub in ("dive", "enter"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} void dive <system_id>")
            return 1
        ok, msg = engine.void_dive(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if sub == "emerge":
        ok, msg = engine.void_emerge()
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    status = engine.void_status()

    if sub in ("lanes", "map", "chart"):
        print(f"\n{BOLD}{MAGENTA}╔════ THE HOLLOW BETWEEN: VOID LANE CHART ═════════════════════════════╗{RESET}")
        for sys_id, neighbors in status["lanes"].items():
            system = engine.state.systems.get(sys_id)
            name = system.name if system else sys_id
            print(f"║ {CYAN}{name:<36}{RESET} -> {', '.join(neighbors)}")
        print(f"╚═════════════════════════════════════════════════════════════════════╝{RESET}")
        return 0

    print(f"\n{BOLD}{MAGENTA}╔════ THE HOLLOW BETWEEN: VOID TRAVERSAL ═════════════════════════════╗{RESET}")
    traversal = status["traversal"]
    if traversal is not None:
        dest_sys = engine.state.systems.get(traversal["destination_system_id"])
        dest_name = dest_sys.name if dest_sys else traversal["destination_system_id"]
        print(f"║ Status:     {MAGENTA}IN THE VOID{RESET} bound for {BOLD}{dest_name}{RESET}")
        print(f"║ Stability:  {_bar(int(traversal['stability']), 130, 24, GREEN if traversal['stability'] > 60 else RED)}")
        print(f"║ Storms:     {YELLOW}{traversal['storms_weathered']}{RESET} weathered  |  Progress: {int((status['traversal_progress'] or 0.0) * 100)}%")
        print(
            f"║ Resonance:  {YELLOW}{traversal.get('resonance', 0.0):.0f}{RESET} storm resonance  |  "
            f"Payout: ~{status.get('projected_resonance_credits', 0)} cr, ~{status.get('projected_resonance_xp', 0)} XP"
        )
        print(f"║ {CYAN}Type: void emerge{RESET} for emergency surfacing (prorated resonance, hull and shield damage).")
    else:
        if status["dive_ready"]:
            print(f"║ Status:     {GREEN}READY TO DIVE{RESET} (orbiting a black-hole event horizon)")
            print(f"║ Storm Risk: {YELLOW}{status['storm_chance'] * 100:.0f}%{RESET} per tick in the Hollow")
            print(f"╠════ CHARTED DESTINATIONS ════════════════════════════════════════════╣{RESET}")
            if status["destinations"]:
                for dest in status["destinations"]:
                    print(f"║ • {BOLD}{dest['system_id']:<24}{RESET} {dest['name']:<28} Fuel: ~{dest['fuel_estimate']}")
                print(f"║ {CYAN}Type: void dive <system_id>{RESET} to slip beyond the horizon.")
            else:
                print(f"║ No void lanes lead onward from this horizon.")
        else:
            print(f"║ Status:     {RED}VOID DRIVE OFFLINE{RESET}")
            for blocker in status["blockers"]:
                print(f"║ • {YELLOW}{blocker}{RESET}")
    print(f"╚═════════════════════════════════════════════════════════════════════╝{RESET}")
    return 0


def cmd_reactor(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Inspect reactor telemetry and manage thermal doctrine."""
    sub = parts[1].lower() if len(parts) > 1 else "status"
    reactor = engine.get_reactor_report()
    if sub in ("status", "list", "report"):
        print(f"\n{BOLD}{CYAN}=== REACTOR CORE SIMULATION ==={RESET}")
        print(f"Mode:        {YELLOW}{reactor['mode_name']}{RESET} ({reactor['mode']})")
        print(f"Core Heat:   {_bar(int(reactor['heat']), int(reactor['max_heat']), 24, RED if reactor['heat_pct'] >= 70 else YELLOW)}")
        print(f"Integrity:   {_bar(int(reactor['integrity']), int(reactor['max_integrity']), 24, GREEN)}")
        print(f"Output:      {YELLOW}{reactor['efficiency'] * 100:.0f}%{RESET} effective power")
        print(f"Cooling:     {CYAN}{reactor['cooling']:.1f}{RESET} heat/tick  |  Generation: {YELLOW}{reactor['heat_generation']:.1f}{RESET} heat/tick")
        print(f"Sector:      heat x{reactor['map_heat_mult']:.2f}, cooling {reactor['map_cooling_bonus']:+.1f}")
        print(f"\n{DIM}Modes:{RESET}")
        for mode_id, profile in REACTOR_MODES.items():
            marker = f"{GREEN}▶{RESET}" if mode_id == reactor["mode"] else " "
            print(f"  {marker} {BOLD}{mode_id:<10}{RESET} {profile['description']}")
        print(f"\n{DIM}Commands:{RESET} reactor mode <balanced|economy|overdrive|silent> | reactor vent | reactor repair")
        return 0

    if sub in ("mode", "set"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} reactor mode <balanced|economy|overdrive|silent>")
            return 1
        ok, msg = engine.set_reactor_mode(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if sub in ("vent", "purge", "cool"):
        ok, msg = engine.vent_reactor_coolant()
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if sub in ("repair", "service"):
        ok, msg = engine.repair_reactor()
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    print(f"{RED}Unknown reactor command '{sub}'. Options: status, mode, vent, repair.{RESET}")
    return 1


def cmd_mapmods(engine: SimulationEngine) -> int:
    """Display active sector map modifiers and their simulation effects."""
    system = engine.current_system
    print(f"\n{BOLD}{CYAN}=== SECTOR MAP MODIFIERS: {system.name.upper()} ==={RESET}")
    if not system.modifiers:
        print(f"{DIM}Standard space: no environmental modifiers active in this system.{RESET}")
    for modifier in system.modifiers:
        print(f"• {BOLD}{modifier.name}{RESET} [{modifier.category.upper()}] ({modifier.id})")
        print(f"  {DIM}{modifier.description}{RESET}")
        print(f"  Effects: {CYAN}{', '.join(describe_modifier_effects(modifier.effects)) or 'None'}{RESET}\n")
    print(f"{DIM}Other charted systems:{RESET}")
    for sid, candidate in engine.state.systems.items():
        if sid == system.id or not candidate.modifiers:
            continue
        print(f"  {candidate.name:<24} {', '.join(m.name for m in candidate.modifiers)}")
    return 0


def _describe_ship_mod_effects(effects: dict[str, float]) -> list[str]:
    labels = {
        "max_hull": ("Hull", 1.0),
        "max_shield": ("Shield", 1.0),
        "cargo_capacity": ("Cargo", 1.0),
        "reactor_output": ("Reactor output", 100.0),
        "reactor_cooling": ("Cooling", 1.0),
        "heat_capacity": ("Heat cap", 1.0),
        "heat_generation": ("Heat gen", 100.0),
        "reactor_integrity": ("Core integrity", 1.0),
        "combat_damage": ("Damage", 1.0),
        "drone_yield": ("Drone yield", 100.0),
    }
    out: list[str] = []
    for key, value in effects.items():
        if key == "fuel_efficiency":
            out.append(f"Fuel burn {int(-value * 100):+d}%")
        elif key == "scan_mult":
            out.append(f"Scan yield {int(round((value - 1.0) * 100)):+d}%")
        elif key in ("evasion", "relic_find", "trade_margin"):
            out.append(f"{key.replace('_', ' ').title()} {int(value * 100):+d}%")
        else:
            label, scale = labels.get(key, (key.replace("_", " ").title(), 1.0))
            out.append(f"{label} {int(round(value * scale)):+d}")
    return out


def cmd_refit(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    """Ship modification section: inspect, install, or remove structural refits."""
    sub = parts[1].lower() if len(parts) > 1 else "list"
    if sub in ("list", "status", "catalog"):
        report = engine.get_ship_mod_report()
        print(f"\n{BOLD}{CYAN}=== SHIP MODIFICATION SECTION ==={RESET}")
        print(f"{DIM}Structural refits are permanent until removed at a drydock. Each slot holds one modification.{RESET}\n")
        for slot in report["slots"]:
            installed_id = report["installed"].get(slot)
            installed = get_ship_mod(installed_id) if installed_id else None
            status = f"{GREEN}{installed.name}{RESET}" if installed else f"{DIM}empty{RESET}"
            print(f"{BOLD}{slot_label(slot):<20}{RESET} [{status}]")
        print(f"\n{BOLD}Available modifications:{RESET}")
        installed_ids = set(report["installed"].values())
        for mod in CATALOG_SHIP_MODS:
            if mod.id in installed_ids:
                continue
            print(f"  • {BOLD}{mod.name}{RESET} ({mod.id}) [{slot_label(mod.slot)}] - {YELLOW}{mod.cost} cr{RESET}")
            print(f"    {DIM}{mod.description}{RESET}")
        print(f"\n{DIM}Install:{RESET} refit install <mod_id>   {DIM}Remove:{RESET} refit remove <slot>")
        return 0

    if sub in ("install", "buy"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} refit install <mod_id>")
            return 1
        ok, msg = engine.install_ship_mod(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if sub in ("remove", "sell", "uninstall"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} refit remove <slot>")
            return 1
        ok, msg = engine.remove_ship_mod(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1

    if sub in ("info", "show"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} refit info <mod_id>")
            return 1
        mod = get_ship_mod(parts[2])
        if not mod:
            print(f"{RED}Unknown ship modification '{parts[2]}'.{RESET}")
            return 1
        print(f"\n{BOLD}{mod.name}{RESET} ({mod.id}) [{slot_label(mod.slot)}] {YELLOW}{mod.cost} cr{RESET}")
        print(mod.description)
        print(f"Effects: {CYAN}{_describe_ship_mod_effects(mod.effects)}{RESET}")
        return 0

    print(f"{RED}Unknown refit command '{sub}'. Options: list, install, remove, info.{RESET}")
    return 1


def cmd_character(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    sub = parts[1].lower() if len(parts) > 1 else "status"
    if sub in ("status", "sheet", "list"):
        report = engine.get_character_report()
        ch = report["character"]
        print(f"\n{BOLD}{CYAN}=== COMMANDER PROFILE ==={RESET}")
        print(f"{BOLD}{ch['name']}{RESET} | Age {YELLOW}{ch['age']}{RESET} | Background {ch['background']} | Level {GREEN}{ch['level']}{RESET}")
        print(f"XP {ch['xp']}/{ch['next_level_xp']} | Skill points {YELLOW}{ch['skill_points']}{RESET}")
        print(f"{BOLD}Skills:{RESET}")
        for sid, info in report["skills"].items():
            print(f"  {info['name']:<14} R{info['level']}  {DIM}{info['description']}{RESET}")
        print(f"{BOLD}Abilities:{RESET}")
        for aid, info in report["abilities"].items():
            state = f"{GREEN}READY{RESET}" if info["unlocked"] and info["cooldown"] <= 0 else (f"{YELLOW}CD {info['cooldown']}{RESET}" if info["unlocked"] else f"{DIM}LOCKED{RESET}")
            print(f"  {aid:<20} {info['name']:<24} {state} {DIM}{info['description']}{RESET}")
        print(f"\n{DIM}Train: character train <skill> | Ability: character use <ability> [faction]{RESET}")
        return 0
    if sub in ("train", "learn"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} character train <{'|'.join(SKILL_CATALOG)}>")
            return 1
        ok, msg = engine.train_character_skill(parts[2].lower())
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("use", "ability"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} character use <{'|'.join(ABILITY_CATALOG)}> [faction_id]")
            return 1
        ok, msg = engine.use_character_ability(parts[2].lower(), parts[3] if len(parts) > 3 else None)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown character command '{sub}'. Options: status, train, use.{RESET}")
    return 1


def cmd_research(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    sub = parts[1].lower() if len(parts) > 1 else "status"
    report = engine.get_research_report()
    if sub in ("status", "list"):
        print(f"\n{BOLD}{CYAN}=== RESEARCH DIRECTORATE ==={RESET}")
        print(f"Banked points: {YELLOW}{report['points']}{RESET}")
        print(f"Active project: {CYAN}{report['active_project_id'] or 'none'}{RESET}")
        if report["active_project"]:
            p = report["active_project"]
            print(f"  {p['name']}: {_bar(report['progress'], p['cost'], 24, CYAN)}")
        print(f"Completed: {', '.join(report['completed']) or 'none'}")
        print(f"{BOLD}Available projects:{RESET}")
        for p in report["available"]:
            print(f"  {p['id']:<26} {p['name']:<30} {YELLOW}{p['cost']} pts{RESET} {DIM}{p['description']}{RESET}")
        print(f"\n{DIM}Start: research start <project_id>{RESET}")
        return 0
    if sub in ("start", "choose"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} research start <project_id>")
            return 1
        ok, msg = engine.choose_research(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown research command '{sub}'. Options: status, start.{RESET}")
    return 1


def cmd_outpost(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    sub = parts[1].lower() if len(parts) > 1 else "list"
    report = engine.get_outpost_report()
    if sub in ("list", "status"):
        print(f"\n{BOLD}{CYAN}=== OUTPOST COMMAND ==={RESET}")
        if not report["outposts"]:
            print(f"{DIM}No outposts founded. Orbit a body and use: outpost build <type> [body_id]{RESET}")
        for o in report["outposts"]:
            print(f"{o['id']:<34} {BOLD}{o['name']:<34}{RESET} LVL {o['level']} POP {o['population']:,} [{o['system_id']}]")
            print(f"  Production/tick: {CYAN}{o['production_effective']}{RESET}")
        print(f"{BOLD}Available outpost types:{RESET}")
        for t in OUTPOST_TYPES:
            print(f"  {t.id:<10} {t.name:<26} {YELLOW}{t.cost} cr{RESET} {DIM}{t.description}{RESET}")
        return 0
    if sub in ("build", "found"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} outpost build <type> [body_id]")
            return 1
        body_id = parts[3] if len(parts) > 3 else (engine.state.ship.orbiting_body_id or "")
        ok, msg = engine.build_outpost(body_id, parts[2].lower())
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("upgrade", "up"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} outpost upgrade <outpost_id>")
            return 1
        ok, msg = engine.upgrade_outpost(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown outpost command '{sub}'. Options: list, build, upgrade.{RESET}")
    return 1


def cmd_diplomacy(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    sub = parts[1].lower() if len(parts) > 1 else "list"
    if sub in ("list", "status"):
        print(f"\n{BOLD}{CYAN}=== FACTION DIPLOMACY ==={RESET}")
        for leader in engine.state.faction_leaders:
            faction = CANONICAL_FACTIONS.get(leader.faction_id)
            standing = engine.state.ship.faction_standings.get(leader.faction_id, 0)
            eliminated = leader.faction_id in engine.state.eliminated_factions
            print(
                f"{leader.faction_id:<20} {BOLD}{leader.name:<18}{RESET} {leader.title:<18} "
                f"{CYAN}{leader.behavior:<13}{RESET} standing {standing:+4d}"
                + (f" {RED}[ELIMINATED]{RESET}" if eliminated else "")
            )
        active_wars = [w for w in engine.state.wars if w.active]
        print(f"\nActive wars: {len(active_wars)}")
        for war in active_wars:
            print(f"  {war.attacker_id} vs {war.defender_id} | score {war.war_score:+.1f} | since tick {war.started_tick}")
        print(f"\n{DIM}Actions: diplomacy improve|gift|alliance|declare_war|peace <faction_id> [amount]{RESET}")
        return 0
    if len(parts) < 3:
        print(f"{RED}Usage:{RESET} diplomacy <improve|gift|alliance|declare_war|peace> <faction_id> [amount]")
        return 1
    amount = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    ok, msg = engine.faction_diplomacy(parts[2].lower(), sub, amount)
    print((GREEN if ok else RED) + msg + RESET)
    if ok:
        storage.save(engine.state)
    return 0 if ok else 1


def cmd_route(engine: SimulationEngine, target: str) -> int:
    plan = engine.plan_route(target)
    if not plan["reachable"]:
        print(f"{RED}No hyperlane route to '{target}'.{RESET}")
        return 1
    print(f"\n{BOLD}{CYAN}=== NAVIGATION PLOT: {target.upper()} ==={RESET}")
    print(f"Route: {YELLOW}{' -> '.join(plan['path'])}{RESET}")
    print(f"Jumps: {plan['jumps']} | Distance: {plan['distance_ly']} ly | Fuel estimate: {plan['fuel_estimate']}")
    if plan["black_hole_hazard"]:
        print(f"{RED}WARNING: black-hole hazard on route (+fuel demand).{RESET}")
    print(f"{DIM}Execute auto-route: navigate {target}{RESET}")
    return 0


def cmd_crew(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    sub = parts[1].lower() if len(parts) > 1 else "list"
    report = engine.get_crew_report()
    if sub in ("list", "status", "roster"):
        print(f"\n{BOLD}{CYAN}=== CREW ROSTER ==={RESET}")
        print(f"Active {report['active']}/{report['capacity']} | Upkeep {report['upkeep']} cr/month")
        for member in report["crew"]:
            morale_note = f"{RED}!! NEAR DESERTION{RESET}" if member["morale"] < 20 else (f"{YELLOW}LOW{RESET}" if member["morale"] < 35 else f"{GREEN}OK{RESET}")
            injury_note = f" {RED}INJURED {member.get('injury_ticks', 0)}t{RESET}" if member.get("injury_ticks", 0) else ""
            xp_note = f"{CYAN}XP {member.get('xp', 0)}/{max(1, member['skill'] * 40)}{RESET}"
            print(
                f"{member['id']:<18} {BOLD}{member['name']:<18}{RESET} {member['role']:<12} "
                f"SKILL {member['skill']} {xp_note} MORALE {member['morale']:.0f} [{morale_note}] WAGE {member['wage']} PORTRAIT {member['portrait']}{injury_note}"
            )
        print(f"\n{DIM}Recruit: crew recruit <{'|'.join(r.id for r in CREW_ROLES)}> | Drill: crew train <id> | Dismiss: crew dismiss <id> | Shore leave: crew shore{RESET}")
        print(f"{DIM}Away teams: away | away launch <mission_type> [crew_ids...] | away recall <mission_id>{RESET}")
        return 0
    if sub in ("recruit", "hire"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} crew recruit <{'|'.join(r.id for r in CREW_ROLES)}>")
            return 1
        ok, msg = engine.recruit_crew(parts[2].lower())
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("train", "drill"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} crew train <crew_id>")
            return 1
        ok, msg = engine.train_crew_member(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("shore", "leave", "rest"):
        ok, msg = engine.shore_leave()
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("dismiss", "fire"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} crew dismiss <crew_id>")
            return 1
        ok, msg = engine.dismiss_crew(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown crew command '{sub}'. Options: list, recruit, train, shore, dismiss.{RESET}")
    return 1


def cmd_away(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    sub = parts[1].lower() if len(parts) > 1 else "list"
    report = engine.get_away_report()
    body = report.get("body")
    if sub in ("list", "status", "teams"):
        print(f"\n{BOLD}{CYAN}=== AWAY TEAMS & EXPEDITIONS ==={RESET}")
        if not body:
            print(f"{YELLOW}No orbital body. Orbit a world or station to deploy an away team.{RESET}")
        else:
            hazards = ", ".join(body["hazards"]) if body["hazards"] else "none"
            print(f"Orbit: {BOLD}{body['name']}{RESET} [{body['body_type']}] | Hazards: {hazards}")
        if report["active"]:
            print(f"\n{BOLD}ACTIVE EXPEDITIONS ({len(report['active'])}/{report['max_active']}){RESET}")
            for mission in report["active"]:
                team = ", ".join(member["name"] for member in mission["team"])
                print(
                    f"  {mission['icon']} {BOLD}{mission['name']:<20}{RESET} {mission['body_name']:<28} "
                    f"RISK {mission['risk']}% | {mission['progress']:.0f}% | {mission['remaining_ticks']}t left | {team}"
                )
        else:
            print(f"\n{DIM}No away teams deployed.{RESET}")
        if body:
            print(f"\n{BOLD}AVAILABLE EXPEDITIONS{RESET}")
            for mission in report["available"]:
                team = ", ".join(member["name"] for member in mission["team"]) or "none"
                state = f"{GREEN}READY{RESET}" if mission["available"] else f"{YELLOW}BLOCKED{RESET}"
                risk_label = "N/A" if mission["risk"] is None else f"{mission['risk']}%"
                print(
                    f"  {mission['icon']} {BOLD}{mission['id']:<18}{RESET} {mission['name']:<20} "
                    f"RISK {risk_label} | {mission['duration_ticks']}t | team {len(mission['team'])}/{mission['team_size']} "
                    f"| {', '.join(mission['rewards'])} | {state}"
                )
                reason_note = f" - {mission['reason']}" if mission["reason"] else ""
                print(f"     {DIM}Best-fit team: {team}{reason_note}{RESET}")
        injuries = [member for member in report["crew"] if member["injury_ticks"] > 0]
        if injuries:
            print(f"\n{RED}INJURED CREW:{RESET} " + ", ".join(
                f"{member['name']} ({member['injury_ticks']}t)" for member in injuries
            ))
        print(f"\n{DIM}Deploy: away launch <mission_type> [crew_ids...] | Recall: away recall <mission_id>{RESET}")
        return 0
    if sub in ("launch", "deploy"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} away launch <mission_type> [crew_ids...]")
            return 1
        crew_ids = parts[3:] or None
        ok, msg = engine.launch_away_mission(parts[2], crew_ids)
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("recall", "abort"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} away recall <mission_id>")
            return 1
        ok, msg = engine.recall_away_mission(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown away command '{sub}'. Options: list, launch, recall.{RESET}")
    return 1


def cmd_pirate(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1].lower() if len(parts) > 1 else "status"
    pirate = engine.state.active_pirate
    if action in ("status", "list"):
        if pirate is None:
            print(f"\n{DIM}No pirate encounter active. Raid risk rises in pirate havens, low-security systems and hostile space.{RESET}")
            return 0
        print(f"\n{RED}{BOLD}=== PIRATE INTERCEPT ==={RESET}")
        print(f"{BOLD}{pirate.band_name}{RESET} // {pirate.ship_class} // threat {pirate.threat} // {pirate.system_name}")
        print(pirate.description)
        print(f"Toll demanded: {YELLOW}{pirate.toll_credits} cr{RESET} | Your credits: {engine.state.ship.credits}")
        print(f"{DIM}Resolve: pirate pay | pirate fight | pirate evade{RESET}")
        return 0
    if action not in ("pay", "fight", "evade", "flee"):
        print(f"{RED}Unknown pirate action '{action}'. Use pay, fight, or evade.{RESET}")
        return 1
    ok, msg = engine.resolve_pirate_encounter(action)
    print((GREEN if ok else RED) + msg + RESET)
    if ok:
        storage.save(engine.state)
    return 0 if ok else 1


def cmd_decision(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1].lower() if len(parts) > 1 else "status"
    pending = engine.state.pending_decision
    if action in ("status", "list", "show"):
        if pending is None:
            print(f"\n{DIM}No decision pending. Time and flight are clear.{RESET}")
            return 0
        print(f"\n{YELLOW}{BOLD}=== DECISION REQUIRED ==={RESET}")
        print(f"{BOLD}{pending.title}{RESET} [{pending.severity.upper()}]")
        print(pending.description)
        for choice in pending.choices:
            print(f"  {CYAN}{choice.id:<16}{RESET} {choice.label} - {choice.description}")
        print(f"{DIM}Resolve: decision choose <choice_id>{RESET}")
        return 0
    if action in ("choose", "resolve"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} decision choose <choice_id>")
            return 1
        ok, msg = engine.resolve_decision(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown decision action '{action}'. Use status or choose.{RESET}")
    return 1


def cmd_quantum(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1].lower() if len(parts) > 1 else "routes"
    report = engine.get_quantum_trade_report()
    if action in ("routes", "list", "freight"):
        if not report.get("docked"):
            print(f"\n{YELLOW}{report.get('message', 'Dock at a station first.')}{RESET}")
            return 1
        print(f"\n{BOLD}{CYAN}=== QUANTUM FREIGHT LANES ==={RESET}")
        print(f"Docked: {BOLD}{report.get('body', '')}{RESET} | active orders {len(report['orders'])}/{report['max_orders']}")
        if not report["routes"]:
            print(f"{DIM}No cargo in the hold with a profitable quantum lane.{RESET}")
        for route in report["routes"]:
            net_color = GREEN if route["net"] > 0 else RED
            print(
                f"  {BOLD}{route['commodity_name']:<18}{RESET} x{route['quantity']:<4} -> {route['destination_system_name']:<20} "
                f"{route['destination_name']:<18} {route['jumps']}j {route['duration_ticks']}t "
                f"FEE {route['fee']} cr PAYOUT {route['payout']} cr NET {net_color}{route['net']:+d} cr{RESET}"
            )
        print(f"{DIM}Ship: quantum ship <commodity_id> <quantity> <destination_system_id>{RESET}")
        return 0
    if action in ("orders", "status"):
        orders = report["orders"]
        if not orders:
            print(f"\n{DIM}No quantum freight orders in transit.{RESET}")
            return 0
        print(f"\n{BOLD}QUANTUM FREIGHT IN TRANSIT ({len(orders)}/{report['max_orders']}){RESET}")
        for order in orders:
            remaining = max(0, int(order["arrival_tick"]) - engine.state.time.tick)
            print(
                f"  {order['id']:<22} {order['quantity']}x {order['commodity_id']:<16} -> {order['destination_name']:<18} "
                f"ETA {remaining}t | fee {order['fee_paid']} cr"
            )
        return 0
    if action in ("ship", "send", "place"):
        if len(parts) < 5:
            print(f"{RED}Usage:{RESET} quantum ship <commodity_id> <quantity> <destination_system_id>")
            return 1
        try:
            quantity = int(parts[3])
        except ValueError:
            print(f"{RED}Quantity must be an integer.{RESET}")
            return 1
        ok, msg = engine.place_quantum_order(parts[2], quantity, parts[4])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown quantum action '{action}'. Use routes, orders or ship.{RESET}")
    return 1


def cmd_surface(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    action = parts[1].lower() if len(parts) > 1 else "list"
    report = engine.get_surface_report()
    if action in ("list", "status", "ops"):
        if not report.get("landed"):
            print(f"\n{YELLOW}No surface team deployed. Orbit a landable body and run `land <body_id>`.{RESET}")
            return 1
        body = report["body"]
        print(f"\n{BOLD}{CYAN}=== SURFACE OPERATIONS: {body['name']} ==={RESET}")
        print(f"{body['body_type']} | gravity {body['gravity']} | hazards {', '.join(body['hazards']) or 'none'} | worked {report['used_count']}/{report['total_count']}")
        for op in report["operations"]:
            if op["used"]:
                state = f"{DIM}WORKED{RESET}"
            else:
                state = f"{GREEN}READY{RESET}"
            print(
                f"  {BOLD}{op['id']:<18}{RESET} {op['name']:<20} RISK {op['risk']}% | "
                f"{op['credits']} cr | {op['research']} res | {op['credit_cost']} cr cost | {state}"
            )
            print(f"     {DIM}{op['description']}{RESET}")
        print(f"{DIM}Run: surface op <operation_id>{RESET}")
        return 0
    if action in ("op", "run"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} surface op <operation_id>")
            return 1
        ok, msg = engine.perform_surface_operation(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown surface action '{action}'. Use list or op.{RESET}")
    return 1


def cmd_weapons(engine: SimulationEngine, storage: StorageManager, parts: list[str]) -> int:
    sub = parts[1].lower() if len(parts) > 1 else "list"
    report = engine.get_weapon_report()
    if sub in ("list", "status", "catalog"):
        print(f"\n{BOLD}{CYAN}=== WEAPON SYSTEMS ==={RESET}")
        print(f"Primary: {YELLOW}{report['primary']}{RESET} | Installed: {', '.join(report['installed'])}")
        for weapon in report["catalog"]:
            marker = f"{GREEN}*{RESET}" if weapon["id"] in report["installed"] else " "
            print(
                f"{marker} {weapon['id']:<20} {BOLD}{weapon['name']:<26}{RESET} {weapon['weapon_type']:<9} "
                f"DMG {weapon['damage']:<3} SHD x{weapon['shield_mult']:.2f} HULL x{weapon['hull_mult']:.2f} "
                f"ACC {weapon['accuracy']*100:.0f}% {YELLOW}{weapon['cost']} cr{RESET}"
            )
        print(f"\n{DIM}Install/select: weapons install <weapon_id> | set <weapon_id>{RESET}")
        return 0
    if sub in ("install", "buy"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} weapons install <weapon_id>")
            return 1
        ok, msg = engine.install_weapon(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    if sub in ("set", "select"):
        if len(parts) < 3:
            print(f"{RED}Usage:{RESET} weapons set <weapon_id>")
            return 1
        ok, msg = engine.set_primary_weapon(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        if ok:
            storage.save(engine.state)
        return 0 if ok else 1
    print(f"{RED}Unknown weapons command '{sub}'. Options: list, install, set.{RESET}")
    return 1


def cmd_repl(engine: SimulationEngine, storage: StorageManager) -> int:
    """Launch interactive terminal command session."""
    engine.allow_decision_events = True
    # Print status upon entry
    cmd_status(engine)
    print(f"\n{GREEN}Sub-space quantum link active. Type 'help' for command matrix, 'serve' for Web HUD.{RESET}\n")

    server_handle: BackgroundServer | None = None

    while True:
        try:
            line = input(f"{CYAN}voidfarer [{engine.state.ship.current_system_id}]> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting VoidFarer link.")
            break

        if not line:
            continue

        # Clean user-pasted shell invocations (e.g. `py -m voidfarer.cli serve` or `python ...`)
        if line.startswith("py -m voidfarer.cli ") or line.startswith("python -m voidfarer.cli "):
            line = line.split("voidfarer.cli ")[1].strip()
        elif line.startswith("py ") or line.startswith("python "):
            print(f"{YELLOW}Note:{RESET} You are inside the VoidFarer interactive REPL. Omit 'python' or 'py'.")
            parts = line.split()
            if len(parts) > 1 and parts[1] != "-m":
                line = " ".join(parts[1:])
            else:
                continue

        parts = line.split()
        cmd = parts[0].lower()

        pending = engine.state.pending_decision
        pirate = engine.state.active_pirate
        allowed_while_blocked = {
            "decision", "decide", "pirate", "corsair", "status", "save",
            "serve", "time", "help", "?", "exit", "quit", "q",
        }
        if (pending is not None or pirate is not None) and cmd not in allowed_while_blocked:
            if pending is not None:
                print(f"{RED}Decision required:{RESET} {pending.title}. Use `decision` first.")
            else:
                print(
                    f"{RED}Pirate intercept unresolved:{RESET} {pirate.band_name} demands "
                    f"{pirate.toll_credits} cr. Use `pirate pay`, `pirate fight`, or `pirate evade`."
                )
            continue

        if cmd in ("exit", "quit", "q"):
            break
        elif cmd == "status":
            cmd_status(engine)
        elif cmd in ("chart",):
            cmd_chart(engine)
        elif cmd in ("map", "mapmods", "sector"):
            if len(parts) > 1 and parts[1].lower() in ("mods", "modifiers", "effects"):
                cmd_mapmods(engine)
            else:
                cmd_chart(engine)
        elif cmd in ("crew", "roster"):
            cmd_crew(engine, storage, parts)
        elif cmd in ("away", "expedition", "teams"):
            cmd_away(engine, storage, parts)
        elif cmd in ("pirate", "corsair"):
            cmd_pirate(engine, storage, parts)
        elif cmd in ("decision", "decide"):
            cmd_decision(engine, storage, parts)
        elif cmd in ("quantum", "freight"):
            cmd_quantum(engine, storage, parts)
        elif cmd in ("surface", "landing"):
            cmd_surface(engine, storage, parts)
        elif cmd in ("weapons", "weapon"):
            cmd_weapons(engine, storage, parts)
        elif cmd in ("reactor", "core", "thermal"):
            cmd_reactor(engine, storage, parts)
        elif cmd in ("character", "commander", "profile", "skills"):
            cmd_character(engine, storage, parts)
        elif cmd in ("research", "tech", "science"):
            cmd_research(engine, storage, parts)
        elif cmd in ("outpost", "outposts", "colony"):
            cmd_outpost(engine, storage, parts)
        elif cmd in ("diplomacy", "diplo", "leaders"):
            cmd_diplomacy(engine, storage, parts)
        elif cmd in ("route", "plot"):
            if len(parts) < 2:
                print(f"{RED}Usage:{RESET} route <system_id>")
            else:
                cmd_route(engine, parts[1])
        elif cmd in ("navigate", "autoroute"):
            if len(parts) < 2:
                print(f"{RED}Usage:{RESET} navigate <system_id>")
            else:
                ok, msg = engine.navigate_to(parts[1])
                print((GREEN if ok else RED) + msg + RESET)
                storage.save(engine.state)
        elif cmd in ("refit", "mods", "shipmods", "shipmod"):
            cmd_refit(engine, storage, parts)
        elif cmd == "market":
            cmd_market(engine)
        elif cmd == "fleet":
            cmd_fleet(engine, storage, parts)
        elif cmd in ("upgrades", "upgrade", "arsenal", "shop"):
            cmd_upgrades(engine, storage, parts)
        elif cmd in ("combat", "fight", "battle"):
            cmd_combat(engine, storage, parts)
        elif cmd in ("contracts", "contract", "bounties", "bounty"):
            cmd_contracts(engine, storage, parts)
        elif cmd in ("claim",):
            cmd_contracts(engine, storage, ["contracts", "claim"] + parts[1:])
        elif cmd in ("mastery", "talents", "talent", "perks"):
            cmd_mastery(engine, storage, parts)
        elif cmd in ("unlock",):
            cmd_mastery(engine, storage, ["mastery", "unlock"] + parts[1:])
        elif cmd in ("relics", "relic", "vault", "artifacts"):
            cmd_relics(engine)
        elif cmd in ("codex", "achievements", "milestones"):
            cmd_codex(engine, storage, parts)
        elif cmd in ("log", "journal", "captainslog"):
            cmd_log(engine)
        elif cmd in ("streak", "fire"):
            cmd_streak(engine)
        elif cmd in ("tutorial", "academy", "cadet"):
            cmd_tutorial(engine, storage, parts)
        elif cmd in ("story", "campaign", "act", "lore", "comms"):
            cmd_story(engine, storage, parts)
        elif cmd in ("void", "hollow"):
            cmd_void(engine, storage, parts)
        elif cmd in ("serve", "web", "gui", "hud"):
            if len(parts) > 1 and parts[1] in ("stop", "shutdown"):
                if server_handle is not None:
                    server_handle.stop()
                    server_handle = None
                    print(f"{GREEN}Holographic Web Cockpit stopped.{RESET}")
                else:
                    print(f"{YELLOW}Cockpit server is not running.{RESET}")
                continue

            port = 8080
            for i, p in enumerate(parts):
                if p in ("--port", "-p") and i + 1 < len(parts):
                    try:
                        port = int(parts[i + 1])
                    except ValueError:
                        print(f"{YELLOW}Invalid port '{parts[i + 1]}'; using {port}.{RESET}")
                elif p.isdigit():
                    port = int(p)

            if server_handle is None:
                server_handle = start_background_server(engine, storage, port=port)
                if server_handle is not None:
                    print(f"\n{GREEN}Holographic Web Cockpit HUD launched successfully!{RESET}")
                    print(f"{CYAN}Uplink URL: http://127.0.0.1:{server_handle.port}{RESET}")
                    print(f"{DIM}(Web HUD and simulation ticker are running concurrently; type 'serve stop' to stop.){RESET}\n")
                else:
                    print(f"{YELLOW}Cockpit server notice:{RESET} Could not bind port {port}. Choose another port with 'serve <port>'.")
            else:
                print(f"{CYAN}Holographic Web Cockpit is currently running at http://127.0.0.1:{server_handle.port}{RESET}")

        elif cmd == "jump":
            if len(parts) < 2:
                print(f"{RED}Usage:{RESET} jump <system_id>")
            else:
                ok, msg = engine.jump(parts[1])
                print((GREEN if ok else RED) + msg + RESET)
                storage.save(engine.state)
        elif cmd == "orbit":
            if len(parts) < 2:
                print(f"{RED}Usage:{RESET} orbit <body_id>")
            else:
                ok, msg = engine.orbit(parts[1])
                print((GREEN if ok else RED) + msg + RESET)
                storage.save(engine.state)
        elif cmd == "travel":
            if len(parts) < 2:
                print(f"{RED}Usage:{RESET} travel <body_id> [--mode sublight|quantum]")
            else:
                mode = "sublight"
                for idx, tok in enumerate(parts):
                    if tok == "--mode" and idx + 1 < len(parts):
                        mode = parts[idx + 1]
                    elif tok in ("sublight", "quantum"):
                        mode = tok
                ok, msg = engine.start_travel(parts[1], mode=mode)
                print((GREEN if ok else RED) + msg + RESET)
                storage.save(engine.state)
        elif cmd == "events":
            cmd_events(engine, storage, parts)
        elif cmd == "scan":
            ok, msg, _ = engine.scan()
            print((GREEN if ok else RED) + msg + RESET)
            storage.save(engine.state)
        elif cmd == "power":
            if len(parts) < 5:
                print(f"{RED}Usage:{RESET} power <engines> <shields> <sensors> <weapons>")
            else:
                try:
                    e, s, se, w = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                    ok, msg = engine.route_power(e, s, se, w)
                    print((GREEN if ok else RED) + msg + RESET)
                    storage.save(engine.state)
                except ValueError:
                    print(f"{RED}Error:{RESET} Power values must be integers summing to 100.")
        elif cmd == "buy":
            if len(parts) < 3:
                print(f"{RED}Usage:{RESET} buy <commodity_id> <quantity|max|all>")
            else:
                try:
                    if parts[2].lower() in ("max", "all"):
                        ok, msg = engine.trade_max(parts[1], is_buy=True)
                    else:
                        ok, msg = engine.trade(parts[1], int(parts[2]), is_buy=True)
                    print((GREEN if ok else RED) + msg + RESET)
                    storage.save(engine.state)
                except ValueError:
                    print(f"{RED}Error:{RESET} Quantity must be an integer.")
        elif cmd == "sell":
            if len(parts) < 3:
                print(f"{RED}Usage:{RESET} sell <commodity_id> <quantity|max|all>")
            else:
                try:
                    if parts[2].lower() in ("max", "all"):
                        ok, msg = engine.trade_max(parts[1], is_buy=False)
                    else:
                        ok, msg = engine.trade(parts[1], int(parts[2]), is_buy=False)
                    print((GREEN if ok else RED) + msg + RESET)
                    storage.save(engine.state)
                except ValueError:
                    print(f"{RED}Error:{RESET} Quantity must be an integer.")
        elif cmd == "anomaly":
            if len(parts) < 2:
                print(f"{RED}Usage:{RESET} anomaly <choice_id>")
            else:
                ok, msg = engine.resolve_anomaly(parts[1])
                print((GREEN if ok else RED) + msg + RESET)
                storage.save(engine.state)
        elif cmd == "repair":
            try:
                amt = int(parts[1]) if len(parts) > 1 else 25
            except ValueError:
                print(f"{RED}Error:{RESET} Repair amount must be an integer.")
                continue
            ok, msg = engine.repair_hull(amt)
            print((GREEN if ok else RED) + msg + RESET)
            storage.save(engine.state)
        elif cmd == "refuel":
            try:
                amt = int(parts[1]) if len(parts) > 1 else 20
            except ValueError:
                print(f"{RED}Error:{RESET} Fuel amount must be an integer.")
                continue
            ok, msg = engine.refuel(amt)
            print((GREEN if ok else RED) + msg + RESET)
            storage.save(engine.state)
        elif cmd in ("factions", "faction"):
            cmd_factions(engine, storage, parts)
        elif cmd in ("war", "wars"):
            cmd_war(engine, storage, parts[1].lower() if len(parts) > 1 else "list", parts[2:])
        elif cmd in ("settings", "options"):
            cmd_settings(engine, storage, parts[1].lower() if len(parts) > 1 else "show", parts[2:])
        elif cmd in ("corps", "corporations", "corp"):
            cmd_corporations(engine, storage, parts)
        elif cmd in ("time", "chrono", "tick", "wait"):
            cmd_time(engine, storage, parts[1:])
        elif cmd in ("economy", "econ"):
            cmd_economy(engine)
        elif cmd in ("inventory", "inv", "cargo"):
            cmd_inventory(engine, storage, parts)
        elif cmd in ("use",):
            cmd_inventory(engine, storage, ["inventory", "use"] + parts[1:])
        elif cmd in ("jettison", "drop"):
            cmd_inventory(engine, storage, ["inventory", "jettison"] + parts[1:])
        elif cmd in ("shipyard", "drydock"):
            cmd_shipyard(engine, storage, parts)
        elif cmd in ("chassis",):
            cmd_shipyard(engine, storage, ["shipyard", "chassis"] + parts[1:])
        elif cmd in ("saves", "save", "load"):
            if cmd in ("save", "load"):
                cmd_saves(engine, storage, ["saves", cmd] + parts[1:])
            else:
                cmd_saves(engine, storage, parts)
        elif cmd == "help":
            print(f"{BOLD}Available subcommands:{RESET}")
            print("  status                         - Telemetry, fleet roster, and subsystem readouts")
            print("  time [status|pause|speed|step] - Cosmic time, ticks, and temporal speed controls")
            print("  economy / econ                 - Galactic macroeconomic conditions and trade routes")
            print("  inventory [buy|use|jettison]   - Hold manifest, station consumables & usable items")
            print("  shipyard [chassis|sell]        - Orbital shipyard, chassis showroom, and drydocks")
            print("  chart / map                    - Hyperlane network & orbital bodies")
            print("  factions                       - Galactic factions, sovereign standings & perks")
            print("  war [list|support]             - Active wars, territory fronts & credit pledges")
            print("  corps / corporations           - Megacorporations, specialties & trade bonuses")
            print("  jump <system_id>               - Hyperspace jump to adjacent star")
            print("  orbit <body_id>                - Enter orbit around planet or station")
            print("  scan                           - Sensor sweep of orbiting body (relic discovery)")
            print("  contracts [claim <id>]         - Active sector bounty contracts (Zeigarnik loop)")
            print("  mastery [unlock <id>]          - Pilot rank, XP progression, and talent tree")
            print("  tutorial [skip|reset]          - Cadet Flight Academy onboarding and guidance")
            print("  story [choose <id>]            - The Precursor Cipher narrative campaign")
            print("  void [status|lanes|dive|emerge] - The Hollow Between void lane traversal")
            print("  relics                         - Ancient Precursor Relic vault & passive fleet buffs")
            print("  streak                         - Expedition jump streak & multiplier status")
            print("  market                         - Check commodity trade prices")
            print("  buy <comm> <qty|max>           - Buy commodities (max: all you can afford and hold)")
            print("  sell <comm> <qty|all>          - Sell commodities (all: the whole hold of it)")
            print("  fleet [harvest|buy|deploy]     - Autonomous fleet assets and drone yields")
            print("  upgrades [buy <id>]            - Station hardware upgrades and module shop")
            print("  combat <fire|drone|target|flee>- Tactical maneuvers during hostile intercepts")
            print("  power <e> <s> <se> <w>         - Distribute 100% reactor power")
            print("  anomaly <choice_id>            - Resolve active spatial encounter")
            print("  repair [amt]                   - Repair hull integrity at station")
            print("  refuel [amt]                   - Replenish quantum fuel at station")
            print("  serve [--port 8080|stop]       - Launch/stop concurrent Web Cockpit HUD")
            print("  quests                         - Unified story and contract quest panel")
            print("  ai [list|hail|buy|sell|hire|ally] - AI captain diplomacy and trade")
            print("  messages [list|send|read]      - Intergalactic quantum messaging")
            print("  depot [status|deposit|withdraw|sell] - System cargo depot operations")
            print("  land <body_id>                 - Land on a habitable body")
            print("  mercs [list|hire|dismiss|refit] - Mercenary contracts and fleet refits")
            print("  allies [list|form]             - Alliance roster and formation")
            print("  saves [list|save|load|delete] [slot] - Manage multiple save slots")
            print("  exit / quit                    - Close interactive link")
        else:
            print(f"{RED}Unknown command '{cmd}'. Type 'help' for command matrix.{RESET}")

    if server_handle is not None:
        server_handle.stop()
        server_handle = None
    return 0


def cmd_events(engine: SimulationEngine, storage: StorageManager, parts: Sequence[str]) -> int:
    """List or dismiss cockpit popup events."""
    action = parts[1].lower() if len(parts) > 1 else "list"
    if action == "dismiss":
        if len(parts) < 3 or not parts[2]:
            print(f"{RED}Usage:{RESET} events dismiss <event_id>")
            return 1
        ok, msg = engine.dismiss_event(parts[2])
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1

    undismissed = [e for e in engine.state.events if not e.dismissed]
    if not undismissed:
        print(f"{DIM}No active cockpit events.{RESET}")
        return 0
    print(f"\n{CYAN}{BOLD}=== ACTIVE COCKPIT EVENTS ({len(undismissed)}) ==={RESET}")
    for evt in undismissed:
        print(f"  [{evt.id}] ({evt.kind.upper()} @ Tick #{evt.tick}) {BOLD}{evt.title}{RESET}: {evt.message}")
    return 0


def _trade_quantity(value: str) -> int | str:
    """argparse type for trade orders: a positive count, or `max`/`all` for the largest possible order."""
    if value.lower() in ("max", "all"):
        return "max"
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a whole number, 'max' or 'all', got '{value}'") from None


def _run_trade(engine: SimulationEngine, commodity_id: str, quantity: int | str, is_buy: bool) -> tuple[bool, str]:
    if quantity == "max":
        return engine.trade_max(commodity_id, is_buy=is_buy)
    return engine.trade(commodity_id, int(quantity), is_buy=is_buy)


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="voidfarer",
        description="VoidFarer: Autonomous Deep-Space Fleet, Procedural Galaxy & Holographic Cockpit Simulator",
    )
    parser.add_argument("--save-path", help="Custom save file or directory path")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Print ship telemetry and navigation status")
    subparsers.add_parser("chart", help="Display star systems and orbital bodies")
    subparsers.add_parser("market", help="Display local commodity exchange quotes")
    subparsers.add_parser("economy", help="Display galactic economy shocks and trade routes")
    inv_p = subparsers.add_parser("inventory", help="Inspect cargo hold manifest, buy consumables, and use items")
    inv_p.add_argument("action", nargs="?", default="list", choices=["list", "buy", "use", "jettison"])
    inv_p.add_argument("arg1", nargs="?", help="Item ID")
    inv_p.add_argument("arg2", nargs="?", help="Quantity")
    shipyard_p = subparsers.add_parser("shipyard", help="Orbital shipyard chassis and module sales")
    shipyard_p.add_argument("action", nargs="?", default="list", choices=["list", "catalog", "status", "chassis", "buy_chassis", "sell", "uninstall"])
    shipyard_p.add_argument("target", nargs="?", help="Chassis ID or module slot")
    subparsers.add_parser("scan", help="Execute sensor scan on orbiting body")
    subparsers.add_parser("repl", help="Launch interactive terminal cockpit")

    fleet_p = subparsers.add_parser("fleet", help="Autonomous fleet and drone operations")
    fleet_p.add_argument("action", nargs="?", default="list", choices=["list", "harvest", "buy", "deploy", "ships", "buy_escort", "assign", "repair_escorts", "dismiss_escort"])
    fleet_p.add_argument("arg1", nargs="?", help="Drone type or drone ID")
    fleet_p.add_argument("arg2", nargs="?", help="Target star system ID")

    subparsers.add_parser("quests", help="Unified quest panel (story + contracts)")

    ai_p = subparsers.add_parser("ai", help="AI captain diplomacy, trade, hire, and alliances")
    ai_p.add_argument("action", nargs="?", default="list", choices=["list", "hail", "buy", "sell", "hire", "ally"])
    ai_p.add_argument("captain_id", nargs="?", help="AI captain ID")
    ai_p.add_argument("commodity_id", nargs="?", help="Commodity for buy/sell")
    ai_p.add_argument("quantity", nargs="?", type=int, default=1)

    msg_p = subparsers.add_parser("messages", help="Intergalactic quantum messaging")
    msg_p.add_argument("action", nargs="?", default="list", choices=["list", "send", "read", "tree", "trees", "choose"])
    msg_p.add_argument("args", nargs="*", help="Message arguments")

    depot_p = subparsers.add_parser("depot", help="System cargo depot operations")
    depot_p.add_argument("action", nargs="?", default="status", choices=["status", "deposit", "withdraw", "sell"])
    depot_p.add_argument("item_id", nargs="?", help="Item ID")
    depot_p.add_argument("quantity", nargs="?", type=int, default=1)

    land_p = subparsers.add_parser("land", help="Land on a habitable body")
    land_p.add_argument("body_id", help="Celestial body ID")

    merc_p = subparsers.add_parser("mercs", help="Mercenary contracts and fleet refits")
    merc_p.add_argument("action", nargs="?", default="list", choices=["list", "hire", "dismiss", "refit"])
    merc_p.add_argument("target_id", nargs="?", help="Mercenary catalog ID or fleet drone ID")

    allies_p = subparsers.add_parser("allies", help="Alliance roster and formation")
    allies_p.add_argument("action", nargs="?", default="list", choices=["list", "form"])
    allies_p.add_argument("captain_id", nargs="?", help="AI captain ID")

    upg_p = subparsers.add_parser("upgrades", help="Station hardware modules arsenal")
    upg_p.add_argument("action", nargs="?", default="list", choices=["list", "buy"])
    upg_p.add_argument("upgrade_id", nargs="?", help="Upgrade ID to purchase")

    combat_p = subparsers.add_parser("combat", help="Execute tactical combat maneuver")
    combat_p.add_argument(
        "action",
        choices=["fire", "laser", "attack", "drone", "strike", "target", "subsystem", "absorb", "shield", "defend", "evade", "dodge", "flee", "escape"],
        help="Tactical maneuver",
    )
    combat_p.add_argument("target", nargs="?", help="Subsystem target for 'combat target' (weapons or shields)")

    contracts_p = subparsers.add_parser("contracts", help="Inspect and claim dynamic sector bounty contracts")
    contracts_p.add_argument("action", nargs="?", default="list", choices=["list", "claim", "refresh"])
    contracts_p.add_argument("contract_id", nargs="?", help="Contract ID to claim")

    mastery_p = subparsers.add_parser("mastery", help="Pilot rank progression and talent specializations")
    mastery_p.add_argument("action", nargs="?", default="status", choices=["status", "list", "unlock"])
    mastery_p.add_argument("talent_id", nargs="?", help="Talent ID to unlock")

    subparsers.add_parser("relics", help="Display ancient Precursor Relics and passive modifiers")
    subparsers.add_parser("streak", help="Display expedition jump streak and multiplier")

    tut_p = subparsers.add_parser("tutorial", help="Cadet Flight Academy onboarding and guidance")
    tut_p.add_argument("action", nargs="?", default="status", choices=["status", "skip", "reset"])

    story_p = subparsers.add_parser("story", help="The Precursor Cipher narrative campaign")
    story_p.add_argument("action", nargs="?", default="status", choices=["status", "choose"])
    story_p.add_argument("choice_id", nargs="?", help="Choice ID to select")

    void_p = subparsers.add_parser("void", help="The Hollow Between void lane traversal")
    void_p.add_argument("action", nargs="?", default="status", choices=["status", "lanes", "dive", "emerge"])
    void_p.add_argument("system_id", nargs="?", help="Destination system ID for dive")

    jump_p = subparsers.add_parser("jump", help="Jump to adjacent star system")
    jump_p.add_argument("system_id", help="Target star system ID")

    orbit_p = subparsers.add_parser("orbit", help="Enter orbit around celestial body")
    orbit_p.add_argument("body_id", help="Target body ID")

    travel_p = subparsers.add_parser("travel", help="Initiate sublight or quantum in-system transit")
    travel_p.add_argument("body_id", help="Destination celestial body ID")
    travel_p.add_argument("--mode", default="sublight", choices=["sublight", "quantum"], help="Transit mode")

    events_p = subparsers.add_parser("events", help="List or dismiss cockpit popup events")
    events_p.add_argument("action", nargs="?", default="list", choices=["list", "dismiss"])
    events_p.add_argument("event_id", nargs="?", help="Event ID to dismiss")

    saves_p = subparsers.add_parser("saves", help="List, save, load, or delete save slots")
    saves_p.add_argument("action", nargs="?", default="list", choices=["list", "save", "load", "delete"])
    saves_p.add_argument("slot", nargs="?", default="default", help="Save slot name (default: 'default')")

    pwr_p = subparsers.add_parser("power", help="Route reactor power (must sum to 100)")
    pwr_p.add_argument("engines", type=int, help="Engines power percentage")
    pwr_p.add_argument("shields", type=int, help="Shields power percentage")
    pwr_p.add_argument("sensors", type=int, help="Sensors power percentage")
    pwr_p.add_argument("weapons", type=int, help="Weapons power percentage")

    buy_p = subparsers.add_parser("buy", help="Buy commodities")
    buy_p.add_argument("commodity_id", help="Commodity identifier")
    buy_p.add_argument("quantity", type=_trade_quantity, help="Quantity to purchase, or max")

    sell_p = subparsers.add_parser("sell", help="Sell commodities")
    sell_p.add_argument("commodity_id", help="Commodity identifier")
    sell_p.add_argument("quantity", type=_trade_quantity, help="Quantity to sell, or all")

    anom_p = subparsers.add_parser("anomaly", help="Resolve active anomaly encounter")
    anom_p.add_argument("choice_id", help="Selected choice ID")

    rep_p = subparsers.add_parser("repair", help="Repair hull integrity")
    rep_p.add_argument("amount_pos", nargs="?", type=int, help="Hull points to restore (default 25)")
    rep_p.add_argument("--amount", type=int, default=None, help="Hull points to restore")

    ref_p = subparsers.add_parser("refuel", help="Replenish quantum fuel")
    ref_p.add_argument("amount_pos", nargs="?", type=int, help="Fuel units to add (default 20)")
    ref_p.add_argument("--amount", type=int, default=None, help="Fuel units to add")

    serve_p = subparsers.add_parser("serve", help="Launch Holographic Web Cockpit server")
    serve_p.add_argument("--port", type=int, default=8080, help="HTTP server port")
    serve_p.add_argument("--host", default="127.0.0.1", help="HTTP server host")
    serve_p.add_argument("--open", action="store_true", help="Automatically launch web browser")

    subparsers.add_parser("factions", help="Inspect galactic sovereign factions and reputation")
    war_p = subparsers.add_parser("war", help="Galactic wars, fronts and war pledges")
    war_p.add_argument("action", nargs="?", default="list", choices=["list", "support"])
    war_p.add_argument("args", nargs="*", help="support: <war_id> <faction_id> <credits>")
    subparsers.add_parser("corps", help="Inspect interstellar megacorporations and trade perks")
    subparsers.add_parser("corporations", help="Alias for 'corps'")

    crew_p = subparsers.add_parser("crew", help="Crew roster, recruiting, drills, shore leave, and portraits")
    crew_p.add_argument("action", nargs="?", default="list", choices=["list", "recruit", "train", "shore", "dismiss"])
    crew_p.add_argument("value", nargs="?", help="Role or crew id")

    away_p = subparsers.add_parser("away", help="Deploy, inspect, or recall away-team expeditions")
    away_p.add_argument("action", nargs="?", default="list", choices=["list", "launch", "recall"])
    away_p.add_argument("values", nargs="*", help="Mission type, crew ids, or mission id")

    pirate_p = subparsers.add_parser("pirate", help="Inspect or resolve a pirate toll encounter")
    pirate_p.add_argument("action", nargs="?", default="status", choices=["status", "pay", "fight", "evade"])

    decision_p = subparsers.add_parser("decision", help="Inspect or resolve the pending real-time decision")
    decision_p.add_argument("action", nargs="?", default="status", choices=["status", "choose"])
    decision_p.add_argument("choice_id", nargs="?", help="Choice id to resolve")

    quantum_p = subparsers.add_parser("quantum", help="Quantum freight routes, orders, and shipping")
    quantum_p.add_argument("action", nargs="?", default="routes", choices=["routes", "orders", "ship"])
    quantum_p.add_argument("values", nargs="*", help="commodity, quantity, destination_system_id")

    surface_p = subparsers.add_parser("surface", help="Inspect or run landing-party surface operations")
    surface_p.add_argument("action", nargs="?", default="list", choices=["list", "op"])
    surface_p.add_argument("operation_id", nargs="?", help="Surface operation id")

    settings_p = subparsers.add_parser("settings", help="Simulation options such as decision cadence")
    settings_p.add_argument("action", nargs="?", default="show", choices=["show", "decisions"])
    settings_p.add_argument("value", nargs="?", help="relaxed, normal or frequent")

    subparsers.add_parser("salvage", help="Board the derelict at the current body")
    subparsers.add_parser("scoop", help="Scoop fuel from a star, gas giant, or ice body")

    weapons_p = subparsers.add_parser("weapons", help="Weapon types, installation, and primary selection")
    weapons_p.add_argument("action", nargs="?", default="list", choices=["list", "install", "set"])
    weapons_p.add_argument("weapon_id", nargs="?", help="Weapon id")

    character_p = subparsers.add_parser("character", help="Commander profile, skills, age, and abilities")
    character_p.add_argument("action", nargs="?", default="status", choices=["status", "train", "use"])
    character_p.add_argument("value", nargs="?", help="Skill or ability id")
    character_p.add_argument("target", nargs="?", help="Optional faction target")

    research_p = subparsers.add_parser("research", help="Research projects and technology bonuses")
    research_p.add_argument("action", nargs="?", default="status", choices=["status", "start"])
    research_p.add_argument("project_id", nargs="?", help="Research project id")

    outpost_p = subparsers.add_parser("outpost", help="Found and upgrade planetary outposts")
    outpost_p.add_argument("action", nargs="?", default="list", choices=["list", "build", "upgrade"])
    outpost_p.add_argument("outpost_type", nargs="?", help="Outpost type or outpost id")
    outpost_p.add_argument("body_id", nargs="?", help="Body id for construction")

    diplomacy_p = subparsers.add_parser("diplomacy", help="Faction diplomacy, leaders, and wars")
    diplomacy_p.add_argument("action", nargs="?", default="list", choices=["list", "improve", "gift", "alliance", "ceasefire"])
    diplomacy_p.add_argument("faction_id", nargs="?", help="Faction id")
    diplomacy_p.add_argument("amount", nargs="?", type=int, default=0, help="Aid amount")

    route_p = subparsers.add_parser("route", help="Plot a multi-jump hyperlane route")
    route_p.add_argument("system_id", help="Target star system id")

    nav_p = subparsers.add_parser("navigate", help="Automatically jump along the shortest route")
    nav_p.add_argument("system_id", help="Target star system id")

    reactor_p = subparsers.add_parser("reactor", help="Inspect reactor heat, integrity, and operating modes")
    reactor_p.add_argument("action", nargs="?", default="status", choices=["status", "mode", "vent", "repair"])
    reactor_p.add_argument("value", nargs="?", help="Reactor mode or action value")

    map_p = subparsers.add_parser("mapmods", help="Display active sector map modifiers and effects")
    map_p.add_argument("action", nargs="?", default="list", choices=["list", "mods"])

    refit_p = subparsers.add_parser("refit", help="Ship modification section: structural refits")
    refit_p.add_argument("action", nargs="?", default="list", choices=["list", "install", "remove", "info"])
    refit_p.add_argument("target", nargs="?", help="Modification ID or slot")

    subparsers.add_parser("simulation", help="Print unified simulation telemetry report")
    subparsers.add_parser("log", help="Captain's log: career statistics, milestones, and flight record")
    codex_p = subparsers.add_parser("codex", help="Discovery codex progress and achievement rewards")
    codex_p.add_argument("action", nargs="?", default="list", help="list, show <id>, claim <id>, or a category id")
    codex_p.add_argument("entry_id", nargs="?", help="Codex entry id for show/claim")

    time_p = subparsers.add_parser("time", help="Inspect and control simulation time and ticks")
    time_p.add_argument("action", nargs="?", default="status", choices=["status", "pause", "resume", "play", "speed", "step", "wait", "tick"])
    time_p.add_argument("value", nargs="?", help="Speed multiplier or tick count")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    custom_dir = Path(args.save_path) if getattr(args, "save_path", None) else None
    engine, storage = _get_engine(custom_dir)

    pending = engine.state.pending_decision
    if pending is not None and args.command not in ("decision", "status", "save", "serve", "time", "quit"):
        print(f"{RED}Decision required:{RESET} {pending.title}. Run `decision` and choose an option first.")
        return 1

    pirate = engine.state.active_pirate
    if pirate is not None and args.command not in ("pirate", "decision", "status", "save", "serve", "time", "quit"):
        print(
            f"{RED}Pirate intercept unresolved:{RESET} {pirate.band_name} demands {pirate.toll_credits} cr. "
            "Run `pirate pay`, `pirate fight`, or `pirate evade` first."
        )
        return 1

    if args.command == "status":
        return cmd_status(engine)
    elif args.command == "crew":
        parts = ["crew", args.action]
        if args.value:
            parts.append(args.value)
        return cmd_crew(engine, storage, parts)
    elif args.command == "away":
        return cmd_away(engine, storage, ["away", args.action] + list(args.values))
    elif args.command == "pirate":
        return cmd_pirate(engine, storage, ["pirate", args.action])
    elif args.command == "decision":
        return cmd_decision(engine, storage, ["decision", args.action] + ([args.choice_id] if args.choice_id else []))
    elif args.command == "quantum":
        return cmd_quantum(engine, storage, ["quantum", args.action] + list(args.values))
    elif args.command == "surface":
        return cmd_surface(engine, storage, ["surface", args.action] + ([args.operation_id] if args.operation_id else []))
    elif args.command == "weapons":
        parts = ["weapons", args.action]
        if args.weapon_id:
            parts.append(args.weapon_id)
        return cmd_weapons(engine, storage, parts)
    elif args.command == "character":
        parts = ["character", args.action]
        if args.value:
            parts.append(args.value)
        if args.target:
            parts.append(args.target)
        return cmd_character(engine, storage, parts)
    elif args.command == "research":
        parts = ["research", args.action]
        if args.project_id:
            parts.append(args.project_id)
        return cmd_research(engine, storage, parts)
    elif args.command == "outpost":
        parts = ["outpost", args.action]
        if args.outpost_type:
            parts.append(args.outpost_type)
        if args.body_id:
            parts.append(args.body_id)
        return cmd_outpost(engine, storage, parts)
    elif args.command == "diplomacy":
        parts = ["diplomacy", args.action]
        if args.faction_id:
            parts.append(args.faction_id)
        parts.append(str(args.amount))
        return cmd_diplomacy(engine, storage, parts)
    elif args.command == "route":
        return cmd_route(engine, args.system_id)
    elif args.command == "navigate":
        ok, msg = engine.navigate_to(args.system_id)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "reactor":
        parts = ["reactor", args.action]
        if args.value:
            parts.append(args.value)
        return cmd_reactor(engine, storage, parts)
    elif args.command == "mapmods":
        return cmd_mapmods(engine)
    elif args.command == "refit":
        parts = ["refit", args.action]
        if args.target:
            parts.append(args.target)
        return cmd_refit(engine, storage, parts)
    elif args.command == "log":
        return cmd_log(engine)
    elif args.command == "codex":
        parts = ["codex", args.action]
        if args.entry_id:
            parts.append(args.entry_id)
        return cmd_codex(engine, storage, parts)
    elif args.command == "simulation":
        report = engine.get_simulation_report()
        print(f"\n{BOLD}{CYAN}=== SIMULATION REPORT ==={RESET}")
        print(f"Tick {report['tick']} | {report['date']} | {report['system']}")
        print(f"Map: {', '.join(m['name'] for m in report['map_modifiers']) or 'Standard space'}")
        print(f"Reactor: {report['reactor']['mode']} | heat {report['reactor']['heat']}/{report['reactor']['max_heat']} | "
              f"eff {report['reactor']['efficiency']*100:.0f}% | integrity {report['reactor']['integrity']}")
        print(f"Power efficiency: {report['power_efficiency']*100:.0f}%")
        return 0
    elif args.command == "time":
        parts = [args.action]
        if args.value:
            parts.append(args.value)
        return cmd_time(engine, storage, parts)
    elif args.command == "factions":
        return cmd_factions(engine, storage, ["factions"])
    elif args.command == "war":
        return cmd_war(engine, storage, args.action, args.args)
    elif args.command == "settings":
        return cmd_settings(engine, storage, args.action, [args.value] if args.value else [])
    elif args.command == "corps":
        return cmd_corporations(engine, storage, ["corps"])
    elif args.command == "corporations":
        return cmd_corporations(engine, storage, ["corporations"])
    elif args.command == "chart":
        return cmd_chart(engine)
    elif args.command == "market":
        return cmd_market(engine)
    elif args.command == "economy":
        return cmd_economy(engine)
    elif args.command == "inventory":
        parts = ["inventory"]
        if args.action != "list":
            parts.append(args.action)
            if args.arg1:
                parts.append(args.arg1)
            if args.arg2:
                parts.append(args.arg2)
        return cmd_inventory(engine, storage, parts)
    elif args.command == "shipyard":
        parts = ["shipyard"]
        if args.action != "list":
            parts.append(args.action)
            if args.target:
                parts.append(args.target)
        return cmd_shipyard(engine, storage, parts)
    elif args.command == "fleet":
        parts = ["fleet"]
        if args.action != "list":
            parts.append(args.action)
            if args.arg1:
                parts.append(args.arg1)
            if args.arg2:
                parts.append(args.arg2)
        return cmd_fleet(engine, storage, parts)
    elif args.command == "quests":
        return cmd_quests(engine)
    elif args.command == "ai":
        parts = ["ai", args.action]
        if args.captain_id:
            parts.append(args.captain_id)
        if args.commodity_id:
            parts.append(args.commodity_id)
        if args.quantity is not None:
            parts.append(str(args.quantity))
        return cmd_ai(engine, storage, parts)
    elif args.command == "messages":
        return cmd_messages(engine, storage, ["messages", args.action] + list(args.args))
    elif args.command == "depot":
        parts = ["depot", args.action]
        if args.item_id:
            parts.append(args.item_id)
        if args.quantity is not None:
            parts.append(str(args.quantity))
        return cmd_depot(engine, storage, parts)
    elif args.command == "land":
        return cmd_land(engine, storage, args.body_id)
    elif args.command == "mercs":
        parts = ["mercs", args.action]
        if args.target_id:
            parts.append(args.target_id)
        return cmd_mercs(engine, storage, parts)
    elif args.command == "allies":
        parts = ["allies", args.action]
        if args.captain_id:
            parts.append(args.captain_id)
        return cmd_allies(engine, storage, parts)
    elif args.command == "upgrades":
        parts = ["upgrades"]
        if args.action != "list":
            parts.append(args.action)
            if args.upgrade_id:
                parts.append(args.upgrade_id)
        return cmd_upgrades(engine, storage, parts)
    elif args.command == "combat":
        parts = ["combat", args.action]
        if args.target:
            parts.append(args.target)
        return cmd_combat(engine, storage, parts)
    elif args.command == "contracts":
        parts = ["contracts"]
        if args.action != "list":
            parts.append(args.action)
            if args.contract_id:
                parts.append(args.contract_id)
        return cmd_contracts(engine, storage, parts)
    elif args.command == "mastery":
        parts = ["mastery"]
        if args.action not in ("status", "list"):
            parts.append(args.action)
            if args.talent_id:
                parts.append(args.talent_id)
        return cmd_mastery(engine, storage, parts)
    elif args.command == "relics":
        return cmd_relics(engine)
    elif args.command == "streak":
        return cmd_streak(engine)
    elif args.command == "tutorial":
        parts = ["tutorial"]
        if args.action != "status":
            parts.append(args.action)
        return cmd_tutorial(engine, storage, parts)
    elif args.command == "story":
        parts = ["story"]
        if args.action != "status":
            parts.append(args.action)
            if args.choice_id:
                parts.append(args.choice_id)
        return cmd_story(engine, storage, parts)
    elif args.command == "void":
        parts = ["void"]
        if args.action != "status":
            parts.append(args.action)
            if args.system_id:
                parts.append(args.system_id)
        return cmd_void(engine, storage, parts)
    elif args.command == "scan":
        ok, msg, _ = engine.scan()
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "salvage":
        ok, msg, report = engine.salvage_derelict()
        print((GREEN if ok else RED) + msg + RESET)
        if ok and report.get("site"):
            site = report["site"]
            print(f"{DIM}Site: {site['name']} | Risk: {report['danger']*100:.0f}% | Success: {report['success']}{RESET}")
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "scoop":
        ok, msg = engine.scoop_fuel()
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "jump":
        ok, msg = engine.jump(args.system_id)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "orbit":
        ok, msg = engine.orbit(args.body_id)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "travel":
        ok, msg = engine.start_travel(args.body_id, mode=args.mode)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "events":
        parts = ["events", args.action]
        if args.event_id:
            parts.append(args.event_id)
        return cmd_events(engine, storage, parts)
    elif args.command == "saves":
        return cmd_saves(engine, storage, ["saves", args.action, args.slot])
    elif args.command == "power":
        ok, msg = engine.route_power(args.engines, args.shields, args.sensors, args.weapons)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "buy":
        ok, msg = _run_trade(engine, args.commodity_id, args.quantity, is_buy=True)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "sell":
        ok, msg = _run_trade(engine, args.commodity_id, args.quantity, is_buy=False)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "anomaly":
        ok, msg = engine.resolve_anomaly(args.choice_id)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "repair":
        amount = args.amount if args.amount is not None else (args.amount_pos if args.amount_pos is not None else 25)
        ok, msg = engine.repair_hull(amount)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "refuel":
        amount = args.amount if args.amount is not None else (args.amount_pos if args.amount_pos is not None else 20)
        ok, msg = engine.refuel(amount)
        print((GREEN if ok else RED) + msg + RESET)
        storage.save(engine.state)
        return 0 if ok else 1
    elif args.command == "repl":
        return cmd_repl(engine, storage)
    elif args.command == "serve":
        return run_server(engine, storage, port=args.port, host=args.host, open_browser=args.open)

    return 0


if __name__ == "__main__":
    sys.exit(main())

