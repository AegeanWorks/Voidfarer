"""Domain state models and frozen data transfer objects for VoidFarer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any


@dataclass(frozen=True)
class Moon:
    """Natural satellite orbiting a planet."""

    id: str
    name: str
    orbit_radius: float
    radius_km: float
    color: str
    resource: str = "none"
    landable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Moon:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            orbit_radius=float(data.get("orbit_radius", 0.1)),
            radius_km=float(data.get("radius_km", 1000.0)),
            color=str(data.get("color", "#c0c0c0")),
            resource=str(data.get("resource", "none")),
            landable=bool(data.get("landable", False)),
        )


@dataclass(frozen=True)
class CelestialBody:
    """Represents a planetary, stellar, or orbital body in a star system."""

    id: str
    name: str
    body_type: str  # 'star', 'terrestrial', 'gas_giant', 'oceanic', 'volcanic', 'orbital_station', 'asteroid_belt', 'desert_world', 'ice_world', 'lava_world', 'ringed_giant', 'research_outpost'
    orbit_radius: float  # In Astronomical Units (AU)
    orbit_speed: float = 0.05  # Orbital angular velocity
    current_angle: float = 0.0  # Current orbital phase (radians)
    radius_km: float = 6000.0
    color: str = "#00f0ff"  # Hex display color
    hazards: tuple[str, ...] = ()
    station_dockable: bool = False
    market_archetype: str = "none"  # 'none', 'mining', 'agricultural', 'industrial', 'high_tech', 'black_market'
    scan_completed: bool = False
    scan_discovery: str = ""
    gravity: float = 1.0
    atmosphere: str = "none"
    temperature_c: int = 0
    resources: tuple[str, ...] = ()
    moons: tuple[Moon, ...] = ()
    landable: bool = False
    faction: str = "Unclaimed"
    population: int = 0
    government: str = "None"
    habitability: float = 0.0
    salvage_claimed: bool = False
    volatile_tapped: int = 0
    volatile_recharge_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CelestialBody:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            body_type=str(data["body_type"]),
            orbit_radius=float(data["orbit_radius"]),
            orbit_speed=float(data.get("orbit_speed", 0.05)),
            current_angle=float(data.get("current_angle", 0.0)),
            radius_km=float(data.get("radius_km", 6000.0)),
            color=str(data.get("color", "#00f0ff")),
            hazards=tuple(data.get("hazards", ())),
            station_dockable=bool(data.get("station_dockable", False)),
            market_archetype=str(data.get("market_archetype", "none")),
            scan_completed=bool(data.get("scan_completed", False)),
            scan_discovery=str(data.get("scan_discovery", "")),
            gravity=float(data.get("gravity", 1.0)),
            atmosphere=str(data.get("atmosphere", "none")),
            temperature_c=int(data.get("temperature_c", 0)),
            resources=tuple(data.get("resources", ())),
            moons=tuple(Moon.from_dict(m) for m in data.get("moons", ())),
            landable=bool(data.get("landable", str(data.get("body_type", "")) in {"terrestrial", "oceanic", "savanna", "tundra"})),
            faction=str(data.get("faction", "Unclaimed")),
            population=int(data.get("population", 0)),
            government=str(data.get("government", "None")),
            habitability=float(data.get("habitability", 0.0)),
            salvage_claimed=bool(data.get("salvage_claimed", False)),
            volatile_tapped=max(0, int(data.get("volatile_tapped", 0))),
            volatile_recharge_tick=max(0, int(data.get("volatile_recharge_tick", 0))),
        )


@dataclass(frozen=True)
class MapModifier:
    """Persistent environmental condition that reshapes local sector simulation."""

    id: str
    name: str
    category: str  # 'hazard', 'anomaly', 'commerce', 'phenomenon'
    description: str
    effects: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MapModifier:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            category=str(data.get("category", "phenomenon")),
            description=str(data.get("description", "")),
            effects={str(k): float(v) for k, v in data.get("effects", {}).items()},
        )


@dataclass(frozen=True)
class StarSystem:
    """Represents a star system with celestial bodies and hyperlane links."""

    id: str
    name: str
    seed: int
    x: float
    y: float
    spectral_type: str  # 'O', 'B', 'A', 'F', 'G', 'K', 'M', 'Neutron', 'BlackHole'
    color: str
    security: float  # 0.0 (anarchy) to 1.0 (high-sec)
    faction: str
    bodies: tuple[CelestialBody, ...]
    connections: tuple[str, ...] = ()
    dominant_corp: str | None = None
    modifiers: tuple[MapModifier, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "seed": self.seed,
            "x": self.x,
            "y": self.y,
            "spectral_type": self.spectral_type,
            "color": self.color,
            "security": self.security,
            "faction": self.faction,
            "bodies": [b.to_dict() for b in self.bodies],
            "connections": list(self.connections),
            "dominant_corp": self.dominant_corp,
            "modifiers": [m.to_dict() for m in self.modifiers],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StarSystem:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            seed=int(data["seed"]),
            x=float(data["x"]),
            y=float(data["y"]),
            spectral_type=str(data["spectral_type"]),
            color=str(data.get("color", "#ffffff")),
            security=float(data.get("security", 0.5)),
            faction=str(data.get("faction", "Independent")),
            bodies=tuple(CelestialBody.from_dict(b) for b in data.get("bodies", [])),
            connections=tuple(data.get("connections", ())),
            dominant_corp=data.get("dominant_corp"),
            modifiers=tuple(MapModifier.from_dict(m) for m in data.get("modifiers", ())),
        )


@dataclass(frozen=True)
class Commodity:
    """Trade goods and planetary resources."""

    id: str
    name: str
    category: str  # 'raw', 'industrial', 'medical', 'tech', 'contraband'
    base_price: int
    volatility: float
    volume: int = 1


@dataclass(frozen=True)
class MarketQuote:
    """Current price quotation for a commodity at a local market."""

    commodity_id: str
    name: str
    category: str
    buy_price: int
    sell_price: int
    supply: int
    demand: int


@dataclass(frozen=True)
class ShipPower:
    """Reactor power distribution across primary subsystems (sum <= 100)."""

    engines: int = 25
    shields: int = 25
    sensors: int = 25
    weapons: int = 25

    def __post_init__(self) -> None:
        total = self.engines + self.shields + self.sensors + self.weapons
        if total > 100:
            raise ValueError(f"Total allocated power ({total}%) exceeds reactor capacity (100%)")
        if any(p < 0 for p in (self.engines, self.shields, self.sensors, self.weapons)):
            raise ValueError("Subsystem power cannot be negative")

    def to_dict(self) -> dict[str, int]:
        return {
            "engines": self.engines,
            "shields": self.shields,
            "sensors": self.sensors,
            "weapons": self.weapons,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShipPower:
        return cls(
            engines=int(data.get("engines", 25)),
            shields=int(data.get("shields", 25)),
            sensors=int(data.get("sensors", 25)),
            weapons=int(data.get("weapons", 25)),
        )


@dataclass(frozen=True)
class AnomalyChoice:
    """Player decision branch for resolving a deep-space anomaly encounter."""

    choice_id: str
    text: str
    required_power: str  # 'engines', 'shields', 'sensors', 'weapons', 'none'
    min_power_threshold: int
    outcome_text: str
    hull_delta: int = 0
    credits_delta: int = 0
    fuel_delta: int = 0
    cargo_reward: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnomalyChoice:
        return cls(
            choice_id=str(data["choice_id"]),
            text=str(data["text"]),
            required_power=str(data.get("required_power", "none")),
            min_power_threshold=int(data.get("min_power_threshold", 0)),
            outcome_text=str(data["outcome_text"]),
            hull_delta=int(data.get("hull_delta", 0)),
            credits_delta=int(data.get("credits_delta", 0)),
            fuel_delta=int(data.get("fuel_delta", 0)),
            cargo_reward=dict(data.get("cargo_reward", {})),
        )


@dataclass(frozen=True)
class AnomalyEncounter:
    """Procedurally triggered deep-space anomaly event."""

    id: str
    title: str
    description: str
    severity: str  # 'minor', 'moderate', 'critical'
    choices: tuple[AnomalyChoice, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "choices": [c.to_dict() for c in self.choices],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnomalyEncounter:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data["description"]),
            severity=str(data.get("severity", "moderate")),
            choices=tuple(AnomalyChoice.from_dict(c) for c in data.get("choices", [])),
        )


@dataclass(frozen=True)
class FleetDrone:
    """Autonomous fleet asset deployed to star systems for mining, scouting, or escort."""

    id: str
    name: str
    drone_type: str  # 'mining', 'scout', 'combat_escort'
    assigned_system_id: str
    status: str = "harvesting"  # 'harvesting', 'patrolling', 'idle'
    cargo_accumulated: int = 0
    credits_accumulated: int = 0
    level: int = 1
    efficiency: float = 1.0
    integrity: int = 100
    sorties: int = 0
    specialty: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FleetDrone:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            drone_type=str(data["drone_type"]),
            assigned_system_id=str(data.get("assigned_system_id", "sol")),
            status=str(data.get("status", "harvesting")),
            cargo_accumulated=int(data.get("cargo_accumulated", 0)),
            credits_accumulated=int(data.get("credits_accumulated", 0)),
            level=int(data.get("level", 1)),
            efficiency=float(data.get("efficiency", 1.0)),
            integrity=int(data.get("integrity", 100)),
            sorties=int(data.get("sorties", 0)),
            specialty=str(data.get("specialty", "")),
        )


@dataclass(frozen=True)
class AICaptain:
    """Persistent autonomous captain that trades, hails, allies, or fights."""

    id: str
    name: str
    archetype: str  # 'trader', 'mercenary', 'ally', 'pirate'
    system_id: str
    credits: int
    cargo: dict[str, int] = field(default_factory=dict)
    standing: int = 0
    trust: int = 0
    ally: bool = False
    hired: bool = False
    hull: int = 100
    max_hull: int = 100
    damage: int = 10
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AICaptain:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            archetype=str(data.get("archetype", "trader")),
            system_id=str(data.get("system_id", "sol")),
            credits=int(data.get("credits", 1000)),
            cargo=dict(data.get("cargo", {})),
            standing=int(data.get("standing", 0)),
            trust=int(data.get("trust", 0)),
            ally=bool(data.get("ally", False)),
            hired=bool(data.get("hired", False)),
            hull=int(data.get("hull", 100)),
            max_hull=int(data.get("max_hull", 100)),
            damage=int(data.get("damage", 10)),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True)
class Depot:
    """System-local cargo depot that can hold and sell commodities."""

    id: str
    name: str
    system_id: str
    capacity: int = 200
    cargo: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Depot:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            system_id=str(data.get("system_id", "sol")),
            capacity=int(data.get("capacity", 200)),
            cargo=dict(data.get("cargo", {})),
        )


@dataclass(frozen=True)
class MessageChoice:
    """One branch of an interactive message-tree node."""

    id: str
    label: str
    description: str = ""
    outcome: dict[str, Any] = field(default_factory=dict)
    next_node_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageChoice:
        return cls(
            id=str(data["id"]),
            label=str(data.get("label", data["id"])),
            description=str(data.get("description", "")),
            outcome={str(k): v for k, v in data.get("outcome", {}).items()},
            next_node_id=data.get("next_node_id"),
        )


@dataclass(frozen=True)
class QuantumMessage:
    """Intergalactic quantum-encrypted message stored in the ship inbox."""

    id: str
    sender: str
    recipient: str
    subject: str
    body: str
    tick: int = 0
    read: bool = False
    tree_id: str | None = None
    node_id: str | None = None
    choices: tuple[MessageChoice, ...] = ()
    resolved_choice: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["choices"] = [c.to_dict() for c in self.choices]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuantumMessage:
        return cls(
            id=str(data["id"]),
            sender=str(data.get("sender", "Unknown")),
            recipient=str(data.get("recipient", "Commander")),
            subject=str(data.get("subject", "")),
            body=str(data.get("body", "")),
            tick=int(data.get("tick", 0)),
            read=bool(data.get("read", False)),
            tree_id=data.get("tree_id"),
            node_id=data.get("node_id"),
            choices=tuple(MessageChoice.from_dict(c) for c in data.get("choices", ())),
            resolved_choice=data.get("resolved_choice"),
        )


@dataclass(frozen=True)
class ShipUpgrade:
    """Modular hardware upgrade installed on flagship."""

    id: str
    name: str
    slot: str  # 'engines', 'shields', 'sensors', 'weapons', 'cargo'
    cost: int
    description: str
    stat_bonus: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShipUpgrade:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            slot=str(data["slot"]),
            cost=int(data["cost"]),
            description=str(data["description"]),
            stat_bonus=dict(data.get("stat_bonus", {})),
        )


@dataclass(frozen=True)
class CombatEncounter:
    """Hostile deep-space pirate or automated intercept encounter."""

    id: str
    enemy_name: str
    enemy_class: str
    enemy_hull: int
    enemy_max_hull: int
    enemy_damage: int
    bounty_credits: int
    salvage_commodity: str = "titanium"
    enemy_shield: int = 0
    enemy_max_shield: int = 0
    faction_id: str = "outlaw_corsairs"
    special_ability: str = "none"
    ability_cooldown: int = 0
    telegraphed_action: str = "Hostile weapons powering up"
    ai_profile: str = "aggressive"
    enemy_intent: str = "fire"
    archetype_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CombatEncounter:
        return cls(
            id=str(data["id"]),
            enemy_name=str(data["enemy_name"]),
            enemy_class=str(data["enemy_class"]),
            enemy_hull=int(data["enemy_hull"]),
            enemy_max_hull=int(data["enemy_max_hull"]),
            enemy_damage=int(data["enemy_damage"]),
            bounty_credits=int(data["bounty_credits"]),
            salvage_commodity=str(data.get("salvage_commodity", "titanium")),
            enemy_shield=int(data.get("enemy_shield", 0)),
            enemy_max_shield=int(data.get("enemy_max_shield", 0)),
            faction_id=str(data.get("faction_id", "outlaw_corsairs")),
            special_ability=str(data.get("special_ability", "none")),
            ability_cooldown=int(data.get("ability_cooldown", 0)),
            telegraphed_action=str(data.get("telegraphed_action", "Hostile weapons powering up")),
            ai_profile=str(data.get("ai_profile", "aggressive")),
            enemy_intent=str(data.get("enemy_intent", "fire")),
            archetype_id=str(data.get("archetype_id", "")),
        )


@dataclass(frozen=True)
class BountyContract:
    """Dynamic mission contract leveraging Zeigarnik task completion tension."""

    id: str
    title: str
    description: str
    category: str  # 'combat', 'mining', 'exploration', 'trade'
    target_count: int
    current_count: int = 0
    reward_credits: int = 500
    reward_xp: int = 150
    reward_relic_tier: str | None = None
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BountyContract:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data["description"]),
            category=str(data.get("category", "exploration")),
            target_count=int(data.get("target_count", 1)),
            current_count=int(data.get("current_count", 0)),
            reward_credits=int(data.get("reward_credits", 500)),
            reward_xp=int(data.get("reward_xp", 150)),
            reward_relic_tier=data.get("reward_relic_tier"),
            completed=bool(data.get("completed", False)),
        )


@dataclass(frozen=True)
class PrecursorRelic:
    """Ancient artifact dropped via variable ratio schedule with passive multipliers."""

    id: str
    name: str
    rarity: str  # 'common', 'rare', 'epic', 'legendary'
    description: str
    passive_stat: str  # 'laser_dmg', 'shield_cap', 'fuel_efficiency', 'trade_margin', 'scanner_bounty'
    stat_multiplier: float  # e.g. 0.15 for +15%
    discovered_at_system: str = "sol"
    bonuses: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PrecursorRelic:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            rarity=str(data.get("rarity", "common")),
            description=str(data.get("description", "")),
            passive_stat=str(data.get("passive_stat", "laser_dmg")),
            stat_multiplier=float(data.get("stat_multiplier", 0.05)),
            discovered_at_system=str(data.get("discovered_at_system", "sol")),
            bonuses=dict(data.get("bonuses", {})),
        )


@dataclass(frozen=True)
class PilotMastery:
    """Self-Determination Theory competence framework: XP, levels, and talent specs."""

    level: int = 1
    xp: int = 0
    next_level_xp: int = 500
    talent_points: int = 0
    specializations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "xp": self.xp,
            "next_level_xp": self.next_level_xp,
            "talent_points": self.talent_points,
            "specializations": list(self.specializations),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PilotMastery:
        return cls(
            level=int(data.get("level", 1)),
            xp=int(data.get("xp", 0)),
            next_level_xp=int(data.get("next_level_xp", 500)),
            talent_points=int(data.get("talent_points", 0)),
            specializations=tuple(data.get("specializations", ())),
        )


@dataclass(frozen=True)
class TutorialStep:
    """A progressive instructional milestone in the Cadet Flight Academy."""

    id: str  # e.g., 'step_orbit', 'step_scan', 'step_trade', 'step_jump', 'step_drone', 'step_combat'
    title: str
    instruction: str
    hint: str
    description: str = ""
    action_target: str = ""
    reward_credits: int = 250
    reward_xp: int = 100
    completed: bool = False

    def __post_init__(self) -> None:
        if not self.description and self.instruction:
            object.__setattr__(self, "description", self.instruction)
        elif not self.instruction and self.description:
            object.__setattr__(self, "instruction", self.description)
        if not self.action_target and "_" in self.id:
            object.__setattr__(self, "action_target", self.id.split("_", 1)[1])

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "instruction": self.instruction,
            "description": self.description or self.instruction,
            "hint": self.hint,
            "action_target": self.action_target or (self.id.split("_", 1)[1] if "_" in self.id else ""),
            "reward_credits": self.reward_credits,
            "reward_xp": self.reward_xp,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TutorialStep:
        inst = str(data.get("instruction") or data.get("description") or "")
        step_id = str(data["id"])
        target = str(data.get("action_target") or (step_id.split("_", 1)[1] if "_" in step_id else ""))
        return cls(
            id=step_id,
            title=str(data["title"]),
            instruction=inst,
            description=inst,
            hint=str(data.get("hint", "")),
            action_target=target,
            reward_credits=int(data.get("reward_credits", 250)),
            reward_xp=int(data.get("reward_xp", 100)),
            completed=bool(data.get("completed", False)),
        )


@dataclass(frozen=True)
class TutorialState:
    """State of the Cadet Flight Academy onboarding progression."""

    active: bool = True
    current_step_index: int = 0
    steps: tuple[TutorialStep, ...] = ()
    completed: bool = False
    skipped: bool = False

    @property
    def is_active(self) -> bool:
        return self.active and not self.completed and not self.skipped and (self.current_step_index < len(self.steps))

    @property
    def current_step(self) -> TutorialStep:
        if self.steps and 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return TutorialStep(id="none", title="Graduated", instruction="", hint="")

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "is_active": self.is_active,
            "current_step_index": self.current_step_index,
            "steps": [s.to_dict() for s in self.steps],
            "completed": self.completed,
            "skipped": self.skipped,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TutorialState:
        raw_steps = data.get("steps") or ()
        steps = tuple(TutorialStep.from_dict(s) for s in raw_steps)

        return cls(
            active=bool(data.get("active", True)),
            current_step_index=int(data.get("current_step_index", 0)),
            steps=steps,
            completed=bool(data.get("completed", False)),
            skipped=bool(data.get("skipped", False)),
        )


@dataclass(frozen=True)
class StoryRequirements:
    """Gating conditions that must hold before a story choice or chapter unlocks."""

    required_flags: tuple[str, ...] = ()
    forbidden_flags: tuple[str, ...] = ()
    min_reputation: dict[str, int] = field(default_factory=dict)
    required_relic_ids: tuple[str, ...] = ()
    orbit_body_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_flags": list(self.required_flags),
            "forbidden_flags": list(self.forbidden_flags),
            "min_reputation": dict(self.min_reputation),
            "required_relic_ids": list(self.required_relic_ids),
            "orbit_body_id": self.orbit_body_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> StoryRequirements | None:
        if not data:
            return None
        return cls(
            required_flags=tuple(data.get("required_flags", ())),
            forbidden_flags=tuple(data.get("forbidden_flags", ())),
            min_reputation={str(k): int(v) for k, v in dict(data.get("min_reputation", {})).items()},
            required_relic_ids=tuple(data.get("required_relic_ids", ())),
            orbit_body_id=data.get("orbit_body_id"),
        )


@dataclass(frozen=True)
class StoryChoice:
    """Branching story decision impacting faction alignment, rewards, and narrative path."""

    id: str
    text: str
    faction_alignment: str  # 'coalition', 'syndicate', 'precursor', 'independent'
    reward_credits: int = 0
    reward_relic_id: str | None = None
    outcome_text: str = ""
    cost_credits: int = 0
    sets_flags: tuple[str, ...] = ()
    requirements: StoryRequirements | None = None
    locked_text: str = ""
    follow_up: StoryTransmission | None = None

    @property
    def label(self) -> str:
        return self.text

    @property
    def consequence_summary(self) -> str:
        return self.outcome_text

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "label": self.label,
            "faction_alignment": self.faction_alignment,
            "reward_credits": self.reward_credits,
            "reward_relic_id": self.reward_relic_id,
            "outcome_text": self.outcome_text,
            "consequence_summary": self.consequence_summary,
            "cost_credits": self.cost_credits,
            "sets_flags": list(self.sets_flags),
            "requirements": self.requirements.to_dict() if self.requirements else None,
            "locked_text": self.locked_text,
            "follow_up": self.follow_up.to_dict() if self.follow_up else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryChoice:
        return cls(
            id=str(data["id"]),
            text=str(data.get("text") or data.get("label") or ""),
            faction_alignment=str(data.get("faction_alignment", "independent")),
            reward_credits=int(data.get("reward_credits", 0)),
            reward_relic_id=data.get("reward_relic_id"),
            outcome_text=str(data.get("outcome_text") or data.get("consequence_summary") or ""),
            cost_credits=int(data.get("cost_credits", 0)),
            sets_flags=tuple(data.get("sets_flags", ())),
            requirements=StoryRequirements.from_dict(data.get("requirements")),
            locked_text=str(data.get("locked_text", "")),
            follow_up=StoryTransmission.from_dict(data["follow_up"]) if data.get("follow_up") else None,
        )


@dataclass(frozen=True)
class StoryTransmission:
    """Character audio dispatch received across the subspace radio array."""

    speaker: str
    callsign: str
    channel: str
    message: str
    timestamp_system: str = "sol"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryTransmission:
        return cls(
            speaker=str(data["speaker"]),
            callsign=str(data.get("callsign", "UNKNOWN")),
            channel=str(data.get("channel", "Subspace Broad-Band")),
            message=str(data["message"]),
            timestamp_system=str(data.get("timestamp_system", "sol")),
        )


@dataclass(frozen=True)
class StoryChapter:
    """An episodic narrative chapter in the Precursor Cipher campaign."""

    chapter_index: int
    title: str
    target_system_id: str | None
    objective: str
    transmission: StoryTransmission
    choices: tuple[StoryChoice, ...] = ()
    completed: bool = False
    chosen_id: str | None = None
    requirements: StoryRequirements | None = None
    skipped: bool = False

    @property
    def id(self) -> str:
        chapter_ids = {
            0: "act1_ghost_signal",
            1: "act2_sirius_forge",
            2: "act3_eternity_gate",
            3: "act4_hollow_between",
            4: "act5_first_voidfarers",
        }
        return chapter_ids.get(self.chapter_index, f"act{self.chapter_index + 1}")

    @property
    def synopsis(self) -> str:
        return self.objective

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "chapter_index": self.chapter_index,
            "title": self.title,
            "target_system_id": self.target_system_id,
            "objective": self.objective,
            "synopsis": self.synopsis,
            "transmission": self.transmission.to_dict(),
            "choices": [c.to_dict() for c in self.choices],
            "completed": self.completed,
            "chosen_id": self.chosen_id,
            "requirements": self.requirements.to_dict() if self.requirements else None,
            "skipped": self.skipped,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryChapter:
        raw_tx = data.get("transmission") or {"speaker": "System", "callsign": "AI", "channel": "Local", "message": ""}
        return cls(
            chapter_index=int(data.get("chapter_index", 0)),
            title=str(data.get("title", "Prologue")),
            target_system_id=data.get("target_system_id"),
            objective=str(data.get("objective") or data.get("synopsis") or ""),
            transmission=StoryTransmission.from_dict(raw_tx),
            choices=tuple(StoryChoice.from_dict(c) for c in data.get("choices", ())),
            completed=bool(data.get("completed", False)),
            chosen_id=data.get("chosen_id"),
            requirements=StoryRequirements.from_dict(data.get("requirements")),
            skipped=bool(data.get("skipped", False)),
        )


@dataclass(frozen=True)
class StoryState:
    """Master progression tracker for narrative campaign and faction standings."""

    campaign_title: str = "The Precursor Cipher"
    current_chapter_index: int = 0
    chapters: tuple[StoryChapter, ...] = ()
    transmission_log: tuple[StoryTransmission, ...] = ()
    reputation: dict[str, int] = field(default_factory=lambda: {"coalition": 0, "syndicate": 0, "precursor": 0})
    completed: bool = False
    flags: dict[str, bool] = field(default_factory=dict)
    ending_id: str | None = None

    @property
    def active_act(self) -> int:
        return self.current_chapter_index + 1

    @property
    def current_chapter_id(self) -> str:
        if self.chapters and 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index].id
        return f"act{self.active_act}"

    @property
    def current_chapter(self) -> StoryChapter:
        if self.chapters and 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index]
        return StoryChapter(
            chapter_index=0,
            title="Epilogue",
            target_system_id=None,
            objective="All narrative objectives fulfilled.",
            transmission=StoryTransmission("Archon", "Archon-Prime", "Subspace Void", "The galaxy awakens."),
        )

    @property
    def faction_reputation(self) -> dict[str, int]:
        return self.reputation

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_title": self.campaign_title,
            "current_chapter_index": self.current_chapter_index,
            "active_act": self.active_act,
            "current_chapter_id": self.current_chapter_id,
            "chapters": [c.to_dict() for c in self.chapters],
            "transmission_log": [t.to_dict() for t in self.transmission_log],
            "reputation": dict(self.reputation),
            "faction_reputation": dict(self.reputation),
            "completed": self.completed,
            "flags": dict(self.flags),
            "ending_id": self.ending_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryState:
        raw_chapters = data.get("chapters") or ()
        chapters = tuple(StoryChapter.from_dict(c) for c in raw_chapters)

        raw_tx = data.get("transmission_log")
        if not raw_tx and chapters:
            transmission_log = (chapters[0].transmission,)
        else:
            transmission_log = tuple(StoryTransmission.from_dict(t) for t in (raw_tx or ()))

        return cls(
            campaign_title=str(data.get("campaign_title", "The Precursor Cipher")),
            current_chapter_index=int(data.get("current_chapter_index", 0)),
            chapters=chapters,
            transmission_log=transmission_log,
            reputation=dict(data.get("reputation") or data.get("faction_reputation") or {"coalition": 0, "syndicate": 0, "precursor": 0}),
            completed=bool(data.get("completed", False)),
            flags={str(k): bool(v) for k, v in dict(data.get("flags") or {}).items()},
            ending_id=data.get("ending_id"),
        )


@dataclass(frozen=True)
class TravelState:
    """In-system transit between two celestial bodies."""

    origin_body_id: str | None
    destination_body_id: str
    mode: str = "sublight"  # 'sublight' or 'quantum'
    started_tick: int = 0
    arrival_tick: int = 0
    distance_au: float = 0.0
    duration_ticks: int = 1

    def progress(self, current_tick: int) -> float:
        total = max(1, self.arrival_tick - self.started_tick)
        elapsed = max(0, min(total, current_tick - self.started_tick))
        return elapsed / total

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TravelState:
        return cls(
            origin_body_id=data.get("origin_body_id"),
            destination_body_id=str(data["destination_body_id"]),
            mode=str(data.get("mode", "sublight")),
            started_tick=int(data.get("started_tick", 0)),
            arrival_tick=int(data.get("arrival_tick", 0)),
            distance_au=float(data.get("distance_au", 0.0)),
            duration_ticks=int(data.get("duration_ticks", 1)),
        )


@dataclass(frozen=True)
class VoidTraversalState:
    """Transit through the Hollow Between along a void lane between black-hole anchors."""

    origin_system_id: str
    destination_system_id: str
    started_tick: int = 0
    arrival_tick: int = 0
    duration_ticks: int = 1
    stability: float = 100.0
    storms_weathered: int = 0
    resonance: float = 0.0

    def progress(self, current_tick: int) -> float:
        total = max(1, self.arrival_tick - self.started_tick)
        elapsed = max(0, min(total, current_tick - self.started_tick))
        return elapsed / total

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoidTraversalState:
        return cls(
            origin_system_id=str(data["origin_system_id"]),
            destination_system_id=str(data["destination_system_id"]),
            started_tick=int(data.get("started_tick", 0)),
            arrival_tick=int(data.get("arrival_tick", 0)),
            duration_ticks=int(data.get("duration_ticks", 1)),
            stability=float(data.get("stability", 100.0)),
            storms_weathered=int(data.get("storms_weathered", 0)),
            resonance=float(data.get("resonance", 0.0)),
        )


@dataclass(frozen=True)
class GameEvent:
    """Realtime popup event delivered to the cockpit."""

    id: str
    kind: str
    title: str
    message: str
    tick: int = 0
    dismissed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameEvent:
        return cls(
            id=str(data["id"]),
            kind=str(data.get("kind", "system")),
            title=str(data.get("title", "")),
            message=str(data.get("message", "")),
            tick=int(data.get("tick", 0)),
            dismissed=bool(data.get("dismissed", False)),
        )


@dataclass(frozen=True)
class ReactorState:
    """Thermal and structural state of the fusion reactor core."""

    heat: float = 0.0
    max_heat: float = 100.0
    integrity: float = 100.0
    max_integrity: float = 100.0
    mode: str = "balanced"
    last_vent_tick: int = -999

    def to_dict(self) -> dict[str, Any]:
        return {
            "heat": round(self.heat, 2),
            "max_heat": self.max_heat,
            "integrity": round(self.integrity, 2),
            "max_integrity": self.max_integrity,
            "mode": self.mode,
            "last_vent_tick": self.last_vent_tick,
            "heat_pct": round(min(100.0, max(0.0, self.heat / self.max_heat * 100.0)), 1) if self.max_heat else 0.0,
            "integrity_pct": round(min(100.0, max(0.0, self.integrity / self.max_integrity * 100.0)), 1) if self.max_integrity else 0.0,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReactorState:
        max_heat = max(1.0, float(data.get("max_heat", 100.0)))
        max_integrity = max(1.0, float(data.get("max_integrity", 100.0)))
        return cls(
            heat=max(0.0, min(max_heat, float(data.get("heat", 0.0)))),
            max_heat=max_heat,
            integrity=max(0.0, min(max_integrity, float(data.get("integrity", max_integrity)))),
            max_integrity=max_integrity,
            mode=str(data.get("mode", "balanced")),
            last_vent_tick=int(data.get("last_vent_tick", -999)),
        )


@dataclass(frozen=True)
class PlayerCharacter:
    """Persistent commander profile with aging, skills, and activatable abilities."""

    name: str = "Astraea"
    age: int = 31
    background: str = "Navigator"
    level: int = 1
    xp: int = 0
    next_level_xp: int = 400
    skill_points: int = 0
    skills: dict[str, int] = field(default_factory=lambda: {
        "piloting": 1, "engineering": 1, "science": 1,
        "combat": 1, "diplomacy": 1, "trade": 1,
    })
    abilities: tuple[str, ...] = ("overclock", "emergency_repair", "battle_focus", "science_burst")
    ability_cooldowns: dict[str, int] = field(default_factory=dict)
    traits: tuple[str, ...] = ()
    portrait: str = "commander_01"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "age": self.age,
            "background": self.background,
            "level": self.level,
            "xp": self.xp,
            "next_level_xp": self.next_level_xp,
            "skill_points": self.skill_points,
            "skills": dict(self.skills),
            "abilities": list(self.abilities),
            "ability_cooldowns": dict(self.ability_cooldowns),
            "traits": list(self.traits),
            "portrait": self.portrait,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlayerCharacter:
        defaults = {"piloting": 1, "engineering": 1, "science": 1, "combat": 1, "diplomacy": 1, "trade": 1}
        return cls(
            name=str(data.get("name", "Astraea")),
            age=max(18, int(data.get("age", 31))),
            background=str(data.get("background", "Navigator")),
            level=max(1, int(data.get("level", 1))),
            xp=max(0, int(data.get("xp", 0))),
            next_level_xp=max(100, int(data.get("next_level_xp", 400))),
            skill_points=max(0, int(data.get("skill_points", 0))),
            skills={**defaults, **{str(k): int(v) for k, v in data.get("skills", {}).items()}},
            abilities=tuple(data.get("abilities", ("overclock", "emergency_repair", "battle_focus", "science_burst"))),
            ability_cooldowns={str(k): int(v) for k, v in data.get("ability_cooldowns", {}).items()},
            traits=tuple(data.get("traits", ())),
            portrait=str(data.get("portrait", "commander_01")),
        )


@dataclass(frozen=True)
class ResearchState:
    """Research progress and completed technology unlocks."""

    points: int = 0
    progress: int = 0
    active_project_id: str | None = None
    completed: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": self.points,
            "progress": self.progress,
            "active_project_id": self.active_project_id,
            "completed": list(self.completed),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResearchState:
        return cls(
            points=max(0, int(data.get("points", 0))),
            progress=max(0, int(data.get("progress", 0))),
            active_project_id=data.get("active_project_id"),
            completed=tuple(data.get("completed", ())),
        )


@dataclass(frozen=True)
class Outpost:
    """Player-owned planetary or orbital installation that produces value each tick."""

    id: str
    name: str
    system_id: str
    body_id: str
    outpost_type: str = "mining"
    level: int = 1
    population: int = 250
    modules: dict[str, int] = field(default_factory=lambda: {"extractor": 1})
    production: dict[str, float] = field(default_factory=lambda: {"credits": 8.0, "research": 1.0})
    integrity: float = 100.0
    founded_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Outpost:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            system_id=str(data["system_id"]),
            body_id=str(data["body_id"]),
            outpost_type=str(data.get("outpost_type", "mining")),
            level=max(1, int(data.get("level", 1))),
            population=max(0, int(data.get("population", 250))),
            modules={str(k): int(v) for k, v in data.get("modules", {"extractor": 1}).items()},
            production={str(k): float(v) for k, v in data.get("production", {}).items()},
            integrity=float(data.get("integrity", 100.0)),
            founded_tick=int(data.get("founded_tick", 0)),
        )


@dataclass(frozen=True)
class FleetShip:
    """Player-owned escort warship attached to the fleet manager."""

    id: str
    name: str
    ship_class: str
    role: str  # 'escort', 'frigate', 'cruiser', 'carrier'
    hull: int
    max_hull: int
    shield: int
    max_shield: int
    damage: int
    evasion: float = 0.05
    assigned_system_id: str = "sol"
    status: str = "escorting"
    experience: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FleetShip:
        max_hull = max(1, int(data.get("max_hull", 120)))
        max_shield = max(0, int(data.get("max_shield", 60)))
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "Escort")),
            ship_class=str(data.get("ship_class", "Escort Corvette")),
            role=str(data.get("role", "escort")),
            hull=max(0, min(max_hull, int(data.get("hull", max_hull)))),
            max_hull=max_hull,
            shield=max(0, min(max_shield, int(data.get("shield", max_shield)))),
            max_shield=max_shield,
            damage=max(1, int(data.get("damage", 12))),
            evasion=max(0.0, min(0.8, float(data.get("evasion", 0.05)))),
            assigned_system_id=str(data.get("assigned_system_id", "sol")),
            status=str(data.get("status", "escorting")),
            experience=max(0, int(data.get("experience", 0))),
        )


@dataclass(frozen=True)
class FactionLeader:
    """Individual leader whose behavior drives a faction's simulation policy."""

    id: str
    faction_id: str
    name: str
    title: str
    behavior: str  # 'militarist', 'merchant', 'isolationist', 'opportunist', 'visionary'
    aggression: float = 0.5
    diplomacy: float = 0.5
    ambition: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactionLeader:
        return cls(
            id=str(data["id"]),
            faction_id=str(data["faction_id"]),
            name=str(data.get("name", "Leader")),
            title=str(data.get("title", "Sovereign")),
            behavior=str(data.get("behavior", "opportunist")),
            aggression=max(0.0, min(1.0, float(data.get("aggression", 0.5)))),
            diplomacy=max(0.0, min(1.0, float(data.get("diplomacy", 0.5)))),
            ambition=max(0.0, min(1.0, float(data.get("ambition", 0.5)))),
        )


@dataclass(frozen=True)
class WarState:
    """Active or concluded war between two sovereign factions."""

    id: str
    attacker_id: str
    defender_id: str
    started_tick: int
    war_score: float = 0.0
    active: bool = True
    captured_systems: tuple[str, ...] = ()
    ended_tick: int | None = None
    # Credits the player pledged to each side, by faction id.
    support: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "captured_systems": list(self.captured_systems)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WarState:
        ended = data.get("ended_tick")
        return cls(
            id=str(data["id"]),
            attacker_id=str(data["attacker_id"]),
            defender_id=str(data["defender_id"]),
            started_tick=int(data.get("started_tick", 0)),
            war_score=float(data.get("war_score", 0.0)),
            active=bool(data.get("active", True)),
            captured_systems=tuple(str(sid) for sid in data.get("captured_systems", ())),
            ended_tick=int(ended) if ended is not None else None,
            support={str(k): int(v) for k, v in data.get("support", {}).items()},
        )


@dataclass(frozen=True)
class CrewMember:
    """Recruitable crew specialist with a role, morale, wage, and portrait."""

    id: str
    name: str
    role: str
    skill: int = 2
    morale: float = 75.0
    wage: int = 25
    portrait: str = "crew_01"
    specialty: str = ""
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrewMember:
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "Crew Member")),
            role=str(data.get("role", "deckhand")),
            skill=max(1, min(10, int(data.get("skill", 2)))),
            morale=max(0.0, min(100.0, float(data.get("morale", 75.0)))),
            wage=max(0, int(data.get("wage", 25))),
            portrait=str(data.get("portrait", "crew_01")),
            specialty=str(data.get("specialty", "")),
            status=str(data.get("status", "active")),
        )


@dataclass(frozen=True)
class ShipState:
    """Complete telemetry, resource inventory, and status of the player's flagship."""

    commander_name: str
    callsign: str
    ship_class: str
    hull: int
    max_hull: int
    shield: int
    max_shield: int
    fuel: int
    max_fuel: int
    credits: int
    cargo: dict[str, int]
    cargo_capacity: int
    current_system_id: str
    orbiting_body_id: str | None
    power: ShipPower = field(default_factory=ShipPower)
    reactor: ReactorState = field(default_factory=ReactorState)
    upgrades: tuple[str, ...] = ()
    equipped_upgrades: dict[str, str] = field(default_factory=dict)
    ship_mods: dict[str, str] = field(default_factory=dict)
    fleet_drones: tuple[FleetDrone, ...] = ()
    fleet_ships: tuple[FleetShip, ...] = ()
    battle_stance: str = "balanced"
    crew: tuple[CrewMember, ...] = ()
    weapons: tuple[str, ...] = ("pulse_laser",)
    primary_weapon: str = "pulse_laser"
    message_bonuses: dict[str, float] = field(default_factory=dict)
    flight_log: tuple[str, ...] = ()
    streak: int = 1
    relics: tuple[PrecursorRelic, ...] = ()
    mastery: PilotMastery = field(default_factory=PilotMastery)
    active_contracts: tuple[BountyContract, ...] = ()
    tactical_combo: int = 0
    near_miss_scanner_bonus: float = 0.0
    tutorial: TutorialState = field(default_factory=TutorialState)
    story: StoryState = field(default_factory=StoryState)
    faction_standings: dict[str, int] = field(default_factory=dict)
    corp_standings: dict[str, int] = field(default_factory=dict)
    allies: tuple[str, ...] = ()
    landed_body_id: str | None = None
    travel: TravelState | None = None
    void_traversal: VoidTraversalState | None = None
    # Credits paid for the units still in the hold, per commodity (trade P/L basis).
    cargo_cost: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "commander_name": self.commander_name,
            "callsign": self.callsign,
            "ship_class": self.ship_class,
            "hull": self.hull,
            "max_hull": self.max_hull,
            "shield": self.shield,
            "max_shield": self.max_shield,
            "fuel": self.fuel,
            "max_fuel": self.max_fuel,
            "credits": self.credits,
            "cargo": dict(self.cargo),
            "cargo_cost": dict(self.cargo_cost),
            "cargo_capacity": self.cargo_capacity,
            "current_system_id": self.current_system_id,
            "orbiting_body_id": self.orbiting_body_id,
            "power": self.power.to_dict(),
            "reactor": self.reactor.to_dict(),
            "upgrades": list(self.upgrades),
            "equipped_upgrades": dict(self.equipped_upgrades),
            "ship_mods": dict(self.ship_mods),
            "fleet_drones": [d.to_dict() for d in self.fleet_drones],
            "fleet_ships": [s.to_dict() for s in self.fleet_ships],
            "battle_stance": self.battle_stance,
            "crew": [c.to_dict() for c in self.crew],
            "weapons": list(self.weapons),
            "primary_weapon": self.primary_weapon,
            "message_bonuses": dict(self.message_bonuses),
            "flight_log": list(self.flight_log),
            "streak": self.streak,
            "relics": [r.to_dict() for r in self.relics],
            "mastery": self.mastery.to_dict(),
            "active_contracts": [c.to_dict() for c in self.active_contracts],
            "tactical_combo": self.tactical_combo,
            "near_miss_scanner_bonus": self.near_miss_scanner_bonus,
            "tutorial": self.tutorial.to_dict(),
            "story": self.story.to_dict(),
            "faction_standings": dict(self.faction_standings),
            "corp_standings": dict(self.corp_standings),
            "allies": list(self.allies),
            "landed_body_id": self.landed_body_id,
            "travel": self.travel.to_dict() if self.travel else None,
            "void_traversal": self.void_traversal.to_dict() if self.void_traversal else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShipState:
        story_data = data.get("story", {})
        story_rep = story_data.get("reputation", {}) if isinstance(story_data, dict) else {}
        default_factions = {
            "sol_coalition": int(story_rep.get("coalition", 0)),
            "vanguard_syndicate": int(story_rep.get("syndicate", 0)),
            "precursor_watch": int(story_rep.get("precursor", 0)),
            "nebula_collective": 0,
            "outlaw_corsairs": -15,
        }
        faction_standings = dict(data.get("faction_standings") or default_factions)

        default_corps = {
            "hyperion_dynamics": 0,
            "astraea_pharma": 0,
            "omnicorp_mining": 0,
            "nexus_cybernetics": 0,
            "vortex_fuel": 0,
        }
        corp_standings = dict(data.get("corp_standings") or default_corps)

        return cls(
            commander_name=str(data.get("commander_name", "Valerius")),
            callsign=str(data.get("callsign", "Aegis-7")),
            ship_class=str(data.get("ship_class", "Vanguard Explorer")),
            hull=int(data.get("hull", 100)),
            max_hull=int(data.get("max_hull", 100)),
            shield=int(data.get("shield", 100)),
            max_shield=int(data.get("max_shield", 100)),
            fuel=int(data.get("fuel", 50)),
            max_fuel=int(data.get("max_fuel", 50)),
            credits=int(data.get("credits", 1500)),
            cargo=dict(data.get("cargo", {})),
            cargo_capacity=int(data.get("cargo_capacity", 30)),
            cargo_cost={str(k): int(v) for k, v in data.get("cargo_cost", {}).items()},
            current_system_id=str(data.get("current_system_id", "sol")),
            orbiting_body_id=data.get("orbiting_body_id"),
            power=ShipPower.from_dict(data.get("power", {})),
            reactor=ReactorState.from_dict(data.get("reactor", {})),
            upgrades=tuple(data.get("upgrades", ())),
            equipped_upgrades=dict(data.get("equipped_upgrades", {})),
            ship_mods={str(k): str(v) for k, v in data.get("ship_mods", {}).items()},
            fleet_drones=tuple(FleetDrone.from_dict(d) for d in data.get("fleet_drones", [])),
            fleet_ships=tuple(FleetShip.from_dict(s) for s in data.get("fleet_ships", [])),
            battle_stance=str(data.get("battle_stance", "balanced")),
            crew=tuple(CrewMember.from_dict(c) for c in data.get("crew", ())),
            weapons=tuple(data.get("weapons", ("pulse_laser",))),
            primary_weapon=str(data.get("primary_weapon", "pulse_laser")),
            message_bonuses={str(k): float(v) for k, v in data.get("message_bonuses", {}).items()},
            flight_log=tuple(data.get("flight_log", ())),
            streak=int(data.get("streak", 1)),
            relics=tuple(PrecursorRelic.from_dict(r) for r in data.get("relics", [])),
            mastery=PilotMastery.from_dict(data.get("mastery", {})),
            active_contracts=tuple(BountyContract.from_dict(c) for c in data.get("active_contracts", [])),
            tactical_combo=int(data.get("tactical_combo", 0)),
            near_miss_scanner_bonus=float(data.get("near_miss_scanner_bonus", 0.0)),
            tutorial=TutorialState.from_dict(data.get("tutorial", {})),
            story=StoryState.from_dict(data.get("story", {})),
            faction_standings=faction_standings,
            corp_standings=corp_standings,
            allies=tuple(data.get("allies", ())),
            landed_body_id=data.get("landed_body_id"),
            travel=TravelState.from_dict(data["travel"]) if data.get("travel") else None,
            void_traversal=VoidTraversalState.from_dict(data["void_traversal"]) if data.get("void_traversal") else None,
        )


@dataclass(frozen=True)
class TimeState:
    """Universal cosmic stardate, simulation ticks, and time control state."""

    tick: int = 0
    stardate: float = 3042.00
    speed: float = 1.0  # 0.0=paused, 1.0=normal, 2.0=fast, 5.0=faster, 10.0=warp
    is_paused: bool = False
    time_scale: str = "1x"
    elapsed_days: float = 0.0

    @property
    def era(self) -> str:
        return "Quantum Age (31st Century)"

    @property
    def current_date(self) -> str:
        """In-game calendar date (DD.MM.YYYY), starting 01.01.3042 at tick zero."""
        start = date(3042, 1, 1)
        return (start + timedelta(days=int(self.elapsed_days))).strftime("%d.%m.%Y")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "stardate": round(self.stardate, 2),
            "date": self.current_date,
            "era": self.era,
            "speed": self.speed,
            "is_paused": self.is_paused,
            "time_scale": self.time_scale,
            "elapsed_days": round(self.elapsed_days, 2),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimeState:
        if not data:
            return cls()
        return cls(
            tick=int(data.get("tick", 0)),
            stardate=float(data.get("stardate", 3042.0)),
            speed=float(data.get("speed", 1.0)),
            is_paused=bool(data.get("is_paused", False)),
            time_scale=str(data.get("time_scale", "1x")),
            elapsed_days=float(data.get("elapsed_days", 0.0)),
        )


@dataclass(frozen=True)
class EconomicEvent:
    """Cosmic economic shock, boom, crisis, or embargo shifting commodity supply and prices."""

    id: str
    title: str
    description: str
    system_id: str
    commodity_id: str
    price_multiplier: float
    duration_ticks: int
    category: str = "boom"  # 'boom', 'crisis', 'shortage', 'breakthrough', 'blockade'

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EconomicEvent:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data["description"]),
            system_id=str(data["system_id"]),
            commodity_id=str(data["commodity_id"]),
            price_multiplier=float(data.get("price_multiplier", 1.0)),
            duration_ticks=int(data.get("duration_ticks", 20)),
            category=str(data.get("category", "boom")),
        )


@dataclass(frozen=True)
class SystemMarketState:
    """Localized commodity supply stockpiles, demand pressures, and local production."""

    system_id: str
    stockpiles: dict[str, int] = field(default_factory=dict)
    production_rates: dict[str, int] = field(default_factory=dict)
    consumption_rates: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "stockpiles": dict(self.stockpiles),
            "production_rates": dict(self.production_rates),
            "consumption_rates": dict(self.consumption_rates),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SystemMarketState:
        return cls(
            system_id=str(data["system_id"]),
            stockpiles={k: int(v) for k, v in data.get("stockpiles", {}).items()},
            production_rates={k: int(v) for k, v in data.get("production_rates", {}).items()},
            consumption_rates={k: int(v) for k, v in data.get("consumption_rates", {}).items()},
        )


@dataclass(frozen=True)
class GlobalEconomyState:
    """Galactic economy simulation tracking localized market states and macro-economic events."""

    markets: dict[str, SystemMarketState] = field(default_factory=dict)
    active_events: tuple[EconomicEvent, ...] = ()
    last_updated_tick: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "markets": {k: v.to_dict() for k, v in self.markets.items()},
            "active_events": [e.to_dict() for e in self.active_events],
            "last_updated_tick": self.last_updated_tick,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GlobalEconomyState:
        if not data:
            return cls()
        markets = {
            k: SystemMarketState.from_dict(v)
            for k, v in data.get("markets", {}).items()
        }
        events = tuple(
            EconomicEvent.from_dict(e)
            for e in data.get("active_events", [])
        )
        return cls(
            markets=markets,
            active_events=events,
            last_updated_tick=int(data.get("last_updated_tick", 0)),
        )


@dataclass(frozen=True)
class CodexState:
    """Persistent captain's log progress: claimed milestones and their dates."""

    claimed: tuple[str, ...] = ()
    claimed_dates: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claimed": list(self.claimed),
            "claimed_dates": dict(self.claimed_dates),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodexState:
        if not data:
            return cls()
        claimed = tuple(str(entry_id) for entry_id in data.get("claimed", ()))
        dates = {
            str(entry_id): str(claimed_date)
            for entry_id, claimed_date in data.get("claimed_dates", {}).items()
        }
        return cls(claimed=claimed, claimed_dates=dates)


@dataclass(frozen=True)
class GameState:
    """Master simulation universe state container."""

    version: int
    galaxy_seed: int
    ship: ShipState
    systems: dict[str, StarSystem]
    visited_systems: tuple[str, ...]
    active_anomaly: AnomalyEncounter | None = None
    active_combat: CombatEncounter | None = None
    time: TimeState = field(default_factory=TimeState)
    stats: dict[str, int] = field(default_factory=lambda: {
        "jumps": 0,
        "scans": 0,
        "trades": 0,
        "anomalies_resolved": 0,
        "combat_victories": 0,
        "credits_earned": 0,
    })
    economy: GlobalEconomyState = field(default_factory=GlobalEconomyState)
    ai_captains: tuple[AICaptain, ...] = ()
    depots: tuple[Depot, ...] = ()
    messages: tuple[QuantumMessage, ...] = ()
    events: tuple[GameEvent, ...] = ()
    character: PlayerCharacter = field(default_factory=PlayerCharacter)
    research: ResearchState = field(default_factory=ResearchState)
    outposts: tuple[Outpost, ...] = ()
    faction_leaders: tuple[FactionLeader, ...] = ()
    wars: tuple[WarState, ...] = ()
    eliminated_factions: tuple[str, ...] = ()
    codex: CodexState = field(default_factory=CodexState)
    local_dock_purchases: dict[tuple[str, str, str], tuple[int, int]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "galaxy_seed": self.galaxy_seed,
            "ship": self.ship.to_dict(),
            "systems": {k: v.to_dict() for k, v in self.systems.items()},
            "visited_systems": list(self.visited_systems),
            "active_anomaly": self.active_anomaly.to_dict() if self.active_anomaly else None,
            "active_combat": self.active_combat.to_dict() if self.active_combat else None,
            "time": self.time.to_dict(),
            "stats": dict(self.stats),
            "economy": self.economy.to_dict(),
            "ai_captains": [c.to_dict() for c in self.ai_captains],
            "depots": [d.to_dict() for d in self.depots],
            "messages": [m.to_dict() for m in self.messages],
            "events": [e.to_dict() for e in self.events],
            "character": self.character.to_dict(),
            "research": self.research.to_dict(),
            "outposts": [o.to_dict() for o in self.outposts],
            "faction_leaders": [l.to_dict() for l in self.faction_leaders],
            "wars": [w.to_dict() for w in self.wars],
            "eliminated_factions": list(self.eliminated_factions),
            "codex": self.codex.to_dict(),
            "local_dock_purchases": {
                "|".join(tag): [quantity, cost]
                for tag, (quantity, cost) in self.local_dock_purchases.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        systems = {
            k: StarSystem.from_dict(v)
            for k, v in data.get("systems", {}).items()
        }
        active_anomaly = (
            AnomalyEncounter.from_dict(data["active_anomaly"])
            if data.get("active_anomaly")
            else None
        )
        active_combat = (
            CombatEncounter.from_dict(data["active_combat"])
            if data.get("active_combat")
            else None
        )
        dock_purchases: dict[tuple[str, str, str], tuple[int, int]] = {}
        for raw_tag, raw_lot in (data.get("local_dock_purchases") or {}).items():
            parts = str(raw_tag).split("|")
            if len(parts) != 3 or not isinstance(raw_lot, (list, tuple)) or len(raw_lot) != 2:
                continue
            try:
                quantity, cost = int(raw_lot[0]), int(raw_lot[1])
            except (TypeError, ValueError):
                continue
            if quantity > 0 and cost >= 0:
                dock_purchases[(parts[0], parts[1], parts[2])] = (quantity, cost)
        return cls(
            version=int(data.get("version", 1)),
            galaxy_seed=int(data.get("galaxy_seed", 42)),
            ship=ShipState.from_dict(data["ship"]),
            systems=systems,
            visited_systems=tuple(data.get("visited_systems", ())),
            active_anomaly=active_anomaly,
            active_combat=active_combat,
            time=TimeState.from_dict(data.get("time", {})),
            stats=dict(data.get("stats", {
                "jumps": 0,
                "scans": 0,
                "trades": 0,
                "anomalies_resolved": 0,
                "combat_victories": 0,
                "credits_earned": 0,
            })),
            economy=GlobalEconomyState.from_dict(data.get("economy", {})),
            ai_captains=tuple(AICaptain.from_dict(c) for c in data.get("ai_captains", ())),
            depots=tuple(Depot.from_dict(d) for d in data.get("depots", ())),
            messages=tuple(QuantumMessage.from_dict(m) for m in data.get("messages", ())),
            events=tuple(GameEvent.from_dict(e) for e in data.get("events", ())),
            character=PlayerCharacter.from_dict(data.get("character", {})),
            research=ResearchState.from_dict(data.get("research", {})),
            outposts=tuple(Outpost.from_dict(o) for o in data.get("outposts", ())),
            faction_leaders=tuple(FactionLeader.from_dict(l) for l in data.get("faction_leaders", ())),
            wars=tuple(WarState.from_dict(w) for w in data.get("wars", ())),
            eliminated_factions=tuple(data.get("eliminated_factions", ())),
            codex=CodexState.from_dict(data.get("codex", {})),
            local_dock_purchases=dock_purchases,
        )

