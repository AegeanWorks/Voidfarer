"""Contraband smuggling mechanics, customs scanner risks, and security interdiction."""

from __future__ import annotations

import random
from typing import Any

from voidfarer.galaxy import CANONICAL_COMMODITIES, COMMODITY_MAP
from voidfarer.models import CustomsEncounter, ShipPower, ShipState, StarSystem

CONTRABAND_COMMODITY_IDS: frozenset[str] = frozenset({
    c.id for c in CANONICAL_COMMODITIES if c.category == "contraband"
} | {"xenoliths"})

PATROL_VESSELS: dict[str, list[str]] = {
    "Sol Coalition": [
        "Sol Coalition Customs Cutter 'Vigilant'",
        "Sol Enforcer 'Iron Bastion'",
        "Titan Security Interceptor 'Aegis'",
    ],
    "Kepler Concord": [
        "Kepler Concord Customs Skiff 'Veritas'",
        "Concord Border Patrol 'Arbiter'",
    ],
    "Iron Meridian": [
        "Meridian Border Guard 'Hammer'",
        "Meridian Interceptor 'Dread'",
    ],
    "default": [
        "System Customs Cutter 'Sentinel'",
        "Sector Security Gunboat 'Peacekeeper'",
        "Federal Patrol Corvette 'Vindicator'",
    ],
}


def is_contraband(commodity_id: str) -> bool:
    """Return True if the commodity is classed as illicit contraband."""
    if commodity_id in CONTRABAND_COMMODITY_IDS:
        return True
    comm = COMMODITY_MAP.get(commodity_id)
    return bool(comm and comm.category == "contraband")


def get_contraband_in_cargo(cargo: dict[str, int]) -> dict[str, int]:
    """Extract all contraband goods and counts currently in the ship hold."""
    return {
        cid: int(qty)
        for cid, qty in cargo.items()
        if int(qty) > 0 and is_contraband(cid)
    }


def calculate_customs_scan_risk(
    system: StarSystem,
    cargo: dict[str, int],
    ship: ShipState,
    power: ShipPower | None = None,
    equipment: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    """Compute detection probability and explanatory tactical factors."""
    contraband = get_contraband_in_cargo(cargo)
    if not contraband:
        return 0.0, ["Clean manifest (no contraband detected)"]

    if system.security < 0.65:
        return 0.0, ["Low security sector - no active customs cordon"]

    # Base scan frequency scaled by system security level
    base_chance = (system.security - 0.50) * 0.90
    reasons = [f"High-security cordon ({system.security:.2f})"]

    total_units = sum(contraband.values())
    if total_units >= 3:
        cargo_penalty = min(0.20, (total_units // 3) * 0.05)
        base_chance += cargo_penalty
        reasons.append(f"Significant illicit cargo volume ({total_units} units)")

    # Evasion factors
    evasion = 0.0
    # 1. Stealth chassis / upgrades
    is_stealth_hull = any(
        kw in ship.ship_class.lower()
        for kw in ("stealth", "ghost", "phantom", "shadow")
    )
    has_stealth_upgrades = any(
        "stealth" in uid.lower() or "cloak" in uid.lower()
        for uid in getattr(ship, "equipped_upgrades", ())
    )
    if is_stealth_hull or has_stealth_upgrades:
        evasion += 0.40
        reasons.append("Stealth hull signature dampening (+40% evasion)")

    # 2. Sensor power ECM scrambling
    if power and power.sensors >= 35:
        evasion += 0.25
        reasons.append("Sensor array ECM scrambling (+25% evasion)")

    # 3. Engines speed / hyperlane exit boost
    if power and power.engines >= 40:
        evasion += 0.10
        reasons.append("High-thrust hyperlane exit (+10% evasion)")

    # 4. Pilot mastery
    mastery_lvl = getattr(ship.mastery, "level", 1)
    if mastery_lvl >= 3:
        pilot_bonus = min(0.15, (mastery_lvl - 1) * 0.03)
        evasion += pilot_bonus
        reasons.append(f"Pilot evasion mastery (+{int(pilot_bonus * 100)}%)")

    net_chance = max(0.04, min(0.85, base_chance * (1.0 - min(0.85, evasion))))
    return net_chance, reasons


def generate_customs_encounter(
    system: StarSystem,
    cargo: dict[str, int],
    ship: ShipState,
    seed: int = 0,
) -> CustomsEncounter:
    """Generate a deterministic customs inspection encounter."""
    rng = random.Random(seed if seed != 0 else 42)
    contraband = get_contraband_in_cargo(cargo)

    vessel_pool = PATROL_VESSELS.get(system.faction, PATROL_VESSELS["default"])
    patrol_vessel = rng.choice(vessel_pool)

    # Calculate fine based on black market value
    total_val = 0
    for cid, qty in contraband.items():
        base_price = COMMODITY_MAP[cid].base_price if cid in COMMODITY_MAP else 500
        total_val += base_price * qty

    fine = max(180, int(total_val * 1.40 + rng.randint(0, 50)))
    bribe = max(90, int(fine * 0.55 + rng.randint(-15, 25)))

    desc = (
        f"{patrol_vessel} hails your ship with tactical locks engaged: "
        f"'Unscheduled cargo signature detected. Stand by for customs interdiction inspection.'"
    )

    return CustomsEncounter(
        id=f"customs_{system.id}_{seed % 100000}",
        faction=system.faction,
        system_id=system.id,
        system_name=system.name,
        patrol_vessel=patrol_vessel,
        contraband_found=contraband,
        fine_amount=fine,
        bribe_amount=bribe,
        description=desc,
        seed=seed,
    )
