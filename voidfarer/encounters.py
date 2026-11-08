"""Unified view and resolver for VoidFarer's blocking encounters.

Anomalies, pirate tolls, customs inspections and decision events are four
different models with four resolvers, four routes and four cards. They all mean
the same thing to the player: "the game is waiting for one choice." This module
normalizes them into one encounter payload and one resolve entry point while the
existing models, saves and resolver effects stay untouched.

The functions are read-only except ``resolve``, which delegates to the engine's
existing resolver so effects, logs and contracts remain identical.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState

ENCOUNTER_KINDS = ("decision", "pirate", "customs", "anomaly")


def _action(
    action_id: str,
    label: str,
    detail: str = "",
    *,
    cost: int = 0,
    disabled: bool = False,
    reason: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": action_id,
        "label": label,
        "detail": detail,
        "cost": cost,
        "disabled": disabled,
    }
    if reason:
        payload["reason"] = reason
    return payload


def _decision(state: GameState) -> dict[str, Any]:
    pending = state.pending_decision
    return {
        "kind": "decision",
        "id": pending.id,
        "title": pending.title,
        "tag": f"DECISION REQUIRED // {str(pending.severity or 'major').upper()}",
        "description": pending.description,
        "detail": "",
        "actions": [
            _action(choice.id, choice.label, choice.description)
            for choice in pending.choices
        ],
        "data": pending.to_dict(),
    }


def _pirate(state: GameState) -> dict[str, Any]:
    pirate = state.active_pirate
    credits = int(state.ship.credits)
    fuel_cost = 6 + int(pirate.threat)
    return {
        "kind": "pirate",
        "id": pirate.id,
        "title": f"{pirate.band_name} // {pirate.ship_class}",
        "tag": "PIRATE INTERCEPT",
        "description": pirate.description,
        "detail": (
            f"DEMAND: {pirate.toll_credits} CREDITS // "
            f"THREAT {pirate.threat} // {pirate.system_name}"
        ),
        "actions": [
            _action(
                "pay",
                f"PAY {pirate.toll_credits} CR",
                "The raider peels away.",
                cost=pirate.toll_credits,
                disabled=credits < pirate.toll_credits,
                reason=f"Needs {pirate.toll_credits} cr (have {credits}).",
            ),
            _action("fight", "FIGHT", "Open fire; resolve as a hostile intercept."),
            _action(
                "evade",
                f"EVADE (-{fuel_cost} FUEL)",
                "Burn clear; a failed burn takes hull damage.",
                cost=fuel_cost,
            ),
        ],
        "data": pirate.to_dict(),
    }


def _customs(state: GameState) -> dict[str, Any]:
    customs = state.active_customs
    credits = int(state.ship.credits)
    fuel = int(state.ship.fuel)
    units = sum(int(quantity) for quantity in customs.contraband_found.values())
    return {
        "kind": "customs",
        "id": customs.id,
        "title": customs.patrol_vessel,
        "tag": "SECURITY PATROL // CONTRABAND DETECTED",
        "description": customs.description,
        "detail": (
            f"ILLICIT GOODS: {units} units // "
            f"FINE {customs.fine_amount} CR // BRIBE {customs.bribe_amount} CR"
        ),
        "actions": [
            _action(
                "bribe",
                f"BRIBE {customs.bribe_amount} CR",
                "Clear the manifest off the record (+30 XP).",
                cost=customs.bribe_amount,
                disabled=credits < customs.bribe_amount,
                reason=f"Needs {customs.bribe_amount} cr (have {credits}).",
            ),
            _action("jettison", "JETTISON CONTRABAND", f"Purge {units} units; released clean."),
            _action(
                "confiscate",
                f"SUBMIT (FINE {customs.fine_amount} CR)",
                "Lose the contraband, pay the fine, take -5 standing.",
                cost=customs.fine_amount,
            ),
            _action(
                "flee",
                "FLEE CORDON (-5 FUEL)",
                "Escape chance; failure costs hull, cargo and standing.",
                cost=5,
                disabled=fuel < 5,
                reason=f"Needs 5 fuel (have {fuel}).",
            ),
        ],
        "data": customs.to_dict(),
    }


def _anomaly(state: GameState) -> dict[str, Any]:
    anomaly = state.active_anomaly
    return {
        "kind": "anomaly",
        "id": anomaly.id,
        "title": anomaly.title,
        "tag": f"PROXIMITY HAZARD // {str(anomaly.severity).upper()}",
        "description": anomaly.description,
        "detail": "",
        "actions": [
            _action(
                choice.choice_id,
                choice.text,
                (
                    f"CHECK: {choice.required_power.upper()} >= {choice.min_power_threshold}%"
                    if choice.required_power != "none"
                    else "SAFE HARVEST"
                ),
            )
            for choice in anomaly.choices
        ],
        "data": anomaly.to_dict(),
    }


def active_encounter(state: GameState) -> dict[str, Any] | None:
    """Return the highest-priority blocking encounter, or None.

    Priority matches the state-machine contract: decision, pirate, customs,
    anomaly. Only one of these is normally active at a time; the order makes the
    result deterministic if a save or debug state contains several.
    """
    if state.pending_decision is not None:
        return _decision(state)
    if state.active_pirate is not None:
        return _pirate(state)
    if state.active_customs is not None:
        return _customs(state)
    if state.active_anomaly is not None:
        return _anomaly(state)
    return None


def encounter_report(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state, the cockpit and agents."""
    encounter = active_encounter(state)
    return {
        "active": encounter is not None,
        "kind": encounter["kind"] if encounter else None,
        "encounter": encounter,
        "available": list(ENCOUNTER_KINDS),
    }


def resolve(
    engine: Any, kind: str | None, action: str
) -> tuple[bool, str]:
    """Resolve the active encounter through its existing engine resolver.

    ``kind`` is optional: when omitted, the active encounter's kind is used.
    A mismatched kind is rejected so a stale client cannot route a choice to the
    wrong machine.
    """
    with engine.lock:
        encounter = active_encounter(engine.state)
        if encounter is None:
            return False, "No blocking encounter is active."
        active_kind = encounter["kind"]
        requested = str(kind).strip().lower() if kind else active_kind
        if requested not in ENCOUNTER_KINDS:
            return False, (
                f"Unknown encounter kind '{requested}'. "
                f"Use one of: {', '.join(ENCOUNTER_KINDS)}."
            )
        if requested != active_kind:
            return False, f"Active encounter is '{active_kind}', not '{requested}'."
        action = str(action).strip()
        if not action:
            return False, "An encounter action is required."
    if active_kind == "decision":
        return engine.resolve_decision(action)
    if active_kind == "pirate":
        return engine.resolve_pirate_encounter(action)
    if active_kind == "customs":
        return engine.resolve_customs(action)
    return engine.resolve_anomaly(action)
