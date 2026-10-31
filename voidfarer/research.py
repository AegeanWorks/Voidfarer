"""Research projects and technology bonuses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResearchProject:
    id: str
    name: str
    category: str
    cost: int
    description: str
    effects: dict[str, float]
    prerequisites: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "cost": self.cost,
            "description": self.description,
            "effects": dict(self.effects),
            "prerequisites": list(self.prerequisites),
        }


RESEARCH_PROJECTS: tuple[ResearchProject, ...] = (
    ResearchProject(
        id="advanced_cooling",
        name="Advanced Coolant Loops",
        category="engineering",
        cost=120,
        description="Micro-channel heat exchangers improve reactor cooling.",
        effects={"reactor_cooling": 4.0},
    ),
    ResearchProject(
        id="efficient_fusion",
        name="Efficient Fusion Ignition",
        category="engineering",
        cost=220,
        description="Stabilized plasma burn raises reactor output.",
        effects={"reactor_output": 0.10},
        prerequisites=("advanced_cooling",),
    ),
    ResearchProject(
        id="deep_survey_arrays",
        name="Deep Survey Arrays",
        category="science",
        cost=160,
        description="Long-baseline interferometry improves scan yields.",
        effects={"scan_mult": 1.25},
    ),
    ResearchProject(
        id="plasma_weapons",
        name="Plasma Weapon Theory",
        category="combat",
        cost=240,
        description="Magnetic containment improves weapon damage.",
        effects={"combat_damage": 15.0},
    ),
    ResearchProject(
        id="diplomatic_corps",
        name="Diplomatic Corps",
        category="society",
        cost=180,
        description="Professional envoys improve faction negotiation.",
        effects={"diplomacy_bonus": 0.15},
    ),
    ResearchProject(
        id="colonial_administration",
        name="Colonial Administration",
        category="society",
        cost=200,
        description="Standardized outpost logistics raise production.",
        effects={"outpost_yield": 0.25},
    ),
    ResearchProject(
        id="automated_hull_repair",
        name="Automated Hull Repair",
        category="engineering",
        cost=260,
        description="Self-healing hull microcapsules repair damage over time.",
        effects={"hull_repair_per_tick": 1.0},
        prerequisites=("efficient_fusion",),
    ),
    ResearchProject(
        id="quantum_entanglement",
        name="Quantum Entanglement Networks",
        category="quantum",
        cost=360,
        description="Entangled relay pairs enable instant message trees and deep-space coordination.",
        effects={"scan_mult": 1.15, "diplomacy_bonus": 0.10},
        prerequisites=("deep_survey_arrays",),
    ),
    ResearchProject(
        id="quantum_drive",
        name="Quantum Drive Tuning",
        category="quantum",
        cost=420,
        description="Phase-locked drive coils cut hyperspace fuel demand.",
        effects={"fuel_efficiency": 0.75},
        prerequisites=("wormhole_theory",),
    ),
    ResearchProject(
        id="quantum_shielding",
        name="Entangled Deflector Lattice",
        category="quantum",
        cost=400,
        description="Entangled particles spread incoming fire across the shield lattice.",
        effects={"reactor_cooling": 5.0, "combat_damage": 5.0},
        prerequisites=("advanced_cooling",),
    ),
    ResearchProject(
        id="quantum_weapons",
        name="Quantum Phase Weapons",
        category="quantum",
        cost=480,
        description="Phase-aligned emitters unlock quantum lance integration.",
        effects={"combat_damage": 20.0},
        prerequisites=("plasma_weapons",),
    ),
    ResearchProject(
        id="wormhole_theory",
        name="Wormhole Navigation Theory",
        category="science",
        cost=320,
        description="Gravitational routing cuts hyperspace fuel consumption.",
        effects={"fuel_efficiency": 0.90},
        prerequisites=("deep_survey_arrays",),
    ),
)

RESEARCH_MAP: dict[str, ResearchProject] = {p.id: p for p in RESEARCH_PROJECTS}

DEFAULT_RESEARCH_BONUSES: dict[str, float] = {
    "reactor_cooling": 0.0,
    "reactor_output": 0.0,
    "scan_mult": 1.0,
    "combat_damage": 0.0,
    "diplomacy_bonus": 0.0,
    "outpost_yield": 0.0,
    "hull_repair_per_tick": 0.0,
    "fuel_efficiency": 1.0,
}


def get_research_project(project_id: str) -> ResearchProject | None:
    return RESEARCH_MAP.get(project_id)


def calculate_research_bonuses(completed: tuple[str, ...]) -> dict[str, float]:
    bonuses = dict(DEFAULT_RESEARCH_BONUSES)
    for project_id in completed:
        project = RESEARCH_MAP.get(project_id)
        if not project:
            continue
        for stat, value in project.effects.items():
            if stat == "scan_mult":
                bonuses["scan_mult"] *= float(value)
            elif stat == "fuel_efficiency":
                bonuses["fuel_efficiency"] *= float(value)
            elif stat in bonuses:
                bonuses[stat] += float(value)
    bonuses["fuel_efficiency"] = max(0.25, min(1.0, bonuses["fuel_efficiency"]))
    return bonuses


def available_projects(completed: tuple[str, ...], active_project_id: str | None) -> list[ResearchProject]:
    completed_set = set(completed)
    return [
        p for p in RESEARCH_PROJECTS
        if p.id not in completed_set
        and p.id != active_project_id
        and all(prereq in completed_set for prereq in p.prerequisites)
    ]
