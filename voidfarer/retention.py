"""Psychological retention mechanics, Precursor relics, dynamic contracts, and pilot mastery."""

from __future__ import annotations

import random
from typing import Any

from voidfarer.models import BountyContract, PilotMastery, PrecursorRelic, ShipState

PILOT_TALENTS: dict[str, dict[str, Any]] = {
    "void_cartographer": {
        "id": "void_cartographer",
        "name": "Void Cartographer",
        "category": "exploration",
        "branch": "EXPLORATION",
        "tier": 1,
        "requires": (),
        "description": "+30% sensor scan research credits and +20% Precursor Relic resonance detection.",
        "scan_bonus": 0.30,
        "relic_bonus": 0.20,
    },
    "dreadnought_tactics": {
        "id": "dreadnought_tactics",
        "name": "Dreadnought Tactician",
        "category": "combat",
        "branch": "COMBAT",
        "tier": 1,
        "requires": (),
        "description": "+25% tactical laser damage and +25 MW shield overcharge absorption.",
        "laser_bonus": 0.25,
        "shield_boost": 25,
    },
    "swarm_commander": {
        "id": "swarm_commander",
        "name": "Swarm Fleet Overlord",
        "category": "fleet",
        "branch": "FLEET",
        "tier": 1,
        "requires": (),
        "description": "+50% autonomous fleet drone harvest yields across all deployed systems.",
        "drone_bonus": 0.50,
    },
    "quantum_smuggler": {
        "id": "quantum_smuggler",
        "name": "Quantum Smuggler",
        "category": "trade",
        "branch": "TRADE",
        "tier": 1,
        "requires": (),
        "description": "-25% hyperlane jump fuel burn and +20% commodity market profit margins.",
        "fuel_reduction": 0.25,
        "trade_bonus": 0.20,
    },
    "deep_space_arrays": {
        "id": "deep_space_arrays",
        "name": "Deep Space Arrays",
        "category": "exploration",
        "branch": "EXPLORATION",
        "tier": 2,
        "requires": ("void_cartographer",),
        "description": "Further +20% sensor scan yields and +10% relic discovery chance.",
        "scan_bonus": 0.20,
        "relic_bonus": 0.10,
    },
    "overcharge_capacitors": {
        "id": "overcharge_capacitors",
        "name": "Overcharge Capacitors",
        "category": "combat",
        "branch": "COMBAT",
        "tier": 2,
        "requires": ("dreadnought_tactics",),
        "description": "Further +15% tactical laser damage and +15 MW shield overcharge.",
        "laser_bonus": 0.15,
        "shield_boost": 15,
    },
    "drone_armada": {
        "id": "drone_armada",
        "name": "Drone Armada",
        "category": "fleet",
        "branch": "FLEET",
        "tier": 2,
        "requires": ("swarm_commander",),
        "description": "Further +25% fleet drone yield and +10 fleet unit integrity.",
        "drone_bonus": 0.25,
    },
    "black_market_contacts": {
        "id": "black_market_contacts",
        "name": "Black Market Contacts",
        "category": "trade",
        "branch": "TRADE",
        "tier": 2,
        "requires": ("quantum_smuggler",),
        "description": "Further +15% trade margin and +1 quantum message capacity.",
        "trade_bonus": 0.15,
    },
}

CATALOG_RELICS: tuple[PrecursorRelic, ...] = (
    # Common
    PrecursorRelic(
        id="relic_crystal_diode",
        name="Silicon Phase Diode",
        rarity="common",
        description="Faintly humming crystalline semiconductor enhancing sensor clarity (+10% scan bounty).",
        passive_stat="scanner_bounty",
        stat_multiplier=0.10,
    ),
    PrecursorRelic(
        id="relic_nano_plating",
        name="Ablative Nanofiber Weave",
        rarity="common",
        description="Self-repairing hull nanofiber augmenting structural integrity (+15 maximum hull).",
        passive_stat="max_hull",
        stat_multiplier=15.0,
    ),
    # Rare
    PrecursorRelic(
        id="relic_tachyon_emitter",
        name="Tachyon Pulse Emitter",
        rarity="rare",
        description="Ancient beam focal lens boosting laser cannon output (+20% laser damage).",
        passive_stat="laser_dmg",
        stat_multiplier=0.20,
    ),
    PrecursorRelic(
        id="relic_flux_capacitor",
        name="Subspace Flux Capacitor",
        rarity="rare",
        description="Spatial folding power reservoir enhancing shield capacitance (+25 MW max shield).",
        passive_stat="shield_cap",
        stat_multiplier=25.0,
    ),
    # Epic
    PrecursorRelic(
        id="relic_dark_core",
        name="Micro-Singularity Siphon",
        rarity="epic",
        description="Tamed gravitational vortex reducing hyperlane jump fuel burn by 30%.",
        passive_stat="fuel_efficiency",
        stat_multiplier=0.30,
    ),
    PrecursorRelic(
        id="relic_chrono_anchor",
        name="Chrono-Displacement Anchor",
        rarity="epic",
        description="Distorts local causality to amplify autonomous fleet drone yields by +40%.",
        passive_stat="drone_yield",
        stat_multiplier=0.40,
    ),
    # Legendary
    PrecursorRelic(
        id="relic_eye_of_void",
        name="Eye of the Void",
        rarity="legendary",
        description="Supreme Precursor artifact: +35% laser combat strike damage and +35% scientific scan bounties.",
        passive_stat="void_eye",
        stat_multiplier=0.35,
    ),
    PrecursorRelic(
        id="relic_stellar_forge",
        name="Ancient Stellar Forge Core",
        rarity="legendary",
        description="Precursor matter compiler: +30% market trade profits and +40 MW shield capacity.",
        passive_stat="stellar_forge",
        stat_multiplier=0.30,
    ),
)

RELICS_BY_RARITY: dict[str, list[PrecursorRelic]] = {
    "common": [r for r in CATALOG_RELICS if r.rarity == "common"],
    "rare": [r for r in CATALOG_RELICS if r.rarity == "rare"],
    "epic": [r for r in CATALOG_RELICS if r.rarity == "epic"],
    "legendary": [r for r in CATALOG_RELICS if r.rarity == "legendary"],
}

CONTRACT_TEMPLATES = (    {
        "category": "combat",
        "title": "Pirate Outlaw Intercept",
        "desc_template": "Neutralize {target} hostile outlaw raiders or corsairs in low-sec corridors.",
        "target_range": (1, 3),
        "base_credits": 750,
        "base_xp": 200,
        "relic_tier": "rare",
    },
    {
        "category": "exploration",
        "title": "Cartographic Stellar Sweep",
        "desc_template": "Perform scientific sensor sweeps on {target} celestial bodies.",
        "target_range": (2, 4),
        "base_credits": 550,
        "base_xp": 160,
        "relic_tier": "common",
    },
    {
        "category": "mining",
        "title": "Industrial Titanium Siphon",
        "desc_template": "Harvest and transfer {target} titanium units from fleet drones or salvage.",
        "target_range": (10, 25),
        "base_credits": 650,
        "base_xp": 150,
        "relic_tier": None,
    },
    {
        "category": "trade",
        "title": "Commercial Exchange Mandate",
        "desc_template": "Execute {target} commercial commodity transactions across system starports.",
        "target_range": (2, 4),
        "base_credits": 500,
        "base_xp": 130,
        "relic_tier": None,
    },
    {
        "category": "pirates",
        "title": "Corsair Toll Reversal",
        "desc_template": "Resolve {target} pirate interceptions without losing the ship.",
        "target_range": (1, 3),
        "base_credits": 900,
        "base_xp": 220,
        "relic_tier": "rare",
    },
    {
        "category": "delivery",
        "title": "Quantum Freight Manifest",
        "desc_template": "Deliver {target} quantum freight orders to their destination ports.",
        "target_range": (1, 3),
        "base_credits": 700,
        "base_xp": 170,
        "relic_tier": None,
    },
    {
        "category": "surface",
        "title": "Surface Survey Charter",
        "desc_template": "Complete {target} surface operations on landable worlds.",
        "target_range": (1, 3),
        "base_credits": 620,
        "base_xp": 160,
        "relic_tier": "common",
    },
    {
        "category": "anomaly",
        "title": "Anomalous Signal Recovery",
        "desc_template": "Resolve {target} spatial anomaly encounters.",
        "target_range": (1, 2),
        "base_credits": 850,
        "base_xp": 210,
        "relic_tier": "rare",
    },
    {
        "category": "diplomacy",
        "title": "Diplomatic Goodwill Circuit",
        "desc_template": "Complete {target} diplomatic goodwill missions for local powers.",
        "target_range": (1, 2),
        "base_credits": 560,
        "base_xp": 140,
        "relic_tier": None,
    },
)

CONTRACT_CATEGORIES: tuple[str, ...] = (
    "exploration", "combat", "mining", "trade", "delivery",
    "pirates", "surface", "anomaly", "diplomacy",
)


def generate_contract(rng: random.Random, category: str | None = None) -> BountyContract:
    """Procedurally instantiate a fresh BountyContract following Zeigarnik task loops."""
    if category:
        candidates = [t for t in CONTRACT_TEMPLATES if t["category"] == category]
        template = rng.choice(candidates) if candidates else rng.choice(CONTRACT_TEMPLATES)
    else:
        template = rng.choice(CONTRACT_TEMPLATES)

    target = rng.randint(template["target_range"][0], template["target_range"][1])
    cid = f"contract_{template['category']}_{rng.randint(1000, 9999)}"
    desc = template["desc_template"].format(target=target)
    cred = template["base_credits"] * target
    xp = template["base_xp"] * target

    return BountyContract(
        id=cid,
        title=template["title"],
        description=desc,
        category=template["category"],
        target_count=target,
        current_count=0,
        reward_credits=cred,
        reward_xp=xp,
        reward_relic_tier=template["relic_tier"],
        completed=False,
    )


def generate_initial_contracts(rng: random.Random) -> tuple[BountyContract, ...]:
    """Generate the starter trio of active contracts across distinct categories."""
    cats = ["exploration", "combat", "mining"]
    return tuple(generate_contract(rng, category=c) for c in cats)


def roll_relic_drop(
    rng: random.Random,
    bonus_prob: float = 0.0,
    forced_tier: str | None = None,
    current_system: str = "sol",
) -> tuple[PrecursorRelic | None, bool]:
    """Execute a Variable Ratio drop roll for Precursor Relics.

    Returns:
        (relic, is_near_miss): If a relic drops, is_near_miss is False.
        If a relic fails to drop but fell within the near-miss window, is_near_miss is True.
    """
    if forced_tier:
        tier_pool = RELICS_BY_RARITY.get(forced_tier, RELICS_BY_RARITY["common"])
        chosen = rng.choice(tier_pool)
        return (
            PrecursorRelic(
                id=f"{chosen.id}_{rng.randint(100, 999)}",
                name=chosen.name,
                rarity=chosen.rarity,
                description=chosen.description,
                passive_stat=chosen.passive_stat,
                stat_multiplier=chosen.stat_multiplier,
                discovered_at_system=current_system,
                bonuses=dict(chosen.bonuses),
            ),
            False,
        )

    base_threshold = 0.30 + bonus_prob
    roll = rng.random()

    if roll < base_threshold:
        # Rolled a relic! Determine rarity tier via weighted distribution
        tier_roll = rng.random()
        if tier_roll < 0.50:
            tier = "common"
        elif tier_roll < 0.80:
            tier = "rare"
        elif tier_roll < 0.95:
            tier = "epic"
        else:
            tier = "legendary"

        pool = RELICS_BY_RARITY[tier]
        chosen = rng.choice(pool)
        return (
            PrecursorRelic(
                id=f"{chosen.id}_{rng.randint(100, 999)}",
                name=chosen.name,
                rarity=chosen.rarity,
                description=chosen.description,
                passive_stat=chosen.passive_stat,
                stat_multiplier=chosen.stat_multiplier,
                discovered_at_system=current_system,
                bonuses=dict(chosen.bonuses),
            ),
            False,
        )

    # Near-miss window: roll just missed the threshold by <= 0.15
    if roll < base_threshold + 0.15:
        return None, True

    return None, False


def calculate_passive_multipliers(ship: ShipState) -> dict[str, float]:
    """Calculate aggregate multipliers across streak, installed relics, and pilot talents."""
    streak = max(1, ship.streak)
    # Streak multiplies yields up to +150% (2.5x)
    streak_mult = 1.0 + min(1.5, (streak - 1) * 0.15)

    multipliers: dict[str, float] = {
        "laser_dmg": 1.0,
        "shield_cap": 0.0,
        "max_hull": 0.0,
        "fuel_efficiency": 1.0,
        "scan_bounty": 1.0 * streak_mult,
        "trade_margin": 1.0 * streak_mult,
        "drone_yield": 1.0,
        "relic_find": 0.0,
        "void_stability": 0.0,
    }

    # Apply pilot talents
    specs = set(ship.mastery.specializations)
    if "void_cartographer" in specs:
        multipliers["scan_bounty"] += 0.30
        multipliers["relic_find"] += 0.20
    if "dreadnought_tactics" in specs:
        multipliers["laser_dmg"] += 0.25
        multipliers["shield_cap"] += 25.0
    if "swarm_commander" in specs:
        multipliers["drone_yield"] += 0.50
    if "quantum_smuggler" in specs:
        multipliers["fuel_efficiency"] -= 0.25
        multipliers["trade_margin"] += 0.20

    # Apply precursor relics
    for r in ship.relics:
        for bonus_stat, bonus_value in r.bonuses.items():
            if bonus_stat in ("scanner_bounty", "scan_bounty"):
                multipliers["scan_bounty"] += bonus_value
            elif bonus_stat == "fuel_efficiency":
                multipliers["fuel_efficiency"] = max(0.40, multipliers["fuel_efficiency"] - bonus_value)
            elif bonus_stat == "void_eye":
                multipliers["laser_dmg"] += bonus_value
            elif bonus_stat == "stellar_forge":
                multipliers["trade_margin"] += bonus_value
                multipliers["shield_cap"] += 40.0 * (bonus_value / 0.30 if bonus_value else 0.0)
            elif bonus_stat in multipliers:
                multipliers[bonus_stat] += bonus_value
        stat = r.passive_stat
        mult = r.stat_multiplier
        if stat == "laser_dmg":
            multipliers["laser_dmg"] += mult
        elif stat == "shield_cap":
            multipliers["shield_cap"] += mult
        elif stat == "max_hull":
            multipliers["max_hull"] += mult
        elif stat == "fuel_efficiency":
            multipliers["fuel_efficiency"] = max(0.40, multipliers["fuel_efficiency"] - mult)
        elif stat in ("scanner_bounty", "scan_bounty"):
            multipliers["scan_bounty"] += mult
        elif stat == "drone_yield":
            multipliers["drone_yield"] += mult
        elif stat == "trade_margin":
            multipliers["trade_margin"] += mult
        elif stat == "void_eye":
            multipliers["laser_dmg"] += mult
            multipliers["scan_bounty"] += mult
        elif stat == "stellar_forge":
            multipliers["trade_margin"] += mult
            multipliers["shield_cap"] += 40.0
        elif stat == "void_stability":
            multipliers["void_stability"] += mult

    return multipliers
