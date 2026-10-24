"""
Drive the real VoidFarer cockpit in Edge through Playwright.

This is the visual-review driver: it starts the real server in-process, opens the real page in
a Playwright browser at an exact viewport, drives the requested game state, and writes a true
browser screenshot plus console/layout evidence. It is a developer tool and an optional
dev-only dependency (`pip install playwright`); the game runtime stays zero-dependency.

Usage: python tools/ui_browser.py --viewports desktop --scenario cockpit --out DIR
       python tools/ui_browser.py --scenario target --tab market --headed
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / "voidfarer" / "static"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from voidfarer.engine import SimulationEngine  # noqa: E402
from voidfarer.server import VoidFarerHandler, start_background_server  # noqa: E402
from voidfarer.storage import StorageManager  # noqa: E402
from tools.ui_audit import TABS, VIEWPORTS  # noqa: E402

SCENARIOS = ("cockpit", "menu", "settings", "character", "target", "event", "combat", "galaxy", "death")
TAB_IDS = {
    "player": "tabBtnPlayer",
    "skills": "tabBtnSkills",
    "crew": "tabBtnCrew",
    "ship": "tabBtnShip",
    "market": "tabBtnMarket",
    "arsenal": "tabBtnArsenal",
    "fleet": "tabBtnFleet",
    "contracts": "tabBtnContracts",
    "empire": "tabBtnEmpire",
    "quests": "tabBtnQuests",
    "ai": "tabBtnAI",
    "depot": "tabBtnDepot",
    "messages": "tabBtnMessages",
    "story": "tabBtnStory",
    "factions": "tabBtnFactions",
    "codex": "tabBtnCodex",
}


def _open_cockpit(page: Any, scenario: str, tab: str, timeout: int) -> None:
    """Wait for the cockpit and move it into the requested review state."""
    page.wait_for_function("() => Boolean(window.cockpit)", timeout=timeout)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=timeout)
    page.wait_for_timeout(700)
    if scenario != "menu":
        page.evaluate(
            """() => {
                const cockpit = window.cockpit;
                cockpit.gameStarted = true;
                cockpit.closeMainMenu();
                if (cockpit.fetchGalaxy) cockpit.fetchGalaxy();
                if (cockpit.refreshState) cockpit.refreshState(true);
            }"""
        )
        page.wait_for_timeout(1200)
    if scenario == "settings":
        page.evaluate("() => window.cockpit.openSettings()")
        page.wait_for_timeout(500)
    elif scenario == "character":
        page.evaluate("() => window.cockpit.openCharacterCreation()")
        page.wait_for_timeout(500)
    elif scenario == "target":
        page.evaluate(
            """async () => {
                const cockpit = window.cockpit;
                const bodies = (cockpit.state.current_system && cockpit.state.current_system.bodies) || [];
                const orbitingId = cockpit.state.ship && cockpit.state.ship.orbiting_body_id;
                const body = bodies.find(item => item.id !== orbitingId && item.body_type !== "star") || bodies[0];
                if (body) {
                    cockpit.selectedTarget = body;
                    cockpit.selectedType = "body";
                    cockpit.updateTargetCard();
                    if (cockpit.refreshTransitPreview) {
                        await cockpit.refreshTransitPreview(body.id);
                    }
                }
            }"""
        )
        page.wait_for_timeout(700)
    elif scenario == "event":
        page.evaluate(
            """() => {
                const cockpit = window.cockpit;
                cockpit.state.undismissed_events = [
                    { id: "audit-signal", kind: "exploration", tick: 0,
                      title: "Anomalous Signal Detected",
                      message: "A harmonic pulse repeats beneath the quantum noise in the outer system." },
                    { id: "audit-contract", kind: "trade", tick: 0,
                      title: "Commodity Contract Fulfilled",
                      message: "Sol Logistics confirms the titanium delivery. Payment is ready at the exchange." }
                ];
                cockpit.renderEventPopups();
                cockpit.gameStarted = false;
            }"""
        )
        page.wait_for_timeout(500)
    elif scenario == "galaxy":
        page.evaluate(
            """() => {
                const button = document.getElementById("viewGalaxyBtn");
                if (button) {
                    button.click();
                } else {
                    window.cockpit.viewMode = "GALAXY";
                    window.cockpit.drawRadar();
                }
            }"""
        )
        page.wait_for_timeout(900)
    elif scenario == "death":
        page.evaluate(
            """() => {
                const cockpit = window.cockpit;
                cockpit.showDeathOverlay();
                cockpit.gameStarted = false;
            }"""
        )
        page.wait_for_timeout(700)
    elif scenario == "combat":
        page.evaluate(
            """() => {
                const card = document.getElementById("combatCard");
                if (card) card.style.display = "flex";
                const title = document.getElementById("combatEnemyTitle");
                if (title) title.textContent = "Corsair Marauder";
                const faction = document.getElementById("combatEnemyFaction");
                if (faction) faction.textContent = "FACTION: OUTLAW";
                const hp = document.getElementById("combatEnemyHp");
                if (hp) hp.textContent = "72 / 80";
                const bar = document.getElementById("combatEnemyBar");
                if (bar) bar.style.width = "90%";
                const shield = document.getElementById("combatShieldContainer");
                if (shield) shield.style.display = "flex";
                const shieldValue = document.getElementById("combatEnemyShield");
                if (shieldValue) shieldValue.textContent = "18 / 30";
                const shieldBar = document.getElementById("combatEnemyShieldBar");
                if (shieldBar) shieldBar.style.width = "60%";
                window.cockpit.gameStarted = false;
            }"""
        )
        page.wait_for_timeout(500)
    if tab and scenario == "cockpit":
        page.evaluate("(name) => window.cockpit.switchRightTab(name)", tab)
        page.wait_for_timeout(900)


def _metrics(page: Any) -> Dict[str, Any]:
    """Return viewport, scroll, element and tiny-text counts from the live page."""
    return page.evaluate(
        """() => {
            const root = document.documentElement;
            const elements = Array.from(document.querySelectorAll("body *"));
            const tinyElements = elements.filter(element => {
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                const text = Array.from(element.childNodes).some(node =>
                    node.nodeType === 3 && node.textContent.trim());
                return rect.width > 0 && rect.height > 0 && text && parseFloat(style.fontSize) < 12;
            }).map(element => ({
                el: element.tagName.toLowerCase() + (element.id ? "#" + element.id : ""),
                fontSize: parseFloat(getComputedStyle(element).fontSize),
                text: (element.innerText || element.textContent || "").trim().slice(0, 80)
            }));
            const eventNode = document.getElementById("eventPopupContainer");
            const combatNode = document.getElementById("combatCard");
            return {
                viewport: [innerWidth, innerHeight],
                scroll: [root.scrollWidth, root.scrollHeight],
                horizontal: root.scrollWidth > innerWidth + 1,
                elements: elements.length,
                tinyText: tinyElements.length,
                tinyDetails: tinyElements.slice(0, 40),
                eventPopup: eventNode ? {
                    display: getComputedStyle(eventNode).display,
                    text: (eventNode.innerText || "").slice(0, 200)
                } : null,
                combatCard: combatNode ? {
                    display: getComputedStyle(combatNode).display,
                    text: (combatNode.innerText || "").slice(0, 200)
                } : null
            };
        }"""
    )


def _run_viewport(browser: Any, url: str, name: str, viewport: tuple[int, int],
                  scenario: str, tab: str, out: Path, timeout: int,
                  scroll: str = "top") -> Dict[str, Any]:
    """Open one real browser viewport, drive it and capture a true screenshot."""
    context = browser.new_context(
        viewport={"width": viewport[0], "height": viewport[1]},
        device_scale_factor=1,
        color_scheme="dark",
    )
    page = context.new_page()
    errors: List[str] = []

    def on_console(message: Any) -> None:
        if message.type == "error":
            errors.append(f"console: {message.text}")

    page.on("console", on_console)
    page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
    page.on("response", lambda response: errors.append(f"http {response.status}: {response.url}")
            if response.status >= 400 else None)
    page.on("requestfailed", lambda request: errors.append(
        f"requestfailed: {request.url} // {request.failure}"))
    label = f"{name}-{tab}" if tab else name
    if scroll == "bottom":
        label += "-bottom"
    target = out / f"{label}.png"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        _open_cockpit(page, scenario, tab, timeout)
        if scroll == "bottom":
            page.evaluate("() => { const el = document.querySelector('.terminal-content-stack'); if (el) el.scrollTop = el.scrollHeight; }")
            page.wait_for_timeout(300)
        page.screenshot(path=str(target), full_page=False, animations="disabled")
        metrics = _metrics(page)
    finally:
        context.close()
    return {
        "name": label,
        "scenario": scenario,
        "tab": tab or None,
        "scroll": scroll,
        "viewport": list(viewport),
        "screenshot": target.name,
        "errors": errors,
        **metrics,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the browser review driver and write screenshots plus a small JSON report."""
    parser = argparse.ArgumentParser(description="Playwright browser review for VoidFarer")
    parser.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "voidfarer_browser"))
    parser.add_argument("--viewports", default="desktop,laptop,short")
    parser.add_argument("--scenario", default="cockpit", choices=SCENARIOS)
    parser.add_argument("--tab", default="", choices=("",) + TABS)
    parser.add_argument("--timeout", type=int, default=30000, help="milliseconds per page step")
    parser.add_argument("--scroll", default="top", choices=("top", "bottom"),
                        help="scroll the terminal content to the top or bottom")
    parser.add_argument("--headed", action="store_true", help="show the browser window")
    parser.add_argument("--channel", default="msedge", help="Playwright browser channel")
    args = parser.parse_args(argv)

    names = [name.strip() for name in args.viewports.split(",") if name.strip()]
    unknown = [name for name in names if name not in VIEWPORTS]
    if unknown:
        print(f"Why: unknown viewport(s): {', '.join(unknown)}.")
        print(f"Fix: choose from {', '.join(VIEWPORTS)}.")
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Why: Playwright is not installed; the real-browser review needs it.")
        print("Fix: run `python -m pip install playwright` once for development.")
        return 2

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="voidfarer_browser_"))
    handle = None
    reports: List[Dict[str, Any]] = []
    try:
        storage = StorageManager(workdir / "save")
        engine = SimulationEngine(state=storage.load())
        handle = start_background_server(engine, storage, port=0)
        if handle is None:
            print("Why: the cockpit server could not bind a local port.")
            print("Fix: stop the process holding the port or retry.")
            return 1
        VoidFarerHandler.static_dir = STATIC_DIR
        url = f"http://127.0.0.1:{handle.port}/"
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(channel=args.channel, headless=not args.headed)
            except Exception as exc:
                print(f"Why: the real browser could not launch ({exc}).")
                print("Fix: install Microsoft Edge or pass another Playwright channel.")
                return 2
            try:
                for name in names:
                    report = _run_viewport(browser, url, name, VIEWPORTS[name], args.scenario,
                                           args.tab, out, args.timeout, args.scroll)
                    reports.append(report)
                    print(f"{report['name']}: errors {len(report['errors'])} "
                          f"hscroll {int(report['horizontal'])} tiny {report['tinyText']} -> "
                          f"{out / report['screenshot']}")
            finally:
                browser.close()
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "driver": "playwright",
            "channel": args.channel,
            "viewports": reports,
        }
        (out / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        lines = ["# VoidFarer real-browser review", ""]
        lines.append("| State | Viewport | Errors | H-scroll | Tiny<12 | Screenshot |")
        lines.append("|---|---|---|---|---|---|")
        for report in reports:
            width, height = report["viewport"]
            lines.append(f"| {report['name']} | {width}x{height} | {len(report['errors'])} "
                         f"| {int(report['horizontal'])} | {report['tinyText']} "
                         f"| {report['screenshot']} |")
        (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Report: {out / 'report.md'}")
        return 0
    finally:
        if handle is not None:
            handle.stop()
        VoidFarerHandler.static_dir = STATIC_DIR
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
