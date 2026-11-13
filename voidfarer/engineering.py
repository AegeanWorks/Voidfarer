"""One report and action surface for power, reactor, repair, salvage and fabrication.

The cockpit SHIP tab shows reactor heat, power routing, hull, fuel and salvage in
one place, but the CLI exposes eight verbs. This module normalizes the telemetry
and routes each action to the existing engine method.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState

ENGINEERING_ACTIONS = (
    "power", "reactor_mode", "reactor_vent", "reactor_repair",
    "repair", "refuel", "overhaul", "fabricate", "salvage", "scoop", "burn_cells",
)

FABRICATION_BLUEPRINTS = ("patch_kit", "fuel_cell")


def engineering_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    ship = state.ship
    reactor = ship.reactor
    return {
        "hull": ship.hull,
        "max_hull": ship.max_hull,
        "fuel": ship.fuel,
        "max_fuel": ship.max_fuel,
        "power": ship.power.to_dict(),
        "reactor_heat": round(float(reactor.heat), 1),
        "reactor_mode": reactor.mode,
        "credits": ship.credits,
    }


def engineering_report(engine: Any) -> dict[str, Any]:
    """Return reactor, power, hull/fuel, salvage, scoop and fabrication in one payload."""
    snapshot = engine.get_status_snapshot(include_static=False)
    ship = snapshot["ship"]
    reactor = engine.get_reactor_report()
    hull = int(ship["hull"])
    max_hull = int(ship["max_hull"])
    fuel = int(ship["fuel"])
    max_fuel = int(ship["max_fuel"])
    cargo = ship.get("cargo", {})
    return {
        "reactor": reactor,
        "power": ship["power"],
        "hull": {
            "current": hull,
            "max": max_hull,
            "percent": round(100.0 * hull / max(1, max_hull), 1),
        },
        "fuel": {
            "current": fuel,
            "max": max_fuel,
            "percent": round(100.0 * fuel / max(1, max_fuel), 1),
        },
        "credits": int(ship["credits"]),
        "salvage": snapshot.get("salvage_site"),
        "scoop": snapshot.get("scoop"),
        "fabrication": {
            "blueprints": list(FABRICATION_BLUEPRINTS),
            "titanium": int(cargo.get("titanium", 0)),
            "can_fabricate": int(cargo.get("titanium", 0)) > 0,
            "fuel_cells": int(cargo.get("fuel_cells", 0)),
            "can_burn_cells": int(cargo.get("fuel_cells", 0)) > 0 and fuel < max_fuel,
        },
        "counts": {
            "hull_percent": round(100.0 * hull / max(1, max_hull), 1),
            "fuel_percent": round(100.0 * fuel / max(1, max_fuel), 1),
            "heat_percent": reactor["heat_pct"],
            "power_total": sum(int(value) for value in ship["power"].values()),
            "salvage_available": bool(snapshot.get("salvage_site")),
            "scoop_available": bool((snapshot.get("scoop") or {}).get("available")),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def engineering_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one engineering command to its existing engine method."""
    action = str(action).strip().lower()
    if action == "power":
        return engine.route_power(
            _int(kwargs.get("engines"), 30),
            _int(kwargs.get("shields"), 25),
            _int(kwargs.get("sensors"), 25),
            _int(kwargs.get("weapons"), 20),
        )
    if action == "reactor_mode":
        return engine.set_reactor_mode(_text(kwargs.get("mode")))
    if action == "reactor_vent":
        return engine.vent_reactor_coolant()
    if action == "reactor_repair":
        return engine.repair_reactor()
    if action == "repair":
        return engine.repair_hull(_int(kwargs.get("amount"), 25))
    if action == "refuel":
        return engine.refuel(_int(kwargs.get("amount"), 20))
    if action == "overhaul":
        return engine.overhaul_ship()
    if action == "fabricate":
        return engine.fabricate_munitions(_text(kwargs.get("blueprint")))
    if action == "salvage":
        ok, message, _report = engine.salvage_derelict(
            strategy=_text(kwargs.get("strategy")) or "balanced"
        )
        return ok, message
    if action == "scoop":
        return engine.scoop_fuel()
    if action == "burn_cells":
        return engine.burn_fuel_cells(_int(kwargs.get("quantity"), 1))
    return False, (
        f"Unknown engineering action '{action}'. "
        f"Use one of: {', '.join(ENGINEERING_ACTIONS)}."
    )
