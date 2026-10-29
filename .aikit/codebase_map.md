# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `87`
- **Total Classes**: `222`
- **Total Top-Level Functions**: `302`
- **Total Class Methods**: `1302`
- **Total Source Lines**: `36423`

---

## 📦 Modules & Exported Symbols

### [`tests/__init__.py`](tests/__init__.py)
> *VoidFarer test suite package.*

**Size**: `1` lines (`36` bytes)

---

### [`tests/test_adaptive_ui_salvage.py`](tests/test_adaptive_ui_salvage.py)
> *Regression tests for the Windows high-DPI cockpit, derelict salvage,*

**Size**: `207` lines (`9144` bytes)

**Classes:**
- `class TestAdaptiveCockpitAssets`
  - Method `.setUpClass()`
  - Method `.test_css_declares_windows_desktop_profiles()`
  - Method `.test_settings_expose_density_and_scale()`
  - Method `.test_radar_is_dpi_aware_and_mouse_ready()`
  - Method `.test_polling_and_hotkeys_are_guarded()`
- `class TestSalvageModelsAndCatalog`
  - Method `.test_legacy_body_payload_defaults_salvage_flag()`
  - Method `.test_derelict_generation_is_deterministic()`
  - Method `.test_stations_never_generate_derelicts()`
  - Method `.test_sol_has_at_least_one_salvage_site()`
- `class TestExplorationMechanics`
  - Method `.setUp()`
  - Method `._derelict_body()`
  - Method `.test_salvage_rewards_cargo_and_claims_site()`
  - Method `.test_salvage_requires_a_derelict()`
  - Method `.test_fuel_scoop_refuels_and_heats_reactor()`
  - Method `.test_fuel_scoop_requires_a_scoopable_body()`
  - Method `.test_scoop_yield_scales_with_science_skill()`
  - Method `.test_snapshot_exposes_salvage_and_scoop_hints()`
  - Method `.test_crew_drill_raises_skill_and_spends_credits()`
  - Method `.test_crew_drill_caps_skill()`
- `class TestNewMechanicWiring`
  - Method `.setUpClass()`
  - Method `.test_api_and_cli_expose_the_new_mechanics()`
  - Method `.test_cockpit_exposes_new_action_buttons()`

---

### [`tests/test_agent_play.py`](tests/test_agent_play.py)
> *The headless AI captain must be able to reach and exercise the game without a human.*

**Size**: `110` lines (`5032` bytes)

**Classes:**
- `class AgentApiCatalogTest`
  - Method `.setUpClass()`
  - Method `.test_catalog_describes_every_post_route()`
  - Method `.test_catalog_fields_match_the_endpoint_contract()`
  - Method `.test_observations_include_state()`
- `class AgentPlayTest`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.test_catalog_is_served_over_rest()`
  - Method `.test_ai_captain_plays_without_a_human()`
  - Method `.test_every_catalog_action_is_attempted_or_documented()`
  - Method `.test_coverage_gap_detection()`
  - Method `.test_the_engine_state_stays_loadable_after_play()`

---

### [`tests/test_ai_and_calendar.py`](tests/test_ai_and_calendar.py)
> *Regression tests for adaptive enemy AI, expanded systems, and calendar dates.*

**Size**: `197` lines (`7587` bytes)

**Classes:**
- `class TestAdaptiveEnemyAI`
  - Method `.test_defensive_profile_braces_against_player_combo()`
  - Method `.test_opportunist_executes_wounded_player()`
  - Method `.test_adaptive_profile_disrupts_high_combo()`
  - Method `.test_warlord_regenerates_when_wounded()`
  - Method `.test_generated_enemies_carry_ai_profile_and_intent()`
  - Method `.test_ai_fields_round_trip_through_save_data()`
  - Method `._combat_engine(intent, profile, player_combo)`
  - Method `.test_brace_reduces_player_strike_damage()`
  - Method `.test_execute_increases_counter_battery_damage()`
  - Method `.test_evade_can_make_player_strike_miss()`
  - Method `.test_ai_chooses_next_intent_from_player_combo()`
- `class TestExpandedGalaxy`
  - Method `.test_every_system_has_at_least_five_planets_and_a_station()`
  - Method `.test_sol_station_id_remains_stable()`
- `class TestCalendarDate`
  - Method `.test_initial_calendar_date()`
  - Method `.test_calendar_date_advances_and_rolls_over_months()`
  - Method `.test_time_payload_exposes_date()`
  - Method `.test_engine_tick_updates_calendar_date()`

---

### [`tests/test_away_missions.py`](tests/test_away_missions.py)
> *Away-team expeditions: catalog, deterministic outcomes, injuries, XP, parity and saves.*

**Size**: `307` lines (`12972` bytes)

**Classes:**
- `class AwayCatalogTest`
  - Method `.test_catalog_has_multiple_distinct_missions()`
  - Method `.test_auto_team_prefers_matching_specialty_and_excludes_assigned()`
  - Method `.test_risk_falls_with_specialist_skill_and_rises_with_hazards()`
  - Method `.test_resolution_is_deterministic_and_reports_outcome()`
  - Method `._body()`
- `class AwayEngineTest`
  - Method `.setUp()`
  - Method `._launch_any()`
  - Method `.test_report_lists_body_missions_and_crew()`
  - Method `.test_launch_assigns_an_uninjured_team_and_persists()`
  - Method `.test_launch_rejects_injured_team_and_combat()`
  - Method `.test_tick_resolves_success_and_awards_cargo_or_credits()`
  - Method `.test_tick_failure_injures_crew_and_blocks_their_bonus()`
  - Method `.test_recall_returns_crew_without_reward()`
  - Method `.test_injuries_recover_and_medic_speeds_it()`
  - Method `.test_crew_xp_promotes_skill_and_keeps_remainder()`
  - Method `.test_old_saves_default_new_fields()`
  - Method `.test_mission_round_trip()`
- `class AwayParityTest`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.setUp()`
  - Method `._get(path)`
  - Method `._post(path, payload)`
  - Method `.test_rest_report_and_launch()`
  - Method `.test_cli_lists_away_teams()`

**Functions:**
- `def _crew(member_id, role, skill, specialty, injury)`

---

### [`tests/test_batch_launchers.py`](tests/test_batch_launchers.py)
> *Regression tests for the Windows batch launchers (``play.bat``, ``voidfarer.bat``).*

**Size**: `57` lines (`2141` bytes)

**Classes:**
- `class TestLauncherLineEndings` - *cmd.exe parses CRLF batches reliably; lone LF endings can abort a script mid-file.*
  - Method `._assert_crlf(path)`
  - Method `.test_play_bat_uses_crlf_line_endings()`
  - Method `.test_voidfarer_bat_uses_crlf_line_endings()`
- `class TestLauncherMenu` - *The interactive mission menu must survive its ASCII banner and exit cleanly.*
  - Method `.test_menu_choice_zero_renders_and_exits_cleanly()`

---

### [`tests/test_captains_log_codex.py`](tests/test_captains_log_codex.py)
> *Regression tests for the captain's log, discovery codex, statistics, and rewards.*

**Size**: `224` lines (`9462` bytes)

**Classes:**
- `class TestCodexCatalog`
  - Method `.test_entry_ids_are_unique_and_resolvable()`
  - Method `.test_entries_have_positive_targets_and_valid_categories()`
  - Method `.test_report_covers_every_entry_and_starts_unclaimed()`
  - Method `.test_fresh_engine_has_no_completed_milestones()`
  - Method `.test_unknown_metric_is_rejected()`
- `class TestCodexState`
  - Method `.test_round_trip_preserves_claims_and_dates()`
  - Method `.test_legacy_game_payload_defaults_codex()`
- `class TestCodexEngine`
  - Method `.setUp()`
  - Method `._entry(entry_id)`
  - Method `.test_jump_progresses_jump_and_system_metrics()`
  - Method `.test_claim_grants_credits_xp_and_persists_once()`
  - Method `.test_locked_and_unknown_claims_are_rejected_without_side_effects()`
  - Method `.test_scoop_increments_the_statistic()`
  - Method `.test_status_snapshot_exposes_the_codex()`
  - Method `.test_claims_survive_save_and_load()`
- `class TestCodexCli`
  - Method `.setUp()`
  - Method `._run(argv)`
  - Method `.test_log_and_codex_commands_render()`
  - Method `.test_codex_claim_after_jump()`
- `class TestCodexCockpitAssets`
  - Method `.test_index_declares_the_captains_log_tab()`
  - Method `.test_javascript_renders_and_claims_codex_entries()`
  - Method `.test_styles_cover_codex_cards()`

---

### [`tests/test_cli.py`](tests/test_cli.py)
> *Unit tests for command-line arguments and subcommands.*

**Size**: `223` lines (`9667` bytes)

**Classes:**
- `class _IsolatedCliTestCase` - *Base for CLI tests: redirect default storage away from the player's live save.*
  - Method `.setUp()`
- `class TestCLI`
  - Method `.test_cli_help()`
  - Method `.test_cli_status()`
  - Method `.test_cli_chart()`
  - Method `.test_cli_power()`
  - Method `.test_cli_combat_accepts_documented_actions()`
  - Method `.test_cli_shipyard_subcommands_parse()`
  - Method `.test_cli_corporations_alias()`
  - Method `.test_cli_repair_and_refuel_accept_positional_amounts()`
  - Method `.test_cli_fleet_list()`
  - Method `.test_cli_upgrades_list()`
  - Method `.test_cli_contracts_list()`
  - Method `.test_cli_mastery_status()`
  - Method `.test_cli_relics()`
  - Method `.test_cli_streak()`
- `class TestCLIStabilization` - *Regression tests for numeric guards and the station consumable terminal.*
  - Method `.setUp()`
  - Method `.test_inventory_jettison_non_numeric_quantity_is_handled()`
  - Method `.test_inventory_buy_usage_without_item_id()`
  - Method `.test_inventory_buy_consumable_at_station()`
  - Method `.test_repl_repair_and_refuel_reject_non_numeric_amounts()`
- `class TestCLIRelicsWithRecoveredRelics` - *A save that already has relics must render the vault and modifiers (regression).*
  - Method `.test_relics_command_with_recovered_relics()`
  - Method `.test_cli_frontier_commands()`
- `class TestCLIMaxTrades` - *`buy <id> max` and `sell <id> all` match the REST max flag and the REPL.*
  - Method `.test_sell_all_and_buy_max()`
  - Method `.test_non_numeric_quantity_is_rejected()`

---

### [`tests/test_cockpit_layout.py`](tests/test_cockpit_layout.py)
> *Layout regression tests for the holographic web cockpit (index.html / style.css / app.js).*

**Size**: `1130` lines (`51156` bytes)

**Classes:**
- `class _DomNode` - *Minimal element tree node built from html.parser events.*
  - Method `.__init__(tag, attrs)`
  - Method `.find_by_id(element_id)`
  - Method `.ancestors()`
  - Method `.has_class(name)`
- `class _TreeBuilder`
  - Method `.__init__()`
  - Method `._append(tag, attrs, closing)`
  - Method `.handle_starttag(tag, attrs)`
  - Method `.handle_startendtag(tag, attrs)`
  - Method `.handle_endtag(tag)`
- `class TestCockpitLayout`
  - Method `.setUpClass()`
  - Method `._rule_body(selector)`
  - Method `._ancestor_ids(node)`
  - Method `._document_order()`
  - Method `.test_telemetry_log_sits_in_the_right_of_the_bottom_command_strip()`
  - Method `.test_command_strip_holds_reactor_skills_and_right_column()`
  - Method `.test_source_order_keeps_the_strip_after_the_cockpit()`
  - Method `.test_radar_settings_sit_above_the_flight_log_but_are_separate()`
  - Method `.test_radar_zoom_controls_are_vertical_with_center_in_middle()`
  - Method `.test_telemetry_log_carries_a_hide_button()`
  - Method `.test_log_collapse_style_and_toggle_wiring_exist()`
  - Method `.test_chrono_deck_is_the_last_block_of_the_top_bar()`
  - Method `.test_chrono_deck_is_pushed_to_the_right_edge()`
  - Method `.test_terminal_lives_in_the_left_deck()`
  - Method `.test_terminal_uses_a_vertical_rail_beside_the_content()`
  - Method `.test_center_column_keeps_radar_and_reactor_moves_to_bottom_strip()`
  - Method `.test_context_alerts_live_in_the_center_column()`
- `class TestCockpitRuntimeContracts` - *Static regression checks for runtime wiring that the DOM structure cannot exercise.*
  - Method `.setUpClass()`
  - Method `.test_pointer_coordinates_are_scaled_to_canvas_space()`
  - Method `.test_drag_suppresses_the_following_click()`
  - Method `.test_preload_renderers_guard_against_missing_state()`
  - Method `.test_power_sliders_sync_from_authoritative_state()`
  - Method `.test_cargo_meter_uses_manifest_volume()`
  - Method `.test_scan_sound_reads_discovery_contract()`
  - Method `.test_canvas_uses_literal_colors_not_css_variables()`
  - Method `.test_chrono_displays_calendar_date()`
- `class TestFrontierCockpitUI`
  - Method `.setUpClass()`
  - Method `.test_main_menu_and_windows_exist()`
  - Method `.test_frontier_tabs_and_radar_overlay_exist()`
  - Method `.test_frontier_renderers_are_wired()`
  - Method `.test_esc_key_toggles_main_menu()`
  - Method `.test_multiple_save_slots_ui_exists()`
  - Method `.test_nav_radar_orbital_map_is_full_viewport_background()`
  - Method `.test_radar_background_is_black()`
- `class TestCockpitEscaping`
  - Method `.setUpClass()`
  - Method `.test_dynamic_server_data_is_escaped()`
  - Method `.test_faction_colors_are_whitelisted()`
- `class TestSleekHUDDeclutter`
  - Method `.setUpClass()`
  - Method `.test_nav_radar_header_is_transparent_on_map_label()`
  - Method `.test_grid_and_label_buttons_are_bound_exactly_once()`
  - Method `.test_quick_scan_is_bound_exactly_once()`
  - Method `.test_left_terminal_is_collapsible_drawer()`
  - Method `.test_bottom_strip_log_is_compact_and_keeps_its_controls()`
  - Method `.test_ability_strip_has_icons_hotkeys_and_use_wiring()`
  - Method `.test_reactor_mode_and_vent_buttons_are_wired()`
  - Method `.test_cockpit_uses_themed_cursor_assets()`
  - Method `.test_command_strip_hotkeys_are_wired()`
- `class TestExpandableReactorAndVitalsAlignment`
  - Method `.setUpClass()`
  - Method `.test_reactor_panel_has_toggle_button_and_collapse_wiring()`
  - Method `.test_topbar_actions_line_appears_before_vitals_row()`
  - Method `.test_vital_stat_cards_have_equal_size_styling()`
- `class TestSingleLineVitalsAndDistanceParity`
  - Method `.setUpClass()`
  - Method `.test_topbar_and_vitals_wrap_on_narrow_viewports()`
  - Method `.test_vital_cards_match_chrono_box_height()`
  - Method `.test_orbit_button_uses_timed_transit()`
  - Method `.test_radar_backdrop_is_cached()`
- `class TestArsenalParityAndBulkDepotUI`
  - Method `.setUpClass()`
  - Method `.test_arsenal_contains_shipyard_and_weapons_containers()`
  - Method `.test_app_wires_chassis_and_weapon_commissioning()`
  - Method `.test_depots_support_bulk_actions()`
  - Method `.test_glassmorphic_styles_for_showroom_and_weapons()`
- `class TestStoryAndVoidCockpit` - *Story branching UI and the Hollow Between void traversal panel.*
  - Method `.setUpClass()`
  - Method `.test_story_tab_holds_objectives_choices_and_void_panel()`
  - Method `.test_story_section_source_order()`
  - Method `.test_app_wires_void_endpoints_and_renders()`
  - Method `.test_locked_story_choices_render_disabled_with_reasons()`
  - Method `.test_void_and_locked_choice_styles_exist()`
- `class TestCrewSimulationCockpit` - *Living crew telemetry: morale bars, shore leave, and cash-flow readouts.*
  - Method `.setUpClass()`
  - Method `.test_crew_tab_holds_cashflow_shore_and_roster()`
  - Method `.test_crew_section_source_order()`
  - Method `.test_app_wires_shore_leave_and_morale_bars()`
  - Method `.test_crew_simulation_styles_exist()`
- `class TestLeftTerminalLedger` - *Left terminal: one visible tab on load, keyboard tab cycling, and two-line ledger records.*
  - Method `.setUpClass()`
  - Method `._tab_contents(node)`
  - Method `.test_only_the_player_tab_is_visible_before_scripts_run()`
  - Method `.test_bracket_keys_cycle_terminal_tabs()`
  - Method `.test_ledger_records_use_three_column_two_line_grid()`
  - Method `.test_outliner_label_stays_on_one_line()`
- `class TestMarketBulkTrading` - *Commerce tab: lot selector, max orders and cost-basis feedback.*
  - Method `.setUpClass()`
  - Method `.test_lot_selector_sits_in_the_market_tab()`
  - Method `.test_max_orders_and_cost_basis_reach_the_api()`
- `class TestSettingsConsoleQoL` - *Settings console: volume, gameplay automation, interface memory, controls and reset.*
  - Method `.setUpClass()`
  - Method `.test_new_settings_live_in_the_settings_overlay_and_are_wired()`
  - Method `.test_every_sound_goes_through_the_master_gain()`
- `class TestCockpitPolling` - *Client polling contract: cached catalogs, lite payloads, adaptive cadence, guarded rebuilds.*
  - Method `.setUpClass()`
  - Method `.test_every_api_call_goes_through_the_catalog_aware_wrapper()`
  - Method `.test_poll_cadence_follows_the_chrono()`
  - Method `.test_open_tab_is_not_rebuilt_under_a_pressed_pointer()`
- `class TestCommandStripFit` - *G-005/G-013 at every width, and power routing that works without a hidden APPLY button.*
  - Method `.setUpClass()`
  - Method `._last(selector, prop)`
  - Method `.test_strip_stays_beside_a_full_height_terminal()`
  - Method `.test_strip_panels_are_not_capped_at_210px()`
  - Method `.test_power_sliders_and_presets_commit_without_the_apply_button()`
- `class TestStrategicGalaxyMap` - *Galaxy map: faction territory, war fronts and legend, fitted to the visible map area.*
  - Method `.setUpClass()`
  - Method `.test_map_views_share_one_visible_area_centre()`
  - Method `.test_territory_is_cached_and_drawn_from_politics()`
- `class TestCelestialModels` - *Procedural celestial models: their own module, loaded before the cockpit, sprites cached.*
  - Method `.setUpClass()`
  - Method `.test_renderer_loads_before_the_cockpit()`
  - Method `.test_every_generated_body_type_has_a_model()`
  - Method `.test_surface_sprites_are_cached()`
- `class TestStrategyPanels` - *Strategy actions in the cockpit: war pledges, outpost founding and the monthly treasury.*
  - Method `.setUpClass()`
  - Method `.test_wars_panel_sits_in_the_factions_tab_and_pledges()`
  - Method `.test_only_your_own_wars_offer_a_ceasefire_petition()`
  - Method `.test_open_space_anchor_draws_the_flagship_and_prices_from_the_anchor()`
  - Method `.test_third_party_wars_never_expose_a_player_peace_button()`
  - Method `.test_outposts_are_founded_from_the_empire_tab()`
  - Method `.test_treasury_is_reported_per_month()`
- `class TestPostPushPolishLayout` - *Contract header readability, compact reactor strip and deterministic surface scenario.*
  - Method `.setUpClass()`
  - Method `.test_target_card_scrolls_instead_of_spilling_at_short_viewports()`
  - Method `.test_target_card_reports_population_capacity_and_world_tech()`
  - Method `.test_contract_header_stacks_short_badge_above_unclamped_title_at_narrow_widths()`
  - Method `.test_compact_reactor_strip_uses_four_proportional_tracks()`
  - Method `.test_surface_ops_scrolls_target_card_and_browser_driver_prepares_surface()`
  - Method `.test_waypoint_review_prepares_an_open_space_anchor()`
  - Method `.test_factions_review_prepares_a_coalition_war_for_the_petition_control()`
  - Method `.test_every_click_has_a_stable_handle_for_automation()`
  - Method `.test_aikit_link_and_decision_cadence_are_visible()`
  - Method `.test_browser_review_proves_every_click_has_a_unique_handle()`
  - Method `.test_every_static_button_can_be_identified_by_a_headless_driver()`
  - Method `.test_event_toasts_clear_the_left_terminal_at_720p()`
  - Method `.test_scroll_cue_text_meets_the_twelve_pixel_floor()`
  - Method `.test_compact_command_strip_controls_meet_the_24px_target()`
- `class TestTerminalDeckScrolling` - *Long terminal tabs must scroll inside the deck instead of running off-screen.*
  - Method `.setUpClass()`
  - Method `.test_active_tab_content_scrolls_within_the_left_deck()`
  - Method `.test_left_deck_stretches_its_rows_so_the_scroll_area_has_a_height()`
  - Method `.test_faction_list_fills_the_deck_instead_of_a_pixel_cap()`
  - Method `.test_dyson_shell_replaces_the_star_corona()`
  - Method `.test_more_below_cue_is_a_real_element_not_the_decorative_frame()`
  - Method `.test_cue_also_watches_inner_tab_scrollers()`
- `class TestFactionEconomyCard` - *The faction card must show where money comes from and where it goes.*
  - Method `.setUpClass()`
  - Method `.test_card_lists_tax_trade_industry_and_upkeep()`
  - Method `.test_breakdown_wraps_between_figures_not_mid_value()`
  - Method `.test_card_shows_positive_net_in_green()`
  - Method `.test_card_shows_trade_partners_and_tech_progress()`

---

### [`tests/test_combat_void_depth.py`](tests/test_combat_void_depth.py)
> *Regression tests for progression-scaled combat and Hollow resonance risk/reward.*

**Size**: `286` lines (`12577` bytes)

**Classes:**
- `class TestProgressionThreatScaling`
  - Method `.test_threat_multiplier_starts_flat_and_grows()`
  - Method `.test_generated_enemy_scales_with_threat_level()`
  - Method `.test_dreadnought_boss_is_gated_behind_mastery()`
- `class TestEarlyCombatRisk`
  - Method `.test_a_marauder_costs_hull_to_a_fresh_corvette()`
  - Method `.test_defensive_actions_also_end_in_defeat()`
  - Method `.test_a_destroyed_ship_cannot_tick_back_to_life()`
  - Method `.test_zero_hull_ends_combat_as_a_defeat_without_bounty()`
- `class TestEvasiveBurnDiscipline`
  - Method `._engine(fuel, streak, combo)`
  - Method `.test_successful_evasive_burn_costs_fuel_and_resets_streak()`
  - Method `.test_failed_evasive_burn_still_burns_fuel_and_keeps_combat()`
  - Method `.test_evasive_burn_requires_fuel()`
- `class TestVoidResonance`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `._traversal(started, arrival, resonance, stability)`
  - Method `._set_void_ship(traversal, credits, visited)`
  - Method `.test_resonance_defaults_and_roundtrips()`
  - Method `.test_storm_accumulates_resonance_with_low_stability_premium()`
  - Method `.test_status_projects_resonance_payout()`
  - Method `.test_arrival_pays_resonance_credits_and_xp()`
  - Method `.test_emergency_emerge_pays_only_prorated_resonance()`
  - Method `.test_cli_and_cockpit_expose_resonance()`

---

### [`tests/test_economy.py`](tests/test_economy.py)
> *Unit tests for the dynamic galactic economy, stockpiles, events, and trade routes.*

**Size**: `233` lines (`10832` bytes)

**Classes:**
- `class TestInitialEconomy` - *Verify baseline economy generation across the galaxy.*
  - Method `.setUp()`
  - Method `.test_every_system_has_a_market()`
  - Method `.test_stockpiles_are_positive()`
  - Method `.test_initial_event_is_seeded()`
- `class TestTickGlobalEconomy` - *Verify production, consumption, event decay, and last-updated tracking.*
  - Method `.setUp()`
  - Method `.test_production_and_consumption_rates_apply()`
  - Method `.test_last_updated_tick_advances()`
  - Method `.test_events_decay_and_expire()`
- `class TestDynamicMarketQuotes` - *Verify localized quote computation and profitable route discovery.*
  - Method `.setUp()`
  - Method `.test_quote_has_positive_spread()`
  - Method `.test_events_shift_local_prices()`
  - Method `.test_trade_routes_are_sorted_and_cross_system()`
  - Method `.test_faction_standing_influences_quote()`
  - Method `.test_same_station_trade_cannot_arbitrage()`
  - Method `.test_same_station_reorbit_keeps_the_arbitrage_guard()`
  - Method `.test_new_game_clears_and_load_preserves_the_arbitrage_guard()`
  - Method `.test_load_does_not_reopen_same_station_arbitrage()`
  - Method `.test_friendly_standing_is_applied_once_on_purchase()`
  - Method `.test_friendly_standing_cannot_arbitrage_locally()`
  - Method `.test_sell_from_depot_uses_dynamic_quote_and_updates_stockpiles()`

---

### [`tests/test_empire_character_fleet.py`](tests/test_empire_character_fleet.py)
> *Regression tests for character, research, outposts, factions, fleet, and travel additions.*

**Size**: `391` lines (`18610` bytes)

**Classes:**
- `class CharacterResearchOutpostTest`
  - Method `.setUp()`
  - Method `.test_character_state_round_trip_and_age()`
  - Method `.test_train_skill_requires_points_and_valid_skill()`
  - Method `.test_emergency_repair_ability_heals_and_sets_cooldown()`
  - Method `.test_high_skill_unlocks_the_late_abilities()`
  - Method `.test_overclock_is_a_timed_reactor_surge()`
  - Method `.test_research_project_completes_on_tick()`
  - Method `.test_unknown_research_project_rejected()`
  - Method `.test_outpost_builds_and_produces_on_tick()`
  - Method `.test_outpost_requires_orbit()`
  - Method `.test_outposts_pay_back_over_multiple_months()`
  - Method `.test_outpost_upgrade_costs_less_than_building_and_adds_quarter_output()`
  - Method `.test_old_outposts_use_the_current_catalog_yields()`
  - Method `.test_commander_creation_reconciles_rank_seven_unlocks()`
  - Method `.test_constructor_reconciles_rank_seven_unlocks()`
  - Method `.test_overclock_surge_decays_once_per_combat_turn()`
  - Method `.test_loading_an_old_save_reconciles_rank_seven_unlocks()`
  - Method `.test_failed_ability_checks_do_not_burn_the_cooldown()`
  - Method `.test_snapshot_exposes_ability_cooldown_totals()`
  - Method `.test_old_reactor_saves_default_the_surge_fields()`
- `class FactionDiplomacyWarTest`
  - Method `.setUp()`
  - Method `.test_leaders_generated_deterministically()`
  - Method `.test_diplomacy_improve_and_no_captain_declared_war()`
  - Method `.test_resolve_wars_captures_and_eliminates_faction()`
- `class FleetAndNavigationTest`
  - Method `.setUp()`
  - Method `.test_escort_purchase_requires_credits_and_dock()`
  - Method `.test_fleet_damage_and_casualties()`
  - Method `.test_battle_stance_and_solar_panel_upgrade()`
  - Method `.test_route_planning()`
  - Method `.test_black_holes_and_ring_worlds_exist()`
- `class NewSystemsSerializationAndCLITest`
  - Method `.test_snapshot_outpost_options_match_what_the_server_accepts()`
  - Method `.test_game_state_round_trip_preserves_new_fields()`
  - Method `.test_new_cli_commands_run()`
  - Method `.test_cockpit_fleet_character_empire_and_void_fade_wiring()`

---

### [`tests/test_engine.py`](tests/test_engine.py)
> *Unit tests for simulation engine state transitions, flight, upgrades, fleet, and combat.*

**Size**: `428` lines (`17988` bytes)

**Classes:**
- `class TestEngine`
  - Method `.setUp()`
  - Method `.test_initial_state()`
  - Method `.test_jump_valid_and_invalid()`
  - Method `.test_orbit_and_scan()`
  - Method `.test_power_routing()`
  - Method `.test_trade_buy_and_sell()`
  - Method `.test_upgrades_purchase_and_bonus()`
  - Method `.test_fleet_drone_operations()`
  - Method `.test_combat_resolution_victory_and_flee()`
  - Method `.test_contracts_progression_and_claiming()`
  - Method `.test_pilot_mastery_and_talents()`
  - Method `.test_expedition_streak_and_combos()`
  - Method `.test_tick_decays_combat_ability_cooldown()`
  - Method `.test_trade_respects_cargo_volume_not_just_units()`
  - Method `.test_available_chassis_excludes_current_ship()`
  - Method `.test_starter_chassis_cannot_be_repurchased()`
  - Method `.test_sell_upgrade_removes_module_name_from_manifest()`
  - Method `.test_buy_item_requires_station_and_consumable()`
  - Method `.test_buy_ship_chassis_rejects_if_cargo_exceeds_new_capacity()`
  - Method `.test_sell_upgrade_rejects_if_cargo_exceeds_reduced_capacity()`
  - Method `.test_remove_ship_mod_rejects_if_cargo_exceeds_reduced_capacity()`
  - Method `.test_quantum_travel_fuel_cost_applies_fuel_efficiency_bonuses()`

---

### [`tests/test_engine_hardening.py`](tests/test_engine_hardening.py)
> *Regression tests for audit-driven engine hardening.*

**Size**: `178` lines (`7324` bytes)

**Classes:**
- `class EngineHardeningTest`
  - Method `.setUp()`
  - Method `._set_ship(**kwargs)`
  - Method `._orbit_station()`
  - Method `.test_repair_rejects_zero_and_negative_amounts()`
  - Method `.test_refuel_rejects_zero_and_negative_amounts()`
  - Method `.test_upgrade_recompute_preserves_relic_max_hull()`
  - Method `.test_chassis_purchase_preserves_relic_max_shield()`
  - Method `.test_scan_awards_random_max_hull_relic_immediately()`
  - Method `.test_scan_and_step_preserve_dominant_corp()`
  - Method `.test_replacing_an_occupied_upgrade_slot_is_rejected()`
  - Method `.test_drone_harvest_rejects_when_cargo_hold_is_full()`
  - Method `.test_repeat_scan_of_surveyed_body_awards_no_bounty()`
  - Method `.test_story_choice_updates_faction_standing()`
  - Method `.test_buy_drone_rejects_unknown_system()`
  - Method `.test_cargo_grant_clamps_to_free_volume()`
  - Method `.test_combat_salvage_respects_full_cargo_hold()`

---

### [`tests/test_equipment_bonuses.py`](tests/test_equipment_bonuses.py)
> *Regression tests for hardware module stat bonuses and chassis specialty perks.*

**Size**: `173` lines (`7518` bytes)

**Classes:**
- `class TestEquipmentBonusAggregation` - *Verify the pure aggregation rules without touching engine state.*
  - Method `.setUp()`
  - Method `._bonuses(**ship_kwargs)`
  - Method `.test_bare_starter_ship_has_neutral_bonuses()`
  - Method `.test_engine_module_reduces_fuel_multiplier()`
  - Method `.test_sensor_modules_add_scan_and_relic_bonuses()`
  - Method `.test_utility_modules_expose_shield_and_ecm_bonuses()`
  - Method `.test_chassis_specialty_perks_are_mapped()`
- `class TestEngineEquipmentIntegration` - *Verify the engine actually consumes the aggregated bonuses.*
  - Method `._jump_fuel_used(equipped)`
  - Method `.test_warp_booster_reduces_jump_fuel_burn()`
  - Method `._scan_bounty(equipped)`
  - Method `.test_deep_core_scanner_increases_scan_bounty()`
  - Method `._sell_revenue(ship_class)`
  - Method `.test_freighter_chassis_boosts_trade_margin()`
  - Method `._enemy_hull_after_shot(equipped, ship_class)`
  - Method `.test_weapon_module_and_gunship_chassis_add_combat_damage()`
  - Method `._shield_recharged(equipped)`
  - Method `.test_reactive_shield_regenerator_adds_tick_recharge()`
  - Method `._combat_after_jump(equipped)`
  - Method `.test_ecm_scrambler_reduces_pirate_encounter_chance()`

---

### [`tests/test_exploration_depth.py`](tests/test_exploration_depth.py)
> *Regression tests for exploration depth: survey completion, scan discipline, salvage contracts, and scoop reserves.*

**Size**: `207` lines (`8634` bytes)

**Classes:**
- `class TestScanDiscipline`
  - Method `.setUp()`
  - Method `.test_zero_sensor_power_does_not_consume_a_scan()`
  - Method `.test_full_system_survey_awards_bonus_and_codex_progress()`
- `class TestSalvageContractSynergy`
  - Method `.setUp()`
  - Method `.test_titanium_salvage_advances_mining_contract()`
- `class TestVolatileReserve`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `._star()`
  - Method `.test_reserve_is_deterministic_and_type_limited()`
  - Method `.test_legacy_body_defaults_to_untapped()`
  - Method `.test_negative_volatile_counters_are_clamped_on_load()`
  - Method `.test_far_future_recharge_tick_is_capped_to_one_interval()`
  - Method `.test_recharge_schedule_is_exact_and_not_boundary_aligned()`
  - Method `.test_large_tick_jump_recharges_multiple_pending_taps()`
  - Method `.test_scoop_depletes_reservoir_then_recharges()`
  - Method `.test_snapshot_exposes_reserve_and_depletion()`

---

### [`tests/test_faction_trade_tech.py`](tests/test_faction_trade_tech.py)
> *Faction trade links and technology drift across the simulation.*

**Size**: `169` lines (`6330` bytes)

**Classes:**
- `class TestTradeLinks`
  - Method `.setUpClass()`
  - Method `.test_peaceful_neighbours_trade()`
  - Method `.test_every_link_crosses_a_hyperlane_between_the_two_owners()`
  - Method `.test_war_severs_the_route()`
  - Method `.test_each_faction_keeps_at_most_three_partners()`
  - Method `.test_route_pays_half_its_volume_to_each_endpoint()`
  - Method `.test_partner_names_are_canonical_names()`
  - Method `.test_trade_links_round_trip_in_a_save()`
- `class TestTechnologyDrift`
  - Method `.setUpClass()`
  - Method `.test_research_accumulates_into_a_new_tech_level()`
  - Method `.test_tech_never_exceeds_the_cap()`
  - Method `.test_economy_carries_trade_partners_and_income()`
  - Method `.test_worlds_drift_up_and_capacity_follows()`
  - Method `.test_faction_tech_levels_advance_over_time()`

**Functions:**
- `def _pair(link)`

---

### [`tests/test_factions_and_enemies.py`](tests/test_factions_and_enemies.py)
> *Unit tests for Factions, Corporations, and Enhanced Combat Enemies.*

**Size**: `255` lines (`10181` bytes)

**Classes:**
- `class TestFactionsAndCorporations` - *Test faction registries, corporations, standing calculations, and market modifiers.*
  - Method `.test_canonical_factions_exist()`
  - Method `.test_canonical_corporations_exist()`
  - Method `.test_faction_standing_tiers()`
  - Method `.test_market_modifiers()`
- `class TestEnemiesAndCombatModels` - *Test enemy archetypes, generation, and extended CombatEncounter model.*
  - Method `.test_enemy_archetypes()`
  - Method `.test_generate_system_enemy()`
  - Method `.test_combat_encounter_backward_compatibility()`
  - Method `.test_ship_state_faction_standings_migration()`
  - Method `.test_tactical_combat_shield_and_actions()`
  - Method `.test_combat_victory_faction_standing_shift()`

---

### [`tests/test_frontier_depth.py`](tests/test_frontier_depth.py)
> *Frontier depth: pirates, decisions, quantum freight, surface ops, populations, and UI affordances.*

**Size**: `424` lines (`21225` bytes)

**Classes:**
- `class FrontierContentTest`
  - Method `.test_galaxy_has_more_systems_factions_and_anomalies()`
  - Method `.test_populations_are_realistic_and_devastation_kills_growth()`
  - Method `.test_war_capture_devastates_and_displaces_population()`
  - Method `.test_every_anomaly_has_a_power_free_escape()`
  - Method `.test_new_state_fields_survive_save_round_trip()`
  - Method `.test_initial_standings_include_frontier_powers()`
  - Method `.test_contract_board_has_new_categories()`
- `class PirateEncounterTest`
  - Method `.test_risk_rises_in_havens()`
  - Method `.test_pay_fight_and_evade_paths()`
- `class DecisionEventTest`
  - Method `.test_at_least_twenty_five_conditional_events()`
  - Method `.test_pending_decision_blocks_time_until_resolved()`
  - Method `.test_decisions_are_rate_limited_by_the_cadence_window()`
  - Method `.test_cadence_choices_and_snapshot()`
  - Method `.test_cadence_is_persisted_with_the_save()`
  - Method `.test_low_hull_event_is_eligible()`
- `class QuantumFreightTest`
  - Method `.test_freight_costs_fee_arrives_later_and_progresses_delivery_contract()`
  - Method `.test_quantum_report_lists_lanes()`
- `class SurfaceOperationTest`
  - Method `.test_landing_opens_choices_and_marks_site_branch_worked()`
- `class FrontierUiContractTest`
  - Method `.test_cockpit_has_new_mechanics_surfaces()`
  - Method `.test_source_files_have_no_mojibake()`
- `class FrontierApiTest`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.setUp()`
  - Method `._request(method, path, payload)`
  - Method `.test_get_quantum_and_surface_report()`
  - Method `.test_refresh_contracts_endpoint()`
  - Method `.test_pending_decision_blocks_and_resolves_over_rest()`
  - Method `.test_pirate_resolve_endpoint()`
- `class PirateLockTest`
  - Method `.test_active_pirate_blocks_tick_flight_and_trade_until_resolved()`
  - Method `.test_surface_cargo_reports_display_names()`

---

### [`tests/test_frontier_systems.py`](tests/test_frontier_systems.py)
> *Coverage for frontier systems: AI captains, depots, messages, landing, and fleets.*

**Size**: `264` lines (`11497` bytes)

**Classes:**
- `class FrontierBootstrapTest`
  - Method `.setUp()`
  - Method `.test_initial_state_has_captains_depots_and_messages()`
  - Method `.test_save_round_trip_preserves_frontier_state()`
  - Method `.test_quest_panel_contains_story_and_contracts()`
- `class AICaptainTest`
  - Method `.setUp()`
  - Method `.test_ai_trade_moves_captains_and_changes_stockpiles()`
  - Method `.test_hail_increases_trust()`
  - Method `.test_alliance_requires_trust_then_adds_ally()`
  - Method `.test_ai_trade_with_captain_changes_both_cargo_holds()`
- `class DepotTest`
  - Method `.setUp()`
  - Method `.test_deposit_withdraw_and_sell_from_depot()`
  - Method `.test_snapshot_reports_depot_used_volume()`
- `class QuantumMessageTest`
  - Method `.setUp()`
  - Method `.test_send_and_read_message()`
- `class LandingAndFleetTest`
  - Method `.setUp()`
  - Method `.test_landing_on_habitable_body()`
  - Method `.test_landing_rejected_on_uninhabitable_body()`
  - Method `.test_hire_refit_and_dismiss_mercenary()`
  - Method `.test_drone_stats_survive_ticks_and_deploy()`
- `class TalentBranchTest`
  - Method `.setUp()`
  - Method `.test_tier_two_requires_branch_root()`
  - Method `.test_every_talent_declares_branch_and_tier()`
- `class ProceduralGalaxyTest`
  - Method `.test_new_star_types_moons_and_planet_types()`
  - Method `.test_moon_model_round_trip()`
  - Method `.test_depot_model_round_trip()`
  - Method `.test_quantum_message_model_round_trip()`

---

### [`tests/test_galactic_politics.py`](tests/test_galactic_politics.py)
> *Galactic politics: power-driven wars over hyperlane fronts, peace treaties and player war support.*

**Size**: `369` lines (`17973` bytes)

**Classes:**
- `class FixedRng` - *Noise-free rng: uniform returns a fixed value, choice takes the first item.*
  - Method `.__init__(value)`
  - Method `.uniform(low, high)`
  - Method `.choice(seq)`
- `class TestWarFronts`
  - Method `.setUp()`
  - Method `._war(**kwargs)`
  - Method `.test_frontier_is_loser_territory_adjacent_to_the_winner()`
  - Method `.test_capture_takes_a_front_system_and_spends_the_score()`
  - Method `.test_no_front_means_no_capture()`
  - Method `._assign(owners)`
  - Method `.test_more_core_territory_means_more_war_effort()`
  - Method `.test_overextension_caps_war_effort()`
  - Method `.test_a_hegemon_faces_containment()`
  - Method `.test_last_stand_bonus_does_not_empower_the_besieged_attacker()`
  - Method `.test_capital_needs_double_score()`
  - Method `.test_the_capital_holds_while_the_defender_still_owns_other_worlds()`
  - Method `.test_a_defending_faction_is_not_dogpiled()`
  - Method `.test_exhaustion_ends_the_war_with_a_treaty()`
  - Method `.test_old_war_records_load_with_defaults()`
- `class TestWarSupport`
  - Method `.test_support_spends_credits_shifts_score_and_standing()`
  - Method `.test_support_is_refused_when_it_cannot_apply()`
  - Method `.test_snapshot_exposes_territory_and_fronts()`
- `class TestCaptainDiplomacyLimits` - *A privateer captain petitions; they never command sovereign war and peace.*
  - Method `.test_a_captain_cannot_declare_war()`
  - Method `.test_cannot_petition_a_war_you_are_not_in()`
  - Method `.test_petition_needs_the_envoy_fee()`
  - Method `.test_petition_acceptance_ends_the_war_and_charges_the_envoy()`
  - Method `.test_petition_refusal_is_reported_and_costs_nothing()`
  - Method `.test_petition_odds_rise_with_standing_and_diplomacy()`
  - Method `.test_a_losing_side_is_more_willing_to_talk_than_a_winning_one()`
- `class TestWarSupportParity`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.test_rest_support()`
  - Method `.test_cli_war_list_and_support()`
  - Method `.test_rest_ceasefire_is_a_petition()`
  - Method `.test_cli_diplomacy_cannot_declare_war()`
  - Method `.test_cli_war_list_marks_your_own_wars()`

**Functions:**
- `def _owner_ids(systems, name)`
- `def _engine_at_war(credits)`
- `def _engine_third_party_war(credits, war_score, active)`

---

### [`tests/test_galaxy.py`](tests/test_galaxy.py)
> *Unit tests for procedural galaxy generation, hyperlane mesh, and market quotes.*

**Size**: `88` lines (`3742` bytes)

**Classes:**
- `class TestGalaxy`
  - Method `.test_galaxy_generation_determinism()`
  - Method `.test_hyperlane_connectivity()`
  - Method `.test_market_quotes_calculation()`
  - Method `.test_random_anomaly_generation()`
  - Method `.test_population_mechanics_and_colony_tiers()`
  - Method `.test_orbit_and_sublight_distance_parity()`

---

### [`tests/test_inventory.py`](tests/test_inventory.py)
> *Unit tests for the item catalog, cargo manifest, and consumable usage.*

**Size**: `109` lines (`4115` bytes)

**Classes:**
- `class TestItemCatalog` - *Verify catalog integrity, consumable metadata, and fallbacks.*
  - Method `.test_catalog_keys_match_item_ids()`
  - Method `.test_consumables_are_usable_with_effects()`
  - Method `.test_commodities_are_not_usable()`
  - Method `.test_unknown_item_falls_back_to_generic_commodity()`
  - Method `.test_manifest_skips_empty_stacks_and_computes_volume()`
  - Method `.test_cargo_volume_sums_item_footprints()`
- `class TestUseItem` - *Verify consumable effects, clamping, and cargo bookkeeping.*
  - Method `.setUp()`
  - Method `._with_cargo(cargo, **ship_kwargs)`
  - Method `.test_repair_paste_restores_hull_and_consumes_one()`
  - Method `.test_last_repair_paste_leaves_cargo()`
  - Method `.test_repair_paste_clamps_to_max_hull()`
  - Method `.test_use_missing_item_fails()`
  - Method `.test_commodity_cannot_be_consumed()`
  - Method `.test_decoy_requires_active_combat()`

---

### [`tests/test_logbook.py`](tests/test_logbook.py)
> *Flight-log windowing: galactic news must outlive routine AI-trade chatter.*

**Size**: `140` lines (`5962` bytes)

**Classes:**
- `class SummarizeTradesTest`
  - Method `.test_two_captain_lines_become_one_summary()`
  - Method `.test_summary_keeps_the_position_of_the_first_trade_line()`
  - Method `.test_lines_that_are_not_trades_pass_through()`
- `class NotableNewsTest`
  - Method `.test_war_news_is_notable()`
  - Method `.test_routine_chatter_is_not_notable()`
  - Method `.test_trade_spam_cannot_evict_a_capture()`
  - Method `.test_the_newest_half_of_the_log_always_survives()`
  - Method `.test_older_news_is_not_promoted_past_newer_news()`
  - Method `.test_trim_keeps_the_newest_lines_when_nothing_is_notable()`
  - Method `.test_short_logs_are_untouched()`
- `class WarNewsEventsTest`
  - Method `.test_capture_and_treaty_become_notifications()`
  - Method `.test_declarations_stay_in_the_log_only()`
  - Method `.test_at_most_two_events_per_tick()`
  - Method `.test_an_undismissed_duplicate_is_not_repeated()`
  - Method `.test_a_dismissed_event_may_be_announced_again()`
- `class WarReachesThePlayerTest`
  - Method `.test_a_simulated_campaign_shows_a_war_headline_to_the_player()`
  - Method `.test_trade_chatter_is_summarized_once_per_tick()`
  - Method `.test_log_never_exceeds_its_limit()`

---

### [`tests/test_messaging_crew_quantum.py`](tests/test_messaging_crew_quantum.py)
> *Regression tests for message trees, crew, portraits, weapons, quantum tech, and megastructures.*

**Size**: `215` lines (`9835` bytes)

**Classes:**
- `class MessageTreeTest`
  - Method `.setUp()`
  - Method `.test_tree_root_is_seeded_and_has_branches()`
  - Method `.test_decode_branch_grants_research_and_follow_up()`
  - Method `.test_sell_branch_grants_credits()`
  - Method `.test_choice_cannot_be_replayed()`
  - Method `.test_message_model_round_trip_with_choices()`
  - Method `.test_tree_catalog_has_multiple_trees()`
- `class CrewWeaponTest`
  - Method `.setUp()`
  - Method `.test_starting_crew_and_bonuses()`
  - Method `.test_recruit_and_dismiss_crew()`
  - Method `.test_crew_round_trip_and_catalog()`
  - Method `.test_weapon_variety_and_install()`
  - Method `.test_weapon_requires_credits()`
  - Method `.test_combat_misfire_telemetry_preserves_weapon_misfire_description()`
  - Method `.test_non_weapon_strike_reports_enemy_evasion()`
- `class QuantumAndObjectsTest`
  - Method `.test_quantum_research_projects_exist()`
  - Method `.test_dyson_sphere_relay_wormhole_and_collector_exist()`
  - Method `.test_character_portrait_and_era()`
  - Method `.test_cli_new_systems_commands()`
  - Method `.test_cockpit_message_choices_crew_portrait_wiring()`

---

### [`tests/test_models.py`](tests/test_models.py)
> *Unit tests for domain state models and frozen DTO serialization.*

**Size**: `323` lines (`10912` bytes)

**Classes:**
- `class TestModels`
  - Method `.test_ship_power_validation()`
  - Method `.test_celestial_body_serialization()`
  - Method `.test_star_system_serialization()`
  - Method `.test_fleet_drone_serialization()`
  - Method `.test_ship_upgrade_serialization()`
  - Method `.test_combat_encounter_serialization()`
  - Method `.test_bounty_contract_serialization()`
  - Method `.test_precursor_relic_serialization()`
  - Method `.test_pilot_mastery_serialization()`
  - Method `.test_game_state_roundtrip()`
  - Method `.test_tutorial_and_story_models_serialization()`

---

### [`tests/test_monthly_economy.py`](tests/test_monthly_economy.py)
> *Monthly economy: crew wages are a monthly rate accrued on the calendar, not a per-tick charge.*

**Size**: `43` lines (`1833` bytes)

**Classes:**
- `class TestMonthlyWages`
  - Method `.test_tick_crew_charges_exactly_the_wage_due()`
  - Method `.test_a_new_commander_pays_one_month_of_wages_per_month()`
  - Method `.test_cash_flow_reports_monthly_rates()`
  - Method `.test_month_end_report_is_logged_once_per_month()`

---

### [`tests/test_navigation_traffic.py`](tests/test_navigation_traffic.py)
> *Open-space transit vectors and the NPC traffic that shares the map.*

**Size**: `122` lines (`5717` bytes)

**Classes:**
- `class EmptySpaceTransitTest`
  - Method `.test_waypoint_transit_does_not_promise_an_orbit()`
  - Method `.test_arrival_holds_station_in_open_space()`
  - Method `.test_leaving_open_space_prices_the_transit_from_the_anchor()`
  - Method `.test_orbiting_a_body_clears_the_open_space_anchor()`
  - Method `.test_waypoint_is_refused_outside_the_transit_envelope()`
  - Method `.test_a_second_vector_cannot_be_plotted_mid_flight()`
  - Method `.test_survey_and_orbit_actions_need_a_body()`
  - Method `.test_waypoint_survives_a_save_round_trip()`
- `class NpcTrafficTest`
  - Method `.test_every_captain_has_a_place_on_the_map()`

---

### [`tests/test_perks_relics_rep.py`](tests/test_perks_relics_rep.py)
> *Regression tests for faction perks, enemy reputation rewards, and multi-stat relics.*

**Size**: `135` lines (`5862` bytes)

**Classes:**
- `class FactionPerkTest`
  - Method `.setUp()`
  - Method `._set_standing(faction_id, standing)`
  - Method `.test_friendly_faction_grants_repair_discount()`
  - Method `.test_allied_faction_grants_free_refuel()`
  - Method `.test_syndicate_standing_adds_trade_margin()`
  - Method `.test_faction_specific_tier_perks()`
- `class EnemyRepRewardTest`
  - Method `._victory(archetype_id)`
  - Method `.test_warlord_rep_rewards_are_applied()`
  - Method `.test_corporate_rep_rewards_update_corp_standings()`
- `class MultiStatRelicTest`
  - Method `.test_relic_bonuses_round_trip()`
  - Method `.test_eye_of_void_boosts_laser_and_scan()`
  - Method `.test_core_matrix_boosts_fuel_and_laser()`
  - Method `.test_sentinel_matrix_applies_hull_and_shield()`
- `class BackgroundServerTest`
  - Method `.test_background_server_starts_and_stops()`

---

### [`tests/test_population_economy.py`](tests/test_population_economy.py)
> *Population capacity, technology limits, wartime devastation and faction treasuries.*

**Size**: `373` lines (`16481` bytes)

**Classes:**
- `class FixedZeroRng` - *Random source that always fires the attrition roll and returns zero noise.*
  - Method `.random()`
  - Method `.uniform(low, high)`
- `class TestPopulationCapacity`
  - Method `.test_generated_worlds_are_normalized_to_their_capacity()`
  - Method `.test_technology_and_habitability_raise_capacity()`
  - Method `.test_batched_ticks_never_overshoot_capacity()`
  - Method `.test_growth_stops_at_capacity_and_devastation_reverses_it()`
  - Method `.test_civil_order_changes_population_growth()`
  - Method `.test_devastation_recovery_scales_with_tech_and_order()`
  - Method `.test_dyson_swarm_is_a_small_maintenance_population_not_a_planet()`
  - Method `.test_swarm_physics_describe_habitats_not_a_planet_surface()`
- `class TestWarDevastation`
  - Method `.test_front_worlds_lose_people_and_gain_devastation()`
- `class TestFactionEconomy`
  - Method `.test_capture_retunes_worlds_to_the_new_owner_technology()`
  - Method `.test_broke_faction_cannot_open_a_new_front()`
  - Method `.test_outposts_grow_to_their_housing_ceiling_and_stop()`
  - Method `.test_cockpit_capacity_constant_matches_python()`
  - Method `.test_batched_resolution_advances_wars_across_the_batch()`
  - Method `.test_bankrupt_faction_sues_for_peace()`
  - Method `.test_solvent_factions_keep_fighting()`
  - Method `.test_every_surviving_faction_has_a_treasury_and_cash_flow()`
  - Method `.test_war_adds_upkeep_and_reduces_net_income()`
  - Method `.test_tick_pays_income_into_the_treasury()`
  - Method `.test_faction_economies_survive_a_game_state_round_trip()`
  - Method `.test_legacy_save_without_capacity_migrates_once()`
  - Method `.test_batched_tick_still_declares_wars_and_scars_worlds()`
  - Method `.test_reload_does_not_repopulate_a_war_killed_world()`
  - Method `.test_war_tick_lowers_front_population()`

---

### [`tests/test_reactor_map_shipmods.py`](tests/test_reactor_map_shipmods.py)
> *Regression tests for reactor simulation, sector map modifiers, and ship modifications.*

**Size**: `330` lines (`14316` bytes)

**Classes:**
- `class ReactorSimulationTest`
  - Method `.setUp()`
  - Method `.test_reactor_state_round_trip()`
  - Method `.test_ship_state_round_trip_preserves_reactor_and_mods()`
  - Method `.test_overdrive_heats_core_and_economy_recovers()`
  - Method `.test_vent_purges_heat_and_enforces_cooldown()`
  - Method `.test_heat_derates_effective_subsystem_power()`
  - Method `.test_reactor_repair_requires_dock()`
  - Method `.test_reactor_report_exposes_modes_and_cooling()`
- `class MapModifierTest`
  - Method `.test_map_modifier_round_trip()`
  - Method `.test_star_system_round_trip_preserves_modifiers()`
  - Method `.engine_body()`
  - Method `.test_generation_is_deterministic_and_non_empty()`
  - Method `.test_aggregate_combines_multiplicative_and_additive_effects()`
  - Method `.test_map_modifier_generation_uses_seed()`
- `class ShipModificationTest`
  - Method `.setUp()`
  - Method `.test_catalog_declares_valid_slots_and_effects()`
  - Method `.test_install_and_remove_mod_recomputes_capacities()`
  - Method `.test_remove_rejects_module_id_that_is_not_installed()`
  - Method `.test_slot_conflict_rejected()`
  - Method `.test_overcharged_core_raises_reactor_output()`
  - Method `.test_ship_mods_require_dock()`
  - Method `.test_ship_mod_report_lists_catalog_and_bonuses()`
  - Method `.test_upgrade_recompute_preserves_ship_mod_capacities()`
  - Method `.test_snapshot_exposes_reactor_map_and_ship_mods()`
- `class NewCLIAndCockpitWiringTest`
  - Method `.test_cli_runs_new_simulation_commands()`
  - Method `.test_cockpit_contains_ship_mod_and_reactor_controls()`
- `class ShipDossierLegibilityTest` - *The 48px silhouette cases and the narrow catalog rows must stay readable.*
  - Method `.setUpClass()`
  - Method `.test_every_slot_has_a_code_that_fits_the_case()`
  - Method `.test_report_ships_slot_codes_to_the_cockpit()`
  - Method `.test_status_snapshot_also_carries_the_slot_codes()`
  - Method `.test_silhouette_cases_show_the_code_and_a_real_wrench_glyph()`
  - Method `.test_catalog_names_wrap_instead_of_losing_words()`
  - Method `.test_research_rows_align_their_cost_and_start_button()`

---

### [`tests/test_server.py`](tests/test_server.py)
> *Unit and integration tests for embedded HTTP server REST endpoints.*

**Size**: `410` lines (`18125` bytes)

**Classes:**
- `class TestServer`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.setUp()`
  - Method `._get(path)`
  - Method `._post(path, body)`
  - Method `._post_raw(path, payload, content_type)`
  - Method `.test_get_static_index()`
  - Method `.test_get_api_state()`
  - Method `.test_get_api_galaxy()`
  - Method `.test_reactor_map_and_shipmod_endpoints()`
  - Method `.test_new_game_applies_commander_profile()`
  - Method `.test_new_game_rejects_over_budget_commander_profile()`
  - Method `.test_character_research_fleet_diplomacy_endpoints()`
  - Method `.test_crew_weapon_and_message_tree_endpoints()`
  - Method `.test_post_power()`
  - Method `.test_post_travel_preview()`
  - Method `.test_post_orbit_and_scan()`
  - Method `.test_post_drone_and_upgrade_endpoints()`
  - Method `.test_contracts_and_relics_endpoints()`
  - Method `.test_malformed_json_is_rejected()`
  - Method `.test_non_object_json_is_rejected()`
  - Method `.test_wrong_field_type_is_rejected()`
  - Method `.test_negative_repair_and_refuel_are_rejected()`
  - Method `.test_trade_rejects_non_boolean_is_buy()`
  - Method `.test_step_rejects_negative_and_non_finite_delta()`
  - Method `.test_scan_response_exposes_relic_and_near_miss()`
  - Method `.test_reset_is_deterministic_for_a_seed()`
  - Method `.test_get_api_shipyard_excludes_current_chassis()`
  - Method `.test_post_inventory_buy_rejects_non_numeric_quantity()`
  - Method `.test_frontier_endpoints()`
  - Method `.test_landing_and_depot_endpoints()`
  - Method `.test_save_load_delete_endpoints()`
  - Method `.test_multiple_save_slots_endpoints_and_listing()`
  - Method `.test_codex_claim_endpoint()`

---

### [`tests/test_sim_mechanics.py`](tests/test_sim_mechanics.py)
> *Unit and integration tests for the living crew, volume-aware market, and cash-flow mechanics.*

**Size**: `399` lines (`16523` bytes)

**Classes:**
- `class TestCrewMoraleCore`
  - Method `.test_morale_event_clamps_and_logs()`
  - Method `.test_inactive_members_do_not_drift()`
  - Method `.test_unpaid_crew_can_resign_deterministically()`
  - Method `.test_paid_crew_never_resigns()`
  - Method `.test_critical_morale_warning_is_logged()`
  - Method `.test_shore_leave_restore_math()`
- `class TestEngineMoraleEvents`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `._crew_morale()`
  - Method `.test_story_choice_celebration_raises_morale()`
  - Method `.test_hostile_arrival_lowers_morale()`
  - Method `.test_void_storm_lowers_morale()`
- `class TestShoreLeave`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `.test_shore_leave_requires_docking()`
  - Method `.test_shore_leave_restores_morale_for_credits()`
  - Method `.test_shore_leave_rejects_peak_morale()`
  - Method `.test_shore_leave_rejects_insufficient_credits()`
  - Method `.test_cli_crew_shore_command()`
  - Method `.test_cli_main_crew_shore()`
- `class TestVolumeAwareMarket`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `._stock(commodity_id)`
  - Method `.test_single_unit_keeps_flat_price()`
  - Method `.test_bulk_buy_pays_market_impact()`
  - Method `.test_bulk_sell_earns_diminishing_returns()`
  - Method `.test_buy_rejected_when_impact_exceeds_credits()`
  - Method `.test_arbitrage_guard_still_blocks_same_station_round_trip()`
- `class TestCashFlowTelemetry`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `.test_cash_flow_fields_and_math()`
  - Method `.test_scout_drone_counts_as_passive_income()`
  - Method `.test_snapshot_and_crew_report_expose_cash_flow()`
  - Method `.test_cli_status_prints_cash_flow()`
- `class TestServerCrewShoreEndpoint`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `._post(path, body)`
  - Method `.test_post_crew_shore()`

**Functions:**
- `def _member(member_id, morale, status, wage)`

---

### [`tests/test_snapshot_catalogs.py`](tests/test_snapshot_catalogs.py)
> *Static catalogs: built once, served by /api/catalogs, and left out of polls that cache them.*

**Size**: `87` lines (`3717` bytes)

**Classes:**
- `class TestStaticCatalogs`
  - Method `.test_catalogs_cover_exactly_the_static_keys()`
  - Method `.test_catalogs_are_built_once()`
  - Method `.test_full_snapshot_still_carries_every_catalog()`
  - Method `.test_lite_snapshot_omits_catalogs_and_keeps_live_state()`
- `class TestCatalogEndpoints`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.setUp()`
  - Method `._request(method, path, body, cached)`
  - Method `.test_catalog_endpoint_serves_every_static_key()`
  - Method `.test_catalog_endpoint_ignores_the_cache_header()`
  - Method `.test_state_poll_is_full_by_default_and_lite_when_cached()`
  - Method `.test_action_responses_honour_the_cache_header()`

---

### [`tests/test_storage.py`](tests/test_storage.py)
> *Unit tests for atomic persistence, crash safety, and shadow backup recovery.*

**Size**: `153` lines (`6485` bytes)

**Classes:**
- `class TestStorage`
  - Method `.setUp()`
  - Method `.test_save_and_load()`
  - Method `.test_dock_purchase_cost_basis_round_trips()`
  - Method `.test_corrupt_file_quarantine_and_backup_recovery()`
  - Method `.test_failed_atomic_replace_raises_and_preserves_previous_save()`
  - Method `.test_schema_invalid_primary_falls_back_to_backup()`
  - Method `.test_invalid_utf8_does_not_crash_loading()`
  - Method `.test_multiple_save_slots_persist_list_and_delete_independently()`
  - Method `.test_invalid_save_slot_name_raises_value_error()`

---

### [`tests/test_story.py`](tests/test_story.py)
> *Unit and integration tests for Cadet Flight Academy and The Precursor Cipher story campaign.*

**Size**: `674` lines (`28755` bytes)

**Classes:**
- `class TestStoryAndTutorial`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `.test_tutorial_initial_state()`
  - Method `.test_tutorial_progressive_milestones()`
  - Method `.test_tutorial_skip_and_reset()`
  - Method `.test_story_initialization_and_first_chapter()`
  - Method `.test_story_arrival_transmissions()`
  - Method `.test_story_choices_and_factions()`
  - Method `.test_story_serialization_roundtrip()`
  - Method `.test_story_target_system_enforcement_and_full_campaign()`
  - Method `.test_relic_passive_multipliers_integration()`
  - Method `.test_cli_tutorial_and_story_commands()`
  - Method `.test_cli_main_entrypoint()`
- `class TestServerStoryAndTutorial`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `._get(path)`
  - Method `._post(path, body)`
  - Method `.test_server_tutorial_endpoints()`
  - Method `.test_server_story_endpoints()`
- `class TestStoryBranchingMechanics` - *Requirement-gated choices, persistent flags, endings, and legacy-save migration.*
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `._travel_to(destination)`
  - Method `.test_story_status_reports_objectives_and_locks()`
  - Method `.test_act_iv_requires_black_hole_orbit()`
  - Method `.test_locked_choices_report_branch_resolvable_reasons()`
  - Method `.test_persistent_flags_drive_distinct_endings()`
  - Method `.test_follow_up_transmissions_persist()`
  - Method `.test_resolve_story_ending_variants()`
  - Method `.test_chapter_flag_gating_skips_ineligible_chapters()`
  - Method `.test_migrate_story_state_variants()`
  - Method `.test_engine_load_state_migrates_legacy_campaign()`
  - Method `.test_serialization_roundtrip_preserves_flags_and_ending()`

---

### [`tests/test_time_and_ticks.py`](tests/test_time_and_ticks.py)
> *Comprehensive automated test suite for Time, Ticks, and Temporal Controls in VoidFarer.*

**Size**: `325` lines (`13134` bytes)

**Classes:**
- `class TestTimeStateModel` - *Verify TimeState dataclass serialization, defaults, and legacy migration.*
  - Method `.test_default_values()`
  - Method `.test_to_dict_and_from_dict()`
  - Method `.test_tick_interval_scales_with_chrono_speed()`
  - Method `.test_gamestate_backward_compatibility()`
- `class TestSimulationEngineTimeAndTicks` - *Verify time progression, orbital dynamics, shield regen, and drone harvests.*
  - Method `.setUp()`
  - Method `.test_single_tick()`
  - Method `.test_multi_tick()`
  - Method `.test_orbital_angle_progression()`
  - Method `.test_passive_shield_recharge()`
  - Method `.test_fleet_drone_harvest_accumulation()`
  - Method `.test_time_control_pause_resume()`
  - Method `.test_time_speed_settings()`
  - Method `.test_step_time()`
  - Method `.test_status_snapshot_contains_time()`
  - Method `.test_pause_resume_speed_memory()` - *Verify speed rate (e.g. 5x) is retained across pause and resume cycles.*
  - Method `.test_jump_advances_transit_time()` - *Verify interstellar hyperspace jumps advance cosmic time and orbits by 2 ticks (12 hours).*
  - Method `.test_state_preservation_across_operations()` - *Verify operations like orbit, scan, and power routing never wipe temporal clock state.*
- `class TestServerTimeEndpoints` - *Verify REST API time endpoints: /api/time, /api/time/step, /api/time/speed, etc.*
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `._get(path)`
  - Method `._post(path, body)`
  - Method `.test_get_api_time()`
  - Method `.test_post_api_time_step()`
  - Method `.test_post_api_time_speed()`
  - Method `.test_post_api_time_pause_and_resume()`

---

### [`tests/test_trade_ledger.py`](tests/test_trade_ledger.py)
> *Trade ledger: per-commodity cost basis, realised profit and max-quantity orders.*

**Size**: `160` lines (`7106` bytes)

**Classes:**
- `class TestTradeCostBasis`
  - Method `.test_buy_records_what_was_paid()`
  - Method `.test_sell_reports_profit_and_releases_cost_proportionally()`
  - Method `.test_stale_cost_is_reset_when_the_hold_was_emptied_elsewhere()`
  - Method `.test_jettison_releases_the_cost_basis_proportionally()`
  - Method `.test_old_saves_load_with_an_empty_cost_basis()`
  - Method `.test_cost_basis_round_trips()`
- `class TestMaxOrders`
  - Method `.test_max_buy_is_bounded_by_hold_volume()`
  - Method `.test_max_buy_is_bounded_by_credits()`
  - Method `.test_max_sell_sells_everything_held()`
  - Method `.test_max_with_nothing_possible_explains_why()`
  - Method `.test_max_buy_names_the_hold_when_a_unit_does_not_fit()`
  - Method `.test_snapshot_exposes_max_buy_and_average_cost()`
- `class TestMaxOrderParity`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `.setUp()`
  - Method `.test_rest_trade_accepts_max_flag()`
  - Method `.test_repl_sell_all()`

**Functions:**
- `def _docked_engine(credits, cargo)`

---

### [`tests/test_transit_civ_events.py`](tests/test_transit_civ_events.py)
> *Tests for in-system transit (TravelState), planetary civilization metadata, and cockpit GameEvents.*

**Size**: `356` lines (`16308` bytes)

**Classes:**
- `class TestTransitCivEvents` - *Verify TravelState, planetary faction/population/government, and GameEvent lifecycles.*
  - Method `.setUp()`
  - Method `.test_gamestate_roundtrip_preserves_events_travel_and_civ_metadata()`
  - Method `.test_galaxy_generates_planetary_civilization_metadata()`
  - Method `.test_sublight_transit_progresses_and_completes_on_tick()`
  - Method `.test_quantum_in_system_transit_consumes_fuel_and_arrives_next_tick()`
  - Method `.test_start_travel_validation_guards()`
  - Method `.test_travel_preview_reports_eta_fuel_and_risk()`
  - Method `.test_transit_hazard_applies_damage_delay_and_event()`
  - Method `.test_start_travel_rejects_same_body_and_active_transit()`
  - Method `.test_event_emission_and_dismissal()`
  - Method `.test_cli_and_cockpit_surface_for_travel_and_events()`
  - Method `.test_scientifically_accurate_planetary_physics_and_habitability()`
  - Method `.test_legacy_save_backfills_scientific_physics_and_habitability()`
  - Method `.test_sublight_transit_calculates_2d_euclidean_distance_and_appropriate_ticks()`
  - Method `.test_cockpit_persistent_transit_animation_and_habitability_display()`

---

### [`tests/test_ui_audit.py`](tests/test_ui_audit.py)
> *The headless cockpit audit has deterministic viewport, parsing and wrapper helpers.*

**Size**: `78` lines (`3811` bytes)

**Classes:**
- `class AuditHelpersTest`
  - Method `.test_wide_viewports_get_only_window_chrome()`
  - Method `.test_laptop_keeps_an_exact_iframe()`
  - Method `.test_parse_audit_reads_an_escaped_payload()`
  - Method `.test_parse_audit_refuses_a_missing_payload()`
  - Method `.test_prepare_static_injects_the_collector_and_wrapper()`
  - Method `.test_severe_findings_name_the_blocking_categories()`
  - Method `.test_modal_layers_are_not_reported_as_hud_collisions()`
  - Method `.test_browser_command_emulates_windows_scaling()`
  - Method `.test_a_blurry_radar_backing_store_is_a_severe_finding()`
  - Method `.test_summary_line_reports_the_radar_state()`

---

### [`tests/test_ui_inventory.py`](tests/test_ui_inventory.py)
> *The cockpit inventory proof covers controls, handlers, routes, hotkeys and theme tokens.*

**Size**: `35` lines (`1400` bytes)

**Classes:**
- `class InventoryTest`
  - Method `.test_the_inventory_names_the_core_controls_and_handlers()`
  - Method `.test_the_inventory_names_the_ui_routes_and_theme_surface()`
  - Method `.test_the_inventory_is_sorted_and_deduplicated()`

---

### [`tests/test_void_traversal.py`](tests/test_void_traversal.py)
> *Unit and integration tests for the Hollow Between void traversal mechanics.*

**Size**: `452` lines (`18605` bytes)

**Classes:**
- `class TestVoidLanes`
  - Method `.setUp()`
  - Method `.test_anchors_are_black_hole_systems()`
  - Method `.test_lane_determinism_per_seed()`
  - Method `.test_anchor_mesh_connectivity()`
  - Method `.test_void_route_plan_metrics()`
  - Method `.test_void_shortest_route_symmetry()`
- `class TestVoidTraversalState`
  - Method `.test_roundtrip_and_progress()`
  - Method `.test_ship_state_serialization()`
- `class TestVoidDiveAndTraversal`
  - Method `.setUp()`
  - Method `.tearDown()`
  - Method `._goto_cygnus_horizon()`
  - Method `.test_dive_requires_black_hole_orbit()`
  - Method `.test_dive_validation_errors()`
  - Method `.test_dive_initializes_traversal()`
  - Method `.test_relic_grants_starting_stability()`
  - Method `.test_emergency_emergence_restores_horizon_orbit()`
  - Method `.test_tick_advances_to_arrival()`
  - Method `.test_first_visit_cartography_bounty()`
  - Method `.test_storms_damage_and_are_recorded()`
  - Method `.test_stability_collapse_forces_emergence()`
  - Method `.test_gateways_open_calms_storms()`
  - Method `.test_void_status_parity_fields()`
  - Method `.test_void_status_reports_destination_name_in_transit()`
  - Method `.test_snapshot_includes_void_and_story_status()`
  - Method `.test_cli_void_commands()`
  - Method `.test_legacy_save_backfills_black_hole_horizons()`
  - Method `.test_cli_main_entrypoint()`
- `class TestServerVoidEndpoints`
  - Method `.setUpClass()`
  - Method `.tearDownClass()`
  - Method `._get(path)`
  - Method `._post(path, body)`
  - Method `.test_get_api_void()`
  - Method `.test_post_api_void_dive_rejected_without_horizon()`
  - Method `.test_post_api_void_emerge_rejected_when_not_traversing()`
  - Method `.test_story_endpoint_includes_status()`

---

### [`tests/test_war_news_persistence.py`](tests/test_war_news_persistence.py)
> *War news must survive a real save/load cycle, like every other game state.*

**Size**: `48` lines (`2088` bytes)

**Classes:**
- `class WarNewsPersistenceTest`
  - Method `.test_war_notifications_and_trimmed_log_survive_a_disk_round_trip()`
  - Method `.test_a_reloaded_campaign_keeps_announcing_new_wars()`

---

### [`tools/__init__.py`](tools/__init__.py)
> *Developer proofs for VoidFarer.*

**Size**: `1` lines (`38` bytes)

---

### [`tools/ai_play.py`](tools/ai_play.py)
> *Play VoidFarer headlessly through the public API and report mechanic coverage.*

**Size**: `75` lines (`2939` bytes)

**Functions:**
- `def main(argv)`

---

### [`tools/ui_audit.py`](tools/ui_audit.py)
> *Capture VoidFarer cockpit screenshots and a measurable UI audit with headless Edge or Chrome.*

**Size**: `924` lines (`36684` bytes)

**Functions:**
- `def find_browser()` - *Locate an installed Edge or Chrome executable without a third-party dependency.*
- `def outer_window(viewport)` - *Outer window size that yields the requested inner viewport for Windows desktop sizes.*
- `def prepare_static(source, workdir)` - *Copy the cockpit and add a same-origin viewport wrapper plus an error collector.*
- `def parse_audit(dom)` - *Read the JSON audit payload out of a dumped wrapper DOM.*
- `def browser_command(browser, viewport, profile, screenshot, url, dpr)` - *Headless Edge/Chrome argument list for one capture at a device scale factor.*
- `def run_browser(browser, url, viewport, profile, screenshot, timeout, dpr)` - *Run one headless capture at a viewport and return stdout, stderr and the exit code.*
- `def audit_viewport(browser, port, name, viewport, workdir, out, timeout, scenario, tab, dpr)` - *Capture one viewport and return its parsed audit report.*
- `def summary_line(report)` - *One ASCII-safe console line for a viewport report.*
- `def severe_findings(report)` - *Names of findings that should fail an explicit audit check.*
- `def write_report(reports, out, browser)` - *Write the combined JSON and Markdown evidence packet.*
- `def main(argv)` - *Run the audit, write screenshots plus JSON/Markdown, and print a concise summary.*

---

### [`tools/ui_browser.py`](tools/ui_browser.py)
> *Drive the real VoidFarer cockpit in Edge through Playwright.*

**Size**: `457` lines (`20752` bytes)

**Functions:**
- `def _open_cockpit(page, scenario, tab, timeout)` - *Wait for the cockpit and move it into the requested review state.*
- `def _metrics(page)` - *Return viewport, scroll, element and tiny-text counts from the live page.*
- `def _click_probe(page)` - *Enumerate every cockpit control through the shipped click map and prove handles are unique.*
- `def _run_viewport(browser, url, name, viewport, scenario, tab, out, timeout, scroll, click_map)` - *Open one real browser viewport, drive it and capture a true screenshot.*
- `def _prepare_surface(engine)` - *Put the live engine on a landed body so the surface-ops panel has real data.*
- `def _prepare_waypoint(engine)` - *Fly the flagship to an open-space vector so the void anchor is on screen.*
- `def _prepare_factions(engine)` - *Advance a fresh campaign until the Coalition is at war, so the petition control renders.*
- `def main(argv)` - *Run the browser review driver and write screenshots plus a small JSON report.*

---

### [`tools/ui_inventory.py`](tools/ui_inventory.py)
> *Print VoidFarer's cockpit inventory, one entry per line.*

**Size**: `184` lines (`7734` bytes)

**Classes:**
- `class SurfaceParser` - *Collects identified elements, roles, live regions and hotkey chips of one page.*
  - Method `.__init__()`
  - Method `._start(tag, attrs, self_closing)`
  - Method `.handle_starttag(tag, attrs)`
  - Method `.handle_startendtag(tag, attrs)`
  - Method `.handle_data(data)`
  - Method `.handle_endtag(tag)`

**Functions:**
- `def html_entries(path)` - *Identified elements, actions, roles, live regions and hotkey labels of a page.*
- `def script_entries(path)` - *Handlers, DOM bindings, API calls and hotkeys declared by the cockpit script.*
- `def route_entries(path)` - *The exact `/api/` routes the cockpit server dispatches.*
- `def token_entries(path)` - *Theme custom properties the stylesheet declares.*
- `def inventory(static)` - *Every inventory entry of a cockpit directory, sorted and deduplicated.*
- `def main(argv)` - *Write the inventory to stdout; exit 1 when the surface has no entries at all.*

---

### [`voidfarer/__init__.py`](voidfarer/__init__.py)
> *VoidFarer: Autonomous deep-space fleet, procedural galaxy, and holographic cockpit simulation engine.*

**Size**: `4` lines (`159` bytes)

---

### [`voidfarer/agent_api.py`](voidfarer/agent_api.py)
> *Discoverable action catalog so an AI can play every mechanic through the public API.*

**Size**: `78` lines (`2653` bytes)

**Functions:**
- `def _sections(source)` - *Split the handler source into the GET and POST halves.*
- `def _route_blocks(section)`
- `def _fields(block)`
- `def build_action_catalog(handler_cls)` - *Read the handler's own route table and describe every callable endpoint.*

---

### [`voidfarer/agent_play.py`](voidfarer/agent_play.py)
> *Headless AI captain: plays the game through the same HTTP API the cockpit uses.*

**Size**: `683` lines (`29431` bytes)

**Classes:**
- `class ApiClient` - *Minimal JSON HTTP client for the cockpit server.*
  - Method `.__init__(host, port, timeout)`
  - Method `.get(path)`
  - Method `.post(path, payload)`
  - Method `._open(request)`
- `class AiCaptain` - *A deterministic policy that exercises every mechanic family it can reach.*
  - Method `.__init__(client, seed)`
  - Method `.play(steps)`
  - Method `._choose(step)`
  - Method `._next_tour_action()`
  - Method `._tour_power()`
  - Method `._tour_reactor()`
  - Method `._tour_route()`
  - Method `._tour_messages()`
  - Method `._tour_contracts()`
  - Method `._tour_refuel()`
  - Method `._tour_repair()`
  - Method `._tour_crew()`
  - Method `._tour_upgrade()`
  - Method `._tour_weapon()`
  - Method `._tour_shipmod()`
  - Method `._tour_outpost()`
  - Method `._tour_surface()`
  - Method `._tour_away()`
  - Method `._tour_ai()`
  - Method `._tour_codex()`
  - Method `._tour_mastery()`
  - Method `._tour_training()`
  - Method `._tour_depot()`
  - Method `._tour_preview()`
  - Method `._tour_stance()`
  - Method `._tour_weapon_set()`
  - Method `._tour_events()`
  - Method `._tour_crew_train()`
  - Method `._tour_ability()`
  - Method `._tour_drone()`
  - Method `._tour_mercenary()`
  - Method `._tour_escort()`
  - Method `._tour_time_speed()`
  - Method `._tour_navigate()`
  - Method `._tour_war()`
  - Method `._tour_dock()`
  - Method `._tour_point()`
  - Method `._tour_weapon_install()`
  - Method `._tour_reactor_vent()`
  - Method `._tour_reactor_repair()`
  - Method `._tour_time_pause()`
  - Method `._tour_time_resume()`
  - Method `._tour_shipmod_remove()`
  - Method `._is_docked()`
  - Method `._dockable_body()`
  - Method `._current_faction_id()`
  - Method `._pick_body(prefer_unvisited)`
  - Method `._cheapest_quote(quotes)`
  - Method `._first_research_project()`
  - Method `.report()`

**Functions:**
- `def coverage_gaps(catalog_paths, covered)` - *Catalog endpoints with neither an AI attempt nor a documented reason.*

---

### [`voidfarer/away.py`](voidfarer/away.py)
> *Away-team expeditions: body missions, deterministic outcomes, and crew risk.*

**Size**: `306` lines (`10283` bytes)

**Classes:**
- `class AwayMissionType` - *One expedition profile that can be launched from orbit.*
  - Method `.to_dict()`
  - Method `.available_on(body)`

**Functions:**
- `def get_away_mission_type(mission_type)`
- `def site_key(mission_type, body_id)` - *Stable key for a worked site, so a body cannot be farmed by the same expedition.*
- `def available_missions(body)` - *Every expedition profile that can be launched from orbit around this body.*
- `def _fit(member, required_skill)`
- `def crew_fit(member, required_skill)` - *Effective aptitude of one crew member for a mission's required discipline.*
- `def auto_team(mission_type, crew, assigned_ids)` - *Pick the best available specialists for a mission, deterministically.*
- `def mission_risk(mission_type, body, team)` - *Risk percentage after body hazards, gravity and specialist aptitude.*
- `def _mission_rng(mission, galaxy_seed)`
- `def resolve_away_mission(mission, mission_type, body, team, galaxy_seed)` - *Resolve one due expedition deterministically. Returns an outcome packet.*

---

### [`voidfarer/character.py`](voidfarer/character.py)
> *Commander character progression, skills, and activatable abilities.*

**Size**: `154` lines (`6112` bytes)

**Functions:**
- `def skill_level(character, skill)`
- `def skill_bonus(character, skill)` - *Percent bonus per skill level above baseline.*
- `def reconcile_abilities(character)` - *Append every ability whose skill requirement this character already meets.*
- `def train_skill(character, skill)`
- `def award_character_xp(character, amount)`
- `def advance_age(character, elapsed_days_before, elapsed_days_after)`
- `def ability_ready(character, ability_id)`
- `def start_ability_cooldown(character, ability_id)`
- `def tick_ability_cooldowns(character, num_ticks)`

---

### [`voidfarer/cli.py`](voidfarer/cli.py)
> *Command-line interface and interactive terminal REPL for VoidFarer.*

**Size**: `2954` lines (`151715` bytes)

**Functions:**
- `def _get_engine(storage_dir)` - *Initialize or restore simulation engine from disk.*
- `def _bar(current, maximum, length, color)` - *Generate ANSI filled progress bar.*
- `def cmd_status(engine)` - *Display current flagship telemetry, fleet roster, and star system status.*
- `def cmd_time(engine, storage, argv)` - *Manage simulation cosmic time, ticks, and speed controls.*
- `def cmd_chart(engine)` - *Print galaxy starmap and celestial bodies within current system.*
- `def cmd_market(engine)` - *Display commodity prices and supply/demand at the current orbital body.*
- `def cmd_economy(engine)` - *Display galactic macroeconomic conditions, active events, and lucrative trade routes.*
- `def cmd_inventory(engine, storage, parts)` - *Display and manage ship cargo manifest, usable consumables, and hold capacity.*
- `def cmd_shipyard(engine, storage, parts)` - *Orbital shipyard: inspect ship chassis upgrades, purchase vessels, and sell modules.*
- `def cmd_fleet(engine, storage, parts)` - *Manage autonomous fleet drones, mining escorts, and harvest yields.*
- `def cmd_quests(engine)`
- `def cmd_ai(engine, storage, parts)`
- `def cmd_messages(engine, storage, parts)`
- `def cmd_depot(engine, storage, parts)`
- `def cmd_land(engine, storage, body_id)`
- `def cmd_saves(engine, storage, parts)` - *List, save, load, or delete named save slots.*
- `def cmd_mercs(engine, storage, parts)`
- `def cmd_allies(engine, storage, parts)`
- `def cmd_upgrades(engine, storage, parts)` - *Inspect and purchase hardware modules from station arsenal.*
- `def cmd_combat(engine, storage, parts)` - *Execute tactical combat maneuvers during hostile intercepts.*
- `def cmd_war(engine, storage, action, args)` - *List active wars and their fronts, or pledge credits to one side.*
- `def cmd_settings(engine, storage, action, args)` - *Show or change simulation options, chiefly how often quick-time decisions interrupt.*
- `def cmd_factions(engine, storage, parts)` - *Inspect galactic sovereign factions, standings, active territory, and diplomatic perks.*
- `def cmd_corporations(engine, storage, parts)` - *Inspect interstellar megacorporations, commercial specialties, and corporate standing.*
- `def cmd_contracts(engine, storage, parts)` - *Inspect dynamic sector bounties, claim completed contracts, and trigger fresh assignments.*
- `def cmd_mastery(engine, storage, parts)` - *Display pilot progression rank, talent tree specializations, and allocate perks.*
- `def cmd_relics(engine)` - *Display recovered ancient Precursor relics and passive fleet bonuses.*
- `def cmd_log(engine)` - *Display the captain's log: career statistics, milestones, and flight record.*
- `def cmd_codex(engine, storage, parts)` - *Inspect the discovery codex and claim completed milestone rewards.*
- `def cmd_streak(engine)` - *Display current expedition jump streak and active loss aversion multiplier.*
- `def cmd_tutorial(engine, storage, parts)` - *Cadet Flight Academy progressive tutorial system.*
- `def cmd_story(engine, storage, parts)` - *The Precursor Cipher: Branching episodic space opera campaign.*
- `def cmd_void(engine, storage, parts)` - *The Hollow Between: void lane traversal between black-hole anchors.*
- `def cmd_reactor(engine, storage, parts)` - *Inspect reactor telemetry and manage thermal doctrine.*
- `def cmd_mapmods(engine)` - *Display active sector map modifiers and their simulation effects.*
- `def _describe_ship_mod_effects(effects)`
- `def cmd_refit(engine, storage, parts)` - *Ship modification section: inspect, install, or remove structural refits.*
- `def cmd_character(engine, storage, parts)`
- `def cmd_research(engine, storage, parts)`
- `def cmd_outpost(engine, storage, parts)`
- `def cmd_diplomacy(engine, storage, parts)`
- `def cmd_route(engine, target)`
- `def cmd_crew(engine, storage, parts)`
- `def cmd_away(engine, storage, parts)`
- `def cmd_pirate(engine, storage, parts)`
- `def cmd_decision(engine, storage, parts)`
- `def cmd_quantum(engine, storage, parts)`
- `def cmd_surface(engine, storage, parts)`
- `def cmd_weapons(engine, storage, parts)`
- `def cmd_repl(engine, storage)` - *Launch interactive terminal command session.*
- `def cmd_events(engine, storage, parts)` - *List or dismiss cockpit popup events.*
- `def _trade_quantity(value)` - *argparse type for trade orders: a positive count, or `max`/`all` for the largest possible order.*
- `def _run_trade(engine, commodity_id, quantity, is_buy)`
- `def main(argv)` - *Main CLI entrypoint.*

---

### [`voidfarer/codex.py`](voidfarer/codex.py)
> *Captain's log and discovery codex: milestones, statistics, and rewards.*

**Size**: `606` lines (`20869` bytes)

**Classes:**
- `class CodexCategory` - *A thematic grouping of codex milestones.*
  - Method `.to_dict()`
- `class CodexEntry` - *One discovery milestone and its reward.*
  - Method `.to_dict()`

**Functions:**
- `def get_codex_entry(entry_id)` - *Resolve one codex milestone by identifier.*
- `def _seen_bodies(state)`
- `def metric_value(state, metric)` - *Compute one codex metric from the saved game state.*
- `def evaluate_codex(state)` - *Return every milestone with current progress, completion, and claim state.*
- `def build_codex_report(state)` - *Build the JSON-safe captain's log and discovery codex report.*

---

### [`voidfarer/crew.py`](voidfarer/crew.py)
> *Crew roles, recruiting, portraits, and crew-derived ship bonuses.*

**Size**: `280` lines (`10336` bytes)

**Classes:**
- `class CrewRole`
  - Method `.to_dict()`

**Functions:**
- `def get_crew_role(role_id)`
- `def recruit_crew_member(role_id, seed, current_count)`
- `def calculate_crew_bonuses(crew)`
- `def crew_upkeep(crew)` - *Monthly wage bill of the active crew.*
- `def wages_due(crew, days_before, days_after)` - *Whole credits of monthly wages accrued between two calendar points (cumulative, so*
- `def tick_crew(crew, num_ticks, credits_available, rng, wage_due)` - *Advance wages and morale; unpaid crews sink toward desertion.*
- `def apply_morale_event(crew, delta, reason)` - *Shift every active member's morale by an event delta, clamped to 0..100.*
- `def crew_xp_to_next(member)` - *Experience required for the next rank: veterans take longer to train.*
- `def award_crew_xp(member, amount)` - *Add expedition experience and promote a specialist when a rank threshold is crossed.*
- `def recover_crew_injuries(crew, num_ticks, medic_aboard)` - *Heal away-team injuries over time; an active medic doubles the recovery rate.*
- `def shore_leave_restore(crew)` - *Compute a fleet-wide shore leave outcome: restored crew and morale points.*
- `def crew_catalog()`

---

### [`voidfarer/decisions.py`](voidfarer/decisions.py)
> *Conditional real-time decision events that pause the simulation until resolved.*

**Size**: `372` lines (`25433` bytes)

**Classes:**
- `class DecisionDefinition`

**Functions:**
- `def _system(state)`
- `def _body(state)`
- `def _credits(state)`
- `def _avg_morale(state)`
- `def _has_contraband(state)`
- `def _any_injury(state)`
- `def _war_active(state)`
- `def _at_inhabited(state)`
- `def _at_station(state)`
- `def _low_hull(state)`
- `def _low_fuel(state)`
- `def _high_heat(state)`
- `def _bad_area(state)`
- `def _choice(choice_id, label, description, effects)`
- `def eligible_decisions(state, trigger)` - *Definitions whose trigger and state condition are satisfied and not yet seen.*
- `def make_decision_event(definition, tick, trigger)`

---

### [`voidfarer/demographics.py`](voidfarer/demographics.py)
> *Population capacity, technology limits, and logistic growth for VoidFarer worlds.*

**Size**: `243` lines (`8440` bytes)

**Functions:**
- `def clamp_tech_level(tech_level)` - *Return a whole tech level in the supported 1..10 band.*
- `def tech_capacity_multiplier(tech_level)` - *Life-support and density multiplier: roughly 0.7x at TL1, 4.5x at TL8.*
- `def effective_capacity(population_capacity, devastation)` - *Capacity left after war damage; devastation removes up to 65% of the ceiling.*
- `def compute_population_capacity(body_type, radius_km, habitability, tech_level)` - *Maximum sustainable population from surface area, habitability and technology.*
- `def world_tech_level(faction, body_type, market_archetype, faction_tech)` - *Technology available on a world from its owner and local industrial base.*
- `def initial_population(body_type, radius_km, habitability, tech_level, faction, market_archetype, station_dockable)` - *Settle a generated world at a faction-appropriate share of its capacity.*
- `def devastation_recovery(tech_level, stability)` - *Points of devastation a world repairs per tick from its tech and civil order.*
- `def step_population(population, population_capacity, habitability, tech_level, devastation, num_ticks, stability)` - *Advance one world's population with logistic growth, tech limits and war deaths.*

---

### [`voidfarer/economy.py`](voidfarer/economy.py)
> *Dynamic Global Economy, supply/demand simulation, economic events, and galactic trade network.*

**Size**: `412` lines (`15732` bytes)

**Functions:**
- `def generate_initial_economy(systems, rng)` - *Construct baseline economy state with localized stockpiles and initial macroeconomic conditions.*
- `def tick_global_economy(state, num_ticks, systems, rng)` - *Advance economic simulation: update stockpiles, decrement event clocks, spawn emergent news.*
- `def faction_standing_price_factor(faction_standing)` - *Return the single diplomatic price multiplier for a faction standing value.*
- `def calculate_dynamic_market_quote(system, body, commodity, economy, faction_standing)` - *Compute precision localized pricing reflecting global stockpile supply/demand and macroeconomic events.*
- `def get_galactic_trade_routes(systems, economy)` - *Compute the most profitable interstellar trade routes across all explored star systems.*

---

### [`voidfarer/enemies.py`](voidfarer/enemies.py)
> *Hostile Enemy Archetypes, Tactical Combat AI, and Procedural Intercept Generation.*

**Size**: `279` lines (`10979` bytes)

**Classes:**
- `class EnemyArchetype` - *Blueprint for procedural hostile intercepts across galactic territories.*

**Functions:**
- `def threat_multiplier(threat_level)` - *Scale generated intercept strength with the pilot's command experience.*
- `def choose_enemy_intent(profile, special_ability, ability_ready, enemy_hull, enemy_max_hull, enemy_shield, enemy_max_shield, player_hull, player_max_hull, player_shield, player_max_shield, player_combo)` - *Pick the next hostile maneuver from hull, shield, combo, and AI profile state.*
- `def generate_system_enemy(system_id, security, faction, seed, threat_level)` - *Generate a procedurally balanced CombatEncounter matching star system characteristics.*

---

### [`voidfarer/engine.py`](voidfarer/engine.py)
> *Deterministic state machine and simulation engine for VoidFarer.*

**Size**: `7544` lines (`374952` bytes)

**Classes:**
- `class SimulationEngine` - *Coordinates space flight, star navigation, fleet drones, upgrades, and tactical combat.*
  - Method `._stable_unit(*parts)` - *Deterministic [0,1) roll that does not disturb the live RNG stream.*
  - Method `.war_news_events(lines, tick, existing)` - *Turn this tick's captures, treaties and eliminations into at most two events.*
  - Method `.__init__(seed, state)`
  - Method `._bootstrap_frontier()` - *Backfill frontier systems for legacy saves without changing the save schema.*
  - Method `._clone_ship(**kwargs)` - *Create a new ShipState preserving all unspecified telemetry and inventory attributes.*
  - Method `._clone_state(**kwargs)` - *Create a new GameState preserving time, stats, economy, and all unspecified universe fields.*
  - Method `._research_bonuses()`
  - Method `._skill(skill)`
  - Method `._combined_equipment(ship)`
  - Method `._crew_bonuses(ship)`
  - Method `._faction_stability()` - *System owner name -> its faction's civil stability (default 50 for unclaimed).*
  - Method `._faction_technology()` - *System owner name -> its faction's current technology level.*
  - Method `._drift_world_technology(systems, faction_tech, previous_tick, new_tick)` - *Upgrade settled worlds toward their owner's tech at most once per drift window.*
  - Method `._map_effects(system)` - *Aggregate the active map modifiers of a system (defaults to the current one).*
  - Method `._effective_power(subsystem, ship)` - *Allocated subsystem power after reactor mode, heat, and integrity derating.*
  - Method `._recompute_caps(ship, equipped, ship_mods)` - *Recompute maximum hull, shield, cargo, and fuel from chassis, modules, and mods.*
  - Method `._grant_cargo(cargo, commodity_id, quantity)` - *Add as many units as the hold allows, returning (granted, overflow).*
  - Method `._replace_system_body(body_id, **changes)` - *Return a systems map with one body of the current system replaced.*
  - Method `._apply_relic_stat_bonuses(hull, max_hull, shield, max_shield, relics)` - *Raise current and maximum hull/shield for newly acquired permanent relics.*
  - Method `._progress_tutorial(action_type)` - *Advance the Cadet Flight Academy if current step requirement is satisfied.*
  - Method `._award_pilot_xp(amount, current_mastery)` - *Award experience points and compute level promotions and talent points.*
  - Method `._progress_contracts(category, amount, contracts)` - *Advance matching active contracts toward completion objectives.*
  - Method `.reset(seed, profile)` - *Reset the simulation to a fresh galaxy with an isolated deterministic RNG stream.*
  - Method `._validate_commander_profile(profile)` - *Reject commander profiles whose starting skills exceed the creation budget.*
  - Method `._apply_commander_profile(profile)` - *Apply the commander name, age, background and starting skills chosen at creation.*
  - Method `.load_state(state)` - *Replace the live universe with a loaded save and reseed its RNG stream.*
  - Method `._create_initial_state(seed)` - *Construct a fresh universe state rooted at Sol System.*
  - Property `.current_system`
  - Property `.orbiting_body`
  - Method `._body_by_id(body_id)` - *Look up a celestial body anywhere in the known galaxy.*
  - Method `._void_storm_chance()` - *Current void storm probability, calmed by open gateways.*
  - Method `._void_resonance_payout(resonance, share)` - *Convert weathered-storm resonance into credits and pilot XP.*
  - Method `.void_dive(target_system_id)` - *Slip through a black-hole event horizon into the Hollow Between.*
  - Method `.void_emerge()` - *Emergency surfacing from an active void traversal, back through the entry horizon.*
  - Method `.void_status()` - *Void traversal readiness, lanes, and active traversal state (CLI/REST/cockpit parity).*
  - Method `._process_drone_cycle(ship)` - *Advance autonomous drone harvest cycle across star systems.*
  - Method `.jump(target_system_id)` - *Execute a hyperspace jump to an adjacent star system.*
  - Method `._ship_position()` - *Current in-system position: the orbited body, or the open-space anchor.*
  - Method `.compute_body_distance_au(target_body, origin_body)` - *Compute 2D polar Euclidean distance in AU from the current position to a body.*
  - Method `.orbit(body_id)` - *Establish orbital trajectory around a celestial body in the current system.*
  - Method `._transit_risk(system, mode, effects)` - *Sector hazard risk for one in-system transit, reduced by piloting and quantum drive.*
  - Method `._travel_plan(body_id, mode)` - *Compute a transit plan without mutating state; shared by preview and execution.*
  - Method `.preview_travel(body_id, mode)` - *Return ETA, fuel, risk and hazard names for a potential transit.*
  - Method `._point_travel_plan(waypoint_au, waypoint_angle, mode)` - *Plan a transit to an empty-space vector, measured from the system's star.*
  - Method `.start_travel_to_point(waypoint_au, waypoint_angle, mode)` - *Fly to an empty-space vector instead of a body: no orbit is established on arrival.*
  - Method `.start_travel(body_id, mode)` - *Initiate sublight or quantum in-system transit toward a celestial body.*
  - Method `.scan()` - *Perform sensor sweep of current body or local space.*
  - Method `.route_power(engines, shields, sensors, weapons)` - *Adjust reactor power distribution across ship subsystems.*
  - Method `.set_reactor_mode(mode)` - *Select the reactor operating doctrine (balanced, economy, overdrive, silent).*
  - Method `.vent_reactor_coolant()` - *Purge reactor heat immediately, with a coolant recharge cooldown.*
  - Method `.repair_reactor()` - *Repair reactor core integrity at an orbital drydock.*
  - Method `.get_reactor_report()` - *Detailed reactor telemetry derived from current ship and sector conditions.*
  - Method `.install_ship_mod(mod_id)` - *Install a structural ship modification at an orbital drydock.*
  - Method `.remove_ship_mod(slot, expected_mod_id)` - *Remove a structural modification and recover part of its cost.*
  - Method `.get_ship_mod_report()` - *Serializable structural modification catalog and installed layout.*
  - Method `.get_simulation_report()` - *Unified simulation telemetry: reactor, environment, and structural refits.*
  - Method `.get_codex_report()` - *Captain's log and discovery codex derived from the saved game state.*
  - Method `.claim_codex_reward(entry_id)` - *Claim one completed codex milestone and persist its reward.*
  - Method `.train_character_skill(skill)`
  - Method `.use_character_ability(ability_id, target_faction_id)`
  - Method `.choose_research(project_id)`
  - Method `.build_outpost(body_id, outpost_type_id)`
  - Method `.upgrade_outpost(outpost_id)`
  - Method `.get_character_report()`
  - Method `.get_research_report()`
  - Method `.get_outpost_report()`
  - Method `.faction_diplomacy(faction_id, action, amount)`
  - Method `.buy_escort(escort_type, system_id)`
  - Method `.assign_escort(ship_id, system_id)`
  - Method `.repair_escorts(amount)`
  - Method `.dismiss_escort(ship_id)`
  - Method `.get_fleet_manager_report()`
  - Method `.plan_route(target_system_id)`
  - Method `.navigate_to(target_system_id)`
  - Method `.recruit_crew(role_id)`
  - Method `.dismiss_crew(crew_id)`
  - Method `.get_crew_report()`
  - Method `._away_assigned_ids(ship)`
  - Method `._away_reward_preview(mission_type)`
  - Method `.get_away_report()` - *Body expeditions available from orbit, active teams, and crew readiness.*
  - Method `.launch_away_mission(mission_type, crew_ids)` - *Deploy an away team from orbit. Spent crew stop contributing ship bonuses.*
  - Method `.recall_away_mission(mission_id)` - *Abort one expedition and return its team to the ship with no reward.*
  - Method `.cash_flow()` - *Monthly credit flow: crew payroll against passive income (drones, outposts).*
  - Method `.install_weapon(weapon_id)`
  - Method `.set_primary_weapon(weapon_id)`
  - Method `.get_weapon_report()`
  - Method `.resolve_message_choice(message_id, choice_id)`
  - Method `.get_message_tree_report()`
  - Method `._bulk_buy_cost(body, comm, quantity, standing, unit_price)` - *Price a buy order by walking the local stockpile, so bulk orders move the price they pay.*
  - Method `.max_trade_quantity(commodity_id, is_buy)` - *Largest order that would succeed now: affordable and in-hold for buys, all held units for sells.*
  - Method `.trade_max(commodity_id, is_buy)` - *Buy as many units as credits and hold allow, or sell every unit held.*
  - Method `.trade(commodity_id, quantity, is_buy)` - *Execute buy or sell commodity order at orbiting market.*
  - Method `._destination_market_body(system)`
  - Method `._quantum_fee(commodity, quantity, jumps)`
  - Method `.get_quantum_trade_report()` - *Arbitrage routes for cargo already in the hold, with fees and transit times.*
  - Method `.place_quantum_order(commodity_id, quantity, destination_system_id)` - *Ship owned cargo through the quantum lane; cargo leaves now and pays on arrival.*
  - Method `._resolve_quantum_orders(orders, tick, systems, economy)`
  - Method `.buy_upgrade(upgrade_id)` - *Purchase and install a hardware upgrade module at an orbital station.*
  - Method `.sell_upgrade(slot)` - *Uninstall and sell an equipped hardware module back to shipyard for credits.*
  - Method `.buy_ship_chassis(chassis_id)` - *Purchase and commission a new spacecraft hull chassis at an orbital shipyard.*
  - Method `.use_item(item_id)` - *Consume a usable item from cargo (nanite repair paste, shield battery, fuel canister, decoy).*
  - Method `.buy_item(item_id, quantity)` - *Purchase consumable items from an orbital station terminal.*
  - Method `.jettison_cargo(item_id, quantity)` - *Jettison cargo into the cosmic vacuum to free hold space.*
  - Method `.buy_drone(drone_type, assigned_system_id)` - *Purchase and commission an autonomous fleet drone.*
  - Method `.deploy_drone(drone_id, target_system_id)` - *Redeploy an autonomous fleet asset to a different star system.*
  - Method `.collect_drone_yield(drone_id)` - *Collect accumulated cargo and research credits from fleet drones.*
  - Method `.set_battle_stance(stance)` - *Set fleet battle doctrine: balanced, aggressive, or defensive.*
  - Method `._combat_defeat(combat, note, fleet_ships, crew, streak, fuel)` - *End a fight at 0 hull, pausing time so a destroyed ship cannot recover by ticking.*
  - Method `.combat_action(action)` - *Execute a tactical combat maneuver against an active hostile intercept.*
  - Method `.resolve_anomaly(choice_id)` - *Resolve current deep-space anomaly encounter with power-check validation.*
  - Method `.resolve_pirate_encounter(action)` - *Resolve a pirate toll: pay, fight, or burn clear. Flight resumes afterward.*
  - Method `.repair_hull(amount)` - *Repair ship hull integrity at orbital station.*
  - Method `.refuel(amount)` - *Refuel quantum drive at orbital station.*
  - Method `.step_orbits(delta_time)` - *Advance celestial bodies along orbital mechanics paths and cycle fleet drones.*
  - Method `.refresh_contracts()` - *Reroll the mission board across every category for a broker fee.*
  - Method `.claim_contract(contract_id)` - *Claim rewards for a fulfilled contract and immediately draw a new assignment.*
  - Method `.unlock_talent(talent_id)` - *Unlock a Pilot Specialization Perk using available talent points.*
  - Method `._story_unmet_requirements(requirements, *, chapter)` - *List human-readable unmet gating conditions for a chapter or choice.*
  - Method `.story_status()` - *Objective snapshot of the narrative campaign for CLI, REST, and cockpit parity.*
  - Method `.make_story_choice(choice_id)` - *Resolve a branching story dilemma in the active campaign chapter.*
  - Method `.skip_tutorial()` - *Skip Cadet Flight Academy and unlock unrestricted operational status.*
  - Method `.reset_tutorial()` - *Reset Cadet Flight Academy to step 1 for revision or retraining.*
  - Property `.current_chassis_id` - *Id of the chassis matching the ship's commissioned class (falls back to the class name).*
  - Method `.get_status_snapshot(include_static)` - *Produce a JSON serializable telemetry snapshot for the HUD.*
  - Method `.support_war(war_id, faction_id, credits)` - *Pledge credits to one side of an active war: shifts its score and your standings.*
  - Method `._ceasefire_chance(faction_id, war)` - *Odds a petition is accepted: standing, diplomacy skill and how the war is going.*
  - Method `.galactic_politics()` - *Territory, borders and war fronts for the strategic map and the factions panel.*
  - Method `.get_quests()` - *Return a unified quest panel view of the story chapter and active contracts.*
  - Method `._find_ai_captain(captain_id)`
  - Method `._replace_ai_captain(captain)`
  - Method `.interact_ai(captain_id, action, commodity_id, quantity)` - *Hail, trade with, hire, or ally with an autonomous captain.*
  - Method `.send_quantum_message(recipient, subject, body)` - *Send an intergalactic quantum-encrypted message.*
  - Method `.mark_message_read(message_id)`
  - Method `._depot_for_current_system()`
  - Method `._require_docked()`
  - Method `.deposit_cargo(item_id, quantity)`
  - Method `.withdraw_cargo(item_id, quantity)`
  - Method `.sell_from_depot(item_id, quantity)`
  - Method `.land_on_body(body_id)` - *Land on a habitable body and collect surface discovery rewards.*
  - Method `.get_surface_report()` - *Landing-party operations available on the currently landed body.*
  - Method `.perform_surface_operation(operation_id)` - *Run one surface operation, then mark the site branch as worked.*
  - Method `.salvage_derelict()` - *Board the current body's derelict hulk for cargo, credits, and hazard risk.*
  - Method `.scoop_fuel()` - *Recover fuel from a star, gas giant, or ice body currently in orbit.*
  - Method `.train_crew_member(crew_id)` - *Run a paid training drill that raises one crew member's skill rank.*
  - Method `.shore_leave()` - *Grant fleet-wide shore leave at a docked station, restoring crew morale for credits.*
  - Method `.hire_mercenary(merc_id)`
  - Method `.dismiss_fleet_unit(drone_id)`
  - Method `.refit_fleet_unit(drone_id)`
  - Method `.form_alliance(captain_id)`
  - Method `._decision_lock_reason()`
  - Method `._action_lock_reason()` - *Reason flight or exploration actions are frozen (decision or pirate toll).*
  - Method `._decision_cooldown()`
  - Method `._decision_chance_multiplier()`
  - Method `.set_decision_cadence(cadence)` - *Choose how often blocking quick-time decisions may interrupt the flight.*
  - Method `.decisions_ready_in()` - *Ticks left before another blocking decision may open.*
  - Method `.maybe_trigger_decision(trigger)` - *Evaluate conditional events and open at most one blocking decision.*
  - Method `.resolve_decision(choice_id)` - *Apply a decision choice; time and flight remain locked until this succeeds.*
  - Method `.tick(num_ticks)` - *Advance the simulation universe by num_ticks.*
  - Method `.emit_event(kind, title, message)` - *Create and append a cockpit popup GameEvent.*
  - Method `.dismiss_event(event_id)` - *Mark a cockpit popup GameEvent as dismissed.*
  - Method `.pause_time()` - *Pause simulation temporal clock while preserving current playback rate.*
  - Method `.resume_time()` - *Resume simulation temporal clock restoring previous speed multiplier.*
  - Method `.set_time_speed(speed)` - *Set simulation speed multiplier (0.0x to 10.0x).*
  - Method `.step_time(num_ticks)` - *Advance simulation by a discrete number of ticks.*

**Functions:**
- `def static_catalogs()` - *Build the code-constant catalogs once per process; callers must treat them as read-only.*
- `def _cargo_cost_after(previous_cargo, previous_cost, cargo)` - *Carry the paid basis of held cargo through any mutation outside a market trade.*

---

### [`voidfarer/exploration.py`](voidfarer/exploration.py)
> *Derelict salvage sites, fuel scooping profiles, and crew training drills.*

**Size**: `167` lines (`5983` bytes)

**Classes:**
- `class DerelictSite` - *A deterministic, once-per-body salvage site with a risk/reward profile.*
  - Method `.to_dict()`

**Functions:**
- `def scoop_reserve(body)` - *Deterministic number of scoop passes a body's volatiles support.*
- `def recharge_volatile_reserve(tapped, recharge_tick, current_tick)` - *Apply elapsed recharge intervals to one body's queued volatile taps.*
- `def _stable_crc(*parts)`
- `def derive_derelict(system_id, system_seed, body)` - *Return the body's deterministic salvage site, or None when it has none.*
- `def scoop_profile(body)` - *Return the fuel-scooping profile for a body, or None when it cannot be scooped.*
- `def scoop_yield(body, effective_sensor_power, science_skill)` - *Compute fuel recovered by a single scoop pass.*
- `def crew_training_cost(member)` - *Credits required for the next skill rank of a crew specialist.*

---

### [`voidfarer/faction_economy.py`](voidfarer/faction_economy.py)
> *Basic per-faction economy: tax base, industry, upkeep, treasury and war burden.*

**Size**: `206` lines (`7614` bytes)

**Functions:**
- `def _owned_systems(faction_name, systems)`
- `def _faction_identity(faction_id)`
- `def compute_faction_economy(faction_id, systems, wars, treasury, stability, trade_links, tech_level, tech_progress, num_ticks)` - *Derive one faction's population, output, wartime burden and per-tick cash flow.*
- `def initialize_faction_economies(systems, wars, eliminated, trade_links)` - *Create opening treasuries for every surviving canonical faction.*
- `def tick_faction_economies(economies, systems, wars, eliminated, num_ticks, trade_links)` - *Advance faction treasuries, research and trade; report a war drain or a breakthrough.*

---

### [`voidfarer/faction_state.py`](voidfarer/faction_state.py)
> *Dynamic faction leaders, behaviors, war resolution, and elimination.*

**Size**: `470` lines (`21049` bytes)

**Functions:**
- `def generate_faction_leaders(seed)` - *Create one deterministic leader per canonical sovereign faction.*
- `def _faction_systems(faction_id, systems)`
- `def faction_strength(faction_id, systems)`
- `def _faction_name(faction_id)`
- `def war_effort(faction_id, systems)` - *Strength a faction can actually project at the front.*
- `def war_momentum(attacker_id, defender_id, systems)` - *Per-step score drift before noise: effort ratio, defender edge and hegemon containment.*
- `def _capture_target(front, loser_id, loser_name, score, systems, rng)` - *Front worlds fall first; a capital only falls to double the capture score.*
- `def _devastate_system(system, rng, severity)` - *A captured front loses civilians and gains persistent devastation.*
- `def frontier_systems(winner_name, loser_name, systems)` - *Loser-held systems with a hyperlane into winner territory, sorted for determinism.*
- `def apply_war_devastation(wars, systems, rng, num_ticks)` - *Bombard both sides of every active front: civilians die and devastation accumulates.*
- `def _end_war(war, score, current_tick, logs)`
- `def force_peace_for_broke_factions(wars, economies, current_tick)` - *A faction that cannot pay its upkeep sues for peace instead of fighting on.*
- `def _apply_owner_technology(system, owner_name)` - *A conquered world adopts its new owner's flag, government, tech and capacity.*
- `def resolve_wars(wars, systems, rng, current_tick, eliminated, num_ticks)` - *Advance wars toward resolution: strength drives momentum, captures follow fronts.*
- `def simulate_faction_behaviors(leaders, wars, systems, rng, current_tick, eliminated, num_ticks, broke_factions)` - *Apply leader archetypes: declare wars, then resolve active fronts.*
- `def leader_for(leaders, faction_id)`

---

### [`voidfarer/faction_trade.py`](voidfarer/faction_trade.py)
> *Faction-to-faction trade: hyperlane-adjacent, peaceful pairs exchange goods.*

**Size**: `148` lines (`5197` bytes)

**Functions:**
- `def _faction_name(faction_id)`
- `def _systems_owned(systems, faction_name)`
- `def _cross_lanes(systems, left_name, right_name)` - *Hyperlanes with one endpoint owned by each faction.*
- `def warring_pairs(wars)` - *Canonical faction pairs currently fighting; their trade is blockaded.*
- `def compute_trade_links(systems, wars, economies, eliminated)` - *Derive the strongest peaceful hyperlane routes, capped per faction.*
- `def trade_income_for(faction_id, links)` - *Each route pays half its volume to each endpoint.*
- `def trade_partners_for(faction_id, links)`
- `def trade_partner_names(faction_id, links)`

---

### [`voidfarer/factions.py`](voidfarer/factions.py)
> *Galactic Factions, Megacorporations, Standings, and Geopolitical Mechanics.*

**Size**: `332` lines (`13550` bytes)

**Classes:**
- `class Faction` - *Sovereign faction or interstellar coalition.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class Corporation` - *Interstellar megacorporation shaping sector commerce and industrial technology.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`

**Functions:**
- `def get_faction(faction_id)` - *Retrieve canonical faction by ID.*
- `def government_for(faction_name, body_type)` - *Government installed by a faction, preserving science outposts as directorates.*
- `def get_corporation(corp_id)` - *Retrieve canonical corporation by ID.*
- `def get_faction_standing_tier(standing)` - *Calculate standing tier label and active perk description.*
- `def calculate_faction_market_modifier(faction_id, standing)` - *Calculate purchase price multiplier based on faction standing.*
- `def get_faction_id_from_name(name)` - *Resolve faction name to normalized faction ID.*
- `def get_faction_service_perks(faction_id, standing)` - *Return concrete service modifiers for the current standing tier and faction.*

---

### [`voidfarer/fleet.py`](voidfarer/fleet.py)
> *Escort warship catalog and fleet-manager behavior.*

**Size**: `149` lines (`4884` bytes)

**Functions:**
- `def get_escort_template(escort_type)`
- `def build_fleet_ship(escort_type, system_id, count)`
- `def fleet_damage(ships, formation)`
- `def fleet_evasion_bonus(ships, formation)`
- `def apply_fleet_casualties(ships, damage)` - *Distribute incoming damage across escorts, returning survivors and absorbed damage.*
- `def repair_fleet_ships(ships, amount)`

---

### [`voidfarer/frontier.py`](voidfarer/frontier.py)
> *Frontier systems: autonomous captains, depots, mercenaries, and quantum messages.*

**Size**: `180` lines (`7193` bytes)

**Functions:**
- `def generate_ai_captains(systems, seed)` - *Create a deterministic roster of autonomous captains distributed across the galaxy.*
- `def generate_depots(systems)` - *Create one system-local depot per star system.*
- `def generate_welcome_messages(tick)` - *Seed the inbox with onboarding quantum messages.*
- `def _adjust_stock(market, commodity_id, delta)`
- `def simulate_ai_trade(captains, economy, systems, rng)` - *Move AI traders between systems and mutate local stockpiles through buys and sells.*

---

### [`voidfarer/galaxy.py`](voidfarer/galaxy.py)
> *Procedural galaxy generator, celestial orbital mechanics, and market economy.*

**Size**: `1287` lines (`57353` bytes)

**Classes:**
- `class GalaxyGenerator` - *Generates deterministic star systems, celestial bodies, and hyperlane corridors.*
  - Method `.__init__(seed)`
  - Method `.generate_galaxy()` - *Generate connected star systems across the sector.*
  - Method `._generate_bodies(sys_id, sys_name, spectral, faction)` - *Generate central star and orbiting planetary bodies.*
  - Method `._build_hyperlanes(systems)` - *Calculate hyperlane network ensuring a fully connected graph.*
  - Method `.get_market_quotes(system, body)` - *Compute localized commodity market pricing based on archetype and security.*
  - Method `.get_random_anomaly(seed)` - *Select and instantiate a deep-space anomaly event.*

**Functions:**
- `def black_hole_body(sys_id, sys_name)` - *Construct the black-hole event horizon body for a void gate system.*
- `def compute_habitability_index(body_type, gravity, temperature_c, atmosphere, hazards)` - *Compute a scientific Earth Similarity / Habitability Index in [0.0, 100.0].*
- `def compute_scientific_planet_properties(body_type, spectral_type, orbit_radius_au, rad_sample, grav_sample, temp_jitter, hazards)` - *Derive physically consistent radius_km, gravity, atmosphere, temperature_c, and habitability.*
- `def get_colony_tier(population)` - *Classify world or habitat population into sociological colony tiers.*
- `def step_population_dynamics(body, num_ticks, stability)` - *Advance population with capacity, technology, devastation and civil-order limits.*
- `def world_tech_level(faction, body_type, market_archetype, faction_tech)` - *Re-exported from demographics: tech level of a world from owner and industry.*

---

### [`voidfarer/inventory.py`](voidfarer/inventory.py)
> *Inventory items, consumables, and cargo management.*

**Size**: `180` lines (`5784` bytes)

**Classes:**
- `class InventoryItem` - *Itemized inventory item manifest (trade commodity or usable space consumable).*
  - Method `.to_dict()`

**Functions:**
- `def get_item_info(item_id)` - *Retrieve item metadata, falling back to a default commodity if unlisted.*
- `def calculate_cargo_volume(cargo)` - *Total hold volume currently occupied by inventory cargo.*
- `def get_inventory_manifest(cargo)` - *Compute detailed inventory manifest itemizing quantities, volume footprint, and usability.*

---

### [`voidfarer/logbook.py`](voidfarer/logbook.py)
> *Flight-log windowing: notable galactic news must outlive routine chatter.*

**Size**: `96` lines (`3288` bytes)

**Functions:**
- `def is_notable(line)` - *True when a log line carries galactic news rather than ambient chatter.*
- `def summarize_trades(lines)` - *Collapse one trade line per captain into a single per-tick summary.*
- `def trim_log(lines, limit)` - *Keep the newest half of the log plus the most recent galactic news.*

---

### [`voidfarer/mapmods.py`](voidfarer/mapmods.py)
> *Sector map modifiers: persistent environmental conditions that reshape simulation.*

**Size**: `208` lines (`7603` bytes)

**Functions:**
- `def get_map_modifier(modifier_id)`
- `def generate_map_modifiers(seed, system_id, security, system_index)` - *Generate deterministic per-system modifiers without touching the galaxy RNG stream.*
- `def aggregate_map_modifiers(system)` - *Fold every active map modifier into one effect dictionary.*
- `def describe_modifier_effects(effects)` - *Human readable effect labels for CLI and cockpit rendering.*
- `def system_modifier_summary(system)` - *Serializable modifier summaries for telemetry consumers.*
- `def filter_catalog(category)`

---

### [`voidfarer/messaging.py`](voidfarer/messaging.py)
> *Branching quantum message trees and their consequences.*

**Size**: `290` lines (`11940` bytes)

**Classes:**
- `class MessageNode`
- `class MessageTree`
  - Method `.node(node_id)`

**Functions:**
- `def tree_root_message(tree_id, tick, message_id)`
- `def follow_up_message(tree_id, node_id, tick, parent_id)`
- `def choice_by_id(message, choice_id)`
- `def tree_catalog()`

---

### [`voidfarer/models.py`](voidfarer/models.py)
> *Domain state models and frozen data transfer objects for VoidFarer.*

**Size**: `2148` lines (`79664` bytes)

**Classes:**
- `class Moon` - *Natural satellite orbiting a planet.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class CelestialBody` - *Represents a planetary, stellar, or orbital body in a star system.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class MapModifier` - *Persistent environmental condition that reshapes local sector simulation.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class StarSystem` - *Represents a star system with celestial bodies and hyperlane links.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class Commodity` - *Trade goods and planetary resources.*
- `class MarketQuote` - *Current price quotation for a commodity at a local market.*
- `class ShipPower` - *Reactor power distribution across primary subsystems (sum <= 100).*
  - Method `.__post_init__()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnomalyChoice` - *Player decision branch for resolving a deep-space anomaly encounter.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AnomalyEncounter` - *Procedurally triggered deep-space anomaly event.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class FleetDrone` - *Autonomous fleet asset deployed to star systems for mining, scouting, or escort.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AICaptain` - *Persistent autonomous captain that trades, hails, allies, or fights.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class Depot` - *System-local cargo depot that can hold and sell commodities.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class MessageChoice` - *One branch of an interactive message-tree node.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class QuantumMessage` - *Intergalactic quantum-encrypted message stored in the ship inbox.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class ShipUpgrade` - *Modular hardware upgrade installed on flagship.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class CombatEncounter` - *Hostile deep-space pirate or automated intercept encounter.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class BountyContract` - *Dynamic mission contract leveraging Zeigarnik task completion tension.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class PrecursorRelic` - *Ancient artifact dropped via variable ratio schedule with passive multipliers.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class PilotMastery` - *Self-Determination Theory competence framework: XP, levels, and talent specs.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class TutorialStep` - *A progressive instructional milestone in the Cadet Flight Academy.*
  - Method `.__post_init__()`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class TutorialState` - *State of the Cadet Flight Academy onboarding progression.*
  - Property `.is_active`
  - Property `.current_step`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class StoryRequirements` - *Gating conditions that must hold before a story choice or chapter unlocks.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class StoryChoice` - *Branching story decision impacting faction alignment, rewards, and narrative path.*
  - Property `.label`
  - Property `.consequence_summary`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class StoryTransmission` - *Character audio dispatch received across the subspace radio array.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class StoryChapter` - *An episodic narrative chapter in the Precursor Cipher campaign.*
  - Property `.id`
  - Property `.synopsis`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class StoryState` - *Master progression tracker for narrative campaign and faction standings.*
  - Property `.active_act`
  - Property `.current_chapter_id`
  - Property `.current_chapter`
  - Property `.faction_reputation`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class TravelState` - *In-system transit to a celestial body or to an empty-space vector.*
  - Method `.progress(current_tick)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class VoidTraversalState` - *Transit through the Hollow Between along a void lane between black-hole anchors.*
  - Method `.progress(current_tick)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class DecisionChoice` - *One selectable response to a pending decision event.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class DecisionEvent` - *A blocking decision that must be resolved before time or flight advances.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class PirateEncounter` - *A pirate toll encounter that must be resolved before flight continues.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class GameEvent` - *Realtime popup event delivered to the cockpit.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class ReactorState` - *Thermal and structural state of the fusion reactor core.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class PlayerCharacter` - *Persistent commander profile with aging, skills, and activatable abilities.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class ResearchState` - *Research progress and completed technology unlocks.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class Outpost` - *Player-owned planetary or orbital installation that produces value each tick.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class FleetShip` - *Player-owned escort warship attached to the fleet manager.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class FactionLeader` - *Individual leader whose behavior drives a faction's simulation policy.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class WarState` - *Active or concluded war between two sovereign factions.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class FactionEconomy` - *Per-faction treasury and the derived flows that feed it every tick.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class TradeLink` - *A live commercial route between two peaceful factions.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class CrewMember` - *Recruitable crew specialist with a role, morale, wage, and portrait.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class TradeOrder` - *A quantum freight order: cargo leaves now and is sold at the destination on arrival.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class AwayMission` - *An away-team expedition assigned to a celestial body for a finite duration.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class ShipState` - *Complete telemetry, resource inventory, and status of the player's flagship.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class TimeState` - *Universal cosmic stardate, simulation ticks, and time control state.*
  - Property `.era`
  - Property `.current_date` - *In-game calendar date (DD.MM.YYYY), starting 01.01.3042 at tick zero.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class EconomicEvent` - *Cosmic economic shock, boom, crisis, or embargo shifting commodity supply and prices.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class SystemMarketState` - *Localized commodity supply stockpiles, demand pressures, and local production.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class GlobalEconomyState` - *Galactic economy simulation tracking localized market states and macro-economic events.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class CodexState` - *Persistent captain's log progress: claimed milestones and their dates.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class GameState` - *Master simulation universe state container.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`

---

### [`voidfarer/navigation.py`](voidfarer/navigation.py)
> *Navigation routing, jump planning, and black-hole hazard helpers.*

**Size**: `182` lines (`6395` bytes)

**Functions:**
- `def shortest_route(systems, start_id, target_id)`
- `def route_plan(systems, start_id, target_id, base_jump_fuel)`
- `def system_has_black_hole(system)`
- `def void_anchor_systems(systems)` - *Ids of systems holding a black-hole event horizon, sorted for determinism.*
- `def system_distance_ly(a, b)`
- `def generate_void_lanes(systems, galaxy_seed)` - *Deterministically derive the void-lane graph of the Hollow Between.*
- `def void_shortest_route(lanes, start_id, target_id)`
- `def void_lane_metrics(systems, first, second)` - *Fuel cost and duration for one void lane crossing.*
- `def void_route_plan(systems, galaxy_seed, start_id, target_id)` - *Plan a multi-lane traversal through the Hollow Between.*

---

### [`voidfarer/outposts.py`](voidfarer/outposts.py)
> *Outpost construction and production catalogs.*

**Size**: `185` lines (`6852` bytes)

**Classes:**
- `class OutpostType`
  - Method `.to_dict()`

**Functions:**
- `def get_outpost_type(outpost_type)`
- `def can_build_on(body, outpost_type)`
- `def outpost_population_capacity(outpost_type, level)` - *Housing ceiling for an installation: colony domes hold far more than a mining rig.*
- `def outpost_capacity_for(outpost)` - *Stored housing ceiling, falling back to the catalog for older saves.*
- `def grow_outpost_population(outpost, num_ticks)` - *Logistic settlement growth toward the housing ceiling, never past it.*
- `def build_outpost(outpost_type, system_id, body, current_tick, existing_count)`
- `def outpost_tick_production(outpost, yield_multiplier)` - *Effective per-tick yield: catalog base, level growth, then modules and map multipliers.*
- `def upgrade_outpost(outpost, cost_scale)`

---

### [`voidfarer/pirates.py`](voidfarer/pirates.py)
> *Pirate bands, toll encounters, and deterministic raid generation.*

**Size**: `98` lines (`3097` bytes)

**Classes:**
- `class PirateRisk`

**Functions:**
- `def pirate_risk(system, faction_standing, has_escort, evasion)` - *Risk of a pirate toll encounter in a system, before the engine RNG roll.*
- `def generate_pirate_encounter(system, seed, threat_level, standing)` - *Build a deterministic pirate toll encounter for one jump or orbit.*

---

### [`voidfarer/reactor.py`](voidfarer/reactor.py)
> *Reactor core simulation: operating modes, thermal load, cooling, and derating.*

**Size**: `159` lines (`6429` bytes)

**Functions:**
- `def get_reactor_mode(mode)`
- `def reactor_derating(reactor)` - *Efficiency multiplier from core integrity and thermal saturation.*
- `def reactor_output_efficiency(reactor, output_bonus)` - *Effective output multiplier applied to every powered subsystem.*
- `def reactor_cooling_rate(reactor, equipment_bonuses, map_cooling_bonus)`
- `def reactor_heat_capacity(reactor, equipment_bonuses)`
- `def simulate_reactor_tick(reactor, total_allocation, num_ticks, equipment_bonuses, map_effects, hull_hazard, output_bonus)` - *Advance reactor heat and integrity for the given number of ticks.*
- `def vent_reactor(reactor, current_tick, cooldown_ticks)` - *Emergency coolant purge: dump heat anywhere, at a small integrity cost.*

---

### [`voidfarer/research.py`](voidfarer/research.py)
> *Research projects and technology bonuses.*

**Size**: `179` lines (`5777` bytes)

**Classes:**
- `class ResearchProject`
  - Method `.to_dict()`

**Functions:**
- `def get_research_project(project_id)`
- `def calculate_research_bonuses(completed)`
- `def available_projects(completed, active_project_id)`

---

### [`voidfarer/retention.py`](voidfarer/retention.py)
> *Psychological retention mechanics, Precursor relics, dynamic contracts, and pilot mastery.*

**Size**: `437` lines (`15358` bytes)

**Functions:**
- `def generate_contract(rng, category)` - *Procedurally instantiate a fresh BountyContract following Zeigarnik task loops.*
- `def generate_initial_contracts(rng)` - *Generate the starter trio of active contracts across distinct categories.*
- `def roll_relic_drop(rng, bonus_prob, forced_tier, current_system)` - *Execute a Variable Ratio drop roll for Precursor Relics.*
- `def calculate_passive_multipliers(ship)` - *Calculate aggregate multipliers across streak, installed relics, and pilot talents.*

---

### [`voidfarer/server.py`](voidfarer/server.py)
> *Zero-dependency embedded HTTP server and REST API for the VoidFarer Web Cockpit.*

**Size**: `1313` lines (`55984` bytes)

**Classes:**
- `class ThreadedHTTPServer` - *Multi-threaded HTTP server handling concurrent HUD telemetry requests.*
- `class VoidFarerHandler` - *Handles REST API actions and serves static cockpit assets.*
  - Method `.log_message(format, *args)` - *Suppress standard access logs for clean terminal output.*
  - Method `._send_json(data, status)`
  - Method `._without_catalogs(data)` - *Drop static catalogs from the snapshot a response carries under `state` or `data`.*
  - Method `._send_error_json(message, status, include_state)`
  - Method `._read_body_json()`
  - Method `.do_OPTIONS()`
  - Method `.do_GET()`
  - Method `.do_POST()`
  - Method `._do_post()`
- `class BackgroundServer` - *Handle for a concurrent server + simulation ticker launched from the REPL.*
  - Method `.__init__(server, server_thread, ticker, stop_event, engine, storage)`
  - Property `.port`
  - Method `.stop()`

**Functions:**
- `def _int_field(body, key, default, minimum)`
- `def _float_field(body, key, default, minimum)`
- `def _bool_field(body, key, default)`
- `def tick_interval(speed)` - *Wall-clock seconds between simulation ticks for a chrono speed multiplier.*
- `def start_background_server(engine, storage, port, host)` - *Launch the cockpit server and simulation ticker without blocking the REPL.*
- `def run_server(engine, storage, port, host, open_browser, enable_ticker)` - *Start local cockpit HTTP server daemon with background temporal ticker.*

---

### [`voidfarer/shipmods.py`](voidfarer/shipmods.py)
> *Structural ship modifications: permanent refits with explicit trade-offs.*

**Size**: `208` lines (`7179` bytes)

**Classes:**
- `class ShipMod` - *A permanent structural refit available at orbital drydocks.*
  - Method `.to_dict()`

**Functions:**
- `def get_ship_mod(mod_id)`
- `def get_available_ship_mods(installed)`
- `def get_ship_mod_sell_value(mod_id)`
- `def calculate_ship_mod_bonuses(ship_mods)` - *Aggregate structural modification effects into the common bonus keyspace.*
- `def slot_label(slot)`
- `def slot_code(slot)` - *Short, always-fitting code for the 48px silhouette case.*

---

### [`voidfarer/storage.py`](voidfarer/storage.py)
> *Crash-resilient storage engine and atomic persistence for VoidFarer.*

**Size**: `194` lines (`7708` bytes)

**Classes:**
- `class StorageManager` - *Manages power-loss safe atomic persistence and shadow backups.*
  - Method `.__init__(data_dir)`
  - Method `._write_atomic(target_path, data)` - *Write JSON payload atomically using a unique temporary file, fsync, and shadow backup.*
  - Method `._read_json_file(target_path)`
  - Method `._quarantine(target_path)`
  - Method `._slot_path(slot)`
  - Method `.save(state, slot)` - *Atomically persist universe and ship state into the requested save slot.*
  - Method `.load(slot)` - *Load game state from disk for the given slot, quarantining corrupt primary data and trying the backup.*
  - Method `.clear(slot)` - *Remove save file and shadow backup for the given slot.*
  - Method `.delete_save(slot)` - *Delete a save slot and its shadow backup.*
  - Method `.list_saves()` - *List all available save slots with summary metadata.*

**Functions:**
- `def resolve_slot_name(slot)` - *Validate and normalize a save slot identifier.*
- `def _extract_save_summary(slot_name, path, data)` - *Build a compact metadata dictionary for a save slot.*

---

### [`voidfarer/story.py`](voidfarer/story.py)
> *Interactive Cadet Flight Academy tutorial and branching narrative campaign systems.*

**Size**: `505` lines (`22710` bytes)

**Functions:**
- `def generate_initial_tutorial()` - *Construct a fresh Cadet Flight Academy tutorial state.*
- `def generate_initial_story()` - *Construct fresh narrative campaign state.*
- `def resolve_story_ending(story)` - *Deterministically resolve which ending variant the campaign resolves to.*
- `def ending_transmission(ending_id, timestamp_system)` - *Build the final campaign transmission for a resolved ending.*
- `def migrate_story_state(story)` - *Extend a legacy campaign save into the current chapter list, preserving all resolved state.*

---

### [`voidfarer/surface.py`](voidfarer/surface.py)
> *Surface operations: choose what your landing party does after touchdown.*

**Size**: `169` lines (`5265` bytes)

**Classes:**
- `class SurfaceOperation`
  - Method `.to_dict()`

**Functions:**
- `def _stable_unit(*parts)`
- `def surface_risk(operation, body)`
- `def surface_report(ship, body)`
- `def resolve_surface_operation(operation, body, ship, galaxy_seed, tick)`

---

### [`voidfarer/upgrades.py`](voidfarer/upgrades.py)
> *Hardware upgrade catalog, fleet drone definitions, shipyard chassis, and equipment registry.*

**Size**: `433` lines (`15077` bytes)

**Classes:**
- `class ShipChassis` - *Pre-configured spacecraft hull chassis available for purchase at orbital shipyards.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`

**Functions:**
- `def get_upgrade(upgrade_id)`
- `def get_available_upgrades(installed)` - *Return upgrades that have not yet been installed.*
- `def get_chassis(chassis_id)`
- `def get_chassis_for_ship_class(ship_class)` - *Resolve the commissioned chassis from the ship class recorded in the save.*
- `def calculate_equipment_bonuses(ship)` - *Aggregate equipped module and chassis stat bonuses into effective multipliers.*
- `def get_available_chassis(current_chassis_id)` - *Return ship chassis available for purchase (excluding current ship).*
- `def get_sell_value(upgrade_id)` - *Calculate credit trade-in value when selling or uninstalling a hardware module (60% of base cost).*

---

### [`voidfarer/weapons.py`](voidfarer/weapons.py)
> *Weapon catalog and combat modifiers.*

**Size**: `56` lines (`2337` bytes)

**Classes:**
- `class WeaponSpec`
  - Method `.to_dict()`

**Functions:**
- `def get_weapon(weapon_id)`
- `def weapon_catalog()`

---
