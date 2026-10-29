"""Discoverable action catalog so an AI can play every mechanic through the public API."""

from __future__ import annotations

import inspect
import re
from typing import Any


_ROUTE_RE = re.compile(r'if path == "(/api/[^"]+)"')
_FIELD_RES = (
    re.compile(r'body\.get\("([^"]+)"'),
    re.compile(r'_int_field\(body,\s*"([^"]+)"'),
    re.compile(r'_float_field\(body,\s*"([^"]+)"'),
)


def _sections(source: str) -> dict[str, str]:
    """Split the handler source into the GET and POST halves."""
    get_at = source.find("def do_GET")
    post_at = source.find("def _do_post")
    if get_at < 0 or post_at < 0:
        return {"GET": "", "POST": ""}
    return {
        "GET": source[get_at:post_at],
        "POST": source[post_at:],
    }


def _route_blocks(section: str) -> list[tuple[str, str]]:
    matches = list(_ROUTE_RE.finditer(section))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        blocks.append((match.group(1), section[start:end]))
    return blocks


def _fields(block: str) -> list[str]:
    found: list[str] = []
    for pattern in _FIELD_RES:
        for name in pattern.findall(block):
            if name not in found:
                found.append(name)
    return found


def build_action_catalog(handler_cls: type) -> dict[str, Any]:
    """Read the handler's own route table and describe every callable endpoint."""
    try:
        source = inspect.getsource(handler_cls)
    except (OSError, TypeError):
        return {"ok": False, "actions": [], "observations": []}
    catalog: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for method, section in _sections(source).items():
        for path, block in _route_blocks(section):
            entry = {"method": method, "path": path}
            fields = _fields(block) if method == "POST" else []
            if fields:
                entry["fields"] = fields
            if method == "GET":
                observations.append(entry)
            else:
                catalog.append(entry)
    catalog.sort(key=lambda item: item["path"])
    observations.sort(key=lambda item: item["path"])
    return {
        "ok": True,
        "actions": catalog,
        "observations": observations,
        "notes": [
            "POST every action with a JSON object of its listed fields.",
            "Read state from GET /api/state, or /api/agent/actions for this catalog.",
            "A pending decision or pirate intercept blocks other actions until resolved.",
        ],
    }
