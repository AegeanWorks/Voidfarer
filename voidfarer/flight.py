"""One report and action surface for route plotting, navigation and local flight.

The map, route plot, auto-route, jump, orbit and in-system travel are one cockpit
flight workflow, but the CLI exposes five verbs. This module normalizes the flight
state and routes each movement action to the existing engine method.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState

FLIGHT_ACTIONS = ("plot", "navigate", "jump", "orbit", "travel", "arrive")


def flight_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    return {
        "current_system": state.ship.current_system_id,
        "orbiting_body": state.ship.orbiting_body_id,
        "landed_body": state.ship.landed_body_id,
        "traveling": state.ship.travel is not None,
        "fuel": int(state.ship.fuel),
        "max_fuel": int(state.ship.max_fuel),
    }


def flight_report(engine: Any) -> dict[str, Any]:
    """Return the current system, bodies, travel state and route options."""
    state = engine.state
    system = engine.current_system
    orbiting = state.ship.orbiting_body_id
    landed = state.ship.landed_body_id
    travel = state.ship.travel
    connections = []
    for system_id in system.connections:
        target = state.systems.get(system_id)
        plan = engine.plan_route(system_id)
        connections.append({
            "id": system_id,
            "name": target.name if target else system_id,
            "visited": system_id in state.visited_systems,
            "jumps": plan.get("jumps", 0),
            "distance_ly": plan.get("distance_ly", 0.0),
            "fuel_estimate": plan.get("fuel_estimate", 0),
            "reachable": bool(plan.get("reachable")),
        })
    bodies = [
        {
            "id": body.id,
            "name": body.name,
            "body_type": body.body_type,
            "orbit_radius": round(float(body.orbit_radius), 2),
            "landable": bool(body.landable),
            "scanned": bool(body.scan_completed),
            "orbiting": body.id == orbiting,
            "landed": body.id == landed,
        }
        for body in system.bodies
    ]
    return {
        "system": {
            "id": system.id,
            "name": system.name,
            "faction": system.faction,
            "security": round(float(system.security), 2),
            "connections": list(system.connections),
        },
        "bodies": bodies,
        "connections": connections,
        "ship": {
            "fuel": int(state.ship.fuel),
            "max_fuel": int(state.ship.max_fuel),
            "credits": int(state.ship.credits),
            "orbiting_body": orbiting,
            "landed_body": landed,
            "traveling": travel is not None,
            "travel": travel.to_dict() if travel is not None else None,
        },
        "counts": {
            "connections": len(connections),
            "reachable": sum(1 for route in connections if route["reachable"]),
            "bodies": len(bodies),
            "landable_bodies": sum(1 for body in bodies if body["landable"]),
            "scanned_bodies": sum(1 for body in bodies if body["scanned"]),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def flight_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one flight command to its existing engine method."""
    action = str(action).strip().lower()
    if action in ("plot", "route"):
        target = _text(kwargs.get("target"))
        plan = engine.plan_route(target)
        if not plan.get("reachable"):
            return False, f"No hyperlane route to '{target}'."
        path = " -> ".join(plan["path"])
        return True, (
            f"Plot to {target}: {path} | {plan['jumps']} jumps | "
            f"{plan['distance_ly']} ly | ~{plan['fuel_estimate']} fuel"
        )
    if action in ("navigate", "go"):
        return engine.navigate_to(_text(kwargs.get("target")))
    if action == "jump":
        return engine.jump(_text(kwargs.get("system_id")))
    if action == "orbit":
        return engine.orbit(_text(kwargs.get("body_id")))
    if action == "arrive":
        return engine.arrive_now()
    if action == "travel":
        return engine.start_travel(
            _text(kwargs.get("body_id")), mode=_text(kwargs.get("mode")) or "sublight"
        )
    return False, (
        f"Unknown flight action '{action}'. "
        f"Use one of: {', '.join(FLIGHT_ACTIONS)}."
    )
