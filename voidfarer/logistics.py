"""One report and action surface for trade, freight, depots and inventory.

The market, auto-trade broker, quantum freight, depots and consumables are five
CLI surfaces and a dozen routes. This module normalizes them into one logistics
report and one action entry point; the underlying engine methods stay unchanged.
"""

from __future__ import annotations

from typing import Any

from voidfarer.inventory import calculate_cargo_volume
from voidfarer.models import GameState

LOGISTICS_ACTIONS = (
    "buy", "sell", "buy_max", "sell_max", "sell_all",
    "automation_on", "automation_off",
    "quantum_automation_on", "quantum_automation_off",
    "quantum_order",
    "deposit", "withdraw", "depot_sell",
    "item_buy", "item_use", "jettison",
    "fabricate",
)


def _depot_row(state: GameState) -> dict[str, Any] | None:
    depot = next(
        (candidate for candidate in state.depots
         if candidate.system_id == state.ship.current_system_id),
        None,
    )
    if depot is None:
        return None
    return {
        **depot.to_dict(),
        "used_volume": calculate_cargo_volume(depot.cargo),
    }


def logistics_summary(state: GameState) -> dict[str, Any]:
    """Compact payload for /api/state."""
    depot = _depot_row(state)
    return {
        "cargo_volume": calculate_cargo_volume(state.ship.cargo),
        "cargo_capacity": int(state.ship.cargo_capacity),
        "credits": int(state.ship.credits),
        "depot": depot is not None,
        "depot_volume": depot["used_volume"] if depot else 0,
        "trade_automation": bool(state.trade_automation.enabled),
        "quantum_automation": bool(state.quantum_automation.enabled),
        "freight_orders": len(state.ship.trade_orders),
    }


def logistics_report(engine: Any) -> dict[str, Any]:
    """Return market quotes, cargo, depot, automation and freight in one payload."""
    snapshot = engine.get_status_snapshot(include_static=False)
    state = engine.state
    depot = _depot_row(state)
    cargo_volume = calculate_cargo_volume(state.ship.cargo)
    return {
        "credits": int(state.ship.credits),
        "market": snapshot.get("market_quotes", []),
        "cargo": {
            "hold": dict(state.ship.cargo),
            "volume": cargo_volume,
            "capacity": int(state.ship.cargo_capacity),
            "manifest": snapshot.get("inventory_manifest", []),
            "avg_cost": snapshot.get("cargo_avg_cost", {}),
        },
        "depot": depot,
        "automation": {
            "trade": state.trade_automation.to_dict(),
            "quantum": state.quantum_automation.to_dict(),
        },
        "freight": {
            "orders": [order.to_dict() for order in state.ship.trade_orders],
            "routes": snapshot.get("trade_routes", []),
        },
        "counts": {
            "market_lines": len(snapshot.get("market_quotes", [])),
            "cargo_items": len(state.ship.cargo),
            "freight_orders": len(state.ship.trade_orders),
            "depot_items": len(depot["cargo"]) if depot else 0,
        },
    }


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def logistics_action(engine: Any, action: str, **kwargs: Any) -> tuple[bool, str]:
    """Route one logistics command to its existing engine method."""
    action = str(action).strip().lower()
    if action in ("buy", "sell"):
        return engine.trade(
            _text(kwargs.get("commodity_id")),
            max(1, _int(kwargs.get("quantity"), 1)),
            action == "buy",
        )
    if action == "sell_all":
        return engine.sell_all_profitable()
    if action in ("buy_max", "sell_max"):
        return engine.trade_max(_text(kwargs.get("commodity_id")), action == "buy_max")
    if action == "automation_on":
        return engine.set_trade_automation(
            _text(kwargs.get("commodity_id")),
            _int(kwargs.get("buy_below")),
            _int(kwargs.get("sell_above")),
            max(1, _int(kwargs.get("quantity"), 1)),
            enabled=True,
        )
    if action == "automation_off":
        return engine.set_trade_automation(enabled=False)
    if action == "quantum_automation_on":
        return engine.set_quantum_automation(True, max(0, _int(kwargs.get("min_net"), 100)))
    if action == "quantum_automation_off":
        return engine.set_quantum_automation(False)
    if action in ("quantum_order", "ship"):
        return engine.place_quantum_order(
            _text(kwargs.get("commodity_id")),
            max(1, _int(kwargs.get("quantity"), 1)),
            _text(kwargs.get("destination_system_id")),
        )
    if action == "deposit":
        return engine.deposit_cargo(_text(kwargs.get("item_id")), max(1, _int(kwargs.get("quantity"), 1)))
    if action == "withdraw":
        return engine.withdraw_cargo(_text(kwargs.get("item_id")), max(1, _int(kwargs.get("quantity"), 1)))
    if action == "depot_sell":
        return engine.sell_from_depot(_text(kwargs.get("item_id")), max(1, _int(kwargs.get("quantity"), 1)))
    if action == "item_buy":
        return engine.buy_item(_text(kwargs.get("item_id")), max(1, _int(kwargs.get("quantity"), 1)))
    if action == "item_use":
        return engine.use_item(_text(kwargs.get("item_id")))
    if action == "jettison":
        return engine.jettison_cargo(_text(kwargs.get("item_id")), max(1, _int(kwargs.get("quantity"), 1)))
    if action == "fabricate":
        return engine.fabricate_munitions(_text(kwargs.get("munitions_type")) or "patch_kit")
    return False, (
        f"Unknown logistics action '{action}'. "
        f"Use one of: {', '.join(LOGISTICS_ACTIONS)}."
    )
