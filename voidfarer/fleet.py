"""Escort warship catalog and fleet-manager behavior."""

from __future__ import annotations

from dataclasses import replace
import random
from typing import Any

from voidfarer.models import FleetShip, StarSystem
from voidfarer.pirates import pirate_risk


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


# Veterans earn their rank in battle; each rank is a legible power spike rather than a
# hidden percentage. Thresholds and bonuses are data so reports and tests share one table.
FLEET_RANKS: tuple[dict[str, Any], ...] = (
    {"name": "Green", "threshold": 0, "damage": 0.00, "evasion": 0.00},
    {"name": "Regular", "threshold": 25, "damage": 0.02, "evasion": 0.01},
    {"name": "Veteran", "threshold": 75, "damage": 0.06, "evasion": 0.02},
    {"name": "Elite", "threshold": 150, "damage": 0.12, "evasion": 0.03},
    {"name": "Ace", "threshold": 300, "damage": 0.20, "evasion": 0.05},
)
FLEET_MAX_EXPERIENCE = int(FLEET_RANKS[-1]["threshold"])
FLEET_TRAINING_XP = 10
PATROL_SWEEP_TICKS = 6

FLEET_UPKEEP_BY_ROLE: dict[str, int] = {
    "escort": 30,
    "frigate": 55,
    "cruiser": 90,
    "carrier": 110,
    "prize": 25,
}


def get_escort_template(escort_type: str) -> dict[str, Any] | None:
    return ESCORT_CATALOG.get(escort_type)


def fleet_rank(experience: int) -> dict[str, Any]:
    """Resolve veterancy rank, badge progress and cumulative combat bonuses."""
    xp = max(0, min(FLEET_MAX_EXPERIENCE, int(experience)))
    index = 0
    for candidate, rank in enumerate(FLEET_RANKS):
        if xp >= int(rank["threshold"]):
            index = candidate
    current = FLEET_RANKS[index]
    following = FLEET_RANKS[index + 1] if index + 1 < len(FLEET_RANKS) else None
    if following is None:
        progress = 1.0
        next_threshold = FLEET_MAX_EXPERIENCE
    else:
        span = int(following["threshold"]) - int(current["threshold"])
        progress = (xp - int(current["threshold"])) / span if span > 0 else 1.0
        next_threshold = int(following["threshold"])
    return {
        "name": str(current["name"]),
        "index": index,
        "threshold": int(current["threshold"]),
        "next_threshold": next_threshold,
        "next_rank": str(following["name"]) if following else "",
        "progress": round(max(0.0, min(1.0, progress)), 3),
        "damage_bonus": float(current["damage"]),
        "evasion_bonus": float(current["evasion"]),
        "experience": xp,
        "max_experience": FLEET_MAX_EXPERIENCE,
    }


def fleet_training_cost(experience: int) -> int:
    """Drydock instruction gets dearer as a crew approaches the next rank."""
    xp = max(0, min(FLEET_MAX_EXPERIENCE, int(experience)))
    return 200 + xp * 5


def fleet_upkeep(ships: tuple[FleetShip, ...]) -> int:
    """Monthly payroll for living escorts; destroyed hulls cost nothing."""
    return sum(
        FLEET_UPKEEP_BY_ROLE.get(ship.role, 30)
        for ship in ships
        if ship.hull > 0
    )


def fleet_victory_experience(enemy_max_hull: int) -> int:
    """A tougher kill teaches more than farming a lone corsair."""
    return 3 + min(6, max(0, int(enemy_max_hull) // 40))


def resolve_patrol_sweep(
    ship: FleetShip,
    system: StarSystem,
    tick: int,
    galaxy_seed: int,
    faction_standing: int = 0,
) -> dict[str, Any]:
    """Resolve one remote patrol cycle; even a quiet tour trains the crew."""
    risk = pirate_risk(system, faction_standing, patrol_escorts=0)
    contact_chance = min(0.85, risk.chance * 2.0 + 0.10)
    roll = random.Random(
        f"{galaxy_seed}:patrol:{ship.id}:{tick}"
    ).random()
    contacted = roll < contact_chance
    if contacted:
        security = max(0.0, min(1.0, float(system.security)))
        credits = 60 + int((1.0 - security) * 180)
        experience = 3
        hull_damage = max(1, int(2 + risk.chance * 14))
        text = (
            f"PATROL SWEEP: {ship.name} drove corsairs out of {system.name} "
            f"(+{credits} cr, +{experience} XP, hull -{hull_damage})."
        )
    else:
        credits = 0
        experience = 1
        hull_damage = 0
        text = ""
    return {
        "ship_id": ship.id,
        "ship_name": ship.name,
        "system_id": system.id,
        "system_name": system.name,
        "contacted": contacted,
        "credits": credits,
        "experience": experience,
        "hull_damage": hull_damage,
        "text": text,
    }


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


def fleet_ships_in_system(ships: tuple[FleetShip, ...], system_id: str) -> tuple[FleetShip, ...]:
    """Escorts physically stationed in one system; remote patrols do not join a fight."""
    return tuple(ship for ship in ships if ship.assigned_system_id == system_id)


def escort_sale_value(ship: FleetShip) -> int:
    """Drydock resale value of an escort or prize, discounted for battle damage."""
    base = max(0, ship.max_hull) * 10 + max(0, ship.damage) * 60 + max(0, ship.max_shield) * 2
    condition = 0.25 if ship.status == "destroyed" else 0.68 if ship.status == "damaged" else 1.0
    return max(100, int(base * 0.5 * condition))


def fleet_damage(ships: tuple[FleetShip, ...], formation: str = "balanced") -> int:
    if not ships:
        return 0
    mult = {"aggressive": 1.20, "defensive": 0.70, "balanced": 1.0}.get(formation, 1.0)
    total = 0
    for ship in ships:
        if ship.hull <= 0:
            continue
        rank = fleet_rank(ship.experience)
        # Experience gives a shallow continuous edge; ranks add the visible jump.
        growth = 1.0 + min(0.50, ship.experience * 0.005) + rank["damage_bonus"]
        total += max(1, int(ship.damage * growth * mult))
    return total


def fleet_evasion_bonus(ships: tuple[FleetShip, ...], formation: str = "balanced") -> float:
    if not ships:
        return 0.0
    screen = sum(
        ship.evasion + fleet_rank(ship.experience)["evasion_bonus"]
        for ship in ships
        if ship.status == "escorting" and ship.hull > 0
    )
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
            experience=min(FLEET_MAX_EXPERIENCE, ship.experience + (2 if new_hull > 0 else 0)),
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
