"""Layout regression tests for the holographic web cockpit (index.html / style.css / app.js).

Pins the cockpit layout rules (project guidelines G-001..G-003, G-013):
  1. The bottom command strip holds reactor distribution on the left, skills in
     the middle, and radar settings above the Tactical Flight Log on the right, in
     one row, each with an icon and a hotkey. The log keeps a HIDE/SHOW button.
  2. The Chrono tick/time settings deck sits at the right upper corner, as the last
     block of the top status bar.
  3. The Commerce/Arsenal/Fleet terminal runs vertically (up to down) on the left
     side: a vertical tab rail with the active tab's content beside it.
The radar remains the center-column map; the right strip column keeps a separate radar
settings panel above the flight log.
"""

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

STATIC_DIR = Path(__file__).parent.parent / "voidfarer" / "static"
INDEX_HTML = STATIC_DIR / "index.html"
STYLE_CSS = STATIC_DIR / "style.css"
APP_JS = STATIC_DIR / "app.js"

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

TAB_BUTTON_IDS = (
    "tabBtnMarket",
    "tabBtnArsenal",
    "tabBtnFleet",
    "tabBtnContracts",
    "tabBtnStory",
    "tabBtnFactions",
)

TAB_CONTENT_IDS = (
    "tabContentMarket",
    "tabContentArsenal",
    "tabContentFleet",
    "tabContentContracts",
    "tabContentStory",
    "tabContentFactions",
)


class _DomNode:
    """Minimal element tree node built from html.parser events."""

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []
        self.parent = None

    def find_by_id(self, element_id):
        if self.attrs.get("id") == element_id:
            return self
        for child in self.children:
            found = child.find_by_id(element_id)
            if found is not None:
                return found
        return None

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _DomNode("document", {})
        self.stack = [self.root]

    def _append(self, tag, attrs, closing):
        node = _DomNode(tag, attrs)
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        if not closing and tag not in VOID_ELEMENTS:
            self.stack.append(node)

    def handle_starttag(self, tag, attrs):
        self._append(tag, attrs, closing=False)

    def handle_startendtag(self, tag, attrs):
        self._append(tag, attrs, closing=True)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


class TestCockpitLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parser = _TreeBuilder()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        parser.close()
        cls.dom = parser.root
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def _rule_body(self, selector):
        match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", self.css)
        self.assertIsNotNone(match, f"missing CSS rule for {selector}")
        return match.group(1)

    def _ancestor_ids(self, node):
        return [ancestor.attrs.get("id") for ancestor in node.ancestors()]

    def _document_order(self):
        order = []

        def walk(node):
            node_id = node.attrs.get("id")
            if node_id:
                order.append(node_id)
            for child in node.children:
                walk(child)

        walk(self.dom)
        return order

    # --- Rule 1: telemetry log on the right of the top command strip, with a hide button ---

    def test_telemetry_log_sits_in_the_right_of_the_bottom_command_strip(self):
        log_panel = self.dom.find_by_id("logPanel")
        self.assertIsNotNone(log_panel, "telemetry log panel (#logPanel) missing from index.html")
        self.assertTrue(log_panel.has_class("log-panel"))
        self.assertIn("hudCommandStrip", self._ancestor_ids(log_panel),
                      "telemetry log must live in the bottom command strip")
        self.assertIn("hudStripRight", self._ancestor_ids(log_panel),
                      "telemetry log must sit in the right strip column")
        self.assertIsNone(log_panel.find_by_id("mapControlsPanel"),
                          "radar settings must not be nested inside the log panel")
        self.assertIsNotNone(log_panel.find_by_id("flightLogStream"),
                             "flight log stream must be inside the log panel")

    def test_command_strip_holds_combined_power_panel_and_right_column(self):
        strip = self.dom.find_by_id("hudCommandStrip")
        self.assertIsNotNone(strip, "command strip (#hudCommandStrip) missing")
        child_ids = [child.attrs.get("id") for child in strip.children]
        self.assertEqual(
            child_ids,
            ["panelReactor", "hudStripRight"],
            "strip order must be the combined power panel, then the radar/log column",
        )
        reactor = self.dom.find_by_id("panelReactor")
        self.assertIsNotNone(reactor.find_by_id("hudSkillsPanel"),
                             "abilities must live inside the combined power panel")
        self.assertRegex(
            self.css,
            r"\.hud-command-strip\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*2\.15fr\)\s*minmax\(280px,\s*1fr\)",
            "the combined power panel must take the wide column and radar/log the narrow column",
        )
        self.assertRegex(
            self.css,
            r"\.power-abilities-body\s*\{[^}]*grid-template-columns:\s*minmax\(0,\s*1\.18fr\)\s*minmax\(0,\s*0\.92fr\)",
            "reactor routing and abilities must share one two-section body",
        )
        self.assertRegex(
            self.css,
            r"\.hud-command-strip\s*\{[^}]*grid-row:\s*2",
            "the command strip must occupy the bottom grid row",
        )

    def test_source_order_keeps_the_strip_after_the_cockpit(self):
        order = self._document_order()
        self.assertLess(order.index("panelLeft"), order.index("panelCenter"))
        self.assertLess(order.index("panelCenter"), order.index("hudCommandStrip"),
                        "the strip must follow the cockpit in DOM order for accessibility")

    def test_radar_settings_sit_above_the_flight_log_but_are_separate(self):
        right = self.dom.find_by_id("hudStripRight")
        self.assertIsNotNone(right)
        child_ids = [child.attrs.get("id") for child in right.children]
        self.assertEqual(child_ids, ["mapControlsPanel", "logPanel"])
        self.assertIsNone(self.dom.find_by_id("panelRight"),
                          "the old right deck must be removed")

    def test_radar_zoom_controls_are_vertical_with_center_in_middle(self):
        zoom = [child.attrs.get("id") for child in self.dom.find_by_id("mapControlsPanel")
                .find_by_id("btnZoomIn").parent.children]
        self.assertEqual(zoom, ["btnZoomIn", "btnResetView", "btnZoomOut"])
        self.assertRegex(
            self.css,
            r"\.radar-zoom-stack\s*\{[^}]*flex-direction:\s*column",
            "the circular zoom controls must stack vertically",
        )
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn(">+</button>", html)
        self.assertIn(">−</button>", html)
        self.assertNotIn("MOVE CLOSER", html)
        self.assertNotIn("MOVE OUTSIDE", html)
        self.assertRegex(
            self.css,
            r"\.radar-zoom-btn\s*\{[^}]*border-radius:\s*50%",
            "zoom buttons must be circular",
        )
        for button_id in ("btnZoomIn", "btnResetView", "btnZoomOut"):
            with self.subTest(button_id=button_id):
                self.assertIn(f'getElementById("{button_id}").addEventListener', self.js)

    def test_telemetry_log_carries_a_hide_button(self):
        log_panel = self.dom.find_by_id("logPanel")
        self.assertIsNotNone(log_panel)
        toggle = log_panel.find_by_id("btnToggleLog")
        self.assertIsNotNone(toggle, "telemetry log must carry a HIDE/SHOW button")

    def test_log_collapse_style_and_toggle_wiring_exist(self):
        self.assertRegex(self.css, r"\.log-panel\.log-collapsed[^{]*\{[^}]*display:\s*none")
        self.assertIn("btnToggleLog", self.js, "app.js must bind the log HIDE/SHOW button")
        self.assertIn("log-collapsed", self.js, "app.js must toggle the collapsed log class")

    # --- Rule 2: chrono deck pinned to the right upper corner ---

    def test_chrono_deck_is_the_last_block_of_the_top_bar(self):
        topbar = self.dom.find_by_id("hudTopBar")
        self.assertIsNotNone(topbar)
        self.assertTrue(topbar.children, "top bar must have content")
        last_child = topbar.children[-1]
        self.assertEqual(last_child.attrs.get("id"), "hudTimeDeck",
                         "the chrono/tick deck must sit at the far right of the top bar")
        self.assertTrue(last_child.has_class("hud-time-deck"))

    def test_chrono_deck_is_pushed_to_the_right_edge(self):
        deck_rule = self._rule_body(".hud-time-deck")
        self.assertIn("margin-left", deck_rule)
        self.assertIn("auto", deck_rule,
                      "the chrono deck must be pushed to the right edge of the top bar")

    # --- Rule 3: vertical Commerce/Arsenal/Fleet terminal on the left ---

    def test_terminal_lives_in_the_left_deck(self):
        left_deck = self.dom.find_by_id("panelLeft")
        self.assertIsNotNone(left_deck, "left terminal deck (#panelLeft) missing from index.html")
        self.assertTrue(left_deck.has_class("panel-left"))

        for tab_id in TAB_BUTTON_IDS:
            button = self.dom.find_by_id(tab_id)
            self.assertIsNotNone(button, f"missing tab button #{tab_id}")
            self.assertIn("panelLeft", self._ancestor_ids(button),
                          f"#{tab_id} must sit in the left terminal deck")

        for content_id in TAB_CONTENT_IDS:
            content = self.dom.find_by_id(content_id)
            self.assertIsNotNone(content, f"missing tab content #{content_id}")
            self.assertIn("panelLeft", self._ancestor_ids(content),
                          f"#{content_id} must sit in the left terminal deck")

    def test_terminal_uses_a_vertical_rail_beside_the_content(self):
        deck_rule = self._rule_body(".panel-left")
        self.assertIn("grid", deck_rule, "the left deck must lay the rail out beside the content")

        rail_rule = self._rule_body(".panel-left .deck-tabs-header")
        self.assertIn("column", rail_rule, "the tab rail must run vertically (up to down)")

    # --- Center column: radar map; reactor moved to the top command strip ---

    def test_center_column_keeps_radar_and_reactor_moves_to_bottom_strip(self):
        radar = self.dom.find_by_id("panelNav")
        reactor = self.dom.find_by_id("panelReactor")
        self.assertIn("panelCenter", self._ancestor_ids(radar),
                      "the radar must live in the center column")
        self.assertIn("hudCommandStrip", self._ancestor_ids(reactor),
                      "the reactor must live in the bottom command strip")
        self.assertRegex(
            self.css,
            r"\.panel-left\s*\{[^}]*grid-row:\s*1\s*/\s*span\s*2",
            "the left deck must span both rows so the strip starts beside it",
        )

    def test_context_alerts_live_in_the_center_column(self):
        for alert_id in ("combatCard", "anomalyCard"):
            alert = self.dom.find_by_id(alert_id)
            self.assertIsNotNone(alert, f"missing alert card #{alert_id}")
            self.assertIn("panelCenter", self._ancestor_ids(alert),
                          f"#{alert_id} must live in the center column")


if __name__ == "__main__":
    unittest.main()

class TestCockpitRuntimeContracts(unittest.TestCase):
    """Static regression checks for runtime wiring that the DOM structure cannot exercise."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_pointer_coordinates_are_scaled_to_canvas_space(self):
        self.assertIn("pointerToCanvas(e)", self.js)
        self.assertIn("this.pointerToCanvas(e)", self.js)
        self.assertIn("this.canvas.width / Math.max(1, rect.width)", self.js)

    def test_drag_suppresses_the_following_click(self):
        self.assertIn("this.suppressClick", self.js)
        self.assertIn("this.dragMoved", self.js)

    def test_preload_renderers_guard_against_missing_state(self):
        for method in ("renderMarketTable", "renderArsenal", "renderFleet", "renderContracts", "renderTalentBranches", "renderRelics", "renderFactions", "drawGalaxyView", "updateTargetCard"):
            self.assertRegex(
                self.js,
                rf"{method}\([^)]*\) \{{\s*if \(!this\.state\) return;",
                f"{method} must return before dereferencing state",
            )

    def test_power_sliders_sync_from_authoritative_state(self):
        self.assertIn("syncPowerSlidersFromState()", self.js)
        self.assertIn("this.powerDirty", self.js)
        self.assertIn("this.syncPowerSlidersFromState();", self.js)

    def test_cargo_meter_uses_manifest_volume(self):
        self.assertIn("this.state.inventory_manifest", self.js)
        self.assertIn("item.total_volume", self.js)

    def test_scan_sound_reads_discovery_contract(self):
        self.assertIn("const discovery = json.discovery || {};", self.js)
        self.assertIn("discovery.relic", self.js)
        self.assertIn("discovery.near_miss", self.js)

    def test_canvas_uses_literal_colors_not_css_variables(self):
        self.assertNotRegex(self.js, r"ctx\.(?:strokeStyle|fillStyle) = \"var\(--neon")
        self.assertIn('ctx.strokeStyle = "#7fb7c9"', self.js)
        self.assertIn('ctx.fillStyle = "#8fbf9f"', self.js)

    def test_chrono_displays_calendar_date(self):
        self.assertIn("DATE ${t.date", self.js)
        self.assertIn("DATE 01.01.3042", INDEX_HTML.read_text(encoding="utf-8"))

class TestFrontierCockpitUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_main_menu_and_windows_exist(self):
        for marker in ("mainMenuOverlay", "settingsOverlay", "btnMenuSave", "btnMenuLoad", "btnMenuDelete", "btnMenuNew"):
            self.assertIn(f'id="{marker}"', self.html)
        for marker in ("skillsPerksBranches", "skillsTalentPoints", "relicsGrid"):
            self.assertIn(f'id="{marker}"', self.html)
        self.assertNotIn('id="perksOverlay"', self.html,
                         "pilot perks must be inline in the Skills tab, not a duplicate overlay")
        self.assertNotIn('id="btnOpenPerks"', self.html,
                         "pilot perks must not have a top-bar shortcut duplicating the Skills tab")

    def test_frontier_tabs_and_radar_overlay_exist(self):
        for marker in ("tabBtnQuests", "tabBtnAI", "tabBtnDepot", "tabBtnMessages", "viewOrbitBtn", "viewGalaxyBtn", "btnToggleGrid", "btnToggleLabels", "btnLandTarget", "targetGravity", "quickScanBtn"):
            self.assertIn(f'id="{marker}"', self.html)

    def test_frontier_renderers_are_wired(self):
        for method in ("renderQuests", "renderAICaptains", "renderDepots", "renderMessages", "renderSkillsPerks", "renderTalentBranches", "renderRelics", "handleUnlockPerk", "startTravelAnimation", "menuAction", "handleLandAction"):
            self.assertIn(method, self.js)

    def test_esc_key_toggles_main_menu(self):
        self.assertIn("Escape", self.js)
        self.assertIn("toggleMainMenu", self.js)
        self.assertIn("ESC", self.html)

    def test_menu_resume_closes_without_reload(self):
        at = self.js.find("btnMenuResume")
        self.assertGreaterEqual(at, 0)
        end = self.js.find("});", at)
        self.assertGreater(end, at)
        block = self.js[at:end]
        self.assertIn("closeMainMenu", block)
        self.assertNotIn("/api/load", block)

    def test_multiple_save_slots_ui_exists(self):
        for marker in ("saveSlotInput", "saveSlotsList"):
            self.assertIn(f'id="{marker}"', self.html)
        for method in ("fetchSaves", "renderSaveSlots", "/api/saves"):
            self.assertIn(method, self.js)

    def test_nav_radar_orbital_map_is_full_viewport_background(self):
        self.assertRegex(
            self.css,
            r"\.canvas-radar-container\.radar-background-layer\s*\{[^}]*position:\s*fixed[^}]*inset:\s*0[^}]*width:\s*100vw[^}]*height:\s*100vh[^}]*z-index:\s*0",
        )
        self.assertIn("radar-background-layer", self.html)
        self.assertRegex(
            self.css,
            r"\.panel-center\s*\{[^}]*backdrop-filter:\s*none[^}]*pointer-events:\s*none",
        )
        self.assertIn("resizeRadarCanvas", self.js)

    def test_radar_background_is_black(self):
        self.assertIn(".canvas-radar-container { background: #000; }", self.css)

class TestCockpitEscaping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_dynamic_server_data_is_escaped(self):
        for marker in (
            "this.escapeHtml(q.name)",
            "this.escapeHtml(u.name)",
            "this.escapeHtml(c.title)",
            "this.escapeHtml(t.name)",
            "this.escapeHtml(r.name)",
            "this.escapeHtml(tx.message)",
            "this.escapeHtml(f.name)",
            "this.escapeHtml(c.name)",
        ):
            self.assertIn(marker, self.js)

    def test_faction_colors_are_whitelisted(self):
        self.assertIn("safeColor(value", self.js)
        self.assertIn("this.safeColor(f.primary_color)", self.js)

class TestSleekHUDDeclutter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_nav_radar_header_is_transparent_on_map_label(self):
        self.assertRegex(
            self.css,
            r"\.nav-panel\s*>\s*\.panel-header\s*\{[^}]*background:\s*transparent[^}]*border:\s*none[^}]*backdrop-filter:\s*none[^}]*pointer-events:\s*none",
            "NAV-radar header must float transparently on the map without a bulky box",
        )

    def test_grid_and_label_buttons_are_bound_exactly_once(self):
        self.assertEqual(self.js.count('this.btnToggleGrid.addEventListener("click"'), 1,
                         "GRID must toggle once per click, not twice")
        self.assertEqual(self.js.count('this.btnToggleLabels.addEventListener("click"'), 1,
                         "LABELS must toggle once per click, not twice")

    def test_quick_scan_is_bound_exactly_once(self):
        self.assertEqual(
            self.js.count('this.quickScanBtn.addEventListener("click"'),
            1,
            "a single sensor-scan click must dispatch exactly one scan action",
        )

    def test_left_terminal_is_collapsible_drawer(self):
        self.assertRegex(
            self.css,
            r"\.panel-left\.drawer-collapsed\s*\.terminal-content-stack\s*\{[^}]*display:\s*none",
            "terminal content stack must be hidden when left drawer is collapsed",
        )
        # Panel starts expanded by default (no drawer-collapsed class), but supports collapsing
        self.assertIn('class="deck-panel panel-left"', self.html)
        self.assertIn("drawer-collapsed", self.js)
        self.assertIn("this.panelLeft", self.js)

    def test_bottom_strip_log_is_compact_and_keeps_its_controls(self):
        self.assertRegex(
            self.css,
            r"\.hud-command-strip\s+\.flight-log-stream\s*\{[^}]*height:\s*96px",
            "the strip flight log must use the reduced 96px height",
        )
        self.assertIn("btnToggleLog", self.js)
        self.assertIn("clearLogBtn", self.js)

    def test_ability_strip_has_icons_hotkeys_and_use_wiring(self):
        self.assertIn('id="hudSkillsPanel"', self.html)
        self.assertIn('id="hudSkillsGrid"', self.html)
        self.assertIn("renderSkillsQuickPanel", self.js)
        self.assertIn("useAbilityQuick", self.js)
        self.assertIn("ABILITY_ORDER", self.js)
        self.assertIn("ABILITY_META", self.js)
        self.assertIn("SKILL_HOTKEYS", self.js)
        self.assertIn("data-train-skill", self.js)
        self.assertIn("TRAIN 1 SP", self.js)
        self.assertIn("reportProblem", self.js)
        self.assertIn("deathAcknowledged", self.js)
        self.assertIn('role="status" aria-live="polite"', self.html)
        self.assertNotIn("Spend points with SHIFT+1..6", self.html)
        self.assertIn("SHIFT+1..6 // K HIDE // TRAIN", self.html)
        self.assertNotIn('id="hudSkillsPoints"', self.html)
        self.assertNotIn('id="characterSkills"', self.html,
                         "the PLAYER tab must no longer own a skills summary")

    def test_reactor_mode_and_vent_buttons_are_wired(self):
        self.assertIn('querySelectorAll(".reactor-mode-btn")', self.js)
        self.assertIn('addEventListener("click", () => this.handleReactorMode', self.js)
        self.assertIn('addEventListener("click", () => this.handleReactorVent', self.js)

    def test_cockpit_uses_themed_cursor_assets(self):
        for name in ("cursor-default.svg", "cursor-pointer.svg", "cursor-crosshair.svg"):
            with self.subTest(asset=name):
                self.assertTrue((STATIC_DIR / name).exists(), f"missing themed cursor {name}")
        self.assertIn('url("cursor-default.svg")', self.css)
        self.assertIn('url("cursor-pointer.svg")', self.css)
        self.assertIn('url("cursor-crosshair.svg")', self.css)

    def test_command_strip_hotkeys_are_wired(self):
        for token in ('hotkey === "p"', 'hotkey === "k"', 'hotkey === "l"',
                      'e.shiftKey && /^Digit[1-6]$/', 'KeyQ', 'KeyW', 'KeyE', 'KeyR'):
            with self.subTest(token=token):
                self.assertIn(token, self.js)
        self.assertIn('this.btnToggleSkills.addEventListener', self.js)
        self.assertIn('id="btnToggleSkills"', INDEX_HTML.read_text(encoding="utf-8"))

class TestExpandableReactorAndVitalsAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        parser = _TreeBuilder()
        parser.feed(cls.html)
        parser.close()
        cls.dom = parser.root

    def test_reactor_panel_has_toggle_button_and_collapse_wiring(self):
        reactor = self.dom.find_by_id("panelReactor")
        self.assertIsNotNone(reactor, "reactor sub-panel (#panelReactor) missing")
        self.assertLess(self.html.index('id="hudCommandStrip"'), self.html.index('id="panelReactor"'),
                        "the reactor must live in the top command strip")
        toggle = reactor.find_by_id("btnToggleReactor")
        self.assertIsNotNone(toggle, "reactor must have a HIDE/SHOW button (#btnToggleReactor)")
        self.assertRegex(
            self.css,
            r"\.reactor-panel\.reactor-collapsed\s*\.power-matrix[^{]*\{[^}]*display:\s*none",
            "reactor power matrix must be hidden when reactor is collapsed",
        )
        self.assertIn("btnToggleReactor", self.js, "app.js must bind the reactor toggle button")
        self.assertIn("reactor-collapsed", self.js, "app.js must toggle reactor-collapsed class")

    def test_topbar_actions_line_appears_before_vitals_row(self):
        topbar = self.dom.find_by_id("hudTopBar")
        self.assertIsNotNone(topbar)
        classes = [child.attrs.get("class", "") for child in topbar.children]
        actions_idx = next((i for i, c in enumerate(classes) if "hud-top-actions" in c), -1)
        vitals_idx = next((i for i, c in enumerate(classes) if "vitals-row" in c), -1)
        self.assertNotEqual(actions_idx, -1, "hud-top-actions missing from topbar")
        self.assertNotEqual(vitals_idx, -1, "vitals-row missing from topbar")
        self.assertLess(actions_idx, vitals_idx, "sound fx/actions line must be placed before vitals row")

    def test_vital_stat_cards_have_equal_size_styling(self):
        self.assertRegex(
            self.css,
            r"\.vital-card\s*\{[^}]*flex:\s*1\s+1\s+0",
            "vital cards must have equal flex distribution",
        )
        self.assertRegex(
            self.css,
            r"\.vital-card\s*\{[^}]*height:\s*44px[^}]*box-sizing:\s*border-box",
            "vital cards must have equal height and box-sizing",
        )

class TestSingleLineVitalsAndDistanceParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_topbar_and_vitals_wrap_on_narrow_viewports(self):
        self.assertRegex(
            self.css,
            r"\.hud-topbar\s*\{[^}]*flex-wrap:\s*wrap",
            "hud-topbar must wrap onto multiple lines on narrow viewports",
        )
        self.assertRegex(
            self.css,
            r"\.vitals-row\s*\{[^}]*flex-wrap:\s*wrap",
            "vitals-row must wrap onto multiple lines on narrow viewports",
        )

    def test_vital_cards_match_chrono_box_height(self):
        self.assertRegex(
            self.css,
            r"\.hud-time-deck\s*\{[^}]*height:\s*44px[^}]*box-sizing:\s*border-box",
            "hud-time-deck must match vital card 44px height and border-box sizing",
        )

    def test_orbit_button_uses_timed_transit(self):
        self.assertIn("TRANSIT & ORBIT (${estTicks}T)", self.js)
        self.assertNotIn("btnSublightTarget", self.js)
        self.assertIn('id="transitPlan"', self.html)
        self.assertIn("/api/travel/preview", self.js)
        self.assertIn("refreshTransitPreview", self.js)
        self.assertIn("COURSE PLOT", self.js)
        self.assertIn("transit-plan-risk", self.js)

    def test_radar_backdrop_is_cached(self):
        self.assertIn("ensureRadarBackdrop", self.js)
        self.assertIn("drawImage(this.radarBackdrop", self.js)

    def test_idle_radar_frames_are_throttled(self):
        self.assertIn("IDLE_FRAME_MS", self.js)
        self.assertIn("timestamp - lastDraw >= IDLE_FRAME_MS", self.js)
        self.assertIn("state?.time?.is_paused", self.js)

    def test_orbits_fit_the_visible_radar(self):
        self.assertRegex(self.js, r"orbitFitScale\(bodies\)\s*\{")
        self.assertIn("const auScale = this.orbitFitScale(bodies);", self.js)
        self.assertIn("Math.min(rect.w, rect.h)", self.js,
                      "orbit fit must use the visible map rectangle, not the full viewport")

    def test_radar_labels_are_collision_placed_inside_the_map(self):
        self.assertIn("placeRadarLabel", self.js)
        self.assertIn("_radarLabelBoxes", self.js)
        self.assertIn("box.x + box.w > rect.x + rect.w", self.js,
                      "labels must be rejected when they leave the visible radar")

    def test_canvas_labels_use_a_loaded_console_font(self):
        self.assertFalse("Share Tech Mono" in self.js, "canvas cannot rely on an unloaded font")
        self.assertIn("'Cascadia Mono', Consolas, monospace", self.js)

    def test_diplomacy_war_lookup_compares_ids_instead_of_using_in(self):
        self.assertNotIn(" in (w.attacker_id", self.js,
                         "JS `in` needs an object; war IDs are strings")
        self.assertIn(
            'w.attacker_id === "sol_coalition" || w.defender_id === "sol_coalition"',
            self.js,
        )

class TestArsenalParityAndBulkDepotUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_arsenal_contains_shipyard_and_weapons_containers(self):
        self.assertIn('id="shipyardChassisList"', self.html)
        self.assertIn('id="weaponsBayList"', self.html)

    def test_app_wires_chassis_and_weapon_commissioning(self):
        self.assertIn("handleCommissionChassis", self.js)
        self.assertIn("/api/shipyard/chassis", self.js)
        self.assertIn("handleInstallWeapon", self.js)
        self.assertIn("/api/weapons/install", self.js)
        self.assertIn("handleSetPrimaryWeapon", self.js)
        self.assertIn("/api/weapons/set", self.js)

    def test_depots_support_bulk_actions(self):
        self.assertIn("WITHDRAW ALL", self.js)
        self.assertIn("DEPOSIT ALL", self.js)
        self.assertIn("SELL ALL", self.js)

    def test_glassmorphic_styles_for_showroom_and_weapons(self):
        self.assertIn(".chassis-showroom", self.css)
        self.assertIn(".weapons-bay", self.css)
        self.assertIn(".chassis-card", self.css)
        self.assertIn(".weapon-card", self.css)


class TestStoryAndVoidCockpit(unittest.TestCase):
    """Story branching UI and the Hollow Between void traversal panel."""

    @classmethod
    def setUpClass(cls):
        parser = _TreeBuilder()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        parser.close()
        cls.dom = parser.root
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_story_tab_holds_objectives_choices_and_void_panel(self):
        story_tab = self.dom.find_by_id("tabContentStory")
        self.assertIsNotNone(story_tab, "story tab (#tabContentStory) missing")
        for element_id in ("storyObjectivesBox", "storyObjectivesList", "voidTraversePanel", "voidStatusBadge", "voidBody"):
            node = story_tab.find_by_id(element_id)
            self.assertIsNotNone(node, f"#{element_id} missing from the story tab")

    def test_story_section_source_order(self):
        order = []
        for element_id in ("storySynopsisText", "storyObjectivesBox", "storyChoiceContainer", "voidTraversePanel", "transmissionsStream"):
            index = self.html.find(f'id="{element_id}"')
            self.assertGreaterEqual(index, 0, f"#{element_id} missing from index.html")
            order.append(index)
        self.assertEqual(order, sorted(order), "story tab sections are out of order")

    def test_app_wires_void_endpoints_and_renders(self):
        self.assertIn("renderVoid", self.js)
        self.assertIn("handleVoidDive", self.js)
        self.assertIn("handleVoidEmerge", self.js)
        self.assertIn("/api/void/dive", self.js)
        self.assertIn("/api/void/emerge", self.js)
        self.assertIn("void-transit", self.js, "app.js must toggle the void transit radar overlay class")

    def test_locked_story_choices_render_disabled_with_reasons(self):
        self.assertIn("story-choice-locked", self.js)
        self.assertIn("card.disabled = true", self.js)
        self.assertIn("choice-lock-reason", self.js)
        self.assertIn("story_status", self.js, "renderStory must consume the story_status objective payload")

    def test_void_and_locked_choice_styles_exist(self):
        for selector in (".void-traverse-panel", ".story-objectives-box", ".story-choice-locked", "body.void-transit"):
            self.assertIn(selector, self.css, f"missing CSS rule for {selector}")


class TestCrewSimulationCockpit(unittest.TestCase):
    """Living crew telemetry: morale bars, shore leave, and cash-flow readouts."""

    @classmethod
    def setUpClass(cls):
        parser = _TreeBuilder()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        parser.close()
        cls.dom = parser.root
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_crew_tab_holds_cashflow_shore_and_roster(self):
        crew_tab = self.dom.find_by_id("tabContentCrew")
        self.assertIsNotNone(crew_tab, "crew tab (#tabContentCrew) missing")
        for element_id in ("crewCashFlow", "crewShoreRow", "btnShoreLeave", "crewRoster", "crewAssignments"):
            node = crew_tab.find_by_id(element_id)
            self.assertIsNotNone(node, f"#{element_id} missing from the crew tab")

    def test_crew_section_source_order(self):
        order = []
        for element_id in ("crewCashFlow", "crewRoster", "crewShoreRow", "crewAssignments"):
            index = self.html.find(f'id="{element_id}"')
            self.assertGreaterEqual(index, 0, f"#{element_id} missing from index.html")
            order.append(index)
        self.assertEqual(order, sorted(order), "crew tab sections are out of order")

    def test_app_wires_shore_leave_and_morale_bars(self):
        self.assertIn("handleShoreLeave", self.js)
        self.assertIn("/api/crew/shore", self.js)
        self.assertIn("crew-morale-bar", self.js)
        self.assertIn("crew-morale-critical", self.js)
        self.assertIn("cash_flow", self.js, "renderCrew must consume the cash-flow payload")

    def test_crew_simulation_styles_exist(self):
        for selector in (".crew-cashflow-row", ".crew-shore-row", ".crew-morale-bar", ".crew-morale-fill"):
            self.assertIn(selector, self.css, f"missing CSS rule for {selector}")



class TestLeftTerminalLedger(unittest.TestCase):
    """Left terminal: one visible tab on load, keyboard tab cycling, and two-line ledger records."""

    @classmethod
    def setUpClass(cls):
        parser = _TreeBuilder()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        parser.close()
        cls.dom = parser.root
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def _tab_contents(self, node):
        if node.has_class("tab-content"):
            yield node
        for child in node.children:
            yield from self._tab_contents(child)

    def test_only_the_player_tab_is_visible_before_scripts_run(self):
        visible = [node.attrs.get("id") for node in self._tab_contents(self.dom)
                   if "display: none" not in (node.attrs.get("style") or "")]
        self.assertEqual(visible, ["tabContentPlayer"])

    def test_bracket_keys_cycle_terminal_tabs(self):
        self.assertIn("cycleTerminalTab", self.js)
        self.assertIn('"BracketLeft"', self.js)
        self.assertIn('"BracketRight"', self.js)

    def test_ledger_records_use_three_column_two_line_grid(self):
        match = re.search(r"--ledger-record-cols:\s*([^;]+);", self.css)
        self.assertIsNotNone(match, "missing --ledger-record-cols token")
        tracks = re.findall(r"\w+\([^)]*\)|\S+", match.group(1))
        self.assertEqual(len(tracks), 3, "ledger records use icon | body | value/action")
        for selector in (".contract-card", ".drone-card", ".fleet-ship-card", ".fleet-procurement-row"):
            self.assertIn(selector, self.css)

    def test_outliner_label_stays_on_one_line(self):
        rules = re.findall(r"\.panel-left \.deck-tabs-header::before\s*\{([^}]*)\}", self.css)
        self.assertTrue(any("white-space: nowrap" in body for body in rules))


class TestMarketBulkTrading(unittest.TestCase):
    """Commerce tab: lot selector, max orders and cost-basis feedback."""

    @classmethod
    def setUpClass(cls):
        parser = _TreeBuilder()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        parser.close()
        cls.dom = parser.root
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_lot_selector_sits_in_the_market_tab(self):
        market = self.dom.find_by_id("tabContentMarket")
        bar = market.find_by_id("marketLotBar")
        self.assertIsNotNone(bar, "#marketLotBar missing from the market tab")
        lots = [child.attrs.get("data-lot") for child in bar.children if child.tag == "button"]
        self.assertEqual(lots, ["1", "5", "10", "max"])

    def test_max_orders_and_cost_basis_reach_the_api(self):
        self.assertIn("max: true", self.js)
        self.assertIn("cargo_avg_cost", self.js)
        self.assertIn("max_buy", self.js)


class TestSettingsConsoleQoL(unittest.TestCase):
    """Settings console: volume, gameplay automation, interface memory, controls and reset."""

    SETTING_IDS = ("settingVolume", "settingAutoPause", "settingAutoClaim", "settingTradeLot", "settingRememberTab")

    @classmethod
    def setUpClass(cls):
        parser = _TreeBuilder()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        parser.close()
        cls.dom = parser.root
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_new_settings_live_in_the_settings_overlay_and_are_wired(self):
        overlay = self.dom.find_by_id("settingsOverlay")
        for element_id in self.SETTING_IDS + ("btnResetSettings", "settingsControls"):
            self.assertIsNotNone(overlay.find_by_id(element_id), f"#{element_id} missing from settings")
        for element_id in self.SETTING_IDS + ("btnResetSettings",):
            self.assertIn(f'"{element_id}"', self.js, f"#{element_id} is not wired in app.js")

    def test_every_sound_goes_through_the_master_gain(self):
        self.assertNotIn("gain.connect(this.ctx.destination)", self.js)
        self.assertIn("setVolume", self.js)


class TestCockpitPolling(unittest.TestCase):
    """Client polling contract: cached catalogs, lite payloads, adaptive cadence, guarded rebuilds."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_every_api_call_goes_through_the_catalog_aware_wrapper(self):
        raw = re.findall(r"await fetch\(([^)]*)\)", self.js)
        self.assertEqual(raw, ['"/api/catalogs"'], "only loadCatalogs may bypass apiFetch")
        self.assertIn('"X-VoidFarer-Catalogs"', self.js)

    def test_poll_cadence_follows_the_chrono(self):
        self.assertIn("schedulePoll", self.js)
        self.assertIn("pollInterval", self.js)
        self.assertNotRegex(self.js, r"setInterval\([^)]*refreshState")

    def test_open_tab_is_not_rebuilt_under_a_pressed_pointer(self):
        self.assertIn("terminalBusy()", self.js)
        self.assertIn('"pointerdown"', self.js)


class TestCommandStripFit(unittest.TestCase):
    """G-005/G-013 at every width, and power routing that works without a hidden APPLY button."""

    @classmethod
    def setUpClass(cls):
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def _last(self, selector, prop):
        values = re.findall(re.escape(selector) + r"\s*\{[^}]*?" + prop + r":\s*([^;]+);", self.css)
        self.assertTrue(values, f"no {prop} for {selector}")
        return values[-1].strip()

    def test_strip_stays_beside_a_full_height_terminal(self):
        self.assertEqual(self._last(".hud-command-strip", "grid-column"), "2 / -1")
        self.assertEqual(self._last(".panel-left", "grid-row"), "1 / span 2")

    def test_strip_panels_are_not_capped_at_210px(self):
        self.assertEqual(self._last(".hud-strip-panel", "max-height"), "none")

    def test_power_sliders_and_presets_commit_without_the_apply_button(self):
        self.assertIn('addEventListener("change", () => this.commitPowerRoute())', self.js)
        self.assertGreaterEqual(self.js.count("this.commitPowerRoute();"), 3, "each preset commits")


class TestStrategicGalaxyMap(unittest.TestCase):
    """Galaxy map: faction territory, war fronts and legend, fitted to the visible map area."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_map_views_share_one_visible_area_centre(self):
        self.assertIn("mapCenter()", self.js)
        self.assertNotIn("this.viewW / 2 + this.panX", self.js)

    def test_territory_is_cached_and_drawn_from_politics(self):
        self.assertIn("galactic_politics", self.js)
        self.assertIn("this.territoryKey !== key", self.js, "territory must be cached, not rebuilt every frame")
        self.assertIn("drawPoliticsLegend", self.js)
        self.assertIn("war.fronts", self.js)

    def test_galaxy_has_a_nebula_layer_and_seeded_star_rays(self):
        self.assertIn("drawGalaxyNebula(ctx, transform, now)", self.js)
        self.assertIn(
            'this.drawStarGlyph(ctx, sx, sy, radius, s.color || "#6fc3d7", s.id, now)',
            self.js,
        )
        self.assertIn("const ray", self.js)
        self.assertIn("dust lane", self.js.lower())


class TestCelestialModels(unittest.TestCase):
    """Procedural celestial models: their own module, loaded before the cockpit, sprites cached."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.celestial = (STATIC_DIR / "celestial.js").read_text(encoding="utf-8")

    def test_renderer_loads_before_the_cockpit(self):
        self.assertLess(self.html.index('src="celestial.js"'), self.html.index('src="app.js"'))
        self.assertIn("new window.CelestialRenderer()", self.js)

    def test_every_generated_body_type_has_a_model(self):
        body_types = (
            "terrestrial", "oceanic", "super_earth", "savanna", "tundra", "desert_world", "barren", "ice_world",
            "lava_world", "volcanic", "toxic", "gas_giant", "ringed_giant", "ice_giant", "ring_world",
            "dyson_sphere", "orbital_station", "research_outpost", "quantum_relay", "solar_collector",
            "black_hole", "wormhole", "asteroid_belt",
        )
        for body_type in body_types:
            self.assertTrue(body_type in self.celestial, f"no model for {body_type}")

    def test_surface_sprites_are_cached(self):
        self.assertIn("this.sprites.get(key)", self.celestial)
        self.assertIn("bodyDisplayRadius(b)", self.js, "drawing and hit tests share one body size")

    def test_body_limb_follows_the_star(self):
        self.assertIn("drawLimb(ctx, x, y, r, lightAngle)", self.celestial)
        self.assertNotIn("this.limb(ctx, R)", self.celestial,
                         "the baked highlight must not contradict the terminator")

    def test_ship_models_cover_hull_classes(self):
        self.assertIn('variant = "standard"', self.celestial)
        for variant in ("freighter", "fighter", "explorer", "stealth", "capital"):
            self.assertTrue(variant in self.celestial, f"no ship model for {variant}")

    def test_cloud_bands_drift_over_time(self):
        self.assertIn("drawCloudDrift", self.celestial)
        self.assertIn("this.drawCloudDrift(ctx, body, x, y, r, now)", self.celestial)

    def test_rocky_worlds_turn_slowly(self):
        self.assertIn("SURFACE_SPIN_PERIOD_MS", self.celestial)
        self.assertIn("surfaceSpin(body, now)", self.celestial)
        self.assertIn("this.surfaceSpin(body, now)", self.celestial)
        # Giants keep their static bands; only rocky surfaces turn.
        self.assertIn("if (!ROCKY_STYLES[body.body_type]) return 0;", self.celestial)
        # Polar caps stay with the axis instead of rotating with the terrain.
        self.assertIn("this.drawCaps(ctx, x, y, r)", self.celestial)
        self.assertNotIn("ctx.ellipse(0, -R * 0.95", self.celestial)


class TestGraphicsAssets(unittest.TestCase):
    """Browser identity and galaxy texture assets."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_favicon_is_linked_and_present(self):
        self.assertIn("favicon.svg", self.html)
        path = STATIC_DIR / "favicon.svg"
        self.assertTrue(path.exists(), "favicon.svg is missing")
        self.assertIn("viewBox", path.read_text(encoding="utf-8"))

    def test_territory_has_a_cached_hatch_pattern(self):
        self.assertIn("createPattern", self.js)
        self.assertIn("source-atop", self.js)

    def test_no_color_emoji_remain_in_the_cockpit(self):
        combined = self.html + self.js
        color = sorted({ch for ch in combined if ord(ch) >= 0x1F000})
        self.assertFalse(color, f"color emoji remain: {color}")

    def test_territory_raster_uses_finer_cells(self):
        self.assertIn("this.viewW / 960", self.js)
        self.assertIn("Math.max(2, Math.round(this.viewW / 960))", self.js)

    def test_badge_dot_colors_are_all_styled(self):
        for name in ("dot-cyan", "dot-red", "dot-purple"):
            self.assertIn(
                f".{name} {{ background: var(--neon-",
                self.css,
                f"{name} must use a palette token instead of falling back to the default dot color",
            )

    def test_hud_text_meets_the_twelve_pixel_readability_floor(self):
        selectors = (
            ".vital-label", ".vital-subtext", ".vital-icon",
            ".cadet-pip", ".cadet-pip-divider",
            ".salvage-rewards-row", ".subsystem-title", ".btn-subsystem",
            ".fabrication-header", ".btn-fabricate",
            ".subsystem-gauge .gauge-label", ".subsystem-gauge .gauge-val",
            ".crew-station-select", ".station-badge", ".market-trend-badge",
            ".target-info-grid", ".log-line .log-time", ".log-line .log-tag",
            ".fleet-upkeep-line", ".fleet-stance-label", ".fleet-stance-btn",
            ".fleet-stance-hint", ".fleet-role",
        )
        for selector in selectors:
            match = re.search(rf"^{re.escape(selector)}[^{{]*\{{[^}}]*font-size:\s*([\d.]+)px", self.css, re.M)
            self.assertIsNotNone(match, f"{selector} must declare a pixel font-size")
            self.assertGreaterEqual(float(match.group(1)), 12.0, f"{selector} is below the 12px floor")

    def test_ability_pip_contrast_meets_wcag_aa(self):
        # 0.7 alpha blends to >=4.7:1 on both pip backgrounds; lower alphas fail AA.
        for selector in (".cadet-pip", ".cadet-pip-divider"):
            block = re.search(rf"^{re.escape(selector)} \{{[^}}]*\}}", self.css, re.M)
            self.assertIsNotNone(block, f"{selector} must be declared")
            alpha = re.search(r"color: rgba\(127, 183, 201, ([\d.]+)\)", block.group(0))
            self.assertIsNotNone(alpha, f"{selector} must use the muted cyan token")
            self.assertGreaterEqual(float(alpha.group(1)), 0.7,
                                    f"{selector} contrast falls below WCAG AA")

    def test_ship_labels_and_portrait_initials_use_12px(self):
        self.assertNotIn('font-size="9"', self.js)
        self.assertIn('font-size="12"', self.js)
        self.assertIn("Math.max(12, size * 0.24)", self.js)

    def test_fleet_stance_buttons_meet_the_minimum_target_size(self):
        match = re.search(r"^\.fleet-stance-btn \{[^}]*min-height:\s*(\d+)px", self.css, re.M)
        self.assertIsNotNone(match, ".fleet-stance-btn must declare a min-height")
        self.assertGreaterEqual(int(match.group(1)), 24,
                                "fleet stance buttons are below the 24px target floor")


    def test_legacy_theme_tokens_alias_the_console_palette(self):
        self.assertIn("--neon-cyan: var(--console-cyan)", self.css)
        self.assertIn("--text-primary: var(--console-ivory)", self.css)

    def test_core_palette_is_declared_once(self):
        tokens = {
            "--console-bg": "#06090f",
            "--console-panel": "#0c121c",
            "--console-panel-2": "#101825",
            "--console-gold": "#c9a35a",
            "--console-gold-bright": "#e2c078",
            "--console-ivory": "#ece4d4",
            "--console-cyan": "#7fb7c9",
            "--console-red": "#c96b5a",
            "--console-green": "#8fbf9f",
            "--console-purple": "#a98bbd",
        }
        remainder = self.css
        for token, value in tokens.items():
            self.assertIn(f"{token}: {value};", self.css)
            remainder = remainder.replace(f"{token}: {value};", "")
        for token, value in tokens.items():
            self.assertEqual(remainder.lower().count(value), 0, f"{value} must use {token}")


class TestDrydockServiceQuotes(unittest.TestCase):
    """The service deck must quote the engine's live prices, not a client estimate."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_service_labels_read_the_engine_quote(self):
        self.assertIn("const drydock = this.state.drydock", self.js)
        for label in ("repairCostLabel", "refuelCostLabel", "overhaulCostLabel"):
            self.assertIn(f"this.{label}", self.js)
        self.assertNotIn("Math.round(wearVal * 4.5)", self.js,
                         "overhaul cost must come from the engine, not a client estimate")


class TestRelicFusionCockpit(unittest.TestCase):
    """Relic fusion needs a cockpit path beside the CLI and REST endpoint."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_relic_panel_offers_fusion_controls(self):
        self.assertIn("btn-relic-fuse", self.js)
        self.assertIn("handleFuseRelics", self.js)
        self.assertIn("/api/relics/fuse", self.js)
        self.assertIn(".btn-relic-fuse", self.css)
        self.assertIn("FUSE 3×", self.js)


class TestParticleFX(unittest.TestCase):
    """Visual-only particle layer: pooled, frame-updated and wired to world actions."""


    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        path = STATIC_DIR / "particles.js"
        cls.particles = path.read_text(encoding="utf-8") if path.exists() else ""

    def test_particle_system_loads_before_the_cockpit(self):
        self.assertIn('src="particles.js"', self.html)
        self.assertLess(self.html.index('src="particles.js"'), self.html.index('src="app.js"'))
        self.assertIn("window.ParticleSystem = ParticleSystem", self.particles)

    def test_particle_pool_is_capped(self):
        self.assertIn("class ParticleSystem", self.particles)
        self.assertIn("this.max", self.particles)
        self.assertIn("this.items.length >= this.max", self.particles)

    def test_frame_updates_and_draws_the_layer(self):
        self.assertIn("this.particles?.update()", self.js)
        self.assertIn("this.particles?.draw(ctx)", self.js)
        self.assertIn("globalCompositeOperation", self.particles)
        self.assertIn("ctx.restore()", self.particles)

    def test_ship_transit_scan_and_combat_emit_particles(self):
        self.assertIn("particles?.trail", self.js)
        self.assertIn("particles?.warp", self.js)
        self.assertIn("particles?.ring", self.js)
        self.assertIn("particles?.burst", self.js)
        self.assertIn("lastShipPosition", self.js)


class TestCombatVisual(unittest.TestCase):
    """Tactical combat viewport: two hulls, a firing beam and impact particles."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_combat_card_has_a_tactical_canvas(self):
        self.assertIn('id="combatVisual"', self.html)
        self.assertIn(".combat-visual", self.css)

    def test_combat_visual_draws_two_ships_and_fx(self):
        self.assertIn("drawCombatVisual()", self.js)
        self.assertIn("this.combatFx", self.js)
        self.assertIn("this.combatScene", self.js)

    def test_combat_action_arms_a_beam_or_burst(self):
        self.assertIn("combatBeamUntil", self.js)
        self.assertIn("combatFlash", self.js)

    def test_ship_and_enemy_variants_are_resolved_on_the_map(self):
        self.assertIn("shipVariant()", self.js)
        self.assertIn("enemyVariant()", self.js)
        self.assertIn("this.shipVariant()", self.js)
        self.assertIn("this.enemyVariant()", self.js)

    def test_combat_stance_and_ability_hint_are_not_tiny(self):
        self.assertNotIn("font-size: 0.48rem", self.css)
        self.assertNotRegex(
            self.css,
            r"\.combat-stance-line\s*\{[^}]*font-size:\s*11px",
            "the combat stance line must meet the 12px floor",
        )

    def test_combat_reports_shield_deflection_and_hull_damage_audio(self):
        self.assertIn("this.sound.playShieldDeflect();", self.js)
        self.assertIn("this.sound.playHullDamage();", self.js)
        self.assertNotIn("playBuzzer", self.js, "fabrication failures must use a real SoundController method")



class TestSurfaceTileMap(unittest.TestCase):
    """Seeded surface tiles: biome coverage, canvas wiring and site selection."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        path = STATIC_DIR / "surfacemap.js"
        cls.surface = path.read_text(encoding="utf-8") if path.exists() else ""

    def test_surface_renderer_loads_before_the_cockpit(self):
        self.assertIn('src="surfacemap.js"', self.html)
        self.assertLess(self.html.index('src="surfacemap.js"'), self.html.index('src="app.js"'))
        self.assertIn("window.SurfaceMapRenderer = SurfaceMapRenderer", self.surface)

    def test_biome_palettes_cover_landable_types(self):
        for body_type in (
            "terrestrial", "oceanic", "savanna", "tundra", "super_earth", "desert_world",
            "barren", "ice_world", "lava_world", "volcanic", "toxic", "gas_giant",
        ):
            self.assertTrue(body_type in self.surface, f"no surface biome for {body_type}")

    def test_surface_card_embeds_the_map_canvas(self):
        self.assertIn('id="surfaceMapCanvas"', self.js)
        self.assertIn(".surface-map-canvas", self.css)
        self.assertIn("this.surfaceMap.draw(", self.js)

    def test_clicking_a_site_selects_the_operation(self):
        self.assertIn("hitTest", self.surface)
        self.assertIn("surfaceSelectedOp", self.js)
        self.assertIn("this.surfaceMap.hitTest(", self.js)

    def test_map_is_seeded_by_body_and_operations(self):
        self.assertIn("generate(body, operations)", self.surface)
        self.assertIn("body.id", self.surface)
        self.assertIn("list.map", self.surface)


class TestStrategyPanels(unittest.TestCase):
    """Strategy actions in the cockpit: war pledges, outpost founding and the monthly treasury."""

    @classmethod
    def setUpClass(cls):
        parser = _TreeBuilder()
        parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
        parser.close()
        cls.dom = parser.root
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_wars_panel_sits_in_the_factions_tab_and_pledges(self):
        self.assertIsNotNone(self.dom.find_by_id("tabContentFactions").find_by_id("warsList"))
        self.assertIn('"/api/war/support"', self.js)

    def test_only_your_own_wars_offer_a_ceasefire_petition(self):
        self.assertIn('data-petition-ceasefire', self.js)
        self.assertIn("PETITION CEASEFIRE", self.js)
        self.assertIn("Sovereign war", self.js, "third-party wars are not the captain's to end")
        self.assertNotIn('"/api/war/mediate"', self.js)
        self.assertRegex(self.css, r"\.war-mediate\s*\{[^}]*display:\s*flex")

    def test_open_space_anchor_draws_the_flagship_and_prices_from_the_anchor(self):
        self.assertIn("VF-FLAGSHIP (OPEN SPACE)", self.js)
        self.assertIn("ship.waypoint_au", self.js)
        self.assertIn("ship.waypoint_angle", self.js)

    def test_third_party_wars_never_expose_a_player_peace_button(self):
        self.assertNotIn("MEDIATE CEASEFIRE", self.js)
        self.assertNotIn("mediate_war", self.js)

    def test_outposts_are_founded_from_the_empire_tab(self):
        self.assertIsNotNone(self.dom.find_by_id("tabContentEmpire").find_by_id("outpostBuild"))
        self.assertIn('"/api/outpost/build"', self.js)
        self.assertNotIn("use the outpost build API/CLI", self.js)

    def test_treasury_is_reported_per_month(self):
        self.assertIn("net_per_month", self.js)
        self.assertNotIn("net_per_tick", self.js)


class TestPostPushPolishLayout(unittest.TestCase):
    """Contract header readability, compact reactor strip and deterministic surface scenario."""

    @classmethod
    def setUpClass(cls):
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.browser_tool = (STATIC_DIR.parent.parent / "tools" / "ui_browser.py").read_text(encoding="utf-8")

    def test_decision_overlay_sits_above_the_main_menu(self):
        decision = re.search(r"\.decision-overlay\s*\{[^}]*z-index:\s*(\d+)", self.css, re.S)
        menu = re.search(r"\.main-menu-overlay\s*\{[^}]*z-index:\s*(\d+)", self.css, re.S)
        self.assertIsNotNone(decision)
        self.assertIsNotNone(menu)
        self.assertGreater(int(decision.group(1)), int(menu.group(1)))

    def test_target_card_scrolls_instead_of_spilling_at_short_viewports(self):
        self.assertRegex(self.css, r"\.nav-target-card\s*\{[^}]*overflow-y:\s*auto", re.S)
        self.assertRegex(self.css, r"\.nav-target-card\s*\{[^}]*overscroll-behavior:\s*contain", re.S)

    def test_target_card_reports_population_capacity_and_world_tech(self):
        self.assertIn('id="targetCapacity"', self.html)
        self.assertIn('id="targetTech"', self.html)
        self.assertIn("population_capacity", self.js)
        self.assertIn("DYSON SWARM", self.js)

    def test_contract_header_stacks_short_badge_above_unclamped_title_at_narrow_widths(self):
        self.assertIn("contract-cat-label-full", self.js)
        self.assertIn("contract-cat-label-short", self.js)
        self.assertRegex(
            self.css,
            r"\.contract-card\s*>\s*\.contract-header\s*\{\s*flex-direction:\s*column",
        )

    def test_compact_reactor_strip_uses_four_proportional_tracks(self):
        self.assertIn("grid-template-columns: 1.12fr 1.12fr 1.22fr 0.82fr;", self.css)
        self.assertIn(".hud-command-strip .pwr-icon { display: none; }", self.css)

    def test_surface_ops_scrolls_target_card_and_browser_driver_prepares_surface(self):
        self.assertIn('this.surfaceOps.closest(".nav-target-card")', self.js)
        self.assertIn(".surface-op-main .surface-op-reward { order: 2; margin-left: auto; white-space: nowrap; }", self.css)
        self.assertIn(".hud-command-strip .skill-quick-icon { display: none; }", self.css)
        self.assertIn('"surface"', self.browser_tool)
        self.assertIn("def _prepare_surface(", self.browser_tool)
        self.assertIn("engine.allow_decision_events = False", self.browser_tool)

    def test_waypoint_review_prepares_an_open_space_anchor(self):
        self.assertIn('"waypoint"', self.browser_tool)
        self.assertIn("def _prepare_waypoint(", self.browser_tool)
        self.assertIn('args.scenario == "waypoint"', self.browser_tool)
        self.assertIn("waypoint_au", self.browser_tool)

    def test_factions_review_prepares_a_coalition_war_for_the_petition_control(self):
        self.assertIn("def _prepare_factions(", self.browser_tool)
        self.assertIn('if args.tab == "factions"', self.browser_tool)
        self.assertIn("_prepare_factions(engine)", self.browser_tool)
        self.assertIn('"sol_coalition" in (war.attacker_id, war.defender_id)', self.browser_tool)

    def test_every_click_has_a_stable_handle_for_automation(self):
        self.assertIn("voidfarerClickMap", self.js)
        self.assertIn("clickMap()", self.js)
        self.assertIn("ensureTestId", self.js)
        self.assertIn("voidfarerAgentActions", self.js)
        self.assertIn("/api/agent/actions", self.js)

    def test_aikit_link_and_decision_cadence_are_visible(self):
        self.assertIn('data-testid="aikit-link"', self.html)
        self.assertIn('data-testid="setting-decision-cadence"', self.html)
        self.assertIn('"/api/settings/decisions"', self.js)
        self.assertIn('<option value="relaxed" selected>', self.html,
                      "the settings form must default to the relaxed cadence")

    def test_repeated_row_controls_get_unique_testids(self):
        self.assertIn("element.dataset[identity[0]]}-${index}", self.js)
        self.assertIn("market BUY/SELL", self.js)

    def test_galaxy_traffic_is_selectable_and_target_card_state_is_reset(self):
        self.assertGreaterEqual(self.js.count("galaxyTrafficPositions("), 3)
        self.assertIn('classList.remove("is-devastated")', self.js)
        self.assertIn("this.transitPreviewBodyId = null;", self.js)

    def test_browser_review_proves_every_click_has_a_unique_handle(self):
        self.assertIn("def _click_probe(", self.browser_tool)
        self.assertIn("window.voidfarerClickMap", self.browser_tool)
        self.assertIn("--click-map", self.browser_tool)
        self.assertIn("missing_testid", self.browser_tool)
        self.assertIn("duplicates", self.browser_tool)

    def test_every_static_button_can_be_identified_by_a_headless_driver(self):
        class _Buttons(HTMLParser):
            def __init__(self):
                super().__init__()
                self.unidentified = []

            def handle_starttag(self, tag, attrs):
                if tag != "button":
                    return
                data = dict(attrs)
                hooks = ("id", "data-testid", "data-slot", "data-lot", "data-type", "data-mode", "data-action")
                if not any(data.get(hook) for hook in hooks):
                    self.unidentified.append(data)

        parser = _Buttons()
        parser.feed(self.html)
        self.assertEqual(parser.unidentified, [], "every button needs an id, testid or data hook")

    def test_event_toasts_clear_the_left_terminal_at_720p(self):
        self.assertRegex(
            self.css,
            r"@media\s*\(max-width:\s*1599px\)\s*\{[^@]*\.event-popup-container\s*\{"
            r"[^}]*left:\s*auto[^}]*right:\s*448px[^}]*width:\s*min\(360px,\s*28vw\)",
            re.S,
        )

    def test_scroll_cue_text_meets_the_twelve_pixel_floor(self):
        self.assertRegex(
            self.css,
            r"\.deck-scroll-cue\s*\{[^}]*font-size:\s*12px",
            re.S,
        )

    def test_compact_command_strip_controls_meet_the_24px_target(self):
        self.assertIn(
            ".hud-command-strip .reactor-mode-btn,\n"
            "    .hud-command-strip #btnVentReactor { min-height: 24px; }",
            self.css,
        )
        self.assertIn(
            ".hud-command-strip .skill-quick-chip { min-height: 24px; padding: 1px 5px; }",
            self.css,
        )


class TestTerminalDeckScrolling(unittest.TestCase):
    """Long terminal tabs must scroll inside the deck instead of running off-screen."""

    @classmethod
    def setUpClass(cls):
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.html = INDEX_HTML.read_text(encoding="utf-8")

    def test_active_tab_content_scrolls_within_the_left_deck(self):
        self.assertRegex(
            self.css,
            r"\.panel-left\s*>\s*\.terminal-content-stack\s*\{[^}]*overflow-y:\s*auto",
            re.S,
        )
        self.assertRegex(
            self.css,
            r"\.panel-left\s*>\s*\.terminal-content-stack\s*\{[^}]*overscroll-behavior:\s*contain",
            re.S,
        )

    def test_left_deck_stretches_its_rows_so_the_scroll_area_has_a_height(self):
        self.assertRegex(
            self.css,
            r"\.panel-left\s*\{[^}]*align-items:\s*stretch",
            re.S,
        )

    def test_faction_list_fills_the_deck_instead_of_a_pixel_cap(self):
        self.assertRegex(
            self.css,
            r"\.factions-panel\s*\{[^}]*max-height:\s*100%",
            re.S,
        )
        self.assertNotRegex(self.css, r"\.factions-panel\s*\{[^}]*max-height:\s*520px")

    def test_dyson_shell_replaces_the_star_corona(self):
        self.assertIn("hasDysonSwarm", self.js)
        self.assertIn('if (b.body_type === "star" && hasDysonSwarm)', self.js)
        self.assertIn('b.body_type === "dyson_sphere" ? cx', self.js)

    def test_more_below_cue_is_a_real_element_not_the_decorative_frame(self):
        self.assertIn('id="deckScrollCue"', self.html)
        self.assertIn("deck-scroll-cue", self.css)
        self.assertIn(".panel-left.has-more-below .deck-scroll-cue", self.css)
        self.assertIn("initDeckScrollHint", self.js)
        self.assertIn('classList.toggle("has-more-below"', self.js)

    def test_cue_also_watches_inner_tab_scrollers(self):
        self.assertIn('stack.addEventListener("scroll", sync, true)', self.js)
        self.assertIn('querySelectorAll(".tab-content")', self.js)

    def test_outliner_panel_ends_with_its_sections(self):
        rules = re.findall(r"\.panel-left\s*\{([^}]*)\}", self.css, re.S)
        self.assertTrue(rules, "missing .panel-left rule")
        final_rule = rules[-1]
        self.assertIn("align-self: start", final_rule,
                      "the left drawer must not stretch to the bottom of its grid area")
        self.assertIn("height: fit-content", final_rule,
                      "the left drawer must end with its content instead of filling the column")
        self.assertIn("max-height: 100%", final_rule,
                      "long tab content must still scroll inside the viewport")


class TestShipDisclosures(unittest.TestCase):
    """The dense SHIP tab defaults to collapsed rooms and module catalog."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_rooms_and_catalog_use_named_disclosures(self):
        self.assertIn('id="btnToggleShipRooms"', self.html)
        self.assertIn('data-label="ROOMS"', self.html)
        self.assertIn('id="shipRoomDetails" hidden', self.html)
        self.assertIn('id="btnToggleShipCatalog"', self.html)
        self.assertIn('data-label="MODULES"', self.html)
        self.assertIn('id="shipModulesGrid" hidden', self.html)
        self.assertIn("is-collapsed", self.html)
        self.assertIn("toggleShipDisclosure", self.js)
        self.assertIn("applyDisclosure", self.js)
        self.assertIn(".ship-room-details[hidden], .ship-modules-grid[hidden]", self.css)


class TestLeftPanelUniformity(unittest.TestCase):
    """Every left tab shares one header height and one section rhythm."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_every_tab_header_is_one_compact_block(self):
        headers = re.findall(r"\.tab-content > \.panel-header \{([^}]*)\}", self.css, re.S)
        self.assertTrue(any("min-height: 56px" in body for body in headers))
        self.assertTrue(any("flex-wrap: wrap" in body for body in headers))
        titles = re.findall(
            r"\.tab-content > \.panel-header > \.panel-title \{([^}]*)\}", self.css, re.S
        )
        self.assertTrue(any(
            "font-size: 13.5px" in body and "text-overflow: ellipsis" in body
            for body in titles
        ))
        self.assertIn("white-space: nowrap", self.css.split("#tabContentCrew .panel-title", 1)[1])

    def test_section_headings_share_one_style(self):
        rule = re.search(
            r"\.tab-content \.subpanel-title,\s*"
            r"\.tab-content \.commission-title,\s*"
            r"\.tab-content \.research-queue-header \{([^}]*)\}",
            self.css,
            re.S,
        )
        self.assertIsNotNone(rule, "missing shared left-panel section heading rule")
        body = rule.group(1)
        self.assertIn("font-size: 12px", body)
        self.assertIn("color: var(--console-gold)", body)
        self.assertIn("text-transform: uppercase", body)

    def test_narrow_lists_stack_instead_of_squeezing(self):
        self.assertIn("#depotList .depot-card", self.css)
        self.assertIn('"cost start queue"', self.css)
        self.assertIn(".factions-meter-bar { grid-template-columns: minmax(0, 1fr); gap: 4px; }", self.css)

    def test_story_title_drops_the_duplicated_act_prefix(self):
        self.assertIn("this.storyChapterTitle.textContent = curChap.title.toUpperCase();", self.js)
        self.assertNotIn("ACT ${story.active_act}: ${curChap.title.toUpperCase()}", self.js)
        self.assertIn("activeTitle.title = activeTitle.textContent.trim();", self.js)

    def test_factions_title_and_intros_are_compacted(self):
        self.assertIn("FACTIONS & CORPORATIONS", self.html)
        self.assertNotIn("GALACTIC FACTIONS & CORPORATIONS", self.html)
        self.assertEqual(self.html.count('class="panel-intro-text" title='), 3)


class TestFleetDisclosures(unittest.TestCase):
    """The dense FLEET tab defaults to collapsed contracts and procurement."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_contracts_and_commission_use_named_disclosures(self):
        self.assertIn('id="btnToggleMercenaries"', self.html)
        self.assertIn('data-label="MERCENARY CONTRACTS"', self.html)
        self.assertIn('id="mercenaryDetails" hidden', self.html)
        self.assertIn('id="btnToggleCommission"', self.html)
        self.assertIn('data-label="COMMISSION"', self.html)
        self.assertIn('id="commissionDetails" hidden', self.html)
        self.assertIn("id=\"mercenaryCount\"", self.html)
        self.assertIn(".fleet-disclosure-toggle", self.css)
        self.assertIn("#mercenaryDetails[hidden], #commissionDetails[hidden]", self.css)
        self.assertIn("toggleFleetDisclosure", self.js)
        self.assertIn("applyDisclosure", self.js)

    def test_mercenary_contracts_render_without_owned_drones(self):
        body = self.js.split("    renderFleet() {", 1)[1].split("    renderContracts() {", 1)[0]
        # After the drone list is read, no early return may skip the mercenary
        # block: owning zero drones must not hide the hiring contracts.
        after_drones = body.split("const drones = this.state.ship.fleet_drones || [];", 1)[1]
        self.assertNotIn("return;", after_drones)
        self.assertIn("if (this.mercenaryRoster)", after_drones)
        self.assertIn("this.mercenaryCount.textContent", after_drones)
        self.assertIn("No fleet drones active. Use SHOW COMMISSION", after_drones)


class TestCommerceDisclosures(unittest.TestCase):
    """The dense COMMERCE tab defaults to collapsed broker and freight sections."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_auto_trade_and_freight_use_named_disclosures(self):
        self.assertIn('id="btnToggleAutoTrade"', self.html)
        self.assertIn('data-label="AUTO-TRADE"', self.html)
        self.assertIn('id="autoTradeDetails" hidden', self.html)
        self.assertIn('id="btnToggleQuantumFreight"', self.html)
        self.assertIn('data-label="QUANTUM FREIGHT"', self.html)
        self.assertIn('id="quantumFreightDetails" hidden', self.html)
        self.assertIn(".trade-disclosure-toggle", self.css)
        self.assertIn("#autoTradeDetails[hidden], #quantumFreightDetails[hidden]", self.css)
        self.assertIn("toggleTradeDisclosure", self.js)
        self.assertIn("applyDisclosure", self.js)

    def test_market_table_stays_above_the_optional_broker_panels(self):
        table = self.html.index('class="commodity-table-container"')
        auto = self.html.index('id="tradeAutomationPanel"')
        quantum = self.html.index('id="quantumFreightShell"')
        self.assertLess(table, auto)
        self.assertLess(auto, quantum)


class TestPlayerAbilityDedup(unittest.TestCase):
    """The PLAYER card points at the command strip instead of duplicating its controls."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_player_card_has_no_second_ability_use_set(self):
        self.assertIn("player-ability-hint", self.js)
        self.assertIn("Use the bottom command strip", self.js)
        self.assertNotIn("data-use-ability", self.js)
        self.assertIn(".player-ability-hint", self.css)


class TestFocusRail(unittest.TestCase):
    """The default terminal rail shows the five core systems plus one disclosure."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_advanced_systems_are_disclosed_by_one_control(self):
        self.assertEqual(self.html.count('data-advanced="true"'), 11)
        self.assertIn('id="btnToggleAdvancedTabs"', self.html)
        self.assertIn('MORE SYSTEMS', self.html)
        self.assertIn(
            '.deck-tabs-header:not(.show-advanced) .deck-tab-btn[data-advanced="true"]',
            self.css,
        )
        self.assertIn("setAdvancedTabsVisible", self.js)
        self.assertIn("this.setAdvancedTabsVisible(!this.advancedTabsVisible)", self.js)
        self.assertIn('getAttribute("data-advanced") === "true"', self.js)


class TestProgressionTrackLabels(unittest.TestCase):
    """The PLAYER card must name Commander and Pilot Mastery as separate tracks."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_player_card_labels_both_tracks(self):
        self.assertIn("COMMANDER LVL ${ch.level || 1}", self.js)
        self.assertIn("PILOT MASTERY LVL ${masteryLevel}", self.js)
        self.assertIn("this.state.ship?.mastery", self.js)
        self.assertIn(".character-mastery-row", self.css)


class TestAudioLevelUpCue(unittest.TestCase):
    """A Pilot Mastery promotion must invoke the synthesized level-up cue once."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_promotion_calls_the_level_up_cue(self):
        self.assertIn("this._lastMasteryLevel", self.js)
        self.assertIn("this.sound.playLevelUp()", self.js)
        self.assertIn("masteryLevel > this._lastMasteryLevel", self.js)


class TestAudioMuteControl(unittest.TestCase):
    """The top-bar mute must persist and silence the master gain immediately."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_toggle_persists_and_mutes_the_master_gain(self):
        self.assertIn("setEnabled(on)", self.js)
        self.assertIn("this.setEnabled(!this.enabled)", self.js)
        self.assertIn("this.enabled ? this.volume : 0", self.js)
        self.assertRegex(
            self.js,
            r'audioToggleBtn\.addEventListener\("click",[\s\S]{0,700}this\.saveSettings\(\)',
        )


class TestRadarTrafficLabels(unittest.TestCase):
    """NPC names must share the body-label collision map, not paint over it."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_traffic_labels_join_the_collision_map(self):
        self.assertIn("this.placeRadarLabel(\n                    ctx, captain.name", self.js)
        self.assertNotIn("ctx.fillText(captain.name", self.js)


class TestCombatGaugeHonesty(unittest.TestCase):
    """The DRIVES gauge must reflect the persisted engines-disable state, not a brace posture."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_engines_gauge_reads_persistent_disable(self):
        self.assertIn("c.enemy_engines_disabled", self.js)
        self.assertNotIn("const isBraced = c.enemy_intent === \"brace\"", self.js)


class TestCadetRibbonAtMinimumViewport(unittest.TestCase):
    """The onboarding ribbon must keep its content height at 1280x720."""

    @classmethod
    def setUpClass(cls):
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_cadet_banner_opts_out_of_flex_shrink(self):
        self.assertRegex(
            self.css,
            r"(?s)\.cadet-academy-banner\s*\{[^}]*flex-shrink:\s*0",
            "the cadet ribbon is a flex item and must not shrink below its badge at 720p",
        )


class TestFactionEconomyCard(unittest.TestCase):
    """The faction card must show where money comes from and where it goes."""

    @classmethod
    def setUpClass(cls):
        cls.css = STYLE_CSS.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.html = INDEX_HTML.read_text(encoding="utf-8")

    def test_card_lists_tax_trade_industry_and_upkeep(self):
        self.assertIn("econ-breakdown", self.js)
        self.assertIn("TAX ${signed(tax)}", self.js)
        self.assertIn("TRADE ${signed(trade)}", self.js)
        self.assertIn("IND ${signed(industry)}", self.js)
        self.assertIn("UPKEEP", self.js)

    def test_breakdown_wraps_between_figures_not_mid_value(self):
        self.assertRegex(
            self.css,
            r"\.faction-economy\.econ-breakdown\s*\{[^}]*flex-wrap:\s*wrap",
            re.S,
        )
        self.assertIn('<span>TAX', self.js)

    def test_card_shows_positive_net_in_green(self):
        self.assertIn("econ-net", self.js)
        self.assertIn('net >= 0 ? "is-pos" : "is-neg"', self.js)
        self.assertRegex(self.css, r"\.econ-net\.is-pos\s*\{[^}]*color:")

    def test_card_shows_trade_partners_and_tech_progress(self):
        self.assertIn("trade_partner_names", self.js)
        self.assertIn("trade_partners", self.js)
        self.assertIn("tech_progress", self.js)
        self.assertIn("TRADE ${partners}", self.js)

class TestVectorTravelCockpit(unittest.TestCase):
    """Open-space vectors need a visible reticle and the same transit animation as bodies."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_selected_vector_draws_a_reticle_and_course(self):
        self.assertIn("drawPointSelection(ctx, cx, cy, auScale, ship);", self.js)
        self.assertIn("drawPointSelection(ctx, cx, cy, auScale, ship) {", self.js)
        self.assertIn("VECTOR ", self.js)
        self.assertIn("this.selectedType === \"point\"", self.js)

    def test_point_travel_starts_the_transit_animation(self):
        self.assertIn("this.startTravelAnimation(fromId, null, activeTravel);", self.js)
        self.assertIn("isPoint", self.js)
        self.assertIn("activeTravel.waypoint_au", self.js)
        self.assertIn("activeTravel.waypoint_angle", self.js)

    def test_transit_animation_marks_the_destination_vector(self):
        self.assertIn("anim.isPoint", self.js)
        self.assertIn("DESTINATION VECTOR", self.js)

    def test_browser_review_can_select_a_vector(self):
        tool = (STATIC_DIR.parent.parent / "tools" / "ui_browser.py").read_text(encoding="utf-8")
        self.assertIn('"vector"', tool)
        self.assertIn('selectedType = "point"', tool)

class TestWorldReliefCockpit(unittest.TestCase):
    """The target card must expose post-war rebuilding and relief controls."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_target_card_holds_rebuild_and_relief_actions(self):
        for element_id in ("btnRebuildTarget", "btnReliefTarget"):
            self.assertIn(f'id="{element_id}"', self.html)
        for marker in ("handleReconstructAction", '"/api/reconstruct"', "btnRebuildTarget", "btnReliefTarget"):
            self.assertIn(marker, self.js)

    def test_reconstruction_controls_have_stable_testids(self):
        self.assertIn('data-testid="rebuild-target"', self.html)
        self.assertIn('data-testid="relief-target"', self.html)

    def test_browser_review_prepares_a_devastated_world(self):
        tool = (STATIC_DIR.parent.parent / "tools" / "ui_browser.py").read_text(encoding="utf-8")
        self.assertIn('"relief"', tool)
        self.assertIn("def _prepare_relief(", tool)
        self.assertIn("devastation=60.0", tool)

class TestBoardingCockpit(unittest.TestCase):
    """The combat card must expose a gated boarding action."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_combat_card_holds_a_board_button(self):
        self.assertIn('id="btnCombatBoard"', self.html)
        self.assertIn('data-testid="combat-board"', self.html)
        self.assertIn('handleCombat("board_enemy")', self.js)
        self.assertIn("btnCombatBoard", self.js)

    def test_board_button_is_gated_by_shields_hull_and_marine(self):
        for marker in ("enemy_shield <= 0", "enemy_hull <= crippledAt", 'member.role === "marine"'):
            self.assertIn(marker, self.js)

    def test_browser_review_prepares_a_boarding_action(self):
        tool = (STATIC_DIR.parent.parent / "tools" / "ui_browser.py").read_text(encoding="utf-8")
        self.assertIn('"boarding"', tool)
        self.assertIn("def _prepare_boarding(", tool)
        self.assertIn("enemy_hull=20", tool)

class TestFleetPrizeCockpit(unittest.TestCase):
    """Captured prizes must be sellable from the fleet manager."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_fleet_manager_has_a_sell_control(self):
        self.assertIn("data-escort-sell", self.js)
        self.assertIn('"/api/fleet/escort/sell"', self.js)
        self.assertIn("sale_value", self.js)
        self.assertIn(".fleet-ship-card > div.fleet-head { grid-column: 2;", self.css)
        self.assertIn(".fleet-ship-card > div.ship-actions { grid-column: 3;", self.css)

class TestFleetVeterancyCockpit(unittest.TestCase):
    """Escort cards must show rank progress and a drydock training control."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_fleet_cards_show_rank_progress_and_training(self):
        for marker in (
            "fleet-veterancy",
            "fleet-rank",
            "fleet-xp-fill",
            "data-escort-train",
            '"/api/fleet/escort/train"',
            "training_cost",
        ):
            self.assertIn(marker, self.js)
        for selector in (".fleet-rank", ".fleet-xp-bar", ".fleet-xp-fill"):
            self.assertIn(selector, self.css)

    def test_fleet_cards_show_patrol_cadence(self):
        self.assertIn("patrol_sweep_ticks", self.js)
        self.assertIn("PATROL ${patrolTicks}T", self.js)

    def test_fleet_cards_offer_captain_assignment(self):
        for marker in (
            "data-escort-captain-assign",
            "data-escort-captain-recall",
            '"/api/fleet/escort/captain"',
            "fleet-captain-row",
            "captain_name",
            "captain_skill",
        ):
            self.assertIn(marker, self.js)
        self.assertIn(".fleet-captain-row", self.css)

    def test_fleet_cards_offer_squadron_roles(self):
        for marker in (
            "data-escort-role",
            "data-next-role",
            '"/api/fleet/escort/role"',
            "fleet-role",
            "tactical_role",
        ):
            self.assertIn(marker, self.js)
        self.assertIn(".fleet-role", self.css)

    def test_fleet_cards_show_service_records(self):
        self.assertIn("fleet-service", self.js)
        self.assertIn("patrol_contacts", self.js)
        self.assertIn("patrol_credits", self.js)
        self.assertIn(".fleet-service", self.css)

    def test_fleet_manager_shows_monthly_upkeep(self):
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertIn('id="fleetUpkeepLine"', html)
        self.assertIn("fleetUpkeepLine", self.js)
        self.assertIn("upkeep_per_month", self.js)
        self.assertIn(".fleet-upkeep-line", self.css)


class TestFleetStanceCockpit(unittest.TestCase):
    """Battle stance must be controllable and visible in the cockpit."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_cockpit_offers_three_stance_buttons(self):
        for stance in ("balanced", "aggressive", "defensive"):
            self.assertIn(f'data-fleet-stance="{stance}"', self.html)
        self.assertIn("fleetStanceRow", self.html)
        self.assertIn("fleetStanceHint", self.html)
        self.assertIn("combatStanceLine", self.html)

    def test_stance_controls_post_to_the_existing_endpoint(self):
        self.assertIn('"/api/combat/stance"', self.js)
        self.assertIn("battle_stance", self.js)
        self.assertIn("FLEET STANCE:", self.js)

    def test_stance_layout_and_active_state_are_styled(self):
        self.assertIn(".fleet-stance-row", self.css)
        self.assertIn(".fleet-stance-btn.active", self.css)
        self.assertIn(".combat-stance-line", self.css)


class TestCaptainGambitCockpit(unittest.TestCase):
    """The combat card must offer the once-per-battle captain action."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_combat_card_has_a_captain_gambit_button(self):
        self.assertIn('id="btnCombatGambit"', self.html)
        self.assertIn("CAPTAIN'S GAMBIT", self.html)
        self.assertIn('"/api/combat/gambit"', self.js)
        self.assertIn("captain_gambit_used", self.js)


class TestCrewMedalsCockpit(unittest.TestCase):
    """Crew cards must show earned service medals."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_crew_rows_render_medals(self):
        self.assertIn("crew-medals", self.js)
        self.assertIn("m.medals", self.js)

    def test_medal_badges_are_styled(self):
        self.assertIn(".crew-medals", self.css)
        self.assertIn(".crew-medals span", self.css)


class TestMegastructureCockpit(unittest.TestCase):
    """The target card must expose megastructure restoration."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_target_card_has_a_restore_button(self):
        for marker in (
            'id="btnRestoreTarget"',
            '"/api/megastructure/restore"',
            "megastructure",
            "RESTORE (",
        ):
            self.assertIn(marker, self.html + self.js)


class TestOutpostSupplyCockpit(unittest.TestCase):
    """Outpost cards must expose supply hub linking and status."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_outpost_cards_offer_link_and_unlink(self):
        for marker in (
            "data-outpost-link",
            "data-outpost-unlink",
            '"/api/outpost/link"',
            "supply_hub_name",
            "supply_link_count",
            "outpost-supply-bar",
        ):
            self.assertIn(marker, self.js)

    def test_supply_bar_is_styled(self):
        self.assertIn(".outpost-supply-bar", self.css)
        self.assertIn(".outpost-supply-status", self.css)


class TestResearchQueueCockpit(unittest.TestCase):
    """The Empire research list must expose queue and cancel controls."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_research_rows_offer_queue_and_cancel(self):
        for marker in (
            "data-research-queue",
            "data-research-cancel",
            '"/api/research/queue"',
            '"/api/research/cancel"',
            "research-queue-row",
        ):
            self.assertIn(marker, self.js)
        self.assertIn(".research-queue-row", self.css)


class TestOutpostModuleCockpit(unittest.TestCase):
    """The Empire tab must expose outpost module installation."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_outpost_rows_offer_a_module_installer(self):
        for marker in ("data-outpost-module-select", "data-outpost-module-install", '"/api/outpost/module"', "outpost_modules"):
            self.assertIn(marker, self.js)
        self.assertIn(".outpost-module-bar", self.css)

    def test_outpost_rows_offer_crew_assignment(self):
        for marker in (
            "data-outpost-crew-select",
            "data-outpost-crew-assign",
            "data-outpost-crew-recall",
            '"/api/outpost/crew"',
            "crew_multiplier",
        ):
            self.assertIn(marker, self.js)
        for selector in (".outpost-crew-bar", ".outpost-crew-chip", ".crew-outpost"):
            self.assertIn(selector, self.css)

    def test_outpost_rows_offer_integrity_repair(self):
        for marker in (
            "data-outpost-repair",
            '"/api/outpost/repair"',
            "outpost-integrity",
            "outpost-row-actions",
        ):
            self.assertIn(marker, self.js)
        for selector in (".outpost-integrity", ".outpost-row-actions"):
            self.assertIn(selector, self.css)

    def test_outpost_rows_offer_specialization(self):
        for marker in (
            "data-outpost-spec-select",
            "data-outpost-spec-set",
            '"/api/outpost/specialize"',
            "specialization_label",
        ):
            self.assertIn(marker, self.js)
        self.assertIn(".outpost-spec-bar", self.css)

    def test_local_shipyard_shows_services_online(self):
        self.assertIn("SERVICES ONLINE", self.js)
        self.assertIn("outpost-service-badge", self.css)
        self.assertIn("SHIPYARD LINK", self.js)

class TestQuantumAutomationCockpit(unittest.TestCase):
    """The quantum freight panel must expose the auto-freight policy."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_quantum_panel_offers_automation_controls(self):
        for marker in (
            "quantumAutoEnabled",
            "quantumAutoMin",
            '"/api/trade/quantum/automation"',
            "handleQuantumAutomation",
        ):
            self.assertIn(marker, self.js)
        self.assertIn(".quantum-auto", self.css)


class TestTradeAutomationCockpit(unittest.TestCase):
    """The Commerce tab must expose the docked auto-trade broker."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_market_tab_holds_the_broker_controls(self):
        for element_id in (
            "tradeAutomationPanel", "autoTradeCommodity", "autoTradeBuy",
            "autoTradeSell", "autoTradeQty", "btnAutoTradeEnable", "btnAutoTradeDisable",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        for marker in ("renderTradeAutomation", "handleTradeAutomation", '"/api/trade/automation"'):
            self.assertIn(marker, self.js)
        self.assertIn(".trade-automation", self.css)

class TestDiplomacyActionsCockpit(unittest.TestCase):
    """Faction rows must expose improve, gift, alliance and ceasefire actions."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_diplomacy_rows_offer_the_full_action_set(self):
        for marker in (
            "data-diplo-action",
            'data-diplo-action="gift"',
            'data-diplo-action="non_aggression"',
            'data-diplo-action="trade_pact"',
            'data-diplo-action="research_pact"',
            'data-diplo-action="alliance"',
            'data-diplo-action="ceasefire"',
            "handleDiplomacyAction",
            "trade_pacts",
        ):
            self.assertIn(marker, self.js)
        self.assertIn(".diplomacy-actions", self.css)
        self.assertIn("ALLIED", self.js)
        self.assertIn("PACT", self.js)
        self.assertIn("R&D", self.js)
        self.assertIn("research_pacts", self.js)
        self.assertIn("non_aggression_until", self.js)
        self.assertIn("NAP", self.js)

class TestWarBondsCockpit(unittest.TestCase):
    """War cards must explain the bond payout terms."""

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = STYLE_CSS.read_text(encoding="utf-8")

    def test_war_cards_show_bond_terms(self):
        self.assertIn("war-bond-note", self.js)
        self.assertIn("1.5x", self.js)
        self.assertIn(".war-bond-note", self.css)
