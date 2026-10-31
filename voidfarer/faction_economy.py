"""Basic per-faction economy: tax base, industry, upkeep, treasury and war burden."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from voidfarer.demographics import (
    FACTION_TECH_LEVELS,
    MAX_TECH_LEVEL,
    TECH_PROGRESS_INDUSTRY,
    TECH_PROGRESS_ORDER,
    TECH_PROGRESS_PER_LEVEL,
    clamp_tech_level,
)
from voidfarer.faction_trade import trade_income_for, trade_partners_for
from voidfarer.factions import CANONICAL_FACTIONS
from voidfarer.models import FactionEconomy, StarSystem, TradeLink, WarState


def _owned_systems(faction_name: str, systems: dict[str, StarSystem]) -> list[StarSystem]:
    return [system for system in systems.values() if system.faction == faction_name]


def _faction_identity(faction_id: str) -> tuple[str, str]:
    faction = CANONICAL_FACTIONS.get(faction_id)
    if faction is None:
        return faction_id, faction_id
    return faction.id, faction.name


def compute_faction_economy(
    faction_id: str,
    systems: dict[str, StarSystem],
    wars: Sequence[WarState] = (),
    treasury: int = 0,
    stability: float = 50.0,
    trade_links: Sequence[TradeLink] = (),
    tech_level: int | None = None,
    tech_progress: float = 0.0,
    num_ticks: int = 1,
) -> FactionEconomy:
    """Derive one faction's population, output, wartime burden and per-tick cash flow."""
    canonical_id, faction_name = _faction_identity(faction_id)
    owned = _owned_systems(faction_name, systems)
    population = sum(body.population for system in owned for body in system.bodies)
    worlds = sum(1 for system in owned for body in system.bodies if body.population > 0)
    tech = clamp_tech_level(
        tech_level
        if tech_level is not None
        else FACTION_TECH_LEVELS.get(faction_name, FACTION_TECH_LEVELS["Unclaimed"])
    )
    active_wars = sum(
        1 for war in wars
        if war.active and canonical_id in (war.attacker_id, war.defender_id)
    )

    populated = [body for system in owned for body in system.bodies if body.population > 0]
    if populated:
        weighted_devastation = sum(
            body.devastation * body.population for body in populated
        ) / max(1, population)
    else:
        weighted_devastation = 0.0
    average_security = (
        sum(system.security for system in owned) / len(owned) if owned else 0.0
    )

    war_burden = min(1.0, active_wars * 0.18 + weighted_devastation / 100.0 * 0.6)
    stability_target = (
        45.0
        + tech * 2.5
        + average_security * 20.0
        - war_burden * 35.0
        + (5.0 if treasury > 0 else -10.0)
    )
    new_stability = max(0.0, min(100.0, stability * 0.85 + stability_target * 0.15))

    population_millions = population / 1_000_000.0
    tax_income = int(
        population_millions
        * 0.012
        * (0.5 + tech / 20.0)
        * (new_stability / 100.0)
        * (1.0 - war_burden * 0.5)
    )
    trade_income = (
        trade_income_for(canonical_id, trade_links)
        + int(population_millions * 0.001)
    )
    trade_partners = trade_partners_for(canonical_id, trade_links)
    industrial_output = int(
        population_millions
        * 0.008
        * (1.0 + tech / 10.0)
        * (1.0 - weighted_devastation / 100.0)
    )
    gross_income = tax_income + trade_income + industrial_output
    # Peacetime garrisons are cheap; a shooting war consumes a large share of the
    # economy, so two simultaneous fronts can outrun a treasury and force a peace.
    peacetime_upkeep = int(worlds * 8 + population_millions * 0.003)
    war_fraction = min(0.95, active_wars * 0.50 + weighted_devastation / 100.0 * 0.20)
    military_upkeep = peacetime_upkeep + int(gross_income * war_fraction)
    net_income = gross_income - military_upkeep

    # Research accumulates from industry and civil order; each 100 points is a tech level.
    progress = max(0.0, float(tech_progress))
    progress += (
        industrial_output * TECH_PROGRESS_INDUSTRY
        + new_stability * TECH_PROGRESS_ORDER
    ) * max(1, int(num_ticks))
    while progress >= TECH_PROGRESS_PER_LEVEL and tech < MAX_TECH_LEVEL:
        progress -= TECH_PROGRESS_PER_LEVEL
        tech += 1
    if tech >= MAX_TECH_LEVEL:
        progress = min(progress, TECH_PROGRESS_PER_LEVEL - 0.1)

    return FactionEconomy(
        faction_id=canonical_id,
        treasury=max(0, int(treasury)),
        population=max(0, int(population)),
        worlds=worlds,
        tech_level=tech,
        tech_progress=round(progress, 2),
        stability=round(new_stability, 1),
        tax_income=max(0, tax_income),
        trade_income=max(0, trade_income),
        trade_partners=trade_partners,
        industrial_output=max(0, industrial_output),
        military_upkeep=max(0, military_upkeep),
        war_burden=round(war_burden, 3),
        net_income=net_income,
    )


def initialize_faction_economies(
    systems: dict[str, StarSystem],
    wars: Sequence[WarState] = (),
    eliminated: Sequence[str] = (),
    trade_links: Sequence[TradeLink] = (),
) -> tuple[FactionEconomy, ...]:
    """Create opening treasuries for every surviving canonical faction."""
    removed = set(eliminated)
    economies: list[FactionEconomy] = []
    for faction_id, faction in CANONICAL_FACTIONS.items():
        if faction_id in removed:
            continue
        population = sum(
            body.population
            for system in systems.values()
            if system.faction == faction.name
            for body in system.bodies
        )
        opening = 50_000 + int(population / 1_000_000.0 * 2.0)
        economy = compute_faction_economy(
            faction_id,
            systems,
            wars,
            treasury=opening,
            stability=50.0,
            trade_links=trade_links,
        )
        economies.append(replace(economy, treasury=opening, tech_progress=0.0))
    return tuple(economies)


def tick_faction_economies(
    economies: Sequence[FactionEconomy],
    systems: dict[str, StarSystem],
    wars: Sequence[WarState],
    eliminated: Sequence[str],
    num_ticks: int = 1,
    trade_links: Sequence[TradeLink] = (),
) -> tuple[tuple[FactionEconomy, ...], list[str]]:
    """Advance faction treasuries, research and trade; report a war drain or a breakthrough."""
    removed = set(eliminated)
    updated: list[FactionEconomy] = []
    logs: list[str] = []
    for economy in economies:
        if economy.faction_id in removed:
            updated.append(economy)
            continue
        report = compute_faction_economy(
            economy.faction_id,
            systems,
            wars,
            treasury=economy.treasury,
            stability=economy.stability,
            trade_links=trade_links,
            tech_level=economy.tech_level,
            tech_progress=economy.tech_progress,
            num_ticks=num_ticks,
        )
        new_treasury = max(0, economy.treasury + report.net_income * max(0, int(num_ticks)))
        name = CANONICAL_FACTIONS.get(economy.faction_id)
        if report.tech_level > economy.tech_level:
            logs.append(
                f"TECH BREAKTHROUGH: {name.name if name else economy.faction_id} "
                f"reached tech level {report.tech_level}."
            )
        if economy.treasury > 0 and new_treasury == 0 and report.net_income < 0:
            logs.append(
                f"TREASURY EXHAUSTED: {name.name if name else economy.faction_id} cannot pay its wartime upkeep."
            )
        updated.append(replace(report, treasury=new_treasury))
    return tuple(updated), logs
