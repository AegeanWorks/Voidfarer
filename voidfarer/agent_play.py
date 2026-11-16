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
    "/api/step": "orbit-only micro-step (delta_time); use /api/time/step for full ticks",
    "/api/tutorial/reset": "meta: replays onboarding",
    "/api/tutorial/skip": "meta: skips onboarding",
    "/api/messages/choose": "needs an interactive message-tree node",
    "/api/messages/send": "needs a valid recipient",
    "/api/ally/form": "needs high standing and a prepared captain",
    "/api/anomaly": "prompt-driven: an anomaly must be resolved",
    "/api/combat": "prompt-driven: a hostile intercept must occur",
    "/api/pirate/resolve": "prompt-driven: a pirate toll must intercept",
    "/api/customs/resolve": "prompt-driven: an active customs interdiction must intercept",
    "/api/fabricate": "needs titanium alloy in cargo hold",
    "/api/weather": "telemetry endpoint for solar space weather",
    "/api/overhaul": "needs an orbital dock and hyperlane frame wear",
    "/api/relics/fuse": "needs three relics of one rarity",
    "/api/decision/resolve": "prompt-driven: a blocking decision must be pending",
    "/api/encounter/resolve": "alias: routes to the prompt-driven decision/pirate/customs/anomaly resolvers",
    "/api/fitting/install": "alias: routes to the existing upgrade/module/weapon/chassis installers",
    "/api/fitting/remove": "alias: routes to the existing upgrade/module removals",
    "/api/fleet/action": "alias: routes to the existing drone/escort/mercenary/alliance actions",
    "/api/logistics/action": "alias: routes to the existing trade/automation/freight/depot/inventory actions",
    "/api/progress/action": "alias: routes to the existing skill/talent/ability/relic/codex actions",
    "/api/empire/action": "alias: routes to the existing research/outpost/megastructure/diplomacy actions",
    "/api/crew/action": "alias: routes to the existing recruit/train/shore/station/away actions",
    "/api/intel/action": "alias: routes the existing scan and war-support actions",
    "/api/engineering/action": "alias: routes the existing power/reactor/repair/refuel/fabricate actions",
    "/api/narrative/action": "alias: routes the existing story/tutorial/contract/event actions",
    "/api/comms/action": "alias: routes the existing captain hail/trade/hire and message actions",
    "/api/surface/action": "alias: routes the existing land/surface-operation/reconstruct actions",
    "/api/flight/action": "alias: routes the existing plot/navigate/jump/orbit/travel actions",
    "/api/reconstruct": "needs a devastated inhabited world in orbit",
    "/api/void/dive": "needs a black-hole horizon",
    "/api/void/emerge": "needs an active void traversal",
    "/api/inventory/buy": "no item shop catalog is exposed by the API",
    "/api/inventory/use": "no consumable is in the hold",
    "/api/inventory/jettison": "no item catalog is exposed by the API",
    "/api/ship/module": "needs an owned ship module",
    "/api/shipyard/chassis": "needs a shipyard and a new hull purchase",
    "/api/shipyard/sell": "needs a spare hull in the shipyard",
    "/api/outpost/upgrade": "needs a founded outpost",
    "/api/outpost/module": "needs a founded outpost and module credits",
    "/api/outpost/crew": "needs a founded outpost and available crew",
    "/api/outpost/specialize": "needs a level-3 outpost and credits",
    "/api/outpost/repair": "needs a damaged outpost and credits",
    "/api/drone/collect": "needs a deployed drone",
    "/api/depot/sell": "needs stock sitting in a depot",
    "/api/trade/automation": "needs a docked market and configured thresholds",
    "/api/trade/quantum/automation": "needs a docked market and surplus cargo",
    "/api/research/queue": "needs a valid, incomplete research project",
    "/api/research/cancel": "needs a project already in the research queue",
    "/api/depot/withdraw": "needs stock sitting in a depot",
    "/api/fleet/dismiss": "needs an owned escort",
    "/api/fleet/escort/assign": "needs an owned escort",
    "/api/fleet/escort/dismiss": "needs an owned escort",
    "/api/fleet/escort/repair": "needs a damaged escort",
    "/api/fleet/escort/train": "needs a docked escort, credits and spare experience",
    "/api/fleet/escort/role": "needs an owned escort outside combat",
    "/api/fleet/escort/captain": "needs an owned escort and an available crew member",
    "/api/fleet/refit": "needs an owned escort",
    "/api/fleet/escort/sell": "needs a docked station and an owned escort",
    "/api/contract/claim": "needs a completed contract",
    "/api/contract/swap": "needs a pending contract offer from a claim",
    "/api/away/recall": "needs an active away mission",
    "/api/crew/shore": "needs crew ashore at a colony",
    "/api/crew/station": "needs an active crew specialist",
    "/api/crew/dismiss": "would erase the only crew roster in the run",
    "/api/story/choice": "needs an active story choice",
    "/api/trade/quantum/place": "needs a quantum-trade unlock",
    "/api/combat/gambit": "needs an active fight and a local escort captain",
    "/api/outpost/link": "needs two outposts in one system",
    "/api/megastructure/restore": "needs orbit and a restorable megastructure",
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
                    return 0, {"ok": False, "message": f"invalid JSON response: {raw[:200]}"}
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

    # A runaway guard, not a comfort limit: the CLI honours any request up to this bound
    # and reports when it has to clamp (ADR-341).
    MAX_STEPS = 2000
    # Affordability gates can pass later (contracts pay out), so a refused action is
    # retried after a cooldown instead of being written off for the whole run (ADR-345).
    REFUSAL_RETRY_STEPS = 40
    # A gate that never opens (an unaffordable 3,200 cr hire on a 143 cr treasury)
    # would otherwise be retried every cooldown for the whole run; three honest
    # attempts are enough to prove it was tried later (ADR-348).
    REFUSAL_RETRY_LIMIT = 3
    RETRYABLE_REFUSAL_WORDS = (
        "insufficient credits", "cr required", "costs", "skill point",
        "level", "not enough", "requires",
    )
    # Once the guided tour is exhausted the fallback trade would otherwise fire every
    # other step and bleed credits on the spread; twelve trades exercise the mechanic.
    MAX_FALLBACK_TRADES = 12
    # Titanium is the drone haul and occupies 2 volume per unit; the captain needs
    # that much free space to bank one unit (ADR-350). Pinned against the catalog.
    TITANIUM_VOLUME = 2
    # Upkeep actions can be needed again and again; a one-shot success left the captain
    # flying on fumes for 1,400 ticks after a single refuel (ADR-349).
    REPEATABLE_MIN_INTERVAL = {"/api/refuel": 60, "/api/drone/collect": 30}

    def __init__(self, client: ApiClient, seed: int = 42) -> None:
        self.client = client
        self.seed = seed
        self.state: dict[str, Any] = {}
        self.families: dict[str, int] = {}
        self.refusals: list[str] = []
        self.errors: list[str] = []
        self.steps_taken = 0
        self.steps_requested = 0
        # Cooldowns must survive separate play() calls on the same campaign (ADR-345).
        self.total_steps = 0
        self.travelled = 0
        self.visited_bodies: set[str] = set()
        self.attempted: set[str] = set()
        self.attempted_signatures: set[tuple[str, str]] = set()
        self.succeeded: set[str] = set()
        self.catalog_paths: list[str] = []
        self.tour_cursor = 0
        self.tour_exhausted = False
        self.retry_at: dict[tuple[str, str], int] = {}
        self.refusal_attempts: dict[tuple[str, str], int] = {}
        self.repeat_last: dict[tuple[str, str], int] = {}
        self.fallback_trades = 0

    def play(self, steps: int = 40) -> dict[str, Any]:
        self.steps_requested = max(1, int(steps))
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

        for step in range(min(self.steps_requested, self.MAX_STEPS)):
            self.steps_taken = step + 1
            self.total_steps += 1
            # Phase must run on the campaign clock, not the call-local one, so a run split
            # into several play() calls follows the same path as one long call (ADR-347).
            path, body, family = self._choose(self.total_steps - 1)
            if path is None:
                break
            status, payload = self.client.post(path, body)
            if status == 409 and payload.get("state"):
                # A blocking prompt appeared mid-step; adopt it and retry this path later.
                self.state = payload["state"]
                self.refusals.append(f"{family}: blocked by prompt")
                continue
            signature = self._tour_signature(path, body or {})
            self.attempted.add(path)
            self.attempted_signatures.add(signature)
            if status != 200:
                self.errors.append(f"POST {path} -> {status}: {payload.get('message', '')}")
                if payload.get("state"):
                    self.state = payload["state"]
                continue
            if not payload.get("ok"):
                message = str(payload.get("message", "refused"))
                self.refusals.append(f"{family}: {message}")
                self._note_refusal(signature, message)
                if payload.get("state"):
                    self.state = payload["state"]
                continue
            self.families[family] = self.families.get(family, 0) + 1
            self.succeeded.add(path)
            self.retry_at.pop(signature, None)
            self.refusal_attempts.pop(signature, None)
            self.repeat_last[signature] = self.total_steps
            if payload.get("state"):
                self.state = payload["state"]
        return self.report()

    def _choose(self, step: int) -> tuple[str | None, dict[str, Any], str]:
        state = self.state
        ship = state.get("ship") or {}
        # A destroyed hull stops the clock (every time step advances 0 ticks), so a run that
        # ignores it spins forever. Claim the insurance rebuild the death overlay offers,
        # through the same engineering action the UI posts (ADR-349).
        if int(ship.get("hull") or 0) <= 0:
            return "/api/engineering/action", {"action": "insurance"}, "insurance"
        # Time can pause long after the one-shot PAUSE/RESUME tour steps ran (alerts,
        # decisions); a paused clock advances 0 ticks per step and freezes the campaign
        # while every action silently succeeds (ADR-349). Resume is state-driven.
        if (state.get("time") or {}).get("is_paused"):
            return "/api/time/resume", {}, "time_resume"
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

        customs = state.get("active_customs")
        if customs:
            return "/api/customs/resolve", {"action": "jettison"}, "customs"
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

        trade = self._trade_choice(step)
        if trade is not None:
            return trade

        if body and body.get("landable") and not ship.get("landed_body_id") and step % 3 == 0:
            return "/api/land", {"target": body["id"]}, "land"

        # A jump burns the real hop cost, not one unit; using the published estimates
        # stopped 47 attempts that could only be refused (ADR-348).
        if step % 20 == 5:
            system = (state.get("current_system") or {}).get("connections") or []
            costs = state.get("jump_fuel_costs") or {}
            fuel = int(ship.get("fuel") or 0)
            # Without a published estimate the old floor still applies: some fuel.
            affordable = [
                sid for sid in system
                if ((fuel >= int(costs[sid])) if sid in costs else fuel > 0)
            ]
            if affordable:
                return "/api/jump", {"target": affordable[step % len(affordable)]}, "jump"

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

    def _note_refusal(self, signature: tuple[str, str], message: str) -> None:
        """Schedule one bounded retry for a resource gate; drop the cooldown after the last."""
        attempts = self.refusal_attempts.get(signature, 0) + 1
        self.refusal_attempts[signature] = attempts
        if self._refusal_may_pass(message) and attempts < self.REFUSAL_RETRY_LIMIT:
            self.retry_at[signature] = self.total_steps + self.REFUSAL_RETRY_STEPS
        else:
            # A stale cooldown would read as expired and allow one more attempt.
            self.retry_at.pop(signature, None)

    def _refusal_may_pass(self, message: str) -> bool:
        """True when the refusal is a resource gate that later play can satisfy."""
        text = str(message).lower()
        return any(word in text for word in self.RETRYABLE_REFUSAL_WORDS)

    def _trade_choice(self, step: int):
        """Sell one unit when the hold is volume-full, otherwise buy one on even steps.

        Cargo capacity is measured in VOLUME, not unit count. Comparing the unit count to
        it kept the captain buying into a full hold and collecting hundreds of refusals
        (ADR-343); the snapshot now carries cargo_free_volume for this decision.
        """
        ship = self.state.get("ship") or {}
        quotes = self.state.get("market_quotes") or {}
        # The cap guards speculative buying; selling to keep the hold from jamming
        # drone collection must always work (ADR-350).
        if not quotes:
            return None
        cargo = ship.get("cargo") or {}
        capacity = int(ship.get("cargo_capacity") or 0)
        free_volume = ship.get("cargo_free_volume")
        if free_volume is None:
            free_volume = capacity - sum(int(v) for v in cargo.values())
        free_volume = int(free_volume)
        if cargo and free_volume < self.TITANIUM_VOLUME:
            item = next((k for k, v in cargo.items() if int(v) > 0), None)
            if item:
                self.fallback_trades += 1
                return "/api/trade", {"commodity_id": item, "quantity": 1, "is_buy": False}, "trade"
        commodity = self._cheapest_quote(quotes)
        if (commodity and free_volume >= 1 and step % 2 == 0
                and self.fallback_trades < self.MAX_FALLBACK_TRADES):
            self.fallback_trades += 1
            return "/api/trade", {"commodity_id": commodity, "quantity": 1, "is_buy": True}, "trade"
        return None

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
            self._tour_contract_claim,
            self._tour_swap,
            self._tour_refuel,
            self._tour_repair,
            self._tour_crew,
            self._tour_upgrade,
            self._tour_weapon,
            self._tour_shipmod,
            self._tour_outpost,
            self._tour_outpost_upgrade,
            self._tour_outpost_module,
            self._tour_outpost_crew,
            self._tour_outpost_repair,
            self._tour_outpost_specialize,
            self._tour_land,
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
            self._tour_drone_collect,
            self._tour_fleet_refit_damaged,
            self._tour_crew_autostaff,
            self._tour_mercenary,
            self._tour_escort,
            self._tour_escort_role,
            self._tour_escort_train,
            self._tour_escort_captain,
            self._tour_escort_repair,
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
            self._tour_shipmods,
            self._tour_shipmod_remove,
            self._tour_orbit,
            self._tour_salvage,
            self._tour_scoop,
            self._tour_burn_cells,
        )
        attempts = 0
        while attempts < len(builders):
            builder = builders[self.tour_cursor % len(builders)]
            self.tour_cursor += 1
            attempts += 1
            action = builder()
            if action is not None:
                path, body, _family = action
                if not self._tour_action_attempted(path, body):
                    return action
        self.tour_exhausted = True
        return None

    # One route can carry several sub-actions (the fleet and crew aliases); the tour keys
    # those on the sub-action so a newly added one is not starved by its sibling.
    # One route can carry several sub-actions (the fleet and crew aliases) or act on one
    # specific id (a contract claim); the tour keys those on that field so a sibling or a
    # second completed contract is not starved by the first attempt (ADR-344).
    SIGNATURE_ROUTES = {
        "/api/fleet/action": "action",
        "/api/crew/action": "action",
        "/api/contract/claim": "contract_id",
        # One route installs twelve different mods; keying on the path meant a single
        # early refusal (or a removal) locked every later install (ADR-352).
        "/api/shipmods/install": "mod_id",
        "/api/shipmods/remove": "slot",
    }

    def _tour_signature(self, path: str, body: dict[str, Any]) -> tuple[str, str]:
        field = self.SIGNATURE_ROUTES.get(path)
        if not field:
            return (path, "")
        return (path, str((body or {}).get(field) or ""))

    def _tour_action_attempted(self, path: str, body: dict[str, Any]) -> bool:
        signature = self._tour_signature(path, body)
        retry_at = self.retry_at.get(signature)
        if retry_at is not None:
            return self.total_steps < retry_at
        interval = self.REPEATABLE_MIN_INTERVAL.get(path)
        if interval is not None:
            last = self.repeat_last.get(signature)
            if last is None:
                return False
            return self.total_steps - last < interval
        if path in self.SIGNATURE_ROUTES:
            return signature in self.attempted_signatures
        return path in self.attempted

    def _tour_swap(self):
        """Exercise the free contract-offer swap once offers exist."""
        ship = self.state.get("ship") or {}
        offers = ship.get("contract_offers") or []
        active = ship.get("active_contracts") or []
        if not offers or not active:
            return None
        offer = offers[0] if isinstance(offers[0], dict) else None
        drop = active[-1] if isinstance(active[-1], dict) else None
        if not offer or not drop or not offer.get("id") or not drop.get("id"):
            return None
        return "/api/contract/swap", {"offer_id": offer["id"], "drop_id": drop["id"]}, "contract_swap"

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

    def _tour_contract_claim(self):
        """Bank a finished contract instead of leaving its rewards stranded (ADR-344)."""
        for contract in (self.state.get("ship") or {}).get("active_contracts") or []:
            if not isinstance(contract, dict) or not contract.get("completed"):
                continue
            contract_id = str(contract.get("id") or "")
            if not contract_id:
                continue
            body = {"contract_id": contract_id}
            if self._tour_action_attempted("/api/contract/claim", body):
                continue
            return "/api/contract/claim", body, "contract_claim"
        return None

    def _tour_refuel(self):
        ship = self.state.get("ship") or {}
        if not self._is_docked():
            return None
        if int(ship.get("credits") or 0) < 100 or int(ship.get("fuel") or 0) >= int(ship.get("max_fuel") or 0):
            return None
        return "/api/refuel", {"amount": 10}, "refuel"

    def _tour_burn_cells(self):
        """Burn one hold Quantum Fuel Cell when the tank has room (the fuel-cell emergency refuel)."""
        ship = self.state.get("ship") or {}
        cells = int((ship.get("cargo") or {}).get("fuel_cells") or 0)
        if cells < 1 or int(ship.get("fuel") or 0) >= int(ship.get("max_fuel") or 0):
            return None
        return "/api/engineering/action", {"action": "burn_cells", "quantity": 1}, "burn_cells"

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

    # Outposts keep producing after they are founded; these steps exercise the management
    # surface once a site exists. Costs mirror the engine so the captain never posts an
    # action the treasury cannot pay for (ADR-346).
    OUTPOST_UPGRADE_COST_PER_LEVEL = 450

    def _outpost_rows(self):
        return [o for o in self.state.get("outposts") or []
                if isinstance(o, dict) and o.get("id")]

    def _outpost_credits(self):
        return int((self.state.get("ship") or {}).get("credits") or 0)

    def _tour_outpost_upgrade(self):
        credits = self._outpost_credits()
        for outpost in self._outpost_rows():
            level = int(outpost.get("level") or 0)
            if level < 1 or level >= 5:
                continue
            if credits < self.OUTPOST_UPGRADE_COST_PER_LEVEL * level:
                continue
            return ("/api/outpost/upgrade",
                    {"outpost_id": outpost["id"], "level": level}, "outpost_upgrade")
        return None

    def _tour_outpost_module(self):
        credits = self._outpost_credits()
        catalog = self.state.get("outpost_modules") or {}
        if not isinstance(catalog, dict) or not catalog:
            return None
        for outpost in self._outpost_rows():
            installed = outpost.get("modules") or {}
            for module_id, module in sorted(catalog.items(),
                                            key=lambda item: int((item[1] or {}).get("cost") or 0)):
                if not isinstance(module, dict) or not module_id:
                    continue
                count = int(installed.get(module_id, 0))
                if count >= 3:
                    continue
                cost = int(module.get("cost") or 0) * (count + 1)
                if credits < cost:
                    continue
                return ("/api/outpost/module",
                        {"outpost_id": outpost["id"], "module_id": module_id}, "outpost_module")
        return None

    def _tour_outpost_crew(self):
        outposts = self._outpost_rows()
        if not outposts:
            return None
        stationed = {str(crew_id) for outpost in outposts
                     for crew_id in outpost.get("assigned_crew") or []}
        captains = {str(ship.get("captain_id") or "")
                    for ship in (self.state.get("fleet_manager") or {}).get("ships") or []
                    if isinstance(ship, dict)}
        free_crew = [
            member for member in self.state.get("crew") or []
            if isinstance(member, dict)
            and member.get("status") == "active"
            and int(member.get("injury_ticks") or 0) == 0
            and not str(member.get("station") or "")
            and str(member.get("id") or "") not in stationed
            and str(member.get("id") or "") not in captains
        ]
        if not free_crew:
            return None
        for outpost in outposts:
            capacity = int(outpost.get("crew_capacity") or 0)
            if len(outpost.get("assigned_crew") or []) >= capacity:
                continue
            return ("/api/outpost/crew",
                    {"outpost_id": outpost["id"], "crew_id": free_crew[0]["id"],
                     "action": "assign"}, "outpost_crew")
        return None

    def _tour_outpost_repair(self):
        credits = self._outpost_credits()
        for outpost in self._outpost_rows():
            if float(outpost.get("integrity") or 100.0) >= 100.0:
                continue
            if credits < int(outpost.get("repair_cost") or 0):
                continue
            return "/api/outpost/repair", {"outpost_id": outpost["id"]}, "outpost_repair"
        return None

    def _tour_outpost_specialize(self):
        credits = self._outpost_credits()
        for outpost in self._outpost_rows():
            if int(outpost.get("level") or 0) < 3:
                continue
            cost = int(outpost.get("specialization_cost") or 0)
            if credits < cost:
                continue
            current = str(outpost.get("specialization") or "")
            choice = "industry" if current != "industry" else "research"
            return ("/api/outpost/specialize",
                    {"outpost_id": outpost["id"], "specialization": choice}, "outpost_specialize")
        return None

    def _tour_land(self):
        """Reach a landable body so the surface-operation tour has real work to do."""
        ship = self.state.get("ship") or {}
        if ship.get("landed_body_id") or ship.get("travel") or ship.get("void_traversal"):
            return None
        body = self.state.get("orbiting_body") or {}
        if body.get("landable") and body.get("id"):
            return "/api/land", {"target": body["id"]}, "land"
        current = self.state.get("current_system") or {}
        target = next(
            (candidate for candidate in current.get("bodies") or []
             if isinstance(candidate, dict) and candidate.get("landable") and candidate.get("id")),
            None,
        )
        if target and ship.get("orbiting_body_id") != target["id"]:
            return "/api/travel", {"body_id": target["id"], "mode": "sublight"}, "travel"
        return None

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
        # Hailing runs over the quantum link, so any known captain is reachable even
        # when the flagship is between systems.
        for captain in self.state.get("ai_captains") or []:
            if isinstance(captain, dict) and captain.get("id"):
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

    # Bridge station per role and the drone wear mark; keep in step with the engine
    # (SimulationEngine.STATION_BY_ROLE and SimulationEngine.REFIT_WORN_INTEGRITY).
    STATION_BY_ROLE = {
        "pilot": "helm", "marine": "tactical", "engineer": "engineering",
        "scientist": "science", "medic": "medical",
    }
    REFIT_WORN_INTEGRITY = 40
    REFIT_COST = 300

    def _tour_fleet_refit_damaged(self):
        """Refit the whole worn drone line at once when a dock and credits allow it."""
        ship = self.state.get("ship") or {}
        worn = [
            drone for drone in ship.get("fleet_drones") or []
            if isinstance(drone, dict)
            and int(drone.get("integrity") or 0) <= self.REFIT_WORN_INTEGRITY
        ]
        if not worn or not self._is_docked():
            return None
        if int(ship.get("credits") or 0) < self.REFIT_COST:
            return None
        return "/api/fleet/action", {"action": "refit_damaged"}, "fleet_refit"

    def _tour_crew_autostaff(self):
        """Seat the best officer at every bridge station when the current mix is not optimal."""
        crew = [
            member for member in self.state.get("crew") or []
            if isinstance(member, dict) and member.get("status") == "active"
        ]
        if not crew:
            return None
        wanted: dict[str, str] = {}
        for role, station in self.STATION_BY_ROLE.items():
            candidates = [member for member in crew if member.get("role") == role]
            if candidates:
                best = max(
                    candidates,
                    key=lambda member: (
                        int(member.get("skill") or 0),
                        int(member.get("xp") or 0),
                        str(member.get("id") or ""),
                    ),
                )
                wanted[str(best.get("id"))] = station
        if all(
            str(member.get("station") or "") == wanted.get(str(member.get("id")), "")
            for member in crew
        ):
            return None
        return "/api/crew/action", {"action": "autostaff"}, "crew_autostaff"

    def _tour_drone_collect(self):
        """Bank drone haul: collecting pays credits and advances mining contracts."""
        ship = self.state.get("ship") or {}
        if int(ship.get("hull") or 0) <= 0:
            return None
        drones = [d for d in ship.get("fleet_drones") or [] if isinstance(d, dict)]
        if not any(int(d.get("cargo_accumulated") or 0) > 0
                   or int(d.get("credits_accumulated") or 0) > 0 for d in drones):
            return None
        free_volume = ship.get("cargo_free_volume")
        credits_only = all(int(d.get("cargo_accumulated") or 0) <= 0 for d in drones)
        if (free_volume is not None
                and int(free_volume) < self.TITANIUM_VOLUME
                and not credits_only):
            return None
        return "/api/drone/collect", {}, "drone_collect"

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

    def _escort_rows(self):
        rows = (self.state.get("fleet_manager") or {}).get("ships") or []
        return [ship for ship in rows if isinstance(ship, dict) and ship.get("id")]

    # Once an escort is bought, its squadron role, training, captain and repair are
    # reachable; each builder gates on the state the engine needs (ADR-345).
    def _tour_escort_role(self):
        for ship in self._escort_rows():
            if int(ship.get("hull") or 0) <= 0:
                continue
            current = str(ship.get("tactical_role") or "screen")
            role = "strike" if current != "strike" else "screen"
            return ("/api/fleet/escort/role",
                    {"ship_id": ship["id"], "role": role}, "escort_role")
        return None

    def _tour_escort_train(self):
        if not self._is_docked():
            return None
        credits = int((self.state.get("ship") or {}).get("credits") or 0)
        for ship in self._escort_rows():
            if int(ship.get("hull") or 0) <= 0:
                continue
            if int(ship.get("experience") or 0) >= int(ship.get("experience_max") or 0):
                continue
            if credits < int(ship.get("training_cost") or 0):
                continue
            return "/api/fleet/escort/train", {"ship_id": ship["id"]}, "escort_train"
        return None

    def _tour_escort_captain(self):
        assigned = {str(ship.get("captain_id") or "") for ship in self._escort_rows()}
        crew = [
            member for member in self.state.get("crew") or []
            if isinstance(member, dict)
            and member.get("status") == "active"
            and int(member.get("injury_ticks") or 0) == 0
            and not str(member.get("station") or "")
            and str(member.get("id") or "") not in assigned
        ]
        if not crew:
            return None
        for ship in self._escort_rows():
            if int(ship.get("hull") or 0) <= 0 or str(ship.get("captain_id") or ""):
                continue
            return ("/api/fleet/escort/captain",
                    {"ship_id": ship["id"], "crew_id": crew[0]["id"],
                     "action": "assign"}, "escort_captain")
        return None

    def _tour_escort_repair(self):
        if not self._is_docked():
            return None
        for ship in self._escort_rows():
            hull = int(ship.get("hull") or 0)
            if 0 < hull < int(ship.get("max_hull") or 0):
                return "/api/fleet/escort/repair", {"ship_id": ship["id"]}, "escort_repair"
        return None

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

    def _tour_shipmods(self):
        """Fit a structural mod at a drydock; the tour only ever removed them before (ADR-352)."""
        if not self._is_docked():
            return None
        ship_mods = self.state.get("ship_mods") or {}
        installed = ship_mods.get("installed") or {}
        catalog = [mod for mod in ship_mods.get("catalog") or []
                   if isinstance(mod, dict) and mod.get("id") and mod.get("slot")]
        if not catalog:
            return None
        credits = int((self.state.get("ship") or {}).get("credits") or 0)
        used = int((self.state.get("ship") or {}).get("cargo_used_volume") or 0)
        # A full hold makes every capacity-shedding mod impossible, so fit the cheaper
        # capacity-neutral or capacity-raising mods first and only then try the rest
        # (ADR-352); the engine stays the final authority on overflow.
        candidates = [
            mod for mod in sorted(catalog, key=lambda item: int(item.get("cost") or 0))
            if not str(installed.get(mod["slot"]) or "")
            and credits >= int(mod.get("cost") or 0)
        ]
        roomy = [mod for mod in candidates
                 if int((mod.get("effects") or {}).get("cargo_capacity") or 0) >= 0]
        for mod in roomy or candidates:
            return "/api/shipmods/install", {"mod_id": mod["id"]}, "shipmods"
        return None

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
            "steps_requested": self.steps_requested,
            "steps_capped": self.steps_requested > self.MAX_STEPS,
            "families": dict(sorted(self.families.items())),
            "family_count": len(self.families),
            "attempted": sorted(self.attempted),
            "attempted_count": len(self.attempted),
            "succeeded": sorted(self.succeeded),
            "succeeded_count": len(self.succeeded),
            "coverage_gaps": coverage_gaps(self.catalog_paths, self.attempted),
            "refusals": self.refusals[:12],
            "refusal_count": len(self.refusals),
            "errors": self.errors[:12],
            "error_count": len(self.errors),
            "final": {
                "credits": ship.get("credits"),
                "hull": ship.get("hull"),
                "fuel": ship.get("fuel"),
                "orbiting": ship.get("orbiting_body_id"),
                "tick": (self.state.get("time") or {}).get("tick"),
            },
        }
