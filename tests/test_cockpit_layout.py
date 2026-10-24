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

    def test_command_strip_holds_reactor_skills_and_right_column(self):
        strip = self.dom.find_by_id("hudCommandStrip")
        self.assertIsNotNone(strip, "command strip (#hudCommandStrip) missing")
        child_ids = [child.attrs.get("id") for child in strip.children]
        self.assertEqual(
            child_ids,
            ["panelReactor", "hudSkillsPanel", "hudStripRight"],
            "strip order must be reactor, skills, radar/log column",
        )
        self.assertRegex(
            self.css,
            r"\.hud-command-strip\s*\{[^}]*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)",
            "reactor, skills, and radar/log must stretch equally",
        )
        self.assertRegex(
            self._rule_body(".hud-command-strip"),
            r"grid-template-columns",
            "the command strip must lay its three columns out in one row",
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

    def test_skills_strip_has_icons_hotkeys_and_training_wiring(self):
        self.assertIn('id="hudSkillsPanel"', self.html)
        self.assertIn('id="hudSkillsGrid"', self.html)
        self.assertIn("renderSkillsQuickPanel", self.js)
        self.assertIn("trainSkillQuick", self.js)
        self.assertIn("SKILL_HOTKEYS", self.js)
        self.assertIn("SKILL_META", self.js)
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

    def test_orbit_button_adheres_to_distance_calculation(self):
        self.assertIn("ENTER ORBIT (${distAu.toFixed(2)} AU)", self.js)

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
        for element_id in ("crewCashFlow", "crewAssignments", "crewRoster", "crewShoreRow"):
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

