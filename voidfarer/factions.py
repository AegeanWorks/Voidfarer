"""Galactic Factions, Megacorporations, Standings, and Geopolitical Mechanics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Faction:
    """Sovereign faction or interstellar coalition."""

    id: str
    name: str
    description: str
    ideology: str
    headquarters_system: str
    primary_color: str
    perk_summary: str
    hostile_threshold: int = -50
    friendly_threshold: int = 25
    allied_threshold: int = 70

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Faction:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            ideology=str(data["ideology"]),
            headquarters_system=str(data["headquarters_system"]),
            primary_color=str(data.get("primary_color", "#3b82f6")),
            perk_summary=str(data.get("perk_summary", "")),
            hostile_threshold=int(data.get("hostile_threshold", -50)),
            friendly_threshold=int(data.get("friendly_threshold", 25)),
            allied_threshold=int(data.get("allied_threshold", 70)),
        )


@dataclass(frozen=True)
class Corporation:
    """Interstellar megacorporation shaping sector commerce and industrial technology."""

    id: str
    name: str
    description: str
    headquarters_system: str
    specialty_commodity: str
    corporate_perk: str
    bonus_trade_margin: float = 0.15

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Corporation:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            headquarters_system=str(data["headquarters_system"]),
            specialty_commodity=str(data["specialty_commodity"]),
            corporate_perk=str(data.get("corporate_perk", "")),
            bonus_trade_margin=float(data.get("bonus_trade_margin", 0.15)),
        )


CANONICAL_FACTIONS: dict[str, Faction] = {
    "sol_coalition": Faction(
        id="sol_coalition",
        name="Sol Coalition",
        description="The primary naval authority and legal sovereign of the core star systems.",
        ideology="Rule of Law, Secure Hyperlanes & Defense Logistics",
        headquarters_system="sol",
        primary_color="#3b82f6",
        perk_summary="Naval patrol security and 15% repair cost discount across core worlds.",
    ),
    "vanguard_syndicate": Faction(
        id="vanguard_syndicate",
        name="Free Spacers Syndicate",
        description="A loosely bound confederation of independent freighters, privateers, and smugglers.",
        ideology="Free Enterprise, Smuggler Enclaves & Anti-Colonial Autonomy",
        headquarters_system="sirius",
        primary_color="#10b981",
        perk_summary="Black market clearance and +15% sale profits on contraband and technology.",
    ),
    "precursor_watch": Faction(
        id="precursor_watch",
        name="Precursor Watch",
        description="Monastic scientists and archeologists dedicated to the study of ancient alien tech.",
        ideology="Cosmic Enlightenment, Anomaly Decryption & Xenolith Preservation",
        headquarters_system="pulsar_psr",
        primary_color="#8b5cf6",
        perk_summary="+25% scientific scan XP and guaranteed relic drop rate bonuses.",
    ),
    "nebula_collective": Faction(
        id="nebula_collective",
        name="Nebula Collective",
        description="A consortium of asteroid miners, orbital foundries, and raw material cartels.",
        ideology="Heavy Industry, Automation & Resource Dominance",
        headquarters_system="arcturus",
        primary_color="#f59e0b",
        perk_summary="Deep-space mining drone efficiency (+30% yield) and discounted alloys.",
    ),
    "outlaw_corsairs": Faction(
        id="outlaw_corsairs",
        name="Void Corsairs",
        description="Rogue warbands, hyperlane raiders, and anarchists preying on deep-space shipping.",
        ideology="Ruthless Survival, Interception & Sovereign Piracy",
        headquarters_system="rift_station",
        primary_color="#ef4444",
        perk_summary="Bounties on enemy ships; safe passage through anarchic outer-rim corridors.",
    ),
    "kepler_concord": Faction(
        id="kepler_concord",
        name="Kepler Concord",
        description="A treaty network of observatories, gene banks, and deep-space research habitats.",
        ideology="Open Science, Ecological Stewardship & Shared Discovery",
        headquarters_system="kepler",
        primary_color="#22d3ee",
        perk_summary="Cheaper research projects and bonus xenobiology discoveries on surveyed worlds.",
    ),
    "helios_compact": Faction(
        id="helios_compact",
        name="Helios Compact",
        description="Solar engineers and orbital foundry guilds who power the frontier's industrial spine.",
        ideology="Energy Sovereignty, Foundry Guilds & Frontier Development",
        headquarters_system="helios",
        primary_color="#fbbf24",
        perk_summary="Discounted fuel cells and reactor refits at Compact dockyards.",
    ),
    "ashen_choir": Faction(
        id="ashen_choir",
        name="Ashen Choir",
        description="A contemplative order that tends derelict shrines and listens to the void for omens.",
        ideology="Ancestral Memory, Relic Reverence & Silent Pilgrimage",
        headquarters_system="ashen",
        primary_color="#a78bfa",
        perk_summary="Better relic odds and reduced anomaly hull damage within Choir space.",
    ),
    "iron_meridian": Faction(
        id="iron_meridian",
        name="Iron Meridian",
        description="Mercantile militarists running fortified trade corridors and privateer courts.",
        ideology="Contract Law, Armed Commerce & Corridor Sovereignty",
        headquarters_system="meridian",
        primary_color="#fb7185",
        perk_summary="Escort discounts and higher mission payouts on Meridian contract boards.",
    ),
}

CANONICAL_CORPORATIONS: dict[str, Corporation] = {
    "hyperion_dynamics": Corporation(
        id="hyperion_dynamics",
        name="Hyperion Dynamics",
        description="Premier defense contractor manufacturing pulse cannons and tactical combat drones.",
        headquarters_system="sol",
        specialty_commodity="titanium",
        corporate_perk="Grants access to military-grade laser weapon capacitors and combat escorts.",
        bonus_trade_margin=0.20,
    ),
    "astraea_pharma": Corporation(
        id="astraea_pharma",
        name="Astraea Bio-Pharma",
        description="Pioneers of cryogenic medicine, biogenic nutrients, and life-support modules.",
        headquarters_system="alpha_centauri",
        specialty_commodity="medicines",
        corporate_perk="+20% profit margins when trading Cryo-Antibiotics and Hydroponics.",
        bonus_trade_margin=0.18,
    ),
    "omnicorp_mining": Corporation(
        id="omnicorp_mining",
        name="OmniCorp Astro-Mining",
        description="Monolithic asteroid extraction corporation controlling core foundry stations.",
        headquarters_system="arcturus",
        specialty_commodity="titanium",
        corporate_perk="Discounted hull repairs and automated mining drone upgrades.",
        bonus_trade_margin=0.15,
    ),
    "nexus_cybernetics": Corporation(
        id="nexus_cybernetics",
        name="Nexus Cybernetics",
        description="Advanced AI architecture, quantum substrates, and sensor telemetry arrays.",
        headquarters_system="sirius",
        specialty_commodity="microchips",
        corporate_perk="+25% sensor range and bonus credits when selling Quantum Substrates.",
        bonus_trade_margin=0.22,
    ),
    "vortex_fuel": Corporation(
        id="vortex_fuel",
        name="Vortex Fuel Logistics",
        description="Galaxy-spanning fuel conglomerate refining quantum cells and antimatter thrusters.",
        headquarters_system="betelgeuse",
        specialty_commodity="fuel_cells",
        corporate_perk="30% discount on hyperdrive fuel cell purchases across all affiliated ports.",
        bonus_trade_margin=0.15,
    ),
    "helios_forge": Corporation(
        id="helios_forge",
        name="Helios Forge Combine",
        description="Orbital smelters and solar-collector yards supplying frontier shipbuilders.",
        headquarters_system="helios",
        specialty_commodity="titanium",
        corporate_perk="Discounted hull modules and reactor cooling parts at Compact yards.",
        bonus_trade_margin=0.17,
    ),
    "choir_reliquary": Corporation(
        id="choir_reliquary",
        name="Choir Reliquary Trust",
        description="Curators and licensed antiquarians who authenticate and broker precursor relics.",
        headquarters_system="ashen",
        specialty_commodity="xenoliths",
        corporate_perk="Higher relic sale prices and safer anomaly recovery contracts.",
        bonus_trade_margin=0.20,
    ),
}


def get_faction(faction_id: str) -> Faction | None:
    """Retrieve canonical faction by ID."""
    return CANONICAL_FACTIONS.get(faction_id)


# The civil government a faction installs on its worlds. Generation, conquest and the
# cockpit all read this one table so a captured world never keeps a rival's government.
GOVERNMENT_BY_FACTION: dict[str, str] = {
    "Sol Coalition": "Federal Democracy",
    "Free Spacers Syndicate": "Trade Directorate",
    "Nebula Collective": "Technocratic Council",
    "Void Corsairs": "Pirate Warlordship",
    "Precursor Watch": "Monastic Curate",
    "Kepler Concord": "Research Concordat",
    "Helios Compact": "Foundry Assembly",
    "Ashen Choir": "Relic Curate",
    "Iron Meridian": "Chartered Directorate",
}

DEFAULT_GOVERNMENT = "Colonial Republic"


def government_for(faction_name: str, body_type: str = "") -> str:
    """Government installed by a faction, preserving science outposts as directorates."""
    if body_type == "research_outpost":
        return "Science Directorate"
    return GOVERNMENT_BY_FACTION.get(faction_name, DEFAULT_GOVERNMENT)


def get_corporation(corp_id: str) -> Corporation | None:
    """Retrieve canonical corporation by ID."""
    return CANONICAL_CORPORATIONS.get(corp_id)


def get_faction_standing_tier(standing: int) -> tuple[str, str]:
    """Calculate standing tier label and active perk description."""
    if standing <= -50:
        return "Hostile", "Hostile: +25% Station Tariff & Patrol Intercept Aggression"
    if standing < 0:
        return "Unfriendly", "Unfriendly: +10% Station Tariff"
    if standing < 25:
        return "Neutral", "Neutral: Standard Galactic Tariffs"
    if standing < 70:
        return "Friendly", "Friendly: +10% Trade Margin & 15% Station Repair Discount"
    return "Allied", "Allied: +20% Trade Margin, Free System Refuel, & Naval Escorts"


def calculate_faction_market_modifier(faction_id: str, standing: int) -> float:
    """Calculate purchase price multiplier based on faction standing."""
    if standing <= -50:
        return 1.25  # Severe hostile tariff
    if standing < 0:
        return 1.10  # Unfriendly tariff
    if standing < 25:
        return 1.00  # Standard market rate
    if standing < 70:
        return 0.90  # Friendly 10% discount
    return 0.80  # Allied 20% discount


FACTION_NAME_TO_ID: dict[str, str] = {
    "sol coalition": "sol_coalition",
    "sol federation": "sol_coalition",
    "free spacers syndicate": "vanguard_syndicate",
    "vanguard syndicate": "vanguard_syndicate",
    "outer rim syndicate": "vanguard_syndicate",
    "precursor watch": "precursor_watch",
    "nebula collective": "nebula_collective",
    "void corsairs": "outlaw_corsairs",
    "outer rim anarchy": "outlaw_corsairs",
    "outlaw haven": "outlaw_corsairs",
    "kepler concord": "kepler_concord",
    "helios compact": "helios_compact",
    "ashen choir": "ashen_choir",
    "iron meridian": "iron_meridian",
}


def get_faction_id_from_name(name: str) -> str:
    """Resolve faction name to normalized faction ID."""
    clean = name.strip().lower()
    return FACTION_NAME_TO_ID.get(clean, "outlaw_corsairs" if "outlaw" in clean or "anarchy" in clean else "sol_coalition")



def get_faction_service_perks(faction_id: str, standing: int) -> dict[str, float | bool]:
    """Return concrete service modifiers for the current standing tier and faction."""
    perks: dict[str, float | bool] = {
        "trade_margin": 0.0,
        "repair_discount": 0.0,
        "free_refuel": False,
        "scan_xp_bonus": 0.0,
        "drone_yield_bonus": 0.0,
    }
    if standing >= 70:
        perks["trade_margin"] = float(perks["trade_margin"]) + 0.20
        perks["free_refuel"] = True
    elif standing >= 25:
        perks["trade_margin"] = float(perks["trade_margin"]) + 0.10
        perks["repair_discount"] = max(float(perks["repair_discount"]), 0.15)

    if standing >= 25:
        if faction_id == "sol_coalition":
            perks["repair_discount"] = max(float(perks["repair_discount"]), 0.15)
        elif faction_id == "vanguard_syndicate":
            perks["trade_margin"] = float(perks["trade_margin"]) + 0.15
        elif faction_id == "precursor_watch":
            perks["scan_xp_bonus"] = 0.25
        elif faction_id == "nebula_collective":
            perks["drone_yield_bonus"] = 0.30
    return perks
