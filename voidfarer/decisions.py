"""Conditional real-time decision events that pause the simulation until resolved."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from voidfarer.models import DecisionChoice, DecisionEvent, GameState


Condition = Callable[[GameState], bool]


def _system(state: GameState):
    return state.systems.get(state.ship.current_system_id)


def _body(state: GameState):
    system = _system(state)
    if system is None or state.ship.orbiting_body_id is None:
        return None
    return next((body for body in system.bodies if body.id == state.ship.orbiting_body_id), None)


def _credits(state: GameState) -> int:
    return state.ship.credits


def _avg_morale(state: GameState) -> float:
    crew = [member for member in state.ship.crew if member.status == "active"]
    return sum(member.morale for member in crew) / len(crew) if crew else 100.0


def _has_contraband(state: GameState) -> bool:
    return any(state.ship.cargo.get(item, 0) > 0 for item in ("xenoliths",))


def _any_injury(state: GameState) -> bool:
    return any(member.injury_ticks > 0 for member in state.ship.crew)


def _war_active(state: GameState) -> bool:
    return any(war.active for war in state.wars)


def _at_inhabited(state: GameState) -> bool:
    body = _body(state)
    return body is not None and body.population > 0


def _at_station(state: GameState) -> bool:
    body = _body(state)
    return body is not None and body.station_dockable


def _low_hull(state: GameState) -> bool:
    return state.ship.hull <= max(30, int(state.ship.max_hull * 0.35))


def _low_fuel(state: GameState) -> bool:
    return state.ship.fuel <= max(8, int(state.ship.max_fuel * 0.22))


def _high_heat(state: GameState) -> bool:
    return state.ship.reactor.heat >= state.ship.reactor.max_heat * 0.68


def _bad_area(state: GameState) -> bool:
    system = _system(state)
    return system is not None and (system.security < 0.30 or "pirate" in system.id or "rift" in system.id)


@dataclass(frozen=True)
class DecisionDefinition:
    id: str
    title: str
    description: str
    severity: str
    triggers: tuple[str, ...]
    choices: tuple[DecisionChoice, ...]
    condition: Condition = lambda state: True
    priority: int = 50
    repeatable: bool = False
    chance: float = 0.16


def _choice(choice_id: str, label: str, description: str, effects: dict[str, Any]) -> DecisionChoice:
    return DecisionChoice(id=choice_id, label=label, description=description, effects=effects)


DECISION_DEFINITIONS: tuple[DecisionDefinition, ...] = (
    DecisionDefinition(
        "colony_distress", "Colony Distress Call", "A frontier habitat reports a reactor cascade and asks for immediate aid.",
        "major", ("tick",), (
            _choice("send_aid", "Send emergency aid", "Spend 300 cr on parts and medics.", {"credits": -300, "morale": 4, "standing": {"sol_coalition": 3}, "log": "Your aid convoy reaches the colony in time."}),
            _choice("ignore", "Log the call and move on", "Preserve the treasury; the colony remembers.", {"morale": -2, "standing": {"sol_coalition": -2}, "log": "The colony's calls fade into static."}),
        ), _at_inhabited, priority=55,
    ),
    DecisionDefinition(
        "crew_brawl", "Crew Brawl in the Mess", "Two specialists come to blows over a disputed watch rotation.",
        "minor", ("tick",), (
            _choice("mediate", "Mediate the dispute", "Buy a round and reset the rotation (-80 cr).", {"credits": -80, "morale": 6, "log": "The mess hall settles into an uneasy truce."}),
            _choice("punish", "Punish both ringleaders", "Restore discipline at a cost to trust.", {"morale": -4, "log": "Discipline returns, but the wardroom is cold."}),
        ), lambda state: len(state.ship.crew) >= 2 and _avg_morale(state) < 60, priority=52,
    ),
    DecisionDefinition(
        "mutiny_whispers", "Mutiny Whispers", "The crew is passing around a handwritten list of demands. Morale is critical.",
        "critical", ("tick",), (
            _choice("bonus", "Pay a hardship bonus", "Spend 450 cr to stabilize the roster.", {"credits": -450, "morale": 16, "log": "The demands are withdrawn and the watch resumes."}),
            _choice("dare", "Dare them to walk", "Refuse the demands and assert command.", {"morale": -10, "log": "No one leaves, but the silence on the bridge is absolute."}),
        ), lambda state: _avg_morale(state) < 30, priority=95,
    ),
    DecisionDefinition(
        "reactor_quench", "Reactor Quench Needed", "The core is running hot enough to warp the coolant lines.",
        "major", ("tick",), (
            _choice("vent", "Emergency vent", "Dump heat before the casing cracks.", {"heat": -30, "fuel": -2, "log": "Steam screams through the vents and the core stabilizes."}),
            _choice("ride", "Ride the surge", "Gamble on one more research burn.", {"heat": 14, "research": 30, "log": "The surge yields clean telemetry, but the casing glows."}),
        ), _high_heat, priority=80,
    ),
    DecisionDefinition(
        "hull_breach", "Microfracture Cascade", "A hairline breach is spreading along the outer hull.",
        "critical", ("tick",), (
            _choice("weld", "Emergency weld", "Pay a yard team to patch it now.", {"credits": -260, "hull": 12, "log": "The weld holds and pressure recovers."}),
            _choice("brace", "Brace with cargo plate", "Use titanium stock to seal the seam.", {"cargo": {"titanium": -2}, "hull": 7, "log": "Cargo plate buys you another leg of the journey."}),
        ), _low_hull, priority=92,
    ),
    DecisionDefinition(
        "fuel_skim", "Fuel Margin Critical", "The tanks are nearly dry and the next jump is a gamble.",
        "major", ("tick",), (
            _choice("skim", "Emergency gas skim", "Risk the hull for a fast fill.", {"fuel": 16, "hull": -5, "log": "The scoop grazes the upper atmosphere but the tanks fill."}),
            _choice("trader", "Buy from a passing tanker", "Pay the premium for clean fuel.", {"credits": -220, "fuel": 12, "log": "The tanker tops you off and departs."}),
        ), _low_fuel, priority=88,
    ),
    DecisionDefinition(
        "smuggler_offer", "Smuggler's Offer", "A dockhand offers a sealed crate of xenolith relics, no questions asked.",
        "major", ("tick",), (
            _choice("buy", "Buy the crate", "Take the contraband and the risk.", {"credits": -380, "cargo": {"xenoliths": 1}, "standing": {"outlaw_corsairs": 2, "sol_coalition": -2}, "log": "The crate disappears into your hold."}),
            _choice("report", "Report the smuggler", "Trade the tip for a clean conscience and a bounty.", {"credits": 220, "standing": {"sol_coalition": 3, "outlaw_corsairs": -4}, "log": "Patrol officers thank you and sweep the dock."}),
        ), _at_station, priority=58,
    ),
    DecisionDefinition(
        "patrol_inspection", "Patrol Inspection", "A coalition cutter orders you to hold for a contraband sweep.",
        "critical", ("tick",), (
            _choice("submit", "Submit to inspection", "Surrender the contraband and keep your record clean.", {"remove_cargo": {"xenoliths": 999}, "standing": {"sol_coalition": 2}, "log": "The contraband is seized; no charges are filed."}),
            _choice("bribe", "Bribe the inspector", "Make the problem disappear.", {"credits": -320, "standing": {"sol_coalition": -1}, "log": "The cutter breaks formation without a word."}),
            _choice("run", "Run the checkpoint", "Burn hard and hope the patrol loses you.", {"fuel": -6, "standing": {"sol_coalition": -6}, "log": "You outrun the cutter, but your transponder is flagged."}),
        ), lambda state: _has_contraband(state) and _at_station(state), priority=86,
    ),
    DecisionDefinition(
        "research_grant", "Research Grant Application", "A Kepler foundation offers to co-fund your next laboratory burn.",
        "minor", ("tick",), (
            _choice("fund", "Match the grant", "Invest 200 cr in the lab.", {"credits": -200, "research": 50, "log": "The lab returns a promising result."}),
            _choice("publish", "Publish for prestige", "Take the stipend and share the data.", {"credits": 150, "standing": {"kepler_concord": 3}, "log": "Kepler archivists cite your work."}),
        ), lambda state: state.research.points >= 80, priority=45,
    ),
    DecisionDefinition(
        "refugee_flotilla", "Refugee Flotilla", "A cluster of civilian transports requests shelter and supplies.",
        "major", ("tick",), (
            _choice("house", "Open the hangar", "Spend 250 cr on food, water and berths.", {"credits": -250, "morale": 5, "standing": {"sol_coalition": 3}, "log": "The flotilla departs with full tanks and your name on its manifest."}),
            _choice("turn_away", "Turn them away", "Preserve supplies for your own crew.", {"morale": -4, "standing": {"sol_coalition": -2}, "log": "The transports bank away into the dark."}),
        ), _at_inhabited, priority=62,
    ),
    DecisionDefinition(
        "war_refugees", "War Refugees at the Line", "A war front is pushing civilian traffic into your lane.",
        "major", ("tick",), (
            _choice("escort", "Escort them clear", "Burn fuel to guide the convoy.", {"fuel": -4, "morale": 5, "standing": {"sol_coalition": 2}, "log": "The convoy makes it through under your escort."}),
            _choice("close", "Close your docking ports", "Keep the ship buttoned up.", {"morale": -3, "log": "You watch the convoy scatter without you."}),
        ), lambda state: _war_active(state) and _at_inhabited(state), priority=65,
    ),
    DecisionDefinition(
        "blockade_run", "Blockade Runner", "A wartime blockade has tightened around a nearby trade lane.",
        "critical", ("tick",), (
            _choice("run", "Run the blockade", "Push through at full burn.", {"fuel": -8, "hull": -5, "credits": 520, "log": "You punch through the picket line with cargo intact."}),
            _choice("wait", "Wait for the gap", "Pay for safe harbor until the patrol rotates.", {"credits": -180, "log": "The patrol rotates and you slip through later."}),
        ), _war_active, priority=68,
    ),
    DecisionDefinition(
        "anomaly_echo", "Anomaly Echo", "Your sensors catch a repeating echo from the last anomaly you resolved.",
        "minor", ("tick",), (
            _choice("follow", "Follow the echo", "Spend fuel to chase the signal.", {"fuel": -3, "research": 35, "log": "The echo resolves into a clean physics dataset."}),
            _choice("archive", "Archive it", "Sell the telemetry to a local observatory.", {"credits": 180, "log": "An observatory buys the archive without haggling."}),
        ), lambda state: int(state.stats.get("anomalies_resolved", 0)) >= 1, priority=40,
    ),
    DecisionDefinition(
        "precursor_dream", "Precursor Dream", "A relic in your hold resonates during the night watch.",
        "minor", ("tick",), (
            _choice("meditate", "Let the crew listen", "Turn the resonance into a shared experience.", {"morale": 5, "research": 25, "log": "The crew describes the same impossible city."}),
            _choice("sell", "Sell the recording", "A collector pays for the experience.", {"credits": 320, "morale": -1, "log": "The recording leaves the ship in a sealed case."}),
        ), lambda state: bool(state.ship.relics), priority=42,
    ),
    DecisionDefinition(
        "injury_triage", "Injury Triage", "An injured specialist is hiding the severity of their wounds.",
        "major", ("tick",), (
            _choice("treat", "Order full medbay care", "Spend 200 cr and pull them off duty.", {"credits": -200, "heal_injuries": 6, "morale": 3, "log": "The medbay stabilizes the specialist."}),
            _choice("push", "Let them finish the rotation", "Keep the roster whole for now.", {"morale": -3, "log": "The specialist finishes the watch, jaw tight."}),
        ), _any_injury, priority=85,
    ),
    DecisionDefinition(
        "market_panic", "Market Panic", "A rumor sweeps the exchange and the bid stack starts to wobble.",
        "minor", ("trade",), (
            _choice("corner", "Corner the dip", "Buy the panic with 400 cr.", {"credits": -400, "research": 10, "log": "The market steadies and your position improves."}),
            _choice("ride", "Ride the wave", "Sell into the noise.", {"credits": 180, "log": "You take a small profit before the floor settles."}),
        ), lambda state: _at_station(state), priority=35,
    ),
    DecisionDefinition(
        "derelict_signal", "Derelict Signal", "An unclaimed derelict is broadcasting on a civilian band.",
        "minor", ("orbit",), (
            _choice("board", "Board immediately", "Send a team before the drift takes it.", {"hull": -4, "credits": 320, "log": "The team returns with a sealed credit chit."}),
            _choice("mark", "Mark it for later", "Log the orbit and preserve the hull.", {"research": 15, "log": "You file the coordinates for a future salvage run."}),
        ), lambda state: _body(state) is not None and not state.ship.landed_body_id, priority=38,
    ),
    DecisionDefinition(
        "ruins_excavation", "Surface Ruins", "The landing survey finds a sealed pre-colonial structure under the regolith.",
        "major", ("land",), (
            _choice("excavate", "Excavate now", "Risk the site for a quick payday.", {"credits": 450, "cargo": {"xenoliths": 1}, "log": "The vault opens onto a chamber of relic glass."}),
            _choice("preserve", "Preserve the site", "Call in the Choir and document it.", {"research": 30, "standing": {"ashen_choir": 3}, "log": "The Choir records the site and pays a documentation stipend."}),
        ), lambda state: state.ship.landed_body_id is not None, priority=60,
    ),
    DecisionDefinition(
        "storm_warning", "Storm Warning", "A charged particle front is sweeping through the system.",
        "major", ("tick",), (
            _choice("shelter", "Shelter behind the moon", "Burn fuel to wait out the front.", {"fuel": -3, "log": "The storm passes over your shelter."}),
            _choice("push", "Push through", "Gamble on the hull and the schedule.", {"hull": -8, "credits": 220, "log": "You ride the storm and collect a courier bonus."}),
        ), lambda state: _system(state) is not None and bool(_system(state).modifiers), priority=48,
    ),
    DecisionDefinition(
        "faction_envoy", "Faction Envoy", "An envoy from a friendly power proposes a standing trade compact.",
        "minor", ("tick",), (
            _choice("accept", "Accept the compact", "Take the signing stipend and the obligation.", {"credits": 280, "standing": {"sol_coalition": 2}, "log": "The compact is sealed with a handshake and a data key."}),
            _choice("decline", "Decline politely", "Keep your options open.", {"standing": {"sol_coalition": -1}, "log": "The envoy departs with a thin smile."}),
        ), lambda state: any(value >= 25 for value in state.ship.faction_standings.values()), priority=44,
    ),
    DecisionDefinition(
        "outpost_strike", "Outpost Strike", "Workers at one of your outposts have stopped production.",
        "major", ("tick",), (
            _choice("negotiate", "Negotiate", "Spend 200 cr on safety upgrades.", {"credits": -200, "morale": 4, "log": "Production resumes under a new safety charter."}),
            _choice("break", "Break the strike", "Replace the ringleaders and restart the line.", {"credits": 120, "morale": -5, "log": "The line runs again, quieter than before."}),
        ), lambda state: bool(state.outposts), priority=50,
    ),
    DecisionDefinition(
        "black_market_raid", "Black Market Raid", "Enforcement drones are sweeping the black market while you are docked.",
        "critical", ("tick",), (
            _choice("hide", "Hide the cargo", "Pay a fixer to move it.", {"credits": -160, "log": "The drones find empty crates and move on."}),
            _choice("fight", "Defend the dock", "Shoot it out and take what you can.", {"hull": -8, "credits": 300, "standing": {"outlaw_corsairs": 3, "sol_coalition": -3}, "log": "The drones withdraw; the fixer pays for the chaos."}),
        ), lambda state: _at_station(state) and (_body(state).market_archetype == "black_market" if _body(state) else False), priority=75,
    ),
    DecisionDefinition(
        "ghost_transmission", "Ghost Transmission", "A voice on the emergency band recites coordinates in an extinct dialect.",
        "minor", ("tick",), (
            _choice("answer", "Answer the transmission", "Spend power to hold the channel.", {"research": 35, "morale": 2, "log": "The voice answers with a single star chart."}),
            _choice("ignore", "Let it fade", "Preserve the reactor margin.", {"fuel": 2, "log": "The transmission dissolves into carrier hiss."}),
        ), lambda state: _system(state) is not None and _system(state).id in ("ashen", "cygnus_x1", "golconda"), priority=47,
    ),
    DecisionDefinition(
        "nav_buoy", "Navigation Buoy", "A derelict nav buoy offers a shortcut through the local hyperlane.",
        "minor", ("jump",), (
            _choice("buy", "Buy the route", "Pay for the buoy's chart key.", {"credits": -120, "fuel": 8, "log": "The shortcut saves a full tank of fuel."}),
            _choice("salvage", "Strip the buoy", "Take its power cell and charts.", {"credits": 180, "fuel": -2, "log": "The buoy's cell tops up your reserve."}),
        ), _low_fuel, priority=70,
    ),
    DecisionDefinition(
        "meridian_contract", "Meridian Escort Contract", "An Iron Meridian factor needs a ship to escort a cargo hauler.",
        "minor", ("tick",), (
            _choice("accept", "Accept the escort", "Commit the ship for one leg.", {"credits": 420, "standing": {"iron_meridian": 2}, "log": "The hauler reaches its gate without incident."}),
            _choice("decline", "Decline the contract", "Keep your current route.", {"standing": {"iron_meridian": -1}, "log": "The factor marks your file as unreliable."}),
        ), lambda state: state.ship.faction_standings.get("iron_meridian", 0) >= 0, priority=41,
    ),
    DecisionDefinition(
        "crew_bond", "Crew Bonding Night", "The crew has synced watches well enough to ask for a night off.",
        "minor", ("tick",), (
            _choice("celebrate", "Approve the gathering", "Spend 100 cr on a proper meal.", {"credits": -100, "morale": 4, "log": "The mess hall rings with bad music and good stories."}),
            _choice("drill", "Run a surprise drill", "Trade morale for readiness.", {"morale": -1, "research": 12, "log": "The drill is sharp; the wardroom is less amused."}),
        ), lambda state: _avg_morale(state) >= 78, priority=30,
    ),
    DecisionDefinition(
        "old_friend", "Old Friend, New Venture", "A former academy classmate asks you to back a frontier survey.",
        "minor", ("tick",), (
            _choice("invest", "Invest 500 cr", "Bet on the survey and the friendship.", {"credits": -500, "research": 45, "morale": 2, "log": "The survey returns a promising mineral map."}),
            _choice("decline", "Decline", "Keep the credits in the war chest.", {"log": "Your friend wishes you a safe voyage."}),
        ), lambda state: _credits(state) >= 2500, priority=32,
    ),
    DecisionDefinition(
        "medical_shortage", "Medical Shortage", "The medbay is low on cryo-antibiotics and a fever is spreading.",
        "major", ("tick",), (
            _choice("buy", "Buy from the local clinic", "Pay whatever they ask.", {"credits": -240, "morale": 4, "log": "The fever breaks within a watch."}),
            _choice("ration", "Ration the remaining stock", "Keep the healthy crew on duty.", {"morale": -3, "log": "The fever burns through the off-shift."}),
        ), lambda state: len(state.ship.crew) >= 2 and state.ship.cargo.get("medicines", 0) <= 0, priority=54,
    ),
    DecisionDefinition(
        "pirate_tipoff", "Pirate Tip-Off", "A dockhand whispers that a fat convoy will pass a weakly patrolled lane.",
        "minor", ("tick",), (
            _choice("raid", "Set an ambush", "Risk the patrol for a rich prize.", {"fuel": -4, "hull": -6, "credits": 480, "standing": {"outlaw_corsairs": 2, "sol_coalition": -2}, "log": "The convoy's escorts are elsewhere; the prize is yours."}),
            _choice("sell_tip", "Sell the tip to patrol", "Take the clean bounty.", {"credits": 200, "standing": {"sol_coalition": 2}, "log": "The patrol pays for the lane and time."}),
        ), _bad_area, priority=66,
    ),
    DecisionDefinition(
        "salvage_dispute", "Salvage Dispute", "Another captain claims the derelict you are working.",
        "minor", ("orbit",), (
            _choice("share", "Split the salvage", "Avoid a fight and take half.", {"credits": 180, "standing": {"vanguard_syndicate": 2}, "log": "The other captain leaves with a fair split."}),
            _choice("claim", "Enforce your claim", "Stand your ground.", {"hull": -4, "credits": 340, "standing": {"vanguard_syndicate": -2}, "log": "The other ship backs off, guns cold."}),
        ), lambda state: _body(state) is not None and not state.ship.landed_body_id, priority=36,
    ),
    DecisionDefinition(
        "quantum_arbitrage", "Quantum Arbitrage Window", "Two exchanges are briefly quoting the same substrate at wildly different prices.",
        "minor", ("trade",), (
            _choice("arbitrage", "Exploit the window", "Commit 500 cr to the spread.", {"credits": -500, "research": 15, "log": "The spread closes before the window does."}),
            _choice("report", "Report the anomaly", "Let the exchange regulators handle it.", {"credits": 120, "standing": {"kepler_concord": 1}, "log": "The exchange credits your account for the report."}),
        ), _at_station, priority=34,
    ),
    DecisionDefinition(
        "crew_desertion", "Desertion Risk", "A senior specialist has packed their locker and is waiting at the airlock.",
        "critical", ("tick",), (
            _choice("retain", "Offer a retention package", "Spend 350 cr to keep them.", {"credits": -350, "morale": 12, "log": "The specialist unpacks and returns to the watch."}),
            _choice("release", "Let them go", "A clean break is better than a sour one.", {"morale": -6, "log": "The airlock cycles and the locker stays empty."}),
        ), lambda state: _avg_morale(state) < 35, priority=90,
    ),
    DecisionDefinition(
        "warp_sickness", "Warp Sickness", "Half the crew reports vertigo and nosebleeds after the last jump.",
        "major", ("jump",), (
            _choice("stand_down", "Stand down the watch", "Rest the crew and lose time.", {"morale": 5, "fuel": -2, "log": "The symptoms fade with rest."}),
            _choice("push", "Push through the rotation", "Keep the ship moving.", {"morale": -4, "hull": -2, "log": "The crew works through the sickness."}),
        ), lambda state: int(state.stats.get("jumps", 0)) >= 3, priority=56,
    ),
    DecisionDefinition(
        "deep_scan_opportunity", "Deep-Scan Opportunity", "A rare alignment lets the sensors peer through a nearby dust lane.",
        "minor", ("scan",), (
            _choice("burn", "Burn sensors for detail", "Spend reactor margin on a deep scan.", {"heat": 12, "research": 30, "log": "The deep scan reveals a hidden moonlet."}),
            _choice("safe", "Take the standard pass", "Keep the reactor cool.", {"research": 8, "log": "The standard pass yields routine telemetry."}),
        ), lambda state: state.ship.reactor.heat < state.ship.reactor.max_heat * 0.5, priority=39,
    ),
    DecisionDefinition(
        "landing_permit", "Landing Permit", "A local authority wants a fee before allowing surface access.",
        "minor", ("orbit",), (
            _choice("pay", "Pay the permit", "Keep the landing legal.", {"credits": -140, "standing": {"sol_coalition": 1}, "log": "The permit clears and the pad lights come on."}),
            _choice("bypass", "Land on the far side", "Risk the fine for a free approach.", {"standing": {"sol_coalition": -2}, "log": "You touch down out of sight of the tower."}),
        ), _at_inhabited, priority=33,
    ),
)

DECISION_MAP: dict[str, DecisionDefinition] = {d.id: d for d in DECISION_DEFINITIONS}


def eligible_decisions(state: GameState, trigger: str) -> list[DecisionDefinition]:
    """Definitions whose trigger and state condition are satisfied and not yet seen."""
    seen = set(state.decision_history)
    result = []
    for definition in DECISION_DEFINITIONS:
        if trigger not in definition.triggers and "*" not in definition.triggers:
            continue
        if not definition.repeatable and definition.id in seen:
            continue
        try:
            if not definition.condition(state):
                continue
        except (AttributeError, KeyError, TypeError, ValueError, IndexError):
            continue
        result.append(definition)
    result.sort(key=lambda definition: (-definition.priority, definition.id))
    return result


def make_decision_event(definition: DecisionDefinition, tick: int, trigger: str) -> DecisionEvent:
    return DecisionEvent(
        id=f"dec_{definition.id}_{tick}",
        definition_id=definition.id,
        title=definition.title,
        description=definition.description,
        severity=definition.severity,
        trigger=trigger,
        tick=tick,
        choices=definition.choices,
    )
