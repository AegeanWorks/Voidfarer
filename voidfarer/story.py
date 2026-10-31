"""Interactive Cadet Flight Academy tutorial and branching narrative campaign systems."""

from __future__ import annotations

from typing import Any

from voidfarer.models import (
    PilotMastery,
    PrecursorRelic,
    ShipState,
    StoryChapter,
    StoryChoice,
    StoryRequirements,
    StoryState,
    StoryTransmission,
    TutorialState,
    TutorialStep,
)

# Initial 6-step progressive scaffolding for Cadet Flight Academy
INITIAL_TUTORIAL_STEPS: tuple[TutorialStep, ...] = (
    TutorialStep(
        id="step_orbit",
        title="Orbital Insertion",
        instruction="Establish an orbital trajectory around a local celestial body.",
        hint="Run `orbit sol_body_1` or click 'ENTER ORBIT' on the Radar HUD.",
        reward_credits=200,
        reward_xp=80,
    ),
    TutorialStep(
        id="step_scan",
        title="Planetary Sensor Sweep",
        instruction="Perform a deep sensor scan of your orbiting body to analyze resources and detect relics.",
        hint="Run `scan` or click 'SENSOR SCAN' on the top status deck.",
        reward_credits=250,
        reward_xp=100,
    ),
    TutorialStep(
        id="step_power",
        title="Reactor Power Routing",
        instruction="Re-route reactor core output across engines, shields, sensors, and weapons.",
        hint="Run `power 30 25 25 20` or adjust the reactor sliders in Web HUD.",
        reward_credits=200,
        reward_xp=80,
    ),
    TutorialStep(
        id="step_trade",
        title="Orbital Station Commerce",
        instruction="Access a station commodity exchange and execute a buy or sell trade.",
        hint="Run `buy fuel_cells 1` or click BUY on the Commerce terminal.",
        reward_credits=300,
        reward_xp=120,
    ),
    TutorialStep(
        id="step_drone",
        title="Autonomous Fleet Command",
        instruction="Commission an autonomous drone asset to begin harvesting remote star systems.",
        hint="Run `fleet buy mining` or commission an asset in the Fleet tab.",
        reward_credits=350,
        reward_xp=150,
    ),
    TutorialStep(
        id="step_jump",
        title="Hyperspace Jump Transit",
        instruction="Spin up quantum warp drives and execute a hyperlane jump to an adjacent star system.",
        hint="Run `jump alpha_centauri` or target Alpha Centauri on the Galaxy Map.",
        reward_credits=400,
        reward_xp=200,
    ),
)


def generate_initial_tutorial() -> TutorialState:
    """Construct a fresh Cadet Flight Academy tutorial state."""
    return TutorialState(
        active=True,
        current_step_index=0,
        steps=INITIAL_TUTORIAL_STEPS,
        completed=False,
        skipped=False,
    )


# Narrative Campaign: "The Precursor Cipher"
CAMPAIGN_CHAPTERS: tuple[StoryChapter, ...] = (
    StoryChapter(
        chapter_index=0,
        title="Act I: The Ghost Transmission",
        target_system_id="sol",
        objective="Investigate the harmonic subspace pulse originating from Sol's asteroid belt.",
        transmission=StoryTransmission(
            speaker="Admiral Vance",
            callsign="SC-HighCommand",
            channel="Encrypted Coalition Command",
            message="Commander Astraea. Long-range sensor arrays on Mars detected an anomalous signal on 1420 MHz. It matches ancient Precursor mathematical constants. We need an autonomous scout to investigate immediately.",
            timestamp_system="sol",
        ),
        choices=(
            StoryChoice(
                id="choice_vance_telemetry",
                text="Transmit decoded telemetry directly to Coalition Naval High Command.",
                faction_alignment="coalition",
                reward_credits=800,
                outcome_text="Admiral Vance commends your loyalty. Coalition patrol corvettes bolster local system security.",
                sets_flags=("intel_shared_coalition",),
                follow_up=StoryTransmission(
                    speaker="Admiral Vance",
                    callsign="SC-HighCommand",
                    channel="Encrypted Coalition Command",
                    message="Telemetry received and verified, Commander. You have earned Coalition trust — and its long memory.",
                    timestamp_system="sol",
                ),
            ),
            StoryChoice(
                id="choice_cipher_leak",
                text="Leak encrypted telemetry to Cipher's Syndicate shadow-relay for heavy black-market credits.",
                faction_alignment="syndicate",
                reward_credits=1400,
                reward_relic_id="relic_cipher_key",
                outcome_text="Cipher transfers black-market credits and an ancient Decryption Key into your vault.",
                sets_flags=("intel_leaked_syndicate",),
                follow_up=StoryTransmission(
                    speaker="Cipher",
                    callsign="Shadow-Relay",
                    channel="Shadow Frequency 99.4",
                    message="A profitable exchange, Commander. The Syndicate remembers friends — and forgets nothing.",
                    timestamp_system="sol",
                ),
            ),
        ),
        completed=False,
    ),
    StoryChapter(
        chapter_index=1,
        title="Act II: The Sirius Fabrication Reliquary",
        target_system_id="sirius",
        objective="Travel to Sirius System and establish orbit around the ancient orbital relic reliquary.",
        transmission=StoryTransmission(
            speaker="Cipher",
            callsign="Shadow-Relay",
            channel="Shadow Frequency 99.4",
            message="Impressive flying, Commander. The beacon telemetry revealed coordinates to a dormant Precursor nanite reliquary buried in the Sirius corona. The Coalition wants to weaponize it, but true explorers know its value.",
            timestamp_system="sirius",
        ),
        choices=(
            StoryChoice(
                id="choice_salvage_core",
                text="Extract the Precursor Core Matrix directly into your flagship reactor.",
                faction_alignment="precursor",
                reward_credits=1000,
                reward_relic_id="relic_core_matrix",
                outcome_text="Alien nanites synchronize with your core reactor, dramatically surging engine power and shields.",
                sets_flags=("core_matrix_installed",),
            ),
            StoryChoice(
                id="choice_colony_power",
                text="Reconfigure the reliquary to power the struggling Sirius Frontier Colony orbital habitat.",
                faction_alignment="coalition",
                reward_credits=900,
                reward_relic_id="relic_humanitarian_medal",
                outcome_text="Thousands of frontier colonists celebrate your heroic deed. Station merchants grant permanent discounts.",
                sets_flags=("sirius_colony_powered",),
            ),
        ),
        completed=False,
    ),
    StoryChapter(
        chapter_index=2,
        title="Act III: The Gateway of Eternity",
        target_system_id="vega",
        objective="Navigate to Vega System to confront the Precursor AI guardian and decide the fate of the galaxy.",
        transmission=StoryTransmission(
            speaker="Archon Intelligence",
            callsign="Archon-Prime",
            channel="Subspace Void Broadcast",
            message="Organic entity verified. For 100,000 stellar cycles, this gate has slept. You carry our resonance keys. Choose: will humanity claim the hyperlane stars, or shall the gateways return to silence?",
            timestamp_system="vega",
        ),
        choices=(
            StoryChoice(
                id="choice_unleash_gateways",
                text="Activate the Precursor Hyperlane Super-Gateways for infinite galactic exploration.",
                faction_alignment="precursor",
                reward_credits=3000,
                reward_relic_id="relic_archon_crest",
                outcome_text="The galaxy blazes with iridescent hyperlane streams! You are hailed as the First VoidFarer of the New Age.",
                sets_flags=("gateways_open",),
            ),
            StoryChoice(
                id="choice_safeguard_lock",
                text="Seal the gateways behind an impenetrable quantum firewall to prevent extra-galactic incursions.",
                faction_alignment="coalition",
                reward_credits=2500,
                reward_relic_id="relic_sentinel_matrix",
                outcome_text="The gateway locks with a resonant hum. Galactic civilization enters an era of fortified defense.",
                sets_flags=("gateways_sealed",),
            ),
        ),
        completed=False,
    ),
    StoryChapter(
        chapter_index=3,
        title="Act IV: The Hollow Between",
        target_system_id="cygnus_x1",
        objective="Descend to the Cygnus Void Gate event horizon and answer the echo of the First VoidFarers.",
        transmission=StoryTransmission(
            speaker="Echo of the First VoidFarers",
            callsign="Hollow-Chorus",
            channel="Beyond the Event Horizon",
            message="Little navigator. The lanes you walk are ripples on a deeper sea. Beyond the black horizons lies the Hollow Between — the void our ships once sailed. Come to the Cygnus gate. Hold the horizon. Listen.",
            timestamp_system="cygnus_x1",
        ),
        choices=(
            StoryChoice(
                id="choice_first_dive",
                text="Swear the Voidfarer's Oath and attune your hull to the Hollow Between.",
                faction_alignment="precursor",
                reward_credits=1200,
                reward_relic_id="relic_void_compass",
                outcome_text="The echo harmonizes with your reactor core. Your hull remembers the first dive — and the void steadies around you.",
                sets_flags=("voidfarer_oath",),
                follow_up=StoryTransmission(
                    speaker="Echo of the First VoidFarers",
                    callsign="Hollow-Chorus",
                    channel="Beyond the Event Horizon",
                    message="The oath is sworn. The compass points into the dark. Sail carefully, VoidFarer: the Hollow rewards the bold and swallows the careless.",
                    timestamp_system="cygnus_x1",
                ),
            ),
            StoryChoice(
                id="choice_horizon_witness",
                text="Hold the accretion shelf and chart the rift without descending.",
                faction_alignment="coalition",
                reward_credits=1600,
                reward_relic_id="relic_horizon_lens",
                outcome_text="From the shimmering shelf you map the rift's geometry. Coalition cartographers immortalize your restraint.",
                sets_flags=("horizon_witnessed",),
                follow_up=StoryTransmission(
                    speaker="Admiral Vance",
                    callsign="SC-HighCommand",
                    channel="Encrypted Coalition Command",
                    message="Sound judgment at the Cygnus gate, Commander. The charts you held back may save a thousand ships.",
                    timestamp_system="cygnus_x1",
                ),
            ),
        ),
        completed=False,
        requirements=StoryRequirements(orbit_body_id="cygnus_x1_black_hole"),
    ),
    StoryChapter(
        chapter_index=4,
        title="Act V: Echoes of the First VoidFarers",
        target_system_id="rift_station",
        objective="Carry the void's answer to The Dark Abyss and decide what the echoes become.",
        transmission=StoryTransmission(
            speaker="Echo of the First VoidFarers",
            callsign="Hollow-Chorus",
            channel="Beyond the Event Horizon",
            message="The chorus gathers at the Dark Abyss, where our last ships vanished. What we leave behind is yours to shape: a title, an archive, or a bargain. Choose what the echoes become.",
            timestamp_system="rift_station",
        ),
        choices=(
            StoryChoice(
                id="choice_claim_title",
                text="Claim the title: succeed the First VoidFarers as navigators of the Hollow Between.",
                faction_alignment="precursor",
                reward_credits=2000,
                reward_relic_id="relic_echo_crown",
                outcome_text="The chorus falls silent, then sings as one. The Crown of Echoes settles on your brow.",
                sets_flags=("title_claimed",),
                requirements=StoryRequirements(required_flags=("voidfarer_oath",)),
                locked_text="Requires swearing the Voidfarer's Oath at the Cygnus Void Gate (Act IV).",
            ),
            StoryChoice(
                id="choice_archive_echoes",
                text="Archive the echo chorus in the Coalition deep-vaults so no empire can weaponize it.",
                faction_alignment="coalition",
                reward_credits=2400,
                outcome_text="The echoes rest in encrypted silence. The Coalition awards you its highest civilian honor.",
                sets_flags=("echoes_archived",),
            ),
            StoryChoice(
                id="choice_sell_echoes",
                text="Sell the echo recordings to Cipher's shadow-relay as the ultimate black-market artifact.",
                faction_alignment="syndicate",
                reward_credits=5000,
                outcome_text="Cipher pays a fortune for the song of the dead. Somewhere in the dark, a broker smiles.",
                sets_flags=("echoes_sold",),
                requirements=StoryRequirements(required_flags=("intel_leaked_syndicate",)),
                locked_text="Requires leaking the Cipher telemetry to the Syndicate in Act I.",
            ),
        ),
        completed=False,
    ),
)


def generate_initial_story() -> StoryState:
    """Construct fresh narrative campaign state."""
    first_ch = CAMPAIGN_CHAPTERS[0]
    return StoryState(
        campaign_title="The Precursor Cipher",
        current_chapter_index=0,
        chapters=CAMPAIGN_CHAPTERS,
        transmission_log=(first_ch.transmission,),
        reputation={"coalition": 0, "syndicate": 0, "precursor": 0},
        completed=False,
    )


# Unique Story Relics
STORY_RELICS: dict[str, PrecursorRelic] = {
    "relic_cadet_wings": PrecursorRelic(
        id="relic_cadet_wings",
        name="Cadet Honor Wings",
        rarity="rare",
        description="Awarded for graduating from the Cadet Flight Academy (+15 HP and +15% scan research bounty).",
        passive_stat="max_hull",
        stat_multiplier=15.0,
        bonuses={"scan_bounty": 0.15},
    ),
    "relic_cipher_key": PrecursorRelic(
        id="relic_cipher_key",
        name="Syndicate Cipher Key",
        rarity="epic",
        description="Decrypted alien quantum cipher granting +25% trade profit margins across all markets.",
        passive_stat="trade_margin",
        stat_multiplier=0.25,
    ),
    "relic_core_matrix": PrecursorRelic(
        id="relic_core_matrix",
        name="Precursor Core Matrix",
        rarity="legendary",
        description="Alien energy matrix increasing hyperlane jump fuel efficiency by +35% and laser power by +25%.",
        passive_stat="fuel_efficiency",
        stat_multiplier=0.35,
        bonuses={"laser_dmg": 0.25},
    ),
    "relic_humanitarian_medal": PrecursorRelic(
        id="relic_humanitarian_medal",
        name="Frontier Humanitarian Medal",
        rarity="epic",
        description="Conferred by grateful Sirius colonists (+35 MW maximum shield capacity).",
        passive_stat="shield_cap",
        stat_multiplier=35.0,
    ),
    "relic_archon_crest": PrecursorRelic(
        id="relic_archon_crest",
        name="Archon's Eternal Crest",
        rarity="legendary",
        description="The ultimate mark of the Precursor Architects (+40% laser strike power and +50% research bounty).",
        passive_stat="laser_dmg",
        stat_multiplier=0.40,
        bonuses={"scan_bounty": 0.50},
    ),
    "relic_sentinel_matrix": PrecursorRelic(
        id="relic_sentinel_matrix",
        name="Sentinel Aegis Matrix",
        rarity="legendary",
        description="Galactic defense seal reinforcing flagship structural integrity (+50 HP and +40 MW shields).",
        passive_stat="max_hull",
        stat_multiplier=50.0,
        bonuses={"shield_cap": 40.0},
    ),
    "relic_void_compass": PrecursorRelic(
        id="relic_void_compass",
        name="Void Compass of the First Dive",
        rarity="legendary",
        description="Harmonized echo of the Hollow Between (+20 void traversal stability).",
        passive_stat="void_stability",
        stat_multiplier=20.0,
    ),
    "relic_horizon_lens": PrecursorRelic(
        id="relic_horizon_lens",
        name="Horizon Lens",
        rarity="epic",
        description="Refracted chart of the Cygnus rift (+20% scan research bounty).",
        passive_stat="scan_bounty",
        stat_multiplier=0.20,
    ),
    "relic_echo_crown": PrecursorRelic(
        id="relic_echo_crown",
        name="Crown of Echoes",
        rarity="legendary",
        description="Succession crown of the First VoidFarers (+25% laser power, +25% scan bounty, +10 void stability).",
        passive_stat="laser_dmg",
        stat_multiplier=0.25,
        bonuses={"scan_bounty": 0.25, "void_stability": 10.0},
    ),
}


# Human-readable glossary for story flags set by campaign choices
STORY_FLAG_GLOSSARY: dict[str, str] = {
    "intel_shared_coalition": "Sharing the Cipher telemetry with Coalition High Command (Act I)",
    "intel_leaked_syndicate": "Leaking the Cipher telemetry to the Syndicate shadow-relay (Act I)",
    "core_matrix_installed": "Extracting the Precursor Core Matrix at Sirius (Act II)",
    "sirius_colony_powered": "Powering the Sirius Frontier Colony (Act II)",
    "gateways_open": "Activating the Precursor Hyperlane Super-Gateways (Act III)",
    "gateways_sealed": "Sealing the gateways behind the quantum firewall (Act III)",
    "voidfarer_oath": "Swearing the Voidfarer's Oath at the Cygnus Void Gate (Act IV)",
    "horizon_witnessed": "Charting the Cygnus rift from the accretion shelf (Act IV)",
    "title_claimed": "Claiming the title of the First VoidFarers (Act V)",
    "echoes_archived": "Archiving the echo chorus in Coalition deep-vaults (Act V)",
    "echoes_sold": "Selling the echo recordings to the Syndicate (Act V)",
}


# Campaign Endings
ENDING_VARIANTS: dict[str, dict[str, str]] = {
    "ending_first_voidfarer": {
        "title": "First VoidFarer of the Hollow Between",
        "epilogue": "With the Crown of Echoes upon your brow, the void lanes steady at your approach. Where the Precursors vanished, you now sail — and the chorus follows your wake like a tide.",
        "speaker": "Echo of the First VoidFarers",
        "message": "The title passes. The Hollow has a new navigator. Sail far, VoidFarer, and sing us home.",
    },
    "ending_sentinel": {
        "title": "Sentinel of the Charted Stars",
        "epilogue": "The echo chorus rests in encrypted silence within the Coalition deep-vaults. The charted stars sleep safer for it, and your name is spoken in every harbor of the realm.",
        "speaker": "Admiral Vance",
        "message": "The void will always call, Commander. Tonight, the realm sleeps because you did not answer alone.",
    },
    "ending_shadow_broker": {
        "title": "Shadow Broker of the Lanes",
        "epilogue": "The song of the dead sells for a fortune in the dark markets of the rift. Somewhere beyond the horizons, Cipher's brokers raise a glass to your name — and keep a file on it.",
        "speaker": "Cipher",
        "message": "The echo recordings were pristine, Commander. The Syndicate's appreciation is... substantial. And permanent.",
    },
}


def resolve_story_ending(story: StoryState) -> str:
    """Deterministically resolve which ending variant the campaign resolves to."""
    flags = story.flags
    if flags.get("echoes_sold"):
        return "ending_shadow_broker"
    if flags.get("title_claimed"):
        return "ending_first_voidfarer"
    return "ending_sentinel"


def ending_transmission(ending_id: str, timestamp_system: str = "rift_station") -> StoryTransmission:
    """Build the final campaign transmission for a resolved ending."""
    variant = ENDING_VARIANTS.get(ending_id, ENDING_VARIANTS["ending_sentinel"])
    return StoryTransmission(
        speaker=variant["speaker"],
        callsign="Campaign-Epilogue",
        channel="Subspace Void Broadcast",
        message=variant["message"],
        timestamp_system=timestamp_system,
    )


# Migration for legacy 3-act campaign saves
LEGACY_CAMPAIGN_LENGTH = 3

VOID_AWAKENING_TRANSMISSION = StoryTransmission(
    speaker="Echo of the First VoidFarers",
    callsign="Hollow-Chorus",
    channel="Beyond the Event Horizon",
    message="Little navigator. You thought the song ended at the gate. The verses you have not yet heard wait beyond the black horizons. Come to the Cygnus gate. Hold the horizon. Listen.",
    timestamp_system="cygnus_x1",
)


def migrate_story_state(story: StoryState) -> StoryState:
    """Extend a legacy campaign save into the current chapter list, preserving all resolved state.

    Legacy saves carry the first three acts. This appends the newer acts, and reopens a
    completed legacy campaign so the new acts become playable. Fresh or already-current
    saves pass through unchanged.
    """
    if story.campaign_title != "The Precursor Cipher":
        return story
    current_length = len(story.chapters)
    if current_length >= len(CAMPAIGN_CHAPTERS) or current_length == 0:
        return story

    merged = list(story.chapters)
    for chapter in CAMPAIGN_CHAPTERS[current_length:]:
        merged.append(chapter)

    was_completed = story.completed
    new_index = story.current_chapter_index
    if was_completed:
        new_index = current_length

    new_transmissions = list(story.transmission_log)
    if was_completed:
        new_transmissions.append(VOID_AWAKENING_TRANSMISSION)

    return StoryState(
        campaign_title=story.campaign_title,
        current_chapter_index=new_index,
        chapters=tuple(merged),
        transmission_log=tuple(new_transmissions),
        reputation=dict(story.reputation),
        completed=False,
        flags=dict(story.flags),
        ending_id=None,
    )

# Factory aliases
create_initial_tutorial_state = generate_initial_tutorial
create_initial_story_state = generate_initial_story
