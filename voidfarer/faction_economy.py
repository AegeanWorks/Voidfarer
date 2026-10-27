"""Basic per-faction economy: tax base, industry, upkeep, treasury and war burden."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from voidfarer.demographics import FACTION_TECH_LEVELS
from voidfarer.factions import CANONICAL_FACTIONS
from voidfarer.models import FactionEconomy, StarSystem, WarState


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
) -> FactionEconomy:
    """Derive one faction's population, output, wartime burden and per-tick cash flow."""
    canonical_id, faction_name = _faction_identity(faction_id)
    owned = _owned_systems(faction_name, systems)
    population = sum(body.population for system in owned for body in system.bodies)
    worlds = sum(1 for system in owned for body in system.bodies if body.population > 0)
    tech = FACTION_TECH_LEVELS.get(faction_name, FACTION_TECH_LEVELS["Unclaimed"])
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
    trade_income = int(population_millions * 0.004 + len(owned) * 2)
    industrial_output = int(
        population_millions
        * 0.008
        * (1.0 + tech / 10.0)
        * (1.0 - weighted_devastation / 100.0)
    )
    military_upkeep = int(worlds * 6 + active_wars * 45)
    net_income = tax_income + trade_income + industrial_output - military_upkeep

    return FactionEconomy(
        faction_id=canonical_id,
        treasury=max(0, int(treasury)),
        population=max(0, int(population)),
        worlds=worlds,
        tech_level=tech,
        stability=round(new_stability, 1),
        tax_income=max(0, tax_income),
        trade_income=max(0, trade_income),
        industrial_output=max(0, industrial_output),
        military_upkeep=max(0, military_upkeep),
        war_burden=round(war_burden, 3),
        net_income=net_income,
    )


def initialize_faction_economies(
    systems: dict[str, StarSystem],
    wars: Sequence[WarState] = (),
    eliminated: Sequence[str] = (),
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
        economy = compute_faction_economy(faction_id, systems, wars, treasury=opening, stability=50.0)
        economies.append(replace(economy, treasury=opening))
    return tuple(economies)


def tick_faction_economies(
    economies: Sequence[FactionEconomy],
    systems: dict[str, StarSystem],
    wars: Sequence[WarState],
    eliminated: Sequence[str],
    num_ticks: int = 1,
) -> tuple[tuple[FactionEconomy, ...], list[str]]:
    """Advance faction treasuries and report when a war drains one dry."""
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
        )
        new_treasury = max(0, economy.treasury + report.net_income * max(0, int(num_ticks)))
        if economy.treasury > 0 and new_treasury == 0 and report.net_income < 0:
            name = CANONICAL_FACTIONS.get(economy.faction_id)
            logs.append(
                f"TREASURY EXHAUSTED: {name.name if name else economy.faction_id} cannot pay its wartime upkeep."
            )
        updated.append(replace(report, treasury=new_treasury))
    return tuple(updated), logs
