"""Navigation routing, jump planning, and black-hole hazard helpers."""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Any

from voidfarer.models import StarSystem

BLACK_HOLE_HAZARD = {
    "fuel_mult": 1.25,
    "encounter_mult": 1.15,
    "scan_mult": 1.40,
    "relic_find": 0.10,
}

# Void traversal tuning (PRINCIPLE G-012: deterministic per save seed, stdlib only)
VOID_LANE_SEED_SALT = 0x5A17
VOID_SPOKE_COUNT = 2
VOID_SPOKE_POOL = 4
VOID_DIVE_BASE_FUEL = 10
VOID_MIN_DURATION_TICKS = 3
VOID_MAX_DURATION_TICKS = 8


def shortest_route(systems: dict[str, StarSystem], start_id: str, target_id: str) -> list[str]:
    if start_id == target_id:
        return [start_id]
    if start_id not in systems or target_id not in systems:
        return []
    queue: deque[list[str]] = deque([[start_id]])
    visited = {start_id}
    while queue:
        path = queue.popleft()
        current = path[-1]
        for neighbor in systems[current].connections:
            if neighbor in visited or neighbor not in systems:
                continue
            next_path = path + [neighbor]
            if neighbor == target_id:
                return next_path
            visited.add(neighbor)
            queue.append(next_path)
    return []


def route_plan(systems: dict[str, StarSystem], start_id: str, target_id: str, base_jump_fuel: int = 8) -> dict[str, Any]:
    path = shortest_route(systems, start_id, target_id)
    if not path:
        return {"reachable": False, "path": [], "jumps": 0, "distance_ly": 0.0, "fuel_estimate": 0}
    distance = 0.0
    for first, second in zip(path, path[1:]):
        a = systems[first]
        b = systems[second]
        distance += math.hypot(a.x - b.x, a.y - b.y)
    jumps = max(0, len(path) - 1)
    hazard_mult = 1.0
    if any(any(body.body_type == "black_hole" for body in systems[sid].bodies) for sid in path):
        hazard_mult = BLACK_HOLE_HAZARD["fuel_mult"]
    return {
        "reachable": True,
        "path": path,
        "jumps": jumps,
        "distance_ly": round(distance, 2),
        "fuel_estimate": max(1, int(round(base_jump_fuel * jumps * hazard_mult))),
        "black_hole_hazard": hazard_mult > 1.0,
    }


def system_has_black_hole(system: StarSystem) -> bool:
    return any(body.body_type == "black_hole" for body in system.bodies)


def void_anchor_systems(systems: dict[str, StarSystem]) -> list[str]:
    """Ids of systems holding a black-hole event horizon, sorted for determinism."""
    return sorted(sid for sid, system in systems.items() if system_has_black_hole(system))


def system_distance_ly(a: StarSystem, b: StarSystem) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def generate_void_lanes(systems: dict[str, StarSystem], galaxy_seed: int) -> dict[str, tuple[str, ...]]:
    """Deterministically derive the void-lane graph of the Hollow Between.

    Black-hole anchors are fully meshed, and each anchor gains seeded spokes to the
    farthest non-anchor systems. The same galaxy seed always yields the same lanes.
    """
    anchors = void_anchor_systems(systems)
    lanes: dict[str, set[str]] = {anchor: set() for anchor in anchors}
    for first, second in zip(anchors, anchors[1:] + anchors[:1]):
        if first == second:
            continue
        lanes[first].add(second)
        lanes[second].add(first)

    rng = random.Random((int(galaxy_seed) ^ VOID_LANE_SEED_SALT) & 0xFFFFFFFF)
    non_anchors = sorted(sid for sid in systems if sid not in anchors)
    for anchor in anchors:
        pool = sorted(
            non_anchors,
            key=lambda sid: (-system_distance_ly(systems[anchor], systems[sid]), sid),
        )[:VOID_SPOKE_POOL]
        spokes = rng.sample(pool, min(VOID_SPOKE_COUNT, len(pool)))
        for spoke in spokes:
            lanes.setdefault(spoke, set()).add(anchor)
            lanes[anchor].add(spoke)

    return {sid: tuple(sorted(neighbors)) for sid, neighbors in sorted(lanes.items())}


def void_shortest_route(lanes: dict[str, tuple[str, ...]], start_id: str, target_id: str) -> list[str]:
    if start_id == target_id:
        return [start_id]
    if start_id not in lanes or target_id not in lanes:
        return []
    queue: deque[list[str]] = deque([[start_id]])
    visited = {start_id}
    while queue:
        path = queue.popleft()
        current = path[-1]
        for neighbor in lanes[current]:
            if neighbor in visited or neighbor not in lanes:
                continue
            next_path = path + [neighbor]
            if neighbor == target_id:
                return next_path
            visited.add(neighbor)
            queue.append(next_path)
    return []


def void_lane_metrics(systems: dict[str, StarSystem], first: str, second: str) -> dict[str, float]:
    """Fuel cost and duration for one void lane crossing."""
    distance = system_distance_ly(systems[first], systems[second])
    fuel = VOID_DIVE_BASE_FUEL + int(distance // 20)
    duration = max(
        VOID_MIN_DURATION_TICKS,
        min(VOID_MAX_DURATION_TICKS, VOID_MIN_DURATION_TICKS + int(distance // 40)),
    )
    return {"distance_ly": round(distance, 2), "fuel": fuel, "duration_ticks": duration}


def void_route_plan(
    systems: dict[str, StarSystem],
    galaxy_seed: int,
    start_id: str,
    target_id: str,
) -> dict[str, Any]:
    """Plan a multi-lane traversal through the Hollow Between."""
    lanes = generate_void_lanes(systems, galaxy_seed)
    path = void_shortest_route(lanes, start_id, target_id)
    if not path:
        return {
            "reachable": False,
            "path": [],
            "lanes": 0,
            "distance_ly": 0.0,
            "fuel_estimate": 0,
            "duration_ticks": 0,
            "storm_risk": 0.0,
        }
    distance = 0.0
    fuel = 0
    duration = 0
    for first, second in zip(path, path[1:]):
        metrics = void_lane_metrics(systems, first, second)
        distance += metrics["distance_ly"]
        fuel += metrics["fuel"]
        duration += metrics["duration_ticks"]
    crossings = max(0, len(path) - 1)
    return {
        "reachable": True,
        "path": path,
        "lanes": crossings,
        "distance_ly": round(distance, 2),
        "fuel_estimate": fuel,
        "duration_ticks": duration,
        "storm_risk": round(min(0.95, 0.30 + 0.12 * crossings), 2),
    }
