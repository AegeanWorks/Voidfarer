"""Play VoidFarer headlessly through the public API and report mechanic coverage."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import threading
from pathlib import Path
from typing import Optional, Sequence

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from voidfarer.agent_play import AiCaptain, ApiClient  # noqa: E402
from voidfarer.engine import SimulationEngine  # noqa: E402
from voidfarer.server import ThreadedHTTPServer, VoidFarerHandler  # noqa: E402
from voidfarer.storage import StorageManager  # noqa: E402


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Drive a headless VoidFarer campaign through the cockpit API.",
    )
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true", help="Print the raw report as JSON")
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as temp_dir:
        engine = SimulationEngine(seed=args.seed)
        engine.allow_decision_events = True
        VoidFarerHandler.engine = engine
        VoidFarerHandler.storage = StorageManager(temp_dir)
        VoidFarerHandler.static_dir = Path(__file__).parent.parent / "voidfarer" / "static"
        server = ThreadedHTTPServer(("127.0.0.1", 0), VoidFarerHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = ApiClient(port=server.server_port)
            captain = AiCaptain(client, seed=args.seed)
            report = captain.play(steps=args.steps)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2.0)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"AI captain: {report['steps']} steps, {report['family_count']} mechanic families")
        for family, count in report["families"].items():
            print(f"  {family:<12} {count}")
        if report["refusals"]:
            print(f"  refusals: {len(report['refusals'])} (first: {report['refusals'][0]})")
        for error in report["errors"]:
            print(f"  ERROR: {error}")
        final = report["final"]
        print(
            f"Final: tick {final['tick']} // {final['credits']} cr // hull {final['hull']} "
            f"// fuel {final['fuel']} // orbiting {final['orbiting']}"
        )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
