"""Canonical contract for VoidFarer's implicit state machines.

The game encodes its modes in fields, presence checks and branch conditions:
``ship.travel`` being set means "in transit", ``pending_decision`` being set means
"clock blocked", and so on. This module is the single read-only description of
those machines for developers, the cockpit and autonomous agents. It does not
change simulation behavior; it names the states, transitions and surface gates
that the engine already implements.

The registry is intentionally data-only (frozen dataclasses and tuples) so it can
be served from the REST API, printed by the CLI, and asserted by tests without
importing the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from voidfarer.models import GameState
from voidfarer.reactor import CRITICAL_HEAT, MIN_MODE_HEAT


@dataclass(frozen=True)
class Transition:
    """One named edge in a state machine."""

    event: str
    source: str
    target: str
    guard: str = ""
    effect: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "from": self.source,
            "to": self.target,
            "guard": self.guard,
            "effect": self.effect,
        }


@dataclass(frozen=True)
class Machine:
    """A named implicit state machine and the surfaces that enforce it."""

    id: str
    title: str
    owner: str
    states: tuple[str, ...]
    initial: str
    terminal: tuple[str, ...]
    transitions: tuple[Transition, ...]
    blocks_time: bool = False
    blocks_flight: bool = False
    http_block: bool = False
    cli_block: bool = False
    evidence: tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "owner": self.owner,
            "states": list(self.states),
            "initial": self.initial,
            "terminal": list(self.terminal),
            "transitions": [transition.to_dict() for transition in self.transitions],
            "blocks_time": self.blocks_time,
            "blocks_flight": self.blocks_flight,
            "http_block": self.http_block,
            "cli_block": self.cli_block,
            "evidence": list(self.evidence),
            "note": self.note,
        }


MACHINES: tuple[Machine, ...] = (
    Machine(
        id="clock",
        title="Simulation clock",
        owner="GameState.time.is_paused",
        states=("running", "paused"),
        initial="running",
        terminal=(),
        transitions=(
            Transition("pause", "running", "paused", effect="time.is_paused=True"),
            Transition("resume", "paused", "running", effect="time.is_paused=False"),
        ),
        evidence=("voidfarer/models.py:2127", "voidfarer/engine.py:10334"),
        note="The clock is a UI/simulation setting. Direct tick() calls ignore it; "
             "the server and cockpit decide whether to request a tick.",
    ),
    Machine(
        id="simulation",
        title="Tick gate",
        owner="engine.tick precedence",
        states=("running", "blocked_decision", "blocked_pirate", "destroyed"),
        initial="running",
        terminal=("destroyed",),
        transitions=(
            Transition("tick", "running", "running", guard="no pending decision, pirate or 0 hull"),
            Transition("decision", "running", "blocked_decision", guard="pending_decision is set"),
            Transition("pirate", "running", "blocked_pirate", guard="active_pirate is set"),
            Transition("destroyed", "running", "destroyed", guard="ship.hull <= 0"),
            Transition("resolve", "blocked_decision", "running", effect="pending_decision cleared"),
            Transition("resolve", "blocked_pirate", "running", effect="active_pirate cleared"),
        ),
        blocks_time=True,
        evidence=("voidfarer/engine.py:9363"),
        note="Precedence is decision > pirate > hull <= 0. Customs, anomaly and combat "
             "do not block tick today; that difference is documented, not changed.",
    ),
    Machine(
        id="onboarding",
        title="Cadet Flight Academy",
        owner="ship.tutorial",
        states=("active", "completed", "skipped", "inactive"),
        initial="active",
        terminal=("completed", "skipped"),
        transitions=(
            Transition("perform", "active", "active", guard="action matches current step",
                       effect="step marked complete; index += 1"),
            Transition("perform", "active", "completed", guard="last step completed",
                       effect="graduation reward"),
            Transition("skip", "active", "skipped"),
            Transition("reset", "skipped", "active", effect="step 0, skipped=False"),
            Transition("reset", "completed", "active", effect="step 0, completed=False"),
        ),
        evidence=("voidfarer/models.py:739", "voidfarer/engine.py:957",
                  "voidfarer/engine.py:7666", "voidfarer/engine.py:7681"),
        note="Out-of-order actions are ignored; the current step is the only accepted match.",
    ),
    Machine(
        id="campaign",
        title="Precursor Cipher campaign",
        owner="ship.story",
        states=("chapter_active", "chapter_skipped", "completed"),
        initial="chapter_active",
        terminal=("completed",),
        transitions=(
            Transition("choose", "chapter_active", "chapter_active",
                       guard="chapter requirements and choice requirements met",
                       effect="chapter completed, reputation/relics applied, next chapter"),
            Transition("gate", "chapter_active", "chapter_skipped",
                       guard="next chapter flag gate cannot open"),
            Transition("choose", "chapter_active", "completed", guard="last chapter resolved"),
        ),
        evidence=("voidfarer/models.py:960", "voidfarer/engine.py:7495"),
        note="Skipped chapters remain in the list with skipped=True; the ending is "
             "resolved from the accumulated flags.",
    ),
    Machine(
        id="travel",
        title="In-system transit",
        owner="ship.travel",
        states=("idle", "sublight", "quantum"),
        initial="idle",
        terminal=(),
        transitions=(
            Transition("start", "idle", "sublight", guard="no action lock; a travel plan exists"),
            Transition("start", "idle", "quantum", guard="quantum plan and fuel"),
            Transition("arrive", "sublight", "idle", effect="orbit destination or hold waypoint"),
            Transition("arrive", "quantum", "idle", effect="orbit destination or hold waypoint"),
            Transition("abort", "sublight", "idle", guard="orbit the origin body"),
            Transition("abort", "quantum", "idle", guard="orbit the origin body"),
        ),
        evidence=("voidfarer/models.py:1037", "voidfarer/engine.py:2297",
                  "voidfarer/engine.py:9752"),
        note="An active travel blocks body services via _transit_lock_reason; it does not "
             "block tick because ticks are how the trip progresses.",
    ),
    Machine(
        id="void",
        title="Hollow Between traversal",
        owner="ship.void_traversal",
        states=("idle", "traversing"),
        initial="idle",
        terminal=(),
        transitions=(
            Transition("dive", "idle", "traversing", guard="orbit a black hole; lane and fuel valid"),
            Transition("arrive", "traversing", "idle", effect="arrive at destination system"),
            Transition("emerge", "traversing", "idle", guard="emergency surfacing",
                       effect="hull/shield shear, prorated resonance"),
        ),
        blocks_flight=True,
        evidence=("voidfarer/models.py:1075", "voidfarer/engine.py:1358",
                  "voidfarer/engine.py:1433", "voidfarer/engine.py:9116"),
        note="Void traversal blocks flight actions, but not tick: ticks drive storms and arrival.",
    ),
    Machine(
        id="combat",
        title="Hostile intercept",
        owner="GameState.active_combat",
        states=("idle", "engaged", "defeated"),
        initial="idle",
        terminal=("defeated",),
        transitions=(
            Transition("intercept", "idle", "engaged", effect="active_combat set"),
            Transition("action", "engaged", "engaged", effect="exchange fire, update intent"),
            Transition("victory", "engaged", "idle", guard="enemy hull <= 0",
                       effect="bounty/salvage, active_combat cleared"),
            Transition("flee", "engaged", "idle", effect="fuel cost, active_combat cleared"),
            Transition("defeat", "engaged", "defeated", guard="player hull <= 0",
                       effect="hull 0, time paused, active_combat cleared"),
        ),
        blocks_flight=True,
        evidence=("voidfarer/models.py:503", "voidfarer/engine.py:5977",
                  "voidfarer/engine.py:5952"),
        note="There is no explicit 'active' flag: presence in active_combat is the state. "
             "Boarding is a guarded action inside 'engaged', not a separate machine.",
    ),
    Machine(
        id="boarding",
        title="Boarding a crippled hostile",
        owner="derived from active_combat + crew",
        states=("unavailable", "available", "resolved"),
        initial="unavailable",
        terminal=("resolved",),
        transitions=(
            Transition("cripple", "unavailable", "available",
                       guard="enemy shield 0, hull <= 30% max, active uninjured marine"),
            Transition("board", "available", "resolved",
                       guard="boarding chance succeeds", effect="prize captured"),
            Transition("repel", "available", "resolved", effect="crew injury, action spent"),
        ),
        evidence=("voidfarer/engine.py:6168"),
        note="Derived sub-state. It has no persistence of its own; the outcome is a "
             "combat action and a prize/injury effect.",
    ),
    Machine(
        id="anomaly",
        title="Spatial anomaly",
        owner="GameState.active_anomaly",
        states=("idle", "pending"),
        initial="idle",
        terminal=(),
        transitions=(
            Transition("trigger", "idle", "pending", effect="active_anomaly set"),
            Transition("resolve", "pending", "idle", guard="power check and choice",
                       effect="hull/credits/fuel/cargo outcome"),
        ),
        blocks_flight=True,
        evidence=("voidfarer/models.py:281", "voidfarer/engine.py:6753"),
        note="Jump already blocks on anomaly; orbit/travel did not before ADR-214. "
             "Anomaly does not block tick today.",
    ),
    Machine(
        id="pirate",
        title="Pirate toll",
        owner="GameState.active_pirate",
        states=("idle", "pending"),
        initial="idle",
        terminal=(),
        transitions=(
            Transition("trigger", "idle", "pending"),
            Transition("pay", "pending", "idle", guard="credits >= toll"),
            Transition("fight", "pending", "idle", effect="combat interception"),
            Transition("evade", "pending", "idle", guard="fuel", effect="standing/fuel cost"),
        ),
        blocks_time=True,
        blocks_flight=True,
        http_block=True,
        cli_block=True,
        evidence=("voidfarer/models.py:1176", "voidfarer/engine.py:6830",
                  "voidfarer/engine.py:9378", "voidfarer/server.py:475",
                  "voidfarer/cli.py:92"),
    ),
    Machine(
        id="customs",
        title="Customs interdiction",
        owner="GameState.active_customs",
        states=("idle", "pending"),
        initial="idle",
        terminal=(),
        transitions=(
            Transition("trigger", "idle", "pending"),
            Transition("bribe", "pending", "idle", guard="credits"),
            Transition("jettison", "pending", "idle", effect="contraband removed"),
            Transition("confiscate", "pending", "idle", guard="credits", effect="fine"),
            Transition("flee", "pending", "idle", guard="fuel", effect="warrant/standing"),
        ),
        blocks_flight=True,
        http_block=True,
        cli_block=True,
        evidence=("voidfarer/models.py:1209", "voidfarer/engine.py:6906",
                  "voidfarer/server.py:458", "voidfarer/cli.py:93"),
        note="Blocks flight, HTTP POST and CLI commands, but not tick today.",
    ),
    Machine(
        id="decision",
        title="Real-time decision",
        owner="GameState.pending_decision",
        states=("idle", "pending"),
        initial="idle",
        terminal=(),
        transitions=(
            Transition("trigger", "idle", "pending", guard="cadence and chance"),
            Transition("choose", "pending", "idle", effect="effects applied; history appended"),
        ),
        blocks_time=True,
        blocks_flight=True,
        http_block=True,
        cli_block=True,
        evidence=("voidfarer/models.py:1137", "voidfarer/engine.py:9366",
                  "voidfarer/engine.py:9259", "voidfarer/server.py:446",
                  "voidfarer/cli.py:91"),
    ),
    Machine(
        id="research",
        title="Research project",
        owner="GameState.research",
        states=("idle", "active", "queued", "finished"),
        initial="idle",
        terminal=("finished",),
        transitions=(
            Transition("start", "idle", "active", guard="prerequisites met"),
            Transition("start", "queued", "active", effect="removed from queue; progress = 0"),
            Transition("switch", "active", "active", effect="progress = 0 (discarded)"),
            Transition("queue", "idle", "queued", guard="prerequisites met"),
            Transition("cancel", "queued", "idle"),
            Transition("complete", "active", "idle", guard="progress >= cost",
                       effect="completed; auto-start queue"),
        ),
        evidence=("voidfarer/models.py:1378", "voidfarer/engine.py:2948",
                  "voidfarer/engine.py:9572"),
        note="Switching the active project resets progress; ADR-214 makes the discarded "
             "progress visible in the transition message.",
    ),
    Machine(
        id="contracts",
        title="Bounty contract",
        owner="ship.contract_offers / active_contracts / completed_quests",
        states=("offer", "active", "ready_to_claim", "claimed"),
        initial="offer",
        terminal=("claimed",),
        transitions=(
            Transition("accept", "offer", "active"),
            Transition("progress", "active", "active", effect="current_count += n"),
            Transition("complete", "active", "ready_to_claim", guard="current_count >= target"),
            Transition("claim", "ready_to_claim", "claimed", effect="rewards; move to completed"),
            Transition("swap", "offer", "offer", effect="replace an offer"),
        ),
        evidence=("voidfarer/models.py:561", "voidfarer/engine.py:7242",
                  "voidfarer/engine.py:1045"),
    ),
    Machine(
        id="away",
        title="Away-team expedition",
        owner="ship.away_missions",
        states=("idle", "outbound"),
        initial="idle",
        terminal=(),
        transitions=(
            Transition("launch", "idle", "outbound", guard="available crew, no active combat"),
            Transition("resolve", "outbound", "idle", guard="tick >= started + duration",
                       effect="rewards/injuries, site marked complete"),
            Transition("recall", "outbound", "idle", effect="crew returns without rewards"),
        ),
        evidence=("voidfarer/models.py:1785", "voidfarer/engine.py:4318",
                  "voidfarer/engine.py:4416"),
    ),
    Machine(
        id="outpost",
        title="Planetary outpost",
        owner="GameState.outposts",
        states=("operational", "damaged", "ruined"),
        initial="operational",
        terminal=(),
        transitions=(
            Transition("build", "operational", "operational"),
            Transition("upgrade", "operational", "operational"),
            Transition("capture_damage", "operational", "damaged", effect="integrity - damage"),
            Transition("capture_damage", "damaged", "ruined", guard="integrity <= 0"),
            Transition("repair", "damaged", "operational", guard="credits/repair action"),
        ),
        evidence=("voidfarer/models.py:1408", "voidfarer/engine.py:3310",
                  "voidfarer/engine.py:9672"),
        note="There is no stored status flag; integrity is the state.",
    ),
    Machine(
        id="reactor",
        title="Reactor core",
        owner="ship.reactor",
        states=("nominal", "overheated", "critical", "breached"),
        initial="nominal",
        terminal=("breached",),
        transitions=(
            Transition("heat", "nominal", "overheated", guard=f"heat >= {MIN_MODE_HEAT:g}"),
            Transition("heat", "overheated", "critical", guard=f"heat >= {CRITICAL_HEAT:g}"),
            Transition("cool", "critical", "overheated", effect="vent or cooling"),
            Transition("cool", "overheated", "nominal", effect="cooling"),
            Transition("rupture", "critical", "breached", guard="integrity <= 0"),
            Transition("repair", "breached", "nominal", guard="repair_reactor"),
        ),
        evidence=("voidfarer/models.py:1280", "voidfarer/reactor.py:49",
                  "voidfarer/engine.py:2590"),
        note="Mode (balanced/economy/overdrive/silent) is a separate selector that feeds heat.",
    ),
    Machine(
        id="messages",
        title="Quantum message",
        owner="GameState.messages",
        states=("unread", "read", "resolved"),
        initial="unread",
        terminal=("resolved",),
        transitions=(
            Transition("read", "unread", "read"),
            Transition("choose", "unread", "resolved", effect="choice applied; follow-up node"),
            Transition("choose", "read", "resolved", effect="choice applied; follow-up node"),
        ),
        evidence=("voidfarer/models.py:439", "voidfarer/engine.py:4509",
                  "voidfarer/engine.py:8287"),
        note="Tree messages can append a follow-up node; resolved_choice is the terminal marker.",
    ),
    Machine(
        id="fleet",
        title="Fleet asset",
        owner="ship.fleet_drones / fleet_ships",
        states=("harvesting", "patrolling", "idle", "escorting", "destroyed"),
        initial="harvesting",
        terminal=("destroyed",),
        transitions=(
            Transition("deploy", "idle", "harvesting"),
            Transition("assign", "idle", "escorting", effect="escort to a system"),
            Transition("collect", "harvesting", "idle", effect="cargo/credits harvested"),
            Transition("damage", "escorting", "destroyed", guard="hull <= 0"),
            Transition("refit", "harvesting", "harvesting", effect="integrity/level"),
        ),
        evidence=("voidfarer/models.py:311", "voidfarer/models.py:1456",
                  "voidfarer/engine.py:3895"),
    ),
    Machine(
        id="crew",
        title="Crew member",
        owner="ship.crew",
        states=("active", "injured", "away", "assigned"),
        initial="active",
        terminal=(),
        transitions=(
            Transition("recruit", "active", "active"),
            Transition("injure", "active", "injured", effect="injury_ticks > 0"),
            Transition("recover", "injured", "active", effect="injury_ticks reaches 0"),
            Transition("launch", "active", "away", effect="away mission crew_ids"),
            Transition("assign", "active", "assigned", effect="ship station or outpost"),
            Transition("dismiss", "active", "active", effect="removed from roster"),
        ),
        evidence=("voidfarer/models.py:1647", "voidfarer/engine.py:4318",
                  "voidfarer/crew.py:263"),
        note="status is 'active'; injury_ticks, mission membership and station encode "
             "the other modes.",
    ),
    Machine(
        id="save",
        title="Save slot lifecycle",
        owner="StorageManager",
        states=("clean", "backup_recovered", "corrupt_quarantined", "missing"),
        initial="missing",
        terminal=(),
        transitions=(
            Transition("save", "missing", "clean"),
            Transition("save", "clean", "clean", effect="atomic write + .bak"),
            Transition("load", "clean", "clean"),
            Transition("corrupt", "clean", "corrupt_quarantined", effect="primary moved aside"),
            Transition("fallback", "corrupt_quarantined", "backup_recovered",
                       guard=".bak parses"),
            Transition("load", "missing", "missing"),
        ),
        evidence=("voidfarer/storage.py:95", "voidfarer/storage.py:100",
                  "voidfarer/storage.py:80"),
        note="The recovery path is currently visible only through the returned GameState; "
             "a load report is a deferred DX proposal.",
    ),
    Machine(
        id="automation",
        title="Docked automation",
        owner="GameState.trade_automation / quantum_automation",
        states=("off", "armed", "cooldown"),
        initial="off",
        terminal=(),
        transitions=(
            Transition("enable", "off", "armed", guard="docked"),
            Transition("run", "armed", "cooldown", effect="trade/order placed"),
            Transition("ready", "cooldown", "armed", guard="tick cooldown elapsed"),
            Transition("disable", "armed", "off"),
        ),
        evidence=("voidfarer/models.py:1727", "voidfarer/models.py:1757",
                  "voidfarer/engine.py:4710", "voidfarer/engine.py:4825"),
    ),
    Machine(
        id="diplomacy",
        title="Faction war and pacts",
        owner="GameState.wars / ship pacts",
        states=("peace", "war", "ended"),
        initial="peace",
        terminal=(),
        transitions=(
            Transition("declare", "peace", "war"),
            Transition("score", "war", "war"),
            Transition("peace", "war", "ended", effect="ended_tick set"),
            Transition("pact", "peace", "peace", effect="trade/research/alliance/NAP"),
        ),
        evidence=("voidfarer/models.py:1549", "voidfarer/engine.py:7968"),
        note="Pacts are independent flags with expiry ticks; war is the only explicit "
             "active/ended machine.",
    ),
    Machine(
        id="codex",
        title="Codex milestone",
        owner="GameState.codex",
        states=("unclaimed", "claimed"),
        initial="unclaimed",
        terminal=("claimed",),
        transitions=(
            Transition("claim", "unclaimed", "claimed", guard="milestone met"),
        ),
        evidence=("voidfarer/models.py:2265", "voidfarer/engine.py:2826"),
    ),
)


MACHINE_BY_ID: dict[str, Machine] = {machine.id: machine for machine in MACHINES}


def catalog() -> dict[str, Any]:
    """Return the full machine registry and the surface gates it documents."""
    return {
        "schema": 1,
        "source": "voidfarer/state_machines.py",
        "machines": [machine.to_dict() for machine in MACHINES],
        "surface_gates": {
            "engine_flight": sorted(
                machine.id for machine in MACHINES if machine.blocks_flight
            ),
            "engine_time": sorted(
                machine.id for machine in MACHINES if machine.blocks_time
            ),
            "http_post": sorted(
                machine.id for machine in MACHINES if machine.http_block
            ),
            "cli": sorted(
                machine.id for machine in MACHINES if machine.cli_block
            ),
        },
        "notes": [
            "A machine is 'active' when its owner field is present or its state is not "
            "the initial state.",
            "Presence encodes state for active_combat, active_pirate, active_customs, "
            "active_anomaly, pending_decision, ship.travel and ship.void_traversal.",
            "Server and CLI gates are stricter than the engine action gate by design; "
            "GET/status/inspection remain available while blocked.",
            "Tick precedence is decision > pirate > hull <= 0. Customs, anomaly and combat "
            "do not block tick; see each machine note.",
        ],
    }


def _entry(machine_id: str, state: str, **detail: Any) -> dict[str, Any]:
    machine = MACHINE_BY_ID[machine_id]
    return {
        "state": state,
        "terminal": state in machine.terminal,
        "blocks_time": machine.blocks_time and state not in ("idle", "running"),
        "blocks_flight": machine.blocks_flight and state not in ("idle", "running"),
        "detail": {key: value for key, value in detail.items() if value is not None},
    }


def _tutorial_state(state: GameState) -> dict[str, Any]:
    tutorial = state.ship.tutorial
    steps = tutorial.steps
    if tutorial.completed:
        current = "completed"
    elif tutorial.skipped:
        current = "skipped"
    elif tutorial.active and tutorial.current_step_index < len(steps):
        current = "active"
    else:
        current = "inactive"
    step = tutorial.current_step
    return _entry(
        "onboarding",
        current,
        step_index=tutorial.current_step_index,
        step_count=len(steps),
        step_id=step.id,
        step_title=step.title,
    )


def _campaign_state(state: GameState) -> dict[str, Any]:
    story = state.ship.story
    current = "completed" if story.completed else "chapter_active"
    chapter = story.current_chapter
    return _entry(
        "campaign",
        current,
        chapter_index=story.current_chapter_index,
        act=story.active_act,
        chapter_id=story.current_chapter_id,
        chapter_title=chapter.title,
        skipped_chapters=sum(1 for c in story.chapters if c.skipped),
    )


def _travel_state(state: GameState) -> dict[str, Any]:
    travel = state.ship.travel
    if travel is None:
        return _entry("travel", "idle")
    return _entry(
        "travel",
        travel.mode if travel.mode in ("sublight", "quantum") else "sublight",
        destination=travel.destination_body_id or "open space",
        started_tick=travel.started_tick,
        arrival_tick=travel.arrival_tick,
        progress=round(travel.progress(state.time.tick), 3),
    )


def _void_state(state: GameState) -> dict[str, Any]:
    traversal = state.ship.void_traversal
    if traversal is None:
        return _entry("void", "idle")
    return _entry(
        "void",
        "traversing",
        origin=traversal.origin_system_id,
        destination=traversal.destination_system_id,
        arrival_tick=traversal.arrival_tick,
        progress=round(traversal.progress(state.time.tick), 3),
        stability=round(traversal.stability, 1),
        resonance=round(traversal.resonance, 1),
    )


def _combat_state(state: GameState) -> dict[str, Any]:
    combat = state.active_combat
    if combat is None:
        return _entry("combat", "defeated" if state.ship.hull <= 0 else "idle")
    marines = [
        member for member in state.ship.crew
        if member.role == "marine" and member.status == "active" and member.injury_ticks == 0
    ]
    crippled_at = max(1, int(combat.enemy_max_hull * 0.30))
    boardable = bool(marines) and combat.enemy_shield <= 0 and combat.enemy_hull <= crippled_at
    return _entry(
        "combat",
        "engaged",
        enemy=combat.enemy_name,
        enemy_hull=combat.enemy_hull,
        enemy_max_hull=combat.enemy_max_hull,
        enemy_shield=combat.enemy_shield,
        enemy_max_shield=combat.enemy_max_shield,
        intent=combat.enemy_intent,
        boardable=boardable,
        boarding_reason=(
            "ready" if boardable
            else "shields up" if combat.enemy_shield > 0
            else "hull too high" if combat.enemy_hull > crippled_at
            else "no active marine"
        ),
    )


def _encounter_state(machine_id: str, encounter: Any, label_fields: tuple[str, ...]) -> dict[str, Any]:
    if encounter is None:
        return _entry(machine_id, "idle")
    detail = {field_name: getattr(encounter, field_name, None) for field_name in label_fields}
    return _entry(machine_id, "pending", **detail)


def _research_state(state: GameState) -> dict[str, Any]:
    research = state.research
    if research.active_project_id:
        current = "active"
    elif research.queue:
        current = "queued"
    elif research.completed:
        current = "finished"
    else:
        current = "idle"
    return _entry(
        "research",
        current,
        active_project=research.active_project_id,
        progress=research.progress,
        completed=len(research.completed),
        queued=list(research.queue),
    )


def _contract_state(state: GameState) -> dict[str, Any]:
    offers = len(state.ship.contract_offers)
    active = len(state.ship.active_contracts)
    ready = sum(1 for contract in state.ship.active_contracts if contract.completed)
    claimed = len(state.completed_quests)
    if ready:
        current = "ready_to_claim"
    elif active:
        current = "active"
    elif offers:
        current = "offer"
    else:
        current = "idle"
    return _entry(
        "contracts",
        current,
        offers=offers,
        active=active,
        ready_to_claim=ready,
        claimed=claimed,
    )


def _away_state(state: GameState) -> dict[str, Any]:
    missions = state.ship.away_missions
    if not missions:
        return _entry("away", "idle")
    next_arrival = min(
        mission.started_tick + mission.duration_ticks for mission in missions
    )
    return _entry(
        "away",
        "outbound",
        count=len(missions),
        next_arrival_tick=next_arrival,
        mission_types=sorted({mission.mission_type for mission in missions}),
    )


def _outpost_state(state: GameState) -> dict[str, Any]:
    outposts = state.outposts
    if not outposts:
        return _entry("outpost", "operational", count=0)
    if any(outpost.integrity <= 0 for outpost in outposts):
        current = "ruined"
    elif any(outpost.integrity < 100 for outpost in outposts):
        current = "damaged"
    else:
        current = "operational"
    return _entry(
        "outpost",
        current,
        count=len(outposts),
        ruined=sum(1 for outpost in outposts if outpost.integrity <= 0),
        damaged=sum(1 for outpost in outposts if 0 < outpost.integrity < 100),
    )


def _reactor_state(state: GameState) -> dict[str, Any]:
    reactor = state.ship.reactor
    if reactor.integrity <= 0:
        current = "breached"
    elif reactor.heat >= CRITICAL_HEAT:
        current = "critical"
    elif reactor.heat >= MIN_MODE_HEAT:
        current = "overheated"
    else:
        current = "nominal"
    return _entry(
        "reactor",
        current,
        mode=reactor.mode,
        heat=round(reactor.heat, 1),
        max_heat=round(reactor.max_heat, 1),
        integrity=round(reactor.integrity, 1),
    )


def _message_state(state: GameState) -> dict[str, Any]:
    messages = state.messages
    unread = sum(1 for message in messages if not message.read and not message.resolved_choice)
    resolved = sum(1 for message in messages if message.resolved_choice)
    current = "empty" if not messages else ("unread" if unread else "read")
    return _entry(
        "messages",
        current,
        total=len(messages),
        unread=unread,
        resolved=resolved,
    )


def _fleet_state(state: GameState) -> dict[str, Any]:
    drones = state.ship.fleet_drones
    ships = state.ship.fleet_ships
    if not drones and not ships:
        return _entry("fleet", "idle", drones=0, ships=0)
    return _entry(
        "fleet",
        "deployed",
        drones=len(drones),
        ships=len(ships),
        drone_statuses={
            status: sum(1 for drone in drones if drone.status == status)
            for status in sorted({drone.status for drone in drones})
        },
        destroyed_ships=sum(1 for ship in ships if ship.hull <= 0),
    )


def _crew_state(state: GameState) -> dict[str, Any]:
    crew = state.ship.crew
    if not crew:
        return _entry("crew", "idle", total=0)
    away_ids = {cid for mission in state.ship.away_missions for cid in mission.crew_ids}
    injured = sum(1 for member in crew if member.injury_ticks > 0)
    away = sum(1 for member in crew if member.id in away_ids)
    assigned = sum(1 for member in crew if member.station)
    return _entry(
        "crew",
        "staffed",
        total=len(crew),
        injured=injured,
        away=away,
        assigned=assigned,
    )


def _automation_state(state: GameState) -> dict[str, Any]:
    trade = state.trade_automation
    quantum = state.quantum_automation
    current = "armed" if trade.enabled or quantum.enabled else "off"
    return _entry(
        "automation",
        current,
        trade=bool(trade.enabled),
        quantum=bool(quantum.enabled),
        trade_runs=trade.trades,
        quantum_orders=quantum.orders,
    )


def _diplomacy_state(state: GameState) -> dict[str, Any]:
    active_wars = [war for war in state.wars if war.active]
    return _entry(
        "diplomacy",
        "war" if active_wars else "peace",
        active_wars=len(active_wars),
        ended_wars=sum(1 for war in state.wars if not war.active),
        trade_pacts=len(state.ship.trade_pacts),
        research_pacts=len(state.ship.research_pacts),
        alliances=len(state.ship.allies),
    )


def _codex_state(state: GameState) -> dict[str, Any]:
    claimed = len(state.codex.claimed)
    return _entry(
        "codex",
        "claimed" if claimed else "unclaimed",
        claimed=claimed,
    )


def _save_state(state: GameState) -> dict[str, Any]:
    return _entry(
        "save",
        "clean",
        note="Runtime save recovery state is reported by StorageManager.load(); "
             "this inspector only describes the contract.",
    )


def inspect_state(state: GameState) -> dict[str, Any]:
    """Return the current state of every machine that can be derived from GameState."""
    paused = bool(state.time.is_paused)
    pending = state.pending_decision
    pirate = state.active_pirate
    customs = state.active_customs
    anomaly = state.active_anomaly
    hull = state.ship.hull

    if hull <= 0:
        simulation = _entry("simulation", "destroyed", hull=hull)
    elif pending is not None:
        simulation = _entry("simulation", "blocked_decision", title=pending.title)
    elif pirate is not None:
        simulation = _entry("simulation", "blocked_pirate", band=pirate.band_name)
    else:
        simulation = _entry("simulation", "running", tick=state.time.tick)

    return {
        "clock": _entry("clock", "paused" if paused else "running"),
        "simulation": simulation,
        "onboarding": _tutorial_state(state),
        "campaign": _campaign_state(state),
        "travel": _travel_state(state),
        "void": _void_state(state),
        "combat": _combat_state(state),
        "boarding": _entry(
            "boarding",
            "available" if _combat_state(state)["detail"].get("boardable") else "unavailable",
            reason=_combat_state(state)["detail"].get("boarding_reason"),
        ),
        "anomaly": _encounter_state("anomaly", anomaly, ("id", "title", "severity")),
        "pirate": _encounter_state("pirate", pirate, ("id", "band_name", "toll_credits")),
        "customs": _encounter_state("customs", customs, ("id", "patrol_vessel", "fine_amount")),
        "decision": _encounter_state("decision", pending, ("id", "title", "severity")),
        "research": _research_state(state),
        "contracts": _contract_state(state),
        "away": _away_state(state),
        "outpost": _outpost_state(state),
        "reactor": _reactor_state(state),
        "messages": _message_state(state),
        "fleet": _fleet_state(state),
        "crew": _crew_state(state),
        "automation": _automation_state(state),
        "diplomacy": _diplomacy_state(state),
        "codex": _codex_state(state),
        "save": _save_state(state),
    }


def _active(states: dict[str, Any], flag: str) -> list[str]:
    return sorted(
        machine_id
        for machine_id, entry in states.items()
        if entry.get(flag) and entry["state"] not in ("idle", "running", "clean", "off")
    )


def situation(state: GameState) -> dict[str, Any]:
    """Return one compact, priority-ordered summary for clients and agents."""
    states = inspect_state(state)
    blocking_flight = _active(states, "blocks_flight")
    blocking_time = _active(states, "blocks_time")

    if states["simulation"]["state"] == "destroyed":
        summary = "DESTROYED: hull 0 — load a save or start a new game"
        primary = "simulation"
    elif states["decision"]["state"] == "pending":
        detail = states["decision"]["detail"]
        summary = f"DECISION REQUIRED: {detail.get('title', 'choose an option')}"
        primary = "decision"
    elif states["pirate"]["state"] == "pending":
        detail = states["pirate"]["detail"]
        summary = (
            f"PIRATE INTERDICTION: {detail.get('band_name', 'raiders')} demands "
            f"{detail.get('toll_credits', 0)} cr"
        )
        primary = "pirate"
    elif states["customs"]["state"] == "pending":
        detail = states["customs"]["detail"]
        summary = f"CUSTOMS INTERDICTION: {detail.get('patrol_vessel', 'patrol')}"
        primary = "customs"
    elif states["combat"]["state"] == "engaged":
        detail = states["combat"]["detail"]
        summary = (
            f"COMBAT: {detail.get('enemy', 'hostile')} hull "
            f"{detail.get('enemy_hull', 0)}/{detail.get('enemy_max_hull', 0)}, "
            f"shields {detail.get('enemy_shield', 0)}/{detail.get('enemy_max_shield', 0)}"
        )
        primary = "combat"
    elif states["anomaly"]["state"] == "pending":
        detail = states["anomaly"]["detail"]
        summary = f"ANOMALY: {detail.get('title', 'unresolved spatial anomaly')}"
        primary = "anomaly"
    elif states["void"]["state"] == "traversing":
        detail = states["void"]["detail"]
        summary = (
            f"VOID TRAVERSAL: {detail.get('origin', '?')} -> "
            f"{detail.get('destination', '?')} ({int(detail.get('progress', 0) * 100)}%)"
        )
        primary = "void"
    elif states["travel"]["state"] in ("sublight", "quantum"):
        detail = states["travel"]["detail"]
        summary = (
            f"IN TRANSIT ({states['travel']['state']}): {detail.get('destination', '?')} "
            f"arrives tick {detail.get('arrival_tick', '?')}"
        )
        primary = "travel"
    elif states["onboarding"]["state"] == "active":
        detail = states["onboarding"]["detail"]
        summary = (
            f"ACADEMY: step {detail.get('step_index', 0) + 1}/{detail.get('step_count', 0)} "
            f"— {detail.get('step_title', 'onboarding')}"
        )
        primary = "onboarding"
    else:
        summary = "IDLE: no blocking encounter"
        primary = "idle"

    return {
        "summary": summary,
        "primary": primary,
        "blocking_flight": blocking_flight,
        "blocking_time": blocking_time,
        "states": {machine_id: entry["state"] for machine_id, entry in states.items()},
    }
