"""Away-team expeditions: body missions, deterministic outcomes, and crew risk.

An away team leaves the ship while the commander keeps flying. Missions resolve on
the simulation tick from a stable seed, so a given save always produces the same
outcome. Failures injure specialists, which halves their ship bonus until the
medbay or time restores them.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
from typing import Any, Iterable, Sequence

from voidfarer.inventory import get_item_info
from voidfarer.models import AwayMission, CelestialBody, CrewMember


@dataclass(frozen=True)
class AwayMissionType:
    """One expedition profile that can be launched from orbit."""

    id: str
    name: str
    icon: str
    description: str
    duration_ticks: int
    team_size: int
    base_risk: int
    required_skill: str
    credits: int
    research: int
    cargo: tuple[tuple[str, int], ...]
    morale: int
    standing: int
    body_types: tuple[str, ...] = ()
    min_population: int = 0
    contract_category: str = "exploration"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "duration_ticks": self.duration_ticks,
            "team_size": self.team_size,
            "base_risk": self.base_risk,
            "required_skill": self.required_skill,
            "credits": self.credits,
            "research": self.research,
            "cargo": [{"id": item_id, "name": get_item_info(item_id).name, "quantity": quantity}
                      for item_id, quantity in self.cargo],
            "morale": self.morale,
            "standing": self.standing,
            "contract_category": self.contract_category,
        }

    def available_on(self, body: CelestialBody) -> bool:
        if body.body_type in ("star", "black_hole"):
            return False
        if self.min_population > 0 and body.population < self.min_population:
            return False
        return not self.body_types or body.body_type in self.body_types


AWAY_MISSION_TYPES: tuple[AwayMissionType, ...] = (
    AwayMissionType(
        id="geological_survey",
        name="Geological Survey",
        icon="◈",
        description="Map mineral seams and core samples with a compact survey team.",
        duration_ticks=6,
        team_size=1,
        base_risk=10,
        required_skill="science",
        credits=90,
        research=35,
        cargo=(("titanium", 2),),
        morale=0,
        standing=0,
        body_types=(
            "terrestrial", "oceanic", "desert_world", "ice_world", "lava_world",
            "volcanic", "barren", "asteroid_belt", "super_earth", "tundra", "savanna",
        ),
        contract_category="mining",
    ),
    AwayMissionType(
        id="salvage_sweep",
        name="Salvage Sweep",
        icon="◇",
        description="Cut through a debris field and recover intact components before the drift.",
        duration_ticks=8,
        team_size=2,
        base_risk=20,
        required_skill="engineering",
        credits=240,
        research=10,
        cargo=(("microchips", 1), ("titanium", 2)),
        morale=0,
        standing=0,
        contract_category="mining",
    ),
    AwayMissionType(
        id="xenobiology",
        name="Xenobiology Study",
        icon="❖",
        description="Collect living samples from a biosphere under quarantine protocol.",
        duration_ticks=10,
        team_size=2,
        base_risk=24,
        required_skill="science",
        credits=130,
        research=80,
        cargo=(("medicines", 1), ("hydroponics", 2)),
        morale=1,
        standing=1,
        body_types=(
            "terrestrial", "oceanic", "savanna", "tundra", "ice_world",
            "gas_giant", "ringed_giant", "ice_giant", "super_earth", "ring_world",
        ),
    ),
    AwayMissionType(
        id="colony_relief",
        name="Colony Relief",
        icon="△",
        description="Run medical supplies and engineers into a settlement in crisis.",
        duration_ticks=5,
        team_size=2,
        base_risk=6,
        required_skill="medical",
        credits=170,
        research=15,
        cargo=(("hydroponics", 2),),
        morale=6,
        standing=3,
        min_population=1,
        contract_category="exploration",
    ),
    AwayMissionType(
        id="distress_sweep",
        name="Distress Sweep",
        icon="✶",
        description="Board a silent distress beacon with marines and bring the survivors home.",
        duration_ticks=7,
        team_size=3,
        base_risk=36,
        required_skill="combat",
        credits=330,
        research=20,
        cargo=(("fuel_cells", 2),),
        morale=3,
        standing=4,
        contract_category="combat",
    ),
)

AWAY_MISSION_MAP: dict[str, AwayMissionType] = {m.id: m for m in AWAY_MISSION_TYPES}


def get_away_mission_type(mission_type: str) -> AwayMissionType | None:
    return AWAY_MISSION_MAP.get(mission_type)


def site_key(mission_type: str, body_id: str) -> str:
    """Stable key for a worked site, so a body cannot be farmed by the same expedition."""
    return f"{body_id}:{mission_type}"


def available_missions(body: CelestialBody | None) -> tuple[AwayMissionType, ...]:
    """Every expedition profile that can be launched from orbit around this body."""
    if body is None:
        return ()
    return tuple(m for m in AWAY_MISSION_TYPES if m.available_on(body))


def _fit(member: CrewMember, required_skill: str) -> float:
    if member.status != "active" or member.injury_ticks > 0:
        return 0.0
    value = float(max(1, member.skill))
    if member.specialty == required_skill:
        value += 4.0
    elif member.role == required_skill:
        value += 2.0
    return value


def crew_fit(member: CrewMember, required_skill: str) -> float:
    """Effective aptitude of one crew member for a mission's required discipline."""
    return _fit(member, required_skill)


def auto_team(
    mission_type: AwayMissionType,
    crew: Sequence[CrewMember],
    assigned_ids: Iterable[str] = (),
) -> tuple[CrewMember, ...]:
    """Pick the best available specialists for a mission, deterministically."""
    assigned = set(assigned_ids)
    candidates = [
        member for member in crew
        if member.status == "active" and member.injury_ticks == 0 and member.id not in assigned
    ]
    candidates.sort(key=lambda member: (-_fit(member, mission_type.required_skill), -member.skill, member.id))
    return tuple(candidates[: mission_type.team_size])


def mission_risk(
    mission_type: AwayMissionType,
    body: CelestialBody,
    team: Sequence[CrewMember],
) -> int:
    """Risk percentage after body hazards, gravity and specialist aptitude."""
    if not team:
        return 100
    fit = sum(_fit(member, mission_type.required_skill) for member in team) / len(team)
    hazard = 4 * len(body.hazards)
    gravity = max(0.0, abs(float(body.gravity or 1.0) - 1.0) * 6.0)
    risk = mission_type.base_risk + hazard + gravity - fit * 1.4
    return max(3, min(70, int(round(risk))))


def _mission_rng(mission: AwayMission, galaxy_seed: int) -> random.Random:
    digest = hashlib.blake2b(
        f"{galaxy_seed}|{mission.id}|{mission.system_id}|{mission.body_id}|"
        f"{mission.started_tick}|{','.join(sorted(mission.crew_ids))}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return random.Random(int.from_bytes(digest, "big"))


def resolve_away_mission(
    mission: AwayMission,
    mission_type: AwayMissionType,
    body: CelestialBody,
    team: Sequence[CrewMember],
    galaxy_seed: int,
) -> dict[str, Any]:
    """Resolve one due expedition deterministically. Returns an outcome packet."""
    rng = _mission_rng(mission, galaxy_seed)
    roll = rng.random()
    risk_fraction = max(0.0, min(1.0, mission.risk / 100.0))
    success = roll >= risk_fraction
    critical = success and roll >= min(0.97, risk_fraction + 0.45)
    fit = (
        sum(_fit(member, mission_type.required_skill) for member in team) / len(team)
        if team else 0.0
    )
    scale = max(0.65, min(1.8, 0.65 + 0.12 * fit))
    if critical:
        scale *= 1.5
    if not success:
        scale = 0.2

    credits = int(round(mission_type.credits * scale))
    research = int(round(mission_type.research * scale))
    cargo = tuple(
        (item_id, max(1, int(round(quantity * scale))))
        for item_id, quantity in mission_type.cargo
    ) if success else ()
    morale = mission_type.morale + (2 if critical else 0) if success else -3
    standing = mission_type.standing if success else 0
    xp = (18 + int(6 * fit)) if success else 4
    if critical:
        xp += 12
    xp = max(1, xp)

    injuries: dict[str, int] = {}
    if not success and team:
        count = 2 if mission.risk >= 40 and len(team) > 1 else 1
        for member in rng.sample(list(team), k=min(count, len(team))):
            injuries[member.id] = rng.randint(8, 16)

    outcome = "CRITICAL SUCCESS" if critical else ("SUCCESS" if success else "INCIDENT")
    reward_parts = []
    if credits:
        reward_parts.append(f"+{credits} cr")
    if research:
        reward_parts.append(f"+{research} research")
    if cargo:
        reward_parts.append(", ".join(f"+{qty} {get_item_info(item).name}" for item, qty in cargo))
    if morale and success:
        reward_parts.append(f"morale +{morale}")
    if standing:
        reward_parts.append(f"standing +{standing}")
    if injuries:
        reward_parts.append(f"{len(injuries)} crew injured")
    suffix = f" ({'; '.join(reward_parts)})" if reward_parts else ""
    log = f"AWAY TEAM [{outcome}]: {mission_type.name} at {body.name}{suffix}."

    return {
        "success": success,
        "critical": critical,
        "risk": mission.risk,
        "credits": credits,
        "research": research,
        "cargo": cargo,
        "morale": morale,
        "standing": standing,
        "injuries": injuries,
        "xp": {member.id: xp for member in team},
        "contract_category": mission_type.contract_category,
        "contract_progress": 1 if success else 0,
        "log": log,
    }
