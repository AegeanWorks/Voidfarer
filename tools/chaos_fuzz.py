"""Chaos-fuzz the engine with random valid actions and check state invariants."""

from __future__ import annotations

import argparse
import json
import random
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from voidfarer.crew import CREW_ROLES  # noqa: E402
from voidfarer.engine import SimulationEngine  # noqa: E402


class Findings:
    """Collect crashes and invariant breaches once per distinct signature."""

    def __init__(self) -> None:
        self.actions = 0
        self.successes = 0
        self.refusals = 0
        self.crashes: list[dict[str, Any]] = []
        self.violations: list[dict[str, Any]] = []
        self._seen: set[tuple[str, str]] = set()

    def violation(self, kind: str, detail: str, action: str) -> None:
        key = (kind, detail[:60])
        if key in self._seen:
            return
        self._seen.add(key)
        self.violations.append({"kind": kind, "detail": detail, "action": action})

    def crash(self, action: str, seed: int, step: int, exc: Exception) -> None:
        self.crashes.append({
            "action": action,
            "seed": seed,
            "step": step,
            "error": f"{type(exc).__name__}: {exc}",
            "trace": traceback.format_exc()[-1200:],
        })


def check_invariants(engine: SimulationEngine, findings: Findings, action: str) -> None:
    """Every campaign state must stay inside its declared bounds."""
    state = engine.state
    ship = state.ship
    if ship.credits < 0:
        findings.violation("negative_credits", str(ship.credits), action)
    if not 0 <= ship.hull <= ship.max_hull:
        findings.violation("hull_bounds", f"{ship.hull}/{ship.max_hull}", action)
    if not 0 <= ship.shield <= ship.max_shield:
        findings.violation("shield_bounds", f"{ship.shield}/{ship.max_shield}", action)
    if not 0 <= ship.fuel <= ship.max_fuel:
        findings.violation("fuel_bounds", f"{ship.fuel}/{ship.max_fuel}", action)
    if any(quantity < 0 for quantity in ship.cargo.values()):
        findings.violation("negative_cargo", str(dict(ship.cargo)), action)
    crew_ids = [member.id for member in ship.crew]
    if len(crew_ids) != len(set(crew_ids)):
        findings.violation("duplicate_crew", ",".join(crew_ids), action)
    if state.time.tick < 0:
        findings.violation("negative_tick", str(state.time.tick), action)
    for system in state.systems.values():
        for body in system.bodies:
            if body.population < 0:
                findings.violation("negative_population", body.id, action)
            if 0 < body.population_capacity < body.population:
                findings.violation(
                    "population_over_capacity",
                    f"{body.id} {body.population}/{body.population_capacity}",
                    action,
                )
            if not -0.001 <= float(body.devastation) <= 100.001:
                findings.violation("devastation_range", f"{body.id} {body.devastation}", action)
    for outpost in state.outposts:
        if outpost.level < 1:
            findings.violation("outpost_level", outpost.id, action)
    for depot in state.depots:
        if any(quantity < 0 for quantity in depot.cargo.values()):
            findings.violation("negative_depot", depot.id, action)


def dock_somewhere(engine: SimulationEngine) -> tuple[bool, str]:
    for body in engine.current_system.bodies:
        if body.station_dockable:
            return engine.orbit(body.id)
    return False, "No dock in this system."


def choose_action(
    engine: SimulationEngine, rng: random.Random
) -> tuple[str, Callable[[], Any]]:
    """Pick one random action that is legal in the current blocking state."""
    state = engine.state
    ship = state.ship
    system = engine.current_system

    if state.active_combat is not None:
        return "combat", lambda: engine.combat_action(rng.choice([
            "fire_lasers", "brace_for_impact", "target_shields", "target_engines",
            "vent_heat", "flee", "board_enemy", "combat_gambit",
        ]))
    if state.active_anomaly is not None:
        choices = [choice.choice_id for choice in state.active_anomaly.choices]
        if not choices:
            return "anomaly", lambda: engine.resolve_anomaly("")
        return "anomaly", lambda: engine.resolve_anomaly(rng.choice(choices))
    if state.active_pirate is not None:
        return "pirate", lambda: engine.resolve_pirate_encounter(
            rng.choice(["pay", "fight", "flee"])
        )
    if state.active_customs is not None:
        return "customs", lambda: engine.resolve_customs(
            rng.choice(["jettison", "bribe", "submit"])
        )
    if state.pending_decision is not None:
        choices = [choice.id for choice in state.pending_decision.choices]
        if choices:
            return "decision", lambda: engine.resolve_decision(rng.choice(choices))

    roll = rng.random()
    if roll < 0.18 and system.connections:
        return "jump", lambda: engine.jump(rng.choice(system.connections))
    if roll < 0.30:
        body = rng.choice(system.bodies)
        return "orbit", lambda: engine.orbit(body.id)
    if roll < 0.36:
        return "scan", lambda: engine.scan()
    if roll < 0.44:
        body = rng.choice([candidate for candidate in system.bodies if candidate.landable] or system.bodies)
        return "land", lambda: engine.land_on_body(body.id)
    if roll < 0.52:
        return "dock", lambda: dock_somewhere(engine)
    if roll < 0.58 and ship.cargo:
        commodity = rng.choice(list(ship.cargo))
        return "sell", lambda: engine.trade(commodity, 1, False)
    if roll < 0.66:
        commodity = rng.choice(["water", "food", "titanium", "xenoliths"])
        return "buy", lambda: engine.trade(commodity, 1, True)
    if roll < 0.72:
        return "salvage", lambda: engine.salvage_derelict(
            rng.choice(["balanced", "fast", "careful"])
        )
    if roll < 0.78:
        return "scoop", lambda: engine.scoop_fuel()
    if roll < 0.84:
        return "repair", lambda: engine.repair_hull(30)
    if roll < 0.88:
        roles = [role.id for role in CREW_ROLES]
        return "recruit", lambda: engine.recruit_crew(rng.choice(roles))
    if roll < 0.92 and ship.crew:
        return "dismiss", lambda: engine.dismiss_crew(rng.choice(ship.crew).id)
    if roll < 0.96 and ship.crew:
        member = rng.choice(ship.crew)
        return "station", lambda: engine.assign_crew_station(
            member.id, rng.choice(["", "helm", "engineering", "sensors"])
        )
    return "tick", lambda: engine.tick(rng.choice([1, 2, 3]))


def run_seed(seed: int, actions: int, findings: Findings) -> None:
    rng = random.Random(seed * 7919 + 3)
    engine = SimulationEngine(seed=seed)
    engine.allow_decision_events = True
    for step in range(actions):
        name, action = choose_action(engine, rng)
        findings.actions += 1
        try:
            result = action()
        except Exception as exc:  # noqa: BLE001 - the fuzz must capture everything
            findings.crash(name, seed, step, exc)
            if len(findings.crashes) >= 5:
                return
            continue
        ok = bool(result[0]) if isinstance(result, tuple) else True
        if ok:
            findings.successes += 1
        else:
            findings.refusals += 1
        check_invariants(engine, findings, f"{name}@seed{seed}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fuzz the VoidFarer engine with random valid actions and check invariants.",
    )
    parser.add_argument("--seed", action="append", type=int, default=None,
                        help="Galaxy seed to fuzz; repeat the flag for several (default: 3)")
    parser.add_argument("--actions", type=int, default=2000,
                        help="Random actions per seed (default: 2000)")
    parser.add_argument("--json", action="store_true", help="Print the raw report as JSON")
    args = parser.parse_args(argv)
    if args.actions < 1:
        parser.error("--actions must be >= 1")
    seeds = args.seed or [3]

    findings = Findings()
    for seed in seeds:
        run_seed(seed, args.actions, findings)

    report = {
        "seeds": seeds,
        "actions": findings.actions,
        "successes": findings.successes,
        "refusals": findings.refusals,
        "crashes": findings.crashes,
        "violations": findings.violations,
        "ok": not findings.crashes and not findings.violations,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Chaos fuzz: {report['actions']} actions across {len(seeds)} seed(s), "
            f"{report['successes']} succeeded, {report['refusals']} refused"
        )
        print(f"Crashes: {len(findings.crashes)}  Invariant breaches: {len(findings.violations)}")
        for crash in findings.crashes[:5]:
            print(f"  CRASH seed {crash['seed']} step {crash['step']} {crash['action']}: {crash['error']}")
        for breach in findings.violations[:10]:
            print(f"  BREACH {breach['kind']}: {breach['detail']} ({breach['action']})")
        if not report["ok"]:
            print("Why: the engine produced a crash or an out-of-bounds state under random play.")
            print("Fix: reproduce with the printed seed and step, then add a failing test before the fix.")
            return 1
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
