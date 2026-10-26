"""Captain's log and discovery codex: milestones, statistics, and rewards.

The codex is a deterministic projection of the saved game state. Milestones are
never tracked separately from play; each one reads a metric derived from the
existing universe, so legacy saves unlock retroactively without RNG drift.
Only claimed rewards are persisted, inside ``GameState.codex``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from voidfarer.models import GameState

MEGASTRUCTURE_TYPES = frozenset({
    "dyson_sphere",
    "ring_world",
    "quantum_relay",
    "wormhole",
    "solar_collector",
})


@dataclass(frozen=True)
class CodexCategory:
    """A thematic grouping of codex milestones."""

    id: str
    name: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "description": self.description}


@dataclass(frozen=True)
class CodexEntry:
    """One discovery milestone and its reward."""

    id: str
    category: str
    title: str
    description: str
    hint: str
    metric: str
    target: int
    reward_credits: int = 0
    reward_xp: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "hint": self.hint,
            "metric": self.metric,
            "target": self.target,
            "reward_credits": self.reward_credits,
            "reward_xp": self.reward_xp,
            "reward_summary": f"{self.reward_credits} CR / {self.reward_xp} XP",
        }


CODEX_CATEGORIES: tuple[CodexCategory, ...] = (
    CodexCategory("exploration", "Exploration", "Jumps, surveys, landings, wrecks, and megastructures."),
    CodexCategory("command", "Command", "Crew, escorts, outposts, and research."),
    CodexCategory("commerce", "Commerce", "Trade volume, profit, and completed contracts."),
    CodexCategory("combat", "Combat", "Hostile victories and anomaly resolutions."),
    CodexCategory("diplomacy", "Diplomacy", "First contact, alliances, and faction standing."),
    CodexCategory("legacy", "Legacy", "Messages, campaign, relics, and codex mastery."),
)

CODEX_ENTRIES: tuple[CodexEntry, ...] = (
    # Exploration
    CodexEntry(
        "first_light", "exploration", "First Light",
        "Complete the first hyperspace jump beyond the home system.",
        "Run `jump alpha_centauri` from Sol.",
        "jumps", 1, 150, 50,
    ),
    CodexEntry(
        "pathfinder", "exploration", "Pathfinder",
        "Chart three distinct star systems.",
        "Jump to two more systems.",
        "systems_visited", 3, 300, 100,
    ),
    CodexEntry(
        "cartographer", "exploration", "Cartographer",
        "Chart six distinct star systems.",
        "Follow hyperlanes deeper into the sector.",
        "systems_visited", 6, 600, 200,
    ),
    CodexEntry(
        "surveyor", "exploration", "Surveyor",
        "Complete ten planetary sensor sweeps.",
        "Orbit a body and run `scan`.",
        "scans", 10, 250, 100,
    ),
    CodexEntry(
        "deep_survey", "exploration", "Deep Survey",
        "Complete thirty planetary sensor sweeps.",
        "Sweep every body in the systems you visit.",
        "scans", 30, 800, 250,
    ),
    CodexEntry(
        "system_surveyor", "exploration", "System Surveyor",
        "Complete a full system survey.",
        "Scan every body in a single star system.",
        "systems_surveyed", 1, 400, 120,
    ),
    CodexEntry(
        "sector_cartographer", "exploration", "Sector Cartographer",
        "Complete three full system surveys.",
        "Finish survey sweeps across multiple systems.",
        "systems_surveyed", 3, 1200, 350,
    ),
    CodexEntry(
        "bootprint", "exploration", "Bootprint",
        "Land on a habitable world for the first time.",
        "Orbit a landable body and run `land <body_id>`.",
        "landings", 1, 200, 75,
    ),
    CodexEntry(
        "wreck_diver", "exploration", "Wreck Diver",
        "Board five derelicts.",
        "Run `salvage` while orbiting a derelict site.",
        "salvage", 5, 800, 250,
    ),
    CodexEntry(
        "fuel_rat", "exploration", "Fuel Rat",
        "Scoop fuel from a star, gas giant, or ice world.",
        "Orbit a scoopable body and run `scoop`.",
        "scoops", 1, 150, 50,
    ),
    CodexEntry(
        "field_team", "exploration", "Field Team",
        "Complete five away-team expeditions.",
        "Deploy an away team from the CREW tab while in orbit.",
        "away_missions", 5, 500, 160,
    ),
    CodexEntry(
        "corsair_bane", "combat", "Corsair Bane",
        "Defeat five pirate bands in direct engagement.",
        "Resolve pirate intercepts with the FIGHT option.",
        "pirates_fought", 5, 900, 240,
    ),
    CodexEntry(
        "freight_baron", "commerce", "Freight Baron",
        "Deliver ten quantum freight orders.",
        "Open the QUANTUM FREIGHT board while docked.",
        "deliveries", 10, 1200, 300,
    ),
    CodexEntry(
        "surface_pioneer", "exploration", "Surface Pioneer",
        "Complete three surface operations.",
        "Land on a landable body and choose a surface action.",
        "surface_ops", 3, 600, 180,
    ),
    CodexEntry(
        "decision_maker", "command", "Decision Maker",
        "Resolve ten command decisions.",
        "Answer the blocking decisions that appear during flight.",
        "decisions_resolved", 10, 750, 200,
    ),
    CodexEntry(
        "helium_harvester", "exploration", "Helium Harvester",
        "Scoop fuel ten times.",
        "Scoop fuel whenever the tanks run low.",
        "scoops", 10, 700, 200,
    ),
    CodexEntry(
        "megastructure", "exploration", "Megastructure Survey",
        "See three distinct megastructure types.",
        "Visit systems hosting ring worlds, Dyson spheres, relays, or wormholes.",
        "megastructures_seen", 3, 1000, 300,
    ),
    CodexEntry(
        "event_horizon", "exploration", "Event Horizon",
        "Visit a system containing a black hole.",
        "Plot a route toward a black-hole system.",
        "black_holes_visited", 1, 900, 250,
    ),
    CodexEntry(
        "xenobiologist", "exploration", "Xenobiologist",
        "Observe twelve distinct celestial body types.",
        "Survey systems with varied planet archetypes.",
        "body_types_seen", 12, 700, 200,
    ),
    # Command
    CodexEntry(
        "first_crew", "command", "Crew Expansion",
        "Expand the starting crew to three members.",
        "Run `crew recruit <role>` at a station.",
        "crew", 3, 200, 75,
    ),
    CodexEntry(
        "skeleton_crew", "command", "Skeleton Crew",
        "Maintain a crew of four.",
        "Recruit specialists for every station.",
        "crew", 4, 800, 250,
    ),
    CodexEntry(
        "veteran_crew", "command", "Veteran Crew",
        "Train a crew member to skill rank five.",
        "Run `crew train <crew_id>` repeatedly.",
        "crew_max_skill", 5, 600, 200,
    ),
    CodexEntry(
        "escort", "command", "Escort Duty",
        "Commission your first escort warship.",
        "Run `fleet buy_escort <class>` at a drydock.",
        "escorts", 1, 500, 150,
    ),
    CodexEntry(
        "squadron", "command", "Squadron Command",
        "Field three escort warships.",
        "Build a balanced escort wing.",
        "escorts", 3, 1200, 350,
    ),
    CodexEntry(
        "outpost", "command", "Foothold",
        "Found your first planetary outpost.",
        "Run `outpost build <type> <body_id>`.",
        "outposts", 1, 500, 150,
    ),
    CodexEntry(
        "industrialist", "command", "Industrialist",
        "Operate three outposts.",
        "Expand production across visited systems.",
        "outposts", 3, 1500, 450,
    ),
    CodexEntry(
        "scholar", "command", "Scholar",
        "Complete a research project.",
        "Run `research start <project_id>`.",
        "research", 1, 400, 120,
    ),
    CodexEntry(
        "technologist", "command", "Technologist",
        "Complete four research projects.",
        "Climb the technology tree.",
        "research", 4, 1200, 350,
    ),
    # Commerce
    CodexEntry(
        "first_trade", "commerce", "First Trade",
        "Complete a commodity trade.",
        "Run `buy <commodity> <qty>` or `sell <commodity> <qty>` at a station.",
        "trades", 1, 100, 40,
    ),
    CodexEntry(
        "merchant", "commerce", "Merchant",
        "Complete twenty-five commodity trades.",
        "Exploit price differences across systems.",
        "trades", 25, 700, 220,
    ),
    CodexEntry(
        "tycoon", "commerce", "Tycoon",
        "Earn 50,000 credits across your career.",
        "Trade, scan, salvage, and claim contracts.",
        "credits_earned", 50000, 2000, 500,
    ),
    CodexEntry(
        "contractor", "commerce", "Contractor",
        "Complete three bounty contracts.",
        "Claim finished assignments from the contracts board.",
        "contracts_completed", 3, 700, 220,
    ),
    # Combat
    CodexEntry(
        "first_blood", "combat", "First Blood",
        "Win your first space battle.",
        "Fight off a hostile intercept.",
        "combat_victories", 1, 250, 90,
    ),
    CodexEntry(
        "ace", "combat", "Ace",
        "Win five space battles.",
        "Patrol low-security systems.",
        "combat_victories", 5, 1000, 300,
    ),
    CodexEntry(
        "warlord", "combat", "Warlord",
        "Win fifteen space battles.",
        "Break the corsair fleets.",
        "combat_victories", 15, 2500, 600,
    ),
    CodexEntry(
        "anomaly", "combat", "Anomaly Resolved",
        "Resolve a spatial anomaly.",
        "Investigate proximity alerts and choose an outcome.",
        "anomalies_resolved", 1, 250, 80,
    ),
    # Diplomacy
    CodexEntry(
        "first_contact", "diplomacy", "First Contact",
        "Form your first alliance with an AI captain.",
        "Run `allies form <captain_id>`.",
        "allies", 1, 300, 100,
    ),
    CodexEntry(
        "envoy", "diplomacy", "Envoy",
        "Hold alliances with two captains.",
        "Build a coalition across the sector.",
        "allies", 2, 700, 220,
    ),
    CodexEntry(
        "diplomat", "diplomacy", "Diplomat",
        "Reach +60 standing with any faction.",
        "Run `diplomacy improve <faction_id>` and aid their causes.",
        "faction_standing_max", 60, 900, 250,
    ),
    CodexEntry(
        "ambassador", "diplomacy", "Ambassador",
        "Hold alliances with three captains.",
        "Turn the frontier into a stable coalition.",
        "allies", 3, 1200, 320,
    ),
    # Legacy
    CodexEntry(
        "signal", "legacy", "Signal Decoded",
        "Resolve your first quantum message branch.",
        "Run `messages tree` and choose a branch.",
        "messages_resolved", 1, 300, 100,
    ),
    CodexEntry(
        "network", "legacy", "Network Weaver",
        "Resolve three quantum message branches.",
        "Follow every message tree to its outcome.",
        "messages_resolved", 3, 900, 250,
    ),
    CodexEntry(
        "cipher", "legacy", "The Precursor Cipher",
        "Complete the narrative campaign.",
        "Resolve every act of the Precursor Cipher.",
        "story_complete", 1, 2000, 600,
    ),
    CodexEntry(
        "relic_hunter", "legacy", "Relic Hunter",
        "Recover three Precursor relics.",
        "Scan worlds, win battles, and claim high-tier contracts.",
        "relics", 3, 900, 280,
    ),
    CodexEntry(
        "curator", "legacy", "Curator",
        "Claim ten codex milestones.",
        "Collect rewards from the discovery codex.",
        "codex_claimed", 10, 1000, 300,
    ),
    CodexEntry(
        "completionist", "legacy", "Completionist",
        "Claim twenty-five codex milestones.",
        "Turn the frontier into a complete record.",
        "codex_claimed", 25, 3000, 800,
    ),
)

CODEX_MAP: dict[str, CodexEntry] = {entry.id: entry for entry in CODEX_ENTRIES}

METRIC_LABELS: dict[str, str] = {
    "jumps": "Hyperspace jumps",
    "systems_visited": "Systems charted",
    "scans": "Planetary scans",
    "systems_surveyed": "Systems surveyed",
    "landings": "Surface landings",
    "salvage": "Derelicts boarded",
    "scoops": "Fuel scoops",
    "away_missions": "Away missions completed",
    "decisions_resolved": "Decisions resolved",
    "pirates_fought": "Pirates fought",
    "deliveries": "Quantum freight deliveries",
    "surface_ops": "Surface operations",
    "trades": "Commodity trades",
    "credits_earned": "Credits earned",
    "combat_victories": "Combat victories",
    "contracts_completed": "Contracts completed",
    "anomalies_resolved": "Anomalies resolved",
    "messages_resolved": "Message branches",
    "relics": "Precursor relics",
    "crew": "Crew members",
    "crew_max_skill": "Best crew skill",
    "escorts": "Escort warships",
    "drones": "Fleet drones",
    "outposts": "Outposts",
    "research": "Research projects",
    "allies": "Captain alliances",
    "ai_contacts": "AI first contacts",
    "faction_standing_max": "Peak faction standing",
    "pilot_level": "Pilot mastery level",
    "body_types_seen": "Body types observed",
    "megastructures_seen": "Megastructure types",
    "black_holes_visited": "Black-hole systems",
    "story_complete": "Campaign completed",
    "codex_claimed": "Codex rewards claimed",
}

CODEX_METRICS: tuple[str, ...] = tuple(METRIC_LABELS)

STATS_ORDER: tuple[str, ...] = (
    "jumps",
    "systems_visited",
    "scans",
    "systems_surveyed",
    "landings",
    "salvage",
    "scoops",
    "away_missions",
    "decisions_resolved",
    "pirates_fought",
    "deliveries",
    "surface_ops",
    "trades",
    "credits_earned",
    "combat_victories",
    "contracts_completed",
    "anomalies_resolved",
    "messages_resolved",
    "relics",
    "crew",
    "crew_max_skill",
    "escorts",
    "drones",
    "outposts",
    "research",
    "allies",
    "ai_contacts",
    "faction_standing_max",
    "pilot_level",
    "body_types_seen",
    "megastructures_seen",
    "black_holes_visited",
    "story_complete",
    "codex_claimed",
)


def get_codex_entry(entry_id: str) -> CodexEntry | None:
    """Resolve one codex milestone by identifier."""
    return CODEX_MAP.get(entry_id)


def _seen_bodies(state: GameState) -> list[Any]:
    system_ids = state.visited_systems or (state.ship.current_system_id,)
    return [
        body
        for system_id in system_ids
        if system_id in state.systems
        for body in state.systems[system_id].bodies
    ]


def metric_value(state: GameState, metric: str) -> int:
    """Compute one codex metric from the saved game state."""
    if metric not in METRIC_LABELS:
        raise ValueError(f"Unknown codex metric '{metric}'")

    ship = state.ship
    if metric == "jumps":
        return int(state.stats.get("jumps", 0))
    if metric == "systems_visited":
        return len(state.visited_systems)
    if metric == "scans":
        return int(state.stats.get("scans", 0))
    if metric == "systems_surveyed":
        return int(state.stats.get("systems_surveyed", 0))
    if metric == "landings":
        return int(state.stats.get("landings", 0))
    if metric == "salvage":
        return int(state.stats.get("salvage", 0))
    if metric == "scoops":
        return int(state.stats.get("scoops", 0))
    if metric == "away_missions":
        return int(state.stats.get("away_missions", 0))
    if metric == "decisions_resolved":
        return int(state.stats.get("decisions_resolved", 0))
    if metric == "pirates_fought":
        return int(state.stats.get("pirates_fought", 0))
    if metric == "deliveries":
        return int(state.stats.get("deliveries", 0))
    if metric == "surface_ops":
        return int(state.stats.get("surface_ops", 0))
    if metric == "trades":
        return int(state.stats.get("trades", 0))
    if metric == "credits_earned":
        return int(state.stats.get("credits_earned", 0))
    if metric == "combat_victories":
        return int(state.stats.get("combat_victories", 0))
    if metric == "contracts_completed":
        return int(state.stats.get("contracts_completed", 0))
    if metric == "anomalies_resolved":
        return int(state.stats.get("anomalies_resolved", 0))
    if metric == "messages_resolved":
        return sum(1 for message in state.messages if message.resolved_choice)
    if metric == "relics":
        return len(ship.relics)
    if metric == "crew":
        return len(ship.crew)
    if metric == "crew_max_skill":
        return max((member.skill for member in ship.crew), default=0)
    if metric == "escorts":
        return len(ship.fleet_ships)
    if metric == "drones":
        return len(ship.fleet_drones)
    if metric == "outposts":
        return len(state.outposts)
    if metric == "research":
        return len(state.research.completed)
    if metric == "allies":
        return len(ship.allies)
    if metric == "ai_contacts":
        return sum(1 for captain in state.ai_captains if captain.ally or captain.hired or captain.trust > 0)
    if metric == "faction_standing_max":
        return max((int(value) for value in ship.faction_standings.values()), default=0)
    if metric == "pilot_level":
        return ship.mastery.level
    if metric == "story_complete":
        return 1 if ship.story.completed else 0
    if metric == "codex_claimed":
        return len(state.codex.claimed)

    bodies = _seen_bodies(state)
    if metric == "body_types_seen":
        return len({body.body_type for body in bodies})
    if metric == "megastructures_seen":
        return len({body.body_type for body in bodies if body.body_type in MEGASTRUCTURE_TYPES})
    if metric == "black_holes_visited":
        system_ids = state.visited_systems or (ship.current_system_id,)
        return sum(
            1
            for system_id in set(system_ids)
            if system_id in state.systems
            and any(body.body_type == "black_hole" for body in state.systems[system_id].bodies)
        )
    raise ValueError(f"Unknown codex metric '{metric}'")


def evaluate_codex(state: GameState) -> list[dict[str, Any]]:
    """Return every milestone with current progress, completion, and claim state."""
    claimed = set(state.codex.claimed)
    records: list[dict[str, Any]] = []
    for entry in CODEX_ENTRIES:
        value = metric_value(state, entry.metric)
        completed = value >= entry.target
        records.append({
            **entry.to_dict(),
            "value": value,
            "progress": min(value, entry.target),
            "completed": completed,
            "claimed": entry.id in claimed,
            "claimed_date": state.codex.claimed_dates.get(entry.id, ""),
            "ready": completed and entry.id not in claimed,
        })
    return records


def build_codex_report(state: GameState) -> dict[str, Any]:
    """Build the JSON-safe captain's log and discovery codex report."""
    records = evaluate_codex(state)
    completed = sum(1 for record in records if record["completed"])
    claimed = sum(1 for record in records if record["claimed"])
    ready = sum(1 for record in records if record["ready"])
    by_id = {record["id"]: record for record in records}

    categories = []
    for category in CODEX_CATEGORIES:
        members = [record for record in records if record["category"] == category.id]
        categories.append({
            **category.to_dict(),
            "entries": len(members),
            "completed": sum(1 for record in members if record["completed"]),
            "claimed": sum(1 for record in members if record["claimed"]),
        })

    log = []
    for entry_id in reversed(state.codex.claimed):
        record = by_id.get(entry_id)
        if record is None:
            continue
        log.append({
            "id": record["id"],
            "title": record["title"],
            "date": record["claimed_date"],
            "reward_credits": record["reward_credits"],
            "reward_xp": record["reward_xp"],
        })

    return {
        "categories": categories,
        "entries": records,
        "totals": {
            "entries": len(records),
            "categories": len(CODEX_CATEGORIES),
            "completed": completed,
            "claimed": claimed,
            "ready": ready,
            "completion_pct": round(completed / len(records) * 100) if records else 0,
        },
        "stats": [
            {"id": metric, "label": METRIC_LABELS[metric], "value": metric_value(state, metric)}
            for metric in STATS_ORDER
        ],
        "log": log,
        "flight_log": list(state.ship.flight_log[-12:]),
    }
