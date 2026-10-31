"""Reactor core simulation: operating modes, thermal load, cooling, and derating."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from voidfarer.models import ReactorState

REACTOR_MODES: dict[str, dict[str, Any]] = {
    "balanced": {
        "name": "Balanced",
        "description": "Nominal output with standard thermal load.",
        "output_mult": 1.00,
        "heat_mult": 1.00,
        "cooling_mult": 1.00,
        "evasion": 0.0,
        "encounter_mult": 1.0,
    },
    "economy": {
        "name": "Economy",
        "description": "Throttled core: 18% less output, 30% less heat, improved cooling.",
        "output_mult": 0.82,
        "heat_mult": 0.70,
        "cooling_mult": 1.15,
        "evasion": 0.0,
        "encounter_mult": 1.0,
    },
    "overdrive": {
        "name": "Overdrive",
        "description": "Overcharged plasma: +35% output with 85% more heat and reduced cooling.",
        "output_mult": 1.35,
        "heat_mult": 1.85,
        "cooling_mult": 0.90,
        "evasion": 0.0,
        "encounter_mult": 1.0,
    },
    "silent": {
        "name": "Silent Running",
        "description": "Low-emission stealth profile: 35% less output, 45% less heat, +10% evasion.",
        "output_mult": 0.65,
        "heat_mult": 0.55,
        "cooling_mult": 1.10,
        "evasion": 0.10,
        "encounter_mult": 0.80,
    },
}

MIN_MODE_HEAT = 70.0
CRITICAL_HEAT = 92.0


def get_reactor_mode(mode: str) -> dict[str, Any]:
    return REACTOR_MODES.get(str(mode).strip().lower(), REACTOR_MODES["balanced"])


def reactor_derating(reactor: ReactorState) -> float:
    """Efficiency multiplier from core integrity and thermal saturation."""
    integrity_ratio = max(0.05, reactor.integrity / max(1.0, reactor.max_integrity))
    heat_ratio = reactor.heat / max(1.0, reactor.max_heat)
    thermal = 1.0
    if reactor.heat > MIN_MODE_HEAT:
        thermal = max(0.30, 1.0 - ((reactor.heat - MIN_MODE_HEAT) / 30.0) * 0.45)
    if heat_ratio >= 0.99:
        thermal *= 0.55
    return max(0.05, integrity_ratio * thermal)


def reactor_output_efficiency(reactor: ReactorState, output_bonus: float = 0.0) -> float:
    """Effective output multiplier applied to every powered subsystem."""
    mode = get_reactor_mode(reactor.mode)
    frame_bonus = max(-0.60, float(output_bonus))
    surge = float(reactor.surge_bonus) if reactor.surge_ticks > 0 else 0.0
    return max(0.05, float(mode["output_mult"]) * (1.0 + frame_bonus) * (1.0 + max(0.0, surge)) * reactor_derating(reactor))


def reactor_cooling_rate(reactor: ReactorState, equipment_bonuses: dict[str, float], map_cooling_bonus: float = 0.0) -> float:
    mode = get_reactor_mode(reactor.mode)
    base = 6.0
    rate = (base + float(equipment_bonuses.get("reactor_cooling", 0.0)) + float(map_cooling_bonus)) * float(mode["cooling_mult"])
    return max(0.5, rate)


def reactor_heat_capacity(reactor: ReactorState, equipment_bonuses: dict[str, float]) -> float:
    return max(20.0, 100.0 + float(equipment_bonuses.get("heat_capacity", 0.0)))


def simulate_reactor_tick(
    reactor: ReactorState,
    total_allocation: int,
    num_ticks: int,
    equipment_bonuses: dict[str, float],
    map_effects: dict[str, float] | None = None,
    hull_hazard: float = 0.0,
    output_bonus: float = 0.0,
) -> tuple[ReactorState, dict[str, Any]]:
    """Advance reactor heat and integrity for the given number of ticks."""
    if num_ticks <= 0:
        return reactor, {"heat_delta": 0.0, "cooling": 0.0, "hull_damage": 0, "overheated": False}

    map_effects = map_effects or {}
    mode = get_reactor_mode(reactor.mode)
    max_heat = reactor_heat_capacity(reactor, equipment_bonuses)
    cooling = reactor_cooling_rate(reactor, equipment_bonuses, float(map_effects.get("cooling_bonus", 0.0)))
    heat_generation = max(0.0, (max(0, int(total_allocation)) / 100.0) * 5.5)
    heat_generation *= float(mode["heat_mult"])
    heat_generation *= max(0.05, 1.0 + float(equipment_bonuses.get("heat_generation", 0.0)))
    heat_generation *= max(0.2, float(map_effects.get("heat_mult", 1.0)))
    heat_generation += max(0.0, hull_hazard) * 0.5

    net_heat = (heat_generation - cooling) * num_ticks
    new_heat = max(0.0, min(max_heat, reactor.heat + net_heat))

    integrity = reactor.integrity
    hull_damage = 0
    if new_heat >= CRITICAL_HEAT:
        damage_rate = 0.35 + ((new_heat - CRITICAL_HEAT) / max(1.0, max_heat - CRITICAL_HEAT)) * 1.65
        integrity = max(0.0, integrity - damage_rate * num_ticks)
    if new_heat >= max_heat:
        hull_damage = max(1, int(round(num_ticks * 1.5)))
    elif new_heat >= CRITICAL_HEAT:
        hull_damage = max(0, int(round(num_ticks * 0.25)))

    updated = replace(
        reactor,
        heat=round(new_heat, 2),
        integrity=round(integrity, 2),
        max_heat=max_heat,
        max_integrity=max(reactor.max_integrity, 100.0 + float(equipment_bonuses.get("reactor_integrity", 0.0))),
        surge_ticks=max(0, int(reactor.surge_ticks) - num_ticks),
        surge_bonus=float(reactor.surge_bonus) if int(reactor.surge_ticks) - num_ticks > 0 else 0.0,
    )
    report = {
        "heat_delta": round(new_heat - reactor.heat, 2),
        "cooling": round(cooling, 2),
        "heat_generation": round(heat_generation, 2),
        "hull_damage": hull_damage,
        "overheated": new_heat >= MIN_MODE_HEAT,
        "critical": new_heat >= CRITICAL_HEAT,
        "efficiency": round(reactor_output_efficiency(updated, output_bonus), 3),
    }
    return updated, report


def vent_reactor(reactor: ReactorState, current_tick: int, cooldown_ticks: int = 5) -> tuple[bool, ReactorState, str]:
    """Emergency coolant purge: dump heat anywhere, at a small integrity cost."""
    remaining = cooldown_ticks - (current_tick - reactor.last_vent_tick)
    if reactor.last_vent_tick >= 0 and remaining > 0:
        return False, reactor, f"Coolant purge recharging: ready in {remaining} tick(s)."
    if reactor.heat <= 5.0:
        return False, reactor, "Reactor thermal load is already within safe limits."
    new_heat = max(2.0, reactor.heat - 45.0)
    updated = replace(
        reactor,
        heat=new_heat,
        integrity=max(0.0, reactor.integrity - 1.0),
        last_vent_tick=current_tick,
    )
    return True, updated, f"Emergency coolant purge vented {round(reactor.heat - new_heat, 1)} heat (now {new_heat:.1f})."
