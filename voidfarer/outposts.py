"""Outpost construction and production catalogs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from voidfarer.models import CelestialBody, Outpost


@dataclass(frozen=True)
class OutpostType:
    id: str
    name: str
    description: str
    cost: int
    production: dict[str, float]
    module: str
    allowed_bodies: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cost": self.cost,
            "production": dict(self.production),
            "module": self.module,
            "allowed_bodies": list(self.allowed_bodies),
        }


OUTPOST_TYPES: tuple[OutpostType, ...] = (
    OutpostType(
        id="mining",
        name="Mining Outpost",
        description="Extracts ore and produces credits each tick.",
        cost=1800,
        production={"credits": 3.0, "titanium": 1.0},
        module="extractor",
        allowed_bodies=("asteroid_belt", "lava_world", "barren", "desert_world", "ice_world"),
    ),
    OutpostType(
        id="research",
        name="Research Station",
        description="Generates research points from local phenomena.",
        cost=2200,
        production={"credits": 2.0, "research": 2.0},
        module="laboratory",
        allowed_bodies=("research_outpost", "ice_world", "gas_giant", "ringed_giant", "black_hole", "ring_world"),
    ),
    OutpostType(
        id="solar",
        name="Solar Collector Array",
        description="Solar panels feeding a local power grid and credit market.",
        cost=1400,
        production={"credits": 3.0, "fuel_cells": 1.0},
        module="solar_array",
        allowed_bodies=("terrestrial", "oceanic", "desert_world", "savanna", "ring_world"),
    ),
    OutpostType(
        id="shipyard",
        name="Frontier Shipyard",
        description="Supports escort construction and hull servicing.",
        cost=3200,
        production={"credits": 3.0},
        module="drydock",
        allowed_bodies=("orbital_station", "ring_world"),
    ),
    OutpostType(
        id="colony",
        name="Civilian Colony",
        description="Grows population and tax revenue over time.",
        cost=2600,
        production={"credits": 4.0, "hydroponics": 1.0},
        module="habitat",
        allowed_bodies=("terrestrial", "oceanic", "savanna", "tundra", "ring_world"),
    ),
)

OUTPOST_MAP: dict[str, OutpostType] = {o.id: o for o in OUTPOST_TYPES}

OUTPOST_PREFERRED_ROLES: dict[str, tuple[str, ...]] = {
    "mining": ("engineer", "quartermaster"),
    "research": ("scientist", "engineer"),
    "solar": ("engineer", "scientist"),
    "shipyard": ("engineer", "quartermaster"),
    "colony": ("medic", "quartermaster"),
}

OUTPOST_CREW_CAPACITY = 3
OUTPOST_CREW_MAX_MULTIPLIER = 1.60

OUTPOST_SPECIALIZATIONS: dict[str, dict[str, Any]] = {
    "industry": {
        "label": "Industry",
        "cost": 600,
        "outputs": {"credits": 1.30, "other": 1.0},
        "crew_capacity": 0,
    },
    "research": {
        "label": "Research",
        "cost": 600,
        "outputs": {"research": 1.40, "credits": 0.85, "other": 1.0},
        "crew_capacity": 0,
    },
    "commerce": {
        "label": "Commerce",
        "cost": 600,
        "outputs": {"credits": 1.20, "other": 1.05},
        "crew_capacity": 0,
    },
    "logistics": {
        "label": "Logistics",
        "cost": 600,
        "outputs": {"credits": 1.10, "research": 1.10, "other": 1.10},
        "crew_capacity": 1,
    },
}

OUTPOST_MODULE_CATALOG: dict[str, dict[str, Any]] = {
    "extractor": {"name": "Ore Extractor", "cost": 400, "production": {"credits": 4.0}},
    "laboratory": {"name": "Research Laboratory", "cost": 500, "production": {"research": 3.0}},
    "solar_array": {"name": "Solar Panel Array", "cost": 300, "production": {"credits": 3.0, "fuel_cells": 1.0}},
    "drydock": {"name": "Drydock Bay", "cost": 700, "production": {"credits": 3.0}},
    "habitat": {"name": "Habitat Ring", "cost": 450, "production": {"credits": 2.0, "hydroponics": 1.0}},
    "sentry_grid": {"name": "Sentry Grid", "cost": 650, "production": {}, "defense": 12},
}

OUTPOST_SUPPLY_MAX_LINKS = 2
OUTPOST_SUPPLY_LINK_BONUS = 0.05
OUTPOST_SUPPLY_HUB_BONUS = 0.08


def outpost_supply_multiplier(
    outpost: Outpost, outposts: tuple[Outpost, ...]
) -> float:
    """Linked outposts gain 5%; a hub gains 8% per attached outpost (max 2)."""
    by_id = {candidate.id: candidate for candidate in outposts}
    if outpost.supply_hub_id:
        hub = by_id.get(outpost.supply_hub_id)
        if (
            hub is not None
            and hub.system_id == outpost.system_id
            and not hub.supply_hub_id
        ):
            return 1.0 + OUTPOST_SUPPLY_LINK_BONUS
        return 1.0
    linked = sum(
        1
        for candidate in outposts
        if candidate.supply_hub_id == outpost.id
        and candidate.system_id == outpost.system_id
    )
    return 1.0 + OUTPOST_SUPPLY_HUB_BONUS * min(
        OUTPOST_SUPPLY_MAX_LINKS, linked
    )



def get_outpost_type(outpost_type: str) -> OutpostType | None:
    return OUTPOST_MAP.get(outpost_type)


def can_build_on(body: CelestialBody, outpost_type: OutpostType) -> bool:
    if body.body_type == "ring_world":
        return outpost_type.id in ("solar", "colony", "research", "shipyard")
    if body.station_dockable:
        return outpost_type.id in ("shipyard", "research")
    if not outpost_type.allowed_bodies:
        return body.body_type != "star"
    return body.body_type in outpost_type.allowed_bodies


def outpost_population_capacity(outpost_type: str, level: int) -> int:
    """Housing ceiling for an installation: colony domes hold far more than a mining rig."""
    base = 30_000 if outpost_type == "colony" else 6_000
    return base * max(1, int(level))


def outpost_capacity_for(outpost: Outpost) -> int:
    """Stored housing ceiling, falling back to the catalog for older saves."""
    if outpost.population_capacity > 0:
        return outpost.population_capacity
    return outpost_population_capacity(outpost.outpost_type, outpost.level)


def grow_outpost_population(outpost: Outpost, num_ticks: int) -> int:
    """Logistic settlement growth toward the housing ceiling, never past it."""
    capacity = outpost_capacity_for(outpost)
    population = max(0, int(outpost.population))
    ticks = max(0, int(num_ticks))
    if population <= 0 or capacity <= 0 or ticks <= 0:
        return min(population, capacity)
    if population >= capacity:
        return capacity
    rate = 0.00005
    ratio = (capacity - population) / population * pow(2.718281828459045, -rate * ticks)
    return max(population, min(capacity, int(round(capacity / (1.0 + ratio)))))


def build_outpost(
    outpost_type: OutpostType,
    system_id: str,
    body: CelestialBody,
    current_tick: int,
    existing_count: int,
) -> Outpost:
    return Outpost(
        id=f"outpost_{outpost_type.id}_{system_id}_{existing_count + 1}",
        name=f"{body.name} {outpost_type.name}",
        system_id=system_id,
        body_id=body.id,
        outpost_type=outpost_type.id,
        level=1,
        population=250 if outpost_type.id != "colony" else 1200,
        population_capacity=outpost_population_capacity(outpost_type.id, 1),
        modules={outpost_type.module: 1},
        production=dict(outpost_type.production),
        integrity=100.0,
        founded_tick=current_tick,
    )


def outpost_defense(outpost: Outpost, crew_by_id: dict[str, Any]) -> int:
    """Base hardening plus Sentry Grids and stationed marines."""
    defense = 10
    for module_id, count in outpost.modules.items():
        template = OUTPOST_MODULE_CATALOG.get(module_id, {})
        defense += int(template.get("defense", 0)) * max(0, int(count))
    for crew_id in outpost.assigned_crew:
        member = crew_by_id.get(crew_id)
        if member is not None and getattr(member, "status", "active") == "active":
            if getattr(member, "role", "") == "marine":
                defense += 4
    return defense


def outpost_repair_cost(outpost: Outpost) -> int:
    """Immediate repairs get dearer with the damage taken."""
    integrity = max(0.0, min(100.0, float(outpost.integrity)))
    return max(100, int((100.0 - integrity) * 8))


def outpost_crew_capacity(outpost: Outpost) -> int:
    """Logistics specialization adds one specialist slot."""
    spec = OUTPOST_SPECIALIZATIONS.get(outpost.specialization)
    bonus = int(spec["crew_capacity"]) if spec else 0
    return OUTPOST_CREW_CAPACITY + bonus


def outpost_crew_multiplier(outpost: Outpost, crew_by_id: dict[str, Any]) -> float:
    """Stationed specialists add a base lift plus a bonus in their preferred role."""
    multiplier = 1.0
    preferred = OUTPOST_PREFERRED_ROLES.get(outpost.outpost_type, ())
    for crew_id in outpost.assigned_crew:
        member = crew_by_id.get(crew_id)
        if member is None or getattr(member, "status", "active") != "active":
            continue
        skill = max(0, int(getattr(member, "skill", 1)))
        multiplier += 0.08 + skill * 0.02
        if getattr(member, "role", "") in preferred:
            multiplier += 0.06
    return min(OUTPOST_CREW_MAX_MULTIPLIER, multiplier)


def outpost_tick_production(
    outpost: Outpost,
    yield_multiplier: float = 1.0,
    crew_multiplier: float = 1.0,
    supply_multiplier: float = 1.0,
) -> dict[str, float]:
    """Effective per-tick yield: catalog base, level growth, modules, crew and map multipliers."""
    template = OUTPOST_MAP.get(outpost.outpost_type)
    base = template.production if template else outpost.production
    level_mult = 1.25 ** max(0, outpost.level - 1)
    production_modules = sum(
        max(0, int(count))
        for module_id, count in outpost.modules.items()
        if OUTPOST_MODULE_CATALOG.get(module_id, {}).get("production")
    )
    module_mult = 1.0 + max(0, production_modules - 1) * 0.10
    crew_mult = max(0.1, min(OUTPOST_CREW_MAX_MULTIPLIER, crew_multiplier))
    integrity_mult = max(0.0, min(1.0, float(outpost.integrity) / 100.0))
    spec = OUTPOST_SPECIALIZATIONS.get(outpost.specialization)
    spec_outputs = spec["outputs"] if spec else {}
    return {
        key: round(
            value
            * level_mult
            * module_mult
            * crew_mult
            * integrity_mult
            * max(0.1, yield_multiplier)
            * max(0.1, supply_multiplier)
            * float(spec_outputs.get(key, spec_outputs.get("other", 1.0))),
            2,
        )
        for key, value in base.items()
    }


def upgrade_outpost(outpost: Outpost, cost_scale: int = 450) -> tuple[bool, Outpost, int, str]:
    if outpost.level >= 5:
        return False, outpost, 0, "Outpost is already at maximum level."
    cost = cost_scale * outpost.level
    from dataclasses import replace

    upgraded = replace(
        outpost,
        level=outpost.level + 1,
        integrity=100.0,
        population_capacity=outpost_population_capacity(outpost.outpost_type, outpost.level + 1),
        population=min(
            int(outpost.population * 1.25),
            outpost_population_capacity(outpost.outpost_type, outpost.level + 1),
        ),
    )
    return True, upgraded, cost, f"Upgraded {outpost.name} to level {upgraded.level} for {cost} cr."
