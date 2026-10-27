"""Procedural galaxy generator, celestial orbital mechanics, and market economy."""

from __future__ import annotations

import math
import random
from dataclasses import replace
from typing import Sequence

from voidfarer.demographics import (
    FACTION_TECH_LEVELS,
    compute_population_capacity,
    initial_population,
    step_population,
    world_tech_level as _world_tech_level,
)
from voidfarer.mapmods import generate_map_modifiers
from voidfarer.models import (
    AnomalyChoice,
    AnomalyEncounter,
    CelestialBody,
    Commodity,
    MarketQuote,
    Moon,
    StarSystem,
)

CANONICAL_COMMODITIES: tuple[Commodity, ...] = (
    Commodity(id="fuel_cells", name="Quantum Fuel Cells", category="industrial", base_price=50, volatility=0.15, volume=1),
    Commodity(id="titanium", name="Titanium Alloy", category="raw", base_price=120, volatility=0.25, volume=2),
    Commodity(id="hydroponics", name="Hydroponic Nutrients", category="agricultural", base_price=40, volatility=0.20, volume=1),
    Commodity(id="medicines", name="Cryo-Antibiotics", category="medical", base_price=220, volatility=0.30, volume=1),
    Commodity(id="microchips", name="Quantum Substrates", category="tech", base_price=450, volatility=0.35, volume=1),
    Commodity(id="xenoliths", name="Xenolith Relics", category="contraband", base_price=950, volatility=0.50, volume=3),
)

COMMODITY_MAP: dict[str, Commodity] = {c.id: c for c in CANONICAL_COMMODITIES}

SYSTEM_ARCHETYPES = [
    ("sol", "Sol System", 0.0, 0.0, "G", "#ffd700", 1.0, "Sol Coalition", "hyperion_dynamics"),
    ("alpha_centauri", "Alpha Centauri", 18.0, 12.0, "K", "#ffaa44", 0.9, "Sol Coalition", "astraea_pharma"),
    ("sirius", "Sirius Prime", -22.0, 15.0, "A", "#cce6ff", 0.85, "Free Spacers Syndicate", "nexus_cybernetics"),
    ("procyon", "Procyon Nexus", 10.0, -28.0, "F", "#fff4e6", 0.8, "Free Spacers Syndicate", "nexus_cybernetics"),
    ("vega", "Vega Outpost", -35.0, -18.0, "A", "#99ccff", 0.65, "Nebula Collective", "omnicorp_mining"),
    ("arcturus", "Arcturus Foundry", 32.0, 30.0, "K", "#ff7733", 0.55, "Nebula Collective", "omnicorp_mining"),
    ("betelgeuse", "Betelgeuse Forge", -45.0, 38.0, "M", "#ff3333", 0.40, "Free Spacers Syndicate", "vortex_fuel"),
    ("cygnus_x1", "Cygnus Void Gate", 48.0, -35.0, "BlackHole", "#8833ff", 0.15, "Void Corsairs", None),
    ("pulsar_psr", "PSR Core Beacon", -15.0, 52.0, "Neutron", "#33ffff", 0.20, "Precursor Watch", None),
    ("rift_station", "The Dark Abyss", 55.0, 42.0, "M", "#cc2255", 0.05, "Void Corsairs", None),
    ("orion_belt", "Orion Belt", -58.0, -8.0, "B", "#aabfff", 0.35, "Nebula Collective", "omnicorp_mining"),
    ("trappist", "TRAPPIST-1", 8.0, 46.0, "M", "#ff7755", 0.30, "Precursor Watch", None),
    ("wolf_359", "Wolf 359", 30.0, -50.0, "RedGiant", "#ff4400", 0.25, "Free Spacers Syndicate", "vortex_fuel"),
    ("golconda", "Golconda Rift", 66.0, 8.0, "O", "#9bb0ff", 0.10, "Void Corsairs", None),
    ("cyclops", "Cyclops Binary", -70.0, 30.0, "Binary", "#ffcc66", 0.45, "Sol Coalition", "hyperion_dynamics"),
    ("kepler", "Kepler Concord", 12.0, 66.0, "G", "#7bf1a8", 0.72, "Kepler Concord", "astraea_pharma"),
    ("helios", "Helios Compact", 20.0, -58.0, "F", "#ffb020", 0.58, "Helios Compact", "vortex_fuel"),
    ("ashen", "Ashen Choir", -62.0, 58.0, "M", "#9b7bd4", 0.28, "Ashen Choir", None),
    ("meridian", "Iron Meridian", 62.0, 22.0, "K", "#fb7185", 0.66, "Iron Meridian", "hyperion_dynamics"),
    ("vela", "Vela Anchorage", -80.0, -42.0, "B", "#a5b4fc", 0.52, "Helios Compact", "omnicorp_mining"),
    ("lyra", "Lyra Breadbasket", 76.0, -12.0, "A", "#e0f2fe", 0.61, "Free Spacers Syndicate", "astraea_pharma"),
    ("draco", "Draco Reach", -30.0, -68.0, "K", "#f97316", 0.22, "Iron Meridian", "omnicorp_mining"),
    ("phoenix", "Phoenix Verge", 40.0, 62.0, "G", "#fde68a", 0.44, "Helios Compact", "helios_forge"),
]

# Systems whose generator appends a black-hole event horizon (void traversal gates)
VOID_GATE_SYSTEM_IDS = ("cygnus_x1", "golconda")

# The pre-expansion core worlds. Their market generation keeps the original RNG stream
# stable for existing saves and deterministic balance tests; new frontier systems use
# their own derived RNG so expanding the map does not perturb legacy gameplay outcomes.
LEGACY_SYSTEM_IDS: tuple[str, ...] = (
    "sol", "alpha_centauri", "sirius", "procyon", "vega", "arcturus", "betelgeuse",
    "cygnus_x1", "pulsar_psr", "rift_station", "orion_belt", "trappist", "wolf_359",
    "golconda", "cyclops",
)


def black_hole_body(sys_id: str, sys_name: str) -> CelestialBody:
    """Construct the black-hole event horizon body for a void gate system."""
    return CelestialBody(
        id=f"{sys_id}_black_hole",
        name=f"{sys_name} Event Horizon",
        body_type="black_hole",
        orbit_radius=0.45,
        orbit_speed=0.11,
        current_angle=math.pi * 0.5,
        radius_km=28.0,
        color="#0b0014",
        hazards=("gravity_well", "tidal_shear", "radiation"),
        station_dockable=False,
        market_archetype="none",
        scan_completed=False,
        scan_discovery="Gravitational singularity with an accretion halo rich in exotic particles.",
        gravity=999.0,
        atmosphere="Event Horizon / Vacuum",
        temperature_c=-270,
        resources=("xenoliths",),
        moons=(),
        landable=False,
        faction="Unclaimed",
        population=0,
        government="None",
        habitability=0.0,
    )

ANOMALIES_CATALOG = [
    {
        "id": "derelict_cruiser",
        "title": "Derelict Dreadnought Beacon",
        "description": "Long-range sensors detect a silent decommissioned battlecruiser drifting in an unstable gravitational vortex.",
        "severity": "moderate",
        "choices": [
            {
                "choice_id": "salvage_hull",
                "text": "Send automated salvage drones to breach the cargo bay (Needs Shields >= 35%)",
                "required_power": "shields",
                "min_power_threshold": 35,
                "outcome_text": "Drones safely deflect orbital debris and recover valuable titanium alloys and credits.",
                "hull_delta": 0,
                "credits_delta": 450,
                "fuel_delta": -5,
                "cargo_reward": {"titanium": 4},
            },
            {
                "choice_id": "download_logs",
                "text": "Align sensor array to decrypt encrypted black-box memory (Needs Sensors >= 40%)",
                "required_power": "sensors",
                "min_power_threshold": 40,
                "outcome_text": "Sensor harmonics decrypt the memory core, uncovering navigational telemetry and rare quantum substrate schematics.",
                "hull_delta": 0,
                "credits_delta": 600,
                "fuel_delta": -3,
                "cargo_reward": {"microchips": 2},
            },
            {
                "choice_id": "emergency_jump",
                "text": "Reroute power to sub-light engines and clear the hazard perimeter",
                "required_power": "engines",
                "min_power_threshold": 20,
                "outcome_text": "The engines push the ship clear of the debris field without taking hull damage.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": -2,
                "cargo_reward": {},
            },
            {
                "choice_id": "derelict_withdraw",
                "text": "Withdraw and leave the hulk to the vortex",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You clear the vortex perimeter and leave the dead ship to its orbit.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "tachyon_rift",
        "title": "Tachyon Space-Time Anomaly",
        "description": "A miniature tachyon rift pulses rhythmically, distorting chronometric sensors and emitting Cherenkov luminescence.",
        "severity": "critical",
        "choices": [
            {
                "choice_id": "harmonic_drain",
                "text": "Calibrate shield harmonics to harvest tachyon flux energy (Needs Shields >= 45%)",
                "required_power": "shields",
                "min_power_threshold": 45,
                "outcome_text": "Shield arrays absorb the gravitational surge, supercharging the ship's hyperdrive fuel reserves.",
                "hull_delta": 0,
                "credits_delta": 300,
                "fuel_delta": 25,
                "cargo_reward": {"fuel_cells": 3},
            },
            {
                "choice_id": "xenolith_extraction",
                "text": "Fire focused pulse laser to destabilize crystallizing vacuum nodes (Needs Weapons >= 40%)",
                "required_power": "weapons",
                "min_power_threshold": 40,
                "outcome_text": "Coherent laser fire cleaves dense exotic crystals from the vortex. Xenolith relics recovered!",
                "hull_delta": -10,
                "credits_delta": 800,
                "fuel_delta": -5,
                "cargo_reward": {"xenoliths": 1},
            },
            {
                "choice_id": "scan_and_retreat",
                "text": "Execute passive sensor pass and stand off (Needs Sensors >= 25%)",
                "required_power": "sensors",
                "min_power_threshold": 25,
                "outcome_text": "Sensors log valuable astrophysical telemetry before radiation reaches danger levels.",
                "hull_delta": 0,
                "credits_delta": 250,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
            {
                "choice_id": "rift_withdraw",
                "text": "Back away from the rift and resume course",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You pull back from the chronometric distortion and let the rift close.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "stranded_freighter",
        "title": "Distress Signal: Merchant Cryo-Freighter",
        "description": "An automated SOS broadcast originates from a disabled civilian transport surrounded by micro-meteors.",
        "severity": "minor",
        "choices": [
            {
                "choice_id": "transfer_fuel",
                "text": "Transfer 5 fuel units and assist with repairs (Needs Engines >= 30%)",
                "required_power": "engines",
                "min_power_threshold": 30,
                "outcome_text": "The grateful crew awards you a generous credit bounty and fresh medical supplies.",
                "hull_delta": 0,
                "credits_delta": 500,
                "fuel_delta": -5,
                "cargo_reward": {"medicines": 3},
            },
            {
                "choice_id": "escort_tow",
                "text": "Lock tractor beam and escort them out of the meteor swarm (Needs Shields >= 35%)",
                "required_power": "shields",
                "min_power_threshold": 35,
                "outcome_text": "Shields withstand the impact cascade. The transport authority pays a substantial rescue bonus.",
                "hull_delta": -5,
                "credits_delta": 750,
                "fuel_delta": -4,
                "cargo_reward": {"hydroponics": 5},
            },
            {
                "choice_id": "ignore_distress",
                "text": "Log the coordinates and continue on current heading",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You log the beacon and maintain your patrol corridor.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": 0,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "quantum_ghost_ship",
        "title": "Quantum Ghost Ship",
        "description": "A frigate phases in and out of sensor lock, its transponder broadcasting a distress code from a century ago.",
        "severity": "critical",
        "choices": [
            {
                "choice_id": "board_ghost",
                "text": "Board through the phase shadow with cutting teams (Needs Weapons >= 35%)",
                "required_power": "weapons",
                "min_power_threshold": 35,
                "outcome_text": "The boarding team recovers a sealed vault of quantum substrates before the hull phases out.",
                "hull_delta": -12,
                "credits_delta": 900,
                "fuel_delta": -3,
                "cargo_reward": {"microchips": 2, "xenoliths": 1},
            },
            {
                "choice_id": "ghost_scan",
                "text": "Match the phase frequency and record its memory core (Needs Sensors >= 45%)",
                "required_power": "sensors",
                "min_power_threshold": 45,
                "outcome_text": "The memory core yields a navigational cipher and a modest archival bounty.",
                "hull_delta": 0,
                "credits_delta": 650,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
            {
                "choice_id": "ghost_withdraw",
                "text": "Withdraw before the phase instability collapses",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You clear the ghost's radius and log the encounter.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": 0,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "helium_storm",
        "title": "Helium Storm Front",
        "description": "A stellar flare drives a charged helium wall across the shipping lane, shredding unshielded hulls.",
        "severity": "major",
        "choices": [
            {
                "choice_id": "storm_surf",
                "text": "Surf the storm front to skim free fuel (Needs Engines >= 50%)",
                "required_power": "engines",
                "min_power_threshold": 50,
                "outcome_text": "The ship rides the pressure wave and scoops a rich charge of helium-3.",
                "hull_delta": -8,
                "credits_delta": 200,
                "fuel_delta": 20,
                "cargo_reward": {"fuel_cells": 2},
            },
            {
                "choice_id": "storm_shield",
                "text": "Brace behind the shield envelope and ride it out (Needs Shields >= 40%)",
                "required_power": "shields",
                "min_power_threshold": 40,
                "outcome_text": "The shields hold. A grateful convoy pays for your relay telemetry.",
                "hull_delta": 0,
                "credits_delta": 450,
                "fuel_delta": -2,
                "cargo_reward": {},
            },
            {
                "choice_id": "storm_wait",
                "text": "Cut engines and wait for the front to pass",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You wait out the storm at minimal power.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "precursor_library",
        "title": "Precursor Data Library",
        "description": "A derelict archive station unfolds like a metal flower, its index still warm after millennia.",
        "severity": "major",
        "choices": [
            {
                "choice_id": "library_decrypt",
                "text": "Decrypt the index with a narrow-band sensor interrogator (Needs Sensors >= 55%)",
                "required_power": "sensors",
                "min_power_threshold": 55,
                "outcome_text": "The index opens. You copy a fragment of precursor mathematics and its substrate lattice.",
                "hull_delta": 0,
                "credits_delta": 1200,
                "fuel_delta": -3,
                "cargo_reward": {"microchips": 3, "xenoliths": 1},
            },
            {
                "choice_id": "library_salvage",
                "text": "Cut open the archive shell and strip its alloy ribs (Needs Weapons >= 30%)",
                "required_power": "weapons",
                "min_power_threshold": 30,
                "outcome_text": "The shell yields high-grade alloy but the archive collapses behind you.",
                "hull_delta": -6,
                "credits_delta": 300,
                "fuel_delta": -2,
                "cargo_reward": {"titanium": 4},
            },
            {
                "choice_id": "library_leave",
                "text": "Mark the archive for the Choir and leave it intact",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You record the coordinates and leave the archive undisturbed.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": 0,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "pirate_beacon",
        "title": "Pirate Lure Beacon",
        "description": "A false distress beacon pings from a hollow asteroid; ion trails betray waiting raiders.",
        "severity": "minor",
        "choices": [
            {
                "choice_id": "beacon_jam",
                "text": "Jam the beacon and sell its cipher to local patrol (Needs Sensors >= 30%)",
                "required_power": "sensors",
                "min_power_threshold": 30,
                "outcome_text": "The patrol pays for the cipher and the ambush goes cold.",
                "hull_delta": 0,
                "credits_delta": 350,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
            {
                "choice_id": "beacon_ambush",
                "text": "Spring the ambush and break the raiders (Needs Weapons >= 45%)",
                "required_power": "weapons",
                "min_power_threshold": 45,
                "outcome_text": "You scatter the ambush and strip the abandoned raider skiff.",
                "hull_delta": -10,
                "credits_delta": 700,
                "fuel_delta": -4,
                "cargo_reward": {"titanium": 1},
            },
            {
                "choice_id": "beacon_avoid",
                "text": "Burn clear of the asteroid field",
                "required_power": "engines",
                "min_power_threshold": 25,
                "outcome_text": "You clear the field before the raiders can close.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": -3,
                "cargo_reward": {},
            },
            {
                "choice_id": "beacon_withdraw",
                "text": "Cut thrust and let the beacon fade",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You drift clear of the lure and leave the raiders waiting.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "crystal_bloom",
        "title": "Crystal Bloom",
        "description": "A lattice of translucent crystals blooms from a dead moon, singing on the hull microphones.",
        "severity": "minor",
        "choices": [
            {
                "choice_id": "bloom_harvest",
                "text": "Crack the outer lattice and harvest the resonating cores (Needs Weapons >= 25%)",
                "required_power": "weapons",
                "min_power_threshold": 25,
                "outcome_text": "The cores ring in the cargo bay, worth a small fortune to the Choir.",
                "hull_delta": -4,
                "credits_delta": 400,
                "fuel_delta": -2,
                "cargo_reward": {"xenoliths": 1},
            },
            {
                "choice_id": "bloom_study",
                "text": "Record the resonance pattern from a safe standoff (Needs Sensors >= 35%)",
                "required_power": "sensors",
                "min_power_threshold": 35,
                "outcome_text": "The resonance data is purchased by a Kepler observatory.",
                "hull_delta": 0,
                "credits_delta": 500,
                "fuel_delta": -1,
                "cargo_reward": {},
            },
            {
                "choice_id": "bloom_leave",
                "text": "Leave the bloom undisturbed",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "The bloom fades behind your wake.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": 0,
                "cargo_reward": {},
            },
        ],
    },
    {
        "id": "meridian_convoy",
        "title": "Meridian Convoy Under Fire",
        "description": "A Meridian trade convoy is pinned by corsair skiffs, its escorts burning hard.",
        "severity": "major",
        "choices": [
            {
                "choice_id": "convoy_intercept",
                "text": "Intercept the corsairs and break their attack run (Needs Weapons >= 40%)",
                "required_power": "weapons",
                "min_power_threshold": 40,
                "outcome_text": "The corsairs scatter. Meridian factors pay a contract bounty and load medical cargo.",
                "hull_delta": -6,
                "credits_delta": 850,
                "fuel_delta": -3,
                "cargo_reward": {"medicines": 2},
            },
            {
                "choice_id": "convoy_escort",
                "text": "Push between the convoy and the raiders (Needs Shields >= 45%)",
                "required_power": "shields",
                "min_power_threshold": 45,
                "outcome_text": "Your shields absorb the first volley and the convoy slips clear.",
                "hull_delta": -10,
                "credits_delta": 600,
                "fuel_delta": -2,
                "cargo_reward": {},
            },
            {
                "choice_id": "convoy_ignore",
                "text": "Hold course and let the Meridian escorts handle it",
                "required_power": "none",
                "min_power_threshold": 0,
                "outcome_text": "You pass the burning convoy without slowing.",
                "hull_delta": 0,
                "credits_delta": 0,
                "fuel_delta": 0,
                "cargo_reward": {},
            },
        ],
    },
]

STELLAR_FLUX_MAP: dict[str, float] = {
    "O": 16.0,
    "B": 7.5,
    "A": 2.8,
    "F": 1.5,
    "G": 1.0,
    "K": 0.55,
    "M": 0.22,
    "RedGiant": 4.5,
    "Binary": 1.8,
    "WolfRayet": 12.0,
    "Neutron": 0.30,
    "BlackHole": 0.35,
}

STELLAR_TEMP_MAP: dict[str, int] = {
    "O": 38000,
    "B": 20000,
    "A": 8800,
    "F": 6700,
    "G": 5778,
    "K": 4600,
    "M": 3200,
    "RedGiant": 3600,
    "Binary": 6100,
    "WolfRayet": 45000,
    "Neutron": 600000,
    "BlackHole": 120000,
}

SCIENTIFIC_ATMO_MAP: dict[str, str] = {
    "terrestrial": "N2 78%, O2 21%, Ar 1% (1.0 atm)",
    "oceanic": "N2 75%, O2 22%, H2O 3% (1.2 atm)",
    "savanna": "N2 77%, O2 21%, CO2 1% (1.1 atm)",
    "tundra": "N2 81%, O2 18%, Ar 1% (0.85 atm)",
    "super_earth": "N2 74%, O2 23%, CO2 2% (1.8 atm)",
    "desert_world": "CO2 95%, N2 3%, Ar 2% (0.06 atm)",
    "ice_world": "N2 95%, CH4 5% (0.15 atm)",
    "lava_world": "SO2 65%, CO2 30%, SiO Vapor (18 atm)",
    "volcanic": "CO2 88%, SO2 9%, H2S 3% (4.5 atm)",
    "toxic": "CO2 96%, N2 3.5%, H2SO4 Clouds (90 atm)",
    "gas_giant": "H2 89%, He 10%, CH4 1% (Deep Envelope)",
    "ringed_giant": "H2 93%, He 6.5%, NH3 0.5% (Deep Envelope)",
    "ice_giant": "H2 80%, He 17%, CH4 3% (Ice Giant)",
    "methane_storm": "H2 80%, He 17%, CH4 3% (Ice Giant)",
    "barren": "Vacuum / Trace Exosphere (0 atm)",
    "asteroid_belt": "Vacuum (0 atm)",
    "orbital_station": "Regulated N2 79%, O2 21% (1.0 atm)",
    "research_outpost": "Regulated N2 78%, O2 21% (0.95 atm)",
    "ring_world": "Regulated N2 78%, O2 21% (1.0 atm, megastructure)",
    "dyson_sphere": "Engineered stellar atmosphere / collected flux",
    "quantum_relay": "Regulated N2 79%, O2 21% (station habitat)",
    "solar_collector": "Vacuum / photovoltaic lattice",
    "wormhole": "Exotic spacetime throat (no atmosphere)",
    "black_hole": "Event Horizon / Vacuum",
    "star": "Ionized H/He Plasma Corona",
}


def compute_habitability_index(
    body_type: str,
    gravity: float,
    temperature_c: int,
    atmosphere: str,
    hazards: Sequence[str] = (),
) -> float:
    """Compute a scientific Earth Similarity / Habitability Index in [0.0, 100.0]."""
    if body_type in ("star", "gas_giant", "ringed_giant", "ice_giant", "methane_storm", "lava_world"):
        return 0.0
    if body_type in ("orbital_station", "research_outpost"):
        return 82.0
    if body_type == "ring_world":
        return 94.0
    if body_type == "dyson_sphere":
        return 96.0
    if body_type in ("quantum_relay",):
        return 84.0
    if body_type in ("solar_collector", "wormhole"):
        return 0.0
    if body_type == "black_hole":
        return 0.0

    temp_sim = math.exp(-(((temperature_c - 18.0) / 36.0) ** 2)) if -90 <= temperature_c <= 115 else 0.0
    grav_sim = math.exp(-(((gravity - 1.0) / 0.58) ** 2)) if 0.1 <= gravity <= 3.0 else 0.05

    atmo_upper = atmosphere.upper()
    if "O2" in atmo_upper and "N2" in atmo_upper:
        atmo_factor = 0.90 if body_type in ("tundra", "super_earth") else 1.0
    elif body_type == "desert_world":
        atmo_factor = 0.32
    elif body_type == "ice_world":
        atmo_factor = 0.18
    elif body_type in ("volcanic", "toxic"):
        atmo_factor = 0.04
    else:
        atmo_factor = 0.02

    hazard_factor = 0.88 ** len(hazards)
    score = 100.0 * atmo_factor * (0.55 * temp_sim + 0.45 * grav_sim) * hazard_factor
    return round(min(100.0, max(0.0, score)), 1)


def compute_scientific_planet_properties(
    body_type: str,
    spectral_type: str,
    orbit_radius_au: float,
    rad_sample: float = 6000.0,
    grav_sample: float = 1.0,
    temp_jitter: int = 0,
    hazards: Sequence[str] = (),
) -> dict[str, float | int | str]:
    """Derive physically consistent radius_km, gravity, atmosphere, temperature_c, and habitability."""
    u = max(0.0, min(1.0, (rad_sample - 2500.0) / 62500.0))
    v = max(0.0, min(1.0, (grav_sample - 0.4) / 2.2))

    # (min_r_km, max_r_km, min_density_gcm3, max_density_gcm3, albedo, greenhouse_k, min_t_c, max_t_c)
    physics_table: dict[str, tuple[float, float, float, float, float, float, int, int]] = {
        "terrestrial": (5900.0, 6800.0, 5.25, 5.65, 0.30, 33.0, 6, 30),
        "oceanic": (6300.0, 7200.0, 4.60, 5.05, 0.27, 36.0, 10, 34),
        "savanna": (5800.0, 6600.0, 5.20, 5.55, 0.28, 38.0, 18, 38),
        "tundra": (5500.0, 6300.0, 5.10, 5.45, 0.52, 18.0, -38, -8),
        "super_earth": (8100.0, 9900.0, 5.75, 6.25, 0.32, 42.0, 4, 36),
        "desert_world": (4200.0, 5700.0, 4.35, 5.00, 0.36, 12.0, -14, 62),
        "barren": (2400.0, 3900.0, 3.80, 5.00, 0.12, 0.0, -195, 220),
        "ice_world": (2600.0, 4300.0, 1.95, 2.65, 0.65, 4.0, -195, -95),
        "lava_world": (6000.0, 7700.0, 5.60, 6.20, 0.10, 680.0, 560, 1320),
        "volcanic": (5700.0, 7300.0, 5.35, 5.95, 0.18, 290.0, 210, 490),
        "toxic": (5900.0, 6500.0, 5.15, 5.42, 0.72, 480.0, 175, 465),
        "gas_giant": (64000.0, 71500.0, 1.24, 1.42, 0.50, 25.0, -155, -95),
        "ringed_giant": (55000.0, 61000.0, 0.69, 0.88, 0.47, 18.0, -180, -120),
        "ice_giant": (24000.0, 26500.0, 1.28, 1.62, 0.42, 12.0, -212, -160),
        "methane_storm": (24000.0, 26500.0, 1.28, 1.62, 0.42, 12.0, -212, -160),
        "asteroid_belt": (420.0, 820.0, 2.10, 2.75, 0.14, 0.0, -205, 65),
        "orbital_station": (12.0, 18.0, 1.0, 1.0, 0.35, 0.0, 20, 22),
        "research_outpost": (10.0, 15.0, 1.0, 1.0, 0.35, 0.0, 20, 22),
        "ring_world": (14000.0, 16000.0, 5.2, 5.5, 0.32, 34.0, 16, 26),
        "black_hole": (20.0, 40.0, 900.0, 1200.0, 0.02, 0.0, -270, -270),
        "dyson_sphere": (80000.0, 95000.0, 2.0, 2.4, 0.04, 12.0, 18, 30),
        "quantum_relay": (14.0, 22.0, 1.0, 1.0, 0.35, 0.0, 20, 22),
        "solar_collector": (8.0, 14.0, 1.0, 1.0, 0.10, 0.0, 15, 25),
        "wormhole": (12.0, 18.0, 1.0, 1.0, 0.01, 0.0, -270, -270),
    }

    r_min, r_max, rho_min, rho_max, albedo, gh_k, t_min, t_max = physics_table.get(
        body_type, (5800.0, 6500.0, 5.10, 5.51, 0.30, 30.0, -10, 35)
    )
    radius_km = round(r_min + u * (r_max - r_min), 1)
    if body_type == "orbital_station":
        gravity = 0.50
    elif body_type == "research_outpost":
        gravity = 0.40
    elif body_type == "black_hole":
        gravity = 999.0
    else:
        density = rho_min + v * (rho_max - rho_min)
        gravity = round(max(0.02, (radius_km / 6371.0) * (density / 5.514)), 2)

    lum = STELLAR_FLUX_MAP.get(spectral_type, 1.0)
    r_eff = max(0.35, float(orbit_radius_au))
    t_eq_k = 278.5 * ((lum * (1.0 - albedo)) ** 0.25) / math.sqrt(r_eff)
    raw_temp_c = int(round(t_eq_k + gh_k - 273.15 + temp_jitter))
    if body_type in ("orbital_station", "research_outpost"):
        temperature_c = 21
    elif body_type in ("black_hole", "wormhole"):
        temperature_c = -270
    elif body_type == "dyson_sphere":
        temperature_c = 22
    elif body_type in ("barren", "asteroid_belt"):
        temperature_c = max(t_min, min(t_max, raw_temp_c))
    else:
        mid_t = 0.5 * (t_min + t_max)
        blended = int(round(0.65 * mid_t + 0.35 * raw_temp_c))
        temperature_c = max(t_min, min(t_max, blended))

    atmosphere = SCIENTIFIC_ATMO_MAP.get(body_type, "Vacuum (0 atm)")
    habitability = compute_habitability_index(body_type, gravity, temperature_c, atmosphere, hazards)
    return {
        "radius_km": radius_km,
        "gravity": gravity,
        "atmosphere": atmosphere,
        "temperature_c": temperature_c,
        "habitability": habitability,
    }


def get_colony_tier(population: int) -> str:
    """Classify world or habitat population into sociological colony tiers."""
    pop = int(population)
    if pop <= 0:
        return "Uninhabited"
    if pop < 10_000:
        return "Outpost"
    if pop < 1_000_000:
        return "Colony"
    if pop < 50_000_000:
        return "Settlement"
    if pop < 1_000_000_000:
        return "Metropolis"
    return "Mega-Ecumenopolis"


def step_population_dynamics(body: CelestialBody, num_ticks: int = 1, stability: float = 50.0) -> int:
    """Advance population with capacity, technology, devastation and civil-order limits."""
    if body.population <= 0 or num_ticks <= 0:
        return 0
    capacity = body.population_capacity
    if capacity <= 0:
        capacity = compute_population_capacity(
            body.body_type, body.radius_km, body.habitability, body.tech_level
        )
    return step_population(
        body.population,
        capacity,
        body.habitability,
        body.tech_level,
        body.devastation,
        num_ticks,
        stability,
    )


def world_tech_level(faction: str, body_type: str, market_archetype: str = "none") -> int:
    """Re-exported from demographics: tech level of a world from owner and industry."""
    return _world_tech_level(faction, body_type, market_archetype)


class GalaxyGenerator:
    """Generates deterministic star systems, celestial bodies, and hyperlane corridors."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_galaxy(self) -> dict[str, StarSystem]:
        """Generate connected star systems across the sector."""
        systems: dict[str, StarSystem] = {}

        # 1. Create base systems
        for index, (
            sys_id,
            name,
            x,
            y,
            spectral,
            color,
            sec,
            faction,
            dominant_corp,
        ) in enumerate(SYSTEM_ARCHETYPES):
            bodies = self._generate_bodies(sys_id, name, spectral, faction)
            systems[sys_id] = StarSystem(
                id=sys_id,
                name=name,
                seed=self.rng.randint(1000, 99999),
                x=x,
                y=y,
                spectral_type=spectral,
                color=color,
                security=sec,
                faction=faction,
                bodies=tuple(bodies),
                connections=(),
                dominant_corp=dominant_corp,
                modifiers=generate_map_modifiers(self.seed, sys_id, sec, index),
            )

        # 2. Build hyperlane mesh ensuring full graph connectivity
        connections = self._build_hyperlanes(systems)
        final_systems: dict[str, StarSystem] = {}
        for s_id, s_obj in systems.items():
            final_systems[s_id] = StarSystem(
                id=s_obj.id,
                name=s_obj.name,
                seed=s_obj.seed,
                x=s_obj.x,
                y=s_obj.y,
                spectral_type=s_obj.spectral_type,
                color=s_obj.color,
                security=s_obj.security,
                faction=s_obj.faction,
                bodies=s_obj.bodies,
                connections=tuple(sorted(connections[s_id])),
                dominant_corp=s_obj.dominant_corp,
                modifiers=s_obj.modifiers,
            )
        return final_systems

    def _generate_bodies(
        self, sys_id: str, sys_name: str, spectral: str, faction: str = "Sol Coalition"
    ) -> list[CelestialBody]:
        """Generate central star and orbiting planetary bodies."""
        bodies: list[CelestialBody] = []

        # Central primary star
        star_colors = {
            "O": "#9bb0ff", "B": "#aabfff", "A": "#cad7ff", "F": "#f8f7ff",
            "G": "#ffd700", "K": "#ffaa44", "M": "#ff5533", "BlackHole": "#8833ff",
            "Neutron": "#33ffff", "WolfRayet": "#ff66cc", "RedGiant": "#ff4400",
            "Binary": "#ffcc66",
        }
        star_color = star_colors.get(spectral, "#ffd700")
        bodies.append(
            CelestialBody(
                id=f"{sys_id}_star",
                name=f"{sys_name} Primary",
                body_type="star",
                orbit_radius=0.0,
                orbit_speed=0.0,
                current_angle=0.0,
                radius_km=696340.0,
                color=star_color,
                hazards=("solar_radiation",),
                station_dockable=False,
                market_archetype="none",
                scan_completed=True,
                scan_discovery=f"{spectral}-class stellar primary emitting radiant plasma.",
                gravity=28.0,
                atmosphere=SCIENTIFIC_ATMO_MAP["star"],
                temperature_c=STELLAR_TEMP_MAP.get(spectral, 5778),
                resources=("helium",),
                habitability=0.0,
            )
        )

        archetype_pool = [
            ("terrestrial", "mineral_rich", "mining", "#d4a373", "Rich subterranean veins of rare heavy metals."),
            ("oceanic", "habitable", "agricultural", "#48cae4", "Atmospheric bio-spheres generating organic nutrients."),
            ("gas_giant", "hydrogen_storm", "industrial", "#f4a261", "Upper atmospheric siphon extracting deuterium isotopes."),
            ("orbital_station", "citadel", "high_tech", "#00f0ff", "Orbital manufacturing enclave producing quantum substrates."),
            ("asteroid_belt", "debris_field", "mining", "#8d99ae", "Shattered planetesimals harboring raw titanium ores."),
            ("desert_world", "silicate_plains", "mining", "#e9c46a", "Sun-scorched dunes concealing rare silicate crystal seams."),
            ("ice_world", "cryo_ocean", "agricultural", "#a8dadc", "Subsurface cryo-oceans teeming with cultivable extremophiles."),
            ("lava_world", "magma_forge", "industrial", "#e76f51", "Tectonic magma vents powering automated heavy foundries."),
            ("ringed_giant", "helium_harvest", "industrial", "#c9ada7", "Ringed gas envelope mined for helium-3 and exotic isotopes."),
            ("research_outpost", "science", "high_tech", "#b5179e", "Deep-space research campus studying precursor field harmonics."),
            ("savanna", "fertile_plains", "agricultural", "#90be6d", "Temperate savanna belts ideal for colony agriculture."),
            ("tundra", "permafrost", "agricultural", "#bde0fe", "Cold tundra biome supporting hardy medicinal flora."),
            ("toxic", "acid_mists", "industrial", "#b5e48c", "Caustic cloud layers rich in industrial catalysts."),
            ("barren", "cratered", "mining", "#adb5bd", "Airless crater fields exposing shallow metal deposits."),
            ("super_earth", "high_gravity", "mining", "#6a994e", "High-gravity world with dense ore-bearing mantle."),
            ("ice_giant", "methane_storm", "industrial", "#a2d2ff", "Frigid ice giant harvesting volatile methane clathrates."),
        ]

        if sys_id in ("betelgeuse", "cygnus_x1", "rift_station"):
            archetype_pool.append(
                ("volcanic", "dark_market", "black_market", "#e63946", "Unregulated shadow bazaar trafficking illicit xenoliths.")
            )
        if sys_id in ("sol", "alpha_centauri", "cyclops"):
            archetype_pool.append(
                ("ring_world", "orbital_ring", "high_tech", "#c77dff", "Ancient ring megastructure supporting a stratified orbital civilization.")
            )

        habitable_types = {"terrestrial", "oceanic", "savanna", "tundra", "ring_world", "dyson_sphere"}
        resource_map = {
            "terrestrial": ("titanium",), "oceanic": ("hydroponics",), "gas_giant": ("fuel_cells",),
            "asteroid_belt": ("titanium", "xenoliths"), "desert_world": ("titanium",), "ice_world": ("hydroponics",),
            "lava_world": ("microchips",), "ringed_giant": ("fuel_cells",), "research_outpost": ("microchips",),
            "savanna": ("hydroponics", "medicines"), "tundra": ("medicines",), "toxic": ("medicines",),
            "barren": ("titanium",), "super_earth": ("titanium", "xenoliths"), "ice_giant": ("fuel_cells",),
            "volcanic": ("xenoliths",), "ring_world": ("microchips", "hydroponics"),
            "black_hole": ("xenoliths",), "solar_array": ("fuel_cells",),
            "dyson_sphere": ("microchips", "fuel_cells"), "quantum_relay": ("microchips",),
            "solar_collector": ("fuel_cells",), "wormhole": ("xenoliths",),
        }
        moon_colors = ("#c0c0c0", "#9a8c98", "#e0e1dd", "#8ecae6")
        gov_map = {
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
        default_gov = gov_map.get(faction, "Colonial Republic")

        num_bodies = 6 if sys_id in ("sol", "betelgeuse") else 5
        for i in range(num_bodies):
            body_type, designation, market_arch, color, discovery = archetype_pool[
                (i + len(sys_id)) % len(archetype_pool)
            ]
            orbit_dist = 1.0 + (i + 1) * 1.35
            orbit_speed = 0.08 / (i + 1)
            is_station = body_type in ("orbital_station", "research_outpost")
            body_id = f"{sys_id}_body_{i+1}"
            body_name = f"{sys_name} {chr(65+i)} ({designation.title()})"

            moon_count = 0
            if body_type in ("gas_giant", "ringed_giant", "ice_giant", "super_earth"):
                moon_count = 1 + (i % 3)
            elif body_type in habitable_types:
                moon_count = 1 + (i % 2)
            moons = tuple(
                Moon(
                    id=f"{body_id}_moon_{j + 1}",
                    name=f"{body_name} Moon {j + 1}",
                    orbit_radius=0.10 + 0.07 * j,
                    radius_km=600.0 + 350.0 * ((i + j) % 5),
                    color=moon_colors[(i + j) % len(moon_colors)],
                    resource=("titanium" if j % 2 == 0 else "hydroponics") if body_type in habitable_types else "none",
                    landable=body_type in habitable_types and j == 0,
                )
                for j in range(moon_count)
            )

            body_hazards = ("pirate_activity",) if market_arch == "black_market" else ()
            rad_seed = 4000.0 + ((i + len(sys_id)) % 9) * 6500.0
            grav_seed = 0.65 + ((i * 3 + len(sys_id)) % 7) * 0.22
            jitter_seed = ((i * 5 + len(sys_id)) % 9) - 4
            phys = compute_scientific_planet_properties(
                body_type=body_type,
                spectral_type=spectral,
                orbit_radius_au=orbit_dist,
                rad_sample=rad_seed,
                grav_sample=grav_seed,
                temp_jitter=jitter_seed,
                hazards=body_hazards,
            )

            is_inhabited = is_station or body_type in habitable_types
            body_tech = world_tech_level(faction, body_type, market_arch)
            body_capacity = compute_population_capacity(
                body_type, float(phys["radius_km"]), float(phys["habitability"]), body_tech
            )
            if body_type in habitable_types or is_station:
                body_pop = initial_population(
                    body_type,
                    float(phys["radius_km"]),
                    float(phys["habitability"]),
                    body_tech,
                    faction,
                    market_arch,
                    is_station,
                )
                body_gov = "Science Directorate" if body_type == "research_outpost" else default_gov
            else:
                body_pop = 0
                body_gov = "None"

            bodies.append(
                CelestialBody(
                    id=body_id,
                    name=body_name,
                    body_type=body_type,
                    orbit_radius=orbit_dist,
                    orbit_speed=orbit_speed,
                    current_angle=(i * 1.6) % (2 * math.pi),
                    radius_km=float(phys["radius_km"]),
                    color=color,
                    hazards=body_hazards,
                    station_dockable=is_inhabited,
                    market_archetype=market_arch,
                    scan_completed=False,
                    scan_discovery=discovery,
                    gravity=float(phys["gravity"]),
                    atmosphere=str(phys["atmosphere"]),
                    temperature_c=int(phys["temperature_c"]),
                    resources=resource_map.get(body_type, ()),
                    moons=moons,
                    landable=body_type in habitable_types,
                    faction=faction if is_inhabited else "Unclaimed",
                    population=body_pop,
                    population_capacity=body_capacity,
                    tech_level=body_tech,
                    government=body_gov,
                    habitability=float(phys["habitability"]),
                )
            )

        special_objects = {
            "sol": ("dyson_sphere", "Helios Dyson Swarm", 0.06, "#ffd166", "Partial Dyson swarm: millions of collector panels and maintenance habitats harvesting the Sol primary.", True),
            "alpha_centauri": ("quantum_relay", "Quantum Relay Alpha", 2.4, "#7bf1a8", "Entanglement relay node carrying instant messages across the frontier.", True),
            "cygnus_x1": ("wormhole", "Cygnus Throat", 4.8, "#d0bfff", "Stable wormhole mouth bending local hyperspace lanes.", False),
            "cyclops": ("solar_collector", "Cyclops Collector Swarm", 3.1, "#ffd60a", "Orbital solar-panel lattice feeding the colony grid.", True),
        }
        if sys_id in special_objects:
            obj_type, obj_name, obj_orbit, obj_color, obj_discovery, obj_dock = special_objects[sys_id]
            obj_phys = compute_scientific_planet_properties(
                body_type=obj_type,
                spectral_type=spectral,
                orbit_radius_au=obj_orbit,
                rad_sample=6000.0,
                grav_sample=1.0,
                temp_jitter=0,
                hazards=(),
            )
            obj_tech = world_tech_level(faction, obj_type, "high_tech" if obj_dock else "none")
            # A swarm is a shell around the primary, not a planet orbiting at its own
            # radius: its physical radius is the collector-shell distance (0.25 AU).
            obj_radius = (
                0.25 * 149_600_000.0 if obj_type == "dyson_sphere" else float(obj_phys["radius_km"])
            )
            obj_population = (
                initial_population(
                    obj_type,
                    obj_radius,
                    float(obj_phys["habitability"]),
                    obj_tech,
                    faction,
                    "high_tech",
                    obj_dock,
                )
                if obj_dock
                else 0
            )
            obj_capacity = (
                compute_population_capacity(
                    obj_type, obj_radius, float(obj_phys["habitability"]), obj_tech
                )
                if obj_dock
                else 0
            )
            bodies.append(
                CelestialBody(
                    id=f"{sys_id}_{obj_type}",
                    name=obj_name,
                    body_type=obj_type,
                    orbit_radius=obj_orbit,
                    orbit_speed=0.045,
                    current_angle=1.7,
                    radius_km=obj_radius,
                    color=obj_color,
                    hazards=() if obj_type != "wormhole" else ("tidal_shear",),
                    station_dockable=obj_dock,
                    market_archetype="high_tech" if obj_dock else "none",
                    scan_completed=False,
                    scan_discovery=obj_discovery,
                    gravity=float(obj_phys["gravity"]),
                    atmosphere=str(obj_phys["atmosphere"]),
                    temperature_c=int(obj_phys["temperature_c"]),
                    resources=("microchips", "fuel_cells") if obj_type != "wormhole" else ("xenoliths",),
                    moons=(),
                    landable=obj_dock,
                    faction=faction if obj_dock else "Unclaimed",
                    population=obj_population,
                    population_capacity=obj_capacity,
                    tech_level=obj_tech,
                    government="Solar Engineering Directorate" if obj_type == "dyson_sphere" else ("Relay Authority" if obj_dock else "None"),
                    habitability=float(obj_phys["habitability"]),
                )
            )

        if sys_id in ("sol", "alpha_centauri", "cyclops"):
            ring_phys = compute_scientific_planet_properties(
                body_type="ring_world",
                spectral_type=spectral,
                orbit_radius_au=4.2,
                rad_sample=7200.0,
                grav_sample=1.0,
                temp_jitter=0,
                hazards=(),
            )
            ring_tech = world_tech_level(faction, "ring_world", "high_tech")
            ring_radius = float(ring_phys["radius_km"])
            ring_capacity = compute_population_capacity(
                "ring_world", ring_radius, float(ring_phys["habitability"]), ring_tech
            )
            bodies.append(
                CelestialBody(
                    id=f"{sys_id}_ring_world",
                    name=f"{sys_name} Ring World (Orbital Habitat)",
                    body_type="ring_world",
                    orbit_radius=4.2,
                    orbit_speed=0.035,
                    current_angle=0.9,
                    radius_km=ring_radius,
                    color="#c77dff",
                    hazards=(),
                    station_dockable=True,
                    market_archetype="high_tech",
                    scan_completed=False,
                    scan_discovery="Ancient ring megastructure with layered habitat bands and orbital shipyards.",
                    gravity=float(ring_phys["gravity"]),
                    atmosphere=str(ring_phys["atmosphere"]),
                    temperature_c=int(ring_phys["temperature_c"]),
                    resources=("microchips", "hydroponics"),
                    moons=(),
                    landable=True,
                    faction=faction,
                    population=initial_population(
                        "ring_world", ring_radius, float(ring_phys["habitability"]), ring_tech, faction, "high_tech", True
                    ),
                    population_capacity=ring_capacity,
                    tech_level=ring_tech,
                    government=gov_map.get(faction, "Ring Assembly"),
                    habitability=float(ring_phys["habitability"]),
                )
            )

        if sys_id in VOID_GATE_SYSTEM_IDS:
            bodies.append(black_hole_body(sys_id, sys_name))

        if not any(b.landable for b in bodies[1:]):
            landable_index = len(bodies) - 2 if bodies[-1].station_dockable else len(bodies) - 1
            savanna_phys = compute_scientific_planet_properties(
                body_type="savanna",
                spectral_type=spectral,
                orbit_radius_au=bodies[landable_index].orbit_radius,
                rad_sample=6200.0,
                grav_sample=1.0,
                temp_jitter=0,
                hazards=bodies[landable_index].hazards,
            )
            savanna_tech = world_tech_level(faction, "savanna", "agricultural")
            savanna_radius = float(savanna_phys["radius_km"])
            bodies[landable_index] = replace(
                bodies[landable_index],
                body_type="savanna",
                color="#90be6d",
                radius_km=savanna_radius,
                atmosphere=str(savanna_phys["atmosphere"]),
                temperature_c=int(savanna_phys["temperature_c"]),
                gravity=float(savanna_phys["gravity"]),
                habitability=float(savanna_phys["habitability"]),
                resources=("hydroponics", "medicines"),
                landable=True,
                station_dockable=True,
                scan_discovery="Temperate savanna world with a breathable atmosphere and fertile colony belts.",
                faction=faction,
                population=initial_population(
                    "savanna", savanna_radius, float(savanna_phys["habitability"]), savanna_tech, faction, "agricultural", True
                ),
                population_capacity=compute_population_capacity(
                    "savanna", savanna_radius, float(savanna_phys["habitability"]), savanna_tech
                ),
                tech_level=savanna_tech,
                government=default_gov,
            )

        if not any(b.station_dockable for b in bodies[1:]):
            station_phys = compute_scientific_planet_properties(
                body_type="orbital_station",
                spectral_type=spectral,
                orbit_radius_au=bodies[-1].orbit_radius,
            )
            station_tech = world_tech_level(faction, "orbital_station", "high_tech")
            station_radius = float(station_phys["radius_km"])
            bodies[-1] = replace(
                bodies[-1],
                body_type="orbital_station",
                color="#00f0ff",
                radius_km=station_radius,
                gravity=float(station_phys["gravity"]),
                atmosphere=str(station_phys["atmosphere"]),
                temperature_c=int(station_phys["temperature_c"]),
                habitability=float(station_phys["habitability"]),
                hazards=(),
                station_dockable=True,
                market_archetype="high_tech",
                scan_discovery="Orbital trade citadel servicing deep-space convoys.",
                faction=faction,
                population=initial_population(
                    "orbital_station", station_radius, float(station_phys["habitability"]), station_tech, faction, "high_tech", True
                ),
                population_capacity=compute_population_capacity(
                    "orbital_station", station_radius, float(station_phys["habitability"]), station_tech
                ),
                tech_level=station_tech,
                government=default_gov,
            )

        return bodies

    def _build_hyperlanes(
        self, systems: dict[str, StarSystem]
    ) -> dict[str, set[str]]:
        """Calculate hyperlane network ensuring a fully connected graph."""
        adj: dict[str, set[str]] = {k: set() for k in systems}
        sys_list = list(systems.values())

        # Connect closest neighbors
        for s1 in sys_list:
            distances = []
            for s2 in sys_list:
                if s1.id != s2.id:
                    dist = math.hypot(s1.x - s2.x, s1.y - s2.y)
                    distances.append((dist, s2.id))
            distances.sort()
            # Link at least the 2 nearest neighbors
            for _, target_id in distances[:2]:
                adj[s1.id].add(target_id)
                adj[target_id].add(s1.id)

        # Connect spanning links to avoid islands
        for i in range(len(sys_list) - 1):
            s_a = sys_list[i].id
            s_b = sys_list[i + 1].id
            adj[s_a].add(s_b)
            adj[s_b].add(s_a)

        return adj

    @staticmethod
    def get_market_quotes(
        system: StarSystem, body: CelestialBody
    ) -> list[MarketQuote]:
        """Compute localized commodity market pricing based on archetype and security."""
        quotes: list[MarketQuote] = []
        sec = system.security
        arch = body.market_archetype

        for comm in CANONICAL_COMMODITIES:
            base = comm.base_price
            supply = 50
            demand = 50

            # Archetype price adjustments
            if arch == "mining":
                if comm.id == "titanium":
                    supply = 120
                    demand = 20
                    base = int(base * 0.70)
                elif comm.id in ("hydroponics", "microchips"):
                    supply = 15
                    demand = 110
                    base = int(base * 1.35)
            elif arch == "agricultural":
                if comm.id == "hydroponics":
                    supply = 140
                    demand = 15
                    base = int(base * 0.65)
                elif comm.id in ("titanium", "medicines"):
                    supply = 20
                    demand = 100
                    base = int(base * 1.30)
            elif arch == "high_tech":
                if comm.id == "microchips":
                    supply = 110
                    demand = 25
                    base = int(base * 0.75)
                elif comm.id in ("titanium", "fuel_cells"):
                    supply = 30
                    demand = 120
                    base = int(base * 1.25)
            elif arch == "black_market":
                if comm.id == "xenoliths":
                    supply = 60
                    demand = 150
                    base = int(base * 1.60)
                elif comm.id == "medicines":
                    supply = 30
                    demand = 130
                    base = int(base * 1.40)

            # Security modifier (anarchy drives up fuel and risk premiums)
            if sec < 0.3:
                if comm.id in ("fuel_cells", "medicines"):
                    base = int(base * 1.25)

            # Spread calculation
            spread = max(2, int(base * 0.12))
            buy_price = base + spread
            sell_price = max(1, base - spread)

            quotes.append(
                MarketQuote(
                    commodity_id=comm.id,
                    name=comm.name,
                    category=comm.category,
                    buy_price=buy_price,
                    sell_price=sell_price,
                    supply=supply,
                    demand=demand,
                )
            )

        return quotes

    @staticmethod
    def get_random_anomaly(seed: int | None = None) -> AnomalyEncounter:
        """Select and instantiate a deep-space anomaly event."""
        rng = random.Random(seed)
        chosen = rng.choice(ANOMALIES_CATALOG)
        return AnomalyEncounter.from_dict(chosen)
