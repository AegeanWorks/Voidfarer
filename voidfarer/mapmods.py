"""Sector map modifiers: persistent environmental conditions that reshape simulation."""

from __future__ import annotations

import random
from typing import Any, Sequence

from voidfarer.models import MapModifier, StarSystem

MAP_MODIFIER_CATALOG: tuple[MapModifier, ...] = (
    MapModifier(
        id="ion_storm",
        name="Ion Storm Corridor",
        category="hazard",
        description="Charged particle fronts blind sensors and mask hostile signatures.",
        effects={"sensor_mult": 0.75, "scan_mult": 0.85, "encounter_mult": 1.15, "cooling_bonus": -2.0},
    ),
    MapModifier(
        id="nebula_drift",
        name="Dense Nebula Drift",
        category="phenomenon",
        description="Cold gas clouds hide the ship from raiders while improving long-range survey contrast.",
        effects={"evasion": 0.20, "scan_mult": 1.15, "cooling_bonus": 6.0, "sensor_mult": 0.90},
    ),
    MapModifier(
        id="asteroid_shoals",
        name="Asteroid Shoals",
        category="hazard",
        description="Dense debris fields slow flight paths and stress deflector geometry.",
        effects={"fuel_mult": 1.15, "evasion": -0.08, "hull_hazard": 1.0},
    ),
    MapModifier(
        id="radiation_belt",
        name="Radiation Belt",
        category="hazard",
        description="Hard radiation saturates heat exchangers and degrades reactor cooling.",
        effects={"heat_mult": 1.30, "cooling_bonus": -3.0, "scan_mult": 1.05},
    ),
    MapModifier(
        id="solar_flare_zone",
        name="Solar Flare Zone",
        category="hazard",
        description="Violent stellar weather spikes reactor thermal load and scrambles telemetry.",
        effects={"heat_mult": 1.45, "sensor_mult": 0.85, "fuel_mult": 1.05},
    ),
    MapModifier(
        id="quantum_tide",
        name="Quantum Tide",
        category="phenomenon",
        description="Tidal spacetime harmonics reduce hyperspace fuel demand and sharpen sensors.",
        effects={"fuel_mult": 0.80, "scan_mult": 1.10, "sensor_mult": 1.15},
    ),
    MapModifier(
        id="derelict_graveyard",
        name="Derelict Graveyard",
        category="anomaly",
        description="Thousands of dead hulls drift here, rich in salvage and precursor resonance.",
        effects={"relic_find": 0.12, "scan_mult": 1.20, "encounter_mult": 1.10},
    ),
    MapModifier(
        id="trade_confluence",
        name="Trade Confluence",
        category="commerce",
        description="Busy convoy lanes and bonded warehouses widen commercial margins.",
        effects={"trade_margin": 0.10, "encounter_mult": 0.90},
    ),
    MapModifier(
        id="pirate_blockade",
        name="Pirate Blockade",
        category="hazard",
        description="Corsair picket lines interdict civilian traffic and tax every exchange.",
        effects={"encounter_mult": 1.40, "trade_margin": -0.05, "evasion": -0.05},
    ),
    MapModifier(
        id="dark_matter_eddy",
        name="Dark Matter Eddy",
        category="anomaly",
        description="Gravitational shear distorts navigation but reveals hidden mass concentrations.",
        effects={"fuel_mult": 1.20, "scan_mult": 1.30, "relic_find": 0.08},
    ),
    MapModifier(
        id="crystal_shoals",
        name="Crystal Shoals",
        category="phenomenon",
        description="Lattice formations amplify sensor returns and scatter hostile targeting locks.",
        effects={"scan_mult": 1.25, "evasion": 0.12, "cooling_bonus": 2.0},
    ),
)

MAP_MODIFIER_MAP: dict[str, MapModifier] = {m.id: m for m in MAP_MODIFIER_CATALOG}

DEFAULT_MAP_EFFECTS: dict[str, float] = {
    "fuel_mult": 1.0,
    "scan_mult": 1.0,
    "encounter_mult": 1.0,
    "sensor_mult": 1.0,
    "heat_mult": 1.0,
    "cooling_bonus": 0.0,
    "trade_margin": 0.0,
    "relic_find": 0.0,
    "evasion": 0.0,
    "hull_hazard": 0.0,
}

_HAZARD_POOL = ("ion_storm", "asteroid_shoals", "radiation_belt", "solar_flare_zone", "pirate_blockade")
_PHENOMENON_POOL = ("nebula_drift", "quantum_tide", "crystal_shoals", "dark_matter_eddy")


def get_map_modifier(modifier_id: str) -> MapModifier | None:
    return MAP_MODIFIER_MAP.get(modifier_id)


def generate_map_modifiers(
    seed: int,
    system_id: str,
    security: float,
    system_index: int,
) -> tuple[MapModifier, ...]:
    """Generate deterministic per-system modifiers without touching the galaxy RNG stream."""
    rng = random.Random((int(seed) * 2_654_435_761 + int(system_index) * 40_503) & 0xFFFFFFFF)
    roll = rng.random()
    if roll < 0.18:
        return ()
    count = 2 if roll > 0.82 else 1

    pool: list[str] = list(_PHENOMENON_POOL)
    pool.extend(_HAZARD_POOL)
    if security < 0.30:
        pool.extend(("pirate_blockade", "derelict_graveyard"))
    if security > 0.75:
        pool.extend(("trade_confluence", "quantum_tide"))

    chosen_ids: list[str] = []
    while len(chosen_ids) < count and pool:
        candidate = rng.choice(pool)
        pool = [p for p in pool if p != candidate]
        chosen_ids.append(candidate)
    return tuple(MAP_MODIFIER_MAP[mid] for mid in chosen_ids)


def aggregate_map_modifiers(system: StarSystem | None) -> dict[str, float]:
    """Fold every active map modifier into one effect dictionary."""
    effects = dict(DEFAULT_MAP_EFFECTS)
    if system is None:
        return effects
    for modifier in system.modifiers:
        for key, value in modifier.effects.items():
            if key in ("fuel_mult", "scan_mult", "encounter_mult", "sensor_mult", "heat_mult"):
                effects[key] *= float(value)
            elif key in effects:
                effects[key] += float(value)
    effects["fuel_mult"] = max(0.25, effects["fuel_mult"])
    effects["scan_mult"] = max(0.1, effects["scan_mult"])
    effects["encounter_mult"] = max(0.1, effects["encounter_mult"])
    effects["sensor_mult"] = max(0.1, effects["sensor_mult"])
    effects["heat_mult"] = max(0.2, effects["heat_mult"])
    return effects


def describe_modifier_effects(effects: dict[str, float]) -> list[str]:
    """Human readable effect labels for CLI and cockpit rendering."""
    labels = {
        "fuel_mult": "Jump fuel",
        "scan_mult": "Scan yield",
        "encounter_mult": "Encounter risk",
        "sensor_mult": "Sensor range",
        "heat_mult": "Reactor heat",
        "cooling_bonus": "Cooling",
        "trade_margin": "Trade margin",
        "relic_find": "Relic chance",
        "evasion": "Evasion",
        "hull_hazard": "Hull hazard",
    }
    out: list[str] = []
    for key, label in labels.items():
        value = effects.get(key, 0.0)
        if key.endswith("_mult"):
            pct = int(round((value - 1.0) * 100))
            if pct:
                out.append(f"{label} {pct:+d}%")
        elif key == "cooling_bonus":
            if value:
                out.append(f"{label} {value:+.0f}")
        elif value:
            out.append(f"{label} {value * 100:+.0f}%")
    return out


def system_modifier_summary(system: StarSystem | None) -> list[dict[str, Any]]:
    """Serializable modifier summaries for telemetry consumers."""
    if system is None:
        return []
    return [
        {
            "id": m.id,
            "name": m.name,
            "category": m.category,
            "description": m.description,
            "effects": dict(m.effects),
        }
        for m in system.modifiers
    ]


def filter_catalog(category: str | None = None) -> Sequence[MapModifier]:
    if not category:
        return MAP_MODIFIER_CATALOG
    return tuple(m for m in MAP_MODIFIER_CATALOG if m.category == category)
