"""Weapon catalog and combat modifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WeaponSpec:
    id: str
    name: str
    weapon_type: str
    damage: int
    shield_mult: float
    hull_mult: float
    accuracy: float
    description: str
    cost: int
    tech: str = "conventional"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "weapon_type": self.weapon_type,
            "damage": self.damage,
            "shield_mult": self.shield_mult,
            "hull_mult": self.hull_mult,
            "accuracy": self.accuracy,
            "description": self.description,
            "cost": self.cost,
            "tech": self.tech,
        }


WEAPON_CATALOG: tuple[WeaponSpec, ...] = (
    WeaponSpec("pulse_laser", "Pulse Laser Battery", "laser", 20, 1.0, 1.0, 0.92, "Reliable balanced-energy weapon.", 0, "conventional"),
    WeaponSpec("railgun", "Kinetic Railgun", "kinetic", 24, 0.55, 1.35, 0.82, "High-velocity slugs punish exposed hulls.", 1800, "conventional"),
    WeaponSpec("missile_pod", "Swarm Missile Pod", "missile", 18, 0.90, 1.10, 0.86, "Guided warheads that track evasive targets.", 2100, "conventional"),
    WeaponSpec("plasma_lance", "Plasma Lance", "plasma", 28, 1.25, 0.85, 0.80, "Superheated plasma melts deflector emitters.", 3200, "plasma"),
    WeaponSpec("ion_disruptor", "Ion Disruptor", "ion", 14, 1.85, 0.55, 0.90, "Ion pulses collapse shields but barely scratch hull.", 2600, "ion"),
    WeaponSpec("quantum_lance", "Quantum Phase Lance", "quantum", 34, 1.45, 1.20, 0.88, "Phase-aligned beam bypasses conventional armor geometry.", 6800, "quantum"),
    WeaponSpec("entangled_torpedo", "Entangled Torpedo", "quantum", 40, 0.75, 1.60, 0.72, "Quantum-linked torpedo that ignores point defense.", 8200, "quantum"),
    WeaponSpec("drone_swarm", "Autonomous Drone Swarm", "drone", 16, 0.95, 1.05, 0.94, "Multiple independent strike craft saturate defenses.", 3000, "drone"),
)

WEAPON_MAP: dict[str, WeaponSpec] = {w.id: w for w in WEAPON_CATALOG}


def get_weapon(weapon_id: str) -> WeaponSpec | None:
    return WEAPON_MAP.get(weapon_id)


def weapon_catalog() -> list[dict[str, Any]]:
    return [w.to_dict() for w in WEAPON_CATALOG]
