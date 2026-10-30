"""Ancient megastructure restoration catalog and production bonuses."""

from __future__ import annotations

from typing import Any, Iterable

from voidfarer.models import CelestialBody

MEGASTRUCTURE_RESTORATION: dict[str, dict[str, Any]] = {
    "dyson_sphere": {
        "name": "Dyson Swarm",
        "cost": 12000,
        "bonus": "credits",
        "amount": 0.15,
        "label": "+15% outpost credits",
    },
    "ring_world": {
        "name": "Ring World",
        "cost": 10000,
        "bonus": "all",
        "amount": 0.10,
        "label": "+10% all outpost output",
    },
    "quantum_relay": {
        "name": "Quantum Relay",
        "cost": 8000,
        "bonus": "research",
        "amount": 0.15,
        "label": "+15% outpost research",
    },
    "solar_collector": {
        "name": "Solar Collector",
        "cost": 6000,
        "bonus": "fuel_cells",
        "amount": 0.20,
        "label": "+20% fuel-cell output",
    },
    "wormhole": {
        "name": "Wormhole Gate",
        "cost": 15000,
        "bonus": "jump_fuel",
        "amount": 1,
        "label": "-1 jump fuel",
    },
}


def get_restoration(body_type: str) -> dict[str, Any] | None:
    return MEGASTRUCTURE_RESTORATION.get(str(body_type))


def restoration_bonuses(bodies: Iterable[CelestialBody]) -> dict[str, float]:
    """Additive economy and jump bonuses from every restored megastructure."""
    bonuses: dict[str, float] = {
        "credits": 0.0,
        "research": 0.0,
        "fuel_cells": 0.0,
        "all": 0.0,
        "jump_fuel": 0.0,
    }
    for body in bodies:
        if not body.restoration_complete:
            continue
        entry = get_restoration(body.body_type)
        if entry is None:
            continue
        bonuses[str(entry["bonus"])] += float(entry["amount"])
    return bonuses


def apply_output_bonus(
    production: dict[str, float], bonuses: dict[str, float]
) -> dict[str, float]:
    """Apply the shared restoration table to one outpost's per-tick yield."""
    boosted: dict[str, float] = {}
    for key, value in production.items():
        multiplier = 1.0 + bonuses.get("all", 0.0) + bonuses.get(key, 0.0)
        boosted[key] = round(value * multiplier, 2)
    return boosted
