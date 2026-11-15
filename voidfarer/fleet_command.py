"""One report and action surface for every fleet asset.

Drones, escort warships, mercenaries and alliances are one fleet to the player
and one tab in the cockpit, but four CLI surfaces and fifteen routes. This
module normalizes the roster and routes commands to the existing engine methods,
so costs, limits, logs and saves stay identical.
"""

from __future__ import annotations

from typing import Any

from voidfarer.fleet import (
    ESCORT_CATALOG,
    escort_sale_value,
    fleet_damage,
    fleet_evasion_bonus,
    fleet_rank,
    fleet_ships_in_system,
    fleet_upkeep,
)
from voidfarer.frontier import MERCENARY_CATALOG
from voidfarer.models import GameState
from voidfarer.upgrades import CATALOG_DRONE_TEMPLATES

FLEET_ACTIONS = (
    "buy_drone", "deploy", "collect", "dismiss", "refit", "refit_damaged",
    "buy_escort", "assign", "role", "train", "captain", "recall_captain",
    "repair", "sell", "dismiss_escort",
    "hire", "ally",
)


def _drone_rows(state: GameState) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    drones: list[dict[str, Any]] = []
    mercenary_units: list[dict[str, Any]] = []
    for unit in state.ship.fleet_drones:
        row = {
            **unit.to_dict(),
            "yield_rate": round(unit.efficiency * (0.5 + unit.integrity / 200.0), 2),
        }
        if unit.drone_type == "mercenary":
            mercenary_units.append(row)
        else:
            drones.append(row)
    return drones, mercenary_units


def _escort_rows(state: GameState) -> list[dict[str, Any]]:
    rows = []
    for ship in state.ship.fleet_ships:
        rows.append({
            **ship.to_dict(),
            "rank": fleet_rank(ship.experience)["name"],
            "sale_value": escort_sale_value(ship),
        })
    return rows


def _mercenary_rows(state: GameState, mercenary_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hired_specialties = {unit.get("specialty") for unit in mercenary_units}
    return [
        {
            **merc,
            "hired": merc["specialty"] in hired_specialties,
            "affordable": state.ship.credits >= int(merc["cost"]),
        }
        for merc in MERCENARY_CATALOG.values()
    ]


def _alliance_rows(state: GameState) -> dict[str, Any]:
    return {
        "allies": list(state.ship.allies),
        "captains": [
            {
                "id": captain.id,
                "name": captain.name,
                "trust": captain.trust,
                "standing": captain.standing,
                "ally": captain.ally,
                "hired": captain.hired,
            }
            for captain in state.ai_captains
        ],
        "allied_count": sum(1 for captain in state.ai_captains if captain.ally),
    }


def fleet_report(state: GameState) -> dict[str, Any]:
    """Return the whole fleet roster, catalogs, upkeep and alliance state."""
    drones, mercenary_units = _drone_rows(state)
    escorts = _escort_rows(state)
    mercenaries = _mercenary_rows(state, mercenary_units)
    alliances = _alliance_rows(state)
    ships = state.ship.fleet_ships
    local = fleet_ships_in_system(ships, state.ship.current_system_id)
    return {
        "current_system": state.ship.current_system_id,
        "battle_stance": state.ship.battle_stance,
        "credits": int(state.ship.credits),
        "drones": drones,
        "mercenaries": mercenaries,
        "escorts": escorts,
        "alliances": alliances,
        "catalogs": {
            "drones": CATALOG_DRONE_TEMPLATES,
            "escorts": ESCORT_CATALOG,
            "mercenaries": MERCENARY_CATALOG,
        },
        "counts": {
            "drones": len(drones),
            "mercenary_units": len(mercenary_units),
            "escorts": len(escorts),
            "allies": alliances["allied_count"],
            "local_escorts": len(local),
        },
        "upkeep_per_month": fleet_upkeep(ships),
        "damage": fleet_damage(ships, state.ship.battle_stance),
        "evasion_bonus": round(fleet_evasion_bonus(ships, state.ship.battle_stance), 3),
    }


def fleet_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    report = fleet_report(state)
    return {
        "counts": report["counts"],
        "upkeep_per_month": report["upkeep_per_month"],
        "damage": report["damage"],
        "evasion_bonus": report["evasion_bonus"],
        "battle_stance": report["battle_stance"],
        "campaign": report["current_system"],
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def fleet_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one fleet command to its existing engine method."""
    action = str(action).strip().lower()
    if action in ("hire", "hire_mercenary"):
        return engine.hire_mercenary(_text(kwargs.get("merc_id")))
    if action in ("dismiss", "dismiss_unit"):
        return engine.dismiss_fleet_unit(_text(kwargs.get("unit_id")))
    if action in ("refit", "refit_unit"):
        return engine.refit_fleet_unit(_text(kwargs.get("unit_id")))
    if action == "refit_damaged":
        return engine.refit_damaged_drones()
    if action in ("ally", "form_alliance"):
        return engine.form_alliance(_text(kwargs.get("captain_id")))
    if action in ("buy_drone", "buy"):
        return engine.buy_drone(_text(kwargs.get("drone_type")), kwargs.get("system_id") or None)
    if action == "deploy":
        return engine.deploy_drone(_text(kwargs.get("unit_id")), _text(kwargs.get("system_id")))
    if action in ("collect", "harvest"):
        ok, message, _ = engine.collect_drone_yield(kwargs.get("unit_id") or None)
        return ok, message
    if action == "buy_escort":
        return engine.buy_escort(_text(kwargs.get("escort_type")), kwargs.get("system_id") or None)
    if action == "assign":
        return engine.assign_escort(_text(kwargs.get("ship_id")), _text(kwargs.get("system_id")))
    if action in ("role", "set_role"):
        return engine.set_fleet_role(_text(kwargs.get("ship_id")), _text(kwargs.get("role")))
    if action == "train":
        return engine.train_fleet_ship(_text(kwargs.get("ship_id")))
    if action == "captain":
        return engine.assign_fleet_captain(_text(kwargs.get("ship_id")), _text(kwargs.get("crew_id")))
    if action == "recall_captain":
        return engine.recall_fleet_captain(_text(kwargs.get("ship_id")))
    if action in ("repair", "repair_escorts"):
        return engine.repair_escorts(int(kwargs.get("amount", 60)))
    if action == "sell":
        return engine.sell_escort(_text(kwargs.get("ship_id")))
    if action == "dismiss_escort":
        return engine.dismiss_escort(_text(kwargs.get("ship_id")))
    return False, (
        f"Unknown fleet action '{action}'. "
        f"Use one of: {', '.join(FLEET_ACTIONS)}."
    )
