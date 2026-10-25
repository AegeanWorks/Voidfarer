"""Hostile Enemy Archetypes, Tactical Combat AI, and Procedural Intercept Generation."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from voidfarer.models import CombatEncounter


@dataclass(frozen=True)
class EnemyArchetype:
    """Blueprint for procedural hostile intercepts across galactic territories."""

    id: str
    name: str
    enemy_class: str
    faction_id: str
    base_hull: int
    base_shield: int
    base_damage: int
    special_ability: str  # 'none', 'emp_overload', 'shield_drain', 'nanite_regen', 'tachyon_lance'
    ability_desc: str
    bounty_credits: int
    salvage_commodity: str
    rep_rewards: dict[str, int]
    ai_profile: str = "aggressive"


ENEMY_ARCHETYPES: dict[str, EnemyArchetype] = {
    "corsair_interceptor": EnemyArchetype(
        id="corsair_interceptor",
        name="Corsair Interceptor",
        enemy_class="Light Raider",
        faction_id="outlaw_corsairs",
        base_hull=70,
        base_shield=25,
        base_damage=24,
        special_ability="none",
        ability_desc="High sub-light agility with rapid kinetic projectile barrages.",
        bounty_credits=450,
        salvage_commodity="fuel_cells",
        rep_rewards={"sol_coalition": 4, "outlaw_corsairs": -6},
        ai_profile="aggressive",
    ),
    "syndicate_marauder": EnemyArchetype(
        id="syndicate_marauder",
        name="Syndicate Marauder",
        enemy_class="Assault Frigate",
        faction_id="vanguard_syndicate",
        base_hull=105,
        base_shield=50,
        base_damage=30,
        special_ability="shield_drain",
        ability_desc="Siphons 15 MW energy from player shields to reinforce its own deflector grid.",
        bounty_credits=750,
        salvage_commodity="titanium",
        rep_rewards={"sol_coalition": 6, "vanguard_syndicate": -8},
        ai_profile="opportunist",
    ),
    "corporate_enforcer": EnemyArchetype(
        id="corporate_enforcer",
        name="Hyperion Tactical Enforcer",
        enemy_class="Security Cruiser",
        faction_id="hyperion_dynamics",
        base_hull=125,
        base_shield=65,
        base_damage=30,
        special_ability="emp_overload",
        ability_desc="Emits an electro-magnetic burst that drains laser power and strains weapon systems.",
        bounty_credits=900,
        salvage_commodity="microchips",
        rep_rewards={"outlaw_corsairs": 6, "hyperion_dynamics": -10},
        ai_profile="defensive",
    ),
    "precursor_sentinel": EnemyArchetype(
        id="precursor_sentinel",
        name="Archon Automated Sentinel",
        enemy_class="Alien Automaton",
        faction_id="precursor_watch",
        base_hull=150,
        base_shield=90,
        base_damage=40,
        special_ability="tachyon_lance",
        ability_desc="Fires a high-frequency tachyon beam that bypasses shields directly into ship hull.",
        bounty_credits=1200,
        salvage_commodity="xenoliths",
        rep_rewards={"precursor_watch": 8, "outlaw_corsairs": 4},
        ai_profile="adaptive",
    ),
    "warlord_dreadnought": EnemyArchetype(
        id="warlord_dreadnought",
        name="Void Warlord Flagship",
        enemy_class="Capital Dreadnought",
        faction_id="outlaw_corsairs",
        base_hull=240,
        base_shield=120,
        base_damage=48,
        special_ability="nanite_regen",
        ability_desc="Autonomous nanite swarms rapidly repair 20 hull damage while shields stay online.",
        bounty_credits=2500,
        salvage_commodity="xenoliths",
        rep_rewards={"sol_coalition": 15, "nebula_collective": 12, "vanguard_syndicate": 10, "outlaw_corsairs": -25},
        ai_profile="warlord",
    ),
}


INTENT_TELEGRAPHS = {
    "fire": "Weapons locked; charging main batteries",
    "brace": "Ablative plating rotating to absorb incoming fire",
    "evade": "Maneuvering thrusters primed for an evasive jink",
    "execute": "Targeting weak points for a killing blow",
    "ability": "Special weapon system charging to full power",
}

SPECIAL_TELEGRAPHS = {
    "shield_drain": "Energy siphon arrays locking onto flagship deflectors",
    "emp_overload": "EMP capacitors charging up for weapon disruption",
    "tachyon_lance": "Tachyon focal lenses aligning for phase-shield breach",
    "nanite_regen": "Nanite repair matrix deployed in automated standby",
}

# Dynamic difficulty: hostile forces answer a proven commander with heavier metal.
THREAT_SCALE_PER_LEVEL = 0.05
THREAT_SCALE_CAP = 0.75
DREADNOUGHT_MIN_THREAT_LEVEL = 4


def threat_multiplier(threat_level: int) -> float:
    """Scale generated intercept strength with the pilot's command experience.

    A fresh pilot (level 1) keeps the original archetype numbers. Each later
    level adds 5% hull, shields and damage (bounty follows at 80% of the same
    curve), capped at +75%.
    """
    try:
        level = int(threat_level)
    except (TypeError, ValueError):
        level = 1
    return 1.0 + min(THREAT_SCALE_CAP, max(0, level - 1) * THREAT_SCALE_PER_LEVEL)


def choose_enemy_intent(
    profile: str,
    special_ability: str,
    ability_ready: bool,
    enemy_hull: int,
    enemy_max_hull: int,
    enemy_shield: int,
    enemy_max_shield: int,
    player_hull: int,
    player_max_hull: int,
    player_shield: int,
    player_max_shield: int,
    player_combo: int,
) -> tuple[str, str]:
    """Pick the next hostile maneuver from hull, shield, combo, and AI profile state."""
    enemy_hp = enemy_hull / max(1, enemy_max_hull)
    enemy_sh = enemy_shield / max(1, enemy_max_shield)
    player_hp = player_hull / max(1, player_max_hull)
    player_sh = player_shield / max(1, player_max_shield)
    has_ability = ability_ready and special_ability != "none"

    if profile == "warlord":
        if enemy_hp < 0.55 and special_ability == "nanite_regen" and has_ability:
            return "ability", SPECIAL_TELEGRAPHS[special_ability]
        if player_hp < 0.35:
            return "execute", INTENT_TELEGRAPHS["execute"]
        if player_combo >= 2:
            return "brace", INTENT_TELEGRAPHS["brace"]
    elif profile == "defensive":
        if player_combo >= 2:
            return "brace", INTENT_TELEGRAPHS["brace"]
        if player_sh < 0.30 and has_ability and special_ability == "emp_overload":
            return "ability", SPECIAL_TELEGRAPHS[special_ability]
        if enemy_hp < 0.35 or enemy_sh < 0.25:
            return "brace", INTENT_TELEGRAPHS["brace"]
    elif profile == "opportunist":
        if player_hp <= 0.35:
            return "execute", INTENT_TELEGRAPHS["execute"]
        if player_sh > 0.40 and has_ability and special_ability == "shield_drain":
            return "ability", SPECIAL_TELEGRAPHS[special_ability]
        if enemy_sh < 0.20 and has_ability and special_ability == "tachyon_lance":
            return "ability", SPECIAL_TELEGRAPHS[special_ability]
    elif profile == "adaptive":
        if player_combo >= 3 and has_ability:
            return "ability", SPECIAL_TELEGRAPHS[special_ability]
        if player_hp < 0.30 and has_ability:
            return "ability", SPECIAL_TELEGRAPHS[special_ability]
        if enemy_hp < 0.30:
            return "evade", INTENT_TELEGRAPHS["evade"]
        if player_combo >= 2:
            return "brace", INTENT_TELEGRAPHS["brace"]
    else:  # aggressive
        if player_hp < 0.35:
            return "execute", INTENT_TELEGRAPHS["execute"]
        if has_ability:
            return "ability", SPECIAL_TELEGRAPHS[special_ability]
        if player_combo >= 3:
            return "brace", INTENT_TELEGRAPHS["brace"]

    if has_ability and (enemy_sh < 0.50 or player_sh > 0.50):
        return "ability", SPECIAL_TELEGRAPHS[special_ability]
    return "fire", INTENT_TELEGRAPHS["fire"]


def generate_system_enemy(
    system_id: str,
    security: float,
    faction: str,
    seed: int | None = None,
    threat_level: int = 1,
) -> CombatEncounter:
    """Generate a procedurally balanced CombatEncounter matching star system characteristics."""
    rng = random.Random(seed)
    threat = threat_multiplier(threat_level)
    try:
        level = int(threat_level)
    except (TypeError, ValueError):
        level = 1

    # Low security boss spawn chance (Capital Dreadnought) only for proven pilots.
    # The roll is still consumed for low-security systems at every level so the
    # seeded archetype sequence stays stable for existing saves.
    boss_roll = rng.random() if security < 0.20 else 1.0
    if security < 0.20 and level >= DREADNOUGHT_MIN_THREAT_LEVEL and boss_roll < 0.30:
        arch = ENEMY_ARCHETYPES["warlord_dreadnought"]
    elif "pulsar" in system_id.lower() or "cygnus" in system_id.lower() or "precursor" in faction.lower():
        arch = ENEMY_ARCHETYPES["precursor_sentinel"]
    elif security >= 0.70:
        # High security corporate or light corsair infiltrator
        choices = ["corporate_enforcer", "corsair_interceptor"]
        arch = ENEMY_ARCHETYPES[rng.choice(choices)]
    elif security >= 0.35:
        # Mid security syndicate or raider
        choices = ["syndicate_marauder", "corsair_interceptor"]
        arch = ENEMY_ARCHETYPES[rng.choice(choices)]
    else:
        # Outlaw pirate infested
        choices = ["corsair_interceptor", "syndicate_marauder"]
        arch = ENEMY_ARCHETYPES[rng.choice(choices)]

    # Slight variance (+/- 10%) plus progression threat scaling.
    hull_var = int(arch.base_hull * rng.uniform(0.9, 1.15) * threat)
    shield_var = int(arch.base_shield * rng.uniform(0.9, 1.15) * threat)
    dmg_var = int(arch.base_damage * rng.uniform(0.95, 1.10) * threat)
    bounty = int(arch.bounty_credits * (1.0 + (threat - 1.0) * 0.8))

    initial_telegraph = "Weapons powering up; calibrating fire control"
    if arch.special_ability == "shield_drain":
        initial_telegraph = "Energy siphon arrays locking onto flagship deflectors"
    elif arch.special_ability == "emp_overload":
        initial_telegraph = "EMP capacitors charging up for weapon disruption"
    elif arch.special_ability == "tachyon_lance":
        initial_telegraph = "Tachyon focal lenses aligning for phase-shield breach"
    elif arch.special_ability == "nanite_regen":
        initial_telegraph = "Nanite repair matrix deployed in automated standby"

    return CombatEncounter(
        id=f"combat_{system_id}_{rng.randint(100, 999)}",
        enemy_name=arch.name,
        enemy_class=arch.enemy_class,
        enemy_hull=hull_var,
        enemy_max_hull=hull_var,
        enemy_damage=dmg_var,
        bounty_credits=bounty,
        salvage_commodity=arch.salvage_commodity,
        enemy_shield=shield_var,
        enemy_max_shield=shield_var,
        faction_id=arch.faction_id,
        special_ability=arch.special_ability,
        ability_cooldown=0,
        telegraphed_action=initial_telegraph,
        ai_profile=arch.ai_profile,
        enemy_intent="fire",
        archetype_id=arch.id,
    )
