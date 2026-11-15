"""Quick-start commander archetypes: a skill spread, an origin and a small starting loadout.

One click on the creation screen picks all three, so a first-time captain skips the 20-point
allocation. Skills spend exactly the creation budget (checked by tests); the loadout is applied by
``SimulationEngine`` when the profile names an archetype.

PRINCIPLE-009.
"""

from __future__ import annotations

from typing import Any

ARCHETYPES: dict[str, dict[str, Any]] = {
    "vanguard": {
        "name": "Coalition Vanguard",
        "background": "Navigator",
        "summary": "Balanced captain with the Cadet Academy active. The recommended first run.",
        "skills": {"piloting": 9, "engineering": 8, "science": 8, "combat": 8, "diplomacy": 8, "trade": 9},
    },
    "merchant": {
        "name": "Free Spacer Merchant",
        "background": "Merchant",
        "summary": "Bigger hold and a Free Spacers trade pact; the academy is skipped.",
        "skills": {"piloting": 8, "engineering": 7, "science": 8, "combat": 7, "diplomacy": 10, "trade": 10},
    },
    "smuggler": {
        "name": "Syndicate Smuggler",
        "background": "Prospector",
        "summary": "Silent reactor, sensor-heavy power and one contraband crate; the academy is skipped.",
        "skills": {"piloting": 10, "engineering": 8, "science": 7, "combat": 9, "diplomacy": 6, "trade": 10},
    },
}

# Free Spacers Syndicate, the signatory of the merchant's starting trade pact.
MERCHANT_PACT_FACTION = "vanguard_syndicate"
MERCHANT_EXTRA_HOLD = 20
SMUGGLER_POWER = (25, 15, 40, 20)  # engines, shields, sensors, weapons: sensors clear the 35% ECM line
SMUGGLER_CRATE = ("xenoliths", 1)


def archetype_catalog() -> list[dict[str, Any]]:
    """The archetypes as a list for the creation screen, in display order."""
    return [{"id": key, **entry} for key, entry in ARCHETYPES.items()]
