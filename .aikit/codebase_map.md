# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `64`
- **Total Classes**: `158`
- **Total Top-Level Functions**: `198`
- **Total Class Methods**: `899`
- **Total Source Lines**: `26742`

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

**Size**: `198` lines (`8509` bytes)

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

---

### [`tests/test_cockpit_layout.py`](tests/test_cockpit_layout.py)
> *Layout regression tests for the holographic web cockpit (index.html / style.css / app.js).*

**Size**: `692` lines (`31456` bytes)

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
  - Method `.test_skills_strip_has_icons_hotkeys_and_training_wiring()`
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

---

### [`tests/test_combat_void_depth.py`](tests/test_combat_void_depth.py)
> *Regression tests for progression-scaled combat and Hollow resonance risk/reward.*

**Size**: `200` lines (`8546` bytes)

**Classes:**
- `class TestProgressionThreatScaling`
  - Method `.test_threat_multiplier_starts_flat_and_grows()`
  - Method `.test_generated_enemy_scales_with_threat_level()`
  - Method `.test_dreadnought_boss_is_gated_behind_mastery()`
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

**Size**: `221` lines (`10258` bytes)

**Classes:**
- `class CharacterResearchOutpostTest`
  - Method `.setUp()`
  - Method `.test_character_state_round_trip_and_age()`
  - Method `.test_train_skill_requires_points_and_valid_skill()`
  - Method `.test_emergency_repair_ability_heals_and_sets_cooldown()`
  - Method `.test_research_project_completes_on_tick()`
  - Method `.test_unknown_research_project_rejected()`
  - Method `.test_outpost_builds_and_produces_on_tick()`
  - Method `.test_outpost_requires_orbit()`
- `class FactionDiplomacyWarTest`
  - Method `.setUp()`
  - Method `.test_leaders_generated_deterministically()`
  - Method `.test_diplomacy_improve_and_declare_war()`
  - Method `.test_resolve_wars_captures_and_eliminates_faction()`
- `class FleetAndNavigationTest`
  - Method `.setUp()`
  - Method `.test_escort_purchase_requires_credits_and_dock()`
  - Method `.test_fleet_damage_and_casualties()`
  - Method `.test_battle_stance_and_solar_panel_upgrade()`
  - Method `.test_route_planning()`
  - Method `.test_black_holes_and_ring_worlds_exist()`
- `class NewSystemsSerializationAndCLITest`
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

### [`tests/test_reactor_map_shipmods.py`](tests/test_reactor_map_shipmods.py)
> *Regression tests for reactor simulation, sector map modifiers, and ship modifications.*

**Size**: `269` lines (`11583` bytes)

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

**Size**: `399` lines (`16518` bytes)

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

### [`tests/test_transit_civ_events.py`](tests/test_transit_civ_events.py)
> *Tests for in-system transit (TravelState), planetary civilization metadata, and cockpit GameEvents.*

**Size**: `355` lines (`16253` bytes)

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

**Size**: `50` lines (`2155` bytes)

**Classes:**
- `class AuditHelpersTest`
  - Method `.test_wide_viewports_get_only_window_chrome()`
  - Method `.test_laptop_keeps_an_exact_iframe()`
  - Method `.test_parse_audit_reads_an_escaped_payload()`
  - Method `.test_parse_audit_refuses_a_missing_payload()`
  - Method `.test_prepare_static_injects_the_collector_and_wrapper()`
  - Method `.test_severe_findings_name_the_blocking_categories()`

---

### [`tests/test_ui_inventory.py`](tests/test_ui_inventory.py)
> *The cockpit inventory proof covers controls, handlers, routes, hotkeys and theme tokens.*

**Size**: `34` lines (`1276` bytes)

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

### [`tools/__init__.py`](tools/__init__.py)
> *Developer proofs for VoidFarer.*

**Size**: `1` lines (`38` bytes)

---

### [`tools/ui_audit.py`](tools/ui_audit.py)
> *Capture VoidFarer cockpit screenshots and a measurable UI audit with headless Edge or Chrome.*

**Size**: `861` lines (`33205` bytes)

**Functions:**
- `def find_browser()` - *Locate an installed Edge or Chrome executable without a third-party dependency.*
- `def outer_window(viewport)` - *Outer window size that yields the requested inner viewport for Windows desktop sizes.*
- `def prepare_static(source, workdir)` - *Copy the cockpit and add a same-origin viewport wrapper plus an error collector.*
- `def parse_audit(dom)` - *Read the JSON audit payload out of a dumped wrapper DOM.*
- `def run_browser(browser, url, viewport, profile, screenshot, timeout)` - *Run one headless capture at a viewport and return stdout, stderr and the exit code.*
- `def audit_viewport(browser, port, name, viewport, workdir, out, timeout, scenario, tab)` - *Capture one viewport and return its parsed audit report.*
- `def summary_line(report)` - *One ASCII-safe console line for a viewport report.*
- `def severe_findings(report)` - *Names of findings that should fail an explicit audit check.*
- `def write_report(reports, out, browser)` - *Write the combined JSON and Markdown evidence packet.*
- `def main(argv)` - *Run the audit, write screenshots plus JSON/Markdown, and print a concise summary.*

---

### [`tools/ui_browser.py`](tools/ui_browser.py)
> *Drive the real VoidFarer cockpit in Edge through Playwright.*

**Size**: `334` lines (`14954` bytes)

**Functions:**
- `def _open_cockpit(page, scenario, tab, timeout)` - *Wait for the cockpit and move it into the requested review state.*
- `def _metrics(page)` - *Return viewport, scroll, element and tiny-text counts from the live page.*
- `def _run_viewport(browser, url, name, viewport, scenario, tab, out, timeout, scroll)` - *Open one real browser viewport, drive it and capture a true screenshot.*
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

### [`voidfarer/character.py`](voidfarer/character.py)
> *Commander character progression, skills, and activatable abilities.*

**Size**: `130` lines (`5086` bytes)

**Functions:**
- `def skill_level(character, skill)`
- `def skill_bonus(character, skill)` - *Percent bonus per skill level above baseline.*
- `def train_skill(character, skill)`
- `def award_character_xp(character, amount)`
- `def advance_age(character, elapsed_days_before, elapsed_days_after)`
- `def ability_ready(character, ability_id)`
- `def start_ability_cooldown(character, ability_id)`
- `def tick_ability_cooldowns(character, num_ticks)`

---

### [`voidfarer/cli.py`](voidfarer/cli.py)
> *Command-line interface and interactive terminal REPL for VoidFarer.*

**Size**: `2585` lines (`132149` bytes)

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
- `def cmd_weapons(engine, storage, parts)`
- `def cmd_repl(engine, storage)` - *Launch interactive terminal command session.*
- `def cmd_events(engine, storage, parts)` - *List or dismiss cockpit popup events.*
- `def main(argv)` - *Main CLI entrypoint.*

---

### [`voidfarer/codex.py`](voidfarer/codex.py)
> *Captain's log and discovery codex: milestones, statistics, and rewards.*

**Size**: `556` lines (`18952` bytes)

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

**Size**: `219` lines (`7858` bytes)

**Classes:**
- `class CrewRole`
  - Method `.to_dict()`

**Functions:**
- `def get_crew_role(role_id)`
- `def recruit_crew_member(role_id, seed, current_count)`
- `def calculate_crew_bonuses(crew)`
- `def crew_upkeep(crew)`
- `def tick_crew(crew, num_ticks, credits_available, rng)` - *Advance wages and morale; unpaid crews sink toward desertion.*
- `def apply_morale_event(crew, delta, reason)` - *Shift every active member's morale by an event delta, clamped to 0..100.*
- `def shore_leave_restore(crew)` - *Compute a fleet-wide shore leave outcome: restored crew and morale points.*
- `def crew_catalog()`

---

### [`voidfarer/economy.py`](voidfarer/economy.py)
> *Dynamic Global Economy, supply/demand simulation, economic events, and galactic trade network.*

**Size**: `399` lines (`15039` bytes)

**Functions:**
- `def generate_initial_economy(systems, rng)` - *Construct baseline economy state with localized stockpiles and initial macroeconomic conditions.*
- `def tick_global_economy(state, num_ticks, systems, rng)` - *Advance economic simulation: update stockpiles, decrement event clocks, spawn emergent news.*
- `def faction_standing_price_factor(faction_standing)` - *Return the single diplomatic price multiplier for a faction standing value.*
- `def calculate_dynamic_market_quote(system, body, commodity, economy, faction_standing)` - *Compute precision localized pricing reflecting global stockpile supply/demand and macroeconomic events.*
- `def get_galactic_trade_routes(systems, economy)` - *Compute the most profitable interstellar trade routes across all explored star systems.*

---

### [`voidfarer/enemies.py`](voidfarer/enemies.py)
> *Hostile Enemy Archetypes, Tactical Combat AI, and Procedural Intercept Generation.*

**Size**: `279` lines (`10978` bytes)

**Classes:**
- `class EnemyArchetype` - *Blueprint for procedural hostile intercepts across galactic territories.*

**Functions:**
- `def threat_multiplier(threat_level)` - *Scale generated intercept strength with the pilot's command experience.*
- `def choose_enemy_intent(profile, special_ability, ability_ready, enemy_hull, enemy_max_hull, enemy_shield, enemy_max_shield, player_hull, player_max_hull, player_shield, player_max_shield, player_combo)` - *Pick the next hostile maneuver from hull, shield, combo, and AI profile state.*
- `def generate_system_enemy(system_id, security, faction, seed, threat_level)` - *Generate a procedurally balanced CombatEncounter matching star system characteristics.*

---

### [`voidfarer/engine.py`](voidfarer/engine.py)
> *Deterministic state machine and simulation engine for VoidFarer.*

**Size**: `5569` lines (`278884` bytes)

**Classes:**
- `class SimulationEngine` - *Coordinates space flight, star navigation, fleet drones, upgrades, and tactical combat.*
  - Method `.__init__(seed, state)`
  - Method `._bootstrap_frontier()` - *Backfill frontier systems for legacy saves without changing the save schema.*
  - Method `._clone_ship(**kwargs)` - *Create a new ShipState preserving all unspecified telemetry and inventory attributes.*
  - Method `._clone_state(**kwargs)` - *Create a new GameState preserving time, stats, economy, and all unspecified universe fields.*
  - Method `._research_bonuses()`
  - Method `._skill(skill)`
  - Method `._combined_equipment(ship)`
  - Method `._crew_bonuses(ship)`
  - Method `._map_effects(system)` - *Aggregate the active map modifiers of a system (defaults to the current one).*
  - Method `._effective_power(subsystem, ship)` - *Allocated subsystem power after reactor mode, heat, and integrity derating.*
  - Method `._recompute_caps(ship, equipped, ship_mods)` - *Recompute maximum hull, shield, cargo, and fuel from chassis, modules, and mods.*
  - Method `._grant_cargo(cargo, commodity_id, quantity)` - *Add as many units as the hold allows, returning (granted, overflow).*
  - Method `._replace_system_body(body_id, **changes)` - *Return a systems map with one body of the current system replaced.*
  - Method `._apply_relic_stat_bonuses(hull, max_hull, shield, max_shield, relics)` - *Raise current and maximum hull/shield for newly acquired permanent relics.*
  - Method `._progress_tutorial(action_type)` - *Advance the Cadet Flight Academy if current step requirement is satisfied.*
  - Method `._award_pilot_xp(amount, current_mastery)` - *Award experience points and compute level promotions and talent points.*
  - Method `._progress_contracts(category, amount)` - *Advance matching active contracts toward completion objectives.*
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
  - Method `.compute_body_distance_au(target_body, origin_body)` - *Compute 2D polar Euclidean distance in AU between two bodies (or current orbit/star origin).*
  - Method `.orbit(body_id)` - *Establish orbital trajectory around a celestial body in the current system.*
  - Method `._transit_risk(system, mode, effects)` - *Sector hazard risk for one in-system transit, reduced by piloting and quantum drive.*
  - Method `._travel_plan(body_id, mode)` - *Compute a transit plan without mutating state; shared by preview and execution.*
  - Method `.preview_travel(body_id, mode)` - *Return ETA, fuel, risk and hazard names for a potential transit.*
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
  - Method `.cash_flow()` - *Per-tick credit flow telemetry: crew upkeep against passive income estimates.*
  - Method `.install_weapon(weapon_id)`
  - Method `.set_primary_weapon(weapon_id)`
  - Method `.get_weapon_report()`
  - Method `.resolve_message_choice(message_id, choice_id)`
  - Method `.get_message_tree_report()`
  - Method `.trade(commodity_id, quantity, is_buy)` - *Execute buy or sell commodity order at orbiting market.*
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
  - Method `.combat_action(action)` - *Execute a tactical combat maneuver against an active hostile intercept.*
  - Method `.resolve_anomaly(choice_id)` - *Resolve current deep-space anomaly encounter with power-check validation.*
  - Method `.repair_hull(amount)` - *Repair ship hull integrity at orbital station.*
  - Method `.refuel(amount)` - *Refuel quantum drive at orbital station.*
  - Method `.step_orbits(delta_time)` - *Advance celestial bodies along orbital mechanics paths and cycle fleet drones.*
  - Method `.claim_contract(contract_id)` - *Claim rewards for a fulfilled contract and immediately draw a new assignment.*
  - Method `.unlock_talent(talent_id)` - *Unlock a Pilot Specialization Perk using available talent points.*
  - Method `._story_unmet_requirements(requirements, *, chapter)` - *List human-readable unmet gating conditions for a chapter or choice.*
  - Method `.story_status()` - *Objective snapshot of the narrative campaign for CLI, REST, and cockpit parity.*
  - Method `.make_story_choice(choice_id)` - *Resolve a branching story dilemma in the active campaign chapter.*
  - Method `.skip_tutorial()` - *Skip Cadet Flight Academy and unlock unrestricted operational status.*
  - Method `.reset_tutorial()` - *Reset Cadet Flight Academy to step 1 for revision or retraining.*
  - Property `.current_chassis_id` - *Id of the chassis matching the ship's commissioned class (falls back to the class name).*
  - Method `.get_status_snapshot()` - *Produce a comprehensive JSON serializable telemetry snapshot for the HUD.*
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
  - Method `.salvage_derelict()` - *Board the current body's derelict hulk for cargo, credits, and hazard risk.*
  - Method `.scoop_fuel()` - *Recover fuel from a star, gas giant, or ice body currently in orbit.*
  - Method `.train_crew_member(crew_id)` - *Run a paid training drill that raises one crew member's skill rank.*
  - Method `.shore_leave()` - *Grant fleet-wide shore leave at a docked station, restoring crew morale for credits.*
  - Method `.hire_mercenary(merc_id)`
  - Method `.dismiss_fleet_unit(drone_id)`
  - Method `.refit_fleet_unit(drone_id)`
  - Method `.form_alliance(captain_id)`
  - Method `.tick(num_ticks)` - *Advance the simulation universe by num_ticks.*
  - Method `.emit_event(kind, title, message)` - *Create and append a cockpit popup GameEvent.*
  - Method `.dismiss_event(event_id)` - *Mark a cockpit popup GameEvent as dismissed.*
  - Method `.pause_time()` - *Pause simulation temporal clock while preserving current playback rate.*
  - Method `.resume_time()` - *Resume simulation temporal clock restoring previous speed multiplier.*
  - Method `.set_time_speed(speed)` - *Set simulation speed multiplier (0.0x to 10.0x).*
  - Method `.step_time(num_ticks)` - *Advance simulation by a discrete number of ticks.*

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

### [`voidfarer/faction_state.py`](voidfarer/faction_state.py)
> *Dynamic faction leaders, behaviors, war resolution, and elimination.*

**Size**: `164` lines (`7241` bytes)

**Functions:**
- `def generate_faction_leaders(seed)` - *Create one deterministic leader per canonical sovereign faction.*
- `def _faction_systems(faction_id, systems)`
- `def faction_strength(faction_id, systems)`
- `def resolve_wars(wars, systems, rng, current_tick, eliminated)` - *Advance wars, transfer territory, and eliminate factions that lose all systems.*
- `def simulate_faction_behaviors(leaders, wars, systems, rng, current_tick, eliminated, num_ticks)` - *Apply leader archetypes: declare wars, then resolve active fronts.*
- `def leader_for(leaders, faction_id)`

---

### [`voidfarer/factions.py`](voidfarer/factions.py)
> *Galactic Factions, Megacorporations, Standings, and Geopolitical Mechanics.*

**Size**: `250` lines (`9842` bytes)

**Classes:**
- `class Faction` - *Sovereign faction or interstellar coalition.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class Corporation` - *Interstellar megacorporation shaping sector commerce and industrial technology.*
  - Method `.to_dict()`
  - Method `.from_dict(data)`

**Functions:**
- `def get_faction(faction_id)` - *Retrieve canonical faction by ID.*
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

**Size**: `176` lines (`6939` bytes)

**Functions:**
- `def generate_ai_captains(systems, seed)` - *Create a deterministic roster of autonomous captains distributed across the galaxy.*
- `def generate_depots(systems)` - *Create one system-local depot per star system.*
- `def generate_welcome_messages(tick)` - *Seed the inbox with onboarding quantum messages.*
- `def _adjust_stock(market, commodity_id, delta)`
- `def simulate_ai_trade(captains, economy, systems, rng)` - *Move AI traders between systems and mutate local stockpiles through buys and sells.*

---

### [`voidfarer/galaxy.py`](voidfarer/galaxy.py)
> *Procedural galaxy generator, celestial orbital mechanics, and market economy.*

**Size**: `907` lines (`40437` bytes)

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
- `def step_population_dynamics(body, num_ticks)` - *Advance population deterministically based on habitability and world type.*

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

**Size**: `1809` lines (`66570` bytes)

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
- `class TravelState` - *In-system transit between two celestial bodies.*
  - Method `.progress(current_tick)`
  - Method `.to_dict()`
  - Method `.from_dict(data)`
- `class VoidTraversalState` - *Transit through the Hollow Between along a void lane between black-hole anchors.*
  - Method `.progress(current_tick)`
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
- `class CrewMember` - *Recruitable crew specialist with a role, morale, wage, and portrait.*
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

**Size**: `151` lines (`5277` bytes)

**Classes:**
- `class OutpostType`
  - Method `.to_dict()`

**Functions:**
- `def get_outpost_type(outpost_type)`
- `def can_build_on(body, outpost_type)`
- `def build_outpost(outpost_type, system_id, body, current_tick, existing_count)`
- `def outpost_tick_production(outpost, yield_multiplier)`
- `def upgrade_outpost(outpost, cost_scale)`

---

### [`voidfarer/reactor.py`](voidfarer/reactor.py)
> *Reactor core simulation: operating modes, thermal load, cooling, and derating.*

**Size**: `156` lines (`6161` bytes)

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

**Size**: `388` lines (`13747` bytes)

**Functions:**
- `def generate_contract(rng, category)` - *Procedurally instantiate a fresh BountyContract following Zeigarnik task loops.*
- `def generate_initial_contracts(rng)` - *Generate the starter trio of active contracts across distinct categories.*
- `def roll_relic_drop(rng, bonus_prob, forced_tier, current_system)` - *Execute a Variable Ratio drop roll for Precursor Relics.*
- `def calculate_passive_multipliers(ship)` - *Calculate aggregate multipliers across streak, installed relics, and pilot talents.*

---

### [`voidfarer/server.py`](voidfarer/server.py)
> *Zero-dependency embedded HTTP server and REST API for the VoidFarer Web Cockpit.*

**Size**: `1158` lines (`48496` bytes)

**Classes:**
- `class ThreadedHTTPServer` - *Multi-threaded HTTP server handling concurrent HUD telemetry requests.*
- `class VoidFarerHandler` - *Handles REST API actions and serves static cockpit assets.*
  - Method `.log_message(format, *args)` - *Suppress standard access logs for clean terminal output.*
  - Method `._send_json(data, status)`
  - Method `._send_error_json(message, status)`
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

**Size**: `193` lines (`6683` bytes)

**Classes:**
- `class ShipMod` - *A permanent structural refit available at orbital drydocks.*
  - Method `.to_dict()`

**Functions:**
- `def get_ship_mod(mod_id)`
- `def get_available_ship_mods(installed)`
- `def get_ship_mod_sell_value(mod_id)`
- `def calculate_ship_mod_bonuses(ship_mods)` - *Aggregate structural modification effects into the common bonus keyspace.*
- `def slot_label(slot)`

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
