"""One report and action surface for commander, pilot and collection progress.

Character skills, pilot mastery, abilities, relics, the codex and the jump streak
are six CLI surfaces and eight routes. This module normalizes them into one
progress report and one action entry point; the engine methods are unchanged.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState
from voidfarer.retention import relic_set_bonuses, streak_multiplier

PROGRESS_ACTIONS = ("train", "use", "unlock", "claim", "fuse")


def progress_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    character = state.character
    mastery = state.ship.mastery
    return {
        "commander_level": character.level,
        "commander_xp": character.xp,
        "commander_next_xp": character.next_level_xp,
        "skill_points": character.skill_points,
        "pilot_level": mastery.level,
        "pilot_xp": mastery.xp,
        "pilot_next_xp": mastery.next_level_xp,
        "talent_points": mastery.talent_points,
        "relics": len(state.ship.relics),
        "codex_claimed": len(state.codex.claimed),
        "streak": state.ship.streak,
    }


def progress_report(engine: Any) -> dict[str, Any]:
    """Return commander, pilot, abilities, relics, codex and streak in one payload."""
    character = engine.get_character_report()
    codex = engine.get_codex_report()
    state = engine.state
    mastery = state.ship.mastery
    return {
        "commander": character["character"],
        "skills": character["skills"],
        "abilities": character["abilities"],
        "pilot": mastery.to_dict(),
        "relics": {
            "owned": [relic.to_dict() for relic in state.ship.relics],
            "set_bonuses": relic_set_bonuses(state.ship.relics),
        },
        "codex": codex,
        "streak": {
            "count": state.ship.streak,
            "multiplier": round(streak_multiplier(state.ship.streak), 2),
        },
        "counts": {
            "skills": len(character["skills"]),
            "abilities_unlocked": sum(
                1 for ability in character["abilities"].values() if ability["unlocked"]
            ),
            "relics": len(state.ship.relics),
            "codex_claimed": len(state.codex.claimed),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def progress_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one progression command to its existing engine method."""
    action = str(action).strip().lower()
    if action == "train":
        return engine.train_character_skill(_text(kwargs.get("skill")))
    if action in ("use", "ability"):
        return engine.use_character_ability(
            _text(kwargs.get("ability_id")),
            _text(kwargs.get("target_faction_id")) or None,
        )
    if action in ("unlock", "talent"):
        return engine.unlock_talent(_text(kwargs.get("talent_id")))
    if action in ("claim", "codex"):
        return engine.claim_codex_reward(_text(kwargs.get("entry_id")))
    if action in ("fuse", "relics"):
        ok, message, _ = engine.fuse_relics(_text(kwargs.get("rarity")))
        return ok, message
    return False, (
        f"Unknown progress action '{action}'. "
        f"Use one of: {', '.join(PROGRESS_ACTIONS)}."
    )
