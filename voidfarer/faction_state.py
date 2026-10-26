"""Dynamic faction leaders, behaviors, war resolution, and elimination."""

from __future__ import annotations

import math
import random
from dataclasses import replace
from typing import Any, Sequence

from voidfarer.factions import CANONICAL_FACTIONS
from voidfarer.models import FactionLeader, StarSystem, WarState

LEADER_ARCHETYPES: dict[str, dict[str, Any]] = {
    "militarist": {"aggression": 0.85, "diplomacy": 0.25, "ambition": 0.75},
    "merchant": {"aggression": 0.30, "diplomacy": 0.75, "ambition": 0.55},
    "isolationist": {"aggression": 0.20, "diplomacy": 0.45, "ambition": 0.25},
    "opportunist": {"aggression": 0.60, "diplomacy": 0.55, "ambition": 0.85},
    "visionary": {"aggression": 0.35, "diplomacy": 0.70, "ambition": 0.65},
}

LEADER_NAMES: tuple[str, ...] = (
    "Admiral Vance", "Director Sable", "Archon Ilsa", "Warlord Kaez", "Magister Orun",
    "Consul Mira", "Captain Voss", "Prime HALCYON", "Prefect Dain", "Envoy Tessa",
)

LEADER_TITLES: tuple[str, ...] = (
    "High Admiral", "Trade Director", "Archon", "Warlord", "Magister",
    "First Consul", "Fleet Marshal", "Prime Intelligence", "Prefect", "Chief Envoy",
)


def generate_faction_leaders(seed: int) -> tuple[FactionLeader, ...]:
    """Create one deterministic leader per canonical sovereign faction."""
    rng = random.Random(int(seed) * 104_729 + 17)
    archetypes = list(LEADER_ARCHETYPES)
    leaders: list[FactionLeader] = []
    for index, (faction_id, faction) in enumerate(CANONICAL_FACTIONS.items()):
        archetype = archetypes[index % len(archetypes)]
        profile = LEADER_ARCHETYPES[archetype]
        leaders.append(FactionLeader(
            id=f"leader_{faction_id}",
            faction_id=faction_id,
            name=LEADER_NAMES[index % len(LEADER_NAMES)],
            title=LEADER_TITLES[index % len(LEADER_TITLES)],
            behavior=archetype,
            aggression=profile["aggression"],
            diplomacy=profile["diplomacy"],
            ambition=profile["ambition"],
        ))
    return tuple(leaders)


def _faction_systems(faction_id: str, systems: dict[str, StarSystem]) -> list[str]:
    target = CANONICAL_FACTIONS.get(faction_id)
    name = target.name if target else faction_id
    return [sid for sid, system in systems.items() if system.faction == name]


def faction_strength(faction_id: str, systems: dict[str, StarSystem]) -> float:
    owned = _faction_systems(faction_id, systems)
    population = sum(
        body.population
        for sid in owned
        for body in systems[sid].bodies
    )
    return len(owned) * 100.0 + population / 1_000_000.0


# A side converts this much war score into one captured front system, then spends it.
WAR_CAPTURE_THRESHOLD = 12.0
# Wars end in a treaty after this many ticks, or once this many systems changed hands.
WAR_EXHAUSTION_TICKS = 240
WAR_MAX_CAPTURES = 3
# Strength advantage moves the score by up to this much per resolution step.
WAR_MOMENTUM = 3.0
WAR_NOISE = 2.5
# Every system beyond the core dilutes a faction's war effort (administrative overextension).
WAR_CORE_SIZE = 3
WAR_OVEREXTENSION = 0.35
# Attrition pulls the score back toward a stalemate each step, so only a sustained edge
# (steady state = momentum / attrition) reaches the capture threshold.
WAR_ATTRITION = 0.05
# A faction holding this share of the galaxy faces a containment coalition.
WAR_HEGEMON_SHARE = 0.4
WAR_CONTAINMENT_EDGE = 1.2
# Realms below their core size fight a last stand: this edge per missing core system.
WAR_LAST_STAND_EDGE = 0.6
# After a treaty the same two factions keep the peace this long.
WAR_TRUCE_TICKS = 600
# Chance per tick that aggressive leaders consider a new war (capped per batch).
WAR_DECLARATION_RATE = 0.025


def _faction_name(faction_id: str) -> str:
    return CANONICAL_FACTIONS[faction_id].name if faction_id in CANONICAL_FACTIONS else faction_id


def war_effort(faction_id: str, systems: dict[str, StarSystem]) -> float:
    """Strength a faction can actually project at the front.

    Territory dominates; population adds a logarithmic industrial base so a populous capital
    helps without deciding wars alone. Large realms pay an overextension penalty.
    """
    owned = _faction_systems(faction_id, systems)
    population_millions = sum(body.population for sid in owned for body in systems[sid].bodies) / 1_000_000.0
    base = len(owned) * 100.0 + 60.0 * math.log10(1.0 + population_millions)
    return base / (1.0 + WAR_OVEREXTENSION * max(0, len(owned) - WAR_CORE_SIZE))


def war_momentum(attacker_id: str, defender_id: str, systems: dict[str, StarSystem]) -> float:
    """Per-step score drift before noise: effort ratio, defender edge and hegemon containment."""
    attack, defend = war_effort(attacker_id, systems), war_effort(defender_id, systems)
    momentum = WAR_MOMENTUM * (attack - defend) / max(1.0, attack + defend)
    total = max(1, len(systems))
    attacker_owned = len(_faction_systems(attacker_id, systems))
    defender_owned = len(_faction_systems(defender_id, systems))
    if attacker_owned / total >= WAR_HEGEMON_SHARE:
        momentum -= WAR_CONTAINMENT_EDGE
    if defender_owned / total >= WAR_HEGEMON_SHARE:
        momentum += WAR_CONTAINMENT_EDGE
    momentum -= WAR_LAST_STAND_EDGE * max(0, WAR_CORE_SIZE - defender_owned)
    return momentum


def _capture_target(front: list[str], loser_id: str, loser_name: str, score: float,
                    systems: dict[str, StarSystem], rng: random.Random) -> str | None:
    """Front worlds fall first; a capital only falls to double the capture score."""
    capital = CANONICAL_FACTIONS[loser_id].headquarters_system if loser_id in CANONICAL_FACTIONS else None
    outer = [sid for sid in front if sid != capital]
    if outer:
        return rng.choice(outer)
    if not front:
        return None
    if len(_faction_systems(loser_id, systems)) > 1:
        return None
    return front[0] if abs(score) >= 2 * WAR_CAPTURE_THRESHOLD else None


def _devastate_system(
    system: StarSystem,
    rng: random.Random,
    severity: float = 1.0,
) -> tuple[StarSystem, int]:
    """A captured front loses civilians and gains persistent devastation."""
    bodies = []
    lost_total = 0
    for body in system.bodies:
        if body.population <= 0:
            bodies.append(replace(body, devastation=min(100.0, (body.devastation or 0.0) + 2.0 * severity)))
            continue
        loss_rate = rng.uniform(0.018, 0.052) * max(0.4, severity)
        lost = max(1, int(body.population * loss_rate))
        lost_total += lost
        bodies.append(
            replace(
                body,
                population=max(0, body.population - lost),
                devastation=min(100.0, (body.devastation or 0.0) + rng.uniform(14.0, 28.0) * severity),
            )
        )
    return replace(system, bodies=tuple(bodies)), lost_total


def frontier_systems(winner_name: str, loser_name: str, systems: dict[str, StarSystem]) -> list[str]:
    """Loser-held systems with a hyperlane into winner territory, sorted for determinism."""
    return sorted(
        sid for sid, system in systems.items()
        if system.faction == loser_name
        and any(systems[n].faction == winner_name for n in system.connections if n in systems)
    )


def _end_war(war: WarState, score: float, current_tick: int, logs: list[str]) -> WarState:
    attacker, defender = _faction_name(war.attacker_id), _faction_name(war.defender_id)
    if not war.captured_systems:
        outcome = "status quo restored"
    else:
        outcome = f"{len(war.captured_systems)} system(s) changed hands"
    logs.append(f"PEACE: {attacker} and {defender} sign a treaty; {outcome}.")
    return replace(war, war_score=round(score, 2), active=False, ended_tick=current_tick)


def resolve_wars(
    wars: Sequence[WarState],
    systems: dict[str, StarSystem],
    rng: random.Random,
    current_tick: int,
    eliminated: tuple[str, ...],
) -> tuple[tuple[WarState, ...], dict[str, StarSystem], tuple[str, ...], list[str]]:
    """Advance wars one step: strength drives momentum, captures follow hyperlane fronts.

    Positive score favours the attacker. Reaching the threshold captures one front system
    and spends the threshold; with no shared border the advance stalls at half. Wars end in
    a treaty after WAR_EXHAUSTION_TICKS or WAR_MAX_CAPTURES captures, or when a side is gone.
    """
    logs: list[str] = []
    updated_wars: list[WarState] = []
    updated_systems = dict(systems)
    removed = set(eliminated)
    for war in wars:
        if not war.active:
            updated_wars.append(war)
            continue
        attacker_name, defender_name = _faction_name(war.attacker_id), _faction_name(war.defender_id)
        momentum = war_momentum(war.attacker_id, war.defender_id, updated_systems)
        score = war.war_score * (1.0 - WAR_ATTRITION) + momentum + rng.uniform(-WAR_NOISE, WAR_NOISE)
        captured = war.captured_systems
        if abs(score) >= WAR_CAPTURE_THRESHOLD:
            sign = 1.0 if score > 0 else -1.0
            winner_name, loser_name = (attacker_name, defender_name) if sign > 0 else (defender_name, attacker_name)
            loser_id = war.defender_id if sign > 0 else war.attacker_id
            front = frontier_systems(winner_name, loser_name, updated_systems)
            target = _capture_target(front, loser_id, loser_name, score, updated_systems, rng)
            if target is not None:
                updated_systems[target] = replace(updated_systems[target], faction=winner_name)
                severity = 2.0 if abs(score) >= 2 * WAR_CAPTURE_THRESHOLD else 1.0
                updated_systems[target], civilians_lost = _devastate_system(
                    updated_systems[target], rng, severity
                )
                captured = captured + (target,)
                score -= sign * WAR_CAPTURE_THRESHOLD
                logs.append(
                    f"WAR: {winner_name} captured {updated_systems[target].name} from {loser_name}; "
                    f"{civilians_lost:,} civilians displaced and the world left devastated."
                )
            elif not front:
                # No shared border: the offensive stalls until a front opens.
                score = sign * WAR_CAPTURE_THRESHOLD / 2
            else:
                # Only a defended capital faces the attacker: the siege holds below double score.
                score = sign * min(abs(score), 2 * WAR_CAPTURE_THRESHOLD - 0.01)
        war = replace(war, war_score=round(score, 2), captured_systems=captured)

        gone = next(
            (fid for fid in (war.attacker_id, war.defender_id)
             if not _faction_systems(fid, updated_systems)),
            None,
        )
        if gone is not None:
            if gone not in removed:
                removed.add(gone)
                logs.append(f"FACTION ELIMINATED: {gone} has no remaining territory.")
            updated_wars.append(replace(war, active=False, ended_tick=current_tick))
        elif len(captured) >= WAR_MAX_CAPTURES or current_tick - war.started_tick >= WAR_EXHAUSTION_TICKS:
            updated_wars.append(_end_war(war, score, current_tick, logs))
        else:
            updated_wars.append(war)
    return tuple(updated_wars), updated_systems, tuple(sorted(removed)), logs


def simulate_faction_behaviors(
    leaders: Sequence[FactionLeader],
    wars: Sequence[WarState],
    systems: dict[str, StarSystem],
    rng: random.Random,
    current_tick: int,
    eliminated: tuple[str, ...],
    num_ticks: int = 1,
) -> tuple[tuple[WarState, ...], dict[str, StarSystem], tuple[str, ...], list[str]]:
    """Apply leader archetypes: declare wars, then resolve active fronts."""
    logs: list[str] = []
    # Active wars and recent treaties both block a new declaration between the same pair.
    active_pairs = {
        frozenset((w.attacker_id, w.defender_id)) for w in wars
        if w.active or (w.ended_tick is not None and current_tick - w.ended_tick < WAR_TRUCE_TICKS)
    }
    new_wars = list(wars)
    living = [
        fid for fid in CANONICAL_FACTIONS
        if fid not in eliminated and _faction_systems(fid, systems)
    ]
    if len(living) >= 2 and rng.random() < min(0.30, WAR_DECLARATION_RATE * num_ticks):
        for leader in leaders:
            if leader.faction_id not in living or leader.aggression < 0.55:
                continue
            # No dogpiling: a faction already defending one war cannot be attacked again.
            defending = {w.defender_id for w in new_wars if w.active}
            targets = [
                fid for fid in living
                if fid != leader.faction_id and fid not in defending
                and frozenset((leader.faction_id, fid)) not in active_pairs
            ]
            if not targets:
                continue
            weakest = min(targets, key=lambda fid: faction_strength(fid, systems))
            pair = frozenset((leader.faction_id, weakest))
            if rng.random() > leader.aggression * 0.45:
                continue
            war = WarState(
                id=f"war_{current_tick}_{leader.faction_id}_{weakest}",
                attacker_id=leader.faction_id,
                defender_id=weakest,
                started_tick=current_tick,
            )
            new_wars.append(war)
            active_pairs.add(pair)
            attacker_name = CANONICAL_FACTIONS[leader.faction_id].name
            defender_name = CANONICAL_FACTIONS[weakest].name if weakest in CANONICAL_FACTIONS else weakest
            logs.append(f"WAR DECLARED: {attacker_name} ({leader.name}) moves against {defender_name}.")
            break

    resolved_wars, systems, eliminated_now, war_logs = resolve_wars(
        new_wars, systems, rng, current_tick, eliminated
    )
    logs.extend(war_logs)
    return resolved_wars, systems, eliminated_now, logs


def leader_for(leaders: Sequence[FactionLeader], faction_id: str) -> FactionLeader | None:
    return next((l for l in leaders if l.faction_id == faction_id), None)
