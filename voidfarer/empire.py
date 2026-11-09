"""One report and action surface for research, outposts, megastructures and diplomacy.

They are one EMPIRE tab in the cockpit but four CLI surfaces and a dozen routes.
This module normalizes them and routes actions to the existing engine methods.
"""

from __future__ import annotations

from typing import Any

from voidfarer.factions import CANONICAL_CORPORATIONS, CANONICAL_FACTIONS
from voidfarer.models import GameState

EMPIRE_ACTIONS = (
    "research_start", "research_queue", "research_cancel",
    "outpost_build", "outpost_upgrade", "outpost_module", "outpost_repair",
    "outpost_specialize", "outpost_crew", "outpost_recall",
    "outpost_link", "outpost_unlink",
    "megastructure_restore",
    "diplomacy", "war_support",
)


def _leader_rows(state: GameState) -> list[dict[str, Any]]:
    rows = []
    for leader in state.faction_leaders:
        faction = CANONICAL_FACTIONS.get(leader.faction_id)
        rows.append({
            "faction_id": leader.faction_id,
            "name": leader.name,
            "title": leader.title,
            "behavior": leader.behavior,
            "faction_name": faction.name if faction else leader.faction_id,
            "ideology": faction.ideology if faction else "",
            "standing": int(state.ship.faction_standings.get(leader.faction_id, 0)),
            "eliminated": leader.faction_id in state.eliminated_factions,
            "trade_pact": leader.faction_id in state.ship.trade_pacts,
            "research_pact": leader.faction_id in state.ship.research_pacts,
            "alliance": leader.faction_id in state.ship.allies,
            "nap_until": int(state.ship.non_aggression_until.get(leader.faction_id, 0)),
        })
    return rows


def empire_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    return {
        "research_active": state.research.active_project_id,
        "research_points": int(state.research.points),
        "research_completed": len(state.research.completed),
        "outposts": len(state.outposts),
        "leaders": len(state.faction_leaders),
        "active_wars": sum(1 for war in state.wars if war.active),
        "allies": len(state.ship.allies),
    }


def empire_report(engine: Any) -> dict[str, Any]:
    """Return research, outposts, megastructure, diplomacy and corporations."""
    research = engine.get_research_report()
    outposts = engine.get_outpost_report()
    megastructure = engine.get_megastructure_report()
    state = engine.state
    leaders = _leader_rows(state)
    wars = [war.to_dict() for war in state.wars]
    corporations = [
        {
            "id": corp_id,
            "name": corp.name,
            "standing": int(state.ship.corp_standings.get(corp_id, 0)),
        }
        for corp_id, corp in CANONICAL_CORPORATIONS.items()
    ]
    return {
        "research": research,
        "outposts": outposts,
        "megastructure": megastructure,
        "diplomacy": {
            "leaders": leaders,
            "wars": wars,
            "active_wars": sum(1 for war in wars if war.get("active")),
        },
        "corporations": corporations,
        "counts": {
            "research_available": len(research.get("available", [])),
            "research_completed": len(research.get("completed", [])),
            "outposts": len(outposts.get("outposts", [])),
            "leaders": len(leaders),
            "active_wars": sum(1 for war in wars if war.get("active")),
            "corporations": len(corporations),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def empire_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one empire command to its existing engine method."""
    action = str(action).strip().lower()
    if action == "research_start":
        return engine.choose_research(_text(kwargs.get("project_id")))
    if action == "research_queue":
        return engine.queue_research(_text(kwargs.get("project_id")))
    if action == "research_cancel":
        return engine.cancel_queued_research(_text(kwargs.get("project_id")))
    if action == "outpost_build":
        return engine.build_outpost(
            _text(kwargs.get("body_id")), _text(kwargs.get("outpost_type_id"))
        )
    if action == "outpost_upgrade":
        return engine.upgrade_outpost(_text(kwargs.get("outpost_id")))
    if action == "outpost_module":
        return engine.install_outpost_module(
            _text(kwargs.get("outpost_id")), _text(kwargs.get("module_id"))
        )
    if action == "outpost_repair":
        return engine.repair_outpost(_text(kwargs.get("outpost_id")))
    if action == "outpost_specialize":
        return engine.specialize_outpost(
            _text(kwargs.get("outpost_id")), _text(kwargs.get("specialization"))
        )
    if action == "outpost_crew":
        return engine.assign_outpost_crew(
            _text(kwargs.get("outpost_id")), _text(kwargs.get("crew_id"))
        )
    if action == "outpost_recall":
        return engine.recall_outpost_crew(
            _text(kwargs.get("outpost_id")), _text(kwargs.get("crew_id"))
        )
    if action == "outpost_link":
        return engine.link_outpost_supply(
            _text(kwargs.get("outpost_id")), _text(kwargs.get("hub_id"))
        )
    if action == "outpost_unlink":
        return engine.unlink_outpost_supply(_text(kwargs.get("outpost_id")))
    if action == "megastructure_restore":
        return engine.restore_megastructure(_text(kwargs.get("body_id")))
    if action == "diplomacy":
        return engine.faction_diplomacy(
            _text(kwargs.get("faction_id")),
            _text(kwargs.get("diplomacy_action")),
            _int(kwargs.get("amount")),
        )
    if action == "war_support":
        return engine.support_war(
            _text(kwargs.get("war_id")),
            _text(kwargs.get("faction_id")),
            _int(kwargs.get("credits")),
        )
    return False, (
        f"Unknown empire action '{action}'. "
        f"Use one of: {', '.join(EMPIRE_ACTIONS)}."
    )
