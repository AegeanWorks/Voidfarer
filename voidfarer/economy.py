"""Dynamic Global Economy, supply/demand simulation, economic events, and galactic trade network."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import random
from typing import Any, Sequence

from voidfarer.models import (
    CelestialBody,
    Commodity,
    EconomicEvent,
    GlobalEconomyState,
    MarketQuote,
    StarSystem,
    SystemMarketState,
)


# Canonical production archetypes
ARCHETYPE_PRODUCTIONS: dict[str, dict[str, int]] = {
    "mining": {"titanium": 12, "fuel_cells": 3},
    "agricultural": {"hydroponics": 15, "medicines": 4},
    "high_tech": {"microchips": 10, "fuel_cells": 5},
    "industrial": {"fuel_cells": 12, "microchips": 4},
    "black_market": {"xenoliths": 6, "medicines": 5},
}

ARCHETYPE_CONSUMPTIONS: dict[str, dict[str, int]] = {
    "mining": {"hydroponics": 8, "microchips": 6, "medicines": 4},
    "agricultural": {"titanium": 6, "fuel_cells": 5, "microchips": 3},
    "high_tech": {"titanium": 8, "fuel_cells": 7, "hydroponics": 5},
    "industrial": {"titanium": 10, "hydroponics": 6, "medicines": 3},
    "black_market": {"fuel_cells": 6, "microchips": 5, "hydroponics": 6},
}

# Template shocks for emergent economic events
EVENT_TEMPLATES = [
    {
        "id_prefix": "mining_boom",
        "title": "Rich Asteroid Vein Discovered",
        "description": "Deep-space core drillers strike an ultra-dense titanium seam. Local supply floods the market, crashing export prices.",
        "commodity_id": "titanium",
        "price_multiplier": 0.60,
        "category": "boom",
        "duration": 35,
    },
    {
        "id_prefix": "medical_crisis",
        "title": "Bio-Pathogen Containment Alert",
        "description": "A virulent orbital flu strain overwhelms local colony med-centers. Demand and prices for cryo-antibiotics skyrocket.",
        "commodity_id": "medicines",
        "price_multiplier": 1.85,
        "category": "crisis",
        "duration": 40,
    },
    {
        "id_prefix": "tech_breakthrough",
        "title": "Subspace Processor Quantum Leap",
        "description": "Local research labs unveil high-yield quantum wafer synthesis, slashing manufacturing costs and market prices.",
        "commodity_id": "microchips",
        "price_multiplier": 0.65,
        "category": "breakthrough",
        "duration": 30,
    },
    {
        "id_prefix": "pirate_blockade",
        "title": "Corsair Hyperlane Interdiction",
        "description": "Armed raiders harass incoming fuel freighters. Hyperdrive fuel cell prices spike due to severe local shortages.",
        "commodity_id": "fuel_cells",
        "price_multiplier": 1.75,
        "category": "blockade",
        "duration": 25,
    },
    {
        "id_prefix": "crop_blight",
        "title": "Hydroponic Dome Fungal Blight",
        "description": "Atmospheric scrubber failure ravages orbital aeroponic farms. Food rations and hydroponic nutrients in critical shortage.",
        "commodity_id": "hydroponics",
        "price_multiplier": 1.80,
        "category": "shortage",
        "duration": 30,
    },
    {
        "id_prefix": "precursor_fever",
        "title": "Ancient Relic Smuggling Surge",
        "description": "Black market syndicates report high-paying private collectors competing desperately for authentic xenolith artifacts.",
        "commodity_id": "xenoliths",
        "price_multiplier": 1.95,
        "category": "boom",
        "duration": 45,
    },
]


def generate_initial_economy(systems: dict[str, StarSystem], rng: random.Random | None = None) -> GlobalEconomyState:
    """Construct baseline economy state with localized stockpiles and initial macroeconomic conditions."""
    if rng is None:
        rng = random.Random(42)

    markets: dict[str, SystemMarketState] = {}
    from voidfarer.galaxy import CANONICAL_COMMODITIES

    for sys_id, system in systems.items():
        # Determine dominant archetype from bodies
        arch = "mining"
        for body in system.bodies:
            if body.market_archetype != "none":
                arch = body.market_archetype
                break

        prod = dict(ARCHETYPE_PRODUCTIONS.get(arch, {"fuel_cells": 5, "titanium": 5}))
        cons = dict(ARCHETYPE_CONSUMPTIONS.get(arch, {"hydroponics": 5, "medicines": 3}))

        stockpiles: dict[str, int] = {}
        for comm in CANONICAL_COMMODITIES:
            base_stock = 60
            if comm.id in prod:
                base_stock = 120 + rng.randint(-15, 25)
            elif comm.id in cons:
                base_stock = 30 + rng.randint(-10, 15)
            else:
                base_stock = 50 + rng.randint(-10, 15)
            stockpiles[comm.id] = max(10, base_stock)

        markets[sys_id] = SystemMarketState(
            system_id=sys_id,
            stockpiles=stockpiles,
            production_rates=prod,
            consumption_rates=cons,
        )

    # Seed 1 initial event to make galaxy immediately alive
    initial_event = EconomicEvent(
        id="evt_medical_crisis_alpha_centauri",
        title="Colony Bio-Pathogen Containment Alert",
        description="Alpha Centauri medical centers report high demand for cryo-antibiotics following a localized respiratory outbreak.",
        system_id="alpha_centauri",
        commodity_id="medicines",
        price_multiplier=1.70,
        duration_ticks=50,
        category="crisis",
    )

    return GlobalEconomyState(
        markets=markets,
        active_events=(initial_event,),
        last_updated_tick=0,
    )


MIN_STOCK = 5
MAX_STOCK = 300


def tick_global_economy(
    state: GlobalEconomyState,
    num_ticks: int,
    systems: dict[str, StarSystem],
    rng: random.Random | None = None,
) -> tuple[GlobalEconomyState, list[str]]:
    """Advance economic simulation: update stockpiles, decrement event clocks, spawn emergent news."""
    if rng is None:
        rng = random.Random()

    news_logs: list[str] = []
    updated_markets = dict(state.markets)

    # 1. Update stockpiles across systems
    for sys_id, market in state.markets.items():
        system = systems.get(sys_id)
        populated = [body for body in system.bodies if body.population > 0] if system else []
        if populated:
            average_devastation = sum(
                max(0.0, float(body.devastation or 0.0)) for body in populated
            ) / len(populated)
        elif system and system.bodies:
            average_devastation = sum(
                max(0.0, float(body.devastation or 0.0)) for body in system.bodies
            ) / len(system.bodies)
        else:
            average_devastation = 0.0
        production_factor = max(0.25, 1.0 - average_devastation / 100.0 * 0.60)
        new_stocks = dict(market.stockpiles)
        for comm_id, p_rate in market.production_rates.items():
            # Production adds units over ticks; bombed industry cannot meet its old rate.
            growth = int((p_rate * num_ticks) / 4 * production_factor)
            new_stocks[comm_id] = min(MAX_STOCK, new_stocks.get(comm_id, 50) + growth)

        for comm_id, c_rate in market.consumption_rates.items():
            # Consumption consumes units over ticks
            consumption = int((c_rate * num_ticks) / 4)
            new_stocks[comm_id] = max(MIN_STOCK, new_stocks.get(comm_id, 50) - consumption)

        updated_markets[sys_id] = SystemMarketState(
            system_id=sys_id,
            stockpiles=new_stocks,
            production_rates=market.production_rates,
            consumption_rates=market.consumption_rates,
        )

    # 2. Update active events
    remaining_events: list[EconomicEvent] = []
    for evt in state.active_events:
        new_dur = evt.duration_ticks - num_ticks
        if new_dur > 0:
            remaining_events.append(
                EconomicEvent(
                    id=evt.id,
                    title=evt.title,
                    description=evt.description,
                    system_id=evt.system_id,
                    commodity_id=evt.commodity_id,
                    price_multiplier=evt.price_multiplier,
                    duration_ticks=new_dur,
                    category=evt.category,
                )
            )
        else:
            sys_name = systems.get(evt.system_id).name if evt.system_id in systems else evt.system_id
            news_logs.append(f"MARKET STABILIZED: {evt.title} at {sys_name} has concluded. Prices normalized.")

    # 3. Potentially spawn new emergent economic events (approx 4% chance per tick if < 3 active events)
    if len(remaining_events) < 3 and systems and rng.random() < min(0.35, 0.04 * num_ticks):
        template = rng.choice(EVENT_TEMPLATES)
        target_sys_id = rng.choice(list(systems.keys()))
        target_sys = systems[target_sys_id]

        new_evt_id = f"evt_{template['id_prefix']}_{target_sys_id}_{rng.randint(100, 999)}"
        # Check not duplicate on same system & commodity
        if not any(e.system_id == target_sys_id and e.commodity_id == template["commodity_id"] for e in remaining_events):
            new_event = EconomicEvent(
                id=new_evt_id,
                title=f"{template['title']} ({target_sys.name})",
                description=template["description"],
                system_id=target_sys_id,
                commodity_id=template["commodity_id"],
                price_multiplier=template["price_multiplier"],
                duration_ticks=template["duration"] + rng.randint(-5, 10),
                category=template["category"],
            )
            remaining_events.append(new_event)
            news_logs.append(f"⚡ GALACTIC NEWS: {new_event.title}! {new_event.description}")

    new_state = GlobalEconomyState(
        markets=updated_markets,
        active_events=tuple(remaining_events),
        last_updated_tick=state.last_updated_tick + num_ticks,
    )
    return new_state, news_logs


def faction_standing_price_factor(faction_standing: int) -> float:
    """Return the single diplomatic price multiplier for a faction standing value."""
    return 1.0 - max(-0.15, min(0.10, int(faction_standing) * 0.0015))


def calculate_dynamic_market_quote(
    system: StarSystem,
    body: CelestialBody,
    commodity: Commodity,
    economy: GlobalEconomyState,
    faction_standing: int = 0,
) -> MarketQuote:
    """Compute precision localized pricing reflecting global stockpile supply/demand and macroeconomic events."""
    base = commodity.base_price

    # 1. Base Archetype adjustments
    arch = body.market_archetype
    supply = 50
    demand = 50

    if arch == "mining":
        if commodity.id == "titanium":
            supply = 120
            demand = 20
            base = int(base * 0.70)
        elif commodity.id in ("hydroponics", "microchips"):
            supply = 15
            demand = 110
            base = int(base * 1.35)
    elif arch == "agricultural":
        if commodity.id == "hydroponics":
            supply = 140
            demand = 15
            base = int(base * 0.65)
        elif commodity.id in ("titanium", "medicines"):
            supply = 20
            demand = 100
            base = int(base * 1.30)
    elif arch == "high_tech":
        if commodity.id == "microchips":
            supply = 110
            demand = 25
            base = int(base * 0.75)
        elif commodity.id in ("titanium", "fuel_cells"):
            supply = 30
            demand = 120
            base = int(base * 1.25)
    elif arch == "black_market":
        if commodity.id == "xenoliths":
            supply = 60
            demand = 150
            base = int(base * 1.60)
        elif commodity.id == "medicines":
            supply = 30
            demand = 130
            base = int(base * 1.40)

    # 2. Stockpile influence from GlobalEconomyState
    sys_market = economy.markets.get(system.id)
    if sys_market and commodity.id in sys_market.stockpiles:
        stock = sys_market.stockpiles[commodity.id]
        supply = stock
        # Stockpile ratio to baseline (60 units)
        stock_ratio = stock / 60.0
        # High stock lowers price, low stock raises price (0.75x to 1.35x clamp)
        stock_factor = max(0.75, min(1.35, 1.0 / (stock_ratio ** 0.35)))
        base = int(base * stock_factor)

    # 3. Macroeconomic Event multiplier
    for evt in economy.active_events:
        if evt.system_id == system.id and evt.commodity_id == commodity.id:
            base = int(base * evt.price_multiplier)
            if evt.price_multiplier > 1.0:
                demand = int(demand * 1.5)
            else:
                supply = int(supply * 1.5)

    # 4. Security risk premium
    if system.security < 0.3:
        if commodity.id in ("fuel_cells", "medicines", "xenoliths"):
            base = int(base * 1.25)

    # 4b. Faction diplomatic discount or tariff
    if faction_standing != 0:
        base = max(2, int(base * faction_standing_price_factor(faction_standing)))

    # 5. Spread calculation
    spread = max(2, int(base * 0.12))
    buy_price = max(2, base + spread)
    sell_price = max(1, base - spread)

    return MarketQuote(
        commodity_id=commodity.id,
        name=commodity.name,
        category=commodity.category,
        buy_price=buy_price,
        sell_price=sell_price,
        supply=supply,
        demand=demand,
    )


def get_galactic_trade_routes(
    systems: dict[str, StarSystem],
    economy: GlobalEconomyState,
) -> list[dict[str, Any]]:
    """Compute the most profitable interstellar trade routes across all explored star systems."""
    from voidfarer.galaxy import CANONICAL_COMMODITIES

    quotes_by_system: dict[str, dict[str, MarketQuote]] = {}
    for sys_id, system in systems.items():
        # Find dockable trading body
        trade_body = next((b for b in system.bodies if b.station_dockable), None)
        if not trade_body:
            trade_body = system.bodies[0] if system.bodies else None
        if not trade_body:
            continue

        quotes_by_system[sys_id] = {}
        for comm in CANONICAL_COMMODITIES:
            q = calculate_dynamic_market_quote(system, trade_body, comm, economy)
            quotes_by_system[sys_id][comm.id] = q

    routes: list[dict[str, Any]] = []
    for comm in CANONICAL_COMMODITIES:
        # Find lowest buy price and highest sell price across systems
        best_buy_sys = None
        min_buy = 999999
        best_sell_sys = None
        max_sell = -1

        for sys_id, quotes in quotes_by_system.items():
            if comm.id in quotes:
                q = quotes[comm.id]
                if q.buy_price < min_buy:
                    min_buy = q.buy_price
                    best_buy_sys = sys_id
                if q.sell_price > max_sell:
                    max_sell = q.sell_price
                    best_sell_sys = sys_id

        if best_buy_sys and best_sell_sys and best_buy_sys != best_sell_sys:
            profit = max_sell - min_buy
            margin_pct = round((profit / float(min_buy)) * 100.0, 1) if min_buy > 0 else 0.0
            if profit > 0:
                routes.append({
                    "commodity_id": comm.id,
                    "commodity_name": comm.name,
                    "buy_system_id": best_buy_sys,
                    "buy_system_name": systems[best_buy_sys].name,
                    "buy_price": min_buy,
                    "sell_system_id": best_sell_sys,
                    "sell_system_name": systems[best_sell_sys].name,
                    "sell_price": max_sell,
                    "profit_per_unit": profit,
                    "profit_margin_pct": margin_pct,
                })

    routes.sort(key=lambda r: r["profit_per_unit"], reverse=True)
    return routes
