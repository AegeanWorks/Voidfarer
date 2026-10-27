"""Population capacity, technology limits, and logistic growth for VoidFarer worlds.

A world can only carry as many people as its habitable surface, life-support
technology, and remaining biosphere allow. War devastation removes capacity and
adds a death rate, so a bombed world cannot keep growing toward its old ceiling.
"""

from __future__ import annotations

import math

# Faction development caps the life-support and urban-density technology available
# on its worlds. The values are tech levels, not population multipliers.
FACTION_TECH_LEVELS: dict[str, int] = {
    "Sol Coalition": 9,
    "Kepler Concord": 9,
    "Helios Compact": 8,
    "Nebula Collective": 8,
    "Precursor Watch": 8,
    "Iron Meridian": 7,
    "Free Spacers Syndicate": 6,
    "Ashen Choir": 5,
    "Void Corsairs": 4,
    "Unclaimed": 2,
}

# Fraction of computed capacity that a faction actually settles at generation time.
# Core worlds are densely settled; pirate and frontier holdings are sparse.
FACTION_OCCUPANCY: dict[str, float] = {
    "Sol Coalition": 0.55,
    "Kepler Concord": 0.50,
    "Helios Compact": 0.45,
    "Iron Meridian": 0.40,
    "Nebula Collective": 0.35,
    "Free Spacers Syndicate": 0.28,
    "Precursor Watch": 0.20,
    "Ashen Choir": 0.15,
    "Void Corsairs": 0.08,
    "Unclaimed": 0.0,
}

# How much of a world's geometric surface is usable for habitation. Oceans and ice
# need pressurised habitats; airless rock supports only sealed enclaves.
BODY_AREA_FACTORS: dict[str, float] = {
    "terrestrial": 1.0,
    "savanna": 1.0,
    "super_earth": 1.2,
    "oceanic": 0.45,
    "tundra": 0.60,
    "desert_world": 0.35,
    "ice_world": 0.18,
    "barren": 0.05,
    "lava_world": 0.02,
    "volcanic": 0.03,
    "toxic": 0.04,
}

# Artificial habitats are limited by life-support volume rather than surface area.
ARTIFICIAL_CAPACITY: dict[str, int] = {
    "orbital_station": 3_000_000,
    "research_outpost": 800_000,
    "quantum_relay": 400_000,
    "solar_collector": 150_000,
    "dyson_sphere": 30_000_000,
}

ZERO_CAPACITY_TYPES = frozenset({
    "star",
    "gas_giant",
    "ringed_giant",
    "ice_giant",
    "methane_storm",
    "asteroid_belt",
    "black_hole",
    "wormhole",
})

# People per square kilometre at tech level 1 on a perfectly habitable world.
BASE_DENSITY = 4.5


def clamp_tech_level(tech_level: int | float) -> int:
    """Return a whole tech level in the supported 1..10 band."""
    try:
        value = int(tech_level)
    except (TypeError, ValueError):
        value = 1
    return max(1, min(10, value))


def tech_capacity_multiplier(tech_level: int | float) -> float:
    """Life-support and density multiplier: roughly 0.7x at TL1, 4.5x at TL8."""
    tech = clamp_tech_level(tech_level)
    return 0.55 * (1.30 ** tech)


def effective_capacity(population_capacity: int, devastation: float = 0.0) -> int:
    """Capacity left after war damage; devastation removes up to 65% of the ceiling."""
    cap = max(0, int(population_capacity))
    if cap <= 0:
        return 0
    dev = max(0.0, min(100.0, float(devastation or 0.0)))
    return max(0, int(round(cap * (1.0 - 0.65 * dev / 100.0))))


def compute_population_capacity(
    body_type: str,
    radius_km: float,
    habitability: float,
    tech_level: int | float = 1,
) -> int:
    """Maximum sustainable population from surface area, habitability and technology."""
    hab = max(0.0, min(100.0, float(habitability or 0.0)))
    tech = clamp_tech_level(tech_level)
    if body_type in ZERO_CAPACITY_TYPES or hab <= 0.0:
        return 0

    if body_type in ARTIFICIAL_CAPACITY:
        base = ARTIFICIAL_CAPACITY[body_type]
        support = 0.5 + tech / 10.0
        biosphere = 0.5 + 0.5 * (hab / 100.0)
        return max(0, int(round(base * support * biosphere)))

    radius = max(1.0, float(radius_km or 1.0))
    area_km2 = 4.0 * math.pi * radius * radius
    area_factor = BODY_AREA_FACTORS.get(body_type, 0.35)
    # Habitability enters non-linearly: a 50% world is much less than half as useful
    # because refuges, agriculture, and infrastructure all compete for the same land.
    biosphere = (hab / 100.0) ** 1.80
    capacity = area_km2 * BASE_DENSITY * tech_capacity_multiplier(tech) * area_factor * biosphere
    return max(0, int(round(capacity)))


def initial_population(
    body_type: str,
    radius_km: float,
    habitability: float,
    tech_level: int | float,
    faction: str,
    market_archetype: str = "none",
    station_dockable: bool = False,
) -> int:
    """Settle a generated world at a faction-appropriate share of its capacity."""
    capacity = compute_population_capacity(body_type, radius_km, habitability, tech_level)
    if capacity <= 0:
        return 0
    if body_type in ("dyson_sphere",):
        occupancy = 0.45
    elif body_type == "ring_world":
        occupancy = 0.35
    elif station_dockable or body_type in ARTIFICIAL_CAPACITY:
        occupancy = min(0.85, 0.55 + clamp_tech_level(tech_level) * 0.02)
    else:
        occupancy = FACTION_OCCUPANCY.get(faction, 0.12)
    if market_archetype == "high_tech":
        occupancy += 0.04
    return max(0, min(capacity, int(round(capacity * occupancy))))


def step_population(
    population: int,
    population_capacity: int,
    habitability: float,
    tech_level: int | float,
    devastation: float = 0.0,
    num_ticks: int = 1,
) -> int:
    """Advance one world's population with logistic growth, tech limits and war deaths."""
    pop = max(0, int(population))
    ticks = max(0, int(num_ticks))
    if pop <= 0 or ticks <= 0:
        return 0
    cap = effective_capacity(population_capacity, devastation)
    if cap <= 0:
        return 0

    hab = max(0.0, min(100.0, float(habitability or 0.0))) / 100.0
    tech = clamp_tech_level(tech_level)
    tech_growth = 1.0 + 0.08 * (tech - 1)
    base_rate = 0.00045 * tech_growth * (0.10 + 0.90 * hab)

    if pop > cap:
        # Over-capacity worlds shed people through emigration, famine, and crowding.
        excess = pop / float(cap) - 1.0
        decline_rate = min(0.02, 0.004 + excess * 0.02)
        factor = (1.0 - decline_rate) ** ticks
        grown = pop * factor
    else:
        # Closed-form logistic growth keeps a batched tick (for example tick(2000))
        # from compounding one headroom figure and overshooting capacity.
        ratio = (float(cap - pop) / pop) * math.exp(-base_rate * ticks)
        grown = cap / (1.0 + ratio)

    dev = max(0.0, min(100.0, float(devastation or 0.0)))
    if dev > 0:
        death_rate = (dev / 100.0) ** 1.5 * 0.0022
        grown *= max(0.0, 1.0 - death_rate * ticks)

    return max(0, min(cap, int(round(grown))))
