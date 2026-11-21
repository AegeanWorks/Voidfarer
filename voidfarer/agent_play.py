"""Headless AI captain: plays the game through the same HTTP API the cockpit uses."""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from typing import Any

from voidfarer.engine import CATALOG_CACHE_HEADER, STATIC_SNAPSHOT_KEYS


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
    "/api/messages/send": "the 180-step mail visit reads and resolves mail; the 2,000-step campaign sends after Act VI",
    "/api/ally/form": "needs high standing and a prepared captain",
    "/api/anomaly": "prompt-driven: an anomaly must be resolved",
    "/api/combat": "prompt-driven: a hostile intercept must occur",
    "/api/pirate/resolve": "prompt-driven: a pirate toll must intercept",
    "/api/customs/resolve": "prompt-driven: an active customs interdiction must intercept",
    "/api/fabricate": "the 180-step trip reaches the builder with a full hull and tank; the 2,000-step campaign fabricates when hurt",
    "/api/weather": "telemetry endpoint for solar space weather",
    "/api/overhaul": "the 180-step gate ends before Act VI; the 2,000-step campaign overhauls once",
    "/api/relics/fuse": "the 180-step gate collects fewer than three relics; the 2,000-step campaign fuses one set",
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
    "/api/reconstruct": "the 180-step gate predates the war declarations; the campaign rebuilds one world",
    "/api/void/dive": "needs the Act IV black-hole orbit, which only a 2,000-step campaign reaches",
    "/api/void/emerge": "needs an active void traversal after that dive",
    "/api/war/support": "faction wars are declared after the 180-step gate; the 2,000-step campaign supports one",
    "/api/inventory/jettison": "the captain sells or stores cargo instead of dumping it",
    "/api/ship/module": "alias: routes to the shipmods install/remove pair the captain already uses",
    "/api/shipyard/chassis": "the 180-step treasury cannot cover a hull; the 2,000-step campaign commissions one",
    "/api/shipyard/sell": "the 180-step gate ends before Act VI; the 2,000-step campaign trades in an equipped slot",
    "/api/outpost/upgrade": "needs a founded outpost",
    "/api/outpost/module": "needs a founded outpost and module credits",
    "/api/outpost/crew": "needs a founded outpost and available crew",
    "/api/outpost/specialize": "needs a level-3 outpost and credits",
    "/api/outpost/repair": "needs a damaged outpost and credits",
    "/api/drone/collect": "needs a deployed drone",
    "/api/depot/sell": "needs stock sitting in a depot",
    "/api/away/recall": "the 180-step gate finishes the first expedition; the 2,000-step campaign recalls a later team",
    "/api/trade/automation": "the broker is armed after Act VI; the 180-step gate ends before the campaign does",
    "/api/trade/quantum/automation": "auto-freight is armed after Act VI; the 180-step gate ends before the campaign does",
    "/api/research/queue": "needs a valid, incomplete research project",
    "/api/research/cancel": "needs a project already in the research queue",
    "/api/depot/withdraw": "needs stock sitting in a depot",
    "/api/fleet/dismiss": "the captain keeps its drone line; dismissal is permanent",
    "/api/fleet/escort/assign": "the patrol rotation runs after Act VI; the 180-step gate ends before the campaign does",
    "/api/fleet/escort/dismiss": "a live hull is never decommissioned; the campaign only scraps a destroyed escort",
    "/api/fleet/escort/repair": "needs a damaged escort",
    "/api/fleet/escort/train": "needs a docked escort, credits and spare experience",
    "/api/fleet/escort/role": "needs an owned escort outside combat",
    "/api/fleet/escort/captain": "needs an owned escort and an available crew member",
    "/api/fleet/refit": "the captain refits worn drones through the fleet action alias",
    "/api/fleet/escort/sell": "the 180-step gate owns one bought escort; the campaign sells a captured prize instead",
    "/api/contract/claim": "needs a completed contract",
    "/api/contract/swap": "needs a pending contract offer from a claim",

    "/api/crew/shore": "needs crew ashore at a colony",
    "/api/crew/station": "needs an active crew specialist",
    "/api/crew/dismiss": "the 180-step gate keeps its starting roster; the 2,000-step campaign trims duplicate recruits",
    "/api/story/choice": "needs an active story choice",
    "/api/trade/quantum/place": "the lane opens after Act VI; the 180-step gate ends before the campaign does",
    "/api/combat/gambit": "the 180-step gate ends before an escort captain is assigned; the campaign recalls its armed wing and spends the gambit in one fight",
    "/api/outpost/link": "the 180-step gate founds one outpost; the 2,000-step campaign builds a same-system pair",
    "/api/megastructure/restore": "the 180-step gate never orbits a restorable body; the 2,000-step campaign restores one",
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

    def get(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, Any]]:
        request = urllib.request.Request(self.base + path, method="GET", headers=headers or {})
        return self._open(request)

    def post(
        self,
        path: str,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        data = json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(
            self.base + path, data=data, method="POST",
            headers={"Content-Type": "application/json", **(headers or {})},
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
    # Experience and credit gates open much later than 80 steps: a 2,000-step campaign
    # reached Pilot Mastery 6 with 21,775 cr while its level-1 outpost refusal had
    # already been written off (ADR-361). After the fast attempts, the gate is released
    # on a slow horizon until the action is actually attempted.
    SLOW_RETRY_STEPS = 180
    SLOW_RETRY_LIMIT = 12
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
    NAVIGATION_FUEL_RESERVE = 5
    STORY_TRAVEL_RETRY_STEPS = 30
    # Act IV asks for the Cygnus horizon and the Voidfarer's Oath; surfacing after a
    # quarter of the crossing proves the lane without sailing past the chapter (ADR-366).
    VOID_EMERGE_PROGRESS = 0.25
    # The station terminal's survival consumables; one of each is bought per campaign so
    # the item shop is exercised, and the decoy is the guaranteed last-resort escape
    # when fuel cannot buy one (ADR-367, ADR-371).
    SUPPLY_ITEM_ID = "nanite_repair_paste"
    SUPPLY_FALLBACK_PRICE = 250
    SUPPLY_DECOY_ID = "decoy_countermeasure"
    SUPPLY_FALLBACK_DECOY_PRICE = 350
    SUPPLY_VOLUME = 1
    # Keep enough credits for repairs and fuel after a capital hull purchase (ADR-379).
    CHASSIS_CREDIT_RESERVE = 1000
    # The broker's buy ceiling sits above the quoted price so a quiet market move
    # cannot cancel the one armed window (ADR-380).
    AUTOMATION_BUY_MARGIN = 1.10
    # Auto-freight is stood down after its order lands or this many steps pass (ADR-381).
    QUANTUM_AUTOMATION_WINDOW = 10
    # The engine's alliance gate; hailing adds two trust per action (ADR-385).
    ALLY_TRUST = 50
    # Mirrors SimulationEngine.OUTPOST_CHARTER_MASTERY_LEVEL (ADR-390).
    OUTPOST_CHARTER_LEVEL = 2
    # Mirrors SimulationEngine.RECONSTRUCTION_CREDIT_COST (ADR-395).
    RECONSTRUCTION_COST = 600
    # Mirrors exploration.SCOOP_PROFILES keys; the drift test pins them (ADR-396).
    SCOOP_BODY_TYPES = frozenset({
        "star", "gas_giant", "ringed_giant", "ice_world", "ice_giant",
    })
    # Mirrors exploration.DERELICT_EXCLUDED_TYPES (ADR-396).
    DERELICT_EXCLUDED_TYPES = frozenset({
        "star", "orbital_station", "research_outpost", "black_hole",
        "wormhole", "quantum_relay", "solar_collector",
    })
    # Mirrors SimulationEngine.RELIEF_CARGO: landing medicines, hydroponics and a
    # fuel cell rebuilds 40 devastation for 5 standing instead of 20 for 2 (ADR-425).
    RELIEF_CARGO = (("medicines", 2), ("hydroponics", 2), ("fuel_cells", 1))
    # Six purchase actions are enough for three bags at any dock; after that the
    # captain falls back to the credit rebuild rather than hunting forever.
    RELIEF_STOCK_LIMIT = 6

    # The codex's quantum broker target: five automated freight orders (ADR-429).
    QUANTUM_ORDER_TARGET = 5
    # The codex's freight-baron milestone: ten quantum freight deliveries. One run
    # passes the broker target on the way, so it keeps shipping until both are banked;
    # the hard cap stops a lane whose deliveries lag its orders (ADR-434).
    FREIGHT_DELIVERY_TARGET = 10
    QUANTUM_ORDER_LIMIT = 16
    # Four freight slots exist; buying four units gives every order a full lot.
    QUANTUM_BUY_QUANTITY = 4
    # Six cooldown ticks per order plus transit waits; eight idle steps means the
    # current hold has no profitable lane and the run should stop.
    QUANTUM_IDLE_LIMIT = 8

    # A full-system survey pays 300 cr + 120 XP and unlocks two milestones, but the
    # tour only ever scans the body it happens to orbit; the post-story captain sweeps
    # one system, bounded so a hostile anomaly chain cannot eat the errands (ADR-427).
    SURVEY_SCAN_LIMIT = 24

    # The codex's technologist milestone: four completed research projects. The bench
    # is otherwise idle after the first project, so the post-story captain keeps it
    # busy until the milestone is banked (ADR-432).
    RESEARCH_TARGET = 4

    # The codex's field-team milestone: five completed expeditions. The tour launches
    # one team and protects it, so the post-story captain keeps deploying fresh teams
    # until the milestone is banked (ADR-433).
    AWAY_MISSION_TARGET = 5

    # The codex's squadron milestone: three commissioned escorts, and Captain Corps:
    # three assigned escort captains. The tour commissions one and staffs it, so the
    # post-story captain buys and staffs the rest (ADR-435).
    SQUADRON_TARGET = 3
    CAPTAIN_CORPS_TARGET = 3
    # Keep enough credits for repairs and fuel after a hull purchase.
    SQUADRON_CREDIT_RESERVE = 1000

    # A body hosts a derelict about 40% of the time, so three probes are enough to
    # find one while a derelict-free system cannot eat the post-story errands.
    SALVAGE_PROBE_LIMIT = 3
    # Economy is the mildest reactor doctrine, so the tour tries it first and only
    # falls back to the rest of the catalog when the core already runs it (ADR-398).
    REACTOR_MODE_ORDER = ("economy", "balanced", "silent", "overdrive")
    # Mirrors reactor.vent_reactor: a purge needs more than 5 heat and a 5-tick
    # coolant recharge, so a heat spike must be vented while it is still live (ADR-404).
    REACTOR_VENT_MIN_HEAT = 5.0
    REACTOR_VENT_COOLDOWN = 5
    # Mirrors engine.repair_reactor's floor: servicing costs at least 120 cr (ADR-404).
    REACTOR_SERVICE_COST = 120
    # A low-security cordon only rolls about one arrival in eight, so sixteen jumps
    # (eight arrivals) gives the ferry enough chances to prove the mechanic while the
    # fuel guard and the dock refuel keep it safe (ADR-400).
    SMUGGLE_JUMP_LIMIT = 16
    # Mirrors outposts.OUTPOST_TYPES costs; the drift test keeps them equal (ADR-390).
    OUTPOST_COSTS = {
        "mining": 1800, "research": 2200, "solar": 1400,
        "shipyard": 3200, "colony": 2600,
    }
    # Mirrors megastructures.MEGASTRUCTURE_RESTORATION; the drift test keeps them equal
    # (ADR-391).
    MEGASTRUCTURE_TYPES = frozenset({
        "dyson_sphere", "ring_world", "quantum_relay", "solar_collector", "wormhole",
    })

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
        # One-shot combat tricks are remembered per encounter so a spent action is not
        # chosen again while the snapshot is one call behind (ADR-362).
        self.combat_used: dict[str, set[str]] = {}
        # The Hollow Between is entered and surfaced once per campaign (ADR-366).
        self.void_attempted = False
        self.void_emerged = False
        # Two emergency fuel burns per campaign, chosen by state rather than tour
        # position so adding steps cannot starve the mechanic (ADR-355).
        self.emergency_burns = 0
        self.MAX_EMERGENCY_BURNS = 2
        self.fallback_trades = 0
        # One tick per armed broker window, so the automation cannot tick forever (ADR-380).
        self.automation_waited = False
        # The step auto-freight was armed on; its window is bounded by steps (ADR-381).
        self.quantum_armed_at = 0
        # The first expedition is left to finish; later ones prove the recall (ADR-384).
        self.away_protected_mission = ""
        # Bodies already orbited while looking for a second outpost site (ADR-390).
        self.outpost_probed: set[str] = set()
        # Bodies already orbited while looking for a restorable structure (ADR-391).
        self.megastructure_probed: set[str] = set()
        # Post-story prospecting remembers dry rocks and scoopable taps so neither
        # search orbits the same body twice (ADR-396).
        self.salvage_probed: set[str] = set()
        self.salvage_probes = 0
        self.scoop_probed: set[str] = set()
        # One gambit recall per campaign; a refused recall must not repeat each fight
        # (ADR-397).
        self.gambit_recalled = False
        # The post-campaign reactor doctrine change is attempted once (ADR-398).
        self.reactor_switched = False
        # One full-system survey per campaign, and the scan/orbit steps it spent (ADR-427).
        self.survey_done = False
        self.survey_scans = 0
        # Research bench state: the target is reached and the projects already tried,
        # so a refused start cannot repeat forever (ADR-432).
        self.research_done = False
        self.research_tried: set[str] = set()
        # Away rotation state: the target is reached and the (mission_type, body)
        # pairs already tried, so a refused launch cannot repeat (ADR-433).
        self.away_rotation_done = False
        self.away_launch_tried: set[tuple[str, str]] = set()
        # Squadron state: the target is reached, the (ship, crew) pairs tried and the
        # purchase attempts, so a refused action cannot repeat (ADR-435).
        self.squadron_done = False
        self.squadron_tried: set[tuple[str, str]] = set()
        self.squadron_buys = 0
        # One attempt per (pact action, faction) so a refused signature cannot loop (ADR-428).
        self.pact_tried: set[tuple[str, str]] = set()
        # One pirate may be fought per campaign when the hull is healthy (ADR-431).
        self.pirate_fought = False
        # Quantum freight run state: finished, idle steps, last seen order count (ADR-429).
        self.quantum_done = False
        self.quantum_idle = 0
        self.quantum_last_orders = 0
        # Relief stocking: how many purchase actions have tried to fill the bags (ADR-425).
        self.relief_stock_attempts = 0
        # One smuggling run per campaign: the contraband lot bought and the jumps
        # spent carrying it toward a cordon (ADR-400).
        self.smuggling_item = ""
        self.smuggling_jumps = 0
        # Fallback-jump rotation; one keeps the historic first slot (ADR-401).
        self.fallback_jumps = 1
        # Static catalogs are fetched once and re-injected into every slim action
        # response, so each step moves ~57 KB less JSON (ADR-420).
        self.catalogs: dict[str, Any] = {}

    def _adopt_state(self, snapshot: Any) -> None:
        """Adopt a response snapshot, restoring catalogs the server omitted (ADR-420)."""
        if not isinstance(snapshot, dict):
            return
        if self.catalogs:
            merged = dict(snapshot)
            for key, value in self.catalogs.items():
                merged.setdefault(key, value)
            snapshot = merged
        self.state = snapshot

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
        self._adopt_state(payload.get("state") or payload.get("data") or payload)
        # The first snapshot is full; keep the code-constant catalogs so later slim
        # action responses can be rehydrated without a second full fetch (ADR-420).
        self.catalogs = {
            key: self.state[key] for key in STATIC_SNAPSHOT_KEYS if key in self.state
        }

        for step in range(min(self.steps_requested, self.MAX_STEPS)):
            self.steps_taken = step + 1
            self.total_steps += 1
            # Phase must run on the campaign clock, not the call-local one, so a run split
            # into several play() calls follows the same path as one long call (ADR-347).
            path, body, family = self._choose(self.total_steps - 1)
            if path is None:
                break
            status, payload = self.client.post(
                path, body, headers={CATALOG_CACHE_HEADER: "1"}
            )
            if status == 409 and payload.get("state"):
                # A blocking prompt appeared mid-step; adopt it and retry this path later.
                self._adopt_state(payload["state"])
                self.refusals.append(f"{family}: blocked by prompt")
                continue
            signature = self._tour_signature(path, body or {})
            self.attempted.add(path)
            self.attempted_signatures.add(signature)
            if status != 200:
                self.errors.append(f"POST {path} -> {status}: {payload.get('message', '')}")
                if payload.get("state"):
                    self._adopt_state(payload["state"])
                continue
            if not payload.get("ok"):
                message = str(payload.get("message", "refused"))
                self.refusals.append(f"{family}: {message}")
                self._note_refusal(signature, message)
                if payload.get("state"):
                    self._adopt_state(payload["state"])
                continue
            self.families[family] = self.families.get(family, 0) + 1
            self.succeeded.add(path)
            self.retry_at.pop(signature, None)
            self.refusal_attempts.pop(signature, None)
            self.repeat_last[signature] = self.total_steps
            if payload.get("state"):
                self._adopt_state(payload["state"])
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
        if state.get("active_pirate"):
            return self._pirate_resolution()

        customs = state.get("active_customs")
        if customs:
            return "/api/customs/resolve", {"action": "jettison"}, "customs"
        if state.get("active_combat"):
            gambit = self._gambit_action()
            if gambit is not None:
                return gambit
            return self._combat_choice()
        if state.get("active_anomaly"):
            anomaly = self._anomaly_action()
            if anomaly is not None:
                return anomaly

        # The rotating tour reaches its recall builder only after a 6-10 tick expedition
        # has resolved, so abort an active team before any transit tick (ADR-384).
        recall = self._away_recall_action()
        if recall is not None:
            return recall

        if ship.get("travel"):
            return "/api/time/step", {"ticks": 1}, "time"

        # A void crossing freezes every flight action; ride it a little, then surface
        # back at the entry horizon before the chapter choice (ADR-366).
        void = state.get("void") or {}
        if ship.get("void_traversal") or void.get("traversal"):
            progress = float(void.get("traversal_progress") or 0.0)
            if not self.void_emerged and progress >= self.VOID_EMERGE_PROGRESS:
                self.void_emerged = True
                return "/api/void/emerge", {}, "void_emerge"
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

        # Act IV's void beat: dive at the required horizon and surface again, which
        # exercises the Hollow Between and restores the orbit the chapter needs.
        dive = self._void_dive_action()
        if dive is not None:
            return dive

        # Resolve a chapter standing in its own target system before any dock trip or body
        # travel can carry the ship away from the required place (ADR-360).
        hold = self._story_hold_action()
        if hold is not None:
            return hold

        # A war is a live-state opportunity; the rotating tour can miss its window when
        # station errands shift the clock, so support it as soon as it appears (ADR-371).
        war = self._tour_war()
        if war is not None and not self._tour_action_attempted(war[0], war[1]):
            return war

        # The station terminal's consumable is bought once and used when hurt, so the
        # item terminal and its use are exercised (ADR-367).
        supply = self._supply_action()
        if supply is not None:
            return supply
        # Once the guided tour is spent, a late dock still refills the second survival
        # item; this is state-driven so the tour cannot lock the decoy out forever (ADR-371).
        if self.tour_exhausted:
            refill = self._tour_supply_decoy()
            if refill is not None and not self._tour_action_attempted(refill[0], refill[1]):
                return refill

        # A devastated inhabited world is the war-recovery surface; rebuild the worst
        # one in the current system before the construction errands (ADR-395).
        reconstruct = self._reconstruct_action()
        if reconstruct is not None:
            return reconstruct

        # A half-empty tank is a real errand: orbit a scoopable body instead of
        # waiting for a station that may be a jump away (ADR-396).
        scoop = self._scoop_action()
        if scoop is not None:
            return scoop

        # The wars left derelicts across the galaxy; probe a plausible body so the
        # salvage mechanic succeeds instead of refusing at a station (ADR-396).
        salvage = self._salvage_action()
        if salvage is not None:
            return salvage

        # A same-system outpost pair is the only way to exercise the supply link; the
        # post-campaign captain builds both and routes the newer through the older.
        outpost = self._outpost_link_action()
        if outpost is not None:
            return outpost

        # Ancient structures are the other same-system construction surface; one restore
        # per campaign after the outpost pair (ADR-391).
        structure = self._megastructure_action()
        if structure is not None:
            return structure

        # Relic fusion is the post-campaign progress capstone: one set for one higher
        # rarity, once, before the station errand (ADR-392).
        fusion = self._relic_fuse_action()
        if fusion is not None:
            return fusion

        # A worn frame is pure downside, so scrub it once at the first post-story dock
        # rather than waiting for the rotating tour (ADR-393).
        overhaul = self._overhaul_action()
        if overhaul is not None:
            return overhaul

        # Titanium in the hold becomes a field repair once the campaign is over and the
        # hull or tank is actually hurt (ADR-394).
        fabricate = self._fabricate_action()
        if fabricate is not None:
            return fabricate

        # The reactor doctrine is a whole-ship trade-off, so it changes once after the
        # campaign instead of rerouting the short gate (ADR-398).
        reactor = self._reactor_mode_action()
        if reactor is not None:
            return reactor

        # A transient heat spike must be vented while it is live, then the purge's
        # integrity cost is serviced at the next dock (ADR-404).
        vent = self._reactor_vent_action()
        if vent is not None:
            return vent
        service = self._reactor_repair_action()
        if service is not None:
            return service

        # A post-story smuggling run buys one contraband lot and carries it at the
        # quoted cordon until the scan fires, then dumps it under pressure (ADR-400).
        # It runs after the construction errands so those opportunities are not lost
        # to the ferry's jumps and tick shifts.
        smuggle = self._smuggle_action()
        if smuggle is not None:
            return smuggle

        # A friendly faction at standing 40 or 60 will sign a trade or research pact.
        pact = self._pact_action()
        if pact is not None:
            return pact

        # Automated quantum freight needs a dock, a lot and cooldown ticks (ADR-429).
        freight = self._quantum_freight_action()
        if freight is not None:
            return freight

        # A full-system survey pays a completion bonus the rotating tour can never
        # collect; it runs last so no established errand is displaced (ADR-427).
        survey = self._survey_action()
        if survey is not None:
            return survey

        # Station services live at a dock; reach one before touring menu mechanics.
        if not self._is_docked():
            dock = self._dockable_body()
            if dock and dock.get("id") != ship.get("orbiting_body_id"):
                return "/api/travel", {"body_id": dock["id"], "mode": "sublight"}, "dock"

        # A capital hull is the shipyard's headline purchase; take it once the treasury
        # can cover the hull, a repair reserve and the current hold (ADR-379).
        chassis = self._chassis_action()
        if chassis is not None:
            return chassis

        # A squadron of three staffed escorts is the fleet's lifetime milestone pair;
        # the tour commissions one, so the rest are bought and staffed here (ADR-435).
        squadron = self._squadron_action()
        if squadron is not None:
            return squadron

        # The docked broker is armed on a live quote after the campaign, proves one
        # automated trade, and is stood down before its loop can fill the hold (ADR-380).
        automation = self._automation_action()
        if automation is not None:
            return automation

        # Quantum freight follows the same post-campaign pattern on the engine's own
        # route report: one order, one armed auto-freight window (ADR-381).
        quantum = self._quantum_manual_action()
        if quantum is not None:
            return quantum

        # Escorts rotate through connected patrol lanes after the campaign so a
        # detached wing is recalled and the fleet ends local (ADR-382).
        patrol = self._patrol_action()
        if patrol is not None:
            return patrol

        # A captain starts at 10-40 trust; the post-campaign hail chain reaches the
        # engine's 50-trust alliance gate and then forms the alliance (ADR-385).
        ally = self._ally_action()
        if ally is not None:
            return ally

        send = self._send_action()
        if send is not None:
            return send

        sell = self._shipyard_sell_action()
        if sell is not None:
            return sell

        # A captured prize is scrap value at a drydock, and selling one proves the
        # fleet sale without disarming the bought escort (ADR-399).
        prize_sale = self._prize_sale_action()
        if prize_sale is not None:
            return prize_sale

        # A wrecked bought escort cannot be repaired or refunded; decommission it so
        # its officer is not held in a dead hull (ADR-402).
        wreck = self._wreck_dismiss_action()
        if wreck is not None:
            return wreck

        dismissal = self._crew_dismiss_action()
        if dismissal is not None:
            return dismissal

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

        # Once landed, work the first available surface operation straight away. Leaving it
        # to the rotating tour let the endpoint be starved out of the 180-step gate when
        # other steps were added (ADR-354).
        if ship.get("landed_body_id"):
            report = state.get("surface_report") or {}
            if report.get("landed"):
                for operation in report.get("operations") or []:
                    if (isinstance(operation, dict) and operation.get("id")
                            and operation.get("available", True)
                            and not operation.get("used")):
                        return ("/api/surface/op",
                                {"operation_id": operation["id"]}, "surface")

        # Burn a spare fuel cell when the tank runs low; this is state-driven so the
        # rotating tour cannot starve it when other steps are added (ADR-355).
        if (self.emergency_burns < self.MAX_EMERGENCY_BURNS
                and int(ship.get("fuel") or 0) < max(1, int(ship.get("max_fuel") or 0) // 3)
                and int((ship.get("cargo") or {}).get("fuel_cells") or 0) > 0):
            self.emergency_burns += 1
            return ("/api/engineering/action",
                    {"action": "burn_cells", "quantity": 1}, "burn_cells")

        # A jump burns the real hop cost, not one unit; using the published estimates
        # stopped 47 attempts that could only be refused (ADR-348).
        jump = self._fallback_jump(step)
        if jump is not None:
            return jump

        # Touristing between bodies is the last resort, not the default: otherwise the
        # captain spends the whole run in transit and never exercises a station mechanic.
        if step % 12 == 6:
            target_body = self._pick_body(prefer_unvisited=True)
            current_id = ship.get("orbiting_body_id")
            if target_body and target_body["id"] != current_id:
                self.travelled += 1
                self.visited_bodies.add(str(target_body["id"]))
                return "/api/travel", {"body_id": target_body["id"], "mode": "sublight"}, "travel"

        # The bench is idle after the first project, so a free step starts the next
        # available one; it needs no dock or travel (ADR-432).
        research = self._research_action()
        if research is not None:
            return research

        # A fresh body orbit is where an expedition can be deployed; a free step
        # launches the next available mission and waits for it to resolve (ADR-433).
        away = self._away_rotation_action()
        if away is not None:
            return away

        return "/api/time/step", {"ticks": 1}, "time"

    def _fallback_jump(self, step: int):
        """Rotate the post-story fallback jump across the affordable lanes (ADR-401).

        ``step % len(affordable)`` froze on one slot because the cadence advances the
        step by 20 and every jump therefore landed on the same remainder, so the captain
        ping-ponged between two systems and never reached the restorable worlds beyond
        them. The pre-story path keeps that frozen slot because the 180-step gate was
        measured on it; the rotation counter starts at one so the first post-story jump
        also keeps its historic slot.
        """
        if step % 20 != 5:
            return None
        state = self.state
        ship = state.get("ship") or {}
        connections = (state.get("current_system") or {}).get("connections") or []
        costs = state.get("jump_fuel_costs") or {}
        fuel = int(ship.get("fuel") or 0)
        # Without a published estimate the old floor still applies: some fuel.
        affordable = [
            system_id for system_id in connections
            if ((fuel >= int(costs[system_id])) if system_id in costs else fuel > 0)
        ]
        if not affordable:
            return None
        # Before the campaign ends, the frozen step remainder is the benchmark route
        # the 180-step gate was measured on (58 families); rotation starts with the
        # post-story exploration where the ping-pong actually starves mechanics.
        if (state.get("story_status") or {}).get("completed"):
            target = affordable[self.fallback_jumps % len(affordable)]
            self.fallback_jumps += 1
        else:
            target = affordable[step % len(affordable)]
        return "/api/jump", {"target": target}, "jump"

    def _anomaly_action(self):
        """Take an anomaly choice whose power check passes, not always the first one.

        The card marks each check READY or FAILS with the effective percentage; the first
        choice is often the deepest check and cost 15 hull per failure in campaign probes
        (ADR-372). Without that payload, fall back to the lowest threshold, where a
        'none' check is always safe.
        """
        anomaly = self.state.get("active_anomaly") or {}
        choices = [choice for choice in anomaly.get("choices") or [] if isinstance(choice, dict)]
        if not choices:
            return None
        actions = ((self.state.get("encounter") or {}).get("encounter") or {}).get("actions") or []
        ready = {
            str(action.get("id"))
            for action in actions
            if isinstance(action, dict) and action.get("ready")
        }
        chosen = next(
            (
                choice for choice in choices
                if str(choice.get("choice_id") or choice.get("id") or "") in ready
            ),
            None,
        )
        if chosen is None:
            chosen = min(choices, key=self._anomaly_threshold)
        choice_id = str(chosen.get("choice_id") or chosen.get("id") or "")
        if not choice_id:
            return None
        return "/api/anomaly", {"choice_id": choice_id}, "anomaly"

    @staticmethod
    def _anomaly_threshold(choice: dict[str, Any]) -> int:
        if str(choice.get("required_power") or "none") == "none":
            return 0
        try:
            return int(choice.get("min_power_threshold") or 0)
        except (TypeError, ValueError):
            return 0

    def _combat_choice(self):
        """Pick a combat action from the live state: survival first, then the tactical surface.

        Firing lasers every turn kept only one of the thirteen combat actions reachable and
        lost the ship repeatedly; each one-shot action is remembered per encounter so a
        refused or spent trick is not retried in a loop (ADR-362).
        """
        combat = self.state.get("active_combat") or {}
        ship = self.state.get("ship") or {}
        hull = int(ship.get("hull") or 0)
        max_hull = max(1, int(ship.get("max_hull") or 1))
        shield = int(ship.get("shield") or 0)
        max_shield = max(1, int(ship.get("max_shield") or 1))
        fuel = int(ship.get("fuel") or 0)
        reactor = self.state.get("reactor") or ship.get("reactor") or {}
        heat_pct = float(reactor.get("heat_pct") or 0.0)
        enemy_hull = int(combat.get("enemy_hull") or 0)
        enemy_max_hull = max(1, int(combat.get("enemy_max_hull") or 1))
        enemy_shield = int(combat.get("enemy_shield") or 0)
        enemy_damage = int(combat.get("enemy_damage") or 0)
        intent = str(combat.get("enemy_intent") or "")
        used = self.combat_used.setdefault(str(combat.get("id") or "combat"), set())

        def pick(action: str):
            used.add(action)
            return "/api/combat", {"action": action}, "combat"

        if hull * 4 <= max_hull and fuel >= 8:
            return pick("flee")
        if hull * 5 <= max_hull * 2 and fuel >= 3 and "evasive_burn" not in used:
            return pick("evasive_burn")
        if hull * 2 <= max_hull and "decoy" not in used:
            # Once the burn is spent (or fuel cannot buy one at all), the station decoy is
            # the only guaranteed way out of a losing fight (ADR-371, ADR-373).
            if int((ship.get("cargo") or {}).get(self.SUPPLY_DECOY_ID) or 0) > 0:
                used.add("decoy")
                return "/api/inventory/use", {"item_id": self.SUPPLY_DECOY_ID}, "combat_item"
        if heat_pct >= 85.0 and "vent_heat" not in used:
            return pick("vent_heat")
        if enemy_shield <= 0 and enemy_hull * 10 <= enemy_max_hull * 3 and "board_enemy" not in used:
            marines = [
                member for member in self.state.get("crew") or []
                if isinstance(member, dict) and str(member.get("role")) == "marine"
                and str(member.get("status")) == "active"
                and int(member.get("injury_ticks") or 0) == 0
            ]
            if marines:
                return pick("board_enemy")
        if (shield * 3 <= max_shield and hull * 4 <= max_hull * 3
                and enemy_damage >= 5 and "shield_absorb" not in used):
            # Absorbing every turn can outlast the enemy indefinitely (it damages neither
            # hull), so it is one defensive trick per fight, not a strategy (ADR-362).
            return pick("shield_absorb")
        drones = ship.get("fleet_drones") or []
        if (any(isinstance(drone, dict) and drone.get("drone_type") in ("combat_escort", "scout")
                for drone in drones) and "drone_strike" not in used):
            return pick("drone_strike")
        if intent == "evade" and not combat.get("enemy_engines_disabled") and "target_engines" not in used:
            return pick("target_engines")
        if enemy_damage >= 20 and "target_weapons" not in used:
            return pick("target_weapons")
        if enemy_shield > 0 and "target_shields" not in used:
            return pick("target_shields")
        if heat_pct >= 60.0 and "point_defense" not in used:
            return pick("point_defense")
        weapons = int((ship.get("power") or {}).get("weapons") or 0)
        if hull * 5 <= max_hull * 3 and weapons >= 15 and "target_bridge" not in used:
            return pick("target_bridge")
        return "/api/combat", {"action": "fire_lasers"}, "combat"

    def _smuggle_action(self):
        """Buy one contraband lot and run it at the quoted high-security cordon (ADR-400).

        The customs scan only rolls on arrival in a high-security system, so the run
        buys at a dock, jumps at the cordon the snapshot quotes, and when that system's
        own neighbours have no cordon it hops out once so the quoted system becomes
        adjacent again. The encounter itself is resolved by the blocking-prompt flow.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if "/api/customs/resolve" in self.succeeded:
            return None
        if self.smuggling_jumps >= self.SMUGGLE_JUMP_LIMIT:
            return None
        ship = self.state.get("ship") or {}
        cargo = ship.get("cargo") or {}
        if not self.smuggling_item:
            if not self._is_docked():
                return None
            quotes = [
                quote for quote in self.state.get("market_quotes") or []
                if isinstance(quote, dict)
                and str(quote.get("category") or "") == "contraband"
            ]
            if not quotes:
                return None
            row = min(quotes, key=lambda quote: int(quote.get("buy_price") or 0))
            item = str(row.get("commodity_id") or "")
            if not item or int(row.get("max_buy") or 0) < 1:
                return None
            if int(ship.get("credits") or 0) < int(row.get("buy_price") or 0):
                return None
            self.smuggling_item = item
            return "/api/trade", {"commodity_id": item, "quantity": 1, "is_buy": True}, "trade"
        if int(cargo.get(self.smuggling_item) or 0) <= 0:
            return None
        system = self.state.get("current_system") or {}
        connections = [str(item) for item in system.get("connections") or [] if item]
        if not connections:
            return None
        risk = self.state.get("customs_risk") or {}
        target = str(risk.get("system_id") or "")
        if target not in connections:
            # Standing inside the cordon: the quoted system is not adjacent to itself,
            # so hop out once and let the next step quote it as the neighbour again.
            target = connections[0]
        costs = self.state.get("jump_fuel_costs") or {}
        cost = int(costs.get(target) or 0)
        fuel = int(ship.get("fuel") or 0)
        if cost and fuel < cost + self.NAVIGATION_FUEL_RESERVE:
            if self._is_docked() and int(ship.get("credits") or 0) >= 100:
                return "/api/refuel", {"amount": 10}, "refuel"
            return None
        self.smuggling_jumps += 1
        return "/api/jump", {"target": target}, "jump"

    def _pirate_resolution(self):
        """Fight one post-story pirate when clearly stronger, else evade (ADR-431).

        The captain has always evaded, so the engine's fight branch (toll refused,
        combat starts, bounty on victory) had no AI proof. Half hull is the safety
        floor, and one fight per campaign bounds the detour.
        """
        if not (self.state.get("active_pirate") or {}):
            return None
        ship = self.state.get("ship") or {}
        hull = int(ship.get("hull") or 0)
        max_hull = max(1, int(ship.get("max_hull") or 0))
        if (
            (self.state.get("story_status") or {}).get("completed")
            and not self.pirate_fought
            and hull * 2 >= max_hull
        ):
            self.pirate_fought = True
            return "/api/pirate/resolve", {"action": "fight"}, "pirate"
        return "/api/pirate/resolve", {"action": "evade"}, "pirate"

    def _gambit_action(self):
        """Recall an armed escort and spend its captain's once-per-battle gambit (ADR-397).

        The gambit's effect depends on the escort captain's role, so the policy only
        posts the command when that role's engine gate is already open. Assignment
        between systems does not spend a combat turn, so the recall is safe mid-fight.
        """
        if "/api/combat/gambit" in self.attempted:
            return None
        combat = self.state.get("active_combat") or {}
        if combat.get("captain_gambit_used"):
            return None
        system_id = str((self.state.get("current_system") or {}).get("id") or "")
        if not system_id:
            return None
        crew = {
            str(member.get("id")): member
            for member in self.state.get("crew") or []
            if isinstance(member, dict)
        }
        armed = [
            ship for ship in self._escort_rows()
            if int(ship.get("hull") or 0) > 0 and str(ship.get("captain_id") or "")
        ]
        if not armed:
            return None
        local = [
            ship for ship in armed
            if str(ship.get("assigned_system_id") or "") == system_id
        ]
        if not local:
            if self.gambit_recalled:
                return None
            self.gambit_recalled = True
            body = {"ship_id": str(armed[0]["id"]), "system_id": system_id}
            return "/api/fleet/escort/assign", body, "escort_assign"
        ship = self.state.get("ship") or {}
        hull = int(ship.get("hull") or 0)
        max_hull = max(1, int(ship.get("max_hull") or 1))
        role = str((crew.get(str(local[0]["captain_id"])) or {}).get("role") or "")
        ready = {
            "engineer": hull < max_hull,
            "medic": any(int(escort.get("hull") or 0) < int(escort.get("max_hull") or 0)
                         for escort in local),
            "quartermaster": any(
                int(escort.get("shield") or 0) < int(escort.get("max_shield") or 0)
                for escort in local),
            "pilot": float(combat.get("captain_evasion_bonus") or 0.0) < 0.35,
            "scientist": int(combat.get("enemy_shield") or 0) > 0,
            "marine": int(combat.get("enemy_damage") or 0) > 1,
        }
        if not ready.get(role):
            return None
        return "/api/combat/gambit", {}, "combat_gambit"

    def _note_refusal(self, signature: tuple[str, str], message: str) -> None:
        """Schedule a fast retry, then a slow one, then drop a gate that never opens."""
        attempts = self.refusal_attempts.get(signature, 0) + 1
        self.refusal_attempts[signature] = attempts
        if not self._refusal_may_pass(message):
            self.retry_at.pop(signature, None)
        elif attempts < self.REFUSAL_RETRY_LIMIT:
            self.retry_at[signature] = self.total_steps + self.REFUSAL_RETRY_STEPS
        elif attempts < self.SLOW_RETRY_LIMIT:
            self.retry_at[signature] = self.total_steps + self.SLOW_RETRY_STEPS
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
            # Only market commodities trade here; station consumables share the cargo
            # hold but have no quote, and selling one retried forever (ADR-371).
            item = next((k for k, v in cargo.items() if int(v) > 0 and k in quotes), None)
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
            # The station terminal's consumables are bought at the opening dock before the
            # fallback jump can leave Sol; the decoy has its own builder so the paste
            # cannot starve it after its second wrap (ADR-367, ADR-371).
            self._tour_supply,
            self._tour_supply_decoy,
            # A market trade must happen before the fallback's even-step parity can drift;
            # the route is cheap and does not depend on a specific system (ADR-371).
            self._tour_trade,
            # The opening chapter is gated on being in Sol, and the fallback jump leaves at
            # step 5 of every run, so the story step must be the first tour action (ADR-354).
            self._tour_story_choice,
            self._tour_story_orbit,
            self._tour_story_travel,
            self._tour_power,
            self._tour_reactor,
            self._tour_route,
            self._tour_messages,
            self._tour_contracts,
            self._tour_research_queue,
            self._tour_research_cancel,
            self._tour_message_send,
            self._tour_shore_leave,
            self._tour_contract_claim,
            self._tour_swap,
            self._tour_refuel,
            self._tour_overhaul,
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
            self._tour_depot_withdraw,
            self._tour_depot_sell,
            self._tour_preview,
            self._tour_stance,
            self._tour_weapon_set,
            self._tour_events,
            self._tour_crew_train,
            self._tour_crew_station,
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
            self._tour_fabricate,
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
        # Six chapters share one choice route; keying on the path let Act I lock the
        # whole campaign after its first resolution (ADR-360).
        "/api/story/choice": "choice_id",
        # Both survival items share the buy and use routes; keying on the path let the
        # repair paste lock the decoy out of the shop (ADR-371).
        "/api/inventory/buy": "item_id",
        "/api/inventory/use": "item_id",
        # A pilot and a marine share the recruit route; keying on the path kept the
        # marine out and boarded nothing (ADR-375).
        "/api/crew/recruit": "role_id",
        # Many bodies share one orbit route; keying on the path let the first generic
        # orbit lock the chapter's required body (ADR-360).
        "/api/orbit": "target",
        # One route installs twelve different mods; keying on the path meant a single
        # early refusal (or a removal) locked every later install (ADR-352).
        "/api/shipmods/install": "mod_id",
        "/api/shipmods/remove": "slot",
        # Each outpost level is a different upgrade; keying on the path stopped the
        # climb at level 2 and made level-3 specialization unreachable (ADR-377).
        "/api/outpost/upgrade": "level",
        # A tree branch spawns a follow-up node with its own choices; keying on the
        # path would let the root lock every follow-up out of the tour (ADR-378).
        "/api/messages/choose": "message_id",
        # Arming and standing the broker down are two distinct actions; keying on the
        # path would leave the disable direction unreachable after the arm (ADR-380).
        "/api/trade/automation": "enabled",
        # One quantum order per commodity and the same arm/disable split as the broker
        # keep both freight directions reachable (ADR-381).
        "/api/trade/quantum/place": "commodity_id",
        "/api/trade/quantum/automation": "enabled",
        # Patrol and recall target different systems, so the system id is the action
        # identity and the recall stays reachable after the patrol (ADR-382).
        "/api/fleet/escort/assign": "system_id",
        # Every expedition is recalled by its own id, so one abort cannot lock the
        # second mission out of the policy (ADR-384).
        "/api/away/recall": "mission_id",
        # Each expedition type may launch once, so a late type can prove the recall
        # after the first team has already completed its survey (ADR-384).
        "/api/away/launch": "mission_type",
        # Trust and alliance are per captain, so every captain stays reachable for
        # the post-campaign hail chain (ADR-385).
        "/api/ally/form": "captain_id",
        # Each equipped slot is a separate trade-in, so one sale cannot lock the others
        # out of the post-campaign policy (ADR-387).
        "/api/shipyard/sell": "slot",
        # The roster trim dismisses one redundant member at a time (ADR-388).
        "/api/crew/dismiss": "crew_id",
        # One restoration per body, so a second structure stays reachable (ADR-391).
        "/api/megastructure/restore": "body_id",
        # A rebuilt world is keyed by its body id (ADR-395).
        "/api/reconstruct": "body_id",
        # Every completed milestone is a separate claim; keying on the path let the
        # first claim lock all remaining rewards out for the whole campaign (ADR-426).
        "/api/codex/claim": "entry_id",
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
        story_target = str((self.state.get("story_status") or {}).get("target_system_id") or "")
        if path == "/api/navigate" and story_target and story_target == str((body or {}).get("system_id") or ""):
            # A story course can be interrupted; retry the target after the same cooldown
            # without making the generic one-shot navigate step repeat (ADR-360).
            last = self.repeat_last.get(signature)
            return last is not None and self.total_steps - last < self.STORY_TRAVEL_RETRY_STEPS
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

    def _reactor_mode_action(self):
        """Switch the post-campaign core to economy so the doctrine change is proven (ADR-398).

        The rotating tour reposts the current mode (a guaranteed refusal), and switching
        doctrine inside the 180-step gate reroutes the whole trip, so the change waits
        until the story is over and is attempted once.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if "/api/reactor/mode" in self.succeeded:
            return None
        if self.reactor_switched:
            return None
        reactor = self.state.get("reactor") or {}
        modes = reactor.get("modes")
        if not modes:
            return None
        if isinstance(modes, dict):
            ids = [str(mode_id) for mode_id in modes]
        else:
            ids = [
                str(mode) if isinstance(mode, str) else str((mode or {}).get("id") or "")
                for mode in modes
            ]
        current = str(reactor.get("mode") or "balanced")
        for mode_id in self.REACTOR_MODE_ORDER:
            if mode_id in ids and mode_id != current:
                self.reactor_switched = True
                return "/api/reactor/mode", {"mode": mode_id}, "reactor"
        return None

    def _reactor_vent_action(self):
        """Vent a live heat spike after the campaign while it is still hot (ADR-404).

        The rotating tour visits the purge slot on its own cadence, so a spike that
        lasts a few ticks is usually gone by then; a state-driven purge fires while
        the heat is actually present and proves the emergency coolant.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        reactor = self.state.get("reactor") or {}
        if float(reactor.get("heat") or 0.0) <= self.REACTOR_VENT_MIN_HEAT:
            return None
        last_vent = int(reactor.get("last_vent_tick", -1))
        if last_vent >= 0:
            tick = int((self.state.get("time") or {}).get("tick") or 0)
            if tick - last_vent < self.REACTOR_VENT_COOLDOWN:
                return None
        return "/api/reactor/vent", {}, "reactor_vent"

    def _reactor_repair_action(self):
        """Service the core at a post-story dock once it is hurt or overheated (ADR-404).

        A purge always costs a point of integrity, so the repair that follows it is
        real maintenance rather than a no-op post.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if not self._is_docked():
            return None
        reactor = self.state.get("reactor") or {}
        missing = max(
            0.0,
            float(reactor.get("max_integrity") or 0.0)
            - float(reactor.get("integrity") or 0.0),
        )
        if missing <= 0.5 and float(reactor.get("heat") or 0.0) <= self.REACTOR_VENT_MIN_HEAT:
            return None
        if int((self.state.get("ship") or {}).get("credits") or 0) < self.REACTOR_SERVICE_COST:
            return None
        return "/api/reactor/repair", {}, "reactor_repair"

    def _tour_route(self):
        connections = (self.state.get("current_system") or {}).get("connections") or []
        if not connections:
            return None
        return "/api/route", {"system_id": connections[0]}, "route"

    def _tour_messages(self):
        """Resolve one live branch, then fall back to plain mail (ADR-378)."""
        messages = [m for m in self.state.get("messages") or []
                    if isinstance(m, dict) and m.get("id")]
        for message in messages:
            if message.get("resolved_choice"):
                continue
            for choice in message.get("choices") or []:
                if isinstance(choice, dict) and choice.get("id"):
                    return ("/api/messages/choose",
                            {"message_id": message["id"], "choice_id": choice["id"]},
                            "messages_choose")
        for message in messages:
            if not message.get("read"):
                return "/api/messages/read", {"message_id": message["id"]}, "messages"
        return None

    def _unread_message_action(self):
        """Read plain inbox mail so a live branch cannot hide the read route."""
        for message in self.state.get("messages") or []:
            if not isinstance(message, dict) or not message.get("id"):
                continue
            if message.get("read") or message.get("resolved_choice"):
                continue
            if any(isinstance(choice, dict) and choice.get("id")
                   for choice in message.get("choices") or []):
                continue
            return "/api/messages/read", {"message_id": message["id"]}, "messages"
        return None

    def _tour_contracts(self):
        return "/api/contracts/refresh", {}, "contracts"

    def _tour_story_choice(self):
        """Resolve the active chapter's first unlocked choice; the tour never touched the arc."""
        status = self.state.get("story_status") or {}
        if status.get("completed") or not status.get("ready"):
            return None
        for choice in status.get("choices") or []:
            if isinstance(choice, dict) and choice.get("id") and not choice.get("locked"):
                return "/api/story/choice", {"choice_id": choice["id"]}, "story"
        return None

    def _void_dive_action(self):
        """Take the story's own void beat once: dive at the required horizon.

        Shadowing every black-hole orbit would wander the galaxy for no story reason, so
        this triggers only when the active chapter requires orbit around the body the ship
        is already orbiting, with shields, hull and fuel to survive the crossing (ADR-366).
        """
        if self.void_attempted:
            return None
        story = self.state.get("story_status") or {}
        if story.get("completed"):
            return None
        target = str(story.get("target_system_id") or "")
        current = str((self.state.get("current_system") or {}).get("id") or "")
        if not target or current != target:
            return None
        chapter = (self.state.get("story_chapters_map") or {}).get(
            str(story.get("chapter_id") or "")
        ) or {}
        required = str((chapter.get("requirements") or {}).get("orbit_body_id") or "")
        ship = self.state.get("ship") or {}
        if not required or required != str(ship.get("orbiting_body_id") or ""):
            return None
        void = self.state.get("void") or {}
        if not void.get("dive_ready"):
            return None
        hull = int(ship.get("hull") or 0)
        max_hull = max(1, int(ship.get("max_hull") or 1))
        shield = int(ship.get("shield") or 0)
        max_shield = max(1, int(ship.get("max_shield") or 1))
        if hull * 2 < max_hull or shield * 10 < max_shield * 3:
            return None
        fuel = int(ship.get("fuel") or 0)
        affordable = [
            destination
            for destination in void.get("destinations") or []
            if isinstance(destination, dict)
            and int(destination.get("fuel_estimate") or 0) + self.NAVIGATION_FUEL_RESERVE <= fuel
        ]
        if not affordable:
            return None
        target_system = str(min(
            affordable, key=lambda destination: int(destination.get("fuel_estimate") or 0)
        ).get("system_id") or "")
        if not target_system:
            return None
        self.void_attempted = True
        return "/api/void/dive", {"target_system_id": target_system}, "void"

    def _supply_action(self):
        """Use a held repair paste when the hull is hurt outside a blocking encounter (ADR-367).

        Buying is a tour builder so it does not steal an early tour slot from the 180-step
        gate; using is state-driven because damage appears wherever combat leaves it.
        """
        ship = self.state.get("ship") or {}
        cargo = ship.get("cargo") or {}
        held = int(cargo.get(self.SUPPLY_ITEM_ID) or 0)
        hull = int(ship.get("hull") or 0)
        max_hull = max(1, int(ship.get("max_hull") or 1))
        if held <= 0 or hull >= max_hull:
            return None
        if (self.state.get("active_combat") or self.state.get("active_anomaly")
                or self.state.get("active_pirate") or self.state.get("active_customs")
                or self.state.get("pending_decision")):
            return None
        body = {"item_id": self.SUPPLY_ITEM_ID}
        if self._tour_action_attempted("/api/inventory/use", body):
            return None
        return "/api/inventory/use", body, "supply_use"

    def _chassis_action(self):
        """Commission the cheapest fitting hull once, after Act VI at a service dock (ADR-379)."""
        if "/api/shipyard/chassis" in self.attempted or not self._is_docked():
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        ship = self.state.get("ship") or {}
        credits = int(ship.get("credits") or 0)
        used = int(ship.get("cargo_used_volume") or 0)
        current_class = str(ship.get("ship_class") or "")
        candidates: list[tuple[int, str]] = []
        for chassis in self.state.get("available_chassis") or []:
            if not isinstance(chassis, dict) or not chassis.get("id"):
                continue
            cost = int(chassis.get("cost") or 0)
            capacity = int(chassis.get("cargo_capacity") or 0)
            if cost <= 0 or capacity < used:
                continue
            if credits < cost + self.CHASSIS_CREDIT_RESERVE:
                continue
            if current_class and str(chassis.get("ship_class") or "") == current_class:
                continue
            candidates.append((cost, str(chassis["id"])))
        if not candidates:
            return None
        chassis_id = min(candidates)[1]
        return "/api/shipyard/chassis", {"chassis_id": chassis_id}, "chassis"

    def _automation_action(self):
        """Arm the docked broker on the cheapest quote, then stand it down (ADR-380).

        One armed window proves the automation: the captain lets a single engine tick
        pass so the broker executes at the dock, then disables it so the three-tick
        rearm loop cannot crowd the hold.
        """
        auto = self.state.get("trade_automation") or {}
        if auto.get("enabled"):
            if int(auto.get("trades") or 0) > 0 or self.automation_waited:
                body = {"enabled": False}
                if self._tour_action_attempted("/api/trade/automation", body):
                    return None
                return "/api/trade/automation", body, "automation"
            ship = self.state.get("ship") or {}
            free = ship.get("cargo_free_volume")
            free = int(ship.get("cargo_capacity") or 0) if free is None else int(free)
            if self._is_docked() and free >= 1:
                self.automation_waited = True
                return "/api/time/step", {"ticks": 1}, "time"
            return None
        if not self._is_docked():
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        quotes = self.state.get("market_quotes") or {}
        commodity_id = self._cheapest_quote(quotes)
        if not commodity_id:
            return None
        buy_price = self._quote_price(quotes, commodity_id, "buy_price")
        if buy_price <= 0:
            return None
        ship = self.state.get("ship") or {}
        if int(ship.get("credits") or 0) < buy_price:
            return None
        body = {
            "commodity_id": commodity_id,
            "buy_below": int(math.ceil(buy_price * self.AUTOMATION_BUY_MARGIN)),
            "sell_above": 0,
            "quantity": 1,
            "enabled": True,
        }
        if self._tour_action_attempted("/api/trade/automation", body):
            return None
        return "/api/trade/automation", body, "automation"

    @staticmethod
    def _quote_price(quotes: Any, commodity_id: str, field: str) -> float:
        """Read one price from the quote list or its id-keyed form."""
        items = quotes if isinstance(quotes, list) else list((quotes or {}).values())
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("commodity_id") or item.get("id") or "")
            if item_id == commodity_id:
                price = item.get(field)
                return float(price) if isinstance(price, (int, float)) else 0.0
        return 0.0

    def _quantum_report(self) -> dict[str, Any] | None:
        """Read the docked quantum-freight report so routes come from the engine."""
        status, payload = self.client.get("/api/trade/quantum")
        if status != 200 or not payload.get("ok"):
            return None
        return payload.get("quantum") or payload.get("report") or {}

    def _quantum_manual_action(self):
        """Place one quantum order, then arm and stand down auto-freight (ADR-381).

        The engine's route report already prices every held commodity against every
        reachable terminal, so the captain never guesses a fee or a destination.
        """
        auto = self.state.get("quantum_automation") or {}
        if auto.get("enabled"):
            window_passed = self.total_steps - self.quantum_armed_at >= self.QUANTUM_AUTOMATION_WINDOW
            if int(auto.get("orders") or 0) > 0 or window_passed:
                body = {"enabled": False}
                if self._tour_action_attempted("/api/trade/quantum/automation", body):
                    return None
                return "/api/trade/quantum/automation", body, "quantum_automation"
            return None
        if not self._is_docked():
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        report = self._quantum_report()
        if not report or not report.get("docked"):
            return None
        ship = self.state.get("ship") or {}
        credits = int(ship.get("credits") or 0)
        routes = [
            route for route in report.get("routes") or []
            if isinstance(route, dict) and int(route.get("net") or 0) > 0
            and int(route.get("fee") or 0) <= credits
            and str(route.get("commodity_id") or "")
            and str(route.get("destination_system_id") or "")
        ]
        routes.sort(key=lambda route: -int(route.get("net") or 0))
        if not routes:
            return None
        route = routes[0]
        body = {
            "commodity_id": str(route["commodity_id"]),
            "quantity": 1,
            "destination_system_id": str(route["destination_system_id"]),
        }
        if not self._tour_action_attempted("/api/trade/quantum/place", body):
            return "/api/trade/quantum/place", body, "quantum_place"
        arm = {"enabled": True, "min_net": 0}
        if self._tour_action_attempted("/api/trade/quantum/automation", arm):
            return None
        self.quantum_armed_at = self.total_steps
        return "/api/trade/quantum/automation", arm, "quantum_automation"

    def _fabricate_action(self):
        """Field-fabricate one patch kit or fuel cell after the campaign (ADR-394).

        The tour already tries this builder, but a long run often reaches it with a full
        hull and tank; the post-story gap is exactly when the titanium is worth spending.
        """
        if "/api/fabricate" in self.succeeded:
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        ship = self.state.get("ship") or {}
        if int((ship.get("cargo") or {}).get("titanium") or 0) < 1:
            return None
        if int(ship.get("hull") or 0) < int(ship.get("max_hull") or 0):
            body = {"munitions_type": "patch_kit"}
        elif int(ship.get("fuel") or 0) < int(ship.get("max_fuel") or 0):
            body = {"munitions_type": "fuel_cell"}
        else:
            return None
        if self._tour_action_attempted("/api/fabricate", body):
            return None
        return "/api/fabricate", body, "fabricate"

    def _overhaul_action(self):
        """Scrub hyperlane frame wear once after the campaign at a drydock (ADR-393).

        The rotating tour owns an overhaul builder, but the long campaigns never reach it
        once the post-story actions queue ahead, so wear accumulates to the cap.
        """
        if "/api/overhaul" in self.attempted or not self._is_docked():
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        ship = self.state.get("ship") or {}
        wear = float(ship.get("wear") or 0.0)
        cost = int((self.state.get("drydock") or {}).get("overhaul_cost") or 0)
        if wear <= 0.0 or cost <= 0:
            return None
        if int(ship.get("credits") or 0) < cost:
            return None
        return "/api/overhaul", {}, "overhaul"

    def _relic_fuse_action(self):
        """Fuse the lowest complete relic set once after the campaign (ADR-392).

        The campaign collects dozens of common relics; one fusion proves the ladder
        without consuming the whole collection.
        """
        if "/api/relics/fuse" in self.attempted:
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        counts: dict[str, int] = {}
        for relic in (self.state.get("ship") or {}).get("relics") or []:
            if isinstance(relic, dict):
                rarity = str(relic.get("rarity") or "").lower()
                if rarity:
                    counts[rarity] = counts.get(rarity, 0) + 1
        for rarity in ("common", "rare", "epic"):
            if counts.get(rarity, 0) >= 3:
                return "/api/relics/fuse", {"rarity": rarity}, "relic_fuse"
        return None

    def _megastructure_action(self):
        """Restore the first affordable restorable structure after the campaign (ADR-391).

        The snapshot reports cost, orbit and completion only for the current body, so the
        captain probes the restorable body types and lets the report confirm each one.
        """
        if "/api/megastructure/restore" in self.attempted:
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        ship = self.state.get("ship") or {}
        credits = int(ship.get("credits") or 0)
        report = self.state.get("megastructure") or {}
        if report.get("restorable") and not report.get("complete"):
            body_id = str(report.get("body_id") or "")
            if body_id and report.get("orbiting") and credits >= int(report.get("cost") or 0):
                return ("/api/megastructure/restore", {"body_id": body_id},
                        "megastructure")
            if report.get("orbiting"):
                return None
        system = self.state.get("current_system") or {}
        orbiting = str((self.state.get("orbiting_body") or {}).get("id") or "")
        if report.get("restorable") and orbiting:
            self.megastructure_probed.add(orbiting)
        for body in system.get("bodies") or []:
            if not isinstance(body, dict):
                continue
            body_id = str(body.get("id") or "")
            if not body_id or body_id == orbiting:
                continue
            if str(body.get("body_type") or "") not in self.MEGASTRUCTURE_TYPES:
                continue
            if body_id in self.megastructure_probed:
                continue
            return "/api/orbit", {"target": body_id}, "orbit"
        return None

    def _reconstruct_action(self):
        """Orbit and rebuild the worst devastated inhabited world in this system (ADR-395).

        Wars leave devastated colonies across the galaxy; the credit mode is cheap and
        the standing gain is real, so the captain takes the first one it can reach.
        """
        if "/api/reconstruct" in self.attempted:
            return None
        system = self.state.get("current_system") or {}
        targets = [
            body for body in system.get("bodies") or []
            if isinstance(body, dict) and body.get("id")
            and int(body.get("population") or 0) > 0
            and float(body.get("devastation") or 0.0) > 0.0
        ]
        if not targets:
            return None
        target = max(targets, key=lambda body: float(body.get("devastation") or 0.0))
        body_id = str(target["id"])
        ship = self.state.get("ship") or {}
        cargo = ship.get("cargo") or {}
        missing = [
            (item_id, max(0, quantity - int(cargo.get(item_id, 0))))
            for item_id, quantity in self.RELIEF_CARGO
            if int(cargo.get(item_id, 0)) < quantity
        ]
        stocked_here = (
            missing
            and self._is_docked()
            and self.relief_stock_attempts < self.RELIEF_STOCK_LIMIT
        )
        if stocked_here:
            # Stock the relief bags while already at a dock; away from one the captain
            # takes the credit rebuild rather than detouring for supplies (ADR-425).
            quotes = {
                str(quote.get("commodity_id")): quote
                for quote in self.state.get("market_quotes") or []
                if isinstance(quote, dict)
            }
            credits = int(ship.get("credits") or 0)
            for item_id, need in missing:
                quote = quotes.get(item_id)
                if not quote:
                    continue
                if int(quote.get("max_buy") or 0) < need:
                    continue
                if credits < int(quote.get("buy_price") or 0) * need:
                    continue
                self.relief_stock_attempts += 1
                return ("/api/trade",
                        {"commodity_id": item_id, "quantity": need, "is_buy": True},
                        "trade")
            # No bag is buyable here: fall through to the credit rebuild below.
        orbiting = str((self.state.get("orbiting_body") or {}).get("id") or "")
        landed = str(ship.get("landed_body_id") or "")
        if body_id not in (orbiting, landed):
            return "/api/orbit", {"target": body_id}, "orbit"
        if not missing:
            return ("/api/reconstruct", {"body_id": body_id, "mode": "relief"},
                    "reconstruct")
        if int(ship.get("credits") or 0) < self.RECONSTRUCTION_COST:
            return None
        return ("/api/reconstruct", {"body_id": body_id, "mode": "credits"},
                "reconstruct")

    def _note_pact_attempt(self, action: str, faction_id: str) -> None:
        """Remember a signature attempt so a refusal is not retried forever (ADR-428)."""
        self.pact_tried.add((action, faction_id))

    def _pact_action(self):
        """Sign a trade pact, then a research pact, with a friendly faction (ADR-428).

        Both pacts pay off in credits or research, and two milestones key on them, but
        the tour only ever improves standing and never signs. The engine's gates are
        mirrored exactly: standing 40 for trade, 60 for research, no belligerent in a
        war that involves the player's polity, and each pact once per faction.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        ship = self.state.get("ship") or {}
        standings = ship.get("faction_standings") or {}
        trade = {str(faction) for faction in ship.get("trade_pacts") or []}
        research = {str(faction) for faction in ship.get("research_pacts") or []}
        wars = [
            war for war in self.state.get("wars") or []
            if isinstance(war, dict) and war.get("active")
        ]

        def at_war_with_player(faction_id: str) -> bool:
            return any(
                "sol_coalition" in (war.get("attacker_id"), war.get("defender_id"))
                and faction_id in (war.get("attacker_id"), war.get("defender_id"))
                for war in wars
            )

        def best(threshold: int, held: set[str], action: str) -> tuple[int, str] | None:
            rows = [
                (int(standing), str(faction))
                for faction, standing in standings.items()
                if int(standing) >= threshold
                and str(faction) not in held
                and not at_war_with_player(str(faction))
                and (action, str(faction)) not in self.pact_tried
            ]
            return max(rows) if rows else None

        pick = best(40, trade, "trade_pact")
        if pick is not None:
            self._note_pact_attempt("trade_pact", pick[1])
            return "/api/diplomacy", {"faction_id": pick[1], "action": "trade_pact"}, "diplomacy"
        pick = best(60, research, "research_pact")
        if pick is not None:
            self._note_pact_attempt("research_pact", pick[1])
            return "/api/diplomacy", {"faction_id": pick[1], "action": "research_pact"}, "diplomacy"
        return None

    def _quantum_freight_action(self):
        """Run the automated quantum freight lane until both broker milestones (ADR-434).

        The rotating tour arms and disarms the broker, so the automation never ships a
        load and the engine's ``_run_quantum_automation`` path stays unexercised. This
        run arms it for good, buys a full lot when the hold is empty, and advances the
        clock so the cooldown places one order per call; eight idle steps without a new
        order means the hold has no profitable lane and the run stops. The run passes
        the broker target (five automated orders) and continues to the freight-baron
        milestone (ten deliveries), so one run banks both; a hard order cap covers a
        lane whose deliveries lag its orders.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if self.quantum_done:
            return None
        automation = self.state.get("quantum_automation") or {}
        orders = int(automation.get("orders") or 0)
        deliveries = int((self.state.get("stats") or {}).get("deliveries") or 0)
        broker_banked = orders >= self.QUANTUM_ORDER_TARGET
        freight_banked = deliveries >= self.FREIGHT_DELIVERY_TARGET
        if (broker_banked and freight_banked) or orders >= self.QUANTUM_ORDER_LIMIT:
            self.quantum_done = True
            if automation.get("enabled"):
                return (
                    "/api/trade/quantum/automation",
                    {"enabled": False},
                    "trade_quantum_automation",
                )
            return None
        if orders != self.quantum_last_orders:
            self.quantum_last_orders = orders
            self.quantum_idle = 0
        if not self._is_docked():
            return None
        if not automation.get("enabled"):
            return (
                "/api/trade/quantum/automation",
                {"enabled": True, "min_net": 0},
                "trade_quantum_automation",
            )
        ship = self.state.get("ship") or {}
        trade_orders = ship.get("trade_orders") or []
        free = ship.get("cargo_free_volume")
        free = int(ship.get("cargo_capacity") or 0) if free is None else int(free)
        # A profitable stack already in the hold ships itself; a fresh lot keeps the
        # lane working, so buy whenever the hold has room instead of only when empty.
        # The hold starts full of salvage, and waiting for it to empty stopped the run
        # at the broker target with no lane left (ADR-434). Buying waits for every
        # slot to clear, so one lot ships per delivery cycle instead of piling up.
        if not trade_orders and free >= self.QUANTUM_BUY_QUANTITY:
            credits = int(ship.get("credits") or 0)
            quotes = [
                quote
                for quote in self.state.get("market_quotes") or []
                if isinstance(quote, dict)
                and int(quote.get("max_buy") or 0) >= self.QUANTUM_BUY_QUANTITY
                and credits >= int(quote.get("buy_price") or 0) * self.QUANTUM_BUY_QUANTITY
            ]
            if quotes:
                row = min(quotes, key=lambda quote: int(quote.get("buy_price") or 0))
                return (
                    "/api/trade",
                    {"commodity_id": str(row["commodity_id"]),
                     "quantity": self.QUANTUM_BUY_QUANTITY, "is_buy": True},
                    "trade",
                )
        self.quantum_idle += 1
        if self.quantum_idle >= self.QUANTUM_IDLE_LIMIT:
            self.quantum_done = True
            return None
        return "/api/time/step", {"ticks": 6}, "time"

    def _research_action(self):
        """Start the next available research project after the campaign (ADR-432).

        The captain starts one project at step 1 and the bench then sits idle for the
        rest of the save: research points keep accruing from outposts, pacts and
        salvage, but no later project ever starts, so prerequisites and the
        technologist milestone (four completions) stay unreachable. Starting the first
        available project whenever the bench is idle keeps the tech tree advancing; it
        needs no dock or travel, so it runs after every established errand.
        """
        if self.research_done:
            return None
        research = self.state.get("research") or {}
        if len(research.get("completed") or []) >= self.RESEARCH_TARGET:
            self.research_done = True
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if research.get("active_project_id") or research.get("queue"):
            return None
        for project in research.get("available") or []:
            project_id = str(project.get("id") or "") if isinstance(project, dict) else ""
            if project_id and project_id not in self.research_tried:
                self.research_tried.add(project_id)
                return "/api/research/start", {"project_id": project_id}, "research"
        return None

    def _away_rotation_action(self):
        """Keep away teams deployed after the campaign (ADR-433).

        The tour launches one expedition, the first team is protected and every later
        one is recalled, so ``away_missions`` ends at one in every campaign and the
        field-team milestone (five completions) plus the Deep Explorer medal stay
        unreachable. The rotation launches the first unworked, fully staffable mission
        the current orbit offers whenever no team is deployed, and waits for that team
        to resolve. Each ``(mission_type, body)`` pair is tried once, so a refused
        launch cannot repeat.
        """
        if self.away_rotation_done:
            return None
        ship = self.state.get("ship") or {}
        if ship.get("away_missions"):
            return None
        stat = int((self.state.get("stats") or {}).get("away_missions") or 0)
        if stat >= self.AWAY_MISSION_TARGET:
            self.away_rotation_done = True
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        report = self.state.get("away_report") or {}
        body = report.get("body") or self.state.get("orbiting_body") or {}
        body_id = str(body.get("id") or "")
        for mission in report.get("available") or []:
            if not isinstance(mission, dict) or not mission.get("id"):
                continue
            if not mission.get("available", True) or mission.get("worked"):
                continue
            mission_type = str(
                mission.get("mission_type") or mission.get("type") or mission["id"]
            )
            if (mission_type, body_id) in self.away_launch_tried:
                continue
            self.away_launch_tried.add((mission_type, body_id))
            return "/api/away/launch", {"mission_type": mission_type}, "away"
        return None

    def _squadron_action(self):
        """Commission and staff escorts up to the squadron milestones (ADR-435).

        A campaign ends with one commissioned corvette and one captain: the tour buys
        a single escort and the Act battles destroy it, so Squadron Command (three
        escorts) and Captain Corps (three captains) stay unreachable even though the
        milestones count lifetime commissions and assignments. The policy staffs every
        living escort without a captain first, then commissions the cheapest hull
        until three exist; each (ship, crew) pair is tried once and purchases are
        bounded, so a refusal cannot loop.
        """
        if self.squadron_done:
            return None
        stats = self.state.get("stats") or {}
        commissioned = sum(
            int(value)
            for key, value in stats.items()
            if key.startswith("escort_commissions_")
        )
        assigned = int(stats.get("escort_captains_assigned") or 0)
        if (commissioned >= self.SQUADRON_TARGET
                and assigned >= self.CAPTAIN_CORPS_TARGET):
            self.squadron_done = True
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if not self._is_docked():
            return None
        rows = self._escort_rows()
        commanded = {str(ship.get("captain_id") or "") for ship in rows}
        crew = [
            member for member in self.state.get("crew") or []
            if isinstance(member, dict)
            and member.get("id")
            and str(member.get("status")) == "active"
            and int(member.get("injury_ticks") or 0) == 0
            and not str(member.get("station") or "").strip()
            and str(member.get("id")) not in commanded
        ]
        if assigned < self.CAPTAIN_CORPS_TARGET:
            for ship in rows:
                hull = int(ship.get("hull") or 0)
                if hull <= 0 or str(ship.get("captain_id") or ""):
                    continue
                ship_id = str(ship["id"])
                for member in crew:
                    crew_id = str(member["id"])
                    pair = (ship_id, crew_id)
                    if pair in self.squadron_tried:
                        continue
                    self.squadron_tried.add(pair)
                    return (
                        "/api/fleet/escort/captain",
                        {"ship_id": ship_id, "crew_id": crew_id,
                         "action": "assign"},
                        "escort_captain",
                    )
        if commissioned < self.SQUADRON_TARGET:
            # Never buy a hull that would sit unstaffed: a living escort without a
            # captain is the next assignment, so the purchase waits for it (and only
            # a crew member who could command the new hull opens another slot).
            unstaffed = any(
                int(ship.get("hull") or 0) > 0
                and not str(ship.get("captain_id") or "")
                for ship in rows
            )
            if not crew or unstaffed:
                return None
            catalog = (self.state.get("fleet_manager") or {}).get("catalog") or {}
            options = [
                (int(row.get("cost") or 0), str(key))
                for key, row in catalog.items()
                if isinstance(row, dict) and int(row.get("cost") or 0) > 0
            ]
            if not options or self.squadron_buys >= self.SQUADRON_TARGET:
                return None
            cost, escort_type = min(options)
            credits = int((self.state.get("ship") or {}).get("credits") or 0)
            if credits < cost + self.SQUADRON_CREDIT_RESERVE:
                return None
            self.squadron_buys += 1
            return (
                "/api/fleet/escort/buy",
                {"escort_type": escort_type,
                 "system_id": (self.state.get("current_system") or {}).get("id", "")},
                "fleet",
            )
        return None

    def _survey_action(self):
        """Finish one full-system survey after the campaign (ADR-427).

        A survey bonus is only paid when every body in the system has been scanned, and
        the rotating tour never completes one. The sweep orbits and scans any unscanned
        body in order, bounded by ``SURVEY_SCAN_LIMIT`` steps; hostile bodies that refuse
        an orbit are skipped so a single anomaly cannot stall the sweep.
        """
        if self.survey_done or self.survey_scans >= self.SURVEY_SCAN_LIMIT:
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        system = self.state.get("current_system") or {}
        bodies = [body for body in system.get("bodies") or [] if isinstance(body, dict)]
        pending = [body for body in bodies if body.get("id") and not body.get("scan_completed")]
        if not pending:
            self.survey_done = True
            return None
        orbiting = str((self.state.get("orbiting_body") or {}).get("id") or "")
        target = next((body for body in pending if str(body.get("id")) == orbiting), None)
        if target is None:
            self.survey_scans += 1
            return "/api/orbit", {"target": str(pending[0]["id"])}, "orbit"
        self.survey_scans += 1
        return "/api/scan", {}, "scan"

    def _scoop_action(self):
        """Orbit a scoopable body when the post-story tank is running low (ADR-396).

        The general flight flow already claims a scoop under the ship; this policy
        only moves the captain to a star, gas giant or ice body that offers one.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if "/api/scoop" in self.succeeded:
            return None
        ship = self.state.get("ship") or {}
        fuel = int(ship.get("fuel") or 0)
        max_fuel = max(1, int(ship.get("max_fuel") or 0))
        if fuel * 2 >= max_fuel:
            return None
        # Claim a scoop under the ship here: the salvage and construction errands
        # would otherwise orbit away before the general flight flow runs (ADR-396).
        if (self.state.get("scoop") or {}).get("available"):
            return "/api/scoop", {}, "scoop"
        current = str((self.state.get("orbiting_body") or {}).get("id") or "")
        system = self.state.get("current_system") or {}
        for body in system.get("bodies") or []:
            if not isinstance(body, dict):
                continue
            body_id = str(body.get("id") or "")
            if (not body_id or body_id == current
                    or body_id in self.scoop_probed
                    or str(body.get("body_type") or "") not in self.SCOOP_BODY_TYPES):
                continue
            self.scoop_probed.add(body_id)
            return "/api/orbit", {"target": body_id}, "orbit"
        return None

    def _salvage_action(self):
        """Probe a plausible derelict body after the campaign (ADR-396).

        Derelicts are deterministic per body but invisible until the captain orbits
        one, so the probe is capped instead of scanning the whole system.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        if "/api/salvage" in self.succeeded:
            return None
        # Claim the derelict under the ship before another errand orbits away; this
        # also covers the body that reached the probe limit (ADR-396).
        if self.state.get("salvage_site"):
            return "/api/salvage", {}, "salvage"
        if self.salvage_probes >= self.SALVAGE_PROBE_LIMIT:
            return None
        current = str((self.state.get("orbiting_body") or {}).get("id") or "")
        system = self.state.get("current_system") or {}
        for body in system.get("bodies") or []:
            if not isinstance(body, dict):
                continue
            body_id = str(body.get("id") or "")
            if (not body_id or body_id == current
                    or body_id in self.salvage_probed
                    or body.get("station_dockable")
                    or body.get("salvage_claimed")
                    or str(body.get("body_type") or "") in self.DERELICT_EXCLUDED_TYPES):
                continue
            self.salvage_probed.add(body_id)
            self.salvage_probes += 1
            return "/api/orbit", {"target": body_id}, "orbit"
        return None

    def _outpost_link_action(self):
        """Build two same-system outposts, then link their supply (ADR-390).

        The supply link is the only route that needs a pair in one system, and the
        post-campaign treasury covers both. Only dockable bodies are orbited so the
        station errand does not fight the construction trip.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        # One pair per campaign: the first link attempt ends the construction flow so a
        # later jump cannot seed a fresh pair in every system (ADR-390).
        if "/api/outpost/link" in self.attempted:
            return None
        system = self.state.get("current_system") or {}
        system_id = str(system.get("id") or "")
        local = [
            outpost for outpost in self.state.get("outposts") or []
            if isinstance(outpost, dict)
            and str(outpost.get("system_id") or "") == system_id
        ]
        if len(local) >= 2:
            return self._outpost_link_pair(local)
        ship = self.state.get("ship") or {}
        level = int((ship.get("mastery") or {}).get("level") or 0)
        if level < self.OUTPOST_CHARTER_LEVEL:
            return None
        body = self.state.get("orbiting_body") or {}
        body_id = str(body.get("id") or "")
        occupied = bool(self.state.get("outpost_body_occupied")) or any(
            str(outpost.get("body_id") or "") == body_id for outpost in local)
        options = [
            str(option) for option in self.state.get("outpost_options") or []
            if str(option) in self.OUTPOST_COSTS
        ]
        credits = int(ship.get("credits") or 0)
        if body_id and not occupied:
            if options:
                outpost_type = min(options, key=lambda option: self.OUTPOST_COSTS[option])
                if credits >= self.OUTPOST_COSTS[outpost_type]:
                    return ("/api/outpost/build",
                            {"body_id": body_id, "outpost_type": outpost_type},
                            "outpost_build")
                return None
            self.outpost_probed.add(body_id)
        for candidate in system.get("bodies") or []:
            if not isinstance(candidate, dict):
                continue
            candidate_id = str(candidate.get("id") or "")
            if not candidate_id or candidate_id == body_id:
                continue
            if candidate_id in self.outpost_probed:
                continue
            if not candidate.get("station_dockable"):
                continue
            if any(str(outpost.get("body_id") or "") == candidate_id for outpost in local):
                continue
            return "/api/orbit", {"target": candidate_id}, "orbit"
        return None

    def _outpost_link_pair(self, local):
        """Route the newest unlinked outpost through the oldest unlinked hub."""
        if "/api/outpost/link" in self.attempted:
            return None
        linked_ids = {str(outpost.get("supply_hub_id") or "") for outpost in local}
        sources = [
            outpost for outpost in reversed(local)
            if not outpost.get("supply_hub_id")
            and str(outpost.get("id") or "") not in linked_ids
        ]
        hubs = [
            outpost for outpost in local
            if not outpost.get("supply_hub_id")
            and str(outpost.get("id") or "") not in linked_ids
        ]
        for source in sources:
            for hub in hubs:
                if source.get("id") == hub.get("id"):
                    continue
                return ("/api/outpost/link",
                        {"outpost_id": str(source["id"]), "hub_id": str(hub["id"])},
                        "outpost_link")
        return None

    def _crew_dismiss_action(self):
        """Trim redundant unassigned crew after the campaign, weakest first (ADR-388).

        The message-tree policy recruits one engineer per refugee flotilla, so the
        post-campaign roster is mostly duplicates. Keep the two best of each
        role-specialty pair; never touch a bridge station, an outpost or a commander.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        crew = [member for member in self.state.get("crew") or []
                if isinstance(member, dict) and member.get("id")]
        if len(crew) <= 2:
            return None
        assigned: set[str] = set()
        for outpost in self.state.get("outposts") or []:
            if isinstance(outpost, dict):
                assigned.update(str(cid) for cid in outpost.get("assigned_crew") or [])
        for ship in (self.state.get("fleet_manager") or {}).get("ships") or []:
            if isinstance(ship, dict) and ship.get("captain_id"):
                assigned.add(str(ship["captain_id"]))
        for mission in (self.state.get("ship") or {}).get("away_missions") or []:
            if isinstance(mission, dict):
                assigned.update(str(cid) for cid in mission.get("crew_ids") or [])
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for member in crew:
            key = (str(member.get("role") or ""), str(member.get("specialty") or ""))
            groups.setdefault(key, []).append(member)
        candidates: list[dict[str, Any]] = []
        for members in groups.values():
            members.sort(key=lambda member: (-int(member.get("skill") or 0),
                                             str(member.get("id"))))
            for member in members[2:]:
                if str(member["id"]) in assigned:
                    continue
                if str(member.get("station") or "").strip():
                    continue
                candidates.append(member)
        candidates.sort(key=lambda member: (int(member.get("skill") or 0),
                                            str(member.get("id"))))
        for member in candidates:
            body = {"crew_id": str(member["id"])}
            if self._tour_action_attempted("/api/crew/dismiss", body):
                continue
            return "/api/crew/dismiss", body, "crew_dismiss"
        return None

    def _shipyard_sell_action(self):
        """Trade in one safe equipped upgrade at a dock after the campaign (ADR-387).

        Cargo and fuel-capacity modules are kept because removing them can overflow the
        hold or clamp the tank; a low tank waits for the refuel builder first.
        """
        if "/api/shipyard/sell" in self.attempted or not self._is_docked():
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        ship = self.state.get("ship") or {}
        if int(ship.get("fuel") or 0) * 2 < int(ship.get("max_fuel") or 1):
            return None
        equipped = ship.get("equipped_upgrades") or {}
        if not isinstance(equipped, dict):
            return None
        catalog = {
            str(upgrade.get("id")): upgrade
            for upgrade in self.state.get("catalog_upgrades") or []
            if isinstance(upgrade, dict) and upgrade.get("id")
        }
        for slot in sorted(equipped):
            upgrade = catalog.get(str(equipped.get(slot))) or {}
            bonus = upgrade.get("stat_bonus") or {}
            if "cargo_capacity" in bonus or "max_fuel" in bonus:
                continue
            body = {"slot": str(slot)}
            if self._tour_action_attempted("/api/shipyard/sell", body):
                continue
            return "/api/shipyard/sell", body, "shipyard_sell"
        return None

    def _prize_sale_action(self):
        """Sell one captured prize at a drydock after the campaign (ADR-399).

        A prize is captured by boarding, so it is the one fleet hull the captain can
        lose without disarming itself; the bought escort is never touched.
        """
        if "/api/fleet/escort/sell" in self.succeeded:
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        prizes = [
            ship for ship in self._escort_rows()
            if str(ship.get("role") or "") == "prize"
        ]
        if not prizes:
            return None
        if not self._is_docked():
            dock = self._dockable_body()
            if dock and dock.get("id"):
                return "/api/travel", {"body_id": dock["id"], "mode": "sublight"}, "dock"
            return None
        return "/api/fleet/escort/sell", {"ship_id": str(prizes[0]["id"])}, "fleet_sell"

    def _wreck_dismiss_action(self):
        """Decommission a destroyed escort so its officer is released (ADR-402).

        A hull at zero cannot be repaired (the repair tour requires hull above zero)
        and cannot fight, but its assigned captain keeps the seat forever. Prizes are
        left to the drydock sale; only a dead bought escort is decommissioned in place.
        """
        if "/api/fleet/escort/dismiss" in self.succeeded:
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        wrecks = [
            ship for ship in self._escort_rows()
            if str(ship.get("role") or "") != "prize"
            and int(ship.get("hull") or 0) <= 0
        ]
        if not wrecks:
            return None
        return "/api/fleet/escort/dismiss", {"ship_id": str(wrecks[0]["id"])}, "fleet_dismiss"

    def _send_action(self):
        """Send one quantum report to a real correspondent after the campaign (ADR-386)."""
        if "/api/messages/send" in self.attempted:
            return None
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        recipient = ""
        for message in self.state.get("messages") or []:
            if isinstance(message, dict) and str(message.get("sender") or "").strip():
                recipient = str(message["sender"]).strip()
                break
        if not recipient:
            for captain in self.state.get("ai_captains") or []:
                if isinstance(captain, dict) and str(captain.get("name") or "").strip():
                    recipient = str(captain["name"]).strip()
                    break
        if not recipient:
            return None
        return ("/api/messages/send",
                {"recipient": recipient, "subject": "Survey report",
                 "body": "Routine survey telemetry from the current campaign."}, "messages_send")

    def _ally_action(self):
        """Hail the most trusted non-ally to 50 trust, then ally (ADR-385)."""
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        candidates = [
            captain for captain in self.state.get("ai_captains") or []
            if isinstance(captain, dict) and captain.get("id") and not captain.get("ally")
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda captain: -int(captain.get("trust") or 0))
        lead = candidates[0]
        if int(lead.get("trust") or 0) >= self.ALLY_TRUST:
            body = {"captain_id": str(lead["id"])}
            if self._tour_action_attempted("/api/ally/form", body):
                return None
            return "/api/ally/form", body, "ally"
        return ("/api/ai/interact",
                {"captain_id": str(lead["id"]), "action": "hail"}, "ai")

    def _patrol_action(self):
        """Recall a detached escort, then patrol one onto a connected lane (ADR-382).

        Assignment only changes the escort's station, so the rotation is reversible
        and the fleet ends the campaign local.
        """
        if not (self.state.get("story_status") or {}).get("completed"):
            return None
        system = self.state.get("current_system") or {}
        system_id = str(system.get("id") or "")
        escorts = [
            ship for ship in self._escort_rows()
            if int(ship.get("hull") or 0) > 0 and ship.get("id")
        ]
        for ship in escorts:
            assigned = str(ship.get("assigned_system_id") or "")
            if system_id and assigned and assigned != system_id:
                body = {"ship_id": str(ship["id"]), "system_id": system_id}
                if not self._tour_action_attempted("/api/fleet/escort/assign", body):
                    return "/api/fleet/escort/assign", body, "escort_assign"
        connections = [str(item) for item in system.get("connections") or [] if item]
        if not connections:
            return None
        for ship in escorts:
            if str(ship.get("assigned_system_id") or "") != system_id:
                continue
            body = {"ship_id": str(ship["id"]), "system_id": connections[0]}
            if not self._tour_action_attempted("/api/fleet/escort/assign", body):
                return "/api/fleet/escort/assign", body, "escort_assign"
        return None

    def _tour_supply(self):
        """Buy the station repair paste so the item terminal is exercised (ADR-367)."""
        ship = self.state.get("ship") or {}
        if int((ship.get("cargo") or {}).get(self.SUPPLY_ITEM_ID) or 0) > 0:
            return None
        return self._supply_purchase(self.SUPPLY_ITEM_ID, self.SUPPLY_FALLBACK_PRICE)

    def _tour_supply_decoy(self):
        """Buy the last-resort ECM decoy once, separately so the paste cannot starve it (ADR-371)."""
        ship = self.state.get("ship") or {}
        if int((ship.get("cargo") or {}).get(self.SUPPLY_DECOY_ID) or 0) > 0:
            return None
        return self._supply_purchase(self.SUPPLY_DECOY_ID, self.SUPPLY_FALLBACK_DECOY_PRICE)

    def _supply_purchase(self, item_id: str, fallback_price: int):
        ship = self.state.get("ship") or {}
        if not self._is_docked():
            return None
        catalog = {
            str(item.get("id")): item
            for item in self.state.get("catalog_items") or []
            if isinstance(item, dict)
        }
        row = catalog.get(item_id) or {}
        price = int(row.get("base_price") or fallback_price)
        volume = int(row.get("volume") or self.SUPPLY_VOLUME)
        free = ship.get("cargo_free_volume")
        free = int(ship.get("cargo_capacity") or 0) if free is None else int(free)
        if int(ship.get("credits") or 0) < price or free < volume:
            return None
        return "/api/inventory/buy", {"item_id": item_id, "quantity": 1}, "supply"

    def _story_hold_action(self):
        """Resolve the local chapter instead of letting a dock trip or body travel leave it.

        The rotating tour runs only on even steps and the dock trip runs before it, so a
        ready chapter could be walked out of; once the required body was orbited, the
        de-duplicated orbit signature never fired again (ADR-360).
        """
        story = self.state.get("story_status") or {}
        if story.get("completed") or not story.get("target_system_id"):
            return None
        current = str((self.state.get("current_system") or {}).get("id") or "")
        if current != str(story.get("target_system_id")):
            return None
        unmet = [str(item) for item in story.get("unmet_requirements") or []]
        if not unmet:
            return self._tour_story_choice()
        if all("orbit" in item.lower() for item in unmet):
            return self._tour_story_orbit()
        return None

    def _tour_story_travel(self):
        """Fly to the chapter target when the tank can cover the whole route plus a reserve.

        The snapshot publishes the real course estimate, so this cannot strand itself on a
        multi-hop trip the way the first prototype did (ADR-358, ADR-360).
        """
        status = self.state.get("story_status") or {}
        if status.get("completed"):
            return None
        target = str(status.get("target_system_id") or "")
        current = str((self.state.get("current_system") or {}).get("id") or "")
        ship = self.state.get("ship") or {}
        if not target or target == current:
            return None
        route = status.get("route") or {}
        if not route.get("reachable") or not route.get("fuel_estimate"):
            return None
        if ship.get("travel") or self.state.get("active_combat") or self.state.get("active_anomaly"):
            return None
        needed = int(route["fuel_estimate"]) + self.NAVIGATION_FUEL_RESERVE
        if int(ship.get("fuel") or 0) < needed:
            return None
        return "/api/navigate", {"system_id": target}, "story_travel"

    def _tour_story_orbit(self):
        """Orbit the body a chapter explicitly demands (Act IV's black hole, ADR-360)."""
        status = self.state.get("story_status") or {}
        chapter_id = str(status.get("chapter_id") or "")
        chapter = (self.state.get("story_chapters_map") or {}).get(chapter_id) or {}
        requirements = chapter.get("requirements") or {}
        body_id = str(requirements.get("orbit_body_id") or "")
        if not body_id:
            return None
        ship = self.state.get("ship") or {}
        if str(ship.get("orbiting_body_id") or "") == body_id:
            return None
        system = self.state.get("current_system") or {}
        if not any(isinstance(body, dict) and body.get("id") == body_id
                   for body in system.get("bodies") or []):
            return None
        return "/api/orbit", {"target": body_id}, "story_orbit"

    def _tour_message_send(self):
        """Read pending inbox mail first, then send to the first correspondent (ADR-354, ADR-378)."""
        mail = self._unread_message_action()
        if mail is not None:
            return mail
        messages = [m for m in self.state.get("messages") or [] if isinstance(m, dict)]
        recipient = str((messages[0].get("sender") if messages else "") or "")
        if not recipient:
            return None
        return ("/api/messages/send",
                {"recipient": recipient, "subject": "Survey report",
                 "body": "Routine survey telemetry from the current campaign."}, "messages_send")

    def _tour_shore_leave(self):
        if not self._is_docked():
            return None
        active = [member for member in self.state.get("crew") or []
                  if isinstance(member, dict) and member.get("status") == "active"]
        if not active:
            return None
        if not any(float(member.get("morale") or 100.0) < 99.9 for member in active):
            return None
        return "/api/crew/shore", {}, "crew_shore"

    def _away_recall_action(self):
        """Let the first team finish, then abort a later expedition (ADR-384)."""
        missions = [
            mission for mission in (self.state.get("ship") or {}).get("away_missions") or []
            if isinstance(mission, dict) and mission.get("id")
        ]
        if not missions:
            return None
        if not self.away_protected_mission:
            self.away_protected_mission = str(missions[0]["id"])
            return None
        if not self.away_rotation_done and (self.state.get("story_status") or {}).get("completed"):
            # The post-story rotation wants every expedition to resolve; it launches
            # only when none is active, so a lone mission is its own team and is
            # adopted as protected instead of being recalled (ADR-433).
            if len(missions) == 1:
                self.away_protected_mission = str(missions[0]["id"])
                return None
        for mission in missions:
            mission_id = str(mission["id"])
            if mission_id == self.away_protected_mission:
                continue
            body = {"mission_id": mission_id}
            if self._tour_action_attempted("/api/away/recall", body):
                continue
            return "/api/away/recall", body, "away_recall"
        return None

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

    def _tour_overhaul(self):
        """Scrub hyperlane frame wear at a drydock; the wear only appears after many jumps."""
        if not self._is_docked():
            return None
        ship = self.state.get("ship") or {}
        if float(ship.get("wear") or 0.0) <= 0.0:
            return None
        quote = self.state.get("drydock") or {}
        cost = int(quote.get("overhaul_cost") or 0)
        if cost > int(ship.get("credits") or 0):
            return None
        return "/api/overhaul", {}, "overhaul"

    def _tour_repair(self):
        # Attempted at any dock: an undamaged hull gets a harmless refusal, which keeps the
        # endpoint covered when the run happens to take no damage (ADR-353).
        if not self._is_docked():
            return None
        return "/api/repair", {}, "repair"

    def _tour_crew(self):
        """Hire the pilot, then the marine, from one builder (ADR-375, ADR-376).

        The recruit route is keyed by role_id, so one builder can fill both roles across
        visits; a separate marine builder cost a tour slot and dropped late coverage.
        """
        roles = self.state.get("crew_roles") or []
        if not roles or not self._is_docked():
            return None
        by_id = {
            str(role.get("id")): role
            for role in roles
            if isinstance(role, dict)
        }
        present = {
            str(member.get("role"))
            for member in self.state.get("crew") or []
            if isinstance(member, dict) and str(member.get("status")) != "dead"
        }
        credits = int((self.state.get("ship") or {}).get("credits") or 0)
        for role_id in ("pilot", "marine"):
            role = by_id.get(role_id)
            if role is None or role_id in present:
                continue
            if credits < int(role.get("cost") or 0):
                continue
            return "/api/crew/recruit", {"role_id": role_id}, "crew"
        return None

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
        """Claim any completed milestone that has not been banked yet (ADR-426).

        The signature is keyed on the entry id, so repeated claims stay reachable; keying
        it on the path allowed exactly one claim per campaign while dozens stayed ready.
        """
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
        # Three units so the later withdraw and sell steps have stock to work with (ADR-353).
        quantity = min(3, int(manifest[0].get("quantity") or 1))
        return "/api/depot/deposit", {"item_id": item_id, "quantity": quantity}, "depot"

    def _depot_stock(self):
        """The current system's depot and its first item with stock."""
        system_id = (self.state.get("current_system") or {}).get("id")
        depot = next(
            (d for d in (self.state.get("depots") or [])
             if isinstance(d, dict) and d.get("system_id") == system_id),
            None,
        )
        if depot is None:
            return None, None
        cargo = depot.get("cargo") or {}
        item = next((key for key, value in cargo.items() if int(value or 0) > 0), None)
        return depot, item

    def _tour_depot_withdraw(self):
        if not self._is_docked():
            return None
        _depot, item = self._depot_stock()
        if not item:
            return None
        free = int((self.state.get("ship") or {}).get("cargo_free_volume") or 0)
        if free < 2:
            return None
        return "/api/depot/withdraw", {"item_id": item, "quantity": 1}, "depot_withdraw"

    def _tour_depot_sell(self):
        if not self._is_docked():
            return None
        _depot, item = self._depot_stock()
        if not item:
            return None
        return "/api/depot/sell", {"item_id": item, "quantity": 1}, "depot_sell"

    def _tour_research_queue(self):
        research = self.state.get("research") or {}
        completed = set(research.get("completed") or [])
        queued = set(research.get("queue") or [])
        active = research.get("active_project_id")
        for project in research.get("available") or []:
            project_id = str(project.get("id") or "") if isinstance(project, dict) else ""
            if project_id and project_id not in completed \
                    and project_id not in queued and project_id != active:
                return "/api/research/queue", {"project_id": project_id}, "research_queue"
        return None

    def _tour_research_cancel(self):
        queue = (self.state.get("research") or {}).get("queue") or []
        if not queue:
            return None
        project_id = str(queue[0])
        return "/api/research/cancel", {"project_id": project_id}, "research_cancel"

    def _tour_trade(self):
        """Take one market trade on the tour so the route survives station errands (ADR-371)."""
        if self._tour_action_attempted("/api/trade", {}):
            return None
        return self._trade_choice(0)

    def _tour_fabricate(self):
        ship = self.state.get("ship") or {}
        if int((ship.get("cargo") or {}).get("titanium") or 0) < 1:
            return None
        if int(ship.get("hull") or 0) < int(ship.get("max_hull") or 0):
            return "/api/fabricate", {"munitions_type": "patch_kit"}, "fabricate"
        if int(ship.get("fuel") or 0) < int(ship.get("max_fuel") or 0):
            return "/api/fabricate", {"munitions_type": "fuel_cell"}, "fabricate"
        return None

    def _tour_crew_station(self):
        crew = [member for member in self.state.get("crew") or []
                if isinstance(member, dict) and member.get("status") == "active"
                and int(member.get("injury_ticks") or 0) == 0
                and not str(member.get("station") or "")]
        if not crew:
            return None
        assigned = {str(crew_id) for outpost in self.state.get("outposts") or []
                    if isinstance(outpost, dict)
                    for crew_id in outpost.get("assigned_crew") or []}
        captains = {str(ship.get("captain_id") or "")
                    for ship in (self.state.get("fleet_manager") or {}).get("ships") or []
                    if isinstance(ship, dict)}
        for member in crew:
            crew_id = str(member.get("id") or "")
            if not crew_id or crew_id in assigned or crew_id in captains:
                continue
            station = self.STATION_BY_ROLE.get(str(member.get("role") or ""))
            if station:
                return "/api/crew/station", {"crew_id": crew_id, "station": station}, "crew_station"
        return None

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
