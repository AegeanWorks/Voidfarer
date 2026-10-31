"""
Print VoidFarer's cockpit inventory, one entry per line.

The UI guard snapshots this output before a cockpit edit and compares it afterwards, so a
dropped control, handler, REST route, hotkey, theme token or static asset becomes a lost
line. The dump is pure parsing: it never starts a server or a browser, and its order is
sorted and stable.

Usage: python tools/ui_inventory.py [static-directory]

PRINCIPLE-003, PRINCIPLE-010, PRINCIPLE-015.
"""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Set

PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / "voidfarer" / "static"
SERVER_FILE = PROJECT_DIR / "voidfarer" / "server.py"

ELEMENT_ASSIGNMENT = re.compile(
    r'this\.([A-Za-z_$][\w$]*)\s*=\s*document\.getElementById\("([^"]+)"\)')
LISTENER_PATTERN = re.compile(
    r'this\.([A-Za-z_$][\w$]*)\??\.addEventListener\(\s*["\']([^"\']+)')
DIRECT_LISTENER_PATTERN = re.compile(
    r'document\.getElementById\("([^"]+)"\)\??\.addEventListener\(\s*["\']([^"\']+)')
WINDOW_LISTENER_PATTERN = re.compile(
    r'window\.addEventListener\(\s*["\']([^"\']+)')
METHOD_PATTERN = re.compile(
    r"^\s{4}(?:async\s+|static\s+|get\s+|set\s+)*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{",
    re.MULTILINE)
FUNCTION_ASSIGNMENT = re.compile(
    r"this\.([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?function\s*\(")
API_PATTERN = re.compile(r"""["'`](/api/[^"'`\s?#]*)""")
ROUTE_PATTERN = re.compile(r'path == "(/api/[^"]+)"')
KEY_PATTERN = re.compile(r'(?:e\.key|hotkey)\s*===\s*["\']([^"\']+)["\']')
CODE_PATTERN = re.compile(r'e\.code\s*===\s*["\']([^"\']+)["\']')
CODE_ARRAY_PATTERN = re.compile(r"\[([^\]]*)\]\.includes\(e\.code\)")
QUOTED_PATTERN = re.compile(r"""["']([^"']+)["']""")
GENERATED_ID_PATTERN = re.compile(r'id="([A-Za-z][\w-]*)"')
DIGIT_RANGE_PATTERN = re.compile(r"\^Digit\[1-6\]\$")
TOKEN_PATTERN = re.compile(r"^\s*(--[a-z0-9-]+)\s*:", re.MULTILINE)
TITLE_HOTKEY_PATTERN = re.compile(r"Hotkey:\s*([A-Za-z0-9+]+)", re.IGNORECASE)


class SurfaceParser(HTMLParser):
    """Collects identified elements, roles, live regions and hotkey chips of one page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: Set[str] = set()
        self._hotkey_depth = 0
        self._hotkey_text: List[str] = []

    def _start(self, tag: str, attrs, self_closing: bool) -> None:
        values = {name: value or "" for name, value in attrs}
        element = values.get("id")
        label = f"{tag}#{element}" if element else tag
        if element:
            self.entries.add(f"element {tag}#{element}")
        action = values.get("data-action")
        if action:
            self.entries.add(f"action {action}")
        if "aria-live" in values:
            self.entries.add(f"live-region {label}")
        if values.get("role"):
            self.entries.add(f"role {label} {values['role']}")
        title = values.get("title", "")
        match = TITLE_HOTKEY_PATTERN.search(title)
        if match:
            self.entries.add(f"hotkey label:{match.group(1).lower()}")
        if "hotkey-chip" in values.get("class", "").split() and not self_closing:
            self._hotkey_depth = 1
            self._hotkey_text = []
        elif self._hotkey_depth and not self_closing:
            self._hotkey_depth += 1

    def handle_starttag(self, tag: str, attrs) -> None:
        self._start(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self._start(tag, attrs, self_closing=True)

    def handle_data(self, data: str) -> None:
        if self._hotkey_depth:
            self._hotkey_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._hotkey_depth:
            return
        self._hotkey_depth -= 1
        if self._hotkey_depth == 0:
            text = "".join(self._hotkey_text).strip()
            if text:
                self.entries.add(f"hotkey label:{text.lower()}")


def html_entries(path: Path) -> Set[str]:
    """Identified elements, actions, roles, live regions and hotkey labels of a page."""
    parser = SurfaceParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser.entries


def script_entries(path: Path) -> Set[str]:
    """Handlers, DOM bindings, API calls and hotkeys declared by the cockpit script."""
    text = path.read_text(encoding="utf-8")
    entries: Set[str] = set()
    elements = {name: element for name, element in ELEMENT_ASSIGNMENT.findall(text)}
    for name, event in LISTENER_PATTERN.findall(text):
        target = elements.get(name, f"property:{name}")
        entries.add(f"binding {target} {event}")
    for element, event in DIRECT_LISTENER_PATTERN.findall(text):
        entries.add(f"binding {element} {event}")
    for event in WINDOW_LISTENER_PATTERN.findall(text):
        entries.add(f"binding window {event}")
    entries.update(f"handler {method}" for method in METHOD_PATTERN.findall(text))
    entries.update(f"handler {method}" for method in FUNCTION_ASSIGNMENT.findall(text))
    for endpoint in API_PATTERN.findall(text):
        entries.add(f"api {endpoint}")
    for key in KEY_PATTERN.findall(text):
        entries.add(f"hotkey key:{key.lower()}")
    for code in CODE_PATTERN.findall(text):
        entries.add(f"hotkey code:{code}")
    for group in CODE_ARRAY_PATTERN.findall(text):
        entries.update(f"hotkey code:{code}" for code in QUOTED_PATTERN.findall(group))
    if DIGIT_RANGE_PATTERN.search(text):
        entries.add("hotkey code:Digit1..6")
    entries.update(f"generated-element {element}" for element in GENERATED_ID_PATTERN.findall(text))
    return entries


def route_entries(path: Path) -> Set[str]:
    """The exact `/api/` routes the cockpit server dispatches."""
    if not path.is_file():
        return set()
    return {f"route {route}" for route in ROUTE_PATTERN.findall(path.read_text(encoding="utf-8"))}


def token_entries(path: Path) -> Set[str]:
    """Theme custom properties the stylesheet declares."""
    text = path.read_text(encoding="utf-8")
    return {f"token {name}" for name in TOKEN_PATTERN.findall(text)}


def inventory(static: Path) -> List[str]:
    """Every inventory entry of a cockpit directory, sorted and deduplicated."""
    entries: Set[str] = set()
    for page in sorted(static.glob("*.html")):
        entries |= html_entries(page)
    for script in sorted(static.glob("*.js")):
        entries |= script_entries(script)
    for stylesheet in sorted(static.glob("*.css")):
        entries |= token_entries(stylesheet)
    entries |= route_entries(SERVER_FILE)
    entries.update(f"asset {path.name}" for path in sorted(static.iterdir()) if path.is_file())
    return sorted(entries)


def main(argv: List[str]) -> int:
    """Write the inventory to stdout; exit 1 when the surface has no entries at all."""
    static = Path(argv[1]).resolve() if len(argv) > 1 else STATIC_DIR
    if not static.is_dir():
        print(f"no such cockpit directory: {static}", file=sys.stderr)
        print("Why: the inventory proof needs VoidFarer's static surface.", file=sys.stderr)
        print("Fix: run it from the project root, or pass the static directory.", file=sys.stderr)
        return 2
    entries = inventory(static)
    if not entries:
        print(f"no cockpit inventory found under {static}", file=sys.stderr)
        print("Why: an empty inventory would hide every lost control.", file=sys.stderr)
        print("Fix: check that index.html still carries ids and app.js binds handlers.",
              file=sys.stderr)
        return 1
    print("\n".join(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
