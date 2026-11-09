"""One report and action surface for chart, economy, factions, wars and corps.

These are read-only intelligence views in the cockpit, but the CLI exposes seven
verbs. This module assembles them once and routes the two actions (scan and war
support) to the existing engine methods.
"""

from __future__ import annotations

from typing import Any

from voidfarer.economy import get_galactic_trade_routes
from voidfarer.factions import (
    CANONICAL_CORPORATIONS,
    CANONICAL_FACTIONS,
    get_faction_standing_tier,
)
from voidfarer.models import GameState

INTEL_ACTIONS = ("scan", "war_support")


def intel_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    current = state.systems.get(state.ship.current_system_id)
    bodies = current.bodies if current else ()
    return {
        "current_system": current.name if current else state.ship.current_system_id,
        "systems": len(state.systems),
        "visited": len(state.visited_systems),
        "scanned_bodies": sum(1 for body in bodies if body.scan_completed),
        "bodies": len(bodies),
        "active_wars": sum(1 for war in state.wars if war.active),
        "factions": len(CANONICAL_FACTIONS),
        "corporations": len(CANONICAL_CORPORATIONS),
    }


def _system_rows(engine: Any) -> list[dict[str, Any]]:
    state = engine.state
    current_id = engine.current_system.id
    return [
        {
            "id": system.id,
            "name": system.name,
            "security": round(float(system.security), 2),
            "connections": list(system.connections),
            "modifiers": [modifier.name for modifier in system.modifiers],
            "current": system.id == current_id,
            "visited": system.id in state.visited_systems,
        }
        for system in state.systems.values()
    ]


def _body_rows(engine: Any) -> list[dict[str, Any]]:
    system = engine.current_system
    orbiting = engine.state.ship.orbiting_body_id
    return [
        {
            "id": body.id,
            "name": body.name,
            "body_type": body.body_type,
            "orbit_radius": round(float(body.orbit_radius), 2),
            "dockable": bool(body.station_dockable),
            "scanned": bool(body.scan_completed),
            "orbiting": body.id == orbiting,
        }
        for body in system.bodies
    ]


def _faction_rows(state: GameState) -> list[dict[str, Any]]:
    rows = []
    for faction_id, faction in CANONICAL_FACTIONS.items():
        standing = int(state.ship.faction_standings.get(faction_id, 0))
        tier, perk = get_faction_standing_tier(standing)
        rows.append({
            "id": faction_id,
            "name": faction.name,
            "ideology": faction.ideology,
            "headquarters_system": faction.headquarters_system,
            "standing": standing,
            "tier": tier,
            "perk": perk,
            "eliminated": faction_id in state.eliminated_factions,
        })
    return rows


def _corporation_rows(state: GameState) -> list[dict[str, Any]]:
    return [
        {
            "id": corp_id,
            "name": corp.name,
            "headquarters_system": corp.headquarters_system,
            "specialty_commodity": corp.specialty_commodity,
            "bonus_trade_margin": round(float(corp.bonus_trade_margin), 3),
            "perk": corp.corporate_perk,
            "standing": int(state.ship.corp_standings.get(corp_id, 0)),
        }
        for corp_id, corp in CANONICAL_CORPORATIONS.items()
    ]


def intel_report(engine: Any) -> dict[str, Any]:
    """Return chart, economy, factions, wars and corporations in one payload."""
    state = engine.state
    economy = state.economy
    routes = get_galactic_trade_routes(state.systems, economy)
    politics = engine.galactic_politics()
    events = [
        {
            "title": event.title,
            "system_id": event.system_id,
            "commodity_id": event.commodity_id,
            "price_multiplier": float(event.price_multiplier),
            "duration_ticks": int(event.duration_ticks),
            "description": event.description,
        }
        for event in economy.active_events
    ]
    factions = _faction_rows(state)
    corporations = _corporation_rows(state)
    wars = politics.get("wars", [])
    return {
        "chart": {
            "current_system": engine.current_system.id,
            "systems": _system_rows(engine),
            "bodies": _body_rows(engine),
        },
        "economy": {
            "tick": int(state.time.tick),
            "events": events,
            "trade_routes": routes[:6],
        },
        "factions": factions,
        "wars": wars,
        "corporations": corporations,
        "counts": {
            "systems": len(state.systems),
            "visited": len(state.visited_systems),
            "scanned_bodies": sum(
                1 for body in engine.current_system.bodies if body.scan_completed
            ),
            "factions": len(factions),
            "active_wars": sum(1 for war in wars if war.get("active")),
            "corporations": len(corporations),
            "trade_routes": len(routes),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def intel_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one intel action to its existing engine method."""
    action = str(action).strip().lower()
    if action == "scan":
        ok, message, _report = engine.scan()
        return ok, message
    if action == "war_support":
        return engine.support_war(
            _text(kwargs.get("war_id")),
            _text(kwargs.get("faction_id")),
            _int(kwargs.get("credits")),
        )
    return False, (
        f"Unknown intel action '{action}'. "
        f"Use one of: {', '.join(INTEL_ACTIONS)}."
    )
