"""Deterministic state machine and simulation engine for VoidFarer."""

from __future__ import annotations

from dataclasses import asdict, replace
from functools import lru_cache
import copy
import hashlib
import math
import random
import threading
import time
from typing import Any, Sequence

from voidfarer.enemies import (
    ENEMY_ARCHETYPES,
    EXECUTE_DAMAGE_MULTIPLIER,
    TACHYON_LANCE_HULL_DAMAGE,
    choose_enemy_intent,
    generate_system_enemy,
)
from voidfarer.factions import (
    CANONICAL_CORPORATIONS,
    CANONICAL_FACTIONS,
    get_corporation,
    get_faction,
    get_faction_id_from_name,
    get_faction_service_perks,
    get_faction_standing_tier,
)
from voidfarer.crew import (
    CREW_ROLES,
    DAYS_PER_MONTH,
    apply_morale_event,
    award_crew_xp,
    award_service_medals,
    calculate_crew_bonuses,
    crew_catalog,
    crew_upkeep,
    crew_xp_to_next,
    get_crew_role,
    recruit_crew_member,
    recover_crew_injuries,
    shore_leave_restore,
    tick_crew,
    wages_due,
)
from voidfarer.character import (
    ABILITY_CATALOG,
    COMMANDER_BACKGROUNDS,
    MAX_STARTING_SKILL_TOTAL,
    SKILL_CATALOG,
    STARTING_SKILL_BASE,
    STARTING_SKILL_POINTS,
    ability_ready,
    advance_age,
    apply_background_bonus,
    award_character_xp,
    match_background,
    reconcile_abilities,
    skill_bonus,
    start_ability_cooldown,
    tick_ability_cooldowns,
    train_skill,
)
from voidfarer.codex import build_codex_report, get_codex_entry
from voidfarer.decisions import eligible_decisions, make_decision_event
from voidfarer.pirates import generate_pirate_encounter, pirate_risk
from voidfarer.smuggling import (
    calculate_customs_scan_risk,
    generate_customs_encounter,
    get_contraband_in_cargo,
    is_contraband,
)
from voidfarer.away import (
    AWAY_MISSION_MAP,
    AWAY_MISSION_TYPES,
    auto_team,
    available_missions,
    crew_fit,
    get_away_mission_type,
    mission_risk,
    resolve_away_mission,
    site_key,
)
from voidfarer.exploration import (
    SCOOP_RECHARGE_TICKS,
    crew_training_cost,
    derive_derelict,
    recharge_volatile_reserve,
    scoop_profile,
    scoop_reserve,
    scoop_yield,
)
from voidfarer.economy import (
    MAX_STOCK,
    MIN_STOCK,
    calculate_dynamic_market_quote,
    faction_standing_price_factor,
    generate_initial_economy,
    get_galactic_trade_routes,
    tick_global_economy,
)
from voidfarer.faction_state import (
    faction_strength,
    force_peace_for_broke_factions,
    generate_faction_leaders,
    leader_for,
    leader_voice,
    simulate_faction_behaviors,
)
from voidfarer.fleet import (
    CAPTAIN_VICTORY_XP,
    ESCORT_CATALOG,
    FLEET_MAX_EXPERIENCE,
    FLEET_TACTICAL_ROLES,
    FLEET_TRAINING_XP,
    PATROL_SWEEP_TICKS,
    apply_fleet_casualties,
    build_fleet_ship,
    escort_sale_value,
    fleet_damage,
    fleet_rank,
    fleet_ships_in_system,
    fleet_evasion_bonus,
    fleet_support_repair,
    fleet_training_cost,
    fleet_upkeep,
    fleet_victory_experience,
    get_escort_template,
    normalize_fleet_role,
    repair_fleet_ships,
    resolve_patrol_sweep,
)
from voidfarer.megastructures import (
    apply_output_bonus,
    get_restoration,
    restoration_bonuses,
)
from voidfarer.navigation import (
    JUMP_ENCOUNTER_TUNING,
    generate_void_lanes,
    route_plan,
    shortest_route,
    system_has_black_hole,
    void_route_plan,
)
from voidfarer.outposts import (
    OUTPOST_CREW_CAPACITY,
    OUTPOST_MAP,
    OUTPOST_MODULE_CATALOG,
    OUTPOST_SPECIALIZATIONS,
    OUTPOST_SUPPLY_HUB_BONUS,
    OUTPOST_SUPPLY_LINK_BONUS,
    OUTPOST_SUPPLY_MAX_LINKS,
    OUTPOST_TYPES,
    build_outpost,
    can_build_on,
    get_outpost_type,
    grow_outpost_population,
    outpost_crew_capacity,
    outpost_crew_multiplier,
    outpost_defense,
    outpost_repair_cost,
    outpost_supply_multiplier,
    outpost_tick_production,
    upgrade_outpost,
)
from voidfarer.research import (
    RESEARCH_BASE_GAIN_PER_TICK,
    RESEARCH_MAP,
    RESEARCH_PROJECTS,
    available_projects,
    calculate_research_bonuses,
    get_research_project,
)
from voidfarer.inventory import (
    ITEM_CATALOG,
    calculate_cargo_volume,
    get_inventory_manifest,
    get_item_info,
)
from voidfarer.galaxy import (
    CANONICAL_COMMODITIES,
    COMMODITY_MAP,
    LEGACY_SYSTEM_IDS,
    VOID_GATE_SYSTEM_IDS,
    GalaxyGenerator,
    black_hole_body,
    compute_scientific_planet_properties,
    get_colony_tier,
    step_population_dynamics,
    world_tech_level,
)
from voidfarer.demographics import (
    TECH_DRIFT_TICKS,
    compute_population_capacity,
    devastation_recovery,
    initial_population,
)
from voidfarer.faction_economy import initialize_faction_economies, tick_faction_economies
from voidfarer.faction_trade import compute_trade_links, trade_partner_names
from voidfarer.messaging import (
    choice_by_id,
    follow_up_message,
    quantum_offer_for_standing,
    refugee_messages_for_new_wars,
    tree_catalog,
    tree_root_message,
)
from voidfarer.mapmods import (
    aggregate_map_modifiers,
    generate_map_modifiers,
    get_map_modifier,
    system_modifier_summary,
)
from voidfarer.reactor import (
    REACTOR_MODES,
    get_reactor_mode,
    reactor_cooling_rate,
    reactor_heat_capacity,
    reactor_output_efficiency,
    simulate_reactor_tick,
    vent_reactor,
)
from voidfarer.weapons import WEAPON_MAP, get_weapon, weapon_catalog
from voidfarer.logbook import is_notable, summarize_trades, trim_log
from voidfarer.shipmods import (
    CATALOG_SHIP_MODS,
    SHIP_MOD_SLOTS,
    calculate_ship_mod_bonuses,
    get_available_ship_mods,
    get_ship_mod,
    get_ship_mod_sell_value,
    slot_code,
    slot_label,
)
from voidfarer.models import (
    AICaptain,
    AwayMission,
    BountyContract,
    CelestialBody,
    CodexState,
    CombatEncounter,
    Commodity,
    Depot,
    EconomicEvent,
    FactionLeader,
    FleetDrone,
    FleetShip,
    GameEvent,
    GameState,
    GlobalEconomyState,
    MarketQuote,
    PilotMastery,
    PrecursorRelic,
    CrewMember,
    CustomsEncounter,
    CompletedQuest,
    Outpost,
    PlayerCharacter,
    QuantumMessage,
    ReactorState,
    ResearchState,
    ShipPower,
    ShipState,
    ShipUpgrade,
    StarSystem,
    StoryChapter,
    StoryChoice,
    StoryRequirements,
    StoryState,
    StoryTransmission,
    SystemMarketState,
    TimeState,
    TradeOrder,
    TravelState,
    TutorialState,
    TutorialStep,
    VoidTraversalState,
    WarState,
)
from voidfarer.frontier import (
    MERCENARY_CATALOG,
    captain_hail,
    generate_ai_captains,
    generate_depots,
    generate_welcome_messages,
    simulate_ai_trade,
)
from voidfarer.retention import (
    CATALOG_RELICS,
    CONTRACT_CATEGORIES,
    CONTRACT_OFFER_COUNT,
    CONTRACT_OFFERS_MAX,
    NEAR_MISS_COMBAT_HULL_FRACTION,
    NEAR_MISS_SALVAGE_WINDOW,
    NEAR_MISS_SCAN_BONUS,
    PILOT_TALENTS,
    RELIC_BASE_THRESHOLD,
    RELIC_NEAR_MISS_WINDOW,
    STREAK_TUNING,
    calculate_passive_multipliers,
    generate_contract,
    generate_initial_contracts,
    payout_magnitude_for,
    payout_odds_table,
    relic_set_bonuses,
    roll_relic_drop,
    streak_multiplier,
)
from voidfarer.surface import (
    SURFACE_OPERATION_MAP,
    resolve_surface_operation,
    surface_report,
)
from voidfarer.story import (
    CAMPAIGN_CHAPTERS,
    ENDING_VARIANTS,
    INITIAL_TUTORIAL_STEPS,
    STORY_FLAG_GLOSSARY,
    STORY_RELICS,
    ending_transmission,
    generate_initial_story,
    generate_initial_tutorial,
    migrate_story_state,
    resolve_story_ending,
)
from voidfarer.upgrades import (
    CATALOG_CHASSIS,
    CATALOG_DRONE_TEMPLATES,
    CATALOG_UPGRADES,
    CHASSIS_MAP,
    UPGRADE_MAP,
    calculate_equipment_bonuses,
    get_available_chassis,
    get_available_upgrades,
    get_chassis,
    get_chassis_for_ship_class,
    get_sell_value,
    get_upgrade,
)


# Snapshot keys whose values are code constants: identical for every save, tick and seed.
STATIC_SNAPSHOT_KEYS = (
    "catalog_chassis",
    "catalog_drones",
    "catalog_relics",
    "catalog_talents",
    "catalog_upgrades",
    "catalog_weapons",
    "character_skill_catalog",
    "character_background_catalog",
    "crew_roles",
    "enemy_archetypes",
    "mercenary_catalog",
    "outpost_catalog",
    "outpost_modules",
    "outpost_specializations",
    "story_chapters",
    "story_chapters_map",
    "weapons",
)


@lru_cache(maxsize=1)
def static_catalogs() -> dict[str, Any]:
    """Build the code-constant catalogs once per process; callers must treat them as read-only."""
    return {
        "catalog_chassis": [c.to_dict() for c in CATALOG_CHASSIS],
        "catalog_drones": CATALOG_DRONE_TEMPLATES,
        "catalog_relics": [r.to_dict() for r in CATALOG_RELICS],
        "catalog_talents": PILOT_TALENTS,
        "catalog_upgrades": [u.to_dict() for u in CATALOG_UPGRADES],
        "catalog_weapons": weapon_catalog(),
        "character_skill_catalog": {sid: dict(info) for sid, info in SKILL_CATALOG.items()},
    "character_background_catalog": {bid: dict(info) for bid, info in COMMANDER_BACKGROUNDS.items()},
        "crew_roles": crew_catalog(),
        "enemy_archetypes": {aid: asdict(a) for aid, a in ENEMY_ARCHETYPES.items()},
        "mercenary_catalog": MERCENARY_CATALOG,
        "outpost_catalog": [t.to_dict() for t in OUTPOST_TYPES],
        "outpost_modules": OUTPOST_MODULE_CATALOG,
        "outpost_specializations": OUTPOST_SPECIALIZATIONS,
        "story_chapters": [c.to_dict() for c in CAMPAIGN_CHAPTERS],
        "story_chapters_map": {c.id: c.to_dict() for c in CAMPAIGN_CHAPTERS},
        "weapons": weapon_catalog(),
    }


def _cargo_cost_after(previous_cargo: dict[str, int], previous_cost: dict[str, int],
                      cargo: dict[str, int]) -> dict[str, int]:
    """Carry the paid basis of held cargo through any mutation outside a market trade."""
    costs: dict[str, int] = {}
    for item_id, quantity in cargo.items():
        held = max(0, int(previous_cargo.get(item_id, 0)))
        paid = max(0, int(previous_cost.get(item_id, 0)))
        if quantity <= 0 or held <= 0 or paid <= 0:
            continue
        costs[item_id] = paid * int(quantity) // held if quantity <= held else paid
    return {item_id: cost for item_id, cost in costs.items() if cost > 0}


class SimulationEngine:
    """Coordinates space flight, star navigation, fleet drones, upgrades, and tactical combat."""

    MIN_SURVEY_SENSOR_POWER = 5.0
    SURVEY_COMPLETION_CREDITS = 300
    SURVEY_COMPLETION_XP = 120

    @staticmethod
    def _stable_unit(*parts: object) -> float:
        """Deterministic [0,1) roll that does not disturb the live RNG stream."""
        payload = "|".join(str(part) for part in parts).encode("utf-8")
        digest = hashlib.blake2b(payload, digest_size=8).digest()
        return int.from_bytes(digest, "big") / float(2**64)

    # Only the dramatic headlines reach the cockpit as notifications; declarations stay
    # in the flight log so a long war does not bury the player in toasts.
    AI_TRADE_LOG_TICKS = 5
    TRADE_AUTOMATION_COOLDOWN = 3
    QUANTUM_AUTOMATION_COOLDOWN = 6
    WAR_NEWS_COOLDOWN_TICKS = 12
    RECONSTRUCTION_CREDIT_COST = 600
    RECONSTRUCTION_CREDIT_DEVASTATION = 20.0
    RELIEF_DEVASTATION = 40.0
    RELIEF_CARGO = (("medicines", 2), ("hydroponics", 2), ("fuel_cells", 1))
    WAR_NEWS_TITLES = (
        ("WAR: ", "System Captured"),
        ("PEACE: ", "Peace Treaty Signed"),
        ("BANKRUPT PEACE: ", "Peace Treaty Signed"),
        ("FACTION ELIMINATED: ", "Faction Eliminated"),
    )

    @classmethod
    def war_news_events(cls, lines: list[str], tick: int, existing: list[GameEvent]) -> list[GameEvent]:
        """Turn this tick's captures, treaties and eliminations into one headline at most."""
        latest_war_tick = max(
            (event.tick for event in existing if event.kind == "war" and not event.dismissed),
            default=-10**9,
        )
        if tick - latest_war_tick < cls.WAR_NEWS_COOLDOWN_TICKS:
            return []
        seen = {event.message for event in existing if not event.dismissed}
        events: list[GameEvent] = []
        for line in lines:
            title = next((label for prefix, label in cls.WAR_NEWS_TITLES if line.startswith(prefix)), None)
            if title is None or line in seen:
                continue
            seen.add(line)
            events.append(
                GameEvent(
                    id=f"evt_{tick}_{len(existing) + len(events) + 1}",
                    kind="war",
                    title=title,
                    message=line,
                    tick=tick,
                    dismissed=False,
                )
            )
            if len(events) >= 1:
                break
        return events

    def __init__(self, seed: int = 42, state: GameState | None = None) -> None:
        self.lock = threading.RLock()
        self.seed = seed
        self.rng = random.Random(seed)
        self.allow_decision_events = False
        # Cadence is a preference, so it lives in the save's stats rather than only in RAM.
        self.decision_cadence = (
            self._cadence_from_state(state) if state is not None else self.DEFAULT_DECISION_CADENCE
        )

        if state is not None:
            ship = state.ship
            tut = ship.tutorial
            if not tut.steps and not tut.completed and not tut.skipped:
                tut = generate_initial_tutorial()
            st = ship.story
            if not st.chapters:
                st = generate_initial_story()
            else:
                st = migrate_story_state(st)
            state = replace(state, character=reconcile_abilities(state.character)[0])
            self.state = state
            new_ship = self._clone_ship(tutorial=tut, story=st) if (tut != ship.tutorial or st != ship.story) else ship
            econ = state.economy
            if not econ or not econ.markets:
                econ = generate_initial_economy(state.systems, self.rng)
            if new_ship != ship or econ != state.economy:
                self.state = self._clone_state(ship=new_ship, economy=econ)
        else:
            self.state = self._create_initial_state(seed)
        self._local_dock_purchases: dict[tuple[str, str, str], tuple[int, int]] = dict(
            self.state.local_dock_purchases
        )
        self._bootstrap_frontier()

    def _bootstrap_frontier(self) -> None:
        """Backfill frontier systems for legacy saves without changing the save schema."""
        updates: dict[str, Any] = {}
        if not self.state.ai_captains:
            updates["ai_captains"] = generate_ai_captains(self.state.systems, self.state.galaxy_seed)
        if not self.state.depots:
            updates["depots"] = generate_depots(self.state.systems)
        if not self.state.messages:
            updates["messages"] = generate_welcome_messages(self.state.time.tick)
        if not any(m.tree_id for m in self.state.messages):
            root = tree_root_message("precursor_signal", self.state.time.tick)
            if root:
                updates["messages"] = tuple(updates.get("messages", self.state.messages)) + (root,)
        if not self.state.faction_leaders:
            updates["faction_leaders"] = generate_faction_leaders(self.state.galaxy_seed)
        if not self.state.ship.crew:
            updates["ship"] = self._clone_ship(crew=(
                CrewMember(id="crew_engineer_1", name="Imani Vale", role="engineer", skill=3, morale=82.0, wage=35, portrait="crew_02", specialty="engineering"),
                CrewMember(id="crew_pilot_2", name="Rook Calder", role="pilot", skill=2, morale=78.0, wage=30, portrait="crew_05", specialty="evasion"),
            ))
        if not self.state.ship.weapons:
            updates["ship"] = self._clone_ship(weapons=("pulse_laser",), primary_weapon="pulse_laser")
        gov_map = {
            "Sol Coalition": "Federal Democracy",
            "Free Spacers Syndicate": "Trade Directorate",
            "Nebula Collective": "Technocratic Council",
            "Void Corsairs": "Pirate Warlordship",
            "Precursor Watch": "Monastic Curate",
        }
        updated_systems: dict[str, StarSystem] = {}
        systems_changed = False
        for sys_index, (sys_id, sys_obj) in enumerate(self.state.systems.items()):
            if not sys_obj.modifiers:
                legacy_modifiers = generate_map_modifiers(self.state.galaxy_seed, sys_id, sys_obj.security, sys_index)
                if legacy_modifiers:
                    sys_obj = replace(sys_obj, modifiers=legacy_modifiers)
                    systems_changed = True
            new_bodies = []
            body_changed = False
            for idx, body in enumerate(sys_obj.bodies):
                updated_body = body
                # A body with no capacity field predates the demographics model; only
                # those legacy worlds are seeded. A world emptied by war keeps its
                # population at zero instead of being silently repopulated on load.
                legacy_body = body.population_capacity <= 0
                if body.body_type not in ("star", "black_hole", "wormhole") and ("(" not in body.atmosphere or (body.habitability == 0.0 and body.body_type not in ("gas_giant", "ringed_giant", "ice_giant", "methane_storm", "lava_world"))):
                    rad_seed = 4000.0 + ((idx + len(sys_id)) % 9) * 6500.0
                    grav_seed = 0.65 + ((idx * 3 + len(sys_id)) % 7) * 0.22
                    jitter_seed = ((idx * 5 + len(sys_id)) % 9) - 4
                    phys = compute_scientific_planet_properties(
                        body_type=body.body_type,
                        spectral_type=sys_obj.spectral_type,
                        orbit_radius_au=body.orbit_radius,
                        rad_sample=rad_seed,
                        grav_sample=grav_seed,
                        temp_jitter=jitter_seed,
                        hazards=body.hazards,
                    )
                    updated_body = replace(
                        updated_body,
                        radius_km=float(phys["radius_km"]),
                        gravity=float(phys["gravity"]),
                        atmosphere=str(phys["atmosphere"]),
                        temperature_c=int(phys["temperature_c"]),
                        habitability=float(phys["habitability"]),
                    )
                if (
                    updated_body.body_type not in ("star", "black_hole", "wormhole")
                    and legacy_body
                ):
                    # Only a pre-demographics world needs its capacity backfilled; a
                    # drifted or conquered world must keep the level it earned.
                    tech = world_tech_level(
                        sys_obj.faction, updated_body.body_type, updated_body.market_archetype
                    )
                    capacity = compute_population_capacity(
                        updated_body.body_type,
                        updated_body.radius_km,
                        updated_body.habitability,
                        tech,
                    )
                    if tech != updated_body.tech_level or capacity != updated_body.population_capacity:
                        updated_body = replace(
                            updated_body,
                            tech_level=tech,
                            population_capacity=capacity,
                        )
                if (
                    legacy_body
                    and updated_body.devastation <= 0.0
                    and (updated_body.station_dockable or updated_body.landable)
                    and updated_body.population == 0
                ):
                    pop = initial_population(
                        updated_body.body_type,
                        updated_body.radius_km,
                        updated_body.habitability,
                        updated_body.tech_level,
                        sys_obj.faction,
                        updated_body.market_archetype,
                        updated_body.station_dockable,
                    )
                    gov = "Science Directorate" if updated_body.body_type == "research_outpost" else gov_map.get(sys_obj.faction, "Colonial Republic")
                    updated_body = replace(
                        updated_body,
                        faction=sys_obj.faction if updated_body.faction == "Unclaimed" else updated_body.faction,
                        population=pop,
                        government=gov if updated_body.government == "None" else updated_body.government,
                    )
                elif updated_body.population > updated_body.population_capacity > 0:
                    updated_body = replace(
                        updated_body,
                        population=updated_body.population_capacity,
                    )
                if updated_body != body:
                    body_changed = True
                new_bodies.append(updated_body)
            # Backfill black-hole event horizons for legacy saves predating void gates
            if sys_id in VOID_GATE_SYSTEM_IDS and not any(b.body_type == "black_hole" for b in new_bodies):
                new_bodies.append(black_hole_body(sys_id, sys_obj.name))
                body_changed = True
            if body_changed:
                updated_systems[sys_id] = replace(sys_obj, bodies=tuple(new_bodies))
                systems_changed = True
            else:
                updated_systems[sys_id] = sys_obj
        if systems_changed:
            updates["systems"] = updated_systems
        trade_links = compute_trade_links(
            updated_systems,
            self.state.wars,
            self.state.faction_economies,
            self.state.eliminated_factions,
        )
        if not self.state.faction_economies:
            updates["faction_economies"] = initialize_faction_economies(
                updated_systems,
                self.state.wars,
                self.state.eliminated_factions,
                trade_links,
            )
        if trade_links != self.state.trade_links:
            updates["trade_links"] = trade_links
        if updates:
            self.state = self._clone_state(**updates)

    def _clone_ship(self, **kwargs: Any) -> ShipState:
        """Create a new ShipState preserving all unspecified telemetry and inventory attributes."""
        cur = self.state.ship
        cargo = kwargs.get("cargo", cur.cargo)
        cargo_cost = kwargs.get("cargo_cost")
        if cargo_cost is None:
            cargo_cost = _cargo_cost_after(cur.cargo, cur.cargo_cost, cargo)
        return ShipState(
            commander_name=kwargs.get("commander_name", cur.commander_name),
            callsign=kwargs.get("callsign", cur.callsign),
            ship_class=kwargs.get("ship_class", cur.ship_class),
            hull=kwargs.get("hull", cur.hull),
            max_hull=kwargs.get("max_hull", cur.max_hull),
            shield=kwargs.get("shield", cur.shield),
            max_shield=kwargs.get("max_shield", cur.max_shield),
            fuel=kwargs.get("fuel", cur.fuel),
            max_fuel=kwargs.get("max_fuel", cur.max_fuel),
            credits=kwargs.get("credits", cur.credits),
            cargo=cargo,
            cargo_capacity=kwargs.get("cargo_capacity", cur.cargo_capacity),
            current_system_id=kwargs.get("current_system_id", cur.current_system_id),
            orbiting_body_id=kwargs.get("orbiting_body_id", cur.orbiting_body_id),
            power=kwargs.get("power", cur.power),
            reactor=kwargs.get("reactor", cur.reactor),
            upgrades=kwargs.get("upgrades", cur.upgrades),
            equipped_upgrades=kwargs.get("equipped_upgrades", cur.equipped_upgrades),
            ship_mods=kwargs.get("ship_mods", cur.ship_mods),
            rooms=kwargs.get("rooms", cur.rooms),
            fleet_drones=kwargs.get("fleet_drones", cur.fleet_drones),
            fleet_ships=kwargs.get("fleet_ships", cur.fleet_ships),
            battle_stance=kwargs.get("battle_stance", cur.battle_stance),
            crew=kwargs.get("crew", cur.crew),
            weapons=kwargs.get("weapons", cur.weapons),
            primary_weapon=kwargs.get("primary_weapon", cur.primary_weapon),
            message_bonuses=kwargs.get("message_bonuses", cur.message_bonuses),
            flight_log=kwargs.get("flight_log", cur.flight_log),
            streak=kwargs.get("streak", cur.streak),
            wear=kwargs.get("wear", cur.wear),
            relics=kwargs.get("relics", cur.relics),
            mastery=kwargs.get("mastery", cur.mastery),
            active_contracts=kwargs.get("active_contracts", cur.active_contracts),
            contract_offers=kwargs.get("contract_offers", cur.contract_offers),
            tactical_combo=kwargs.get("tactical_combo", cur.tactical_combo),
            near_miss_scanner_bonus=kwargs.get("near_miss_scanner_bonus", cur.near_miss_scanner_bonus),
            tutorial=kwargs.get("tutorial", cur.tutorial),
            story=kwargs.get("story", cur.story),
            faction_standings=kwargs.get("faction_standings", cur.faction_standings),
            corp_standings=kwargs.get("corp_standings", cur.corp_standings),
            allies=kwargs.get("allies", cur.allies),
            trade_pacts=kwargs.get("trade_pacts", cur.trade_pacts),
            research_pacts=kwargs.get("research_pacts", cur.research_pacts),
            non_aggression_until=kwargs.get(
                "non_aggression_until", cur.non_aggression_until
            ),
            landed_body_id=kwargs["landed_body_id"] if "landed_body_id" in kwargs else cur.landed_body_id,
            travel=kwargs["travel"] if "travel" in kwargs else cur.travel,
            void_traversal=kwargs["void_traversal"] if "void_traversal" in kwargs else cur.void_traversal,
            away_missions=kwargs.get("away_missions", cur.away_missions),
            away_completed=kwargs.get("away_completed", cur.away_completed),
            trade_orders=kwargs.get("trade_orders", cur.trade_orders),
            surface_used=kwargs.get("surface_used", cur.surface_used),
            cargo_cost=cargo_cost,
            waypoint_au=kwargs.get("waypoint_au", cur.waypoint_au),
            waypoint_angle=kwargs.get("waypoint_angle", cur.waypoint_angle),
        )

    def _merge_fleet_ships(self, updated_local: tuple[FleetShip, ...]) -> tuple[FleetShip, ...]:
        """Apply local battle updates without dropping escorts on patrol elsewhere."""
        local_by_id = {ship.id: ship for ship in updated_local}
        current = self.state.ship.fleet_ships
        current_ids = {ship.id for ship in current}
        merged = [local_by_id.get(ship.id, ship) for ship in current]
        merged.extend(ship for ship in updated_local if ship.id not in current_ids)
        return tuple(merged)

    def _clone_state(self, **kwargs: Any) -> GameState:
        """Create a new GameState preserving time, stats, economy, and all unspecified universe fields."""
        cur = self.state
        return GameState(
            version=kwargs.get("version", cur.version),
            galaxy_seed=kwargs.get("galaxy_seed", cur.galaxy_seed),
            ship=kwargs.get("ship", cur.ship),
            systems=kwargs.get("systems", cur.systems),
            visited_systems=kwargs.get("visited_systems", cur.visited_systems),
            active_anomaly=kwargs["active_anomaly"] if "active_anomaly" in kwargs else cur.active_anomaly,
            active_combat=kwargs["active_combat"] if "active_combat" in kwargs else cur.active_combat,
            active_pirate=kwargs["active_pirate"] if "active_pirate" in kwargs else cur.active_pirate,
            active_customs=kwargs["active_customs"] if "active_customs" in kwargs else cur.active_customs,
            pending_decision=kwargs["pending_decision"] if "pending_decision" in kwargs else cur.pending_decision,
            decision_history=kwargs.get("decision_history", cur.decision_history),
            time=kwargs.get("time", cur.time),
            stats=kwargs.get("stats", cur.stats),
            economy=kwargs.get("economy", cur.economy),
            ai_captains=kwargs.get("ai_captains", cur.ai_captains),
            depots=kwargs.get("depots", cur.depots),
            messages=kwargs.get("messages", cur.messages),
            events=kwargs.get("events", cur.events),
            character=kwargs.get("character", cur.character),
            research=kwargs.get("research", cur.research),
            outposts=kwargs.get("outposts", cur.outposts),
            faction_leaders=kwargs.get("faction_leaders", cur.faction_leaders),
            wars=kwargs.get("wars", cur.wars),
            faction_economies=kwargs.get("faction_economies", cur.faction_economies),
            trade_links=kwargs.get("trade_links", cur.trade_links),
            eliminated_factions=kwargs.get("eliminated_factions", cur.eliminated_factions),
            codex=kwargs.get("codex", cur.codex),
            local_dock_purchases=kwargs.get("local_dock_purchases", cur.local_dock_purchases),
            completed_quests=kwargs.get("completed_quests", cur.completed_quests),
            trade_automation=kwargs.get("trade_automation", cur.trade_automation),
            quantum_automation=kwargs.get(
                "quantum_automation", cur.quantum_automation
            ),
        )

    def _research_bonuses(self) -> dict[str, float]:
        return calculate_research_bonuses(self.state.research.completed)

    def _skill(self, skill: str) -> float:
        return skill_bonus(self.state.character, skill)

    def _combined_equipment(self, ship: ShipState | None = None) -> dict[str, float]:
        target = ship if ship is not None else self.state.ship
        bonuses = calculate_equipment_bonuses(target)
        research = self._research_bonuses()
        bonuses["reactor_cooling"] = float(bonuses.get("reactor_cooling", 0.0)) + float(research["reactor_cooling"]) + self._skill("engineering") * 2.0
        bonuses["reactor_output"] = float(bonuses.get("reactor_output", 0.0)) + float(research["reactor_output"])
        bonuses["hull_repair_per_tick"] = float(bonuses.get("hull_repair_per_tick", 0.0)) + float(research["hull_repair_per_tick"])
        persistent = target.message_bonuses
        bonuses["fuel_efficiency"] = float(bonuses.get("fuel_efficiency", 1.0)) * (1.0 - min(0.40, float(persistent.get("fuel_efficiency", 0.0))))
        for stat in ("reactor_output", "reactor_cooling", "heat_capacity", "max_shield", "scan_mult", "combat_damage"):
            if stat in persistent:
                bonuses[stat] = float(bonuses.get(stat, 0.0)) + float(persistent[stat])
        crew = self._crew_bonuses(target)
        bonuses["fuel_efficiency"] = float(bonuses.get("fuel_efficiency", 1.0)) * float(crew["fuel_efficiency"])
        bonuses["scan_mult"] = float(bonuses.get("scan_mult", 1.0)) * float(crew["scan_mult"])
        for stat in ("evasion", "reactor_cooling", "combat_damage", "trade_margin", "hull_repair_per_tick", "research_per_tick", "boarding_defense"):
            bonuses[stat] = float(bonuses.get(stat, 0.0)) + float(crew.get(stat, 0.0))
        return bonuses

    def _crew_bonuses(self, ship: ShipState | None = None) -> dict[str, float]:
        target = ship if ship is not None else self.state.ship
        assigned = {cid for mission in target.away_missions for cid in mission.crew_ids}
        assigned.update(
            cid for outpost in self.state.outposts for cid in outpost.assigned_crew
        )
        assigned.update(
            ship.captain_id for ship in target.fleet_ships if ship.captain_id
        )
        return calculate_crew_bonuses(tuple(member for member in target.crew if member.id not in assigned))

    def _faction_stability(self) -> dict[str, float]:
        """System owner name -> its faction's civil stability (default 50 for unclaimed)."""
        return {
            CANONICAL_FACTIONS[economy.faction_id].name: economy.stability
            for economy in self.state.faction_economies
            if economy.faction_id in CANONICAL_FACTIONS
        }

    def _faction_technology(self) -> dict[str, int]:
        """System owner name -> its faction's current technology level."""
        return {
            CANONICAL_FACTIONS[economy.faction_id].name: economy.tech_level
            for economy in self.state.faction_economies
            if economy.faction_id in CANONICAL_FACTIONS
        }

    def _drift_world_technology(
        self,
        systems: dict[str, StarSystem],
        faction_tech: dict[str, int],
        previous_tick: int,
        new_tick: int,
    ) -> dict[str, StarSystem]:
        """Upgrade settled worlds toward their owner's tech at most once per drift window."""
        cycles = new_tick // TECH_DRIFT_TICKS - previous_tick // TECH_DRIFT_TICKS
        if cycles <= 0:
            return systems
        updated: dict[str, StarSystem] = {}
        for sys_id, system in systems.items():
            owner_tech = faction_tech.get(system.faction)
            bodies = []
            changed = False
            for body in system.bodies:
                target = world_tech_level(
                    system.faction,
                    body.body_type,
                    body.market_archetype,
                    owner_tech,
                )
                if target > body.tech_level:
                    tech = min(target, body.tech_level + cycles)
                    capacity = compute_population_capacity(
                        body.body_type,
                        body.radius_km,
                        body.habitability,
                        tech,
                    )
                    bodies.append(
                        replace(body, tech_level=tech, population_capacity=capacity)
                    )
                    changed = True
                else:
                    bodies.append(body)
            updated[sys_id] = replace(system, bodies=tuple(bodies)) if changed else system
        return updated

    def _map_effects(self, system: StarSystem | None = None) -> dict[str, float]:
        """Aggregate the active map modifiers of a system (defaults to the current one)."""
        return aggregate_map_modifiers(system if system is not None else self.current_system)

    def _effective_power(self, subsystem: str, ship: ShipState | None = None) -> float:
        """Allocated subsystem power after reactor mode, heat, and integrity derating."""
        target = ship if ship is not None else self.state.ship
        allocation = float(getattr(target.power, subsystem, 0))
        output_bonus = float(self._combined_equipment(target).get("reactor_output", 0.0))
        return allocation * reactor_output_efficiency(target.reactor, output_bonus)

    def _recompute_caps(
        self,
        ship: ShipState,
        equipped: dict[str, str] | None = None,
        ship_mods: dict[str, str] | None = None,
    ) -> tuple[int, int, int, int]:
        """Recompute maximum hull, shield, cargo, and fuel from chassis, modules, and mods."""
        chassis = get_chassis_for_ship_class(ship.ship_class)
        base_hull = chassis.max_hull if chassis else 100
        base_shield = chassis.max_shield if chassis else 100
        base_capacity = chassis.cargo_capacity if chassis else 40
        base_fuel = chassis.max_fuel if chassis else 60
        probe = replace(
            ship,
            equipped_upgrades=equipped if equipped is not None else ship.equipped_upgrades,
            ship_mods=ship_mods if ship_mods is not None else ship.ship_mods,
        )
        equipment = calculate_equipment_bonuses(probe)
        passives = calculate_passive_multipliers(probe)
        max_hull = max(10, base_hull + int(equipment["max_hull"]) + int(passives["max_hull"]))
        max_shield = max(10, base_shield + int(equipment["max_shield"]) + int(passives["shield_cap"]))
        cargo_capacity = max(5, base_capacity + int(equipment["cargo_capacity"]))
        max_fuel = max(10, base_fuel + int(equipment.get("max_fuel", 0.0)))
        return max_hull, max_shield, cargo_capacity, max_fuel

    def _grant_cargo(self, cargo: dict[str, int], commodity_id: str, quantity: int) -> tuple[int, int]:
        """Add as many units as the hold allows, returning (granted, overflow)."""
        unit_volume = max(1, calculate_cargo_volume({commodity_id: 1}))
        free_volume = self.state.ship.cargo_capacity - calculate_cargo_volume(cargo)
        granted = min(max(0, int(quantity)), max(0, free_volume // unit_volume))
        if granted > 0:
            cargo[commodity_id] = cargo.get(commodity_id, 0) + granted
        return granted, int(quantity) - granted

    def _replace_system_body(self, body_id: str, **changes: Any) -> dict[str, StarSystem]:
        """Return a systems map with one body of the current system replaced."""
        cur_sys = self.current_system
        bodies = tuple(
            replace(body, **changes) if body.id == body_id else body
            for body in cur_sys.bodies
        )
        new_sys = StarSystem(
            id=cur_sys.id,
            name=cur_sys.name,
            seed=cur_sys.seed,
            x=cur_sys.x,
            y=cur_sys.y,
            spectral_type=cur_sys.spectral_type,
            color=cur_sys.color,
            security=cur_sys.security,
            faction=cur_sys.faction,
            bodies=bodies,
            connections=cur_sys.connections,
            dominant_corp=cur_sys.dominant_corp,
            modifiers=cur_sys.modifiers,
        )
        systems = dict(self.state.systems)
        systems[cur_sys.id] = new_sys
        return systems

    def _apply_relic_stat_bonuses(
        self,
        hull: int,
        max_hull: int,
        shield: int,
        max_shield: int,
        relics: Sequence[PrecursorRelic],
    ) -> tuple[int, int, int, int]:
        """Raise current and maximum hull/shield for newly acquired permanent relics."""
        for relic in relics:
            stats = dict(relic.bonuses)
            stats[relic.passive_stat] = stats.get(relic.passive_stat, 0.0) + relic.stat_multiplier
            if relic.passive_stat == "stellar_forge":
                stats.setdefault("shield_cap", 40.0)
            if "max_hull" in stats:
                bonus = int(stats["max_hull"])
                max_hull += bonus
                hull += bonus
            if "shield_cap" in stats:
                bonus = int(stats["shield_cap"])
                max_shield += bonus
                shield += bonus
        return hull, max_hull, shield, max_shield

    def _progress_tutorial(self, action_type: str) -> tuple[TutorialState, int, int, list[PrecursorRelic], list[str]]:
        """Advance the Cadet Flight Academy if current step requirement is satisfied."""
        cur = self.state.ship.tutorial
        if not cur.active or cur.completed or cur.skipped:
            return cur, 0, 0, [], []

        if cur.current_step_index >= len(cur.steps):
            return cur, 0, 0, [], []

        current_step = cur.steps[cur.current_step_index]
        match_map = {
            "step_orbit": "orbit",
            "step_scan": "scan",
            "step_power": "power",
            "step_trade": "trade",
            "step_drone": "drone",
            "step_jump": "jump",
        }

        if match_map.get(current_step.id) != action_type:
            return cur, 0, 0, [], []

        updated_steps = list(cur.steps)
        updated_steps[cur.current_step_index] = TutorialStep(
            id=current_step.id,
            title=current_step.title,
            instruction=current_step.instruction,
            hint=current_step.hint,
            reward_credits=current_step.reward_credits,
            reward_xp=current_step.reward_xp,
            completed=True,
        )

        credits_awarded = current_step.reward_credits
        xp_awarded = current_step.reward_xp
        relics_awarded: list[PrecursorRelic] = []
        logs: list[str] = [
            f"ACADEMY STEP COMPLETE: [{current_step.title}] finished (+{current_step.reward_credits} cr, +{current_step.reward_xp} XP)!"
        ]

        next_idx = cur.current_step_index + 1
        is_all_done = next_idx >= len(cur.steps)

        if is_all_done:
            credits_awarded += 1500
            xp_awarded += 400
            cadet_wings = STORY_RELICS.get("relic_cadet_wings")
            if cadet_wings:
                relics_awarded.append(cadet_wings)
            logs.append("🎓 ACADEMY GRADUATION: Commander Astraea has graduated from the Cadet Flight Academy! Awarded Cadet Honor Wings (+1,500 cr, +400 XP).")

        new_tutorial = TutorialState(
            active=cur.active,
            current_step_index=next_idx,
            steps=tuple(updated_steps),
            completed=is_all_done,
            skipped=cur.skipped,
        )
        return new_tutorial, credits_awarded, xp_awarded, relics_awarded, logs

    def _award_pilot_xp(self, amount: int, current_mastery: PilotMastery) -> tuple[PilotMastery, list[str]]:
        """Award experience points and compute level promotions and talent points."""
        new_xp = current_mastery.xp + amount
        level = current_mastery.level
        next_xp = max(1, current_mastery.next_level_xp)
        points = current_mastery.talent_points
        logs: list[str] = []

        while new_xp >= next_xp:
            new_xp -= next_xp
            level += 1
            points += 1
            next_xp = int(next_xp * 1.5)
            logs.append(f"★ PILOT PROMOTION: Reached Pilot Mastery Level {level}! Earned +1 Specialization Point.")
            if level == self.OUTPOST_CHARTER_MASTERY_LEVEL:
                logs.append(
                    "★ OUTPOST CHARTERS AVAILABLE: recognized commander status confirmed — "
                    "found colonies from the Empire tab (outpost build)."
                )

        return PilotMastery(
            level=level,
            xp=new_xp,
            next_level_xp=next_xp,
            talent_points=points,
            specializations=current_mastery.specializations,
        ), logs

    def _progress_contracts(
        self,
        category: str,
        amount: int = 1,
        contracts: Sequence[BountyContract] | None = None,
    ) -> tuple[tuple[BountyContract, ...], list[str]]:
        """Advance matching active contracts toward completion objectives."""
        updated: list[BountyContract] = []
        logs: list[str] = []
        for c in contracts if contracts is not None else self.state.ship.active_contracts:
            if c.category == category and not c.completed:
                new_cnt = min(c.target_count, c.current_count + amount)
                is_done = new_cnt >= c.target_count
                updated.append(
                    BountyContract(
                        id=c.id,
                        title=c.title,
                        description=c.description,
                        category=c.category,
                        target_count=c.target_count,
                        current_count=new_cnt,
                        reward_credits=c.reward_credits,
                        reward_xp=c.reward_xp,
                        reward_relic_tier=c.reward_relic_tier,
                        completed=is_done,
                    )
                )
                if is_done:
                    logs.append(f"OBJECTIVE COMPLETE: [{c.title}] ready to claim ({c.reward_credits} cr, {c.reward_xp} XP)!")
            else:
                updated.append(c)
        return tuple(updated), logs

    def reset(self, seed: int = 42, profile: dict[str, Any] | None = None) -> tuple[bool, str]:
        """Reset the simulation to a fresh galaxy with an isolated deterministic RNG stream."""
        with self.lock:
            if profile:
                error = self._validate_commander_profile(profile)
                if error:
                    return False, error
            try:
                seed_int = int(seed)
            except (TypeError, ValueError):
                return False, "Seed must be an integer."
            if seed_int < 0:
                return False, "Seed must be a non-negative integer."
            self.seed = seed_int
            self.rng = random.Random(self.seed)
            self.state = self._create_initial_state(self.seed)
            self.decision_cadence = self.DEFAULT_DECISION_CADENCE
            self._local_dock_purchases = {}
            if profile:
                self._apply_commander_profile(profile)
            return True, "Simulation reset to factory state."

    @staticmethod
    def _validate_commander_profile(profile: dict[str, Any]) -> str | None:
        """Reject commander profiles whose starting skills exceed the creation budget."""
        raw_skills = profile.get("skills") if isinstance(profile.get("skills"), dict) else {}
        total = 0
        for skill in SKILL_CATALOG:
            try:
                level = int(raw_skills.get(skill, 1))
            except (TypeError, ValueError):
                level = 1
            total += max(1, min(10, level))
        if total > MAX_STARTING_SKILL_TOTAL:
            return (
                f"Starting skills exceed the {MAX_STARTING_SKILL_TOTAL}-point budget "
                f"(requested {total}). Lower one or more skills and try again."
            )
        return None

    def _apply_commander_profile(self, profile: dict[str, Any]) -> None:
        """Apply the commander name, age, background and starting skills chosen at creation."""
        character = self.state.character
        name = str(profile.get("name") or character.name).strip()[:24] or character.name
        try:
            age = max(18, min(99, int(profile.get("age", character.age) or character.age)))
        except (TypeError, ValueError):
            age = character.age
        background = str(profile.get("background") or character.background).strip()[:32] or character.background
        raw_skills = profile.get("skills") if isinstance(profile.get("skills"), dict) else {}
        skills = dict(character.skills)
        for skill in skills:
            if skill not in raw_skills:
                continue
            try:
                skills[skill] = max(1, min(10, int(raw_skills[skill])))
            except (TypeError, ValueError):
                continue
        matched = match_background(background)
        if matched is not None:
            background = str(COMMANDER_BACKGROUNDS[matched]["name"])
            skills = apply_background_bonus(skills, matched)
        updated_character = replace(character, name=name, age=age, background=background, skills=skills)
        updated_character, _ = reconcile_abilities(updated_character)
        updated_ship = self._clone_ship(commander_name=name)
        self.state = self._clone_state(character=updated_character, ship=updated_ship)

    def load_state(self, state: GameState) -> tuple[bool, str]:
        """Replace the live universe with a loaded save and reseed its RNG stream."""
        with self.lock:
            self.seed = int(state.galaxy_seed)
            self.rng = random.Random(self.seed)
            state = replace(state, character=reconcile_abilities(state.character)[0])
            self.state = state
            st = state.ship.story
            if not st.chapters:
                st = generate_initial_story()
            else:
                st = migrate_story_state(st)
            if st != state.ship.story:
                self.state = self._clone_state(ship=self._clone_ship(story=st))
            self._local_dock_purchases = dict(state.local_dock_purchases)
            self.decision_cadence = self._cadence_from_state(self.state)
            self._bootstrap_frontier()
            return True, f"Loaded save at {state.time.current_date} (tick #{state.time.tick})."

    def _create_initial_state(self, seed: int) -> GameState:
        """Construct a fresh universe state rooted at Sol System."""
        generator = GalaxyGenerator(seed=seed)
        systems = generator.generate_galaxy()
        initial_contracts = generate_initial_contracts(self.rng)
        extra_contract_rng = random.Random(seed ^ 0x9E3779B9)
        initial_contracts = initial_contracts + (
            generate_contract(extra_contract_rng, "trade"),
            generate_contract(extra_contract_rng, "delivery"),
        )

        ship = ShipState(
            commander_name="Astraea",
            callsign="VF-Vanguard",
            ship_class="Corvette Scout",
            hull=100,
            max_hull=100,
            shield=100,
            max_shield=100,
            fuel=60,
            max_fuel=60,
            credits=2000,
            cargo={"fuel_cells": 5, "hydroponics": 10},
            cargo_capacity=40,
            current_system_id="sol",
            orbiting_body_id="sol_body_1",
            power=ShipPower(engines=30, shields=25, sensors=25, weapons=20),
            upgrades=("Pulse Scanner MK-I", "Shield Buffer"),
            equipped_upgrades={},
            crew=(
                CrewMember(id="crew_engineer_1", name="Imani Vale", role="engineer", skill=3, morale=82.0, wage=35, portrait="crew_02", specialty="engineering"),
                CrewMember(id="crew_pilot_2", name="Rook Calder", role="pilot", skill=2, morale=78.0, wage=30, portrait="crew_05", specialty="evasion"),
            ),
            fleet_drones=(
                FleetDrone(
                    id="drone_mining_1",
                    name="Mining Drone Alpha",
                    drone_type="mining",
                    assigned_system_id="sol",
                    status="harvesting",
                ),
            ),
            flight_log=("Command initialization verified at Sol Starport.",),
            streak=1,
            relics=(),
            mastery=PilotMastery(level=1, xp=0, next_level_xp=500, talent_points=0, specializations=()),
            active_contracts=initial_contracts,
            tactical_combo=0,
            near_miss_scanner_bonus=0.0,
            tutorial=generate_initial_tutorial(),
            story=generate_initial_story(),
            faction_standings={
                "sol_coalition": 0,
                "vanguard_syndicate": 0,
                "precursor_watch": 0,
                "nebula_collective": 0,
                "outlaw_corsairs": -15,
                "kepler_concord": 0,
                "helios_compact": 0,
                "ashen_choir": 0,
                "iron_meridian": 0,
            },
            corp_standings={
                "hyperion_dynamics": 0,
                "astraea_pharma": 0,
                "omnicorp_mining": 0,
                "nexus_cybernetics": 0,
                "vortex_fuel": 0,
                "helios_forge": 0,
                "choir_reliquary": 0,
            },
        )

        legacy_ids = set(LEGACY_SYSTEM_IDS)
        legacy_systems = {sid: sys for sid, sys in systems.items() if sid in legacy_ids}
        frontier_systems = {sid: sys for sid, sys in systems.items() if sid not in legacy_ids}
        economy = generate_initial_economy(legacy_systems, self.rng)
        if frontier_systems:
            frontier_econ = generate_initial_economy(
                frontier_systems, random.Random(seed ^ 0x5F3759DF)
            )
            economy = replace(
                economy,
                markets={**economy.markets, **frontier_econ.markets},
            )
        return GameState(
            version=1,
            galaxy_seed=seed,
            ship=ship,
            systems=systems,
            visited_systems=("sol",),
            active_anomaly=None,
            active_combat=None,
            active_pirate=None,
            pending_decision=None,
            decision_history=(),
            stats={
                "jumps": 0,
                "scans": 0,
                "trades": 0,
                "anomalies_resolved": 0,
                "combat_victories": 0,
                "ships_captured": 0,
                "ships_sold": 0,
                "credits_earned": 0,
                "contracts_completed": 0,
                "away_missions": 0,
                "away_successes": 0,
                "away_failures": 0,
                "away_injuries": 0,
                "pirate_encounters": 0,
                "pirates_paid": 0,
                "pirates_evaded": 0,
                "pirates_fought": 0,
                "landings": 0,
                "surface_ops": 0,
                "worlds_rebuilt": 0,
                "relief_deliveries": 0,
                "decisions_resolved": 0,
                "last_decision_tick": 0,
                "quantum_orders": 0,
                "deliveries": 0,
            },
            economy=economy,
            ai_captains=generate_ai_captains(systems, seed),
            depots=generate_depots(systems),
            messages=generate_welcome_messages(0) + ((tree_root_message("precursor_signal", 0) or QuantumMessage(id="tree_precursor_signal_0", sender="Cipher", recipient="Commander", subject="A signal beneath the noise", body="A precursor carrier wave is repeating beneath the quantum noise.")),),
        )

    @property
    def current_system(self) -> StarSystem:
        return self.state.systems[self.state.ship.current_system_id]

    @property
    def orbiting_body(self) -> CelestialBody | None:
        b_id = self.state.ship.orbiting_body_id
        if not b_id:
            return None
        for b in self.current_system.bodies:
            if b.id == b_id:
                return b
        return None

    @property
    def docked_body(self) -> CelestialBody | None:
        """The body whose station services are available; none in transit or the void."""
        if self.state.ship.travel is not None or self.state.ship.void_traversal is not None:
            return None
        return self.orbiting_body

    def _body_by_id(self, body_id: str) -> CelestialBody | None:
        """Look up a celestial body anywhere in the known galaxy."""
        for system in self.state.systems.values():
            for body in system.bodies:
                if body.id == body_id:
                    return body
        return None

    # ------------------------------------------------------------------
    # Void traversal: the Hollow Between (G-012 parity and determinism)
    # ------------------------------------------------------------------

    VOID_STORM_BASE_CHANCE = 0.20
    VOID_STORM_STABILITY_LOSS = 15.0
    VOID_STORM_SHIELD_LOSS = 10
    VOID_STORM_HULL_LOSS = 5
    VOID_EMERGENCE_HULL_DAMAGE = 25
    VOID_ARRIVAL_XP = 50
    VOID_FIRST_VISIT_BONUS = 400
    VOID_RESONANCE_CREDITS = 120
    VOID_RESONANCE_XP = 15
    VOID_EMERGE_RESONANCE_SHARE = 0.5
    VOID_LOW_STABILITY_THRESHOLD = 30.0
    VOID_LOW_STABILITY_RESONANCE_BONUS = 1.0

    def _void_storm_chance(self) -> float:
        """Current void storm probability, calmed by open gateways."""
        chance = self.VOID_STORM_BASE_CHANCE
        if self.state.ship.story.flags.get("gateways_open"):
            chance *= 0.75
        return chance

    def _void_resonance_payout(self, resonance: float, share: float = 1.0) -> tuple[int, int]:
        """Convert weathered-storm resonance into credits and pilot XP.

        ``share`` lets an emergency emergence pay only the prorated fraction the
        commander actually braved before turning back.
        """
        value = max(0.0, float(resonance)) * max(0.0, min(1.0, float(share)))
        return (
            int(round(value * self.VOID_RESONANCE_CREDITS)),
            int(round(value * self.VOID_RESONANCE_XP)),
        )

    def void_dive(self, target_system_id: str) -> tuple[bool, str]:
        """Slip through a black-hole event horizon into the Hollow Between."""
        with self.lock:
            target = str(target_system_id).strip()
            if self.state.ship.void_traversal is not None:
                return False, "Already traversing the Hollow Between."
            if self.state.active_combat is not None:
                return False, "Void drive locked by hostile enemy tractor field! Must resolve combat or flee."
            if self.state.active_anomaly is not None:
                return False, "Void drive locked: unresolved spatial anomaly in proximity!"
            if self.state.ship.travel is not None:
                return False, "Cannot dive while in sublight transit."

            cur_sys = self.current_system
            orbiting = self.orbiting_body
            if orbiting is None or orbiting.body_type != "black_hole":
                return False, "Void dive requires orbit around a black-hole event horizon."

            if target == cur_sys.id:
                return False, "Void lanes lead elsewhere: choose a destination system."
            if target not in self.state.systems:
                return False, f"Unknown system target '{target}'."

            plan = void_route_plan(self.state.systems, self.state.galaxy_seed, cur_sys.id, target)
            if not plan["reachable"]:
                return False, f"No void lane leads from {cur_sys.name} to '{target}'."

            fuel_cost = int(plan["fuel_estimate"])
            if self.state.ship.fuel < fuel_cost:
                return False, f"Insufficient Quantum Fuel: {fuel_cost} units required, {self.state.ship.fuel} available."

            min_shield = max(10, int(self.state.ship.max_shield * 0.25))
            if self.state.ship.shield < min_shield:
                return False, f"Void shear demands {min_shield}+ MW shields ({self.state.ship.shield} available)."

            passives = calculate_passive_multipliers(self.state.ship)
            stability = min(130.0, 100.0 + float(passives.get("void_stability", 0.0)))
            duration = int(plan["duration_ticks"])
            started = self.state.time.tick
            traversal = VoidTraversalState(
                origin_system_id=cur_sys.id,
                destination_system_id=target,
                started_tick=started,
                arrival_tick=started + duration,
                duration_ticks=duration,
                stability=stability,
            )

            new_stats = dict(self.state.stats)
            new_stats["void_dives"] = int(new_stats.get("void_dives", 0)) + 1
            dest_sys = self.state.systems[target]
            log_entry = (
                f"VOID DIVE: Hull slips beyond the {orbiting.name} into the Hollow Between, "
                f"bound for {dest_sys.name} ({plan['lanes']} lane(s), ETA {duration} tick(s), fuel: {fuel_cost})."
            )
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            self.state = self._clone_state(
                ship=self._clone_ship(
                    fuel=self.state.ship.fuel - fuel_cost,
                    orbiting_body_id=None,
                    waypoint_au=0.0,
                    waypoint_angle=0.0,
                    void_traversal=traversal,
                    flight_log=tuple(new_log[-20:]),
                ),
                stats=new_stats,
            )
            self.emit_event(
                "void",
                "Void Dive Initiated",
                f"The Hollow Between opens. Destination: {dest_sys.name}. Hold your shields steady.",
            )
            return True, f"Void dive initiated toward {dest_sys.name}. Estimated traversal: {duration} tick(s)."

    def void_emerge(self) -> tuple[bool, str]:
        """Emergency surfacing from an active void traversal, back through the entry horizon."""
        with self.lock:
            traversal = self.state.ship.void_traversal
            if traversal is None:
                return False, "Not currently traversing the void."

            progress = traversal.progress(self.state.time.tick)
            hull_damage = int(5 + progress * 15)
            shield_damage = int(10 + progress * 25)
            resonance_credits, resonance_xp = self._void_resonance_payout(
                traversal.resonance,
                progress * self.VOID_EMERGE_RESONANCE_SHARE,
            )
            new_mastery = self.state.ship.mastery
            xp_logs: list[str] = []
            if resonance_xp > 0:
                new_mastery, xp_logs = self._award_pilot_xp(resonance_xp, new_mastery)
            origin_sys = self.state.systems.get(traversal.origin_system_id)
            origin_name = origin_sys.name if origin_sys else traversal.origin_system_id
            horizon_id = None
            if origin_sys is not None:
                for body in origin_sys.bodies:
                    if body.body_type == "black_hole":
                        horizon_id = body.id
                        break

            resonance_note = ""
            if resonance_credits > 0 or resonance_xp > 0:
                resonance_note = (
                    f" Resonance yield: +{resonance_credits} cr, +{resonance_xp} XP "
                    f"({traversal.resonance:.0f} storm resonance at {int(progress * 100)}% traversal)."
                )
            log_entry = (
                f"VOID EMERGENCE: Emergency surfacing at {origin_name} after "
                f"{int(progress * 100)}% traversal. Hull stress -{hull_damage}, shield shear -{shield_damage}."
                f"{resonance_note}"
            )
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry] + xp_logs
            stats = dict(self.state.stats)
            stats["credits_earned"] = int(stats.get("credits_earned", 0)) + resonance_credits
            banked_resonance = traversal.resonance * progress * self.VOID_EMERGE_RESONANCE_SHARE
            stats["void_resonance"] = int(stats.get("void_resonance", 0)) + int(round(banked_resonance))
            stats["void_emerges"] = int(stats.get("void_emerges", 0)) + 1

            self.state = self._clone_state(
                ship=self._clone_ship(
                    hull=max(1, self.state.ship.hull - hull_damage),
                    shield=max(0, self.state.ship.shield - shield_damage),
                    credits=self.state.ship.credits + resonance_credits,
                    mastery=new_mastery,
                    orbiting_body_id=horizon_id,
                    waypoint_au=0.0,
                    waypoint_angle=0.0,
                    void_traversal=None,
                    flight_log=tuple(new_log[-20:]),
                ),
                stats=stats,
            )
            self.emit_event(
                "void",
                "Void Emergence",
                f"The void releases you violently at {origin_name}. Shields and hull took shear damage."
                + (f" Resonance salvage: {resonance_credits} cr." if resonance_credits else ""),
            )
            return True, (
                f"Emergency emergence at {origin_name}. Hull -{hull_damage}, shields -{shield_damage}."
                + (f" Resonance yield: +{resonance_credits} cr, +{resonance_xp} XP." if resonance_credits or resonance_xp else "")
            )

    def void_status(self) -> dict[str, Any]:
        """Void traversal readiness, lanes, and active traversal state (CLI/REST/cockpit parity)."""
        with self.lock:
            lanes = generate_void_lanes(self.state.systems, self.state.galaxy_seed)
            cur_id = self.state.ship.current_system_id
            traversal = self.state.ship.void_traversal

            reasons: list[str] = []
            if self.state.active_combat is not None:
                reasons.append("Hostile tractor field locks the void drive")
            if self.state.active_anomaly is not None:
                reasons.append("Unresolved spatial anomaly in proximity")
            if self.state.ship.travel is not None:
                reasons.append("Sublight transit in progress")
            orbiting = self.orbiting_body
            if orbiting is None or orbiting.body_type != "black_hole":
                reasons.append("Orbit a black-hole event horizon to dive")

            destinations = []
            if not reasons:
                for sys_id in sorted(lanes.get(cur_id, ())):
                    dest = self.state.systems.get(sys_id)
                    if dest is None:
                        continue
                    plan = void_route_plan(self.state.systems, self.state.galaxy_seed, cur_id, sys_id)
                    destinations.append({
                        "system_id": sys_id,
                        "name": dest.name,
                        "fuel_estimate": plan["fuel_estimate"],
                        "duration_ticks": plan["duration_ticks"],
                    })

            emerge_now = (
                self._void_resonance_payout(
                    traversal.resonance,
                    traversal.progress(self.state.time.tick) * self.VOID_EMERGE_RESONANCE_SHARE,
                )
                if traversal else (0, 0)
            )
            return {
                "current_system_id": cur_id,
                "anchors": [sid for sid in lanes if any(
                    body.body_type == "black_hole" for body in self.state.systems[sid].bodies
                )],
                "lanes": {sid: list(neighbors) for sid, neighbors in lanes.items()},
                "traversal": traversal.to_dict() if traversal else None,
                "destination_name": (
                    self.state.systems[traversal.destination_system_id].name
                    if traversal and traversal.destination_system_id in self.state.systems
                    else None
                ),
                "traversal_progress": round(traversal.progress(self.state.time.tick), 3) if traversal else None,
                "resonance": round(traversal.resonance, 1) if traversal else 0.0,
                "projected_resonance_credits": self._void_resonance_payout(traversal.resonance)[0] if traversal else 0,
                "projected_resonance_xp": self._void_resonance_payout(traversal.resonance)[1] if traversal else 0,
                "projected_emerge_credits": emerge_now[0],
                "projected_emerge_xp": emerge_now[1],
                "dive_ready": not reasons,
                "blockers": reasons,
                "destinations": destinations,
                "storm_chance": round(self._void_storm_chance(), 3),
                "shield": self.state.ship.shield,
                "fuel": self.state.ship.fuel,
                # Push-your-luck projector: every number the gamble needs,
                # stated from the same constants the tick loop reads.
                "gamble": {
                    "storm_chance": round(self._void_storm_chance(), 3),
                    "stability_loss_per_storm": self.VOID_STORM_STABILITY_LOSS,
                    "shield_loss_per_storm": self.VOID_STORM_SHIELD_LOSS,
                    "hull_loss_per_storm": self.VOID_STORM_HULL_LOSS,
                    "low_stability_threshold": self.VOID_LOW_STABILITY_THRESHOLD,
                    "low_stability_bonus": self.VOID_LOW_STABILITY_RESONANCE_BONUS,
                    "emerge_share": self.VOID_EMERGE_RESONANCE_SHARE,
                    "collapse_hull_cost": self.VOID_EMERGENCE_HULL_DAMAGE,
                    "collapse_resonance_kept": 0.0,
                    "credits_per_resonance": self.VOID_RESONANCE_CREDITS,
                    "xp_per_resonance": self.VOID_RESONANCE_XP,
                    "arrival_xp": self.VOID_ARRIVAL_XP,
                    "first_visit_bonus": self.VOID_FIRST_VISIT_BONUS,
                },
            }

    def _process_drone_cycle(self, ship: ShipState) -> tuple[FleetDrone, ...]:
        """Advance autonomous drone harvest cycle across star systems."""
        updated_drones = []
        for d in ship.fleet_drones:
            assigned_system = self.state.systems.get(d.assigned_system_id)
            faction_id = get_faction_id_from_name(assigned_system.faction) if assigned_system else "sol_coalition"
            perks = get_faction_service_perks(faction_id, self.state.ship.faction_standings.get(faction_id, 0))
            yield_bonus = 1.0 + float(perks["drone_yield_bonus"])
            if d.drone_type == "mining":
                yield_amount = max(1, int(2 * d.efficiency * (0.5 + d.integrity / 200.0) * yield_bonus))
                updated_drones.append(
                    replace(
                        d,
                        status="harvesting",
                        cargo_accumulated=d.cargo_accumulated + yield_amount,
                        sorties=d.sorties + 1,
                        integrity=max(0, d.integrity - 1),
                        level=d.level + 1 if (d.sorties + 1) % 10 == 0 else d.level,
                    )
                )
            elif d.drone_type == "scout":
                yield_amount = max(10, int(75 * d.efficiency * (0.5 + d.integrity / 200.0) * yield_bonus))
                updated_drones.append(
                    replace(
                        d,
                        status="patrolling",
                        credits_accumulated=d.credits_accumulated + yield_amount,
                        sorties=d.sorties + 1,
                        integrity=max(0, d.integrity - 1),
                        level=d.level + 1 if (d.sorties + 1) % 10 == 0 else d.level,
                    )
                )
            else:
                updated_drones.append(d)
        return tuple(updated_drones)

    def jump(self, target_system_id: str) -> tuple[bool, str]:
        """Execute a hyperspace jump to an adjacent star system."""
        with self.lock:
            if self.state.active_combat is not None:
                return False, "Hyperspace drive locked by hostile enemy tractor field! Must resolve combat or flee."

            lock = self._action_lock_reason()
            if lock:
                return False, lock

            if self.state.active_anomaly is not None:
                return False, "Hyperspace drive locked: unresolved spatial anomaly in proximity!"

            cur_sys = self.current_system
            if target_system_id not in cur_sys.connections:
                return False, f"System '{target_system_id}' is not linked via hyperlane corridor."

            target_sys = self.state.systems.get(target_system_id)
            if not target_sys:
                return False, f"Unknown system target '{target_system_id}'."

            # Calculate fuel cost (with warp booster upgrade bonus, relics, and talents)
            passives = calculate_passive_multipliers(self.state.ship)
            equipment = self._combined_equipment()
            eng_pwr = self._effective_power("engines")
            base_fuel = 8
            if eng_pwr >= 40:
                fuel_cost = max(3, base_fuel - 3)
            elif eng_pwr < 20:
                fuel_cost = base_fuel + 4
            else:
                fuel_cost = base_fuel

            origin_map = self._map_effects(cur_sys)
            target_map = self._map_effects(target_sys)
            route_fuel_mult = (float(origin_map["fuel_mult"]) + float(target_map["fuel_mult"])) / 2.0
            research = self._research_bonuses()
            fuel_cost = max(1, int(fuel_cost * equipment["fuel_efficiency"] * passives["fuel_efficiency"] * research["fuel_efficiency"] * (1.0 - min(0.25, self._skill("piloting"))) * route_fuel_mult))
            fuel_cost = max(
                1,
                fuel_cost - int(self._megastructure_bonuses()["jump_fuel"]),
            )

            if self.state.ship.fuel < fuel_cost:
                return False, f"Insufficient Quantum Fuel: {fuel_cost} units required, {self.state.ship.fuel} available."

            # Execute jump
            self._local_dock_purchases.clear()
            new_fuel = self.state.ship.fuel - fuel_cost
            visited = set(self.state.visited_systems)
            visited.add(target_system_id)

            # Update streak (rewarding safe transit under loss aversion mechanics)
            new_streak = min(int(STREAK_TUNING["max_streak"]), self.state.ship.streak + 1) if self.state.ship.hull >= 75 else self.state.ship.streak
            streak_mult = streak_multiplier(new_streak)
            log_entry = f"Hyperspace jump completed to {target_sys.name} (fuel: {fuel_cost}). Streak: x{streak_mult:.2f} ({new_streak} jumps)."
            if system_has_black_hole(target_sys):
                log_entry += " WARNING: gravitational shear from a black hole increased fuel demand and reactor load."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            # Process autonomous fleet drone cycle
            updated_drones = self._process_drone_cycle(self.state.ship)

            # Progress exploration contracts and award navigation pilot XP
            updated_contracts, contract_logs = self._progress_contracts("exploration", 1)
            new_log.extend(contract_logs)
            new_mastery, xp_logs = self._award_pilot_xp(35, self.state.ship.mastery)
            new_log.extend(xp_logs)

            # Encounter calculation
            anomaly = None
            combat = None

            # Check hostile faction interception or low security ambush
            has_escort = any(d.drone_type == "combat_escort" for d in self.state.ship.fleet_drones)
            sys_faction_id = get_faction_id_from_name(target_sys.faction)
            standing = self.state.ship.faction_standings.get(sys_faction_id, 0)
            is_hostile_territory = standing <= -50
            home_faction_id = get_faction_id_from_name(cur_sys.faction)
            home_standing = self.state.ship.faction_standings.get(home_faction_id, 0)
            escort_evasion = 0.25 if home_standing >= 70 else 0.0
            reactor_mode = get_reactor_mode(self.state.ship.reactor.mode)
            encounter_evasion = min(
                0.90,
                equipment["pirate_evasion"]
                + escort_evasion
                + float(origin_map["evasion"])
                + float(target_map["evasion"])
                + float(reactor_mode.get("evasion", 0.0)),
            )
            encounter_risk_mult = float(target_map["encounter_mult"]) * float(reactor_mode.get("encounter_mult", 1.0))

            if is_hostile_territory and self.rng.random() < min(0.95, JUMP_ENCOUNTER_TUNING["hostile_sec_combat"] * encounter_risk_mult * (1.0 - encounter_evasion)):
                combat = generate_system_enemy(
                    system_id=target_system_id,
                    security=target_sys.security,
                    faction=target_sys.faction,
                    seed=self.rng.randint(1000, 99999),
                    threat_level=self.state.ship.mastery.level,
                )
                new_log.append(f"HOSTILE PATROL: Intercepted by {combat.enemy_name} due to hostile faction standing ({standing})!")
            elif target_sys.security < 0.35:
                if has_escort:
                    new_log.append("TACTICAL: Combat escort frigate dispersed hostile ambush.")
                elif self.rng.random() < min(0.95, JUMP_ENCOUNTER_TUNING["low_sec_combat"] * encounter_risk_mult * (1.0 - encounter_evasion)):
                    combat = generate_system_enemy(
                        system_id=target_system_id,
                        security=target_sys.security,
                        faction=target_sys.faction,
                        seed=self.rng.randint(1000, 99999),
                        threat_level=self.state.ship.mastery.level,
                    )
                    new_log.append(f"ALERT: Intercepted by hostile {combat.enemy_name}! Weapons locked.")

            if not combat and self.rng.random() < JUMP_ENCOUNTER_TUNING["anomaly"]:
                anomaly = GalaxyGenerator.get_random_anomaly(self.rng.randint(1, 99999))
                new_log.append(f"WARNING: Deep-space anomaly detected! [{anomaly.title}]")

            active_pirate = None
            if not combat and not anomaly and self.allow_decision_events:
                patrol_escorts = sum(
                    1 for escort in self.state.ship.fleet_ships
                    if escort.assigned_system_id == target_system_id and escort.hull > 0
                )
                raid_risk = pirate_risk(
                    target_sys, standing, has_escort, encounter_evasion,
                    patrol_escorts=patrol_escorts,
                    allied=(
                        target_sys.faction != "Unclaimed"
                        and get_faction_id_from_name(target_sys.faction)
                        in self.state.ship.allies
                    ),
                )
                pirate_roll = self._stable_unit(
                    self.state.galaxy_seed, "pirate", target_system_id, self.state.time.tick
                )
                if pirate_roll < raid_risk.chance:
                    active_pirate = generate_pirate_encounter(
                        target_sys,
                        seed=int(self._stable_unit(
                            self.state.galaxy_seed, "pirate_seed", target_system_id, self.state.time.tick
                        ) * 99999) + 1,
                        threat_level=max(1, self.state.ship.mastery.level),
                        standing=standing,
                    )
                    new_log.append(
                        f"PIRATE ENCOUNTER: {active_pirate.band_name} demands "
                        f"{active_pirate.toll_credits} cr for safe passage ({raid_risk.reason})."
                    )
            # Check contraband security customs inspection in high-security systems
            active_customs = None
            if not combat and not anomaly and active_pirate is None:
                contraband = get_contraband_in_cargo(self.state.ship.cargo)
                if contraband and target_sys.security >= 0.65:
                    scan_chance, _ = calculate_customs_scan_risk(
                        target_sys, self.state.ship.cargo, self.state.ship, self.state.ship.power, equipment
                    )
                    customs_roll = self._stable_unit(
                        self.state.galaxy_seed, "customs", target_system_id, self.state.time.tick
                    )
                    if customs_roll < scan_chance:
                        active_customs = generate_customs_encounter(
                            target_sys,
                            self.state.ship.cargo,
                            self.state.ship,
                            seed=int(self._stable_unit(
                                self.state.galaxy_seed, "customs_seed", target_system_id, self.state.time.tick
                            ) * 99999) + 1,
                        )
                        new_log.append(
                            f"CUSTOMS INTERDICTION: {active_customs.patrol_vessel} locked scanners on illicit cargo ({len(contraband)} types detected)!"
                        )

            # Tutorial progression on hyperspace jump
            new_tut, tut_cr, tut_xp, tut_relics, tut_logs = self._progress_tutorial("jump")
            new_log.extend(tut_logs)
            if tut_xp > 0:
                new_mastery, xp_logs = self._award_pilot_xp(tut_xp, new_mastery)
                new_log.extend(xp_logs)

            # Story transmission alert if arrived in chapter target system
            story = self.state.ship.story
            new_story = story
            if not story.completed and story.current_chapter_index < len(story.chapters):
                cur_chap = story.chapters[story.current_chapter_index]
                if cur_chap.target_system_id == target_system_id and not cur_chap.completed:
                    new_log.append(f"📡 INCOMING SUBSPACE TRANSMISSION: [{cur_chap.transmission.speaker}] '{cur_chap.title}'")
                    existing_msgs = {t.message for t in story.transmission_log}
                    if cur_chap.transmission.message not in existing_msgs:
                        new_story = StoryState(
                            campaign_title=story.campaign_title,
                            current_chapter_index=story.current_chapter_index,
                            chapters=story.chapters,
                            transmission_log=tuple(list(story.transmission_log) + [cur_chap.transmission]),
                            reputation=story.reputation,
                            completed=story.completed,
                        )

            new_hull, new_max_hull, new_shield, new_max_shield = self._apply_relic_stat_bonuses(
                self.state.ship.hull,
                self.state.ship.max_hull,
                self.state.ship.shield,
                self.state.ship.max_shield,
                tut_relics,
            )

            # Solar storm space weather hazards in high-energy spectral systems
            new_reactor = self.state.ship.reactor
            if not combat and target_sys.spectral_type in ("O", "B", "WolfRayet", "RedGiant", "Neutron"):
                weather_roll = self._stable_unit(
                    self.state.galaxy_seed, "solar_weather", target_system_id, self.state.time.tick
                )
                if weather_roll < 0.35:
                    if self.state.ship.power.shields >= 35:
                        new_log.append(
                            f"SPACE WEATHER DEFLECTION: Deflector grid ({self.state.ship.power.shields}% power) deflected high-energy coronal solar flare from {target_sys.name} (+25 Pilot XP)."
                        )
                        new_mastery, xp_logs = self._award_pilot_xp(25, new_mastery)
                        new_log.extend(xp_logs)
                    else:
                        surge_drain = 15
                        if new_shield >= surge_drain:
                            new_shield -= surge_drain
                        else:
                            overflow = surge_drain - new_shield
                            new_shield = 0
                            new_hull = max(1, new_hull - overflow)
                        max_h = reactor_heat_capacity(new_reactor, equipment)
                        new_reactor = replace(new_reactor, heat=min(max_h, new_reactor.heat + 8.0))
                        new_log.append(
                            f"SPACE WEATHER HAZARD: High-energy coronal solar flare from {target_sys.name} penetrated deflector grid! (-15 Shield, +8 Reactor Heat). Maintain Shields >= 35% in high-energy systems to deflect radiation."
                        )

            arrival_crew = self.state.ship.crew
            if is_hostile_territory:
                arrival_crew, hostile_morale_log = apply_morale_event(
                    self.state.ship.crew, -2.0, f"arrival in hostile {target_sys.name} territory"
                )
                if hostile_morale_log:
                    new_log.append(hostile_morale_log)

            new_ship = self._clone_ship(
                hull=new_hull,
                max_hull=new_max_hull,
                shield=new_shield,
                max_shield=new_max_shield,
                reactor=new_reactor,
                fuel=new_fuel,
                credits=self.state.ship.credits + tut_cr,
                current_system_id=target_system_id,
                orbiting_body_id=target_sys.bodies[0].id if target_sys.bodies else None,
                landed_body_id=None,
                travel=None,
                waypoint_au=0.0,
                waypoint_angle=0.0,
                fleet_drones=updated_drones,
                flight_log=tuple(new_log[-20:]),
                streak=new_streak,
                wear=min(100.0, self.state.ship.wear + 1.0),
                mastery=new_mastery,
                relics=tuple(list(self.state.ship.relics) + tut_relics),
                active_contracts=updated_contracts,
                tactical_combo=0,
                tutorial=new_tut,
                story=new_story,
                crew=arrival_crew,
            )

            stats = dict(self.state.stats)
            stats["jumps"] += 1
            if active_pirate is not None:
                stats["pirate_encounters"] = int(stats.get("pirate_encounters", 0)) + 1

            # Advance cosmic time by 2 ticks (12 hours transit) during interstellar hyperspace jump
            cur_time = self.state.time
            new_tick = cur_time.tick + 2
            new_days = cur_time.elapsed_days + 0.5
            new_stardate = 3042.0 + (new_days / 365.25)
            transit_time = TimeState(
                tick=new_tick,
                stardate=new_stardate,
                speed=cur_time.speed,
                is_paused=cur_time.is_paused,
                time_scale=cur_time.time_scale,
                elapsed_days=new_days,
            )

            # Advance planetary orbits across all systems by 2 transit ticks
            stability_by_faction = self._faction_stability()
            updated_systems = {}
            for sys_id, system in self.state.systems.items():
                faction_stability = stability_by_faction.get(system.faction, 50.0)
                updated_bodies = []
                for body in system.bodies:
                    d_angle = body.orbit_speed * 0.05 * 2
                    updated_pop = (
                        step_population_dynamics(body, 2, faction_stability)
                        if body.population > 0
                        else body.population
                    )
                    recovery = devastation_recovery(body.tech_level, faction_stability) * 2
                    updated_bodies.append(
                        replace(
                            body,
                            current_angle=(body.current_angle + d_angle) % (2.0 * math.pi),
                            population=updated_pop,
                            devastation=max(0.0, (body.devastation or 0.0) - recovery),
                        )
                    )
                updated_systems[sys_id] = StarSystem(
                    id=system.id,
                    name=system.name,
                    seed=system.seed,
                    x=system.x,
                    y=system.y,
                    spectral_type=system.spectral_type,
                    color=system.color,
                    security=system.security,
                    faction=system.faction,
                    bodies=tuple(updated_bodies),
                    connections=system.connections,
                    dominant_corp=system.dominant_corp,
                    modifiers=system.modifiers,
                )

            # Advance global economy by 2 transit ticks
            new_econ, econ_logs = tick_global_economy(self.state.economy, 2, self.state.systems, self.rng)
            if econ_logs:
                new_flight_log = list(new_ship.flight_log) + econ_logs
                new_ship = replace(new_ship, flight_log=tuple(trim_log(new_flight_log)))

            self.state = self._clone_state(
                ship=new_ship,
                systems=updated_systems,
                visited_systems=tuple(sorted(visited)),
                active_anomaly=anomaly,
                active_combat=combat,
                active_pirate=active_pirate,
                active_customs=active_customs,
                stats=stats,
                time=transit_time,
                economy=new_econ,
                local_dock_purchases={},
            )

            msg = f"Jump successful: arrived in {target_sys.name}."
            if self.allow_decision_events:
                self.maybe_trigger_decision("jump")
            if combat:
                msg += f" WARNING: Intercepted by {combat.enemy_name}!"
            return True, msg

    def _ship_position(self) -> tuple[float, float]:
        """Current in-system position: the orbited body, or the open-space anchor."""
        origin = self.orbiting_body
        if origin is not None:
            return float(origin.orbit_radius), float(origin.current_angle or 0.0)
        return float(self.state.ship.waypoint_au or 0.0), float(self.state.ship.waypoint_angle or 0.0)

    def compute_body_distance_au(
        self,
        target_body: CelestialBody,
        origin_body: CelestialBody | None = None,
    ) -> float:
        """Compute 2D polar Euclidean distance in AU from the current position to a body."""
        if origin_body is not None:
            origin_au = float(origin_body.orbit_radius)
            origin_angle = float(origin_body.current_angle or 0.0)
        else:
            origin_au, origin_angle = self._ship_position()
        ox = origin_au * math.cos(origin_angle)
        oy = origin_au * math.sin(origin_angle)
        tx = target_body.orbit_radius * math.cos(target_body.current_angle)
        ty = target_body.orbit_radius * math.sin(target_body.current_angle)
        return round(max(0.25, math.hypot(tx - ox, ty - oy)), 2)

    def orbit(self, body_id: str) -> tuple[bool, str]:
        """Establish orbital trajectory around a celestial body in the current system."""
        with self.lock:
            cur_sys = self.current_system
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            matched = None
            for b in cur_sys.bodies:
                if b.id == body_id:
                    matched = b
                    break

            if not matched:
                return False, f"Celestial body '{body_id}' not found in {cur_sys.name}."

            active = self.state.ship.travel
            if active is not None and active.origin_body_id != body_id:
                return (
                    False,
                    "In transit: wait for arrival, or orbit the origin body to abort the trip.",
                )

            distance_au = self.compute_body_distance_au(matched)
            log_entry = f"Orbital capture achieved around {matched.name} ({distance_au:.1f} AU)."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            new_tut, tut_cr, tut_xp, tut_relics, tut_logs = self._progress_tutorial("orbit")
            new_log.extend(tut_logs)
            new_mastery, xp_logs = self._award_pilot_xp(tut_xp, self.state.ship.mastery) if tut_xp > 0 else (self.state.ship.mastery, [])
            new_log.extend(xp_logs)

            new_ship = self._clone_ship(
                orbiting_body_id=body_id,
                landed_body_id=None,
                travel=None,
                waypoint_au=0.0,
                waypoint_angle=0.0,
                credits=self.state.ship.credits + tut_cr,
                mastery=new_mastery,
                relics=tuple(list(self.state.ship.relics) + tut_relics),
                tutorial=new_tut,
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(ship=new_ship)
            if self.allow_decision_events:
                self.maybe_trigger_decision("orbit")
            return True, f"Now in orbit around {matched.name} ({distance_au:.1f} AU)."

    def _transit_risk(self, system: StarSystem | None, mode: str,
                      effects: dict[str, float] | None = None) -> tuple[float, list[str]]:
        """Sector hazard risk for one in-system transit, reduced by piloting and quantum drive."""
        map_effects = effects if effects is not None else self._map_effects(system)
        hazard = max(0.0, float(map_effects.get("hull_hazard", 0.0)))
        encounter = max(0.0, float(map_effects.get("encounter_mult", 1.0)) - 1.0)
        evasion = float(map_effects.get("evasion", 0.0)) + self._skill("piloting") * 0.5
        risk = 0.03 + hazard * 0.10 + encounter * 0.08
        risk *= max(0.25, 1.0 - evasion)
        if mode == "quantum":
            risk *= 0.35
        risk = max(0.03, min(0.45, risk))
        hazards = sorted({
            modifier.name for modifier in (system.modifiers if system else ())
            if modifier.category == "hazard"
        })
        return round(risk, 3), hazards

    def _travel_plan(self, body_id: str, mode: str) -> tuple[dict[str, Any] | None, str]:
        """Compute a transit plan without mutating state; shared by preview and execution."""
        norm_mode = str(mode).strip().lower()
        if norm_mode not in ("sublight", "quantum"):
            return None, f"Invalid transit mode '{mode}'. Choose 'sublight' or 'quantum'."

        cur_sys = self.current_system
        matched = next((b for b in cur_sys.bodies if b.id == body_id), None)
        if not matched:
            return None, f"Celestial body '{body_id}' not found in {cur_sys.name}."

        origin = self.orbiting_body
        origin_id = origin.id if origin else None
        distance_au = self.compute_body_distance_au(matched)
        map_effects = self._map_effects(cur_sys)
        risk, hazards = self._transit_risk(cur_sys, norm_mode, map_effects)

        fuel_cost = 0
        if norm_mode == "quantum":
            equipment = self._combined_equipment()
            passives = calculate_passive_multipliers(self.state.ship)
            research = self._research_bonuses()
            fuel_mult = (
                float(map_effects["fuel_mult"])
                * equipment["fuel_efficiency"]
                * passives.get("fuel_efficiency", 1.0)
                * research.get("fuel_efficiency", 1.0)
                * (1.0 - min(0.25, self._skill("piloting")))
            )
            fuel_cost = max(2, int(math.ceil(distance_au * 1.0 * fuel_mult)))
            duration_ticks = 1
        else:
            engine_factor = max(0.4, self._effective_power("engines") / 25.0) * (1.0 + self._skill("piloting"))
            sublight_speed_au = max(0.35, 1.15 * engine_factor)
            duration_ticks = max(1, int(math.ceil(distance_au / sublight_speed_au)))

        blocked_reason = ""
        if origin is not None and origin.id == matched.id:
            blocked_reason = f"Already in orbit around {matched.name}."
        elif self.state.ship.travel is not None:
            active = self.state.ship.travel
            destination_name = next(
                (b.name for b in cur_sys.bodies if b.id == active.destination_body_id),
                "open space" if active.destination_body_id is None else active.destination_body_id,
            )
            blocked_reason = (
                f"Already in transit to {destination_name}; "
                f"arrival is scheduled for tick {active.arrival_tick}."
            )
        elif norm_mode == "quantum" and self.state.ship.fuel < fuel_cost:
            blocked_reason = f"Insufficient quantum fuel: need {fuel_cost}, have {self.state.ship.fuel}."
        return {
            "mode": norm_mode,
            "body_id": matched.id,
            "body_name": matched.name,
            "origin_body_id": origin_id,
            "distance_au": round(distance_au, 2),
            "duration_ticks": duration_ticks,
            "fuel_cost": fuel_cost,
            "risk": risk,
            "hazards": hazards,
            "can_start": not blocked_reason,
            "blocked_reason": blocked_reason,
        }, ""

    def preview_travel(self, body_id: str, mode: str = "sublight") -> tuple[bool, dict[str, Any] | str]:
        """Return ETA, fuel, risk and hazard names for a potential transit."""
        with self.lock:
            plan, message = self._travel_plan(body_id, mode)
            if plan is None:
                return False, message
            return True, plan

    EMPTY_SPACE_MIN_AU = 0.05
    EMPTY_SPACE_MAX_AU = 60.0

    def _point_travel_plan(
        self, waypoint_au: float, waypoint_angle: float, mode: str
    ) -> tuple[dict[str, Any] | None, str]:
        """Plan a transit to an empty-space vector, measured from the system's star."""
        norm_mode = str(mode).strip().lower()
        if norm_mode not in ("sublight", "quantum"):
            return None, f"Invalid transit mode '{mode}'. Choose 'sublight' or 'quantum'."
        try:
            target_au = float(waypoint_au)
            target_angle = float(waypoint_angle)
        except (TypeError, ValueError, OverflowError):
            return None, "Waypoint needs a numeric distance and bearing."
        if not math.isfinite(target_au) or not math.isfinite(target_angle):
            return None, "Waypoint distance and bearing must be finite numbers."
        if not self.EMPTY_SPACE_MIN_AU <= target_au <= self.EMPTY_SPACE_MAX_AU:
            return (
                None,
                f"Waypoint {target_au:.2f} AU is outside the "
                f"{self.EMPTY_SPACE_MIN_AU}-{self.EMPTY_SPACE_MAX_AU} AU transit envelope.",
            )

        cur_sys = self.current_system
        origin = self.orbiting_body
        origin_au, origin_angle = self._ship_position()
        dx = math.cos(target_angle) * target_au - math.cos(origin_angle) * origin_au
        dy = math.sin(target_angle) * target_au - math.sin(origin_angle) * origin_au
        distance_au = max(0.0, math.hypot(dx, dy))
        map_effects = self._map_effects(cur_sys)
        risk, hazards = self._transit_risk(cur_sys, norm_mode, map_effects)

        fuel_cost = 0
        if norm_mode == "quantum":
            equipment = self._combined_equipment()
            passives = calculate_passive_multipliers(self.state.ship)
            research = self._research_bonuses()
            fuel_mult = (
                float(map_effects["fuel_mult"])
                * equipment["fuel_efficiency"]
                * passives.get("fuel_efficiency", 1.0)
                * research.get("fuel_efficiency", 1.0)
                * (1.0 - min(0.25, self._skill("piloting")))
            )
            fuel_cost = max(2, int(math.ceil(distance_au * 1.0 * fuel_mult)))
            duration_ticks = 1
        else:
            engine_factor = max(0.4, self._effective_power("engines") / 25.0) * (1.0 + self._skill("piloting"))
            sublight_speed_au = max(0.35, 1.15 * engine_factor)
            duration_ticks = max(1, int(math.ceil(distance_au / sublight_speed_au)))

        blocked_reason = ""
        if distance_au < 0.05:
            blocked_reason = "You are already holding station at that vector."
        elif self.state.ship.travel is not None:
            active = self.state.ship.travel
            destination_name = next(
                (b.name for b in cur_sys.bodies if b.id == active.destination_body_id),
                "open space",
            )
            blocked_reason = (
                f"Already in transit to {destination_name}; "
                f"arrival is scheduled for tick {active.arrival_tick}."
            )
        elif norm_mode == "quantum" and self.state.ship.fuel < fuel_cost:
            blocked_reason = f"Insufficient quantum fuel: need {fuel_cost}, have {self.state.ship.fuel}."
        return {
            "mode": norm_mode,
            "body_id": None,
            "body_name": f"Open space {target_au:.2f} AU",
            "origin_body_id": origin.id if origin else None,
            "destination_au": round(target_au, 3),
            "destination_angle": round(target_angle, 4),
            "distance_au": round(distance_au, 2),
            "duration_ticks": duration_ticks,
            "fuel_cost": fuel_cost,
            "risk": risk,
            "hazards": hazards,
            "can_start": not blocked_reason,
            "blocked_reason": blocked_reason,
        }, ""

    def start_travel_to_point(
        self, waypoint_au: float, waypoint_angle: float, mode: str = "sublight"
    ) -> tuple[bool, str]:
        """Fly to an empty-space vector instead of a body: no orbit is established on arrival."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            plan, message = self._point_travel_plan(waypoint_au, waypoint_angle, mode)
            if plan is None:
                return False, message
            if not plan["can_start"]:
                return False, str(plan["blocked_reason"])

            distance_au = float(plan["distance_au"])
            duration_ticks = int(plan["duration_ticks"])
            fuel_cost = int(plan["fuel_cost"])
            hazard_hit = self.rng.random() < float(plan["risk"])
            shield_loss = 0
            hull_loss = 0
            hazard_delay = 0
            hazard_name = ""
            if hazard_hit:
                hazard_delay = 1
                damage = max(4, min(18, int(4 + distance_au * 0.5)))
                shield_loss = min(self.state.ship.shield, damage)
                hull_loss = min(max(0, self.state.ship.hull - 1), damage - shield_loss)
                hazard_name = " // ".join(plan["hazards"]) or "Micrometeoroid Swarm"

            cur_tick = self.state.time.tick
            total_ticks = duration_ticks + hazard_delay
            travel = TravelState(
                origin_body_id=plan["origin_body_id"],
                destination_body_id=None,
                mode=plan["mode"],
                started_tick=cur_tick,
                arrival_tick=cur_tick + total_ticks,
                distance_au=distance_au,
                duration_ticks=total_ticks,
                waypoint_au=float(plan["destination_au"]),
                waypoint_angle=float(plan["destination_angle"]),
            )
            label = plan["body_name"]
            log_entry = (
                f"Engaged {plan['mode']} drive toward {label} "
                f"({distance_au:.1f} AU, ETA {total_ticks} tick(s), fuel: {fuel_cost})."
            )
            new_events = list(self.state.events)
            if hazard_hit:
                log_entry += (
                    f" TRANSIT HAZARD: {hazard_name}; shields -{shield_loss}, "
                    f"hull -{hull_loss}, ETA +{hazard_delay} tick."
                )
                new_events.append(GameEvent(
                    id=f"evt_{cur_tick}_{len(new_events) + 1}",
                    kind="hazard",
                    title=f"Transit Hazard: {hazard_name}",
                    message=(
                        f"{hazard_name} struck during transit to {label}. "
                        f"Shields -{shield_loss}, hull -{hull_loss}, arrival delayed by {hazard_delay} tick."
                    ),
                    tick=cur_tick,
                    dismissed=False,
                ))
            new_ship = self._clone_ship(
                fuel=self.state.ship.fuel - fuel_cost,
                shield=self.state.ship.shield - shield_loss,
                hull=self.state.ship.hull - hull_loss,
                landed_body_id=None,
                travel=travel,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log_entry]),
            )
            new_time = replace(self.state.time, is_paused=False) if self.state.time.is_paused else self.state.time
            self.state = self._clone_state(ship=new_ship, time=new_time, events=tuple(new_events))
            return True, log_entry

    def start_travel(self, body_id: str, mode: str = "sublight") -> tuple[bool, str]:
        """Initiate sublight or quantum in-system transit toward a celestial body."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            plan, message = self._travel_plan(body_id, mode)
            if plan is None:
                return False, message
            if not plan["can_start"]:
                return False, str(plan["blocked_reason"])

            cur_sys = self.current_system
            matched = next(b for b in cur_sys.bodies if b.id == body_id)
            distance_au = float(plan["distance_au"])
            duration_ticks = int(plan["duration_ticks"])
            fuel_cost = int(plan["fuel_cost"])
            hazard_hit = self.rng.random() < float(plan["risk"])

            shield_loss = 0
            hull_loss = 0
            hazard_delay = 0
            hazard_name = ""
            if hazard_hit:
                hazard_delay = 1
                damage = max(4, min(18, int(4 + distance_au * 0.5)))
                shield_loss = min(self.state.ship.shield, damage)
                hull_loss = min(max(0, self.state.ship.hull - 1), damage - shield_loss)
                hazard_name = " // ".join(plan["hazards"]) or "Micrometeoroid Swarm"

            cur_tick = self.state.time.tick
            total_ticks = duration_ticks + hazard_delay
            travel = TravelState(
                origin_body_id=plan["origin_body_id"],
                destination_body_id=matched.id,
                mode=plan["mode"],
                started_tick=cur_tick,
                arrival_tick=cur_tick + total_ticks,
                distance_au=distance_au,
                duration_ticks=total_ticks,
            )

            log_entry = (
                f"Engaged {plan['mode']} drive toward {matched.name} "
                f"({distance_au:.1f} AU, ETA {total_ticks} tick(s), fuel: {fuel_cost})."
            )
            new_events = list(self.state.events)
            if hazard_hit:
                log_entry += (
                    f" TRANSIT HAZARD: {hazard_name}; shields -{shield_loss}, "
                    f"hull -{hull_loss}, ETA +{hazard_delay} tick."
                )
                new_events.append(GameEvent(
                    id=f"evt_{cur_tick}_{len(new_events) + 1}",
                    kind="hazard",
                    title=f"Transit Hazard: {hazard_name}",
                    message=(
                        f"{hazard_name} struck during transit to {matched.name}. "
                        f"Shields -{shield_loss}, hull -{hull_loss}, arrival delayed by {hazard_delay} tick."
                    ),
                    tick=cur_tick,
                    dismissed=False,
                ))
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            new_ship = self._clone_ship(
                fuel=self.state.ship.fuel - fuel_cost,
                shield=self.state.ship.shield - shield_loss,
                hull=self.state.ship.hull - hull_loss,
                landed_body_id=None,
                travel=travel,
                flight_log=tuple(new_log[-20:]),
            )
            new_time = replace(self.state.time, is_paused=False) if self.state.time.is_paused else self.state.time
            self.state = self._clone_state(ship=new_ship, time=new_time, events=tuple(new_events))
            return True, log_entry

    def scan(self) -> tuple[bool, str, dict[str, Any]]:
        """Perform sensor sweep of current body or local space."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock, {}
            transit = self._transit_lock_reason()
            if transit:
                return False, transit, {}
            body = self.docked_body
            if not body:
                return False, "Cannot scan: ship must establish orbit around a celestial body first.", {}

            if body.scan_completed:
                return False, f"{body.name} has already been surveyed; no further research bounty is available.", {}

            passives = calculate_passive_multipliers(self.state.ship)
            equipment = self._combined_equipment()
            map_effects = self._map_effects()
            pwr = self._effective_power("sensors") * float(map_effects["sensor_mult"])
            if pwr < self.MIN_SURVEY_SENSOR_POWER:
                return (
                    False,
                    f"Sensor array needs at least {self.MIN_SURVEY_SENSOR_POWER:.0f} MW to resolve a survey "
                    f"(currently {pwr:.1f} MW). Route reactor power to sensors first.",
                    {},
                )
            credit_bounty = int(100 * (pwr / 25.0))
            research = self._research_bonuses()
            credit_bounty = int(credit_bounty * equipment["scan_mult"] * passives["scan_bounty"] * research["scan_mult"] * (1.0 + self._skill("science")) * float(map_effects["scan_mult"]))

            # Mark scan completed on body
            was_complete = all(b.scan_completed for b in self.current_system.bodies)
            updated_bodies = []
            for b in self.current_system.bodies:
                if b.id == body.id:
                    scanned = replace(b, scan_completed=True)
                    updated_bodies.append(scanned)
                else:
                    updated_bodies.append(b)
            survey_complete = all(b.scan_completed for b in updated_bodies)
            newly_complete = survey_complete and not was_complete
            survey_bonus = self.SURVEY_COMPLETION_CREDITS if newly_complete else 0
            survey_xp = self.SURVEY_COMPLETION_XP if newly_complete else 0

            cur_sys = self.current_system
            new_sys = StarSystem(
                id=cur_sys.id,
                name=cur_sys.name,
                seed=cur_sys.seed,
                x=cur_sys.x,
                y=cur_sys.y,
                spectral_type=cur_sys.spectral_type,
                color=cur_sys.color,
                security=cur_sys.security,
                faction=cur_sys.faction,
                bodies=tuple(updated_bodies),
                connections=cur_sys.connections,
                dominant_corp=cur_sys.dominant_corp,
                modifiers=cur_sys.modifiers,
            )

            systems = dict(self.state.systems)
            systems[cur_sys.id] = new_sys

            # Award credit bounty and full-system survey completion bonus
            new_credits = self.state.ship.credits + credit_bounty + survey_bonus

            # Variable Ratio relic drop and near-miss feedback
            relic_bonus = (
                passives["relic_find"]
                + equipment["relic_find"]
                + float(map_effects["relic_find"])
                + self.state.ship.near_miss_scanner_bonus
            )
            found_relic, is_near_miss = roll_relic_drop(self.rng, bonus_prob=relic_bonus, current_system=cur_sys.name)
            new_relics = list(self.state.ship.relics)
            new_near_miss = 0.0

            log_entry = f"Sensor scan completed for {body.name}: awarded {credit_bounty} cr scientific research bounty."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            if newly_complete:
                new_log.append(
                    f"SYSTEM SURVEY COMPLETE: {cur_sys.name} fully charted "
                    f"(+{survey_bonus} cr, +{survey_xp} XP)."
                )

            if found_relic:
                new_relics.append(found_relic)
                new_log.append(f"★ PRECURSOR ARTIFACT DISCOVERED: Salvaged {found_relic.rarity.upper()} relic [{found_relic.name}]! {found_relic.description}")
            elif is_near_miss:
                new_near_miss = NEAR_MISS_SCAN_BONUS
                new_log.append("RESONANCE NEAR-MISS: Faint Precursor harmonics slipped out of phase! Sensor array tuned (+25% discovery chance next scan).")

            # Progress exploration contracts and award survey pilot XP
            updated_contracts, contract_logs = self._progress_contracts("exploration", 1)
            new_log.extend(contract_logs)
            scan_faction_id = get_faction_id_from_name(cur_sys.faction)
            scan_perks = get_faction_service_perks(scan_faction_id, self.state.ship.faction_standings.get(scan_faction_id, 0))
            scan_xp = int(50 * (1.0 + float(scan_perks["scan_xp_bonus"]))) + survey_xp
            new_mastery, xp_logs = self._award_pilot_xp(scan_xp, self.state.ship.mastery)
            new_log.extend(xp_logs)

            new_tut, tut_cr, tut_xp, tut_relics, tut_logs = self._progress_tutorial("scan")
            new_log.extend(tut_logs)
            if tut_xp > 0:
                new_mastery, tut_xp_logs = self._award_pilot_xp(tut_xp, new_mastery)
                new_log.extend(tut_xp_logs)

            added_relics = ([found_relic] if found_relic else []) + list(tut_relics)
            new_hull, new_max_hull, new_shield, new_max_shield = self._apply_relic_stat_bonuses(
                self.state.ship.hull,
                self.state.ship.max_hull,
                self.state.ship.shield,
                self.state.ship.max_shield,
                added_relics,
            )

            new_ship = self._clone_ship(
                hull=new_hull,
                max_hull=new_max_hull,
                shield=new_shield,
                max_shield=new_max_shield,
                credits=new_credits + tut_cr,
                relics=tuple(new_relics + tut_relics),
                near_miss_scanner_bonus=new_near_miss,
                mastery=new_mastery,
                active_contracts=updated_contracts,
                tutorial=new_tut,
                flight_log=tuple(new_log[-20:]),
            )

            stats = dict(self.state.stats)
            stats["scans"] += 1
            stats["credits_earned"] += credit_bounty + survey_bonus
            if newly_complete:
                stats["systems_surveyed"] = int(stats.get("systems_surveyed", 0)) + 1
            if is_near_miss:
                stats["near_miss_scans"] = int(stats.get("near_miss_scans", 0)) + 1

            self.state = self._clone_state(ship=new_ship, systems=systems, stats=stats)
            anomaly_roll = self._stable_unit(
                self.state.galaxy_seed, "anomaly", body.id, self.state.time.tick, stats["scans"]
            )
            if anomaly_roll < 0.10:
                anomaly = GalaxyGenerator.get_random_anomaly(
                    int(self._stable_unit(
                        self.state.galaxy_seed, "anomaly_seed", body.id, self.state.time.tick, stats["scans"]
                    ) * 99999) + 1
                )
                warning = f"ANOMALY CONTACT: Sensor sweep disturbed {anomaly.title}."
                new_log = list(self.state.ship.flight_log[-19:]) + [warning]
                self.state = self._clone_state(
                    ship=self._clone_ship(flight_log=tuple(new_log[-20:])),
                    active_anomaly=anomaly,
                )

            if self.allow_decision_events:
                self.maybe_trigger_decision("scan")

            discovery_info = {
                "body_name": body.name,
                "body_type": body.body_type,
                "discovery": body.scan_discovery,
                "bounty": credit_bounty,
                "market_archetype": body.market_archetype,
                "hazards": list(body.hazards),
                "relic": found_relic.to_dict() if found_relic else None,
                "near_miss": is_near_miss,
                "relic_odds": {
                    "base_threshold": RELIC_BASE_THRESHOLD,
                    "bonus_prob": round(relic_bonus, 3),
                    "effective_threshold": round(RELIC_BASE_THRESHOLD + relic_bonus, 3),
                    "near_miss_window": RELIC_NEAR_MISS_WINDOW,
                },
                "survey_complete": newly_complete,
                "survey_bonus": survey_bonus,
            }

            if newly_complete:
                return (
                    True,
                    f"Scan analysis complete: {body.scan_discovery} SYSTEM SURVEY COMPLETE (+{survey_bonus} cr, +{survey_xp} XP).",
                    discovery_info,
                )
            return True, f"Scan analysis complete: {body.scan_discovery}", discovery_info

    def route_power(self, engines: int, shields: int, sensors: int, weapons: int) -> tuple[bool, str]:
        """Adjust reactor power distribution across ship subsystems."""
        with self.lock:
            try:
                new_power = ShipPower(engines=engines, shields=shields, sensors=sensors, weapons=weapons)
            except ValueError as e:
                return False, f"Power routing rejected: {str(e)}"

            log_entry = f"Reactor power redistributed: ENG {engines}%, SHD {shields}%, SEN {sensors}%, WEP {weapons}%."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            new_tut, tut_cr, tut_xp, tut_relics, tut_logs = self._progress_tutorial("power")
            new_log.extend(tut_logs)
            new_mastery, xp_logs = self._award_pilot_xp(tut_xp, self.state.ship.mastery) if tut_xp > 0 else (self.state.ship.mastery, [])
            new_log.extend(xp_logs)

            new_ship = self._clone_ship(
                power=new_power,
                credits=self.state.ship.credits + tut_cr,
                mastery=new_mastery,
                relics=tuple(list(self.state.ship.relics) + tut_relics),
                tutorial=new_tut,
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(ship=new_ship)

            return True, "Reactor power routed successfully."

    def set_reactor_mode(self, mode: str) -> tuple[bool, str]:
        """Select the reactor operating doctrine (balanced, economy, overdrive, silent)."""
        with self.lock:
            normalized = str(mode).strip().lower()
            if normalized not in REACTOR_MODES:
                return False, f"Unknown reactor mode '{mode}'. Choose: {', '.join(REACTOR_MODES)}."
            if self.state.ship.reactor.mode == normalized:
                return False, f"Reactor already operating in {normalized} mode."
            reactor = replace(self.state.ship.reactor, mode=normalized)
            profile = get_reactor_mode(normalized)
            log_entry = f"Reactor mode set to {profile['name']}: {profile['description']}"
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            new_ship = self._clone_ship(reactor=reactor, flight_log=tuple(new_log))
            self.state = self._clone_state(ship=new_ship)
            return True, log_entry

    def vent_reactor_coolant(self) -> tuple[bool, str]:
        """Purge reactor heat immediately, with a coolant recharge cooldown."""
        with self.lock:
            current_tick = self.state.time.tick
            ok, reactor, msg = vent_reactor(self.state.ship.reactor, current_tick)
            if not ok:
                return False, msg
            new_log = list(self.state.ship.flight_log[-19:]) + [msg]
            new_ship = self._clone_ship(reactor=reactor, flight_log=tuple(new_log))
            self.state = self._clone_state(ship=new_ship)
            return True, msg

    def repair_reactor(self) -> tuple[bool, str]:
        """Repair reactor core integrity at an orbital drydock."""
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            reactor = self.state.ship.reactor
            missing = max(0.0, reactor.max_integrity - reactor.integrity)
            if missing <= 0.5 and reactor.heat <= 5.0:
                return False, "Reactor core is already at full integrity and nominal temperature."
            cost = max(120, int(missing * 4.0))
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: reactor servicing requires {cost} cr, you have {self.state.ship.credits} cr."
            updated = replace(
                reactor,
                integrity=reactor.max_integrity,
                heat=min(reactor.heat, max(5.0, reactor.heat - 20.0)),
            )
            log_entry = f"Reactor service completed: integrity restored to {updated.integrity:.0f} for {cost} cr."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            new_ship = self._clone_ship(
                reactor=updated,
                credits=self.state.ship.credits - cost,
                flight_log=tuple(new_log),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, log_entry

    def get_reactor_report(self) -> dict[str, Any]:
        """Detailed reactor telemetry derived from current ship and sector conditions."""
        with self.lock:
            ship = self.state.ship
            equipment = self._combined_equipment(ship)
            map_effects = self._map_effects()
            reactor = ship.reactor
            mode = get_reactor_mode(reactor.mode)
            return {
                "heat": round(reactor.heat, 1),
                "max_heat": round(reactor_heat_capacity(reactor, equipment), 1),
                "heat_pct": round(min(100.0, reactor.heat / max(1.0, reactor_heat_capacity(reactor, equipment)) * 100.0), 1),
                "integrity": round(reactor.integrity, 1),
                "max_integrity": round(reactor.max_integrity, 1),
                "mode": reactor.mode,
                "mode_name": mode["name"],
                "modes": {mid: dict(profile) for mid, profile in REACTOR_MODES.items()},
                "cooling": round(reactor_cooling_rate(reactor, equipment, float(map_effects["cooling_bonus"])), 2),
                "efficiency": round(reactor_output_efficiency(reactor, float(equipment.get("reactor_output", 0.0))), 3),
                "heat_generation": round(
                    (sum(ship.power.to_dict().values()) / 100.0) * 5.5
                    * float(mode["heat_mult"])
                    * max(0.05, 1.0 + float(equipment.get("heat_generation", 0.0)))
                    * max(0.2, float(map_effects["heat_mult"])),
                    2,
                ),
                "map_heat_mult": float(map_effects["heat_mult"]),
                "map_cooling_bonus": float(map_effects["cooling_bonus"]),
                "last_vent_tick": reactor.last_vent_tick,
                "can_vent": reactor.heat > 5.0 and (
                    reactor.last_vent_tick < 0 or self.state.time.tick - reactor.last_vent_tick >= 5
                ),
            }

    def install_ship_mod(self, mod_id: str) -> tuple[bool, str]:
        """Install a structural ship modification at an orbital drydock."""
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            mod = get_ship_mod(mod_id)
            if not mod:
                return False, f"Unknown ship modification '{mod_id}'."
            installed = dict(self.state.ship.ship_mods)
            if installed.get(mod.slot) == mod.id:
                return False, f"{mod.name} is already installed in the {slot_label(mod.slot)} slot."
            if mod.slot in installed:
                existing = get_ship_mod(installed[mod.slot])
                existing_name = existing.name if existing else installed[mod.slot]
                return False, f"{slot_label(mod.slot)} already contains {existing_name}. Remove it before installing {mod.name}."
            if self.state.ship.credits < mod.cost:
                return False, f"Insufficient credits: {mod.name} costs {mod.cost} cr, you have {self.state.ship.credits} cr."

            installed[mod.slot] = mod.id
            new_credits = self.state.ship.credits - mod.cost
            total_hull, total_shield, total_capacity, total_fuel = self._recompute_caps(self.state.ship, ship_mods=installed)
            current_cargo_vol = calculate_cargo_volume(self.state.ship.cargo)
            if current_cargo_vol > total_capacity:
                return False, f"Cargo hold overflow: current inventory ({current_cargo_vol} units) exceeds capacity ({total_capacity} units) with {mod.name}. Sell or store cargo first."
            log_entry = f"Structural refit: installed {mod.name} ({slot_label(mod.slot)}) for {mod.cost} cr."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            new_ship = self._clone_ship(
                hull=min(self.state.ship.hull, total_hull),
                max_hull=total_hull,
                shield=min(self.state.ship.shield, total_shield),
                max_shield=total_shield,
                fuel=min(self.state.ship.fuel, total_fuel),
                max_fuel=total_fuel,
                cargo_capacity=total_capacity,
                credits=new_credits,
                ship_mods=installed,
                flight_log=tuple(new_log),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, log_entry

    def remove_ship_mod(self, slot: str, expected_mod_id: str | None = None) -> tuple[bool, str]:
        """Remove a structural modification and recover part of its cost."""
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            installed = dict(self.state.ship.ship_mods)
            mod_id = installed.get(str(slot))
            if not mod_id:
                return False, f"No structural modification installed in {slot_label(str(slot))}."
            if expected_mod_id is not None and mod_id != expected_mod_id:
                expected = get_ship_mod(expected_mod_id)
                expected_name = expected.name if expected else expected_mod_id
                return False, f"{expected_name} is not installed in {slot_label(str(slot))}."
            installed.pop(str(slot), None)
            mod = get_ship_mod(mod_id)
            refund = get_ship_mod_sell_value(mod_id)
            total_hull, total_shield, total_capacity, total_fuel = self._recompute_caps(self.state.ship, ship_mods=installed)
            mod_name = mod.name if mod else mod_id
            current_cargo_vol = calculate_cargo_volume(self.state.ship.cargo)
            if current_cargo_vol > total_capacity:
                return False, f"Cargo hold overflow: current inventory ({current_cargo_vol} units) exceeds capacity ({total_capacity} units) without {mod_name}. Sell or store cargo first."
            log_entry = f"Structural refit: removed {mod_name} for {refund} cr salvage credit."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            new_ship = self._clone_ship(
                hull=min(self.state.ship.hull, total_hull),
                max_hull=total_hull,
                shield=min(self.state.ship.shield, total_shield),
                max_shield=total_shield,
                fuel=min(self.state.ship.fuel, total_fuel),
                max_fuel=total_fuel,
                cargo_capacity=total_capacity,
                credits=self.state.ship.credits + refund,
                ship_mods=installed,
                flight_log=tuple(new_log),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, log_entry

    def get_ship_mod_report(self) -> dict[str, Any]:
        """Serializable structural modification catalog and installed layout."""
        with self.lock:
            installed = dict(self.state.ship.ship_mods)
            return {
                "slots": list(SHIP_MOD_SLOTS),
                "slot_labels": {slot: slot_label(slot) for slot in SHIP_MOD_SLOTS},
                "slot_codes": {slot: slot_code(slot) for slot in SHIP_MOD_SLOTS},
                "installed": installed,
                "installed_details": {
                    slot: get_ship_mod(mod_id).to_dict() if get_ship_mod(mod_id) else {"id": mod_id}
                    for slot, mod_id in installed.items()
                },
                "catalog": [mod.to_dict() for mod in CATALOG_SHIP_MODS],
                "available": [mod.to_dict() for mod in get_available_ship_mods(installed)],
                "bonuses": calculate_ship_mod_bonuses(installed),
            }

    def get_simulation_report(self) -> dict[str, Any]:
        """Unified simulation telemetry: reactor, environment, and structural refits."""
        with self.lock:
            ship = self.state.ship
            equipment = self._combined_equipment(ship)
            system = self.current_system
            map_effects = self._map_effects(system)
            return {
                "tick": self.state.time.tick,
                "date": self.state.time.current_date,
                "system": system.name,
                "map_modifiers": system_modifier_summary(system),
                "map_effects": map_effects,
                "reactor": {
                    "heat": round(ship.reactor.heat, 1),
                    "max_heat": round(reactor_heat_capacity(ship.reactor, equipment), 1),
                    "integrity": round(ship.reactor.integrity, 1),
                    "mode": ship.reactor.mode,
                    "efficiency": round(reactor_output_efficiency(ship.reactor, float(equipment.get("reactor_output", 0.0))), 3),
                    "cooling": round(reactor_cooling_rate(ship.reactor, equipment, float(map_effects["cooling_bonus"])), 2),
                },
                "ship_mods": dict(ship.ship_mods),
                "equipment_bonuses": equipment,
                "power_efficiency": round(reactor_output_efficiency(ship.reactor, float(equipment.get("reactor_output", 0.0))), 3),
            }

    def get_codex_report(self) -> dict[str, Any]:
        """Captain's log and discovery codex derived from the saved game state."""
        with self.lock:
            return build_codex_report(self.state)

    def claim_codex_reward(self, entry_id: str) -> tuple[bool, str]:
        """Claim one completed codex milestone and persist its reward."""
        with self.lock:
            entry = get_codex_entry(entry_id)
            if entry is None:
                return False, f"Unknown codex milestone '{entry_id}'."
            if entry_id in self.state.codex.claimed:
                return False, f"Reward for '{entry.title}' is already claimed."

            report = build_codex_report(self.state)
            record = next((item for item in report["entries"] if item["id"] == entry_id), None)
            if record is None or not record["completed"]:
                current = record["value"] if record else 0
                return False, f"Locked: {entry.title} ({current}/{entry.target})."

            new_credits = self.state.ship.credits + entry.reward_credits
            new_mastery, xp_logs = self._award_pilot_xp(entry.reward_xp, self.state.ship.mastery)
            claim_log = (
                f"CODEX UNLOCKED: {entry.title} "
                f"(+{entry.reward_credits} cr, +{entry.reward_xp} XP)."
            )
            new_log = list(self.state.ship.flight_log[-19:]) + [claim_log] + xp_logs
            codex = CodexState(
                claimed=self.state.codex.claimed + (entry_id,),
                claimed_dates={
                    **self.state.codex.claimed_dates,
                    entry_id: self.state.time.current_date,
                },
            )
            self.state = self._clone_state(
                ship=self._clone_ship(
                    credits=new_credits,
                    mastery=new_mastery,
                    flight_log=tuple(new_log[-20:]),
                ),
                codex=codex,
            )
            return True, (
                f"Codex milestone claimed: {entry.title} "
                f"(+{entry.reward_credits} cr, +{entry.reward_xp} XP)."
            )

    def train_character_skill(self, skill: str) -> tuple[bool, str]:
        with self.lock:
            ok, character, msg = train_skill(self.state.character, skill)
            if not ok:
                return False, msg
            new_ship = self._clone_ship(flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [msg]))
            self.state = self._clone_state(ship=new_ship, character=character)
            return True, msg

    def use_character_ability(self, ability_id: str, target_faction_id: str | None = None) -> tuple[bool, str]:
        with self.lock:
            ability = ABILITY_CATALOG.get(ability_id)
            if not ability:
                return False, f"Unknown ability '{ability_id}'."
            if not ability_ready(self.state.character, ability_id):
                return False, f"Ability '{ability['name']}' is on cooldown or not unlocked."
            if self.state.ship.hull <= 0:
                return False, "The ship is destroyed; no ability can be engaged."
            ship = self.state.ship
            new_hull = ship.hull
            new_shield = ship.shield
            new_credits = ship.credits
            new_combo = ship.tactical_combo
            new_research = self.state.research
            new_standings = dict(ship.faction_standings)
            msg = ""

            if ability_id == "overclock":
                reactor = replace(
                    ship.reactor,
                    heat=min(ship.reactor.max_heat, ship.reactor.heat + 12.0),
                    surge_ticks=8,
                    surge_bonus=0.25,
                )
                msg = "Reactor Overclock engaged: +25% output for 8 ticks (+12 heat)."
                new_ship = self._clone_ship(reactor=reactor)
            elif ability_id == "emergency_repair":
                if ship.hull >= ship.max_hull:
                    return False, "Emergency Repair requires hull damage to weld."
                gain = 10 + int(self.state.character.skills.get("engineering", 1)) * 3
                new_hull = min(ship.max_hull, ship.hull + gain)
                msg = f"Emergency Repair restored {new_hull - ship.hull} hull."
                new_ship = self._clone_ship(hull=new_hull)
            elif ability_id == "battle_focus":
                if not self.state.active_combat:
                    return False, "Battle Focus requires an active combat engagement."
                new_combo = ship.tactical_combo + 1
                msg = f"Battle Focus: tactical combo advanced to {new_combo}."
                new_ship = self._clone_ship(tactical_combo=new_combo)
            elif ability_id == "charm_offensive":
                if not target_faction_id:
                    return False, "Diplomatic Offensive requires a target faction id."
                if target_faction_id not in CANONICAL_FACTIONS:
                    return False, f"Unknown target faction '{target_faction_id}'."
                if target_faction_id in self.state.eliminated_factions:
                    return False, f"{target_faction_id} has no government left to negotiate with."
                gain = 3 + int(self.state.character.skills.get("diplomacy", 1))
                new_standings[target_faction_id] = max(-100, min(100, new_standings.get(target_faction_id, 0) + gain))
                msg = f"Diplomatic Offensive improved {target_faction_id} standing by {gain}."
                new_ship = self._clone_ship(faction_standings=new_standings)
            elif ability_id == "science_burst":
                gain = 6 + int(self.state.character.skills.get("science", 1)) * 2
                new_research = replace(self.state.research, points=self.state.research.points + gain)
                msg = f"Science Burst generated {gain} research points."
                new_ship = self._clone_ship()
            elif ability_id == "trade_instinct":
                gain = 20 + int(self.state.character.skills.get("trade", 1)) * 6
                new_credits = ship.credits + gain
                msg = f"Trade Instinct yielded {gain} cr."
                new_ship = self._clone_ship(credits=new_credits)
            else:
                return False, f"Ability '{ability_id}' has no implemented effect."

            self.state = self._clone_state(
                ship=new_ship,
                character=start_ability_cooldown(self.state.character, ability_id),
                research=new_research,
            )
            return True, msg

    def choose_research(self, project_id: str) -> tuple[bool, str]:
        with self.lock:
            project = get_research_project(project_id)
            if not project:
                return False, f"Unknown research project '{project_id}'."
            if project_id in self.state.research.completed:
                return False, f"{project.name} is already completed."
            if project_id == self.state.research.active_project_id:
                return False, f"{project.name} is already the active project."
            missing = [p for p in project.prerequisites if p not in self.state.research.completed]
            if missing:
                return False, f"Prerequisites incomplete: {', '.join(missing)}."
            research = replace(
                self.state.research,
                active_project_id=project_id,
                progress=0,
                queue=tuple(pid for pid in self.state.research.queue if pid != project_id),
            )
            self.state = self._clone_state(research=research)
            return True, f"Research directed toward {project.name} ({project.cost} points)."

    def queue_research(self, project_id: str) -> tuple[bool, str]:
        """Append a project to the automatic research queue."""
        with self.lock:
            project = get_research_project(project_id)
            if not project:
                return False, f"Unknown research project '{project_id}'."
            research = self.state.research
            if project_id in research.completed:
                return False, f"{project.name} is already completed."
            if project_id == research.active_project_id:
                return False, f"{project.name} is already the active project."
            if project_id in research.queue:
                return False, f"{project.name} is already queued."
            missing = [p for p in project.prerequisites if p not in research.completed]
            if missing:
                return False, f"Prerequisites incomplete: {', '.join(missing)}."
            updated = replace(research, queue=research.queue + (project_id,))
            self.state = self._clone_state(research=updated)
            return True, f"Queued {project.name} after the active project."

    def cancel_queued_research(self, project_id: str) -> tuple[bool, str]:
        """Remove a project from the research queue without touching the active project."""
        with self.lock:
            research = self.state.research
            if project_id not in research.queue:
                return False, f"{project_id} is not in the research queue."
            updated = replace(
                research, queue=tuple(pid for pid in research.queue if pid != project_id)
            )
            self.state = self._clone_state(research=updated)
            project = get_research_project(project_id)
            name = project.name if project else project_id
            return True, f"Removed {name} from the research queue."

    OUTPOST_CHARTER_MASTERY_LEVEL = 2

    def build_outpost(self, body_id: str, outpost_type_id: str) -> tuple[bool, str]:
        with self.lock:
            outpost_type = get_outpost_type(outpost_type_id)
            if not outpost_type:
                return False, f"Unknown outpost type '{outpost_type_id}'."
            body = next((b for b in self.current_system.bodies if b.id == body_id), None)
            if not body:
                return False, f"Body '{body_id}' not found in {self.current_system.name}."
            if self.state.ship.orbiting_body_id != body_id:
                return False, f"Ship must establish orbit around {body.name} before construction."
            if self.state.ship.mastery.level < self.OUTPOST_CHARTER_MASTERY_LEVEL:
                return False, (
                    f"Outpost charters require Pilot Mastery level "
                    f"{self.OUTPOST_CHARTER_MASTERY_LEVEL} (recognized commander); "
                    f"current level {self.state.ship.mastery.level}. "
                    f"Earn XP through contracts, scans and victories."
                )
            if not can_build_on(body, outpost_type):
                return False, f"{outpost_type.name} cannot be built on a {body.body_type}."
            if any(o.body_id == body_id for o in self.state.outposts):
                return False, f"An outpost already exists on {body.name}."
            if self.state.ship.credits < outpost_type.cost:
                return False, f"Insufficient credits: {outpost_type.name} costs {outpost_type.cost} cr."
            outpost = build_outpost(
                outpost_type,
                self.current_system.id,
                body,
                self.state.time.tick,
                len(self.state.outposts),
            )
            updated_contracts, contract_logs = self._progress_contracts("colonial", 1)
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - outpost_type.cost,
                active_contracts=updated_contracts,
            )
            self.state = self._clone_state(ship=new_ship, outposts=self.state.outposts + (outpost,))
            msg = f"Founded {outpost.name} for {outpost_type.cost} cr."
            if contract_logs:
                msg += " " + " ".join(contract_logs)
            return True, msg

    def upgrade_outpost(self, outpost_id: str) -> tuple[bool, str]:
        with self.lock:
            outpost = next((o for o in self.state.outposts if o.id == outpost_id), None)
            if not outpost:
                return False, f"Unknown outpost '{outpost_id}'."
            ok, upgraded, cost, msg = upgrade_outpost(outpost)
            if not ok:
                return False, msg
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: upgrade costs {cost} cr."
            outposts = tuple(upgraded if o.id == outpost_id else o for o in self.state.outposts)
            new_ship = self._clone_ship(credits=self.state.ship.credits - cost)
            self.state = self._clone_state(ship=new_ship, outposts=outposts)
            return True, msg

    def install_outpost_module(self, outpost_id: str, module_id: str) -> tuple[bool, str]:
        """Install a production module on an outpost; stacks are capped at three."""
        with self.lock:
            outpost = next((o for o in self.state.outposts if o.id == outpost_id), None)
            if outpost is None:
                return False, f"Unknown outpost '{outpost_id}'."
            module = OUTPOST_MODULE_CATALOG.get(module_id)
            if module is None:
                return False, f"Unknown outpost module '{module_id}'."
            count = int(outpost.modules.get(module_id, 0))
            if count >= 3:
                return False, f"{module['name']} has reached the maximum of three stacks."
            cost = int(module["cost"]) * (count + 1)
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: {module['name']} costs {cost} cr."
            modules = dict(outpost.modules)
            modules[module_id] = count + 1
            updated = replace(outpost, modules=modules)
            outposts = tuple(updated if o.id == outpost_id else o for o in self.state.outposts)
            new_ship = self._clone_ship(credits=self.state.ship.credits - cost)
            self.state = self._clone_state(ship=new_ship, outposts=outposts)
            return (
                True,
                f"Installed {module['name']} on {outpost.name} for {cost} cr "
                f"(stack {modules[module_id]}/3).",
            )

    def specialize_outpost(self, outpost_id: str, specialization: str) -> tuple[bool, str]:
        """Choose or switch an outpost's level-3 production focus."""
        with self.lock:
            outpost = next((o for o in self.state.outposts if o.id == outpost_id), None)
            if outpost is None:
                return False, f"Unknown outpost '{outpost_id}'."
            if outpost.level < 3:
                return False, "Outpost specialization unlocks at level 3."
            spec_id = str(specialization).strip().lower()
            spec = OUTPOST_SPECIALIZATIONS.get(spec_id)
            if spec is None:
                return (
                    False,
                    "Unknown specialization; use industry, research, commerce or logistics.",
                )
            if outpost.specialization == spec_id:
                return False, f"{outpost.name} is already specialized in {spec['label']}."
            cost = int(spec["cost"])
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: specialization costs {cost} cr."
            updated = replace(outpost, specialization=spec_id)
            outposts = tuple(
                updated if o.id == outpost_id else o for o in self.state.outposts
            )
            line = (
                f"OUTPOST SPECIALIZATION: {outpost.name} set to {spec['label']} "
                f"for {cost} cr."
            )
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - cost,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(ship=new_ship, outposts=outposts)
            return True, line

    def _outpost_links(self, outpost_id: str) -> tuple[Outpost, ...]:
        """Outposts currently routing their surplus through one hub."""
        return tuple(
            outpost
            for outpost in self.state.outposts
            if outpost.supply_hub_id == outpost_id
        )

    def _outpost_supply_multiplier(self, outpost: Outpost) -> float:
        return outpost_supply_multiplier(outpost, self.state.outposts)

    def link_outpost_supply(
        self, outpost_id: str, hub_id: str
    ) -> tuple[bool, str]:
        """Route one outpost's surplus through a same-system hub."""
        with self.lock:
            source = next(
                (o for o in self.state.outposts if o.id == outpost_id), None
            )
            if source is None:
                return False, f"Unknown outpost '{outpost_id}'."
            hub = next((o for o in self.state.outposts if o.id == hub_id), None)
            if hub is None:
                return False, f"Unknown supply hub '{hub_id}'."
            if source.id == hub.id:
                return False, "An outpost cannot supply itself."
            if source.system_id != hub.system_id:
                return False, "Supply links must stay inside one star system."
            if source.supply_hub_id == hub.id:
                return False, f"{source.name} already supplies through {hub.name}."
            if source.supply_hub_id:
                return False, (
                    f"{source.name} already supplies through another hub; "
                    "unlink it first."
                )
            if hub.supply_hub_id:
                return False, (
                    f"{hub.name} is itself linked to a hub and cannot host links."
                )
            if self._outpost_links(source.id):
                return False, (
                    f"{source.name} hosts its own supply links and cannot "
                    "link upward."
                )
            existing = self._outpost_links(hub.id)
            if len(existing) >= OUTPOST_SUPPLY_MAX_LINKS:
                return False, (
                    f"{hub.name} already hosts {OUTPOST_SUPPLY_MAX_LINKS} links."
                )
            updated = replace(source, supply_hub_id=hub.id)
            outposts = tuple(
                updated if outpost.id == source.id else outpost
                for outpost in self.state.outposts
            )
            line = (
                f"SUPPLY LINK: {source.name} now routes through {hub.name} "
                f"(+{int(OUTPOST_SUPPLY_LINK_BONUS * 100)}% output)."
            )
            new_ship = self._clone_ship(
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(ship=new_ship, outposts=outposts)
            return True, line

    def unlink_outpost_supply(self, outpost_id: str) -> tuple[bool, str]:
        """Sever one outpost's supply link."""
        with self.lock:
            outpost = next(
                (o for o in self.state.outposts if o.id == outpost_id), None
            )
            if outpost is None:
                return False, f"Unknown outpost '{outpost_id}'."
            if not outpost.supply_hub_id:
                return False, f"{outpost.name} has no supply link to sever."
            updated = replace(outpost, supply_hub_id="")
            outposts = tuple(
                updated if candidate.id == outpost.id else candidate
                for candidate in self.state.outposts
            )
            line = f"SUPPLY LINK SEVERED: {outpost.name} is back on local reserves."
            new_ship = self._clone_ship(
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(ship=new_ship, outposts=outposts)
            return True, line

    def _megastructure_bonuses(self) -> dict[str, float]:
        bodies = (
            body
            for system in self.state.systems.values()
            for body in system.bodies
        )
        return restoration_bonuses(bodies)

    def _outpost_production(
        self, outpost: Outpost, yield_mult: float, supply_mult: float
    ) -> dict[str, float]:
        production = outpost_tick_production(
            outpost,
            yield_mult,
            self._outpost_crew_multiplier(outpost),
            supply_mult,
        )
        return apply_output_bonus(production, self._megastructure_bonuses())

    def get_megastructure_report(self) -> dict[str, Any]:
        body = self.orbiting_body
        if body is None:
            return {"restorable": False, "body_id": "", "body_name": ""}
        entry = get_restoration(body.body_type)
        if entry is None:
            return {"restorable": False, "body_id": body.id, "body_name": body.name}
        return {
            "restorable": True,
            "body_id": body.id,
            "body_name": body.name,
            "body_type": body.body_type,
            "complete": body.restoration_complete,
            "cost": int(entry["cost"]),
            "label": str(entry["label"]),
            "orbiting": self.state.ship.orbiting_body_id == body.id,
            "can_restore": (
                not body.restoration_complete
                and self.state.ship.orbiting_body_id == body.id
                and self.state.ship.credits >= int(entry["cost"])
            ),
        }

    def restore_megastructure(self, body_id: str) -> tuple[bool, str]:
        """Restore one ancient structure while orbiting it."""
        with self.lock:
            system = self.current_system
            body = next((b for b in system.bodies if b.id == body_id), None)
            if body is None:
                return False, f"Unknown body '{body_id}' in this system."
            entry = get_restoration(body.body_type)
            if entry is None:
                return False, f"{body.name} is not a restorable megastructure."
            if self.state.ship.orbiting_body_id != body.id:
                return False, f"Orbit {body.name} before starting restoration."
            if body.restoration_complete:
                return False, f"{body.name} is already restored."
            cost = int(entry["cost"])
            if self.state.ship.credits < cost:
                return False, (
                    f"Insufficient credits: restoration of {body.name} costs {cost} cr."
                )
            updated_body = replace(body, restoration_complete=True)
            updated_system = replace(
                system,
                bodies=tuple(
                    updated_body if candidate.id == body.id else candidate
                    for candidate in system.bodies
                ),
            )
            systems = dict(self.state.systems)
            systems[system.id] = updated_system
            stats = dict(self.state.stats)
            stats["megastructures_restored"] = (
                int(stats.get("megastructures_restored", 0)) + 1
            )
            line = (
                f"MEGASTRUCTURE RESTORED: {body.name} comes online "
                f"({entry['label']}) for {cost} cr."
            )
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - cost,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(
                ship=new_ship, systems=systems, stats=stats
            )
            return True, line

    def _outpost_capture_damage(
        self, outpost: Outpost, old_system: Any, new_system: Any, crew_by_id: dict[str, Any]
    ) -> int:
        """Damage a player outpost when its system falls to a non-player power."""
        if (
            old_system is None
            or new_system is None
            or old_system.faction == new_system.faction
            or new_system.faction == CANONICAL_FACTIONS["sol_coalition"].name
        ):
            return 0
        return max(0, 35 - outpost_defense(outpost, crew_by_id))

    def repair_outpost(self, outpost_id: str) -> tuple[bool, str]:
        """Restore an outpost to full integrity with a remote repair contract."""
        with self.lock:
            outpost = next((o for o in self.state.outposts if o.id == outpost_id), None)
            if outpost is None:
                return False, f"Unknown outpost '{outpost_id}'."
            if outpost.integrity >= 100.0:
                return False, f"{outpost.name} is already at full integrity."
            cost = outpost_repair_cost(outpost)
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: repair costs {cost} cr."
            updated = replace(outpost, integrity=100.0)
            outposts = tuple(
                updated if o.id == outpost_id else o for o in self.state.outposts
            )
            line = f"OUTPOST REPAIR: {outpost.name} restored to 100% integrity for {cost} cr."
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - cost,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            stats = dict(self.state.stats)
            stats["outposts_repaired"] = int(stats.get("outposts_repaired", 0)) + 1
            self.state = self._clone_state(
                ship=new_ship, outposts=outposts, stats=stats
            )
            return True, line

    def _crew_ship_id(self, crew_id: str) -> str | None:
        for ship in self.state.ship.fleet_ships:
            if ship.captain_id == crew_id:
                return ship.id
        return None

    def assign_fleet_captain(self, ship_id: str, crew_id: str) -> tuple[bool, str]:
        """Assign one active specialist as an escort captain."""
        with self.lock:
            ship = next((s for s in self.state.ship.fleet_ships if s.id == ship_id), None)
            if ship is None:
                return False, f"Unknown escort '{ship_id}'."
            if ship.hull <= 0:
                return False, f"{ship.name} is destroyed; repair or dismiss it first."
            if ship.captain_id:
                return False, f"{ship.name} already has a captain; recall them first."
            member = next((m for m in self.state.ship.crew if m.id == crew_id), None)
            if member is None:
                return False, f"Unknown crew member '{crew_id}'."
            if member.status != "active" or member.injury_ticks > 0:
                return False, f"{member.name} is not fit for command."
            if self._crew_outpost_id(crew_id) is not None:
                return False, f"{member.name} is stationed at an outpost."
            if any(crew_id in mission.crew_ids for mission in self.state.ship.away_missions):
                return False, f"{member.name} is deployed on an expedition."
            if self._crew_ship_id(crew_id) is not None:
                return False, f"{member.name} already commands another escort."
            updated = replace(
                ship,
                captain_id=member.id,
                captain_role=member.role,
                captain_skill=member.skill,
            )
            fleet_ships = tuple(
                updated if candidate.id == ship.id else candidate
                for candidate in self.state.ship.fleet_ships
            )
            line = (
                f"ESCORT CAPTAIN: {member.name} (skill {member.skill}) takes command "
                f"of {ship.name}."
            )
            new_ship = self._clone_ship(
                fleet_ships=fleet_ships,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, line

    def recall_fleet_captain(self, ship_id: str) -> tuple[bool, str]:
        """Return an escort captain to the flagship roster."""
        with self.lock:
            ship = next((s for s in self.state.ship.fleet_ships if s.id == ship_id), None)
            if ship is None:
                return False, f"Unknown escort '{ship_id}'."
            if not ship.captain_id:
                return False, f"{ship.name} has no captain."
            member = next(
                (m for m in self.state.ship.crew if m.id == ship.captain_id), None
            )
            name = member.name if member else ship.captain_id
            updated = replace(ship, captain_id="", captain_role="", captain_skill=0)
            fleet_ships = tuple(
                updated if candidate.id == ship.id else candidate
                for candidate in self.state.ship.fleet_ships
            )
            line = f"ESCORT CAPTAIN: {name} recalled from {ship.name}."
            new_ship = self._clone_ship(
                fleet_ships=fleet_ships,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, line

    def _crew_outpost_id(self, crew_id: str) -> str | None:
        for outpost in self.state.outposts:
            if crew_id in outpost.assigned_crew:
                return outpost.id
        return None

    def _outpost_crew_multiplier(self, outpost: Outpost) -> float:
        crew_by_id = {member.id: member for member in self.state.ship.crew}
        return outpost_crew_multiplier(outpost, crew_by_id)

    def _outpost_payload(
        self, outpost: Outpost, yield_mult: float | None = None
    ) -> dict[str, Any]:
        crew_by_id = {member.id: member for member in self.state.ship.crew}
        crew_mult = outpost_crew_multiplier(outpost, crew_by_id)
        spec = OUTPOST_SPECIALIZATIONS.get(outpost.specialization)
        hub = next(
            (o for o in self.state.outposts if o.id == outpost.supply_hub_id),
            None,
        )
        linked = self._outpost_links(outpost.id)
        payload = {
            **outpost.to_dict(),
            "crew_multiplier": round(crew_mult, 3),
            "crew_capacity": outpost_crew_capacity(outpost),
            "defense": outpost_defense(outpost, crew_by_id),
            "repair_cost": outpost_repair_cost(outpost),
            "specialization_label": spec["label"] if spec else "",
            "specialization_cost": int(spec["cost"]) if spec else 600,
            "supply_hub_name": hub.name if hub is not None else "",
            "supply_link_count": len(linked),
            "supply_link_names": [candidate.name for candidate in linked],
            "supply_capacity": OUTPOST_SUPPLY_MAX_LINKS,
            "supply_multiplier": round(self._outpost_supply_multiplier(outpost), 3),
            "supply_link_bonus": OUTPOST_SUPPLY_LINK_BONUS,
            "supply_hub_bonus": OUTPOST_SUPPLY_HUB_BONUS,
            "crew_names": [
                crew_by_id[cid].name
                for cid in outpost.assigned_crew
                if cid in crew_by_id
            ],
        }
        if yield_mult is not None:
            payload["production_effective"] = self._outpost_production(
                outpost,
                yield_mult,
                self._outpost_supply_multiplier(outpost),
            )
        return payload

    def assign_outpost_crew(self, outpost_id: str, crew_id: str) -> tuple[bool, str]:
        """Station one active specialist at an outpost; three can work one site."""
        with self.lock:
            outpost = next((o for o in self.state.outposts if o.id == outpost_id), None)
            if outpost is None:
                return False, f"Unknown outpost '{outpost_id}'."
            member = next((m for m in self.state.ship.crew if m.id == crew_id), None)
            if member is None:
                return False, f"Unknown crew member '{crew_id}'."
            if member.status != "active" or member.injury_ticks > 0:
                return False, f"{member.name} is not fit for outpost duty."
            capacity = outpost_crew_capacity(outpost)
            if len(outpost.assigned_crew) >= capacity:
                return False, f"{outpost.name} already has {capacity} specialists."
            if self._crew_ship_id(crew_id) is not None:
                return False, f"{member.name} commands an escort; recall them first."
            current_outpost = self._crew_outpost_id(crew_id)
            if current_outpost is not None:
                return False, f"{member.name} is already stationed at {current_outpost}."
            updated = replace(
                outpost, assigned_crew=outpost.assigned_crew + (crew_id,)
            )
            outposts = tuple(
                updated if o.id == outpost_id else o for o in self.state.outposts
            )
            multiplier = self._outpost_crew_multiplier(updated)
            line = (
                f"OUTPOST CREW: {member.name} assigned to {outpost.name} "
                f"(output x{multiplier:.2f})."
            )
            new_ship = self._clone_ship(
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line])
            )
            self.state = self._clone_state(ship=new_ship, outposts=outposts)
            return True, line

    def recall_outpost_crew(self, outpost_id: str, crew_id: str) -> tuple[bool, str]:
        """Return a stationed specialist to the flagship roster."""
        with self.lock:
            outpost = next((o for o in self.state.outposts if o.id == outpost_id), None)
            if outpost is None:
                return False, f"Unknown outpost '{outpost_id}'."
            if crew_id not in outpost.assigned_crew:
                return False, f"Crew member '{crew_id}' is not stationed at {outpost.name}."
            member = next((m for m in self.state.ship.crew if m.id == crew_id), None)
            name = member.name if member else crew_id
            updated = replace(
                outpost,
                assigned_crew=tuple(cid for cid in outpost.assigned_crew if cid != crew_id),
            )
            outposts = tuple(
                updated if o.id == outpost_id else o for o in self.state.outposts
            )
            line = f"OUTPOST CREW: {name} recalled from {outpost.name}."
            new_ship = self._clone_ship(
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line])
            )
            self.state = self._clone_state(ship=new_ship, outposts=outposts)
            return True, line

    def get_character_report(self) -> dict[str, Any]:
        with self.lock:
            character = self.state.character
            return {
                "character": character.to_dict(),
                "skills": {sid: {"name": info["name"], "description": info["description"], "level": character.skills.get(sid, 1)} for sid, info in SKILL_CATALOG.items()},
                "abilities": {
                    aid: {
                        **info,
                        "unlocked": aid in character.abilities,
                        "cooldown": int(character.ability_cooldowns.get(aid, 0)),
                        "cooldown_total": int(info["cooldown"]),
                    }
                    for aid, info in ABILITY_CATALOG.items()
                },
            }

    def get_research_report(self) -> dict[str, Any]:
        with self.lock:
            research = self.state.research
            active = get_research_project(research.active_project_id) if research.active_project_id else None
            queued = []
            for project_id in research.queue:
                project = get_research_project(project_id)
                if project is not None:
                    queued.append(project.to_dict())
            active_pacts = sum(
                1
                for faction_id in self.state.ship.research_pacts
                if self.research_pact_active(faction_id)
            )
            return {
                "points": research.points,
                "progress": research.progress,
                "active_project_id": research.active_project_id,
                "active_project": active.to_dict() if active else None,
                "queue": list(research.queue),
                "queued": queued,
                "research_pacts": list(self.state.ship.research_pacts),
                "active_research_pacts": active_pacts,
                "pact_bonus": round(0.05 * active_pacts, 2),
                "completed": list(research.completed),
                "bonuses": calculate_research_bonuses(research.completed),
                "available": [p.to_dict() for p in available_projects(research.completed, research.active_project_id)],
                "catalog": [p.to_dict() for p in RESEARCH_PROJECTS],
            }

    def get_outpost_report(self) -> dict[str, Any]:
        with self.lock:
            research_bonus = self._research_bonuses()
            yield_mult = 1.0 + float(research_bonus["outpost_yield"]) + self._skill("trade")
            return {
                "outposts": [
                    self._outpost_payload(o, yield_mult)
                    for o in self.state.outposts
                ],
                "catalog": [t.to_dict() for t in OUTPOST_TYPES],
                "modules": OUTPOST_MODULE_CATALOG,
                "specializations": OUTPOST_SPECIALIZATIONS,
            }

    def _faction_at_war_with_player(self, faction_id: str) -> bool:
        """True when the faction is a belligerent in a war involving the player's polity."""
        return any(
            war.active
            and "sol_coalition" in (war.attacker_id, war.defender_id)
            and faction_id in (war.attacker_id, war.defender_id)
            for war in self.state.wars
        )

    def trade_pact_active(self, faction_id: str) -> bool:
        """A pact pays only while the signatory is not at war with the player."""
        return bool(faction_id) and faction_id in self.state.ship.trade_pacts and not (
            self._faction_at_war_with_player(faction_id)
        )

    def research_pact_active(self, faction_id: str) -> bool:
        """A research accord pays only while the signatory is at peace with the player."""
        return bool(faction_id) and faction_id in self.state.ship.research_pacts and not (
            self._faction_at_war_with_player(faction_id)
        )

    def research_pact_multiplier(self) -> float:
        """Passive research multiplier: +5% for each active research pact."""
        active = sum(
            1
            for faction_id in self.state.ship.research_pacts
            if self.research_pact_active(faction_id)
        )
        return 1.0 + 0.05 * active

    def non_aggression_active(self, faction_id: str) -> bool:
        """A non-aggression pact protects against new wars until its expiry tick."""
        return (
            self.state.ship.non_aggression_until.get(faction_id, 0)
            > self.state.time.tick
        )

    def non_aggression_remaining(self, faction_id: str) -> int:
        return max(
            0,
            self.state.ship.non_aggression_until.get(faction_id, 0)
            - self.state.time.tick,
        )

    def _active_non_aggression_pairs(
        self, tick: int | None = None
    ) -> frozenset[frozenset[str]]:
        """Pairs involving the player's polity that active pacts keep out of war."""
        now = self.state.time.tick if tick is None else int(tick)
        return frozenset(
            frozenset(("sol_coalition", faction_id))
            for faction_id, until in self.state.ship.non_aggression_until.items()
            if until > now and faction_id != "sol_coalition"
        )

    def _leader_voice_line(self, faction_id: str, occasion: str) -> str:
        """Voiced leader reply for a diplomacy exchange, empty when leaderless."""
        leader = leader_for(self.state.faction_leaders, faction_id)
        if leader is None:
            return ""
        return f' {leader.name}: "{leader_voice(leader, occasion)}"'

    @staticmethod
    def _leader_payload(leader) -> dict:
        """Snapshot payload joining leader identity with faction creed and lore."""
        payload = leader.to_dict()
        faction = CANONICAL_FACTIONS.get(leader.faction_id)
        if faction is not None:
            payload["ideology"] = faction.ideology
            payload["description"] = faction.description
            payload["headquarters_system"] = faction.headquarters_system
        return payload

    def faction_diplomacy(self, faction_id: str, action: str, amount: int = 0) -> tuple[bool, str]:
        with self.lock:
            if faction_id not in CANONICAL_FACTIONS:
                return False, f"Unknown faction '{faction_id}'."
            if faction_id in self.state.eliminated_factions:
                return False, f"{CANONICAL_FACTIONS[faction_id].name} has been eliminated."
            act = action.strip().lower()
            standings = dict(self.state.ship.faction_standings)
            current = standings.get(faction_id, 0)
            diplomacy_bonus = self._skill("diplomacy") + self._research_bonuses()["diplomacy_bonus"]
            if act in ("improve", "negotiate"):
                gain = int(3 + diplomacy_bonus * 20 + min(5, max(0, amount)))
                standings[faction_id] = min(100, current + gain)
                new_contracts, contract_logs = self._progress_contracts("diplomacy", 1)
                self.state = self._clone_state(
                    ship=self._clone_ship(faction_standings=standings, active_contracts=new_contracts),
                )
                return True, f"Diplomatic talks with {CANONICAL_FACTIONS[faction_id].name}: standing {current:+d} -> {standings[faction_id]:+d}.{self._leader_voice_line(faction_id, 'greet')}" + (" " + " ".join(contract_logs) if contract_logs else "")
            if act in ("gift", "aid"):
                cost = max(100, int(amount) if amount else 300)
                if self.state.ship.credits < cost:
                    return False, f"Insufficient credits for aid package ({cost} cr)."
                gain = 5 + int(diplomacy_bonus * 20) + cost // 200
                standings[faction_id] = min(100, current + gain)
                new_contracts, contract_logs = self._progress_contracts("diplomacy", 1)
                new_ship = self._clone_ship(
                    credits=self.state.ship.credits - cost,
                    faction_standings=standings,
                    active_contracts=new_contracts,
                )
                self.state = self._clone_state(ship=new_ship)
                return True, f"Aid package delivered to {CANONICAL_FACTIONS[faction_id].name} ({cost} cr, +{gain} standing).{self._leader_voice_line(faction_id, 'thanks')}" + (" " + " ".join(contract_logs) if contract_logs else "")
            if act in ("trade_pact", "pact"):
                faction_name = CANONICAL_FACTIONS[faction_id].name
                if faction_id in self.state.ship.trade_pacts:
                    return False, f"Already hold a trade pact with {faction_name}."
                if self._faction_at_war_with_player(faction_id):
                    return False, f"Cannot sign a trade pact with {faction_name} while at war."
                if current < 40:
                    return (
                        False,
                        f"Trade pact requires standing >= 40 (current {current:+d}).",
                    )
                pacts = tuple(sorted(set(self.state.ship.trade_pacts) | {faction_id}))
                line = f"TRADE PACT: {faction_name} opens its markets to your flag.{self._leader_voice_line(faction_id, 'pact')}"
                new_ship = self._clone_ship(
                    trade_pacts=pacts,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
                )
                self.state = self._clone_state(ship=new_ship)
                return True, line
            if act in ("research_pact", "science_pact"):
                faction_name = CANONICAL_FACTIONS[faction_id].name
                if faction_id in self.state.ship.research_pacts:
                    return False, f"Already hold a research pact with {faction_name}."
                if self._faction_at_war_with_player(faction_id):
                    return False, f"Cannot sign a research pact with {faction_name} while at war."
                if current < 60:
                    return (
                        False,
                        f"Research pact requires standing >= 60 (current {current:+d}).",
                    )
                pacts = tuple(
                    sorted(set(self.state.ship.research_pacts) | {faction_id})
                )
                line = (
                    f"RESEARCH PACT: {faction_name} shares laboratory data "
                    "(+5% passive research while at peace)."
                    f"{self._leader_voice_line(faction_id, 'pact')}"
                )
                new_ship = self._clone_ship(
                    research_pacts=pacts,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
                )
                self.state = self._clone_state(ship=new_ship)
                return True, line
            if act in ("non_aggression", "nap", "nonaggression"):
                faction_name = CANONICAL_FACTIONS[faction_id].name
                if faction_id == "sol_coalition":
                    return False, "The Sol Coalition is your own polity."
                if self.non_aggression_active(faction_id):
                    remaining = self.non_aggression_remaining(faction_id)
                    return (
                        False,
                        f"Already hold a non-aggression pact with {faction_name} "
                        f"({remaining} ticks left).",
                    )
                if self._faction_at_war_with_player(faction_id):
                    return (
                        False,
                        f"Cannot sign a non-aggression pact with {faction_name} while at war.",
                    )
                if current < 30:
                    return (
                        False,
                        f"Non-aggression pact requires standing >= 30 (current {current:+d}).",
                    )
                until = self.state.time.tick + self.NON_AGGRESSION_TICKS
                pacts = dict(self.state.ship.non_aggression_until)
                pacts[faction_id] = until
                line = (
                    f"NON-AGGRESSION PACT: {faction_name} will not open a new war "
                    f"with the Sol Coalition for {self.NON_AGGRESSION_TICKS} ticks."
                    f"{self._leader_voice_line(faction_id, 'pact')}"
                )
                new_ship = self._clone_ship(
                    non_aggression_until=pacts,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
                )
                self.state = self._clone_state(ship=new_ship)
                return True, line
            if act == "alliance":
                if faction_id in self.state.ship.allies:
                    return False, f"Already allied with {CANONICAL_FACTIONS[faction_id].name}."
                if current < 70:
                    return False, f"Alliance requires standing >= 70 (current {current:+d})."
                allies = tuple(sorted(set(self.state.ship.allies) | {faction_id}))
                line = f"ALLIANCE FORMED: {CANONICAL_FACTIONS[faction_id].name} joins your coalition.{self._leader_voice_line(faction_id, 'pact')}"
                new_ship = self._clone_ship(
                    allies=allies,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
                )
                self.state = self._clone_state(ship=new_ship)
                return True, line
            # A privateer captain has no authority to start or end a sovereign war; the
            # only lever is a petition carried to the enemy leadership by an envoy.
            if act in ("declare_war", "war"):
                return False, "A ship's captain cannot declare war in the Coalition's name."
            if act in ("peace", "ceasefire"):
                faction_name = CANONICAL_FACTIONS[faction_id].name
                war = next(
                    (
                        w for w in self.state.wars
                        if w.active and faction_id in (w.attacker_id, w.defender_id)
                        and "sol_coalition" in (w.attacker_id, w.defender_id)
                    ),
                    None,
                )
                if war is None:
                    return False, f"No active war with {faction_name} to petition."
                if self.state.ship.credits < self.CEASEFIRE_ENVOY_COST:
                    return (
                        False,
                        f"An envoy costs {self.CEASEFIRE_ENVOY_COST} cr; you hold {self.state.ship.credits} cr.",
                    )
                chance = self._ceasefire_chance(faction_id, war)
                roll = self._stable_unit(self.state.galaxy_seed, "ceasefire", war.id, self.state.time.tick)
                if roll >= chance:
                    self.state = self._clone_state(
                        ship=self._clone_ship(
                            flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [
                                f"CEASEFIRE PETITION: {faction_name} refuses your envoy."
                            ]),
                        ),
                    )
                    return (
                        False,
                        f"{faction_name} refuses the petition (chance {chance:.0%}). "
                        "Raise standing or let the front move, then petition again.",
                    )
                wars = tuple(
                    replace(w, active=False, ended_tick=self.state.time.tick) if w.id == war.id else w
                    for w in self.state.wars
                )
                standings[faction_id] = min(100, max(current, -40) + 10)
                line = (
                    f"CEASEFIRE: {faction_name} accepts your petition and stands down; "
                    f"the envoy is paid {self.CEASEFIRE_ENVOY_COST} cr."
                )
                self.state = self._clone_state(
                    ship=self._clone_ship(
                        credits=self.state.ship.credits - self.CEASEFIRE_ENVOY_COST,
                        faction_standings=standings,
                        flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
                    ),
                    wars=wars,
                )
                return True, line
            return False, f"Unknown diplomacy action '{action}'."

    def _next_escort_index(self, escort_type: str) -> int:
        """Return a commission counter that never reuses an id freed by sale or loss."""
        prefix = f"escort_{escort_type}_"
        taken = [
            int(ship.id[len(prefix):])
            for ship in self.state.ship.fleet_ships
            if ship.id.startswith(prefix) and ship.id[len(prefix):].isdigit()
        ]
        taken_max = max(taken) if taken else 0
        commissioned_max = int(
            self.state.stats.get(f"escort_commissions_{escort_type}", 0)
        )
        return max(taken_max, commissioned_max)

    def buy_escort(self, escort_type: str, system_id: str | None = None) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            template = get_escort_template(escort_type)
            if not template:
                return False, f"Unknown escort type '{escort_type}'."
            if self.state.ship.credits < template["cost"]:
                return False, f"Insufficient credits: {template['name']} costs {template['cost']} cr."
            target_system = system_id or self.state.ship.current_system_id
            if target_system not in self.state.systems:
                return False, f"Unknown system '{target_system}'."
            ship = build_fleet_ship(
                escort_type, target_system, self._next_escort_index(escort_type)
            )
            stats = dict(self.state.stats)
            try:
                issued = int(ship.id.rsplit("_", 1)[-1])
            except (ValueError, IndexError):
                issued = len(self.state.ship.fleet_ships) + 1
            key = f"escort_commissions_{escort_type}"
            stats[key] = max(int(stats.get(key, 0)), issued)
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - template["cost"],
                fleet_ships=self.state.ship.fleet_ships + (ship,),
            )
            self.state = self._clone_state(ship=new_ship, stats=stats)
            return True, f"Commissioned {ship.name} for {template['cost']} cr."

    def assign_escort(self, ship_id: str, system_id: str) -> tuple[bool, str]:
        with self.lock:
            if system_id not in self.state.systems:
                return False, f"Unknown system '{system_id}'."
            found = False
            updated = []
            for ship in self.state.ship.fleet_ships:
                if ship.id == ship_id:
                    updated.append(replace(ship, assigned_system_id=system_id))
                    found = True
                else:
                    updated.append(ship)
            if not found:
                return False, f"Unknown escort '{ship_id}'."
            self.state = self._clone_state(ship=self._clone_ship(fleet_ships=tuple(updated)))
            return True, f"Escort {ship_id} reassigned to {system_id}."

    def set_fleet_role(self, ship_id: str, role: str) -> tuple[bool, str]:
        """Change an escort's squadron role outside combat."""
        with self.lock:
            if self.state.active_combat is not None:
                return False, "Cannot change squadron roles under fire."
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            target = next((s for s in self.state.ship.fleet_ships if s.id == ship_id), None)
            if target is None:
                return False, f"Unknown escort '{ship_id}'."
            if target.hull <= 0:
                return False, f"{target.name} is destroyed; repair or dismiss it first."
            normalized = normalize_fleet_role(role)
            if str(role).strip().lower() not in FLEET_TACTICAL_ROLES:
                return (
                    False,
                    "Unknown squadron role; use screen, strike or support.",
                )
            updated = replace(target, tactical_role=normalized)
            fleet_ships = tuple(
                updated if ship.id == target.id else ship
                for ship in self.state.ship.fleet_ships
            )
            label = FLEET_TACTICAL_ROLES[normalized]["label"]
            line = f"SQUADRON ROLE: {target.name} set to {label}."
            new_ship = self._clone_ship(
                fleet_ships=fleet_ships,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, line

    def repair_escorts(self, amount: int = 60) -> tuple[bool, str]:
        with self.lock:
            if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                return False, "Repair amount must be a positive integer."
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            cost = max(50, int(amount) * 2)
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits for escort repairs ({cost} cr)."
            repaired, spent = repair_fleet_ships(self.state.ship.fleet_ships, amount)
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - cost,
                fleet_ships=repaired,
            )
            self.state = self._clone_state(ship=new_ship)
            return True, f"Escort repair crews restored {spent} integrity for {cost} cr."

    def train_fleet_ship(self, ship_id: str) -> tuple[bool, str]:
        """Buy a block of drydock instruction for one escort, capped at Ace."""
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            target = next((s for s in self.state.ship.fleet_ships if s.id == ship_id), None)
            if target is None:
                return False, f"Unknown escort '{ship_id}'."
            if target.hull <= 0:
                return False, f"{target.name} is destroyed; repair or dismiss it first."
            if target.experience >= FLEET_MAX_EXPERIENCE:
                return False, f"{target.name} is already an Ace ({FLEET_MAX_EXPERIENCE} XP)."
            gain = min(FLEET_TRAINING_XP, FLEET_MAX_EXPERIENCE - target.experience)
            cost = fleet_training_cost(target.experience)
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits for fleet training ({cost} cr)."
            before = fleet_rank(target.experience)["name"]
            after_rank = fleet_rank(target.experience + gain)
            trained = replace(
                target,
                experience=target.experience + gain,
                training_sessions=target.training_sessions + 1,
            )
            fleet_ships = tuple(
                trained if ship.id == target.id else ship
                for ship in self.state.ship.fleet_ships
            )
            promotion = (
                f" Promoted {before} -> {after_rank['name']}."
                if after_rank["name"] != before
                else f" Progress {after_rank['progress']:.0%} to {after_rank['next_rank']}."
            )
            line = (
                f"FLEET TRAINING: {target.name} +{gain} XP for {cost} cr."
                f"{promotion}"
            )
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - cost,
                fleet_ships=fleet_ships,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, line

    def _fleet_ship_payload(self, ship: FleetShip) -> dict[str, Any]:
        """One escort row with the rank fields the cockpit and CLI both consume."""
        rank = fleet_rank(ship.experience)
        role = normalize_fleet_role(ship.tactical_role)
        role_info = FLEET_TACTICAL_ROLES[role]
        captain = next(
            (member for member in self.state.ship.crew if member.id == ship.captain_id),
            None,
        )
        return {
            **ship.to_dict(),
            "sale_value": escort_sale_value(ship),
            "captain_name": captain.name if captain else "",
            "captain_role_label": ship.captain_role.replace("_", " ").title(),
            "captain_skill": (
                captain.skill if captain is not None else ship.captain_skill
            ),
            "tactical_role": role,
            "role_label": role_info["label"],
            "role_damage": role_info["damage"],
            "role_evasion": role_info["evasion"],
            "role_repair": role_info["repair"],
            "rank": rank["name"],
            "rank_index": rank["index"],
            "rank_progress": rank["progress"],
            "next_rank": rank["next_rank"],
            "next_threshold": rank["next_threshold"],
            "experience_max": FLEET_MAX_EXPERIENCE,
            "training_cost": fleet_training_cost(ship.experience),
            "training_gain": max(
                0, min(FLEET_TRAINING_XP, FLEET_MAX_EXPERIENCE - ship.experience)
            ),
        }

    def dismiss_escort(self, ship_id: str) -> tuple[bool, str]:
        with self.lock:
            target = next((s for s in self.state.ship.fleet_ships if s.id == ship_id), None)
            if not target:
                return False, f"Unknown escort '{ship_id}'."
            remaining = tuple(s for s in self.state.ship.fleet_ships if s.id != ship_id)
            self.state = self._clone_state(ship=self._clone_ship(fleet_ships=remaining))
            return True, f"Escort {target.name} decommissioned."

    def sell_escort(self, ship_id: str) -> tuple[bool, str]:
        """Sell an escort or captured prize at a docked station."""
        with self.lock:
            body = self.docked_body
            if body is None or not body.station_dockable:
                return False, "Dock at a station or colony to sell an escort."
            target = next((s for s in self.state.ship.fleet_ships if s.id == ship_id), None)
            if target is None:
                return False, f"Unknown escort '{ship_id}'."
            value = escort_sale_value(target)
            remaining = tuple(s for s in self.state.ship.fleet_ships if s.id != ship_id)
            stats = dict(self.state.stats)
            stats["ships_sold"] = int(stats.get("ships_sold", 0)) + 1
            log = f"SOLD: {target.name} decommissioned for {value} cr."
            new_ship = self._clone_ship(
                fleet_ships=remaining,
                credits=self.state.ship.credits + value,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
            )
            self.state = self._clone_state(ship=new_ship, stats=stats)
            return True, log

    def get_fleet_manager_report(self) -> dict[str, Any]:
        with self.lock:
            ships = self.state.ship.fleet_ships
            local = fleet_ships_in_system(ships, self.state.ship.current_system_id)
            return {
                "ships": [self._fleet_ship_payload(ship) for ship in ships],
                "catalog": ESCORT_CATALOG,
                "total_damage": fleet_damage(ships),
                "local_damage": fleet_damage(local),
                "evasion_bonus": round(fleet_evasion_bonus(ships), 3),
                "local_evasion_bonus": round(fleet_evasion_bonus(local), 3),
                "patrol_sweep_ticks": PATROL_SWEEP_TICKS,
                "upkeep_per_month": fleet_upkeep(ships),
                "battle_stance": self.state.ship.battle_stance,
                "formations": ["balanced", "aggressive", "defensive"],
            }

    def plan_route(self, target_system_id: str) -> dict[str, Any]:
        with self.lock:
            return route_plan(self.state.systems, self.state.ship.current_system_id, target_system_id)

    def navigate_to(self, target_system_id: str) -> tuple[bool, str]:
        plan = self.plan_route(target_system_id)
        if not plan["reachable"]:
            return False, f"No hyperlane route to '{target_system_id}'."
        messages = []
        for system_id in plan["path"][1:]:
            ok, msg = self.jump(system_id)
            messages.append(msg)
            if not ok:
                return False, " ".join(messages)
            if self.state.active_combat or self.state.active_anomaly:
                messages.append("Route interrupted by a hostile or anomaly encounter.")
                break
        return True, " ".join(messages)

    def recruit_crew(self, role_id: str) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_docked()
            if not ok:
                return False, msg
            role = get_crew_role(role_id)
            if not role:
                return False, f"Unknown crew role '{role_id}'."
            if len([c for c in self.state.ship.crew if c.status == "active"]) >= 8:
                return False, "Crew berths are full (maximum 8 active crew)."
            if self.state.ship.credits < role.cost:
                return False, f"Insufficient credits: {role.name} signing bonus is {role.cost} cr."
            member = recruit_crew_member(role_id, self.state.galaxy_seed, len(self.state.ship.crew))
            if not member:
                return False, "Recruitment database unavailable."
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - role.cost,
                crew=self.state.ship.crew + (member,),
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Recruited {member.name} as {role.name}."]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, f"Recruited {member.name} ({role.name}, skill {member.skill}) for {role.cost} cr."

    def dismiss_crew(self, crew_id: str) -> tuple[bool, str]:
        with self.lock:
            member = next((c for c in self.state.ship.crew if c.id == crew_id), None)
            if not member:
                return False, f"Unknown crew member '{crew_id}'."
            outpost_id = self._crew_outpost_id(crew_id)
            if outpost_id is not None:
                return False, f"{member.name} is stationed at {outpost_id}; recall them first."
            ship_id = self._crew_ship_id(crew_id)
            if ship_id is not None:
                return False, f"{member.name} commands {ship_id}; recall them first."
            remaining = tuple(c for c in self.state.ship.crew if c.id != crew_id)
            self.state = self._clone_state(ship=self._clone_ship(crew=remaining))
            return True, f"Crew member {member.name} dismissed."

    def assign_crew_station(self, crew_id: str, station: str) -> tuple[bool, str]:
        """Assign an active crew specialist to a flagship bridge/departmental station."""
        with self.lock:
            valid_stations = {"helm", "tactical", "engineering", "science", "medical", "unassigned", ""}
            clean_station = station.lower().strip()
            if clean_station not in valid_stations:
                return False, f"Unknown station '{station}'. Valid stations: helm, tactical, engineering, science, medical, unassigned."

            member = next((c for c in self.state.ship.crew if c.id == crew_id), None)
            if not member:
                return False, f"Unknown crew member '{crew_id}'."

            if member.status != "active":
                return False, f"Crew member {member.name} is not on active duty ({member.status})."

            target_station = "" if clean_station == "unassigned" else clean_station
            updated_crew = []
            for c in self.state.ship.crew:
                if c.id == crew_id:
                    updated_crew.append(replace(c, station=target_station))
                elif target_station and getattr(c, "station", "") == target_station:
                    # Unseat previous officer from this station
                    updated_crew.append(replace(c, station=""))
                else:
                    updated_crew.append(c)

            action_desc = "relieved from station duties." if not target_station else f"assigned to the {target_station.upper()} station."
            msg = f"{member.name} ({member.role.capitalize()}, Skill {member.skill}) {action_desc}"
            new_ship = self._clone_ship(
                crew=tuple(updated_crew),
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Duty assignment: {msg}"]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, msg

    def get_crew_report(self) -> dict[str, Any]:
        with self.lock:
            crew = self.state.ship.crew
            assigned = {cid for mission in self.state.ship.away_missions for cid in mission.crew_ids}
            outpost_by_crew = {
                cid: outpost.id
                for outpost in self.state.outposts
                for cid in outpost.assigned_crew
            }
            ship_by_crew = {
                ship.captain_id: ship.id
                for ship in self.state.ship.fleet_ships
                if ship.captain_id
            }
            assigned.update(outpost_by_crew)
            assigned.update(ship_by_crew)
            return {
                "crew": [
                    {
                        **c.to_dict(),
                        "outpost_id": outpost_by_crew.get(c.id),
                        "ship_id": ship_by_crew.get(c.id),
                    }
                    for c in crew
                ],
                "roles": crew_catalog(),
                "bonuses": calculate_crew_bonuses(tuple(c for c in crew if c.id not in assigned)),
                "upkeep": crew_upkeep(crew),
                "capacity": 8,
                "active": len([c for c in crew if c.status == "active"]),
                "cash_flow": self.cash_flow(),
                "morale_warnings": [
                    f"{c.name} is near desertion" for c in crew if c.status == "active" and c.morale < 20.0
                ],
                "injuries": [
                    f"{c.name} injured ({c.injury_ticks} ticks)" for c in crew if c.injury_ticks > 0
                ],
                "away": len(self.state.ship.away_missions),
            }

    AWAY_MAX_ACTIVE = 2

    def _away_assigned_ids(self, ship: ShipState | None = None) -> set[str]:
        target = ship if ship is not None else self.state.ship
        return {cid for mission in target.away_missions for cid in mission.crew_ids}

    def _away_reward_preview(self, mission_type: Any) -> list[str]:
        rewards = [f"+{mission_type.credits} cr", f"{mission_type.research} research"]
        rewards.extend(f"{quantity} x {get_item_info(item_id).name}" for item_id, quantity in mission_type.cargo)
        if mission_type.morale:
            rewards.append(f"morale +{mission_type.morale}")
        if mission_type.standing:
            rewards.append(f"standing +{mission_type.standing}")
        return rewards

    def get_away_report(self) -> dict[str, Any]:
        """Body expeditions available from orbit, active teams, and crew readiness."""
        with self.lock:
            ship = self.state.ship
            body = self.docked_body
            assigned = self._away_assigned_ids(ship)
            tick = self.state.time.tick
            active: list[dict[str, Any]] = []
            for mission in ship.away_missions:
                mission_type = get_away_mission_type(mission.mission_type)
                team = [member for member in ship.crew if member.id in mission.crew_ids]
                total = max(1, mission.duration_ticks)
                remaining = max(0, mission.started_tick + mission.duration_ticks - tick)
                active.append({
                    **mission.to_dict(),
                    "name": mission_type.name if mission_type else mission.mission_type,
                    "icon": mission_type.icon if mission_type else "◇",
                    "team": [
                        {
                            "id": member.id,
                            "name": member.name,
                            "role": member.role,
                            "skill": member.skill,
                            "specialty": member.specialty,
                        }
                        for member in team
                    ],
                    "remaining_ticks": remaining,
                    "progress": round(100.0 * (total - remaining) / total, 1),
                    "duration_ticks": total,
                })

            crew_rows = [
                {
                    **member.to_dict(),
                    "xp_to_next": crew_xp_to_next(member),
                    "assigned_mission_id": next(
                        (mission.id for mission in ship.away_missions if member.id in mission.crew_ids),
                        None,
                    ),
                }
                for member in ship.crew
            ]

            missions: list[dict[str, Any]] = []
            if body is not None:
                for mission_type in available_missions(body):
                    team = auto_team(mission_type, ship.crew, assigned)
                    missing = max(0, mission_type.team_size - len(team))
                    risk = mission_risk(mission_type, body, team) if team else None
                    worked = site_key(mission_type.id, body.id) in ship.away_completed
                    reason = ""
                    if worked:
                        reason = "Site already worked; move to a fresh body."
                    elif len(active) >= self.AWAY_MAX_ACTIVE:
                        reason = "Both expedition slots are deployed."
                    elif missing:
                        reason = f"Need {missing} more healthy crew member(s)."
                    missions.append({
                        **mission_type.to_dict(),
                        "risk": risk,
                        "team": [
                            {
                                "id": member.id,
                                "name": member.name,
                                "role": member.role,
                                "skill": member.skill,
                                "specialty": member.specialty,
                                "fit": round(crew_fit(member, mission_type.required_skill), 1),
                            }
                            for member in team
                        ],
                        "missing_crew": missing,
                        "worked": worked,
                        "available": missing == 0 and len(active) < self.AWAY_MAX_ACTIVE and not worked,
                        "reason": reason,
                        "rewards": self._away_reward_preview(mission_type),
                    })

            body_summary = None
            if body is not None:
                body_summary = {
                    "id": body.id,
                    "name": body.name,
                    "body_type": body.body_type,
                    "hazards": list(body.hazards),
                    "population": body.population,
                    "gravity": body.gravity,
                }
            return {
                "body": body_summary,
                "available": missions,
                "active": active,
                "crew": crew_rows,
                "max_active": self.AWAY_MAX_ACTIVE,
                "assigned_crew_ids": sorted(assigned),
            }

    def launch_away_mission(
        self,
        mission_type: str,
        crew_ids: Sequence[str] | None = None,
    ) -> tuple[bool, str]:
        """Deploy an away team from orbit. Spent crew stop contributing ship bonuses."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            ship = self.state.ship
            body = self.docked_body
            if body is None:
                return False, "Establish orbit around a body before deploying an away team."
            if self.state.active_combat:
                return False, "Cannot deploy an away team while under hostile fire."
            if ship.travel is not None:
                return False, "Cannot deploy an away team during in-system transit."
            if ship.void_traversal is not None:
                return False, "Cannot deploy an away team inside the Hollow Between."
            if len(ship.away_missions) >= self.AWAY_MAX_ACTIVE:
                return False, f"Both expedition slots are deployed (maximum {self.AWAY_MAX_ACTIVE})."
            mission_type_def = get_away_mission_type(str(mission_type))
            if mission_type_def is None:
                return False, f"Unknown expedition type '{mission_type}'."
            if not mission_type_def.available_on(body):
                return False, f"{mission_type_def.name} is not available at {body.name}."
            if site_key(mission_type_def.id, body.id) in ship.away_completed:
                return False, f"{mission_type_def.name} site at {body.name} is already worked; move to a fresh body."

            assigned = self._away_assigned_ids(ship)
            assigned.update(
                cid for outpost in self.state.outposts for cid in outpost.assigned_crew
            )
            if crew_ids is not None:
                requested = list(dict.fromkeys(str(cid) for cid in crew_ids))
                by_id = {member.id: member for member in ship.crew}
                team_members = []
                for cid in requested:
                    member = by_id.get(cid)
                    if member is None:
                        return False, f"Unknown crew member '{cid}'."
                    if member.id in assigned:
                        return False, f"{member.name} is already deployed on an expedition."
                    if member.status != "active":
                        return False, f"{member.name} is not on active duty."
                    if member.injury_ticks > 0:
                        return False, f"{member.name} is injured and cannot deploy."
                    if self._crew_outpost_id(member.id) is not None:
                        return False, f"{member.name} is stationed at an outpost."
                    if self._crew_ship_id(member.id) is not None:
                        return False, f"{member.name} commands an escort."
                    team_members.append(member)
                team = tuple(team_members)
                if len(team) != mission_type_def.team_size:
                    return False, f"{mission_type_def.name} needs exactly {mission_type_def.team_size} crew member(s)."
            else:
                team = auto_team(mission_type_def, ship.crew, assigned)
                if len(team) < mission_type_def.team_size:
                    injured = len([member for member in ship.crew if member.injury_ticks > 0])
                    injury_note = f" ({injured} injured)" if injured else ""
                    return False, (
                        f"{mission_type_def.name} needs {mission_type_def.team_size} healthy crew member(s); "
                        f"only {len(team)} available{injury_note}."
                    )

            tick = self.state.time.tick
            mission_seq = len(ship.away_missions) + 1
            mission_id = f"away_{tick}_{mission_seq}"
            existing = {mission.id for mission in ship.away_missions}
            while mission_id in existing:
                mission_seq += 1
                mission_id = f"away_{tick}_{mission_seq}"
            risk = mission_risk(mission_type_def, body, team)
            mission = AwayMission(
                id=mission_id,
                mission_type=mission_type_def.id,
                system_id=ship.current_system_id,
                body_id=body.id,
                body_name=body.name,
                crew_ids=tuple(member.id for member in team),
                started_tick=tick,
                duration_ticks=mission_type_def.duration_ticks,
                risk=risk,
            )
            names = ", ".join(member.name for member in team)
            log = f"AWAY TEAM DEPLOYED: {mission_type_def.name} at {body.name} ({names}); risk {risk}%."
            self.state = self._clone_state(
                ship=self._clone_ship(
                    away_missions=ship.away_missions + (mission,),
                    flight_log=tuple(list(ship.flight_log[-19:]) + [log]),
                )
            )
            return True, (
                f"{mission_type_def.name} deployed to {body.name}: {names}. "
                f"Risk {risk}%, ETA {mission_type_def.duration_ticks} ticks."
            )

    def recall_away_mission(self, mission_id: str) -> tuple[bool, str]:
        """Abort one expedition and return its team to the ship with no reward."""
        with self.lock:
            ship = self.state.ship
            mission = next((m for m in ship.away_missions if m.id == str(mission_id)), None)
            if mission is None:
                return False, f"No active expedition '{mission_id}'."
            mission_type = get_away_mission_type(mission.mission_type)
            name = mission_type.name if mission_type else mission.mission_type
            remaining = tuple(m for m in ship.away_missions if m.id != mission.id)
            log = f"AWAY TEAM RECALLED: {name} at {mission.body_name}; no salvage recovered."
            self.state = self._clone_state(
                ship=self._clone_ship(
                    away_missions=remaining,
                    flight_log=tuple(list(ship.flight_log[-19:]) + [log]),
                )
            )
            return True, log

    def cash_flow(self) -> dict[str, Any]:
        """Monthly credit flow: crew payroll against passive income (drones, outposts)."""
        with self.lock:
            crew_cost = crew_upkeep(self.state.ship.crew)
            fleet_cost = fleet_upkeep(self.state.ship.fleet_ships)
            upkeep = crew_cost + fleet_cost
            passive = 0.0
            # Scout drones bank credits once per 4-tick harvest cycle
            for drone in self.state.ship.fleet_drones:
                if drone.drone_type != "scout":
                    continue
                faction_id = get_faction_id_from_name(
                    (self.state.systems.get(drone.assigned_system_id) or self.current_system).faction
                )
                perks = get_faction_service_perks(faction_id, self.state.ship.faction_standings.get(faction_id, 0))
                yield_bonus = 1.0 + float(perks["drone_yield_bonus"])
                passive += max(10.0, 75 * drone.efficiency * (0.5 + drone.integrity / 200.0) * yield_bonus) / 4.0
            # Outposts produce credits each tick
            research_yield_mult = 1.0 + float(self._research_bonuses()["outpost_yield"]) + self._skill("trade")
            for outpost in self.state.outposts:
                production = self._outpost_production(
                    outpost,
                    research_yield_mult,
                    self._outpost_supply_multiplier(outpost),
                )
                passive += float(production.get("credits", 0.0))
            # Passive sources pay per tick; a month is DAYS_PER_MONTH days of 0.25-day ticks.
            passive_month = passive * DAYS_PER_MONTH / 0.25
            return {
                "upkeep_per_month": upkeep,
                "crew_upkeep_per_month": crew_cost,
                "fleet_upkeep_per_month": fleet_cost,
                "passive_per_month": round(passive_month, 1),
                "net_per_month": round(passive_month - upkeep, 1),
            }

    def install_weapon(self, weapon_id: str) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            weapon = get_weapon(weapon_id)
            if not weapon:
                return False, f"Unknown weapon '{weapon_id}'."
            if weapon_id in self.state.ship.weapons:
                self.state = self._clone_state(ship=self._clone_ship(primary_weapon=weapon_id))
                return True, f"{weapon.name} selected as primary weapon."
            if self.state.ship.credits < weapon.cost:
                return False, f"Insufficient credits: {weapon.name} costs {weapon.cost} cr."
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - weapon.cost,
                weapons=self.state.ship.weapons + (weapon_id,),
                primary_weapon=weapon_id,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Installed weapon: {weapon.name}."]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, f"Installed {weapon.name} for {weapon.cost} cr and selected it as primary."

    def set_primary_weapon(self, weapon_id: str) -> tuple[bool, str]:
        with self.lock:
            if weapon_id not in self.state.ship.weapons:
                return False, f"Weapon '{weapon_id}' is not installed."
            weapon = get_weapon(weapon_id)
            self.state = self._clone_state(ship=self._clone_ship(primary_weapon=weapon_id))
            return True, f"Primary weapon set to {weapon.name if weapon else weapon_id}."

    def get_weapon_report(self) -> dict[str, Any]:
        with self.lock:
            return {
                "installed": list(self.state.ship.weapons),
                "primary": self.state.ship.primary_weapon,
                "catalog": weapon_catalog(),
            }

    def resolve_message_choice(self, message_id: str, choice_id: str) -> tuple[bool, str]:
        with self.lock:
            message = next((m for m in self.state.messages if m.id == message_id), None)
            if not message:
                return False, f"Unknown message '{message_id}'."
            if message.resolved_choice:
                return False, "This message branch has already been resolved."
            choice = choice_by_id(message, choice_id)
            if not choice:
                return False, f"Unknown choice '{choice_id}' for this message."
            outcome = choice.outcome or {}
            ship = self.state.ship
            hull = ship.hull
            fuel = ship.fuel
            credits = ship.credits
            heat = ship.reactor.heat
            max_shield = ship.max_shield
            reactor_output = ship.message_bonuses.get("reactor_output", 0.0)
            cooling = ship.message_bonuses.get("reactor_cooling", 0.0)
            heat_capacity = ship.message_bonuses.get("heat_capacity", 0.0)
            fuel_eff = ship.message_bonuses.get("fuel_efficiency", 0.0)
            scan_bonus = ship.message_bonuses.get("scan_mult", 0.0)
            combat_bonus = ship.message_bonuses.get("combat_damage", 0.0)
            quantum_keys = ship.message_bonuses.get("quantum_keys", 0.0)
            weapons = ship.weapons
            primary = ship.primary_weapon
            crew = ship.crew
            cargo = dict(ship.cargo)
            standings = dict(ship.faction_standings)
            research = self.state.research

            hull = max(1, min(ship.max_hull, hull + int(outcome.get("hull", 0))))
            fuel = max(0, min(ship.max_fuel, fuel + int(outcome.get("fuel", 0))))
            credits = max(0, credits + int(outcome.get("credits", 0)))
            heat = max(0.0, min(ship.reactor.max_heat, heat + float(outcome.get("heat", 0.0))))
            max_shield = max(10, max_shield + int(outcome.get("max_shield", 0)))
            reactor_output += float(outcome.get("reactor_output", 0.0))
            cooling += float(outcome.get("cooling", 0.0))
            heat_capacity += float(outcome.get("heat_capacity", 0.0))
            fuel_eff += float(outcome.get("fuel_efficiency", 0.0))
            scan_bonus += float(outcome.get("scan_mult", 0.0))
            combat_bonus += float(outcome.get("combat_damage", 0.0))
            quantum_keys += float(outcome.get("quantum_key", 0.0))
            research_gain = int(outcome.get("research", 0))
            if research_gain:
                research = replace(research, points=research.points + research_gain)
            standing_faction = outcome.get("standing_faction")
            if standing_faction:
                standings[standing_faction] = max(-100, min(100, standings.get(standing_faction, 0) + int(outcome.get("standing_delta", 0))))
            standing_other = outcome.get("standing_other")
            if standing_other:
                standings[standing_other] = max(-100, min(100, standings.get(standing_other, 0) + int(outcome.get("standing_other_delta", 0))))
            unlock_weapon = outcome.get("unlock_weapon")
            if unlock_weapon and unlock_weapon not in weapons:
                weapons = weapons + (str(unlock_weapon),)
                primary = str(unlock_weapon)
            crew_role = outcome.get("crew_role")
            if crew_role:
                member = recruit_crew_member(str(crew_role), self.state.galaxy_seed, len(crew))
                if member:
                    crew = crew + (member,)
            cargo_item = outcome.get("cargo")
            if cargo_item:
                cargo[str(cargo_item)] = cargo.get(str(cargo_item), 0) + int(outcome.get("cargo_qty", 1))

            bonuses = dict(ship.message_bonuses)
            bonuses.update({
                "reactor_output": reactor_output,
                "reactor_cooling": cooling,
                "heat_capacity": heat_capacity,
                "fuel_efficiency": fuel_eff,
                "scan_mult": scan_bonus,
                "combat_damage": combat_bonus,
                "quantum_keys": quantum_keys,
            })
            self.state = self._clone_state(
                ship=self._clone_ship(
                    hull=hull,
                    fuel=fuel,
                    credits=credits,
                    max_shield=max_shield,
                    reactor=replace(ship.reactor, heat=heat),
                    weapons=weapons,
                    primary_weapon=primary,
                    crew=crew,
                    cargo=cargo,
                    faction_standings=standings,
                    message_bonuses=bonuses,
                    flight_log=tuple(list(ship.flight_log[-19:]) + [f"Message branch resolved: {choice.label}."]),
                ),
                research=research,
            )

            next_message = follow_up_message(message.tree_id, choice.next_node_id, self.state.time.tick, message.id) if choice.next_node_id and message.tree_id else None
            updated = tuple(
                replace(m, read=True, resolved_choice=choice_id) if m.id == message_id else m
                for m in self.state.messages
            )
            if next_message:
                updated = updated + (next_message,)
            self.state = self._clone_state(messages=updated)
            detail = f" {choice.description}" if choice.description else ""
            return True, f"Branch chosen: {choice.label}.{detail}"

    def get_message_tree_report(self) -> dict[str, Any]:
        with self.lock:
            return {
                "trees": tree_catalog(),
                "messages": [m.to_dict() for m in self.state.messages],
            }

    def _bulk_buy_cost(
        self,
        body: CelestialBody,
        comm: Commodity,
        quantity: int,
        standing: int,
        unit_price: int,
        trade_pact: bool = False,
    ) -> tuple[int, dict[str, int] | None]:
        """Price a buy order by walking the local stockpile, so bulk orders move the price they pay."""
        market = self.state.economy.markets.get(self.current_system.id)
        if market is None:
            return unit_price * quantity, None
        commodity_id = comm.id
        stocks = dict(market.stockpiles)
        remaining = quantity
        total_cost = 0
        while remaining > 0:
            slice_qty = min(remaining, max(1, stocks.get(commodity_id, 50) // 8))
            slice_quote = calculate_dynamic_market_quote(
                self.current_system, body, comm,
                GlobalEconomyState(
                    markets={self.current_system.id: SystemMarketState(
                        system_id=self.current_system.id,
                        stockpiles=stocks,
                        production_rates=market.production_rates,
                        consumption_rates=market.consumption_rates,
                    )},
                    active_events=self.state.economy.active_events,
                    last_updated_tick=self.state.economy.last_updated_tick,
                ),
                faction_standing=standing,
                trade_pact=trade_pact,
            )
            total_cost += slice_quote.buy_price * slice_qty
            stocks[commodity_id] = max(MIN_STOCK, stocks.get(commodity_id, 50) - slice_qty)
            remaining -= slice_qty
        return total_cost, stocks

    def max_trade_quantity(self, commodity_id: str, is_buy: bool) -> int:
        """Largest order that would succeed now: affordable and in-hold for buys, all held units for sells."""
        with self.lock:
            if not is_buy:
                return int(self.state.ship.cargo.get(commodity_id, 0))
            body = self.docked_body
            comm = COMMODITY_MAP.get(commodity_id)
            if not body or not body.station_dockable or not comm:
                return 0
            ship = self.state.ship
            free_volume = ship.cargo_capacity - calculate_cargo_volume(ship.cargo)
            sys_faction_id = get_faction_id_from_name(self.current_system.faction)
            standing = ship.faction_standings.get(sys_faction_id, 0)
            pact = self.trade_pact_active(sys_faction_id)
            unit_price = calculate_dynamic_market_quote(
                self.current_system,
                body,
                comm,
                self.state.economy,
                faction_standing=standing,
                trade_pact=pact,
            ).buy_price
            high = min(free_volume // max(1, comm.volume), ship.credits // max(1, unit_price))
            low = 0
            # Slice pricing only rises with quantity, so the affordable set is a prefix.
            while low < high:
                mid = (low + high + 1) // 2
                if self._bulk_buy_cost(body, comm, mid, standing, unit_price, pact)[0] <= ship.credits:
                    low = mid
                else:
                    high = mid - 1
            return max(0, low)

    def trade_max(self, commodity_id: str, is_buy: bool) -> tuple[bool, str]:
        """Buy as many units as credits and hold allow, or sell every unit held."""
        with self.lock:
            quantity = self.max_trade_quantity(commodity_id, is_buy)
            if quantity <= 0:
                if not is_buy:
                    return False, f"No {commodity_id} in the hold to sell."
                body = self.docked_body
                if not body or not body.station_dockable or commodity_id not in COMMODITY_MAP:
                    # Let the regular order explain the docking or catalogue refusal.
                    return self.trade(commodity_id, 1, is_buy)
                ship = self.state.ship
                comm = COMMODITY_MAP[commodity_id]
                if ship.cargo_capacity - calculate_cargo_volume(ship.cargo) < comm.volume:
                    return False, "Cargo hold capacity exceeded: no free volume for another unit."
                return False, f"Insufficient credits: {ship.credits} cr available is below one unit's price."
            return self.trade(commodity_id, quantity, is_buy)

    def set_trade_automation(
        self,
        commodity_id: str = "",
        buy_below: int = 0,
        sell_above: int = 0,
        quantity: int = 1,
        enabled: bool = True,
    ) -> tuple[bool, str]:
        """Configure the docked broker that buys low and sells high on a cooldown."""
        with self.lock:
            if not enabled:
                self.state = self._clone_state(
                    trade_automation=replace(self.state.trade_automation, enabled=False)
                )
                return True, "Trade automation disabled."
            body = self.docked_body
            if body is None or not body.station_dockable:
                return False, "Dock at a station or colony to configure trade automation."
            commodity_id = str(commodity_id).strip().lower()
            if commodity_id not in COMMODITY_MAP:
                return False, f"Unknown commodity '{commodity_id}'."
            quantity = max(1, min(100, int(quantity)))
            buy_below = max(0, int(buy_below))
            sell_above = max(0, int(sell_above))
            if buy_below <= 0 and sell_above <= 0:
                return False, "Set a buy threshold, a sell threshold, or both."
            if buy_below and sell_above and buy_below >= sell_above:
                return False, "Buy threshold must be below the sell threshold."
            automation = replace(
                self.state.trade_automation,
                enabled=True,
                commodity_id=commodity_id,
                buy_below=buy_below,
                sell_above=sell_above,
                quantity=quantity,
                last_trade_tick=-10**9,
            )
            self.state = self._clone_state(trade_automation=automation)
            name = COMMODITY_MAP[commodity_id].name
            return (
                True,
                f"Trade automation armed: {name} x{quantity}, buy ≤ {buy_below or '--'}, "
                f"sell ≥ {sell_above or '--'}.",
            )

    def get_trade_automation_report(self) -> dict[str, Any]:
        with self.lock:
            return {
                "automation": self.state.trade_automation.to_dict(),
                "docked": self.docked_body is not None,
                "commodities": [
                    {"id": item.id, "name": item.name}
                    for item in COMMODITY_MAP.values()
                ],
            }

    def _run_trade_automation(self) -> None:
        """Execute at most one automated trade per cooldown while docked."""
        automation = self.state.trade_automation
        if not automation.enabled or not automation.commodity_id:
            return
        tick = self.state.time.tick
        if tick - automation.last_trade_tick < self.TRADE_AUTOMATION_COOLDOWN:
            return
        body = self.docked_body
        if body is None or not body.station_dockable:
            return
        if (
            self.state.active_combat is not None
            or self.state.active_anomaly is not None
            or self.state.active_pirate is not None
            or self.state.ship.void_traversal is not None
            or self.state.ship.travel is not None
        ):
            return
        commodity = COMMODITY_MAP.get(automation.commodity_id)
        if commodity is None:
            return
        sys_faction_id = get_faction_id_from_name(self.current_system.faction)
        standing = self.state.ship.faction_standings.get(sys_faction_id, 0)
        quote = calculate_dynamic_market_quote(
            self.current_system,
            body,
            commodity,
            self.state.economy,
            faction_standing=standing,
            trade_pact=self.trade_pact_active(sys_faction_id),
        )
        ship = self.state.ship
        is_sell = (
            automation.sell_above > 0
            and ship.cargo.get(commodity.id, 0) >= automation.quantity
            and quote.sell_price >= automation.sell_above
        )
        is_buy = (
            not is_sell
            and automation.buy_below > 0
            and quote.buy_price <= automation.buy_below
            and ship.credits >= quote.buy_price * automation.quantity
        )
        if not is_sell and not is_buy:
            return
        before = ship.credits
        ok, _ = self.trade(commodity.id, automation.quantity, not is_sell)
        if not ok:
            return
        realized = max(0, self.state.ship.credits - before) if is_sell else 0
        updated = replace(
            automation,
            last_trade_tick=tick,
            trades=automation.trades + 1,
            realized_credits=automation.realized_credits + realized,
        )
        self.state = self._clone_state(trade_automation=updated)

    def set_quantum_automation(
        self, enabled: bool = True, min_net: int = 100
    ) -> tuple[bool, str]:
        """Configure automatic quantum freight while docked."""
        with self.lock:
            if enabled:
                body = self.docked_body
                if body is None or not body.station_dockable:
                    return False, "Dock at a station or colony to configure quantum auto-freight."
            automation = replace(
                self.state.quantum_automation,
                enabled=bool(enabled),
                min_net=max(0, int(min_net)),
                last_order_tick=-10**9 if enabled else self.state.quantum_automation.last_order_tick,
            )
            self.state = self._clone_state(quantum_automation=automation)
            if enabled:
                return (
                    True,
                    f"Quantum auto-freight armed for routes netting at least {automation.min_net} cr.",
                )
            return True, "Quantum auto-freight disabled."

    def get_quantum_automation_report(self) -> dict[str, Any]:
        with self.lock:
            return {
                "automation": self.state.quantum_automation.to_dict(),
                "docked": self.docked_body is not None,
            }

    def _run_quantum_automation(self) -> None:
        """Ship surplus cargo along the best qualifying route on a cooldown."""
        automation = self.state.quantum_automation
        if not automation.enabled:
            return
        tick = self.state.time.tick
        if tick - automation.last_order_tick < self.QUANTUM_AUTOMATION_COOLDOWN:
            return
        body = self.docked_body
        if body is None or not body.station_dockable:
            return
        if len(self.state.ship.trade_orders) >= self.QUANTUM_MAX_ORDERS:
            return
        report = self.get_quantum_trade_report()
        if not report.get("docked"):
            return
        route = next(
            (
                candidate
                for candidate in report.get("routes", ())
                if candidate["net"] >= automation.min_net and candidate["net"] > 0
            ),
            None,
        )
        if route is None:
            return
        ok, _ = self.place_quantum_order(
            route["commodity_id"],
            route["quantity"],
            route["destination_system_id"],
        )
        if not ok:
            return
        updated = replace(
            automation,
            last_order_tick=tick,
            orders=automation.orders + 1,
            last_net=int(route["net"]),
            last_commodity=str(route["commodity_id"]),
            last_destination=str(route["destination_system_id"]),
        )
        line = (
            f"QUANTUM AUTO-FREIGHT: {route['commodity_name']} x{route['quantity']} "
            f"to {route['destination_name']} (net +{route['net']} cr)."
        )
        self.state = self._clone_state(
            quantum_automation=updated,
            ship=self._clone_ship(
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [line])
            ),
        )

    def trade(self, commodity_id: str, quantity: int, is_buy: bool) -> tuple[bool, str]:
        """Execute buy or sell commodity order at orbiting market."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            body = self.docked_body
            if not body or not body.station_dockable:
                return False, "Docking authorization required: ship must orbit a station or habitable colony to trade."

            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                return False, "Quantity must be a positive integer."

            comm = COMMODITY_MAP.get(commodity_id)
            if not comm:
                return False, f"Commodity '{commodity_id}' not traded here."

            sys_faction_id = get_faction_id_from_name(self.current_system.faction)
            standing = self.state.ship.faction_standings.get(sys_faction_id, 0)
            pact = self.trade_pact_active(sys_faction_id)
            quote = calculate_dynamic_market_quote(
                self.current_system,
                body,
                comm,
                self.state.economy,
                faction_standing=standing,
                trade_pact=pact,
            )
            standing_factor = faction_standing_price_factor(standing)
            pact_note = " [trade pact]" if pact else ""
            vol_per_unit = comm.volume

            cargo = dict(self.state.ship.cargo)
            cargo_cost = dict(self.state.ship.cargo_cost)
            stats = dict(self.state.stats)

            passives = calculate_passive_multipliers(self.state.ship)
            equipment = self._combined_equipment()

            # Geopolitical faction & corporate commercial mechanics
            faction_perks = get_faction_service_perks(sys_faction_id, standing)
            new_faction_standings = dict(self.state.ship.faction_standings)
            new_corp_standings = dict(self.state.ship.corp_standings)

            if is_buy:
                unit_price = quote.buy_price
                total_cost, simulated_stocks = self._bulk_buy_cost(
                    body, comm, quantity, standing, unit_price, pact
                )
                if self.state.ship.credits < total_cost:
                    return False, f"Insufficient credits: {total_cost} cr required, {self.state.ship.credits} cr available."

                current_cargo_volume = calculate_cargo_volume(cargo)
                needed_space = quantity * vol_per_unit
                if current_cargo_volume + needed_space > self.state.ship.cargo_capacity:
                    return False, f"Cargo hold capacity exceeded: cannot load {needed_space} units."

                dock_tag = (self.current_system.id, body.id, commodity_id)
                bought_qty, bought_cost = self._local_dock_purchases.get(dock_tag, (0, 0))
                self._local_dock_purchases[dock_tag] = (bought_qty + quantity, bought_cost + total_cost)
                new_credits = self.state.ship.credits - total_cost
                # A hold emptied outside the market (jettison, delivery) leaves no basis to carry.
                prior_cost = cargo_cost.get(commodity_id, 0) if cargo.get(commodity_id, 0) > 0 else 0
                cargo_cost[commodity_id] = prior_cost + total_cost
                cargo[commodity_id] = cargo.get(commodity_id, 0) + quantity
                tariff_note = ""
                if standing_factor > 1.0:
                    tariff_note = f" (+{round((standing_factor - 1.0)*100)}% {self.current_system.faction} tariff)"
                elif standing_factor < 1.0:
                    tariff_note = f" (-{round((1.0 - standing_factor)*100)}% {self.current_system.faction} discount)"
                impact_note = ""
                if quantity > 0 and total_cost > unit_price * quantity:
                    impact_pct = round(((total_cost / quantity) / unit_price - 1.0) * 100.0)
                    if impact_pct >= 1:
                        impact_note = f" (avg {total_cost // quantity}/unit, market impact +{impact_pct}%)"
                msg = f"Purchased {quantity}x {quote.name} for {total_cost} cr{tariff_note}{impact_note}{pact_note}."
            else:
                owned = cargo.get(commodity_id, 0)
                if owned < quantity:
                    return False, f"Insufficient inventory: you have {owned} units, tried to sell {quantity}."

                map_trade_bonus = float(self._map_effects()["trade_margin"])
                margin_mult = passives.get("trade_margin", 1.0) * (
                    1.0
                    + equipment["trade_margin"]
                    + map_trade_bonus
                    + len(self.state.ship.allies) * 0.05
                    + self._skill("trade")
                    + float(faction_perks["trade_margin"])
                )
                margin_mult = max(0.25, margin_mult)
                corp_mult = 1.0
                corp_note = ""
                dom_corp_id = self.current_system.dominant_corp
                if dom_corp_id:
                    corp = get_corporation(dom_corp_id)
                    if corp and corp.specialty_commodity == commodity_id:
                        corp_mult = 1.0 + corp.bonus_trade_margin
                        corp_note = f" [{corp.name} specialty: +{int(corp.bonus_trade_margin*100)}%]"
                        new_corp_standings[dom_corp_id] = min(100, new_corp_standings.get(dom_corp_id, 0) + 2)

                # Lawful commerce slightly boosts local faction relations
                new_faction_standings[sys_faction_id] = min(100, new_faction_standings.get(sys_faction_id, 0) + 1)

                dock_tag = (self.current_system.id, body.id, commodity_id)
                local_bought, local_cost = self._local_dock_purchases.get(dock_tag, (0, 0))
                # Volume-aware execution: selling in slices floods the local stockpile
                # and walks the base price down, so bulk dumps earn diminishing returns.
                simulated_stocks = None
                market = self.state.economy.markets.get(self.current_system.id)
                if market is not None:
                    stocks = dict(market.stockpiles)
                    remaining = quantity
                    base_revenue = 0
                    while remaining > 0:
                        slice_qty = min(remaining, max(1, stocks.get(commodity_id, 50) // 8))
                        slice_quote = calculate_dynamic_market_quote(
                            self.current_system, body, comm,
                            GlobalEconomyState(
                                markets={self.current_system.id: SystemMarketState(
                                    system_id=self.current_system.id,
                                    stockpiles=stocks,
                                    production_rates=market.production_rates,
                                    consumption_rates=market.consumption_rates,
                                )},
                                active_events=self.state.economy.active_events,
                                last_updated_tick=self.state.economy.last_updated_tick,
                            ),
                            faction_standing=standing,
                            trade_pact=pact,
                        )
                        base_revenue += slice_quote.sell_price * slice_qty
                        stocks[commodity_id] = min(MAX_STOCK, stocks.get(commodity_id, 50) + slice_qty)
                        remaining -= slice_qty
                    simulated_stocks = stocks
                    avg_base_sell = base_revenue / quantity
                else:
                    avg_base_sell = quote.sell_price
                bonus_sell = int(avg_base_sell * margin_mult * corp_mult)
                if local_bought > 0:
                    resold_local = min(quantity, local_bought)
                    resold_import = quantity - resold_local
                    remaining_qty = local_bought - resold_local
                    if remaining_qty:
                        remaining_cost = local_cost * remaining_qty // local_bought
                        self._local_dock_purchases[dock_tag] = (remaining_qty, remaining_cost)
                    else:
                        self._local_dock_purchases.pop(dock_tag, None)
                    capped_sell = min(bonus_sell, max(1, local_cost // local_bought - 1))
                    revenue = (resold_local * capped_sell) + (resold_import * bonus_sell)
                    unit_sell_price = revenue // quantity
                else:
                    unit_sell_price = bonus_sell
                    revenue = unit_sell_price * quantity
                new_credits = self.state.ship.credits + revenue
                held_cost = cargo_cost.pop(commodity_id, 0)
                released_cost = held_cost * quantity // owned
                if owned > quantity and held_cost - released_cost > 0:
                    cargo_cost[commodity_id] = held_cost - released_cost
                cargo[commodity_id] = owned - quantity
                if cargo[commodity_id] == 0:
                    del cargo[commodity_id]
                stats["credits_earned"] += revenue
                impact_note = ""
                if quantity > 0 and avg_base_sell < quote.sell_price:
                    impact_pct = round((1.0 - (avg_base_sell / quote.sell_price)) * 100.0)
                    if impact_pct >= 1:
                        impact_note = f" (base avg {avg_base_sell:.0f}/unit, market impact -{impact_pct}%)"
                msg = f"Sold {quantity}x {quote.name} for {revenue} cr (trade margin: x{margin_mult:.2f}){corp_note}{impact_note}{pact_note}."
                if released_cost > 0:
                    msg += f" P/L {revenue - released_cost:+d} cr."

            stats["trades"] += 1
            log_entry = f"Market transaction: {msg}"
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            # Progress trade contracts and award merchant pilot XP
            updated_contracts, contract_logs = self._progress_contracts("trade", 1)
            new_log.extend(contract_logs)
            new_mastery, xp_logs = self._award_pilot_xp(25, self.state.ship.mastery)
            new_log.extend(xp_logs)

            new_tut, tut_cr, tut_xp, tut_relics, tut_logs = self._progress_tutorial("trade")
            new_log.extend(tut_logs)
            if tut_xp > 0:
                new_mastery, tut_xp_logs = self._award_pilot_xp(tut_xp, new_mastery)
                new_log.extend(tut_xp_logs)

            new_ship = self._clone_ship(
                credits=new_credits + tut_cr,
                cargo=cargo,
                cargo_cost=cargo_cost,
                mastery=new_mastery,
                relics=tuple(list(self.state.ship.relics) + tut_relics),
                active_contracts=updated_contracts,
                tutorial=new_tut,
                faction_standings=new_faction_standings,
                corp_standings=new_corp_standings,
                flight_log=tuple(new_log[-20:]),
            )

            # Update local system stockpile in economy
            econ_markets = dict(self.state.economy.markets)
            sys_id = self.current_system.id
            if sys_id in econ_markets:
                sm = econ_markets[sys_id]
                if simulated_stocks is not None:
                    new_stocks = dict(simulated_stocks)
                else:
                    new_stocks = dict(sm.stockpiles)
                    if is_buy:
                        new_stocks[commodity_id] = max(MIN_STOCK, new_stocks.get(commodity_id, 50) - quantity)
                    else:
                        new_stocks[commodity_id] = min(MAX_STOCK, new_stocks.get(commodity_id, 50) + quantity)
                econ_markets[sys_id] = SystemMarketState(
                    system_id=sys_id,
                    stockpiles=new_stocks,
                    production_rates=sm.production_rates,
                    consumption_rates=sm.consumption_rates,
                )
            new_economy = GlobalEconomyState(
                markets=econ_markets,
                active_events=self.state.economy.active_events,
                last_updated_tick=self.state.economy.last_updated_tick,
            )

            self.state = self._clone_state(
                ship=new_ship,
                stats=stats,
                economy=new_economy,
                local_dock_purchases=dict(self._local_dock_purchases),
            )
            if self.allow_decision_events:
                self.maybe_trigger_decision("trade")

            return True, msg

    QUANTUM_MAX_ORDERS = 4

    def _destination_market_body(self, system: StarSystem) -> CelestialBody | None:
        for body in system.bodies:
            if body.station_dockable and body.market_archetype not in ("none", ""):
                return body
        return next((body for body in system.bodies if body.station_dockable), None)

    def _quantum_fee(self, commodity: Any, quantity: int, jumps: int) -> int:
        return max(35, int(25 + jumps * 40 + commodity.volume * quantity * 4))

    def get_quantum_trade_report(self) -> dict[str, Any]:
        """Arbitrage routes for cargo already in the hold, with fees and transit times."""
        with self.lock:
            body = self.docked_body
            if body is None or not body.station_dockable:
                return {
                    "docked": False,
                    "message": "Dock at a station or colony to open quantum freight lanes.",
                    "routes": [],
                    "orders": [order.to_dict() for order in self.state.ship.trade_orders],
                    "max_orders": self.QUANTUM_MAX_ORDERS,
                    "automation": self.state.quantum_automation.to_dict(),
                }
            origin = self.current_system
            routes: list[dict[str, Any]] = []
            for commodity in CANONICAL_COMMODITIES:
                quantity = int(self.state.ship.cargo.get(commodity.id, 0))
                if quantity <= 0:
                    continue
                for system in self.state.systems.values():
                    if system.id == origin.id:
                        continue
                    dest_body = self._destination_market_body(system)
                    if dest_body is None:
                        continue
                    plan = route_plan(self.state.systems, origin.id, system.id)
                    if not plan["reachable"]:
                        continue
                    faction_id = get_faction_id_from_name(system.faction)
                    quote = calculate_dynamic_market_quote(
                        system,
                        dest_body,
                        commodity,
                        self.state.economy,
                        faction_standing=self.state.ship.faction_standings.get(faction_id, 0),
                        trade_pact=self.trade_pact_active(faction_id),
                    )
                    fee = self._quantum_fee(commodity, quantity, int(plan["jumps"]))
                    payout = int(quote.sell_price * quantity * 0.97)
                    routes.append({
                        "commodity_id": commodity.id,
                        "commodity_name": commodity.name,
                        "quantity": quantity,
                        "destination_system_id": system.id,
                        "destination_system_name": system.name,
                        "destination_body_id": dest_body.id,
                        "destination_name": dest_body.name,
                        "jumps": int(plan["jumps"]),
                        "duration_ticks": max(2, int(plan["jumps"]) * 3),
                        "unit_price": quote.sell_price,
                        "fee": fee,
                        "payout": payout,
                        "net": payout - fee,
                    })
            routes.sort(key=lambda route: (-route["net"], route["destination_system_name"], route["commodity_id"]))
            return {
                "docked": True,
                "body": body.name,
                "routes": routes[:6],
                "orders": [order.to_dict() for order in self.state.ship.trade_orders],
                "max_orders": self.QUANTUM_MAX_ORDERS,
                "automation": self.state.quantum_automation.to_dict(),
            }

    def place_quantum_order(
        self,
        commodity_id: str,
        quantity: int,
        destination_system_id: str,
    ) -> tuple[bool, str]:
        """Ship owned cargo through the quantum lane; cargo leaves now and pays on arrival."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            body = self.docked_body
            if body is None or not body.station_dockable:
                return False, "Quantum freight requires a docked station or colony."
            commodity = COMMODITY_MAP.get(str(commodity_id))
            if commodity is None:
                return False, f"Unknown commodity '{commodity_id}'."
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return False, "Quantity must be a positive integer."
            if quantity <= 0:
                return False, "Quantity must be a positive integer."
            held = int(self.state.ship.cargo.get(commodity.id, 0))
            if held < quantity:
                return False, f"Insufficient cargo: hold has {held} {commodity.name}, order needs {quantity}."
            if len(self.state.ship.trade_orders) >= self.QUANTUM_MAX_ORDERS:
                return False, f"All {self.QUANTUM_MAX_ORDERS} quantum freight slots are in use."
            destination = self.state.systems.get(str(destination_system_id))
            if destination is None:
                return False, f"Unknown destination system '{destination_system_id}'."
            if destination.id == self.current_system.id:
                return False, "Choose a destination outside the current system."
            dest_body = self._destination_market_body(destination)
            if dest_body is None:
                return False, f"{destination.name} has no quantum freight terminal."
            plan = route_plan(self.state.systems, self.current_system.id, destination.id)
            if not plan["reachable"]:
                return False, f"No hyperlane route to {destination.name}."
            fee = self._quantum_fee(commodity, quantity, int(plan["jumps"]))
            if self.state.ship.credits < fee:
                return False, f"Quantum freight fee is {fee} cr; treasury has {self.state.ship.credits} cr."
            faction_id = get_faction_id_from_name(destination.faction)
            quote = calculate_dynamic_market_quote(
                destination,
                dest_body,
                commodity,
                self.state.economy,
                faction_standing=self.state.ship.faction_standings.get(faction_id, 0),
                trade_pact=self.trade_pact_active(faction_id),
            )
            cargo = dict(self.state.ship.cargo)
            remaining = held - quantity
            if remaining:
                cargo[commodity.id] = remaining
            else:
                cargo.pop(commodity.id, None)
            cargo_cost = dict(self.state.ship.cargo_cost)
            paid = int(cargo_cost.get(commodity.id, 0))
            if paid and held:
                cargo_cost[commodity.id] = max(0, paid * remaining // held)
                if cargo_cost[commodity.id] <= 0:
                    cargo_cost.pop(commodity.id, None)
            tick = self.state.time.tick
            order = TradeOrder(
                id=f"freight_{tick}_{len(self.state.ship.trade_orders) + 1}",
                commodity_id=commodity.id,
                quantity=quantity,
                origin_system_id=self.current_system.id,
                destination_system_id=destination.id,
                destination_body_id=dest_body.id,
                destination_name=dest_body.name,
                fee_paid=fee,
                created_tick=tick,
                arrival_tick=tick + max(2, int(plan["jumps"]) * 3),
                unit_price_at_launch=quote.sell_price,
            )
            log = (
                f"QUANTUM FREIGHT: {quantity} {commodity.name} departed for {destination.name} "
                f"({dest_body.name}) via {plan['jumps']} jump(s); fee {fee} cr, ETA {order.arrival_tick - tick} ticks."
            )
            stats = dict(self.state.stats)
            stats["quantum_orders"] = int(stats.get("quantum_orders", 0)) + 1
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - fee,
                cargo=cargo,
                cargo_cost=cargo_cost,
                trade_orders=self.state.ship.trade_orders + (order,),
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
            )
            self.state = self._clone_state(ship=new_ship, stats=stats)
            return True, log

    def _resolve_quantum_orders(
        self,
        orders: Sequence[TradeOrder],
        tick: int,
        systems: dict[str, StarSystem],
        economy: GlobalEconomyState,
    ) -> tuple[tuple[TradeOrder, ...], int, list[str], int, GlobalEconomyState]:
        remaining: list[TradeOrder] = []
        credits = 0
        logs: list[str] = []
        delivered = 0
        markets = dict(economy.markets)
        for order in orders:
            if tick < order.arrival_tick:
                remaining.append(order)
                continue
            system = systems.get(order.destination_system_id)
            body = next(
                (candidate for candidate in (system.bodies if system else ()) if candidate.id == order.destination_body_id),
                None,
            )
            commodity = COMMODITY_MAP.get(order.commodity_id)
            if system is None or body is None or commodity is None:
                logs.append(f"QUANTUM FREIGHT LOST: {order.quantity}x {order.commodity_id} never arrived at {order.destination_name}.")
                continue
            faction_id = get_faction_id_from_name(system.faction)
            quote = calculate_dynamic_market_quote(
                system,
                body,
                commodity,
                economy,
                faction_standing=self.state.ship.faction_standings.get(faction_id, 0),
                trade_pact=self.trade_pact_active(faction_id),
            )
            revenue = int(quote.sell_price * order.quantity * 0.97)
            credits += revenue
            market = markets.get(system.id)
            if market is not None:
                stocks = dict(market.stockpiles)
                stocks[order.commodity_id] = min(MAX_STOCK, stocks.get(order.commodity_id, 0) + order.quantity)
                markets[system.id] = replace(market, stockpiles=stocks)
            delivered += 1
            logs.append(
                f"QUANTUM FREIGHT DELIVERED: {order.quantity}x {commodity.name} sold at {system.name} "
                f"for {revenue} cr (fee {order.fee_paid} cr)."
            )
        return tuple(remaining), credits, logs, delivered, replace(economy, markets=markets)

    def buy_upgrade(self, upgrade_id: str) -> tuple[bool, str]:
        """Purchase and install a hardware upgrade module at an orbital station."""
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg

            upgrade = get_upgrade(upgrade_id)
            if not upgrade:
                return False, f"Unknown hardware upgrade '{upgrade_id}'."

            if upgrade.slot in self.state.ship.equipped_upgrades:
                existing_id = self.state.ship.equipped_upgrades[upgrade.slot]
                if existing_id == upgrade_id:
                    return False, f"Module '{upgrade.name}' is already installed."
                existing = get_upgrade(existing_id)
                existing_name = existing.name if existing else existing_id
                return False, (
                    f"Slot '{upgrade.slot}' already houses {existing_name}. "
                    f"Sell the installed module before installing {upgrade.name}."
                )

            if self.state.ship.credits < upgrade.cost:
                return False, f"Insufficient credits: costs {upgrade.cost} cr, you have {self.state.ship.credits} cr."

            new_credits = self.state.ship.credits - upgrade.cost
            equipped = dict(self.state.ship.equipped_upgrades)
            equipped[upgrade.slot] = upgrade_id

            upg_list = list(self.state.ship.upgrades)
            if upgrade.name not in upg_list:
                upg_list.append(upgrade.name)

            # Recompute stats based on chassis, modules, structural mods, relics, and talents.
            total_hull, total_shield, total_capacity, _max_fuel = self._recompute_caps(self.state.ship, equipped=equipped)

            cur_hull = min(self.state.ship.hull, total_hull)
            if "max_hull" in upgrade.stat_bonus:
                cur_hull = total_hull
            cur_shield = min(self.state.ship.shield, total_shield)
            if "max_shield" in upgrade.stat_bonus:
                cur_shield = total_shield

            log_entry = f"Arsenal upgrade: Installed {upgrade.name} ({upgrade.slot.upper()}) for {upgrade.cost} cr."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            new_ship = self._clone_ship(
                hull=cur_hull,
                max_hull=total_hull,
                shield=cur_shield,
                max_shield=total_shield,
                credits=new_credits,
                cargo_capacity=total_capacity,
                upgrades=tuple(upg_list),
                equipped_upgrades=equipped,
                flight_log=tuple(new_log),
            )

            self.state = self._clone_state(ship=new_ship)
            return True, f"Successfully installed {upgrade.name} in {upgrade.slot} slot."

    def sell_upgrade(self, slot: str) -> tuple[bool, str]:
        """Uninstall and sell an equipped hardware module back to shipyard for credits."""
        with self.lock:
            body = self.docked_body
            if not body or not body.station_dockable:
                return False, "Shipyard drydock authorization required: dock at a station or colony to uninstall modules."

            equipped = dict(self.state.ship.equipped_upgrades)
            if slot not in equipped:
                return False, f"No hardware module installed in {slot} slot."

            upg_id = equipped[slot]
            upg = get_upgrade(upg_id)
            trade_in_value = get_sell_value(upg_id)

            del equipped[slot]
            new_credits = self.state.ship.credits + trade_in_value

            total_hull, total_shield, total_capacity, _max_fuel = self._recompute_caps(self.state.ship, equipped=equipped)

            upg_name = upg.name if upg else upg_id
            current_cargo_vol = calculate_cargo_volume(self.state.ship.cargo)
            if current_cargo_vol > total_capacity:
                return False, f"Cargo hold overflow: current inventory ({current_cargo_vol} units) exceeds capacity ({total_capacity} units) without {upg_name}. Sell or store cargo first."

            cur_hull = min(self.state.ship.hull, total_hull)
            cur_shield = min(self.state.ship.shield, total_shield)
            remaining_upgrades = tuple(n for n in self.state.ship.upgrades if n != upg_name)
            msg = f"Uninstalled {upg_name} from {slot} slot for {trade_in_value} cr trade-in value."
            new_log = list(self.state.ship.flight_log[-19:]) + [msg]

            new_ship = self._clone_ship(
                hull=cur_hull,
                max_hull=total_hull,
                shield=cur_shield,
                max_shield=total_shield,
                credits=new_credits,
                cargo_capacity=total_capacity,
                upgrades=remaining_upgrades,
                equipped_upgrades=equipped,
                flight_log=tuple(new_log),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, msg

    def buy_ship_chassis(self, chassis_id: str) -> tuple[bool, str]:
        """Purchase and commission a new spacecraft hull chassis at an orbital shipyard."""
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg

            chassis = get_chassis(chassis_id)
            if not chassis:
                return False, f"Unknown ship chassis '{chassis_id}'."

            if chassis.cost <= 0:
                return False, f"'{chassis.name}' is the standard-issue starter hull and is not sold at shipyards."

            if chassis.ship_class == self.state.ship.ship_class:
                return False, f"Ship is already commissioned as a {chassis.name}."

            if self.state.ship.credits < chassis.cost:
                return False, f"Insufficient credits: {chassis.name} costs {chassis.cost} cr, you have {self.state.ship.credits} cr."

            new_credits = self.state.ship.credits - chassis.cost

            probe = replace(self.state.ship, ship_class=chassis.ship_class)
            total_max_hull, total_max_shield, total_cargo_capacity, total_max_fuel = self._recompute_caps(probe)

            current_cargo_vol = calculate_cargo_volume(self.state.ship.cargo)
            if current_cargo_vol > total_cargo_capacity:
                return False, f"Cargo hold overflow: current inventory ({current_cargo_vol} units) exceeds {chassis.name} capacity ({total_cargo_capacity} units). Sell or store cargo before downsizing."

            msg = f"Commissioned {chassis.name} ({chassis.ship_class}) at shipyard for {chassis.cost} cr! Perk: {chassis.specialty_perk}"
            new_log = list(self.state.ship.flight_log[-19:]) + [msg]

            new_ship = self._clone_ship(
                ship_class=chassis.ship_class,
                hull=total_max_hull,
                max_hull=total_max_hull,
                shield=total_max_shield,
                max_shield=total_max_shield,
                fuel=total_max_fuel,
                max_fuel=total_max_fuel,
                cargo_capacity=total_cargo_capacity,
                credits=new_credits,
                flight_log=tuple(new_log),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, msg

    def use_item(self, item_id: str) -> tuple[bool, str]:
        """Consume a usable item from cargo (nanite repair paste, shield battery, fuel canister, decoy)."""
        with self.lock:
            cargo = dict(self.state.ship.cargo)
            if cargo.get(item_id, 0) <= 0:
                return False, f"Item '{item_id}' not found in cargo hold."

            item_info = get_item_info(item_id)
            if not item_info.is_usable:
                return False, f"'{item_info.name}' is a trade commodity and cannot be consumed directly."

            ship = self.state.ship
            new_hull = ship.hull
            new_shield = ship.shield
            new_fuel = ship.fuel
            combat = self.state.active_combat
            msg = ""

            if item_info.effect_type == "repair_hull":
                if ship.hull >= ship.max_hull:
                    return False, "Hull is already at maximum structural integrity."
                new_hull = min(ship.max_hull, ship.hull + item_info.effect_amount)
                msg = f"Applied {item_info.name}: restored +{new_hull - ship.hull} Hull integrity ({new_hull}/{ship.max_hull})."
            elif item_info.effect_type == "recharge_shield":
                if ship.shield >= ship.max_shield:
                    return False, "Deflector shields are already at maximum capacitance."
                new_shield = min(ship.max_shield, ship.shield + item_info.effect_amount)
                msg = f"Discharged {item_info.name}: boosted Deflector Shields by +{new_shield - ship.shield} MW ({new_shield}/{ship.max_shield})."
            elif item_info.effect_type == "refuel":
                if ship.fuel >= ship.max_fuel:
                    return False, "Hyperdrive fuel tanks are already completely full."
                new_fuel = min(ship.max_fuel, ship.fuel + item_info.effect_amount)
                msg = f"Injected {item_info.name}: loaded +{new_fuel - ship.fuel} Quantum Fuel units ({new_fuel}/{ship.max_fuel})."
            elif item_info.effect_type == "evade_combat":
                if not combat:
                    return False, "Decoy flare is only usable during active hostile combat engagements."
                combat = None
                msg = f"Deployed {item_info.name}! Scrambled hostile sensor lock and escaped combat encounter."
            else:
                return False, f"Unknown item effect '{item_info.effect_type}'."

            cargo[item_id] -= 1
            if cargo[item_id] <= 0:
                del cargo[item_id]

            new_log = list(ship.flight_log[-19:]) + [f"Item used: {msg}"]
            new_ship = self._clone_ship(
                hull=new_hull,
                shield=new_shield,
                fuel=new_fuel,
                cargo=cargo,
                flight_log=tuple(new_log),
            )
            self.state = self._clone_state(ship=new_ship, active_combat=combat)
            return True, msg

    def buy_item(self, item_id: str, quantity: int = 1) -> tuple[bool, str]:
        """Purchase consumable items from an orbital station terminal."""
        with self.lock:
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                return False, "Quantity must be a positive integer."

            body = self.docked_body
            if not body or not body.station_dockable:
                return False, "Station terminal requires docking at a station or colony."

            info = get_item_info(item_id)
            if info.category != "consumable" or not info.is_usable:
                return False, f"'{info.name}' is not sold at station terminals. Trade commodities via the local exchange instead."

            total_cost = info.base_price * quantity
            if self.state.ship.credits < total_cost:
                return False, f"Insufficient credits: {total_cost} cr required, {self.state.ship.credits} cr available."

            cargo = dict(self.state.ship.cargo)
            needed_volume = info.volume * quantity
            if calculate_cargo_volume(cargo) + needed_volume > self.state.ship.cargo_capacity:
                return False, f"Cargo hold capacity exceeded: cannot load {needed_volume} units."

            cargo[item_id] = cargo.get(item_id, 0) + quantity
            new_credits = self.state.ship.credits - total_cost
            msg = f"Purchased {quantity}x {info.name} for {total_cost} cr."
            new_log = list(self.state.ship.flight_log[-19:]) + [f"Station terminal: {msg}"]
            new_ship = self._clone_ship(credits=new_credits, cargo=cargo, flight_log=tuple(new_log))
            self.state = self._clone_state(ship=new_ship)
            return True, msg

    def jettison_cargo(self, item_id: str, quantity: int) -> tuple[bool, str]:
        """Jettison cargo into the cosmic vacuum to free hold space."""
        with self.lock:
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                return False, "Quantity must be a positive integer."
            cargo = dict(self.state.ship.cargo)
            owned = cargo.get(item_id, 0)
            if owned < quantity:
                return False, f"Cannot jettison {quantity} units: you only have {owned} in hold."

            cargo[item_id] = owned - quantity
            if cargo[item_id] <= 0:
                del cargo[item_id]

            item_info = get_item_info(item_id)
            freed_space = quantity * item_info.volume
            msg = f"Jettisoned {quantity}x {item_info.name} into space, freeing {freed_space} cargo hold units."
            new_log = list(self.state.ship.flight_log[-19:]) + [msg]
            new_ship = self._clone_ship(cargo=cargo, flight_log=tuple(new_log))
            self.state = self._clone_state(ship=new_ship)
            return True, msg

    def buy_drone(self, drone_type: str, assigned_system_id: str | None = None) -> tuple[bool, str]:
        """Purchase and commission an autonomous fleet drone."""
        with self.lock:
            body = self.docked_body
            if not body or not body.station_dockable:
                return False, "Drone commissioning hangar requires docking at a station or colony."

            template = CATALOG_DRONE_TEMPLATES.get(drone_type)
            if not template:
                return False, f"Unknown drone model '{drone_type}'. Choices: mining, scout, combat_escort."

            cost = template["cost"]
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: {template['name']} costs {cost} cr."

            target_sys = assigned_system_id or self.state.ship.current_system_id
            if target_sys not in self.state.systems:
                return False, f"Unknown star system '{target_sys}' for drone deployment."
            prefix = f"drone_{drone_type}_"
            taken = [
                int(d.id[len(prefix):])
                for d in self.state.ship.fleet_drones
                if d.id.startswith(prefix) and d.id[len(prefix):].isdigit()
            ]
            next_num = max(taken, default=0) + 1
            drone_id = f"{prefix}{next_num}"
            new_drone = FleetDrone(
                id=drone_id,
                name=f"{template['name']} #{next_num}",
                drone_type=drone_type,
                assigned_system_id=target_sys,
                status="harvesting" if drone_type == "mining" else "patrolling",
            )

            new_credits = self.state.ship.credits - cost
            drones = list(self.state.ship.fleet_drones) + [new_drone]

            log_entry = f"Fleet expansion: Commissioned {new_drone.name} deployed to {target_sys}."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            new_tut, tut_cr, tut_xp, tut_relics, tut_logs = self._progress_tutorial("drone")
            new_log.extend(tut_logs)
            new_mastery, xp_logs = self._award_pilot_xp(tut_xp, self.state.ship.mastery) if tut_xp > 0 else (self.state.ship.mastery, [])
            new_log.extend(xp_logs)

            new_ship = self._clone_ship(
                credits=new_credits + tut_cr,
                fleet_drones=tuple(drones),
                mastery=new_mastery,
                relics=tuple(list(self.state.ship.relics) + tut_relics),
                tutorial=new_tut,
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(ship=new_ship)
            return True, f"Commissioned {new_drone.name} stationed in {target_sys}."

    def deploy_drone(self, drone_id: str, target_system_id: str) -> tuple[bool, str]:
        """Redeploy an autonomous fleet asset to a different star system."""
        with self.lock:
            if target_system_id not in self.state.systems:
                return False, f"Target star system '{target_system_id}' does not exist."

            found = False
            updated_drones = []
            for d in self.state.ship.fleet_drones:
                if d.id == drone_id:
                    found = True
                    updated_drones.append(
                        replace(
                            d,
                            assigned_system_id=target_system_id,
                            status="harvesting" if d.drone_type == "mining" else "patrolling",
                        )
                    )
                else:
                    updated_drones.append(d)

            if not found:
                return False, f"Drone with ID '{drone_id}' not found in fleet."

            new_ship = self._clone_ship(
                fleet_drones=tuple(updated_drones),
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Drone {drone_id} redeployed to {target_system_id}."]),
            )

            self.state = self._clone_state(ship=new_ship)

            return True, f"Drone '{drone_id}' redeployed to {target_system_id}."

    def collect_drone_yield(self, drone_id: str | None = None) -> tuple[bool, str, dict[str, Any]]:
        """Collect accumulated cargo and research credits from fleet drones."""
        with self.lock:
            total_cargo = 0
            total_credits = 0
            updated_drones = []

            for d in self.state.ship.fleet_drones:
                if drone_id is None or d.id == drone_id:
                    total_cargo += d.cargo_accumulated
                    total_credits += d.credits_accumulated
                    updated_drones.append(
                        replace(d, cargo_accumulated=0, credits_accumulated=0)
                    )
                else:
                    updated_drones.append(d)

            if total_cargo == 0 and total_credits == 0:
                return False, "No yield accumulated by fleet drones yet.", {"credits": 0, "cargo": 0}

            passives = calculate_passive_multipliers(self.state.ship)
            total_cargo = int(total_cargo * passives.get("drone_yield", 1.0))
            total_credits = int(total_credits * passives.get("drone_yield", 1.0))

            cargo = dict(self.state.ship.cargo)
            incoming_volume = calculate_cargo_volume({"titanium": total_cargo})
            free_volume = self.state.ship.cargo_capacity - calculate_cargo_volume(cargo)
            if incoming_volume > free_volume:
                return False, (
                    f"Cargo hold has {max(0, free_volume)} volume free but the harvest needs "
                    f"{incoming_volume}. Jettison cargo or expand the hold first."
                ), {"credits": 0, "cargo": 0}
            cargo["titanium"] = cargo.get("titanium", 0) + total_cargo
            new_credits = self.state.ship.credits + total_credits

            stats = dict(self.state.stats)
            stats["credits_earned"] += total_credits

            log_entry = f"Fleet harvest collected: +{total_credits} cr and +{total_cargo} titanium units (yield multiplier x{passives.get('drone_yield', 1.0):.2f})."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            # Progress mining contracts and award fleet commander pilot XP
            updated_contracts, contract_logs = self._progress_contracts("mining", total_cargo)
            new_log.extend(contract_logs)
            new_mastery, xp_logs = self._award_pilot_xp(40, self.state.ship.mastery)
            new_log.extend(xp_logs)

            new_ship = self._clone_ship(
                credits=new_credits,
                cargo=cargo,
                fleet_drones=tuple(updated_drones),
                mastery=new_mastery,
                active_contracts=updated_contracts,
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(
                ship=new_ship,
                stats=stats,
            )

            return True, f"Transferred {total_credits} cr and {total_cargo} units from fleet.", {
                "credits": total_credits,
                "cargo": total_cargo,
            }

    def set_battle_stance(self, stance: str) -> tuple[bool, str]:
        """Set fleet battle doctrine: balanced, aggressive, or defensive."""
        with self.lock:
            normalized = str(stance).strip().lower()
            if normalized not in ("balanced", "aggressive", "defensive"):
                return False, f"Unknown stance '{stance}'. Choose: balanced, aggressive, defensive."
            self.state = self._clone_state(ship=self._clone_ship(battle_stance=normalized))
            return True, f"Fleet battle stance set to {normalized.upper()}."

    def captain_gambit(self) -> tuple[bool, str]:
        """Spend one captain's once-per-battle specialty action."""
        with self.lock:
            combat = self.state.active_combat
            if combat is None:
                return False, "No active combat intercept to command."
            if combat.captain_gambit_used:
                return False, "The captain's gambit is already spent this battle."
            ship = self.state.ship
            local = fleet_ships_in_system(
                ship.fleet_ships, ship.current_system_id
            )
            candidates = [
                escort for escort in local
                if escort.hull > 0 and escort.captain_id
            ]
            if not candidates:
                return False, "No living escort captain is in this system."
            lead = max(
                candidates,
                key=lambda escort: (escort.captain_skill, escort.experience),
            )
            captain = next(
                (member for member in ship.crew if member.id == lead.captain_id),
                None,
            )
            if captain is None:
                return False, f"{lead.name}'s captain record is missing."
            role = captain.role
            skill = max(1, captain.skill)
            new_hull = ship.hull
            new_shield = ship.shield
            new_fleet = ship.fleet_ships
            new_combat = replace(combat, captain_gambit_used=True)
            if role == "engineer":
                repair = 12 + 3 * skill
                if ship.hull >= ship.max_hull:
                    return False, "Hull is already at full integrity; hold the gambit."
                new_hull = min(ship.max_hull, ship.hull + repair)
                detail = f"patches the hull (+{new_hull - ship.hull} integrity)"
            elif role == "medic":
                heal = 6 + 2 * skill
                damaged = [escort for escort in local if escort.hull < escort.max_hull]
                if not damaged:
                    return False, "The local escort wing is undamaged; hold the gambit."
                updated = tuple(
                    replace(
                        escort,
                        hull=min(escort.max_hull, escort.hull + heal),
                        status="escorting",
                    )
                    if escort.id in {ship.id for ship in damaged}
                    else escort
                    for escort in local
                )
                new_fleet = self._merge_fleet_ships(updated)
                detail = f"stabilizes the escort wing (+{heal} hull each)"
            elif role == "quartermaster":
                boost = 10 + 2 * skill
                drained = [escort for escort in local if escort.shield < escort.max_shield]
                if not drained:
                    return False, "The local escort shields are full; hold the gambit."
                updated = tuple(
                    replace(
                        escort,
                        shield=min(escort.max_shield, escort.shield + boost),
                    )
                    if escort.id in {ship.id for ship in drained}
                    else escort
                    for escort in local
                )
                new_fleet = self._merge_fleet_ships(updated)
                detail = f"pushes reserve cells to the screen (+{boost} shield each)"
            elif role == "pilot":
                if combat.captain_evasion_bonus >= 0.35:
                    return False, "The wing is already at maximum evasive posture."
                gained = 0.08 + 0.015 * skill
                new_combat = replace(
                    new_combat,
                    captain_evasion_bonus=min(
                        0.35, combat.captain_evasion_bonus + gained
                    ),
                )
                detail = f"runs the wing through a tightening evasive pattern (+{int(gained * 100)}% evasion)"
            elif role == "scientist":
                if combat.enemy_shield <= 0:
                    return False, "Enemy shields are already down; hold the gambit."
                drained = min(combat.enemy_shield, 15 + 4 * skill)
                new_combat = replace(
                    new_combat,
                    enemy_shield=combat.enemy_shield - drained,
                )
                detail = f"maps the deflector harmonics and drains {drained} MW"
            elif role == "marine":
                if combat.enemy_damage <= 1:
                    return False, "Enemy weapons are already suppressed; hold the gambit."
                cut = min(combat.enemy_damage - 1, 8 + 2 * skill)
                new_combat = replace(
                    new_combat,
                    enemy_damage=combat.enemy_damage - cut,
                )
                detail = f"cuts enemy fire-control (-{cut} hostile damage)"
            else:
                return False, f"{captain.name} has no combat gambit."

            line = (
                f"CAPTAIN'S GAMBIT ({role.title()}): {captain.name} {detail}. "
                "Once per battle."
            )
            new_ship = self._clone_ship(
                hull=new_hull,
                shield=new_shield,
                fleet_ships=new_fleet,
                flight_log=tuple((list(ship.flight_log[-19:]) + [line])[-20:]),
            )
            self.state = self._clone_state(
                ship=new_ship, active_combat=new_combat
            )
            return True, line

    def fuse_relics(self, source_rarity: str) -> tuple[bool, str, dict[str, Any]]:
        """Fuse three relics of one rarity into a single relic of the next rarity."""
        with self.lock:
            ship = self.state.ship
            source_rarity = (source_rarity or "").strip().lower()
            ladder = {"common": "rare", "rare": "epic", "epic": "legendary"}
            if source_rarity not in ladder:
                return False, "Cannot fuse legendary relics further (or unknown rarity).", {}
            owned = [r for r in ship.relics if r.rarity == source_rarity]
            if len(owned) < 3:
                return False, f"Need 3 {source_rarity} relics to fuse (have {len(owned)}).", {}

            target_rarity = ladder[source_rarity]
            owned_ids = {r.id for r in ship.relics}
            candidates = [r for r in CATALOG_RELICS if r.rarity == target_rarity and r.id not in owned_ids]
            if candidates:
                new_relic = self.rng.choice(candidates)
            else:
                new_relic = PrecursorRelic(
                    id=f"fused_{target_rarity}_{len(ship.relics)}",
                    name=f"Fused {target_rarity.title()} Relic",
                    rarity=target_rarity,
                    description="Forged from three lesser relics at a resonance forge.",
                    passive_stat="scan_bounty",
                    stat_multiplier=0.15,
                )

            # Remove the first three source relics.
            remaining: list[Any] = []
            removed = 0
            for r in ship.relics:
                if r.rarity == source_rarity and removed < 3:
                    removed += 1
                    continue
                remaining.append(r)
            remaining.append(new_relic)

            log_entry = f"Relic fusion: 3 {source_rarity} relics forged into {new_relic.name} ({target_rarity})."
            new_ship = self._clone_ship(
                relics=tuple(remaining),
                flight_log=tuple(list(ship.flight_log[-19:]) + [log_entry]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, f"Fused 3 {source_rarity} relics into {new_relic.name} ({target_rarity}).", {"relic": new_relic.to_dict()}

    def _combat_defeat(self, combat: CombatEncounter, note: str = "",
                       fleet_ships: tuple | None = None, crew: tuple | None = None,
                       streak: int | None = None, fuel: int | None = None) -> tuple[bool, str]:
        """End a fight at 0 hull, pausing time so a destroyed ship cannot recover by ticking."""
        ship = self.state.ship
        log_line = f"DEFEAT: {combat.enemy_name} destroyed your {ship.ship_class}."
        if note:
            log_line = f"{note} {log_line}"
        new_log = tuple((list(ship.flight_log[-19:]) + [log_line])[-20:])
        self.state = self._clone_state(
            ship=self._clone_ship(
                hull=0,
                shield=0,
                tactical_combo=0,
                streak=streak if streak is not None else ship.streak,
                crew=crew if crew is not None else ship.crew,
                fleet_ships=fleet_ships if fleet_ships is not None else ship.fleet_ships,
                fuel=fuel if fuel is not None else ship.fuel,
                flight_log=new_log,
            ),
            active_combat=None,
            time=replace(self.state.time, is_paused=True),
        )
        return True, log_line

    def combat_action(self, action: str) -> tuple[bool, str]:
        """Execute a tactical combat maneuver against an active hostile intercept."""
        with self.lock:
            combat = self.state.active_combat
            if not combat:
                return False, "No hostile ship in combat proximity."
            ship = self.state.ship
            if ship.reactor.surge_ticks > 0:
                remaining = ship.reactor.surge_ticks - 1
                self.state = self._clone_state(
                    ship=self._clone_ship(reactor=replace(
                        ship.reactor,
                        surge_ticks=max(0, remaining),
                        surge_bonus=ship.reactor.surge_bonus if remaining > 0 else 0.0,
                    ))
                )

            new_hull = self.state.ship.hull
            new_shield = self.state.ship.shield
            new_credits = self.state.ship.credits
            cargo = dict(self.state.ship.cargo)
            stats = dict(self.state.stats)
            passives = calculate_passive_multipliers(self.state.ship)
            equipment = self._combined_equipment()
            mercenary_damage = sum(
                14 if d.specialty == "assault" else 8 if d.specialty == "evasion" else 4
                for d in self.state.ship.fleet_drones
                if d.drone_type == "mercenary"
            )
            mercenary_evasion = 0.10 if any(
                d.drone_type == "mercenary" and d.specialty == "evasion"
                for d in self.state.ship.fleet_drones
            ) else 0.0
            ally_damage = len(self.state.ship.allies) * 3

            new_combo = self.state.ship.tactical_combo
            new_streak = self.state.ship.streak
            enemy_rem_shield = combat.enemy_shield
            enemy_rem_hull = combat.enemy_hull
            enemy_rem_damage = combat.enemy_damage
            ability_cd = max(0, combat.ability_cooldown - 1)
            intent = combat.enemy_intent if combat.enemy_intent in {"fire", "brace", "evade", "execute", "ability"} else "fire"
            enemy_guard = 0.55 if intent == "brace" else 1.0
            damaging_actions = {"fire_lasers", "drone_strike", "target_subsystem", "target_weapons", "target_shields", "target_engines", "target_bridge", "point_defense"}
            enemy_miss = action in damaging_actions and intent == "evade" and self.rng.random() < 0.35
            weapon_miss = False
            enemy_hull_before = enemy_rem_hull
            enemy_shield_before = enemy_rem_shield
            fleet_ships = fleet_ships_in_system(
                self.state.ship.fleet_ships, self.state.ship.current_system_id
            )
            fleet_volley = 0
            boarding_crew = None
            battle_stance = self.state.ship.battle_stance

            # Combat Reactor Thermal Curve & Overheating Tracking
            heat_gain = 0.0
            if action == "fire_lasers":
                heat_gain = 6.0
            elif action in ("target_subsystem", "target_weapons", "target_shields", "target_engines"):
                heat_gain = 5.0
            elif action == "target_bridge":
                heat_gain = 10.0
            elif action == "shield_absorb":
                heat_gain = 4.0
            elif action == "point_defense":
                heat_gain = 3.0

            if heat_gain > 0.0:
                reactor_mode = self.state.ship.reactor.mode
                if reactor_mode in ("overdrive", "overclock"):
                    heat_gain *= 1.5
                elif reactor_mode in ("economy", "eco"):
                    heat_gain *= 0.7

            max_heat = reactor_heat_capacity(self.state.ship.reactor, equipment)
            combat_reactor = replace(
                self.state.ship.reactor,
                heat=min(max_heat, self.state.ship.reactor.heat + heat_gain),
            )

            if action == "fire_lasers":
                wep_power = self._effective_power("weapons")
                weapon = get_weapon(self.state.ship.primary_weapon) or get_weapon("pulse_laser")
                bonus_wep = int(equipment["combat_damage"])
                research_combat = self._research_bonuses()["combat_damage"]
                base_dmg = int((weapon.damage + int(wep_power * 0.75) + bonus_wep + mercenary_damage + ally_damage + research_combat) * (1.0 + self._skill("combat")) * passives.get("laser_dmg", 1.0) * enemy_guard)
                shield_dmg = max(1, int(base_dmg * weapon.shield_mult))
                hull_dmg = max(1, int(base_dmg * weapon.hull_mult))
                weapon_miss = self.rng.random() > weapon.accuracy
                if weapon_miss:
                    enemy_miss = True
                    new_combo = 0
                    combo_break_note = " COMBO BROKEN: the whiffed shot cost all tactical focus."
                else:
                    new_combo += 1
                    combo_break_note = ""
                crit_text = ""
                if new_combo >= 3:
                    shield_dmg = int(shield_dmg * 1.5)
                    hull_dmg = int(hull_dmg * 1.5)
                    crit_text = f" (TACTICAL OVERCHARGE x{new_combo}: +50% CRIT DAMAGE!)"

                if weapon_miss:
                    strike_desc = f"{weapon.name} firing solution failed; the shot went wide.{combo_break_note}"
                elif enemy_rem_shield > 0:
                    if shield_dmg <= enemy_rem_shield:
                        enemy_rem_shield -= shield_dmg
                        strike_desc = f"{weapon.name} absorbed by enemy deflector shields ({shield_dmg} MW damage dealt, Shield: {enemy_rem_shield}/{combat.enemy_max_shield}){crit_text}."
                    else:
                        overflow = max(1, int((shield_dmg - enemy_rem_shield) * (hull_dmg / max(1, shield_dmg))))
                        enemy_rem_shield = 0
                        enemy_rem_hull -= overflow
                        strike_desc = f"{weapon.name} shattered enemy deflector shields! {overflow} overflow damage struck hull{crit_text}."
                else:
                    enemy_rem_hull -= hull_dmg
                    strike_desc = f"{weapon.name} struck enemy hull directly for {hull_dmg} damage{crit_text}."

            elif action == "drone_strike":
                has_escort = any(d.drone_type == "combat_escort" for d in self.state.ship.fleet_drones)
                has_scout = any(d.drone_type == "scout" for d in self.state.ship.fleet_drones)
                if not has_escort and not has_scout:
                    return False, "No tactical drones deployed. Deploy a Combat Escort or Scout drone first."

                new_combo += 1
                if has_escort:
                    torpedo_dmg = max(1, int(45 * enemy_guard))
                    enemy_rem_hull -= torpedo_dmg
                    strike_desc = f"Combat Escort Frigate launched armor-piercing kinetic torpedo! Inflicted {torpedo_dmg} damage directly to hull (bypassing shields)!"
                else:
                    sensor_burn = max(1, int(35 * enemy_guard))
                    enemy_rem_shield = max(0, enemy_rem_shield - sensor_burn)
                    strike_desc = f"Scout Drone focused beam telemetry! Collapsed {sensor_burn} MW of enemy deflector shields!"

            elif action in ("target_subsystem", "target_weapons", "target_shields", "target_engines", "target_bridge"):
                subsystem = "shields" if action == "target_shields" else ("engines" if action == "target_engines" else ("bridge" if action == "target_bridge" else "weapons"))
                new_combo += 1
                if subsystem == "weapons":
                    enemy_rem_damage = max(6, int(combat.enemy_damage * 0.60))
                    strike_dmg = max(1, int(15 * enemy_guard))
                    if enemy_rem_shield > 0:
                        enemy_rem_shield = max(0, enemy_rem_shield - strike_dmg)
                    else:
                        enemy_rem_hull -= strike_dmg
                    strike_desc = f"Targeted strike hit enemy weapon arrays! Disabled fire-control (-40% enemy firepower) and dealt {strike_dmg} damage!"
                elif subsystem == "shields":
                    shield_ion = max(1, int(40 * enemy_guard))
                    enemy_rem_shield = max(0, enemy_rem_shield - shield_ion)
                    strike_desc = f"Ion pulse targeted enemy shield generators! EMP cascade drained {shield_ion} MW shields!"
                elif subsystem == "engines":
                    strike_dmg = max(1, int(18 * enemy_guard))
                    if strike_dmg <= enemy_rem_shield:
                        enemy_rem_shield -= strike_dmg
                    else:
                        overflow = strike_dmg - enemy_rem_shield
                        enemy_rem_shield = 0
                        enemy_rem_hull -= overflow
                    intent = "brace"
                    enemy_miss = False
                    strike_desc = f"Pinpoint strike on enemy drive manifolds! Disabled impulse thrusters (collapsed enemy evasion) and dealt {strike_dmg} damage!"
                elif subsystem == "bridge":
                    wep_power = self._effective_power("weapons")
                    if wep_power < 15:
                        return False, "Targeting enemy command bridge requires at least 15% Weapons reactor power allocation."
                    bridge_miss = self.rng.random() > 0.75
                    if bridge_miss:
                        weapon_miss = True
                        enemy_miss = True
                        strike_desc = "Targeted bridge shot deflected off reinforced blast shutters; the high-risk strike failed to penetrate."
                    else:
                        crit_dmg = max(1, int(50 * enemy_guard))
                        if crit_dmg <= enemy_rem_shield:
                            enemy_rem_shield -= crit_dmg
                        else:
                            overflow = crit_dmg - enemy_rem_shield
                            enemy_rem_shield = 0
                            enemy_rem_hull -= overflow
                        enemy_rem_damage = 0
                        strike_desc = f"Bridge strike pierced the command deck! Hostile command crew panicked; counter-battery cancelled (0 inbound damage) and dealt {crit_dmg} critical damage!"

                if combat_reactor.heat >= max_heat * 0.85 and heat_gain > 0.0:
                    strike_desc += f" [REACTOR WARNING: Core heat at {combat_reactor.heat:.0f}/{max_heat:.0f} MW]"

            elif action in ("board_enemy", "board", "capture"):
                if combat.enemy_shield > 0:
                    return False, "Enemy shields are still up; collapse them before boarding."
                crippled_at = max(1, int(combat.enemy_max_hull * 0.30))
                if combat.enemy_hull > crippled_at:
                    return (
                        False,
                        f"Enemy hull is still at {combat.enemy_hull}/{combat.enemy_max_hull}; "
                        f"board only below {crippled_at} hull.",
                    )
                marines = [
                    member for member in ship.crew
                    if member.role == "marine" and member.status == "active"
                    and member.injury_ticks == 0
                ]
                if not marines:
                    hurt = any(
                        member.role == "marine" and member.status == "active"
                        and member.injury_ticks > 0
                        for member in ship.crew
                    )
                    if hurt:
                        return False, "Marine boarding party is injured and unfit to breach; let them recover first."
                    return False, "No active marine boarding party aboard."
                marine = max(marines, key=lambda member: member.skill)
                hull_edge = 1.0 - combat.enemy_hull / max(1, combat.enemy_max_hull)
                chance = min(0.92, 0.35 + hull_edge * 0.45 + marine.skill * 0.025)
                if self.rng.random() < chance:
                    prize = FleetShip(
                        id=f"prize_{self.state.time.tick}_{len(fleet_ships) + 1}",
                        name=f"Prize: {combat.enemy_name}",
                        ship_class=combat.enemy_class,
                        role="prize",
                        hull=max(1, combat.enemy_hull),
                        max_hull=max(1, combat.enemy_max_hull),
                        shield=0,
                        max_shield=max(0, combat.enemy_max_shield),
                        damage=max(4, combat.enemy_damage // 2),
                        evasion=0.08,
                        assigned_system_id=self.current_system.id,
                        status="escorting",
                        experience=0,
                    )
                    new_fleet_ships = self._merge_fleet_ships(fleet_ships + (prize,))
                    stats["ships_captured"] = int(stats.get("ships_captured", 0)) + 1
                    stats["combat_victories"] = int(stats.get("combat_victories", 0)) + 1
                    msg = (
                        f"PRIZE CAPTURED: {marine.name}'s boarding party seized "
                        f"{combat.enemy_name}. The crippled {combat.enemy_class} now flies as "
                        f"a {prize.name} escort."
                    )
                    new_log = list(self.state.ship.flight_log[-19:]) + [msg]
                    new_ship = self._clone_ship(
                        fleet_ships=new_fleet_ships,
                        tactical_combo=0,
                        streak=new_streak,
                        flight_log=tuple(new_log[-20:]),
                    )
                    self.state = self._clone_state(
                        ship=new_ship,
                        active_combat=None,
                        stats=stats,
                    )
                    return True, msg

                injured = tuple(
                    replace(member, injury_ticks=max(4, member.injury_ticks + 4))
                    if member.id == marine.id else member
                    for member in ship.crew
                )
                boarding_crew, morale_log = apply_morale_event(
                    injured, -3.0, "boarding action repelled"
                )
                strike_desc = (
                    f"Boarding action repelled by {combat.enemy_name}; "
                    f"{marine.name} was injured and the party fell back."
                )
                if morale_log:
                    strike_desc += f" {morale_log}"
                new_combo = 0

            elif action == "point_defense":
                wep_power = self._effective_power("weapons")
                eng_power = self._effective_power("engines")
                if wep_power < 15 and eng_power < 15:
                    return False, "Point Defense Cannons require at least 15% power routed to Weapons or Engines."
                flak_dmg = 14
                if enemy_rem_shield > 0:
                    shield_hit = min(flak_dmg, enemy_rem_shield)
                    enemy_rem_shield -= shield_hit
                    rem_flak = flak_dmg - shield_hit
                    if rem_flak > 0:
                        enemy_rem_hull = max(0, enemy_rem_hull - rem_flak)
                else:
                    enemy_rem_hull = max(0, enemy_rem_hull - flak_dmg)
                strike_desc = f"Point Defense Cannons engaged! Tungsten flak shredded hostile armor for {flak_dmg} kinetic damage."
                new_combo += 1

            elif action == "vent_heat":
                ok, purged_reactor, purge_msg = vent_reactor(combat_reactor, self.state.time.tick)
                if not ok:
                    return False, purge_msg
                combat_reactor = purged_reactor
                strike_desc = f"Tactical Coolant Vent: {purge_msg}"

            elif action == "shield_absorb":
                boost = 30 + (25 if "dreadnought_tactics" in self.state.ship.mastery.specializations else 0)
                new_shield = min(self.state.ship.max_shield, new_shield + boost)
                mitigated = max(1, int(combat.enemy_damage * 0.35 * (EXECUTE_DAMAGE_MULTIPLIER if intent == "execute" else 1.0)))
                if new_shield >= mitigated:
                    new_shield -= mitigated
                else:
                    new_hull = max(0, new_hull - (mitigated - new_shield))
                    new_shield = 0
                msg = f"Shield capacitors overcharged (+{boost} MW). Enemy barrage deflected, taking only {mitigated} damage."
                if new_hull <= 0:
                    return self._combat_defeat(combat, note=msg)
                next_intent, next_telegraph = choose_enemy_intent(
                    profile=combat.ai_profile,
                    special_ability=combat.special_ability,
                    ability_ready=max(0, combat.ability_cooldown - 1) == 0,
                    enemy_hull=combat.enemy_hull,
                    enemy_max_hull=combat.enemy_max_hull,
                    enemy_shield=combat.enemy_shield,
                    enemy_max_shield=combat.enemy_max_shield,
                    player_hull=new_hull,
                    player_max_hull=self.state.ship.max_hull,
                    player_shield=new_shield,
                    player_max_shield=self.state.ship.max_shield,
                    player_combo=new_combo,
                )
                new_combat = CombatEncounter(
                    id=combat.id,
                    enemy_name=combat.enemy_name,
                    enemy_class=combat.enemy_class,
                    enemy_hull=combat.enemy_hull,
                    enemy_max_hull=combat.enemy_max_hull,
                    enemy_damage=combat.enemy_damage,
                    bounty_credits=combat.bounty_credits,
                    salvage_commodity=combat.salvage_commodity,
                    enemy_shield=combat.enemy_shield,
                    enemy_max_shield=combat.enemy_max_shield,
                    faction_id=combat.faction_id,
                    special_ability=combat.special_ability,
                    ability_cooldown=max(0, combat.ability_cooldown - 1),
                    telegraphed_action=next_telegraph,
                    ai_profile=combat.ai_profile,
                    enemy_intent=next_intent,
                    archetype_id=combat.archetype_id,
                    near_miss_awarded=combat.near_miss_awarded,
                    captain_gambit_used=combat.captain_gambit_used,
                    captain_evasion_bonus=combat.captain_evasion_bonus,
                )
                new_log = list(self.state.ship.flight_log[-19:]) + [msg]
                new_ship = self._clone_ship(hull=new_hull, shield=new_shield, reactor=combat_reactor, tactical_combo=new_combo, streak=new_streak, flight_log=tuple(new_log[-20:]))
                self.state = self._clone_state(ship=new_ship, active_combat=new_combat)
                return True, msg

            elif action == "evasive_burn":
                burn_cost = 3
                if self.state.ship.fuel < burn_cost:
                    return False, f"Insufficient fuel for an evasive burn ({burn_cost} units required)."
                new_fuel = self.state.ship.fuel - burn_cost
                eng = self.state.ship.power.engines
                chance = min(0.95, 0.50 + (eng / 25.0) * 0.20 + equipment["evasion"])
                if self.rng.random() < chance:
                    msg = "High-G burn successful! Evaded enemy weapon tracking and escaped hostile sector (expedition streak reset)."
                    new_combat = None
                    new_streak = 1
                    new_combo = 0
                else:
                    dmg = combat.enemy_damage
                    if new_shield >= dmg:
                        new_shield -= dmg
                    else:
                        new_hull = max(0, new_hull - (dmg - new_shield))
                        new_shield = 0
                    msg = f"Evasive burn failed! Suffered {dmg} damage during high-G maneuver."
                    new_combat = combat
                if new_hull <= 0:
                    return self._combat_defeat(combat, note=msg, fuel=new_fuel)
                new_log = list(self.state.ship.flight_log[-19:]) + [msg]
                new_ship = self._clone_ship(
                    hull=new_hull,
                    shield=new_shield,
                    fuel=new_fuel,
                    tactical_combo=new_combo,
                    streak=new_streak,
                    flight_log=tuple(new_log[-20:]),
                )
                self.state = self._clone_state(ship=new_ship, active_combat=new_combat)
                return True, msg

            elif action == "flee":
                if self.state.ship.fuel < 8:
                    return False, "Insufficient fuel for emergency jump (8 units required)."
                new_fuel = self.state.ship.fuel - 8
                msg = "Emergency hyperspace micro-jump executed. Safely disengaged from hostile sector (expedition streak reset)."
                new_ship = self._clone_ship(hull=new_hull, shield=new_shield, fuel=new_fuel, streak=1, tactical_combo=0, flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [msg]))
                self.state = self._clone_state(ship=new_ship, active_combat=None)
                return True, msg

            else:
                return False, f"Unknown combat action '{action}'. Choices: fire_lasers, drone_strike, target_subsystem, target_weapons, target_shields, target_engines, target_bridge, board_enemy, shield_absorb, point_defense, vent_heat, evasive_burn, flee."

            if enemy_miss:
                enemy_rem_hull = enemy_hull_before
                enemy_rem_shield = enemy_shield_before
                if not weapon_miss:
                    strike_desc = "Enemy AI jinked out of your firing solution; the strike missed."
            # Near-miss comeback (Clark et al.: almost-WON only). The first
            # near-miss per encounter grants one capped +1 combo surge; later
            # ones are flavor. Never manufactured: real hull proximity only.
            if (
                action in damaging_actions
                and not enemy_miss
                and enemy_rem_hull > 0
                and combat.enemy_max_hull > 0
                and enemy_rem_hull <= combat.enemy_max_hull * NEAR_MISS_COMBAT_HULL_FRACTION
            ):
                stats["near_miss_combat"] = int(stats.get("near_miss_combat", 0)) + 1
                if not combat.near_miss_awarded:
                    new_combo += 1
                    combat = replace(combat, near_miss_awarded=True)
                    strike_desc += (
                        f" NEAR-MISS SURGE: {combat.enemy_name} hangs by a thread "
                        "— tactical focus surges (+1 combo, once per fight)!"
                    )
                else:
                    strike_desc += " Near miss again — the kill slips away. Finish it."
            elif fleet_ships and action in damaging_actions:
                fleet_volley = fleet_damage(fleet_ships, battle_stance)
                if fleet_volley > 0:
                    effective_volley = fleet_volley
                    if enemy_rem_shield > 0:
                        shield_hit = min(fleet_volley, enemy_rem_shield)
                        enemy_rem_shield -= shield_hit
                        fleet_volley -= shield_hit
                    if fleet_volley > 0:
                        enemy_rem_hull -= fleet_volley
                    strike_desc += f" Escort wing added {effective_volley} coordinated damage ({battle_stance} stance)."

            # Check if enemy was neutralized
            if enemy_rem_hull <= 0:
                payout_mult, payout_label = payout_magnitude_for(
                    self.seed, "combat-payout", combat.id,
                    int(stats.get("combat_victories", 0)),
                )
                bounty_paid = int(combat.bounty_credits * payout_mult)
                stats[f"payout_{payout_label}"] = int(stats.get(f"payout_{payout_label}", 0)) + 1
                new_credits += bounty_paid
                salvage_granted, salvage_overflow = self._grant_cargo(cargo, combat.salvage_commodity, 2)
                stats["combat_victories"] += 1
                stats["credits_earned"] += bounty_paid
                if any(d.drone_type == "mercenary" and d.specialty == "repair" for d in self.state.ship.fleet_drones):
                    new_hull = min(self.state.ship.max_hull, new_hull + 8)

                salvage_relic, _ = roll_relic_drop(self.rng, bonus_prob=0.20, current_system=self.current_system.name)
                new_relics = list(self.state.ship.relics)
                relic_note = ""
                new_max_hull = self.state.ship.max_hull
                new_max_shield = self.state.ship.max_shield
                if salvage_relic:
                    new_relics.append(salvage_relic)
                    relic_note = f" Salvaged Precursor relic: [{salvage_relic.name}] ({salvage_relic.rarity.upper()})!"
                    new_hull, new_max_hull, new_shield, new_max_shield = self._apply_relic_stat_bonuses(
                        new_hull,
                        new_max_hull,
                        new_shield,
                        new_max_shield,
                        [salvage_relic],
                    )

                updated_contracts, contract_logs = self._progress_contracts("combat", 1)
                new_mastery, xp_logs = self._award_pilot_xp(200, self.state.ship.mastery)

                # Faction and corporate reputation shift upon victory
                new_faction_standings = dict(self.state.ship.faction_standings)
                new_corp_standings = dict(self.state.ship.corp_standings)
                rep_note = ""
                archetype = ENEMY_ARCHETYPES.get(combat.archetype_id)
                if archetype and archetype.rep_rewards:
                    shifts: list[str] = []
                    for entity_id, delta in archetype.rep_rewards.items():
                        if entity_id in CANONICAL_FACTIONS:
                            current = new_faction_standings.get(entity_id, 0)
                            new_faction_standings[entity_id] = max(-100, min(100, current + delta))
                            shifts.append(f"{CANONICAL_FACTIONS[entity_id].name} ({delta:+d})")
                        elif entity_id in CANONICAL_CORPORATIONS:
                            current = new_corp_standings.get(entity_id, 0)
                            new_corp_standings[entity_id] = max(-100, min(100, current + delta))
                            shifts.append(f"{CANONICAL_CORPORATIONS[entity_id].name} ({delta:+d})")
                    if shifts:
                        rep_note = " [Standing: " + ", ".join(shifts) + "]"
                elif combat.faction_id == "outlaw_corsairs":
                    new_faction_standings["sol_coalition"] = min(100, new_faction_standings.get("sol_coalition", 0) + 5)
                    new_faction_standings["nebula_collective"] = min(100, new_faction_standings.get("nebula_collective", 0) + 4)
                    new_faction_standings["vanguard_syndicate"] = min(100, new_faction_standings.get("vanguard_syndicate", 0) + 2)
                    new_faction_standings["outlaw_corsairs"] = max(-100, new_faction_standings.get("outlaw_corsairs", 0) - 10)
                    rep_note = " [Faction Standing: Sol Coalition (+5), Nebula Collective (+4), Void Corsairs (-10)]"
                elif combat.faction_id == "vanguard_syndicate":
                    new_faction_standings["sol_coalition"] = min(100, new_faction_standings.get("sol_coalition", 0) + 6)
                    new_faction_standings["vanguard_syndicate"] = max(-100, new_faction_standings.get("vanguard_syndicate", 0) - 8)
                    rep_note = " [Faction Standing: Sol Coalition (+6), Free Spacers Syndicate (-8)]"
                elif combat.faction_id == "hyperion_dynamics":
                    new_faction_standings["outlaw_corsairs"] = min(100, new_faction_standings.get("outlaw_corsairs", 0) + 6)
                    new_faction_standings["sol_coalition"] = max(-100, new_faction_standings.get("sol_coalition", 0) - 6)
                    rep_note = " [Faction Standing: Void Corsairs (+6), Sol Coalition (-6)]"
                elif combat.faction_id == "precursor_watch":
                    new_faction_standings["precursor_watch"] = min(100, new_faction_standings.get("precursor_watch", 0) + 8)
                    rep_note = " [Faction Standing: Precursor Watch (+8)]"

                xp_gain = fleet_victory_experience(combat.enemy_max_hull)
                local_fleet_ids = {local.id for local in fleet_ships}
                captain_crew = list(self.state.ship.crew)
                local_captains = {
                    escort.captain_id
                    for escort in self.state.ship.fleet_ships
                    if escort.id in local_fleet_ids
                    and escort.captain_id
                    and escort.hull > 0
                }
                captain_promotions: list[str] = []
                for index, member in enumerate(captain_crew):
                    if member.id not in local_captains:
                        continue
                    promoted_member, promoted = award_crew_xp(
                        member, CAPTAIN_VICTORY_XP
                    )
                    promoted_member = replace(
                        promoted_member,
                        battles=promoted_member.battles + 1,
                    )
                    promoted_member, earned_medals = award_service_medals(
                        promoted_member
                    )
                    captain_crew[index] = promoted_member
                    if promoted:
                        captain_promotions.append(
                            f"CAPTAIN PROMOTION: {promoted_member.name} reaches "
                            f"skill {promoted_member.skill}."
                        )
                    if earned_medals:
                        captain_promotions.append(
                            f"SERVICE MEDAL: {promoted_member.name} awarded "
                            f"{', '.join(earned_medals)}."
                        )
                captain_by_id = {member.id: member for member in captain_crew}
                fleet_updates: list[FleetShip] = []
                rank_up_lines: list[str] = []
                for escort in self.state.ship.fleet_ships:
                    if escort.id not in local_fleet_ids:
                        fleet_updates.append(escort)
                        continue
                    before_rank = fleet_rank(escort.experience)["name"]
                    captain = captain_by_id.get(escort.captain_id)
                    updated_escort = replace(
                        escort,
                        experience=min(
                            FLEET_MAX_EXPERIENCE, escort.experience + xp_gain
                        ),
                        status="escorting" if escort.hull > 0 else "destroyed",
                        captain_skill=(
                            captain.skill if captain is not None else escort.captain_skill
                        ),
                    )
                    if updated_escort.hull > 0:
                        updated_escort = replace(
                            updated_escort,
                            battles=updated_escort.battles + 1,
                            kills=updated_escort.kills + 1,
                        )
                    after_rank = fleet_rank(updated_escort.experience)["name"]
                    if after_rank != before_rank:
                        rank_up_lines.append(
                            f"{escort.name} promoted to {after_rank}."
                        )
                    fleet_updates.append(updated_escort)
                new_fleet_ships = tuple(fleet_updates)
                payout_note = (
                    f" [{payout_label.upper()} x{payout_mult:.1f}]"
                    if payout_label != "standard"
                    else ""
                )
                msg = (
                    f"VICTORY: {combat.enemy_name} neutralized! "
                    f"Collected {bounty_paid} cr bounty{payout_note}, salvaged {salvage_granted}x {combat.salvage_commodity}"
                    f"{f' ({salvage_overflow} jettisoned: hold full)' if salvage_overflow else ''}.{relic_note}{rep_note}"
                    + (f" {' '.join(rank_up_lines)}" if rank_up_lines else "")
                    + (f" {' '.join(captain_promotions)}" if captain_promotions else "")
                )
                log_entry = f"Combat outcome: {msg}"
                new_log = list(self.state.ship.flight_log[-19:]) + [log_entry] + contract_logs + xp_logs
                victory_crew, morale_log = apply_morale_event(tuple(captain_crew), 5.0, "combat victory celebrated")
                if morale_log:
                    new_log.append(morale_log)
                systems_after = dict(self.state.systems)
                eliminated_after = self.state.eliminated_factions
                war_target = next(
                    (
                        war for war in self.state.wars
                        if war.active and war.defender_id == combat.faction_id and war.attacker_id == "sol_coalition"
                    ),
                    None,
                )
                if war_target:
                    system = systems_after[self.current_system.id]
                    systems_after[self.current_system.id] = replace(system, faction=CANONICAL_FACTIONS["sol_coalition"].name)
                    msg += f" {system.name} captured for the Sol Coalition."
                    owned = [
                        sid for sid, sys_obj in systems_after.items()
                        if sys_obj.faction == (CANONICAL_FACTIONS[combat.faction_id].name if combat.faction_id in CANONICAL_FACTIONS else "")
                    ]
                    if not owned and combat.faction_id not in eliminated_after:
                        eliminated_after = tuple(sorted(set(eliminated_after) | {combat.faction_id}))
                        msg += f" {combat.faction_id} has been eliminated."

                new_ship = self._clone_ship(
                    hull=new_hull,
                    max_hull=new_max_hull,
                    shield=new_shield,
                    max_shield=new_max_shield,
                    credits=new_credits,
                    cargo=cargo,
                    relics=tuple(new_relics),
                    mastery=new_mastery,
                    active_contracts=updated_contracts,
                    faction_standings=new_faction_standings,
                    corp_standings=new_corp_standings,
                    reactor=combat_reactor,
                    tactical_combo=0,
                    streak=new_streak,
                    crew=victory_crew,
                    fleet_ships=new_fleet_ships,
                    flight_log=tuple(new_log[-20:]),
                )

                self.state = self._clone_state(
                    ship=new_ship,
                    active_combat=None,
                    stats=stats,
                    systems=systems_after,
                    eliminated_factions=eliminated_after,
                )
                return True, msg

            # Enemy counter-attack and tactical abilities
            ability_note = ""
            if intent == "ability" and ability_cd == 0 and combat.special_ability != "none":
                if combat.special_ability == "shield_drain":
                    drain_amt = min(15, new_shield)
                    new_shield -= drain_amt
                    enemy_rem_shield = min(combat.enemy_max_shield, enemy_rem_shield + drain_amt)
                    ability_note = f" [ABILITY: Shield Drain siphoned {drain_amt} MW from your deflectors!]"
                    ability_cd = 2
                elif combat.special_ability == "emp_overload":
                    new_combo = 0
                    enemy_rem_damage += 8
                    ability_note = " [ABILITY: EMP Overload shockwave disrupted tactical systems!]"
                    ability_cd = 2
                elif combat.special_ability == "nanite_regen" and enemy_rem_shield > 0:
                    enemy_rem_hull = min(combat.enemy_max_hull, enemy_rem_hull + 20)
                    ability_note = " [ABILITY: Nanite Swarm regenerated +20 enemy Hull!]"
                    ability_cd = 2
                elif combat.special_ability == "tachyon_lance":
                    new_hull = max(0, new_hull - TACHYON_LANCE_HULL_DAMAGE)
                    ability_note = f" [ABILITY: Tachyon Lance phase-pierced your shields for {TACHYON_LANCE_HULL_DAMAGE} direct hull damage!]"
                    ability_cd = 2

            # Standard counter-battery
            inbound = int(enemy_rem_damage * (EXECUTE_DAMAGE_MULTIPLIER if intent == "execute" else 1.0))
            evasion_note = ""
            if action == "point_defense":
                inbound = max(1, int(inbound * 0.30))
                evasion_note = " [PDC flak screen intercepted 70% of inbound counter-battery!]"
            fleet_evasion = min(
                0.45,
                fleet_evasion_bonus(fleet_ships, battle_stance)
                + combat.captain_evasion_bonus,
            )
            if inbound > 0 and (equipment["evasion"] + mercenary_evasion + fleet_evasion) > 0.0 and self.rng.random() < min(0.95, equipment["evasion"] + mercenary_evasion + fleet_evasion):
                inbound = 0
                evasion_note += " [Ion afterburners and escort screen evaded incoming fire!]"
            if inbound > 0 and fleet_ships:
                fleet_ships, absorbed = apply_fleet_casualties(fleet_ships, max(1, inbound // 2))
                if absorbed > 0:
                    inbound = max(0, inbound - absorbed)
                    evasion_note += f" Escort screen absorbed {absorbed} damage."
            support_repair = fleet_support_repair(fleet_ships)
            if support_repair > 0:
                fleet_ships, repaired = repair_fleet_ships(fleet_ships, support_repair)
                if repaired > 0:
                    evasion_note += f" Support wing restored {repaired} integrity."
            breach_crew = None
            breach_log = ""
            if new_shield >= inbound:
                new_shield -= inbound
            else:
                overflow = inbound - new_shield
                new_shield = 0
                new_hull = max(0, new_hull - overflow)
                new_combo = 0
                breach_crew, breach_log = apply_morale_event(self.state.ship.crew, -4.0, "hull breach under fire")
                if new_hull < 50:
                    new_streak = max(1, self.state.ship.streak - 1)

            if new_hull <= 0:
                return self._combat_defeat(
                    combat, note=breach_log,
                    fleet_ships=self._merge_fleet_ships(fleet_ships),
                    crew=breach_crew if breach_crew is not None else boarding_crew,
                    streak=new_streak,
                )

            # AI selects the next maneuver from live hull, shield, combo, and profile state.
            next_intent, next_telegraph = choose_enemy_intent(
                profile=combat.ai_profile,
                special_ability=combat.special_ability,
                ability_ready=ability_cd == 0,
                enemy_hull=enemy_rem_hull,
                enemy_max_hull=combat.enemy_max_hull,
                enemy_shield=enemy_rem_shield,
                enemy_max_shield=combat.enemy_max_shield,
                player_hull=new_hull,
                player_max_hull=self.state.ship.max_hull,
                player_shield=new_shield,
                player_max_shield=self.state.ship.max_shield,
                player_combo=new_combo,
            )

            msg = f"{strike_desc} Inbound counter-battery dealt {inbound} damage.{evasion_note}{ability_note} (Enemy HP: {enemy_rem_hull}/{combat.enemy_max_hull}, Shield: {enemy_rem_shield}/{combat.enemy_max_shield})"

            new_combat = CombatEncounter(
                id=combat.id,
                enemy_name=combat.enemy_name,
                enemy_class=combat.enemy_class,
                enemy_hull=enemy_rem_hull,
                enemy_max_hull=combat.enemy_max_hull,
                enemy_damage=enemy_rem_damage,
                bounty_credits=combat.bounty_credits,
                salvage_commodity=combat.salvage_commodity,
                enemy_shield=enemy_rem_shield,
                enemy_max_shield=combat.enemy_max_shield,
                faction_id=combat.faction_id,
                special_ability=combat.special_ability,
                ability_cooldown=ability_cd,
                telegraphed_action=next_telegraph,
                ai_profile=combat.ai_profile,
                enemy_intent=next_intent,
                archetype_id=combat.archetype_id,
                near_miss_awarded=combat.near_miss_awarded,
                captain_gambit_used=combat.captain_gambit_used,
                captain_evasion_bonus=combat.captain_evasion_bonus,
            )

            new_log = list(self.state.ship.flight_log[-19:]) + [msg]
            if breach_log:
                new_log.append(breach_log)
            new_ship = self._clone_ship(
                hull=new_hull,
                shield=new_shield,
                reactor=combat_reactor,
                tactical_combo=new_combo,
                streak=new_streak,
                crew=(
                    breach_crew if breach_crew is not None
                    else boarding_crew if boarding_crew is not None
                    else self.state.ship.crew
                ),
                fleet_ships=self._merge_fleet_ships(fleet_ships),
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(
                ship=new_ship,
                active_combat=new_combat,
                stats=stats,
            )
            return True, msg

    def resolve_anomaly(self, choice_id: str) -> tuple[bool, str]:
        """Resolve current deep-space anomaly encounter with power-check validation."""
        with self.lock:
            anomaly = self.state.active_anomaly
            if not anomaly:
                return False, "No active spatial anomaly to resolve."

            choice = next((c for c in anomaly.choices if c.choice_id == choice_id), None)
            if not choice:
                return False, f"Unknown resolution option '{choice_id}'."

            # Verify power threshold
            power_val = 0
            if choice.required_power != "none":
                power_val = self._effective_power(choice.required_power)
                if power_val < choice.min_power_threshold:
                    hull_loss = 15
                    new_hull = max(0, self.state.ship.hull - hull_loss)
                    log_entry = (
                        f"CRITICAL: Failed {choice.required_power.upper()} check ({power_val}% < {choice.min_power_threshold}%)! "
                        f"Hull suffered {hull_loss} damage during anomaly surge."
                    )
                    new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

                    new_ship = self._clone_ship(
                        hull=new_hull,
                        flight_log=tuple(new_log),
                    )

                    self.state = self._clone_state(
                        ship=new_ship,
                        active_anomaly=None,
                    )

                    return False, log_entry

            # Success outcome
            new_hull = min(self.state.ship.max_hull, max(0, self.state.ship.hull + choice.hull_delta))
            new_credits = max(0, self.state.ship.credits + choice.credits_delta)
            new_fuel = min(self.state.ship.max_fuel, max(0, self.state.ship.fuel + choice.fuel_delta))

            cargo = dict(self.state.ship.cargo)
            overflow_items: list[str] = []
            for item_k, item_v in choice.cargo_reward.items():
                granted, overflow = self._grant_cargo(cargo, item_k, item_v)
                if overflow:
                    overflow_items.append(f"{overflow}x {item_k}")

            log_entry = f"Anomaly resolved: {choice.outcome_text}"
            if overflow_items:
                log_entry += f" Hold full: jettisoned {', '.join(overflow_items)}."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            new_contracts, contract_logs = self._progress_contracts("anomaly", 1)
            new_log.extend(contract_logs)

            new_ship = self._clone_ship(
                hull=new_hull,
                fuel=new_fuel,
                credits=new_credits,
                cargo=cargo,
                active_contracts=new_contracts,
                flight_log=tuple(new_log),
            )

            stats = dict(self.state.stats)
            stats["anomalies_resolved"] += 1
            if choice.credits_delta > 0:
                stats["credits_earned"] += choice.credits_delta

            self.state = self._clone_state(
                ship=new_ship,
                active_anomaly=None,
                stats=stats,
            )

            return True, choice.outcome_text

    def resolve_pirate_encounter(self, action: str) -> tuple[bool, str]:
        """Resolve a pirate toll: pay, fight, or burn clear. Flight resumes afterward."""
        with self.lock:
            pirate = self.state.active_pirate
            if pirate is None:
                return False, "No pirate encounter is active."
            action = str(action).strip().lower()
            stats = dict(self.state.stats)
            if action in ("pay", "toll"):
                if self.state.ship.credits < pirate.toll_credits:
                    return False, (
                        f"Insufficient credits: {pirate.toll_credits} cr demanded, "
                        f"{self.state.ship.credits} available."
                    )
                log = (
                    f"PIRATE TOLL PAID: {pirate.band_name} accepts {pirate.toll_credits} cr; "
                    f"the raider peels away."
                )
                new_contracts, contract_logs = self._progress_contracts("pirates", 1)
                new_ship = self._clone_ship(
                    credits=self.state.ship.credits - pirate.toll_credits,
                    active_contracts=new_contracts,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log] + contract_logs),
                )
                stats["pirates_paid"] = int(stats.get("pirates_paid", 0)) + 1
                self.state = self._clone_state(ship=new_ship, active_pirate=None, stats=stats)
                return True, log

            if action in ("fight", "engage"):
                system = self.state.systems.get(pirate.system_id) or self.current_system
                combat = generate_system_enemy(
                    system_id=system.id,
                    security=system.security,
                    faction="Void Corsairs",
                    seed=pirate.seed or self.rng.randint(1000, 99999),
                    threat_level=pirate.threat,
                )
                log = f"PIRATE ENGAGEMENT: Weapons free against {pirate.band_name} ({pirate.ship_class})."
                new_contracts, contract_logs = self._progress_contracts("pirates", 1)
                new_ship = self._clone_ship(
                    active_contracts=new_contracts,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log] + contract_logs),
                )
                stats["pirates_fought"] = int(stats.get("pirates_fought", 0)) + 1
                self.state = self._clone_state(
                    ship=new_ship,
                    active_pirate=None,
                    active_combat=combat,
                    stats=stats,
                )
                return True, log

            if action in ("evade", "flee", "burn"):
                fuel_cost = 6 + pirate.threat
                hull_damage = 0
                if self.rng.random() < 0.40:
                    hull_damage = 5 + pirate.threat * 3
                log = (
                    f"PIRATE EVASION: Burned clear of {pirate.band_name} "
                    f"(fuel -{min(self.state.ship.fuel, fuel_cost)}"
                    + (f", hull -{hull_damage}" if hull_damage else "")
                    + ")."
                )
                new_contracts, contract_logs = self._progress_contracts("pirates", 1)
                new_ship = self._clone_ship(
                    fuel=max(0, self.state.ship.fuel - fuel_cost),
                    hull=max(0, self.state.ship.hull - hull_damage),
                    active_contracts=new_contracts,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log] + contract_logs),
                )
                stats["pirates_evaded"] = int(stats.get("pirates_evaded", 0)) + 1
                self.state = self._clone_state(ship=new_ship, active_pirate=None, stats=stats)
                return True, log

            return False, f"Unknown pirate action '{action}'. Use pay, fight, or evade."

    def resolve_customs(self, action: str) -> tuple[bool, str]:
        """Resolve a customs interdiction: bribe, jettison, confiscate, or flee."""
        with self.lock:
            encounter = self.state.active_customs
            if encounter is None:
                return False, "No customs inspection is active."

            action = str(action).strip().lower()
            stats = dict(self.state.stats)
            sys_faction_id = get_faction_id_from_name(encounter.faction)
            standings = dict(self.state.ship.faction_standings)

            if action in ("bribe", "pay"):
                if self.state.ship.credits < encounter.bribe_amount:
                    return False, f"Insufficient credits: {encounter.bribe_amount} cr required for bribe, {self.state.ship.credits} available."
                new_credits = self.state.ship.credits - encounter.bribe_amount
                stats["bribes_paid"] = int(stats.get("bribes_paid", 0)) + 1
                new_mastery, xp_logs = self._award_pilot_xp(30, self.state.ship.mastery)
                log = f"CUSTOMS BRIBE: Paid {encounter.bribe_amount} cr to {encounter.patrol_vessel}. Manifest cleared off the record (+30 XP)."
                new_ship = self._clone_ship(
                    credits=new_credits,
                    mastery=new_mastery,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log] + xp_logs),
                )
                self.state = self._clone_state(ship=new_ship, active_customs=None, stats=stats)
                return True, log

            if action in ("jettison", "dump"):
                new_cargo = {k: v for k, v in self.state.ship.cargo.items() if not is_contraband(k)}
                dumped_units = sum(encounter.contraband_found.values())
                stats["smuggling_evaded"] = int(stats.get("smuggling_evaded", 0)) + 1
                log = f"CARGO JETTISONED: Purged {dumped_units} units of contraband into the void. Customs scanner reads clean; released without citation."
                new_ship = self._clone_ship(
                    cargo=new_cargo,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
                )
                self.state = self._clone_state(ship=new_ship, active_customs=None, stats=stats)
                return True, log

            if action in ("confiscate", "comply", "surrender"):
                new_cargo = {k: v for k, v in self.state.ship.cargo.items() if not is_contraband(k)}
                fine_paid = min(self.state.ship.credits, encounter.fine_amount)
                new_credits = self.state.ship.credits - fine_paid
                current_standing = standings.get(sys_faction_id, 0)
                standings[sys_faction_id] = max(-100, current_standing - 5)
                stats["contraband_seized"] = int(stats.get("contraband_seized", 0)) + 1
                log = f"CONTRABAND CONFISCATED: Patrol seized illicit goods. Levied {fine_paid} cr penalty and logged citation (-5 standing with {encounter.faction})."
                new_ship = self._clone_ship(
                    cargo=new_cargo,
                    credits=new_credits,
                    faction_standings=standings,
                    flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
                )
                self.state = self._clone_state(ship=new_ship, active_customs=None, stats=stats)
                return True, log

            if action in ("flee", "burn", "evade"):
                fuel_cost = 5
                if self.state.ship.fuel < fuel_cost:
                    return False, f"Insufficient fuel to burn thrusters: {fuel_cost} required."
                new_fuel = self.state.ship.fuel - fuel_cost
                eng_power = self._effective_power("engines")
                current_standing = standings.get(sys_faction_id, 0)
                standings[sys_faction_id] = max(-100, current_standing - 15)

                evasion_success = eng_power >= 35 or self.rng.random() < 0.65
                if evasion_success:
                    stats["smuggling_evaded"] = int(stats.get("smuggling_evaded", 0)) + 1
                    log = f"EVADED CUSTOMS: Emergency engine burn escaped {encounter.patrol_vessel} cordon! Fugitive warrant issued (-15 standing with {encounter.faction})."
                    new_ship = self._clone_ship(
                        fuel=new_fuel,
                        faction_standings=standings,
                        flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
                    )
                    self.state = self._clone_state(ship=new_ship, active_customs=None, stats=stats)
                    return True, log
                else:
                    new_cargo = {k: v for k, v in self.state.ship.cargo.items() if not is_contraband(k)}
                    fine_paid = min(self.state.ship.credits, encounter.fine_amount)
                    new_credits = self.state.ship.credits - fine_paid
                    new_hull = max(1, self.state.ship.hull - 15)
                    stats["contraband_seized"] = int(stats.get("contraband_seized", 0)) + 1
                    log = f"INTERCEPTED: Suppression fire hit your ship (-15 Hull)! Contraband confiscated and {fine_paid} cr fine imposed (-15 standing)."
                    new_ship = self._clone_ship(
                        hull=new_hull,
                        fuel=new_fuel,
                        cargo=new_cargo,
                        credits=new_credits,
                        faction_standings=standings,
                        flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
                    )
                    self.state = self._clone_state(ship=new_ship, active_customs=None, stats=stats)
                    return True, log

            return False, f"Unknown customs action: '{action}'. Choose 'bribe', 'jettison', 'confiscate', or 'flee'."

    def overhaul_ship(self) -> tuple[bool, str]:
        """Overhaul structural frame and hyperlane wear at orbital drydock."""
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, "Ship overhaul requires a station or a Frontier Shipyard in this system."
            wear = self.state.ship.wear
            if wear <= 0.0:
                return False, "Ship structural frame is pristine with 0% hyperlane wear."
            faction_id = get_faction_id_from_name(self.current_system.faction)
            perks = get_faction_service_perks(faction_id, self.state.ship.faction_standings.get(faction_id, 0))
            cost = max(10, int(wear * 4.5 * (1.0 - float(perks["repair_discount"]))))
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: overhaul costs {cost} cr ({wear:.1f}% wear)."
            new_ship = self._clone_ship(
                wear=0.0,
                credits=self.state.ship.credits - cost,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Drydock overhaul completed: {wear:.1f}% wear restored for {cost} cr."]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, f"Structural overhaul completed: {wear:.1f}% wear scrubbed for {cost} cr."

    def drydock_quote(self) -> dict[str, Any]:
        """Live drydock service prices for the cockpit service deck.

        Mirrors the exact formulas used by repair_hull, refuel and overhaul_ship so the
        labels can never quote a different price than the charge.
        """
        with self.lock:
            docked, _ = self._require_service_dock()
            ship = self.state.ship
            faction_id = get_faction_id_from_name(self.current_system.faction)
            perks = get_faction_service_perks(
                faction_id, ship.faction_standings.get(faction_id, 0)
            )
            discount = float(perks["repair_discount"])
            repair_hp = min(25, max(0, ship.max_hull - ship.hull))
            repair_cost = max(0, int(repair_hp * 4 * (1.0 - discount)))
            fuel_units = min(20, max(0, ship.max_fuel - ship.fuel))
            refuel_cost = 0 if perks["free_refuel"] else fuel_units * 6
            wear = max(0.0, float(ship.wear))
            overhaul_cost = 0 if wear <= 0.0 else max(10, int(wear * 4.5 * (1.0 - discount)))
            return {
                "docked": docked,
                "repair_hp": repair_hp,
                "repair_cost": repair_cost,
                "fuel_units": fuel_units,
                "refuel_cost": refuel_cost,
                "free_refuel": bool(perks["free_refuel"]),
                "wear": round(wear, 2),
                "overhaul_cost": overhaul_cost,
                "repair_discount": round(discount, 3),
                "credits": ship.credits,
            }

    def repair_hull(self, amount: int = 25) -> tuple[bool, str]:
        """Repair ship hull integrity at orbital station."""
        with self.lock:
            if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                return False, "Repair amount must be a positive integer."
            ok, msg = self._require_service_dock()
            if not ok:
                return False, (
                    "Repair drydocks require a station or a Frontier Shipyard in this system."
                )

            needed = self.state.ship.max_hull - self.state.ship.hull
            if needed <= 0:
                return False, "Hull integrity already at 100% capacity."

            actual = min(amount, needed)
            faction_id = get_faction_id_from_name(self.current_system.faction)
            perks = get_faction_service_perks(faction_id, self.state.ship.faction_standings.get(faction_id, 0))
            cost = max(0, int(actual * 4 * (1.0 - float(perks["repair_discount"]))))
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: repair costs {cost} cr ({actual} HP)."

            new_ship = self._clone_ship(
                hull=self.state.ship.hull + actual,
                credits=self.state.ship.credits - cost,
                wear=max(0.0, self.state.ship.wear - actual * 0.2),
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Drydock repair: +{actual} HP for {cost} cr."]),
            )

            self.state = self._clone_state(ship=new_ship)
            return True, f"Repairs completed: +{actual} HP restored for {cost} cr."

    def refuel(self, amount: int = 20) -> tuple[bool, str]:
        """Refuel quantum drive at orbital station."""
        with self.lock:
            if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                return False, "Refuel amount must be a positive integer."
            ok, msg = self._require_service_dock()
            if not ok:
                return False, (
                    "Fuel refinery requires a station or a Frontier Shipyard in this system."
                )

            needed = self.state.ship.max_fuel - self.state.ship.fuel
            if needed <= 0:
                return False, "Fuel reserves already at maximum capacity."

            actual = min(amount, needed)
            faction_id = get_faction_id_from_name(self.current_system.faction)
            perks = get_faction_service_perks(faction_id, self.state.ship.faction_standings.get(faction_id, 0))
            cost = 0 if perks["free_refuel"] else actual * 6
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: refueling costs {cost} cr ({actual} fuel)."

            new_ship = self._clone_ship(
                fuel=self.state.ship.fuel + actual,
                credits=self.state.ship.credits - cost,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Refueled +{actual} quantum fuel for {cost} cr."]),
            )

            self.state = self._clone_state(ship=new_ship)

            return True, f"Fuel tanks replenished: +{actual} units for {cost} cr."

    def fabricate_munitions(self, munitions_type: str = "patch_kit") -> tuple[bool, str]:
        """Field-fabricate emergency hull patch kits or fuel packs from raw titanium alloy."""
        with self.lock:
            ship = self.state.ship
            cargo = dict(ship.cargo)
            titanium_count = cargo.get("titanium", 0)
            if titanium_count < 1:
                return False, "Field fabrication failed: Insufficient titanium alloy in cargo (1 unit required)."

            blueprint = munitions_type.lower().strip()
            if blueprint in ("patch_kit", "armor_patch", "hull_patch"):
                if ship.hull >= ship.max_hull:
                    return False, f"Hull integrity is already at maximum capacity ({ship.hull}/{ship.max_hull} HP)."
                new_cargo = dict(cargo)
                new_cargo["titanium"] -= 1
                if new_cargo["titanium"] <= 0:
                    del new_cargo["titanium"]
                restored = min(25, ship.max_hull - ship.hull)
                new_hull = ship.hull + restored
                msg = f"Fabricated Emergency Armor Patch Kit from 1x titanium alloy (+{restored} Hull restored; {new_hull}/{ship.max_hull} HP)."
                new_ship = self._clone_ship(
                    hull=new_hull,
                    cargo=new_cargo,
                    flight_log=tuple(list(ship.flight_log[-19:]) + [msg]),
                )
                self.state = self._clone_state(ship=new_ship)
                return True, msg

            elif blueprint in ("fuel_cell", "fuel_pack", "energy_cell"):
                if ship.fuel >= ship.max_fuel:
                    return False, f"Quantum fuel tanks are already at maximum capacity ({ship.fuel}/{ship.max_fuel} Fuel)."
                new_cargo = dict(cargo)
                new_cargo["titanium"] -= 1
                if new_cargo["titanium"] <= 0:
                    del new_cargo["titanium"]
                restored = min(25, ship.max_fuel - ship.fuel)
                new_fuel = ship.fuel + restored
                msg = f"Synthesized Emergency Fuel Cell Pack from 1x titanium alloy (+{restored} Fuel restored; {new_fuel}/{ship.max_fuel} Fuel)."
                new_ship = self._clone_ship(
                    fuel=new_fuel,
                    cargo=new_cargo,
                    flight_log=tuple(list(ship.flight_log[-19:]) + [msg]),
                )
                self.state = self._clone_state(ship=new_ship)
                return True, msg

            else:
                return False, f"Unknown fabrication blueprint '{munitions_type}'. Valid blueprints: 'patch_kit', 'fuel_cell'."

    def check_solar_weather(self, system: StarSystem | None = None) -> dict[str, Any]:
        """Telemetry check for space weather and coronal radiation risk in the specified or current system."""
        with self.lock:
            sys_obj = system or self.current_system
            is_active = sys_obj.spectral_type in ("O", "B", "WolfRayet", "RedGiant", "Neutron")
            weather_hazard = 0.35 if is_active else 0.0
            return {
                "system_id": sys_obj.id,
                "system_name": sys_obj.name,
                "spectral_type": sys_obj.spectral_type,
                "active_hazard": is_active,
                "hazard_chance": weather_hazard,
                "recommended_shields": 35,
                "player_shields_power": self.state.ship.power.shields,
                "shield_protected": self.state.ship.power.shields >= 35,
            }

    def step_orbits(self, delta_time: float = 1.0) -> None:
        """Advance celestial bodies along orbital mechanics paths and cycle fleet drones."""
        with self.lock:
            updated_systems: dict[str, StarSystem] = {}
            for sys_id, sys_obj in self.state.systems.items():
                updated_bodies = []
                for b in sys_obj.bodies:
                    new_angle = (b.current_angle + b.orbit_speed * delta_time) % (2 * math.pi)
                    updated_bodies.append(replace(b, current_angle=new_angle))
                updated_systems[sys_id] = StarSystem(
                    id=sys_obj.id,
                    name=sys_obj.name,
                    seed=sys_obj.seed,
                    x=sys_obj.x,
                    y=sys_obj.y,
                    spectral_type=sys_obj.spectral_type,
                    color=sys_obj.color,
                    security=sys_obj.security,
                    faction=sys_obj.faction,
                    bodies=tuple(updated_bodies),
                    connections=sys_obj.connections,
                    dominant_corp=sys_obj.dominant_corp,
                    modifiers=sys_obj.modifiers,
                )

            self.state = self._clone_state(systems=updated_systems)

    CONTRACT_REFRESH_COST = 120

    def refresh_contracts(self) -> tuple[bool, str]:
        """Reroll the mission board across every category for a broker fee."""
        with self.lock:
            if self.state.ship.credits < self.CONTRACT_REFRESH_COST:
                return False, (
                    f"Mission board refresh costs {self.CONTRACT_REFRESH_COST} cr; "
                    f"treasury has {self.state.ship.credits} cr."
                )
            categories = list(CONTRACT_CATEGORIES)
            self.rng.shuffle(categories)
            new_contracts = tuple(
                generate_contract(self.rng, category=category)
                for category in categories[:5]
            )
            log = (
                f"MISSION BOARD REFRESHED: five new contracts drawn for "
                f"{self.CONTRACT_REFRESH_COST} cr."
            )
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - self.CONTRACT_REFRESH_COST,
                active_contracts=new_contracts,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, log

    def claim_contract(self, contract_id: str) -> tuple[bool, str, dict[str, Any]]:
        """Claim rewards for a fulfilled contract and immediately draw a new assignment."""
        with self.lock:
            found = None
            for c in self.state.ship.active_contracts:
                if c.id == contract_id:
                    found = c
                    break

            if not found:
                return False, f"Contract '{contract_id}' not found in active assignments.", {}

            if not found.completed:
                return False, f"Contract '{found.title}' is not yet completed ({found.current_count}/{found.target_count}).", {}

            new_credits = self.state.ship.credits + found.reward_credits
            new_mastery, xp_logs = self._award_pilot_xp(found.reward_xp, self.state.ship.mastery)

            # Roll relic if tier specified
            relic = None
            new_relics = list(self.state.ship.relics)
            if found.reward_relic_tier:
                relic, _ = roll_relic_drop(self.rng, forced_tier=found.reward_relic_tier, current_system=self.current_system.name)
                if relic:
                    new_relics.append(relic)

            # Continuous Zeigarnik cycle: replace completed contract with a new task
            new_contract = generate_contract(self.rng, category=found.category)
            updated_contracts = tuple([c for c in self.state.ship.active_contracts if c.id != contract_id] + [new_contract])
            # Autonomy: draw alternative offers beside the auto-replacement so
            # the captain picks work instead of only receiving it. Free swap,
            # never punished (all-ages table, no decline cooldown).
            offer_categories = [c for c in CONTRACT_CATEGORIES if c != found.category]
            self.rng.shuffle(offer_categories)
            fresh_offers = [
                generate_contract(self.rng, category=cat)
                for cat in offer_categories[:CONTRACT_OFFER_COUNT]
            ]
            kept = [o for o in self.state.ship.contract_offers if o.id not in {c.id for c in updated_contracts}]
            contract_offers = tuple((kept + fresh_offers)[-CONTRACT_OFFERS_MAX:])

            relic_msg = f" Discovered Precursor Relic [{relic.name}] ({relic.rarity.upper()})!" if relic else ""
            log_entry = f"CONTRACT CLAIMED: [{found.title}] rewarded {found.reward_credits} cr and {found.reward_xp} XP.{relic_msg}"
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry] + xp_logs

            stats = dict(self.state.stats)
            stats["credits_earned"] += found.reward_credits
            stats["contracts_completed"] = stats.get("contracts_completed", 0) + 1
            stats["contract_offers_drawn"] = int(stats.get("contract_offers_drawn", 0)) + len(fresh_offers)

            new_hull, new_max_hull, new_shield, new_max_shield = self._apply_relic_stat_bonuses(
                self.state.ship.hull,
                self.state.ship.max_hull,
                self.state.ship.shield,
                self.state.ship.max_shield,
                [relic] if relic else [],
            )

            new_ship = self._clone_ship(
                hull=new_hull,
                max_hull=new_max_hull,
                shield=new_shield,
                max_shield=new_max_shield,
                credits=new_credits,
                mastery=new_mastery,
                relics=tuple(new_relics),
                active_contracts=updated_contracts,
                contract_offers=contract_offers,
                flight_log=tuple(new_log[-20:]),
            )

            completed_quest = CompletedQuest(
                id=found.id,
                title=found.title,
                kind=found.category,
                completed_at=time.time() * 1000.0,
                rewards={
                    "credits": found.reward_credits,
                    "xp": found.reward_xp,
                    "relic": relic.name if relic else "",
                },
            )
            new_completed = tuple((list(self.state.completed_quests) + [completed_quest])[-50:])
            self.state = self._clone_state(
                ship=new_ship, stats=stats, completed_quests=new_completed
            )

            return True, f"Claimed {found.title}: +{found.reward_credits} cr, +{found.reward_xp} XP.{relic_msg} New contract: [{new_contract.title}].", {
                "reward_credits": found.reward_credits,
                "reward_xp": found.reward_xp,
                "relic": relic.to_dict() if relic else None,
                "new_contract": new_contract.to_dict(),
                "replacement_options": [o.to_dict() for o in fresh_offers],
            }

    def swap_contract_offer(self, offer_id: str, drop_id: str) -> tuple[bool, str]:
        """Swap a pending contract offer into the active board, free and unpunished.

        The dropped active assignment is discarded without penalty; declining
        or swapping work is never punished at this table (all-ages ethics line).
        """
        with self.lock:
            offer_id = str(offer_id or "").strip()
            drop_id = str(drop_id or "").strip()
            offer = next((o for o in self.state.ship.contract_offers if o.id == offer_id), None)
            if offer is None:
                return False, f"Unknown contract offer '{offer_id}'. Claim a contract to draw offers."
            drop = next((c for c in self.state.ship.active_contracts if c.id == drop_id), None)
            if drop is None:
                return False, f"Unknown active contract '{drop_id}'. Nothing swapped."
            updated_contracts = tuple(
                [c for c in self.state.ship.active_contracts if c.id != drop_id] + [offer]
            )
            remaining_offers = tuple(o for o in self.state.ship.contract_offers if o.id != offer_id)
            log_entry = (
                f"CONTRACT SWAP: chose [{offer.title}] over [{drop.title}]. "
                "No fee, no standing loss."
            )
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            new_ship = self._clone_ship(
                active_contracts=updated_contracts,
                contract_offers=remaining_offers,
                flight_log=tuple(new_log[-20:]),
            )
            stats = dict(self.state.stats)
            stats["contract_swaps"] = int(stats.get("contract_swaps", 0)) + 1
            self.state = self._clone_state(ship=new_ship, stats=stats)
            return True, log_entry

    def unlock_talent(self, talent_id: str) -> tuple[bool, str]:
        """Unlock a Pilot Specialization Perk using available talent points."""
        with self.lock:
            talent = PILOT_TALENTS.get(talent_id)
            if not talent:
                return False, f"Unknown pilot talent '{talent_id}'. Available: {', '.join(PILOT_TALENTS.keys())}."

            mastery = self.state.ship.mastery
            if mastery.talent_points < 1:
                return False, "Insufficient talent points (0 available). Advance Pilot Mastery level first."

            if talent_id in mastery.specializations:
                return False, f"Perk '{talent['name']}' is already unlocked."

            missing = [req for req in talent.get("requires", ()) if req not in mastery.specializations]
            if missing:
                names = ", ".join(PILOT_TALENTS[r]["name"] for r in missing if r in PILOT_TALENTS)
                return False, f"Prerequisite perk(s) required: {names}."

            new_specs = tuple(list(mastery.specializations) + [talent_id])
            new_mastery = PilotMastery(
                level=mastery.level,
                xp=mastery.xp,
                next_level_xp=mastery.next_level_xp,
                talent_points=mastery.talent_points - 1,
                specializations=new_specs,
            )

            log_entry = f"★ SPECIALIZATION UNLOCKED: Pilot mastered [{talent['name']}]! {talent['description']}"
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            new_ship = self._clone_ship(
                mastery=new_mastery,
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(ship=new_ship)
            return True, f"Specialization unlocked: {talent['name']}."

    def _story_unmet_requirements(
        self,
        requirements: StoryRequirements | None,
        *,
        chapter: StoryChapter | None = None,
    ) -> list[str]:
        """List human-readable unmet gating conditions for a chapter or choice."""
        if requirements is None and chapter is None:
            return []
        story = self.state.ship.story
        unmet: list[str] = []
        if chapter is not None:
            if chapter.target_system_id and self.state.ship.current_system_id != chapter.target_system_id:
                unmet.append(
                    f"Travel to {chapter.target_system_id.title()} System "
                    f"(currently in {self.state.ship.current_system_id.title()})"
                )
        if requirements is None:
            return unmet
        for flag in requirements.required_flags:
            if not story.flags.get(flag):
                gloss = STORY_FLAG_GLOSSARY.get(flag, flag)
                unmet.append(f"Requires: {gloss}")
        for flag in requirements.forbidden_flags:
            if story.flags.get(flag):
                gloss = STORY_FLAG_GLOSSARY.get(flag, flag)
                unmet.append(f"Blocked by: {gloss}")
        for faction, minimum in requirements.min_reputation.items():
            if story.reputation.get(faction, 0) < minimum:
                unmet.append(f"Requires {faction.title()} reputation {minimum}+ (currently {story.reputation.get(faction, 0)})")
        for relic_id in requirements.required_relic_ids:
            if relic_id not in {r.id for r in self.state.ship.relics}:
                relic = STORY_RELICS.get(relic_id)
                name = relic.name if relic else relic_id
                unmet.append(f"Requires relic: {name}")
        if requirements.orbit_body_id:
            body = self._body_by_id(requirements.orbit_body_id)
            if self.state.ship.orbiting_body_id != requirements.orbit_body_id:
                body_name = body.name if body else requirements.orbit_body_id
                unmet.append(f"Establish orbit around {body_name}")
        return unmet

    def story_status(self) -> dict[str, Any]:
        """Objective snapshot of the narrative campaign for CLI, REST, and cockpit parity."""
        with self.lock:
            story = self.state.ship.story
            if story.completed or story.current_chapter_index >= len(story.chapters):
                ending = ENDING_VARIANTS.get(story.ending_id or "", ENDING_VARIANTS["ending_sentinel"])
                return {
                    "campaign_title": story.campaign_title,
                    "completed": True,
                    "ending": {"id": story.ending_id, "title": ending["title"], "epilogue": ending["epilogue"]},
                    "flags": dict(story.flags),
                    "reputation": dict(story.reputation),
                    "transmissions": len(story.transmission_log),
                }
            chapter = story.chapters[story.current_chapter_index]
            unmet = self._story_unmet_requirements(chapter.requirements, chapter=chapter)
            choices = []
            for choice in chapter.choices:
                choice_unmet = self._story_unmet_requirements(choice.requirements)
                choices.append({
                    "id": choice.id,
                    "text": choice.text,
                    "faction_alignment": choice.faction_alignment,
                    "cost_credits": choice.cost_credits,
                    "locked": bool(choice_unmet),
                    "lock_reason": choice.locked_text if choice.locked_text and choice_unmet else "; ".join(choice_unmet),
                })
            return {
                "campaign_title": story.campaign_title,
                "completed": False,
                "active_act": story.active_act,
                "chapter_id": chapter.id,
                "title": chapter.title,
                "objective": chapter.objective,
                "target_system_id": chapter.target_system_id,
                "unmet_requirements": unmet,
                "ready": not unmet,
                "choices": choices,
                "flags": dict(story.flags),
                "reputation": dict(story.reputation),
                "transmissions": len(story.transmission_log),
            }

    def make_story_choice(self, choice_id: str) -> tuple[bool, str]:
        """Resolve a branching story dilemma in the active campaign chapter."""
        with self.lock:
            story = self.state.ship.story
            if story.completed or story.current_chapter_index >= len(story.chapters):
                return False, "Campaign storyline is already complete."

            current_chapter = story.chapters[story.current_chapter_index]
            if current_chapter.completed:
                return False, f"Chapter '{current_chapter.title}' is already resolved."

            chapter_unmet = self._story_unmet_requirements(current_chapter.requirements, chapter=current_chapter)
            if chapter_unmet:
                return False, f"Objectives unmet for '{current_chapter.title}': {'; '.join(chapter_unmet)}."

            found_choice = None
            for ch in current_chapter.choices:
                if ch.id == choice_id:
                    found_choice = ch
                    break

            if not found_choice:
                avail = ", ".join(c.id for c in current_chapter.choices)
                return False, f"Choice '{choice_id}' not found. Available choices: {avail}."

            choice_unmet = self._story_unmet_requirements(found_choice.requirements)
            if choice_unmet:
                reason = found_choice.locked_text or "; ".join(choice_unmet)
                return False, f"Choice '{choice_id}' is locked. {reason}."

            cost = getattr(found_choice, "cost_credits", 0)
            if cost > 0 and self.state.ship.credits < cost:
                return False, f"Insufficient credits ({self.state.ship.credits} available, {cost} required)."

            new_credits = self.state.ship.credits + found_choice.reward_credits - cost
            new_relics = list(self.state.ship.relics)
            new_max_hull = self.state.ship.max_hull
            new_hull = self.state.ship.hull
            new_max_shield = self.state.ship.max_shield
            new_shield = self.state.ship.shield
            awarded_relic = None

            if found_choice.reward_relic_id and found_choice.reward_relic_id in STORY_RELICS:
                awarded_relic = STORY_RELICS[found_choice.reward_relic_id]
                existing_relic_ids = {r.id for r in new_relics}
                if awarded_relic.id not in existing_relic_ids:
                    new_relics.append(awarded_relic)
                    new_hull, new_max_hull, new_shield, new_max_shield = self._apply_relic_stat_bonuses(
                        new_hull,
                        new_max_hull,
                        new_shield,
                        new_max_shield,
                        [awarded_relic],
                    )

            new_rep = dict(story.reputation)
            align = found_choice.faction_alignment
            new_rep[align] = new_rep.get(align, 0) + 25

            standing_key = {
                "coalition": "sol_coalition",
                "syndicate": "vanguard_syndicate",
                "precursor": "precursor_watch",
            }.get(align)
            new_faction_standings = dict(self.state.ship.faction_standings)
            if standing_key:
                new_faction_standings[standing_key] = max(
                    -100, min(100, new_faction_standings.get(standing_key, 0) + 25)
                )

            updated_chapters = list(story.chapters)
            updated_chapters[story.current_chapter_index] = StoryChapter(
                chapter_index=current_chapter.chapter_index,
                title=current_chapter.title,
                target_system_id=current_chapter.target_system_id,
                objective=current_chapter.objective,
                transmission=current_chapter.transmission,
                choices=current_chapter.choices,
                completed=True,
                chosen_id=choice_id,
                requirements=current_chapter.requirements,
            )

            new_flags = dict(story.flags)
            for flag in found_choice.sets_flags:
                new_flags[flag] = True

            # Advance past the resolved chapter, skipping chapters whose flag gates can no longer open
            next_idx = story.current_chapter_index + 1
            while next_idx < len(updated_chapters):
                candidate = updated_chapters[next_idx]
                gates = candidate.requirements.required_flags if candidate.requirements else ()
                if gates and not all(new_flags.get(g) for g in gates):
                    updated_chapters[next_idx] = StoryChapter(
                        chapter_index=candidate.chapter_index,
                        title=candidate.title,
                        target_system_id=candidate.target_system_id,
                        objective=candidate.objective,
                        transmission=candidate.transmission,
                        choices=candidate.choices,
                        completed=candidate.completed,
                        chosen_id=candidate.chosen_id,
                        requirements=candidate.requirements,
                        skipped=True,
                    )
                    next_idx += 1
                else:
                    break

            is_campaign_done = next_idx >= len(updated_chapters)
            new_transmissions = list(story.transmission_log)
            if found_choice.follow_up is not None:
                new_transmissions.append(found_choice.follow_up)

            ending_id = None
            if not is_campaign_done:
                next_ch = updated_chapters[next_idx]
                new_transmissions.append(next_ch.transmission)
            else:
                ending_id = resolve_story_ending(
                    StoryState(
                        campaign_title=story.campaign_title,
                        current_chapter_index=next_idx,
                        chapters=tuple(updated_chapters),
                        transmission_log=(),
                        reputation=new_rep,
                        completed=True,
                        flags=new_flags,
                    )
                )
                new_transmissions.append(ending_transmission(ending_id))

            new_story = StoryState(
                campaign_title=story.campaign_title,
                current_chapter_index=next_idx,
                chapters=tuple(updated_chapters),
                transmission_log=tuple(new_transmissions),
                reputation=new_rep,
                completed=is_campaign_done,
                flags=new_flags,
                ending_id=ending_id,
            )

            relic_msg = f" Acquired unique relic [{awarded_relic.name}]!" if awarded_relic else ""
            log_entry = f"STORY DECISION: [{found_choice.text}] resolved. +{found_choice.reward_credits} cr.{relic_msg}"
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            celebration_crew, morale_log = apply_morale_event(self.state.ship.crew, 6.0, "campaign milestone celebrated")
            if morale_log:
                new_log.append(morale_log)

            new_ship = self._clone_ship(
                hull=new_hull,
                max_hull=new_max_hull,
                shield=new_shield,
                max_shield=new_max_shield,
                credits=new_credits,
                relics=tuple(new_relics),
                story=new_story,
                faction_standings=new_faction_standings,
                crew=celebration_crew,
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(ship=new_ship)
            msg = f"Decision resolved: {found_choice.outcome_text}{relic_msg}"
            if is_campaign_done:
                variant = ENDING_VARIANTS.get(ending_id or "", ENDING_VARIANTS["ending_sentinel"])
                msg += f" CAMPAIGN FINALE: {variant['title']}!"

            return True, msg

    def skip_tutorial(self) -> tuple[bool, str]:
        """Skip Cadet Flight Academy and unlock unrestricted operational status."""
        with self.lock:
            cur = self.state.ship.tutorial
            new_tut = TutorialState(
                active=False,
                current_step_index=cur.current_step_index,
                steps=cur.steps,
                completed=False,
                skipped=True,
            )
            new_log = list(self.state.ship.flight_log[-19:]) + ["ACADEMY: Cadet Flight Academy skipped by commander."]
            self.state = self._clone_state(ship=self._clone_ship(tutorial=new_tut, flight_log=tuple(new_log[-20:])))
            return True, "Cadet Flight Academy skipped. Full operational control active."

    def reset_tutorial(self) -> tuple[bool, str]:
        """Reset Cadet Flight Academy to step 1 for revision or retraining."""
        with self.lock:
            new_tut = generate_initial_tutorial()
            new_log = list(self.state.ship.flight_log[-19:]) + ["ACADEMY: Cadet Flight Academy restarted."]
            self.state = self._clone_state(ship=self._clone_ship(tutorial=new_tut, flight_log=tuple(new_log[-20:])))
            return True, "Cadet Flight Academy reset to Step 1."

    @property
    def current_chassis_id(self) -> str:
        """Id of the chassis matching the ship's commissioned class (falls back to the class name)."""
        return next(
            (c.id for c in CATALOG_CHASSIS if c.ship_class == self.state.ship.ship_class),
            self.state.ship.ship_class,
        )

    def get_status_snapshot(self, include_static: bool = True) -> dict[str, Any]:
        """Produce a JSON serializable telemetry snapshot for the HUD.

        `include_static=False` leaves out the code-constant catalogs (see `static_catalogs`),
        for clients that fetched them once from `/api/catalogs`.
        """
        with self.lock:
            cur_sys = self.current_system
            orb_body = self.docked_body
            market_quotes = []
            if orb_body and orb_body.station_dockable:
                quotes = [
                    calculate_dynamic_market_quote(
                        cur_sys,
                        orb_body,
                        c,
                        self.state.economy,
                        faction_standing=self.state.ship.faction_standings.get(
                            get_faction_id_from_name(cur_sys.faction), 0
                        ),
                        trade_pact=self.trade_pact_active(
                            get_faction_id_from_name(cur_sys.faction)
                        ),
                    )
                    for c in CANONICAL_COMMODITIES
                ]
                market_quotes = [
                    {
                        "commodity_id": q.commodity_id,
                        "name": q.name,
                        "category": q.category,
                        "buy_price": q.buy_price,
                        "sell_price": q.sell_price,
                        "supply": q.supply,
                        "demand": q.demand,
                        "max_buy": self.max_trade_quantity(q.commodity_id, is_buy=True),
                    }
                    for q in quotes
                ]
            ship_cargo = self.state.ship.cargo
            cargo_avg_cost = {
                cid: cost // ship_cargo[cid]
                for cid, cost in self.state.ship.cargo_cost.items()
                if ship_cargo.get(cid, 0) > 0
            }

            equipment_snapshot = self._combined_equipment()
            salvage_site = (
                derive_derelict(cur_sys.id, cur_sys.seed, orb_body)
                if orb_body and not orb_body.salvage_claimed
                else None
            )
            scoop = None
            if orb_body:
                profile = scoop_profile(orb_body)
                if profile:
                    reserve = scoop_reserve(orb_body)
                    tapped, recharge_tick = recharge_volatile_reserve(
                        orb_body.volatile_tapped,
                        orb_body.volatile_recharge_tick,
                        self.state.time.tick,
                    )
                    scoop = {
                        **profile,
                        "available": (
                            self.state.ship.fuel < self.state.ship.max_fuel
                            and tapped < reserve
                        ),
                        "tapped": tapped,
                        "reserve": reserve,
                        "next_tap_in": (
                            max(0, recharge_tick - self.state.time.tick)
                            if tapped > 0
                            else 0
                        ),
                    }
            survey_scanned = sum(1 for b in cur_sys.bodies if b.scan_completed)
            snapshot = {
                "ship": self.state.ship.to_dict(),
                "current_system": cur_sys.to_dict(),
                "orbiting_body": orb_body.to_dict() if orb_body else None,
                "outpost_options": (
                    [t.id for t in OUTPOST_TYPES if can_build_on(orb_body, t)] if orb_body else []
                ),
                "outpost_body_occupied": bool(
                    orb_body and any(o.body_id == orb_body.id for o in self.state.outposts)
                ),
                "salvage_site": salvage_site.to_dict() if salvage_site else None,
                "scoop": scoop,
                "survey": {
                    "system_id": cur_sys.id,
                    "scanned": survey_scanned,
                    "total": len(cur_sys.bodies),
                    "complete": survey_scanned >= len(cur_sys.bodies),
                },
                "visited_systems": list(self.state.visited_systems),
                "active_anomaly": self.state.active_anomaly.to_dict() if self.state.active_anomaly else None,
                "active_combat": self.state.active_combat.to_dict() if self.state.active_combat else None,
                "active_pirate": self.state.active_pirate.to_dict() if self.state.active_pirate else None,
                "active_customs": self.state.active_customs.to_dict() if self.state.active_customs else None,
                "pending_decision": self.state.pending_decision.to_dict() if self.state.pending_decision else None,
                "decision_history": list(self.state.decision_history),
                "time": self.state.time.to_dict(),
                "stats": dict(self.state.stats),
                "codex": build_codex_report(self.state),
                "relic_set_bonuses": relic_set_bonuses(self.state.ship.relics),
                "equipment_bonuses": equipment_snapshot,
                "map_modifiers": system_modifier_summary(cur_sys),
                "map_effects": self._map_effects(cur_sys),
                "reactor": {
                    "heat": round(self.state.ship.reactor.heat, 1),
                    "max_heat": round(reactor_heat_capacity(self.state.ship.reactor, equipment_snapshot), 1),
                    "heat_pct": round(
                        min(100.0, self.state.ship.reactor.heat / max(1.0, reactor_heat_capacity(self.state.ship.reactor, equipment_snapshot)) * 100.0),
                        1,
                    ),
                    "integrity": round(self.state.ship.reactor.integrity, 1),
                    "max_integrity": round(self.state.ship.reactor.max_integrity, 1),
                    "mode": self.state.ship.reactor.mode,
                    "mode_name": get_reactor_mode(self.state.ship.reactor.mode)["name"],
                    "surge_ticks": int(self.state.ship.reactor.surge_ticks),
                    "surge_bonus": round(float(self.state.ship.reactor.surge_bonus), 3),
                    "efficiency": round(reactor_output_efficiency(self.state.ship.reactor, float(equipment_snapshot.get("reactor_output", 0.0))), 3),
                    "cooling": round(reactor_cooling_rate(self.state.ship.reactor, equipment_snapshot, float(self._map_effects(cur_sys)["cooling_bonus"])), 2),
                    "modes": {mid: dict(profile) for mid, profile in REACTOR_MODES.items()},
                },
                "character": self.state.character.to_dict(),
                "character_creation": {
                    "skill_base": STARTING_SKILL_BASE,
                    "skill_points": STARTING_SKILL_POINTS,
                    "max_skill": 10,
                    "skills": list(SKILL_CATALOG),
                },
                "character_abilities": {
                    aid: {
                        **info,
                        "unlocked": aid in self.state.character.abilities,
                        "cooldown": int(self.state.character.ability_cooldowns.get(aid, 0)),
                        "cooldown_total": int(info["cooldown"]),
                    }
                    for aid, info in ABILITY_CATALOG.items()
                },
                "research": {
                    **self.state.research.to_dict(),
                    "bonuses": self._research_bonuses(),
                    "active_project": (get_research_project(self.state.research.active_project_id).to_dict() if self.state.research.active_project_id and get_research_project(self.state.research.active_project_id) else None),
                    "queued": [
                        project.to_dict()
                        for project in (
                            get_research_project(pid)
                            for pid in self.state.research.queue
                        )
                        if project is not None
                    ],
                    "research_pacts": list(self.state.ship.research_pacts),
                    "active_research_pacts": sum(
                        1
                        for faction_id in self.state.ship.research_pacts
                        if self.research_pact_active(faction_id)
                    ),
                    "pact_bonus": round(self.research_pact_multiplier() - 1.0, 2),
                    "available": [p.to_dict() for p in available_projects(self.state.research.completed, self.state.research.active_project_id)],
                    "catalog": [p.to_dict() for p in RESEARCH_PROJECTS],
                },
                "outposts": [self._outpost_payload(o) for o in self.state.outposts],
                "megastructure": self.get_megastructure_report(),
                "faction_leaders": [self._leader_payload(leader) for leader in self.state.faction_leaders],
                "wars": [war.to_dict() for war in self.state.wars],
                "faction_economies": [e.to_dict() for e in self.state.faction_economies],
                "trade_links": [t.to_dict() for t in self.state.trade_links],
                "galactic_politics": self.galactic_politics(),
                "eliminated_factions": list(self.state.eliminated_factions),
                "crew": [c.to_dict() for c in self.state.ship.crew],
                "crew_bonuses": self._crew_bonuses(),
                "away_report": self.get_away_report(),
                "surface_report": self.get_surface_report(),
                "primary_weapon": self.state.ship.primary_weapon,
                "trade_automation": self.state.trade_automation.to_dict(),
                "quantum_automation": self.state.quantum_automation.to_dict(),
                "fleet_manager": {
                    "ships": [
                        self._fleet_ship_payload(ship)
                        for ship in self.state.ship.fleet_ships
                    ],
                    "catalog": ESCORT_CATALOG,
                    "total_damage": fleet_damage(self.state.ship.fleet_ships),
                    "local_damage": fleet_damage(fleet_ships_in_system(
                        self.state.ship.fleet_ships, self.state.ship.current_system_id
                    )),
                    "evasion_bonus": round(fleet_evasion_bonus(self.state.ship.fleet_ships), 3),
                    "local_evasion_bonus": round(fleet_evasion_bonus(fleet_ships_in_system(
                        self.state.ship.fleet_ships, self.state.ship.current_system_id
                    )), 3),
                    "patrol_sweep_ticks": PATROL_SWEEP_TICKS,
                    "upkeep_per_month": fleet_upkeep(self.state.ship.fleet_ships),
                    "battle_stance": self.state.ship.battle_stance,
                },
                "ship_mods": {
                    "slots": list(SHIP_MOD_SLOTS),
                    "slot_labels": {slot: slot_label(slot) for slot in SHIP_MOD_SLOTS},
                    "slot_codes": {slot: slot_code(slot) for slot in SHIP_MOD_SLOTS},
                    "installed": dict(self.state.ship.ship_mods),
                    "installed_details": {
                        slot: get_ship_mod(mod_id).to_dict() if get_ship_mod(mod_id) else {"id": mod_id}
                        for slot, mod_id in self.state.ship.ship_mods.items()
                    },
                    "catalog": [mod.to_dict() for mod in CATALOG_SHIP_MODS],
                    "available": [mod.to_dict() for mod in get_available_ship_mods(self.state.ship.ship_mods)],
                    "bonuses": calculate_ship_mod_bonuses(self.state.ship.ship_mods),
                },
                "market_quotes": market_quotes,
                "cargo_avg_cost": cargo_avg_cost,
                "factions": {
                    fid: {
                        **f.to_dict(),
                        "standing": self.state.ship.faction_standings.get(fid, 0),
                        "standing_tier": get_faction_standing_tier(self.state.ship.faction_standings.get(fid, 0))[0],
                        "active_perk": get_faction_standing_tier(self.state.ship.faction_standings.get(fid, 0))[1],
                    }
                    for fid, f in CANONICAL_FACTIONS.items()
                },
                "corporations": {
                    cid: {
                        **c.to_dict(),
                        "standing": self.state.ship.corp_standings.get(cid, 0),
                    }
                    for cid, c in CANONICAL_CORPORATIONS.items()
                },
                "economy": self.state.economy.to_dict(),
                "inventory_manifest": get_inventory_manifest(self.state.ship.cargo),
                "trade_routes": get_galactic_trade_routes(self.state.systems, self.state.economy),
                "available_chassis": [c.to_dict() for c in get_available_chassis(self.current_chassis_id)],
                "ai_captains": [c.to_dict() for c in self.state.ai_captains],
                "depots": [
                    {**d.to_dict(), "used_volume": calculate_cargo_volume(d.cargo)}
                    for d in self.state.depots
                ],
                "messages": [m.to_dict() for m in self.state.messages],
                "events": [e.to_dict() for e in self.state.events],
                "undismissed_events": [e.to_dict() for e in self.state.events if not e.dismissed],
                "travel": self.state.ship.travel.to_dict() if self.state.ship.travel else None,
                "void": self.void_status(),
                "settings": {
                    "decision_cadence": self.decision_cadence,
                    "decisions_ready_in": self.decisions_ready_in(),
                    "decision_cadences": sorted(self.DECISION_CADENCE),
                },
                "story_status": self.story_status(),
                "cash_flow": self.cash_flow(),
                "allies": list(self.state.ship.allies),
                "quests": self.get_quests(),
                "quests_completed": [q.to_dict() for q in self.state.completed_quests],
                "drydock": self.drydock_quote(),
                "fleet_stats": [
                    {
                        **d.to_dict(),
                        "kind": "mercenary" if d.drone_type == "mercenary" else "fleet",
                        "yield_rate": round(d.efficiency * (0.5 + d.integrity / 200.0), 2),
                    }
                    for d in self.state.ship.fleet_drones
                ],
            }
            if include_static:
                snapshot.update(copy.deepcopy(static_catalogs()))
            return snapshot

    # Smallest pledge that moves a war, and the most one pledge can move it.
    WAR_SUPPORT_MIN_CREDITS = 100
    WAR_SUPPORT_MAX_SHIFT = 6.0
    WAR_BOND_MAX_PER_COMMANDER = 6000

    def _resolve_war_bonds(
        self, wars: tuple[WarState, ...]
    ) -> tuple[tuple[WarState, ...], int, list[str]]:
        """Settle pledged war bonds once a war ends; no double payouts."""
        credits = 0
        logs: list[str] = []
        updated: list[WarState] = []
        for war in wars:
            if war.active or war.bonds_resolved:
                updated.append(war)
                continue
            winner = None
            if war.war_score >= 25:
                winner = war.attacker_id
            elif war.war_score <= -25:
                winner = war.defender_id
            for faction_id, pledged in war.support.items():
                pledged = max(0, int(pledged))
                if pledged <= 0:
                    continue
                faction = CANONICAL_FACTIONS.get(faction_id)
                name = faction.name if faction else faction_id
                if winner is None:
                    payout = int(pledged * 0.8)
                elif faction_id == winner:
                    payout = int(pledged * 1.5)
                else:
                    payout = 0
                credits += payout
                if payout:
                    logs.append(
                        f"WAR BONDS: {name} paid {payout} cr on the {war.id} settlement "
                        f"(pledged {pledged})."
                    )
                else:
                    logs.append(
                        f"WAR BONDS LOST: {name} pledge of {pledged} cr on {war.id}."
                    )
            updated.append(replace(war, bonds_resolved=True))
        return tuple(updated), credits, logs

    def support_war(self, war_id: str, faction_id: str, credits: int) -> tuple[bool, str]:
        """Pledge credits to one side of an active war: shifts its score and your standings."""
        with self.lock:
            war = next((w for w in self.state.wars if w.id == war_id), None)
            if war is None or not war.active:
                return False, f"No active war '{war_id}'."
            if faction_id not in (war.attacker_id, war.defender_id):
                return False, f"{faction_id} is not a party to {war_id}."
            if credits < self.WAR_SUPPORT_MIN_CREDITS:
                return False, f"War pledges start at {self.WAR_SUPPORT_MIN_CREDITS} cr."
            ship = self.state.ship
            if ship.credits < credits:
                return False, f"Insufficient credits: {credits} cr pledged, {ship.credits} cr available."
            already = int(war.support.get(faction_id, 0))
            if already + credits > self.WAR_BOND_MAX_PER_COMMANDER:
                return False, (
                    f"Bond subscriptions are capped at {self.WAR_BOND_MAX_PER_COMMANDER} cr "
                    f"per commander per war (already pledged {already} cr to this side)."
                )
            shift = min(self.WAR_SUPPORT_MAX_SHIFT, credits / 400.0)
            score = war.war_score + (shift if faction_id == war.attacker_id else -shift)
            enemy_id = war.defender_id if faction_id == war.attacker_id else war.attacker_id
            gain = min(10, credits // 300)
            standings = dict(ship.faction_standings)
            standings[faction_id] = min(100, standings.get(faction_id, 0) + gain)
            standings[enemy_id] = max(-100, standings.get(enemy_id, 0) - max(1, gain // 2))
            support = dict(war.support)
            support[faction_id] = support.get(faction_id, 0) + credits
            new_war = replace(war, war_score=round(score, 2), support=support)
            side = CANONICAL_FACTIONS[faction_id].name if faction_id in CANONICAL_FACTIONS else faction_id
            msg = (
                f"War pledge: {credits} cr to {side} (front shifts {shift:.1f}; "
                f"standing +{gain}). Bonds pay 1.5x on victory, 0.8x on stalemate."
            )
            self.state = self._clone_state(
                wars=tuple(new_war if w.id == war_id else w for w in self.state.wars),
                ship=self._clone_ship(
                    credits=ship.credits - credits,
                    faction_standings=standings,
                    flight_log=tuple(list(ship.flight_log[-19:]) + [msg]),
                ),
            )
            return True, msg

    # A captain can only petition: the envoy fee is paid when the other side agrees.
    CEASEFIRE_ENVOY_COST = 500
    NON_AGGRESSION_TICKS = 90

    def _ceasefire_chance(self, faction_id: str, war: WarState) -> float:
        """Odds a petition is accepted: standing, diplomacy skill and how the war is going."""
        standing = self.state.ship.faction_standings.get(faction_id, 0)
        skill = self._skill("diplomacy")
        # Positive war score favours the attacker, so this is the asked side's advantage.
        advantage = war.war_score if faction_id == war.attacker_id else -war.war_score
        # A faction that is winning has little reason to talk; a losing one listens.
        pressure = max(-0.20, min(0.20, -advantage / 100.0))
        chance = 0.15 + (standing + 100) / 200.0 * 0.45 + skill * 0.25 + pressure
        return max(0.05, min(0.90, chance))

    def galactic_politics(self) -> dict[str, Any]:
        """Territory, borders and war fronts for the strategic map and the factions panel."""
        with self.lock:
            systems = self.state.systems
            colors = {f.name: f.primary_color for f in CANONICAL_FACTIONS.values()}
            ids = {f.name: fid for fid, f in CANONICAL_FACTIONS.items()}
            active = [w for w in self.state.wars if w.active]
            economies = {e.faction_id: e for e in self.state.faction_economies}
            enemies: dict[str, set[str]] = {}
            for w in active:
                enemies.setdefault(w.attacker_id, set()).add(w.defender_id)
                enemies.setdefault(w.defender_id, set()).add(w.attacker_id)

            def owner_id(sid: str) -> str:
                return ids.get(systems[sid].faction, systems[sid].faction)

            system_view = {}
            for sid, system in systems.items():
                fid = owner_id(sid)
                neighbours = [n for n in system.connections if n in systems]
                system_view[sid] = {
                    "owner_id": fid,
                    "owner": system.faction,
                    "color": colors.get(system.faction, "#7f8a99"),
                    "border": any(systems[n].faction != system.faction for n in neighbours),
                    "front": any(owner_id(n) in enemies.get(fid, set()) for n in neighbours),
                }
            factions = [
                {
                    "id": fid,
                    "name": f.name,
                    "color": f.primary_color,
                    "systems": sum(1 for s in systems.values() if s.faction == f.name),
                    "strength": round(faction_strength(fid, systems), 1),
                    "at_war_with": sorted(enemies.get(fid, set())),
                    "trade_partner_names": trade_partner_names(fid, self.state.trade_links),
                    **(
                        economies[fid].to_dict()
                        if fid in economies
                        else {
                            "treasury": 0,
                            "net_income": 0,
                            "population": 0,
                            "worlds": 0,
                            "tech_level": 1,
                            "stability": 0.0,
                            "war_burden": 0.0,
                        }
                    ),
                }
                for fid, f in CANONICAL_FACTIONS.items()
                if fid not in self.state.eliminated_factions
            ]
            factions.sort(key=lambda f: -f["strength"])
            war_view = []
            for w in active:
                pair = {w.attacker_id, w.defender_id}
                fronts = sorted({
                    tuple(sorted((a, b)))
                    for a in systems for b in systems[a].connections
                    if b in systems and {owner_id(a), owner_id(b)} == pair
                })
                war_view.append({
                    **w.to_dict(),
                    "attacker": CANONICAL_FACTIONS[w.attacker_id].name if w.attacker_id in CANONICAL_FACTIONS else w.attacker_id,
                    "defender": CANONICAL_FACTIONS[w.defender_id].name if w.defender_id in CANONICAL_FACTIONS else w.defender_id,
                    "fronts": [list(f) for f in fronts],
                    # The player is a privateer, not a power: only their own polity's wars
                    # can be petitioned, and only a third-party war is pure politics.
                    "player_party": "sol_coalition" in (w.attacker_id, w.defender_id),
                })
            return {
                "systems": system_view,
                "factions": factions,
                "wars": war_view,
                "trade_links": [t.to_dict() for t in self.state.trade_links],
            }

    def get_quests(self) -> list[dict[str, Any]]:
        """Return a unified quest panel view of the story chapter and active contracts."""
        quests: list[dict[str, Any]] = []
        story = self.state.ship.story
        if not story.completed and story.current_chapter_index < len(story.chapters):
            chapter = story.chapters[story.current_chapter_index]
            quests.append({
                "id": f"story_{chapter.chapter_index}",
                "kind": "story",
                "title": chapter.title,
                "description": chapter.objective,
                "target": chapter.target_system_id,
                "progress": 0,
                "target_count": 1,
                "completed": chapter.completed,
                "reward": "Campaign progression",
            })
        for contract in self.state.ship.active_contracts:
            quests.append({
                "id": contract.id,
                "kind": "contract",
                "title": contract.title,
                "description": contract.description,
                "target": "",
                "progress": contract.current_count,
                "target_count": contract.target_count,
                "completed": contract.completed,
                "reward": f"{contract.reward_credits} cr / {contract.reward_xp} XP",
            })
        return quests

    def _find_ai_captain(self, captain_id: str) -> AICaptain | None:
        return next((c for c in self.state.ai_captains if c.id == captain_id), None)

    def _replace_ai_captain(self, captain: AICaptain) -> tuple[AICaptain, ...]:
        return tuple(captain if c.id == captain.id else c for c in self.state.ai_captains)

    def interact_ai(
        self,
        captain_id: str,
        action: str,
        commodity_id: str | None = None,
        quantity: int = 1,
    ) -> tuple[bool, str]:
        """Hail, trade with, hire, or ally with an autonomous captain."""
        with self.lock:
            captain = self._find_ai_captain(captain_id)
            if not captain:
                return False, f"Unknown AI captain '{captain_id}'."
            action = action.lower()
            if action == "hail":
                updated = replace(captain, trust=min(100, captain.trust + 2), standing=min(100, captain.standing + 1))
                self.state = self._clone_state(ai_captains=self._replace_ai_captain(updated))
                return True, f"{captain.name}: \"{captain_hail(captain)}\" {captain.description} Quantum link trust increased."
            if action in ("buy", "sell"):
                if not commodity_id or commodity_id not in COMMODITY_MAP:
                    return False, "A valid commodity is required for captain trade."
                quantity = max(1, int(quantity))
                price = COMMODITY_MAP[commodity_id].base_price
                cargo = dict(self.state.ship.cargo)
                captain_cargo = dict(captain.cargo)
                if action == "buy":
                    available = captain_cargo.get(commodity_id, 0)
                    if available < quantity:
                        return False, f"{captain.name} has only {available} units of {commodity_id}."
                    cost = int(price * 1.10) * quantity
                    if self.state.ship.credits < cost:
                        return False, f"Insufficient credits: {cost} cr required."
                    incoming = calculate_cargo_volume({commodity_id: quantity})
                    if calculate_cargo_volume(cargo) + incoming > self.state.ship.cargo_capacity:
                        return False, "Cargo hold has insufficient free volume for this purchase."
                    captain_cargo[commodity_id] = available - quantity
                    cargo[commodity_id] = cargo.get(commodity_id, 0) + quantity
                    new_credits = self.state.ship.credits - cost
                    updated_captain = replace(captain, cargo=captain_cargo, credits=captain.credits + cost, trust=min(100, captain.trust + 1))
                    message = f"Purchased {quantity}x {commodity_id} from {captain.name} for {cost} cr."
                else:
                    available = cargo.get(commodity_id, 0)
                    if available < quantity:
                        return False, f"You have only {available} units of {commodity_id}."
                    revenue = int(price * 0.90) * quantity
                    cargo[commodity_id] = available - quantity
                    captain_cargo[commodity_id] = captain_cargo.get(commodity_id, 0) + quantity
                    new_credits = self.state.ship.credits + revenue
                    updated_captain = replace(captain, cargo=captain_cargo, credits=max(0, captain.credits - revenue), trust=min(100, captain.trust + 1))
                    message = f"Sold {quantity}x {commodity_id} to {captain.name} for {revenue} cr."
                new_ship = self._clone_ship(credits=new_credits, cargo=cargo)
                self.state = self._clone_state(ship=new_ship, ai_captains=self._replace_ai_captain(updated_captain))
                return True, message
            if action == "hire":
                if captain.archetype != "mercenary":
                    return False, f"{captain.name} is not a mercenary contractor."
                if captain.hired:
                    return False, f"{captain.name} is already under contract."
                cost = 2500
                if self.state.ship.credits < cost:
                    return False, f"Insufficient credits: {cost} cr required to hire {captain.name}."
                drone = FleetDrone(
                    id=f"merc_{captain.id}",
                    name=captain.name,
                    drone_type="mercenary",
                    assigned_system_id=self.state.ship.current_system_id,
                    status="idle",
                    efficiency=1.0,
                    integrity=100,
                    specialty="assault",
                )
                new_ship = self._clone_ship(
                    credits=self.state.ship.credits - cost,
                    fleet_drones=self.state.ship.fleet_drones + (drone,),
                )
                updated = replace(captain, hired=True, trust=min(100, captain.trust + 10))
                self.state = self._clone_state(ship=new_ship, ai_captains=self._replace_ai_captain(updated))
                return True, f"{captain.name} joined your fleet as a mercenary (+14 combat damage)."
            if action == "ally":
                if captain.ally or captain.id in self.state.ship.allies:
                    return False, f"{captain.name} is already an ally."
                if captain.trust < 50:
                    return False, f"{captain.name} requires 50 trust before an alliance (current: {captain.trust})."
                updated = replace(captain, ally=True, trust=100)
                new_ship = self._clone_ship(allies=self.state.ship.allies + (captain.id,))
                self.state = self._clone_state(ship=new_ship, ai_captains=self._replace_ai_captain(updated))
                return True, f"Alliance formed with {captain.name}. +5% trade margin and fleet support."
            return False, "Unknown AI action. Use hail, buy, sell, hire, or ally."

    def send_quantum_message(self, recipient: str, subject: str, body: str) -> tuple[bool, str]:
        """Send an intergalactic quantum-encrypted message."""
        with self.lock:
            if not recipient.strip() or not subject.strip() or not body.strip():
                return False, "Recipient, subject, and message body are required."
            message = QuantumMessage(
                id=f"msg_{self.state.time.tick}_{len(self.state.messages) + 1}",
                sender=self.state.ship.commander_name,
                recipient=recipient.strip(),
                subject=subject.strip()[:120],
                body=body.strip()[:2000],
                tick=self.state.time.tick,
            )
            self.state = self._clone_state(messages=self.state.messages + (message,))
            return True, f"Quantum message sent to {message.recipient}."

    def mark_message_read(self, message_id: str) -> tuple[bool, str]:
        with self.lock:
            message = next((m for m in self.state.messages if m.id == message_id), None)
            if not message:
                return False, f"Unknown message '{message_id}'."
            updated = tuple(replace(m, read=True) if m.id == message_id else m for m in self.state.messages)
            self.state = self._clone_state(messages=updated)
            return True, f"Message '{message.subject}' marked as read."

    def _depot_for_current_system(self) -> Depot | None:
        return next((d for d in self.state.depots if d.system_id == self.state.ship.current_system_id), None)

    def _shipyard_outpost(self) -> Outpost | None:
        """A player shipyard in the current system can service ships without a station dock."""
        return next(
            (
                outpost
                for outpost in self.state.outposts
                if outpost.outpost_type == "shipyard"
                and outpost.system_id == self.state.ship.current_system_id
            ),
            None,
        )

    def _require_service_dock(self) -> tuple[bool, str]:
        if self.state.active_combat is not None:
            return False, "Shipyard services are unavailable during combat."
        body = self.docked_body
        if body and body.station_dockable:
            return True, ""
        shipyard = self._shipyard_outpost()
        if shipyard is not None:
            return True, ""
        return (
            False,
            "Dock at a station or build a Frontier Shipyard in this system for hull services.",
        )

    def _require_docked(self) -> tuple[bool, str]:
        if self.state.active_combat is not None:
            return False, "Depot operations are unavailable during combat."
        body = self.docked_body
        if not body or not body.station_dockable:
            return False, "Dock at an orbital station or colony to access depot services."
        return True, ""

    def deposit_cargo(self, item_id: str, quantity: int = 1) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_docked()
            if not ok:
                return False, msg
            quantity = int(quantity)
            if quantity <= 0:
                return False, "Deposit quantity must be positive."
            depot = self._depot_for_current_system()
            if not depot:
                return False, "No depot is registered in this system."
            cargo = dict(self.state.ship.cargo)
            if cargo.get(item_id, 0) < quantity:
                return False, f"Cargo hold contains only {cargo.get(item_id, 0)} units of {item_id}."
            incoming = calculate_cargo_volume({item_id: quantity})
            if calculate_cargo_volume(depot.cargo) + incoming > depot.capacity:
                return False, "Depot capacity exceeded."
            cargo[item_id] -= quantity
            if cargo[item_id] <= 0:
                cargo.pop(item_id, None)
            depot_cargo = dict(depot.cargo)
            depot_cargo[item_id] = depot_cargo.get(item_id, 0) + quantity
            updated_depot = replace(depot, cargo=depot_cargo)
            depots = tuple(updated_depot if d.id == depot.id else d for d in self.state.depots)
            self.state = self._clone_state(ship=self._clone_ship(cargo=cargo), depots=depots)
            return True, f"Deposited {quantity}x {item_id} into {depot.name}."

    def withdraw_cargo(self, item_id: str, quantity: int = 1) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_docked()
            if not ok:
                return False, msg
            quantity = int(quantity)
            if quantity <= 0:
                return False, "Withdraw quantity must be positive."
            depot = self._depot_for_current_system()
            if not depot:
                return False, "No depot is registered in this system."
            if depot.cargo.get(item_id, 0) < quantity:
                return False, f"Depot contains only {depot.cargo.get(item_id, 0)} units of {item_id}."
            cargo = dict(self.state.ship.cargo)
            incoming = calculate_cargo_volume({item_id: quantity})
            if calculate_cargo_volume(cargo) + incoming > self.state.ship.cargo_capacity:
                return False, "Cargo hold has insufficient free volume."
            depot_cargo = dict(depot.cargo)
            depot_cargo[item_id] -= quantity
            if depot_cargo[item_id] <= 0:
                depot_cargo.pop(item_id, None)
            cargo[item_id] = cargo.get(item_id, 0) + quantity
            updated_depot = replace(depot, cargo=depot_cargo)
            depots = tuple(updated_depot if d.id == depot.id else d for d in self.state.depots)
            self.state = self._clone_state(ship=self._clone_ship(cargo=cargo), depots=depots)
            return True, f"Withdrew {quantity}x {item_id} from {depot.name}."

    def sell_from_depot(self, item_id: str, quantity: int = 1) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_docked()
            if not ok:
                return False, msg
            quantity = int(quantity)
            if quantity <= 0:
                return False, "Sale quantity must be positive."
            depot = self._depot_for_current_system()
            if not depot:
                return False, "No depot is registered in this system."
            if depot.cargo.get(item_id, 0) < quantity:
                return False, f"Depot contains only {depot.cargo.get(item_id, 0)} units of {item_id}."
            body = self.docked_body
            if not body or body.market_archetype == "none":
                return False, "Current orbital location has no commercial market exchange."
            comm = COMMODITY_MAP.get(item_id)
            if not comm:
                return False, f"Unknown commodity '{item_id}'."
            sys_faction_id = get_faction_id_from_name(self.current_system.faction)
            standing = self.state.ship.faction_standings.get(sys_faction_id, 0)
            quote = calculate_dynamic_market_quote(
                self.current_system,
                body,
                comm,
                self.state.economy,
                faction_standing=standing,
                trade_pact=self.trade_pact_active(sys_faction_id),
            )
            passives = calculate_passive_multipliers(self.state.ship)
            equipment = self._combined_equipment()
            map_trade_bonus = float(self._map_effects()["trade_margin"])
            faction_perks = get_faction_service_perks(sys_faction_id, standing)
            margin_mult = passives.get("trade_margin", 1.0) * (
                1.0
                + equipment["trade_margin"]
                + map_trade_bonus
                + len(self.state.ship.allies) * 0.05
                + self._skill("trade")
                + float(faction_perks["trade_margin"])
            )
            margin_mult = max(0.25, margin_mult)
            corp_mult = 1.0
            dom_corp_id = self.current_system.dominant_corp
            if dom_corp_id:
                corp = get_corporation(dom_corp_id)
                if corp and corp.specialty_commodity == item_id:
                    corp_mult = 1.0 + corp.bonus_trade_margin
            unit_sell = min(max(1, quote.buy_price - 1), int(quote.sell_price * margin_mult * corp_mult))
            revenue = unit_sell * quantity
            # Update local system stockpile in economy
            econ_markets = dict(self.state.economy.markets)
            sys_id = self.current_system.id
            if sys_id in econ_markets:
                sm = econ_markets[sys_id]
                new_stocks = dict(sm.stockpiles)
                new_stocks[item_id] = min(MAX_STOCK, new_stocks.get(item_id, 50) + quantity)
                econ_markets[sys_id] = replace(sm, stockpiles=new_stocks)
            new_economy = replace(self.state.economy, markets=econ_markets)


            depot_cargo = dict(depot.cargo)
            depot_cargo[item_id] -= quantity
            if depot_cargo[item_id] <= 0:
                depot_cargo.pop(item_id, None)
            updated_depot = replace(depot, cargo=depot_cargo)
            depots = tuple(updated_depot if d.id == depot.id else d for d in self.state.depots)
            stats = dict(self.state.stats)
            stats["trades"] = stats.get("trades", 0) + 1
            stats["credits_earned"] = stats.get("credits_earned", 0) + revenue
            self.state = self._clone_state(
                ship=self._clone_ship(credits=self.state.ship.credits + revenue),
                depots=depots,
                stats=stats,
                economy=new_economy,
            )
            return True, f"Sold {quantity}x {item_id} from {depot.name} for {revenue} cr."

    def land_on_body(self, body_id: str) -> tuple[bool, str]:
        """Land on a habitable body and collect surface discovery rewards."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            transit = self._transit_lock_reason()
            if transit:
                return False, transit
            body = next((b for b in self.current_system.bodies if b.id == body_id), None)
            if not body:
                return False, f"Unknown body '{body_id}' in {self.current_system.name}."
            if self.state.ship.orbiting_body_id != body_id:
                return False, "Establish orbit around the body before landing."
            if not body.landable:
                return False, f"{body.name} is not rated for habitable landing operations."
            if self.state.ship.landed_body_id == body_id:
                return False, f"Already landed on {body.name}."
            reward = 150 + int(body.radius_km / 1000) * 5
            stats = dict(self.state.stats)
            stats["landings"] = stats.get("landings", 0) + 1
            stats["credits_earned"] = stats.get("credits_earned", 0) + reward
            log_entry = f"SURFACE LANDING: Touched down on {body.name}. Survey reward +{reward} cr."
            new_ship = self._clone_ship(
                credits=self.state.ship.credits + reward,
                landed_body_id=body_id,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log_entry]),
            )
            self.state = self._clone_state(ship=new_ship, stats=stats)
            if self.allow_decision_events:
                self.maybe_trigger_decision("land")
            return True, log_entry

    def reconstruct_world(self, body_id: str, mode: str = "credits") -> tuple[bool, str]:
        """Rebuild a devastated inhabited world with credits or relief cargo.

        This is the player's counter to war devastation: credits fund a construction
        crew, while relief supplies (medicines, food and fuel) repair more damage and
        earn more standing with the world's owner.
        """
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            transit = self._transit_lock_reason()
            if transit:
                return False, transit
            if self.state.active_combat is not None:
                return False, "Cannot rebuild a world while under hostile fire."
            body = next((candidate for candidate in self.current_system.bodies if candidate.id == body_id), None)
            if body is None:
                return False, f"Unknown body '{body_id}' in {self.current_system.name}."
            ship = self.state.ship
            if ship.orbiting_body_id != body.id and ship.landed_body_id != body.id:
                return False, f"Establish orbit around {body.name} before starting reconstruction."
            if body.population <= 0:
                return False, f"{body.name} has no settled population to rebuild."
            devastation = max(0.0, float(body.devastation or 0.0))
            if devastation <= 0.0:
                return False, f"{body.name} is not devastated; no reconstruction is needed."

            normalized = str(mode).strip().lower()
            if normalized not in ("credits", "relief"):
                return False, "Unknown reconstruction mode. Use 'credits' or 'relief'."
            cargo = dict(ship.cargo)
            crew = ship.crew
            credits = ship.credits
            standings = dict(ship.faction_standings)
            stats = dict(self.state.stats)
            if normalized == "credits":
                if credits < self.RECONSTRUCTION_CREDIT_COST:
                    return (
                        False,
                        f"Reconstruction requires {self.RECONSTRUCTION_CREDIT_COST} cr; "
                        f"treasury has {credits} cr.",
                    )
                credits -= self.RECONSTRUCTION_CREDIT_COST
                reduction = self.RECONSTRUCTION_CREDIT_DEVASTATION
                standing_delta = 2
                kind = "reconstruction"
                title = "World Reconstruction"
                stats["worlds_rebuilt"] = int(stats.get("worlds_rebuilt", 0)) + 1
                log = (
                    f"REBUILD: {body.name} construction crews restored "
                    f"{reduction:.0f} devastation for {self.RECONSTRUCTION_CREDIT_COST} cr."
                )
            else:
                missing = [
                    f"{quantity}x {item_id}"
                    for item_id, quantity in self.RELIEF_CARGO
                    if int(cargo.get(item_id, 0)) < quantity
                ]
                if missing:
                    return False, f"Relief supplies missing: {', '.join(missing)}."
                for item_id, quantity in self.RELIEF_CARGO:
                    remaining = int(cargo.get(item_id, 0)) - quantity
                    if remaining > 0:
                        cargo[item_id] = remaining
                    else:
                        cargo.pop(item_id, None)
                reduction = self.RELIEF_DEVASTATION
                standing_delta = 5
                kind = "relief"
                title = "Relief Convoy Landed"
                stats["relief_deliveries"] = int(stats.get("relief_deliveries", 0)) + 1
                crew, _ = apply_morale_event(crew, 2.0, f"relief {body.name}")
                log = (
                    f"RELIEF: landed medicines, food and fuel at {body.name}; "
                    f"devastation -{reduction:.0f}, crew morale lifted."
                )

            faction_id = get_faction_id_from_name(body.faction) if body.faction != "Unclaimed" else ""
            if faction_id and faction_id not in self.state.eliminated_factions:
                standings[faction_id] = max(-100, min(100, standings.get(faction_id, 0) + standing_delta))
            new_devastation = max(0.0, devastation - reduction)
            systems = dict(self.state.systems)
            system = systems[self.current_system.id]
            systems[system.id] = replace(
                system,
                bodies=tuple(
                    replace(candidate, devastation=new_devastation) if candidate.id == body.id else candidate
                    for candidate in system.bodies
                ),
            )
            events = list(self.state.events)
            events.append(
                GameEvent(
                    id=f"evt_{self.state.time.tick}_{len(events) + 1}",
                    kind=kind,
                    title=title,
                    message=f"{body.name} is now at {new_devastation:.0f}% devastation.",
                    tick=self.state.time.tick,
                    dismissed=False,
                )
            )
            new_ship = self._clone_ship(
                credits=credits,
                cargo=cargo,
                crew=crew,
                faction_standings=standings,
                flight_log=tuple(list(ship.flight_log[-19:]) + [log]),
            )
            self.state = self._clone_state(
                ship=new_ship,
                systems=systems,
                stats=stats,
                events=tuple(events[-50:]),
            )
            return True, log

    def get_surface_report(self) -> dict[str, Any]:
        """Landing-party operations available on the currently landed body."""
        with self.lock:
            landed_id = self.state.ship.landed_body_id
            body = next(
                (candidate for candidate in self.current_system.bodies if candidate.id == landed_id),
                None,
            )
            return surface_report(self.state.ship, body)

    def perform_surface_operation(self, operation_id: str) -> tuple[bool, str]:
        """Run one surface operation, then mark the site branch as worked."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            body = next(
                (candidate for candidate in self.current_system.bodies if candidate.id == self.state.ship.landed_body_id),
                None,
            )
            if body is None:
                return False, "Land on a body before starting surface operations."
            operation = SURFACE_OPERATION_MAP.get(str(operation_id))
            if operation is None:
                return False, f"Unknown surface operation '{operation_id}'."
            if not operation.available_on(body):
                return (
                    False,
                    f"{operation.name} is not available on {body.name} "
                    f"({body.body_type.replace('_', ' ')} surface).",
                )
            key = f"{body.id}:{operation.id}"
            if key in self.state.ship.surface_used:
                return False, f"{operation.name} has already been completed on {body.name}."
            if self.state.ship.credits < operation.credit_cost:
                return False, f"{operation.name} requires {operation.credit_cost} cr; treasury has {self.state.ship.credits} cr."
            outcome = resolve_surface_operation(
                operation, body, self.state.ship, self.state.galaxy_seed, self.state.time.tick
            )
            cargo = dict(self.state.ship.cargo)
            granted_items: list[str] = []
            for item_id, quantity in outcome["cargo"]:
                granted, overflow = self._grant_cargo(cargo, item_id, quantity)
                if granted:
                    granted_items.append(f"+{granted} {get_item_info(item_id).name}")
            crew = self.state.ship.crew
            heal = int(outcome["heal_injuries"])
            if heal:
                crew = tuple(replace(member, injury_ticks=max(0, member.injury_ticks - heal)) for member in crew)
            morale = int(outcome["morale"])
            if morale:
                crew, _ = apply_morale_event(crew, float(morale), f"surface {operation.name}")
            research = self.state.research
            research_delta = int(outcome["research"])
            if research_delta:
                research = ResearchState(
                    points=research.points + research_delta,
                    progress=research.progress + research_delta,
                    active_project_id=research.active_project_id,
                    completed=research.completed,
                    queue=research.queue,
                )
            new_credits = max(
                0,
                self.state.ship.credits + int(outcome["credits"]) - operation.credit_cost,
            )
            new_hull = max(0, min(self.state.ship.max_hull, self.state.ship.hull + int(outcome["hull_delta"])))
            stats = dict(self.state.stats)
            stats["surface_ops"] = int(stats.get("surface_ops", 0)) + 1
            stats["credits_earned"] = int(stats.get("credits_earned", 0)) + int(outcome["credits"])
            new_contracts, contract_logs = self._progress_contracts("surface", 1)
            detail = " ".join(granted_items + contract_logs)
            log = str(outcome["log"]) + (f" {detail}" if detail else "")
            new_ship = self._clone_ship(
                credits=new_credits,
                hull=new_hull,
                cargo=cargo,
                crew=crew,
                active_contracts=new_contracts,
                surface_used=self.state.ship.surface_used + (key,),
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log]),
            )
            self.state = self._clone_state(ship=new_ship, research=research, stats=stats)
            if self.allow_decision_events:
                self.maybe_trigger_decision("land")
            return True, log

    def salvage_derelict(self, strategy: str = "balanced") -> tuple[bool, str, dict[str, Any]]:
        """Board the current body's derelict hulk for cargo, credits, and hazard risk."""
        with self.lock:
            strategy = str(strategy).strip().lower() or "balanced"
            if strategy not in ("cautious", "balanced", "aggressive", "scientific"):
                return (
                    False,
                    f"Unknown salvage strategy '{strategy}'. "
                    "Choose cautious, balanced, aggressive or scientific.",
                    {},
                )
            lock = self._action_lock_reason()
            if lock:
                return False, lock, {}
            transit = self._transit_lock_reason()
            if transit:
                return False, transit, {}
            body = self.docked_body
            if not body:
                return False, "Cannot salvage: establish orbit around a body first.", {}
            if self.state.active_combat:
                return False, "Cannot salvage while under hostile fire.", {}
            if body.salvage_claimed:
                return False, f"The derelict at {body.name} has already been stripped.", {}

            cur_sys = self.current_system
            site = derive_derelict(cur_sys.id, cur_sys.seed, body)
            if site is None:
                return False, f"No derelict salvage is detected at {body.name}.", {}

            equipment = self._combined_equipment()
            crew_bonuses = calculate_crew_bonuses(self.state.ship.crew)
            sensor_edge = (self._effective_power("sensors") - 25) / 25.0 * 0.12
            base_danger = max(0.05, min(0.65, site.danger - sensor_edge - crew_bonuses["boarding_defense"] * 0.5))
            
            if strategy == "cautious":
                danger = max(0.02, base_danger * 0.5)
            elif strategy == "aggressive":
                danger = min(0.85, base_danger + 0.15)
            elif strategy == "scientific":
                danger = min(0.80, base_danger + 0.08) if self._effective_power("sensors") < 25 else base_danger
            else:
                danger = base_danger
                
            danger_roll = self.rng.random()
            success = danger_roll >= danger
            # Almost-WON near-miss: the boarding roll just missed (failed but
            # within the window). First one per scan cycle reuses the sensor
            # tune bonus; all of them are logged, never manufactured.
            salvage_near_miss = (not success) and (danger_roll >= danger - NEAR_MISS_SALVAGE_WINDOW)

            cargo = dict(self.state.ship.cargo)
            granted = 0
            research_gain = 0
            overflow = 0
            payout_mult, payout_label = payout_magnitude_for(
                self.seed, "salvage-payout", site.body_id, strategy,
                int(self.state.stats.get("salvage", 0)),
            )
            if success:
                if strategy == "cautious":
                    granted, overflow = self._grant_cargo(cargo, site.cargo_item, site.cargo_quantity)
                    credits = max(10, int(site.credits * 0.85))
                    hull_damage = 0
                    heat_gain = 2.0
                    outcome = "CAUTIOUS EXTRACTION"
                    xp_award = 65
                elif strategy == "aggressive":
                    extra = 1 if self.rng.random() < 0.45 else 0
                    granted, overflow = self._grant_cargo(cargo, site.cargo_item, site.cargo_quantity + extra)
                    credits = int(site.credits * 1.5)
                    hull_damage = 0
                    heat_gain = 12.0
                    outcome = "HEAVY BREACH HARVEST"
                    xp_award = 75
                elif strategy == "scientific":
                    granted, overflow = self._grant_cargo(cargo, site.cargo_item, site.cargo_quantity)
                    credits = site.credits
                    hull_damage = 0
                    heat_gain = 5.0
                    research_gain = 35
                    outcome = "CORE ARCHIVE EXTRACTED"
                    xp_award = 90
                else:
                    granted, overflow = self._grant_cargo(cargo, site.cargo_item, site.cargo_quantity)
                    credits = site.credits
                    hull_damage = 0
                    heat_gain = 4.0
                    outcome = "HULL STRIPPED"
                    xp_award = 55
                if overflow:
                    outcome += f" ({overflow} unit(s) left behind, hold full)"
            else:
                if strategy == "cautious":
                    credits = max(20, site.credits // 5)
                    hull_damage = min(3, 1 + int(danger * 8))
                    heat_gain = 4.0
                    outcome = "SURVEY ABORTED"
                    xp_award = 30
                elif strategy == "aggressive":
                    credits = max(15, site.credits // 4)
                    hull_damage = 10 + int(danger * 26)
                    heat_gain = 15.0
                    outcome = "BREACH ACCIDENT"
                    xp_award = 20
                else:
                    credits = max(25, site.credits // 4)
                    hull_damage = 6 + int(danger * 22)
                    heat_gain = 9.0
                    outcome = "BOARDING ACCIDENT"
                    xp_award = 25

            # Variable-ratio magnitude on success (unpredictable magnitude AND
            # timing; deterministic stream, live RNG untouched).
            payout_note = ""
            if success and payout_label != "standard":
                credits = int(credits * payout_mult)
                payout_note = f" [{payout_label.upper()} x{payout_mult:.1f}]"
                outcome += payout_note
            # Salvage near-miss: failed but close — wreck schematics tune the
            # sensors (+25% next scan, same capped bonus pool as scan misses).
            tune_note = ""
            tune_bonus = 0.0
            if salvage_near_miss:
                tune_bonus = NEAR_MISS_SCAN_BONUS
                tune_note = " NEAR-MISS: wreck schematics tune the sensors (+25% next scan)."

            reactor = self.state.ship.reactor
            max_heat = reactor_heat_capacity(reactor, equipment)
            new_reactor = replace(reactor, heat=min(max_heat, reactor.heat + heat_gain))
            new_hull = max(1, self.state.ship.hull - hull_damage)
            new_mastery, xp_logs = self._award_pilot_xp(xp_award, self.state.ship.mastery)

            log_entry = (
                f"DERELICT SALVAGE [{outcome}]: {site.name}. +{credits} cr"
                + (f", +{granted} {site.cargo_item}" if granted else "")
                + (f", hull -{hull_damage}" if hull_damage else "")
                + f", reactor heat +{heat_gain:.0f}."
                + (f" Stated danger was {danger:.0%}; roll {danger_roll:.0%}." if not success else f" Stated danger was {danger:.0%}.")
                + tune_note
            )
            updated_contracts = self.state.ship.active_contracts
            contract_logs: list[str] = []
            if success and granted > 0 and site.cargo_item == "titanium":
                updated_contracts, contract_logs = self._progress_contracts("mining", granted)
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry] + xp_logs + contract_logs

            new_ship = self._clone_ship(
                hull=new_hull,
                credits=self.state.ship.credits + credits,
                cargo=cargo,
                reactor=new_reactor,
                mastery=new_mastery,
                active_contracts=updated_contracts,
                near_miss_scanner_bonus=(
                    tune_bonus if salvage_near_miss
                    else self.state.ship.near_miss_scanner_bonus
                ),
                flight_log=tuple(new_log[-20:]),
            )
            stats = dict(self.state.stats)
            stats["salvage"] = stats.get("salvage", 0) + 1
            stats["credits_earned"] = stats.get("credits_earned", 0) + credits
            stats[f"payout_{payout_label}"] = int(stats.get(f"payout_{payout_label}", 0)) + 1
            stats[f"salvage_strategy_{strategy}"] = int(stats.get(f"salvage_strategy_{strategy}", 0)) + 1
            if salvage_near_miss:
                stats["near_miss_salvage"] = int(stats.get("near_miss_salvage", 0)) + 1
            systems = self._replace_system_body(body.id, salvage_claimed=True)
            new_research = self.state.research
            if research_gain > 0:
                new_research = replace(self.state.research, points=self.state.research.points + research_gain)
            self.state = self._clone_state(ship=new_ship, systems=systems, stats=stats, research=new_research)
            if self.allow_decision_events:
                self.maybe_trigger_decision("orbit")
            report = {
                "site": site.to_dict(),
                "success": success,
                "danger": round(danger, 2),
                "danger_roll": round(danger_roll, 3),
                "near_miss": salvage_near_miss,
                "payout_mult": payout_mult,
                "payout_label": payout_label,
                "odds": payout_odds_table(),
                "credits": credits,
                "cargo_item": site.cargo_item if granted else None,
                "cargo_quantity": granted,
                "hull_damage": hull_damage,
            }
            return True, log_entry, report

    def scoop_fuel(self) -> tuple[bool, str]:
        """Recover fuel from a star, gas giant, or ice body currently in orbit."""
        with self.lock:
            lock = self._action_lock_reason()
            if lock:
                return False, lock
            transit = self._transit_lock_reason()
            if transit:
                return False, transit
            body = self.docked_body
            if not body:
                return False, "Cannot scoop fuel: establish orbit around a scoopable body first."
            if self.state.active_combat:
                return False, "Cannot scoop fuel while under hostile fire."
            profile = scoop_profile(body)
            if profile is None:
                return False, f"{body.name} has no accessible volatiles for fuel scooping."
            if self.state.ship.fuel >= self.state.ship.max_fuel:
                return False, "Fuel tanks are already full."
            reserve = scoop_reserve(body)
            base_tapped, base_recharge = recharge_volatile_reserve(
                body.volatile_tapped,
                body.volatile_recharge_tick,
                self.state.time.tick,
            )
            if base_tapped >= reserve:
                return False, (
                    f"{body.name}'s volatile reservoir is depleted "
                    f"({base_tapped}/{reserve} taps). It recharges one tap every "
                    f"{SCOOP_RECHARGE_TICKS} ticks."
                )

            recovered = scoop_yield(
                body,
                self._effective_power("sensors") * float(self._map_effects()["sensor_mult"]),
                self._skill("science"),
            )
            payout_mult, payout_label = payout_magnitude_for(
                self.seed, "scoop-payout", body.id, base_tapped,
            )
            if payout_label != "standard":
                recovered = max(1, int(round(recovered * payout_mult)))
            new_fuel = min(self.state.ship.max_fuel, self.state.ship.fuel + recovered)
            gained = new_fuel - self.state.ship.fuel
            reactor = self.state.ship.reactor
            max_heat = reactor_heat_capacity(reactor, self._combined_equipment())
            new_reactor = replace(reactor, heat=min(max_heat, reactor.heat + profile["heat"]))
            new_tapped = base_tapped + 1
            new_recharge = (
                base_recharge
                if base_tapped > 0
                else self.state.time.tick + SCOOP_RECHARGE_TICKS
            )
            systems = self._replace_system_body(
                body.id,
                volatile_tapped=new_tapped,
                volatile_recharge_tick=new_recharge,
            )

            payout_note = (
                f" [{payout_label.upper()} x{payout_mult:.1f}]"
                if payout_label != "standard"
                else ""
            )
            log_entry = (
                f"FUEL SCOOP: {profile['label']} at {body.name} recovered {gained} fuel{payout_note} "
                f"(reactor heat +{profile['heat']:.0f}, volatiles {new_tapped}/{reserve})."
            )
            new_ship = self._clone_ship(
                fuel=new_fuel,
                reactor=new_reactor,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log_entry]),
            )
            stats = dict(self.state.stats)
            stats["scoops"] = stats.get("scoops", 0) + 1
            stats[f"payout_{payout_label}"] = int(stats.get(f"payout_{payout_label}", 0)) + 1
            self.state = self._clone_state(ship=new_ship, systems=systems, stats=stats)
            return True, log_entry

    def train_crew_member(self, crew_id: str) -> tuple[bool, str]:
        """Run a paid training drill that raises one crew member's skill rank."""
        with self.lock:
            member = next((c for c in self.state.ship.crew if c.id == crew_id), None)
            if not member:
                return False, f"Unknown crew member '{crew_id}'."
            if member.skill >= 10:
                return False, f"{member.name} is already at maximum skill rank."
            cost = crew_training_cost(member)
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: {cost} cr required for the training drill."
            updated = replace(
                member,
                skill=member.skill + 1,
                morale=min(100.0, member.morale + 2.0),
            )
            crew = tuple(updated if c.id == crew_id else c for c in self.state.ship.crew)
            fleet_ships = tuple(
                replace(ship, captain_skill=updated.skill)
                if ship.captain_id == crew_id
                else ship
                for ship in self.state.ship.fleet_ships
            )
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - cost,
                crew=crew,
                fleet_ships=fleet_ships,
            )
            self.state = self._clone_state(ship=new_ship)
            return True, f"{member.name} completed a training drill: skill {member.skill} -> {updated.skill} (-{cost} cr)."

    def shore_leave(self) -> tuple[bool, str]:
        """Grant fleet-wide shore leave at a docked station, restoring crew morale for credits."""
        with self.lock:
            body = self.docked_body
            if not body or not body.station_dockable:
                return False, "Shore leave requires docking at a station or colony with leisure decks."

            active = [m for m in self.state.ship.crew if m.status == "active"]
            if not active:
                return False, "No active crew aboard to grant shore leave."

            deficit = sum(max(0.0, 100.0 - m.morale) for m in active)
            if deficit <= 0:
                return False, "Crew morale is already at peak; the leisure decks stand empty."

            faction_id = get_faction_id_from_name(self.current_system.faction)
            perks = get_faction_service_perks(faction_id, self.state.ship.faction_standings.get(faction_id, 0))
            discount = float(perks.get("repair_discount", 0.0))

            new_crew, restored, cost = shore_leave_restore(self.state.ship.crew)
            cost = max(1, int(cost * (1.0 - discount)))
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: shore leave costs {cost} cr ({restored} morale points)."

            log_entry = f"SHORE LEAVE: Crew rotates through {body.name} leisure decks. +{restored} morale for {cost} cr."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]
            self.state = self._clone_state(
                ship=self._clone_ship(
                    credits=self.state.ship.credits - cost,
                    crew=new_crew,
                    flight_log=tuple(new_log[-20:]),
                )
            )
            self.emit_event(
                "crew",
                "Shore Leave Granted",
                f"The crew returns rested and re-focused. Morale +{restored} for {cost} cr.",
            )
            return True, f"Shore leave completed: +{restored} morale across {len(active)} crew for {cost} cr."

    def hire_mercenary(self, merc_id: str) -> tuple[bool, str]:
        with self.lock:
            merc = MERCENARY_CATALOG.get(merc_id)
            if not merc:
                return False, f"Unknown mercenary '{merc_id}'."
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            if any(d.specialty == merc["specialty"] and d.drone_type == "mercenary" for d in self.state.ship.fleet_drones):
                return False, f"A {merc['specialty']} mercenary is already under contract."
            cost = int(merc["cost"])
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: {cost} cr required."
            drone = FleetDrone(
                id=f"merc_{merc_id}_{len(self.state.ship.fleet_drones) + 1}",
                name=str(merc["name"]),
                drone_type="mercenary",
                assigned_system_id=self.state.ship.current_system_id,
                status="idle",
                efficiency=1.0,
                integrity=100,
                specialty=str(merc["specialty"]),
            )
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - cost,
                fleet_drones=self.state.ship.fleet_drones + (drone,),
            )
            self.state = self._clone_state(ship=new_ship)
            return True, f"Hired {merc['name']} for {cost} cr ({merc['description']})."

    def dismiss_fleet_unit(self, drone_id: str) -> tuple[bool, str]:
        with self.lock:
            drone = next((d for d in self.state.ship.fleet_drones if d.id == drone_id), None)
            if not drone:
                return False, f"Unknown fleet unit '{drone_id}'."
            remaining = tuple(d for d in self.state.ship.fleet_drones if d.id != drone_id)
            self.state = self._clone_state(ship=self._clone_ship(fleet_drones=remaining))
            return True, f"Fleet unit '{drone.name}' dismissed."

    def refit_fleet_unit(self, drone_id: str) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_service_dock()
            if not ok:
                return False, msg
            drone = next((d for d in self.state.ship.fleet_drones if d.id == drone_id), None)
            if not drone:
                return False, f"Unknown fleet unit '{drone_id}'."
            cost = 300
            if self.state.ship.credits < cost:
                return False, f"Insufficient credits: {cost} cr required for refit."
            updated = replace(
                drone,
                level=drone.level + 1,
                efficiency=min(1.75, drone.efficiency + 0.10),
                integrity=100,
            )
            drones = tuple(updated if d.id == drone_id else d for d in self.state.ship.fleet_drones)
            new_ship = self._clone_ship(credits=self.state.ship.credits - cost, fleet_drones=drones)
            self.state = self._clone_state(ship=new_ship)
            return True, f"Refit {drone.name} to level {updated.level} (efficiency {updated.efficiency:.2f})."

    def form_alliance(self, captain_id: str) -> tuple[bool, str]:
        return self.interact_ai(captain_id, "ally")

    def _decision_lock_reason(self) -> str:
        pending = self.state.pending_decision
        if pending is not None:
            return f"Decision required: {pending.title}. Choose an option before continuing."
        return ""

    def _action_lock_reason(self) -> str:
        """Reason flight or exploration actions are frozen (decision, pirate or void)."""
        reason = self._decision_lock_reason()
        if reason:
            return reason
        pirate = self.state.active_pirate
        if pirate is not None:
            return (
                f"Pirate intercept unresolved: {pirate.band_name} demands "
                f"{pirate.toll_credits} cr. Pay, fight, or evade before continuing."
            )
        customs = self.state.active_customs
        if customs is not None:
            return (
                f"Customs interdiction unresolved: {customs.patrol_vessel} locked scanners on your hold. "
                "Bribe, jettison, confiscate, or flee before continuing."
            )
        if self.state.ship.void_traversal is not None:
            return (
                "Void traversal in progress: hold the hull steady, emerge, or wait for arrival "
                "before other flight actions."
            )
        return ""

    def _transit_lock_reason(self) -> str:
        """Body actions need a real orbit; mid-flight the ship has left the old body."""
        active = self.state.ship.travel
        if active is None:
            return ""
        destination = "open space" if active.destination_body_id is None else active.destination_body_id
        return (
            f"In transit to {destination}: wait for arrival or orbit the origin body "
            "to abort the trip before using body services."
        )

    # Quick-time prompts are a garnish, not a drumbeat: one decision per cadence window,
    # and the odds stay low so a normal session sees a handful of them.
    DECISION_CADENCE = {
        "relaxed": (36, 0.55),
        "normal": (18, 1.0),
        "frequent": (6, 1.6),
    }
    DEFAULT_DECISION_CADENCE = "relaxed"

    def _cadence_from_state(self, state: GameState) -> str:
        """Read the saved cadence, falling back to the default for unknown values."""
        saved = str(state.stats.get("decision_cadence", ""))
        return saved if saved in self.DECISION_CADENCE else self.DEFAULT_DECISION_CADENCE

    def _decision_cooldown(self) -> int:
        ticks, _ = self.DECISION_CADENCE.get(
            self.decision_cadence, self.DECISION_CADENCE[self.DEFAULT_DECISION_CADENCE]
        )
        return ticks

    def _decision_chance_multiplier(self) -> float:
        _, multiplier = self.DECISION_CADENCE.get(
            self.decision_cadence, self.DECISION_CADENCE[self.DEFAULT_DECISION_CADENCE]
        )
        return multiplier

    def set_decision_cadence(self, cadence: str) -> tuple[bool, str]:
        """Choose how often blocking quick-time decisions may interrupt the flight."""
        key = str(cadence).strip().lower()
        if key not in self.DECISION_CADENCE:
            return False, f"Unknown cadence '{cadence}'. Choose {', '.join(self.DECISION_CADENCE)}."
        stats = dict(self.state.stats)
        stats["decision_cadence"] = key
        self.state = self._clone_state(stats=stats)
        self.decision_cadence = key
        return True, f"Decision cadence set to {key} (one prompt per {self._decision_cooldown()} ticks)."

    def _last_decision_eval_tick(self) -> int:
        """Last tick that consumed a decision window, prompt or failed roll."""
        stats = self.state.stats

        def _as_int(raw: object) -> int:
            try:
                return int(raw)
            except (TypeError, ValueError):
                return 0

        # Older saves only know last_decision_tick. When the eval key is absent, that
        # key is the only anchor; otherwise the later of the two wins.
        eval_raw = stats.get("last_decision_eval_tick")
        if eval_raw is None:
            return _as_int(stats.get("last_decision_tick", 0))
        return max(_as_int(eval_raw), _as_int(stats.get("last_decision_tick", 0)))

    def decisions_ready_in(self) -> int:
        """Ticks left before another blocking decision may be evaluated."""
        last = self._last_decision_eval_tick()
        return max(0, self._decision_cooldown() - (self.state.time.tick - last))

    def maybe_trigger_decision(
        self, trigger: str = "tick", elapsed_ticks: int = 1
    ) -> dict[str, Any] | None:
        """Evaluate conditional events and open at most one blocking decision.

        A batched tick crosses several cadence windows at once, so the per-window odds
        are compounded instead of rolling once at the final tick.
        """
        with self.lock:
            if self.state.pending_decision is not None:
                return None
            if self.state.active_combat or self.state.active_anomaly or self.state.active_pirate:
                return None
            if self.decisions_ready_in() > 0:
                return None
            eligible = eligible_decisions(self.state, trigger)
            if not eligible:
                return None
            chosen = eligible[0]
            roll = self._stable_unit(
                self.state.galaxy_seed, "decision", trigger, self.state.time.tick, chosen.id
            )
            base = 0.38 if chosen.priority >= 85 else 0.08
            per_window = min(0.95, max(chosen.chance, base) * self._decision_chance_multiplier())
            windows = max(1, min(1000, int(elapsed_ticks) // self._decision_cooldown()))
            threshold = min(0.999, 1.0 - (1.0 - per_window) ** windows)
            stats = dict(self.state.stats)
            stats["last_decision_eval_tick"] = self.state.time.tick
            if roll > threshold:
                # One roll per cadence window: a miss moves the window forward instead of
                # rerolling every tick until something opens.
                self.state = self._clone_state(stats=stats)
                return None
            event = make_decision_event(chosen, self.state.time.tick, trigger)
            stats["last_decision_tick"] = self.state.time.tick
            log = f"DECISION REQUIRED: {event.title}."
            self.state = self._clone_state(
                ship=self._clone_ship(flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log])),
                stats=stats,
                pending_decision=event,
            )
            return event.to_dict()

    def resolve_decision(self, choice_id: str) -> tuple[bool, str]:
        """Apply a decision choice; time and flight remain locked until this succeeds."""
        with self.lock:
            pending = self.state.pending_decision
            if pending is None:
                return False, "No decision is pending."
            choice = next((c for c in pending.choices if c.id == str(choice_id)), None)
            if choice is None:
                return False, f"Unknown decision choice '{choice_id}'."
            ship = self.state.ship
            effects = choice.effects
            cargo = dict(ship.cargo)
            for item_id, quantity in dict(effects.get("cargo", {})).items():
                quantity = int(quantity)
                if quantity >= 0:
                    self._grant_cargo(cargo, item_id, quantity)
                else:
                    remaining = max(0, int(cargo.get(item_id, 0)) + quantity)
                    if remaining:
                        cargo[item_id] = remaining
                    else:
                        cargo.pop(item_id, None)
            for item_id, quantity in dict(effects.get("remove_cargo", {})).items():
                remaining = max(0, int(cargo.get(item_id, 0)) - abs(int(quantity)))
                if remaining:
                    cargo[item_id] = remaining
                else:
                    cargo.pop(item_id, None)

            crew = ship.crew
            heal = int(effects.get("heal_injuries", 0))
            if heal:
                crew = tuple(
                    replace(member, injury_ticks=max(0, member.injury_ticks - heal))
                    for member in crew
                )
            morale = int(effects.get("morale", 0))
            if morale:
                crew, morale_log = apply_morale_event(crew, float(morale), f"decision {pending.title}")
            else:
                morale_log = ""

            standings = dict(ship.faction_standings)
            for faction_id, delta in dict(effects.get("standing", {})).items():
                standings[faction_id] = max(-100, min(100, standings.get(faction_id, 0) + int(delta)))

            reactor = ship.reactor
            heat_delta = float(effects.get("heat", 0))
            if heat_delta:
                reactor = replace(
                    reactor,
                    heat=max(0.0, min(reactor_heat_capacity(reactor, self._combined_equipment(ship)), reactor.heat + heat_delta)),
                )

            research = self.state.research
            research_delta = int(effects.get("research", 0))
            if research_delta:
                research = ResearchState(
                    points=research.points + research_delta,
                    progress=research.progress + research_delta,
                    active_project_id=research.active_project_id,
                    completed=research.completed,
                    queue=research.queue,
                )

            active_contracts = ship.active_contracts
            granted_title = ""
            contract_category = str(effects.get("contract") or "").strip()
            if contract_category:
                granted = generate_contract(self.rng, category=contract_category)
                active_contracts = tuple(list(active_contracts) + [granted])
                granted_title = granted.title

            credits = max(0, ship.credits + int(effects.get("credits", 0)))
            fuel = max(0, min(ship.max_fuel, ship.fuel + int(effects.get("fuel", 0))))
            hull = max(0, min(ship.max_hull, ship.hull + int(effects.get("hull", 0))))
            log = str(effects.get("log") or f"DECISION [{pending.title}]: {choice.label}.")
            if granted_title:
                log = f"{log} New contract: [{granted_title}]."
            new_ship = self._clone_ship(
                credits=credits,
                fuel=fuel,
                hull=hull,
                cargo=cargo,
                crew=crew,
                reactor=reactor,
                faction_standings=standings,
                active_contracts=active_contracts,
                flight_log=tuple(list(ship.flight_log[-19:]) + [log]),
            )
            stats = dict(self.state.stats)
            stats["decisions_resolved"] = int(stats.get("decisions_resolved", 0)) + 1
            history = tuple(list(self.state.decision_history) + [pending.definition_id])
            self.state = self._clone_state(
                ship=new_ship,
                pending_decision=None,
                decision_history=history,
                research=research,
                stats=stats,
            )
            if morale_log:
                return True, f"{log} {morale_log}"
            return True, log

    def tick(self, num_ticks: int = 1) -> dict[str, Any]:
        """Advance the simulation universe by num_ticks."""
        with self.lock:
            pending = self.state.pending_decision
            if pending is not None:
                return {
                    "ticks_advanced": 0,
                    "stardate": round(self.state.time.stardate, 2),
                    "date": self.state.time.current_date,
                    "tick": self.state.time.tick,
                    "time_scale": self.state.time.time_scale,
                    "is_paused": self.state.time.is_paused,
                    "blocked_by_decision": True,
                    "decision": pending.to_dict(),
                }
            if self.state.active_pirate is not None:
                return {
                    "ticks_advanced": 0,
                    "stardate": round(self.state.time.stardate, 2),
                    "date": self.state.time.current_date,
                    "tick": self.state.time.tick,
                    "time_scale": self.state.time.time_scale,
                    "is_paused": self.state.time.is_paused,
                    "blocked_by_encounter": True,
                    "encounter": self.state.active_pirate.to_dict(),
                }
            if num_ticks <= 0:
                return {
                    "ticks_advanced": 0,
                    "stardate": round(self.state.time.stardate, 2),
                    "date": self.state.time.current_date,
                    "tick": self.state.time.tick,
                    "time_scale": self.state.time.time_scale,
                    "is_paused": self.state.time.is_paused,
                }
            if self.state.ship.hull <= 0:
                return {
                    "ticks_advanced": 0,
                    "stardate": round(self.state.time.stardate, 2),
                    "date": self.state.time.current_date,
                    "tick": self.state.time.tick,
                    "time_scale": self.state.time.time_scale,
                    "is_paused": self.state.time.is_paused,
                    "destroyed": True,
                }

            cur_time = self.state.time
            new_tick = cur_time.tick + num_ticks
            new_days = cur_time.elapsed_days + num_ticks * 0.25
            new_stardate = 3042.0 + (new_days / 365.25)
            new_time = TimeState(
                tick=new_tick,
                stardate=new_stardate,
                speed=cur_time.speed,
                is_paused=cur_time.is_paused,
                time_scale=cur_time.time_scale,
                elapsed_days=new_days,
            )
            new_stats_tick = dict(self.state.stats)

            # 1. Orbital revolution: advance current_angle for every body in every star system
            stability_by_faction = self._faction_stability()
            previous_tick = new_tick - num_ticks
            updated_systems = {}
            for sys_id, system in self.state.systems.items():
                faction_stability = stability_by_faction.get(system.faction, 50.0)
                updated_bodies = []
                for body in system.bodies:
                    d_angle = body.orbit_speed * 0.05 * num_ticks
                    updated_pop = (
                        step_population_dynamics(body, num_ticks, faction_stability)
                        if body.population > 0
                        else body.population
                    )
                    tapped, recharge_tick = recharge_volatile_reserve(
                        body.volatile_tapped,
                        body.volatile_recharge_tick,
                        new_tick,
                    )
                    recovery = devastation_recovery(body.tech_level, faction_stability)
                    updated_bodies.append(
                        replace(
                            body,
                            current_angle=(body.current_angle + d_angle) % (2.0 * math.pi),
                            population=updated_pop,
                            devastation=max(0.0, (body.devastation or 0.0) - recovery * num_ticks),
                            volatile_tapped=tapped,
                            volatile_recharge_tick=recharge_tick,
                        )
                    )
                updated_systems[sys_id] = StarSystem(
                    id=system.id,
                    name=system.name,
                    seed=system.seed,
                    x=system.x,
                    y=system.y,
                    spectral_type=system.spectral_type,
                    color=system.color,
                    security=system.security,
                    faction=system.faction,
                    bodies=tuple(updated_bodies),
                    connections=system.connections,
                    dominant_corp=system.dominant_corp,
                    modifiers=system.modifiers,
                )

            # 2. Autonomous fleet drone harvesting over time
            cur_ship = self.state.ship
            new_drones = cur_ship.fleet_drones
            drone_cycles = max(1, num_ticks // 4) if num_ticks >= 4 else (1 if new_tick % 4 == 0 else 0)
            drone_cargo_harvested = 0
            drone_credits_harvested = 0
            if drone_cycles > 0 and cur_ship.fleet_drones:
                cargo_before = sum(d.cargo_accumulated for d in cur_ship.fleet_drones)
                credits_before = sum(d.credits_accumulated for d in cur_ship.fleet_drones)
                for _ in range(min(drone_cycles, 10)):
                    new_drones = self._process_drone_cycle(
                        self._clone_ship(fleet_drones=new_drones)
                    )
                drone_cargo_harvested = sum(d.cargo_accumulated for d in new_drones) - cargo_before
                drone_credits_harvested = sum(d.credits_accumulated for d in new_drones) - credits_before

            # 3. Passive shield capacitor regeneration
            equipment = self._combined_equipment(cur_ship)
            new_shield = cur_ship.shield
            shield_recharged = 0
            if not self.state.active_combat and cur_ship.shield < cur_ship.max_shield:
                shield_gain = int(max(1, (self._effective_power("shields", cur_ship) / 25.0) * num_ticks))
                shield_gain += int(equipment["shield_regen"] * num_ticks)
                new_shield = min(cur_ship.max_shield, cur_ship.shield + shield_gain)
                shield_recharged = new_shield - cur_ship.shield

            # 4. Combat ability cooldown decay
            new_combat = self.state.active_combat
            if new_combat and new_combat.ability_cooldown > 0:
                new_cooldown = max(0, new_combat.ability_cooldown - num_ticks)
                new_combat = replace(new_combat, ability_cooldown=new_cooldown)

            # 5. Advance global economy simulation and autonomous AI trade flows
            new_econ, econ_logs = tick_global_economy(self.state.economy, num_ticks, self.state.systems, self.rng)
            new_ai_captains, new_econ, ai_logs = simulate_ai_trade(
                self.state.ai_captains, new_econ, self.state.systems, self.rng
            )
            # Trade chatter is ambient, not news: one summarized line every few ticks keeps
            # the recent half of the flight log free for arrivals, market shocks and war.
            if new_tick % self.AI_TRADE_LOG_TICKS == 0:
                econ_logs.extend(summarize_trades(ai_logs))

            # 6. Automated repair bay module passive hull healing
            new_hull = cur_ship.hull
            repair_per_tick = equipment["hull_repair_per_tick"]
            if repair_per_tick > 0:
                new_hull = min(cur_ship.max_hull, new_hull + int(repair_per_tick * num_ticks))

            # 7. Character aging, abilities, research, and outpost production
            new_character = advance_age(self.state.character, cur_time.elapsed_days, new_days)
            new_character = tick_ability_cooldowns(new_character, num_ticks)
            research_state = self.state.research
            outpost_credits = 0
            research_gain = RESEARCH_BASE_GAIN_PER_TICK + int((new_character.skills.get("science", 1) - 1) * 0.5)
            research_yield_mult = 1.0 + float(self._research_bonuses()["outpost_yield"]) + self._skill("trade")
            updated_outposts = []
            updated_depots = list(self.state.depots)
            for outpost in self.state.outposts:
                production = self._outpost_production(
                    outpost,
                    research_yield_mult,
                    self._outpost_supply_multiplier(outpost),
                )
                outpost_credits += int(production.get("credits", 0.0) * num_ticks)
                research_gain += int(production.get("research", 0.0) * num_ticks)
                for commodity, quantity in production.items():
                    if commodity in ("credits", "research"):
                        continue
                    grant = max(0, int(quantity * num_ticks))
                    if grant <= 0:
                        continue
                    for index, depot in enumerate(updated_depots):
                        if depot.system_id == outpost.system_id:
                            cargo = dict(depot.cargo)
                            cargo[commodity] = min(depot.capacity, cargo.get(commodity, 0) + grant)
                            updated_depots[index] = replace(depot, cargo=cargo)
                            break
                updated_outposts.append(replace(
                    outpost,
                    population=grow_outpost_population(outpost, num_ticks),
                    integrity=min(100.0, outpost.integrity + 0.1 * num_ticks),
                ))

            research_gain += int(equipment.get("research_per_tick", 0.0) * num_ticks)
            research_gain = int(research_gain * self.research_pact_multiplier())
            new_crew, wage_cost, crew_logs = tick_crew(
                cur_ship.crew, num_ticks, cur_ship.credits + outpost_credits, rng=self.rng,
                wage_due=wages_due(cur_ship.crew, cur_time.elapsed_days, new_days),
            )
            medic_aboard = any(
                member.role == "medic" and member.status == "active" and member.injury_ticks == 0
                for member in new_crew
            )
            new_crew, medbay_logs = recover_crew_injuries(new_crew, num_ticks, medic_aboard=medic_aboard)
            crew_logs.extend(medbay_logs)
            month_rollover = int(new_days // DAYS_PER_MONTH) > int(cur_time.elapsed_days // DAYS_PER_MONTH)

            points = research_state.points + max(0, research_gain)
            progress = research_state.progress + max(0, research_gain)
            completed = list(research_state.completed)
            queue = list(research_state.queue)
            active_id = research_state.active_project_id
            new_flight_log_research = ""
            if active_id:
                project = get_research_project(active_id)
                if project and progress >= project.cost:
                    completed.append(project.id)
                    new_flight_log_research = f"RESEARCH COMPLETE: {project.name}."
                    active_id = None
                    progress = 0
            if active_id is None and queue:
                # Start the first eligible project but keep blocked entries: their
                # prerequisites may finish later, so dropping them would lose the order.
                for index, next_id in enumerate(queue):
                    next_project = get_research_project(next_id)
                    if next_project is None or next_id in completed:
                        continue
                    if any(
                        prerequisite not in completed
                        for prerequisite in next_project.prerequisites
                    ):
                        continue
                    active_id = next_id
                    progress = 0
                    del queue[index]
                    new_flight_log_research += (
                        f" RESEARCH STARTED: {next_project.name}."
                    )
                    break
                queue = [
                    queued_id
                    for queued_id in queue
                    if get_research_project(queued_id) is not None
                    and queued_id not in completed
                ]
            new_research = ResearchState(
                points=points,
                progress=progress,
                active_project_id=active_id,
                completed=tuple(dict.fromkeys(completed)),
                queue=tuple(queue),
            )
            new_character, char_promoted, char_msg = award_character_xp(
                new_character, num_ticks + len(self.state.outposts)
            )
            if char_promoted:
                new_flight_log_research += f" {char_msg}"

            new_fleet_ships = tuple(
                replace(
                    ship,
                    shield=min(ship.max_shield, ship.shield + int(2 * num_ticks)),
                    status="escorting" if ship.hull > 0 else "destroyed",
                )
                for ship in cur_ship.fleet_ships
            )

            # 8. Faction leaders, diplomacy wars, and territorial change
            new_wars, updated_systems, new_eliminated, faction_logs = simulate_faction_behaviors(
                self.state.faction_leaders,
                self.state.wars,
                updated_systems,
                self.rng,
                new_tick,
                self.state.eliminated_factions,
                num_ticks,
                frozenset(
                    economy.faction_id
                    for economy in self.state.faction_economies
                    if economy.treasury <= 0 and economy.net_income < 0
                ),
                non_aggression_pairs=self._active_non_aggression_pairs(new_tick),
            )
            new_trade_links = compute_trade_links(
                updated_systems,
                new_wars,
                self.state.faction_economies,
                new_eliminated,
            )
            new_faction_economies, faction_economy_logs = tick_faction_economies(
                self.state.faction_economies,
                updated_systems,
                new_wars,
                new_eliminated,
                num_ticks,
                new_trade_links,
            )
            faction_logs.extend(faction_economy_logs)
            new_wars, bankrupt_peace_logs = force_peace_for_broke_factions(
                new_wars, new_faction_economies, new_tick
            )
            faction_logs.extend(bankrupt_peace_logs)
            new_wars, bond_credits, bond_logs = self._resolve_war_bonds(new_wars)
            faction_logs.extend(bond_logs)
            if bond_credits:
                new_stats_tick["war_bond_payouts"] = (
                    int(new_stats_tick.get("war_bond_payouts", 0)) + bond_credits
                )

            # A conquered system damages the player's outposts there. Sentry Grids
            # and stationed marines reduce the hit; repair contracts restore them.
            outpost_raid_logs: list[str] = []
            crew_by_id = {member.id: member for member in self.state.ship.crew}
            for index, outpost in enumerate(updated_outposts):
                old_system = self.state.systems.get(outpost.system_id)
                new_system = updated_systems.get(outpost.system_id)
                if (
                    old_system is None
                    or new_system is None
                    or old_system.faction == new_system.faction
                    or new_system.faction == CANONICAL_FACTIONS["sol_coalition"].name
                ):
                    continue
                damage = self._outpost_capture_damage(
                    outpost, old_system, new_system, crew_by_id
                )
                if damage <= 0:
                    continue
                integrity = max(0.0, outpost.integrity - damage)
                updated_outposts[index] = replace(outpost, integrity=integrity)
                new_stats_tick["outposts_raided"] = (
                    int(new_stats_tick.get("outposts_raided", 0)) + 1
                )
                outpost_raid_logs.append(
                    f"OUTPOST RAID: {outpost.name} hit during the fall of "
                    f"{new_system.name} (integrity {integrity:.0f}%)."
                )

            # Technology drift runs after the economy so today's breakthrough upgrades
            # the worlds that can support it, raising their carrying capacity.
            tech_by_name = {
                CANONICAL_FACTIONS[economy.faction_id].name: economy.tech_level
                for economy in new_faction_economies
                if economy.faction_id in CANONICAL_FACTIONS
            }
            updated_systems = self._drift_world_technology(
                updated_systems, tech_by_name, previous_tick, new_tick
            )

            # 9. Reactor thermal simulation: heat, cooling, derating, and core wear
            tick_system = self.state.systems.get(cur_ship.current_system_id, self.current_system)
            tick_map = self._map_effects(tick_system)
            total_allocation = sum(cur_ship.power.to_dict().values())
            new_reactor, reactor_report = simulate_reactor_tick(
                cur_ship.reactor,
                total_allocation,
                num_ticks,
                equipment,
                tick_map,
                float(tick_map.get("hull_hazard", 0.0)),
                float(equipment.get("reactor_output", 0.0)),
            )
            reactor_hull_damage = int(reactor_report.get("hull_damage", 0))
            if reactor_hull_damage > 0:
                new_hull = max(1, new_hull - reactor_hull_damage)

            new_flight_log = list(cur_ship.flight_log)
            if econ_logs:
                new_flight_log.extend(econ_logs)
            if outpost_raid_logs:
                new_flight_log.extend(outpost_raid_logs[-3:])
            if reactor_report["critical"]:
                new_flight_log.append(
                    f"REACTOR CRITICAL: core heat {new_reactor.heat:.0f}/{new_reactor.max_heat:.0f}, "
                    f"efficiency {reactor_report['efficiency'] * 100:.0f}%"
                    + (f", hull stress -{reactor_hull_damage}." if reactor_hull_damage else ".")
                )
            elif reactor_report["overheated"]:
                new_flight_log.append(
                    f"REACTOR WARNING: core heat {new_reactor.heat:.0f}/{new_reactor.max_heat:.0f}; "
                    f"subsystem output at {reactor_report['efficiency'] * 100:.0f}%."
                )

            # 7. In-system transit progression and arrival
            new_orbiting_body_id = cur_ship.orbiting_body_id
            new_landed_body_id = cur_ship.landed_body_id
            new_travel = cur_ship.travel
            new_waypoint_au = cur_ship.waypoint_au
            new_waypoint_angle = cur_ship.waypoint_angle
            new_events = list(self.state.events)
            if cur_ship.travel is not None and new_tick >= cur_ship.travel.arrival_tick:
                new_orbiting_body_id = cur_ship.travel.destination_body_id
                new_landed_body_id = None
                new_travel = None
                cur_sys_obj = updated_systems.get(cur_ship.current_system_id, self.current_system)
                if new_orbiting_body_id is None:
                    # Open-space vector: the ship holds station in the void, orbiting nothing.
                    new_waypoint_au = float(cur_ship.travel.waypoint_au)
                    new_waypoint_angle = float(cur_ship.travel.waypoint_angle)
                    dest_name = f"open space at {cur_ship.travel.waypoint_au:.2f} AU"
                    arr_msg = (
                        f"Holding station in {dest_name} after {cur_ship.travel.mode} transit."
                    )
                else:
                    new_waypoint_au = 0.0
                    new_waypoint_angle = 0.0
                    dest_name = new_orbiting_body_id
                    for b in cur_sys_obj.bodies:
                        if b.id == new_orbiting_body_id:
                            dest_name = b.name
                            break
                    arr_msg = f"Orbital capture achieved around {dest_name} after {cur_ship.travel.mode} transit."
                new_flight_log.append(arr_msg)
                evt_id = f"evt_{new_tick}_{len(new_events) + 1}"
                new_events.append(
                    GameEvent(
                        id=evt_id,
                        kind="arrival",
                        title=(
                            f"Holding Station: {dest_name}"
                            if new_orbiting_body_id is None
                            else f"Orbital Capture: {dest_name}"
                        ),
                        message=arr_msg,
                        tick=new_tick,
                        dismissed=False,
                    )
                )

            # 8. Void traversal: storms, forced emergence, and arrival in the Hollow Between
            new_void = cur_ship.void_traversal
            new_current_system_id = cur_ship.current_system_id
            new_visited_systems = self.state.visited_systems
            new_mastery = cur_ship.mastery
            new_credits_delta = 0
            # new_stats_tick is initialized as dict(self.state.stats) at tick start
            if new_void is not None:
                ticks_in_void = max(0, min(num_ticks, new_void.arrival_tick - cur_time.tick))
                storm_chance = self._void_storm_chance()
                storms_weathered = new_void.storms_weathered
                stability = new_void.stability
                resonance = new_void.resonance
                forced_emergence = False
                for _ in range(ticks_in_void):
                    if stability <= 0:
                        forced_emergence = True
                        break
                    if self.rng.random() < storm_chance:
                        storms_weathered += 1
                        stability -= self.VOID_STORM_STABILITY_LOSS
                        new_shield = max(0, new_shield - self.VOID_STORM_SHIELD_LOSS)
                        new_hull = max(1, new_hull - self.VOID_STORM_HULL_LOSS)
                        resonance += 1.0
                        if stability < self.VOID_LOW_STABILITY_THRESHOLD:
                            new_hull = max(1, new_hull - self.VOID_STORM_HULL_LOSS)
                            resonance += self.VOID_LOW_STABILITY_RESONANCE_BONUS
                        new_crew, storm_morale_log = apply_morale_event(new_crew, -3.0, "void storm shear in the Hollow")
                        new_flight_log.append(
                            f"VOID STORM: Shear front weathered ({storms_weathered} total, "
                            f"resonance {resonance:.0f}). Stability {max(0.0, stability):.0f}%, "
                            f"shields -{self.VOID_STORM_SHIELD_LOSS}."
                        )
                        if storm_morale_log:
                            new_flight_log.append(storm_morale_log)

                if forced_emergence or stability <= 0:
                    origin_sys = self.state.systems.get(new_void.origin_system_id)
                    origin_name = origin_sys.name if origin_sys else new_void.origin_system_id
                    horizon_id = None
                    if origin_sys is not None:
                        for body in origin_sys.bodies:
                            if body.body_type == "black_hole":
                                horizon_id = body.id
                                break
                    new_hull = max(1, new_hull - self.VOID_EMERGENCE_HULL_DAMAGE)
                    new_orbiting_body_id = horizon_id
                    new_void = None
                    new_stats_tick["void_collapses"] = int(new_stats_tick.get("void_collapses", 0)) + 1
                    new_flight_log.append(
                        f"VOID COLLAPSE: Stability lost. The Hollow expels the hull violently at {origin_name} "
                        f"(hull -{self.VOID_EMERGENCE_HULL_DAMAGE}, resonance {resonance:.0f} lost)."
                    )
                    evt_id = f"evt_{new_tick}_{len(new_events) + 1}"
                    new_events.append(
                        GameEvent(
                            id=evt_id,
                            kind="void",
                            title="Void Collapse",
                            message=f"Stability collapsed mid-traversal. Emergency expulsion at {origin_name}.",
                            tick=new_tick,
                            dismissed=False,
                        )
                    )
                elif new_tick >= new_void.arrival_tick:
                    dest_id = new_void.destination_system_id
                    dest_sys = self.state.systems.get(dest_id)
                    dest_name = dest_sys.name if dest_sys else dest_id
                    first_visit = dest_id not in set(self.state.visited_systems)
                    visited = set(self.state.visited_systems)
                    visited.add(dest_id)
                    new_visited_systems = tuple(sorted(visited))
                    new_current_system_id = dest_id
                    resonance_credits, resonance_xp = self._void_resonance_payout(resonance)
                    new_credits_delta += resonance_credits
                    new_mastery, xp_logs = self._award_pilot_xp(
                        self.VOID_ARRIVAL_XP + resonance_xp, cur_ship.mastery
                    )
                    new_flight_log.extend(xp_logs)
                    if first_visit:
                        new_credits_delta += self.VOID_FIRST_VISIT_BONUS
                        new_flight_log.append(
                            f"VOID ARRIVAL: First emergence into {dest_name}. Cartography bounty +{self.VOID_FIRST_VISIT_BONUS} cr."
                        )
                    else:
                        new_flight_log.append(f"VOID ARRIVAL: Emerged into {dest_name} from the Hollow Between.")
                    if resonance > 0:
                        new_flight_log.append(
                            f"HOLLOW RESONANCE: {resonance:.0f} storm resonance crystallized on arrival "
                            f"(+{resonance_credits} cr, +{resonance_xp} XP)."
                        )
                    if stability < 60:
                        new_hull = max(1, new_hull - 5)
                        new_flight_log.append("Turbulent emergence: hull stress -5 from residual shear.")
                    new_stats_void = dict(new_stats_tick)
                    new_stats_void["void_arrivals"] = int(new_stats_void.get("void_arrivals", 0)) + 1
                    new_stats_void["void_resonance"] = int(new_stats_void.get("void_resonance", 0)) + int(round(resonance))
                    new_stats_tick = new_stats_void
                    new_void = None
                    evt_id = f"evt_{new_tick}_{len(new_events) + 1}"
                    new_events.append(
                        GameEvent(
                            id=evt_id,
                            kind="void",
                            title=f"Void Arrival: {dest_name}",
                            message=f"The Hollow Between releases your hull into {dest_name}.",
                            tick=new_tick,
                            dismissed=False,
                        )
                    )
                else:
                    new_void = VoidTraversalState(
                        origin_system_id=new_void.origin_system_id,
                        destination_system_id=new_void.destination_system_id,
                        started_tick=new_void.started_tick,
                        arrival_tick=new_void.arrival_tick,
                        duration_ticks=new_void.duration_ticks,
                        stability=stability,
                        storms_weathered=storms_weathered,
                        resonance=resonance,
                    )

            # 10. Away-team expeditions resolve on the tick, then return their crews
            resolved_away_ids: set[str] = set()
            away_logs: list[str] = []
            away_credits = 0
            away_research = 0
            new_cargo = dict(cur_ship.cargo)
            new_standings = dict(cur_ship.faction_standings)
            new_contracts = cur_ship.active_contracts
            new_away_completed = set(cur_ship.away_completed)
            away_stats = dict(new_stats_tick)
            away_crew_by_id = {member.id: member for member in new_crew}
            for mission in cur_ship.away_missions:
                if new_tick < mission.started_tick + mission.duration_ticks:
                    continue
                mission_type = get_away_mission_type(mission.mission_type)
                mission_system = updated_systems.get(mission.system_id)
                mission_body = (
                    next((body for body in mission_system.bodies if body.id == mission.body_id), None)
                    if mission_system is not None else None
                )
                if mission_type is None or mission_body is None:
                    resolved_away_ids.add(mission.id)
                    away_logs.append(
                        f"AWAY TEAM LOST: the expedition at {mission.body_name or mission.body_id} could not be recovered."
                    )
                    continue
                team = tuple(
                    away_crew_by_id[cid] for cid in mission.crew_ids if cid in away_crew_by_id
                )
                if not team:
                    resolved_away_ids.add(mission.id)
                    away_logs.append(
                        f"AWAY TEAM LOST: no surviving crew returned from {mission.body_name or mission.body_id}."
                    )
                    away_stats["away_missions"] = int(away_stats.get("away_missions", 0)) + 1
                    away_stats["away_failures"] = int(away_stats.get("away_failures", 0)) + 1
                    continue
                outcome = resolve_away_mission(
                    mission, mission_type, mission_body, team, self.state.galaxy_seed
                )
                resolved_away_ids.add(mission.id)
                away_logs.append(outcome["log"])

                for crew_id, amount in outcome["xp"].items():
                    member = away_crew_by_id.get(crew_id)
                    if member is None:
                        continue
                    updated_member, promoted = award_crew_xp(member, amount)
                    away_crew_by_id[crew_id] = updated_member
                    if promoted:
                        away_logs.append(
                            f"CREW PROMOTION: {updated_member.name} reached skill {updated_member.skill} in the field."
                        )
                for crew_id in mission.crew_ids:
                    member = away_crew_by_id.get(crew_id)
                    if member is None:
                        continue
                    updated_member, earned_medals = award_service_medals(
                        replace(
                            member,
                            away_missions=member.away_missions + 1,
                        )
                    )
                    away_crew_by_id[crew_id] = updated_member
                    if earned_medals:
                        away_logs.append(
                            f"SERVICE MEDAL: {updated_member.name} awarded "
                            f"{', '.join(earned_medals)}."
                        )
                for crew_id, injury_ticks in outcome["injuries"].items():
                    member = away_crew_by_id.get(crew_id)
                    if member is None:
                        continue
                    away_crew_by_id[crew_id] = replace(
                        member, injury_ticks=max(member.injury_ticks, int(injury_ticks))
                    )
                if outcome["morale"]:
                    updated_crew, morale_log = apply_morale_event(
                        tuple(away_crew_by_id.values()),
                        float(outcome["morale"]),
                        f"expedition {mission_type.name}",
                    )
                    away_crew_by_id = {member.id: member for member in updated_crew}
                    if morale_log:
                        away_logs.append(morale_log)
                for item_id, quantity in outcome["cargo"]:
                    granted, overflow = self._grant_cargo(new_cargo, item_id, quantity)
                    item_name = get_item_info(item_id).name
                    if granted:
                        away_logs.append(f"AWAY SALVAGE: +{granted} {item_name} recovered.")
                    if overflow:
                        away_logs.append(f"HOLD FULL: {overflow} {item_name} left at the site.")
                away_credits += int(outcome["credits"])
                away_research += int(outcome["research"])
                if outcome["success"]:
                    new_away_completed.add(site_key(mission.mission_type, mission.body_id))
                if outcome["standing"] and mission_system is not None:
                    faction_id = get_faction_id_from_name(mission_system.faction)
                    if faction_id:
                        new_standings[faction_id] = min(
                            100, new_standings.get(faction_id, 0) + int(outcome["standing"])
                        )
                if outcome["contract_progress"]:
                    new_contracts, contract_logs = self._progress_contracts(
                        outcome["contract_category"],
                        int(outcome["contract_progress"]),
                        new_contracts,
                    )
                    away_logs.extend(contract_logs)
                new_mastery, xp_logs = self._award_pilot_xp(
                    30 if outcome["critical"] else (20 if outcome["success"] else 8),
                    new_mastery,
                )
                away_logs.extend(xp_logs)

                away_stats["away_missions"] = int(away_stats.get("away_missions", 0)) + 1
                if outcome["success"]:
                    away_stats["away_successes"] = int(away_stats.get("away_successes", 0)) + 1
                else:
                    away_stats["away_failures"] = int(away_stats.get("away_failures", 0)) + 1
                    away_stats["away_injuries"] = int(away_stats.get("away_injuries", 0)) + len(outcome["injuries"])
                away_stats["credits_earned"] = int(away_stats.get("credits_earned", 0)) + int(outcome["credits"])

                evt_id = f"evt_{new_tick}_{len(new_events) + 1}"
                new_events.append(
                    GameEvent(
                        id=evt_id,
                        kind="away",
                        title=f"Away Team: {mission_type.name}",
                        message=outcome["log"],
                        tick=new_tick,
                        dismissed=False,
                    )
                )

            if resolved_away_ids:
                new_away_missions = tuple(
                    mission for mission in cur_ship.away_missions if mission.id not in resolved_away_ids
                )
                new_crew = tuple(away_crew_by_id.get(member.id, member) for member in new_crew)
                if away_research:
                    new_research = ResearchState(
                        points=new_research.points + away_research,
                        progress=new_research.progress + away_research,
                        active_project_id=new_research.active_project_id,
                        completed=new_research.completed,
                        queue=new_research.queue,
                    )
                new_stats_tick = away_stats
            else:
                new_away_missions = cur_ship.away_missions

            new_trade_orders = cur_ship.trade_orders
            delivery_credits = 0
            delivery_logs: list[str] = []
            if new_trade_orders:
                new_trade_orders, delivery_credits, delivery_logs, delivered, new_econ = self._resolve_quantum_orders(
                    new_trade_orders, new_tick, updated_systems, new_econ
                )
                if delivered:
                    new_contracts, contract_logs = self._progress_contracts(
                        "delivery", delivered, new_contracts
                    )
                    delivery_logs.extend(contract_logs)
                    new_stats_tick["deliveries"] = int(new_stats_tick.get("deliveries", 0)) + delivered
                    new_stats_tick["credits_earned"] = int(new_stats_tick.get("credits_earned", 0)) + delivery_credits
                    new_events.append(
                        GameEvent(
                            id=f"evt_{new_tick}_{len(new_events) + 1}",
                            kind="trade",
                            title="Quantum Freight Delivered",
                            message=" ".join(delivery_logs[-3:]),
                            tick=new_tick,
                            dismissed=False,
                        )
                    )

            # Remote patrols hunt pirates on a slow cycle. They earn bounty credits
            # and a little XP, but can take return fire while the flagship is away.
            patrol_credits = 0
            patrol_contacts = 0
            patrol_logs: list[str] = []
            if new_tick % PATROL_SWEEP_TICKS == 0:
                patrolled: list[FleetShip] = []
                for escort in new_fleet_ships:
                    system = updated_systems.get(escort.assigned_system_id)
                    if (
                        escort.assigned_system_id == new_current_system_id
                        or escort.hull <= 0
                        or system is None
                    ):
                        patrolled.append(escort)
                        continue
                    standing = new_standings.get(
                        get_faction_id_from_name(system.faction), 0
                    )
                    sweep = resolve_patrol_sweep(
                        escort,
                        system,
                        new_tick,
                        self.state.galaxy_seed,
                        standing,
                    )
                    new_hull = max(0, escort.hull - sweep["hull_damage"])
                    patrolled.append(
                        replace(
                            escort,
                            hull=new_hull,
                            status=(
                                "destroyed"
                                if new_hull <= 0
                                else (
                                    "damaged"
                                    if new_hull < escort.max_hull * 0.5
                                    else "escorting"
                                )
                            ),
                            experience=min(
                                FLEET_MAX_EXPERIENCE,
                                escort.experience + sweep["experience"],
                            ),
                            battles=escort.battles + (1 if sweep["contacted"] else 0),
                            patrol_credits=escort.patrol_credits + sweep["credits"],
                            patrol_contacts=escort.patrol_contacts
                            + (1 if sweep["contacted"] else 0),
                        )
                    )
                    patrol_credits += sweep["credits"]
                    if sweep["contacted"]:
                        patrol_contacts += 1
                        patrol_logs.append(sweep["text"])
                new_fleet_ships = tuple(patrolled)
            if patrol_credits:
                new_stats_tick["credits_earned"] = (
                    int(new_stats_tick.get("credits_earned", 0)) + patrol_credits
                )
                new_stats_tick["patrol_bounties"] = (
                    int(new_stats_tick.get("patrol_bounties", 0)) + patrol_credits
                )
                new_flight_log.extend(patrol_logs[-2:])

            fleet_upkeep_cost = (
                fleet_upkeep(new_fleet_ships) if month_rollover else 0
            )
            gross_credits = (
                cur_ship.credits
                + outpost_credits
                - wage_cost
                + new_credits_delta
                + away_credits
                + delivery_credits
                + patrol_credits
                + bond_credits
            )
            fleet_paid = gross_credits >= fleet_upkeep_cost
            if month_rollover and fleet_upkeep_cost and not fleet_paid:
                new_fleet_ships = tuple(
                    replace(
                        ship,
                        status="damaged" if ship.hull > 0 else ship.status,
                    )
                    for ship in new_fleet_ships
                )
                crew_logs.append(
                    f"FLEET PAY SHORTFALL: {fleet_upkeep_cost} cr due; "
                    "escorts stand down to damaged readiness."
                )
            new_credits = max(0, gross_credits - fleet_upkeep_cost)

            if new_flight_log_research:
                new_flight_log.append(new_flight_log_research)
            new_flight_log.extend(faction_logs[-3:])
            # Preserve older notable war lines even when a busy tick overflows three.
            new_flight_log.extend(line for line in faction_logs[:-3] if is_notable(line))
            # A war the player never hears about is not a war. Captures, treaties and
            # eliminations become dismissable cockpit notifications as well as log lines.
            new_events.extend(self.war_news_events(faction_logs, new_tick, new_events))
            if month_rollover:
                crew_logs.append(
                    f"MONTH END: crew payroll runs {crew_upkeep(new_crew)} cr/month, "
                    f"fleet upkeep {fleet_upkeep_cost} cr/month; treasury {new_credits} cr."
                )
            new_flight_log.extend(crew_logs[-2:])
            new_flight_log.extend(away_logs[-6:])
            new_flight_log.extend(delivery_logs[-4:])
            new_ship = self._clone_ship(
                hull=new_hull,
                shield=new_shield,
                credits=new_credits,
                cargo=new_cargo,
                crew=new_crew,
                reactor=new_reactor,
                current_system_id=new_current_system_id,
                orbiting_body_id=new_orbiting_body_id,
                landed_body_id=new_landed_body_id,
                travel=new_travel,
                waypoint_au=new_waypoint_au,
                waypoint_angle=new_waypoint_angle,
                void_traversal=new_void,
                away_missions=new_away_missions,
                away_completed=tuple(sorted(new_away_completed)),
                trade_orders=new_trade_orders,
                mastery=new_mastery,
                fleet_drones=new_drones,
                fleet_ships=new_fleet_ships,
                faction_standings=new_standings,
                active_contracts=new_contracts,
                flight_log=tuple(trim_log(new_flight_log)),
            )

            # Fresh wars displace civilians: queue one refugee-fleet plea unless an
            # unresolved plea already waits in the inbox.
            refugee_pleas = refugee_messages_for_new_wars(
                {w.id for w in self.state.wars},
                new_wars,
                self.state.messages,
                new_tick,
            )
            # The Collective notices rising captains once: a first compact offer.
            quantum_offers = quantum_offer_for_standing(
                new_standings,
                self.state.messages,
                new_tick,
            )
            self.state = self._clone_state(
                ship=new_ship,
                systems=updated_systems,
                visited_systems=new_visited_systems,
                stats=new_stats_tick,
                active_combat=new_combat,
                time=new_time,
                economy=new_econ,
                ai_captains=new_ai_captains,
                events=tuple(new_events[-50:]),
                character=new_character,
                research=new_research,
                outposts=tuple(updated_outposts),
                depots=tuple(updated_depots),
                wars=new_wars,
                faction_economies=new_faction_economies,
                trade_links=new_trade_links,
                eliminated_factions=new_eliminated,
                messages=tuple(self.state.messages) + tuple(refugee_pleas) + tuple(quantum_offers),
            )

            self._run_trade_automation()
            self._run_quantum_automation()
            decision = (
                self.maybe_trigger_decision("tick", num_ticks) if self.allow_decision_events else None
            )
            payload = {
                "ticks_advanced": num_ticks,
                "stardate": round(new_stardate, 2),
                "date": new_time.current_date,
                "tick": new_tick,
                "elapsed_days": round(new_days, 2),
                "shield_recharged": shield_recharged,
                "drone_cargo_harvested": drone_cargo_harvested,
                "drone_credits_harvested": drone_credits_harvested,
                "patrol_credits": patrol_credits,
                "patrol_contacts": patrol_contacts,
                "fleet_upkeep_cost": fleet_upkeep_cost,
                "fleet_upkeep_paid": fleet_paid,
                "war_bond_payouts": bond_credits,
                "reactor_heat": round(new_reactor.heat, 1),
                "reactor_efficiency": round(reactor_output_efficiency(new_reactor, float(equipment.get("reactor_output", 0.0))), 3),
                "reactor_hull_damage": reactor_hull_damage,
                "reactor_critical": bool(reactor_report["critical"]),
                "time_scale": new_time.time_scale,
                "is_paused": new_time.is_paused,
            }
            if decision:
                payload["decision"] = decision
            return payload

    def emit_event(self, kind: str, title: str, message: str) -> GameEvent:
        """Create and append a cockpit popup GameEvent."""
        with self.lock:
            cur_tick = self.state.time.tick
            evt = GameEvent(
                id=f"evt_{cur_tick}_{len(self.state.events) + 1}",
                kind=str(kind),
                title=str(title),
                message=str(message),
                tick=cur_tick,
                dismissed=False,
            )
            updated = list(self.state.events) + [evt]
            self.state = self._clone_state(events=tuple(updated[-50:]))
            return evt

    def dismiss_event(self, event_id: str) -> tuple[bool, str]:
        """Mark a cockpit popup GameEvent as dismissed."""
        with self.lock:
            target = str(event_id).strip()
            updated: list[GameEvent] = []
            found = False
            for evt in self.state.events:
                if evt.id == target:
                    updated.append(replace(evt, dismissed=True))
                    found = True
                else:
                    updated.append(evt)
            if not found:
                return False, f"Event '{target}' not found."
            self.state = self._clone_state(events=tuple(updated))
            return True, f"Event '{target}' dismissed."

    def pause_time(self) -> tuple[bool, str]:
        """Pause simulation temporal clock while preserving current playback rate."""
        with self.lock:
            cur = self.state.time
            saved_speed = cur.speed if cur.speed > 0.0 else 1.0
            new_time = TimeState(
                tick=cur.tick,
                stardate=cur.stardate,
                speed=saved_speed,
                is_paused=True,
                time_scale="PAUSED",
                elapsed_days=cur.elapsed_days,
            )
            self.state = self._clone_state(time=new_time)
            return True, "Simulation clock paused."

    def resume_time(self) -> tuple[bool, str]:
        """Resume simulation temporal clock restoring previous speed multiplier."""
        with self.lock:
            cur = self.state.time
            resumed_speed = cur.speed if cur.speed > 0.0 else 1.0
            scale_str = f"{int(resumed_speed)}x" if resumed_speed.is_integer() else f"{resumed_speed}x"
            new_time = TimeState(
                tick=cur.tick,
                stardate=cur.stardate,
                speed=resumed_speed,
                is_paused=False,
                time_scale=scale_str,
                elapsed_days=cur.elapsed_days,
            )
            self.state = self._clone_state(time=new_time)
            return True, f"Simulation clock resumed at {scale_str} speed."

    def set_time_speed(self, speed: float) -> tuple[bool, str]:
        """Set simulation speed multiplier (0.0x to 10.0x)."""
        with self.lock:
            cur = self.state.time
            clamped = max(0.0, min(10.0, float(speed)))
            is_paused = (clamped == 0.0)
            time_scale = "PAUSED" if is_paused else (f"{int(clamped)}x" if clamped.is_integer() else f"{clamped}x")
            new_time = TimeState(
                tick=cur.tick,
                stardate=cur.stardate,
                speed=clamped if not is_paused else (cur.speed if cur.speed > 0.0 else 1.0),
                is_paused=is_paused,
                time_scale=time_scale,
                elapsed_days=cur.elapsed_days,
            )
            self.state = self._clone_state(time=new_time)
            return True, f"Simulation clock speed set to {time_scale}."

    def step_time(self, num_ticks: int = 1) -> tuple[bool, str, dict[str, Any]]:
        """Advance simulation by a discrete number of ticks."""
        summary = self.tick(max(1, int(num_ticks)))
        return True, f"Advanced {summary['ticks_advanced']} tick(s). Date: {summary['date']} (Tick #{summary['tick']}).", summary

