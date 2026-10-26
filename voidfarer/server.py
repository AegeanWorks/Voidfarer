"""Zero-dependency embedded HTTP server and REST API for the VoidFarer Web Cockpit."""

from __future__ import annotations

import json
import math
import mimetypes
import os
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any

from voidfarer.economy import get_galactic_trade_routes
from voidfarer.engine import STATIC_SNAPSHOT_KEYS, SimulationEngine, static_catalogs
from voidfarer.frontier import MERCENARY_CATALOG
from voidfarer.inventory import get_inventory_manifest
from voidfarer.mapmods import MAP_MODIFIER_CATALOG, aggregate_map_modifiers, system_modifier_summary
from voidfarer.shipmods import get_ship_mod
from voidfarer.storage import StorageManager, resolve_slot_name
from voidfarer.upgrades import (
    CATALOG_CHASSIS,
    CATALOG_UPGRADES,
    get_available_chassis,
    get_available_upgrades,
)

MAX_BODY_BYTES = 1024 * 1024
# A client that sends this header has /api/catalogs cached; its state payloads omit them.
CATALOG_CACHE_HEADER = "X-VoidFarer-Catalogs"


def _int_field(body: dict[str, Any], key: str, default: int, minimum: int | None = None) -> int:
    value = body.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"'{key}' must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' must be an integer") from None
    if isinstance(value, float) and value != parsed:
        raise ValueError(f"'{key}' must be an integer")
    if minimum is not None and parsed < minimum:
        raise ValueError(f"'{key}' must be at least {minimum}")
    return parsed


def _float_field(body: dict[str, Any], key: str, default: float, minimum: float | None = None) -> float:
    value = body.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f"'{key}' must be a number")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' must be a number") from None
    if not math.isfinite(parsed):
        raise ValueError(f"'{key}' must be finite")
    if minimum is not None and parsed < minimum:
        raise ValueError(f"'{key}' must be at least {minimum}")
    return parsed


def _bool_field(body: dict[str, Any], key: str, default: bool) -> bool:
    value = body.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise ValueError(f"'{key}' must be a boolean")




BASE_TICK_SECONDS = 0.5
MIN_TICK_SECONDS = 0.05
AUTOSAVE_SECONDS = 15.0


def tick_interval(speed: float) -> float:
    """Wall-clock seconds between simulation ticks for a chrono speed multiplier."""
    return max(MIN_TICK_SECONDS, BASE_TICK_SECONDS / max(0.1, float(speed or 0.0)))

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server handling concurrent HUD telemetry requests."""
    daemon_threads = True


class VoidFarerHandler(BaseHTTPRequestHandler):
    """Handles REST API actions and serves static cockpit assets."""

    engine: SimulationEngine
    storage: StorageManager
    static_dir: Path

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard access logs for clean terminal output."""
        return

    def _send_json(self, data: Any, status: int = 200) -> None:
        if self.headers.get(CATALOG_CACHE_HEADER) and isinstance(data, dict):
            data = self._without_catalogs(data)
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    @staticmethod
    def _without_catalogs(data: dict[str, Any]) -> dict[str, Any]:
        """Drop static catalogs from the snapshot a response carries under `state` or `data`."""
        trimmed = dict(data)
        for key in ("state", "data"):
            snapshot = trimmed.get(key)
            if isinstance(snapshot, dict) and "ship" in snapshot:
                trimmed[key] = {k: v for k, v in snapshot.items() if k not in STATIC_SNAPSHOT_KEYS}
        return trimmed

    def _send_error_json(self, message: str, status: int = 400, include_state: bool = False) -> None:
        payload: dict[str, Any] = {"ok": False, "error": message, "message": message}
        if include_state and getattr(self, "engine", None) is not None:
            payload["state"] = self.engine.get_status_snapshot()
        self._send_json(payload, status=status)

    def _read_body_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except (TypeError, ValueError):
            raise ValueError("Invalid Content-Length header") from None
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError("Request body is too large or malformed")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Request body must be valid UTF-8") from None
        try:
            parsed = json.loads(decoded)
        except json.JSONDecodeError:
            raise ValueError("Request body must be valid JSON") from None
        if not isinstance(parsed, dict):
            raise ValueError("Request body must be a JSON object")
        return parsed

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", f"Content-Type, {CATALOG_CACHE_HEADER}")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        if path == "/api/state":
            include_static = not self.headers.get(CATALOG_CACHE_HEADER)
            snapshot = self.engine.get_status_snapshot(include_static=include_static)
            self._send_json({"ok": True, "data": snapshot})
            return

        if path == "/api/catalogs":
            self._send_json({"ok": True, "data": static_catalogs()})
            return

        if path == "/api/galaxy":
            with self.engine.lock:
                systems_data = {
                    sid: s.to_dict() for sid, s in self.engine.state.systems.items()
                }
            self._send_json({"ok": True, "systems": systems_data})
            return

        if path == "/api/contracts":
            with self.engine.lock:
                contracts = [c.to_dict() for c in self.engine.state.ship.active_contracts]
            self._send_json({"ok": True, "contracts": contracts})
            return

        if path == "/api/relics":
            with self.engine.lock:
                relics = [r.to_dict() for r in self.engine.state.ship.relics]
            self._send_json({"ok": True, "relics": relics})
            return

        if path == "/api/tutorial":
            with self.engine.lock:
                tut = self.engine.state.ship.tutorial.to_dict()
            self._send_json({"ok": True, "tutorial": tut})
            return

        if path == "/api/story":
            with self.engine.lock:
                story = self.engine.state.ship.story.to_dict()
            self._send_json({"ok": True, "story": story, "status": self.engine.story_status()})
            return

        if path == "/api/void":
            self._send_json({"ok": True, "void": self.engine.void_status()})
            return

        if path == "/api/time":
            with self.engine.lock:
                time_data = self.engine.state.time.to_dict()
            self._send_json({"ok": True, "time": time_data})
            return

        if path == "/api/reactor":
            report = self.engine.get_reactor_report()
            self._send_json({"ok": True, "reactor": report, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/mapmods":
            with self.engine.lock:
                system = self.engine.current_system
                payload = {
                    "system_id": system.id,
                    "system_name": system.name,
                    "modifiers": system_modifier_summary(system),
                    "effects": aggregate_map_modifiers(system),
                    "catalog": [m.to_dict() for m in MAP_MODIFIER_CATALOG],
                }
            self._send_json({"ok": True, **payload})
            return

        if path == "/api/shipmods":
            report = self.engine.get_ship_mod_report()
            self._send_json({"ok": True, "ship_mods": report, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/crew":
            self._send_json({"ok": True, "crew": self.engine.get_crew_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/away":
            self._send_json({"ok": True, "away": self.engine.get_away_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/trade/quantum":
            self._send_json({"ok": True, "quantum": self.engine.get_quantum_trade_report()})
            return

        if path == "/api/surface":
            self._send_json({"ok": True, "surface": self.engine.get_surface_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/weapons":
            self._send_json({"ok": True, "weapons": self.engine.get_weapon_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/messages/trees":
            self._send_json({"ok": True, "trees": self.engine.get_message_tree_report()})
            return

        if path == "/api/simulation":
            report = self.engine.get_simulation_report()
            self._send_json({"ok": True, "simulation": report, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/character":
            self._send_json({"ok": True, "character": self.engine.get_character_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/research":
            self._send_json({"ok": True, "research": self.engine.get_research_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/outposts":
            self._send_json({"ok": True, "outposts": self.engine.get_outpost_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/diplomacy":
            with self.engine.lock:
                leaders = [leader.to_dict() for leader in self.engine.state.faction_leaders]
                wars = [war.to_dict() for war in self.engine.state.wars]
                eliminated = list(self.engine.state.eliminated_factions)
            self._send_json({"ok": True, "leaders": leaders, "wars": wars, "eliminated": eliminated})
            return

        if path == "/api/fleet/ships":
            self._send_json({"ok": True, "fleet": self.engine.get_fleet_manager_report(), "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/economy":
            with self.engine.lock:
                econ_data = self.engine.state.economy.to_dict()
                routes = get_galactic_trade_routes(self.engine.state.systems, self.engine.state.economy)
            self._send_json({"ok": True, "economy": econ_data, "trade_routes": routes})
            return

        if path == "/api/quests":
            with self.engine.lock:
                quests = self.engine.get_quests()
            self._send_json({"ok": True, "quests": quests})
            return

        if path == "/api/ai":
            with self.engine.lock:
                captains = [c.to_dict() for c in self.engine.state.ai_captains]
            self._send_json({"ok": True, "captains": captains})
            return

        if path == "/api/messages":
            with self.engine.lock:
                messages = [m.to_dict() for m in self.engine.state.messages]
            self._send_json({"ok": True, "messages": messages})
            return

        if path == "/api/depots":
            with self.engine.lock:
                depots = [d.to_dict() for d in self.engine.state.depots]
            self._send_json({"ok": True, "depots": depots})
            return

        if path == "/api/fleet":
            with self.engine.lock:
                fleet = [
                    {
                        **d.to_dict(),
                        "yield_rate": round(d.efficiency * (0.5 + d.integrity / 200.0), 2),
                    }
                    for d in self.engine.state.ship.fleet_drones
                ]
            self._send_json({"ok": True, "fleet": fleet, "mercenaries": MERCENARY_CATALOG})
            return

        if path == "/api/inventory":
            with self.engine.lock:
                manifest = get_inventory_manifest(self.engine.state.ship.cargo)
                cargo_data = dict(self.engine.state.ship.cargo)
                capacity = self.engine.state.ship.cargo_capacity
            self._send_json({"ok": True, "cargo": cargo_data, "cargo_capacity": capacity, "manifest": manifest})
            return

        if path == "/api/shipyard":
            with self.engine.lock:
                ship = self.engine.state.ship
                equipped = dict(ship.equipped_upgrades)
                avail_upg = [u.to_dict() for u in get_available_upgrades(ship.equipped_upgrades)]
                avail_chassis = [c.to_dict() for c in get_available_chassis(self.engine.current_chassis_id)]
                cat_upg = [u.to_dict() for u in CATALOG_UPGRADES]
                cat_chassis = [c.to_dict() for c in CATALOG_CHASSIS]
            self._send_json({
                "ok": True,
                "equipped_upgrades": equipped,
                "available_upgrades": avail_upg,
                "catalog_upgrades": cat_upg,
                "available_chassis": avail_chassis,
                "catalog_chassis": cat_chassis,
                "current_ship_class": ship.ship_class,
            })
            return

        if path == "/api/saves":
            self._send_json({"ok": True, "saves": self.storage.list_saves()})
            return

        # Serve static assets
        if path == "/" or path == "":
            rel_path = "index.html"
        else:
            rel_path = path.lstrip("/")

        file_path = (self.static_dir / rel_path).resolve()
        # Security check to prevent directory traversal
        try:
            file_path.relative_to(self.static_dir.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Asset not found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Error reading file")

    def do_POST(self) -> None:
        try:
            self._do_post()
        except OSError as exc:
            self._send_error_json(f"State persistence failed: {exc}", status=HTTPStatus.INTERNAL_SERVER_ERROR)
        except (ValueError, TypeError) as exc:
            self._send_error_json(str(exc), status=HTTPStatus.BAD_REQUEST)

    def _do_post(self) -> None:
        path = self.path.split("?")[0]
        body = self._read_body_json()

        pending = self.engine.state.pending_decision
        if pending is not None and path not in ("/api/decision/resolve", "/api/time", "/api/save"):
            self._send_error_json(
                f"Decision required: {pending.title}. Resolve it before continuing.",
                status=HTTPStatus.CONFLICT,
                include_state=True,
            )
            return

        if (
            self.engine.state.active_pirate is not None
            and path not in ("/api/pirate/resolve", "/api/time", "/api/save")
        ):
            pirate = self.engine.state.active_pirate
            self._send_error_json(
                f"Pirate intercept unresolved: {pirate.band_name} demands {pirate.toll_credits} cr. "
                "Pay, fight, or evade before continuing.",
                status=HTTPStatus.CONFLICT,
                include_state=True,
            )
            return

        if path == "/api/save":
            slot = resolve_slot_name(body.get("slot"))
            self.storage.save(self.engine.state, slot=slot)
            self._send_json({
                "ok": True,
                "slot": slot,
                "message": f"Game saved ({slot}).",
                "saves": self.storage.list_saves(),
            })
            return

        if path == "/api/load":
            slot = resolve_slot_name(body.get("slot"))
            loaded = self.storage.load(slot=slot)
            if loaded is None:
                self._send_error_json(f"No save file is available for slot '{slot}'.", status=HTTPStatus.NOT_FOUND)
                return
            ok, msg = self.engine.load_state(loaded)
            self._send_json({
                "ok": ok,
                "slot": slot,
                "message": f"{msg} [{slot}]",
                "state": self.engine.get_status_snapshot(),
                "saves": self.storage.list_saves(),
            })
            return

        if path == "/api/delete-save":
            slot = resolve_slot_name(body.get("slot"))
            self.storage.clear(slot=slot)
            self._send_json({
                "ok": True,
                "slot": slot,
                "message": f"Save deleted ({slot}).",
                "saves": self.storage.list_saves(),
            })
            return

        if path == "/api/new-game":
            seed = _int_field(body, "seed", 42, minimum=0)
            slot = resolve_slot_name(body.get("slot"))
            profile = body.get("profile") if isinstance(body.get("profile"), dict) else None
            ok, msg = self.engine.reset(seed, profile=profile)
            if ok:
                self.storage.save(self.engine.state, slot=slot)
            self._send_json({
                "ok": ok,
                "slot": slot,
                "message": msg,
                "state": self.engine.get_status_snapshot(),
                "saves": self.storage.list_saves(),
            })
            return

        if path == "/api/land":
            target = str(body.get("target", ""))
            ok, msg = self.engine.land_on_body(target)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/ai/interact":
            captain_id = str(body.get("captain_id", ""))
            action = str(body.get("action", "hail"))
            commodity_id = body.get("commodity_id")
            commodity_id = str(commodity_id) if commodity_id is not None else None
            quantity = _int_field(body, "quantity", 1, minimum=1)
            ok, msg = self.engine.interact_ai(captain_id, action, commodity_id, quantity)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/messages/send":
            recipient = str(body.get("recipient", ""))
            subject = str(body.get("subject", ""))
            message_body = str(body.get("body", ""))
            ok, msg = self.engine.send_quantum_message(recipient, subject, message_body)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/messages/choose":
            ok, msg = self.engine.resolve_message_choice(
                str(body.get("message_id", "")),
                str(body.get("choice_id", "")),
            )
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/crew/recruit":
            ok, msg = self.engine.recruit_crew(str(body.get("role_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/crew/train":
            ok, msg = self.engine.train_crew_member(str(body.get("crew_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/crew/dismiss":
            ok, msg = self.engine.dismiss_crew(str(body.get("crew_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/crew/shore":
            ok, msg = self.engine.shore_leave()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/away/launch":
            mission_type = str(body.get("mission_type", ""))
            raw_crew = body.get("crew_ids")
            crew_ids = [str(cid) for cid in raw_crew] if isinstance(raw_crew, list) and raw_crew else None
            ok, msg = self.engine.launch_away_mission(mission_type, crew_ids)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/away/recall":
            ok, msg = self.engine.recall_away_mission(str(body.get("mission_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/pirate/resolve":
            ok, msg = self.engine.resolve_pirate_encounter(str(body.get("action", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/contracts/refresh":
            ok, msg = self.engine.refresh_contracts()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/decision/resolve":
            ok, msg = self.engine.resolve_decision(str(body.get("choice_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/weapons/install":
            ok, msg = self.engine.install_weapon(str(body.get("weapon_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/weapons/set":
            ok, msg = self.engine.set_primary_weapon(str(body.get("weapon_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/messages/read":
            message_id = str(body.get("message_id", ""))
            ok, msg = self.engine.mark_message_read(message_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/depot/deposit":
            item_id = str(body.get("item_id", ""))
            quantity = _int_field(body, "quantity", 1, minimum=1)
            ok, msg = self.engine.deposit_cargo(item_id, quantity)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/depot/withdraw":
            item_id = str(body.get("item_id", ""))
            quantity = _int_field(body, "quantity", 1, minimum=1)
            ok, msg = self.engine.withdraw_cargo(item_id, quantity)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/depot/sell":
            item_id = str(body.get("item_id", ""))
            quantity = _int_field(body, "quantity", 1, minimum=1)
            ok, msg = self.engine.sell_from_depot(item_id, quantity)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/mercenary/hire":
            merc_id = str(body.get("merc_id", ""))
            ok, msg = self.engine.hire_mercenary(merc_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/fleet/dismiss":
            drone_id = str(body.get("drone_id", ""))
            ok, msg = self.engine.dismiss_fleet_unit(drone_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/fleet/refit":
            drone_id = str(body.get("drone_id", ""))
            ok, msg = self.engine.refit_fleet_unit(drone_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/ally/form":
            captain_id = str(body.get("captain_id", ""))
            ok, msg = self.engine.form_alliance(captain_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/jump":
            target = body.get("target")
            if not target:
                self._send_error_json("Target system ID required")
                return
            ok, msg = self.engine.jump(str(target))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/orbit":
            target = body.get("target")
            if not target:
                self._send_error_json("Target body ID required")
                return
            ok, msg = self.engine.orbit(str(target))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/scan":
            ok, msg, info = self.engine.scan()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "discovery": info, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/salvage":
            ok, msg, report = self.engine.salvage_derelict()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "report": report, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/codex/claim":
            entry_id = str(body.get("entry_id", ""))
            if not entry_id:
                self._send_error_json("Entry ID required")
                return
            ok, msg = self.engine.claim_codex_reward(entry_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/scoop":
            ok, msg = self.engine.scoop_fuel()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/power":
            eng = _int_field(body, "engines", 25, minimum=0)
            shd = _int_field(body, "shields", 25, minimum=0)
            sen = _int_field(body, "sensors", 25, minimum=0)
            wep = _int_field(body, "weapons", 25, minimum=0)
            ok, msg = self.engine.route_power(eng, shd, sen, wep)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/reactor/mode":
            mode = str(body.get("mode", ""))
            ok, msg = self.engine.set_reactor_mode(mode)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/reactor/vent":
            ok, msg = self.engine.vent_reactor_coolant()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/reactor/repair":
            ok, msg = self.engine.repair_reactor()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/shipmods/install":
            mod_id = str(body.get("mod_id", ""))
            ok, msg = self.engine.install_ship_mod(mod_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/shipmods/remove":
            slot = str(body.get("slot", ""))
            ok, msg = self.engine.remove_ship_mod(slot)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/ship/module":
            module_id = str(body.get("module_id", ""))
            action = str(body.get("action", "install")).lower()
            if action == "install":
                ok, msg = self.engine.install_ship_mod(module_id)
            elif action in ("uninstall", "remove"):
                mod = get_ship_mod(module_id)
                ok, msg = (
                    self.engine.remove_ship_mod(mod.slot, expected_mod_id=mod.id)
                    if mod is not None
                    else (False, "Unknown ship module.")
                )
            else:
                ok, msg = False, "Unknown module action."
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/character/train":
            ok, msg = self.engine.train_character_skill(str(body.get("skill", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/character/ability":
            ok, msg = self.engine.use_character_ability(
                str(body.get("ability_id", "")),
                str(body["faction_id"]) if body.get("faction_id") else None,
            )
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/research/start":
            ok, msg = self.engine.choose_research(str(body.get("project_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/outpost/build":
            ok, msg = self.engine.build_outpost(str(body.get("body_id", "")), str(body.get("outpost_type", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/outpost/upgrade":
            ok, msg = self.engine.upgrade_outpost(str(body.get("outpost_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/diplomacy":
            ok, msg = self.engine.faction_diplomacy(
                str(body.get("faction_id", "")),
                str(body.get("action", "improve")),
                _int_field(body, "amount", 0, minimum=0),
            )
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/fleet/escort/buy":
            ok, msg = self.engine.buy_escort(
                str(body.get("escort_type", "corvette")),
                str(body["system_id"]) if body.get("system_id") else None,
            )
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/fleet/escort/assign":
            ok, msg = self.engine.assign_escort(str(body.get("ship_id", "")), str(body.get("system_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/fleet/escort/repair":
            ok, msg = self.engine.repair_escorts(_int_field(body, "amount", 60, minimum=1))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/fleet/escort/dismiss":
            ok, msg = self.engine.dismiss_escort(str(body.get("ship_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/route":
            plan = self.engine.plan_route(str(body.get("system_id", "")))
            self._send_json({"ok": plan["reachable"], "route": plan})
            return

        if path == "/api/navigate":
            ok, msg = self.engine.navigate_to(str(body.get("system_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/trade":
            comm_id = str(body.get("commodity_id", ""))
            is_buy = _bool_field(body, "is_buy", True)
            if _bool_field(body, "max", False):
                ok, msg = self.engine.trade_max(comm_id, is_buy)
            else:
                qty = _int_field(body, "quantity", 0, minimum=0)
                ok, msg = self.engine.trade(comm_id, qty, is_buy)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/trade/quantum/place":
            commodity_id = str(body.get("commodity_id", ""))
            quantity = _int_field(body, "quantity", 0, minimum=1)
            destination = str(body.get("destination_system_id", ""))
            ok, msg = self.engine.place_quantum_order(commodity_id, quantity, destination)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/surface/op":
            ok, msg = self.engine.perform_surface_operation(str(body.get("operation_id", "")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/war/support":
            war_id = str(body.get("war_id", ""))
            faction_id = str(body.get("faction_id", ""))
            credits = _int_field(body, "credits", 0, minimum=0)
            ok, msg = self.engine.support_war(war_id, faction_id, credits)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/anomaly":
            choice_id = str(body.get("choice_id", ""))
            ok, msg = self.engine.resolve_anomaly(choice_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/repair":
            amount = _int_field(body, "amount", 25, minimum=1)
            ok, msg = self.engine.repair_hull(amount)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/refuel":
            amount = _int_field(body, "amount", 20, minimum=1)
            ok, msg = self.engine.refuel(amount)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/upgrade":
            upgrade_id = str(body.get("upgrade_id", ""))
            ok, msg = self.engine.buy_upgrade(upgrade_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/drone/buy":
            drone_type = str(body.get("drone_type", "mining"))
            sys_id = body.get("system_id")
            sys_id = str(sys_id) if sys_id is not None else None
            ok, msg = self.engine.buy_drone(drone_type, sys_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/drone/deploy":
            drone_id = str(body.get("drone_id", ""))
            sys_id = str(body.get("system_id", ""))
            ok, msg = self.engine.deploy_drone(drone_id, sys_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/drone/collect":
            drone_id = body.get("drone_id")
            drone_id = str(drone_id) if drone_id is not None else None
            ok, msg, info = self.engine.collect_drone_yield(drone_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "yield": info, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/combat/stance":
            ok, msg = self.engine.set_battle_stance(str(body.get("stance", "balanced")))
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/combat":
            action = str(body.get("action", "fire_lasers"))
            ok, msg = self.engine.combat_action(action)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/contract/claim":
            contract_id = str(body.get("contract_id", ""))
            ok, msg, info = self.engine.claim_contract(contract_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "claim_info": info, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/mastery/unlock":
            talent_id = str(body.get("talent_id", ""))
            ok, msg = self.engine.unlock_talent(talent_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/step":
            dt = _float_field(body, "delta_time", 1.0, minimum=0.0)
            self.engine.step_orbits(dt)
            self.storage.save(self.engine.state)
            self._send_json({"ok": True, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/tutorial/skip":
            ok, msg = self.engine.skip_tutorial()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/tutorial/reset":
            ok, msg = self.engine.reset_tutorial()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/story/choice":
            choice_id = str(body.get("choice_id", ""))
            ok, msg = self.engine.make_story_choice(choice_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/void/dive":
            target_system_id = str(body.get("target_system_id", ""))
            ok, msg = self.engine.void_dive(target_system_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/void/emerge":
            ok, msg = self.engine.void_emerge()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/time/step":
            ticks = _int_field(body, "ticks", 1, minimum=1)
            ok, msg, summary = self.engine.step_time(ticks)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "summary": summary, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/time/speed":
            speed = _float_field(body, "speed", 1.0, minimum=0.0)
            ok, msg = self.engine.set_time_speed(speed)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/time/pause":
            ok, msg = self.engine.pause_time()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/time/resume":
            ok, msg = self.engine.resume_time()
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/inventory/use":
            item_id = str(body.get("item_id", ""))
            ok, msg = self.engine.use_item(item_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/inventory/buy":
            item_id = str(body.get("item_id", ""))
            quantity = _int_field(body, "quantity", 1, minimum=1)
            ok, msg = self.engine.buy_item(item_id, quantity)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/inventory/jettison":
            item_id = str(body.get("item_id", ""))
            quantity = _int_field(body, "quantity", 1, minimum=1)
            ok, msg = self.engine.jettison_cargo(item_id, quantity)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/shipyard/sell":
            slot = str(body.get("slot", ""))
            ok, msg = self.engine.sell_upgrade(slot)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/shipyard/chassis":
            chassis_id = str(body.get("chassis_id", ""))
            ok, msg = self.engine.buy_ship_chassis(chassis_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/travel/preview":
            body_id = str(body.get("body_id", ""))
            previews = {}
            ok_all = True
            for mode in ("sublight", "quantum"):
                ok, data = self.engine.preview_travel(body_id, mode=mode)
                previews[mode] = {"ok": ok, **(data if isinstance(data, dict) else {"message": str(data)})}
                ok_all = ok_all and ok
            self._send_json({"ok": ok_all, "previews": previews})
            return

        if path == "/api/travel":
            body_id = str(body.get("body_id", ""))
            mode = str(body.get("mode", "sublight"))
            ok, msg = self.engine.start_travel(body_id, mode=mode)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/events/dismiss":
            event_id = str(body.get("event_id", ""))
            ok, msg = self.engine.dismiss_event(event_id)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        if path == "/api/reset":
            seed = _int_field(body, "seed", 42, minimum=0)
            ok, msg = self.engine.reset(seed)
            self.storage.save(self.engine.state)
            self._send_json({"ok": ok, "message": msg, "state": self.engine.get_status_snapshot()})
            return

        self._send_error_json("Invalid API endpoint", status=HTTPStatus.NOT_FOUND)


VoidFarerHTTPHandler = VoidFarerHandler



class BackgroundServer:
    """Handle for a concurrent server + simulation ticker launched from the REPL."""

    def __init__(
        self,
        server: ThreadedHTTPServer,
        server_thread: threading.Thread,
        ticker: threading.Thread | None,
        stop_event: threading.Event,
        engine: SimulationEngine,
        storage: StorageManager,
    ) -> None:
        self.server = server
        self.server_thread = server_thread
        self.ticker = ticker
        self.stop_event = stop_event
        self.engine = engine
        self.storage = storage

    @property
    def port(self) -> int:
        return int(self.server.server_port)

    def stop(self) -> None:
        self.stop_event.set()
        if self.ticker is not None:
            self.ticker.join(timeout=2.0)
        try:
            self.storage.save(self.engine.state)
        except OSError as exc:
            sys.stderr.write(f"[WARN] Final save failed: {exc}\n")
        try:
            self.server.shutdown()
        except (OSError, RuntimeError):  # hygiene: allow best-effort socket teardown during stop
            pass
        try:
            self.server.server_close()
        except OSError:  # hygiene: allow best-effort server_close during stop
            pass
        self.server_thread.join(timeout=2.0)


def start_background_server(
    engine: SimulationEngine,
    storage: StorageManager,
    port: int = 8080,
    host: str = "127.0.0.1",
) -> BackgroundServer | None:
    """Launch the cockpit server and simulation ticker without blocking the REPL."""
    if not 0 <= port <= 65535:
        return None
    static_dir = Path(__file__).parent / "static"
    VoidFarerHandler.engine = engine
    engine.allow_decision_events = True
    VoidFarerHandler.storage = storage
    VoidFarerHandler.static_dir = static_dir

    try:
        server = ThreadedHTTPServer((host, port), VoidFarerHandler)
    except (OSError, OverflowError):
        return None

    stop_event = threading.Event()

    def _ticker_loop() -> None:
        last_save = time.monotonic()
        while not stop_event.is_set():
            time_obj = engine.state.time
            if not time_obj.is_paused and time_obj.speed > 0:
                if stop_event.wait(tick_interval(time_obj.speed)):
                    break
                engine.tick(1)
                if time.monotonic() - last_save >= AUTOSAVE_SECONDS:
                    try:
                        storage.save(engine.state)
                    except OSError as exc:
                        sys.stderr.write(f"[WARN] Autosave failed: {exc}\n")
                    last_save = time.monotonic()
            else:
                if stop_event.wait(0.2):
                    break

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    ticker = threading.Thread(target=_ticker_loop, daemon=True)
    ticker.start()
    return BackgroundServer(server, server_thread, ticker, stop_event, engine, storage)

def run_server(
    engine: SimulationEngine,
    storage: StorageManager,
    port: int = 8080,
    host: str = "127.0.0.1",
    open_browser: bool = False,
    enable_ticker: bool = True,
) -> int:
    """Start local cockpit HTTP server daemon with background temporal ticker."""
    static_dir = Path(__file__).parent / "static"
    if not 0 <= port <= 65535:
        print(f"Why: port {port} is outside the valid TCP range (0-65535).")
        print("Fix: choose a port such as 8080 or 8000.")
        return 1
    VoidFarerHandler.engine = engine
    engine.allow_decision_events = True
    VoidFarerHandler.storage = storage
    VoidFarerHandler.static_dir = static_dir

    try:
        server = ThreadedHTTPServer((host, port), VoidFarerHandler)
    except (OSError, OverflowError) as exc:
        print(f"Why: could not bind {host}:{port} ({exc}).")
        print("Fix: choose another port or stop the process already using it.")
        return 1
    url = f"http://{host}:{port}"
    print(f"\n=======================================================")
    print(f"ğŸš€ VOIDFARER HOLOGRAPHIC COCKPIT ACTIVE")
    print(f"ğŸ“¡ Cockpit HUD URL: {url}")
    print(f"â ±ï¸  Cosmic Time: {engine.state.time.current_date} (Tick #{engine.state.time.tick})")
    print(f"âš¡ Press Ctrl+C to disconnect sub-space uplink")
    print(f"=======================================================\n")

    ticker_stop = threading.Event()

    def _ticker_loop() -> None:
        last_save = time.monotonic()
        while not ticker_stop.is_set():
            time_obj = engine.state.time
            if not time_obj.is_paused and time_obj.speed > 0:
                if ticker_stop.wait(tick_interval(time_obj.speed)):
                    break
                engine.tick(1)
                if time.monotonic() - last_save >= AUTOSAVE_SECONDS:
                    try:
                        storage.save(engine.state)
                    except OSError as exc:
                        print(f"[WARN] Autosave failed: {exc}")
                    last_save = time.monotonic()
            else:
                if ticker_stop.wait(0.2):
                    break

    ticker: threading.Thread | None = None
    if enable_ticker:
        ticker = threading.Thread(target=_ticker_loop, daemon=True)
        ticker.start()

    if open_browser:
        import webbrowser

        def _launch():
            try:
                getattr(webbrowser, "open")(url)
            except (webbrowser.Error, OSError) as exc:
                print(f"Could not open the browser automatically ({exc}). Visit {url} manually.")

        threading.Timer(0.4, _launch).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down sub-space uplink...")
    finally:
        ticker_stop.set()
        if ticker is not None:
            ticker.join(timeout=2.0)
        try:
            storage.save(engine.state)
        except OSError as exc:
            print(f"[WARN] Final save failed: {exc}")
        try:
            server.shutdown()
        except (OSError, RuntimeError):  # hygiene: allow best-effort socket teardown during shutdown
            pass
        try:
            server.server_close()
        except OSError:  # hygiene: allow best-effort server_close during shutdown
            pass
    return 0
