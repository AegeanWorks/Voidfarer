"""Deterministic state machine and simulation engine for VoidFarer."""

from __future__ import annotations

from dataclasses import asdict, replace
import math
import random
import threading
from typing import Any, Sequence

from voidfarer.enemies import (
    ENEMY_ARCHETYPES,
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
    apply_morale_event,
    calculate_crew_bonuses,
    crew_catalog,
    crew_upkeep,
    get_crew_role,
    recruit_crew_member,
    shore_leave_restore,
    tick_crew,
)
from voidfarer.character import (
    ABILITY_CATALOG,
    MAX_STARTING_SKILL_TOTAL,
    SKILL_CATALOG,
    STARTING_SKILL_BASE,
    STARTING_SKILL_POINTS,
    ability_ready,
    advance_age,
    award_character_xp,
    skill_bonus,
    start_ability_cooldown,
    tick_ability_cooldowns,
    train_skill,
)
from voidfarer.codex import build_codex_report, get_codex_entry
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
    generate_faction_leaders,
    leader_for,
    simulate_faction_behaviors,
)
from voidfarer.fleet import (
    ESCORT_CATALOG,
    apply_fleet_casualties,
    build_fleet_ship,
    fleet_damage,
    fleet_evasion_bonus,
    get_escort_template,
    repair_fleet_ships,
)
from voidfarer.navigation import (
    generate_void_lanes,
    route_plan,
    shortest_route,
    system_has_black_hole,
    void_route_plan,
)
from voidfarer.outposts import (
    OUTPOST_MAP,
    OUTPOST_MODULE_CATALOG,
    OUTPOST_TYPES,
    build_outpost,
    can_build_on,
    get_outpost_type,
    outpost_tick_production,
    upgrade_outpost,
)
from voidfarer.research import (
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
    VOID_GATE_SYSTEM_IDS,
    GalaxyGenerator,
    black_hole_body,
    compute_scientific_planet_properties,
    get_colony_tier,
    step_population_dynamics,
)
from voidfarer.messaging import choice_by_id, follow_up_message, tree_catalog, tree_root_message
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
from voidfarer.shipmods import (
    CATALOG_SHIP_MODS,
    SHIP_MOD_SLOTS,
    calculate_ship_mod_bonuses,
    get_available_ship_mods,
    get_ship_mod,
    get_ship_mod_sell_value,
    slot_label,
)
from voidfarer.models import (
    AICaptain,
    BountyContract,
    CelestialBody,
    CodexState,
    CombatEncounter,
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
    TravelState,
    TutorialState,
    TutorialStep,
    VoidTraversalState,
    WarState,
)
from voidfarer.frontier import (
    MERCENARY_CATALOG,
    generate_ai_captains,
    generate_depots,
    generate_welcome_messages,
    simulate_ai_trade,
)
from voidfarer.retention import (
    CATALOG_RELICS,
    PILOT_TALENTS,
    calculate_passive_multipliers,
    generate_contract,
    generate_initial_contracts,
    roll_relic_drop,
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


class SimulationEngine:
    """Coordinates space flight, star navigation, fleet drones, upgrades, and tactical combat."""

    MIN_SURVEY_SENSOR_POWER = 5.0
    SURVEY_COMPLETION_CREDITS = 300
    SURVEY_COMPLETION_XP = 120

    def __init__(self, seed: int = 42, state: GameState | None = None) -> None:
        self.lock = threading.RLock()
        self.seed = seed
        self.rng = random.Random(seed)

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
                if (updated_body.station_dockable or updated_body.landable) and updated_body.population == 0:
                    pop = 120_000_000 + idx * 45_000_000 if updated_body.landable else 250_000 + idx * 85_000
                    gov = "Science Directorate" if updated_body.body_type == "research_outpost" else gov_map.get(sys_obj.faction, "Colonial Republic")
                    updated_body = replace(
                        updated_body,
                        faction=sys_obj.faction if updated_body.faction == "Unclaimed" else updated_body.faction,
                        population=pop,
                        government=gov if updated_body.government == "None" else updated_body.government,
                    )
                    body_changed = True
                if updated_body.body_type != "star" and ("(" not in updated_body.atmosphere or (updated_body.habitability == 0.0 and updated_body.body_type not in ("gas_giant", "ringed_giant", "ice_giant", "methane_storm", "lava_world"))):
                    rad_seed = 4000.0 + ((idx + len(sys_id)) % 9) * 6500.0
                    grav_seed = 0.65 + ((idx * 3 + len(sys_id)) % 7) * 0.22
                    jitter_seed = ((idx * 5 + len(sys_id)) % 9) - 4
                    phys = compute_scientific_planet_properties(
                        body_type=updated_body.body_type,
                        spectral_type=sys_obj.spectral_type,
                        orbit_radius_au=updated_body.orbit_radius,
                        rad_sample=rad_seed,
                        grav_sample=grav_seed,
                        temp_jitter=jitter_seed,
                        hazards=updated_body.hazards,
                    )
                    updated_body = replace(
                        updated_body,
                        radius_km=float(phys["radius_km"]),
                        gravity=float(phys["gravity"]),
                        atmosphere=str(phys["atmosphere"]),
                        temperature_c=int(phys["temperature_c"]),
                        habitability=float(phys["habitability"]),
                    )
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
        if updates:
            self.state = self._clone_state(**updates)

    def _clone_ship(self, **kwargs: Any) -> ShipState:
        """Create a new ShipState preserving all unspecified telemetry and inventory attributes."""
        cur = self.state.ship
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
            cargo=kwargs.get("cargo", cur.cargo),
            cargo_capacity=kwargs.get("cargo_capacity", cur.cargo_capacity),
            current_system_id=kwargs.get("current_system_id", cur.current_system_id),
            orbiting_body_id=kwargs.get("orbiting_body_id", cur.orbiting_body_id),
            power=kwargs.get("power", cur.power),
            reactor=kwargs.get("reactor", cur.reactor),
            upgrades=kwargs.get("upgrades", cur.upgrades),
            equipped_upgrades=kwargs.get("equipped_upgrades", cur.equipped_upgrades),
            ship_mods=kwargs.get("ship_mods", cur.ship_mods),
            fleet_drones=kwargs.get("fleet_drones", cur.fleet_drones),
            fleet_ships=kwargs.get("fleet_ships", cur.fleet_ships),
            battle_stance=kwargs.get("battle_stance", cur.battle_stance),
            crew=kwargs.get("crew", cur.crew),
            weapons=kwargs.get("weapons", cur.weapons),
            primary_weapon=kwargs.get("primary_weapon", cur.primary_weapon),
            message_bonuses=kwargs.get("message_bonuses", cur.message_bonuses),
            flight_log=kwargs.get("flight_log", cur.flight_log),
            streak=kwargs.get("streak", cur.streak),
            relics=kwargs.get("relics", cur.relics),
            mastery=kwargs.get("mastery", cur.mastery),
            active_contracts=kwargs.get("active_contracts", cur.active_contracts),
            tactical_combo=kwargs.get("tactical_combo", cur.tactical_combo),
            near_miss_scanner_bonus=kwargs.get("near_miss_scanner_bonus", cur.near_miss_scanner_bonus),
            tutorial=kwargs.get("tutorial", cur.tutorial),
            story=kwargs.get("story", cur.story),
            faction_standings=kwargs.get("faction_standings", cur.faction_standings),
            corp_standings=kwargs.get("corp_standings", cur.corp_standings),
            allies=kwargs.get("allies", cur.allies),
            landed_body_id=kwargs["landed_body_id"] if "landed_body_id" in kwargs else cur.landed_body_id,
            travel=kwargs["travel"] if "travel" in kwargs else cur.travel,
            void_traversal=kwargs["void_traversal"] if "void_traversal" in kwargs else cur.void_traversal,
        )

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
            eliminated_factions=kwargs.get("eliminated_factions", cur.eliminated_factions),
            codex=kwargs.get("codex", cur.codex),
            local_dock_purchases=kwargs.get("local_dock_purchases", cur.local_dock_purchases),
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
        return calculate_crew_bonuses(target.crew)

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

        return PilotMastery(
            level=level,
            xp=new_xp,
            next_level_xp=next_xp,
            talent_points=points,
            specializations=current_mastery.specializations,
        ), logs

    def _progress_contracts(self, category: str, amount: int = 1) -> tuple[tuple[BountyContract, ...], list[str]]:
        """Advance matching active contracts toward completion objectives."""
        updated: list[BountyContract] = []
        logs: list[str] = []
        for c in self.state.ship.active_contracts:
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
            self.seed = int(seed)
            self.rng = random.Random(self.seed)
            self.state = self._create_initial_state(self.seed)
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
        updated_character = replace(character, name=name, age=age, background=background, skills=skills)
        updated_ship = self._clone_ship(commander_name=name)
        self.state = self._clone_state(character=updated_character, ship=updated_ship)

    def load_state(self, state: GameState) -> tuple[bool, str]:
        """Replace the live universe with a loaded save and reseed its RNG stream."""
        with self.lock:
            self.seed = int(state.galaxy_seed)
            self.rng = random.Random(self.seed)
            self.state = state
            st = state.ship.story
            if not st.chapters:
                st = generate_initial_story()
            else:
                st = migrate_story_state(st)
            if st != state.ship.story:
                self.state = self._clone_state(ship=self._clone_ship(story=st))
            self._local_dock_purchases = dict(state.local_dock_purchases)
            self._bootstrap_frontier()
            return True, f"Loaded save at {state.time.current_date} (tick #{state.time.tick})."

    def _create_initial_state(self, seed: int) -> GameState:
        """Construct a fresh universe state rooted at Sol System."""
        generator = GalaxyGenerator(seed=seed)
        systems = generator.generate_galaxy()
        initial_contracts = generate_initial_contracts(self.rng)

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
            },
            corp_standings={
                "hyperion_dynamics": 0,
                "astraea_pharma": 0,
                "omnicorp_mining": 0,
                "nexus_cybernetics": 0,
                "vortex_fuel": 0,
            },
        )

        economy = generate_initial_economy(systems, self.rng)
        return GameState(
            version=1,
            galaxy_seed=seed,
            ship=ship,
            systems=systems,
            visited_systems=("sol",),
            active_anomaly=None,
            active_combat=None,
            stats={
                "jumps": 0,
                "scans": 0,
                "trades": 0,
                "anomalies_resolved": 0,
                "combat_victories": 0,
                "credits_earned": 0,
                "contracts_completed": 0,
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

            self.state = self._clone_state(
                ship=self._clone_ship(
                    hull=max(1, self.state.ship.hull - hull_damage),
                    shield=max(0, self.state.ship.shield - shield_damage),
                    credits=self.state.ship.credits + resonance_credits,
                    mastery=new_mastery,
                    orbiting_body_id=horizon_id,
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
                    destinations.append({
                        "system_id": sys_id,
                        "name": dest.name,
                        "fuel_estimate": void_route_plan(self.state.systems, self.state.galaxy_seed, cur_id, sys_id)["fuel_estimate"],
                    })

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
                "dive_ready": not reasons,
                "blockers": reasons,
                "destinations": destinations,
                "storm_chance": round(self._void_storm_chance(), 3),
                "shield": self.state.ship.shield,
                "fuel": self.state.ship.fuel,
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

            if self.state.ship.fuel < fuel_cost:
                return False, f"Insufficient Quantum Fuel: {fuel_cost} units required, {self.state.ship.fuel} available."

            # Execute jump
            self._local_dock_purchases.clear()
            new_fuel = self.state.ship.fuel - fuel_cost
            visited = set(self.state.visited_systems)
            visited.add(target_system_id)

            # Update streak (rewarding safe transit under loss aversion mechanics)
            new_streak = min(10, self.state.ship.streak + 1) if self.state.ship.hull >= 75 else self.state.ship.streak
            streak_mult = 1.0 + min(1.5, (new_streak - 1) * 0.15)
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

            if is_hostile_territory and self.rng.random() < min(0.95, 0.65 * encounter_risk_mult * (1.0 - encounter_evasion)):
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
                elif self.rng.random() < min(0.95, 0.40 * encounter_risk_mult * (1.0 - encounter_evasion)):
                    combat = generate_system_enemy(
                        system_id=target_system_id,
                        security=target_sys.security,
                        faction=target_sys.faction,
                        seed=self.rng.randint(1000, 99999),
                        threat_level=self.state.ship.mastery.level,
                    )
                    new_log.append(f"ALERT: Intercepted by hostile {combat.enemy_name}! Weapons locked.")

            if not combat and self.rng.random() < 0.35:
                anomaly = GalaxyGenerator.get_random_anomaly(self.rng.randint(1, 99999))
                new_log.append(f"WARNING: Deep-space anomaly detected! [{anomaly.title}]")

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
                fuel=new_fuel,
                credits=self.state.ship.credits + tut_cr,
                current_system_id=target_system_id,
                orbiting_body_id=target_sys.bodies[0].id if target_sys.bodies else None,
                landed_body_id=None,
                travel=None,
                fleet_drones=updated_drones,
                flight_log=tuple(new_log[-20:]),
                streak=new_streak,
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
            updated_systems = {}
            for sys_id, system in self.state.systems.items():
                updated_bodies = []
                for body in system.bodies:
                    d_angle = body.orbit_speed * 0.05 * 2
                    updated_pop = step_population_dynamics(body, 2) if body.population > 0 else body.population
                    updated_bodies.append(
                        replace(
                            body,
                            current_angle=(body.current_angle + d_angle) % (2.0 * math.pi),
                            population=updated_pop,
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
                new_ship = self._clone_ship(
                    ship_class=new_ship.ship_class,
                    hull=new_ship.hull,
                    max_hull=new_ship.max_hull,
                    shield=new_ship.shield,
                    max_shield=new_ship.max_shield,
                    fuel=new_ship.fuel,
                    max_fuel=new_ship.max_fuel,
                    credits=new_ship.credits,
                    cargo=new_ship.cargo,
                    cargo_capacity=new_ship.cargo_capacity,
                    current_system_id=new_ship.current_system_id,
                    orbiting_body_id=new_ship.orbiting_body_id,
                    landed_body_id=None,
                    travel=None,
                    power=new_ship.power,
                    upgrades=new_ship.upgrades,
                    equipped_upgrades=new_ship.equipped_upgrades,
                    fleet_drones=new_ship.fleet_drones,
                    flight_log=tuple(new_flight_log[-20:]),
                    streak=new_ship.streak,
                    relics=new_ship.relics,
                    mastery=new_ship.mastery,
                    active_contracts=new_ship.active_contracts,
                    tactical_combo=new_ship.tactical_combo,
                    near_miss_scanner_bonus=new_ship.near_miss_scanner_bonus,
                    tutorial=new_ship.tutorial,
                    story=new_ship.story,
                    faction_standings=new_ship.faction_standings,
                    corp_standings=new_ship.corp_standings,
                )

            self.state = self._clone_state(
                ship=new_ship,
                systems=updated_systems,
                visited_systems=tuple(sorted(visited)),
                active_anomaly=anomaly,
                active_combat=combat,
                stats=stats,
                time=transit_time,
                economy=new_econ,
                local_dock_purchases={},
            )

            msg = f"Jump successful: arrived in {target_sys.name}."
            if combat:
                msg += f" WARNING: Intercepted by {combat.enemy_name}!"
            return True, msg

    def compute_body_distance_au(
        self,
        target_body: CelestialBody,
        origin_body: CelestialBody | None = None,
    ) -> float:
        """Compute 2D polar Euclidean distance in AU between two bodies (or current orbit/star origin)."""
        origin = origin_body if origin_body is not None else self.orbiting_body
        if origin is not None:
            ox = origin.orbit_radius * math.cos(origin.current_angle)
            oy = origin.orbit_radius * math.sin(origin.current_angle)
        else:
            ox, oy = 0.0, 0.0
        tx = target_body.orbit_radius * math.cos(target_body.current_angle)
        ty = target_body.orbit_radius * math.sin(target_body.current_angle)
        return round(max(0.25, math.hypot(tx - ox, ty - oy)), 2)

    def orbit(self, body_id: str) -> tuple[bool, str]:
        """Establish orbital trajectory around a celestial body in the current system."""
        with self.lock:
            cur_sys = self.current_system
            matched = None
            for b in cur_sys.bodies:
                if b.id == body_id:
                    matched = b
                    break

            if not matched:
                return False, f"Celestial body '{body_id}' not found in {cur_sys.name}."

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
                credits=self.state.ship.credits + tut_cr,
                mastery=new_mastery,
                relics=tuple(list(self.state.ship.relics) + tut_relics),
                tutorial=new_tut,
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(ship=new_ship)
            return True, f"Now in orbit around {matched.name} ({distance_au:.1f} AU)."

    def start_travel(self, body_id: str, mode: str = "sublight") -> tuple[bool, str]:
        """Initiate sublight or quantum in-system transit toward a celestial body."""
        with self.lock:
            norm_mode = str(mode).strip().lower()
            if norm_mode not in ("sublight", "quantum"):
                return False, f"Invalid transit mode '{mode}'. Choose 'sublight' or 'quantum'."

            cur_sys = self.current_system
            matched = None
            for b in cur_sys.bodies:
                if b.id == body_id:
                    matched = b
                    break

            if not matched:
                return False, f"Celestial body '{body_id}' not found in {cur_sys.name}."

            origin = self.orbiting_body
            origin_id = origin.id if origin else None
            distance_au = self.compute_body_distance_au(matched, origin)

            if origin is not None and origin.id == matched.id:
                return False, f"Already in orbit around {matched.name}."

            active_travel = self.state.ship.travel
            if active_travel is not None:
                dest_name = next(
                    (b.name for b in cur_sys.bodies if b.id == active_travel.destination_body_id),
                    active_travel.destination_body_id,
                )
                return False, f"Already in transit to {dest_name}; arrival is scheduled for tick {active_travel.arrival_tick}."

            new_fuel = self.state.ship.fuel
            if norm_mode == "quantum":
                travel_map = self._map_effects(cur_sys)
                equipment = self._combined_equipment()
                passives = calculate_passive_multipliers(self.state.ship)
                research = self._research_bonuses()
                fuel_mult = (
                    float(travel_map["fuel_mult"])
                    * equipment["fuel_efficiency"]
                    * passives.get("fuel_efficiency", 1.0)
                    * research.get("fuel_efficiency", 1.0)
                    * (1.0 - min(0.25, self._skill("piloting")))
                )
                fuel_cost = max(2, int(math.ceil(distance_au * 1.0 * fuel_mult)))
                if self.state.ship.fuel < fuel_cost:
                    return False, f"Insufficient quantum fuel for micro-jump: need {fuel_cost}, have {self.state.ship.fuel}."
                new_fuel -= fuel_cost
                duration_ticks = 1
            else:
                engine_factor = max(0.4, self._effective_power("engines") / 25.0) * (1.0 + self._skill("piloting"))
                sublight_speed_au = max(0.35, 1.15 * engine_factor)
                duration_ticks = max(1, int(math.ceil(distance_au / sublight_speed_au)))

            cur_tick = self.state.time.tick
            travel = TravelState(
                origin_body_id=origin_id,
                destination_body_id=matched.id,
                mode=norm_mode,
                started_tick=cur_tick,
                arrival_tick=cur_tick + duration_ticks,
                distance_au=distance_au,
                duration_ticks=duration_ticks,
            )

            log_entry = f"Engaged {norm_mode} drive toward {matched.name} ({distance_au:.1f} AU, ETA {duration_ticks} tick(s))."
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry]

            new_ship = self._clone_ship(
                fuel=new_fuel,
                landed_body_id=None,
                travel=travel,
                flight_log=tuple(new_log[-20:]),
            )
            new_time = replace(self.state.time, is_paused=False) if self.state.time.is_paused else self.state.time
            self.state = self._clone_state(ship=new_ship, time=new_time)
            return True, log_entry

    def scan(self) -> tuple[bool, str, dict[str, Any]]:
        """Perform sensor sweep of current body or local space."""
        with self.lock:
            body = self.orbiting_body
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
                new_near_miss = 0.25
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

            self.state = self._clone_state(ship=new_ship, systems=systems, stats=stats)

            discovery_info = {
                "body_name": body.name,
                "body_type": body.body_type,
                "discovery": body.scan_discovery,
                "bounty": credit_bounty,
                "market_archetype": body.market_archetype,
                "hazards": list(body.hazards),
                "relic": found_relic.to_dict() if found_relic else None,
                "near_miss": is_near_miss,
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
            ok, msg = self._require_docked()
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
            ok, msg = self._require_docked()
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
            ok, msg = self._require_docked()
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
            character = start_ability_cooldown(self.state.character, ability_id)
            ship = self.state.ship
            new_hull = ship.hull
            new_shield = ship.shield
            new_credits = ship.credits
            new_combo = ship.tactical_combo
            new_research = self.state.research
            new_standings = dict(ship.faction_standings)
            msg = ""

            if ability_id == "overclock":
                reactor = replace(ship.reactor, heat=max(0.0, ship.reactor.heat + 8.0), mode="overdrive")
                msg = "Reactor Overclock engaged: core forced into overdrive (+8 heat)."
                new_ship = self._clone_ship(reactor=reactor)
            elif ability_id == "emergency_repair":
                gain = 15 + int(self.state.character.skills.get("engineering", 1)) * 5
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
                gain = 4 + int(self.state.character.skills.get("diplomacy", 1)) * 2
                new_standings[target_faction_id] = max(-100, min(100, new_standings.get(target_faction_id, 0) + gain))
                msg = f"Diplomatic Offensive improved {target_faction_id} standing by {gain}."
                new_ship = self._clone_ship(faction_standings=new_standings)
            elif ability_id == "science_burst":
                gain = 18 + int(self.state.character.skills.get("science", 1)) * 6
                new_research = replace(self.state.research, points=self.state.research.points + gain)
                msg = f"Science Burst generated {gain} research points."
                new_ship = self._clone_ship()
            elif ability_id == "trade_instinct":
                gain = 60 + int(self.state.character.skills.get("trade", 1)) * 30
                new_credits = ship.credits + gain
                msg = f"Trade Instinct yielded {gain} cr."
                new_ship = self._clone_ship(credits=new_credits)
            else:
                return False, f"Ability '{ability_id}' has no implemented effect."

            self.state = self._clone_state(
                ship=new_ship,
                character=character,
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
            research = replace(self.state.research, active_project_id=project_id, progress=0)
            self.state = self._clone_state(research=research)
            return True, f"Research directed toward {project.name} ({project.cost} points)."

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
            new_ship = self._clone_ship(credits=self.state.ship.credits - outpost_type.cost)
            self.state = self._clone_state(ship=new_ship, outposts=self.state.outposts + (outpost,))
            return True, f"Founded {outpost.name} for {outpost_type.cost} cr."

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
                    }
                    for aid, info in ABILITY_CATALOG.items()
                },
            }

    def get_research_report(self) -> dict[str, Any]:
        with self.lock:
            research = self.state.research
            active = get_research_project(research.active_project_id) if research.active_project_id else None
            return {
                "points": research.points,
                "progress": research.progress,
                "active_project_id": research.active_project_id,
                "active_project": active.to_dict() if active else None,
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
                    {
                        **o.to_dict(),
                        "production_effective": outpost_tick_production(o, yield_mult),
                    }
                    for o in self.state.outposts
                ],
                "catalog": [t.to_dict() for t in OUTPOST_TYPES],
                "modules": OUTPOST_MODULE_CATALOG,
            }

    def faction_diplomacy(self, faction_id: str, action: str, amount: int = 0) -> tuple[bool, str]:
        with self.lock:
            if faction_id not in CANONICAL_FACTIONS:
                return False, f"Unknown faction '{faction_id}'."
            if faction_id in self.state.eliminated_factions:
                return False, f"{CANONICAL_FACTIONS[faction_id].name} has been eliminated."
            act = action.strip().lower()
            standings = dict(self.state.ship.faction_standings)
            current = standings.get(faction_id, 0)
            leader = leader_for(self.state.faction_leaders, faction_id)
            diplomacy_bonus = self._skill("diplomacy") + self._research_bonuses()["diplomacy_bonus"]
            if act in ("improve", "negotiate"):
                gain = int(3 + diplomacy_bonus * 20 + min(5, max(0, amount)))
                standings[faction_id] = min(100, current + gain)
                self.state = self._clone_state(ship=self._clone_ship(faction_standings=standings))
                return True, f"Diplomatic talks with {CANONICAL_FACTIONS[faction_id].name}: standing {current:+d} -> {standings[faction_id]:+d}."
            if act in ("gift", "aid"):
                cost = max(100, int(amount) if amount else 300)
                if self.state.ship.credits < cost:
                    return False, f"Insufficient credits for aid package ({cost} cr)."
                gain = 5 + int(diplomacy_bonus * 20) + cost // 200
                standings[faction_id] = min(100, current + gain)
                new_ship = self._clone_ship(credits=self.state.ship.credits - cost, faction_standings=standings)
                self.state = self._clone_state(ship=new_ship)
                return True, f"Aid package delivered to {CANONICAL_FACTIONS[faction_id].name} ({cost} cr, +{gain} standing)."
            if act == "alliance":
                if current < 70:
                    return False, f"Alliance requires standing >= 70 (current {current:+d})."
                allies = tuple(sorted(set(self.state.ship.allies) | {faction_id}))
                new_ship = self._clone_ship(allies=allies)
                self.state = self._clone_state(ship=new_ship)
                return True, f"Alliance formed with {CANONICAL_FACTIONS[faction_id].name}."
            if act in ("peace", "ceasefire"):
                wars = []
                ended = False
                for war in self.state.wars:
                    if faction_id in (war.attacker_id, war.defender_id) and "sol_coalition" in (war.attacker_id, war.defender_id):
                        wars.append(replace(war, active=False))
                        ended = True
                    else:
                        wars.append(war)
                standings[faction_id] = min(100, current + 10)
                self.state = self._clone_state(
                    ship=self._clone_ship(faction_standings=standings),
                    wars=tuple(wars),
                )
                return (True, f"Ceasefire accepted by {CANONICAL_FACTIONS[faction_id].name}.") if ended else (False, "No active war with that faction.")
            if act in ("declare_war", "war"):
                if current <= -80:
                    return False, "Faction is already universally hostile."
                standings[faction_id] = -100
                war = WarState(
                    id=f"war_{self.state.time.tick}_sol_{faction_id}",
                    attacker_id="sol_coalition",
                    defender_id=faction_id,
                    started_tick=self.state.time.tick,
                )
                self.state = self._clone_state(
                    ship=self._clone_ship(faction_standings=standings),
                    wars=self.state.wars + (war,),
                )
                leader_note = f" Leader {leader.name} ({leader.behavior}) responds in kind." if leader else ""
                return True, f"War declared on {CANONICAL_FACTIONS[faction_id].name}.{leader_note}"
            return False, f"Unknown diplomacy action '{action}'."

    def buy_escort(self, escort_type: str, system_id: str | None = None) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_docked()
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
            ship = build_fleet_ship(escort_type, target_system, len(self.state.ship.fleet_ships))
            new_ship = self._clone_ship(
                credits=self.state.ship.credits - template["cost"],
                fleet_ships=self.state.ship.fleet_ships + (ship,),
            )
            self.state = self._clone_state(ship=new_ship)
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

    def repair_escorts(self, amount: int = 60) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_docked()
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

    def dismiss_escort(self, ship_id: str) -> tuple[bool, str]:
        with self.lock:
            target = next((s for s in self.state.ship.fleet_ships if s.id == ship_id), None)
            if not target:
                return False, f"Unknown escort '{ship_id}'."
            remaining = tuple(s for s in self.state.ship.fleet_ships if s.id != ship_id)
            self.state = self._clone_state(ship=self._clone_ship(fleet_ships=remaining))
            return True, f"Escort {target.name} decommissioned."

    def get_fleet_manager_report(self) -> dict[str, Any]:
        with self.lock:
            ships = self.state.ship.fleet_ships
            return {
                "ships": [s.to_dict() for s in ships],
                "catalog": ESCORT_CATALOG,
                "total_damage": fleet_damage(ships),
                "evasion_bonus": round(fleet_evasion_bonus(ships), 3),
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
            remaining = tuple(c for c in self.state.ship.crew if c.id != crew_id)
            self.state = self._clone_state(ship=self._clone_ship(crew=remaining))
            return True, f"Crew member {member.name} dismissed."

    def get_crew_report(self) -> dict[str, Any]:
        with self.lock:
            crew = self.state.ship.crew
            return {
                "crew": [c.to_dict() for c in crew],
                "roles": crew_catalog(),
                "bonuses": calculate_crew_bonuses(crew),
                "upkeep": crew_upkeep(crew),
                "capacity": 8,
                "active": len([c for c in crew if c.status == "active"]),
                "cash_flow": self.cash_flow(),
                "morale_warnings": [
                    f"{c.name} is near desertion" for c in crew if c.status == "active" and c.morale < 20.0
                ],
            }

    def cash_flow(self) -> dict[str, Any]:
        """Per-tick credit flow telemetry: crew upkeep against passive income estimates."""
        with self.lock:
            upkeep = crew_upkeep(self.state.ship.crew)
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
                production = outpost_tick_production(outpost, research_yield_mult)
                passive += float(production.get("credits", 0.0))
            return {
                "upkeep_per_tick": upkeep,
                "passive_per_tick": round(passive, 1),
                "net_per_tick": round(passive - upkeep, 1),
            }

    def install_weapon(self, weapon_id: str) -> tuple[bool, str]:
        with self.lock:
            ok, msg = self._require_docked()
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

    def trade(self, commodity_id: str, quantity: int, is_buy: bool) -> tuple[bool, str]:
        """Execute buy or sell commodity order at orbiting market."""
        with self.lock:
            body = self.orbiting_body
            if not body or not body.station_dockable:
                return False, "Docking authorization required: ship must orbit a station or habitable colony to trade."

            if quantity <= 0:
                return False, "Quantity must be greater than zero."

            comm = COMMODITY_MAP.get(commodity_id)
            if not comm:
                return False, f"Commodity '{commodity_id}' not traded here."

            sys_faction_id = get_faction_id_from_name(self.current_system.faction)
            standing = self.state.ship.faction_standings.get(sys_faction_id, 0)
            quote = calculate_dynamic_market_quote(
                self.current_system, body, comm, self.state.economy, faction_standing=standing
            )
            standing_factor = faction_standing_price_factor(standing)
            vol_per_unit = comm.volume

            cargo = dict(self.state.ship.cargo)
            stats = dict(self.state.stats)

            passives = calculate_passive_multipliers(self.state.ship)
            equipment = self._combined_equipment()

            # Geopolitical faction & corporate commercial mechanics
            faction_perks = get_faction_service_perks(sys_faction_id, standing)
            new_faction_standings = dict(self.state.ship.faction_standings)
            new_corp_standings = dict(self.state.ship.corp_standings)

            if is_buy:
                unit_price = quote.buy_price
                simulated_stocks = None
                market = self.state.economy.markets.get(self.current_system.id)
                if market is not None:
                    # Volume-aware execution: walk the local stockpile in slices so
                    # bulk orders move the price they pay (simulation, not a flat quote).
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
                        )
                        total_cost += slice_quote.buy_price * slice_qty
                        stocks[commodity_id] = max(MIN_STOCK, stocks.get(commodity_id, 50) - slice_qty)
                        remaining -= slice_qty
                    simulated_stocks = stocks
                else:
                    total_cost = unit_price * quantity
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
                msg = f"Purchased {quantity}x {quote.name} for {total_cost} cr{tariff_note}{impact_note}."
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
                cargo[commodity_id] = owned - quantity
                if cargo[commodity_id] == 0:
                    del cargo[commodity_id]
                stats["credits_earned"] += revenue
                impact_note = ""
                if quantity > 0 and avg_base_sell < quote.sell_price:
                    impact_pct = round((1.0 - (avg_base_sell / quote.sell_price)) * 100.0)
                    if impact_pct >= 1:
                        impact_note = f" (base avg {avg_base_sell:.0f}/unit, market impact -{impact_pct}%)"
                msg = f"Sold {quantity}x {quote.name} for {revenue} cr (trade margin: x{margin_mult:.2f}){corp_note}{impact_note}."

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

            return True, msg

    def buy_upgrade(self, upgrade_id: str) -> tuple[bool, str]:
        """Purchase and install a hardware upgrade module at an orbital station."""
        with self.lock:
            body = self.orbiting_body
            if not body or not body.station_dockable:
                return False, "Upgrade bay drydock requires docking at a station or colony."

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
            body = self.orbiting_body
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
            body = self.orbiting_body
            if not body or not body.station_dockable:
                return False, "Shipyard drydock authorization required: dock at a station or colony to commission a new chassis."

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
            if quantity <= 0:
                return False, "Quantity must be greater than zero."

            body = self.orbiting_body
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
            if quantity <= 0:
                return False, "Quantity must be greater than zero."
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
            body = self.orbiting_body
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
            drone_id = f"drone_{drone_type}_{len(self.state.ship.fleet_drones) + 1}"
            new_drone = FleetDrone(
                id=drone_id,
                name=f"{template['name']} #{len(self.state.ship.fleet_drones) + 1}",
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

    def combat_action(self, action: str) -> tuple[bool, str]:
        """Execute a tactical combat maneuver against an active hostile intercept."""
        with self.lock:
            combat = self.state.active_combat
            if not combat:
                return False, "No hostile ship in combat proximity."

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
            damaging_actions = {"fire_lasers", "drone_strike", "target_subsystem", "target_weapons", "target_shields"}
            enemy_miss = action in damaging_actions and intent == "evade" and self.rng.random() < 0.35
            weapon_miss = False
            enemy_hull_before = enemy_rem_hull
            enemy_shield_before = enemy_rem_shield
            fleet_ships = self.state.ship.fleet_ships
            fleet_volley = 0
            battle_stance = self.state.ship.battle_stance

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

                new_combo += 1
                crit_text = ""
                if new_combo >= 3:
                    shield_dmg = int(shield_dmg * 1.5)
                    hull_dmg = int(hull_dmg * 1.5)
                    crit_text = f" (TACTICAL OVERCHARGE x{new_combo}: +50% CRIT DAMAGE!)"

                if weapon_miss:
                    strike_desc = f"{weapon.name} firing solution failed; the shot went wide."
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

            elif action in ("target_subsystem", "target_weapons", "target_shields"):
                subsystem = "shields" if action == "target_shields" else "weapons"
                new_combo += 1
                if subsystem == "weapons":
                    enemy_rem_damage = max(6, int(combat.enemy_damage * 0.60))
                    strike_dmg = max(1, int(15 * enemy_guard))
                    if enemy_rem_shield > 0:
                        enemy_rem_shield = max(0, enemy_rem_shield - strike_dmg)
                    else:
                        enemy_rem_hull -= strike_dmg
                    strike_desc = f"Targeted strike hit enemy weapon arrays! Disabled fire-control (-40% enemy firepower) and dealt {strike_dmg} damage!"
                else:
                    shield_ion = max(1, int(40 * enemy_guard))
                    enemy_rem_shield = max(0, enemy_rem_shield - shield_ion)
                    strike_desc = f"Ion pulse targeted enemy shield generators! EMP cascade drained {shield_ion} MW shields!"

            elif action == "shield_absorb":
                boost = 30 + (25 if "dreadnought_tactics" in self.state.ship.mastery.specializations else 0)
                new_shield = min(self.state.ship.max_shield, new_shield + boost)
                mitigated = max(1, int(combat.enemy_damage * 0.35 * (1.5 if intent == "execute" else 1.0)))
                if new_shield >= mitigated:
                    new_shield -= mitigated
                else:
                    new_hull = max(0, new_hull - (mitigated - new_shield))
                    new_shield = 0
                msg = f"Shield capacitors overcharged (+{boost} MW). Enemy barrage deflected, taking only {mitigated} damage."
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
                )
                new_log = list(self.state.ship.flight_log[-19:]) + [msg]
                new_ship = self._clone_ship(hull=new_hull, shield=new_shield, tactical_combo=new_combo, streak=new_streak, flight_log=tuple(new_log[-20:]))
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
                return False, f"Unknown combat action '{action}'. Choices: fire_lasers, drone_strike, target_subsystem, shield_absorb, evasive_burn, flee."

            if enemy_miss:
                enemy_rem_hull = enemy_hull_before
                enemy_rem_shield = enemy_shield_before
                if not weapon_miss:
                    strike_desc = "Enemy AI jinked out of your firing solution; the strike missed."
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
                new_credits += combat.bounty_credits
                salvage_granted, salvage_overflow = self._grant_cargo(cargo, combat.salvage_commodity, 2)
                stats["combat_victories"] += 1
                stats["credits_earned"] += combat.bounty_credits
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

                msg = (
                    f"VICTORY: {combat.enemy_name} neutralized! "
                    f"Collected {combat.bounty_credits} cr bounty, salvaged {salvage_granted}x {combat.salvage_commodity}"
                    f"{f' ({salvage_overflow} jettisoned: hold full)' if salvage_overflow else ''}.{relic_note}{rep_note}"
                )
                log_entry = f"Combat outcome: {msg}"
                new_log = list(self.state.ship.flight_log[-19:]) + [log_entry] + contract_logs + xp_logs

                new_fleet_ships = tuple(
                    replace(s, experience=s.experience + 3, status="escorting" if s.hull > 0 else "destroyed")
                    for s in fleet_ships
                )
                victory_crew, morale_log = apply_morale_event(self.state.ship.crew, 5.0, "combat victory celebrated")
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
                    new_hull = max(0, new_hull - 15)
                    ability_note = " [ABILITY: Tachyon Lance phase-pierced your shields for 15 direct hull damage!]"
                    ability_cd = 2

            # Standard counter-battery
            inbound = int(enemy_rem_damage * (1.5 if intent == "execute" else 1.0))
            evasion_note = ""
            fleet_evasion = fleet_evasion_bonus(fleet_ships, battle_stance)
            if inbound > 0 and (equipment["evasion"] + mercenary_evasion + fleet_evasion) > 0.0 and self.rng.random() < (equipment["evasion"] + mercenary_evasion + fleet_evasion):
                inbound = 0
                evasion_note = " [Ion afterburners and escort screen evaded incoming fire!]"
            if inbound > 0 and fleet_ships:
                fleet_ships, absorbed = apply_fleet_casualties(fleet_ships, max(1, inbound // 2))
                if absorbed > 0:
                    inbound = max(0, inbound - absorbed)
                    evasion_note += f" Escort screen absorbed {absorbed} damage."
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
            )

            new_log = list(self.state.ship.flight_log[-19:]) + [msg]
            if breach_log:
                new_log.append(breach_log)
            new_ship = self._clone_ship(
                hull=new_hull,
                shield=new_shield,
                tactical_combo=new_combo,
                streak=new_streak,
                crew=breach_crew if breach_crew is not None else self.state.ship.crew,
                fleet_ships=fleet_ships,
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

            new_ship = self._clone_ship(
                hull=new_hull,
                fuel=new_fuel,
                credits=new_credits,
                cargo=cargo,
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

    def repair_hull(self, amount: int = 25) -> tuple[bool, str]:
        """Repair ship hull integrity at orbital station."""
        with self.lock:
            if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                return False, "Repair amount must be a positive integer."
            body = self.orbiting_body
            if not body or not body.station_dockable:
                return False, "Repair drydocks available at orbital stations or colonies only."

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
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [f"Drydock repair: +{actual} HP for {cost} cr."]),
            )

            self.state = self._clone_state(ship=new_ship)
            return True, f"Repairs completed: +{actual} HP restored for {cost} cr."

    def refuel(self, amount: int = 20) -> tuple[bool, str]:
        """Refuel quantum drive at orbital station."""
        with self.lock:
            if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
                return False, "Refuel amount must be a positive integer."
            body = self.orbiting_body
            if not body or not body.station_dockable:
                return False, "Fuel refinery available at orbital stations or colonies only."

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

            relic_msg = f" Discovered Precursor Relic [{relic.name}] ({relic.rarity.upper()})!" if relic else ""
            log_entry = f"CONTRACT CLAIMED: [{found.title}] rewarded {found.reward_credits} cr and {found.reward_xp} XP.{relic_msg}"
            new_log = list(self.state.ship.flight_log[-19:]) + [log_entry] + xp_logs

            stats = dict(self.state.stats)
            stats["credits_earned"] += found.reward_credits
            stats["contracts_completed"] = stats.get("contracts_completed", 0) + 1

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
                flight_log=tuple(new_log[-20:]),
            )

            self.state = self._clone_state(ship=new_ship, stats=stats)

            return True, f"Claimed {found.title}: +{found.reward_credits} cr, +{found.reward_xp} XP.{relic_msg} New contract: [{new_contract.title}].", {
                "reward_credits": found.reward_credits,
                "reward_xp": found.reward_xp,
                "relic": relic.to_dict() if relic else None,
                "new_contract": new_contract.to_dict(),
            }

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

    def get_status_snapshot(self) -> dict[str, Any]:
        """Produce a comprehensive JSON serializable telemetry snapshot for the HUD."""
        with self.lock:
            cur_sys = self.current_system
            orb_body = self.orbiting_body
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
                    }
                    for q in quotes
                ]

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
            return {
                "ship": self.state.ship.to_dict(),
                "current_system": cur_sys.to_dict(),
                "orbiting_body": orb_body.to_dict() if orb_body else None,
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
                "time": self.state.time.to_dict(),
                "stats": dict(self.state.stats),
                "codex": build_codex_report(self.state),
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
                    }
                    for aid, info in ABILITY_CATALOG.items()
                },
                "character_skill_catalog": {sid: dict(info) for sid, info in SKILL_CATALOG.items()},
                "research": {
                    **self.state.research.to_dict(),
                    "bonuses": self._research_bonuses(),
                    "active_project": (get_research_project(self.state.research.active_project_id).to_dict() if self.state.research.active_project_id and get_research_project(self.state.research.active_project_id) else None),
                    "available": [p.to_dict() for p in available_projects(self.state.research.completed, self.state.research.active_project_id)],
                    "catalog": [p.to_dict() for p in RESEARCH_PROJECTS],
                },
                "outposts": [o.to_dict() for o in self.state.outposts],
                "outpost_catalog": [t.to_dict() for t in OUTPOST_TYPES],
                "faction_leaders": [leader.to_dict() for leader in self.state.faction_leaders],
                "wars": [war.to_dict() for war in self.state.wars],
                "eliminated_factions": list(self.state.eliminated_factions),
                "crew": [c.to_dict() for c in self.state.ship.crew],
                "crew_roles": crew_catalog(),
                "crew_bonuses": calculate_crew_bonuses(self.state.ship.crew),
                "weapons": weapon_catalog(),
                "primary_weapon": self.state.ship.primary_weapon,
                "fleet_manager": {
                    "ships": [s.to_dict() for s in self.state.ship.fleet_ships],
                    "catalog": ESCORT_CATALOG,
                    "total_damage": fleet_damage(self.state.ship.fleet_ships),
                    "evasion_bonus": round(fleet_evasion_bonus(self.state.ship.fleet_ships), 3),
                },
                "ship_mods": {
                    "slots": list(SHIP_MOD_SLOTS),
                    "slot_labels": {slot: slot_label(slot) for slot in SHIP_MOD_SLOTS},
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
                "catalog_upgrades": [u.to_dict() for u in CATALOG_UPGRADES],
                "catalog_drones": CATALOG_DRONE_TEMPLATES,
                "catalog_talents": PILOT_TALENTS,
                "catalog_relics": [r.to_dict() for r in CATALOG_RELICS],
                "story_chapters": [c.to_dict() for c in CAMPAIGN_CHAPTERS],
                "story_chapters_map": {c.id: c.to_dict() for c in CAMPAIGN_CHAPTERS},
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
                "enemy_archetypes": {aid: asdict(a) for aid, a in ENEMY_ARCHETYPES.items()},
                "economy": self.state.economy.to_dict(),
                "inventory_manifest": get_inventory_manifest(self.state.ship.cargo),
                "trade_routes": get_galactic_trade_routes(self.state.systems, self.state.economy),
                "catalog_chassis": [c.to_dict() for c in CATALOG_CHASSIS],
                "available_chassis": [c.to_dict() for c in get_available_chassis(self.current_chassis_id)],
                "catalog_weapons": weapon_catalog(),
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
                "story_status": self.story_status(),
                "cash_flow": self.cash_flow(),
                "allies": list(self.state.ship.allies),
                "quests": self.get_quests(),
                "mercenary_catalog": MERCENARY_CATALOG,
                "fleet_stats": [
                    {
                        **d.to_dict(),
                        "kind": "mercenary" if d.drone_type == "mercenary" else "fleet",
                        "yield_rate": round(d.efficiency * (0.5 + d.integrity / 200.0), 2),
                    }
                    for d in self.state.ship.fleet_drones
                ],
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
                return True, f"{captain.name}: '{captain.description}' Quantum link trust increased."
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

    def _require_docked(self) -> tuple[bool, str]:
        if self.state.active_combat is not None:
            return False, "Depot operations are unavailable during combat."
        body = self.orbiting_body
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
            body = self.orbiting_body
            if not body or body.market_archetype == "none":
                return False, "Current orbital location has no commercial market exchange."
            comm = COMMODITY_MAP.get(item_id)
            if not comm:
                return False, f"Unknown commodity '{item_id}'."
            sys_faction_id = get_faction_id_from_name(self.current_system.faction)
            standing = self.state.ship.faction_standings.get(sys_faction_id, 0)
            quote = calculate_dynamic_market_quote(
                self.current_system, body, comm, self.state.economy, faction_standing=standing
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
            return True, log_entry

    def salvage_derelict(self) -> tuple[bool, str, dict[str, Any]]:
        """Board the current body's derelict hulk for cargo, credits, and hazard risk."""
        with self.lock:
            body = self.orbiting_body
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
            danger = max(0.05, min(0.65, site.danger - sensor_edge - crew_bonuses["boarding_defense"] * 0.5))
            success = self.rng.random() >= danger

            cargo = dict(self.state.ship.cargo)
            granted = 0
            if success:
                granted, overflow = self._grant_cargo(cargo, site.cargo_item, site.cargo_quantity)
                credits = site.credits
                hull_damage = 0
                heat_gain = 4.0
                outcome = "HULL STRIPPED"
                if overflow:
                    outcome += f" ({overflow} unit(s) left behind, hold full)"
            else:
                credits = max(25, site.credits // 4)
                hull_damage = 6 + int(danger * 22)
                heat_gain = 9.0
                outcome = "BOARDING ACCIDENT"

            reactor = self.state.ship.reactor
            max_heat = reactor_heat_capacity(reactor, equipment)
            new_reactor = replace(reactor, heat=min(max_heat, reactor.heat + heat_gain))
            new_hull = max(1, self.state.ship.hull - hull_damage)
            new_mastery, xp_logs = self._award_pilot_xp(55 if success else 25, self.state.ship.mastery)

            log_entry = (
                f"DERELICT SALVAGE [{outcome}]: {site.name}. +{credits} cr"
                + (f", +{granted} {site.cargo_item}" if granted else "")
                + (f", hull -{hull_damage}" if hull_damage else "")
                + f", reactor heat +{heat_gain:.0f}."
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
                flight_log=tuple(new_log[-20:]),
            )
            stats = dict(self.state.stats)
            stats["salvage"] = stats.get("salvage", 0) + 1
            stats["credits_earned"] = stats.get("credits_earned", 0) + credits
            systems = self._replace_system_body(body.id, salvage_claimed=True)
            self.state = self._clone_state(ship=new_ship, systems=systems, stats=stats)

            report = {
                "site": site.to_dict(),
                "success": success,
                "danger": round(danger, 2),
                "credits": credits,
                "cargo_item": site.cargo_item if granted else None,
                "cargo_quantity": granted,
                "hull_damage": hull_damage,
            }
            return True, log_entry, report

    def scoop_fuel(self) -> tuple[bool, str]:
        """Recover fuel from a star, gas giant, or ice body currently in orbit."""
        with self.lock:
            body = self.orbiting_body
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

            log_entry = (
                f"FUEL SCOOP: {profile['label']} at {body.name} recovered {gained} fuel "
                f"(reactor heat +{profile['heat']:.0f}, volatiles {new_tapped}/{reserve})."
            )
            new_ship = self._clone_ship(
                fuel=new_fuel,
                reactor=new_reactor,
                flight_log=tuple(list(self.state.ship.flight_log[-19:]) + [log_entry]),
            )
            stats = dict(self.state.stats)
            stats["scoops"] = stats.get("scoops", 0) + 1
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
            new_ship = self._clone_ship(credits=self.state.ship.credits - cost, crew=crew)
            self.state = self._clone_state(ship=new_ship)
            return True, f"{member.name} completed a training drill: skill {member.skill} -> {updated.skill} (-{cost} cr)."

    def shore_leave(self) -> tuple[bool, str]:
        """Grant fleet-wide shore leave at a docked station, restoring crew morale for credits."""
        with self.lock:
            body = self.orbiting_body
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
            ok, msg = self._require_docked()
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
            ok, msg = self._require_docked()
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

    def tick(self, num_ticks: int = 1) -> dict[str, Any]:
        """Advance the simulation universe by num_ticks."""
        with self.lock:
            if num_ticks <= 0:
                return {
                    "ticks_advanced": 0,
                    "stardate": round(self.state.time.stardate, 2),
                    "date": self.state.time.current_date,
                    "tick": self.state.time.tick,
                    "time_scale": self.state.time.time_scale,
                    "is_paused": self.state.time.is_paused,
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

            # 1. Orbital revolution: advance current_angle for every body in every star system
            updated_systems = {}
            for sys_id, system in self.state.systems.items():
                updated_bodies = []
                for body in system.bodies:
                    d_angle = body.orbit_speed * 0.05 * num_ticks
                    updated_pop = step_population_dynamics(body, num_ticks) if body.population > 0 else body.population
                    tapped, recharge_tick = recharge_volatile_reserve(
                        body.volatile_tapped,
                        body.volatile_recharge_tick,
                        new_tick,
                    )
                    updated_bodies.append(
                        replace(
                            body,
                            current_angle=(body.current_angle + d_angle) % (2.0 * math.pi),
                            population=updated_pop,
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
            econ_logs.extend(ai_logs[-5:])

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
            research_gain = 1 + int((new_character.skills.get("science", 1) - 1) * 0.5)
            research_yield_mult = 1.0 + float(self._research_bonuses()["outpost_yield"]) + self._skill("trade")
            updated_outposts = []
            updated_depots = list(self.state.depots)
            for outpost in self.state.outposts:
                production = outpost_tick_production(outpost, research_yield_mult)
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
                    population=int(outpost.population * (1.0 + 0.00005 * num_ticks)),
                    integrity=min(100.0, outpost.integrity + 0.1 * num_ticks),
                ))

            research_gain += int(equipment.get("research_per_tick", 0.0) * num_ticks)
            new_crew, wage_cost, crew_logs = tick_crew(cur_ship.crew, num_ticks, cur_ship.credits + outpost_credits, rng=self.rng)

            points = research_state.points + max(0, research_gain)
            progress = research_state.progress + max(0, research_gain)
            completed = list(research_state.completed)
            active_id = research_state.active_project_id
            if active_id:
                project = get_research_project(active_id)
                if project and progress >= project.cost:
                    completed.append(project.id)
                    new_flight_log_research = f"RESEARCH COMPLETE: {project.name}."
                    active_id = None
                    progress = 0
                else:
                    new_flight_log_research = ""
            else:
                new_flight_log_research = ""
            new_research = ResearchState(
                points=points,
                progress=progress,
                active_project_id=active_id,
                completed=tuple(dict.fromkeys(completed)),
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
            new_events = list(self.state.events)
            if cur_ship.travel is not None and new_tick >= cur_ship.travel.arrival_tick:
                new_orbiting_body_id = cur_ship.travel.destination_body_id
                new_landed_body_id = None
                new_travel = None
                cur_sys_obj = updated_systems.get(cur_ship.current_system_id, self.current_system)
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
                        title=f"Orbital Capture: {dest_name}",
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
            new_stats_tick = self.state.stats
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

            if new_flight_log_research:
                new_flight_log.append(new_flight_log_research)
            new_flight_log.extend(faction_logs[-3:])
            new_flight_log.extend(crew_logs[-2:])
            new_ship = self._clone_ship(
                hull=new_hull,
                shield=new_shield,
                credits=max(0, cur_ship.credits + outpost_credits - wage_cost + new_credits_delta),
                crew=new_crew,
                reactor=new_reactor,
                current_system_id=new_current_system_id,
                orbiting_body_id=new_orbiting_body_id,
                landed_body_id=new_landed_body_id,
                travel=new_travel,
                void_traversal=new_void,
                mastery=new_mastery,
                fleet_drones=new_drones,
                fleet_ships=new_fleet_ships,
                flight_log=tuple(new_flight_log[-20:]),
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
                eliminated_factions=new_eliminated,
            )

            return {
                "ticks_advanced": num_ticks,
                "stardate": round(new_stardate, 2),
                "date": new_time.current_date,
                "tick": new_tick,
                "elapsed_days": round(new_days, 2),
                "shield_recharged": shield_recharged,
                "drone_cargo_harvested": drone_cargo_harvested,
                "drone_credits_harvested": drone_credits_harvested,
                "reactor_heat": round(new_reactor.heat, 1),
                "reactor_efficiency": round(reactor_output_efficiency(new_reactor, float(equipment.get("reactor_output", 0.0))), 3),
                "reactor_hull_damage": reactor_hull_damage,
                "reactor_critical": bool(reactor_report["critical"]),
                "time_scale": new_time.time_scale,
                "is_paused": new_time.is_paused,
            }

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

