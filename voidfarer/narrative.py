"""One report and action surface for story, tutorial, quests, contracts and events.

The cockpit already merges the campaign chapter, academy milestones and contracts
into the QUESTS panel, but the CLI exposes five verbs and five routes. This module
normalizes the narrative state and routes each action to the existing engine method.
"""

from __future__ import annotations

from typing import Any

from voidfarer.models import GameState

NARRATIVE_ACTIONS = (
    "story_choose", "tutorial_skip", "tutorial_reset", "tutorial_guide",
    "contract_refresh", "contract_claim", "contract_swap", "event_dismiss",
)


def _rows(items: Any) -> list[dict[str, Any]]:
    return [
        item.to_dict() if hasattr(item, "to_dict") else dict(item)
        for item in items
    ]


def narrative_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    story = state.ship.story
    tutorial = state.ship.tutorial
    return {
        "story_act": int(story.active_act),
        "story_completed": bool(story.completed),
        "story_chapter": int(story.current_chapter_index),
        "tutorial_step": int(tutorial.current_step_index),
        "tutorial_completed": bool(tutorial.completed),
        "tutorial_skipped": bool(tutorial.skipped),
        "contracts": len(state.ship.active_contracts),
        "offers": len(state.ship.contract_offers),
        "events": sum(1 for event in state.events if not event.dismissed),
    }


def narrative_report(engine: Any) -> dict[str, Any]:
    """Return story, tutorial, quests, contracts and events in one payload."""
    state = engine.state
    tutorial = state.ship.tutorial
    steps = [
        {
            "index": index,
            "title": step.title,
            "description": step.description,
            "hint": step.hint,
            "action_target": step.action_target,
            "completed": bool(step.completed),
            "current": index == tutorial.current_step_index,
            "reward_credits": int(step.reward_credits),
            "reward_xp": int(step.reward_xp),
        }
        for index, step in enumerate(tutorial.steps)
    ]
    quests = engine.get_quests()
    contracts = _rows(state.ship.active_contracts)
    offers = _rows(state.ship.contract_offers)
    events = _rows(state.events)
    active_events = [event for event in events if not event.get("dismissed")]
    story = engine.story_status()
    return {
        "story": story,
        "tutorial": {
            "completed": bool(tutorial.completed),
            "skipped": bool(tutorial.skipped),
            "current_step_index": int(tutorial.current_step_index),
            "current_step": next((step for step in steps if step["current"]), None),
            "steps": steps,
        },
        "quests": quests,
        "contracts": contracts,
        "contract_offers": offers,
        "events": events,
        "active_events": active_events,
        "counts": {
            "quests": len(quests),
            "contracts": len(contracts),
            "contract_offers": len(offers),
            "events": len(active_events),
            "tutorial_steps": len(steps),
            "tutorial_completed": sum(1 for step in steps if step["completed"]),
        },
    }


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def narrative_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one narrative command to its existing engine method."""
    action = str(action).strip().lower()
    if action in ("story_choose", "story_choice"):
        return engine.make_story_choice(_text(kwargs.get("choice_id")))
    if action == "tutorial_skip":
        return engine.skip_tutorial()
    if action == "tutorial_reset":
        return engine.reset_tutorial()
    if action == "tutorial_guide":
        ok, message, _guidance = engine.guide_tutorial()
        return ok, message
    if action == "contract_refresh":
        return engine.refresh_contracts()
    if action == "contract_claim":
        ok, message, _info = engine.claim_contract(_text(kwargs.get("contract_id")))
        return ok, message
    if action == "contract_swap":
        return engine.swap_contract_offer(
            _text(kwargs.get("offer_id")), _text(kwargs.get("drop_id"))
        )
    if action == "event_dismiss":
        return engine.dismiss_event(_text(kwargs.get("event_id")))
    return False, (
        f"Unknown narrative action '{action}'. "
        f"Use one of: {', '.join(NARRATIVE_ACTIONS)}."
    )
