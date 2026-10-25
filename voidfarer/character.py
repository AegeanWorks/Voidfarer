"""Commander character progression, skills, and activatable abilities."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from voidfarer.models import PlayerCharacter

SKILL_CATALOG: dict[str, dict[str, Any]] = {
    "piloting": {"name": "Piloting", "description": "Travel speed, evasion, and fuel discipline."},
    "engineering": {"name": "Engineering", "description": "Reactor cooling, repairs, and outpost construction."},
    "science": {"name": "Science", "description": "Scan yield and research generation."},
    "combat": {"name": "Combat", "description": "Weapon damage and tactical ability power."},
    "diplomacy": {"name": "Diplomacy", "description": "Faction relations and war de-escalation."},
    "trade": {"name": "Trade", "description": "Market margins and convoy income."},
}

STARTING_SKILL_BASE = 5
STARTING_SKILL_POINTS = 20
MAX_STARTING_SKILL_TOTAL = len(SKILL_CATALOG) * STARTING_SKILL_BASE + STARTING_SKILL_POINTS

ABILITY_CATALOG: dict[str, dict[str, Any]] = {
    "overclock": {
        "name": "Reactor Overclock",
        "description": "Push the core into a timed surge: +25% subsystem output for 8 ticks at a heat cost.",
        "cooldown": 20,
        "skill": "engineering",
    },
    "emergency_repair": {
        "name": "Emergency Repair",
        "description": "Nano-weld hull damage in flight.",
        "cooldown": 10,
        "skill": "engineering",
    },
    "battle_focus": {
        "name": "Battle Focus",
        "description": "Read hostile telemetry and gain a tactical combo during combat.",
        "cooldown": 6,
        "skill": "combat",
    },
    "charm_offensive": {
        "name": "Diplomatic Offensive",
        "description": "Leverage reputation to improve faction standing.",
        "cooldown": 12,
        "skill": "diplomacy",
    },
    "science_burst": {
        "name": "Science Burst",
        "description": "Synchronize sensor arrays for an immediate research surge.",
        "cooldown": 10,
        "skill": "science",
    },
    "trade_instinct": {
        "name": "Trade Instinct",
        "description": "Exploit local market inefficiencies for instant credits.",
        "cooldown": 12,
        "skill": "trade",
    },
}

# Later powers unlock by investing in the matching skill; the first four are innate.
ABILITY_UNLOCKS: dict[str, dict[str, Any]] = {
    "charm_offensive": {"skill": "diplomacy", "rank": 7},
    "trade_instinct": {"skill": "trade", "rank": 7},
}


def skill_level(character: PlayerCharacter, skill: str) -> int:
    return int(character.skills.get(skill, 1))


def skill_bonus(character: PlayerCharacter, skill: str) -> float:
    """Percent bonus per skill level above baseline."""
    return max(0.0, (skill_level(character, skill) - 1) * 0.04)


def reconcile_abilities(character: PlayerCharacter) -> tuple[PlayerCharacter, list[str]]:
    """Append every ability whose skill requirement this character already meets."""
    abilities = tuple(character.abilities)
    extra = [
        ability_id for ability_id, requirement in ABILITY_UNLOCKS.items()
        if int(character.skills.get(requirement["skill"], 1)) >= requirement["rank"]
        and ability_id not in abilities
    ]
    if not extra:
        return character, []
    return replace(character, abilities=abilities + tuple(extra)), extra


def train_skill(character: PlayerCharacter, skill: str) -> tuple[bool, PlayerCharacter, str]:
    if skill not in SKILL_CATALOG:
        return False, character, f"Unknown skill '{skill}'."
    if character.skill_points <= 0:
        return False, character, "No skill points available. Level up the commander first."
    current = skill_level(character, skill)
    if current >= 10:
        return False, character, f"{SKILL_CATALOG[skill]['name']} is already at maximum rank."
    skills = dict(character.skills)
    skills[skill] = current + 1
    updated = replace(character, skills=skills, skill_points=character.skill_points - 1)
    updated, unlocked = reconcile_abilities(updated)
    msg = f"Trained {SKILL_CATALOG[skill]['name']} to rank {current + 1}."
    if unlocked:
        names = ", ".join(ABILITY_CATALOG[aid]["name"] for aid in unlocked)
        msg += f" Unlocked {names}."
    return True, updated, msg


def award_character_xp(character: PlayerCharacter, amount: int) -> tuple[PlayerCharacter, bool, str]:
    xp = character.xp + max(0, int(amount))
    level = character.level
    next_xp = character.next_level_xp
    points = character.skill_points
    while xp >= next_xp:
        xp -= next_xp
        level += 1
        points += 1
        next_xp = int(next_xp * 1.35)
    updated = replace(character, xp=xp, level=level, next_level_xp=next_xp, skill_points=points)
    if level > character.level:
        return updated, True, f"Commander promotion: level {level} (+1 skill point)."
    return updated, False, ""


def advance_age(character: PlayerCharacter, elapsed_days_before: float, elapsed_days_after: float) -> PlayerCharacter:
    years = int(elapsed_days_after // 365.25) - int(elapsed_days_before // 365.25)
    if years <= 0:
        return character
    return replace(character, age=character.age + years)


def ability_ready(character: PlayerCharacter, ability_id: str) -> bool:
    if ability_id not in ABILITY_CATALOG:
        return False
    if ability_id not in character.abilities:
        return False
    return int(character.ability_cooldowns.get(ability_id, 0)) <= 0


def start_ability_cooldown(character: PlayerCharacter, ability_id: str) -> PlayerCharacter:
    cooldowns = dict(character.ability_cooldowns)
    cooldowns[ability_id] = int(ABILITY_CATALOG[ability_id]["cooldown"])
    return replace(character, ability_cooldowns=cooldowns)


def tick_ability_cooldowns(character: PlayerCharacter, num_ticks: int) -> PlayerCharacter:
    if not character.ability_cooldowns or num_ticks <= 0:
        return character
    cooldowns = {
        key: max(0, value - num_ticks)
        for key, value in character.ability_cooldowns.items()
    }
    return replace(character, ability_cooldowns=cooldowns)
