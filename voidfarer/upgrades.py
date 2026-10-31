"""Hardware upgrade catalog, fleet drone definitions, shipyard chassis, and equipment registry."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Sequence

from voidfarer.models import FleetDrone, ShipState, ShipUpgrade
from voidfarer.shipmods import calculate_ship_mod_bonuses


@dataclass(frozen=True)
class ShipChassis:
    """Pre-configured spacecraft hull chassis available for purchase at orbital shipyards."""

    id: str
    name: str
    ship_class: str
    cost: int
    max_hull: int
    max_shield: int
    max_fuel: int
    cargo_capacity: int
    description: str
    specialty_perk: str
    stat_bonus: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShipChassis:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            ship_class=str(data["ship_class"]),
            cost=int(data["cost"]),
            max_hull=int(data["max_hull"]),
            max_shield=int(data["max_shield"]),
            max_fuel=int(data["max_fuel"]),
            cargo_capacity=int(data["cargo_capacity"]),
            description=str(data["description"]),
            specialty_perk=str(data.get("specialty_perk", "")),
            stat_bonus=dict(data.get("stat_bonus", {})),
        )


CATALOG_CHASSIS: tuple[ShipChassis, ...] = (
    ShipChassis(
        id="vanguard_scout",
        name="Vanguard Explorer",
        ship_class="Corvette Scout",
        cost=0,
        max_hull=100,
        max_shield=100,
        max_fuel=60,
        cargo_capacity=40,
        description="Standard-issue deep space reconnaissance corvette. Balanced, agile, and fuel-efficient.",
        specialty_perk="Baseline Fleet Scout",
    ),
    ShipChassis(
        id="orion_hauler",
        name="Orion Heavy Freighter",
        ship_class="Bulk Merchant Hauler",
        cost=4500,
        max_hull=160,
        max_shield=120,
        max_fuel=80,
        cargo_capacity=120,
        description="Heavy-duty commercial freighter equipped with reinforced cargo hold bays and cargo compression fields.",
        specialty_perk="+15% Galactic Trade Margin & 120-unit Cargo Bay",
        stat_bonus={"trade_margin": 0.15},
    ),
    ShipChassis(
        id="solaris_gunship",
        name="Solaris Strike Frigate",
        ship_class="Tactical Missile Gunship",
        cost=5200,
        max_hull=140,
        max_shield=180,
        max_fuel=50,
        cargo_capacity=35,
        description="Military-grade patrol vessel outfitted with heavy deflector capacitor grids and forward laser mounts.",
        specialty_perk="+20 Tactical Combat Damage & 180 MW Shields",
        stat_bonus={"combat_damage": 20.0},
    ),
    ShipChassis(
        id="chronos_explorer",
        name="Chronos Deep-Space Cruiser",
        ship_class="Long-Range Science Vessel",
        cost=4800,
        max_hull=110,
        max_shield=140,
        max_fuel=120,
        cargo_capacity=60,
        description="Specialized scientific survey cruiser featuring high-capacity hydrogen fuel reserves and deep astrometric sensors.",
        specialty_perk="120 Fuel Capacity & +50% Science Scan Bounties",
        stat_bonus={"scan_mult": 1.5},
    ),
    ShipChassis(
        id="archon_dreadnought",
        name="Archon Sovereign Dreadnought",
        ship_class="Command Battlecruiser",
        cost=12000,
        max_hull=250,
        max_shield=250,
        max_fuel=100,
        cargo_capacity=80,
        description="Pinnacle naval flagship constructed with reinforced neutronium bulkheads and sovereign hardlight shields.",
        specialty_perk="250 Hull & 250 Shields, +35 Combat Damage, Supreme Fleet Asset",
        stat_bonus={"combat_damage": 35.0},
    ),
)

CHASSIS_MAP: dict[str, ShipChassis] = {c.id: c for c in CATALOG_CHASSIS}


CATALOG_UPGRADES: tuple[ShipUpgrade, ...] = (
    # --- Engines ---
    ShipUpgrade(
        id="warp_booster_mk1",
        name="Hyperdrive Booster MK-I",
        slot="engines",
        cost=450,
        description="Sub-light quantum accelerator cutting hyperlane jump fuel burn by 20%.",
        stat_bonus={"fuel_efficiency": 0.20},
    ),
    ShipUpgrade(
        id="warp_booster_mk2",
        name="Hyperdrive Booster MK-II",
        slot="engines",
        cost=850,
        description="Quantum field accelerator reducing hyperlane jump fuel burn by 35%.",
        stat_bonus={"fuel_efficiency": 0.35},
    ),
    ShipUpgrade(
        id="warp_booster_mk3",
        name="Hyperdrive Warp Turbine MK-III",
        slot="engines",
        cost=1800,
        description="Advanced tachyon warp turbine halving hyperlane transit fuel burn by 50%.",
        stat_bonus={"fuel_efficiency": 0.50},
    ),
    ShipUpgrade(
        id="sublight_afterburners",
        name="Ion Sub-Light Afterburners",
        slot="engines",
        cost=900,
        description="Vectoring thruster injectors delivering +15% tactical evasion against incoming pirate fire.",
        stat_bonus={"evasion": 0.15},
    ),

    # --- Shields ---
    ShipUpgrade(
        id="deflector_array_mk1",
        name="Deflector Array MK-I",
        slot="shields",
        cost=500,
        description="Standard energy barrier augmenting shield capacity by +20 MW.",
        stat_bonus={"max_shield": 20.0},
    ),
    ShipUpgrade(
        id="tachyon_shield_matrix",
        name="Tachyon Shield Matrix",
        slot="shields",
        cost=1100,
        description="High-frequency deflector array augmenting shield capacity by +40 MW.",
        stat_bonus={"max_shield": 40.0},
    ),
    ShipUpgrade(
        id="hardlight_barrier_mk3",
        name="Hardlight Aegis Barrier MK-III",
        slot="shields",
        cost=2200,
        description="Military-grade solid light deflector matrix expanding shield capacity by +80 MW.",
        stat_bonus={"max_shield": 80.0},
    ),
    ShipUpgrade(
        id="reactive_shield_booster",
        name="Reactive Shield Regenerator",
        slot="shields",
        cost=1300,
        description="Capacitor cycling system accelerating passive out-of-combat shield recharge by +5 MW per tick.",
        stat_bonus={"shield_regen": 5.0},
    ),

    # --- Sensors ---
    ShipUpgrade(
        id="astrometric_surveyor_mk1",
        name="Astrometric Surveyor MK-I",
        slot="sensors",
        cost=400,
        description="Orbital radio-telescope array increasing planetary scan bounties by +25%.",
        stat_bonus={"scan_mult": 1.25},
    ),
    ShipUpgrade(
        id="deep_core_scanner",
        name="Deep-Core Astrometric Array",
        slot="sensors",
        cost=750,
        description="Sub-space sensor array boosting planetary scan science bounties by +50%.",
        stat_bonus={"scan_mult": 1.5},
    ),
    ShipUpgrade(
        id="tachyon_resonance_suite_mk3",
        name="Tachyon Resonance Suite MK-III",
        slot="sensors",
        cost=1900,
        description="Quantum entanglement detector multiplying scan bounties by +120% and Precursor relic chance by +15%.",
        stat_bonus={"scan_mult": 2.2, "relic_find": 0.15},
    ),

    # --- Weapons ---
    ShipUpgrade(
        id="pulse_cannon_array",
        name="Coherent Laser Strike Battery",
        slot="weapons",
        cost=950,
        description="Focused laser battery delivering +15 hull damage in tactical combat.",
        stat_bonus={"combat_damage": 15.0},
    ),
    ShipUpgrade(
        id="plasma_torpedo_mk2",
        name="Heavy Plasma Torpedo Launcher",
        slot="weapons",
        cost=1500,
        description="Thermal plasma projectile tubes unleashing +30 kinetic damage in space engagements.",
        stat_bonus={"combat_damage": 30.0},
    ),
    ShipUpgrade(
        id="tachyon_lance_mk3",
        name="Tachyon Lance Array MK-III",
        slot="weapons",
        cost=2500,
        description="Capital ship relativistic beam array dealing devastating +55 direct damage.",
        stat_bonus={"combat_damage": 55.0},
    ),

    # --- Cargo ---
    ShipUpgrade(
        id="cargo_expansion_mk1",
        name="Reinforced Cargo Framework",
        slot="cargo",
        cost=350,
        description="Structural hold expansion adding +10 units of safe cargo capacity.",
        stat_bonus={"cargo_capacity": 10.0},
    ),
    ShipUpgrade(
        id="subspace_cargo_pods",
        name="Sub-Space Expanded Cargo Hold",
        slot="cargo",
        cost=600,
        description="Dimensional compression cargo pods expanding hold capacity by +20 units.",
        stat_bonus={"cargo_capacity": 20.0},
    ),
    ShipUpgrade(
        id="dimensional_vault_mk3",
        name="Dimensional Compression Vault",
        slot="cargo",
        cost=1600,
        description="Spatial folding bay granting +50 units of expanded cargo hold capacity.",
        stat_bonus={"cargo_capacity": 50.0},
    ),

    # --- Hull & Armor ---
    ShipUpgrade(
        id="composite_armor_mk1",
        name="Composite Armor Plating",
        slot="hull",
        cost=500,
        description="Layered ceramic-titanium hull plating increasing maximum hull integrity by +25 points.",
        stat_bonus={"max_hull": 25.0},
    ),
    ShipUpgrade(
        id="reactive_armor_mk2",
        name="Reactive Nanite Armor",
        slot="hull",
        cost=1200,
        description="Adaptive nanite alloy hull plating expanding maximum hull integrity by +55 points.",
        stat_bonus={"max_hull": 55.0},
    ),
    ShipUpgrade(
        id="neutronium_bulkhead_mk3",
        name="Neutronium Reinforced Bulkhead",
        slot="hull",
        cost=2600,
        description="Degenerate matter armor framework adding +100 points to maximum ship hull integrity.",
        stat_bonus={"max_hull": 100.0},
    ),

    # --- Utility ---
    ShipUpgrade(
        id="automated_repair_bay",
        name="Automated Nanite Repair Bay",
        slot="utility",
        cost=1400,
        description="Autonomous repair drones that gradually repair +2 hull points each simulation tick.",
        stat_bonus={"hull_repair_per_tick": 2.0},
    ),
    ShipUpgrade(
        id="ecm_scrambler_suite",
        name="Tactical ECM Scrambler Suite",
        slot="utility",
        cost=950,
        description="Electronic countermeasure emitter reducing pirate and hostile encounter chance by 40%.",
        stat_bonus={"pirate_evasion": 0.40},
    ),
    ShipUpgrade(
        id="solar_panel_array",
        name="Photovoltaic Solar Panel Array",
        slot="utility",
        cost=1200,
        description="Deployable solar panels supplement reactor output and cooling in well-lit systems.",
        stat_bonus={"reactor_output": 0.08, "reactor_cooling": 3.0},
    ),
)

UPGRADE_MAP: dict[str, ShipUpgrade] = {u.id: u for u in CATALOG_UPGRADES}

CATALOG_DRONE_TEMPLATES = {
    "mining": {
        "name": "Automated Mining Drone",
        "type": "mining",
        "cost": 650,
        "description": "Extracts raw titanium and minerals in assigned star system each flight cycle.",
    },
    "scout": {
        "name": "Deep-Space Recon Drone",
        "type": "scout",
        "cost": 500,
        "description": "Monitors spatial harmonics and yields steady research credits.",
    },
    "combat_escort": {
        "name": "Vanguard Escort Frigate",
        "type": "combat_escort",
        "cost": 1300,
        "description": "Heavy automated gunboat providing point-defense against pirate ambushes.",
    },
}


def get_upgrade(upgrade_id: str) -> ShipUpgrade | None:
    return UPGRADE_MAP.get(upgrade_id)


def get_available_upgrades(installed: dict[str, str]) -> list[ShipUpgrade]:
    """Return upgrades that have not yet been installed."""
    installed_ids = set(installed.values())
    return [u for u in CATALOG_UPGRADES if u.id not in installed_ids]


def get_chassis(chassis_id: str) -> ShipChassis | None:
    return CHASSIS_MAP.get(chassis_id)


def get_chassis_for_ship_class(ship_class: str) -> ShipChassis | None:
    """Resolve the commissioned chassis from the ship class recorded in the save."""
    return next((c for c in CATALOG_CHASSIS if c.ship_class == ship_class), None)


def calculate_equipment_bonuses(ship: ShipState) -> dict[str, float]:
    """Aggregate equipped module and chassis stat bonuses into effective multipliers.

    Multiplicative stats (fuel savings, scan yield) multiply each source; additive
    stats (combat damage, evasion, regeneration, ECM, trade margin) sum. The result
    never changes persisted state and is safe to call under the engine lock.
    """
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

    sources: list[dict[str, float]] = []
    for upgrade_id in ship.equipped_upgrades.values():
        upgrade = get_upgrade(upgrade_id)
        if upgrade:
            sources.append(upgrade.stat_bonus)
    chassis = get_chassis_for_ship_class(ship.ship_class)
    if chassis:
        sources.append(chassis.stat_bonus)

    for stats in sources:
        for stat, value in stats.items():
            if stat == "fuel_efficiency":
                bonuses["fuel_efficiency"] *= max(0.0, 1.0 - float(value))
            elif stat == "scan_mult":
                bonuses["scan_mult"] *= float(value)
            elif stat in bonuses:
                bonuses[stat] += float(value)

    structural = calculate_ship_mod_bonuses(ship.ship_mods)
    for stat, value in structural.items():
        if stat == "fuel_efficiency":
            bonuses["fuel_efficiency"] *= float(value)
        elif stat == "scan_mult":
            bonuses["scan_mult"] *= float(value)
        elif stat in bonuses:
            bonuses[stat] += float(value)

    bonuses["fuel_efficiency"] = max(0.10, bonuses["fuel_efficiency"])
    bonuses["evasion"] = min(0.90, max(-0.90, bonuses["evasion"]))
    bonuses["pirate_evasion"] = min(0.90, max(0.0, bonuses["pirate_evasion"]))
    bonuses["drone_yield"] = max(0.0, bonuses["drone_yield"])
    return bonuses


def get_available_chassis(current_chassis_id: str) -> list[ShipChassis]:
    """Return ship chassis available for purchase (excluding current ship)."""
    return [c for c in CATALOG_CHASSIS if c.id != current_chassis_id]


def get_sell_value(upgrade_id: str) -> int:
    """Calculate credit trade-in value when selling or uninstalling a hardware module (60% of base cost)."""
    up = get_upgrade(upgrade_id)
    if not up:
        return 0
    return max(50, int(up.cost * 0.60))
