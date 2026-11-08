"""One fitting surface for every ship hardware catalog.

Hardware upgrades, structural mods, weapons and hull chassis are four catalogs
with four install methods. They all answer the same player question — "what can
I bolt onto this ship?" — so this module normalizes them into one report and one
install/remove entry point. The engine methods, costs and effects are unchanged.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState
from voidfarer.shipmods import (
    CATALOG_SHIP_MODS,
    SHIP_MOD_SLOTS,
    get_available_ship_mods,
    get_ship_mod,
    get_ship_mod_sell_value,
    slot_label,
)
from voidfarer.upgrades import (
    get_available_chassis,
    get_available_upgrades,
    get_chassis_for_ship_class,
    get_sell_value,
    get_upgrade,
)
from voidfarer.weapons import WEAPON_CATALOG, get_weapon

FITTING_CATEGORIES = ("upgrades", "modules", "weapons", "chassis")


def _service_dock(state: GameState) -> bool:
    system = state.systems.get(state.ship.current_system_id)
    if system is None:
        return False
    body = next(
        (candidate for candidate in system.bodies if candidate.id == state.ship.orbiting_body_id),
        None,
    )
    return bool(body and body.station_dockable)


def _upgrades(state: GameState) -> dict[str, Any]:
    ship = state.ship
    installed = dict(ship.equipped_upgrades)
    installed_rows = []
    for slot, upgrade_id in sorted(installed.items()):
        upgrade = get_upgrade(upgrade_id)
        installed_rows.append({
            "slot": slot,
            "id": upgrade_id,
            "name": upgrade.name if upgrade else upgrade_id,
            "resale": get_sell_value(upgrade_id),
        })
    available = [
        {
            **upgrade.to_dict(),
            "category": "upgrades",
            "affordable": ship.credits >= upgrade.cost,
        }
        for upgrade in get_available_upgrades(installed)
    ]
    return {
        "label": "Hardware Upgrades",
        "installed": installed_rows,
        "available": available,
        "installed_count": len(installed_rows),
        "available_count": len(available),
    }


def _modules(state: GameState) -> dict[str, Any]:
    ship = state.ship
    installed = dict(ship.ship_mods)
    installed_rows = []
    for slot, mod_id in sorted(installed.items()):
        mod = get_ship_mod(mod_id)
        installed_rows.append({
            "slot": slot,
            "slot_label": slot_label(slot),
            "id": mod_id,
            "name": mod.name if mod else mod_id,
            "resale": get_ship_mod_sell_value(mod_id),
        })
    available = [
        {
            **mod.to_dict(),
            "category": "modules",
            "slot_label": slot_label(mod.slot),
            "slot_occupied": mod.slot in installed,
            "affordable": ship.credits >= mod.cost,
        }
        for mod in get_available_ship_mods(installed)
    ]
    return {
        "label": "Structural Modules",
        "slots": list(SHIP_MOD_SLOTS),
        "installed": installed_rows,
        "available": available,
        "installed_count": len(installed_rows),
        "available_count": len(available),
        "catalog_count": len(CATALOG_SHIP_MODS),
    }


def _weapons(state: GameState) -> dict[str, Any]:
    ship = state.ship
    installed_ids = set(ship.weapons)
    installed = [
        {
            "id": weapon_id,
            "name": get_weapon(weapon_id).name if get_weapon(weapon_id) else weapon_id,
            "primary": weapon_id == ship.primary_weapon,
        }
        for weapon_id in ship.weapons
    ]
    available = [
        {
            **weapon.to_dict(),
            "category": "weapons",
            "installed": weapon.id in installed_ids,
            "affordable": ship.credits >= weapon.cost,
        }
        for weapon in WEAPON_CATALOG
    ]
    return {
        "label": "Ordnance",
        "installed": installed,
        "available": available,
        "primary": ship.primary_weapon,
        "installed_count": len(installed),
        "available_count": sum(1 for weapon in available if not weapon["installed"]),
        "catalog_count": len(WEAPON_CATALOG),
    }


def _chassis(state: GameState) -> dict[str, Any]:
    current = get_chassis_for_ship_class(state.ship.ship_class)
    current_id = current.id if current else state.ship.ship_class
    available = [
        {
            **chassis.to_dict(),
            "category": "chassis",
            "affordable": state.ship.credits >= chassis.cost,
        }
        for chassis in get_available_chassis(current_id)
        if chassis.cost > 0
    ]
    current_row = {
        "id": current_id,
        "name": current.name if current else state.ship.ship_class,
        "ship_class": state.ship.ship_class,
    }
    return {
        "label": "Hulls",
        "current": current_row,
        "installed": [current_row],
        "installed_count": 1,
        "available": available,
        "available_count": len(available),
    }


def fitting_report(state: GameState) -> dict[str, Any]:
    """Return every fitting catalog with installed/available/affordability state."""
    categories = {
        "upgrades": _upgrades(state),
        "modules": _modules(state),
        "weapons": _weapons(state),
        "chassis": _chassis(state),
    }
    return {
        "service_dock": _service_dock(state),
        "credits": int(state.ship.credits),
        "ship_class": state.ship.ship_class,
        "categories": categories,
        "counts": {
            f"{name}_{key}": value
            for name, category in categories.items()
            for key, value in category.items()
            if key.endswith("_count")
        },
    }


def fitting_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state: counts plus the fitted ship identity."""
    report = fitting_report(state)
    return {
        "service_dock": report["service_dock"],
        "ship_class": report["ship_class"],
        "counts": report["counts"],
        "categories": {
            name: {
                "label": category["label"],
                "installed_count": category.get("installed_count", 0),
                "available_count": category.get("available_count", 0),
            }
            for name, category in report["categories"].items()
        },
    }


def install(engine: Any, category: str, item_id: str) -> tuple[bool, str]:
    """Install or purchase one item through its existing engine method."""
    category = str(category).strip().lower()
    item_id = str(item_id).strip()
    if category not in FITTING_CATEGORIES:
        return False, (
            f"Unknown fitting category '{category}'. "
            f"Use one of: {', '.join(FITTING_CATEGORIES)}."
        )
    if not item_id:
        return False, "A fitting item id is required."
    if category == "upgrades":
        return engine.buy_upgrade(item_id)
    if category == "modules":
        return engine.install_ship_mod(item_id)
    if category == "weapons":
        return engine.install_weapon(item_id)
    return engine.buy_ship_chassis(item_id)


def remove(engine: Any, category: str, target: str) -> tuple[bool, str]:
    """Remove/sell one fitted item where the engine supports it."""
    category = str(category).strip().lower()
    target = str(target).strip()
    if category not in FITTING_CATEGORIES:
        return False, (
            f"Unknown fitting category '{category}'. "
            f"Use one of: {', '.join(FITTING_CATEGORIES)}."
        )
    if not target:
        return False, "A slot or item id is required."
    if category == "upgrades":
        return engine.sell_upgrade(target)
    if category == "modules":
        return engine.remove_ship_mod(target)
    return False, (
        f"{category.title()} cannot be removed once fitted; "
        "install or buy a replacement instead."
    )
