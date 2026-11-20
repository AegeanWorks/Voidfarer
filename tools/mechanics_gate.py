"""The project's Phase 4 mechanics proof: campaign coverage plus invariant fuzz."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

PROJECT_DIR = Path(__file__).resolve().parent.parent


def run_step(label: str, command: list[str], timeout: int) -> tuple[bool, str]:
    """Run one proof command and return whether it passed plus a one-line summary."""
    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, f"{label}: timed out after {timeout}s"
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()
        detail = tail[-1] if tail else f"exit {completed.returncode}"
        return False, f"{label}: failed ({detail})"
    summary = (completed.stdout or "").strip().splitlines()
    return True, f"{label}: {summary[0] if summary else 'ok'}"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the mechanics proof: the 180-step campaign coverage report and a "
            "save-interleaved chaos fuzz, both of which must pass."
        ),
    )
    parser.add_argument("--steps", type=int, default=180,
                        help="Campaign coverage steps (default: 180)")
    parser.add_argument("--fuzz-actions", type=int, default=400,
                        help="Random actions in the invariant fuzz (default: 400)")
    parser.add_argument("--fuzz-seed", type=int, default=3,
                        help="Galaxy seed for the invariant fuzz (default: 3)")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON")
    args = parser.parse_args(argv)
    if args.steps < 1 or args.fuzz_actions < 1:
        parser.error("--steps and --fuzz-actions must be >= 1")

    python = sys.executable
    steps = [
        ("campaign", [python, "tools/ai_play.py", "--steps", str(args.steps)], 300),
        (
            "fuzz",
            [
                python, "tools/chaos_fuzz.py",
                "--seed", str(args.fuzz_seed),
                "--actions", str(args.fuzz_actions),
                "--save-every", "100",
            ],
            300,
        ),
    ]

    results = []
    ok = True
    for label, command, timeout in steps:
        passed, message = run_step(label, command, timeout)
        results.append({"label": label, "ok": passed, "message": message})
        ok = ok and passed

    if args.json:
        import json
        print(json.dumps({"ok": ok, "results": results}, indent=2))
    else:
        for row in results:
            print(("PASS " if row["ok"] else "FAIL ") + row["message"])
        if not ok:
            print("Why: one of the mechanics proofs regressed, so the headless core no longer")
            print("     covers a mechanic or an invariant under random play.")
            print("Fix: run the failing command directly, reproduce the seed/step it prints,")
            print("     and add a failing test before changing the engine.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
