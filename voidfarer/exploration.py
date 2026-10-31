"""Derelict salvage sites, fuel scooping profiles, and crew training drills."""

from __future__ import annotations

import zlib
from dataclasses import asdict, dataclass
from typing import Any

from voidfarer.models import CelestialBody, CrewMember

DERELICT_EXCLUDED_TYPES = frozenset({
    "star",
    "orbital_station",
    "research_outpost",
    "black_hole",
    "wormhole",
    "quantum_relay",
    "solar_collector",
})

DERELICT_KINDS: dict[str, tuple[str, str, str]] = {
    "asteroid_belt": ("mining_hulk", "Ore Hauler Wreck", "titanium"),
    "lava_world": ("magma_rig", "Foundry Rig Wreck", "titanium"),
    "ringed_giant": ("cryo_freighter", "Cryo Freighter Wreck", "fuel_cells"),
    "gas_giant": ("gas_harvester", "Gas Harvester Wreck", "fuel_cells"),
    "ice_world": ("colony_transport", "Colony Transport Wreck", "medicines"),
    "desert_world": ("survey_cutter", "Survey Cutter Wreck", "microchips"),
    "ring_world": ("precursor_hulk", "Precursor Hulk", "xenoliths"),
    "dyson_sphere": ("precursor_hulk", "Precursor Hulk", "xenoliths"),
}

SCOOP_PROFILES: dict[str, dict[str, Any]] = {
    "star": {"base": 22, "heat": 12.0, "label": "Stellar plasma ram scoop"},
    "gas_giant": {"base": 16, "heat": 8.0, "label": "Gas envelope scoop"},
    "ringed_giant": {"base": 14, "heat": 8.0, "label": "Ring-plane gas scoop"},
    "ice_world": {"base": 10, "heat": 6.0, "label": "Cryo-volatile scoop"},
    "ice_giant": {"base": 12, "heat": 7.0, "label": "Cryo-volatile scoop"},
}

# Local volatile reservoirs prevent a single body from becoming an infinite fuel tap.
SCOOP_RESERVE_BASE: dict[str, int] = {
    "star": 6,
    "gas_giant": 5,
    "ringed_giant": 4,
    "ice_giant": 4,
    "ice_world": 3,
}
SCOOP_RECHARGE_TICKS = 6


def scoop_reserve(body: CelestialBody) -> int:
    """Deterministic number of scoop passes a body's volatiles support."""
    base = SCOOP_RESERVE_BASE.get(body.body_type, 0)
    if base <= 0:
        return 0
    return base + _stable_crc(body.id) % 3


def recharge_volatile_reserve(
    tapped: int,
    recharge_tick: int,
    current_tick: int,
) -> tuple[int, int]:
    """Apply elapsed recharge intervals to one body's queued volatile taps.

    ``recharge_tick`` is the absolute tick of the next due recharge. When a
    large tick step crosses several intervals, all due taps return at once and
    the schedule advances to the next future slot.
    """
    tapped = max(0, int(tapped))
    recharge_tick = max(0, int(recharge_tick))
    current_tick = max(0, int(current_tick))
    if tapped <= 0:
        return 0, 0
    if recharge_tick <= 0:
        return tapped, current_tick + SCOOP_RECHARGE_TICKS
    if recharge_tick > current_tick + SCOOP_RECHARGE_TICKS:
        recharge_tick = current_tick + SCOOP_RECHARGE_TICKS
    if current_tick < recharge_tick:
        return tapped, recharge_tick
    steps = 1 + (current_tick - recharge_tick) // SCOOP_RECHARGE_TICKS
    remaining = max(0, tapped - steps)
    if remaining <= 0:
        return 0, 0
    return remaining, recharge_tick + steps * SCOOP_RECHARGE_TICKS


@dataclass(frozen=True)
class DerelictSite:
    """A deterministic, once-per-body salvage site with a risk/reward profile."""

    body_id: str
    name: str
    kind: str
    description: str
    credits: int
    cargo_item: str
    cargo_quantity: int
    danger: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_crc(*parts: str) -> int:
    return zlib.crc32("|".join(parts).encode("utf-8")) & 0xFFFFFFFF


def derive_derelict(system_id: str, system_seed: int, body: CelestialBody) -> DerelictSite | None:
    """Return the body's deterministic salvage site, or None when it has none."""
    if body.body_type in DERELICT_EXCLUDED_TYPES or body.station_dockable:
        return None
    kind_data = DERELICT_KINDS.get(body.body_type, ("freighter", "Freighter Wreck", "titanium"))
    kind, kind_label, cargo_item = kind_data
    roll = _stable_crc(system_id, str(system_seed), body.id, body.body_type)
    if roll % 100 >= 60:
        return None
    credits = 120 + roll % 240 + min(180, int(body.radius_km / 900))
    danger = round(0.22 + (roll % 30) / 100.0, 2)
    return DerelictSite(
        body_id=body.id,
        name=f"{kind_label} // {body.name}",
        kind=kind,
        description=(
            f"Abandoned {kind_label.lower()} adrift at {body.name}. "
            "Boarding teams can strip cargo and data cores, but the hulk's "
            "structure and automated defenses remain unstable."
        ),
        credits=credits,
        cargo_item=cargo_item,
        cargo_quantity=1 + roll % 3,
        danger=danger,
    )


def scoop_profile(body: CelestialBody) -> dict[str, Any] | None:
    """Return the fuel-scooping profile for a body, or None when it cannot be scooped."""
    profile = SCOOP_PROFILES.get(body.body_type)
    if profile is None:
        return None
    return {
        "body_id": body.id,
        "body_type": body.body_type,
        "base": int(profile["base"]),
        "heat": float(profile["heat"]),
        "label": str(profile["label"]),
    }


def scoop_yield(body: CelestialBody, effective_sensor_power: float, science_skill: float = 1.0) -> int:
    """Compute fuel recovered by a single scoop pass.

    ``science_skill`` is the fractional bonus from ``character.skill_bonus``
    (0.0 at rank 1); values of 1.0 or more are treated as a raw legacy rank.
    """
    profile = scoop_profile(body)
    if profile is None:
        return 0
    power_factor = 0.6 + max(0.0, effective_sensor_power) / 25.0 * 0.4
    skill_bonus = science_skill if science_skill < 1.0 else (science_skill - 1.0)
    skill_factor = 1.0 + max(0.0, skill_bonus) * 0.5
    return max(1, min(48, int(round(profile["base"] * power_factor * skill_factor))))


def crew_training_cost(member: CrewMember) -> int:
    """Credits required for the next skill rank of a crew specialist."""
    return 160 + max(1, member.skill) * 120
