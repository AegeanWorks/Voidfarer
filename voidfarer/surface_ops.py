"""One report and action surface for landing, surface operations and reconstruction.

The cockpit's SURFACE panel already combines the landing party and the world's
condition, but the CLI splits `land`, `surface` and `reconstruct`. This module
normalizes the surface state and routes each action to the existing engine method.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState

SURFACE_ACTIONS = ("land", "operation", "reconstruct")


def _current_body(state: GameState) -> Any:
    system = state.systems.get(state.ship.current_system_id)
    if system is None:
        return None
    target_id = state.ship.orbiting_body_id or state.ship.landed_body_id
    return next((body for body in system.bodies if body.id == target_id), None)


def surface_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    body = _current_body(state)
    return {
        "landed": bool(state.ship.landed_body_id),
        "body": body.id if body else state.ship.orbiting_body_id,
        "can_land": bool(body and body.landable and not state.ship.landed_body_id),
        "population": int(body.population) if body else 0,
        "devastation": float(body.devastation or 0.0) if body else 0.0,
        "can_reconstruct": bool(
            body and body.population > 0 and float(body.devastation or 0.0) > 0.0
        ),
    }


def surface_report(engine: Any) -> dict[str, Any]:
    """Return the landing party, surface operations and reconstruction state."""
    surface = engine.get_surface_report()
    landed_id = engine.state.ship.landed_body_id
    body = engine.orbiting_body or (engine._body_by_id(landed_id) if landed_id else None)
    reconstruction: dict[str, Any] = {"available": False}
    if body is not None:
        devastation = float(body.devastation or 0.0)
        reconstruction = {
            "body_id": body.id,
            "body_name": body.name,
            "population": int(body.population),
            "devastation": round(devastation, 2),
            "cost_credits": int(engine.RECONSTRUCTION_CREDIT_COST),
            "credit_reduction": float(engine.RECONSTRUCTION_CREDIT_DEVASTATION),
            "relief_cargo": [list(entry) for entry in engine.RELIEF_CARGO],
            "available": body.population > 0 and devastation > 0.0,
        }
    return {
        "surface": surface,
        "body": {
            "id": body.id,
            "name": body.name,
            "body_type": body.body_type,
            "gravity": float(body.gravity),
            "hazards": list(body.hazards),
            "landable": bool(body.landable),
            "orbiting": engine.state.ship.orbiting_body_id == body.id,
            "landed": engine.state.ship.landed_body_id == body.id,
        } if body else None,
        "reconstruction": reconstruction,
        "counts": {
            "landed": bool(surface.get("landed")),
            "operations": len(surface.get("operations", [])),
            "ready_operations": sum(
                1 for operation in surface.get("operations", [])
                if not operation.get("used")
            ),
            "can_land": bool(body.landable and not surface.get("landed")) if body else False,
            "can_reconstruct": bool(reconstruction.get("available")),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def surface_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one surface command to its existing engine method."""
    action = str(action).strip().lower()
    if action == "land":
        return engine.land_on_body(_text(kwargs.get("body_id")))
    if action in ("operation", "op", "run"):
        return engine.perform_surface_operation(_text(kwargs.get("operation_id")))
    if action == "reconstruct":
        return engine.reconstruct_world(
            _text(kwargs.get("body_id")), _text(kwargs.get("mode")) or "credits"
        )
    return False, (
        f"Unknown surface action '{action}'. "
        f"Use one of: {', '.join(SURFACE_ACTIONS)}."
    )
