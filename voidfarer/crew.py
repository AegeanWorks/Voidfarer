"""Crew roles, recruiting, portraits, and crew-derived ship bonuses."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Sequence

from voidfarer.models import CrewMember


@dataclass(frozen=True)
class CrewRole:
    id: str
    name: str
    description: str
    cost: int
    wage: int
    specialty: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cost": self.cost,
            "wage": self.wage,
            "specialty": self.specialty,
        }


CREW_ROLES: tuple[CrewRole, ...] = (
    CrewRole("pilot", "Flight Pilot", "Improves evasion and fuel discipline.", 900, 30, "evasion"),
    CrewRole("engineer", "Reactor Engineer", "Improves cooling and damage control.", 1100, 35, "engineering"),
    CrewRole("scientist", "Science Officer", "Improves scans and research generation.", 1200, 38, "science"),
    CrewRole("medic", "Medical Officer", "Improves hull repair and crew morale.", 800, 28, "medical"),
    CrewRole("marine", "Marine Sergeant", "Improves boarding defense and weapon damage.", 1000, 32, "combat"),
    CrewRole("quartermaster", "Quartermaster", "Improves trade margins and cargo discipline.", 850, 26, "trade"),
)

CREW_ROLE_MAP: dict[str, CrewRole] = {r.id: r for r in CREW_ROLES}

CREW_NAMES: tuple[str, ...] = (
    "Imani Vale", "Rook Calder", "Sera Nwosu", "Dax Mercer", "Liora Venn",
    "Tomas Ryn", "Nadia Sol", "Kade Orin", "Mira Quell", "Juno Pike",
)

PORTRAIT_IDS: tuple[str, ...] = (
    "crew_01", "crew_02", "crew_03", "crew_04", "crew_05",
    "crew_06", "crew_07", "crew_08", "crew_09", "crew_10",
)


def get_crew_role(role_id: str) -> CrewRole | None:
    return CREW_ROLE_MAP.get(role_id)


def recruit_crew_member(role_id: str, seed: int, current_count: int) -> CrewMember | None:
    role = get_crew_role(role_id)
    if not role:
        return None
    rng = random.Random(int(seed) * 7919 + current_count * 104_729 + 3)
    return CrewMember(
        id=f"crew_{role.id}_{current_count + 1}",
        name=rng.choice(CREW_NAMES),
        role=role.id,
        skill=2 + rng.randint(0, 2),
        morale=75.0 + rng.randint(0, 15),
        wage=role.wage,
        portrait=rng.choice(PORTRAIT_IDS),
        specialty=role.specialty,
        status="active",
    )


def calculate_crew_bonuses(crew: Sequence[CrewMember]) -> dict[str, float]:
    bonuses: dict[str, float] = {
        "fuel_efficiency": 1.0,
        "evasion": 0.0,
        "reactor_cooling": 0.0,
        "hull_repair_per_tick": 0.0,
        "scan_mult": 1.0,
        "research_per_tick": 0.0,
        "combat_damage": 0.0,
        "trade_margin": 0.0,
        "boarding_defense": 0.0,
    }
    for member in crew:
        if member.status != "active":
            continue
        skill = max(1, member.skill)
        morale = max(0.25, member.morale / 100.0)
        if member.role == "pilot":
            bonuses["evasion"] += 0.015 * skill * morale
            bonuses["fuel_efficiency"] *= max(0.80, 1.0 - 0.012 * skill * morale)
        elif member.role == "engineer":
            bonuses["reactor_cooling"] += 1.4 * skill * morale
            bonuses["hull_repair_per_tick"] += 0.15 * skill * morale
        elif member.role == "scientist":
            bonuses["scan_mult"] *= 1.0 + 0.035 * skill * morale
            bonuses["research_per_tick"] += 0.8 * skill * morale
        elif member.role == "medic":
            bonuses["hull_repair_per_tick"] += 0.30 * skill * morale
        elif member.role == "marine":
            bonuses["combat_damage"] += 2.5 * skill * morale
            bonuses["boarding_defense"] += 0.05 * skill * morale
        elif member.role == "quartermaster":
            bonuses["trade_margin"] += 0.015 * skill * morale
    bonuses["evasion"] = min(0.45, bonuses["evasion"])
    bonuses["fuel_efficiency"] = max(0.50, min(1.0, bonuses["fuel_efficiency"]))
    return bonuses


# Crew wages are a monthly rate; the engine accrues them day by day on the calendar.
DAYS_PER_MONTH = 30.0


def crew_upkeep(crew: Sequence[CrewMember]) -> int:
    """Monthly wage bill of the active crew."""
    return sum(member.wage for member in crew if member.status == "active")


def wages_due(crew: Sequence[CrewMember], days_before: float, days_after: float) -> int:
    """Whole credits of monthly wages accrued between two calendar points (cumulative, so
    fractions carry over between ticks instead of being lost or double-charged)."""
    upkeep = crew_upkeep(crew)
    return int(upkeep * days_after // DAYS_PER_MONTH) - int(upkeep * days_before // DAYS_PER_MONTH)


# Morale thresholds for the living crew simulation
RESIGN_MORALE = 20.0
RESIGN_CHANCE_PER_TICK = 0.08
CRITICAL_MORALE = 35.0


def tick_crew(
    crew: Sequence[CrewMember],
    num_ticks: int,
    credits_available: int,
    rng: random.Random | None = None,
    wage_due: int | None = None,
) -> tuple[tuple[CrewMember, ...], int, list[str]]:
    """Advance wages and morale; unpaid crews sink toward desertion.

    `wage_due` is the accrued wage for this step (see `wages_due`); without it the whole
    wage bill is charged per tick, the legacy rate kept for direct callers.

    Only active members drift. Wages are paid from available credits; shortfalls
    drain morale, and members below the resignation threshold may desert while
    the pay crisis lasts (seeded rng keeps desertion deterministic per stream).
    """
    from dataclasses import replace

    if rng is None:
        rng = random.Random()

    logs: list[str] = []
    upkeep = crew_upkeep(crew) * num_ticks if wage_due is None else max(0, wage_due)
    paid = min(upkeep, max(0, credits_available))
    unpaid = upkeep - paid
    updated: list[CrewMember] = []
    resigned: list[str] = []
    warned = False
    for member in crew:
        if member.status != "active":
            updated.append(member)
            continue
        morale = member.morale
        if unpaid > 0:
            morale = max(0.0, morale - 0.8 * num_ticks)
        else:
            morale = min(100.0, morale + 0.1 * num_ticks)
        if morale < RESIGN_MORALE and unpaid > 0:
            if rng.random() < min(0.5, RESIGN_CHANCE_PER_TICK * num_ticks):
                resigned.append(f"{member.name} ({member.role}) resigned over unpaid wages and abandoned ship.")
                continue
        if morale < CRITICAL_MORALE and not warned:
            logs.append(f"CREW MORALE CRITICAL: {member.name} is near desertion. Pay wages or grant shore leave.")
            warned = True
        updated.append(replace(member, morale=round(morale, 1)))
    if unpaid > 0:
        logs.append(f"CREW WAGES UNPAID: {unpaid} cr short; morale is falling.")
    for notice in resigned:
        logs.append(f"CREW RESIGNED: {notice}")
    return tuple(updated), paid, logs


def apply_morale_event(
    crew: Sequence[CrewMember],
    delta: float,
    reason: str,
) -> tuple[tuple[CrewMember, ...], str | None]:
    """Shift every active member's morale by an event delta, clamped to 0..100."""
    from dataclasses import replace

    if not crew or delta == 0:
        return tuple(crew), None
    updated = []
    for member in crew:
        if member.status != "active":
            updated.append(member)
            continue
        morale = max(0.0, min(100.0, member.morale + delta))
        updated.append(replace(member, morale=round(morale, 1)))
    sign = "+" if delta > 0 else ""
    return tuple(updated), f"CREW MORALE {sign}{delta:g} ({reason})."


def shore_leave_restore(crew: Sequence[CrewMember]) -> tuple[tuple[CrewMember, ...], int, int]:
    """Compute a fleet-wide shore leave outcome: restored crew and morale points.

    Returns (updated_crew, restored_points, credit_cost). Each active member
    recovers up to 35 morale; the credit cost scales with the total restored.
    """
    from dataclasses import replace

    per_member_cap = 35.0
    flat_fee = 25
    cost_per_point = 6
    updated = []
    restored = 0.0
    for member in crew:
        if member.status != "active":
            updated.append(member)
            continue
        deficit = max(0.0, 100.0 - member.morale)
        gain = min(per_member_cap, deficit)
        restored += gain
        updated.append(replace(member, morale=round(min(100.0, member.morale + gain), 1)))
    cost = flat_fee + int(cost_per_point * restored) if restored > 0 else 0
    return tuple(updated), int(restored), cost


def crew_catalog() -> list[dict[str, Any]]:
    return [role.to_dict() for role in CREW_ROLES]
