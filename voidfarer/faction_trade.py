"""Faction-to-faction trade: hyperlane-adjacent, peaceful pairs exchange goods.

Links are derived each tick rather than stored as player state: a declaration of war
severs every route between the belligerents on the next tick, and a captured border
opens or closes lanes without a migration.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from voidfarer.factions import CANONICAL_FACTIONS
from voidfarer.models import FactionEconomy, StarSystem, TradeLink, WarState

# A route needs both partners to be reachable from one another by a hyperlane.
TRADE_BASE_FACTOR = 0.35
TRADE_LANE_FACTOR = 0.15
TRADE_MAX_LANES = 4
TRADE_POPULATION_SCALE = 1e8
TRADE_MAX_PARTNERS = 3
# Stability of the weaker partner gates how much actually moves.
TRADE_ORDER_FLOOR = 0.40


def _faction_name(faction_id: str) -> str:
    faction = CANONICAL_FACTIONS.get(faction_id)
    return faction.name if faction else faction_id


def _systems_owned(systems: dict[str, StarSystem], faction_name: str) -> list[StarSystem]:
    return [system for system in systems.values() if system.faction == faction_name]


def _cross_lanes(
    systems: dict[str, StarSystem],
    left_name: str,
    right_name: str,
) -> int:
    """Hyperlanes with one endpoint owned by each faction."""
    lanes = 0
    for system in systems.values():
        if system.faction != left_name:
            continue
        for neighbour in system.connections:
            other = systems.get(neighbour)
            if other is not None and other.faction == right_name:
                lanes += 1
    return lanes


def warring_pairs(wars: Sequence[WarState]) -> set[frozenset[str]]:
    """Canonical faction pairs currently fighting; their trade is blockaded."""
    return {
        frozenset((war.attacker_id, war.defender_id))
        for war in wars
        if war.active
    }


def compute_trade_links(
    systems: dict[str, StarSystem],
    wars: Sequence[WarState] = (),
    economies: Sequence[FactionEconomy] = (),
    eliminated: Iterable[str] = (),
) -> tuple[TradeLink, ...]:
    """Derive the strongest peaceful hyperlane routes, capped per faction."""
    removed = set(eliminated)
    blockaded = warring_pairs(wars)
    stability = {economy.faction_id: economy.stability for economy in economies}
    population = {
        fid: sum(
            body.population
            for system in _systems_owned(systems, _faction_name(fid))
            for body in system.bodies
        )
        for fid in CANONICAL_FACTIONS
    }
    living = [
        fid for fid in CANONICAL_FACTIONS
        if fid not in removed and population.get(fid, 0) > 0
    ]

    candidates: list[TradeLink] = []
    for index, left in enumerate(living):
        for right in living[index + 1:]:
            if frozenset((left, right)) in blockaded:
                continue
            lanes = _cross_lanes(systems, _faction_name(left), _faction_name(right))
            if lanes <= 0:
                continue
            pop_left, pop_right = population[left], population[right]
            order = (
                TRADE_ORDER_FLOOR
                + (1.0 - TRADE_ORDER_FLOOR)
                * min(stability.get(left, 50.0), stability.get(right, 50.0))
                / 100.0
            )
            factor = TRADE_BASE_FACTOR + min(lanes, TRADE_MAX_LANES) * TRADE_LANE_FACTOR
            volume = int(
                math.sqrt(pop_left * pop_right) / TRADE_POPULATION_SCALE * factor * order
            )
            if volume > 0:
                endpoint_a, endpoint_b = sorted((left, right))
                candidates.append(
                    TradeLink(faction_a=endpoint_a, faction_b=endpoint_b, volume=volume)
                )

    # Keep each faction's three richest routes so the player-facing summary stays simple.
    candidates.sort(key=lambda link: (-link.volume, link.faction_a, link.faction_b))
    kept: list[TradeLink] = []
    counts: dict[str, int] = {fid: 0 for fid in living}
    for link in candidates:
        if counts[link.faction_a] >= TRADE_MAX_PARTNERS:
            continue
        if counts[link.faction_b] >= TRADE_MAX_PARTNERS:
            continue
        counts[link.faction_a] += 1
        counts[link.faction_b] += 1
        kept.append(link)
    kept.sort(key=lambda link: (link.faction_a, link.faction_b))
    return tuple(kept)


def trade_income_for(faction_id: str, links: Sequence[TradeLink]) -> int:
    """Each route pays half its volume to each endpoint."""
    half_total = sum(
        link.volume // 2
        for link in links
        if faction_id in (link.faction_a, link.faction_b)
    )
    return int(half_total)


def trade_partners_for(faction_id: str, links: Sequence[TradeLink]) -> int:
    return sum(
        1 for link in links if faction_id in (link.faction_a, link.faction_b)
    )


def trade_partner_names(faction_id: str, links: Sequence[TradeLink]) -> list[str]:
    names: list[str] = []
    for link in links:
        if link.faction_a == faction_id:
            names.append(_faction_name(link.faction_b))
        elif link.faction_b == faction_id:
            names.append(_faction_name(link.faction_a))
    return sorted(names)
