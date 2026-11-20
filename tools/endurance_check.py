"""Long-run endurance check: play many segments, reload between each, verify no drift."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional, Sequence

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from voidfarer.agent_play import AiCaptain, ApiClient  # noqa: E402
from voidfarer.engine import SimulationEngine  # noqa: E402
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler  # noqa: E402
from voidfarer.storage import StorageManager  # noqa: E402

WALL_CLOCK = {"completed_at", "created_at", "started_at", "saved_at", "timestamp", "recorded_at"}


def strip_clock(value: Any, key: Optional[str] = None) -> Any:
    """Drop real-time timestamps so two runs can be compared meaningfully."""
    if key in WALL_CLOCK:
        return "<clock>"
    if isinstance(value, dict):
        return {name: strip_clock(item, name) for name, item in value.items()}
    if isinstance(value, list):
        return [strip_clock(item) for item in value]
    return value


def diff(a: Any, b: Any, path: tuple = ()) -> list[tuple[tuple, Any, Any]]:
    """Return every differing leaf between two serialized states."""
    out: list[tuple[tuple, Any, Any]] = []
    if path and str(path[-1]) in WALL_CLOCK:
        return out
    if type(a) is not type(b):
        return [(path, a, b)]
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append((path + (key,), a.get(key, "<missing>"), b.get(key, "<missing>")))
            else:
                out.extend(diff(a[key], b[key], path + (key,)))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path, f"len {len(a)}", f"len {len(b)}"))
        for index, (x, y) in enumerate(zip(a, b)):
            out.extend(diff(x, y, path + (index,)))
    elif a != b:
        out.append((path, a, b))
    return out


def serve(engine: SimulationEngine, data_dir: str):
    VoidFarerHandler.engine = engine
    VoidFarerHandler.storage = StorageManager(data_dir)
    VoidFarerHandler.static_dir = PROJECT_DIR / "voidfarer" / "static"
    server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def stop(server, thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2.0)


def run(seed: int, segment: int, segments: int) -> dict[str, Any]:
    """Play ``segments`` chunks of ``segment`` steps, reloading a save between each."""
    drift: list[dict[str, Any]] = []
    captain = None
    with tempfile.TemporaryDirectory() as data_dir:
        engine = SimulationEngine(seed=seed)
        engine.allow_decision_events = True
        server, thread = serve(engine, data_dir)
        try:
            captain = AiCaptain(ApiClient(port=server.server_port), seed=seed)
            for index in range(segments):
                captain.play(steps=segment)
                if index == segments - 1:
                    break
                saved = strip_clock(engine.state.to_dict())
                StorageManager(data_dir).save(engine.state)
                stop(server, thread)
                engine = SimulationEngine(state=StorageManager(data_dir).load())
                engine.allow_decision_events = True
                server, thread = serve(engine, data_dir)
                captain.client = ApiClient(port=server.server_port)
                rows = diff(saved, strip_clock(engine.state.to_dict()))
                if rows:
                    drift.append({
                        "segment": index,
                        "step": captain.total_steps,
                        "fields": [".".join(map(str, path)) for path, _, _ in rows[:6]],
                    })
        finally:
            stop(server, thread)

    assert captain is not None
    return {
        "seed": seed,
        "steps": captain.total_steps,
        "segments": segments,
        "errors": len(captain.errors),
        "refusals": len(captain.refusals),
        "families": len(captain.families),
        "succeeded": len(captain.succeeded),
        "attempted": len(captain.attempted),
        "drift": drift,
        "ok": not captain.errors and not drift,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Play a long campaign in segments, reloading a save between each.",
    )
    parser.add_argument("--seed", type=int, default=3, help="Galaxy seed (default: 3)")
    parser.add_argument("--segment", type=int, default=500,
                        help="Steps per segment (default: 500); play() caps one call at 2000")
    parser.add_argument("--segments", type=int, default=20,
                        help="Number of segments, so total steps = segment * segments (default: 20)")
    parser.add_argument("--json", action="store_true", help="Print the raw report as JSON")
    args = parser.parse_args(argv)
    if args.segment < 1 or args.segments < 1:
        parser.error("--segment and --segments must be >= 1")

    report = run(args.seed, args.segment, args.segments)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Endurance: {report['steps']} steps over {report['segments']} segments, "
            f"{report['families']} families, {report['succeeded']} succeeded / "
            f"{report['attempted']} attempted, {report['refusals']} refusals"
        )
        print(f"Errors: {report['errors']}  Save/reload drifts: {len(report['drift'])}")
        for row in report["drift"]:
            print(f"  DRIFT segment {row['segment']} step {row['step']}: {', '.join(row['fields'])}")
        if not report["ok"]:
            print("Why: a long segmented campaign raised errors or a reload changed the universe.")
            print("Fix: reproduce with the printed seed and segment, then add a failing test first.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
