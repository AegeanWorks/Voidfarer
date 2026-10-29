"""Structural ship modifications: permanent refits with explicit trade-offs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SHIP_MOD_SLOTS: tuple[str, ...] = ("frame", "reactor_core", "thermal", "drive", "ops")

SHIP_MOD_SLOT_LABELS: dict[str, str] = {
    "frame": "Frame & Armor",
    "reactor_core": "Reactor Core",
    "thermal": "Thermal Control",
    "drive": "Drive & Thrusters",
    "ops": "Operations Suite",
}

# The silhouette slot boxes are 48px squares, so a full label clips to "Therm...".
# These three-letter codes fit; the full label stays in the tooltip and aria-label.
SHIP_MOD_SLOT_CODES: dict[str, str] = {
    "frame": "FRM",
    "reactor_core": "CORE",
    "thermal": "THM",
    "drive": "DRV",
    "ops": "OPS",
}


@dataclass(frozen=True)
class ShipMod:
    """A permanent structural refit available at orbital drydocks."""

    id: str
    name: str
    slot: str
    cost: int
    description: str
    effects: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CATALOG_SHIP_MODS: tuple[ShipMod, ...] = (
    ShipMod(
        id="reinforced_spine",
        name="Reinforced Structural Spine",
        slot="frame",
        cost=1400,
        description="Load-bearing truss refit: +60 max hull, but 10 fewer cargo volume units.",
        effects={"max_hull": 60.0, "cargo_capacity": -10.0},
    ),
    ShipMod(
        id="expanded_hangar",
        name="Expanded Hangar Deck",
        slot="frame",
        cost=1600,
        description="Pressurized modular hangar: +30 cargo capacity at the cost of 20 max hull.",
        effects={"cargo_capacity": 30.0, "max_hull": -20.0},
    ),
    ShipMod(
        id="ablative_lattice",
        name="Ablative Hull Lattice",
        slot="frame",
        cost=2100,
        description="Sacrificial outer lattice: +45 hull and +0.10 evasion, but 8% heavier fuel burn.",
        effects={"max_hull": 45.0, "evasion": 0.10, "fuel_efficiency": -0.08},
    ),
    ShipMod(
        id="overcharged_core",
        name="Overcharged Fusion Core",
        slot="reactor_core",
        cost=2400,
        description="Magnetic confinement overdrive: +25% reactor output, but +40% heat generation and -10 heat capacity.",
        effects={"reactor_output": 0.25, "heat_generation": 0.40, "heat_capacity": -10.0},
    ),
    ShipMod(
        id="efficient_core",
        name="Efficient Tokamak Core",
        slot="reactor_core",
        cost=1800,
        description="High-efficiency ignition: +10% output and -20% heat generation, but -15 max shield.",
        effects={"reactor_output": 0.10, "heat_generation": -0.20, "max_shield": -15.0},
    ),
    ShipMod(
        id="cryo_loop",
        name="Cryogenic Coolant Loop",
        slot="thermal",
        cost=1500,
        description="Deep cryo heat exchangers: +10 cooling and +25 max heat, but -0.05 evasion.",
        effects={"reactor_cooling": 10.0, "heat_capacity": 25.0, "evasion": -0.05},
    ),
    ShipMod(
        id="thermal_shunt",
        name="Emergency Thermal Shunt",
        slot="thermal",
        cost=1100,
        description="Expendable heat sinks: +18 max heat and +5 cooling, but -15 cargo capacity.",
        effects={"heat_capacity": 18.0, "reactor_cooling": 5.0, "cargo_capacity": -15.0},
    ),
    ShipMod(
        id="vector_thrusters",
        name="Vector Ion Thrusters",
        slot="drive",
        cost=1700,
        description="Omni-directional thruster pods: +0.18 evasion and +10% jump efficiency, but -10 hull.",
        effects={"evasion": 0.18, "fuel_efficiency": 0.10, "max_hull": -10.0},
    ),
    ShipMod(
        id="mass_driver_tuning",
        name="Mass Driver Tuning",
        slot="drive",
        cost=1900,
        description="Recoil-compensated rails: +25 combat damage, but -0.10 evasion.",
        effects={"combat_damage": 25.0, "evasion": -0.10},
    ),
    ShipMod(
        id="deep_survey_suite",
        name="Deep Survey Suite",
        slot="ops",
        cost=2000,
        description="Cryogenic telescope and spectrometer bay: +45% scan yield, but -15 max shield.",
        effects={"scan_mult": 1.45, "max_shield": -15.0},
    ),
    ShipMod(
        id="fleet_control_nexus",
        name="Fleet Control Nexus",
        slot="ops",
        cost=2200,
        description="Dedicated drone command uplink: +20% drone yield and +15% trade margin, but -20 hull.",
        effects={"drone_yield": 0.20, "trade_margin": 0.15, "max_hull": -20.0},
    ),
    ShipMod(
        id="salvage_processor",
        name="Salvage Processor Array",
        slot="ops",
        cost=1300,
        description="Automated wreck processing: +12% relic find chance and +10% scan yield, but -5 cooling.",
        effects={"relic_find": 0.12, "scan_mult": 1.10, "reactor_cooling": -5.0},
    ),
)

SHIP_MOD_MAP: dict[str, ShipMod] = {m.id: m for m in CATALOG_SHIP_MODS}


def get_ship_mod(mod_id: str) -> ShipMod | None:
    return SHIP_MOD_MAP.get(mod_id)


def get_available_ship_mods(installed: dict[str, str]) -> list[ShipMod]:
    installed_ids = set(installed.values())
    return [m for m in CATALOG_SHIP_MODS if m.id not in installed_ids]


def get_ship_mod_sell_value(mod_id: str) -> int:
    mod = get_ship_mod(mod_id)
    if not mod:
        return 0
    return max(100, int(mod.cost * 0.50))


def calculate_ship_mod_bonuses(ship_mods: dict[str, str]) -> dict[str, float]:
    """Aggregate structural modification effects into the common bonus keyspace."""
    bonuses: dict[str, float] = {
        "fuel_efficiency": 1.0,
        "scan_mult": 1.0,
        "relic_find": 0.0,
        "combat_damage": 0.0,
        "evasion": 0.0,
        "shield_regen": 0.0,
        "pirate_evasion": 0.0,
        "trade_margin": 0.0,
        "max_hull": 0.0,
        "max_shield": 0.0,
        "cargo_capacity": 0.0,
        "hull_repair_per_tick": 0.0,
        "reactor_output": 0.0,
        "reactor_cooling": 0.0,
        "heat_capacity": 0.0,
        "heat_generation": 0.0,
        "reactor_integrity": 0.0,
        "drone_yield": 0.0,
    }
    for mod_id in ship_mods.values():
        mod = get_ship_mod(mod_id)
        if not mod:
            continue
        for stat, value in mod.effects.items():
            if stat == "fuel_efficiency":
                bonuses["fuel_efficiency"] *= max(0.0, 1.0 - float(value))
            elif stat == "scan_mult":
                bonuses["scan_mult"] *= float(value)
            elif stat in bonuses:
                bonuses[stat] += float(value)
    bonuses["fuel_efficiency"] = max(0.10, bonuses["fuel_efficiency"])
    bonuses["evasion"] = min(0.90, max(-0.90, bonuses["evasion"]))
    bonuses["reactor_output"] = max(-0.60, bonuses["reactor_output"])
    bonuses["heat_generation"] = max(-0.80, bonuses["heat_generation"])
    return bonuses


def slot_label(slot: str) -> str:
    return SHIP_MOD_SLOT_LABELS.get(slot, slot.replace("_", " ").title())


def slot_code(slot: str) -> str:
    """Short, always-fitting code for the 48px silhouette case."""
    return SHIP_MOD_SLOT_CODES.get(slot, slot.replace("_", "")[:4].upper())
