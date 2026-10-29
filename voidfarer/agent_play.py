"""Headless AI captain: plays the game through the same HTTP API the cockpit uses."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


# Actions the policy cannot reach in an ordinary campaign, with the reason. Every other
# endpoint in the catalog must be attempted by the headless captain, so a new mechanic
# cannot ship without an AI path or an explicit justification here.
CONTEXT_ACTIONS: dict[str, str] = {
    "/api/delete-save": "lifecycle: destroys the campaign",
    "/api/load": "lifecycle: replaces live state from disk",
    "/api/new-game": "lifecycle: starts a fresh campaign",
    "/api/reset": "lifecycle: wipes the campaign",
    "/api/save": "lifecycle: persistence, not a game mechanic",
    "/api/step": "alias of /api/time/step",
    "/api/tutorial/reset": "meta: replays onboarding",
    "/api/tutorial/skip": "meta: skips onboarding",
    "/api/messages/choose": "needs an interactive message-tree node",
    "/api/messages/send": "needs a valid recipient",
    "/api/ally/form": "needs high standing and a prepared captain",
    "/api/anomaly": "prompt-driven: an anomaly must be resolved",
    "/api/combat": "prompt-driven: a hostile intercept must occur",
    "/api/pirate/resolve": "prompt-driven: a pirate toll must intercept",
    "/api/void/dive": "needs a black-hole horizon",
    "/api/void/emerge": "needs an active void traversal",
    "/api/inventory/buy": "no item shop catalog is exposed by the API",
    "/api/inventory/use": "no consumable is in the hold",
    "/api/inventory/jettison": "no item catalog is exposed by the API",
    "/api/ship/module": "needs an owned ship module",
    "/api/shipyard/chassis": "needs a shipyard and a new hull purchase",
    "/api/shipyard/sell": "needs a spare hull in the shipyard",
    "/api/outpost/upgrade": "needs a founded outpost",
    "/api/drone/collect": "needs a deployed drone",
    "/api/depot/sell": "needs stock sitting in a depot",
    "/api/depot/withdraw": "needs stock sitting in a depot",
    "/api/fleet/dismiss": "needs an owned escort",
    "/api/fleet/escort/assign": "needs an owned escort",
    "/api/fleet/escort/dismiss": "needs an owned escort",
    "/api/fleet/escort/repair": "needs a damaged escort",
    "/api/fleet/refit": "needs an owned escort",
    "/api/contract/claim": "needs a completed contract",
    "/api/away/recall": "needs an active away mission",
    "/api/crew/shore": "needs crew ashore at a colony",
    "/api/crew/dismiss": "would erase the only crew roster in the run",
    "/api/story/choice": "needs an active story choice",
    "/api/trade/quantum/place": "needs a quantum-trade unlock",
}


def coverage_gaps(catalog_paths: list[str], covered: set[str]) -> list[str]:
    """Catalog endpoints with neither an AI attempt nor a documented reason."""
    return sorted(
        path for path in catalog_paths
        if path not in covered and path not in CONTEXT_ACTIONS
    )


class ApiClient:
    """Minimal JSON HTTP client for the cockpit server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 8.0) -> None:
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def get(self, path: str) -> tuple[int, dict[str, Any]]:
        request = urllib.request.Request(self.base + path, method="GET")
        return self._open(request)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        data = json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(
            self.base + path, data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        return self._open(request)

    def _open(self, request: urllib.request.Request) -> tuple[int, dict[str, Any]]:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", "replace")
                try:
                    return response.status, json.loads(raw)
                except json.JSONDecodeError:
                    return response.status, {"ok": False, "message": raw[:200]}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, {"ok": False, "message": raw[:200]}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return 0, {"ok": False, "message": f"transport failure: {exc}"}


class AiCaptain:
    """A deterministic policy that exercises every mechanic family it can reach."""

    MAX_STEPS = 200

    def __init__(self, client: ApiClient, seed: int = 42) -> None:
        self.client = client
        self.seed = seed
        self.state: dict[str, Any] = {}
        self.families: dict[str, int] = {}
        self.refusals: list[str] = []
        self.errors: list[str] = []
        self.steps_taken = 0
        self.travelled = 0
        self.visited_bodies: set[str] = set()
        self.attempted: set[str] = set()
        self.succeeded: set[str] = set()
        self.catalog_paths: list[str] = []
        self.tour_cursor = 0
        self.tour_exhausted = False

    def play(self, steps: int = 40) -> dict[str, Any]:
        status, payload = self.client.get("/api/agent/actions")
        if status == 200:
            self.catalog_paths = [entry["path"] for entry in payload.get("actions") or []]
        if not self.catalog_paths:
            self.errors.append(f"GET /api/agent/actions -> {status}: no action catalog")
        status, payload = self.client.get("/api/state")
        if status != 200:
            self.errors.append(f"GET /api/state -> {status}")
            return self.report()
        self.state = payload.get("state") or payload.get("data") or payload

        for step in range(max(1, min(steps, self.MAX_STEPS))):
            self.steps_taken = step + 1
            path, body, family = self._choose(step)
            if path is None:
                break
            status, payload = self.client.post(path, body)
            if status == 409 and payload.get("state"):
                # A blocking prompt appeared mid-step; adopt it and retry this path later.
                self.state = payload["state"]
                self.refusals.append(f"{family}: blocked by prompt")
                continue
            self.attempted.add(path)
            if status != 200:
                self.errors.append(f"POST {path} -> {status}: {payload.get('message', '')}")
                if payload.get("state"):
                    self.state = payload["state"]
                continue
            if not payload.get("ok"):
                self.refusals.append(f"{family}: {payload.get('message', 'refused')}")
                if payload.get("state"):
                    self.state = payload["state"]
                continue
            self.families[family] = self.families.get(family, 0) + 1
            self.succeeded.add(path)
            if payload.get("state"):
                self.state = payload["state"]
        return self.report()

    def _choose(self, step: int) -> tuple[str | None, dict[str, Any], str]:
        state = self.state
        ship = state.get("ship") or {}
        pending = state.get("pending_decision")
        if pending:
            choices = pending.get("choices") or []
            choice_id = ""
            if choices:
                first = choices[0]
                choice_id = first.get("id", "") if isinstance(first, dict) else str(first)
            if choice_id:
                return "/api/decision/resolve", {"choice_id": choice_id}, "decision"
        pirate = state.get("active_pirate")
        if pirate:
            return "/api/pirate/resolve", {"action": "evade"}, "pirate"
        if state.get("active_combat"):
            return "/api/combat", {"action": "fire_lasers"}, "combat"
        if state.get("active_anomaly"):
            choices = (state.get("active_anomaly") or {}).get("choices") or []
            if choices:
                choice = choices[0]
                choice_id = choice.get("choice_id") or choice.get("id") if isinstance(choice, dict) else str(choice)
                if choice_id:
                    return "/api/anomaly", {"choice_id": choice_id}, "anomaly"

        if ship.get("travel"):
            return "/api/time/step", {"ticks": 1}, "time"

        if step == 0:
            return "/api/settings/decisions", {"cadence": "relaxed"}, "settings"

        if step == 1:
            project = self._first_research_project()
            if project:
                return "/api/research/start", {"project_id": project}, "research"

        if step == 2:
            faction = self._current_faction_id()
            if faction:
                return "/api/diplomacy", {"faction_id": faction, "action": "improve"}, "diplomacy"

        # Station services live at a dock; reach one before touring menu mechanics.
        if not self._is_docked():
            dock = self._dockable_body()
            if dock and dock.get("id") != ship.get("orbiting_body_id"):
                return "/api/travel", {"body_id": dock["id"], "mode": "sublight"}, "dock"

        # The guided tour owns every even step, so a long run is guaranteed to reach the
        # station and menu mechanics instead of scanning the same rock forever.
        if step % 2 == 0:
            tour = self._next_tour_action()
            if tour is not None:
                return tour

        if not ship.get("orbiting_body_id") and not ship.get("travel"):
            body = self._pick_body(prefer_unvisited=True)
            if body:
                return "/api/orbit", {"target": body["id"]}, "orbit"

        body = state.get("orbiting_body") or {}
        if state.get("salvage_site") and not body.get("salvage_claimed"):
            return "/api/salvage", {}, "salvage"
        scoop = state.get("scoop") or {}
        if scoop.get("available"):
            return "/api/scoop", {}, "scoop"
        if body and not body.get("scan_completed"):
            return "/api/scan", {}, "scan"

        quotes = state.get("market_quotes") or {}
        if quotes:
            cargo = ship.get("cargo") or {}
            used = sum(int(v) for v in cargo.values())
            capacity = int(ship.get("cargo_capacity") or 0)
            if cargo and capacity and used >= capacity - 2:
                item = next((k for k, v in cargo.items() if int(v) > 0), None)
                if item:
                    return "/api/trade", {"commodity_id": item, "quantity": 1, "is_buy": False}, "trade"
            commodity = self._cheapest_quote(quotes)
            if commodity and step % 2 == 0:
                return "/api/trade", {"commodity_id": commodity, "quantity": 1, "is_buy": True}, "trade"

        if body and body.get("landable") and not ship.get("landed_body_id") and step % 3 == 0:
            return "/api/land", {"target": body["id"]}, "land"

        if step % 20 == 5:
            system = (state.get("current_system") or {}).get("connections") or []
            if system:
                return "/api/jump", {"target": system[step % len(system)]}, "jump"

        # Touristing between bodies is the last resort, not the default: otherwise the
        # captain spends the whole run in transit and never exercises a station mechanic.
        if step % 12 == 6:
            target_body = self._pick_body(prefer_unvisited=True)
            current_id = ship.get("orbiting_body_id")
            if target_body and target_body["id"] != current_id:
                self.travelled += 1
                self.visited_bodies.add(str(target_body["id"]))
                return "/api/travel", {"body_id": target_body["id"], "mode": "sublight"}, "travel"

        return "/api/time/step", {"ticks": 1}, "time"

    # A guided tour of the non-emergency mechanics, built from the live snapshot. Each
    # builder returns None when the state cannot support it, so the captain never posts
    # nonsense just to claim coverage.
    def _next_tour_action(self) -> tuple[str, dict[str, Any], str] | None:
        builders = (
            self._tour_power,
            self._tour_reactor,
            self._tour_route,
            self._tour_messages,
            self._tour_contracts,
            self._tour_refuel,
            self._tour_repair,
            self._tour_crew,
            self._tour_upgrade,
            self._tour_weapon,
            self._tour_shipmod,
            self._tour_outpost,
            self._tour_surface,
            self._tour_away,
            self._tour_ai,
            self._tour_codex,
            self._tour_mastery,
            self._tour_training,
            self._tour_depot,
            self._tour_preview,
            self._tour_stance,
            self._tour_weapon_set,
            self._tour_events,
            self._tour_crew_train,
            self._tour_ability,
            self._tour_drone_buy,
            self._tour_drone_deploy,
            self._tour_mercenary,
            self._tour_escort,
            self._tour_time_speed,
            self._tour_navigate,
            self._tour_war,
            self._tour_dock,
            self._tour_point,
            self._tour_weapon_install,
            self._tour_reactor_vent,
            self._tour_reactor_repair,
            self._tour_time_pause,
            self._tour_time_resume,
            self._tour_shipmod_remove,
            self._tour_orbit,
            self._tour_salvage,
            self._tour_scoop,
        )
        attempts = 0
        while attempts < len(builders):
            builder = builders[self.tour_cursor % len(builders)]
            self.tour_cursor += 1
            attempts += 1
            action = builder()
            if action is not None:
                path = action[0]
                if path not in self.attempted:
                    return action
        self.tour_exhausted = True
        return None

    def _tour_power(self):
        return "/api/power", {"engines": 25, "shields": 25, "sensors": 25, "weapons": 25}, "power"

    def _tour_reactor(self):
        modes = (self.state.get("reactor") or {}).get("modes") or ["balanced"]
        if isinstance(modes, dict):
            mode = next(iter(modes), "balanced")
        elif isinstance(modes[0], str):
            mode = modes[0]
        else:
            mode = (modes[0] or {}).get("id", "balanced")
        return "/api/reactor/mode", {"mode": mode}, "reactor"

    def _tour_route(self):
        connections = (self.state.get("current_system") or {}).get("connections") or []
        if not connections:
            return None
        return "/api/route", {"system_id": connections[0]}, "route"

    def _tour_messages(self):
        for message in self.state.get("messages") or []:
            if isinstance(message, dict) and not message.get("read") and message.get("id"):
                return "/api/messages/read", {"message_id": message["id"]}, "messages"
        return None

    def _tour_contracts(self):
        return "/api/contracts/refresh", {}, "contracts"

    def _tour_refuel(self):
        ship = self.state.get("ship") or {}
        if not self._is_docked():
            return None
        if int(ship.get("credits") or 0) < 100 or int(ship.get("fuel") or 0) >= int(ship.get("max_fuel") or 0):
            return None
        return "/api/refuel", {"amount": 10}, "refuel"

    def _tour_repair(self):
        ship = self.state.get("ship") or {}
        if not self._is_docked() or int(ship.get("hull") or 0) >= int(ship.get("max_hull") or 0):
            return None
        return "/api/repair", {}, "repair"

    def _tour_crew(self):
        roles = self.state.get("crew_roles") or []
        if not roles or not self._is_docked():
            return None
        role = roles[0] if isinstance(roles[0], dict) else {"id": str(roles[0]), "cost": 0}
        if int((self.state.get("ship") or {}).get("credits") or 0) < int(role.get("cost") or 0):
            return None
        return "/api/crew/recruit", {"role_id": role.get("id", "")}, "crew"

    def _tour_upgrade(self):
        catalog = self.state.get("catalog_upgrades") or []
        if not catalog or not self._is_docked():
            return None
        item = catalog[0] if isinstance(catalog[0], dict) else {"id": str(catalog[0]), "cost": 0}
        if int((self.state.get("ship") or {}).get("credits") or 0) < int(item.get("cost") or 0):
            return None
        return "/api/upgrade", {"upgrade_id": item.get("id", "")}, "upgrade"

    def _tour_weapon(self):
        owned = (self.state.get("ship") or {}).get("weapons") or []
        catalog = self.state.get("catalog_weapons") or []
        known = {w.get("id") for w in catalog if isinstance(w, dict)}
        for weapon_id in owned:
            if weapon_id in known and weapon_id != "pulse_laser":
                return "/api/weapons/install", {"weapon_id": weapon_id}, "weapons"
        return None

    def _tour_shipmod(self):
        report = self.state.get("ship_mods") or {}
        available = report.get("available") or []
        if not available or not self._is_docked():
            return None
        item = available[0]
        if not isinstance(item, dict):
            return None
        slot = item.get("slot")
        mod_id = item.get("id") or item.get("mod_id")
        if not slot or not mod_id:
            return None
        return "/api/shipmods/install", {"action": "install", "slot": slot, "mod_id": mod_id}, "shipmods"

    def _tour_outpost(self):
        options = self.state.get("outpost_options") or []
        option = options[0] if options and isinstance(options[0], dict) else {}
        body = self.state.get("orbiting_body") or {}
        body_id = option.get("body_id") or body.get("id")
        if options and isinstance(options[0], str):
            outpost_type = options[0]
        else:
            outpost_type = option.get("outpost_type") or option.get("id")
        if not outpost_type:
            catalog = self.state.get("outpost_catalog") or []
            if catalog and isinstance(catalog[0], dict):
                outpost_type = catalog[0].get("id")
        if not body_id or not outpost_type:
            return None
        return "/api/outpost/build", {"body_id": body_id, "outpost_type": outpost_type}, "outpost"

    def _tour_surface(self):
        report = self.state.get("surface_report") or {}
        if not report.get("landed"):
            return None
        for operation in report.get("operations") or []:
            if (isinstance(operation, dict) and operation.get("id")
                    and operation.get("available", True) and not operation.get("used")):
                return "/api/surface/op", {"operation_id": operation["id"]}, "surface"
        return None

    def _tour_away(self):
        report = self.state.get("away_report") or {}
        for mission in report.get("available") or []:
            if (isinstance(mission, dict) and mission.get("id")
                    and mission.get("available", True) and not mission.get("worked")):
                mission_type = mission.get("mission_type") or mission.get("type") or mission["id"]
                return "/api/away/launch", {"mission_type": mission_type}, "away"
        return None

    def _tour_ai(self):
        system_id = (self.state.get("current_system") or {}).get("id")
        for captain in self.state.get("ai_captains") or []:
            if isinstance(captain, dict) and captain.get("system_id") == system_id and captain.get("id"):
                return "/api/ai/interact", {"captain_id": captain["id"], "action": "hail"}, "ai"
        return None

    def _tour_codex(self):
        codex = self.state.get("codex") or {}
        for entry in codex.get("entries") or []:
            if isinstance(entry, dict) and entry.get("ready") and not entry.get("claimed") and entry.get("id"):
                return "/api/codex/claim", {"entry_id": entry["id"]}, "codex"
        return None

    def _tour_mastery(self):
        talents = self.state.get("catalog_talents") or {}
        keys = list(talents) if isinstance(talents, dict) else []
        if not keys:
            return None
        return "/api/mastery/unlock", {"talent_id": keys[0]}, "mastery"

    def _tour_training(self):
        skills = self.state.get("character_skill_catalog") or {}
        keys = list(skills) if isinstance(skills, dict) else []
        if not keys:
            return None
        return "/api/character/train", {"skill": keys[0]}, "training"

    def _tour_depot(self):
        system_id = (self.state.get("current_system") or {}).get("id")
        manifest = self.state.get("inventory_manifest") or []
        if not manifest or not isinstance(manifest[0], dict):
            return None
        depot = next(
            (d for d in (self.state.get("depots") or [])
             if isinstance(d, dict) and d.get("system_id") == system_id),
            None,
        )
        if depot is None:
            return None
        item_id = manifest[0].get("id")
        if not item_id:
            return None
        return "/api/depot/deposit", {"item_id": item_id, "quantity": 1}, "depot"

    def _tour_preview(self):
        for body in (self.state.get("current_system") or {}).get("bodies") or []:
            if isinstance(body, dict) and body.get("id") and body.get("body_type") != "star":
                return "/api/travel/preview", {"body_id": body["id"]}, "preview"
        return None

    def _tour_stance(self):
        return "/api/combat/stance", {"stance": "balanced"}, "stance"

    def _tour_weapon_set(self):
        owned = (self.state.get("ship") or {}).get("weapons") or []
        if not owned:
            return None
        return "/api/weapons/set", {"weapon_id": owned[0]}, "weapon_set"

    def _tour_events(self):
        for event in self.state.get("events") or []:
            if isinstance(event, dict) and not event.get("dismissed") and event.get("id"):
                return "/api/events/dismiss", {"event_id": event["id"]}, "events"
        return None

    def _tour_crew_train(self):
        if not self._is_docked():
            return None
        for member in self.state.get("crew") or []:
            if isinstance(member, dict) and member.get("id") and member.get("status") == "active":
                return "/api/crew/train", {"crew_id": member["id"]}, "crew_train"
        return None

    def _tour_ability(self):
        for ability_id, ability in (self.state.get("character_abilities") or {}).items():
            if isinstance(ability, dict) and ability.get("unlocked", True):
                return "/api/character/ability", {"ability_id": ability_id}, "ability"
        return None

    def _tour_drone_buy(self):
        if not self._is_docked():
            return None
        types = (self.state.get("catalog_drones") or {})
        drone_type = next(iter(types), "mining") if isinstance(types, dict) else "mining"
        return "/api/drone/buy", {
            "drone_type": drone_type,
            "system_id": (self.state.get("current_system") or {}).get("id", ""),
        }, "drone"

    def _tour_drone_deploy(self):
        if not self._is_docked():
            return None
        drones = (self.state.get("ship") or {}).get("fleet_drones") or []
        if not drones:
            return None
        return "/api/drone/deploy", {
            "drone_id": str(drones[0].get("id", "")),
            "system_id": (self.state.get("current_system") or {}).get("id", ""),
        }, "drone"

    def _tour_orbit(self):
        body = self.state.get("orbiting_body") or {}
        target = body.get("id")
        if not target:
            candidate = next(
                (b for b in (self.state.get("current_system") or {}).get("bodies") or []
                 if isinstance(b, dict) and b.get("id")),
                None,
            )
            target = candidate.get("id") if candidate else None
        if not target:
            return None
        return "/api/orbit", {"target": target}, "orbit"

    def _tour_salvage(self):
        return "/api/salvage", {}, "salvage"

    def _tour_scoop(self):
        return "/api/scoop", {}, "scoop"

    def _tour_mercenary(self):
        if not self._is_docked():
            return None
        catalog = self.state.get("mercenary_catalog") or {}
        keys = list(catalog) if isinstance(catalog, dict) else []
        if not keys:
            return None
        return "/api/mercenary/hire", {"merc_id": keys[0]}, "mercenary"

    def _tour_escort(self):
        if not self._is_docked():
            return None
        catalog = (self.state.get("fleet_manager") or {}).get("catalog") or {}
        keys = list(catalog) if isinstance(catalog, dict) else []
        if not keys:
            return None
        return "/api/fleet/escort/buy", {
            "escort_type": keys[0],
            "system_id": (self.state.get("current_system") or {}).get("id", ""),
        }, "fleet"

    def _tour_time_speed(self):
        return "/api/time/speed", {"speed": 1.0}, "time_speed"

    def _tour_navigate(self):
        connections = (self.state.get("current_system") or {}).get("connections") or []
        if not connections:
            return None
        return "/api/navigate", {"system_id": connections[0]}, "navigate"

    def _tour_war(self):
        for war in self.state.get("wars") or []:
            if isinstance(war, dict) and war.get("active") and war.get("defender_id"):
                return "/api/war/support", {
                    "war_id": war.get("id", ""),
                    "faction_id": war["defender_id"],
                    "credits": 100,
                }, "war"
        return None

    def _tour_dock(self):
        if self._is_docked():
            return None
        dock = self._dockable_body()
        ship = self.state.get("ship") or {}
        if dock and dock.get("id") != ship.get("orbiting_body_id"):
            return "/api/travel", {"body_id": dock["id"], "mode": "sublight"}, "dock"
        return None

    def _tour_point(self):
        if (self.state.get("ship") or {}).get("travel"):
            return None
        return "/api/travel/point", {"distance_au": 4.0, "angle": 0.75, "mode": "sublight"}, "point"

    def _tour_weapon_install(self):
        owned = (self.state.get("ship") or {}).get("weapons") or []
        if not owned or not self._is_docked():
            return None
        return "/api/weapons/install", {"weapon_id": owned[0]}, "weapon_install"

    def _tour_reactor_vent(self):
        return "/api/reactor/vent", {}, "reactor_vent"

    def _tour_reactor_repair(self):
        return "/api/reactor/repair", {}, "reactor_repair"

    def _tour_time_pause(self):
        if (self.state.get("time") or {}).get("is_paused"):
            return None
        return "/api/time/pause", {}, "time_pause"

    def _tour_time_resume(self):
        if not (self.state.get("time") or {}).get("is_paused"):
            return None
        return "/api/time/resume", {}, "time_resume"

    def _tour_shipmod_remove(self):
        installed = (self.state.get("ship_mods") or {}).get("installed") or {}
        slot = next(iter(installed), "frame")
        return "/api/shipmods/remove", {"slot": slot}, "shipmod_remove"

    def _is_docked(self) -> bool:
        return bool((self.state.get("orbiting_body") or {}).get("station_dockable"))

    def _dockable_body(self) -> dict[str, Any] | None:
        for body in (self.state.get("current_system") or {}).get("bodies") or []:
            if isinstance(body, dict) and body.get("station_dockable"):
                return body
        return None

    def _current_faction_id(self) -> str | None:
        system_id = (self.state.get("current_system") or {}).get("id")
        politics = self.state.get("galactic_politics") or {}
        owner = (politics.get("systems") or {}).get(system_id) or {}
        if owner.get("owner_id"):
            return str(owner["owner_id"])
        name = (self.state.get("current_system") or {}).get("faction")
        for faction_id in self.state.get("factions") or []:
            if str(faction_id).replace("_", " ").lower() == str(name or "").lower():
                return str(faction_id)
        return None

    def _pick_body(self, prefer_unvisited: bool = False) -> dict[str, Any] | None:
        bodies = [
            b for b in (self.state.get("current_system") or {}).get("bodies", [])
            if b.get("body_type") != "star"
        ]
        if not bodies:
            return None
        if prefer_unvisited:
            fresh = [b for b in bodies if b.get("id") not in self.visited_bodies]
            if fresh:
                bodies = fresh
        return min(bodies, key=lambda b: float(b.get("orbit_radius") or 0))

    def _cheapest_quote(self, quotes: Any) -> str | None:
        priced: list[tuple[float, str]] = []
        items = quotes if isinstance(quotes, list) else list((quotes or {}).values())
        for quote in items:
            if not isinstance(quote, dict):
                continue
            commodity_id = str(quote.get("commodity_id") or quote.get("id") or "")
            price = quote.get("buy_price") or quote.get("buy") or quote.get("price")
            if commodity_id and isinstance(price, (int, float)):
                priced.append((float(price), commodity_id))
        return min(priced)[1] if priced else None

    def _first_research_project(self) -> str | None:
        research = self.state.get("research") or {}
        projects = research.get("projects") or research.get("available") or []
        if isinstance(projects, dict):
            projects = list(projects.values())
        for project in projects:
            if isinstance(project, dict):
                if project.get("completed"):
                    continue
                if project.get("id"):
                    return str(project["id"])
            elif isinstance(project, str):
                return project
        return None

    def report(self) -> dict[str, Any]:
        ship = self.state.get("ship") or {}
        return {
            "ok": not self.errors and len(self.families) >= 4,
            "steps": self.steps_taken,
            "families": dict(sorted(self.families.items())),
            "family_count": len(self.families),
            "attempted": sorted(self.attempted),
            "attempted_count": len(self.attempted),
            "succeeded": sorted(self.succeeded),
            "succeeded_count": len(self.succeeded),
            "coverage_gaps": coverage_gaps(self.catalog_paths, self.attempted),
            "refusals": self.refusals[:12],
            "errors": self.errors[:12],
            "final": {
                "credits": ship.get("credits"),
                "hull": ship.get("hull"),
                "fuel": ship.get("fuel"),
                "orbiting": ship.get("orbiting_body_id"),
                "tick": (self.state.get("time") or {}).get("tick"),
            },
        }
