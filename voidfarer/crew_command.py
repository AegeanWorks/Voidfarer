"""One report and action surface for crew, stations, shore leave and away teams.

The cockpit has one CREW tab with a roster, roles and an away-team view, but the
CLI splits them into `crew` and `away` with nine routes. This module normalizes
the roster and expeditions and routes actions to the existing engine methods.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState

CREW_ACTIONS = (
    "recruit", "train", "dismiss", "shore", "station",
    "away_launch", "away_recall",
)


def crew_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    crew = state.ship.crew
    away_ids = {cid for mission in state.ship.away_missions for cid in mission.crew_ids}
    active = [member for member in crew if member.status == "active"]
    return {
        "active": len(active),
        "capacity": 8,
        "away": len(state.ship.away_missions),
        "injured": sum(1 for member in crew if member.injury_ticks > 0),
        "on_mission": len(away_ids),
        "average_morale": (
            round(sum(member.morale for member in active) / len(active), 1)
            if active else 0.0
        ),
    }


def crew_report(engine: Any) -> dict[str, Any]:
    """Return the roster, roles, bonuses and expedition state in one payload."""
    roster = engine.get_crew_report()
    away = engine.get_away_report()
    return {
        "roster": roster,
        "away": away,
        "counts": {
            "crew": len(roster.get("crew", [])),
            "active": roster.get("active", 0),
            "capacity": roster.get("capacity", 8),
            "away_missions": len(away.get("active", [])),
            "available_missions": len(away.get("available", [])),
            "injured": len(roster.get("injuries", [])),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def crew_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one crew command to its existing engine method."""
    action = str(action).strip().lower()
    if action in ("recruit", "hire"):
        return engine.recruit_crew(_text(kwargs.get("role_id")))
    if action in ("train", "drill"):
        return engine.train_crew_member(_text(kwargs.get("crew_id")))
    if action == "dismiss":
        return engine.dismiss_crew(_text(kwargs.get("crew_id")))
    if action in ("shore", "leave"):
        return engine.shore_leave()
    if action == "station":
        return engine.assign_crew_station(
            _text(kwargs.get("crew_id")), _text(kwargs.get("station"))
        )
    if action == "away_launch":
        crew_ids = kwargs.get("crew_ids")
        if isinstance(crew_ids, str):
            crew_ids = [crew_ids] if crew_ids else None
        return engine.launch_away_mission(
            _text(kwargs.get("mission_type")), crew_ids or None
        )
    if action == "away_recall":
        return engine.recall_away_mission(_text(kwargs.get("mission_id")))
    return False, (
        f"Unknown crew action '{action}'. "
        f"Use one of: {', '.join(CREW_ACTIONS)}."
    )
