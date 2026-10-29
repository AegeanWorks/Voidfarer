"""Flight-log windowing: notable galactic news must outlive routine chatter.

The log is a 20-line ring buffer, but the tick emits two AI-trader lines every tick, so
within ten ticks a declaration, a capture or a peace treaty is pushed out of the player's
view. This module keeps the buffer chronological while dropping quiet lines first, and
collapses per-captain trade chatter into one line per tick.

PRINCIPLE-009, PRINCIPLE-012.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence

LOG_LIMIT = 20

# Lines the player must be able to read after the fact: who fought, who won, who made
# peace, who died out, and when a faction's science moved the galaxy forward.
NOTABLE_PREFIXES = (
    "WAR:",
    "WAR DECLARED:",
    "PEACE:",
    "FACTION ELIMINATED:",
    "TECH BREAKTHROUGH",
)

TRADE_LINE = re.compile(r"^AI TRADE: (?P<captain>.+?) moved (?P<qty>\d+)x (?P<what>\S+) to \S+\.$")


def is_notable(line: str) -> bool:
    """True when a log line carries galactic news rather than ambient chatter."""
    return line.startswith(NOTABLE_PREFIXES)


def summarize_trades(lines: Iterable[str]) -> List[str]:
    """Collapse one trade line per captain into a single per-tick summary.

    Lines that are not trade chatter pass through untouched and in order; the summary
    takes the position of the first trade line so the log stays chronological.
    """
    result: List[str] = []
    captains: List[str] = []
    crates = 0
    runs = 0
    summary_at = -1
    for line in lines:
        match = TRADE_LINE.match(line)
        if match is None:
            result.append(line)
            continue
        if summary_at < 0:
            summary_at = len(result)
            result.append("")
        runs += 1
        crates += int(match.group("qty"))
        name = match.group("captain")
        if name not in captains:
            captains.append(name)
    if summary_at < 0:
        return result
    shown = ", ".join(captains[:3]) + (f" +{len(captains) - 3} more" if len(captains) > 3 else "")
    result[summary_at] = (
        f"AI TRADE: {runs} run{'s' if runs != 1 else ''} moved {crates} crate"
        f"{'s' if crates != 1 else ''} ({shown})."
    )
    return result


def trim_log(lines: Sequence[str], limit: int = LOG_LIMIT) -> List[str]:
    """Keep the newest half of the log plus the most recent galactic news.

    Reserving half the buffer for the newest lines keeps local context (arrivals, month
    ends, market moves) readable; the rest is filled from older notable lines, so a
    capture or treaty outlives the trade chatter that follows it without turning the
    panel into an all-war feed.
    """
    entries = list(lines)
    if len(entries) <= limit:
        return entries
    recent_start = len(entries) - limit // 2
    keep = set(range(recent_start, len(entries)))
    room = limit - len(keep)
    for index in range(recent_start - 1, -1, -1):
        if room <= 0:
            break
        if is_notable(entries[index]):
            keep.add(index)
            room -= 1
    for index in range(recent_start - 1, -1, -1):
        if room <= 0:
            break
        if index not in keep:
            keep.add(index)
            room -= 1
    return [entries[index] for index in sorted(keep)]
