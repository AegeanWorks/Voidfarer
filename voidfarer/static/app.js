/**
 * VOIDFARER // Tactical Cockpit & Autonomous Galaxy Simulator
 * Master Web Client: Canvas Radar, Procedural Web Audio Synth, Fleet/Arsenal Controller, and REST Link.
 */

const TICKS_PER_SECOND = 2.0;

const SKILL_META = {
    piloting: { name: "Piloting", icon: "✈", desc: "Improves sublight maneuverability, warp efficiency, and evasion." },
    engineering: { name: "Engineering", icon: "⚙", desc: "Boosts repair speed, shield recharge, and module efficiency." },
    science: { name: "Science", icon: "🔬", desc: "Increases scan range, research speed, and anomaly rewards." },
    combat: { name: "Combat", icon: "⚔", desc: "Enhances weapon damage, targeting, and combat abilities." },
    diplomacy: { name: "Diplomacy", icon: "⚖", desc: "Improves standing gains, trade prices, and crew morale." },
    trade: { name: "Trade", icon: "💱", desc: "Increases cargo capacity, buy/sell margins, and depot efficiency." }
};
const SKILL_HOTKEYS = ["⇧1", "⇧2", "⇧3", "⇧4", "⇧5", "⇧6"];
// Activatable commander powers, in hotkey order (SHIFT+1..6).
const ABILITY_ORDER = ["overclock", "emergency_repair", "battle_focus", "charm_offensive", "science_burst", "trade_instinct"];
const ABILITY_META = {
    overclock: { icon: "⚡", name: "Reactor Overclock", label: "Overclock" },
    emergency_repair: { icon: "🛠", name: "Emergency Repair", label: "Repair" },
    battle_focus: { icon: "🎯", name: "Battle Focus", label: "Battle Focus" },
    charm_offensive: { icon: "⚖", name: "Diplomatic Offensive", label: "Diplomacy" },
    science_burst: { icon: "🔬", name: "Science Burst", label: "Science" },
    trade_instinct: { icon: "💱", name: "Trade Instinct", label: "Trade" },
};
const ABILITY_UNLOCK_RANK = { charm_offensive: 7, trade_instinct: 7 };
// Left terminal rail order, top to bottom; [ and ] cycle through it.
const TERMINAL_TABS = [
    "player", "skills", "crew", "ship", "market", "arsenal", "fleet", "contracts",
    "empire", "quests", "ai", "depot", "messages", "story", "factions", "codex",
];
const TRADE_LOTS = ["1", "5", "10", "max"];
// Code-constant catalogs from /api/catalogs, fetched once. Once present, every API call sends
// the cache header so state payloads leave them out, and CockpitApp.state merges them back.
let catalogCache = null;
const CATALOG_CACHE_HEADER = "X-VoidFarer-Catalogs";

function apiFetch(url, options = {}) {
    if (!catalogCache) return fetch(url, options);
    return fetch(url, { ...options, headers: { ...(options.headers || {}), [CATALOG_CACHE_HEADER]: "1" } });
}

async function loadCatalogs() {
    try {
        const res = await fetch("/api/catalogs");
        const json = await res.json();
        if (json.ok && json.data) catalogCache = json.data;
    } catch (e) {
        console.error("Error loading catalogs:", e);
    }
}
// Stored under localStorage "voidfarer_settings"; RESET DEFAULTS restores exactly these.
const SETTINGS_DEFAULTS = {
    sound: true, volume: 0.8, radarGrid: true, radarLabels: true, travelAnimation: true,
    starDensity: 220, uiDensity: "auto", uiScale: 1, rememberTab: true, lastTab: "player",
    tradeLot: "1", autoPause: true, autoClaim: false,
};

class SoundController {
    constructor() {
        this.ctx = null;
        this.master = null;
        this.enabled = true;
        this.volume = 0.8;
    }

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
                // Every voice connects here, so one gain is the master volume.
                this.master = this.ctx.createGain();
                this.master.gain.value = this.volume;
                this.master.connect(this.ctx.destination);
            }
        }
        if (this.ctx && this.ctx.state === "suspended") {
            this.ctx.resume();
        }
    }

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }

    setVolume(volume) {
        this.volume = Math.min(1, Math.max(0, Number(volume)));
        if (this.master) this.master.gain.value = this.volume;
    }

    playBeep(freq = 880, duration = 0.08, type = "sine") {
        if (!this.enabled || !this.ctx) return;
        try {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
            gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start();
            osc.stop(this.ctx.currentTime + duration);
        } catch (e) {}
    }

    playScan() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(400, now);
            osc.frequency.exponentialRampToValueAtTime(1400, now + 0.35);
            gain.gain.setValueAtTime(0.15, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.38);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.4);
        } catch (e) {}
    }

    playJump() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(150, now);
            osc.frequency.exponentialRampToValueAtTime(40, now + 0.6);
            gain.gain.setValueAtTime(0.2, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.65);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.7);
        } catch (e) {}
    }

    playChime() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            [523.25, 659.25, 783.99].forEach((freq, idx) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = "triangle";
                osc.frequency.setValueAtTime(freq, now + idx * 0.06);
                gain.gain.setValueAtTime(0.12, now + idx * 0.06);
                gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.06 + 0.25);
                osc.connect(gain);
                gain.connect(this.master);
                osc.start(now + idx * 0.06);
                osc.stop(now + idx * 0.06 + 0.28);
            });
        } catch (e) {}
    }

    playAlarm() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "square";
            osc.frequency.setValueAtTime(320, now);
            osc.frequency.setValueAtTime(240, now + 0.15);
            gain.gain.setValueAtTime(0.12, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.38);
        } catch (e) {}
    }

    playTransmission() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            [880, 1174, 987, 1318].forEach((freq, idx) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(freq, now + idx * 0.05);
                gain.gain.setValueAtTime(0.12, now + idx * 0.05);
                gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.05 + 0.08);
                osc.connect(gain);
                gain.connect(this.master);
                osc.start(now + idx * 0.05);
                osc.stop(now + idx * 0.05 + 0.09);
            });
        } catch (e) {}
    }

    playLaser() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(850, now);
            osc.frequency.exponentialRampToValueAtTime(80, now + 0.18);
            gain.gain.setValueAtTime(0.2, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.22);
        } catch (e) {}
    }

    playLevelUp() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = "sine";
                osc.frequency.setValueAtTime(freq, now + idx * 0.08);
                gain.gain.setValueAtTime(0.18, now + idx * 0.08);
                gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 0.35);
                osc.connect(gain);
                gain.connect(this.master);
                osc.start(now + idx * 0.08);
                osc.stop(now + idx * 0.08 + 0.38);
            });
        } catch (e) {}
    }

    playBountyChime() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            [392.00, 523.25, 659.25].forEach((freq, idx) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = "triangle";
                osc.frequency.setValueAtTime(freq, now + idx * 0.09);
                gain.gain.setValueAtTime(0.2, now + idx * 0.09);
                gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.09 + 0.4);
                osc.connect(gain);
                gain.connect(this.master);
                osc.start(now + idx * 0.09);
                osc.stop(now + idx * 0.09 + 0.42);
            });
        } catch (e) {}
    }

    playCritHit() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(1200, now);
            osc.frequency.exponentialRampToValueAtTime(60, now + 0.35);
            gain.gain.setValueAtTime(0.35, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.38);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.4);
        } catch (e) {}
    }

    playNearMiss() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(987.77, now);
            osc.frequency.linearRampToValueAtTime(1318.51, now + 0.2);
            osc.frequency.linearRampToValueAtTime(1174.66, now + 0.45);
            gain.gain.setValueAtTime(0.16, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.52);
        } catch (e) {}
    }
}

class CockpitApp {
    get state() {
        return this._state;
    }

    set state(value) {
        this._state = value && catalogCache ? Object.assign(value, catalogCache) : value;
    }

    constructor() {
        this.sound = new SoundController();
        this.celestial = window.CelestialRenderer ? new window.CelestialRenderer() : null;
        this.state = null;
        this.galaxySystems = {};
        this.viewMode = "ORBITS"; // "ORBITS" or "GALAXY"
        this.activeRightTab = null; // null when collapsed, or "market", "arsenal", etc.
        this.selectedTarget = null; // CelestialBody or StarSystem
        this.selectedType = null; // 'body' or 'system'
        this.refreshInFlight = false;
        this.rafId = null;
        this.dpr = 1;
        this.viewW = 1280;
        this.viewH = 720;
        this.uiDensity = "auto";
        this.uiScale = 1;
        this.drawerUserToggled = false;

        // Canvas radar state
        this.canvas = document.getElementById("radarCanvas");
        this.ctx = this.canvas.getContext("2d");
        this.zoom = 1.0;
        this.panX = 0;
        this.panY = 0;
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.hoveredItem = null;
        this.radarGrid = true;
        this.radarLabels = true;
        this.travelAnimationEnabled = true;
        this.travelAnimation = null;
        this.radarBackdrop = null;
        this.radarBackdropKey = null;
        this.savesList = [];
        this.activeSaveSlot = "default";
        this.gameStarted = false;
        this.loadSettings();
        this.terminalPointerDown = false;
        this.skillsPointerDown = false;
        this.deathAcknowledged = false;

        this.initDOMElements();
        this.bindEvents();
        this.initTooltips();
        this.openInitialTerminalTab();
        this.applyViewportProfile();
        this.syncRadarControlState();
        this.startAnimationLoop();
        this.fetchGalaxy();
        this.fetchSaves();
        this.openMainMenu(); // Show main menu on startup

        // Live sync: catalogs first so polls stay lite, then a cadence that follows the chrono.
        loadCatalogs().finally(() => this.schedulePoll());
    }

    initDOMElements() {
        // Cosmic Chronometer & Time Controls
        this.chronoStardate = document.getElementById("chronoStardate");
        this.chronoTick = document.getElementById("chronoTick");
        this.timeStatusBadge = document.getElementById("timeStatusBadge");
        this.btnTimePause = document.getElementById("btnTimePause");
        this.btnTime1x = document.getElementById("btnTime1x");
        this.btnTime2x = document.getElementById("btnTime2x");
        this.btnTime5x = document.getElementById("btnTime5x");
        this.btnTime10x = document.getElementById("btnTime10x");
        this.btnTimeStep = document.getElementById("btnTimeStep");
        this.timeSpeedButtons = [this.btnTime1x, this.btnTime2x, this.btnTime5x, this.btnTime10x];

        // Vitals
        this.hullBar = document.getElementById("hullBar");
        this.hullVal = document.getElementById("hullVal");
        this.shieldBar = document.getElementById("shieldBar");
        this.shieldVal = document.getElementById("shieldVal");
        this.fuelBar = document.getElementById("fuelBar");
        this.fuelVal = document.getElementById("fuelVal");
        this.creditsVal = document.getElementById("creditsVal");
        this.cargoSummary = document.getElementById("cargoSummary");

        // Top actions
        this.audioToggleBtn = document.getElementById("audioToggleBtn");
        this.audioIcon = document.getElementById("audioIcon");
        this.quickScanBtn = document.getElementById("quickScanBtn");

        // Nav
        this.radarTitle = document.getElementById("radarTitle");
        this.viewOrbitBtn = document.getElementById("viewOrbitBtn");
        this.viewGalaxyBtn = document.getElementById("viewGalaxyBtn");
        this.radarCoords = document.getElementById("radarCoords");

        // Target Card
        this.targetType = document.getElementById("targetType");
        this.targetName = document.getElementById("targetName");
        this.targetDist = document.getElementById("targetDist");
        this.targetDesc = document.getElementById("targetDesc");
        this.btnOrbitTarget = document.getElementById("btnOrbitTarget");
        this.btnQuantumTarget = document.getElementById("btnQuantumTarget");
        this.btnLandTarget = document.getElementById("btnLandTarget");
        this.surfaceOps = document.getElementById("surfaceOps");
        this.btnSalvageTarget = document.getElementById("btnSalvageTarget");
        this.btnScoopFuel = document.getElementById("btnScoopFuel");
        this.salvageInfo = document.getElementById("salvageInfo");
        this.btnJumpTarget = document.getElementById("btnJumpTarget");
        this.targetGravity = document.getElementById("targetGravity");
        this.targetAtmosphere = document.getElementById("targetAtmosphere");
        this.targetTemp = document.getElementById("targetTemp");
        this.targetHabitability = document.getElementById("targetHabitability");
        this.targetMoons = document.getElementById("targetMoons");
        this.targetFaction = document.getElementById("targetFaction");
        this.targetPopulation = document.getElementById("targetPopulation");
        this.targetDevastation = document.getElementById("targetDevastation");
        this.targetGovernment = document.getElementById("targetGovernment");
        this.targetResources = document.getElementById("targetResources");
        this.transitPlan = document.getElementById("transitPlan");
        this.transitPreviewToken = 0;
        this.transitPreviewBodyId = null;
        this.transitPreviewAt = 0;
        this.transitPreviewData = null;
        this.eventPopupContainer = document.getElementById("eventPopupContainer");

        // Power Matrix
        this.sliderEng = document.getElementById("sliderEng");
        this.sliderShd = document.getElementById("sliderShd");
        this.sliderSen = document.getElementById("sliderSen");
        this.sliderWep = document.getElementById("sliderWep");
        this.pwrEngVal = document.getElementById("pwrEngVal");
        this.pwrShdVal = document.getElementById("pwrShdVal");
        this.pwrSenVal = document.getElementById("pwrSenVal");
        this.pwrWepVal = document.getElementById("pwrWepVal");
        this.powerTotal = document.getElementById("powerTotal");
        this.applyPowerBtn = document.getElementById("applyPowerBtn");
        this.panelReactor = document.getElementById("panelReactor");
        this.btnToggleReactor = document.getElementById("btnToggleReactor");
        this.powerDirty = false;

        // Log
        this.flightLogStream = document.getElementById("flightLogStream");
        this.logPanel = document.getElementById("logPanel");
        this.btnToggleLog = document.getElementById("btnToggleLog");

        // Combat Card
        this.combatCard = document.getElementById("combatCard");
        this.combatEnemyTitle = document.getElementById("combatEnemyTitle");
        this.combatEnemyFaction = document.getElementById("combatEnemyFaction");
        this.combatEnemyHp = document.getElementById("combatEnemyHp");
        this.combatEnemyBar = document.getElementById("combatEnemyBar");
        this.combatShieldContainer = document.getElementById("combatShieldContainer");
        this.combatEnemyShield = document.getElementById("combatEnemyShield");
        this.combatEnemyShieldBar = document.getElementById("combatEnemyShieldBar");
        this.combatTelegraphBanner = document.getElementById("combatTelegraphBanner");
        this.combatTelegraphText = document.getElementById("combatTelegraphText");
        this.btnCombatFire = document.getElementById("btnCombatFire");
        this.btnCombatDrone = document.getElementById("btnCombatDrone");
        this.btnCombatTarget = document.getElementById("btnCombatTarget");
        this.btnCombatAbsorb = document.getElementById("btnCombatAbsorb");
        this.btnCombatEvade = document.getElementById("btnCombatEvade");
        this.btnCombatFlee = document.getElementById("btnCombatFlee");
        this.combatComboBadge = document.getElementById("combatComboBadge");
        this.combatComboCount = document.getElementById("combatComboCount");
        this.critReadyText = document.getElementById("critReadyText");

        // Anomaly Card
        this.anomalyCard = document.getElementById("anomalyCard");
        this.anomalyTitle = document.getElementById("anomalyTitle");
        this.anomalyDesc = document.getElementById("anomalyDesc");
        this.anomalyChoices = document.getElementById("anomalyChoices");
        this.pirateCard = document.getElementById("pirateCard");
        this.pirateTitle = document.getElementById("pirateTitle");
        this.pirateDesc = document.getElementById("pirateDesc");
        this.pirateTollLine = document.getElementById("pirateTollLine");
        this.btnPiratePay = document.getElementById("btnPiratePay");
        this.btnPirateFight = document.getElementById("btnPirateFight");
        this.btnPirateEvade = document.getElementById("btnPirateEvade");
        this.decisionOverlay = document.getElementById("decisionOverlay");
        this.decisionSeverity = document.getElementById("decisionSeverity");
        this.decisionTitle = document.getElementById("decisionTitle");
        this.decisionDesc = document.getElementById("decisionDesc");
        this.decisionChoices = document.getElementById("decisionChoices");

        // Vitals: Streak & Mastery
        this.vitalStreakCard = document.getElementById("vitalStreakCard");
        this.streakVal = document.getElementById("streakVal");
        this.streakSubtext = document.getElementById("streakSubtext");
        this.vitalMasteryCard = document.getElementById("vitalMasteryCard");
        this.masteryLevelVal = document.getElementById("masteryLevelVal");
        this.masteryBar = document.getElementById("masteryBar");
        this.masterySubtext = document.getElementById("masterySubtext");

        // Cadet Academy Ribbon
        this.cadetBanner = document.getElementById("cadetBanner");
        this.cadetMilestoneTitle = document.getElementById("cadetMilestoneTitle");
        this.cadetMilestoneDesc = document.getElementById("cadetMilestoneDesc");
        this.cadetMilestoneHint = document.getElementById("cadetMilestoneHint");
        this.cadetMilestoneReward = document.getElementById("cadetMilestoneReward");
        this.btnSkipCadet = document.getElementById("btnSkipCadet");
        this.btnResetCadetAcademy = document.getElementById("btnResetCadetAcademy");
        this.cadetGraduationDismissed = false;

        // Left Terminal Deck & Tabs
        this.panelLeft = document.getElementById("panelLeft");
        this.tabBtnMarket = document.getElementById("tabBtnMarket");
        this.tabBtnArsenal = document.getElementById("tabBtnArsenal");
        this.tabBtnShip = document.getElementById("tabBtnShip");
        this.tabBtnFleet = document.getElementById("tabBtnFleet");
        this.tabBtnContracts = document.getElementById("tabBtnContracts");
        this.tabBtnPlayer = document.getElementById("tabBtnPlayer");
        this.tabBtnSkills = document.getElementById("tabBtnSkills");
        this.tabBtnCrew = document.getElementById("tabBtnCrew");
        this.tabBtnEmpire = document.getElementById("tabBtnEmpire");
        this.tabBtnCodex = document.getElementById("tabBtnCodex");
        this.codexBadge = document.getElementById("codexBadge");
        this.tabContentCodex = document.getElementById("tabContentCodex");
        this.codexProgressBadge = document.getElementById("codexProgressBadge");
        this.codexSummaryStrip = document.getElementById("codexSummaryStrip");
        this.codexStatsGrid = document.getElementById("codexStatsGrid");
        this.codexCategoryFilters = document.getElementById("codexCategoryFilters");
        this.codexEntryList = document.getElementById("codexEntryList");
        this.codexLog = document.getElementById("codexLog");
        this.activeCodexCategory = "all";
        this.tabBtnStory = document.getElementById("tabBtnStory");
        this.tabBtnFactions = document.getElementById("tabBtnFactions");
        this.tabBtnQuests = document.getElementById("tabBtnQuests");
        this.tabBtnAI = document.getElementById("tabBtnAI");
        this.tabBtnDepot = document.getElementById("tabBtnDepot");
        this.tabBtnMessages = document.getElementById("tabBtnMessages");
        this.contractsBadge = document.getElementById("contractsBadge");
        this.storyBadge = document.getElementById("storyBadge");
        this.messagesBadge = document.getElementById("messagesBadge");

        this.tabContentMarket = document.getElementById("tabContentMarket");
        this.tabContentArsenal = document.getElementById("tabContentArsenal");
        this.tabContentShip = document.getElementById("tabContentShip");
        this.tabContentFleet = document.getElementById("tabContentFleet");
        this.tabContentContracts = document.getElementById("tabContentContracts");
        this.tabContentPlayer = document.getElementById("tabContentPlayer");
        this.tabContentSkills = document.getElementById("tabContentSkills");
        this.tabContentCrew = document.getElementById("tabContentCrew");
        this.tabContentEmpire = document.getElementById("tabContentEmpire");
        this.tabContentStory = document.getElementById("tabContentStory");
        this.tabContentFactions = document.getElementById("tabContentFactions");
        this.tabContentQuests = document.getElementById("tabContentQuests");
        this.tabContentAI = document.getElementById("tabContentAI");
        this.tabContentDepot = document.getElementById("tabContentDepot");
        this.tabContentMessages = document.getElementById("tabContentMessages");
        this.questsList = document.getElementById("questsList");
        this.questsCompletedList = document.getElementById("questsCompletedList");
        this.aiList = document.getElementById("aiList");
        this.depotSummary = document.getElementById("depotSummary");
        this.depotList = document.getElementById("depotList");
        this.messageList = document.getElementById("messageList");
        this.factionsGrid = document.getElementById("factionsGrid");
        this.corpsGrid = document.getElementById("corpsGrid");

        // Map Controls (moved to right panel)
        this.viewOrbitBtn = document.getElementById("viewOrbitBtn");
        this.viewGalaxyBtn = document.getElementById("viewGalaxyBtn");
        this.btnToggleGrid = document.getElementById("btnToggleGrid");
        this.btnToggleLabels = document.getElementById("btnToggleLabels");

        // Death Overlay
        this.deathOverlay = document.getElementById("deathOverlay");
        this.deathTitle = document.getElementById("deathTitle");
        this.deathMessage = document.getElementById("deathMessage");
        this.deathStats = document.getElementById("deathStats");
        this.btnDeathNewGame = document.getElementById("btnDeathNewGame");
        this.btnDeathLoadSave = document.getElementById("btnDeathLoadSave");
        this.btnDeathMainMenu = document.getElementById("btnDeathMainMenu");

        // Story Comms Elements
        this.storyChapterTitle = document.getElementById("storyChapterTitle");
        this.storyTargetBadge = document.getElementById("storyTargetBadge");
        this.scoreCoalition = document.getElementById("scoreCoalition");
        this.scoreSyndicate = document.getElementById("scoreSyndicate");
        this.scorePrecursor = document.getElementById("scorePrecursor");
        this.storySynopsisText = document.getElementById("storySynopsisText");
        this.storyChoiceContainer = document.getElementById("storyChoiceContainer");
        this.storyChoicesList = document.getElementById("storyChoicesList");
        this.transmissionsStream = document.getElementById("transmissionsStream");
        this.commsLogCount = document.getElementById("commsLogCount");
        this.storyObjectivesBox = document.getElementById("storyObjectivesBox");
        this.storyObjectivesList = document.getElementById("storyObjectivesList");

        // Void Traversal Elements
        this.voidTraversePanel = document.getElementById("voidTraversePanel");
        this.voidStatusBadge = document.getElementById("voidStatusBadge");
        this.voidBody = document.getElementById("voidBody");

        // Contracts & Mastery Containers
        this.contractsList = document.getElementById("contractsList");
        this.btnRefreshContracts = document.getElementById("btnRefreshContracts");
        this.relicsGrid = document.getElementById("relicsGrid");

        // Market
        this.marketTitle = document.getElementById("marketTitle");
        this.marketArch = document.getElementById("marketArch");
        this.marketTableBody = document.getElementById("marketTableBody");
        this.quantumFreight = document.getElementById("quantumFreight");
        this.quantumData = null;
        this.quantumBodyId = null;
        this.noMarketMsg = document.getElementById("noMarketMsg");
        this.cargoDetailed = document.getElementById("cargoDetailed");
        this.cargoMeterFill = document.getElementById("cargoMeterFill");
        this.btnDrydockRepair = document.getElementById("btnDrydockRepair");
        this.btnRefuelTanks = document.getElementById("btnRefuelTanks");

        // Arsenal & Fleet containers
        this.arsenalList = document.getElementById("arsenalList");
        this.shipyardChassisList = document.getElementById("shipyardChassisList");
        this.weaponsBayList = document.getElementById("weaponsBayList");
        this.fleetRoster = document.getElementById("fleetRoster");
        this.fleetShipRoster = document.getElementById("fleetShipRoster");
        this.escortShopGrid = document.getElementById("escortShopGrid");
        this.characterProfile = document.getElementById("characterProfile");
        this.characterAbilities = document.getElementById("characterAbilities");
        this.characterPerks = document.getElementById("characterPerks");
        this.skillsGrid = document.getElementById("skillsGrid");
        this.skillsPointsAvailable = document.getElementById("skillsPointsAvailable");
        this.hudSkillsPanel = document.getElementById("hudSkillsPanel");
        this.hudSkillsGrid = document.getElementById("hudSkillsGrid");
        this.hudSkillsReady = document.getElementById("hudSkillsReady");
        this.btnOpenSkillsTab = document.getElementById("btnOpenSkillsTab");
        this.btnToggleSkills = document.getElementById("btnToggleSkills");
        this.crewAssignments = document.getElementById("crewAssignments");
        this.crewCashFlow = document.getElementById("crewCashFlow");
        this.awaySection = document.getElementById("awaySection");
        this.crewRosterView = document.getElementById("crewRosterView");
        this.crewAwayView = document.getElementById("crewAwayView");
        this.crewAwayCount = document.getElementById("crewAwayCount");
        this.crewViewButtons = Array.from(document.querySelectorAll("[data-crew-view]"));
        this.crewView = "roster";
        this.btnShoreLeave = document.getElementById("btnShoreLeave");
        this.crewShoreNote = document.getElementById("crewShoreNote");
        this.shipVisual = document.getElementById("shipVisual");
        this.shipModulesGrid = document.getElementById("shipModulesGrid");
        this.shipStatsPanel = document.getElementById("shipStatsPanel");
        this.researchSummary = document.getElementById("researchSummary");
        this.researchProjects = document.getElementById("researchProjects");
        this.outpostSummary = document.getElementById("outpostSummary");
        this.outpostList = document.getElementById("outpostList");
        this.diplomacyList = document.getElementById("diplomacyList");
        this.crewRoster = document.getElementById("crewRoster");

        // Reactor simulation strip
        this.reactorHeatFill = document.getElementById("reactorHeatFill");
        this.reactorHeatLabel = document.getElementById("reactorHeatLabel");
        this.reactorOutputLabel = document.getElementById("reactorOutputLabel");
        this.reactorCoolingLabel = document.getElementById("reactorCoolingLabel");
        this.reactorIntegrityLabel = document.getElementById("reactorIntegrityLabel");
        this.reactorModeRow = document.getElementById("reactorModeRow");
        this.btnVentReactor = document.getElementById("btnVentReactor");
        this.sectorModsStrip = document.getElementById("sectorModsStrip");
        this.mercenaryRoster = document.getElementById("mercenaryRoster");
        this.btnHarvestFleet = document.getElementById("btnHarvestFleet");

        // Footer stats
        this.statJumps = document.getElementById("statJumps");
        this.statScans = document.getElementById("statScans");
        this.statTrades = document.getElementById("statTrades");
        this.statVictories = document.getElementById("statVictories");
        this.statAnomalies = document.getElementById("statAnomalies");
        this.statPirates = document.getElementById("statPirates");
        this.statDecisions = document.getElementById("statDecisions");
        this.statLandings = document.getElementById("statLandings");
    }

    bindEvents() {
        // Audio Toggle
        this.audioToggleBtn.addEventListener("click", () => {
            this.sound.init();
            const on = this.sound.toggle();
            this.audioIcon.textContent = on ? "🔊" : "🔇";
            this.audioToggleBtn.style.opacity = on ? "1" : "0.5";
            if (on) this.sound.playBeep(900);
        });

        // Quick Scan
        this.quickScanBtn.addEventListener("click", () => this.handleScan());

        // View Mode Switcher
        this.viewOrbitBtn.addEventListener("click", () => {
            this.sound.init();
            this.sound.playBeep(700);
            this.viewMode = "ORBITS";
            document.body.classList.remove("galaxy-view");
            this.viewOrbitBtn.classList.add("active");
            this.viewGalaxyBtn.classList.remove("active");
            this.selectedTarget = null;
            this.updateTargetCard();
        });

        this.viewGalaxyBtn.addEventListener("click", () => {
            this.sound.init();
            this.sound.playBeep(700);
            this.viewMode = "GALAXY";
            document.body.classList.add("galaxy-view");
            this.viewGalaxyBtn.classList.add("active");
            this.viewOrbitBtn.classList.remove("active");
            this.selectedTarget = null;
            this.updateTargetCard();
        });

        // Radar controls
        document.getElementById("btnZoomIn").addEventListener("click", () => {
            this.zoom = Math.min(2.5, this.zoom + 0.2);
            this.sound.playBeep(1100, 0.04);
        });
        document.getElementById("btnZoomOut").addEventListener("click", () => {
            this.zoom = Math.max(0.4, this.zoom - 0.2);
            this.sound.playBeep(900, 0.04);
        });
        document.getElementById("btnResetView").addEventListener("click", () => {
            this.zoom = 1.0;
            this.panX = 0;
            this.panY = 0;
            this.sound.playBeep(1000, 0.05);
        });

        // Target actions
        this.btnOrbitTarget.addEventListener("click", () => this.handleTravelAction("sublight"));
        this.btnQuantumTarget?.addEventListener("click", () => this.handleTravelAction("quantum"));
        this.btnJumpTarget.addEventListener("click", () => this.handleJumpAction());

        // Power Sliders
        const sliders = [this.sliderEng, this.sliderShd, this.sliderSen, this.sliderWep];
        sliders.forEach(s => s.addEventListener("input", () => {
            this.powerDirty = true;
            this.updatePowerAllocationDisplay();
        }));
        // Releasing a slider routes power; APPLY ROUTE stays as an explicit retry.
        sliders.forEach(s => s.addEventListener("change", () => this.commitPowerRoute()));
        this.applyPowerBtn.addEventListener("click", () => this.handleApplyPower());

        // Presets
        document.getElementById("presetBalanced").addEventListener("click", () => {
            this.setPowerSliders(25, 25, 25, 25);
            this.sound.playBeep(850);
            this.commitPowerRoute();
        });
        document.getElementById("presetSprint").addEventListener("click", () => {
            this.setPowerSliders(45, 20, 20, 15);
            this.sound.playBeep(950);
            this.commitPowerRoute();
        });
        document.getElementById("presetScience").addEventListener("click", () => {
            this.setPowerSliders(20, 20, 45, 15);
            this.sound.playBeep(1050);
            this.commitPowerRoute();
        });

        // Reactor doctrine modes and emergency vent
        if (this.reactorModeRow) {
            this.reactorModeRow.querySelectorAll(".reactor-mode-btn").forEach(btn => {
                btn.addEventListener("click", () => this.handleReactorMode(btn.getAttribute("data-mode")));
            });
        }
        if (this.btnVentReactor) {
            this.btnVentReactor.addEventListener("click", () => this.handleReactorVent());
        }

        // Station Services
        this.btnDrydockRepair.addEventListener("click", () => this.handleRepair());
        this.btnRefuelTanks.addEventListener("click", () => this.handleRefuel());

        // Right Deck Tabs
        this.tabBtnMarket.addEventListener("click", () => this.switchRightTab("market"));
        this.tabBtnArsenal.addEventListener("click", () => this.switchRightTab("arsenal"));
        this.tabBtnShip.addEventListener("click", () => this.switchRightTab("ship"));
        this.tabBtnFleet.addEventListener("click", () => this.switchRightTab("fleet"));

        this.tabBtnContracts.addEventListener("click", () => this.switchRightTab("contracts"));
        if (this.btnRefreshContracts) {
            this.btnRefreshContracts.addEventListener("click", () => this.postAction("/api/contracts/refresh", {}, "contracts"));
        }
        this.tabBtnPlayer.addEventListener("click", () => this.switchRightTab("player"));
        this.tabBtnSkills.addEventListener("click", () => this.switchRightTab("skills"));
        this.tabBtnCrew.addEventListener("click", () => this.switchRightTab("crew"));
        this.crewViewButtons.forEach(button => {
            button.addEventListener("click", () => this.setCrewView(button.getAttribute("data-crew-view")));
        });
        if (this.tabBtnEmpire) this.tabBtnEmpire.addEventListener("click", () => this.switchRightTab("empire"));
        if (this.tabBtnCodex) this.tabBtnCodex.addEventListener("click", () => this.switchRightTab("codex"));
        this.tabBtnStory.addEventListener("click", () => this.switchRightTab("story"));
        if (this.tabBtnFactions) {
            this.tabBtnFactions.addEventListener("click", () => this.switchRightTab("factions"));
        }
        if (this.tabBtnQuests) this.tabBtnQuests.addEventListener("click", () => this.switchRightTab("quests"));
        if (this.tabBtnAI) this.tabBtnAI.addEventListener("click", () => this.switchRightTab("ai"));
        if (this.tabBtnDepot) this.tabBtnDepot.addEventListener("click", () => this.switchRightTab("depot"));
if (this.tabBtnMessages) this.tabBtnMessages.addEventListener("click", () => this.switchRightTab("messages"));

        // Map Controls (in right panel)
        this.btnToggleGrid.addEventListener("click", () => {
            this.radarGrid = !this.radarGrid;
            this.saveSettings();
            this.syncRadarControlState();
            this.drawRadar();
        });
        this.btnToggleLabels.addEventListener("click", () => {
            this.radarLabels = !this.radarLabels;
            this.saveSettings();
            this.syncRadarControlState();
            this.drawRadar();
        });

        // Main menu, settings, perks, and frontier actions
        document.getElementById("btnMainMenu")?.addEventListener("click", () => this.toggleMainMenu());
        document.getElementById("btnCloseSettings")?.addEventListener("click", () => this.closeSettings());
        document.getElementById("btnMenuResume")?.addEventListener("click", () => {
            this.menuAction("/api/load", "Game loaded.");
        });
        document.getElementById("btnMenuSave")?.addEventListener("click", () => this.menuAction("/api/save", "Game saved."));
        document.getElementById("btnMenuLoad")?.addEventListener("click", () => this.menuAction("/api/load", "Game loaded."));
        document.getElementById("btnMenuDelete")?.addEventListener("click", () => {
            const slot = this.getSelectedSaveSlot();
            if (window.confirm(`Delete save slot '${slot}' permanently?`)) this.menuAction("/api/delete-save", "Save deleted.");
        });
        document.getElementById("btnMenuNew")?.addEventListener("click", () => {
            this.openCharacterCreation();
        });
        document.getElementById("btnMenuSettings")?.addEventListener("click", () => this.openSettings());
        document.getElementById("saveSlotInput")?.addEventListener("input", (e) => {
            this.setSelectedSaveSlot(e.target.value, false);
        });
        document.querySelectorAll("#saveSlotPresets .slot-pill").forEach(btn => {
            btn.addEventListener("click", () => {
                const slot = btn.getAttribute("data-slot") || "default";
                this.setSelectedSaveSlot(slot, true);
            });
        });
        this.btnLandTarget?.addEventListener("click", () => this.handleLandAction());
        this.btnSalvageTarget?.addEventListener("click", () => this.handleSalvage());
        this.btnScoopFuel?.addEventListener("click", () => this.handleScoop());
        document.querySelectorAll("#marketLotBar .market-lot-btn").forEach(button => {
            button.addEventListener("click", () => this.setTradeLot(button.getAttribute("data-lot")));
        });
        this.panelLeft?.addEventListener("pointerdown", () => { this.terminalPointerDown = true; });
        this.hudSkillsGrid?.addEventListener("pointerdown", () => { this.skillsPointerDown = true; });
        window.addEventListener("pointerup", () => { this.terminalPointerDown = false; this.skillsPointerDown = false; });
        window.addEventListener("pointercancel", () => { this.terminalPointerDown = false; this.skillsPointerDown = false; });
        [
            "settingSound", "settingVolume", "settingGrid", "settingLabels", "settingAnimation", "settingStarDensity",
            "settingDensity", "settingUiScale", "settingRememberTab", "settingAutoPause", "settingAutoClaim", "settingTradeLot",
        ].forEach(id => {
            document.getElementById(id)?.addEventListener("input", () => this.applySettingsFromUI());
        });
        document.getElementById("btnResetSettings")?.addEventListener("click", () => this.resetSettings());
        document.querySelectorAll(".settings-nav-item").forEach(link => {
            link.addEventListener("click", () => {
                document.querySelectorAll(".settings-nav-item").forEach(item => item.classList.remove("active"));
                link.classList.add("active");
            });
        });
        this.btnSkipCadet.addEventListener("click", () => this.handleSkipCadet());
        if (this.btnResetCadetAcademy) {
            this.btnResetCadetAcademy.addEventListener("click", () => this.handleResetCadet());
        }

        // Character Creation Functions (defined before use)
        this.setupCharacterCreation = function() {
            this.charCreationOverlay = document.getElementById("characterCreationOverlay");
            this.charPoints2 = 20;
            this.charAttrs = { piloting: 5, engineering: 5, science: 5, combat: 5, diplomacy: 5, trade: 5 };

            document.getElementById("btnCloseCharCreation")?.addEventListener("click", () => this.closeCharacterCreation());
            document.getElementById("btnCharNext1")?.addEventListener("click", () => this.charStep(1, 2));
            document.getElementById("btnCharBack2")?.addEventListener("click", () => this.charStep(2, 1));
            document.getElementById("btnCharCreate")?.addEventListener("click", () => this.createCharacter());
        }.bind(this);

        this.setupCharacterCreation();

        // Combat Buttons

        this.openCharacterCreation = function() {
            this.closeMainMenu();
            const meta = this.state?.character_creation || {};
            const base = Number(meta.skill_base) || 5;
            const points = Number(meta.skill_points) || 20;
            const maxSkill = Number(meta.max_skill) || 10;
            const skillIds = Array.isArray(meta.skills) && meta.skills.length
                ? meta.skills
                : ["piloting", "engineering", "science", "combat", "diplomacy", "trade"];
            this.charPoints2 = points;
            this.charMaxSkill = maxSkill;
            this.charAttrs = Object.fromEntries(skillIds.map(id => [id, base]));
            const budgetLabel = document.getElementById("charSkillBudgetLabel");
            if (budgetLabel) budgetLabel.textContent = `STARTING SKILLS (${points} points, max ${maxSkill})`;
            const nameInput = document.getElementById("charName");
            const ageInput = document.getElementById("charAge");
            const backgroundInput = document.getElementById("charBackground");
            if (nameInput) nameInput.value = "";
            if (ageInput) ageInput.value = "30";
            if (backgroundInput) backgroundInput.value = "Navigator";
            this.charCreationOverlay.style.display = "flex";
            this.charStep(0, 1);
            this.renderAttrGrid();
        }.bind(this);

        this.closeCharacterCreation = function() {
            this.charCreationOverlay.style.display = "none";
            if (!this.gameStarted) this.openMainMenu();
        }.bind(this);

        this.charStep = function(from, to) {
            const fromStep = document.getElementById(`charStep${from}`);
            const toStep = document.getElementById(`charStep${to}`);
            if (fromStep) fromStep.style.display = "none";
            if (toStep) toStep.style.display = "flex";
        }.bind(this);

        this.renderAttrGrid = function() {
            const grid = document.getElementById("attrGrid");
            if (!grid) return;
            const attrLabels = { piloting: "PILOTING", engineering: "ENGINEERING", science: "SCIENCE", combat: "COMBAT", diplomacy: "DIPLOMACY", trade: "TRADE" };
            const maxSkill = this.charMaxSkill || 10;
            grid.innerHTML = Object.entries(this.charAttrs).map(([attr, val]) => `
                <div class="attr-item">
                    <label>${this.escapeHtml(attrLabels[attr] || attr.toUpperCase())}</label>
                    <div class="attr-controls">
                        <button class="attr-btn" id="attrMinus-${attr}" ${val <= 1 ? "disabled" : ""}>−</button>
                        <span class="attr-value" id="attrVal-${attr}">${val}</span>
                        <button class="attr-btn" id="attrPlus-${attr}" ${val >= maxSkill || this.charPoints2 <= 0 ? "disabled" : ""}>+</button>
                    </div>
                </div>
            `).join("");
            document.getElementById("charPointsRemaining2").textContent = this.charPoints2;
        }.bind(this);

        this.adjustAttr = function(attr, delta) {
            const current = this.charAttrs[attr];
            const maxSkill = this.charMaxSkill || 10;
            if (delta > 0) {
                if (current >= maxSkill || this.charPoints2 <= 0) return;
                this.charAttrs[attr]++;
                this.charPoints2--;
            } else {
                if (current <= 1) return;
                this.charAttrs[attr]--;
                this.charPoints2++;
            }
            document.getElementById(`attrVal-${attr}`).textContent = this.charAttrs[attr];
            document.getElementById(`attrMinus-${attr}`).disabled = this.charAttrs[attr] <= 1;
            document.getElementById(`attrPlus-${attr}`).disabled = this.charAttrs[attr] >= maxSkill || this.charPoints2 <= 0;
            document.getElementById("charPointsRemaining2").textContent = this.charPoints2;
        }.bind(this);

        this.createCharacter = async function() {
            const name = document.getElementById("charName").value.trim() || "Commander";
            const age = parseInt(document.getElementById("charAge").value) || 30;
            const background = document.getElementById("charBackground").value;
            const slot = this.getSelectedSaveSlot();
            const wasStarted = this.gameStarted;

            this.gameStarted = true;
            const json = await this.postAction("/api/new-game", {
                profile: { name, age, background, skills: this.charAttrs },
                slot
            }, null);
            if (json.ok) {
                this.viewMode = "ORBITS";
                this.selectedTarget = null;
                this.closeCharacterCreation();
                this.closeMainMenu();
                this.fetchGalaxy();
            } else {
                this.gameStarted = wasStarted;
            }
        }.bind(this);
        this.btnCombatFire.addEventListener("click", () => this.handleCombat("fire_lasers"));
        if (this.btnCombatDrone) {
            this.btnCombatDrone.addEventListener("click", () => this.handleCombat("drone_strike"));
        }
        if (this.btnCombatTarget) {
            this.btnCombatTarget.addEventListener("click", () => this.handleCombat("target_subsystem"));
        }
        this.btnCombatAbsorb.addEventListener("click", () => this.handleCombat("shield_absorb"));
        this.btnCombatEvade.addEventListener("click", () => this.handleCombat("evasive_burn"));
        this.btnCombatFlee.addEventListener("click", () => this.handleCombat("flee"));
        if (this.btnPiratePay) this.btnPiratePay.addEventListener("click", () => this.handlePirateAction("pay"));
        if (this.btnPirateFight) this.btnPirateFight.addEventListener("click", () => this.handlePirateAction("fight"));
        if (this.btnPirateEvade) this.btnPirateEvade.addEventListener("click", () => this.handlePirateAction("evade"));

        // Harvest Fleet
        this.btnHarvestFleet.addEventListener("click", () => this.handleHarvestFleet());

        // Drone Commission buttons
        document.querySelectorAll(".btn-drone-buy").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const target = e.currentTarget;
                const dType = target.getAttribute("data-type");
                this.handleCommissionDrone(dType);
            });
        });

        // Canvas interactions & Drag Pan
        this.canvas.addEventListener("mousedown", (e) => {
            const point = this.pointerToCanvas(e);
            this.isDragging = true;
            this.dragMoved = false;
            this.suppressClick = false;
            this.dragStartX = point.x - this.panX;
            this.dragStartY = point.y - this.panY;
        });

        window.addEventListener("mouseup", () => {
            if (this.dragMoved) this.suppressClick = true;
            this.isDragging = false;
        });

        this.canvas.addEventListener("mousemove", (e) => {
            const point = this.pointerToCanvas(e);
            if (this.isDragging) {
                const nextX = point.x - this.dragStartX;
                const nextY = point.y - this.dragStartY;
                if (Math.hypot(nextX - this.panX, nextY - this.panY) > 3) {
                    this.dragMoved = true;
                }
                this.panX = nextX;
                this.panY = nextY;
            } else {
                this.handleCanvasMouseMove(e);
            }
        });

        this.canvas.addEventListener("wheel", (e) => {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.1 : -0.1;
            this.zoom = Math.max(0.4, Math.min(2.5, this.zoom + delta));
        }, { passive: false });

        this.canvas.addEventListener("click", (e) => this.handleCanvasClick(e));

        // Clear Log
        document.getElementById("clearLogBtn").addEventListener("click", () => {
            this.flightLogStream.innerHTML = `<div class="log-line log-system">[SYS] Telemetry stream cleared.</div>`;
        });

        // Collapse / expand the telemetry log (G-013 top command strip)
        if (this.btnToggleLog) {
            this.btnToggleLog.addEventListener("click", () => this.toggleLogPanel());
        }

        // Collapse / expand the reactor power routing panel (G-013 top command strip)
        if (this.btnToggleReactor) {
            this.btnToggleReactor.addEventListener("click", () => this.toggleReactorPanel());
        }

        if (this.btnOpenSkillsTab) {
            this.btnOpenSkillsTab.addEventListener("click", () => this.switchRightTab("skills"));
        }
        if (this.btnToggleSkills) {
            this.btnToggleSkills.addEventListener("click", () => this.toggleSkillsPanel());
        }

        // Time & Ticks Chrono Controls
        if (this.btnTimePause) {
            this.btnTimePause.addEventListener("click", () => this.handleToggleTimePause());
        }
        if (this.btnTimeStep) {
            this.btnTimeStep.addEventListener("click", () => this.handleTimeStep(1));
        }
        if (this.timeSpeedButtons) {
            this.timeSpeedButtons.forEach(btn => {
                if (btn) {
                    btn.addEventListener("click", (e) => {
                        const speed = parseFloat(e.currentTarget.getAttribute("data-speed") || "1.0");
                        this.handleSetTimeSpeed(speed);
                    });
                }
            });
        }

        // Global hotkeys for menu (ESC) and temporal controls (Space = Pause/Resume, 1-4 = Speeds, T = Step)
        window.addEventListener("keydown", (e) => {
            if (e.repeat) return;
            if (e.key === "Escape") {
                e.preventDefault();
                if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) {
                    document.activeElement.blur();
                }
                const settingsOverlay = document.getElementById("settingsOverlay");
                if (settingsOverlay && settingsOverlay.style.display !== "none") {
                    this.closeSettings();
                    return;
                }
                this.toggleMainMenu();
                return;
            }
            if (this.isTypingTarget(document.activeElement)) return;
            if (e.ctrlKey || e.metaKey || e.altKey) return;
            const menu = document.getElementById("mainMenuOverlay");
            const settings = document.getElementById("settingsOverlay");
            const death = document.getElementById("deathOverlay");
            const creation = document.getElementById("characterCreationOverlay");
            const decision = document.getElementById("decisionOverlay");
            const pirateCard = document.getElementById("pirateCard");
            const overlayOpen = (menu && !menu.classList.contains("hidden"))
                || (settings && settings.style.display !== "none")
                || (death && death.style.display === "flex")
                || (creation && creation.style.display !== "none")
                || (decision && decision.style.display !== "none")
                || (pirateCard && pirateCard.style.display !== "none");
            if (overlayOpen) return;
            const hotkey = String(e.key || "").toLowerCase();
            if (hotkey === "p") {
                e.preventDefault();
                this.toggleReactorPanel();
            } else if (hotkey === "k") {
                e.preventDefault();
                this.toggleSkillsPanel();
            } else if (hotkey === "l") {
                e.preventDefault();
                this.toggleLogPanel();
            } else if (e.shiftKey && /^Digit[1-6]$/.test(e.code)) {
                e.preventDefault();
                this.useAbilityQuick(ABILITY_ORDER[Number(e.code.slice(-1)) - 1]);
            } else if (!e.shiftKey && ["KeyQ", "KeyW", "KeyE", "KeyR"].includes(e.code)) {
                e.preventDefault();
                this.nudgeReactorPower({ KeyQ: "engines", KeyW: "shields", KeyE: "sensors", KeyR: "weapons" }[e.code]);
            } else if (e.code === "Space") {
                if (String((document.activeElement || {}).tagName || "").toUpperCase() === "BUTTON") return;
                e.preventDefault();
                this.handleToggleTimePause();
            } else if (e.key === "1") {
                this.handleSetTimeSpeed(1.0);
            } else if (e.key === "2") {
                this.handleSetTimeSpeed(2.0);
            } else if (e.key === "3") {
                this.handleSetTimeSpeed(5.0);
            } else if (e.key === "4") {
                this.handleSetTimeSpeed(10.0);
            } else if (hotkey === "t") {
                this.handleTimeStep(1);
            } else if (e.code === "BracketLeft" || e.code === "BracketRight") {
                e.preventDefault();
                this.cycleTerminalTab(e.code === "BracketRight" ? 1 : -1);
            } else if (e.code === "Backslash") {
                e.preventDefault();
                this.switchRightTab(this.activeRightTab || this.lastTerminalTab || "player");
            }
        });
    }

    openInitialTerminalTab() {
        const remembered = this.rememberTerminalTab && TERMINAL_TABS.includes(this.lastTerminalTab);
        this.switchRightTab(remembered ? this.lastTerminalTab : "player", { quiet: true });
    }

    cycleTerminalTab(step) {
        const current = this.activeRightTab || this.lastTerminalTab || "player";
        const index = Math.max(0, TERMINAL_TABS.indexOf(current));
        const next = TERMINAL_TABS[(index + step + TERMINAL_TABS.length) % TERMINAL_TABS.length];
        this.switchRightTab(next);
    }

    // A rebuild between pointerdown and pointerup swaps the pressed button and drops the click;
    // a rebuild under a focused select or input closes it. Polls skip the tab until it is idle.
    terminalBusy() {
        if (this.terminalPointerDown || this.skillsPointerDown) return true;
        const active = document.activeElement;
        if (active && this.hudSkillsGrid && this.hudSkillsGrid.contains(active)) return true;
        return Boolean(active && this.panelLeft && this.panelLeft.contains(active) && this.isTypingTarget(active));
    }

    isTypingTarget(element) {
        if (!element) return false;
        const tag = String(element.tagName || "").toUpperCase();
        return element.isContentEditable === true
            || ["INPUT", "TEXTAREA", "SELECT"].includes(tag);
    }

    syncRadarControlState() {
        if (this.btnToggleGrid) {
            this.btnToggleGrid.classList.toggle("active", this.radarGrid);
            this.btnToggleGrid.setAttribute("aria-pressed", String(this.radarGrid));
        }
        if (this.btnToggleLabels) {
            this.btnToggleLabels.classList.toggle("active", this.radarLabels);
            this.btnToggleLabels.setAttribute("aria-pressed", String(this.radarLabels));
        }
        const grid = document.getElementById("settingGrid");
        if (grid) grid.checked = this.radarGrid;
        const labels = document.getElementById("settingLabels");
        if (labels) labels.checked = this.radarLabels;
    }

    applyViewportProfile() {
        const width = window.innerWidth || 1280;
        const height = window.innerHeight || 720;
        const scalePercent = Math.max(85, Math.min(120, Number(this.uiScale || 1) * 100));
        let density = this.uiDensity || "auto";
        if (density === "auto") {
            if (width < 1440) density = "compact";
            else if (width >= 2300) density = "comfortable";
            else density = "standard";
        }
        document.documentElement.dataset.density = density;
        document.documentElement.style.setProperty("--ui-scale", String(scalePercent / 100));
        const readout = document.getElementById("viewportReadout");
        if (readout) {
            readout.textContent = `${width}x${height} @${(window.devicePixelRatio || 1).toFixed(1)}x // ${density.toUpperCase()}`;
        }
        this.resizeRadarCanvas();
    }

    requestRadarResize() {
        if (this.radarResizePending) return;
        this.radarResizePending = true;
        requestAnimationFrame(() => {
            this.radarResizePending = false;
            this.resizeRadarCanvas();
            this.applyViewportProfile();
        });
    }

    switchRightTab(tabName, options = {}) {
        if (!options.quiet) {
            this.drawerUserToggled = true;
            this.sound.playBeep(750, 0.05);
        }
        const tabButtons = {
            market: this.tabBtnMarket, arsenal: this.tabBtnArsenal, ship: this.tabBtnShip, fleet: this.tabBtnFleet,
            contracts: this.tabBtnContracts, story: this.tabBtnStory, factions: this.tabBtnFactions,
            quests: this.tabBtnQuests, ai: this.tabBtnAI, depot: this.tabBtnDepot, messages: this.tabBtnMessages,
            player: this.tabBtnPlayer, skills: this.tabBtnSkills, crew: this.tabBtnCrew, empire: this.tabBtnEmpire, codex: this.tabBtnCodex,
        };

        const tabContents = {
            market: this.tabContentMarket, arsenal: this.tabContentArsenal, ship: this.tabContentShip, fleet: this.tabContentFleet,
            contracts: this.tabContentContracts, story: this.tabContentStory, factions: this.tabContentFactions,
            quests: this.tabContentQuests, ai: this.tabContentAI, depot: this.tabContentDepot, messages: this.tabContentMessages,
            player: this.tabContentPlayer, skills: this.tabContentSkills, crew: this.tabContentCrew, empire: this.tabContentEmpire, codex: this.tabContentCodex,
        };

        // If clicking the already open tab, toggle the drawer closed
        if (this.activeRightTab === tabName && this.panelLeft && !this.panelLeft.classList.contains("drawer-collapsed")) {
            this.activeRightTab = null;
            this.panelLeft.classList.add("drawer-collapsed");
            Object.values(tabButtons).forEach(button => {
                if (button) button.classList.remove("active");
            });
            Object.values(tabContents).forEach(content => {
                if (content) content.style.display = "none";
            });
            return;
        }

        this.activeRightTab = tabName;
        if (this.lastTerminalTab !== tabName) {
            this.lastTerminalTab = tabName;
            if (this.rememberTerminalTab && !options.quiet) this.saveSettings();
        }
        if (this.panelLeft) {
            this.panelLeft.classList.remove("drawer-collapsed");
        }

        Object.entries(tabButtons).forEach(([name, button]) => {
            if (button) button.classList.toggle("active", tabName === name);
        });

        Object.entries(tabContents).forEach(([name, content]) => {
            if (content) content.style.display = (tabName === name) ? "flex" : "none";
        });

        if (tabName === "market") this.renderMarketTable();
        if (tabName === "market") this.loadQuantumFreight();
        if (tabName === "arsenal") this.renderArsenal();
        if (tabName === "ship") this.renderShip();
        if (tabName === "player") this.renderPlayer();
        if (tabName === "skills") this.renderSkills();
        if (tabName === "crew") this.renderCrew();
        if (tabName === "empire") this.renderEmpire();
        if (tabName === "codex") this.renderCodex();
        if (tabName === "fleet") this.renderFleet();
        if (tabName === "contracts") this.renderContracts();
        if (tabName === "story") { this.renderStory(); this.renderVoid(); }
        if (tabName === "factions") this.renderFactions();
        if (tabName === "quests") this.renderQuests();
        if (tabName === "ai") this.renderAICaptains();
        if (tabName === "depot") this.renderDepots();
        if (tabName === "messages") this.renderMessages();
    }

    setPowerSliders(e, sh, se, w) {
        this.sliderEng.value = e;
        this.sliderShd.value = sh;
        this.sliderSen.value = se;
        this.sliderWep.value = w;
        this.powerDirty = true;
        this.updatePowerAllocationDisplay();
    }

    syncPowerSlidersFromState() {
        if (!this.state || this.powerDirty) return;
        const power = this.state.ship.power || { engines: 25, shields: 25, sensors: 25, weapons: 25 };
        this.sliderEng.value = power.engines;
        this.sliderShd.value = power.shields;
        this.sliderSen.value = power.sensors;
        this.sliderWep.value = power.weapons;
        this.updatePowerAllocationDisplay();
    }

    updatePowerAllocationDisplay() {
        const e = parseInt(this.sliderEng.value, 10);
        const sh = parseInt(this.sliderShd.value, 10);
        const se = parseInt(this.sliderSen.value, 10);
        const w = parseInt(this.sliderWep.value, 10);
        const total = e + sh + se + w;

        this.pwrEngVal.textContent = `${e}%`;
        this.pwrShdVal.textContent = `${sh}%`;
        this.pwrSenVal.textContent = `${se}%`;
        this.pwrWepVal.textContent = `${w}%`;

        this.powerTotal.textContent = `${total}% ALLOCATED`;
        if (total > 100) {
            this.powerTotal.style.color = "var(--neon-red)";
            this.applyPowerBtn.disabled = true;
        } else {
            this.powerTotal.style.color = "var(--neon-green)";
            this.applyPowerBtn.disabled = false;
        }
    }

    toggleReactorPanel() {
        if (!this.panelReactor) return;
        const collapsed = this.panelReactor.classList.toggle("reactor-collapsed");
        if (this.btnToggleReactor) {
            this.btnToggleReactor.textContent = collapsed ? "SHOW" : "HIDE";
            this.btnToggleReactor.setAttribute("aria-expanded", String(!collapsed));
        }
    }

    toggleSkillsPanel() {
        if (!this.hudSkillsPanel) return;
        const collapsed = this.hudSkillsPanel.classList.toggle("skills-collapsed");
        if (this.btnToggleSkills) this.btnToggleSkills.setAttribute("aria-expanded", String(!collapsed));
    }

    toggleLogPanel() {
        if (!this.logPanel) return;
        const collapsed = this.logPanel.classList.toggle("log-collapsed");
        if (this.btnToggleLog) {
            this.btnToggleLog.textContent = collapsed ? "SHOW" : "HIDE";
            this.btnToggleLog.setAttribute("aria-expanded", String(!collapsed));
        }
    }

    nudgeReactorPower(channel) {
        const sliders = {
            engines: this.sliderEng,
            shields: this.sliderShd,
            sensors: this.sliderSen,
            weapons: this.sliderWep,
        };
        const target = sliders[channel];
        if (!target) return;
        const current = parseInt(target.value, 10) || 0;
        let bump = Math.min(5, 100 - current);
        if (bump <= 0) return;
        target.value = current + bump;
        const donors = Object.entries(sliders)
            .filter(([key]) => key !== channel)
            .sort((a, b) => parseInt(b[1].value, 10) - parseInt(a[1].value, 10));
        for (const [, donor] of donors) {
            if (bump <= 0) break;
            const value = parseInt(donor.value, 10) || 0;
            const take = Math.min(value, bump);
            donor.value = value - take;
            bump -= take;
        }
        this.powerDirty = true;
        this.updatePowerAllocationDisplay();
        this.sound.init();
        this.sound.playBeep(720, 0.04);
    }

    pollInterval() {
        const time = this.state && this.state.time;
        if (!time || time.is_paused) return 1000;
        const speed = Number(time.speed) || 1;
        // 1x runs 2 ticks/s; poll at least that often, and 4 Hz from 5x up.
        return speed >= 5 ? 250 : speed >= 2 ? 333 : 500;
    }

    schedulePoll() {
        clearTimeout(this.pollTimer);
        this.pollTimer = setTimeout(async () => {
            if (!document.hidden && this.gameStarted && this.state) await this.refreshState(true);
            this.schedulePoll();
        }, this.pollInterval());
    }

    async refreshState(silent = false) {
        if (this.refreshInFlight || document.hidden || !this.gameStarted) return;
        this.refreshInFlight = true;
        try {
            const res = await apiFetch("/api/state");
            const json = await res.json();
            if (json.ok && json.data) {
                this.state = json.data;
                this.renderHUD();
                if (!silent) {
                    this.appendLog(`Telemetry synchronized with ${this.state.current_system.name}.`);
                }
            }
        } catch (e) {
            console.error("Error refreshing state:", e);
        } finally {
            this.refreshInFlight = false;
        }
    }

    async fetchGalaxy() {
        try {
            const res = await apiFetch("/api/galaxy");
            const json = await res.json();
            if (json.ok && json.systems) {
                this.galaxySystems = json.systems;
            }
        } catch (e) {
            console.error("Error fetching galaxy:", e);
        }
    }

    renderHUD() {
        if (!this.state) return;
        
        // Safety: if state somehow loaded but game not started, show menu
        if (!this.gameStarted) {
            this.openMainMenu();
            return;
        }
        
        // Check for death
        this.checkDeath();
        this.runAlertAutomation();

        const ship = this.state.ship;
        const curSys = this.state.current_system;
        const orbBody = this.state.orbiting_body;

        // Vitals
        const hullPct = Math.round((ship.hull / ship.max_hull) * 100);
        this.hullBar.style.width = `${hullPct}%`;
        this.hullVal.textContent = `${ship.hull}/${ship.max_hull}`;

        const shieldPct = Math.round((ship.shield / ship.max_shield) * 100);
        this.shieldBar.style.width = `${shieldPct}%`;
        this.shieldVal.textContent = `${ship.shield}/${ship.max_shield}`;

        const fuelPct = Math.round((ship.fuel / ship.max_fuel) * 100);
        this.fuelBar.style.width = `${fuelPct}%`;
        this.fuelVal.textContent = `${ship.fuel}/${ship.max_fuel}`;

        this.creditsVal.textContent = `${ship.credits.toLocaleString()} CR`;

        const manifest = this.state.inventory_manifest || [];
        const totalCargo = manifest.length
            ? manifest.reduce((sum, item) => sum + (item.total_volume || 0), 0)
            : Object.values(ship.cargo).reduce((a, b) => a + b, 0);
        const flow = this.state.cash_flow;
        const monthly = flow ? ` · ${flow.net_per_month >= 0 ? "+" : ""}${Math.round(flow.net_per_month)}/MO` : "";
        this.cargoSummary.textContent = `HOLD: ${totalCargo}/${ship.cargo_capacity}${monthly}`;
        this.cargoSummary.title = flow
            ? `Monthly treasury: payroll -${flow.upkeep_per_month} cr, passive +${flow.passive_per_month} cr`
            : "";
        this.cargoDetailed.textContent = `${totalCargo} / ${ship.cargo_capacity} VOLUME`;
        this.cargoMeterFill.style.width = `${Math.min(100, Math.round((totalCargo / ship.cargo_capacity) * 100))}%`;

        this.syncPowerSlidersFromState();

        // Reactor thermal telemetry
        const reactor = this.state.reactor || {};
        const heatPct = Math.max(0, Math.min(100, Number(reactor.heat_pct || 0)));
        if (this.reactorHeatFill) {
            this.reactorHeatFill.style.width = `${heatPct}%`;
            this.reactorHeatFill.parentElement.parentElement.classList.toggle("reactor-critical", heatPct >= 85);
        }
        if (this.reactorHeatLabel) this.reactorHeatLabel.textContent = `${Math.round(reactor.heat || 0)} / ${Math.round(reactor.max_heat || 100)}`;
        if (this.reactorOutputLabel) this.reactorOutputLabel.textContent = `${Math.round((reactor.efficiency || 1) * 100)}%`;
        if (this.reactorCoolingLabel) this.reactorCoolingLabel.textContent = `${Number(reactor.cooling || 6).toFixed(1)}`;
        if (this.reactorIntegrityLabel) this.reactorIntegrityLabel.textContent = `${Math.round(reactor.integrity || 100)}%`;
        if (this.reactorModeRow) {
            this.reactorModeRow.querySelectorAll(".reactor-mode-btn").forEach(btn => {
                btn.classList.toggle("active", btn.getAttribute("data-mode") === (reactor.mode || "balanced"));
            });
        }
        if (this.btnVentReactor) {
            this.btnVentReactor.disabled = !(reactor.heat > 5);
        }

        // Sector map modifiers
        if (this.sectorModsStrip) {
            const mods = this.state.map_modifiers || [];
            if (!mods.length) {
                this.sectorModsStrip.innerHTML = `<span class="sector-mod-chip">STANDARD SPACE</span>`;
            } else {
                this.sectorModsStrip.innerHTML = mods.map(m =>
                    `<span class="sector-mod-chip ${this.escapeHtml(m.category || "")}" title="${this.escapeHtml(m.description || "")}">${this.escapeHtml(m.name)}</span>`
                ).join("");
            }
        }

        // Streak render
        const streak = ship.streak || 1;
        const streakMult = 1.0 + Math.min(1.5, (streak - 1) * 0.15);
        // The equal-width card shows the count; the payout multiplier leads the subline.
        this.streakVal.textContent = `🔥 ${streak}`;
        this.streakVal.title = `${streak} jump${streak > 1 ? "s" : ""} streak, x${streakMult.toFixed(2)} payouts`;
        this.vitalStreakCard.classList.toggle("high-streak", streak >= 3);
        this.streakSubtext.textContent = streak > 1
            ? `x${streakMult.toFixed(2)} REWARDS // FLEE RESETS`
            : "x1.00 // FLEE RESETS";

        // Mastery render
        const mastery = ship.mastery || { level: 1, xp: 0, next_level_xp: 500, talent_points: 0 };
        this.masteryLevelVal.textContent = `★ LVL ${mastery.level}`;
        const xpPct = Math.min(100, Math.round((mastery.xp / mastery.next_level_xp) * 100));
        this.masteryBar.style.width = `${xpPct}%`;
        this.masterySubtext.textContent = `${mastery.xp}/${mastery.next_level_xp} XP // ${mastery.talent_points} PERK${mastery.talent_points !== 1 ? 'S' : ''}`;

        // Contract ready notification badge
        const contracts = ship.active_contracts || [];
        const readyContracts = contracts.filter(c => c.completed);
        if (readyContracts.length > 0) {
            this.contractsBadge.style.display = "inline-block";
            this.contractsBadge.textContent = readyContracts.length;
        } else {
            this.contractsBadge.style.display = "none";
        }

        // Captain's log ready notification badge
        const codex = this.state.codex;
        if (codex && this.codexBadge) {
            const readyCount = codex.totals ? codex.totals.ready : 0;
            if (readyCount > 0) {
                this.codexBadge.style.display = "inline-block";
                this.codexBadge.textContent = readyCount;
            } else {
                this.codexBadge.style.display = "none";
            }
        }

        // Render Cosmic Chronometer & Time Controls
        if (this.state.time) {
            const t = this.state.time;
            if (this.chronoStardate) {
                this.chronoStardate.textContent = `DATE ${t.date || "01.01.3042"}`;
            }
            if (this.chronoTick) {
                this.chronoTick.textContent = `TICK #${t.tick}`;
            }
            if (this.btnTimePause && this.timeStatusBadge) {
                if (t.is_paused) {
                    this.btnTimePause.textContent = "▶";
                    this.btnTimePause.classList.add("paused");
                    this.btnTimePause.title = "Resume Chrono Stream (Hotkey: Space)";
                    this.timeStatusBadge.textContent = "PAUSED";
                    this.timeStatusBadge.className = "time-status-badge badge-paused";
                } else {
                    this.btnTimePause.textContent = "⏸";
                    this.btnTimePause.classList.remove("paused");
                    this.btnTimePause.title = "Pause Chrono Stream (Hotkey: Space)";
                    this.timeStatusBadge.textContent = `${t.speed}x SPEED`;
                    this.timeStatusBadge.className = "time-status-badge badge-active";
                }
            }
            if (this.timeSpeedButtons) {
                this.timeSpeedButtons.forEach(btn => {
                    if (btn) {
                        const s = parseFloat(btn.getAttribute("data-speed") || "1.0");
                        btn.classList.toggle("active", Math.abs(s - t.speed) < 0.01 && !t.is_paused);
                    }
                });
            }
        }

        // Nav titles
        this.radarTitle.textContent = this.viewMode === "ORBITS" 
            ? `${curSys.name.toUpperCase()} CELESTIAL ORBITS`
            : `SECTOR HYPERLANE GRID`;
        this.radarCoords.textContent = `COORDS: [${curSys.x.toFixed(1)}, ${curSys.y.toFixed(1)}] // ${curSys.faction.toUpperCase()}`;

        // Footer stats
        this.statJumps.textContent = this.state.stats.jumps || 0;
        this.statScans.textContent = this.state.stats.scans || 0;
        this.statTrades.textContent = this.state.stats.trades || 0;
        this.statVictories.textContent = this.state.stats.combat_victories || 0;
        this.statAnomalies.textContent = this.state.stats.anomalies_resolved || 0;
        if (this.statPirates) this.statPirates.textContent = this.state.stats.pirate_encounters || 0;
        if (this.statDecisions) this.statDecisions.textContent = this.state.stats.decisions_resolved || 0;
        if (this.statLandings) this.statLandings.textContent = this.state.stats.landings || 0;

        // Render Combat Intercept Alert
        if (this.state.active_combat) {
            const c = this.state.active_combat;
            this.sound.playAlarm();
            this.combatCard.style.display = "flex";
            this.combatEnemyTitle.textContent = `${c.enemy_name} [${c.enemy_class}]`;
            if (this.combatEnemyFaction) {
                this.combatEnemyFaction.textContent = c.faction_id ? `FACTION: ${c.faction_id.replace('_', ' ').toUpperCase()}` : "";
            }
            this.combatEnemyHp.textContent = `${c.enemy_hull} / ${c.enemy_max_hull}`;
            const pct = Math.round((c.enemy_hull / c.enemy_max_hull) * 100);
            this.combatEnemyBar.style.width = `${pct}%`;

            if (this.combatShieldContainer) {
                if (c.enemy_max_shield > 0) {
                    this.combatShieldContainer.style.display = "flex";
                    this.combatEnemyShield.textContent = `${c.enemy_shield} / ${c.enemy_max_shield}`;
                    const shdPct = Math.round((c.enemy_shield / c.enemy_max_shield) * 100);
                    this.combatEnemyShieldBar.style.width = `${shdPct}%`;
                } else {
                    this.combatShieldContainer.style.display = "none";
                }
            }

            if (this.combatTelegraphBanner) {
                if (c.telegraphed_action) {
                    this.combatTelegraphBanner.style.display = "flex";
                    this.combatTelegraphText.textContent = c.telegraphed_action;
                } else {
                    this.combatTelegraphBanner.style.display = "none";
                }
            }

            // Tactical Combo Counter
            const combo = ship.tactical_combo || 0;
            if (combo > 0) {
                this.combatComboBadge.style.display = "flex";
                this.combatComboCount.textContent = `x${combo}`;
                this.critReadyText.style.display = (combo >= 2) ? "inline" : "none";
            } else {
                this.combatComboBadge.style.display = "none";
            }
        } else {
            this.combatCard.style.display = "none";
        }

        // Render Anomaly Alert
        if (this.state.active_anomaly && !this.state.active_combat) {
            this.sound.playAlarm();
            this.anomalyCard.style.display = "flex";
            this.anomalyTitle.textContent = this.state.active_anomaly.title;
            this.anomalyDesc.textContent = this.state.active_anomaly.description;
            this.anomalyChoices.innerHTML = "";
            this.state.active_anomaly.choices.forEach(ch => {
                const btn = document.createElement("button");
                btn.className = "anomaly-choice-btn";
                const checkInfo = ch.required_power !== "none" 
                    ? `[CHECK: ${ch.required_power.toUpperCase()} >= ${ch.min_power_threshold}%]`
                    : `[SAFE HARVEST]`;
                btn.innerHTML = `${this.escapeHtml(ch.text)} <span class="choice-check">${checkInfo}</span>`;
                btn.addEventListener("click", () => this.handleResolveAnomaly(ch.choice_id));
                this.anomalyChoices.appendChild(btn);
            });
        } else {
            this.anomalyCard.style.display = "none";
        }

        if (this.state.active_pirate && !this.state.active_combat) {
            const pirate = this.state.active_pirate;
            this.sound.playAlarm();
            this.pirateCard.style.display = "flex";
            this.pirateTitle.textContent = `${pirate.band_name} // ${pirate.ship_class}`;
            this.pirateDesc.textContent = pirate.description;
            this.pirateTollLine.textContent = `DEMAND: ${pirate.toll_credits} CREDITS // THREAT ${pirate.threat} // ${pirate.system_name}`;
            this.btnPiratePay.textContent = `PAY ${pirate.toll_credits} CR`;
            this.btnPiratePay.disabled = (ship.credits || 0) < pirate.toll_credits;
            this.btnPirateEvade.textContent = `EVADE (-${6 + pirate.threat} FUEL)`;
        } else {
            this.pirateCard.style.display = "none";
        }

        const pendingDecision = this.state.pending_decision;
        if (pendingDecision && this.decisionOverlay) {
            this.decisionOverlay.style.display = "flex";
            this.decisionSeverity.textContent = `DECISION REQUIRED // ${String(pendingDecision.severity || "major").toUpperCase()}`;
            this.decisionTitle.textContent = pendingDecision.title;
            this.decisionDesc.textContent = pendingDecision.description;
            this.decisionChoices.innerHTML = "";
            (pendingDecision.choices || []).forEach(choice => {
                const button = document.createElement("button");
                button.type = "button";
                button.className = "decision-choice-btn";
                const desc = choice.description ? `<small>${this.escapeHtml(choice.description)}</small>` : "";
                button.innerHTML = `<strong>${this.escapeHtml(choice.label)}</strong>${desc}`;
                button.addEventListener("click", () => this.handleDecisionChoice(choice.id));
                this.decisionChoices.appendChild(button);
            });
        } else if (this.decisionOverlay) {
            this.decisionOverlay.style.display = "none";
        }

        // Cadet Academy Ribbon render
        const tut = ship.tutorial;
        if (tut && !tut.completed && !tut.skipped && tut.steps && tut.steps.length > 0) {
            const step = tut.steps[tut.current_step_index] || tut.steps[0];
            this.cadetBanner.style.display = "flex";
            this.cadetMilestoneTitle.textContent = `Milestone ${tut.current_step_index + 1}/${tut.steps.length}: ${step.title}`;
            this.cadetMilestoneDesc.textContent = step.description;
            this.cadetMilestoneHint.textContent = step.hint;
            this.cadetMilestoneReward.textContent = `+${step.reward_credits} CR / +${step.reward_xp} XP`;
            this.btnSkipCadet.textContent = "SKIP TUTORIAL";
            this.btnSkipCadet.style.display = "inline-block";
        } else if (tut && tut.completed && !this.cadetGraduationDismissed) {
            this.cadetBanner.style.display = "flex";
            this.cadetMilestoneTitle.textContent = "🎓 ACADEMY GRADUATION: Flight Wings Conferred!";
            this.cadetMilestoneDesc.textContent = "Congratulations Commander Astraea! Full flight credentials unlocked. Cadet Honor Wings active.";
            this.cadetMilestoneHint.textContent = "+1,500 CR, +400 XP, and Cadet Honor Wings Precursor Relic awarded.";
            this.cadetMilestoneReward.textContent = "GRADUATED";
            this.btnSkipCadet.textContent = "DISMISS";
            this.btnSkipCadet.style.display = "inline-block";
        } else {
            this.cadetBanner.style.display = "none";
        }

        // Story Comms Badge
        const story = ship.story;
        if (story) {
            let curChap = null;
            if (this.state.story_chapters_map && this.state.story_chapters_map[story.current_chapter_id]) {
                curChap = this.state.story_chapters_map[story.current_chapter_id];
            } else if (Array.isArray(this.state.story_chapters)) {
                curChap = this.state.story_chapters.find(c => c.id === story.current_chapter_id);
            } else if (story.chapters && story.chapters[story.current_chapter_index]) {
                curChap = story.chapters[story.current_chapter_index];
            }
            const hasPendingChoices = curChap && !curChap.completed && curChap.choices && curChap.choices.length > 0;
            if (hasPendingChoices) {
                this.storyBadge.style.display = "inline-block";
                this.storyBadge.textContent = "!";
            } else {
                this.storyBadge.style.display = "none";
            }
        }

        if (this.messagesBadge) {
            const unread = (this.state.messages || []).filter(m => !m.read).length;
            this.messagesBadge.textContent = String(unread);
            this.messagesBadge.style.display = unread > 0 ? "inline-block" : "none";
        }

        // Render Active Tab Content
        if (this.terminalBusy()) {
            // Leave the open tab as it is; the next poll renders it.
        } else if (this.activeRightTab === "market") {
            if (orbBody && orbBody.station_dockable) {
                this.noMarketMsg.style.display = "none";
                this.marketTitle.textContent = `${orbBody.name.toUpperCase()} EXCHANGE`;
                this.marketArch.textContent = orbBody.market_archetype.toUpperCase();
                this.renderMarketTable();
                if (this.quantumBodyId !== orbBody.id) {
                    this.quantumBodyId = orbBody.id;
                    this.loadQuantumFreight();
                } else {
                    this.renderQuantumFreight();
                }
            } else {
                this.noMarketMsg.style.display = "flex";
                this.marketTableBody.innerHTML = "";
                this.marketTitle.textContent = orbBody ? orbBody.name : "DEEP SPACE";
                this.marketArch.textContent = "UNPOPULATED";
                if (this.quantumFreight) this.quantumFreight.style.display = "none";
            }
        } else if (this.activeRightTab === "arsenal") {
            this.renderArsenal();
        } else if (this.activeRightTab === "ship") {
            this.renderShip();
        } else if (this.activeRightTab === "player") {
            this.renderPlayer();
        } else if (this.activeRightTab === "skills") {
            this.renderSkills();
        } else if (this.activeRightTab === "crew") {
            this.renderCrew();
        } else if (this.activeRightTab === "codex") {
            this.renderCodex();
        } else if (this.activeRightTab === "empire") {
            this.renderEmpire();
        } else if (this.activeRightTab === "fleet") {
            this.renderFleet();
        } else if (this.activeRightTab === "contracts") {
            this.renderContracts();
        } else if (this.activeRightTab === "story") {
            this.renderStory();
        } else if (this.activeRightTab === "factions") {
            this.renderFactions();
        } else if (this.activeRightTab === "quests") {
            this.renderQuests();
        } else if (this.activeRightTab === "ai") {
            this.renderAICaptains();
        } else if (this.activeRightTab === "depot") {
            this.renderDepots();
        } else if (this.activeRightTab === "messages") {
            this.renderMessages();
        }

        this.renderSkillsQuickPanel();
        this.renderEventPopups();
        this.updateTargetCard();
        this.renderSurfaceOps();

        // Void transit state: radar overlay + live panel refresh
        document.body.classList.toggle("void-transit", !!(ship && ship.void_traversal));
        this.renderVoid();
    }

    checkDeath() {
        if (!this.state || !this.state.ship || !this.deathOverlay) return;
        const ship = this.state.ship;
        if (this.deathAcknowledged || ship.hull > 0 || this.deathOverlay.style.display === "flex") return;
        this.showDeathOverlay();
        if (this.state.time && !this.state.time.is_paused) {
            apiFetch("/api/time/pause", { method: "POST" }).catch(() => {});
        }
    }

    showDeathOverlay() {
        if (!this.deathOverlay) return;
        
        const ship = this.state.ship;
        const ch = this.state.character || {};
        const stats = this.state.stats || {};
        
        const deathMessages = [
            "Your hull shattered against the unforgiving void.",
            "The darkness claims another wanderer.",
            "Silence falls across the comms. You are lost.",
            "A flash of light, then nothing. The end.",
            "Your atoms scatter across the solar wind.",
            "The galaxy forgets you in a heartbeat."
        ];
        
        const deathTitles = [
            "COMMANDER LOST IN THE VOID",
            "HULL BREACH - ALL HANDS LOST",
            "SIGNAL TERMINATED",
            "VOIDFARER DESTROYED",
            "LAST TRANSMISSION RECEIVED",
            "EXPEDITION ENDED"
        ];
        
        this.deathAcknowledged = true;
        const msg = deathMessages[Math.floor(Math.random() * deathMessages.length)];
        const title = deathTitles[Math.floor(Math.random() * deathTitles.length)];
        
        this.deathTitle.textContent = title;
        this.deathMessage.textContent = msg;
        
        this.deathStats.innerHTML = `
            <div class="death-stat">
                <span class="death-stat-label">Sectors Explored</span>
                <span class="death-stat-value">${stats.jumps || 0}</span>
            </div>
            <div class="death-stat">
                <span class="death-stat-label">Credits Earned</span>
                <span class="death-stat-value">${(stats.credits_earned || 0).toLocaleString()}</span>
            </div>
            <div class="death-stat">
                <span class="death-stat-label">Enemies Destroyed</span>
                <span class="death-stat-value">${stats.combat_victories || 0}</span>
            </div>
            <div class="death-stat">
                <span class="death-stat-label">Anomalies Resolved</span>
                <span class="death-stat-value">${stats.anomalies_resolved || 0}</span>
            </div>
            <div class="death-stat">
                <span class="death-stat-label">Systems Visited</span>
                <span class="death-stat-value">${stats.systems_visited || 0}</span>
            </div>
            <div class="death-stat">
                <span class="death-stat-label">Expedition Duration</span>
                <span class="death-stat-value">${this.formatPlaytime(this.state.time?.tick || 0)}</span>
            </div>
        `;
        
        this.deathOverlay.style.display = "flex";
        this.sound.playAlarm();
        
        // Death overlay buttons
        this.btnDeathNewGame.onclick = () => {
            this.hideDeathOverlay();
            this.gameStarted = false;
            this.openCharacterCreation();
        };
        this.btnDeathLoadSave.onclick = () => {
            this.hideDeathOverlay();
            this.openMainMenu();
        };
        this.btnDeathMainMenu.onclick = () => {
            this.hideDeathOverlay();
            this.openMainMenu();
        };
    }

    hideDeathOverlay() {
        if (this.deathOverlay) {
            this.deathOverlay.style.display = "none";
        }
    }

    formatPlaytime(ticks) {
        if (!ticks) return "00:00";
        const hours = Math.floor(ticks / 3600);
        const minutes = Math.floor((ticks % 3600) / 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }

    renderStory() {
        if (!this.state || !this.state.ship || !this.state.ship.story) return;
        const story = this.state.ship.story;
        const status = this.state.story_status || null;

        // Resolve active chapter reliably across map, array, or embedded state
        let curChap = null;
        if (this.state.story_chapters_map && this.state.story_chapters_map[story.current_chapter_id]) {
            curChap = this.state.story_chapters_map[story.current_chapter_id];
        } else if (Array.isArray(this.state.story_chapters)) {
            curChap = this.state.story_chapters.find(c => c.id === story.current_chapter_id);
        } else if (story.chapters && story.chapters[story.current_chapter_index]) {
            curChap = story.chapters[story.current_chapter_index];
        }

        if (story.completed) {
            const ending = (status && status.ending) || null;
            this.storyChapterTitle.textContent = ending
                ? `CAMPAIGN CONCLUDED: ${ending.title.toUpperCase()}`
                : "CAMPAIGN CONCLUDED: THE PRECURSOR CIPHER";
            this.storyTargetBadge.textContent = "⭐ ALL ACTS RESOLVED";
            this.storySynopsisText.textContent = ending
                ? ending.epilogue
                : "The mysteries of the ancient Precursor network have been unveiled. Your legacy echoes across the hyperlane corridors as First VoidFarer of the New Age.";
            this.storyChoiceContainer.style.display = "none";
        } else if (curChap) {
            this.storyChapterTitle.textContent = `ACT ${story.active_act}: ${curChap.title.toUpperCase()}`;
            const targetText = curChap.completed
                ? "ACT OBJECTIVE COMPLETE"
                : (curChap.target_system_id ? `TARGET: ${curChap.target_system_id.toUpperCase()}` : "TARGET: DEEP SPACE");
            this.storyTargetBadge.textContent = targetText;
            this.storySynopsisText.textContent = curChap.synopsis || curChap.objective || "";

            // Story Choices (locked choices render with their reasons)
            const choiceStatus = {};
            if (status && Array.isArray(status.choices)) {
                status.choices.forEach(c => { choiceStatus[c.id] = c; });
            }
            if (!curChap.completed && curChap.choices && curChap.choices.length > 0) {
                this.storyChoiceContainer.style.display = "flex";
                this.storyChoicesList.innerHTML = "";
                curChap.choices.forEach(c => {
                    const st = choiceStatus[c.id] || {};
                    const locked = !!st.locked;
                    const card = document.createElement("button");
                    card.className = locked ? "story-choice-card story-choice-locked" : "story-choice-card";
                    if (locked) card.disabled = true;
                    const costBadge = c.cost_credits > 0 ? `<span class="choice-cost-badge">COST: ${c.cost_credits} CR</span>` : "";
                    const lockBadge = locked ? `<span class="choice-lock-badge">🔒 LOCKED</span>` : "";
                    const consequence = locked
                        ? `<span class="choice-lock-reason">${this.escapeHtml(st.lock_reason || "Requirements unmet.")}</span>`
                        : this.escapeHtml(c.consequence_summary || c.outcome_text);
                    card.innerHTML = `
                        <div class="choice-header-row">
                            <span class="choice-label-text">${this.escapeHtml(c.label || c.text)}</span>
                            ${costBadge}${lockBadge}
                        </div>
                        <p class="choice-consequence-preview">${consequence}</p>
                    `;
                    if (!locked) card.addEventListener("click", () => this.handleStoryChoice(c.id));
                    this.storyChoicesList.appendChild(card);
                });
            } else {
                this.storyChoiceContainer.style.display = "none";
            }
        }

        // Campaign objective checklist
        const unmet = (status && status.unmet_requirements) || [];
        if (!story.completed && unmet.length > 0) {
            this.storyObjectivesBox.style.display = "block";
            this.storyObjectivesList.innerHTML = "";
            unmet.forEach(req => {
                const li = document.createElement("li");
                li.textContent = req;
                this.storyObjectivesList.appendChild(li);
            });
        } else {
            this.storyObjectivesBox.style.display = "none";
        }

        // Faction alignment meters
        const rep = story.faction_reputation || story.reputation || { coalition: 0, syndicate: 0, precursor: 0 };
        this.scoreCoalition.textContent = (rep.coalition >= 0 ? "+" : "") + (rep.coalition || 0);
        this.scoreSyndicate.textContent = (rep.syndicate >= 0 ? "+" : "") + (rep.syndicate || 0);
        this.scorePrecursor.textContent = (rep.precursor >= 0 ? "+" : "") + (rep.precursor || 0);

        // Subspace Transmissions Feed
        const logs = story.transmission_log || [];
        this.commsLogCount.textContent = `${logs.length} TRANSMISSION${logs.length !== 1 ? 'S' : ''}`;
        const stream = this.transmissionsStream;
        const previousCount = this.storyTransmissionCount || 0;
        const wasAtBottom = stream.scrollHeight - stream.scrollTop - stream.clientHeight < 40;
        stream.innerHTML = "";

        logs.forEach(tx => {
            const item = document.createElement("div");
            item.className = "transmission-item";

            let avatarClass = "avatar-generic";
            let initials = "TX";
            const spk = tx.speaker || "";
            if (spk.includes("Vance")) {
                avatarClass = "avatar-vance";
                initials = "AV";
            } else if (spk.includes("Cipher")) {
                avatarClass = "avatar-cipher";
                initials = "CP";
            } else if (spk.includes("Archon")) {
                avatarClass = "avatar-archon";
                initials = "AP";
            } else if (spk.includes("Echo")) {
                avatarClass = "avatar-archon";
                initials = "EF";
            }

            item.innerHTML = `
                <div class="speaker-avatar ${avatarClass}">${initials}</div>
                <div class="transmission-body">
                    <div class="transmission-header-row">
                        <span class="speaker-title">${this.escapeHtml(tx.speaker)}</span>
                        <span class="callsign-pill">${this.escapeHtml((tx.callsign || 'SECURE').toUpperCase())}</span>
                    </div>
                    <div class="transmission-bubble">"${this.escapeHtml(tx.message)}"</div>
                </div>
            `;
            stream.appendChild(item);
        });
        if (logs.length > previousCount || wasAtBottom) {
            stream.scrollTop = stream.scrollHeight;
        }
        this.storyTransmissionCount = logs.length;
    }

    renderVoid() {
        if (!this.voidTraversePanel || !this.state) return;
        const voidState = this.state.void;
        if (!voidState) return;

        const traversal = voidState.traversal;
        if (traversal) {
            this.voidStatusBadge.textContent = "IN THE HOLLOW BETWEEN";
            this.voidStatusBadge.classList.add("void-badge-active");
            const destName = voidState.destination_name || traversal.destination_system_id;
            const progressPct = Math.round((voidState.traversal_progress || 0) * 100);
            const stability = Math.max(0, Math.round(traversal.stability));
            this.voidBody.innerHTML = `
                <div class="void-transit-row">
                    <span class="void-label">DESTINATION</span>
                    <span class="void-value">${this.escapeHtml(destName)}</span>
                </div>
                <div class="void-transit-row">
                    <span class="void-label">TRAVERSAL</span>
                    <div class="void-meter"><div class="void-meter-fill void-fill-progress" style="width:${progressPct}%"></div></div>
                    <span class="void-value">${progressPct}%</span>
                </div>
                <div class="void-transit-row">
                    <span class="void-label">STABILITY</span>
                    <div class="void-meter"><div class="void-meter-fill ${stability > 60 ? 'void-fill-stable' : 'void-fill-critical'}" style="width:${Math.min(100, stability)}%"></div></div>
                    <span class="void-value">${stability}%</span>
                </div>
                <div class="void-transit-row">
                    <span class="void-label">STORMS</span>
                    <span class="void-value">${traversal.storms_weathered} weathered</span>
                </div>
                <div class="void-transit-row">
                    <span class="void-label">RESONANCE</span>
                    <span class="void-value">${Math.round(traversal.resonance || 0)} storms · ~${voidState.projected_resonance_credits || 0} cr</span>
                </div>
                <button class="btn-hud void-emerge-btn" id="btnVoidEmerge">⚠ EMERGENCY EMERGE</button>
            `;
            const emergeBtn = document.getElementById("btnVoidEmerge");
            if (emergeBtn) emergeBtn.addEventListener("click", () => this.handleVoidEmerge());
        } else if (voidState.dive_ready) {
            this.voidStatusBadge.textContent = "READY TO DIVE";
            this.voidStatusBadge.classList.remove("void-badge-active");
            const destinations = voidState.destinations || [];
            const stormPct = Math.round((voidState.storm_chance || 0) * 100);
            let html = `<div class="void-transit-row"><span class="void-label">STORM RISK</span><span class="void-value">${stormPct}% per tick</span></div>`;
            if (destinations.length > 0) {
                html += `<div class="void-destinations">`;
                destinations.forEach(dest => {
                    html += `
                        <button class="btn-hud void-dive-btn" data-system="${this.escapeHtml(dest.system_id)}">
                            DIVE ▸ ${this.escapeHtml(dest.name)} <span class="void-fuel-note">(~${dest.fuel_estimate} FUEL)</span>
                        </button>
                    `;
                });
                html += `</div>`;
            } else {
                html += `<div class="void-hint">No void lanes lead onward from this horizon.</div>`;
            }
            this.voidBody.innerHTML = html;
            this.voidBody.querySelectorAll(".void-dive-btn").forEach(btn => {
                btn.addEventListener("click", () => this.handleVoidDive(btn.dataset.system));
            });
        } else {
            this.voidStatusBadge.textContent = "VOID DRIVE OFFLINE";
            this.voidStatusBadge.classList.remove("void-badge-active");
            const blockers = voidState.blockers || [];
            let html = "";
            blockers.forEach(b => { html += `<div class="void-hint">• ${this.escapeHtml(b)}</div>`; });
            if (!blockers.length) html = `<div class="void-hint">Telemetry unavailable.</div>`;
            this.voidBody.innerHTML = html;
        }
    }

    async handleVoidDive(systemId) {
        if (!systemId) return;
        this.sound.init();
        try {
            const res = await apiFetch("/api/void/dive", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target_system_id: systemId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(`[VOID] ${json.message}`, "reward");
                this.state = json.state;
                this.renderHUD();
                this.renderStory();
                this.renderVoid();
            } else {
                this.appendLog(`[VOID] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Void dive failed: ${e.message}`, "hazard");
        }
    }

    async handleVoidEmerge() {
        this.sound.init();
        try {
            const res = await apiFetch("/api/void/emerge", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({})
            });
            const json = await res.json();
            if (json.ok) {
                this.appendLog(`[VOID] ${json.message}`, "hazard");
                this.state = json.state;
                this.renderHUD();
                this.renderStory();
                this.renderVoid();
            } else {
                this.appendLog(`[VOID] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Void emergence failed: ${e.message}`, "hazard");
        }
    }

    async handleStoryChoice(choiceId) {
        this.sound.init();
        this.sound.playTransmission();
        try {
            const res = await apiFetch("/api/story/choice", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ choice_id: choiceId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(`[STORY] ${json.message}`, "reward");
                this.state = json.state;
                this.renderHUD();
                this.renderStory();
            } else {
                this.appendLog(`[STORY ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Transmission choice failed: ${e.message}`, "hazard");
        }
    }

    async handleSkipCadet() {
        this.sound.init();
        this.sound.playBeep(700);
        if (this.state && this.state.ship && this.state.ship.tutorial && this.state.ship.tutorial.completed) {
            this.cadetGraduationDismissed = true;
            this.cadetBanner.style.display = "none";
            return;
        }
        try {
            const res = await apiFetch("/api/tutorial/skip", { method: "POST" });
            const json = await res.json();
            if (json.ok) {
                this.appendLog(json.message, "system");
                this.state = json.state;
                this.renderHUD();
            }
        } catch (e) {
            console.error("Error skipping tutorial:", e);
        }
    }

    async handleResetCadet() {
        this.sound.init();
        this.sound.playBeep(850);
        this.cadetGraduationDismissed = false;
        try {
            const res = await apiFetch("/api/tutorial/reset", { method: "POST" });
            const json = await res.json();
            if (json.ok) {
                this.appendLog(json.message, "system");
                this.state = json.state;
                this.renderHUD();
                if (this.activeRightTab === "story") {
                    this.renderStory();
                }
            }
        } catch (e) {
            console.error("Error resetting tutorial:", e);
        }
    }

    renderMarketTable() {
        if (!this.state) return;
        this.syncMarketLotBar();
        this.marketTableBody.innerHTML = "";
        const quotes = this.state.market_quotes || [];
        const cargo = this.state.ship.cargo || {};
        const avgCost = this.state.cargo_avg_cost || {};
        const lot = this.tradeLot;

        quotes.forEach(q => {
            const tr = document.createElement("tr");
            const holdCount = cargo[q.commodity_id] || 0;
            const avg = avgCost[q.commodity_id];
            const maxBuy = Number(q.max_buy ?? 0);
            // A fixed lot is clamped to what the hold and credits allow, so the button never lies.
            const buyQty = lot === "max" ? maxBuy : Math.min(Number(lot), maxBuy);
            const sellQty = lot === "max" ? holdCount : Math.min(Number(lot), holdCount);
            const margin = avg ? (q.sell_price >= avg ? "td-profit" : "td-loss") : "";
            const commId = this.escapeHtml(q.commodity_id);

            tr.innerHTML = `
                <td><strong class="commodity-name">${this.escapeHtml(q.name)}</strong><small class="commodity-category">${this.escapeHtml(q.category)}</small></td>
                <td class="td-buy">${q.buy_price}</td>
                <td class="td-sell ${margin}">${q.sell_price}</td>
                <td class="td-hold">${holdCount}${avg ? `<small class="td-avg" title="Average paid per unit held">@${avg}</small>` : ""}</td>
                <td>
                    <div class="trade-btn-group">
                        <button class="btn-trade" data-comm="${commId}" data-action="buy" data-qty="${buyQty}" ${buyQty <= 0 ? "disabled" : ""}
                            title="${buyQty > 0 ? `Buy ${buyQty}. Shift+click buys the max (${maxBuy}).` : "No credits or hold space for another unit."}">BUY ${buyQty || ""}</button>
                        <button class="btn-trade btn-sell-trade" data-comm="${commId}" data-action="sell" data-qty="${sellQty}" ${holdCount <= 0 ? "disabled" : ""}
                            title="Sell ${sellQty}. Shift+click sells all ${holdCount}.">${lot === "max" && holdCount > 0 ? "SELL ALL" : `SELL ${sellQty || ""}`}</button>
                    </div>
                </td>
            `;

            tr.querySelectorAll(".btn-trade").forEach(b => {
                b.addEventListener("click", (e) => {
                    const button = e.currentTarget;
                    const isBuy = button.getAttribute("data-action") === "buy";
                    const useMax = e.shiftKey || lot === "max";
                    this.handleTrade(button.getAttribute("data-comm"), Number(button.getAttribute("data-qty")), isBuy, useMax);
                });
            });

            this.marketTableBody.appendChild(tr);
        });
    }

    syncMarketLotBar() {
        document.querySelectorAll("#marketLotBar .market-lot-btn").forEach(button => {
            const active = button.getAttribute("data-lot") === this.tradeLot;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });
    }

    setTradeLot(lot) {
        this.tradeLot = TRADE_LOTS.includes(lot) ? lot : "1";
        this.saveSettings();
        this.renderMarketTable();
    }

    async loadQuantumFreight() {
        if (!this.quantumFreight) return;
        try {
            const res = await apiFetch("/api/trade/quantum");
            const json = await res.json();
            if (json.ok) {
                this.quantumData = json.quantum;
                this.renderQuantumFreight();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Quantum freight lanes unavailable: ${e.message}`, "hazard");
        }
    }

    renderQuantumFreight() {
        if (!this.quantumFreight) return;
        const data = this.quantumData;
        const ship = this.state?.ship || {};
        const orders = ship.trade_orders || data?.orders || [];
        this.quantumFreight.style.display = "";
        const commodityNames = new Map(
            (this.state?.market_quotes || []).map(quote => [quote.commodity_id, quote.name])
        );
        const orderRows = orders.length ? orders.map(order => {
            const eta = Math.max(0, Number(order.arrival_tick || 0) - Number(this.state.time?.tick || 0));
            const commodityName = commodityNames.get(order.commodity_id) || order.commodity_id;
            return `<div class="quantum-order-row">
                <span class="q-order-id">${this.escapeHtml(order.id)}</span>
                <span>${order.quantity}x ${this.escapeHtml(commodityName)} -> ${this.escapeHtml(order.destination_name)}</span>
                <span class="q-order-eta">ETA ${eta}T</span>
            </div>`;
        }).join("") : `<p class="panel-intro-text">No freight in transit.</p>`;

        const allRoutes = data?.routes || [];
        const routes = allRoutes.slice(0, window.innerWidth < 1500 ? 4 : 6);
        const routeRows = routes.length ? routes.map(route => {
            const netClass = route.net >= 0 ? "q-net-positive" : "q-net-negative";
            return `<div class="quantum-route-row">
                <div class="q-route-main">
                    <strong>${this.escapeHtml(route.commodity_name)} x${route.quantity}</strong>
                    <small>${this.escapeHtml(route.destination_system_name)} // ${this.escapeHtml(route.destination_name)}</small>
                </div>
                <div class="q-route-meta">
                    <span>${route.jumps}J · ${route.duration_ticks}T</span>
                    <small>FEE ${route.fee} CR</small>
                </div>
                <div class="q-route-net ${netClass}">
                    <strong>${route.net >= 0 ? "+" : ""}${route.net} CR</strong>
                    <small>NET</small>
                </div>
                <button class="btn-hud" data-q-comm="${this.escapeHtml(route.commodity_id)}"
                    data-q-dest="${this.escapeHtml(route.destination_system_id)}"
                    data-q-qty="${route.quantity}" ${data?.docked ? "" : "disabled"}>SHIP</button>
            </div>`;
        }).join("") : `<p class="panel-intro-text">No profitable lanes from the current hold.</p>`;

        this.quantumFreight.innerHTML = `
            <div class="quantum-header">
                <h3 class="subpanel-title">QUANTUM FREIGHT</h3>
                <span>${orders.length}/${data?.max_orders || 4} IN TRANSIT</span>
            </div>
            <div class="quantum-orders">${orderRows}</div>
            <div class="quantum-routes">${routeRows}</div>
            <p class="quantum-note">Cargo leaves immediately; the destination pays on arrival. Fees are charged now.</p>
        `;
        this.quantumFreight.querySelectorAll("[data-q-comm]").forEach(button => {
            button.addEventListener("click", () => this.handleQuantumOrder(
                button.getAttribute("data-q-comm"),
                Number(button.getAttribute("data-q-qty")),
                button.getAttribute("data-q-dest")
            ));
        });
    }

    async handleQuantumOrder(commodityId, quantity, destinationSystemId) {
        try {
            const res = await apiFetch("/api/trade/quantum/place", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    commodity_id: commodityId,
                    quantity,
                    destination_system_id: destinationSystemId,
                })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
            } else {
                this.appendLog(`[FREIGHT BLOCKED] ${json.message}`, "hazard");
            }
            if (json.state) {
                this.state = json.state;
                this.renderHUD();
                this.loadQuantumFreight();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Quantum freight failed: ${e.message}`, "hazard");
        }
    }

    renderArsenal() {
        if (!this.state) return;
        if (this.arsenalList) {
            this.arsenalList.innerHTML = "";
            const upgrades = this.state.catalog_upgrades || [];
            const equipped = this.state.ship.equipped_upgrades || {};
            const credits = this.state.ship.credits;

            upgrades.forEach(u => {
                const isEquipped = equipped[u.slot] === u.id;
                const card = document.createElement("div");
                card.className = `arsenal-card ${isEquipped ? 'installed' : ''}`;

                card.innerHTML = `
                    <div class="arsenal-info">
                        <div class="arsenal-title-row">
                            <span class="slot-tag">${this.escapeHtml(u.slot.toUpperCase())}</span>
                            <strong class="arsenal-name">${this.escapeHtml(u.name)}</strong>
                        </div>
                        <p class="arsenal-desc">${this.escapeHtml(u.description)}</p>
                    </div>
                    <button class="btn-upgrade-buy" ${isEquipped || credits < u.cost ? 'disabled' : ''} data-id="${this.escapeHtml(u.id)}">
                        ${isEquipped ? 'EQUIPPED' : `${u.cost} CR`}
                    </button>
                `;

                if (!isEquipped) {
                    card.querySelector(".btn-upgrade-buy").addEventListener("click", () => this.handleBuyUpgrade(u.id));
                }

                this.arsenalList.appendChild(card);
            });
        }

        // Render Shipyard Chassis Showroom
        if (this.shipyardChassisList) {
            this.shipyardChassisList.innerHTML = "";
            const chassisList = this.state.catalog_chassis || [];
            const currentClass = this.state.ship?.ship_class;
            const credits = this.state.ship?.credits || 0;
            const isDocked = !!(this.state.orbiting_body && this.state.orbiting_body.station_dockable);

            chassisList.forEach(c => {
                const isCurrent = currentClass === c.ship_class;
                const isStarter = c.cost === 0;
                const canAfford = credits >= c.cost;
                const card = document.createElement("div");
                card.className = `chassis-card ${isCurrent ? 'installed' : ''}`;
                card.innerHTML = `
                    <div class="chassis-info">
                        <div class="chassis-title-row">
                            <span class="slot-tag tag-cyan">${this.escapeHtml(c.ship_class)}</span>
                            <strong class="chassis-name">${this.escapeHtml(c.name)}</strong>
                        </div>
                        <p class="chassis-desc">${this.escapeHtml(c.description)}</p>
                        <div class="chassis-specs">
                            <span>Hull: <strong>${c.max_hull}</strong></span>
                            <span>Shield: <strong>${c.max_shield}</strong></span>
                            <span>Fuel: <strong>${c.max_fuel}</strong></span>
                            <span>Cargo: <strong>${c.cargo_capacity}</strong></span>
                        </div>
                        <div class="chassis-perk">★ ${this.escapeHtml(c.specialty_perk)}</div>
                    </div>
                    <button class="btn-upgrade-buy" ${isCurrent || isStarter || !isDocked || !canAfford ? 'disabled' : ''} data-chassis="${this.escapeHtml(c.id)}">
                        ${isCurrent ? 'ACTIVE HULL' : (isStarter ? 'STARTER' : (!isDocked ? 'DRYDOCK REQ.' : `${c.cost} CR`))}
                    </button>
                `;
                if (!isCurrent && !isStarter && isDocked && canAfford) {
                    card.querySelector(".btn-upgrade-buy").addEventListener("click", () => this.handleCommissionChassis(c.id));
                }
                this.shipyardChassisList.appendChild(card);
            });
        }

        // Render Weapons & Ordnance Bay
        if (this.weaponsBayList) {
            this.weaponsBayList.innerHTML = "";
            const weaponsList = this.state.catalog_weapons || [];
            const ownedWeapons = this.state.ship?.weapons || [];
            const primaryWeapon = this.state.ship?.primary_weapon;
            const credits = this.state.ship?.credits || 0;
            const isDocked = !!(this.state.orbiting_body && this.state.orbiting_body.station_dockable);

            weaponsList.forEach(w => {
                const isOwned = ownedWeapons.includes(w.id);
                const isPrimary = primaryWeapon === w.id;
                const canAfford = credits >= w.cost;
                const card = document.createElement("div");
                card.className = `weapon-card ${isPrimary ? 'installed' : ''}`;
                card.innerHTML = `
                    <div class="weapon-info">
                        <div class="weapon-title-row">
                            <span class="slot-tag tag-red">${this.escapeHtml(w.weapon_type.toUpperCase())}</span>
                            <strong class="weapon-name">${this.escapeHtml(w.name)}</strong>
                        </div>
                        <p class="weapon-desc">${this.escapeHtml(w.description)}</p>
                        <div class="weapon-stats">
                            <span>DMG: <strong>${w.damage}</strong></span>
                            <span>Shield: <strong>x${w.shield_mult}</strong></span>
                            <span>Hull: <strong>x${w.hull_mult}</strong></span>
                            <span>ACC: <strong>${Math.round(w.accuracy * 100)}%</strong></span>
                        </div>
                    </div>
                    <button class="btn-upgrade-buy" ${isPrimary || (!isOwned && (!isDocked || !canAfford)) ? 'disabled' : ''} data-weapon="${this.escapeHtml(w.id)}">
                        ${isPrimary ? 'PRIMARY' : (isOwned ? 'EQUIP' : (!isDocked ? 'DRYDOCK REQ.' : `${w.cost} CR`))}
                    </button>
                `;
                const btn = card.querySelector(".btn-upgrade-buy");
                if (isOwned && !isPrimary) {
                    btn.addEventListener("click", () => this.handleSetPrimaryWeapon(w.id));
                } else if (!isOwned && isDocked && canAfford) {
                    btn.addEventListener("click", () => this.handleInstallWeapon(w.id));
                }
                this.weaponsBayList.appendChild(card);
            });
        }
    }

    formatEffectLabel(key, value) {
        const names = {
            max_hull: "HULL", max_shield: "SHIELD", cargo_capacity: "CARGO", fuel_efficiency: "FUEL BURN",
            reactor_output: "REACTOR OUTPUT", reactor_cooling: "COOLING", heat_capacity: "HEAT CAP",
            heat_generation: "HEAT GEN", reactor_integrity: "CORE INTEGRITY", evasion: "EVASION",
            combat_damage: "DAMAGE", scan_mult: "SCAN", relic_find: "RELIC", trade_margin: "TRADE",
            drone_yield: "DRONE YIELD", pirate_evasion: "ECM",
        };
        const label = names[key] || key.replace(/_/g, " ").toUpperCase();
        if (key === "fuel_efficiency") {
            const pct = Math.round((value > 0 ? -value : -value) * 100);
            return `${label} ${value > 0 ? "-" : "+"}${Math.abs(pct)}%`;
        }
        if (key === "scan_mult") return `${label} ${value >= 1 ? "+" : "-"}${Math.abs(Math.round((value - 1) * 100))}%`;
        if (["evasion", "relic_find", "trade_margin", "drone_yield"].includes(key)) {
            return `${label} ${value >= 0 ? "+" : ""}${Math.round(value * 100)}%`;
        }
        if (["reactor_output", "heat_generation"].includes(key)) {
            return `${label} ${value >= 0 ? "+" : ""}${Math.round(value * 100)}%`;
        }
        return `${label} ${value >= 0 ? "+" : ""}${Math.round(value)}`;
    }

    renderPlayer() {
        if (!this.state || !this.characterProfile) return;
        if (this.characterAbilities?.contains(document.activeElement)) return;
        const ch = this.state.character || {};
        const skillPoints = ch.skill_points || 0;
        const xp = ch.xp || 0;
        const nextXp = ch.next_level_xp || 400;
        const xpPct = Math.min(100, (xp / nextXp) * 100);
        const traits = ch.traits || [];

        this.characterProfile.innerHTML = `
            <div class="character-portrait-large">${this.portraitAvatar(ch.portrait, ch.name || "Player", 60)}</div>
            <div class="character-info">
                <div class="character-name-row">
                    <span class="character-name">${this.escapeHtml(ch.name || "Player")}</span>
                </div>
                <div class="character-meta">
                    <span>Age ${ch.age || 30}</span>
                    <span>${this.escapeHtml(ch.background || "Navigator")}</span>
                    <span>${skillPoints} SP AVAILABLE</span>
                </div>
                <div class="character-xp-row">
                    <span class="character-level">LEVEL ${ch.level || 1}</span>
                    <div class="character-xp-bar"><div class="character-xp-fill" style="width: ${xpPct}%"></div></div>
                    <span class="character-xp-text" style="font-family: var(--font-mono); font-size: 12px; color: var(--neon-amber);">${xp}/${nextXp} XP</span>
                </div>
            </div>
        `;

        const abilities = Object.entries(this.state.character_abilities || {});
        const unlocked = new Set(ch.abilities || []);
        const cooldowns = ch.ability_cooldowns || {};
        const shipState = this.state.ship || {};
        const charmTarget = this.abilityTargetFaction("charm_offensive");
        this.characterAbilities.innerHTML = abilities.map(([id, info]) => {
            const isUnlocked = unlocked.has(id);
            const cd = cooldowns[id] || 0;
            const contextBlocked = (id === "battle_focus" && !this.state.active_combat)
                || (id === "emergency_repair" && (Number(shipState.hull || 0) <= 0 || Number(shipState.hull || 0) >= Number(shipState.max_hull || 1)))
                || (id === "charm_offensive" && !charmTarget);
            return `<div class="ability-row ${isUnlocked ? "" : "locked"}">
                <span><strong>${this.escapeHtml(info.name)}</strong><br><small>${this.escapeHtml(info.description)}</small></span>
                <span class="cooldown">${isUnlocked ? (cd > 0 ? `CD ${cd}` : contextBlocked ? "IDLE" : "READY") : "LOCKED"}</span>
                <button class="btn-hud btn-amber" data-use-ability="${this.escapeHtml(id)}" data-ability-faction="${this.escapeHtml(charmTarget || "")}" ${!isUnlocked || cd > 0 || contextBlocked ? "disabled" : ""}>USE</button>
            </div>`;
        }).join("");
        this.characterAbilities.querySelectorAll("[data-use-ability]").forEach(btn =>
            btn.addEventListener("click", () => this.useAbilityQuick(
                btn.getAttribute("data-use-ability"),
                btn.getAttribute("data-ability-faction") || null
            ))
        );

        this.characterPerks.innerHTML = `
            <h4>TRAITS</h4>
            <div class="perks-list">
                ${traits.length
                    ? traits.map(t => `<span class="perk-badge active">${this.escapeHtml(String(t).replace(/_/g, " "))}</span>`).join("")
                    : `<span class="perk-badge">NO TRAITS RECORDED</span>`}
            </div>
        `;
    }

    renderSkills() {
        if (!this.state || !this.skillsGrid) return;
        const ch = this.state.character || {};
        const skillPoints = ch.skill_points || 0;
        if (this.skillsGrid.contains(document.activeElement)) {
            if (this.skillsPointsAvailable) this.skillsPointsAvailable.textContent = skillPoints;
            return;
        }
        const skills = ch.skills || { piloting: 0, engineering: 0, science: 0, combat: 0, diplomacy: 0, trade: 0 };
        const maxRank = 10;

        this.skillsGrid.innerHTML = Object.entries(skills).map(([id, level]) => {
            const meta = SKILL_META[id] || { name: id, icon: "✦", desc: "" };
            const canTrain = skillPoints > 0 && level < maxRank;
            return `
            <div class="skill-card">
                <div class="skill-header">
                    <span class="skill-name"><span class="skill-icon">${meta.icon}</span> ${this.escapeHtml(meta.name)}</span>
                    <span class="skill-level">RANK ${level}/${maxRank}</span>
                </div>
                <div class="skill-bar">
                    <div class="skill-bar-fill" style="width: ${(level / maxRank) * 100}%"></div>
                </div>
                <div class="skill-desc">${this.escapeHtml(meta.desc)}</div>
                <button class="btn-hud btn-amber skill-train-btn" data-train-skill="${this.escapeHtml(id)}" ${canTrain ? "" : "disabled"}>TRAIN 1 SP</button>
            </div>
        `;
        }).join("");
        this.skillsGrid.querySelectorAll("[data-train-skill]").forEach(btn =>
            btn.addEventListener("click", () => this.trainSkill(btn.getAttribute("data-train-skill")))
        );

        if (this.skillsPointsAvailable) {
            this.skillsPointsAvailable.textContent = skillPoints;
        }
        this.renderSkillsPerks();
        this.renderRelics();
    }

    async trainSkill(skillId) {
        if (!skillId || !this.state) return;
        this.sound.init();
        await this.postAction("/api/character/train", { skill: skillId }, null);
        this.renderSkills();
    }

    renderSkillsQuickPanel() {
        if (!this.state || !this.hudSkillsGrid) return;
        const abilities = this.state.character_abilities || {};
        const ship = this.state.ship || {};
        const charmTarget = this.abilityTargetFaction("charm_offensive");
        const inCombat = Boolean(this.state.active_combat);
        const available = id => {
            const info = abilities[id] || {};
            if (!info.unlocked || Number(info.cooldown || 0) > 0) return false;
            if (id === "battle_focus" && !inCombat) return false;
            if (id === "emergency_repair" && Number(ship.hull || 0) <= 0) return false;
            if (id === "emergency_repair" && Number(ship.hull || 0) >= Number(ship.max_hull || 1)) return false;
            if (id === "charm_offensive" && !charmTarget) return false;
            return true;
        };
        const ready = ABILITY_ORDER.filter(available).length;
        if (this.hudSkillsReady) this.hudSkillsReady.textContent = String(ready);
        const signature = ABILITY_ORDER.map(id => `${id}:${(abilities[id] || {}).unlocked ? 1 : 0}:${(abilities[id] || {}).cooldown || 0}`).join("|")
            + `|${inCombat}|${ship.hull}|${ship.max_hull}|${charmTarget || ""}`;
        if (this.skillsPointerDown || this.hudSkillsGrid.contains(document.activeElement)) return;
        if (signature === this.abilitySignature && this.hudSkillsGrid.childElementCount) return;
        this.abilitySignature = signature;
        this.hudSkillsGrid.innerHTML = ABILITY_ORDER.map((id, index) => {
            const info = abilities[id] || {};
            const meta = ABILITY_META[id] || { name: id, icon: "✦" };
            const unlocked = Boolean(info.unlocked);
            const cooldown = Math.max(0, Number(info.cooldown || 0));
            const total = Math.max(1, Number(info.cooldown_total || 0));
            const readyNow = available(id);
            const contextLabel = id === "battle_focus" ? "NO COMBAT"
                : id === "emergency_repair" ? "FULL HULL"
                : id === "charm_offensive" ? "NO TARGET" : "";
            const percent = !unlocked ? 0 : readyNow ? 100 : cooldown > 0 ? Math.max(0, 100 - (cooldown / total) * 100) : 0;
            const stateLabel = !unlocked ? "LOCKED" : readyNow ? "READY" : cooldown > 0 ? `CD ${Math.ceil(cooldown)}` : contextLabel;
            const requirement = info.skill ? `${info.skill} rank ${ABILITY_UNLOCK_RANK[id] || 7}` : "skill training";
            const title = unlocked ? `${meta.name} // ${stateLabel} // ${SKILL_HOTKEYS[index]}` : `${meta.name} // locked: raise ${requirement}`;
            return `
                <button class="skill-quick-chip ${readyNow ? "is-ready" : unlocked ? "is-cooldown" : "is-locked"}"
                        data-quick-ability="${this.escapeHtml(id)}"
                        title="${this.escapeHtml(title)}"
                        ${readyNow ? "" : "disabled"}>
                    <span class="skill-quick-hotkey">${SKILL_HOTKEYS[index] || "-"}</span>
                    <span class="skill-quick-icon">${meta.icon}</span>
                    <span class="skill-quick-name">${this.escapeHtml(meta.label || meta.name)}</span>
                    <span class="skill-quick-rank">${stateLabel}</span>
                    <span class="skill-quick-bar"><i style="width:${percent}%"></i></span>
                </button>
            `;
        }).join("");

        this.hudSkillsGrid.querySelectorAll("[data-quick-ability]").forEach(btn =>
            btn.addEventListener("click", () => this.useAbilityQuick(btn.getAttribute("data-quick-ability")))
        );
    }

    async useAbilityQuick(abilityId, factionOverride = null) {
        if (!abilityId || !this.state || this.abilityPending) return;
        const info = (this.state.character_abilities || {})[abilityId];
        const label = (ABILITY_META[abilityId] || {}).name || abilityId;
        if (!info || !info.unlocked) return this.reportProblem(`${label} is locked; train the matching skill.`);
        if (Number(info.cooldown || 0) > 0) return this.reportProblem(`${label} is on cooldown (${Math.ceil(Number(info.cooldown))} ticks).`);
        if (Number((this.state.ship || {}).hull || 0) <= 0) return this.reportProblem("The ship is destroyed; no ability can be engaged.");
        if (abilityId === "emergency_repair" && Number(this.state.ship.hull) >= Number(this.state.ship.max_hull)) {
            return this.reportProblem("Emergency Repair needs hull damage to weld.");
        }
        if (abilityId === "battle_focus" && !this.state.active_combat) {
            return this.reportProblem("Battle Focus requires an active combat engagement.");
        }
        const factionId = factionOverride || this.abilityTargetFaction(abilityId);
        if (abilityId === "charm_offensive" && !factionId) {
            return this.reportProblem("Diplomatic Offensive needs a sovereign faction in the current system.");
        }
        this.abilityPending = true;
        try {
            this.sound.init();
            await this.postAction("/api/character/ability", {
                ability_id: abilityId,
                faction_id: factionId,
            }, null);
        } finally {
            this.abilityPending = false;
            this.abilitySignature = "";
            this.renderSkillsQuickPanel();
        }
    }

    // Quick-bar diplomacy targets the sovereign faction of the current system, never a fallback.
    abilityTargetFaction(abilityId) {
        if (abilityId !== "charm_offensive") return null;
        const name = (this.state.current_system || {}).faction || "";
        const factions = this.state.factions || {};
        const match = Object.entries(factions).find(([, f]) => f.name === name);
        return match ? match[0] : null;
    }

    renderShip() {
        if (!this.state || !this.shipVisual) return;
        const ship = this.state.ship || {};
        const report = this.state.ship_mods || {};
        const slots = report.slots || [];
        const labels = report.slot_labels || {};
        const installed = report.installed || {};
        const catalog = report.catalog || [];
        const docked = !!(this.state.orbiting_body && this.state.orbiting_body.station_dockable);
        const credits = ship.credits || 0;

        const shipClass = String(ship.ship_class || "Corvette Scout");
        const silhouettes = {
            standard: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#7fb7c9;stop-opacity:0.8"/><stop offset="100%" style="stop-color:#0080ff;stop-opacity:0.6"/></linearGradient></defs><path d="M280,60 L20,10 L20,110 Z" fill="url(#shipGrad)" stroke="#7fb7c9" stroke-width="2"/><circle cx="260" cy="60" r="8" fill="#c9a35a" opacity="0.8"/><rect x="20" y="40" width="60" height="40" fill="#1a2a4a" stroke="#7fb7c9" stroke-width="1" rx="4"/></svg>`,
            freighter: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#c9a35a;stop-opacity:0.8"/><stop offset="100%" style="stop-color:#ff8800;stop-opacity:0.6"/></linearGradient></defs><path d="M260,55 L20,10 L20,110 L260,65 Z" fill="url(#shipGrad)" stroke="#c9a35a" stroke-width="2"/><rect x="30" y="25" width="200" height="70" fill="#2a2a1a" stroke="#c9a35a" stroke-width="1" rx="6"/><circle cx="240" cy="60" r="10" fill="#7fb7c9" opacity="0.8"/></svg>`,
            fighter: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#c96b5a;stop-opacity:0.8"/><stop offset="100%" style="stop-color:#cc0033;stop-opacity:0.6"/></linearGradient></defs><path d="M290,60 L20,10 L20,110 Z" fill="url(#shipGrad)" stroke="#c96b5a" stroke-width="2"/><path d="M270,60 L290,70 L270,80 Z" fill="#c96b5a" opacity="0.8"/><rect x="20" y="45" width="40" height="30" fill="#3a1a1a" stroke="#c96b5a" stroke-width="1" rx="3"/></svg>`,
            explorer: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#a98bbd;stop-opacity:0.8"/><stop offset="100%" style="stop-color:#7209b7;stop-opacity:0.6"/></linearGradient></defs><path d="M270,60 L30,15 L30,105 Z" fill="url(#shipGrad)" stroke="#a98bbd" stroke-width="2"/><ellipse cx="30" cy="60" rx="20" ry="15" fill="#2a1a3a" stroke="#a98bbd" stroke-width="1"/><circle cx="250" cy="60" r="6" fill="#8fbf9f" opacity="0.8"/></svg>`,
            stealth: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#444;stop-opacity:0.9"/><stop offset="100%" style="stop-color:#111;stop-opacity:0.7"/></linearGradient></defs><path d="M280,60 L30,10 L30,110 Z" fill="url(#shipGrad)" stroke="#666" stroke-width="1.5"/><path d="M260,60 L270,65 L260,70" fill="none" stroke="#8fbf9f" stroke-width="2" opacity="0.6"/></svg>`
        };
        const silhouette = /freight|cargo/i.test(shipClass) ? "freighter"
            : /fighter|intercept/i.test(shipClass) ? "fighter"
            : /explor|survey/i.test(shipClass) ? "explorer"
            : /stealth|ghost/i.test(shipClass) ? "stealth"
            : "standard";
        this.shipVisual.innerHTML = silhouettes[silhouette];

        const slotPositions = {
            frame: { top: "50%", left: "20%" },
            reactor_core: { top: "45%", left: "48%" },
            thermal: { top: "25%", left: "62%" },
            drive: { top: "72%", left: "72%" },
            ops: { top: "25%", left: "32%" }
        };

        slots.forEach(slot => {
            const position = slotPositions[slot] || { top: "50%", left: "50%" };
            const modId = installed[slot];
            const mod = catalog.find(m => m.id === modId);
            const slotDiv = document.createElement("div");
            slotDiv.className = `ship-module-slot ${mod ? "filled" : "empty"}`;
            slotDiv.style.top = position.top;
            slotDiv.style.left = position.left;
            slotDiv.dataset.slot = slot;
            slotDiv.innerHTML = mod
                ? `<span class="ship-module-icon">?</span><span class="ship-module-name">${this.escapeHtml(mod.name)}</span>`
                : `<span class="ship-module-icon">+</span><span class="ship-module-name">${this.escapeHtml(labels[slot] || slot)}</span>`;
            slotDiv.title = mod
                ? `${mod.name}: ${mod.description}`
                : `${labels[slot] || slot} ? pick a compatible module below`;
            slotDiv.addEventListener("click", () => {
                if (mod && docked) {
                    this.handleModuleAction(mod.id, "uninstall");
                } else if (mod) {
                    this.appendLog("[SHIP] Dock at a station or colony drydock to remove structural modules.", "system");
                } else {
                    this.appendLog(`[SHIP] Select a ${labels[slot] || slot} module from the list below.`, "system");
                }
            });
            this.shipVisual.appendChild(slotDiv);
        });

        if (this.shipModulesGrid) {
            this.shipModulesGrid.innerHTML = catalog.length ? catalog.map(mod => {
                const isInstalled = installed[mod.slot] === mod.id;
                const slotBusy = Boolean(installed[mod.slot]) && installed[mod.slot] !== mod.id;
                const disabled = !docked || (!isInstalled && (slotBusy || credits < mod.cost));
                const effects = Object.entries(mod.effects || {})
                    .map(([key, value]) => `<span class="ship-module-stat">${this.escapeHtml(this.formatEffectLabel(key, value))}</span>`)
                    .join("");
                return `
                    <div class="ship-module-row ${isInstalled ? "installed" : ""}" data-module="${this.escapeHtml(mod.id)}">
                        <span class="ship-module-glyph">${isInstalled ? "◆" : "◇"}</span>
                        <div class="ship-module-info">
                            <strong>${this.escapeHtml(mod.name)}</strong>
                            <small>${this.escapeHtml(labels[mod.slot] || mod.slot)} // ${this.escapeHtml(mod.description)}</small>
                        </div>
                        <div class="ship-module-effects">
                            ${effects}
                            <span class="ship-module-cost">${isInstalled ? "INSTALLED" : (slotBusy ? "SLOT BUSY" : `${mod.cost} CR`)}</span>
                        </div>
                        <button class="btn-hud ${isInstalled ? "btn-amber" : "btn-cyan"}" data-action="${isInstalled ? "uninstall" : "install"}" ${disabled ? "disabled" : ""}>${isInstalled ? "REMOVE" : "INSTALL"}</button>
                    </div>
                `;
            }).join("") : `<p class="panel-intro-text">No structural refits are available.</p>`;
            this.shipModulesGrid.querySelectorAll("[data-module]").forEach(card => {
                const button = card.querySelector("[data-action]");
                if (button) {
                    button.addEventListener("click", () => this.handleModuleAction(card.dataset.module, button.dataset.action));
                }
            });
        }

        if (this.shipStatsPanel) {
            const cargo = (this.state.inventory_manifest || []).reduce(
                (sum, item) => sum + Number(item.total_volume || 0),
                0
            );
            const rows = [
                ["Hull", `${ship.hull || 0}/${ship.max_hull || 0}`],
                ["Shield", `${ship.shield || 0}/${ship.max_shield || 0}`],
                ["Fuel", `${ship.fuel || 0}/${ship.max_fuel || 0}`],
                ["Cargo", `${cargo}/${ship.cargo_capacity || 0}`],
                ["Class", shipClass.toUpperCase()],
                ["Modules", `${Object.keys(installed).length}/${slots.length || 0}`]
            ];
            this.shipStatsPanel.innerHTML = `
                <h4>SHIP STATISTICS</h4>
                <div class="ship-stats-grid">
                    ${rows.map(([label, value]) => `
                        <div class="ship-stat-item">
                            <span class="ship-stat-label">${label}</span>
                            <span class="ship-stat-value">${this.escapeHtml(String(value))}</span>
                        </div>
                    `).join("")}
                </div>
                ${docked ? "" : `<p class="panel-intro-text" style="color: var(--neon-amber);">Orbit a station or colony drydock to install or remove structural modifications.</p>`}
            `;
        }
    }

    handleModuleAction(modId, action) {
        this.postAction("/api/ship/module", { module_id: modId, action }, "ship");
    }

    renderCrew() {
        if (!this.state) return;
        const crew = this.state.crew || [];
        const bonuses = this.state.crew_bonuses || {};
        const roles = this.state.crew_roles || [];
        const cashFlow = (this.state.crew_report && this.state.crew_report.cash_flow) || this.state.cash_flow || null;
        const bonusLabels = {
            fuel_efficiency: "FUEL EFFICIENCY",
            evasion: "EVASION",
            reactor_cooling: "COOLING",
            hull_repair_per_tick: "HULL REPAIR/TICK",
            scan_mult: "SCAN RANGE",
            research_per_tick: "RESEARCH/TICK",
            combat_damage: "COMBAT DAMAGE",
            trade_margin: "TRADE MARGIN",
            boarding_defense: "BOARDING DEFENSE"
        };

        if (this.crewCashFlow && cashFlow) {
            const net = cashFlow.net_per_month;
            const netColor = net >= 0 ? "var(--neon-green, #00f088)" : "var(--neon-red, #c96b5a)";
            this.crewCashFlow.innerHTML = `
                <span class="cashflow-label">CASH FLOW / MONTH</span>
                <span class="cashflow-value">PAYROLL <strong>-${cashFlow.upkeep_per_month}</strong> CR</span>
                <span class="cashflow-value">PASSIVE <strong>+${cashFlow.passive_per_month}</strong> CR</span>
                <span class="cashflow-value">NET <strong style="color:${netColor}">${net >= 0 ? "+" : ""}${net}</strong> CR</span>
            `;
        }

        if (this.crewAssignments) {
            const bonusChips = Object.entries(bonuses)
                .filter(([, value]) => value !== 0 && value !== 1)
                .map(([key, value]) => {
                    const pct = ["fuel_efficiency", "evasion", "scan_mult", "trade_margin", "boarding_defense"].includes(key);
                    const display = pct
                        ? `${value > 0 && key !== "fuel_efficiency" ? "+" : ""}${Math.round((value - (key === "fuel_efficiency" || key === "scan_mult" ? 1 : 0)) * 100)}%`
                        : `${value > 0 ? "+" : ""}${Math.round(value * 10) / 10}`;
                    return `<span class="crew-bonus-chip">${this.escapeHtml(bonusLabels[key] || key)} ${display}</span>`;
                })
                .join("");
            this.crewAssignments.innerHTML = `
                <h4>ACTIVE CREW BONUSES</h4>
                <div class="crew-bonus-grid">${bonusChips || `<span class="crew-bonus-chip">NO ACTIVE BONUSES</span>`}</div>
                <h4>AVAILABLE ROLES</h4>
                <div class="crew-role-grid">
                    ${roles.map(role => `
                        <div class="crew-role-row">
                            <span class="crew-role-info"><strong>${this.escapeHtml(role.name)}</strong><small>${this.escapeHtml(role.description)}</small></span>
                            <span class="crew-role-cost">${role.cost} CR</span>
                            <button class="btn-hud btn-green" data-recruit-crew="${this.escapeHtml(role.id || role.name)}">RECRUIT</button>
                        </div>
                    `).join("")}
                </div>
            `;
        }

        if (this.crewAssignments) {
            this.crewAssignments.querySelectorAll("[data-recruit-crew]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/crew/recruit", { role_id: btn.getAttribute("data-recruit-crew") }, "crew"))
            );
        }

        if (this.crewRoster) {
            this.crewRoster.innerHTML = crew.length ? crew.map(m => {
                const morale = Math.round(m.morale);
                const moraleClass = morale < 20 ? "crew-morale-critical" : (morale < 35 ? "crew-morale-low" : "");
                const moraleNote = morale < 20 ? " !! NEAR DESERTION" : (morale < 35 ? " LOW" : "");
                const injury = Number(m.injury_ticks || 0);
                const xpToNext = Math.max(1, Number(m.skill || 1) * 40);
                const away = (this.state.away_report?.active || []).find(mission => (mission.crew_ids || []).includes(m.id));
                const statusNote = injury > 0
                    ? ` | <span class="crew-injury">INJURED ${injury}T</span>`
                    : (away ? ` | <span class="crew-away">AWAY: ${this.escapeHtml(away.name)}</span>` : "");
                return `
                <div class="crew-row">
                    <div class="crew-portrait">${this.portraitAvatar(m.portrait, m.name)}</div>
                    <div class="crew-info-block">
                        <strong>${this.escapeHtml(m.name)}</strong>
                        <small>${this.escapeHtml(m.role)} · SKILL ${m.skill} · XP ${m.xp || 0}/${xpToNext}${statusNote}</small>
                    </div>
                    <div class="crew-morale-bar" title="Morale ${morale}${moraleNote}">
                        <div class="crew-morale-fill ${moraleClass}" style="width:${morale}%"></div>
                        <span class="crew-morale-text">${morale}${moraleNote}</span>
                    </div>
                    <div class="crew-actions">
                        <button class="btn-hud btn-amber" data-train-crew="${this.escapeHtml(m.id)}" ${m.skill >= 10 || injury > 0 ? "disabled" : ""}>DRILL</button>
                        <button class="btn-hud" data-dismiss-crew="${this.escapeHtml(m.id)}" ${away ? "disabled" : ""}>DISMISS</button>
                    </div>
                </div>
                `;
            }).join("") : `<p class="panel-intro-text">No crew aboard. Dock at a station and recruit specialists.</p>`;
            this.crewRoster.querySelectorAll("[data-train-crew]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/crew/train", { crew_id: btn.getAttribute("data-train-crew") }, "crew"))
            );
            this.crewRoster.querySelectorAll("[data-dismiss-crew]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/crew/dismiss", { crew_id: btn.getAttribute("data-dismiss-crew") }, "crew"))
            );
        }

        this.renderAway();

        if (this.btnShoreLeave) {
            this.btnShoreLeave.addEventListener("click", () => this.handleShoreLeave());
        }
    }

    renderSurfaceOps() {
        if (!this.surfaceOps) return;
        const data = this.state?.surface_report;
        if (
            !data || !data.landed || this.selectedType !== "body"
            || String(this.selectedTarget?.id || "") !== String(data.body?.id || "")
        ) {
            this.surfaceOps.style.display = "none";
            return;
        }
        const body = data.body || {};
        const operations = data.operations || [];
        const wasHidden = this.surfaceOps.style.display === "none";
        const rows = operations.map(op => {
            const riskClass = op.risk >= 35 ? "risk-high" : (op.risk >= 18 ? "risk-mid" : "risk-low");
            const rewards = [];
            if (op.credits) rewards.push(`+${op.credits} CR`);
            if (op.research) rewards.push(`+${op.research} RES`);
            if (op.credit_cost) rewards.push(`-${op.credit_cost} CR`);
            if (op.heal_injuries) rewards.push(`HEAL ${op.heal_injuries}`);
            if (op.morale) rewards.push(`MORALE ${op.morale > 0 ? "+" : ""}${op.morale}`);
            (op.cargo || []).forEach(item => rewards.push(`+${item.quantity} ${item.name || item.id}`));
            return `<div class="surface-op-row ${op.used ? "is-worked" : ""}">
                <div class="surface-op-main">
                    <strong>${this.escapeHtml(op.name)}</strong>
                    <small>${this.escapeHtml(op.description)}</small>
                    <small class="surface-op-reward">${rewards.map(item => this.escapeHtml(item)).join(" · ")}</small>
                </div>
                <div class="surface-op-side">
                    <span class="away-risk ${riskClass}">${op.risk}%</span>
                    <button class="btn-hud" data-surface-op="${this.escapeHtml(op.id)}" ${op.used ? "disabled" : ""}>${op.used ? "WORKED" : "RUN"}</button>
                </div>
            </div>`;
        }).join("");
        this.surfaceOps.style.display = "block";
        this.surfaceOps.innerHTML = `
            <div class="surface-header">
                <h4>SURFACE OPERATIONS // ${this.escapeHtml(body.name || "")}</h4>
                <span>${data.used_count}/${data.total_count} WORKED</span>
            </div>
            <div class="surface-op-list">${rows || '<p class="panel-intro-text">No operations available.</p>'}</div>
        `;
        this.surfaceOps.querySelectorAll("[data-surface-op]").forEach(button => {
            button.addEventListener("click", () => this.handleSurfaceOp(button.getAttribute("data-surface-op")));
        });
        if (wasHidden) {
            const card = this.surfaceOps.closest(".nav-target-card");
            if (card) card.scrollTop = Math.max(0, this.surfaceOps.offsetTop - 6);
            else this.surfaceOps.scrollIntoView({ block: "nearest" });
        }
    }

    async handleSurfaceOp(operationId) {
        try {
            const res = await apiFetch("/api/surface/op", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ operation_id: operationId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
            } else {
                this.appendLog(`[SURFACE BLOCKED] ${json.message}`, "hazard");
            }
            if (json.state) {
                this.state = json.state;
                this.renderHUD();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Surface operation failed: ${e.message}`, "hazard");
        }
    }

    renderAway() {
        if (!this.awaySection) return;
        const report = this.state?.away_report || {};
        const body = report.body;
        const active = report.active || [];
        const missions = report.available || [];
        const maxActive = report.max_active || 2;
        if (this.crewAwayCount) {
            this.crewAwayCount.textContent = active.length ? String(active.length) : "";
            this.crewAwayCount.classList.toggle("is-live", active.length > 0);
        }
        const bodyLabel = body
            ? `${this.escapeHtml(body.name)} // ${this.escapeHtml(body.body_type || "body")}`
            : "NO ORBIT";

        const activeRows = active.length ? active.map(mission => {
            const team = (mission.team || []).map(member => `${this.escapeHtml(member.name)} (${member.skill})`).join(", ");
            const progress = Math.max(0, Math.min(100, Number(mission.progress || 0)));
            return `
                <div class="away-active-card">
                    <div class="away-active-head">
                        <span class="away-icon">${this.escapeHtml(mission.icon || "◇")}</span>
                        <strong>${this.escapeHtml(mission.name)}</strong>
                        <span class="away-head-meta">ETA ${mission.remaining_ticks}T</span>
                        <button class="btn-hud away-recall-btn" data-away-recall="${this.escapeHtml(mission.id)}">RECALL</button>
                    </div>
                    <div class="away-progress"><span style="width:${progress}%"></span></div>
                    <small class="away-team-line">${team} <span>// risk ${mission.risk}%</span></small>
                </div>
            `;
        }).join("") : `<p class="away-empty">No away teams deployed.</p>`;

        const missionRows = missions.length ? missions.map(mission => {
            const riskValue = mission.risk === null || mission.risk === undefined ? null : Number(mission.risk);
            const riskClass = riskValue === null ? "risk-none" : (riskValue >= 35 ? "risk-high" : (riskValue >= 18 ? "risk-mid" : "risk-low"));
            const riskLabel = riskValue === null ? "N/A" : `${riskValue}%`;
            const team = (mission.team || []).map(member => `${this.escapeHtml(member.name)} ${member.skill}`).join(", ") || "NO HEALTHY CREW";
            const rewards = (mission.rewards || []).map(item => this.escapeHtml(String(item))).join(" · ");
            const blocked = !mission.available;
            const reason = mission.reason ? `<small class="away-reason">${this.escapeHtml(mission.reason)}</small>` : "";
            return `
                <div class="away-mission ${blocked ? "is-blocked" : ""}">
                    <span class="away-icon">${this.escapeHtml(mission.icon || "◇")}</span>
                    <div class="away-mission-info">
                        <div class="away-mission-title">
                            <strong>${this.escapeHtml(mission.name)}</strong>
                            <span class="away-risk ${riskClass}">${riskLabel}</span>
                        </div>
                        <small class="away-desc">${this.escapeHtml(mission.description)}</small>
                        <small class="away-team-line">${team} <span>// ${mission.duration_ticks}T // ${mission.team_size} CREW</span></small>
                        <small class="away-reward-line">${rewards}</small>
                        ${reason}
                        <div class="away-mission-foot">
                            <span class="away-foot-hint">${blocked ? "STANDING BY" : "BEST-FIT TEAM READY"}</span>
                            <button class="btn-hud" data-away-launch="${this.escapeHtml(mission.id)}" ${blocked ? "disabled" : ""}>DEPLOY</button>
                        </div>
                    </div>
                </div>
            `;
        }).join("") : `<p class="away-empty">No expedition profiles fit this body.</p>`;

        this.awaySection.innerHTML = `
            <div class="away-header">
                <h4>AWAY TEAMS</h4>
                <span class="away-deployed">${active.length}/${maxActive} DEPLOYED</span>
            </div>
            <div class="away-body-line">${bodyLabel}</div>
            ${body ? "" : `<p class="away-empty">Establish orbit around a world or station to deploy a team.</p>`}
            ${activeRows}
            <div class="away-mission-list">${body ? missionRows : ""}</div>
        `;
        this.awaySection.querySelectorAll("[data-away-launch]").forEach(btn =>
            btn.addEventListener("click", () => this.handleAwayLaunch(btn.getAttribute("data-away-launch")))
        );
        this.awaySection.querySelectorAll("[data-away-recall]").forEach(btn =>
            btn.addEventListener("click", () => this.handleAwayRecall(btn.getAttribute("data-away-recall")))
        );
    }

    handleAwayLaunch(missionType) {
        return this.postAction("/api/away/launch", { mission_type: missionType }, "crew");
    }

    handleAwayRecall(missionId) {
        return this.postAction("/api/away/recall", { mission_id: missionId }, "crew");
    }

    setCrewView(view) {
        const next = view === "away" ? "away" : "roster";
        this.crewView = next;
        if (this.crewRosterView) this.crewRosterView.style.display = next === "roster" ? "" : "none";
        if (this.crewAwayView) this.crewAwayView.style.display = next === "away" ? "" : "none";
        this.crewViewButtons.forEach(button => {
            const selected = button.getAttribute("data-crew-view") === next;
            button.classList.toggle("is-active", selected);
            button.setAttribute("aria-selected", selected ? "true" : "false");
        });
        if (next === "away") this.renderAway();
    }

    async handleShoreLeave() {
        this.sound.init();
        try {
            const res = await apiFetch("/api/crew/shore", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({})
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(`[CREW] ${json.message}`, "reward");
                this.state = json.state;
                this.renderHUD();
                this.renderCrew();
            } else {
                this.appendLog(`[CREW] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Shore leave failed: ${e.message}`, "hazard");
        }
    }

    portraitAvatar(portraitId, name, size = 40) {
        const palette = ["#7fb7c9", "#c9a35a", "#a98bbd", "#8fbf9f", "#c96b5a", "#66aaff"];
        const key = String(portraitId || name || "crew");
        let hash = 0;
        for (let i = 0; i < key.length; i++) hash = ((hash << 5) - hash + key.charCodeAt(i)) | 0;
        const color = palette[Math.abs(hash) % palette.length];
        const initials = String(name || "?").split(/\s+/).map(p => p[0] || "").slice(0, 2).join("").toUpperCase();
        const fontSize = Math.max(12, size * 0.3);
        return `<svg viewBox="0 0 40 40" width="${size}" height="${size}" role="img" aria-label="${this.escapeHtml(name || "portrait")}">
            <circle cx="20" cy="20" r="18" fill="rgba(0,0,0,.55)" stroke="${color}" stroke-width="1.5"></circle>
            <circle cx="20" cy="15" r="6" fill="${color}" opacity="0.8"></circle>
            <path d="M8 34 Q20 22 32 34" fill="none" stroke="${color}" stroke-width="2" opacity="0.7"></path>
            <text x="20" y="26" text-anchor="middle" font-size="${fontSize}" fill="#fff" font-family="monospace">${this.escapeHtml(initials)}</text>
        </svg>`;
    }

    renderEmpire() {
        if (!this.state || !this.researchSummary) return;
        const research = this.state.research || {};
        const active = research.active_project;
        this.researchSummary.innerHTML = active
            ? `<strong>${this.escapeHtml(active.name)}</strong> — ${research.progress || 0}/${active.cost} points<br>Banked: ${research.points || 0}`
            : `No active project. Banked points: ${research.points || 0}`;
        this.researchProjects.innerHTML = (research.available || []).map(p => `
            <div class="research-row">
                <span>${this.escapeHtml(p.name)}<br><small>${this.escapeHtml(p.description)}</small></span>
                <span>${p.cost} pts</span>
                <button class="btn-hud" data-research="${this.escapeHtml(p.id)}">START</button>
            </div>
        `).join("");
        this.researchProjects.querySelectorAll("[data-research]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/research/start", { project_id: btn.getAttribute("data-research") }, "empire"))
        );

        const outposts = this.state.outposts || [];
        this.outpostSummary.textContent = outposts.length
            ? `${outposts.length} outpost(s) producing each tick.`
            : "No outposts founded yet. Orbit a world and found one below.";
        this.renderOutpostBuild();
        this.outpostList.innerHTML = outposts.map(o => `
            <div class="outpost-row"><span>${this.escapeHtml(o.name)} — LVL ${o.level} — POP ${Number(o.population).toLocaleString()}</span>
            <button class="btn-hud btn-amber" data-outpost-upgrade="${this.escapeHtml(o.id)}">UPGRADE</button></div>
        `).join("");
        this.outpostList.querySelectorAll("[data-outpost-upgrade]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/outpost/upgrade", { outpost_id: btn.getAttribute("data-outpost-upgrade") }, "empire"))
        );

        const leaders = this.state.faction_leaders || [];
        const wars = this.state.wars || [];
        const standings = this.state.ship.faction_standings || {};
        const eliminated = new Set(this.state.eliminated_factions || []);
        this.diplomacyList.innerHTML = leaders.map(l => {
            const atWar = wars.some(w => w.active && (w.defender_id === l.faction_id || w.attacker_id === l.faction_id));
            return `<div class="diplomacy-row ${eliminated.has(l.faction_id) ? "eliminated" : ""}">
                <span><strong>${this.escapeHtml(l.name)}</strong> (${this.escapeHtml(l.faction_id)})<br>
                <small>${this.escapeHtml(l.title)} — <span class="leader-behavior">${this.escapeHtml(l.behavior)}</span></small></span>
                <span>standing ${standings[l.faction_id] || 0}${atWar ? " | WAR" : ""}</span>
                <button class="btn-hud" data-diplo="${this.escapeHtml(l.faction_id)}">IMPROVE</button>
            </div>`;
        }).join("");
        this.diplomacyList.querySelectorAll("[data-diplo]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/diplomacy", { faction_id: btn.getAttribute("data-diplo"), action: "improve", amount: 0 }, "empire"))
        );
    }

    renderCodex() {
        if (!this.state || !this.codexEntryList) return;
        const codex = this.state.codex;
        if (!codex) {
            this.codexEntryList.innerHTML = `<div class="empty-msg">Codex telemetry offline.</div>`;
            return;
        }

        const totals = codex.totals || { entries: 0, completed: 0, claimed: 0, ready: 0, completion_pct: 0 };
        if (this.codexProgressBadge) {
            this.codexProgressBadge.textContent = `${totals.claimed} / ${totals.entries} CLAIMED (${totals.completion_pct}%)`;
        }

        if (this.codexSummaryStrip) {
            this.codexSummaryStrip.innerHTML = `
                <div class="codex-metric-card">
                    <span class="codex-metric-val">${totals.claimed}</span>
                    <span class="codex-metric-lbl">CLAIMED</span>
                </div>
                <div class="codex-metric-card">
                    <span class="codex-metric-val">${totals.completed}</span>
                    <span class="codex-metric-lbl">DISCOVERED</span>
                </div>
                <div class="codex-metric-card ${totals.ready > 0 ? "highlight-ready" : ""}">
                    <span class="codex-metric-val">${totals.ready}</span>
                    <span class="codex-metric-lbl">READY</span>
                </div>
                <div class="codex-metric-card">
                    <span class="codex-metric-val">${totals.entries}</span>
                    <span class="codex-metric-lbl">TOTAL</span>
                </div>
            `;
        }

        if (this.codexStatsGrid) {
            const stats = codex.stats || [];
            this.codexStatsGrid.innerHTML = stats.map(s => `
                <div class="codex-stat-chip">
                    <span class="codex-stat-label">${this.escapeHtml(s.label)}</span>
                    <strong class="codex-stat-value">${Number(s.value).toLocaleString()}</strong>
                </div>
            `).join("");
        }

        if (this.codexCategoryFilters) {
            const categories = codex.categories || [];
            const activeCat = this.activeCodexCategory || "all";
            const buttonsHtml = [
                `<button class="codex-cat-filter ${activeCat === "all" ? "active" : ""}" data-category="all">ALL (${totals.entries})</button>`,
                ...categories.map(c => `
                    <button class="codex-cat-filter ${activeCat === c.id ? "active" : ""}" data-category="${this.escapeHtml(c.id)}">
                        ${this.escapeHtml(c.name.toUpperCase())} (${c.claimed}/${c.entries})
                    </button>
                `)
            ].join("");
            this.codexCategoryFilters.innerHTML = buttonsHtml;
            this.codexCategoryFilters.querySelectorAll("[data-category]").forEach(btn => {
                btn.addEventListener("click", () => {
                    this.activeCodexCategory = btn.getAttribute("data-category");
                    this.renderCodex();
                });
            });
        }

        const activeCat = this.activeCodexCategory || "all";
        const entries = (codex.entries || []).filter(e => activeCat === "all" || e.category === activeCat);

        this.codexEntryList.innerHTML = entries.map(entry => {
            const pct = Math.min(100, Math.round((entry.progress / entry.target) * 100));
            const statusClass = entry.claimed ? "claimed" : (entry.ready ? "ready" : "in-progress");
            let actionHtml = "";
            if (entry.claimed) {
                actionHtml = `<span class="codex-claimed-badge">CLAIMED ${entry.claimed_date ? `// ${this.escapeHtml(entry.claimed_date)}` : ""}</span>`;
            } else if (entry.ready) {
                actionHtml = `<button class="btn-hud btn-green codex-claim-btn" data-claim-codex="${this.escapeHtml(entry.id)}">CLAIM REWARD</button>`;
            } else {
                actionHtml = `<span class="codex-progress-readout">${entry.progress} / ${entry.target}</span>`;
            }

            return `
                <div class="codex-entry ${statusClass}">
                    <div class="codex-entry-header">
                        <div class="codex-entry-title-wrap">
                            <span class="codex-entry-cat">${this.escapeHtml(entry.category.toUpperCase())}</span>
                            <h4 class="codex-entry-title">${this.escapeHtml(entry.title)}</h4>
                        </div>
                        <div class="codex-entry-rewards">
                            <span class="reward-tag">+${entry.reward_credits} CR</span>
                            <span class="reward-tag xp">+${entry.reward_xp} XP</span>
                        </div>
                    </div>
                    <p class="codex-entry-desc">${this.escapeHtml(entry.description)}</p>
                    <p class="codex-entry-hint"><span class="hint-kicker">HINT:</span> ${this.escapeHtml(entry.hint)}</p>
                    <div class="codex-entry-footer">
                        <div class="codex-progress-track">
                            <div class="codex-progress-fill" style="width: ${pct}%;"></div>
                        </div>
                        <div class="codex-entry-action">${actionHtml}</div>
                    </div>
                </div>
            `;
        }).join("");

        this.codexEntryList.querySelectorAll("[data-claim-codex]").forEach(btn => {
            btn.addEventListener("click", () => {
                const entryId = btn.getAttribute("data-claim-codex");
                this.postAction("/api/codex/claim", { entry_id: entryId }, "codex");
            });
        });

        if (this.codexLog) {
            const logs = codex.log || [];
            if (logs.length === 0) {
                this.codexLog.innerHTML = `<div class="empty-msg">No milestones claimed yet. Complete objectives across the galaxy to claim rewards.</div>`;
            } else {
                this.codexLog.innerHTML = logs.map(l => `
                    <div class="codex-log-line">
                        <span class="codex-log-date">${this.escapeHtml(l.date || "LOGGED")}</span>
                        <span class="codex-log-title">${this.escapeHtml(l.title)}</span>
                        <span class="codex-log-reward">+${l.reward_credits} CR / +${l.reward_xp} XP</span>
                    </div>
                `).join("");
            }
        }
    }

    renderFleetManager() {
        if (!this.state || !this.fleetShipRoster) return;
        const fleet = this.state.fleet_manager || {};
        const ships = fleet.ships || this.state.ship.fleet_ships || [];
        if (!ships.length) {
            this.fleetShipRoster.innerHTML = `<p class="panel-intro-text">No escort warships. Commission one below at a drydock.</p>`;
        } else {
            this.fleetShipRoster.innerHTML = ships.map(ship => `
                <div class="fleet-ship-card">
                    <div class="fleet-head"><strong>${this.escapeHtml(ship.name)}</strong> <span class="ship-role">${this.escapeHtml(ship.role.toUpperCase())}</span></div>
                    <div class="fleet-sub">HULL ${ship.hull}/${ship.max_hull} | SHIELD ${ship.shield}/${ship.max_shield} | DMG ${ship.damage}</div>
                    <div class="fleet-value">${this.escapeHtml(String(ship.status || "").toUpperCase())}</div>
                    <div class="ship-actions">
                        <button class="btn-hud btn-amber" data-escort-repair="${this.escapeHtml(ship.id)}">REPAIR</button>
                        <button class="btn-hud" data-escort-dismiss="${this.escapeHtml(ship.id)}">DISMISS</button>
                    </div>
                </div>
            `).join("");
            this.fleetShipRoster.querySelectorAll("[data-escort-repair]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/repair", { amount: 60 }, "fleet"))
            );
            this.fleetShipRoster.querySelectorAll("[data-escort-dismiss]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/dismiss", { ship_id: btn.getAttribute("data-escort-dismiss") }, "fleet"))
            );
        }
        const catalog = fleet.catalog || {};
        if (this.escortShopGrid) {
            this.escortShopGrid.innerHTML = Object.entries(catalog).map(([id, template]) => `
                <button class="btn-hud btn-amber fleet-procurement-row" data-escort-buy="${this.escapeHtml(id)}" title="${this.escapeHtml(template.description)}">
                    <span class="procurement-info"><strong>${this.escapeHtml(template.name)}</strong><small>${this.escapeHtml(template.description)}</small></span>
                    <span class="procurement-value">${template.cost} CR</span>
                    <span class="procurement-action">COMMISSION</span>
                </button>
            `).join("");
            this.escortShopGrid.querySelectorAll("[data-escort-buy]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/buy", { escort_type: btn.getAttribute("data-escort-buy") }, "fleet"))
            );
        }
    }

    renderFleet() {
        if (!this.state) return;
        this.renderFleetManager();
        this.fleetRoster.innerHTML = "";
        const drones = this.state.ship.fleet_drones || [];

        if (drones.length === 0) {
            this.fleetRoster.innerHTML = `<p class="fleet-empty">No fleet drones active. Commission a drone below to start harvesting.</p>`;
            return;
        }

        drones.forEach(d => {
            const card = document.createElement("div");
            card.className = "drone-card";

            card.innerHTML = `
                <div class="drone-meta">
                    <strong class="drone-name">${this.escapeHtml(d.name)}</strong>
                    <span class="drone-sub">${this.escapeHtml(d.drone_type.toUpperCase())} // ${this.escapeHtml(d.assigned_system_id.toUpperCase())} [${this.escapeHtml(d.status.toUpperCase())}]</span>
                </div>
                <div class="drone-stats">
                    LVL ${d.level ?? 1} // EFF ${(d.efficiency ?? 1).toFixed(2)} // INTEGRITY ${d.integrity ?? 100}% // SORTIES ${d.sorties ?? 0}${d.specialty ? " // " + this.escapeHtml(d.specialty.toUpperCase()) : ""}
                </div>
                <div class="drone-yield-badge">
                    +${d.cargo_accumulated} Ore / +${d.credits_accumulated} CR
                </div>
                <div class="drone-actions" style="display:flex;gap:5px;margin-top:6px;">
                    <button class="btn-hud" data-refit="${this.escapeHtml(d.id)}">REFIT (300 CR)</button>
                    <button class="btn-hud" data-dismiss="${this.escapeHtml(d.id)}">DISMISS</button>
                </div>
            `;
            card.querySelector("[data-refit]")?.addEventListener("click", () => this.postAction("/api/fleet/refit", { drone_id: d.id }, "fleet"));
            card.querySelector("[data-dismiss]")?.addEventListener("click", () => this.postAction("/api/fleet/dismiss", { drone_id: d.id }, "fleet"));
            this.fleetRoster.appendChild(card);
        });

        if (this.mercenaryRoster) {
            const catalog = Object.values(this.state.mercenary_catalog || {});
            const hired = new Set((this.state.ship.fleet_drones || []).filter(d => d.drone_type === "mercenary").map(d => d.specialty));
            this.mercenaryRoster.innerHTML = `<h4 class="commission-title">MERCENARY CONTRACTS</h4>` + catalog.map(m => `
                <div class="depot-card fleet-procurement-row">
                    <div class="procurement-info"><h4>${this.escapeHtml(m.name)}</h4><small>${this.escapeHtml(m.description)}</small></div>
                    <span class="procurement-value">${m.cost} CR</span>
                    <div class="depot-actions">
                        <button class="btn-hud btn-cyan" data-merc="${this.escapeHtml(m.id)}" ${hired.has(m.specialty) ? "disabled" : ""}>${hired.has(m.specialty) ? "CONTRACTED" : "HIRE"}</button>
                    </div>
                </div>
            `).join("");
            this.mercenaryRoster.querySelectorAll("[data-merc]").forEach(btn => {
                btn.addEventListener("click", () => this.postAction("/api/mercenary/hire", { merc_id: btn.getAttribute("data-merc") }, "fleet"));
            });
        }
    }

    renderContracts() {
        if (!this.state) return;
        this.contractsList.innerHTML = "";
        const contracts = this.state.ship.active_contracts || [];

        if (contracts.length === 0) {
            this.contractsList.innerHTML = `<p style="padding:12px;font-size:0.75rem;color:var(--text-muted);text-align:center;">No active bounty contracts in flight log.</p>`;
            return;
        }

        contracts.forEach(c => {
            const card = document.createElement("div");
            card.className = `contract-card ${c.completed ? 'completed' : ''}`;
            card.title = `${c.title || "Contract"} - ${c.description || ""}`;

            const pct = Math.min(100, Math.round((c.current_count / c.target_count) * 100));
            const relicBadge = c.reward_relic_tier ? `<span class="reward-pill relic">+Relic [${c.reward_relic_tier.toUpperCase()}]</span>` : '';
            const category = String(c.category || "assignment");
            const categoryCode = {
                combat: "COM", exploration: "EXP", mining: "MIN", trade: "TRD",
                pirates: "PIR", delivery: "DLV", surface: "SRF", anomaly: "ANO",
                diplomacy: "DIP", fleet: "FLT",
            }[category] || category.slice(0, 3).toUpperCase();

            card.innerHTML = `
                <div class="contract-header">
                    <span class="contract-cat-badge cat-${this.escapeHtml(category)}" title="${this.escapeHtml(category.toUpperCase())}"><span class="contract-cat-label-full">${this.escapeHtml(category)}</span><span class="contract-cat-label-short" aria-hidden="true">${this.escapeHtml(categoryCode)}</span></span>
                    <strong class="contract-title">${this.escapeHtml(c.title)}</strong>
                </div>
                <p class="contract-desc">${this.escapeHtml(c.description)}</p>
                <div class="contract-progress-box">
                    <div class="contract-progress-label">
                        <span>PROGRESS</span>
                        <span>${c.current_count} / ${c.target_count} (${pct}%)</span>
                    </div>
                    <div class="contract-progress-meter">
                        <div class="contract-progress-fill" style="width: ${pct}%;"></div>
                    </div>
                </div>
                <div class="contract-footer">
                    <div class="contract-rewards">
                        <span class="reward-pill">+${c.reward_credits.toLocaleString()} CR</span>
                        <span class="reward-pill xp">+${c.reward_xp} XP</span>
                        ${relicBadge}
                    </div>
                    ${c.completed ? `<button class="btn-claim-contract" data-id="${this.escapeHtml(c.id)}">CLAIM REWARD</button>` : `<span class="contract-status">IN PROGRESS</span>`}
                </div>
            `;

            if (c.completed) {
                card.querySelector(".btn-claim-contract").addEventListener("click", () => this.handleClaimContract(c.id));
            }

            this.contractsList.appendChild(card);
        });
    }

    renderTalentBranches(container, pointsEl) {
        if (!this.state) return;
        if (!container) return;
        const mastery = this.state.ship.mastery || { talent_points: 0, specializations: [] };
        const specs = mastery.specializations || [];
        if (pointsEl) pointsEl.textContent = String(mastery.talent_points || 0);

        const talentCatalog = this.state.catalog_talents || {
            "void_cartographer": { id: "void_cartographer", name: "Void Cartographer", category: "exploration", description: "+30% sensor scan research credits and +20% Precursor Relic resonance detection." },
            "dreadnought_tactics": { id: "dreadnought_tactics", name: "Dreadnought Tactician", category: "combat", description: "+25% tactical laser damage and +25 MW shield overcharge absorption." },
            "swarm_commander": { id: "swarm_commander", name: "Swarm Fleet Overlord", category: "fleet", description: "+50% autonomous fleet drone harvest yields across all deployed systems." },
            "quantum_smuggler": { id: "quantum_smuggler", name: "Quantum Smuggler", category: "trade", description: "-25% hyperlane jump fuel burn and +20% commodity market profit margins." }
        };
        const talents = Object.values(talentCatalog);
        const branches = {};
        talents.forEach(t => {
            const branch = t.branch || (t.category || "OTHER").toUpperCase();
            (branches[branch] = branches[branch] || []).push(t);
        });
        container.innerHTML = Object.entries(branches).map(([branch, nodes]) => `
            <div class="perk-branch">
                <h4>${this.escapeHtml(branch)}</h4>
                ${nodes.sort((a, b) => (a.tier || 1) - (b.tier || 1)).map(t => {
                    const unlocked = specs.includes(t.id);
                    const requires = t.requires || [];
                    const requiresMet = requires.every(r => specs.includes(r));
                    const canUnlock = !unlocked && requiresMet && (mastery.talent_points || 0) > 0;
                    return `<div class="perk-node ${unlocked ? "unlocked" : "locked"}">
                        <strong>${this.escapeHtml(t.name)}</strong>
                        <div>${this.escapeHtml(t.description)}</div>
                        ${unlocked ? "<div>UNLOCKED</div>" : `<button class="btn-hud" data-talent="${this.escapeHtml(t.id)}" ${canUnlock ? "" : "disabled"}>${requiresMet ? "UNLOCK" : "REQUIRES " + requires.join(", ").toUpperCase()}</button>`}
                    </div>`;
                }).join("")}
            </div>
        `).join("");
        container.querySelectorAll("[data-talent]").forEach(btn => {
            btn.addEventListener("click", () => this.handleUnlockPerk(btn.getAttribute("data-talent")));
        });
    }

    renderSkillsPerks() {
        this.renderTalentBranches(document.getElementById("skillsPerksBranches"),
            document.getElementById("skillsTalentPoints"));
    }

    renderRelics() {
        if (!this.state) return;
        if (!this.relicsGrid) return;
        const relics = this.state.ship.relics || [];
        if (!relics.length) {
            this.relicsGrid.innerHTML = `<p class="panel-intro-text">No ancient Precursor Relics recovered yet. Recover them via planet sensor sweeps, anomalies and contracts.</p>`;
            return;
        }
        this.relicsGrid.innerHTML = relics.map(r => `
            <div class="relic-card">
                <div class="relic-header-row">
                    <strong class="relic-name">${this.escapeHtml(r.name)}</strong>
                    <span class="relic-rarity-pill rarity-${this.escapeHtml(r.rarity)}">${this.escapeHtml(r.rarity)}</span>
                </div>
                <p class="relic-desc">${this.escapeHtml(r.description)}</p>
            </div>
        `).join("");
    }

    appendLog(text, type = "system") {
        const line = document.createElement("div");
        line.className = `log-line log-${type}`;
        const timeStr = new Date().toLocaleTimeString();
        line.textContent = `[${timeStr}] ${text}`;
        this.flightLogStream.appendChild(line);
        this.flightLogStream.scrollTop = this.flightLogStream.scrollHeight;
    }

    // --- Actions ---

    async handleCombat(action) {
        this.sound.init();
        const currentCombo = (this.state && this.state.ship) ? (this.state.ship.tactical_combo || 0) : 0;
        if (action === "fire_lasers") {
            if (currentCombo >= 2) {
                this.sound.playCritHit();
            } else {
                this.sound.playLaser();
            }
        } else {
            this.sound.playBeep(600);
        }

        try {
            const res = await apiFetch("/api/combat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: action })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
            } else {
                this.appendLog(`[COMBAT] ${json.message}`, "hazard");
            }
            this.state = json.state;
            this.renderHUD();
        } catch (e) {
            this.appendLog(`[ERROR] Tactical maneuver failed: ${e.message}`, "hazard");
        }
    }

    // Settings-driven automation, evaluated on every state render.
    runAlertAutomation() {
        const combatKey = this.state.active_combat ? String(this.state.active_combat.enemy_name || "hostile") : "";
        const events = this.state.undismissed_events || [];
        const firstLook = this.alertBaseline === undefined;
        const newCombat = !firstLook && combatKey && combatKey !== this.alertBaseline.combat;
        const newEvent = !firstLook && events.length > this.alertBaseline.events;
        this.alertBaseline = { combat: combatKey, events: events.length };
        const time = this.state.time;
        if (this.autoPauseOnAlert && (newCombat || newEvent) && time && !time.is_paused && !this.autoPauseInFlight) {
            this.autoPauseInFlight = true;
            this.postTimeControl("/api/time/pause", newCombat ? "hostile intercept" : "new event")
                .finally(() => { this.autoPauseInFlight = false; });
        }
        if (this.autoClaimContracts) {
            this.claimingContracts = this.claimingContracts || new Set();
            (this.state.ship.active_contracts || [])
                .filter(c => c.completed && !this.claimingContracts.has(c.id))
                .forEach(c => {
                    this.claimingContracts.add(c.id);
                    this.handleClaimContract(c.id).finally(() => this.claimingContracts.delete(c.id));
                });
        }
    }

    async postTimeControl(endpoint, reason) {
        try {
            const res = await apiFetch(endpoint, { method: "POST" });
            const json = await res.json();
            if (json.ok && json.state) {
                this.state = json.state;
                this.renderHUD();
                this.appendLog(`[TIME] Auto-paused: ${reason}. SPACE resumes.`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Auto-pause failed: ${e.message}`, "hazard");
        }
    }

    async handleClaimContract(contractId) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/contract/claim", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ contract_id: contractId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playBountyChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[CONTRACT] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Contract claim failed: ${e.message}`, "hazard");
        }
    }

    async handleBuyUpgrade(upgradeId) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/upgrade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ upgrade_id: upgradeId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Upgrade install failed: ${e.message}`, "hazard");
        }
    }

    async handleCommissionChassis(chassisId) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/shipyard/chassis", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ chassis_id: chassisId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Chassis commissioning failed: ${e.message}`, "hazard");
        }
    }

    async handleInstallWeapon(weaponId) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/weapons/install", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ weapon_id: weaponId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Weapon installation failed: ${e.message}`, "hazard");
        }
    }

    async handleSetPrimaryWeapon(weaponId) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/weapons/set", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ weapon_id: weaponId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Primary weapon configuration failed: ${e.message}`, "hazard");
        }
    }

    async handleReactorMode(mode) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/reactor/mode", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mode })
            });
            const json = await res.json();
            if (json.ok) {
                this.appendLog(json.message);
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Reactor mode change failed: ${e.message}`, "hazard");
        }
    }

    async handleReactorVent() {
        this.sound.init();
        try {
            const res = await apiFetch("/api/reactor/vent", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({})
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
            if (json.state) {
                this.state = json.state;
                this.renderHUD();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Coolant purge failed: ${e.message}`, "hazard");
        }
    }

    async handleCommissionDrone(droneType) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/drone/buy", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ drone_type: droneType })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Drone commissioning failed: ${e.message}`, "hazard");
        }
    }

    async handleHarvestFleet() {
        this.sound.init();
        try {
            const res = await apiFetch("/api/drone/collect", { method: "POST" });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[FLEET] ${json.message}`, "system");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Fleet harvest failed: ${e.message}`, "hazard");
        }
    }

    async handleToggleTimePause() {
        this.sound.init();
        this.sound.playBeep(850, 0.05);
        if (!this.state || !this.state.time) return;
        const isPaused = this.state.time.is_paused;
        const endpoint = isPaused ? "/api/time/resume" : "/api/time/pause";
        try {
            const res = await apiFetch(endpoint, { method: "POST" });
            const json = await res.json();
            if (json.ok && json.state) {
                this.state = json.state;
                this.renderHUD();
                this.appendLog(json.message, isPaused ? "system" : "hazard");
            } else if (json.message) {
                this.appendLog(`[TIME] ${json.message}`, "system");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Temporal flux error: ${e.message}`, "hazard");
        }
    }

    async handleSetTimeSpeed(speed) {
        this.sound.init();
        this.sound.playBeep(980, 0.05);
        try {
            const res = await apiFetch("/api/time/speed", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ speed })
            });
            const json = await res.json();
            if (json.ok && json.state) {
                this.state = json.state;
                this.renderHUD();
                this.appendLog(json.message, "system");
            } else if (json.message) {
                this.appendLog(`[TIME] ${json.message}`, "system");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Temporal speed error: ${e.message}`, "hazard");
        }
    }

    async handleTimeStep(ticks = 1) {
        this.sound.init();
        this.sound.playBeep(1150, 0.04);
        try {
            const res = await apiFetch("/api/time/step", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ticks })
            });
            const json = await res.json();
            if (json.ok && json.state) {
                this.state = json.state;
                this.renderHUD();
                this.appendLog(json.message, "system");
                if (json.summary) {
                    if (json.summary.shield_recharged > 0) {
                        this.appendLog(`[DEFLECTOR] Shields restored +${json.summary.shield_recharged} MW during time advance.`, "system");
                    }
                    if (json.summary.drone_cargo_harvested > 0 || json.summary.drone_credits_harvested > 0) {
                        this.appendLog(`[FLEET] Drones gathered +${json.summary.drone_cargo_harvested} ore, +${json.summary.drone_credits_harvested} cr over elapsed time.`, "reward");
                    }
                }
            } else if (json.message) {
                this.appendLog(`[TIME] ${json.message}`, "system");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Temporal step error: ${e.message}`, "hazard");
        }
    }

    async handleScan() {
        this.sound.init();
        this.sound.playScan();
        try {
            const res = await apiFetch("/api/scan", { method: "POST" });
            const json = await res.json();
            if (json.ok) {
                const discovery = json.discovery || {};
                if (discovery.relic || discovery.near_miss) {
                    this.sound.playNearMiss();
                } else {
                    this.sound.playChime();
                }
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Sensor telemetry link failed: ${e.message}`, "hazard");
        }
    }

    async handleJumpAction() {
        if (!this.selectedTarget || this.selectedType !== "system") return;
        this.sound.init();
        this.sound.playJump();
        try {
            const res = await apiFetch("/api/jump", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target: this.selectedTarget.id })
            });
            const json = await res.json();
            if (json.ok) {
                this.appendLog(json.message, "system");
                this.state = json.state;
                this.renderHUD();
                this.updateTargetCard();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Hyperspace jump aborted: ${e.message}`, "hazard");
        }
    }

    commitPowerRoute() {
        const total = [this.sliderEng, this.sliderShd, this.sliderSen, this.sliderWep]
            .reduce((sum, slider) => sum + parseInt(slider.value, 10), 0);
        // Over 100% stays local and red until the pilot rebalances.
        if (total <= 100) this.handleApplyPower();
    }

    async handleApplyPower() {
        this.sound.init();
        this.sound.playBeep(1200);
        const eng = parseInt(this.sliderEng.value, 10);
        const shd = parseInt(this.sliderShd.value, 10);
        const sen = parseInt(this.sliderSen.value, 10);
        const wep = parseInt(this.sliderWep.value, 10);

        try {
            const res = await apiFetch("/api/power", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ engines: eng, shields: shd, sensors: sen, weapons: wep })
            });
            const json = await res.json();
            if (json.ok) {
                this.appendLog(json.message, "system");
                this.state = json.state;
                this.powerDirty = false;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Power route failed: ${e.message}`, "hazard");
        }
    }

    async handleTrade(commId, qty, isBuy, useMax = false) {
        this.sound.init();
        const order = useMax
            ? { commodity_id: commId, is_buy: isBuy, max: true }
            : { commodity_id: commId, quantity: qty, is_buy: isBuy };
        try {
            const res = await apiFetch("/api/trade", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(order)
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Trade failed: ${e.message}`, "hazard");
        }
    }

    async handleResolveAnomaly(choiceId) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/anomaly", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ choice_id: choiceId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(`[RESOLVED] ${json.message}`, "reward");
            } else {
                this.appendLog(`[FAILURE] ${json.message}`, "hazard");
            }
            this.state = json.state;
            this.renderHUD();
        } catch (e) {
            this.appendLog(`[ERROR] Anomaly action failed: ${e.message}`, "hazard");
        }
    }

    async handlePirateAction(action) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/pirate/resolve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, action === "fight" ? "hazard" : "reward");
            } else {
                this.appendLog(`[BLOCKED] ${json.message}`, "hazard");
            }
            if (json.state) {
                this.state = json.state;
                this.renderHUD();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Pirate action failed: ${e.message}`, "hazard");
        }
    }

    async handleDecisionChoice(choiceId) {
        this.sound.init();
        try {
            const res = await apiFetch("/api/decision/resolve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ choice_id: choiceId })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(`[DECISION] ${json.message}`, "reward");
            } else {
                this.appendLog(`[DECISION FAILED] ${json.message}`, "hazard");
            }
            if (json.state) {
                this.state = json.state;
                this.renderHUD();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Decision action failed: ${e.message}`, "hazard");
        }
    }

    async handleRepair() {
        this.sound.init();
        this.sound.playBeep(800);
        try {
            const res = await apiFetch("/api/repair", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ amount: 25 })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Repair failed: ${e.message}`, "hazard");
        }
    }

    async handleRefuel() {
        this.sound.init();
        this.sound.playBeep(850);
        try {
            const res = await apiFetch("/api/refuel", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ amount: 20 })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound.playChime();
                this.appendLog(json.message, "reward");
                this.state = json.state;
                this.renderHUD();
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Refuel failed: ${e.message}`, "hazard");
        }
    }

    calculateBodyDistanceAu(fromBody, toBody) {
        if (!toBody) return 0;
        const ox = fromBody ? (fromBody.orbit_radius || 0) * Math.cos(fromBody.current_angle || 0) : 0;
        const oy = fromBody ? (fromBody.orbit_radius || 0) * Math.sin(fromBody.current_angle || 0) : 0;
        const tx = (toBody.orbit_radius || 0) * Math.cos(toBody.current_angle || 0);
        const ty = (toBody.orbit_radius || 0) * Math.sin(toBody.current_angle || 0);
        return Math.max(0.25, Math.hypot(tx - ox, ty - oy));
    }

    applyTransitPreviewLabels(bodyId) {
        const data = this.transitPreviewData;
        if (!data || data.body_id !== bodyId) return;
        const travel = this.state.ship?.travel;
        const inOrbit = this.state.ship?.orbiting_body_id === bodyId;
        if (travel || inOrbit) return;
        if (data.sublight?.can_start) {
            this.btnOrbitTarget.textContent = `TRANSIT & ORBIT (${data.sublight.duration_ticks}T)`;
        }
        if (data.quantum && this.btnQuantumTarget) {
            this.btnQuantumTarget.textContent = `QUANTUM (1T // ${data.quantum.fuel_cost}F)`;
            this.btnQuantumTarget.disabled = !data.quantum.can_start;
        }
    }

    async refreshTransitPreview(bodyId) {
        if (!this.transitPlan || !bodyId) return;
        const now = Date.now();
        if (this.transitPreviewBodyId === bodyId && now - this.transitPreviewAt < 1500) return;
        this.transitPreviewBodyId = bodyId;
        this.transitPreviewAt = now;
        const token = ++this.transitPreviewToken;
        try {
            const res = await apiFetch("/api/travel/preview", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ body_id: bodyId })
            });
            const json = await res.json();
            if (token !== this.transitPreviewToken || this.selectedTarget?.id !== bodyId) return;
            const sublight = json.previews?.sublight;
            const quantum = json.previews?.quantum;
            if (!json.ok || !sublight?.ok || !quantum?.ok) {
                this.transitPlan.style.display = "none";
                return;
            }
            const riskClass = risk => risk >= 0.20 ? "risk-high" : risk >= 0.10 ? "risk-mid" : "risk-low";
            const riskPct = risk => Math.max(1, Math.round(risk * 100));
            this.transitPlan.innerHTML = `
                <div class="transit-plan-title">TRANSIT PLAN</div>
                <div class="transit-plan-row">
                    <span class="transit-plan-mode">SUBLIGHT</span>
                    <span class="transit-plan-eta">${sublight.duration_ticks}T // FREE</span>
                    <span class="transit-plan-risk ${riskClass(sublight.risk)}">RISK ${riskPct(sublight.risk)}%</span>
                </div>
                <div class="transit-plan-hazard">${this.escapeHtml(sublight.hazards.join(" // ") || "CLEAR CORRIDOR")}</div>
                <div class="transit-plan-row">
                    <span class="transit-plan-mode">QUANTUM</span>
                    <span class="transit-plan-eta">${quantum.duration_ticks}T // ${quantum.fuel_cost}F</span>
                    <span class="transit-plan-risk ${riskClass(quantum.risk)}">RISK ${riskPct(quantum.risk)}%</span>
                </div>
                <div class="transit-plan-hazard">${this.escapeHtml(quantum.hazards.join(" // ") || "CLEAR CORRIDOR")}</div>
            `;
            const inOrbitNow = this.state.ship?.orbiting_body_id === bodyId;
            if (inOrbitNow) {
                this.transitPlan.style.display = "none";
                return;
            }
            this.transitPlan.style.display = "block";
            this.transitPreviewData = { body_id: bodyId, sublight, quantum };
            this.applyTransitPreviewLabels(bodyId);
        } catch (e) {
            this.transitPlan.style.display = "none";
        }
    }

    updateTargetCard() {
        if (!this.state) return;
        const travel = this.state.ship?.travel || this.state.travel || null;
        const targetCard = document.getElementById("navTargetCard");
        
        if (!this.selectedTarget) {
            // Hide target card when nothing selected
            if (targetCard) targetCard.style.display = "none";
            this.transitPreviewToken += 1;
            this.transitPreviewData = null;
            this.transitPreviewBodyId = null;
            if (this.transitPlan) {
                this.transitPlan.style.display = "none";
                this.transitPlan.innerHTML = "";
            }
            return;
        }
        
        // Show target card when target selected
        if (targetCard) targetCard.style.display = "block";

        if (this.selectedType === "body") {
            const fresh = this.state.current_system.bodies.find(b => b.id === this.selectedTarget.id);
            if (!fresh) {
                this.selectedTarget = null;
                return this.updateTargetCard();
            }
            this.selectedTarget = fresh;
            const b = this.selectedTarget;
            const orbBody = this.state.orbiting_body || (this.state.current_system?.bodies || []).find(x => x.id === this.state.ship?.orbiting_body_id) || null;
            const distAu = this.calculateBodyDistanceAu(orbBody, b);
            const engPwr = this.state.ship?.power?.engines ?? 25;
            const piloting = Number(this.state.character?.skills?.piloting ?? 1);
            const pilotingBonus = Math.max(0, piloting - 1) * 0.04;
            const engineFactor = Math.max(0.4, engPwr / 25.0) * (1.0 + pilotingBonus);
            const sublightSpeed = Math.max(0.35, 1.15 * engineFactor);
            const estTicks = Math.max(1, Math.ceil(distAu / sublightSpeed));

            this.targetType.textContent = `TARGET: ${b.body_type.toUpperCase()}`;
            this.targetName.textContent = b.name;
            this.targetDist.textContent = `${distAu.toFixed(2)} AU (ORBIT ${b.orbit_radius.toFixed(2)} AU)`;
            const survey = this.state.survey;
            const surveyNote = survey && survey.total ? ` | SURVEY ${survey.scanned}/${survey.total}` : "";
            this.targetDesc.textContent = (b.scan_completed ? b.scan_discovery : "Uncharted body. Orbital sensor sweep required.") + surveyNote;
            this.btnOrbitTarget.style.display = "inline-block";
            this.btnJumpTarget.style.display = "none";
            const inOrbitHere = (this.state.ship.orbiting_body_id === b.id && !travel);
            const inTransitHere = Boolean(travel && travel.destination_body_id === b.id);
            const hasTravel = Boolean(travel);
            const remainingTicks = travel ? Math.max(1, (travel.arrival_tick || 0) - (this.state.time?.tick || 0)) : 0;
            this.btnOrbitTarget.disabled = inOrbitHere || hasTravel;
            this.btnOrbitTarget.textContent = inOrbitHere
                ? "IN ORBIT"
                : inTransitHere
                    ? `TRANSIT ACTIVE (${remainingTicks}T)`
                    : hasTravel
                        ? "TRANSIT LOCKED"
                        : `TRANSIT & ORBIT (${estTicks}T)`;
            this.btnOrbitTarget.title = "Timed sublight transit; orbit is established on arrival.";
            if (this.btnQuantumTarget) {
                this.btnQuantumTarget.style.display = "inline-block";
                this.btnQuantumTarget.disabled = inOrbitHere || hasTravel;
                this.btnQuantumTarget.textContent = inTransitHere && travel.mode === "quantum"
                    ? "QUANTUM ACTIVE"
                    : hasTravel ? "TRANSIT LOCKED" : "QUANTUM TRANSIT (1T)";
                this.btnQuantumTarget.title = "One-tick micro-jump; costs quantum fuel.";
            }

            this.applyTransitPreviewLabels(b.id);
            this.refreshTransitPreview(b.id);

            this.targetGravity.textContent = `${(b.gravity ?? 1).toFixed(2)} g`;
            this.targetAtmosphere.textContent = b.atmosphere || "none";
            this.targetTemp.textContent = `${b.temperature_c ?? 0} C`;
            if (this.targetHabitability) {
                const hab = Number(b.habitability ?? 0);
                const habLabel = b.body_type === "star"
                    ? "STELLAR"
                    : (hab >= 75 ? "OPTIMAL" : (hab >= 45 ? "MARGINAL" : (hab >= 15 ? "HOSTILE" : "BARREN")));
                this.targetHabitability.textContent = `${hab.toFixed(1)}% (${habLabel})`;
            }
            this.targetMoons.textContent = `${(b.moons || []).length}`;
            if (this.targetFaction) this.targetFaction.textContent = b.faction || "Unclaimed";
            if (this.targetPopulation) {
                const pop = Number(b.population || 0);
                if (pop <= 0) {
                    this.targetPopulation.textContent = "Uninhabited";
                } else {
                    const tier = pop < 10000 ? "Outpost" : (pop < 1000000 ? "Colony" : (pop < 50000000 ? "Settlement" : (pop < 1000000000 ? "Metropolis" : "Mega-Ecumenopolis")));
                    this.targetPopulation.textContent = `${pop.toLocaleString("en-US")} [${tier.toUpperCase()}]`;
                }
            }
            if (this.targetGovernment) this.targetGovernment.textContent = b.government || "None";
            if (this.targetDevastation) {
                const devastation = Number(b.devastation || 0);
                this.targetDevastation.textContent = devastation > 0 ? `${devastation.toFixed(1)}%` : "None";
                this.targetDevastation.classList.toggle("is-devastated", devastation >= 25);
            }
            this.targetResources.innerHTML = (b.resources || []).map(r => `<span>${this.escapeHtml(r)}</span>`).join("");
            if (this.btnLandTarget) {
                this.btnLandTarget.style.display = b.landable ? "inline-block" : "none";
                const canLand = b.landable && this.state.ship.orbiting_body_id === b.id && this.state.ship.landed_body_id !== b.id && !travel;
                this.btnLandTarget.disabled = !canLand;
                this.btnLandTarget.textContent = this.state.ship.landed_body_id === b.id ? "LANDED" : "LAND ON SURFACE";
            }
            const salvage = inOrbitHere ? this.state.salvage_site : null;
            if (this.btnSalvageTarget) {
                this.btnSalvageTarget.style.display = salvage ? "inline-block" : "none";
                this.btnSalvageTarget.disabled = !salvage;
                this.btnSalvageTarget.textContent = salvage ? "BOARD DERELICT" : "NO DERELICT";
            }
            if (this.salvageInfo) {
                if (salvage) {
                    const risk = Math.max(5, Math.round((salvage.danger || 0) * 100));
                    this.salvageInfo.style.display = "block";
                    this.salvageInfo.textContent = `DERELICT: ${salvage.name} // RISK ~${risk}% // REWARD ${salvage.credits} CR + ${salvage.cargo_quantity}x ${salvage.cargo_item}`;
                } else {
                    this.salvageInfo.style.display = "none";
                }
            }
            const scoop = inOrbitHere && this.state.scoop ? this.state.scoop : null;
            if (this.btnScoopFuel) {
                if (!scoop) {
                    this.btnScoopFuel.style.display = "none";
                } else {
                    const depleted = scoop.tapped >= scoop.reserve;
                    this.btnScoopFuel.style.display = "inline-block";
                    this.btnScoopFuel.disabled = !scoop.available;
                    this.btnScoopFuel.title = scoop.tapped > 0
                        ? `Next volatile tap in ${scoop.next_tap_in} ticks`
                        : "";
                    this.btnScoopFuel.textContent = scoop.available
                        ? "SCOOP FUEL"
                        : depleted ? "RESERVOIR DEPLETED" : "TANKS FULL";
                }
            }
        } else if (this.selectedType === "system") {
            this.transitPreviewToken += 1;
            this.transitPreviewData = null;
            this.transitPreviewBodyId = null;
            if (this.transitPlan) {
                this.transitPlan.style.display = "none";
                this.transitPlan.innerHTML = "";
            }
            const fresh = this.galaxySystems[this.selectedTarget.id];
            if (!fresh) {
                this.selectedTarget = null;
                return this.updateTargetCard();
            }
            this.selectedTarget = fresh;
            const s = this.selectedTarget;
            const curSys = this.state.current_system;
            const isConn = curSys.connections.includes(s.id);
            const owner = ((this.state.galactic_politics || {}).systems || {})[s.id];
            const factionName = (owner && owner.owner) || s.faction;
            this.targetType.textContent = `TARGET: STAR SYSTEM [${s.spectral_type}-TYPE]`;
            this.targetName.textContent = s.name;
            const dist = Math.hypot(s.x - curSys.x, s.y - curSys.y);
            this.targetDist.textContent = `${dist.toFixed(1)} LY`;
            this.targetDesc.textContent = `Faction: ${factionName} // Security: ${(s.security * 100).toFixed(0)}% // Linked: ${isConn ? 'YES' : 'NO'}`;
            this.targetGravity.textContent = `${s.spectral_type}-class`;
            this.targetAtmosphere.textContent = `${(s.security * 100).toFixed(0)}% sec`;
            this.targetTemp.textContent = `${s.connections.length} links`;
            if (this.targetHabitability) this.targetHabitability.textContent = "--";
            this.targetMoons.textContent = factionName;
            if (this.targetFaction) this.targetFaction.textContent = factionName || "Unclaimed";
            if (this.targetPopulation) this.targetPopulation.textContent = "--";
            if (this.targetDevastation) this.targetDevastation.textContent = "--";
            if (this.targetGovernment) this.targetGovernment.textContent = "--";
            this.targetResources.innerHTML = "";
            if (this.btnLandTarget) this.btnLandTarget.style.display = "none";
            if (this.btnSalvageTarget) this.btnSalvageTarget.style.display = "none";
            if (this.btnScoopFuel) this.btnScoopFuel.style.display = "none";
            if (this.salvageInfo) this.salvageInfo.style.display = "none";
            if (this.btnQuantumTarget) this.btnQuantumTarget.style.display = "none";
            this.btnOrbitTarget.style.display = "none";
            this.btnJumpTarget.style.display = "inline-block";
            this.btnJumpTarget.disabled = (!isConn || s.id === curSys.id);
            this.btnJumpTarget.textContent = (s.id === curSys.id) ? "CURRENT LOCATION" : (isConn ? "EXECUTE HYPERSPACE JUMP" : "OUT OF HYPERLANE RANGE");
        }
    }

    // --- Canvas Radar Rendering ---

    resizeRadarCanvas() {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        const width = Math.max(320, Math.round(rect.width || window.innerWidth || 1280));
        const height = Math.max(240, Math.round(rect.height || window.innerHeight || 720));
        const dpr = Math.min(3, Math.max(1, window.devicePixelRatio || 1));
        const backingWidth = Math.round(width * dpr);
        const backingHeight = Math.round(height * dpr);
        if (this.canvas.width !== backingWidth || this.canvas.height !== backingHeight) {
            this.canvas.width = backingWidth;
            this.canvas.height = backingHeight;
        }
        this.dpr = dpr;
        this.viewW = width;
        this.viewH = height;
        this.updateMapRect();
    }

    // The canvas spans the whole viewport, but HUD panels cover its edges. Both map views
    // centre and fit inside the visible radar area (.panel-center), measured on resize only.
    updateMapRect() {
        const canvasRect = this.canvas.getBoundingClientRect();
        const view = document.querySelector(".panel-center");
        const r = view ? view.getBoundingClientRect() : canvasRect;
        const x = Math.max(0, r.left - canvasRect.left);
        const y = Math.max(0, r.top - canvasRect.top);
        this.mapRect = {
            x, y,
            w: Math.max(200, Math.min(r.width || this.viewW, this.viewW - x)),
            h: Math.max(160, Math.min(r.height || this.viewH, this.viewH - y)),
        };
    }

    mapCenter() {
        const r = this.mapRect || { x: 0, y: 0, w: this.viewW, h: this.viewH };
        return { x: r.x + r.w / 2 + this.panX, y: r.y + r.h / 2 + this.panY };
    }

    pointerToCanvas(e) {
        const rect = this.canvas.getBoundingClientRect();
        const dpr = this.dpr || 1;
        const scaleX = (this.canvas.width / Math.max(1, rect.width)) / dpr;
        const scaleY = (this.canvas.height / Math.max(1, rect.height)) / dpr;
        return {
            x: (e.clientX - rect.left) * scaleX,
            y: (e.clientY - rect.top) * scaleY,
        };
    }

    radarScale() {
        return Math.max(0.55, Math.min(2.4, Math.min(this.viewW, this.viewH) / 820));
    }

    startRenderLoop() {
        if (this.rafId !== null) return;
        const render = () => {
            if (!document.hidden) this.drawRadar();
            this.rafId = requestAnimationFrame(render);
        };
        this.rafId = requestAnimationFrame(render);
    }

    startAnimationLoop() {
        this.resizeRadarCanvas();
        window.addEventListener("resize", () => this.requestRadarResize());
        window.addEventListener("orientationchange", () => this.requestRadarResize());
        if (typeof ResizeObserver !== "undefined") {
            this.resizeObserver = new ResizeObserver(() => this.requestRadarResize());
            this.resizeObserver.observe(document.getElementById("radarBackgroundLayer") || this.canvas);
            const mapView = document.querySelector(".panel-center");
            if (mapView) this.resizeObserver.observe(mapView);
        }
        window.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                if (this.rafId !== null) cancelAnimationFrame(this.rafId);
                this.rafId = null;
            } else {
                this.startRenderLoop();
                this.refreshState(true);
            }
        });
        this.startRenderLoop();
    }

    ensureRadarBackdrop(w, h) {
        const dpr = this.dpr || 1;
        const starCount = Math.max(600, Math.round((this.starDensity || 220) * 5));
        const key = `${Math.round(w)}x${Math.round(h)}@${dpr}:${starCount}`;
        if (this.radarBackdrop && this.radarBackdropKey === key) return;
        const backdrop = document.createElement("canvas");
        backdrop.width = Math.max(1, Math.round(w * dpr));
        backdrop.height = Math.max(1, Math.round(h * dpr));
        const ctx = backdrop.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        const mapBase = ctx.createRadialGradient(w * 0.5, h * 0.45, 0,
            w * 0.5, h * 0.45, Math.max(w, h) * 0.75);
        mapBase.addColorStop(0, "rgba(21, 42, 74, 1)");
        mapBase.addColorStop(0.55, "rgba(11, 24, 45, 1)");
        mapBase.addColorStop(1, "rgba(4, 9, 19, 1)");
        ctx.fillStyle = mapBase;
        ctx.fillRect(0, 0, w, h);
        if (!this.radarStars || this.radarStars.length !== starCount) {
            this.radarStars = [];
            let seed = 1337;
            const random = () => {
                seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
                return seed / 4294967296;
            };
            for (let index = 0; index < starCount; index += 1) {
                this.radarStars.push({
                    x: random(),
                    y: random(),
                    size: 1.0 + random() * 2.6,
                    alpha: 0.42 + random() * 0.55,
                    warm: random() > 0.86,
                    bright: random() > 0.93,
                });
            }
        }
        const nebula = ctx.createRadialGradient(w * 0.72, h * 0.32, 0,
            w * 0.72, h * 0.32, Math.max(w, h) * 0.65);
        nebula.addColorStop(0, "rgba(58, 104, 160, 0.46)");
        nebula.addColorStop(0.45, "rgba(38, 64, 110, 0.24)");
        nebula.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = nebula;
        ctx.fillRect(0, 0, w, h);
        const goldHaze = ctx.createRadialGradient(w * 0.28, h * 0.7, 0,
            w * 0.28, h * 0.7, Math.max(w, h) * 0.42);
        goldHaze.addColorStop(0, "rgba(201, 163, 90, 0.10)");
        goldHaze.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = goldHaze;
        ctx.fillRect(0, 0, w, h);
        const dust = ctx.createLinearGradient(0, h * 0.1, w, h * 0.9);
        dust.addColorStop(0, "rgba(70, 110, 160, 0)");
        dust.addColorStop(0.42, "rgba(70, 110, 160, 0.12)");
        dust.addColorStop(0.66, "rgba(120, 80, 150, 0.10)");
        dust.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = dust;
        ctx.fillRect(0, 0, w, h);
        ctx.save();
        ctx.translate(w * 0.72, h * 0.3);
        ctx.rotate(-0.35);
        const galaxy = ctx.createRadialGradient(0, 0, 0, 0, 0, Math.max(w, h) * 0.16);
        galaxy.addColorStop(0, "rgba(180, 210, 240, 0.16)");
        galaxy.addColorStop(0.5, "rgba(110, 150, 190, 0.06)");
        galaxy.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = galaxy;
        ctx.beginPath();
        ctx.ellipse(0, 0, Math.max(w, h) * 0.16, Math.max(w, h) * 0.055, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
        this.radarStars.forEach(star => {
            const x = star.x * w;
            const y = star.y * h;
            if (star.bright) {
                ctx.fillStyle = star.warm
                    ? "rgba(236, 204, 142, 0.98)"
                    : "rgba(244, 249, 255, 0.98)";
                ctx.beginPath();
                ctx.arc(x, y, 1.8 + star.size, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
                ctx.fillRect(x, y, 1, 1);
            } else {
                ctx.fillStyle = star.warm
                    ? `rgba(201, 163, 90, ${star.alpha})`
                    : `rgba(233, 240, 247, ${star.alpha})`;
                ctx.fillRect(x, y, star.size, star.size);
            }
        });
        this.radarBackdrop = backdrop;
        this.radarBackdropKey = key;
    }

    drawRadar() {
        const ctx = this.ctx;
        const w = this.viewW;
        const h = this.viewH;
        ctx.setTransform(this.dpr || 1, 0, 0, this.dpr || 1, 0, 0);
        ctx.clearRect(0, 0, w, h);
        this.ensureRadarBackdrop(w, h);
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "source-over";
        ctx.drawImage(this.radarBackdrop, 0, 0, w, h);

        const { x: cx, y: cy } = this.mapCenter();

        // Draw tactical radar grid rings
        ctx.save();
        ctx.strokeStyle = "rgba(127, 183, 201, 0.08)";
        ctx.lineWidth = 1;
        for (let r = 40; r < Math.max(w, h); r += 45 * this.zoom) {
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();
        }
        ctx.restore();

        if (this.viewMode === "ORBITS") {
            this.drawOrbitsView(cx, cy);
        } else {
            this.drawGalaxyView(cx, cy);
        }
    }

    drawOrbitsView(cx, cy) {
        if (!this.state) return;
        const ctx = this.ctx;
        const curSys = this.state.current_system;
        const bodies = curSys.bodies;
        const ship = this.state.ship;
        const now = Date.now() * 0.001;

        const auScale = 45 * this.zoom * this.radarScale();

        if (this.radarGrid) {
            ctx.strokeStyle = "rgba(127, 183, 201, 0.06)";
            ctx.lineWidth = 1;
            for (let radius = 60; radius < Math.max(this.viewW, this.viewH); radius += 60) {
                ctx.beginPath();
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                ctx.stroke();
            }
            for (let x = 0; x < this.viewW; x += 60) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.viewH); ctx.stroke();
            }
            for (let y = 0; y < this.viewH; y += 60) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(this.viewW, y); ctx.stroke();
            }
        }

        bodies.forEach(b => {
            if (b.body_type === "star" && this.celestial) {
                this.celestial.drawStar(ctx, b, cx, cy, 13 * Math.max(0.8, this.zoom) * Math.min(1.6, this.radarScale()), now);
                return;
            }
            if (b.body_type === "star") {
                const pulse = 18 + Math.sin(now * 2) * 2.5;
                const grad = ctx.createRadialGradient(cx, cy, 5, cx, cy, pulse * 1.5);
                grad.addColorStop(0, "#ffffff");
                grad.addColorStop(0.3, b.color);
                grad.addColorStop(1, "transparent");

                ctx.beginPath();
                ctx.arc(cx, cy, pulse * 1.5, 0, Math.PI * 2);
                ctx.fillStyle = grad;
                ctx.fill();

                ctx.beginPath();
                ctx.arc(cx, cy, pulse * 0.7, 0, Math.PI * 2);
                ctx.fillStyle = b.color;
                ctx.fill();
                return;
            }

            // Orbital Ring: fade progressively into the black void at the edge of sensor range.
            const orbitR = b.orbit_radius * auScale;
            const fadeOuter = Math.max(this.viewW, this.viewH) * 0.72;
            if (orbitR > fadeOuter * 1.45) return;
            const orbitFade = Math.max(0.012, 0.16 * (1.0 - Math.pow(orbitR / Math.max(1, fadeOuter), 1.35)));
            ctx.beginPath();
            ctx.arc(cx, cy, orbitR, 0, Math.PI * 2);
            ctx.strokeStyle = (this.selectedTarget && this.selectedTarget.id === b.id)
                ? `rgba(127, 183, 201, ${Math.min(0.85, orbitFade * 4.0).toFixed(3)})`
                : `rgba(127, 183, 201, ${orbitFade.toFixed(3)})`;
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            // Live simulated planetary orbital angle
            const angle = b.current_angle || 0;
            const bx = cx + Math.cos(angle) * orbitR;
            const by = cy + Math.sin(angle) * orbitR;

            const bodyRadius = this.bodyDisplayRadius(b);

            if (this.celestial) {
                if (b.body_type === "asteroid_belt") {
                    this.celestial.drawAsteroidBelt(ctx, b, cx, cy, orbitR, this.zoom, now);
                    ctx.fillStyle = "rgba(200, 190, 175, 0.9)";
                    ctx.beginPath();
                    ctx.arc(bx, by, 3 * this.zoom, 0, Math.PI * 2);
                    ctx.fill();
                } else {
                    this.celestial.drawBody(ctx, b, bx, by, bodyRadius, Math.atan2(cy - by, cx - bx), now, this.dpr || 1);
                    this.celestial.drawMoons(ctx, b, bx, by, bodyRadius, now);
                }
            } else {
                ctx.beginPath();
                ctx.arc(bx, by, bodyRadius, 0, Math.PI * 2);
                ctx.fillStyle = b.color;
                ctx.fill();
            }

            if (this.celestial) {
                // The renderer draws black holes, ring worlds and the rest as full models.
            } else if (b.body_type === "black_hole") {
                ctx.beginPath();
                ctx.arc(bx, by, bodyRadius * 2.2, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(201, 163, 90,0.55)";
                ctx.lineWidth = 1.5;
                ctx.stroke();
                ctx.beginPath();
                ctx.arc(bx, by, bodyRadius * 3.0, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(180,80,255,0.25)";
                ctx.lineWidth = 1;
                ctx.stroke();
            } else if (b.body_type === "ring_world") {
                ctx.beginPath();
                ctx.ellipse(bx, by, bodyRadius * 2.5, bodyRadius * 0.6, 0.35, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(169, 139, 189,0.65)";
                ctx.lineWidth = 1.5;
                ctx.stroke();
            }

            if (this.selectedTarget && this.selectedTarget.id === b.id) {
                ctx.strokeStyle = "#7fb7c9";
                ctx.lineWidth = 1.5;
                ctx.strokeRect(bx - bodyRadius - 5, by - bodyRadius - 5, (bodyRadius + 5) * 2, (bodyRadius + 5) * 2);
            }

            const activeTravel = ship.travel || this.state.travel || null;
            if (ship.orbiting_body_id === b.id && !activeTravel && !this.travelAnimation) {
                // Parked in orbit: the flagship circles its body, nose along the orbit.
                const parkR = bodyRadius + 12 * Math.max(1, this.zoom);
                const parkA = now * 0.5;
                const sx = bx + Math.cos(parkA) * parkR;
                const sy = by + Math.sin(parkA) * parkR;
                if (this.celestial) {
                    this.celestial.drawShip(ctx, sx, sy, parkA + Math.PI / 2, 6 * Math.max(1, this.zoom));
                } else {
                    ctx.beginPath();
                    ctx.arc(sx, sy, 3.5, 0, Math.PI * 2);
                    ctx.fillStyle = "#8fbf9f";
                    ctx.fill();
                }
                ctx.font = "12px 'Share Tech Mono'";
                ctx.fillStyle = "#8fbf9f";
                ctx.fillText("VF-FLAGSHIP", bx + bodyRadius + 14, by - bodyRadius - 10);
            }

            if (this.radarLabels) {
                ctx.font = "12px 'Segoe UI'";
                ctx.fillStyle = "#ece4d4";
                const nameWidth = ctx.measureText(b.name).width;
                let nameX = bx + bodyRadius + 6;
                if (nameX + nameWidth > this.viewW - 6) nameX = bx - bodyRadius - 6 - nameWidth;
                ctx.fillText(b.name, Math.max(6, nameX), by + 3);
            }
        });

        const activeCourseTravel = ship.travel || this.state.travel || null;
        const originBody = bodies.find(b => b.id === ship.orbiting_body_id);
        const targetBody = this.selectedTarget && this.selectedType === "body"
            ? bodies.find(b => b.id === this.selectedTarget.id)
            : null;
        if (!activeCourseTravel && originBody && targetBody && targetBody.id !== originBody.id) {
            const fromAngle = originBody.current_angle || 0;
            const toAngle = targetBody.current_angle || 0;
            const fromX = cx + Math.cos(fromAngle) * originBody.orbit_radius * auScale;
            const fromY = cy + Math.sin(fromAngle) * originBody.orbit_radius * auScale;
            const toX = cx + Math.cos(toAngle) * targetBody.orbit_radius * auScale;
            const toY = cy + Math.sin(toAngle) * targetBody.orbit_radius * auScale;
            ctx.save();
            ctx.setLineDash([6, 6]);
            ctx.strokeStyle = "rgba(111, 195, 215, 0.5)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(fromX, fromY);
            ctx.lineTo(toX, toY);
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.font = "10px 'Segoe UI'";
            ctx.fillStyle = "rgba(236, 228, 212, 0.68)";
            ctx.fillText("COURSE PLOT", (fromX + toX) / 2 + 6, (fromY + toY) / 2 - 6);
            ctx.restore();
        }

        this.drawTravelAnimation(ctx, cx, cy, auScale);
    }

    // Display size is logarithmic in real radius: an Earth ~14px, a gas giant ~22px at 1x,
    // so every world is big enough to show its surface model. Drawing and hit tests share it.
    bodyDisplayRadius(b) {
        const sizeLog = Math.log2(Math.max(1, (b.radius_km || 1000) / 1000));
        return Math.max(6, Math.min(22, 6 + sizeLog * 3)) * this.zoom * Math.min(1.4, this.radarScale());
    }

    galaxyTransform(cx, cy) {
        const systems = Object.values(this.galaxySystems);
        const nodeScale = this.radarScale();
        if (!systems.length) {
            return { scale: 8.0 * this.zoom * nodeScale, cx, cy, nodeScale };
        }
        const xs = systems.map(s => s.x);
        const ys = systems.map(s => s.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        const view = this.mapRect || { w: this.viewW, h: this.viewH };
        // Short map areas keep a legend row along the bottom edge; fit above it.
        const usableH = view.h < 360 ? view.h - 34 : view.h;
        const scale = Math.min(
            (view.w * 0.8) / Math.max(1, maxX - minX),
            (usableH * 0.72) / Math.max(1, maxY - minY)
        ) * this.zoom;
        return {
            scale,
            cx: cx - ((minX + maxX) / 2) * scale,
            cy: cy - (view.h - usableH) / 2 - ((minY + maxY) / 2) * scale,
            nodeScale,
        };
    }

    drawGalaxyView(cx, cy) {
        if (!this.state) return;
        const ctx = this.ctx;
        const curSys = this.state.current_system;
        const systems = Object.values(this.galaxySystems);
        if (!systems.length) return;

        const transform = this.galaxyTransform(cx, cy);
        const scale = transform.scale;
        const gx = transform.cx;
        const gy = transform.cy;
        const nodeScale = transform.nodeScale;
        const politics = this.state.galactic_politics || { systems: {}, factions: [], wars: [] };
        const owners = politics.systems || {};
        const at = s => [gx + s.x * scale, gy + s.y * scale];

        this.drawTerritory(ctx, transform, systems, owners);
        // Crowded maps (720p, zoomed out) label only what matters; the rest show on hover.
        const gaps = systems.map(a => Math.min(...systems.filter(b => b !== a)
            .map(b => Math.hypot((a.x - b.x) * scale, (a.y - b.y) * scale))));
        gaps.sort((m, n) => m - n);
        const crowded = (gaps[Math.floor(gaps.length / 2)] || 999) < 90 * nodeScale;
        const hoveredId = this.hoveredItem && this.hoveredItem.id;

        // Hyperlanes: quiet inside a realm, brighter where they cross a border.
        const drawnPairs = new Set();
        ctx.lineWidth = Math.max(1, nodeScale * 0.8);
        systems.forEach(s1 => {
            const [x1, y1] = at(s1);
            s1.connections.forEach(connId => {
                const pairKey = [s1.id, connId].sort().join("-");
                const s2 = this.galaxySystems[connId];
                if (drawnPairs.has(pairKey) || !s2) return;
                drawnPairs.add(pairKey);
                const [x2, y2] = at(s2);
                const crossing = (owners[s1.id] || {}).owner_id !== (owners[connId] || {}).owner_id;
                ctx.strokeStyle = crossing ? "rgba(236, 228, 212, 0.42)" : "rgba(111, 195, 215, 0.28)";
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            });
        });

        // War fronts: contested lanes pulse red.
        const pulse = 0.55 + 0.35 * Math.sin(Date.now() * 0.004);
        ctx.save();
        ctx.setLineDash([7 * nodeScale, 5 * nodeScale]);
        ctx.lineWidth = Math.max(2, 2.4 * nodeScale);
        ctx.strokeStyle = `rgba(214, 96, 77, ${pulse.toFixed(3)})`;
        (politics.wars || []).forEach(war => (war.fronts || []).forEach(([a, b]) => {
            const sa = this.galaxySystems[a];
            const sb = this.galaxySystems[b];
            if (!sa || !sb) return;
            const [x1, y1] = at(sa);
            const [x2, y2] = at(sb);
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();
        }));
        ctx.restore();

        systems.forEach(s => {
            const [sx, sy] = at(s);
            const owner = owners[s.id] || {};
            const isCurrent = (s.id === curSys.id);
            const isSelected = (this.selectedTarget && this.selectedTarget.id === s.id);
            const radius = (isCurrent ? 9 : 7) * nodeScale;

            this.drawStarGlyph(ctx, sx, sy, radius, s.color || "#6fc3d7");
            // Owner ring: whose system this is, readable even where territories overlap.
            ctx.beginPath();
            ctx.arc(sx, sy, radius + 4 * nodeScale, 0, Math.PI * 2);
            ctx.strokeStyle = owner.color || "#7f8a99";
            ctx.lineWidth = 2 * nodeScale;
            ctx.stroke();
            if (owner.front) {
                ctx.font = `${Math.round(12 * nodeScale)}px 'Segoe UI Symbol', 'Segoe UI'`;
                ctx.fillStyle = "#e07a66";
                ctx.fillText("⚔", sx - radius - 16 * nodeScale, sy - radius - 2 * nodeScale);
            }
            if (isCurrent) {
                ctx.beginPath();
                ctx.arc(sx, sy, radius + 10 * nodeScale, 0, Math.PI * 2);
                ctx.strokeStyle = "#8fbf9f";
                ctx.lineWidth = 1.5 * nodeScale;
                ctx.setLineDash([3 * nodeScale, 3 * nodeScale]);
                ctx.stroke();
                ctx.setLineDash([]);
            }
            if (isSelected) {
                ctx.strokeStyle = "#6fc3d7";
                ctx.lineWidth = 2 * nodeScale;
                const box = radius + 8 * nodeScale;
                ctx.strokeRect(sx - box, sy - box, box * 2, box * 2);
            }

            if (crowded && !isCurrent && !isSelected && !owner.front && s.id !== hoveredId) return;
            const fontSize = Math.max(12, 13 * nodeScale);
            ctx.font = `${fontSize}px 'Segoe UI'`;
            const label = s.name;
            const labelWidth = ctx.measureText(label).width;
            const lx = sx + radius + 9 * nodeScale;
            ctx.fillStyle = "rgba(4, 9, 19, 0.78)";
            ctx.fillRect(lx - 4 * nodeScale, sy - 11 * nodeScale, labelWidth + 8 * nodeScale, 18 * nodeScale);
            ctx.fillStyle = owner.color || "#7f8a99";
            ctx.fillRect(lx - 4 * nodeScale, sy - 11 * nodeScale, 2 * nodeScale, 18 * nodeScale);
            ctx.fillStyle = isCurrent ? "#8fbf9f" : "#ece4d4";
            ctx.fillText(label, lx, sy + 4 * nodeScale);
        });

        this.drawPoliticsLegend(ctx, politics);
    }

    drawStarGlyph(ctx, x, y, radius, color) {
        const glow = ctx.createRadialGradient(x, y, 0, x, y, radius * 2.4);
        glow.addColorStop(0, "rgba(255, 255, 255, 0.95)");
        glow.addColorStop(0.28, color);
        glow.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(x, y, radius * 2.4, 0, Math.PI * 2);
        ctx.fill();
    }

    // Stellaris-style realms: each canvas cell belongs to the nearest system within reach,
    // filled faintly in its owner's colour, with a bright line where ownership changes.
    // Rendered at quarter resolution into an offscreen canvas and redrawn only when the
    // view or the map of owners changes.
    drawTerritory(ctx, transform, systems, owners) {
        const key = [
            this.viewW, this.viewH, transform.scale.toFixed(4),
            systems.map(s => `${s.id}:${(owners[s.id] || {}).owner_id || ""}`).join(","),
        ].join("|");
        const drift = Math.hypot(transform.cx - this.territoryCx, transform.cy - this.territoryCy);
        if (this.territoryKey !== key || !(drift < this.viewW * 0.35)) {
            this.territoryCanvas = this.renderTerritory(transform, systems, owners);
            this.territoryKey = key;
            this.territoryCx = transform.cx;
            this.territoryCy = transform.cy;
        }
        if (this.territoryCanvas) {
            ctx.save();
            ctx.imageSmoothingEnabled = true;
            ctx.drawImage(this.territoryCanvas, transform.cx - this.territoryCx,
                transform.cy - this.territoryCy, this.viewW, this.viewH);
            ctx.restore();
        }
    }

    renderTerritory(transform, systems, owners) {
        // ~480 cells across at any resolution keeps a rebuild (every pan/zoom frame) cheap.
        const cell = Math.max(4, Math.round(this.viewW / 480));
        const cw = Math.ceil(this.viewW / cell);
        const ch = Math.ceil(this.viewH / cell);
        const ownerIds = [];
        const points = systems.map(s => {
            const owner = owners[s.id] || {};
            let idx = ownerIds.indexOf(owner.owner_id);
            if (idx < 0) { ownerIds.push(owner.owner_id); idx = ownerIds.length - 1; }
            const hex = /^#[0-9a-fA-F]{6}$/.test(owner.color || "") ? owner.color : "#7f8a99";
            return {
                x: (transform.cx + s.x * transform.scale) / cell,
                y: (transform.cy + s.y * transform.scale) / cell,
                owner: idx,
                rgb: [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)),
            };
        });
        if (!points.length) return null;
        // A realm reaches a little past half the typical gap to the nearest neighbour.
        const gaps = points.map(p => Math.min(...points.filter(q => q !== p).map(q => Math.hypot(p.x - q.x, p.y - q.y))));
        gaps.sort((a, b) => a - b);
        const reach = Math.max(6, (gaps[Math.floor(gaps.length / 2)] || 20) * 0.9);
        const reach2 = reach * reach;

        const owner = new Int16Array(cw * ch).fill(-1);
        const nearest = new Int16Array(cw * ch).fill(-1);
        const depth = new Float32Array(cw * ch);
        for (let y = 0; y < ch; y++) {
            for (let x = 0; x < cw; x++) {
                let best = -1;
                let bestD = reach2;
                for (let i = 0; i < points.length; i++) {
                    const dx = points[i].x - x;
                    const dy = points[i].y - y;
                    const d = dx * dx + dy * dy;
                    if (d < bestD) { bestD = d; best = i; }
                }
                if (best >= 0) {
                    const at = y * cw + x;
                    nearest[at] = best;
                    owner[at] = points[best].owner;
                    depth[at] = 1 - Math.sqrt(bestD) / reach;
                }
            }
        }

        const canvas = document.createElement("canvas");
        canvas.width = cw;
        canvas.height = ch;
        const tctx = canvas.getContext("2d");
        const image = tctx.createImageData(cw, ch);
        const data = image.data;
        for (let y = 0; y < ch; y++) {
            for (let x = 0; x < cw; x++) {
                const at = y * cw + x;
                const o = owner[at];
                if (o < 0) continue;
                const rgb = points[nearest[at]].rgb;
                const edge = (x > 0 && owner[at - 1] !== o) || (x < cw - 1 && owner[at + 1] !== o)
                    || (y > 0 && owner[at - cw] !== o) || (y < ch - 1 && owner[at + cw] !== o);
                const p = at * 4;
                data[p] = rgb[0];
                data[p + 1] = rgb[1];
                data[p + 2] = rgb[2];
                // Interior: a faint wash that thickens toward the border; border: a solid line.
                data[p + 3] = edge ? 200 : Math.round(26 + 34 * (1 - depth[at]));
            }
        }
        tctx.putImageData(image, 0, 0);
        // Upscale once with a light blur so cell steps become smooth borders; frames then
        // only blit this cached layer.
        // The blurred layer is capped at 1920px wide: blurring a full 4K canvas costs more than
        // the rest of the rebuild, and the per-frame blit stretches it invisibly.
        const layerScale = Math.min(1, 1920 / this.viewW);
        const smooth = document.createElement("canvas");
        smooth.width = Math.round(this.viewW * layerScale);
        smooth.height = Math.round(this.viewH * layerScale);
        const sctx = smooth.getContext("2d");
        sctx.imageSmoothingEnabled = true;
        sctx.imageSmoothingQuality = "high";
        sctx.filter = "blur(1.2px)";
        sctx.drawImage(canvas, 0, 0, smooth.width, smooth.height);
        return smooth;
    }

    drawPoliticsLegend(ctx, politics) {
        const factions = politics.factions || [];
        if (!factions.length) return;
        const r = this.mapRect || { x: 0, y: 0, w: this.viewW, h: this.viewH };
        if (r.h < 360) {
            this.drawPoliticsLegendRow(ctx, factions, r);
            return;
        }
        const rowH = 18;
        const width = 230;
        const height = 26 + factions.length * rowH;
        const x = r.x + 12;
        const y = r.y + r.h - height - 12;
        ctx.save();
        ctx.fillStyle = "rgba(5, 11, 22, 0.82)";
        ctx.fillRect(x, y, width, height);
        ctx.strokeStyle = "rgba(201, 163, 90, 0.35)";
        ctx.strokeRect(x + 0.5, y + 0.5, width - 1, height - 1);
        ctx.font = "12px 'Segoe UI'";
        ctx.fillStyle = "#c9a35a";
        ctx.fillText("GALACTIC POWERS", x + 10, y + 17);
        factions.forEach((f, i) => {
            const ry = y + 26 + i * rowH;
            ctx.fillStyle = f.color;
            ctx.fillRect(x + 10, ry + 3, 10, 10);
            ctx.fillStyle = "#ece4d4";
            ctx.fillText(f.name, x + 28, ry + 12);
            ctx.fillStyle = (f.at_war_with || []).length ? "#e07a66" : "#9fb2c6";
            const tag = `${(f.at_war_with || []).length ? "⚔ " : ""}${f.systems}`;
            ctx.fillText(tag, x + width - 10 - ctx.measureText(tag).width, ry + 12);
        });
        ctx.restore();
    }

    // Short map areas (720p, laptop): one row of swatch, first name word and system count.
    drawPoliticsLegendRow(ctx, factions, r) {
        ctx.save();
        ctx.font = "12px 'Segoe UI'";
        const items = factions.map(f => ({
            f,
            text: `${f.name.split(" ")[0]} ${(f.at_war_with || []).length ? "⚔" : ""}${f.systems}`,
        }));
        const width = items.reduce((sum, item) => sum + 22 + ctx.measureText(item.text).width + 18, 12);
        const x = r.x + 10;
        const y = r.y + r.h - 28;
        ctx.fillStyle = "rgba(5, 11, 22, 0.82)";
        ctx.fillRect(x, y, width, 22);
        let cursor = x + 8;
        items.forEach(({ f, text }) => {
            ctx.fillStyle = f.color;
            ctx.fillRect(cursor, y + 6, 10, 10);
            ctx.fillStyle = (f.at_war_with || []).length ? "#e07a66" : "#ece4d4";
            ctx.fillText(text, cursor + 14, y + 15);
            cursor += 22 + ctx.measureText(text).width + 18;
        });
        ctx.restore();
    }

    handleCanvasMouseMove(e) {
        const point = this.pointerToCanvas(e);
        const mx = point.x;
        const my = point.y;
        const { x: cx, y: cy } = this.mapCenter();

        let hit = null;

        if (this.viewMode === "ORBITS" && this.state) {
            const auScale = 45 * this.zoom * this.radarScale();
            for (const b of this.state.current_system.bodies) {
                if (b.body_type === "star") continue;
                const orbitR = b.orbit_radius * auScale;
                const angle = b.current_angle || 0;
                const bx = cx + Math.cos(angle) * orbitR;
                const by = cy + Math.sin(angle) * orbitR;
                const dist = Math.hypot(mx - bx, my - by);
                if (dist < Math.max(18, this.bodyDisplayRadius(b) + 4)) {
                    hit = { item: b, type: "body" };
                    break;
                }
            }
        } else if (this.viewMode === "GALAXY") {
            const transform = this.galaxyTransform(cx, cy);
            const hitRadius = 18 * Math.max(1, transform.nodeScale);
            for (const s of Object.values(this.galaxySystems)) {
                const sx = transform.cx + s.x * transform.scale;
                const sy = transform.cy + s.y * transform.scale;
                if (Math.hypot(mx - sx, my - sy) < hitRadius) {
                    hit = { item: s, type: "system" };
                    break;
                }
            }
        }

        this.canvas.style.cursor = hit ? "pointer" : "crosshair";
        this.hoveredItem = hit ? hit.item : null;
    }

    handleCanvasClick(e) {
        if (this.suppressClick) {
            this.suppressClick = false;
            return;
        }
        if (this.isDragging) return;
        const point = this.pointerToCanvas(e);
        const mx = point.x;
        const my = point.y;
        const { x: cx, y: cy } = this.mapCenter();
        let hit = false;

        if (this.viewMode === "ORBITS" && this.state) {
            const auScale = 45 * this.zoom * this.radarScale();
            for (const b of this.state.current_system.bodies) {
                if (b.body_type === "star") continue;
                const orbitR = b.orbit_radius * auScale;
                const angle = b.current_angle || 0;
                const bx = cx + Math.cos(angle) * orbitR;
                const by = cy + Math.sin(angle) * orbitR;
                if (Math.hypot(mx - bx, my - by) < Math.max(18, this.bodyDisplayRadius(b) + 4)) {
                    this.selectedTarget = b;
                    this.selectedType = "body";
                    this.sound.playBeep(1000);
                    this.updateTargetCard();
                    hit = true;
                    return;
                }
            }
        } else if (this.viewMode === "GALAXY") {
            const transform = this.galaxyTransform(cx, cy);
            const hitRadius = 18 * Math.max(1, transform.nodeScale);
            for (const s of Object.values(this.galaxySystems)) {
                const sx = transform.cx + s.x * transform.scale;
                const sy = transform.cy + s.y * transform.scale;
                if (Math.hypot(mx - sx, my - sy) < hitRadius) {
                    this.selectedTarget = s;
                    this.selectedType = "system";
                    this.sound.playBeep(1000);
                    this.updateTargetCard();
                    hit = true;
                    return;
                }
            }
        }

        // Clicked on empty space - clear target
        if (!hit) {
            this.selectedTarget = null;
            this.selectedType = null;
            this.updateTargetCard();
        }
    }
    // Outposts the orbited world can host, each with its cost and yield.
    renderOutpostBuild() {
        const host = document.getElementById("outpostBuild");
        if (!host) return;
        const body = this.state.orbiting_body;
        if (!body) {
            host.innerHTML = `<p class="panel-intro-text">Orbit a world to survey outpost sites.</p>`;
            return;
        }
        if (this.state.outpost_body_occupied) {
            host.innerHTML = `<p class="panel-intro-text">${this.escapeHtml(body.name)} already hosts an outpost. Upgrade it from the list above.</p>`;
            return;
        }
        const allowed = new Set(this.state.outpost_options || []);
        const options = (this.state.outpost_catalog || []).filter(t => allowed.has(t.id));
        if (!options.length) {
            host.innerHTML = `<p class="panel-intro-text">${this.escapeHtml(body.name)} cannot host an outpost.</p>`;
            return;
        }
        const credits = this.state.ship.credits;
        host.innerHTML = `<h4 class="commission-title">FOUND AN OUTPOST AT ${this.escapeHtml(body.name.toUpperCase())}</h4>` + options.map(t => {
            const yields = Object.entries(t.production || {}).map(([k, v]) => `+${v} ${k}`).join(" · ");
            return `
                <button class="btn-hud fleet-procurement-row" data-outpost-build="${this.escapeHtml(t.id)}" ${credits < t.cost ? "disabled" : ""}
                    title="${this.escapeHtml(t.description)}">
                    <span class="procurement-info"><strong>${this.escapeHtml(t.name)}</strong><small>${this.escapeHtml(yields)} per tick</small></span>
                    <span class="procurement-value">${t.cost} CR</span>
                    <span class="procurement-action">BUILD</span>
                </button>`;
        }).join("");
        host.querySelectorAll("[data-outpost-build]").forEach(btn => btn.addEventListener("click", () =>
            this.postAction("/api/outpost/build", { body_id: body.id, outpost_type: btn.getAttribute("data-outpost-build") }, "empire")
        ));
    }

    // Active wars as tug-of-war bars: attacker on the left, defender on the right.
    renderWars() {
        const host = document.getElementById("warsList");
        if (!host) return;
        const wars = (this.state.galactic_politics || {}).wars || [];
        if (!wars.length) {
            host.innerHTML = `<p class="panel-intro-text">The galaxy is at peace. For now.</p>`;
            return;
        }
        const colors = {};
        ((this.state.galactic_politics || {}).factions || []).forEach(f => { colors[f.id] = this.safeColor(f.color); });
        const affordable = this.state.ship.credits >= 500;
        host.innerHTML = wars.map(w => {
            const lead = Math.max(-1, Math.min(1, w.war_score / 24));
            const attackerShare = Math.round(50 + lead * 50);
            const captured = (w.captured_systems || []).length;
            const pledge = id => (w.support || {})[id] || 0;
            return `
                <div class="war-card">
                    <div class="war-sides">
                        <strong style="color:${colors[w.attacker_id] || "#ece4d4"}">${this.escapeHtml(w.attacker)}</strong>
                        <span class="war-vs">VS</span>
                        <strong style="color:${colors[w.defender_id] || "#ece4d4"}">${this.escapeHtml(w.defender)}</strong>
                    </div>
                    <div class="war-bar" title="War score ${w.war_score.toFixed(1)}: a side captures a front system at 12">
                        <span style="width:${attackerShare}%;background:${colors[w.attacker_id] || "#c9a35a"}"></span>
                        <span style="width:${100 - attackerShare}%;background:${colors[w.defender_id] || "#7fb7c9"}"></span>
                    </div>
                    <div class="war-meta">${(w.fronts || []).length} front lane(s) · ${captured} system(s) taken · since tick ${w.started_tick}</div>
                    <div class="war-actions">
                        <button class="btn-hud" data-war="${this.escapeHtml(w.id)}" data-side="${this.escapeHtml(w.attacker_id)}" ${affordable ? "" : "disabled"} title="${affordable ? "Pledge 500 cr to this side" : "Needs 500 cr to pledge support"}">BACK ${this.escapeHtml(w.attacker.split(" ")[0].toUpperCase())} / 500</button>
                        <button class="btn-hud" data-war="${this.escapeHtml(w.id)}" data-side="${this.escapeHtml(w.defender_id)}" ${affordable ? "" : "disabled"} title="${affordable ? "Pledge 500 cr to this side" : "Needs 500 cr to pledge support"}">BACK ${this.escapeHtml(w.defender.split(" ")[0].toUpperCase())} / 500</button>
                    </div>
                    ${pledge(w.attacker_id) || pledge(w.defender_id) ? `<div class="war-meta">Your pledges: ${pledge(w.attacker_id)} / ${pledge(w.defender_id)} cr</div>` : ""}
                </div>`;
        }).join("");
        host.querySelectorAll("[data-war]").forEach(btn => btn.addEventListener("click", () =>
            this.postAction("/api/war/support", {
                war_id: btn.getAttribute("data-war"), faction_id: btn.getAttribute("data-side"), credits: 500,
            }, "factions")
        ));
    }

    renderFactions() {
        if (!this.state) return;
        this.renderWars();
        if (!this.state.factions || !this.factionsGrid) return;

        this.factionsGrid.innerHTML = "";
        Object.entries(this.state.factions).forEach(([fid, f]) => {
            const card = document.createElement("div");
            card.className = "faction-card";
            const factionColor = this.safeColor(f.primary_color);
            card.style.borderColor = `${factionColor}44`;
            const tierClass = `tier-${this.escapeHtml(f.standing_tier.toLowerCase())}`;
            const barPct = Math.max(0, Math.min(100, Math.round(((f.standing + 100) / 200) * 100)));

            card.innerHTML = `
                <div class="faction-top-row">
                    <span class="faction-name" style="color: ${factionColor};">${this.escapeHtml(f.name)}</span>
                    <span class="standing-badge ${tierClass}">${this.escapeHtml(f.standing_tier.toUpperCase())} (${f.standing > 0 ? "+" : ""}${f.standing})</span>
                </div>
                <div class="faction-ideology">Ideology: ${this.escapeHtml(f.ideology)} // HQ: ${this.escapeHtml(f.headquarters_system.toUpperCase())}</div>
                <div class="standing-bar-wrap">
                    <div class="standing-bar-fill" style="width: ${barPct}%; background: ${factionColor};"></div>
                </div>
                <div class="faction-perk">Diplomatic Status: <strong>${this.escapeHtml(f.active_perk)}</strong></div>
            `;
            this.factionsGrid.appendChild(card);
        });

        if (!this.state.corporations || !this.corpsGrid) return;

        this.corpsGrid.innerHTML = "";
        Object.entries(this.state.corporations).forEach(([cid, c]) => {
            const card = document.createElement("div");
            card.className = "corp-card";
            const commTitle = this.escapeHtml(c.specialty_commodity.replace('_', ' ').toUpperCase());
            const barPct = Math.max(0, Math.min(100, Math.round(((c.standing + 100) / 200) * 100)));

            card.innerHTML = `
                <div class="corp-top-row">
                    <span class="corp-name">${this.escapeHtml(c.name)}</span>
                    <span class="standing-badge tier-friendly">STANDING: ${c.standing > 0 ? "+" : ""}${c.standing}</span>
                </div>
                <div class="corp-desc">HQ: ${this.escapeHtml(c.headquarters_system.toUpperCase())} // Commercial Specialty: <strong style="color: var(--neon-cyan);">${commTitle}</strong> (+${Math.round(c.bonus_trade_margin * 100)}% Sale Profit)</div>
                <div class="standing-bar-wrap">
                    <div class="standing-bar-fill" style="width: ${barPct}%; background: #ffd700;"></div>
                </div>
                <div class="corp-perk">Sponsorship Benefit: <strong>${this.escapeHtml(c.corporate_perk)}</strong></div>
            `;
            this.corpsGrid.appendChild(card);
        });
    }
    escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, ch => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        }[ch]));
    }

    safeColor(value, fallback = "#7fb7c9") {
        return /^#[0-9a-fA-F]{6}$/.test(String(value || "")) ? value : fallback;
    }

    loadSettings() {
        let saved = {};
        try {
            saved = JSON.parse(localStorage.getItem("voidfarer_settings") || "{}") || {};
        } catch (e) {}
        this.applySettingsProfile({ ...SETTINGS_DEFAULTS, ...saved });
        if (!this.sound.enabled) {
            const audioIcon = document.getElementById("audioIcon");
            if (audioIcon) audioIcon.textContent = "MUTED";
        }
    }

    applySettingsProfile(profile) {
        const volume = Number(profile.volume);
        this.sound.enabled = profile.sound !== false;
        this.sound.setVolume(Number.isFinite(volume) ? volume : SETTINGS_DEFAULTS.volume);
        this.radarGrid = profile.radarGrid !== false;
        this.radarLabels = profile.radarLabels !== false;
        this.travelAnimationEnabled = profile.travelAnimation !== false;
        this.starDensity = Number(profile.starDensity) || SETTINGS_DEFAULTS.starDensity;
        this.uiDensity = profile.uiDensity || SETTINGS_DEFAULTS.uiDensity;
        this.uiScale = Number(profile.uiScale) || SETTINGS_DEFAULTS.uiScale;
        this.rememberTerminalTab = profile.rememberTab !== false;
        this.lastTerminalTab = TERMINAL_TABS.includes(profile.lastTab) ? profile.lastTab : "player";
        this.tradeLot = TRADE_LOTS.includes(String(profile.tradeLot)) ? String(profile.tradeLot) : "1";
        this.autoPauseOnAlert = profile.autoPause !== false;
        this.autoClaimContracts = profile.autoClaim === true;
    }

    saveSettings() {
        const payload = {
            sound: this.sound.enabled,
            volume: this.sound.volume,
            radarGrid: this.radarGrid,
            radarLabels: this.radarLabels,
            travelAnimation: this.travelAnimationEnabled,
            starDensity: this.starDensity,
            uiDensity: this.uiDensity,
            uiScale: this.uiScale,
            rememberTab: this.rememberTerminalTab,
            lastTab: this.lastTerminalTab,
            tradeLot: this.tradeLot,
            autoPause: this.autoPauseOnAlert,
            autoClaim: this.autoClaimContracts,
        };
        try { localStorage.setItem("voidfarer_settings", JSON.stringify(payload)); } catch (e) {}
    }

    applySettingsFromUI() {
        this.sound.enabled = document.getElementById("settingSound")?.checked !== false;
        this.sound.setVolume(Number(document.getElementById("settingVolume")?.value ?? 80) / 100);
        this.radarGrid = document.getElementById("settingGrid")?.checked !== false;
        this.radarLabels = document.getElementById("settingLabels")?.checked !== false;
        this.syncRadarControlState();
        this.drawRadar();
        this.travelAnimationEnabled = document.getElementById("settingAnimation")?.checked !== false;
        this.starDensity = Number(document.getElementById("settingStarDensity")?.value || 220);
        this.uiDensity = document.getElementById("settingDensity")?.value || "auto";
        this.uiScale = Number(document.getElementById("settingUiScale")?.value || 100) / 100;
        this.rememberTerminalTab = document.getElementById("settingRememberTab")?.checked !== false;
        this.autoPauseOnAlert = document.getElementById("settingAutoPause")?.checked !== false;
        this.autoClaimContracts = document.getElementById("settingAutoClaim")?.checked === true;
        const lot = document.getElementById("settingTradeLot")?.value;
        this.tradeLot = TRADE_LOTS.includes(lot) ? lot : "1";
        const volumeValue = document.getElementById("settingVolumeValue");
        if (volumeValue) volumeValue.textContent = `${Math.round(this.sound.volume * 100)}%`;
        const audioIcon = document.getElementById("audioIcon");
        if (audioIcon) audioIcon.textContent = this.sound.enabled ? "SFX" : "MUTED";
        this.applyViewportProfile();
        this.renderMarketTable();
        this.saveSettings();
    }

    resetSettings() {
        this.applySettingsProfile({ ...SETTINGS_DEFAULTS });
        this.populateSettingsForm();
        this.applySettingsFromUI();
        this.appendLog("[SYS] Settings restored to defaults.", "system");
    }

    populateSettingsForm() {
        const toggles = {
            settingSound: this.sound.enabled,
            settingGrid: this.radarGrid,
            settingLabels: this.radarLabels,
            settingAnimation: this.travelAnimationEnabled,
            settingRememberTab: this.rememberTerminalTab,
            settingAutoPause: this.autoPauseOnAlert,
            settingAutoClaim: this.autoClaimContracts,
        };
        Object.entries(toggles).forEach(([id, checked]) => {
            const input = document.getElementById(id);
            if (input) input.checked = checked;
        });
        const fields = {
            settingVolume: Math.round(this.sound.volume * 100),
            settingStarDensity: this.starDensity,
            settingDensity: this.uiDensity,
            settingUiScale: Math.round((this.uiScale || 1) * 100),
            settingTradeLot: this.tradeLot,
        };
        Object.entries(fields).forEach(([id, value]) => {
            const input = document.getElementById(id);
            if (input) input.value = value;
        });
        const volumeValue = document.getElementById("settingVolumeValue");
        if (volumeValue) volumeValue.textContent = `${fields.settingVolume}%`;
    }

    openSettings() {
        this.populateSettingsForm();
        this.applyViewportProfile();
        const overlay = document.getElementById("settingsOverlay");
        if (overlay) overlay.style.display = "flex";
        const settingsContent = document.querySelector(".settings-content");
        if (settingsContent) settingsContent.scrollTop = 0;
        document.querySelectorAll(".settings-nav-item").forEach((item, index) => {
            item.classList.toggle("active", index === 0);
        });
    }

    closeSettings() {
        const overlay = document.getElementById("settingsOverlay");
        if (overlay) overlay.style.display = "none";
    }

    toggleMainMenu() {
        const overlay = document.getElementById("mainMenuOverlay");
        if (!overlay) return;
        if (overlay.classList.contains("hidden")) {
            this.openMainMenu();
        } else {
            this.closeMainMenu();
        }
    }

    openMainMenu() {
        const overlay = document.getElementById("mainMenuOverlay");
        if (overlay) overlay.classList.remove("hidden");
        this.fetchSaves();
        this.sound.playBeep(760, 0.04);
    }

    closeMainMenu() {
        const overlay = document.getElementById("mainMenuOverlay");
        if (overlay) overlay.classList.add("hidden");
        this.sound.playBeep(640, 0.04);
    }

    initTooltips() {
        if (this.tooltipBound) return;
        const tooltip = document.getElementById("hudTooltip");
        if (!tooltip) return;
        this.tooltipBound = true;
        this.tooltipTarget = null;
        this.tooltipTimer = null;
        const hide = () => {
            clearTimeout(this.tooltipTimer);
            if (this.tooltipTarget) this.tooltipTarget.removeAttribute("aria-describedby");
            this.tooltipTarget = null;
            tooltip.classList.remove("visible");
            tooltip.setAttribute("aria-hidden", "true");
        };
        const show = (target) => {
            const text = target.getAttribute("data-tooltip") || target.getAttribute("title");
            if (!text) return;
            if (!target.hasAttribute("data-tooltip")) {
                target.setAttribute("data-tooltip", text);
                target.removeAttribute("title");
            }
            if (!target.getAttribute("aria-label")) target.setAttribute("aria-label", text);
            this.tooltipTarget = target;
            target.setAttribute("aria-describedby", "hudTooltip");
            tooltip.textContent = text;
            tooltip.setAttribute("aria-hidden", "false");
            tooltip.classList.add("visible");
            const rect = target.getBoundingClientRect();
            const box = tooltip.getBoundingClientRect();
            const left = Math.max(8, Math.min(rect.left + rect.width / 2 - box.width / 2,
                window.innerWidth - box.width - 8));
            const above = rect.top - box.height - 10;
            const below = Math.min(rect.bottom + 10, window.innerHeight - box.height - 8);
            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${above >= 8 ? above : below}px`;
        };
        const schedule = (target, delay) => {
            clearTimeout(this.tooltipTimer);
            this.tooltipTimer = setTimeout(() => show(target), delay);
        };
        const find = (event) => event.target instanceof Element
            ? event.target.closest("[data-tooltip], [title]") : null;
        document.addEventListener("mouseover", (event) => {
            const target = find(event);
            if (!target || target === this.tooltipTarget) return;
            hide();
            schedule(target, 350);
        });
        document.addEventListener("mouseout", (event) => {
            const target = find(event);
            if (target && event.relatedTarget && target.contains(event.relatedTarget)) return;
            hide();
        });
        document.addEventListener("focusin", (event) => {
            const target = find(event);
            if (target) schedule(target, 120);
        });
        document.addEventListener("focusout", hide);
        window.addEventListener("scroll", hide, true);
        document.addEventListener("click", hide);
    }

    getSelectedSaveSlot() {
        const input = document.getElementById("saveSlotInput");
        const raw = (input ? input.value : this.activeSaveSlot) || "default";
        const cleaned = raw.trim().replace(/[^A-Za-z0-9_-]/g, "");
        return cleaned || "default";
    }

    setSelectedSaveSlot(slot, syncInput = true) {
        const cleaned = String(slot || "default").trim().replace(/[^A-Za-z0-9_-]/g, "") || "default";
        this.activeSaveSlot = cleaned;
        const input = document.getElementById("saveSlotInput");
        if (syncInput && input) input.value = cleaned;
        document.querySelectorAll("#saveSlotPresets .slot-pill").forEach(btn => {
            btn.classList.toggle("active", btn.getAttribute("data-slot") === cleaned);
        });
        this.renderSaveSlots();
    }

    async fetchSaves() {
        try {
            const res = await apiFetch("/api/saves");
            const json = await res.json();
            if (json.ok && Array.isArray(json.saves)) {
                this.savesList = json.saves;
                this.renderSaveSlots();
            }
        } catch (e) {}
    }

    renderSaveSlots() {
        const listEl = document.getElementById("saveSlotsList");
        if (!listEl) return;
        const active = this.getSelectedSaveSlot();
        if (!Array.isArray(this.savesList) || this.savesList.length === 0) {
            listEl.innerHTML = `<div class="save-slot-empty">No saved slots on disk yet. Select a slot and click SAVE TO SLOT.</div>`;
            return;
        }
        listEl.innerHTML = "";
        this.savesList.forEach(s => {
            const row = document.createElement("div");
            row.className = `save-slot-item${s.slot === active ? " active" : ""}`;
            row.innerHTML = `
                <div class="save-slot-info">
                    <strong>[${this.escapeHtml(s.slot)}]</strong> ${this.escapeHtml(s.commander_name)} // ${this.escapeHtml(s.ship_class)}
                    <small>${this.escapeHtml(s.current_system_id.toUpperCase())} | DATE ${this.escapeHtml(s.stardate)} (TICK #${Number(s.tick || 0)}) | ${Number(s.credits || 0).toLocaleString()} CR</small>
                </div>
                <div class="save-slot-actions">
                    <button type="button" class="btn-slot-act" data-act="load">LOAD</button>
                    <button type="button" class="btn-slot-act" data-act="save">SAVE</button>
                    <button type="button" class="btn-slot-act danger" data-act="delete">DEL</button>
                </div>
            `;
            row.querySelector(".save-slot-info")?.addEventListener("click", () => {
                this.setSelectedSaveSlot(s.slot, true);
            });
            row.querySelector('[data-act="load"]')?.addEventListener("click", () => {
                this.setSelectedSaveSlot(s.slot, true);
                this.menuAction("/api/load", "Game loaded.", s.slot);
            });
            row.querySelector('[data-act="save"]')?.addEventListener("click", () => {
                this.setSelectedSaveSlot(s.slot, true);
                this.menuAction("/api/save", "Game saved.", s.slot);
            });
            row.querySelector('[data-act="delete"]')?.addEventListener("click", () => {
                this.setSelectedSaveSlot(s.slot, true);
                if (window.confirm(`Delete save slot '${s.slot}' permanently?`)) {
                    this.menuAction("/api/delete-save", "Save deleted.", s.slot);
                }
            });
            listEl.appendChild(row);
        });
    }

    async menuAction(endpoint, successMessage, slotOverride = null) {
        const status = document.getElementById("mainMenuStatus");
        const slot = slotOverride || this.getSelectedSaveSlot();
        if (status) status.textContent = "TRANSMITTING...";
        try {
            const res = await apiFetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ slot }),
            });
            const json = await res.json();
            if (json.state) {
                this.state = json.state;
                this.renderHUD();
            }
            if (Array.isArray(json.saves)) {
                this.savesList = json.saves;
                this.renderSaveSlots();
            } else {
                this.fetchSaves();
            }
            if (status) status.textContent = (json.ok ? "OK: " : "ERROR: ") + (json.message || successMessage);
            if (json.ok && ["/api/load", "/api/new-game"].includes(endpoint)) {
                this.closeMainMenu();
                this.viewMode = "ORBITS";
                this.selectedTarget = null;
                this.gameStarted = true;
                this.fetchGalaxy();
            }
            if (json.ok) this.sound.playChime();
        } catch (e) {
            if (status) status.textContent = `ERROR: ${e.message}`;
        }
    }

    async handleUnlockPerk(talentId) {
        try {
            const res = await apiFetch("/api/mastery/unlock", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ talent_id: talentId }),
            });
            const json = await res.json();
            if (json.ok) {
                this.state = json.state;
                this.renderHUD();
                this.renderSkills();
                this.sound.playChime();
                this.appendLog(json.message, "reward");
            } else {
                this.appendLog(`[ERROR] ${json.message}`, "hazard");
            }
        } catch (e) {
            this.appendLog(`[ERROR] Perk unlock failed: ${e.message}`, "hazard");
        }
    }

    renderQuests() {
        if (!this.state) return;
        const quests = this.state.quests || [];
        const completed = this.state.quests_completed || [];

        // Active quests
        if (this.questsList) {
            this.questsList.innerHTML = quests.length ? quests.map(q => {
                const pct = q.target_count > 0 ? Math.min(100, Math.round((q.progress / q.target_count) * 100)) : 0;
                return `<div class="quest-card">
                    <h4>${this.escapeHtml(q.title)}</h4>
                    <div>${this.escapeHtml(q.description)}</div>
                    <div>TYPE: ${this.escapeHtml(q.kind.toUpperCase())} // REWARD: ${this.escapeHtml(q.reward)}</div>
                    <div class="quest-progress"><div style="width:${pct}%"></div></div>
                    <div>${q.progress}/${q.target_count} ${q.completed ? "// COMPLETE" : ""}</div>
                </div>`;
            }).join("") : '<div class="quest-card">No active quests.</div>';
        }

        // Completed quests
        if (this.questsCompletedList) {
            this.questsCompletedList.innerHTML = completed.length ? completed.map(q => {
                const rewards = q.rewards || {};
                return `<div class="quest-completed-card">
                    <div class="quest-completed-header">
                        <span class="quest-completed-name">${this.escapeHtml(q.title)}</span>
                        <span class="quest-completed-date">${this.formatDate(q.completed_at)}</span>
                    </div>
                    <div class="quest-completed-rewards">
                        ${rewards.credits ? `<span class="quest-completed-reward credits">${rewards.credits} CR</span>` : ''}
                        ${rewards.xp ? `<span class="quest-completed-reward xp">${rewards.xp} XP</span>` : ''}
                        ${rewards.relic ? `<span class="quest-completed-reward relic">${this.escapeHtml(rewards.relic)}</span>` : ''}
                    </div>
                </div>`;
            }).join("") : '<div class="quest-card">No completed quests yet.</div>';
        }
    }

    formatDate(timestamp) {
        if (!timestamp) return "Unknown";
        const date = new Date(timestamp);
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
    }

    renderAICaptains() {
        if (!this.state || !this.aiList) return;
        const captains = this.state.ai_captains || [];
        this.aiList.innerHTML = captains.map(c => `
            <div class="ai-card">
                <h4>${this.escapeHtml(c.name)} <small>[${this.escapeHtml(c.archetype.toUpperCase())}]</small></h4>
                <div>${this.escapeHtml(c.description)}</div>
                <div>SYSTEM: ${this.escapeHtml(c.system_id)} // TRUST: ${c.trust} // STANDING: ${c.standing}</div>
                <div>CARGO: ${Object.entries(c.cargo || {}).map(([k, v]) => `${this.escapeHtml(k)} x${v}`).join(", ") || "empty"}</div>
                <div class="ai-actions">
                    <button class="btn-hud" data-captain="${this.escapeHtml(c.id)}" data-action="hail">HAIL</button>
                    <button class="btn-hud" data-captain="${this.escapeHtml(c.id)}" data-action="buy">BUY FUEL</button>
                    <button class="btn-hud" data-captain="${this.escapeHtml(c.id)}" data-action="sell">SELL FUEL</button>
                    ${c.archetype === "mercenary" ? `<button class="btn-hud btn-cyan" data-captain="${this.escapeHtml(c.id)}" data-action="hire" ${c.hired ? "disabled" : ""}>HIRE</button>` : ""}
                    <button class="btn-hud btn-green" data-captain="${this.escapeHtml(c.id)}" data-action="ally" ${c.ally ? "disabled" : ""}>ALLY</button>
                </div>
            </div>
        `).join("") || '<div class="ai-card">No AI captains in range.</div>';
        this.aiList.querySelectorAll("[data-captain]").forEach(btn => {
            btn.addEventListener("click", () => this.handleAIAction(btn.getAttribute("data-captain"), btn.getAttribute("data-action")));
        });
    }

    async handleAIAction(captainId, action) {
        await this.postAction("/api/ai/interact", { captain_id: captainId, action, commodity_id: "fuel_cells", quantity: 1 }, "ai");
    }

    renderDepots() {
        if (!this.state || !this.depotList) return;
        const sysId = this.state.current_system?.id;
        const depot = (this.state.depots || []).find(d => d.system_id === sysId);
        if (!depot) {
            this.depotSummary.textContent = "No depot registered in this system.";
            this.depotList.innerHTML = "";
            return;
        }
        const used = Number.isFinite(depot.used_volume)
            ? depot.used_volume
            : Object.values(depot.cargo || {}).reduce((a, b) => a + b, 0);
        this.depotSummary.textContent = `${depot.name} // STORED VOLUME: ${used}/${depot.capacity}`;
        const depotRows = Object.entries(depot.cargo || {}).map(([item, qty]) => `
            <div class="depot-card">
                <h4>${this.escapeHtml(item)} x${qty}</h4>
                <div class="depot-actions">
                    <button class="btn-hud" data-action="withdraw" data-qty="1" data-item="${this.escapeHtml(item)}">WITHDRAW 1</button>
                    ${qty > 1 ? `<button class="btn-hud" data-action="withdraw" data-qty="${qty}" data-item="${this.escapeHtml(item)}">WITHDRAW ALL</button>` : ""}
                    <button class="btn-hud btn-green" data-action="sell" data-qty="1" data-item="${this.escapeHtml(item)}">SELL 1</button>
                    ${qty > 1 ? `<button class="btn-hud btn-green" data-action="sell" data-qty="${qty}" data-item="${this.escapeHtml(item)}">SELL ALL</button>` : ""}
                </div>
            </div>
        `).join("");
        const shipRows = (this.state.inventory_manifest || []).map(item => {
            const itemQty = item.total_quantity || item.quantity || 0;
            return `
            <div class="depot-card">
                <h4>HOLD: ${this.escapeHtml(item.name || item.id)} x${itemQty}</h4>
                <div class="depot-actions">
                    <button class="btn-hud" data-action="deposit" data-qty="1" data-item="${this.escapeHtml(item.id)}">DEPOSIT 1</button>
                    ${itemQty > 1 ? `<button class="btn-hud" data-action="deposit" data-qty="${itemQty}" data-item="${this.escapeHtml(item.id)}">DEPOSIT ALL</button>` : ""}
                </div>
            </div>
            `;
        }).join("");
        this.depotList.innerHTML = depotRows + shipRows || '<div class="depot-card">Depot and hold are empty.</div>';
        this.depotList.querySelectorAll("[data-action]").forEach(btn => {
            btn.addEventListener("click", () => this.handleDepotAction(
                btn.getAttribute("data-action"),
                btn.getAttribute("data-item"),
                parseInt(btn.getAttribute("data-qty") || "1", 10)
            ));
        });
    }

    async handleDepotAction(action, itemId, quantity = 1) {
        await this.postAction(`/api/depot/${action}`, { item_id: itemId, quantity: quantity }, "depot");
    }

    renderMessages() {
        if (!this.state || !this.messageList) return;
        const messages = this.state.messages || [];
        this.messageList.innerHTML = messages.slice().reverse().map(m => {
            const choices = (m.choices || []).map(choice => `
                <button class="message-choice-btn" data-msg-choice="${this.escapeHtml(choice.id)}" data-msg-id="${this.escapeHtml(m.id)}"
                    ${m.resolved_choice ? "disabled" : ""}>
                    <strong>${this.escapeHtml(choice.label)}</strong>
                    <span>${this.escapeHtml(choice.description || "")}</span>
                </button>
            `).join("");
            return `
                <div class="message-card ${m.read ? "" : "unread"}">
                    <h4>${this.escapeHtml(m.subject)}</h4>
                    <div>FROM: ${this.escapeHtml(m.sender)} // TO: ${this.escapeHtml(m.recipient)} // TICK ${m.tick}
                        ${m.tree_id ? ` // TREE ${this.escapeHtml(m.tree_id)}` : ""}${m.resolved_choice ? ` // RESOLVED: ${this.escapeHtml(m.resolved_choice)}` : ""}</div>
                    <div>${this.escapeHtml(m.body)}</div>
                    ${choices ? `<div class="message-choices">${choices}</div>` : ""}
                    ${m.read ? "" : `<button class="btn-hud" data-message="${this.escapeHtml(m.id)}">MARK READ</button>`}
                </div>
            `;
        }).join("") || '<div class="message-card">Inbox is empty.</div>';
        this.messageList.querySelectorAll("[data-message]").forEach(btn => {
            btn.addEventListener("click", () => this.postAction("/api/messages/read", { message_id: btn.getAttribute("data-message") }, "messages"));
        });
        this.messageList.querySelectorAll("[data-msg-choice]").forEach(btn => {
            btn.addEventListener("click", () => this.postAction("/api/messages/choose", {
                message_id: btn.getAttribute("data-msg-id"),
                choice_id: btn.getAttribute("data-msg-choice"),
            }, "messages"));
        });
        const unread = messages.filter(m => !m.read).length;
        if (this.messagesBadge) {
            this.messagesBadge.textContent = String(unread);
            this.messagesBadge.style.display = unread > 0 ? "inline-block" : "none";
        }
    }

    async handleLandAction() {
        if (!this.selectedTarget || this.selectedType !== "body") return;
        await this.postAction("/api/land", { target: this.selectedTarget.id });
    }

    async handleSalvage() {
        this.sound.init();
        const res = await this.postAction("/api/salvage", {});
        if (res && res.ok) {
            this.sound.playBountyChime();
            this.updateTargetCard();
        }
    }

    async handleScoop() {
        this.sound.init();
        const res = await this.postAction("/api/scoop", {});
        if (res && res.ok) {
            this.sound.playBeep(620, 0.18, "sawtooth");
            this.updateTargetCard();
        }
    }

    async handleTravelAction(mode = "sublight") {
        if (!this.selectedTarget || this.selectedType !== "body") return;
        const fromId = this.state?.ship?.orbiting_body_id || null;
        const targetId = this.selectedTarget.id;
        const res = await this.postAction("/api/travel", { body_id: targetId, mode });
        if (res && res.ok) {
            const activeTravel = this.state?.ship?.travel || this.state?.travel || null;
            this.startTravelAnimation(fromId, targetId, activeTravel);
        }
    }

    renderEventPopups() {
        if (!this.eventPopupContainer || !this.state) return;
        const events = this.state.undismissed_events || (this.state.events || []).filter(e => !e.dismissed);
        if (!events || events.length === 0) {
            this.eventPopupContainer.style.display = "none";
            this.eventPopupContainer.innerHTML = "";
            return;
        }
        this.eventPopupContainer.style.display = "flex";
        this.eventPopupContainer.innerHTML = events.slice(-3).map(evt => `
            <div class="event-popup-card">
                <div class="event-popup-body">
                    <div class="event-popup-meta">[${this.escapeHtml(String(evt.kind || "system").toUpperCase())} // TICK #${Number(evt.tick || 0)}]</div>
                    <strong class="event-popup-title">${this.escapeHtml(evt.title || "")}</strong>
                    <div class="event-popup-message">${this.escapeHtml(evt.message || "")}</div>
                </div>
                <button class="btn-hud btn-cyan" data-dismiss-event="${this.escapeHtml(evt.id)}">DISMISS</button>
            </div>
        `).join("");
        this.eventPopupContainer.querySelectorAll("[data-dismiss-event]").forEach(btn => {
            btn.addEventListener("click", () => {
                this.postAction("/api/events/dismiss", { event_id: btn.dataset.dismissEvent });
            });
        });
    }

    startTravelAnimation(fromBodyId, toBodyId, travelState = null) {
        if (!this.travelAnimationEnabled || !this.state) return;
        const bodies = this.state.current_system?.bodies || [];
        const activeTravel = travelState || this.state.ship?.travel || this.state.travel || null;
        const origId = activeTravel?.origin_body_id || fromBodyId;
        const destId = activeTravel?.destination_body_id || toBodyId;
        const from = bodies.find(b => b.id === origId);
        const to = bodies.find(b => b.id === destId);
        if (!to) return;
        const speed = Math.max(0.25, this.state.time?.speed || 1.0);
        const totalTicks = activeTravel
            ? Math.max(1, activeTravel.duration_ticks || (activeTravel.arrival_tick - activeTravel.started_tick) || 1)
            : 1;
        this.travelAnimation = {
            fromBodyId: origId,
            toBodyId: destId,
            fromAngle: from ? (from.current_angle || 0) : 0,
            fromRadius: from ? from.orbit_radius : 0,
            toAngle: to.current_angle || 0,
            toRadius: to.orbit_radius,
            startedTick: activeTravel ? activeTravel.started_tick : (this.state.time?.tick || 0),
            arrivalTick: activeTravel ? activeTravel.arrival_tick : ((this.state.time?.tick || 0) + 1),
            totalTicks: totalTicks,
            distanceAu: activeTravel ? activeTravel.distance_au : this.calculateBodyDistanceAu(from, to),
            mode: activeTravel ? activeTravel.mode : "orbit",
            isTickSynced: Boolean(activeTravel),
            start: performance.now(),
            lastTickSync: performance.now(),
            lastSeenTick: this.state.time?.tick || 0,
            visualProgress: 0,
            completionStart: null,
            duration: activeTravel ? (totalTicks * 1000) / (speed * TICKS_PER_SECOND) : 1300,
        };
    }

    drawTravelAnimation(ctx, cx, cy, auScale) {
        const activeTravel = this.state?.ship?.travel || this.state?.travel || null;
        if (this.travelAnimationEnabled && activeTravel) {
            if (!this.travelAnimation || this.travelAnimation.toBodyId !== activeTravel.destination_body_id) {
                this.startTravelAnimation(activeTravel.origin_body_id, activeTravel.destination_body_id, activeTravel);
            }
        }
        if (!this.travelAnimation) return;
        const anim = this.travelAnimation;
        const bodies = this.state?.current_system?.bodies || [];
        const liveFrom = bodies.find(b => b.id === anim.fromBodyId);
        const liveTo = bodies.find(b => b.id === anim.toBodyId);
        if (liveFrom) {
            anim.fromAngle = liveFrom.current_angle || 0;
            anim.fromRadius = liveFrom.orbit_radius || 0;
        }
        if (liveTo) {
            anim.toAngle = liveTo.current_angle || 0;
            anim.toRadius = liveTo.orbit_radius || 0;
        }

        let progress = 0;
        if (anim.isTickSynced && activeTravel) {
            const curTick = this.state?.time?.tick ?? anim.startedTick;
            if (curTick !== anim.lastSeenTick) {
                anim.lastSeenTick = curTick;
                anim.lastTickSync = performance.now();
            }
            const elapsedTicks = Math.max(0, curTick - anim.startedTick);
            const speed = Math.max(0.25, this.state?.time?.speed || 1.0);
            const subTick = this.state?.time?.is_paused
                ? 0
                : Math.min(0.98, ((performance.now() - anim.lastTickSync) / 1000) * speed * TICKS_PER_SECOND);
            const targetProgress = Math.min(0.97, Math.max(0, (elapsedTicks + subTick) / Math.max(1, anim.totalTicks)));
            anim.visualProgress = Math.max(
                anim.visualProgress || 0,
                (anim.visualProgress || 0) + (targetProgress - (anim.visualProgress || 0)) * 0.2
            );
            progress = anim.visualProgress;
        } else if (anim.isTickSynced && !activeTravel) {
            if (!anim.completionStart) {
                anim.completionStart = performance.now();
                anim.completionFrom = anim.visualProgress || 0.85;
            }
            const finishRatio = Math.min(1, (performance.now() - anim.completionStart) / 420);
            progress = anim.completionFrom + (1 - anim.completionFrom) * finishRatio;
        } else {
            progress = Math.min(1, (performance.now() - anim.start) / anim.duration);
        }

        const eased = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;
        const ox = cx + Math.cos(anim.fromAngle) * (anim.fromRadius * auScale);
        const oy = cy + Math.sin(anim.fromAngle) * (anim.fromRadius * auScale);
        const tx = cx + Math.cos(anim.toAngle) * (anim.toRadius * auScale);
        const ty = cy + Math.sin(anim.toAngle) * (anim.toRadius * auScale);
        const x = ox + (tx - ox) * eased;
        const y = oy + (ty - oy) * eased;

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(tx, ty);
        ctx.strokeStyle = "rgba(127, 183, 201, 0.45)";
        ctx.lineWidth = 1.25;
        ctx.setLineDash([5, 4]);
        ctx.stroke();
        ctx.setLineDash([]);

        if (this.celestial) {
            this.celestial.drawShip(ctx, x, y, Math.atan2(ty - oy, tx - ox), 9 * Math.max(1, this.zoom), "#7fb7c9");
        } else {
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fillStyle = "#7fb7c9";
            ctx.fill();
        }
        ctx.font = "12px 'Share Tech Mono'";
        ctx.fillStyle = "#7fb7c9";
        if (activeTravel) {
            const remTicks = Math.max(1, (activeTravel.arrival_tick || anim.arrivalTick) - (this.state?.time?.tick || 0));
            const remAu = Math.max(0.05, (anim.distanceAu || 1.0) * (1 - eased)).toFixed(2);
            ctx.fillText(`VF-TRANSIT [${(anim.mode || "sublight").toUpperCase()}] // ${remAu} AU // ETA ${remTicks}T`, x + 8, y - 8);
        } else {
            ctx.fillText("VF-TRANSIT", x + 8, y - 8);
        }
        ctx.restore();

        if (!activeTravel && progress >= 1) {
            this.travelAnimation = null;
        }
    }

    async postAction(endpoint, payload, refreshTab = null) {
        try {
            const res = await apiFetch(endpoint, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const json = await res.json();
            if (json.ok) {
                this.appendLog(json.message, "system");
                this.state = json.state;
                this.renderHUD();
                if (refreshTab && this.activeRightTab === refreshTab) {
                    if (refreshTab === "ai") this.renderAICaptains();
                    if (refreshTab === "depot") this.renderDepots();
                    if (refreshTab === "messages") this.renderMessages();
                }
                this.sound.playBeep(980, 0.05);
            } else {
                this.reportProblem(json.message);
            }
            return json;
        } catch (e) {
            this.reportProblem(e.message);
            return { ok: false, message: e.message };
        }
    }

    reportProblem(message) {
        this.appendLog(`[ERROR] ${message}`, "hazard");
        if (this.logPanel) {
            this.logPanel.classList.remove("log-collapsed");
            if (this.btnToggleLog) {
                this.btnToggleLog.textContent = "HIDE";
                this.btnToggleLog.setAttribute("aria-expanded", "true");
            }
        }
    }
}

// Instantiate on load
window.addEventListener("DOMContentLoaded", () => {
    window.cockpit = new CockpitApp();
});
