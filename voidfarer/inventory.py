"""Inventory items, consumables, and cargo management."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from voidfarer.models import ShipState


@dataclass(frozen=True)
class InventoryItem:
    """Itemized inventory item manifest (trade commodity or usable space consumable)."""

    id: str
    name: str
    category: str  # 'commodity', 'consumable', 'utility'
    volume: int
    base_price: int
    description: str
    is_usable: bool
    effect_type: str | None = None  # 'repair_hull', 'recharge_shield', 'refuel', 'evade_combat'
    effect_amount: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ITEM_CATALOG: dict[str, InventoryItem] = {
    # Canonical trade commodities
    "fuel_cells": InventoryItem(
        id="fuel_cells",
        name="Quantum Fuel Cells",
        category="commodity",
        volume=1,
        base_price=50,
        description="Standardized propellant canisters for hyperlane transit and reactor cores.",
        is_usable=False,
    ),
    "titanium": InventoryItem(
        id="titanium",
        name="Titanium Alloy",
        category="commodity",
        volume=2,
        base_price=120,
        description="High-density aerospace alloy used in structural ship hulls and orbital stations.",
        is_usable=False,
    ),
    "hydroponics": InventoryItem(
        id="hydroponics",
        name="Hydroponic Nutrients",
        category="commodity",
        volume=1,
        base_price=40,
        description="Enriched aeroponic fertilizer and organic rations for space colonists.",
        is_usable=False,
    ),
    "medicines": InventoryItem(
        id="medicines",
        name="Cryo-Antibiotics",
        category="commodity",
        volume=1,
        base_price=220,
        description="Cryogenically stabilized broad-spectrum medical remedies and serums.",
        is_usable=False,
    ),
    "microchips": InventoryItem(
        id="microchips",
        name="Quantum Substrates",
        category="commodity",
        volume=1,
        base_price=450,
        description="Photonic nano-circuitry required for hyperdrive computers and targeting suites.",
        is_usable=False,
    ),
    "xenoliths": InventoryItem(
        id="xenoliths",
        name="Xenolith Relics",
        category="commodity",
        volume=3,
        base_price=950,
        description="Exotic ancient non-baryonic minerals highly sought after by shadow syndicates.",
        is_usable=False,
    ),

    # Usable Consumables
    "nanite_repair_paste": InventoryItem(
        id="nanite_repair_paste",
        name="Nanite Repair Matrix",
        category="consumable",
        volume=1,
        base_price=250,
        description="Self-replicating nanite paste restoring +35 Hull integrity anywhere in space.",
        is_usable=True,
        effect_type="repair_hull",
        effect_amount=35,
    ),
    "shield_overcharge_cell": InventoryItem(
        id="shield_overcharge_cell",
        name="Shield Flux Battery",
        category="consumable",
        volume=1,
        base_price=200,
        description="Capacitor injection cell instantly supercharging deflector shields by +50 MW.",
        is_usable=True,
        effect_type="recharge_shield",
        effect_amount=50,
    ),
    "plasma_fuel_canister": InventoryItem(
        id="plasma_fuel_canister",
        name="Compressed Fuel Canister",
        category="consumable",
        volume=1,
        base_price=150,
        description="Emergency hydrogen canister injecting +20 Hyperdrive Fuel directly into the drive core.",
        is_usable=True,
        effect_type="refuel",
        effect_amount=20,
    ),
    "decoy_countermeasure": InventoryItem(
        id="decoy_countermeasure",
        name="Tactical ECM Decoy Flare",
        category="consumable",
        volume=1,
        base_price=350,
        description="Thermal and sensor jammer flare allowing emergency withdrawal from pirate combat encounters.",
        is_usable=True,
        effect_type="evade_combat",
        effect_amount=1,
    ),
}


def get_item_info(item_id: str) -> InventoryItem:
    """Retrieve item metadata, falling back to a default commodity if unlisted."""
    if item_id in ITEM_CATALOG:
        return ITEM_CATALOG[item_id]
    display_name = item_id.replace("_", " ").title()
    return InventoryItem(
        id=item_id,
        name=display_name,
        category="commodity",
        volume=1,
        base_price=100,
        description=f"Valuable galactic trade goods and resources ({display_name}).",
        is_usable=False,
    )


def calculate_cargo_volume(cargo: dict[str, int]) -> int:
    """Total hold volume currently occupied by inventory cargo."""
    return sum(
        get_item_info(item_id).volume * quantity
        for item_id, quantity in cargo.items()
        if quantity > 0
    )


def get_inventory_manifest(cargo: dict[str, int]) -> list[dict[str, Any]]:
    """Compute detailed inventory manifest itemizing quantities, volume footprint, and usability."""
    manifest: list[dict[str, Any]] = []
    for item_id, quantity in cargo.items():
        if quantity <= 0:
            continue
        info = get_item_info(item_id)
        total_vol = quantity * info.volume
        manifest.append({
            "id": info.id,
            "name": info.name,
            "category": info.category,
            "quantity": quantity,
            "unit_volume": info.volume,
            "total_volume": total_vol,
            "base_price": info.base_price,
            "description": info.description,
            "is_usable": info.is_usable,
            "effect_type": info.effect_type,
            "effect_amount": info.effect_amount,
        })
    return manifest
