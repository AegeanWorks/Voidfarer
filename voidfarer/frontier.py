"""Frontier systems: autonomous captains, depots, mercenaries, and quantum messages."""

from __future__ import annotations

import random
from dataclasses import replace
from typing import Any

from voidfarer.economy import MAX_STOCK, MIN_STOCK
from voidfarer.models import AICaptain, Depot, GlobalEconomyState, QuantumMessage, StarSystem, SystemMarketState

MERCENARY_CATALOG: dict[str, dict[str, Any]] = {
    "merc_ironclad": {
        "id": "merc_ironclad",
        "name": "Ironclad Vanguard",
        "cost": 3200,
        "damage": 14,
        "hull": 90,
        "specialty": "assault",
        "description": "Heavy breaching pod. Adds +14 laser damage and +90 hull support in fleet combat.",
    },
    "merc_ghost": {
        "id": "merc_ghost",
        "name": "Ghost Signal",
        "cost": 2600,
        "damage": 8,
        "hull": 55,
        "specialty": "evasion",
        "description": "Electronic warfare specialist. Adds +8 damage and +10% counter-battery evasion.",
    },
    "merc_medic": {
        "id": "merc_medic",
        "name": "Lazarus Medic",
        "cost": 2200,
        "damage": 4,
        "hull": 60,
        "specialty": "repair",
        "description": "Combat triage unit. Adds +4 damage and restores 8 hull after each victory.",
    },
}

AI_CAPTAIN_SEEDS: tuple[tuple[str, str, str], ...] = (
    ("captain_vega", "Captain Vega", "trader"),
    ("captain_nyx", "Nyx the Broker", "trader"),
    ("captain_rorik", "Rorik Ironjaw", "mercenary"),
    ("captain_sable", "Sable Voss", "ally"),
    ("captain_kade", "Kade Redshift", "pirate"),
)


def generate_ai_captains(systems: dict[str, StarSystem], seed: int = 42) -> tuple[AICaptain, ...]:
    """Create a deterministic roster of autonomous captains distributed across the galaxy."""
    rng = random.Random(seed + 9001)
    system_ids = sorted(systems)
    # Home a *stationary* captain in Sol: traders roam, so a home trader would leave local
    # space empty after one tick. Reassigning which seed sits where consumes no RNG.
    home_index = next(
        (i for i, (_, _, archetype) in enumerate(AI_CAPTAIN_SEEDS) if archetype != "trader"),
        0,
    )
    non_home = [sid for sid in system_ids if sid != "sol"] or system_ids
    cursor = 0
    captures: list[AICaptain] = []
    for index, (captain_id, name, archetype) in enumerate(AI_CAPTAIN_SEEDS):
        if "sol" in systems and index == home_index:
            system_id = "sol"
        else:
            system_id = non_home[cursor % len(non_home)] if non_home else "sol"
            cursor += 1
        captures.append(
            AICaptain(
                id=captain_id,
                name=name,
                archetype=archetype,
                system_id=system_id,
                credits=rng.randint(1200, 6500),
                cargo={"titanium": rng.randint(2, 12), "fuel_cells": rng.randint(1, 6)},
                standing=rng.randint(-10, 25),
                trust=rng.randint(10, 40),
                hull=120,
                max_hull=120,
                damage=18 if archetype in ("mercenary", "pirate") else 10,
                description={
                    "trader": "Independent hauler moving commodities along the hyperlane circuit.",
                    "mercenary": "Private military contractor available for hire at friendly stations.",
                    "ally": "Diplomatic envoy seeking reliable partners in the outer systems.",
                    "pirate": "Opportunistic raider with a price on their transponder.",
                }.get(archetype, "Independent spacefarer."),
            )
        )
    return tuple(captures)


def generate_depots(systems: dict[str, StarSystem]) -> tuple[Depot, ...]:
    """Create one system-local depot per star system."""
    depots: list[Depot] = []
    for sys_id, system in sorted(systems.items()):
        depots.append(
            Depot(
                id=f"depot_{sys_id}",
                name=f"{system.name} Cargo Depot",
                system_id=sys_id,
                capacity=200,
            )
        )
    return tuple(depots)


def generate_welcome_messages(tick: int = 0) -> tuple[QuantumMessage, ...]:
    """Seed the inbox with onboarding quantum messages."""
    return (
        QuantumMessage(
            id="msg_welcome",
            sender="Admiral Vance",
            recipient="Commander",
            subject="Quantum Link Established",
            body="The intergalactic quantum relay is online. You may now exchange encrypted messages with captains and factions from any system.",
            tick=tick,
        ),
        QuantumMessage(
            id="msg_depot",
            sender="Sol Logistics",
            recipient="Commander",
            subject="Depot Access Granted",
            body="Your first cargo depot is active in Sol. Dock at a station to deposit, withdraw, or sell stored cargo directly from the depot.",
            tick=tick,
        ),
    )


def _adjust_stock(market: SystemMarketState, commodity_id: str, delta: int) -> SystemMarketState:
    stocks = dict(market.stockpiles)
    stocks[commodity_id] = max(MIN_STOCK, min(MAX_STOCK, stocks.get(commodity_id, 50) + delta))
    return replace(market, stockpiles=stocks)


def simulate_ai_trade(
    captains: tuple[AICaptain, ...],
    economy: GlobalEconomyState,
    systems: dict[str, StarSystem],
    rng: random.Random,
) -> tuple[tuple[AICaptain, ...], GlobalEconomyState, list[str]]:
    """Move AI traders between systems and mutate local stockpiles through buys and sells."""
    markets = dict(economy.markets)
    updated: list[AICaptain] = []
    logs: list[str] = []

    for captain in captains:
        if captain.archetype != "trader" or captain.system_id not in systems:
            updated.append(captain)
            continue

        origin = systems[captain.system_id]
        neighbors = [sid for sid in origin.connections if sid in systems and sid in markets]
        if not neighbors:
            updated.append(captain)
            continue

        target_id = rng.choice(neighbors)
        origin_market = markets.get(captain.system_id)
        target_market = markets.get(target_id)
        if origin_market is None or target_market is None or not origin_market.stockpiles:
            updated.append(captain)
            continue

        commodity_id = max(origin_market.stockpiles, key=lambda cid: origin_market.stockpiles.get(cid, 0))
        requested = min(4, max(1, captain.credits // 120))
        stock = origin_market.stockpiles.get(commodity_id, 0)
        # Never lift stock out of the reserve floor: the clamp would mint the difference.
        movable = max(0, stock - MIN_STOCK)
        quantity = min(requested, movable)
        if quantity <= 0:
            # Keep the shared RNG stream identical to the old trade path.
            if stock > requested:
                rng.randint(0, 20)
            updated.append(captain)
            continue
        markets[captain.system_id] = _adjust_stock(origin_market, commodity_id, -quantity)
        markets[target_id] = _adjust_stock(target_market, commodity_id, quantity)
        profit = max(10, quantity * (25 + rng.randint(0, 20)))
        updated_cargo = dict(captain.cargo)
        updated_cargo[commodity_id] = updated_cargo.get(commodity_id, 0) + quantity
        updated.append(
            replace(
                captain,
                system_id=target_id,
                credits=captain.credits + profit,
                cargo=updated_cargo,
                trust=min(100, captain.trust + 1),
            )
        )
        logs.append(f"AI TRADE: {captain.name} moved {quantity}x {commodity_id} to {target_id}.")

    return tuple(updated), replace(economy, markets=markets, last_updated_tick=economy.last_updated_tick + 1), logs
