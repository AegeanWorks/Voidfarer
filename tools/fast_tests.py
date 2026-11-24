"""Run the project's unit suite in parallel when the Rust shard runner is built.

The engine and its tests stay the authority: this shim only chooses the
transport. With `rust/target/release/test_shard` present it shards the 216 test
modules across eight interpreter processes, which is several times faster than
one sequential `unittest discover` and runs exactly the same tests. Without the
binary it falls back to the original command, so the project still checks on a
machine with no Rust toolchain.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT.parent.parent / "rust" / "target" / "release" / (
    "test_shard.exe" if sys.platform == "win32" else "test_shard"
)


def main() -> int:
    if BINARY.is_file():
        done = subprocess.run(
            [str(BINARY), "--dir", str(ROOT), "--jobs", "8", "--python", sys.executable],
            cwd=ROOT,
            timeout=1800,
            check=False,
        )
        return done.returncode
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover"],
        cwd=ROOT, timeout=1800, check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
