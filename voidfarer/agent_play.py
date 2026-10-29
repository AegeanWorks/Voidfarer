"""Headless AI captain: plays the game through the same HTTP API the cockpit uses."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


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
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                return exc.code, json.loads(raw)
            except json.JSONDecodeError:
                return exc.code, {"ok": False, "message": raw[:200]}


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

    def play(self, steps: int = 40) -> dict[str, Any]:
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
                # A blocking prompt appeared mid-step; adopt it and resolve next loop.
                self.state = payload["state"]
                self.refusals.append(f"{family}: blocked by prompt")
                continue
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
            commodity = self._cheapest_quote(quotes)
            if commodity and step % 2 == 0:
                return "/api/trade", {"commodity_id": commodity, "quantity": 1, "is_buy": True}, "trade"

        if body and body.get("landable") and not ship.get("landed_body_id") and step % 3 == 0:
            return "/api/land", {"target": body["id"]}, "land"

        if step % 5 == 0:
            system = (state.get("current_system") or {}).get("connections") or []
            if system:
                return "/api/jump", {"target": system[step % len(system)]}, "jump"

        target_body = self._pick_body(prefer_unvisited=True)
        current_id = ship.get("orbiting_body_id")
        if target_body and target_body["id"] != current_id:
            self.travelled += 1
            self.visited_bodies.add(str(target_body["id"]))
            return "/api/travel", {"body_id": target_body["id"], "mode": "sublight"}, "travel"

        if step % 4 == 0:
            return "/api/time/step", {"ticks": 1}, "time"
        return "/api/time/step", {"ticks": 1}, "time"

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
