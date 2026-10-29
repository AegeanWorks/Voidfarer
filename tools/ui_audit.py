"""
Capture VoidFarer cockpit screenshots and a measurable UI audit with headless Edge or Chrome.

The real cockpit is served locally and loaded inside a same-origin wrapper that sizes an iframe
to an exact viewport. The wrapper measures geometry, clipping, contrast, tap targets, labels,
overlaps and console errors, then writes JSON and PNG evidence. This is a developer tool: it is
not a runtime dependency, not part of the shipped cockpit, and not a hard delivery gate.

Usage: python tools/ui_audit.py [--out DIR] [--viewports desktop,tablet,phone] [--browser PATH]

PRINCIPLE-003, PRINCIPLE-010, PRINCIPLE-011, PRINCIPLE-015.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / "voidfarer" / "static"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from voidfarer.engine import SimulationEngine  # noqa: E402
from voidfarer.server import VoidFarerHandler, start_background_server  # noqa: E402
from voidfarer.storage import StorageManager  # noqa: E402

AUDIT_ID = "__ui_audit__"
VIEWPORTS: Dict[str, Tuple[int, int]] = {
    "desktop": (1920, 1080),
    "ultrawide": (2560, 1080),
    "4k": (3840, 2160),
    "laptop": (1366, 768),
    "short": (1280, 720),
}
TABS = ("player", "skills", "crew", "ship", "market", "arsenal", "fleet", "contracts",
        "empire", "quests", "ai", "depot", "messages", "story", "factions", "codex")
CHROME_X = 24
CHROME_Y = 92
BROWSER_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
BROWSER_NAMES = ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser")

ERROR_COLLECTOR = (
    "<script>window.__uiAuditErrors=[];"
    "addEventListener('error',function(e){window.__uiAuditErrors.push(String(e.message||e.error));});"
    "addEventListener('unhandledrejection',function(e){window.__uiAuditErrors.push(String(e.reason));});"
    "</script>"
)

WRAPPER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VoidFarer UI audit</title>
<style>
html,body{margin:0;padding:0;width:100%;height:100%;overflow:hidden;background:#05070c;}
#stage{width:100%;height:100%;display:flex;align-items:center;justify-content:center;}
#cockpit{border:0;display:block;background:#05070c;box-shadow:0 0 0 1px #3a3020;}
#__ui_audit__{display:none;}
</style>
</head>
<body>
<div id="stage"><iframe id="cockpit" title="VoidFarer cockpit"></iframe></div>
<pre id="__ui_audit__"></pre>
<script src="/__ui_audit__.js"></script>
</body>
</html>
"""

WRAPPER_JS = r"""
(function () {
  "use strict";
  var params = new URLSearchParams(location.search);
  var viewportWidth = Number(params.get("w")) || 1920;
  var viewportHeight = Number(params.get("h")) || 1080;
  var target = params.get("target") || "/";
  var scenario = params.get("scenario") || "cockpit";
  var tab = params.get("tab") || "";
  var frame = document.getElementById("cockpit");
  var output = document.getElementById("__ui_audit__");
  var started = Date.now();
  var settled = false;

  frame.style.width = viewportWidth + "px";
  frame.style.height = viewportHeight + "px";

  function describe(element) {
    var tag = element.tagName.toLowerCase();
    var identifier = element.id ? "#" + element.id : "";
    var classes = "";
    if (typeof element.className === "string" && element.className.trim()) {
      classes = "." + element.className.trim().split(/\s+/).slice(0, 2).join(".");
    }
    return tag + identifier + classes;
  }

  function rectOf(rect) {
    return {
      left: Math.round(rect.left * 10) / 10,
      top: Math.round(rect.top * 10) / 10,
      width: Math.round(rect.width * 10) / 10,
      height: Math.round(rect.height * 10) / 10,
      right: Math.round(rect.right * 10) / 10,
      bottom: Math.round(rect.bottom * 10) / 10
    };
  }

  function colorParts(value) {
    var match = String(value).match(/rgba?\(([^)]+)\)/);
    if (!match) {
      return null;
    }
    var parts = match[1].split(",").map(function (part) {
      return parseFloat(part.trim());
    });
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  }

  function composite(top, bottom) {
    var alpha = top.a + bottom.a * (1 - top.a);
    if (alpha <= 0) {
      return { r: 0, g: 0, b: 0, a: 0 };
    }
    function mix(channel) {
      return (top[channel] * top.a + bottom[channel] * bottom.a * (1 - top.a)) / alpha;
    }
    return { r: mix("r"), g: mix("g"), b: mix("b"), a: alpha };
  }

  function backgroundOf(element, win) {
    var node = element;
    var result = null;
    while (node && node.nodeType === 1) {
      var style = win.getComputedStyle(node);
      var color = colorParts(style.backgroundColor);
      if (color && color.a > 0) {
        result = result ? composite(result, color) : color;
        if (result.a >= 0.999) {
          return result;
        }
      }
      node = node.parentElement;
    }
    var base = result || { r: 5, g: 7, b: 12, a: 1 };
    if (base.a < 0.999) {
      base = composite(base, { r: 5, g: 7, b: 12, a: 1 });
    }
    return base;
  }

  function luminance(color) {
    function channel(value) {
      var channelValue = value / 255;
      return channelValue <= 0.03928
        ? channelValue / 12.92
        : Math.pow((channelValue + 0.055) / 1.055, 2.4);
    }
    return 0.2126 * channel(color.r) + 0.7152 * channel(color.g) + 0.0722 * channel(color.b);
  }

  function contrastRatio(first, second) {
    var one = luminance(first);
    var two = luminance(second);
    return (Math.max(one, two) + 0.05) / (Math.min(one, two) + 0.05);
  }

  function visible(style, rect) {
    return style.display !== "none" && style.visibility !== "hidden"
      && parseFloat(style.opacity || "1") > 0 && rect.width > 0 && rect.height > 0;
  }

  function directText(element) {
    var index;
    for (index = 0; index < element.childNodes.length; index += 1) {
      var node = element.childNodes[index];
      if (node.nodeType === 3 && node.textContent.trim()) {
        return true;
      }
    }
    return false;
  }

  function contentOf(element) {
    return (element.innerText || element.textContent || "").replace(/\s+/g, " ").trim();
  }

  function accessibleName(element, doc) {
    var value = element.getAttribute("aria-label");
    if (value && value.trim()) {
      return value.trim();
    }
    var labelled = element.getAttribute("aria-labelledby");
    if (labelled) {
      var text = labelled.split(/\s+/).map(function (id) {
        var node = doc.getElementById(id);
        return node ? contentOf(node) : "";
      }).join(" ").trim();
      if (text) {
        return text;
      }
    }
    value = element.getAttribute("title");
    if (value && value.trim()) {
      return value.trim();
    }
    value = element.getAttribute("alt");
    if (value && value.trim()) {
      return value.trim();
    }
    var tag = element.tagName.toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") {
      if (element.value && String(element.value).trim()) {
        return String(element.value).trim();
      }
      value = element.getAttribute("placeholder");
      if (value && value.trim()) {
        return value.trim();
      }
    }
    var inner = contentOf(element);
    return inner;
  }

  function isInteractive(element, style, win) {
    var tag = element.tagName.toLowerCase();
    if (["button", "a", "input", "select", "textarea", "summary"].indexOf(tag) !== -1) {
      return true;
    }
    var role = (element.getAttribute("role") || "").toLowerCase();
    if (["button", "link", "tab", "menuitem", "menuitemradio", "option", "switch",
         "checkbox", "radio"].indexOf(role) !== -1) {
      return true;
    }
    if (element.hasAttribute("onclick")) {
      return true;
    }
    return style.cursor === "pointer" && element.tabIndex >= 0
      && element.getBoundingClientRect().width < win.innerWidth * 0.8;
  }

  function scrollAncestor(element, axis, win, doc) {
    var node = element.parentElement;
    while (node && node !== doc.body) {
      var style = win.getComputedStyle(node);
      var overflow = axis === "x" ? style.overflowX : style.overflowY;
      if (overflow === "auto" || overflow === "scroll") {
        return true;
      }
      node = node.parentElement;
    }
    return false;
  }

  function add(list, value) {
    if (list.length < 25) {
      list.push(value);
    }
  }

  function clippedByAncestor(element, win, doc) {
    var rect = element.getBoundingClientRect();
    var node = element.parentElement;
    while (node && node !== doc.body) {
      var style = win.getComputedStyle(node);
      var clips = style.overflowX === "hidden" || style.overflowX === "clip"
        || style.overflowY === "hidden" || style.overflowY === "clip"
        || style.overflowY === "auto" || style.overflowY === "scroll";
      if (clips) {
        var box = node.getBoundingClientRect();
        if (rect.bottom <= box.top || rect.top >= box.bottom
            || rect.right <= box.left || rect.left >= box.right) {
          return true;
        }
      }
      node = node.parentElement;
    }
    return false;
  }

  // A fixed layer at 50 or above (decision modal 90, main menu 5100, tooltips 20000)
  // deliberately covers the HUD, so a control under it is occluded, not colliding.
  // Comparing across such layers reported the modal as a defect on every tab.
  function overlayRoot(element, win, doc) {
    var node = element;
    while (node && node !== doc.body) {
      var style = win.getComputedStyle(node);
      if (style.position === "fixed" && parseInt(style.zIndex || "0", 10) >= 50) {
        return node;
      }
      node = node.parentElement;
    }
    return null;
  }

  function audit(win, doc) {
    var width = win.innerWidth;
    var height = win.innerHeight;
    var nodes = Array.prototype.slice.call(doc.querySelectorAll("body *"), 0, 12000);
    var report = {
      counts: { elements: nodes.length, visible: 0, interactive: 0, dom: doc.querySelectorAll("*").length },
      scroll: {},
      media: {},
      clipped: [],
      offscreen: [],
      tinyText: [],
      smallTargets: [],
      targetWarnings: [],
      unlabeled: [],
      contrast: [],
      overlaps: [],
      panels: [],
      headings: [],
      fonts: [],
      colors: [],
      errors: [],
      title: doc.title,
      cockpitReady: Boolean(win.cockpit)
    };
    var interactive = [];
    var fonts = {};
    var colors = {};
    var index;

    for (index = 0; index < nodes.length; index += 1) {
      var element = nodes[index];
      var style = win.getComputedStyle(element);
      var rect = element.getBoundingClientRect();
      if (!visible(style, rect)) {
        continue;
      }
      report.counts.visible += 1;
      var label = describe(element);
      var content = contentOf(element);
      var hasText = directText(element);

      if (hasText) {
        var fontSize = parseFloat(style.fontSize) || 0;
        var fontKey = Math.round(fontSize * 10) / 10 + "px " + style.fontFamily + " " + style.fontWeight;
        fonts[fontKey] = (fonts[fontKey] || 0) + 1;
        colors[style.color] = (colors[style.color] || 0) + 1;
        if (fontSize > 0 && fontSize < 12) {
          add(report.tinyText, { el: label, fontSize: fontSize, text: content.slice(0, 80) });
        }
        var foreground = colorParts(style.color);
        var background = backgroundOf(element, win);
        if (foreground && background) {
          var ratio = contrastRatio(composite(foreground, background), background);
          var large = fontSize >= 24 || (fontSize >= 18.66 && parseInt(style.fontWeight, 10) >= 600);
          if (ratio < (large ? 3 : 4.5)) {
            add(report.contrast, {
              el: label,
              ratio: Math.round(ratio * 100) / 100,
              fontSize: fontSize,
              color: style.color,
              background: "rgb(" + Math.round(background.r) + "," + Math.round(background.g)
                + "," + Math.round(background.b) + ")",
              text: content.slice(0, 80)
            });
          }
        }
      }

      if (content && (style.overflowX === "hidden" || style.overflowX === "clip"
          || style.overflowY === "hidden" || style.overflowY === "clip")
          && style.textOverflow !== "ellipsis"
          && (element.scrollWidth > element.clientWidth + 2
            || element.scrollHeight > element.clientHeight + 2)) {
        add(report.clipped, {
          el: label,
          client: [element.clientWidth, element.clientHeight],
          scroll: [element.scrollWidth, element.scrollHeight],
          text: content.slice(0, 80)
        });
      }

      var offscreen = rect.right > width + 1 || rect.left < -1
        || rect.bottom > height + 1 || rect.top < -1;
      var decorative = style.pointerEvents === "none"
        || /stars-layer|scanline-overlay/.test(String(element.className || ""));
      var inScrollX = scrollAncestor(element, "x", win, doc);
      var inScrollY = scrollAncestor(element, "y", win, doc);
      if (offscreen && !decorative
          && !(inScrollX && (rect.left < 0 || rect.right > width))
          && !(inScrollY && (rect.top < 0 || rect.bottom > height))) {
        add(report.offscreen, { el: label, rect: rectOf(rect), viewport: [width, height] });
      }

      if (element.id && /(bar|panel|deck|strip|terminal|radar|log|hud|menu|drawer|rail|tab)/i.test(element.id)) {
        add(report.panels, { id: element.id, rect: rectOf(rect), display: style.display });
      }

      if (isInteractive(element, style, win)) {
        report.counts.interactive += 1;
        interactive.push({ element: element, label: label, rect: rect });
        if (rect.width < 24 || rect.height < 24) {
          add(report.smallTargets, { el: label, rect: rectOf(rect), severity: "violation" });
        } else if (rect.width < 44 || rect.height < 44) {
          add(report.targetWarnings, { el: label, rect: rectOf(rect), severity: "warning" });
        }
        if (!accessibleName(element, doc)) {
          add(report.unlabeled, { el: label, html: element.outerHTML.slice(0, 140) });
        }
      }
    }

    for (var first = 0; first < interactive.length; first += 1) {
      for (var second = first + 1; second < interactive.length; second += 1) {
        var a = interactive[first];
        var b = interactive[second];
        if (a.element.contains(b.element) || b.element.contains(a.element)) {
          continue;
        }
        if (clippedByAncestor(a.element, win, doc) || clippedByAncestor(b.element, win, doc)) {
          continue;
        }
        if (overlayRoot(a.element, win, doc) !== overlayRoot(b.element, win, doc)) {
          continue;
        }
        if (a.rect.width * a.rect.height > width * height * 0.35
            || b.rect.width * b.rect.height > width * height * 0.35) {
          continue;
        }
        var overlapWidth = Math.max(0, Math.min(a.rect.right, b.rect.right)
          - Math.max(a.rect.left, b.rect.left));
        var overlapHeight = Math.max(0, Math.min(a.rect.bottom, b.rect.bottom)
          - Math.max(a.rect.top, b.rect.top));
        var area = overlapWidth * overlapHeight;
        var smaller = Math.min(a.rect.width * a.rect.height, b.rect.width * b.rect.height);
        if (area > 16 && smaller > 0 && area / smaller > 0.25) {
          add(report.overlaps, {
            a: a.label,
            b: b.label,
            area: Math.round(area),
            ratio: Math.round((area / smaller) * 100) / 100
          });
        }
      }
    }

    report.fonts = Object.keys(fonts).sort(function (left, right) {
      return fonts[right] - fonts[left];
    }).slice(0, 20).map(function (name) {
      return { name: name, count: fonts[name] };
    });
    report.colors = Object.keys(colors).sort(function (left, right) {
      return colors[right] - colors[left];
    }).slice(0, 20).map(function (name) {
      return { name: name, count: colors[name] };
    });
    report.scroll = {
      inner: [width, height],
      document: [doc.documentElement.scrollWidth, doc.documentElement.scrollHeight],
      body: [doc.body.scrollWidth, doc.body.scrollHeight],
      horizontal: doc.documentElement.scrollWidth > width + 1
    };
    report.media = {
      compact: win.matchMedia("(max-width: 1440px)").matches,
      wide: win.matchMedia("(min-width: 2300px)").matches,
      highdpi: win.matchMedia("(min-resolution: 1.5dppx)").matches,
      reduced: win.matchMedia("(prefers-reduced-motion: reduce)").matches
    };
    // G-011 asks for a DPR-correct radar: the canvas backing store must grow with
    // devicePixelRatio while its CSS box stays put. A ratio of 1 at dpr 2 means a
    // blurry map on a 200%-scaled 4K display.
    var radarCanvas = doc.getElementById("radarCanvas");
    if (radarCanvas) {
      var radarBox = radarCanvas.getBoundingClientRect();
      var deviceRatio = win.devicePixelRatio || 1;
      var cssWidth = Math.max(1, Math.round(radarBox.width));
      var expected = Math.round(cssWidth * Math.min(3, Math.max(1, deviceRatio)));
      report.radar = {
        css: [cssWidth, Math.max(1, Math.round(radarBox.height))],
        backing: [radarCanvas.width, radarCanvas.height],
        dpr: deviceRatio,
        expectedBackingWidth: expected,
        dprCorrect: Math.abs(radarCanvas.width - expected) <= 2
      };
    }
    report.headings = Array.prototype.slice.call(
      doc.querySelectorAll("h1,h2,h3,[role=heading]"), 0, 30
    ).map(function (heading) {
      return { el: describe(heading), text: contentOf(heading).slice(0, 100) };
    }).filter(function (heading) {
      return heading.text;
    });
    return report;
  }

  function finish(win, doc, fatal) {
    if (settled) {
      return;
    }
    settled = true;
    var report;
    if (fatal) {
      report = { fatal: fatal, counts: {}, errors: [] };
    } else {
      try {
        report = audit(win, doc);
      } catch (error) {
        report = { fatal: String(error && error.stack ? error.stack : error), counts: {}, errors: [] };
      }
    }
    report.viewport = {
      width: viewportWidth,
      height: viewportHeight,
      dpr: (win && win.devicePixelRatio) || 1
    };
    report.outer = { width: window.innerWidth, height: window.innerHeight };
    report.target = target;
    report.scenario = scenario;
    report.tab = tab;
    if (win && win.cockpit) {
      report.activeTab = win.cockpit.activeRightTab || null;
      var leftPanel = win.document.getElementById("panelLeft");
      report.leftPanelText = leftPanel ? (leftPanel.innerText || "").slice(0, 300) : null;
    }
    report.errors = ((win && win.__uiAuditErrors) || []).slice(0, 50);
    output.textContent = JSON.stringify(report);
  }

  function prepare(win) {
    if (!win.cockpit || win.__auditPrepared) {
      return;
    }
    if (scenario === "menu") {
      return;
    }
    win.__auditPrepared = true;
    win.cockpit.gameStarted = true;
    win.cockpit.closeMainMenu();
    if (win.cockpit.fetchGalaxy) {
      win.cockpit.fetchGalaxy();
    }
    if (win.cockpit.refreshState) {
      win.cockpit.refreshState(true);
    }
    setTimeout(function () {
      if (scenario === "settings" && win.cockpit.openSettings) {
        win.cockpit.openSettings();
      } else if (scenario === "character" && win.cockpit.openCharacterCreation) {
        win.cockpit.openCharacterCreation();
      } else if (scenario === "target" && win.cockpit.state) {
        var bodies = (win.cockpit.state.current_system && win.cockpit.state.current_system.bodies) || [];
        var body = null;
        for (var index = 0; index < bodies.length; index += 1) {
          if (bodies[index].body_type !== "star") {
            body = bodies[index];
            break;
          }
        }
        body = body || bodies[0];
        if (body) {
          win.cockpit.selectedTarget = body;
          win.cockpit.selectedType = "body";
          win.cockpit.updateTargetCard();
        }
      } else if (scenario === "event" && win.cockpit.state) {
        win.cockpit.state.undismissed_events = [
          { id: "audit-signal", kind: "exploration", tick: 0, title: "Anomalous Signal Detected", message: "A harmonic pulse repeats beneath the quantum noise in the outer system." },
          { id: "audit-contract", kind: "trade", tick: 0, title: "Commodity Contract Fulfilled", message: "Sol Logistics confirms the titanium delivery. Payment is ready at the exchange." }
        ];
        win.cockpit.renderEventPopups();
      } else if (scenario === "combat") {
        var combat = win.document.getElementById("combatCard");
        if (combat) combat.style.display = "flex";
      }
      if (tab && tab !== "player" && win.cockpit.switchRightTab) {
        try {
          win.cockpit.switchRightTab(tab);
        } catch (error) {
          win.__uiAuditErrors = win.__uiAuditErrors || [];
          win.__uiAuditErrors.push("tab switch failed: " + String(error));
        }
      }
    }, 700);
  }

  function waitForCockpit() {
    var win = frame.contentWindow;
    var doc = frame.contentDocument;
    if (win && doc && win.cockpit && doc.readyState === "complete") {
      prepare(win);
      setTimeout(function () {
        finish(win, doc, null);
      }, 2200);
      return;
    }
    if (Date.now() - started > 12000) {
      finish(win, doc, "cockpit did not become ready within 12s");
      return;
    }
    setTimeout(waitForCockpit, 100);
  }

  frame.addEventListener("load", function () {
    var win = frame.contentWindow;
    if (win) {
      win.__uiAuditErrors = win.__uiAuditErrors || [];
      win.addEventListener("error", function (event) {
        win.__uiAuditErrors.push(String(event.message || event.error));
      });
      win.addEventListener("unhandledrejection", function (event) {
        win.__uiAuditErrors.push(String(event.reason));
      });
    }
    setTimeout(waitForCockpit, 100);
  });
  frame.src = target;
  setTimeout(waitForCockpit, 100);
})();
"""


def find_browser() -> Optional[Path]:
    """Locate an installed Edge or Chrome executable without a third-party dependency."""
    override = os.environ.get("VOIDFARER_BROWSER")
    if override and Path(override).is_file():
        return Path(override)
    for candidate in BROWSER_CANDIDATES:
        path = Path(candidate)
        if path.is_file():
            return path
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def outer_window(viewport: Tuple[int, int]) -> Tuple[int, int]:
    """Outer window size that yields the requested inner viewport for Windows desktop sizes."""
    width, height = viewport
    return (width + CHROME_X, height + CHROME_Y)


def prepare_static(source: Path, workdir: Path) -> Path:
    """Copy the cockpit and add a same-origin viewport wrapper plus an error collector."""
    target = workdir / "static"
    shutil.copytree(source, target)
    index = target / "index.html"
    page = index.read_text(encoding="utf-8")
    if "</head>" not in page:
        raise ValueError("Why: index.html has no </head>; the audit cannot install an error collector. "
                         "Fix: restore the cockpit page head and rerun.")
    index.write_text(page.replace("</head>", ERROR_COLLECTOR + "</head>", 1), encoding="utf-8")
    (target / "__ui_audit__.html").write_text(WRAPPER_HTML, encoding="utf-8")
    (target / "__ui_audit__.js").write_text(WRAPPER_JS, encoding="utf-8")
    return target


def parse_audit(dom: str) -> Dict[str, Any]:
    """Read the JSON audit payload out of a dumped wrapper DOM."""
    match = re.search(
        r'<pre id="' + re.escape(AUDIT_ID) + r'"[^>]*>(.*?)</pre>', dom, re.DOTALL)
    if not match:
        raise ValueError("Why: the audit page produced no report; the cockpit or wrapper failed. "
                         "Fix: inspect the dumped DOM and browser stderr, then rerun.")
    payload = html.unescape(match.group(1)).strip()
    if not payload:
        raise ValueError("Why: the audit report was empty. Fix: rerun with a longer browser timeout.")
    return json.loads(payload)


def browser_command(browser: Path, viewport: Tuple[int, int], profile: Path,
                    screenshot: Path, url: str, dpr: float = 1) -> List[str]:
    """Headless Edge/Chrome argument list for one capture at a device scale factor.

    Windows scaling is what makes the radar DPR path run: a 4K display at 200% reports
    a 1920x1080 CSS viewport with devicePixelRatio 2, so `--dpr 2` reproduces it.
    """
    outer_width, outer_height = outer_window(viewport)
    return [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        f"--force-device-scale-factor={dpr:g}",
        f"--user-data-dir={profile}",
        f"--window-size={outer_width},{outer_height}",
        "--virtual-time-budget=15000",
        "--run-all-compositor-stages-before-draw",
        f"--screenshot={screenshot}",
        "--dump-dom",
        url,
    ]


def run_browser(browser: Path, url: str, viewport: Tuple[int, int], profile: Path,
                screenshot: Path, timeout: int, dpr: float = 1) -> Tuple[str, str, int]:
    """Run one headless capture at a viewport and return stdout, stderr and the exit code."""
    command = browser_command(browser, viewport, profile, screenshot, url, dpr)
    result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )
    return (result.stdout, result.stderr, result.returncode)


def audit_viewport(browser: Path, port: int, name: str, viewport: Tuple[int, int],
                   workdir: Path, out: Path, timeout: int, scenario: str,
                   tab: str = "", dpr: float = 1) -> Dict[str, Any]:
    """Capture one viewport and return its parsed audit report."""
    width, height = viewport
    label = f"{name}-{tab}" if tab else name
    if dpr != 1:
        label = f"{label}@{dpr:g}x"
    url = (f"http://127.0.0.1:{port}/__ui_audit__.html?w={width}&h={height}"
           f"&target=/&scenario={scenario}")
    if tab:
        url += f"&tab={tab}"
    profile = workdir / f"profile-{label}"
    screenshot = out / f"{label}.png"
    stdout, stderr, code = run_browser(browser, url, viewport, profile, screenshot,
                                       timeout, dpr)
    if code != 0:
        (out / f"{label}-browser.txt").write_text(stderr[-4000:], encoding="utf-8")
    try:
        report = parse_audit(stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        (out / f"{label}-dom.html").write_text(stdout, encoding="utf-8")
        (out / f"{label}-stderr.txt").write_text(stderr[-4000:], encoding="utf-8")
        raise RuntimeError(f"{label}: {exc}") from exc
    report["name"] = label
    report["screenshot"] = screenshot.name
    report["dpr"] = dpr
    return report


def summary_line(report: Dict[str, Any]) -> str:
    """One ASCII-safe console line for a viewport report."""
    viewport = report.get("viewport") or {}
    counts = (
        ("errors", len(report.get("errors") or [])),
        ("hscroll", int(bool((report.get("scroll") or {}).get("horizontal")))),
        ("clipped", len(report.get("clipped") or [])),
        ("offscreen", len(report.get("offscreen") or [])),
        ("tiny", len(report.get("tinyText") or [])),
        ("targets", len(report.get("smallTargets") or [])),
        ("contrast", len(report.get("contrast") or [])),
        ("unlabeled", len(report.get("unlabeled") or [])),
        ("overlaps", len(report.get("overlaps") or [])),
    )
    body = " ".join(f"{name} {value}" for name, value in counts)
    radar = report.get("radar") or {}
    if radar:
        body += f" radar {'ok' if radar.get('dprCorrect') else 'BLURRY'}"
    return f"{report.get('name', 'unknown'):10} {viewport.get('width', 0)}x{viewport.get('height', 0)}: {body}"


def severe_findings(report: Dict[str, Any]) -> List[str]:
    """Names of findings that should fail an explicit audit check."""
    names: List[str] = []
    if report.get("fatal"):
        names.append("fatal")
    if report.get("errors"):
        names.append("console")
    if (report.get("scroll") or {}).get("horizontal"):
        names.append("hscroll")
    for key in ("clipped", "tinyText", "smallTargets", "contrast", "unlabeled"):
        if report.get(key):
            names.append(key)
    radar = report.get("radar") or {}
    if radar and not radar.get("dprCorrect", True):
        names.append("radarDpr")
    return names


def write_report(reports: Sequence[Dict[str, Any]], out: Path, browser: Optional[Path]) -> Path:
    """Write the combined JSON and Markdown evidence packet."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "browser": str(browser) if browser else None,
        "dpr": reports[0].get("dpr", 1) if reports else 1,
        "viewports": list(reports),
    }
    (out / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = ["# VoidFarer UI audit", "", f"Generated: {payload['generated_at']}", ""]
    lines.append("| Viewport | Size | Errors | H-scroll | Clipped | Offscreen | Tiny<12px | Targets<24 | Contrast | Unlabeled | Overlaps |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for report in reports:
        viewport = report.get("viewport") or {}
        lines.append(
            f"| {report.get('name', '?')} | {viewport.get('width', 0)}x{viewport.get('height', 0)} "
            f"| {len(report.get('errors') or [])} "
            f"| {int(bool((report.get('scroll') or {}).get('horizontal')))} "
            f"| {len(report.get('clipped') or [])} "
            f"| {len(report.get('offscreen') or [])} "
            f"| {len(report.get('tinyText') or [])} "
            f"| {len(report.get('smallTargets') or [])} "
            f"| {len(report.get('contrast') or [])} "
            f"| {len(report.get('unlabeled') or [])} "
            f"| {len(report.get('overlaps') or [])} |")
    for report in reports:
        lines.extend(["", f"## {report.get('name', '?')}", ""])
        radar = report.get("radar")
        if radar:
            lines.append(
                f"- radar canvas: CSS {radar['css'][0]}x{radar['css'][1]} px, backing store "
                f"{radar['backing'][0]}x{radar['backing'][1]} px at dpr {radar['dpr']:g} "
                f"({'DPR-correct' if radar.get('dprCorrect') else 'BLURRY: backing store did not scale'})")
            lines.append("")
        for key in ("tinyText", "contrast", "smallTargets", "unlabeled", "clipped", "offscreen", "overlaps"):
            findings = report.get(key) or []
            if not findings:
                continue
            lines.append(f"### {key} ({len(findings)})")
            for finding in findings[:12]:
                lines.append(f"- `{finding}`")
            lines.append("")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out / "report.md"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the audit, write screenshots plus JSON/Markdown, and print a concise summary."""
    parser = argparse.ArgumentParser(description="Headless VoidFarer cockpit UI audit")
    parser.add_argument("--out", default=str(Path(tempfile.gettempdir()) / "voidfarer_ui_audit"),
                        help="directory for screenshots and reports")
    parser.add_argument("--viewports", default="desktop,laptop,short",
                        help="comma-separated Windows desktop viewport names")
    parser.add_argument("--browser", default=None, help="edge/chrome executable path")
    parser.add_argument("--scenario", default="cockpit",
                        choices=("cockpit", "menu", "settings", "character", "target", "event", "combat"),
                        help="cockpit resumes the game; menu/settings/character/target/event/combat audit those states")
    parser.add_argument("--tab", default="", choices=("",) + TABS,
                        help="open an in-game terminal tab before auditing")
    parser.add_argument("--timeout", type=int, default=120, help="seconds per viewport")
    parser.add_argument("--dpr", type=float, default=1.0,
                        help="device pixel ratio to emulate Windows display scaling "
                             "(1.5 = 150%%, 2 = 200%%); default 1. The per-viewport "
                             "timeout scales with dpr squared because raster cost does")
    parser.add_argument("--check", action="store_true", help="exit 1 when severe findings exist")
    args = parser.parse_args(argv)

    names = [name.strip() for name in args.viewports.split(",") if name.strip()]
    unknown = [name for name in names if name not in VIEWPORTS]
    if unknown:
        print(f"Why: unknown viewport(s): {', '.join(unknown)}.")
        print(f"Fix: choose from {', '.join(VIEWPORTS)}.")
        return 2
    if not 1 <= args.dpr <= 3:
        print(f"Why: --dpr {args.dpr:g} is outside the Windows scaling range this tool emulates.")
        print("Fix: pass --dpr 1, 1.25, 1.5 or 2 (100% to 200% scaling).")
        return 2
    browser = Path(args.browser) if args.browser else find_browser()
    if browser is None or not browser.is_file():
        print("Why: no Edge or Chrome executable was found for the headless visual audit.")
        print("Fix: install Edge/Chrome or pass --browser <path>.")
        return 2

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="voidfarer_ui_audit_"))
    handle = None
    reports: List[Dict[str, Any]] = []
    try:
        static = prepare_static(STATIC_DIR, workdir)
        storage = StorageManager(workdir / "save")
        engine = SimulationEngine(state=storage.load())
        handle = start_background_server(engine, storage, port=0)
        if handle is None:
            print("Why: the cockpit server could not bind a local port.")
            print("Fix: stop the process holding the port or retry.")
            return 1
        VoidFarerHandler.static_dir = static
        # A 2x capture rasters four times the pixels and settles the same animated
        # radar for the same virtual time; a measured 1080p@2x pass takes ~350 s, so
        # scaling by dpr squared alone would sit right on the limit.
        timeout = max(1, int(round(args.timeout * max(1.0, 2.0 * args.dpr * args.dpr))))
        if args.dpr != 1:
            print(f"Scaling {args.dpr:g}x: {timeout}s per viewport "
                  f"(a 2x 1080p capture measured ~350s)")
        for name in names:
            viewport = VIEWPORTS[name]
            try:
                report = audit_viewport(browser, handle.port, name, viewport, workdir, out,
                                        timeout, args.scenario, args.tab, args.dpr)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                print(f"[FAIL] {name}: {exc}")
                continue
            reports.append(report)
            print(summary_line(report))
        if not reports:
            print("Why: no viewport produced an audit report.")
            print("Fix: inspect the saved browser/dom files and rerun.")
            return 1
        report_path = write_report(reports, out, browser)
        print(f"Report: {report_path}")
        print(f"Screenshots: {out}")
        if args.check:
            failures = [(report.get("name", "?"), severe_findings(report)) for report in reports]
            failures = [(name, findings) for name, findings in failures if findings]
            if failures:
                for name, findings in failures:
                    print(f"[CHECK] {name}: {', '.join(findings)}")
                return 1
        return 0
    finally:
        if handle is not None:
            handle.stop()
        VoidFarerHandler.static_dir = STATIC_DIR
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
