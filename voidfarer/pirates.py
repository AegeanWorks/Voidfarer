"""Pirate bands, toll encounters, and deterministic raid generation."""

from __future__ import annotations

from dataclasses import dataclass
import random

from voidfarer.models import PirateEncounter, StarSystem


PIRATE_BANDS: tuple[dict[str, object], ...] = (
    {
        "name": "Red Meridian Corsairs",
        "ship_class": "Corsair Raider",
        "flavor": "A painted raider cuts across your bow, its cargo clamps already open.",
    },
    {
        "name": "Ashen Wake",
        "ship_class": "Grave Tender",
        "flavor": "A silent, radiation-scarred hull drifts into weapons range without a hail.",
    },
    {
        "name": "Scrapwing Syndicate",
        "ship_class": "Breaker Skiff",
        "flavor": "A swarm of welded skiffs fences your drive cone with magnetic grapples.",
    },
    {
        "name": "Black Lanterns",
        "ship_class": "Shadow Frigate",
        "flavor": "A frigate with no running lights locks a targeting beam to your reactor.",
    },
    {
        "name": "Orion Freebooters",
        "ship_class": "Freebooter Gunship",
        "flavor": "A gunship broadcasts a cheerful demand for your cargo and a toll for your life.",
    },
)

PIRATE_HAVENS: frozenset[str] = frozenset({"rift_station", "cygnus_x1", "golconda", "draco", "ashen"})


@dataclass(frozen=True)
class PirateRisk:
    chance: float
    reason: str


def pirate_risk(
    system: StarSystem,
    faction_standing: int,
    has_escort: bool = False,
    evasion: float = 0.0,
) -> PirateRisk:
    """Risk of a pirate toll encounter in a system, before the engine RNG roll."""
    chance = 0.04
    reasons = []
    if system.id in PIRATE_HAVENS:
        chance += 0.30
        reasons.append("pirate haven")
    if system.faction.strip().lower() == "void corsairs":
        chance += 0.18
        reasons.append("corsair territory")
    if system.security < 0.30:
        chance += 0.14
        reasons.append("low security")
    if faction_standing <= -50:
        chance += 0.10
        reasons.append("hostile standing")
    if has_escort:
        chance *= 0.45
        reasons.append("escort screen")
    chance *= max(0.20, 1.0 - max(0.0, min(0.90, evasion)))
    return PirateRisk(chance=max(0.01, min(0.75, chance)), reason=", ".join(reasons) or "routine traffic")


def generate_pirate_encounter(
    system: StarSystem,
    seed: int,
    threat_level: int = 1,
    standing: int = 0,
) -> PirateEncounter:
    """Build a deterministic pirate toll encounter for one jump or orbit."""
    rng = random.Random(seed)
    band = rng.choice(PIRATE_BANDS)
    toll = int(90 + threat_level * 55 + max(0.0, 1.0 - system.security) * 260 + rng.randint(0, 90))
    if standing <= -50:
        toll = int(toll * 1.35)
    return PirateEncounter(
        id=f"pirate_{system.id}_{seed % 100000}",
        band_name=str(band["name"]),
        ship_class=str(band["ship_class"]),
        system_id=system.id,
        system_name=system.name,
        toll_credits=max(45, toll),
        threat=max(1, threat_level),
        description=str(band["flavor"]),
        seed=seed,
    )
