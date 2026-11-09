"""One report and action surface for AI captains, quantum messages and trees.

The cockpit has separate AI CAPTAINS and MESSAGES tabs, but the CLI exposes `ai`
and `messages` with nine sub-actions. This module normalizes both and routes each
action to the existing engine method.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState

COMMS_ACTIONS = (
    "hail", "buy", "sell", "hire", "ally",
    "send", "read", "choose",
)


def comms_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    unread = sum(1 for message in state.messages if not message.read)
    return {
        "captains": len(state.ai_captains),
        "allied_captains": sum(1 for captain in state.ai_captains if captain.ally),
        "messages": len(state.messages),
        "unread": unread,
        "unresolved": sum(1 for message in state.messages if message.choices and not message.resolved_choice),
    }


def comms_report(engine: Any) -> dict[str, Any]:
    """Return captains, inbox, trees and unresolved choices in one payload."""
    state = engine.state
    captains = [captain.to_dict() for captain in state.ai_captains]
    messages = [message.to_dict() for message in state.messages]
    trees = engine.get_message_tree_report()["trees"]
    return {
        "captains": captains,
        "messages": messages,
        "trees": trees,
        "counts": {
            "captains": len(captains),
            "allies": sum(1 for captain in captains if captain.get("ally")),
            "messages": len(messages),
            "unread": sum(1 for message in messages if not message.get("read")),
            "unresolved": sum(
                1 for message in messages
                if message.get("choices") and not message.get("resolved_choice")
            ),
            "trees": len(trees),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _int(value: Any, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def comms_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one comms command to its existing engine method."""
    action = str(action).strip().lower()
    if action in ("hail", "buy", "sell", "hire", "ally"):
        return engine.interact_ai(
            _text(kwargs.get("captain_id")),
            action,
            _text(kwargs.get("commodity_id")) or None,
            _int(kwargs.get("quantity"), 1),
        )
    if action == "send":
        return engine.send_quantum_message(
            _text(kwargs.get("recipient")),
            _text(kwargs.get("subject")),
            _text(kwargs.get("body")),
        )
    if action == "read":
        return engine.mark_message_read(_text(kwargs.get("message_id")))
    if action == "choose":
        return engine.resolve_message_choice(
            _text(kwargs.get("message_id")), _text(kwargs.get("choice_id"))
        )
    return False, (
        f"Unknown comms action '{action}'. "
        f"Use one of: {', '.join(COMMS_ACTIONS)}."
    )
