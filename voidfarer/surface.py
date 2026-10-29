"""Surface operations: choose what your landing party does after touchdown."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from voidfarer.inventory import get_item_info
from voidfarer.models import CelestialBody, ShipState


@dataclass(frozen=True)
class SurfaceOperation:
    id: str
    name: str
    description: str
    risk: int
    credits: int = 0
    research: int = 0
    cargo: tuple[tuple[str, int], ...] = ()
    hull_delta: int = 0
    morale: int = 0
    heal_injuries: int = 0
    credit_cost: int = 0
    body_types: tuple[str, ...] = ()

    def available_on(self, body: CelestialBody) -> bool:
        """An empty body_types tuple means the operation works anywhere."""
        return not self.body_types or body.body_type in self.body_types

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "risk": self.risk,
            "credits": self.credits,
            "research": self.research,
            "cargo": [
                {"id": item, "name": get_item_info(item).name, "quantity": qty}
                for item, qty in self.cargo
            ],
            "hull_delta": self.hull_delta,
            "morale": self.morale,
            "heal_injuries": self.heal_injuries,
            "credit_cost": self.credit_cost,
            "body_types": list(self.body_types),
        }


SURFACE_OPERATIONS: tuple[SurfaceOperation, ...] = (
    SurfaceOperation(
        id="surface_survey",
        name="Surface Survey",
        description="Lay seismic charges and map the upper crust from a rover circuit.",
        risk=8,
        credits=180,
        research=30,
    ),
    SurfaceOperation(
        id="core_sample",
        name="Deep Core Sample",
        description="Drive a thermal lance into the mantle for high-grade ore cores.",
        risk=18,
        cargo=(("titanium", 3),),
        hull_delta=-5,
    ),
    SurfaceOperation(
        id="ruin_excavation",
        name="Ruin Excavation",
        description="Open the sealed pre-colonial vault beneath the regolith.",
        risk=28,
        credits=600,
        cargo=(("xenoliths", 1),),
        hull_delta=-8,
    ),
    SurfaceOperation(
        id="wreck_salvage",
        name="Wreck Salvage",
        description="Cut apart a crashed hull for intact avionics and alloy plate.",
        risk=22,
        cargo=(("microchips", 1), ("titanium", 2)),
        hull_delta=-4,
    ),
    SurfaceOperation(
        id="field_rest",
        name="Field Rest & Refit",
        description="Rotate the crew through the lander's medbay and repair the seals.",
        risk=0,
        morale=5,
        heal_injuries=5,
        credit_cost=120,
    ),
    SurfaceOperation(
        id="geothermal_tap",
        name="Geothermal Tap",
        description="Sink a heat exchanger into a shallow magma chamber and bottle the steam.",
        risk=20,
        credits=90,
        cargo=(("fuel_cells", 3),),
        hull_delta=-6,
    ),
    SurfaceOperation(
        id="bio_prospecting",
        name="Bio-Prospecting",
        description="Collect extremophile samples from shaded vents and seep pools.",
        risk=10,
        research=20,
        cargo=(("medicines", 2),),
        morale=2,
    ),
    SurfaceOperation(
        id="crash_site_recovery",
        name="Crash-Site Recovery",
        description="Strip a fresh impact scar for avionics, plate and flight recorders.",
        risk=24,
        cargo=(("microchips", 2), ("titanium", 1)),
        hull_delta=-7,
    ),
    SurfaceOperation(
        id="cryo_drill",
        name="Cryo Drill",
        description="Melt through the ice sheet to tap a sealed subglacial fuel lens.",
        risk=16,
        research=25,
        cargo=(("fuel_cells", 2),),
        body_types=("ice_world", "ice_giant", "tundra"),
    ),
    SurfaceOperation(
        id="magma_tap",
        name="Magma Tap",
        description="Run a shielded siphon along an active lava tube for rare xenoliths.",
        risk=26,
        cargo=(("xenoliths", 1), ("fuel_cells", 2)),
        hull_delta=-8,
        body_types=("lava_world", "volcanic"),
    ),
    SurfaceOperation(
        id="reef_harvest",
        name="Reef Harvest",
        description="Harvest cultivated kelp and reef biomass from the coastal shelf.",
        risk=9,
        credits=120,
        cargo=(("hydroponics", 4),),
        body_types=("oceanic", "savanna"),
    ),
    SurfaceOperation(
        id="cloud_scoop",
        name="Cloud Scoop",
        description="Drop a ram scoop through the upper cloud deck for deuterium.",
        risk=18,
        cargo=(("fuel_cells", 3),),
        body_types=("gas_giant", "ringed_giant"),
    ),
    SurfaceOperation(
        id="deep_mine",
        name="Deep Mine",
        description="Sink a shaft through basement rock into a high-grade ore seam.",
        risk=22,
        cargo=(("titanium", 4),),
        hull_delta=-6,
        body_types=("terrestrial", "super_earth", "barren", "desert_world"),
    ),
)

SURFACE_OPERATION_MAP = {operation.id: operation for operation in SURFACE_OPERATIONS}


def _stable_unit(*parts: object) -> float:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64)


def surface_risk(operation: SurfaceOperation, body: CelestialBody) -> int:
    if operation.risk <= 0:
        return 0
    hazard = sum(1 for _ in body.hazards) * 3
    gravity = max(0.0, abs(float(body.gravity or 1.0) - 1.0) * 8.0)
    return max(0, min(70, int(round(operation.risk + hazard + gravity))))


def surface_report(ship: ShipState, body: CelestialBody | None) -> dict[str, object]:
    if body is None or ship.landed_body_id != body.id:
        return {"landed": False, "body": None, "operations": []}
    used = set(ship.surface_used)
    operations = []
    for operation in SURFACE_OPERATIONS:
        if not operation.available_on(body):
            continue
        key = f"{body.id}:{operation.id}"
        row = operation.to_dict()
        row["risk"] = surface_risk(operation, body)
        row["used"] = key in used
        row["available"] = key not in used
        row["key"] = key
        operations.append(row)
    return {
        "landed": True,
        "body": {
            "id": body.id,
            "name": body.name,
            "body_type": body.body_type,
            "hazards": list(body.hazards),
            "gravity": body.gravity,
            "population": body.population,
        },
        "operations": operations,
        "used_count": len([op for op in operations if op["used"]]),
        "total_count": len(operations),
    }


def resolve_surface_operation(
    operation: SurfaceOperation,
    body: CelestialBody,
    ship: ShipState,
    galaxy_seed: int,
    tick: int,
) -> dict[str, object]:
    risk = surface_risk(operation, body)
    roll = _stable_unit(galaxy_seed, "surface", body.id, operation.id, tick)
    success = roll >= risk / 100.0
    if success:
        return {
            "success": True,
            "risk": risk,
            "credits": operation.credits,
            "research": operation.research,
            "cargo": operation.cargo,
            "hull_delta": operation.hull_delta,
            "morale": operation.morale,
            "heal_injuries": operation.heal_injuries,
            "log": f"SURFACE OP [{operation.name}] succeeded at {body.name}.",
        }
    damage = max(0, abs(operation.hull_delta) + 4)
    return {
        "success": False,
        "risk": risk,
        "credits": 0,
        "research": 0,
        "cargo": (),
        "hull_delta": -damage,
        "morale": -2,
        "heal_injuries": 0,
        "log": f"SURFACE OP [{operation.name}] went wrong at {body.name}: hull -{damage}.",
    }
