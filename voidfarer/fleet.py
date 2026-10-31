"""Escort warship catalog and fleet-manager behavior."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from voidfarer.models import FleetShip


ESCORT_CATALOG: dict[str, dict[str, Any]] = {
    "corvette": {
        "name": "Aegis Escort Corvette",
        "ship_class": "Escort Corvette",
        "role": "escort",
        "cost": 2200,
        "hull": 90,
        "shield": 60,
        "damage": 12,
        "evasion": 0.18,
        "description": "Fast screening ship that intercepts hostile fire.",
    },
    "frigate": {
        "name": "Lancer Missile Frigate",
        "ship_class": "Missile Frigate",
        "role": "frigate",
        "cost": 4200,
        "hull": 160,
        "shield": 110,
        "damage": 24,
        "evasion": 0.10,
        "description": "Line warship with heavy missile batteries.",
    },
    "cruiser": {
        "name": "Bastion Cruiser",
        "ship_class": "Armored Cruiser",
        "role": "cruiser",
        "cost": 7600,
        "hull": 280,
        "shield": 200,
        "damage": 38,
        "evasion": 0.05,
        "description": "Capital escort that anchors a battle line.",
    },
    "carrier": {
        "name": "Nest Carrier",
        "ship_class": "Drone Carrier",
        "role": "carrier",
        "cost": 9800,
        "hull": 240,
        "shield": 160,
        "damage": 30,
        "evasion": 0.04,
        "description": "Launches strike drones and repairs escorts between rounds.",
    },
}


def get_escort_template(escort_type: str) -> dict[str, Any] | None:
    return ESCORT_CATALOG.get(escort_type)


def build_fleet_ship(escort_type: str, system_id: str, count: int) -> FleetShip:
    template = ESCORT_CATALOG[escort_type]
    return FleetShip(
        id=f"escort_{escort_type}_{count + 1}",
        name=f"{template['name']} {count + 1}",
        ship_class=template["ship_class"],
        role=template["role"],
        hull=template["hull"],
        max_hull=template["hull"],
        shield=template["shield"],
        max_shield=template["shield"],
        damage=template["damage"],
        evasion=template["evasion"],
        assigned_system_id=system_id,
        status="escorting",
        experience=0,
    )


def fleet_damage(ships: tuple[FleetShip, ...], formation: str = "balanced") -> int:
    if not ships:
        return 0
    mult = {"aggressive": 1.20, "defensive": 0.70, "balanced": 1.0}.get(formation, 1.0)
    return sum(max(1, int(s.damage * (1.0 + s.experience * 0.01) * mult)) for s in ships if s.hull > 0)


def fleet_evasion_bonus(ships: tuple[FleetShip, ...], formation: str = "balanced") -> float:
    if not ships:
        return 0.0
    screen = sum(s.evasion for s in ships if s.status == "escorting" and s.hull > 0)
    mult = 1.35 if formation == "defensive" else 1.0
    return min(0.30, screen * 0.35 * mult)


def apply_fleet_casualties(ships: tuple[FleetShip, ...], damage: int) -> tuple[tuple[FleetShip, ...], int]:
    """Distribute incoming damage across escorts, returning survivors and absorbed damage."""
    if not ships or damage <= 0:
        return ships, 0
    remaining = damage
    updated: list[FleetShip] = []
    absorbed = 0
    for ship in ships:
        if remaining <= 0:
            updated.append(ship)
            continue
        capacity = ship.shield + ship.hull
        if capacity <= 0:
            updated.append(ship)
            continue
        take = min(remaining, capacity)
        absorbed += take
        remaining -= take
        shield_loss = min(ship.shield, take)
        hull_loss = take - shield_loss
        new_hull = max(0, ship.hull - hull_loss)
        new_shield = max(0, ship.shield - shield_loss)
        updated.append(replace(
            ship,
            hull=new_hull,
            shield=new_shield,
            status="destroyed" if new_hull <= 0 else ("damaged" if new_hull < ship.max_hull * 0.5 else "escorting"),
            experience=ship.experience + (2 if new_hull > 0 else 0),
        ))
    return tuple(updated), absorbed


def repair_fleet_ships(ships: tuple[FleetShip, ...], amount: int) -> tuple[tuple[FleetShip, ...], int]:
    remaining = max(0, amount)
    spent = 0
    updated = []
    for ship in ships:
        if remaining <= 0:
            updated.append(ship)
            continue
        need = (ship.max_shield - ship.shield) + (ship.max_hull - ship.hull)
        repair = min(need, remaining)
        shield_gain = min(ship.max_shield - ship.shield, repair)
        hull_gain = min(ship.max_hull - ship.hull, repair - shield_gain)
        updated.append(replace(
            ship,
            shield=ship.shield + shield_gain,
            hull=ship.hull + hull_gain,
            status="escorting" if ship.hull + hull_gain > 0 else "destroyed",
        ))
        remaining -= repair
        spent += repair
    return tuple(updated), spent
