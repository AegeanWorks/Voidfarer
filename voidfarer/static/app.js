/**
 * VOIDFARER // Tactical Cockpit & Autonomous Galaxy Simulator
 * Master Web Client: Canvas Radar, Procedural Web Audio Synth, Fleet/Arsenal Controller, and REST Link.
 */

const TICKS_PER_SECOND = 2.0;
// A paused, empty cockpit still needs orbit and star motion, but not 60 full redraws/s.
const IDLE_FRAME_MS = 1000 / 30;

// Must match voidfarer/demographics.py DEVASTATION_CAPACITY_LOSS.
const DEVASTATION_CAPACITY_LOSS = 0.65;
// Must match SimulationEngine.RECONSTRUCTION_CREDIT_COST / RELIEF_CARGO.
const RECONSTRUCTION_CREDIT_COST = 600;
const RELIEF_CARGO = [["medicines", 2], ["hydroponics", 2], ["fuel_cells", 1]];

const BODY_TYPE_LABELS = {
    dyson_sphere: "DYSON SWARM",
    ring_world: "RING WORLD",
    orbital_station: "ORBITAL STATION",
    research_outpost: "RESEARCH OUTPOST",
    quantum_relay: "QUANTUM RELAY",
    solar_collector: "SOLAR COLLECTOR",
    desert_world: "DESERT WORLD",
    ice_world: "ICE WORLD",
    lava_world: "LAVA WORLD",
    gas_giant: "GAS GIANT",
    ringed_giant: "RINGED GIANT",
    ice_giant: "ICE GIANT",
    methane_storm: "METHANE STORM",
    super_earth: "SUPER-EARTH",
    asteroid_belt: "ASTEROID BELT",
    black_hole: "BLACK HOLE",
    wormhole: "WORMHOLE",
    terrestrial: "TERRESTRIAL",
    savanna: "SAVANNA",
    tundra: "TUNDRA",
    oceanic: "OCEANIC",
    barren: "BARREN",
    toxic: "TOXIC",
    volcanic: "VOLCANIC",
    star: "STAR",
};

const SKILL_META = {
    piloting: { name: "Piloting", icon: "✈", desc: "Improves sublight maneuverability, warp efficiency, and evasion." },
    engineering: { name: "Engineering", icon: "⚙", desc: "Boosts repair speed, shield recharge, and module efficiency." },
    science: { name: "Science", icon: "⌬", desc: "Increases scan range, research speed, and anomaly rewards." },
    combat: { name: "Combat", icon: "⚔", desc: "Enhances weapon damage, targeting, and combat abilities." },
    diplomacy: { name: "Diplomacy", icon: "⚖", desc: "Improves standing gains, trade prices, and crew morale." },
    trade: { name: "Trade", icon: "¤", desc: "Increases cargo capacity, buy/sell margins, and depot efficiency." }
};
const SKILL_HOTKEYS = ["⇧1", "⇧2", "⇧3", "⇧4", "⇧5", "⇧6"];
// Activatable commander powers, in hotkey order (SHIFT+1..6).
const ABILITY_ORDER = ["overclock", "emergency_repair", "battle_focus", "charm_offensive", "science_burst", "trade_instinct"];
const ABILITY_META = {
    overclock: { icon: "↯", name: "Reactor Overclock", label: "Overclock" },
    emergency_repair: { icon: "✚", name: "Emergency Repair", label: "Repair" },
    battle_focus: { icon: "◎", name: "Battle Focus", label: "Battle Focus" },
    charm_offensive: { icon: "⚖", name: "Diplomatic Offensive", label: "Diplomacy" },
    science_burst: { icon: "⌬", name: "Science Burst", label: "Science" },
    trade_instinct: { icon: "¤", name: "Trade Instinct", label: "Trade" },
};
const ABILITY_UNLOCK_RANK = { charm_offensive: 7, trade_instinct: 7 };
const ROOM_LAYOUTS = {
    standard: [
        ["bridge", "BRIDGE", "FLIGHT", "◆"],
        ["reactor", "REACTOR", "POWER", "◎"],
        ["medbay", "MEDBAY", "RECOVERY", "✚"],
        ["crew", "CREW DECK", "QUARTERS", "◇"],
        ["cargo", "CARGO", "LOGISTICS", "▣"],
        ["sensor", "SENSORIUM", "SCIENCE", "⌬"],
    ],
    freighter: [
        ["bridge", "BRIDGE", "FLIGHT", "◆"],
        ["cargo", "CARGO HOLD", "LOGISTICS", "▣"],
        ["cargo_b", "CARGO HOLD B", "LOGISTICS", "▣"],
        ["reactor", "REACTOR", "POWER", "◎"],
        ["crew", "CREW DECK", "QUARTERS", "◇"],
        ["dock", "DOCKING BAY", "TRANSFER", "⊞"],
    ],
    fighter: [
        ["cockpit", "COCKPIT", "FLIGHT", "◆"],
        ["reactor", "REACTOR", "POWER", "◎"],
        ["weapons", "WEAPONS", "TACTICAL", "⊕"],
        ["medbay", "MEDBAY", "RECOVERY", "✚"],
    ],
    explorer: [
        ["bridge", "BRIDGE", "FLIGHT", "◆"],
        ["sensor", "SENSORIUM", "SCIENCE", "⌬"],
        ["lab", "FIELD LAB", "RESEARCH", "⌘"],
        ["reactor", "REACTOR", "POWER", "◎"],
        ["crew", "CREW DECK", "QUARTERS", "◇"],
        ["airlock", "AIRLOCK", "AWAY TEAM", "△"],
    ],
    stealth: [
        ["cockpit", "COCKPIT", "FLIGHT", "◆"],
        ["reactor", "REACTOR", "POWER", "◎"],
        ["ghost", "GHOST BAY", "COVERT", "◇"],
        ["sensor", "PASSIVE SENSORS", "SCIENCE", "⌬"],
    ],
};
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
                this.master.gain.value = this.enabled ? this.volume : 0;
                this.master.connect(this.ctx.destination);
            }
        }
        if (this.ctx && this.ctx.state === "suspended") {
            this.ctx.resume();
        }
    }

    setEnabled(on) {
        this.enabled = Boolean(on);
        if (this.master) this.master.gain.value = this.enabled ? this.volume : 0;
    }

    toggle() {
        this.setEnabled(!this.enabled);
        return this.enabled;
    }

    setVolume(volume) {
        this.volume = Math.min(1, Math.max(0, Number(volume)));
        if (this.master) this.master.gain.value = this.enabled ? this.volume : 0;
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

    playDock() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(120, now);
            osc.frequency.exponentialRampToValueAtTime(55, now + 0.22);
            gain.gain.setValueAtTime(0.24, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.26);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.28);
            const osc2 = this.ctx.createOscillator();
            const gain2 = this.ctx.createGain();
            osc2.type = "triangle";
            osc2.frequency.setValueAtTime(880, now + 0.08);
            osc2.frequency.setValueAtTime(1320, now + 0.16);
            gain2.gain.setValueAtTime(0.09, now + 0.08);
            gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
            osc2.connect(gain2);
            gain2.connect(this.master);
            osc2.start(now + 0.08);
            osc2.stop(now + 0.38);
        } catch (e) {}
    }

    playWarp() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(60, now);
            osc.frequency.exponentialRampToValueAtTime(320, now + 0.18);
            osc.frequency.exponentialRampToValueAtTime(40, now + 0.42);
            gain.gain.setValueAtTime(0.22, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.48);
        } catch (e) {}
    }

    playFlak() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            [0, 0.07].forEach((delay) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = "square";
                osc.frequency.setValueAtTime(280, now + delay);
                osc.frequency.exponentialRampToValueAtTime(45, now + delay + 0.12);
                gain.gain.setValueAtTime(0.18, now + delay);
                gain.gain.exponentialRampToValueAtTime(0.001, now + delay + 0.14);
                osc.connect(gain);
                gain.connect(this.master);
                osc.start(now + delay);
                osc.stop(now + delay + 0.16);
            });
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

    playShieldDeflect() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime(1200, now);
            osc.frequency.exponentialRampToValueAtTime(580, now + 0.22);
            gain.gain.setValueAtTime(0.22, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.26);
        } catch (e) {}
    }

    playQuantumWarp() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "sawtooth";
            osc.frequency.setValueAtTime(80, now);
            osc.frequency.exponentialRampToValueAtTime(22, now + 0.85);
            gain.gain.setValueAtTime(0.28, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.90);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.92);
        } catch (e) {}
    }

    playCashRegister() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            [1046.50, 1318.51].forEach((freq, idx) => {
                const osc = this.ctx.createOscillator();
                const gain = this.ctx.createGain();
                osc.type = "triangle";
                osc.frequency.setValueAtTime(freq, now + idx * 0.08);
                gain.gain.setValueAtTime(0.18, now + idx * 0.08);
                gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.08 + 0.28);
                osc.connect(gain);
                gain.connect(this.master);
                osc.start(now + idx * 0.08);
                osc.stop(now + idx * 0.08 + 0.30);
            });
        } catch (e) {}
    }

    playHullDamage() {
        if (!this.enabled || !this.ctx) return;
        try {
            const now = this.ctx.currentTime;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = "square";
            osc.frequency.setValueAtTime(95, now);
            osc.frequency.exponentialRampToValueAtTime(30, now + 0.32);
            gain.gain.setValueAtTime(0.25, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
            osc.connect(gain);
            gain.connect(this.master);
            osc.start(now);
            osc.stop(now + 0.38);
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
        this.particles = window.ParticleSystem ? new window.ParticleSystem() : null;
        this.surfaceMap = window.SurfaceMapRenderer ? new window.SurfaceMapRenderer() : null;
        this.surfaceSelectedOp = null;
        this.combatFx = window.ParticleSystem ? new window.ParticleSystem(240) : null;
        this.combatCanvas = document.getElementById("combatVisual");
        this.combatScene = null;
        this.combatBeamUntil = 0;
        this.combatFlash = null;
        this.lastShipPosition = null;
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
        this.panVx = 0;
        this.panVy = 0;
        this.targetPanX = null;
        this.targetPanY = null;
        this.lastDragPoint = null;
        this.lastDragTime = 0;
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
        this.initDeckScrollHint();
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
        this.btnRebuildTarget = document.getElementById("btnRebuildTarget");
        this.btnReliefTarget = document.getElementById("btnReliefTarget");
        this.btnRestoreTarget = document.getElementById("btnRestoreTarget");
        this.salvageInfo = document.getElementById("salvageInfo");
        this.btnJumpTarget = document.getElementById("btnJumpTarget");
        this.btnHailTarget = document.getElementById("btnHailTarget");
        this.btnClearTarget = document.getElementById("btnClearTarget");
        this.targetGravity = document.getElementById("targetGravity");
        this.targetAtmosphere = document.getElementById("targetAtmosphere");
        this.targetTemp = document.getElementById("targetTemp");
        this.targetHabitability = document.getElementById("targetHabitability");
        this.targetCapacity = document.getElementById("targetCapacity");
        this.targetTech = document.getElementById("targetTech");
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
        this.btnCombatBoard = document.getElementById("btnCombatBoard");
        this.btnCombatGambit = document.getElementById("btnCombatGambit");
        this.btnCombatTarget = document.getElementById("btnCombatTarget");
        this.btnCombatPdc = document.getElementById("btnCombatPdc");
        this.btnSubsystemWeapons = document.getElementById("btnSubsystemWeapons");
        this.btnSubsystemShields = document.getElementById("btnSubsystemShields");
        this.btnSubsystemEngines = document.getElementById("btnSubsystemEngines");
        this.btnSubsystemBridge = document.getElementById("btnSubsystemBridge");
        this.btnFabricatePatch = document.getElementById("btnFabricatePatch");
        this.btnFabricateFuel = document.getElementById("btnFabricateFuel");
        this.btnCombatAbsorb = document.getElementById("btnCombatAbsorb");
        this.btnCombatEvade = document.getElementById("btnCombatEvade");
        this.btnCombatFlee = document.getElementById("btnCombatFlee");
        this.combatComboBadge = document.getElementById("combatComboBadge");
        this.combatComboCount = document.getElementById("combatComboCount");
        this.combatStanceLine = document.getElementById("combatStanceLine");
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
        this.customsCard = document.getElementById("customsCard");
        this.customsTitle = document.getElementById("customsTitle");
        this.customsDesc = document.getElementById("customsDesc");
        this.customsManifest = document.getElementById("customsManifest");
        this.btnCustomsBribe = document.getElementById("btnCustomsBribe");
        this.btnCustomsJettison = document.getElementById("btnCustomsJettison");
        this.btnCustomsConfiscate = document.getElementById("btnCustomsConfiscate");
        this.btnCustomsFlee = document.getElementById("btnCustomsFlee");
        this.btnDrydockOverhaul = document.getElementById("btnDrydockOverhaul");
        this.overhaulCostLabel = document.getElementById("overhaulCostLabel");
        this.repairCostLabel = document.getElementById("repairCostLabel");
        this.refuelCostLabel = document.getElementById("refuelCostLabel");
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
        this.marketBadge = document.getElementById("marketBadge");
        this.aiBadge = document.getElementById("aiBadge");
        this.skillsBadge = document.getElementById("skillsBadge");
        this.questsBadge = document.getElementById("questsBadge");
        this.factionsBadge = document.getElementById("factionsBadge");
        this.empireBadge = document.getElementById("empireBadge");
        this.crewBadge = document.getElementById("crewBadge");
        this.fleetBadge = document.getElementById("fleetBadge");
        this.arsenalBadge = document.getElementById("arsenalBadge");
        this.shipBadge = document.getElementById("shipBadge");

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
        this.fleetUpkeepLine = document.getElementById("fleetUpkeepLine");
        this.fleetStanceRow = document.getElementById("fleetStanceRow");
        this.fleetStanceHint = document.getElementById("fleetStanceHint");
        this.marketTableBody = document.getElementById("marketTableBody");
        this.autoTradeCommodity = document.getElementById("autoTradeCommodity");
        this.autoTradeBuy = document.getElementById("autoTradeBuy");
        this.autoTradeSell = document.getElementById("autoTradeSell");
        this.autoTradeQty = document.getElementById("autoTradeQty");
        this.autoTradeStatus = document.getElementById("autoTradeStatus");
        this.autoTradeNote = document.getElementById("autoTradeNote");
        this.btnAutoTradeEnable = document.getElementById("btnAutoTradeEnable");
        this.btnAutoTradeDisable = document.getElementById("btnAutoTradeDisable");
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
        this.shipRoomGrid = document.getElementById("shipRoomGrid");
        this.shipInteriorStatus = document.getElementById("shipInteriorStatus");
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
            this.audioIcon.textContent = on ? "◉" : "◌";
            this.audioToggleBtn.style.opacity = on ? "1" : "0.5";
            const settingSound = document.getElementById("settingSound");
            if (settingSound) settingSound.checked = on;
            this.saveSettings();
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
            const { x: cx, y: cy } = this.mapCenter();
            if (this.lastShipPosition) {
                const shipOffset = Math.hypot(this.lastShipPosition.x - cx, this.lastShipPosition.y - cy);
                if (shipOffset < 8 && (Math.abs(this.panX) > 2 || Math.abs(this.panY) > 2)) {
                    this.targetPanX = 0;
                    this.targetPanY = 0;
                } else {
                    this.targetPanX = -(this.lastShipPosition.x - cx - this.panX);
                    this.targetPanY = -(this.lastShipPosition.y - cy - this.panY);
                }
            } else {
                this.targetPanX = 0;
                this.targetPanY = 0;
            }
            this.panVx = 0;
            this.panVy = 0;
            this.sound.playBeep(1000, 0.05);
        });

        // Target actions
        this.btnOrbitTarget.addEventListener("click", () => this.handleTravelAction("sublight"));
        this.btnQuantumTarget?.addEventListener("click", () => this.handleTravelAction("quantum"));
        this.btnRebuildTarget?.addEventListener("click", () => this.handleReconstructAction("credits"));
        this.btnReliefTarget?.addEventListener("click", () => this.handleReconstructAction("relief"));
        this.btnRestoreTarget?.addEventListener("click", () => this.postAction("/api/megastructure/restore", { body_id: this.selectedTarget?.id }));
        this.btnJumpTarget.addEventListener("click", () => this.handleJumpAction());
        this.btnHailTarget?.addEventListener("click", () => {
            if (this.selectedType === "captain" && this.selectedTarget) {
                this.handleAIAction(this.selectedTarget.id, "hail");
            }
        });
        this.btnClearTarget?.addEventListener("click", () => {
            this.selectedTarget = null;
            this.selectedType = null;
            this.updateTargetCard();
        });

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
        if (this.btnDrydockOverhaul) this.btnDrydockOverhaul.addEventListener("click", () => this.handleOverhaul());
        if (this.btnCustomsBribe) this.btnCustomsBribe.addEventListener("click", () => this.handleCustomsResolve("bribe"));
        if (this.btnCustomsJettison) this.btnCustomsJettison.addEventListener("click", () => this.handleCustomsResolve("jettison"));
        if (this.btnCustomsConfiscate) this.btnCustomsConfiscate.addEventListener("click", () => this.handleCustomsResolve("confiscate"));
        if (this.btnCustomsFlee) this.btnCustomsFlee.addEventListener("click", () => this.handleCustomsResolve("flee"));
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
            this.closeMainMenu();
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
        this.btnAutoTradeEnable?.addEventListener("click", () => this.handleTradeAutomation(true));
        this.btnAutoTradeDisable?.addEventListener("click", () => this.handleTradeAutomation(false));
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
        document.getElementById("settingDecisionCadence")?.addEventListener("change", (event) => {
            this.postAction("/api/settings/decisions", { cadence: event.target.value });
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
        if (this.btnCombatBoard) {
            this.btnCombatBoard.addEventListener("click", () => this.handleCombat("board_enemy"));
        }
        if (this.btnCombatGambit) {
            this.btnCombatGambit.addEventListener("click", () => this.postAction("/api/combat/gambit", {}));
        }
        if (this.btnCombatDrone) {
            this.btnCombatDrone.addEventListener("click", () => this.handleCombat("drone_strike"));
        }
        if (this.btnCombatTarget) {
            this.btnCombatTarget.addEventListener("click", () => this.handleCombat("target_subsystem"));
        }
        if (this.btnCombatPdc) {
            this.btnCombatPdc.addEventListener("click", () => this.handleCombat("point_defense"));
        }
        if (this.btnSubsystemWeapons) {
            this.btnSubsystemWeapons.addEventListener("click", () => this.handleCombat("target_weapons"));
        }
        if (this.btnSubsystemShields) {
            this.btnSubsystemShields.addEventListener("click", () => this.handleCombat("target_shields"));
        }
        if (this.btnSubsystemEngines) {
            this.btnSubsystemEngines.addEventListener("click", () => this.handleCombat("target_engines"));
        }
        if (this.btnSubsystemBridge) {
            this.btnSubsystemBridge.addEventListener("click", () => this.handleCombat("target_bridge"));
        }
        if (this.btnFabricatePatch) {
            this.btnFabricatePatch.addEventListener("click", () => this.handleFabricate("patch_kit"));
        }
        if (this.btnFabricateFuel) {
            this.btnFabricateFuel.addEventListener("click", () => this.handleFabricate("fuel_cell"));
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
            this.lastDragPoint = point;
            this.lastDragTime = performance.now();
            this.panVx = 0;
            this.panVy = 0;
            this.targetPanX = null;
            this.targetPanY = null;
        });

        window.addEventListener("mouseup", () => {
            if (this.dragMoved) this.suppressClick = true;
            this.isDragging = false;
            const speed = Math.hypot(this.panVx, this.panVy);
            if (speed > 40) {
                this.panVx = (this.panVx / speed) * 40;
                this.panVy = (this.panVy / speed) * 40;
            }
        });

        this.canvas.addEventListener("mousemove", (e) => {
            const point = this.pointerToCanvas(e);
            if (this.isDragging) {
                const now = performance.now();
                const dt = Math.max(1, now - (this.lastDragTime || now));
                const nextX = point.x - this.dragStartX;
                const nextY = point.y - this.dragStartY;
                if (Math.hypot(nextX - this.panX, nextY - this.panY) > 3) {
                    this.dragMoved = true;
                }
                if (this.lastDragPoint) {
                    const sampleVx = (point.x - this.lastDragPoint.x) / (dt / 16.67);
                    const sampleVy = (point.y - this.lastDragPoint.y) / (dt / 16.67);
                    this.panVx = this.panVx * 0.35 + sampleVx * 0.65;
                    this.panVy = this.panVy * 0.35 + sampleVy * 0.65;
                }
                this.lastDragPoint = point;
                this.lastDragTime = now;
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
        this.canvas.addEventListener("dblclick", (e) => this.handleCanvasDblClick(e));

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
            } else if (hotkey === "c") {
                e.preventDefault();
                document.getElementById("btnResetView")?.click();
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
            readout.textContent = `${width}x${height} @${(window.devicePixelRatio || 1).toFixed(1)}x // ${density.toUpperCase()} // SCALE ${scalePercent}%`;
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

        // The server owns decision cadence, so mirror it back into the settings select.
        const cadenceSelect = document.getElementById("settingDecisionCadence");
        const cadence = (this.state.settings || {}).decision_cadence;
        if (cadenceSelect && cadence && cadenceSelect.value !== cadence) {
            cadenceSelect.value = cadence;
        }

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
        const monthly = flow ? ` · ${flow.net_per_month >= 0 ? "+" : ""}${Math.round(flow.net_per_month)}/M` : "";
        this.cargoSummary.textContent = `HOLD ${totalCargo}/${ship.cargo_capacity}${monthly}`;
        this.cargoSummary.title = flow
            ? `Monthly treasury: crew+fleet -${flow.upkeep_per_month} cr (fleet ${flow.fleet_upkeep_per_month || 0}), passive +${flow.passive_per_month} cr`
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
        this.streakVal.textContent = `✧ ${streak}`;
        this.streakVal.title = `${streak} jump${streak > 1 ? "s" : ""} streak, x${streakMult.toFixed(2)} payouts`;
        this.vitalStreakCard.classList.toggle("high-streak", streak >= 3);
        this.streakSubtext.textContent = streak > 1
            ? `x${streakMult.toFixed(2)} PAYOUT`
            : "x1.00 BASE";

        // Mastery render
        const mastery = ship.mastery || { level: 1, xp: 0, next_level_xp: 500, talent_points: 0 };
        this.masteryLevelVal.textContent = `★ LVL ${mastery.level}`;
        const xpPct = Math.min(100, Math.round((mastery.xp / mastery.next_level_xp) * 100));
        this.masteryBar.style.width = `${xpPct}%`;
        this.masterySubtext.textContent = `${mastery.xp}/${mastery.next_level_xp} XP${mastery.talent_points ? ' · +' + mastery.talent_points + 'P' : ''}`;

        // Contract ready notification badge
        const contracts = ship.active_contracts || [];
        const readyContracts = contracts.filter(c => c.completed);
        if (readyContracts.length > 0) {
            this.contractsBadge.style.display = "inline-block";
            this.contractsBadge.textContent = readyContracts.length;
        } else {
            this.contractsBadge.style.display = "none";
        }

        // Ship attention badge: docked drydock repair you can afford right now
        if (this.shipBadge) {
            const drydock = this.state.drydock || {};
            const credits = Number((this.state.ship || {}).credits || 0);
            const serviceable = Boolean(drydock.docked)
                && Number(drydock.repair_hp || 0) > 0
                && credits >= Number(drydock.repair_cost || 0);
            this.shipBadge.style.display = serviceable ? "inline-block" : "none";
        }

        // Arsenal attention badge: unequipped upgrades you can afford right now
        if (this.arsenalBadge) {
            const credits = Number((this.state.ship || {}).credits || 0);
            const equipped = (this.state.ship || {}).equipped_upgrades || {};
            const buyable = (this.state.catalog_upgrades || []).filter(u =>
                equipped[u.slot] !== u.id && Number(u.cost || Infinity) <= credits
            ).length;
            if (buyable > 0) {
                this.arsenalBadge.style.display = "inline-block";
                this.arsenalBadge.textContent = buyable;
            } else {
                this.arsenalBadge.style.display = "none";
            }
        }

        // Fleet attention badge: escorts ready to train below Ace at an affordable fee
        if (this.fleetBadge) {
            const credits = Number((this.state.ship || {}).credits || 0);
            const fleetShips = ((this.state.fleet_manager || {}).ships || this.state.ship.fleet_ships || []);
            const trainable = fleetShips.filter(s => {
                const xpMax = Number(s.experience_max || 300);
                return Number(s.experience || 0) < xpMax && Number(s.training_cost || 0) <= credits;
            }).length;
            if (trainable > 0) {
                this.fleetBadge.style.display = "inline-block";
                this.fleetBadge.textContent = trainable;
            } else {
                this.fleetBadge.style.display = "none";
            }
        }

        // Crew attention badge: injured members needing care
        if (this.crewBadge) {
            const hurt = (this.state.ship.crew || []).filter(m => Number(m.injury_ticks || 0) > 0).length;
            if (hurt > 0) {
                this.crewBadge.style.display = "inline-block";
                this.crewBadge.textContent = hurt;
            } else {
                this.crewBadge.style.display = "none";
            }
        }

        // Empire attention badge: outposts with damage you can afford to repair
        if (this.empireBadge) {
            const credits = Number((this.state.ship || {}).credits || 0);
            const repairable = (this.state.outposts || []).filter(o =>
                Number(o.integrity ?? 100) < 100 && Number(o.repair_cost ?? Infinity) <= credits
            ).length;
            if (repairable > 0) {
                this.empireBadge.style.display = "inline-block";
                this.empireBadge.textContent = repairable;
            } else {
                this.empireBadge.style.display = "none";
            }
        }

        // Faction attention badge: active wars involving your polity or your bonds
        if (this.factionsBadge) {
            const gpWars = ((this.state.galactic_politics || {}).wars || []).concat(this.state.wars || []);
            const seen = new Set();
            let involved = 0;
            gpWars.forEach(w => {
                if (!w || !w.active || seen.has(w.id)) return;
                seen.add(w.id);
                const pledged = Object.values(w.support || {}).some(v => Number(v) > 0);
                if (w.attacker_id === "sol_coalition" || w.defender_id === "sol_coalition" || pledged) involved++;
            });
            if (involved > 0) {
                this.factionsBadge.style.display = "inline-block";
                this.factionsBadge.textContent = involved;
            } else {
                this.factionsBadge.style.display = "none";
            }
        }

        // AI command attention badge: recruitable captains (hireable or allyable)
        if (this.aiBadge) {
            const credits = Number((this.state.ship || {}).credits || 0);
            const recruitable = (this.state.ai_captains || []).filter(c => {
                const hireable = c.archetype === "mercenary" && !c.hired && credits >= 2500;
                const allyable = !c.ally && Number(c.trust || 0) >= 50;
                return hireable || allyable;
            }).length;
            if (recruitable > 0) {
                this.aiBadge.style.display = "inline-block";
                this.aiBadge.textContent = recruitable;
            } else {
                this.aiBadge.style.display = "none";
            }
        }

        // Commerce attention badge: held goods selling above average cost
        if (this.marketBadge) {
            const cargo = (this.state.ship || {}).cargo || {};
            const avgCost = this.state.cargo_avg_cost || {};
            const quotes = this.state.market_quotes || [];
            const winners = quotes.filter(q => {
                const hold = Number(cargo[q.commodity_id] || 0);
                const avg = Number(avgCost[q.commodity_id] || 0);
                return hold > 0 && avg > 0 && Number(q.sell_price || 0) > avg;
            }).length;
            if (winners > 0) {
                this.marketBadge.style.display = "inline-block";
                this.marketBadge.textContent = winners;
            } else {
                this.marketBadge.style.display = "none";
            }
        }

        // Skills attention badge: unspent specialization points
        if (this.skillsBadge) {
            const points = Number(((this.state.ship || {}).mastery || {}).talent_points || 0);
            if (points > 0) {
                this.skillsBadge.style.display = "inline-block";
                this.skillsBadge.textContent = points;
            } else {
                this.skillsBadge.style.display = "none";
            }
        }

        // Quest attention badge: claimable contract quests surface here too
        if (this.questsBadge) {
            const claimable = readyContracts.length;
            if (claimable > 0) {
                this.questsBadge.style.display = "inline-block";
                this.questsBadge.textContent = claimable;
            } else {
                this.questsBadge.style.display = "none";
            }
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

            // Subsystem Status Telemetry
            const wepFill = document.getElementById("subsystemFillWep");
            const wepVal = document.getElementById("subsystemValWep");
            const engFill = document.getElementById("subsystemFillEng");
            const engVal = document.getElementById("subsystemValEng");
            const shdFill = document.getElementById("subsystemFillShd");
            const shdVal = document.getElementById("subsystemValShd");
            const brdgFill = document.getElementById("subsystemFillBrdg");
            const brdgVal = document.getElementById("subsystemValBrdg");

            if (wepFill && wepVal) {
                const wepPct = Math.min(100, Math.round((c.enemy_damage / Math.max(1, c.enemy_damage >= 25 ? c.enemy_damage : 30)) * 100));
                wepFill.style.width = `${wepPct}%`;
                wepVal.textContent = wepPct < 80 ? "▲ DAMAGED" : "● 100%";
            }
            if (engFill && engVal) {
                const enginesDisabled = Boolean(c.enemy_engines_disabled);
                engFill.style.width = enginesDisabled ? "25%" : "100%";
                engVal.textContent = enginesDisabled ? "✕ CRIPPLED" : "● NOMINAL";
            }
            if (shdFill && shdVal) {
                const hasShield = (c.enemy_shield || 0) > 0;
                shdFill.style.width = hasShield ? "100%" : "0%";
                shdVal.textContent = hasShield ? "● ACTIVE" : "✕ OFFLINE";
            }
            if (brdgFill && brdgVal) {
                brdgFill.style.width = `${pct}%`;
                brdgVal.textContent = pct < 40 ? "▲ PANICKED" : "● ALERT";
            }

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

            if (this.btnCombatBoard) {
                const crew = ship.crew || [];
                const hasMarine = crew.some(
                    member => member.role === "marine" && member.status === "active"
                        && Number(member.injury_ticks || 0) === 0
                );
                const hurtMarine = !hasMarine && crew.some(
                    member => member.role === "marine" && member.status === "active"
                        && Number(member.injury_ticks || 0) > 0
                );
                const crippledAt = Math.max(1, Math.floor(c.enemy_max_hull * 0.30));
                const boardable = c.enemy_shield <= 0 && c.enemy_hull <= crippledAt && hasMarine;
                this.btnCombatBoard.disabled = !boardable;
                this.btnCombatBoard.title = !hasMarine
                    ? (hurtMarine
                        ? "Marine party injured — let them recover first"
                        : "Recruit a marine before boarding")
                    : c.enemy_shield > 0
                        ? "Collapse enemy shields first"
                        : c.enemy_hull > crippledAt
                            ? `Board only below ${crippledAt} hull`
                            : "Send the marine party across";
            }
            if (this.btnCombatGambit) {
                const localCaptains = (ship.fleet_ships || []).filter(escort =>
                    escort.assigned_system_id === ship.current_system_id
                    && Number(escort.hull) > 0
                    && Boolean(escort.captain_id)
                );
                const gambitReady = !c.captain_gambit_used && localCaptains.length > 0;
                this.btnCombatGambit.disabled = !gambitReady;
                this.btnCombatGambit.title = c.captain_gambit_used
                    ? "The captain's gambit is already spent this battle"
                    : localCaptains.length
                        ? "Spend the lead captain's once-per-battle specialty"
                        : "No living escort captain in this system";
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
            if (this.combatStanceLine) {
                this.combatStanceLine.textContent =
                    `FLEET STANCE: ${String(ship.battle_stance || "balanced").toUpperCase()}`;
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

        if (this.state.active_customs && !this.state.active_combat) {
            const customs = this.state.active_customs;
            this.sound.playAlarm();
            if (this.customsCard) {
                this.customsCard.style.display = "flex";
                this.customsTitle.textContent = `${customs.patrol_vessel}`;
                this.customsDesc.textContent = customs.description;
                const itemsList = Object.entries(customs.contraband_found || {})
                    .map(([cid, qty]) => `${qty}x ${cid.toUpperCase()}`).join(", ");
                if (this.customsManifest) {
                    this.customsManifest.textContent = `ILLICIT GOODS: ${itemsList || "UNREGISTERED CARGO"}`;
                }
                if (this.btnCustomsBribe) {
                    this.btnCustomsBribe.textContent = `BRIBE PATROL (${customs.bribe_amount} CR)`;
                    this.btnCustomsBribe.disabled = (ship.credits || 0) < customs.bribe_amount;
                }
                if (this.btnCustomsJettison) {
                    this.btnCustomsJettison.textContent = `JETTISON ALL CONTRABAND`;
                }
                if (this.btnCustomsConfiscate) {
                    this.btnCustomsConfiscate.textContent = `SUBMIT (FINE: ${customs.fine_amount} CR)`;
                }
                if (this.btnCustomsFlee) {
                    this.btnCustomsFlee.textContent = `BURN ENGINES (-5 FUEL)`;
                    this.btnCustomsFlee.disabled = (ship.fuel || 0) < 5;
                }
            }
        } else if (this.customsCard) {
            this.customsCard.style.display = "none";
        }

        const drydock = this.state.drydock || null;
        if (drydock) {
            // Prices come from the engine quote so a faction repair discount can never
            // make the label disagree with the charge.
            const canService = Boolean(drydock.docked);
            const credits = Number(drydock.credits || 0);
            if (this.repairCostLabel) {
                this.repairCostLabel.textContent = drydock.repair_hp > 0
                    ? `${drydock.repair_hp} HP · ${drydock.repair_cost} CR`
                    : "FULL";
            }
            if (this.btnDrydockRepair) {
                this.btnDrydockRepair.disabled = !canService || drydock.repair_hp <= 0
                    || credits < Number(drydock.repair_cost || 0);
            }
            if (this.refuelCostLabel) {
                this.refuelCostLabel.textContent = drydock.fuel_units > 0
                    ? `${drydock.fuel_units} FUEL · ${drydock.free_refuel ? "FREE" : drydock.refuel_cost + " CR"}`
                    : "FULL";
            }
            if (this.btnRefuelTanks) {
                this.btnRefuelTanks.disabled = !canService || drydock.fuel_units <= 0
                    || (!drydock.free_refuel && credits < Number(drydock.refuel_cost || 0));
            }
            if (this.overhaulCostLabel) {
                this.overhaulCostLabel.textContent = drydock.wear > 0
                    ? `${Number(drydock.wear).toFixed(1)}% WEAR (${drydock.overhaul_cost} CR)`
                    : "0.0% WEAR";
            }
            if (this.btnDrydockOverhaul) {
                this.btnDrydockOverhaul.disabled = !canService || drydock.wear <= 0
                    || credits < Number(drydock.overhaul_cost || 0);
            }
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
            const curIdx = tut.current_step_index || 0;
            this.cadetBanner.style.display = "flex";
            this.cadetMilestoneTitle.textContent = `Milestone ${curIdx + 1}/${tut.steps.length}: ${step.title}`;
            this.cadetMilestoneDesc.textContent = step.description;
            this.cadetMilestoneHint.textContent = step.hint;
            this.cadetMilestoneReward.textContent = `+${step.reward_credits} CR / +${step.reward_xp} XP`;
            const pipsEl = document.getElementById("cadetStepPips");
            if (pipsEl && tut.steps) {
                pipsEl.innerHTML = tut.steps.map((_, i) =>
                    `<span class="cadet-pip ${i < curIdx ? "pip-done" : (i === curIdx ? "pip-active" : "pip-locked")}">${i < curIdx ? "✓" : i + 1}</span>`
                ).join('<span class="cadet-pip-divider">·</span>');
            }
            this.btnSkipCadet.textContent = "SKIP TUTORIAL";
            this.btnSkipCadet.style.display = "inline-block";
        } else if (tut && tut.completed && !this.cadetGraduationDismissed) {
            this.cadetBanner.style.display = "flex";
            this.cadetMilestoneTitle.textContent = "△ ACADEMY GRADUATION: Flight Wings Conferred!";
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
        this.drawCommsOscilloscope();
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
            this.storyTargetBadge.textContent = "★ ALL ACTS RESOLVED";
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
                    const lockBadge = locked ? `<span class="choice-lock-badge">⚿ LOCKED</span>` : "";
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

    drawCommsOscilloscope() {
        const canvas = document.getElementById("commsOscilloscope");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const w = canvas.width;
        const h = canvas.height;
        ctx.fillStyle = "rgba(6, 11, 15, 0.96)";
        ctx.fillRect(0, 0, w, h);

        // 1. Tektronix laboratory CRT graticule
        ctx.strokeStyle = "rgba(127, 183, 201, 0.12)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        // Major axes
        ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2);
        ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h);
        // Vertical graticule lines
        for (let x = 40; x < w; x += 40) {
            ctx.moveTo(x, 0); ctx.lineTo(x, h);
        }
        ctx.stroke();

        // Sub-division micro tick marks along center baseline
        ctx.strokeStyle = "rgba(127, 183, 201, 0.22)";
        ctx.beginPath();
        for (let x = 10; x < w; x += 10) {
            const tickH = (x % 40 === 0) ? 4 : 2;
            ctx.moveTo(x, (h / 2) - tickH);
            ctx.lineTo(x, (h / 2) + tickH);
        }
        ctx.stroke();

        // 2. Modulated RF voice waveform
        const now = performance.now() * 0.003;
        const wavePoints = [];
        for (let x = 0; x < w; x++) {
            const freq = 0.045;
            const carrier = Math.sin(x * freq + now * 3.2) * (h * 0.26);
            const envelope = Math.cos(x * 0.012 - now * 1.6);
            const harmonic = Math.sin(x * 0.12 + now * 5.8) * 2.5;
            const microNoise = Math.sin(x * 0.28 + now * 9.4) * 0.9;
            const y = (h / 2) + (carrier * envelope) + harmonic + microNoise;
            wavePoints.push({ x, y });
        }

        // Trace A: Wide phosphor glow halo
        ctx.strokeStyle = "rgba(143, 191, 159, 0.28)";
        ctx.lineWidth = 3.2;
        ctx.beginPath();
        wavePoints.forEach((pt, i) => {
            if (i === 0) ctx.moveTo(pt.x, pt.y);
            else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();

        // Trace B: Crisp core electron beam
        ctx.strokeStyle = "#8fbf9f";
        ctx.shadowColor = "#8fbf9f";
        ctx.shadowBlur = 5;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        wavePoints.forEach((pt, i) => {
            if (i === 0) ctx.moveTo(pt.x, pt.y);
            else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();
        ctx.shadowBlur = 0;

        // 3. Sweeping electron beam excitation spot
        const sweepX = Math.floor((performance.now() * 0.11) % w);
        const sweepPt = wavePoints[sweepX] || wavePoints[0];
        if (sweepPt) {
            ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
            ctx.beginPath();
            ctx.arc(sweepPt.x, sweepPt.y, 2.0, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = "rgba(143, 191, 159, 0.4)";
            ctx.beginPath();
            ctx.arc(sweepPt.x, sweepPt.y, 5.0, 0, Math.PI * 2);
            ctx.fill();
        }

        // 4. Phosphor telemetry readout
        ctx.font = "9px 'Cascadia Mono', Consolas, monospace";
        ctx.fillStyle = "rgba(143, 191, 159, 0.75)";
        ctx.fillText("FREQ 1420.405 MHz // [CH-A] 50mV/div", 6, 11);
        ctx.fillStyle = "rgba(127, 183, 201, 0.65)";
        ctx.fillText("SNR +28.4 dB // DECRYPTED", w - 142, 11);
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
                this.sound.playCashRegister();
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
        this.syncMarketCategoryFilters();
        this.renderTradeAutomation();
        this.marketTableBody.innerHTML = "";
        const allQuotes = this.state.market_quotes || [];
        const activeCat = this.marketActiveCategory || "all";
        const quotes = activeCat === "all"
            ? allQuotes
            : allQuotes.filter(q => (q.category || "gen").toLowerCase().includes(activeCat) || (q.commodity_id || "").toLowerCase().includes(activeCat));
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

            const diff = avg ? (q.sell_price - avg) : 0;
            const marginChip = avg
                ? `<span class="market-margin-chip ${diff >= 0 ? "margin-pos" : "margin-neg"}">${diff >= 0 ? `+${diff} ▲` : `${diff} ▼`}</span>`
                : "";
            const cat = (q.category || "GEN").toUpperCase().slice(0, 4);

            const baseP = Number(q.base_price || (q.buy_price * 0.85));
            const trend = q.buy_price > baseP * 1.05 ? 1 : (q.buy_price < baseP * 0.95 ? -1 : 0);
            const trendIcon = trend > 0 ? "▲" : (trend < 0 ? "▼" : "—");
            const trendClass = trend > 0 ? "trend-up" : (trend < 0 ? "trend-down" : "trend-flat");
            const sparklineSvg = trend > 0
                ? `<svg class="trend-sparkline" width="28" height="12" viewBox="0 0 28 12"><defs><linearGradient id="sg-${commId}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="currentColor" stop-opacity="0.35"/><stop offset="100%" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs><polygon points="1,11 1,9 7,7 13,8 20,3 27,1 27,11" fill="url(#sg-${commId})" /><path d="M1,9 L7,7 L13,8 L20,3 L27,1" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>`
                : (trend < 0
                    ? `<svg class="trend-sparkline" width="28" height="12" viewBox="0 0 28 12"><defs><linearGradient id="sg-${commId}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="currentColor" stop-opacity="0.35"/><stop offset="100%" stop-color="currentColor" stop-opacity="0"/></linearGradient></defs><polygon points="1,11 1,1 7,3 13,2 20,8 27,10 27,11" fill="url(#sg-${commId})" /><path d="M1,1 L7,3 L13,2 L20,8 L27,10" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>`
                    : `<svg class="trend-sparkline" width="28" height="12" viewBox="0 0 28 12"><path d="M1,6 L7,6 L13,5 L20,7 L27,6" fill="none" stroke="currentColor" stroke-width="1.4"/></svg>`);
            const trendBadge = `<span class="market-trend-badge ${trendClass}" title="Galactic volatility price trend">${sparklineSvg} ${trendIcon}</span>`;

            tr.innerHTML = `
                <td>
                    <div class="commodity-info-cell">
                        <strong class="commodity-name">${this.escapeHtml(q.name)}</strong>
                        <div class="commodity-meta-row">
                            <span class="commodity-cat-badge cat-${cat.toLowerCase()}">${cat}</span>
                            <small class="commodity-category">${this.escapeHtml(q.category)}</small>
                            ${trendBadge}
                            ${marginChip}
                        </div>
                    </div>
                </td>
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

    renderTradeAutomation() {
        if (!this.autoTradeCommodity || !this.state) return;
        const quotes = this.state.market_quotes || [];
        const auto = this.state.trade_automation || {};
        const select = this.autoTradeCommodity;
        const signature = quotes.map(quote => `${quote.commodity_id}:${quote.name}`).join("|");
        if (select.dataset.signature !== signature) {
            select.innerHTML = quotes.map(quote =>
                `<option value="${this.escapeHtml(quote.commodity_id)}">${this.escapeHtml(quote.name)}</option>`
            ).join("");
            select.dataset.signature = signature;
        }
        if (auto.commodity_id) select.value = auto.commodity_id;
        if (this.autoTradeBuy) this.autoTradeBuy.value = auto.buy_below || "";
        if (this.autoTradeSell) this.autoTradeSell.value = auto.sell_above || "";
        if (this.autoTradeQty) this.autoTradeQty.value = auto.quantity || 1;
        if (this.autoTradeStatus) {
            this.autoTradeStatus.textContent = auto.enabled
                ? `ON // ${auto.trades || 0} TRADES // ${auto.realized_credits >= 0 ? "+" : ""}${auto.realized_credits || 0} CR`
                : "OFF";
        }
        if (this.autoTradeNote) {
            this.autoTradeNote.textContent = quotes.length
                ? "Broker executes at most one buy or sell every 3 ticks while docked."
                : "Dock at a station or colony to configure the broker.";
        }
    }

    async handleTradeAutomation(enabled) {
        if (!this.state) return;
        const commodity = this.autoTradeCommodity ? this.autoTradeCommodity.value : "";
        const payload = {
            enabled: Boolean(enabled),
            commodity_id: commodity,
            buy_below: Number(this.autoTradeBuy?.value || 0),
            sell_above: Number(this.autoTradeSell?.value || 0),
            quantity: Number(this.autoTradeQty?.value || 1),
        };
        const res = await this.postAction("/api/trade/automation", payload, "market");
        if (res && res.ok) this.renderTradeAutomation();
    }

    syncMarketLotBar() {
        document.querySelectorAll("#marketLotBar .market-lot-btn").forEach(button => {
            const active = button.getAttribute("data-lot") === this.tradeLot;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });
    }

    syncMarketCategoryFilters() {
        const bar = document.getElementById("marketCategoryFilters");
        if (!bar || bar.dataset.bound) return;
        bar.dataset.bound = "true";
        bar.querySelectorAll(".market-cat-pill").forEach(btn => {
            btn.addEventListener("click", () => {
                bar.querySelectorAll(".market-cat-pill").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                this.marketActiveCategory = btn.dataset.cat || "all";
                this.renderMarketTable();
            });
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

        const auto = this.state?.quantum_automation || {};
        this.quantumFreight.innerHTML = `
            <div class="quantum-header">
                <h3 class="subpanel-title">QUANTUM FREIGHT</h3>
                <span>${orders.length}/${data?.max_orders || 4} IN TRANSIT</span>
            </div>
            <div class="quantum-auto">
                <label><input type="checkbox" id="quantumAutoEnabled" ${auto.enabled ? "checked" : ""}> AUTO-FREIGHT</label>
                <label>MIN NET <input type="number" id="quantumAutoMin" min="0" step="10" value="${Number(auto.min_net ?? 100)}"></label>
                <span>${Number(auto.orders || 0)} orders · last ${Number(auto.last_net || 0) >= 0 ? "+" : ""}${Number(auto.last_net || 0)} CR</span>
            </div>
            <div class="quantum-orders">${orderRows}</div>
            <div class="quantum-routes">${routeRows}</div>
            <p class="quantum-note">Cargo leaves immediately; the destination pays on arrival. Fees are charged now.</p>
        `;
        const autoEnabled = this.quantumFreight.querySelector("#quantumAutoEnabled");
        const autoMin = this.quantumFreight.querySelector("#quantumAutoMin");
        const applyAuto = () => this.handleQuantumAutomation(
            Boolean(autoEnabled?.checked), Number(autoMin?.value || 0)
        );
        autoEnabled?.addEventListener("change", applyAuto);
        autoMin?.addEventListener("change", applyAuto);
        this.quantumFreight.querySelectorAll("[data-q-comm]").forEach(button => {
            button.addEventListener("click", () => this.handleQuantumOrder(
                button.getAttribute("data-q-comm"),
                Number(button.getAttribute("data-q-qty")),
                button.getAttribute("data-q-dest")
            ));
        });
    }

    async handleQuantumAutomation(enabled, minNet) {
        try {
            const res = await apiFetch("/api/trade/quantum/automation", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ enabled: Boolean(enabled), min_net: Number(minNet || 0) }),
            });
            const json = await res.json();
            if (json.state) this.state = json.state;
            if (json.message) this.appendLog(json.message, json.ok ? "reward" : "hazard");
            this.renderHUD();
            this.renderQuantumFreight();
        } catch (e) {
            this.appendLog(`[ERROR] Quantum automation failed: ${e.message}`, "hazard");
        }
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

            const curHull = this.state.ship?.max_hull || 100;
            const curShield = this.state.ship?.max_shield || 50;
            const curFuel = this.state.ship?.max_fuel || 100;
            const curCargo = this.state.ship?.cargo_capacity || 30;

            chassisList.forEach(c => {
                const isCurrent = currentClass === c.ship_class;
                const isStarter = c.cost === 0;
                const canAfford = credits >= c.cost;
                const dHull = c.max_hull - curHull;
                const dShield = c.max_shield - curShield;
                const dFuel = c.max_fuel - curFuel;
                const dCargo = c.cargo_capacity - curCargo;
                const card = document.createElement("div");
                card.className = `chassis-card ${isCurrent ? 'installed' : ''}`;
                card.innerHTML = `
                    <div class="chassis-info">
                        <div class="chassis-title-row">
                            <span class="slot-tag tag-cyan">${this.escapeHtml(c.ship_class)}</span>
                            <strong class="chassis-name">${this.escapeHtml(c.name)}</strong>
                        </div>
                        <p class="chassis-desc">${this.escapeHtml(c.description)}</p>
                        <div class="chassis-specs comparison-matrix">
                            <div class="spec-col">
                                <span class="spec-label">HULL</span>
                                <strong class="spec-val">${c.max_hull}</strong>
                                ${isCurrent ? '' : (dHull > 0 ? `<span class="delta-stat pos">+${dHull} ▲</span>` : dHull < 0 ? `<span class="delta-stat neg">${dHull} ▼</span>` : '<span class="delta-stat eq">±0</span>')}
                            </div>
                            <div class="spec-col">
                                <span class="spec-label">SHIELD</span>
                                <strong class="spec-val">${c.max_shield}</strong>
                                ${isCurrent ? '' : (dShield > 0 ? `<span class="delta-stat pos">+${dShield} ▲</span>` : dShield < 0 ? `<span class="delta-stat neg">${dShield} ▼</span>` : '<span class="delta-stat eq">±0</span>')}
                            </div>
                            <div class="spec-col">
                                <span class="spec-label">FUEL</span>
                                <strong class="spec-val">${c.max_fuel}</strong>
                                ${isCurrent ? '' : (dFuel > 0 ? `<span class="delta-stat pos">+${dFuel} ▲</span>` : dFuel < 0 ? `<span class="delta-stat neg">${dFuel} ▼</span>` : '<span class="delta-stat eq">±0</span>')}
                            </div>
                            <div class="spec-col">
                                <span class="spec-label">CARGO</span>
                                <strong class="spec-val">${c.cargo_capacity}</strong>
                                ${isCurrent ? '' : (dCargo > 0 ? `<span class="delta-stat pos">+${dCargo} ▲</span>` : dCargo < 0 ? `<span class="delta-stat neg">${dCargo} ▼</span>` : '<span class="delta-stat eq">±0</span>')}
                            </div>
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
        const bgCatalog = this.state.character_background_catalog || {};
        const bgEntry = Object.values(bgCatalog).find(b =>
            String((b && b.name) || "").toLowerCase() === String(ch.background || "Navigator").toLowerCase()
        ) || null;
        const bgLore = bgEntry && bgEntry.description ? String(bgEntry.description) : "";
        const bgBonus = bgEntry && bgEntry.skills
            ? Object.entries(bgEntry.skills).map(([s, v]) => `+${v} ${String(s).toUpperCase()}`).join(" · ")
            : "";

        this.characterProfile.innerHTML = `
            <div class="character-portrait-large">${this.portraitAvatar(ch.portrait, ch.name || "Player", 60)}</div>
            <div class="character-info">
                <div class="character-name-row">
                    <span class="character-name">${this.escapeHtml(ch.name || "Player")}</span>
                </div>
                <div class="character-meta">
                    <span>Age ${ch.age || 30}</span>
                    <span title="${this.escapeHtml(bgLore || "No recorded history")}">${this.escapeHtml(ch.background || "Navigator")}</span>
                    <span>${skillPoints} SP AVAILABLE</span>
                </div>
                ${bgLore ? `<div class="character-origin-lore" title="Origin training: ${this.escapeHtml(bgBonus)}">${this.escapeHtml(bgLore)}</div>` : ""}
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
            const isReady = isUnlocked && cd === 0 && !contextBlocked;
            return `<div class="ability-row ${isUnlocked ? (isReady ? "ready" : "") : "locked"}">
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
        const codes = report.slot_codes || {};
        const installed = report.installed || {};
        const catalog = report.catalog || [];
        const docked = !!(this.state.orbiting_body && this.state.orbiting_body.station_dockable);
        const credits = ship.credits || 0;

        const shipClass = String(ship.ship_class || "Corvette Scout");
        const silhouettes = {
            standard: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGradStd" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#0a1828" stop-opacity="0.95"/><stop offset="100%" stop-color="#040c16" stop-opacity="0.98"/></linearGradient></defs><line x1="10" y1="60" x2="290" y2="60" stroke="rgba(127,183,201,0.18)" stroke-width="0.8" stroke-dasharray="4,4"/><path d="M285,60 L190,26 L60,26 L25,44 L25,76 L60,94 L190,94 Z" fill="url(#shipGradStd)" stroke="#7fb7c9" stroke-width="1.8"/><polygon points="280,60 195,34 195,86" fill="rgba(127,183,201,0.15)" stroke="#7fb7c9" stroke-width="1"/><rect x="75" y="40" width="70" height="40" fill="#061220" stroke="rgba(201,163,90,0.6)" stroke-width="1" rx="2"/><circle cx="110" cy="60" r="10" fill="rgba(127,183,201,0.25)" stroke="#7fb7c9" stroke-width="1.2"/><rect x="15" y="48" width="12" height="10" fill="#00f0ff" opacity="0.8"/><rect x="15" y="62" width="12" height="10" fill="#00f0ff" opacity="0.8"/><circle cx="250" cy="60" r="4.5" fill="#c9a35a"/><text x="28" y="112" font-family="'Cascadia Mono',monospace" font-size="12" fill="rgba(127,183,201,0.6)">SEC-01 // VF-CORVETTE</text></svg>`,
            freighter: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGradFr" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#18140a" stop-opacity="0.95"/><stop offset="100%" stop-color="#0c0904" stop-opacity="0.98"/></linearGradient></defs><line x1="10" y1="60" x2="290" y2="60" stroke="rgba(201,163,90,0.18)" stroke-width="0.8" stroke-dasharray="4,4"/><path d="M260,35 L280,60 L260,85 L35,85 L20,70 L20,50 L35,35 Z" fill="url(#shipGradFr)" stroke="#c9a35a" stroke-width="1.8"/><rect x="50" y="22" width="60" height="76" fill="#141008" stroke="rgba(201,163,90,0.5)" stroke-width="1" rx="2"/><rect x="120" y="22" width="60" height="76" fill="#141008" stroke="rgba(201,163,90,0.5)" stroke-width="1" rx="2"/><circle cx="205" cy="60" r="11" fill="rgba(201,163,90,0.25)" stroke="#c9a35a" stroke-width="1.2"/><rect x="12" y="44" width="10" height="12" fill="#ffaa33" opacity="0.85"/><rect x="12" y="64" width="10" height="12" fill="#ffaa33" opacity="0.85"/><circle cx="260" cy="60" r="5" fill="#7fb7c9"/><text x="28" y="112" font-family="'Cascadia Mono',monospace" font-size="12" fill="rgba(201,163,90,0.6)">SEC-02 // CARGO-BULK</text></svg>`,
            fighter: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGradFgt" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#1a0a0a" stop-opacity="0.95"/><stop offset="100%" stop-color="#0d0404" stop-opacity="0.98"/></linearGradient></defs><line x1="10" y1="60" x2="290" y2="60" stroke="rgba(201,107,90,0.18)" stroke-width="0.8" stroke-dasharray="4,4"/><path d="M290,60 L210,38 L40,15 L70,52 L25,52 L25,68 L70,68 L40,105 L210,82 Z" fill="url(#shipGradFgt)" stroke="#c96b5a" stroke-width="1.8"/><circle cx="130" cy="60" r="8" fill="rgba(201,107,90,0.3)" stroke="#c96b5a" stroke-width="1"/><rect x="16" y="55" width="12" height="10" fill="#ff4422" opacity="0.9"/><circle cx="260" cy="60" r="4" fill="#ffd166"/><text x="28" y="112" font-family="'Cascadia Mono',monospace" font-size="12" fill="rgba(201,107,90,0.6)">SEC-03 // STRIKE-INTERCEPTOR</text></svg>`,
            explorer: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGradExp" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#140a1a" stop-opacity="0.95"/><stop offset="100%" stop-color="#0a040d" stop-opacity="0.98"/></linearGradient></defs><line x1="10" y1="60" x2="290" y2="60" stroke="rgba(169,139,189,0.18)" stroke-width="0.8" stroke-dasharray="4,4"/><path d="M290,60 L240,48 L170,30 L45,30 L30,48 L30,72 L45,90 L170,90 L240,72 Z" fill="url(#shipGradExp)" stroke="#a98bbd" stroke-width="1.8"/><circle cx="210" cy="60" r="14" fill="none" stroke="rgba(169,139,189,0.6)" stroke-width="1"/><circle cx="105" cy="60" r="9" fill="rgba(143,191,159,0.25)" stroke="#8fbf9f" stroke-width="1"/><rect x="20" y="54" width="12" height="12" fill="#aa66ff" opacity="0.85"/><circle cx="270" cy="60" r="4.5" fill="#8fbf9f"/><text x="28" y="112" font-family="'Cascadia Mono',monospace" font-size="12" fill="rgba(169,139,189,0.6)">SEC-04 // DEEP-SURVEY</text></svg>`,
            stealth: `<svg viewBox="0 0 300 120" class="ship-silhouette"><defs><linearGradient id="shipGradStl" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#101418" stop-opacity="0.95"/><stop offset="100%" stop-color="#06090c" stop-opacity="0.98"/></linearGradient></defs><line x1="10" y1="60" x2="290" y2="60" stroke="rgba(143,191,159,0.18)" stroke-width="0.8" stroke-dasharray="4,4"/><path d="M285,60 L210,32 L40,46 L65,60 L40,74 L210,88 Z" fill="url(#shipGradStl)" stroke="#8fbf9f" stroke-width="1.5"/><line x1="65" y1="60" x2="250" y2="60" stroke="#8fbf9f" stroke-width="1.2" opacity="0.75"/><circle cx="120" cy="60" r="7" fill="rgba(143,191,159,0.2)" stroke="#8fbf9f" stroke-width="1"/><rect x="32" y="56" width="10" height="8" fill="#55ccaa" opacity="0.75"/><text x="28" y="112" font-family="'Cascadia Mono',monospace" font-size="12" fill="rgba(143,191,159,0.6)">SEC-05 // RECON-GHOST</text></svg>`
        };
        const silhouette = /freight|cargo/i.test(shipClass) ? "freighter"
            : /fighter|intercept/i.test(shipClass) ? "fighter"
            : /explor|survey/i.test(shipClass) ? "explorer"
            : /stealth|ghost/i.test(shipClass) ? "stealth"
            : "standard";
        this.shipVisual.innerHTML = silhouettes[silhouette];
        this.renderShipInterior(silhouette, shipClass);

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
            const code = codes[slot] || String(slot).replace(/_/g, "").slice(0, 4).toUpperCase();
            const slotLabel = labels[slot] || slot;
            slotDiv.innerHTML = mod
                ? `<span class="ship-module-icon">✚</span><span class="ship-module-name">${this.escapeHtml(code)}</span>`
                : `<span class="ship-module-icon">+</span><span class="ship-module-name">${this.escapeHtml(code)}</span>`;
            slotDiv.title = mod
                ? `${slotLabel} — ${mod.name}: ${mod.description}`
                : `${slotLabel} — pick a compatible module below`;
            slotDiv.setAttribute("aria-label", mod ? `${slotLabel}: ${mod.name}` : `${slotLabel}: empty`);
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

    renderShipInterior(silhouette, shipClass) {
        if (!this.shipRoomGrid) return;
        const modelRooms = Array.isArray(this.state.ship && this.state.ship.rooms)
            ? this.state.ship.rooms
            : [];
        const layout = modelRooms.length
            ? modelRooms.map(room => [room.id, room.label, room.function, null, room.status])
            : (ROOM_LAYOUTS[silhouette] || ROOM_LAYOUTS.standard);
        const crew = Array.isArray(this.state.crew) ? this.state.crew : [];
        const installed = this.state.ship_mods && this.state.ship_mods.installed
            ? this.state.ship_mods.installed
            : {};
        const operational = Number(this.state.ship && this.state.ship.hull || 0) > 0;
        const staffedRoles = new Set(crew.map(member => String(member.role || "").toLowerCase()));
        const roleMatches = {
            bridge: ["navigator", "pilot", "commander"],
            cockpit: ["navigator", "pilot", "commander"],
            reactor: ["engineer", "engineering"],
            sensor: ["scientist", "science"],
            lab: ["scientist", "science"],
            weapons: ["gunner", "combat"],
            cargo: ["trader", "quartermaster"],
            cargo_b: ["trader", "quartermaster"],
            crew: ["medic", "security", "engineer"],
            medbay: ["medic", "doctor"],
        };
        const roomCards = layout.map(([id, label, department, icon, modelStatus], index) => {
            const staffed = (roleMatches[id] || []).some(role => staffedRoles.has(role));
            const powered = operational && (index !== layout.length - 1 || Object.keys(installed).length > 0);
            const state = !powered ? "offline" : staffed ? "staffed" : (modelStatus || "online");
            const stateLabel = state.toUpperCase();
            const roomIcon = icon || ({
                bridge: "◆", cockpit: "◆", reactor: "◎", medbay: "✚", crew: "◇",
                cargo: "▣", cargo_b: "▣", sensor: "⌬", lab: "⌘", airlock: "△",
                weapons: "⊕", dock: "⊞", ghost: "◇"
            }[id] || "◇");
            const tip = `${label} // ${department} // ${stateLabel}`;
            return `
                <article class="ship-room-card ${state}" data-room="${this.escapeHtml(id)}" title="${this.escapeHtml(tip)}">
                    <div class="ship-room-card-top">
                        <span class="ship-room-icon" aria-hidden="true">${roomIcon}</span>
                        <span class="ship-room-state">${stateLabel}</span>
                    </div>
                    <strong>${this.escapeHtml(label)}</strong>
                    <small>${this.escapeHtml(department)} // ${String(index + 1).padStart(2, "0")}</small>
                    <div class="ship-room-scanline"></div>
                </article>
            `;
        }).join("");
        this.shipRoomGrid.innerHTML = roomCards;
        if (this.shipInteriorStatus) {
            const staffed = layout.filter(([id]) => (roleMatches[id] || []).some(role => staffedRoles.has(role))).length;
            this.shipInteriorStatus.textContent = `${shipClass.toUpperCase()} // ${staffed}/${layout.length} STAFFED`;
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
                <span class="cashflow-value">PAYROLL <strong>-${cashFlow.crew_upkeep_per_month ?? cashFlow.upkeep_per_month}</strong> CR</span>
                <span class="cashflow-value">FLEET <strong>-${cashFlow.fleet_upkeep_per_month || 0}</strong> CR</span>
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
                const outpost = (this.state.outposts || []).find(o => (o.assigned_crew || []).includes(m.id));
                const captainShip = (this.state.fleet_manager?.ships || []).find(ship => ship.captain_id === m.id);
                const statusNote = injury > 0
                    ? ` | <span class="crew-injury">INJURED ${injury}T</span>`
                    : outpost
                        ? ` | <span class="crew-outpost">OUTPOST: ${this.escapeHtml(outpost.name)}</span>`
                        : captainShip
                            ? ` | <span class="crew-captain">CAPTAIN: ${this.escapeHtml(captainShip.name)}</span>`
                            : (away ? ` | <span class="crew-away">AWAY: ${this.escapeHtml(away.name)}</span>` : "");
                const curStation = (m.station || "").toLowerCase();
                const stationBadge = curStation ? ` <span class="station-badge station-${curStation}">[STATION: ${curStation.toUpperCase()}]</span>` : "";
                const stationOptions = [
                    { id: "", label: "NO STATION" },
                    { id: "helm", label: "➤ HELM (+40% Pilot)" },
                    { id: "engineering", label: "⚡ ENG (+40% Eng)" },
                    { id: "tactical", label: "✦ TAC (+40% Marine)" },
                    { id: "science", label: "⬡ SCI (+40% Sci)" },
                    { id: "medical", label: "✚ MED (+40% Medic)" },
                ];
                const stationSelect = `
                    <select class="crew-station-select" data-station-crew="${this.escapeHtml(m.id)}" ${away || outpost ? "disabled" : ""} title="Assign officer to starship duty station">
                        ${stationOptions.map(opt => `<option value="${opt.id}" ${curStation === opt.id ? "selected" : ""}>${opt.label}</option>`).join("")}
                    </select>
                `;
                const drillCost = 160 + Math.max(1, Number(m.skill || 1)) * 120;
                const drillReady = m.skill < 10 && injury <= 0 && Number((this.state.ship || {}).credits || 0) >= drillCost;
                const drillTitle = m.skill >= 10 ? "Already at maximum skill rank"
                    : (injury > 0 ? "Injured crew cannot drill"
                    : (drillReady ? `Drill to skill ${Number(m.skill) + 1} for ${drillCost} CR` : `Needs ${drillCost} CR`));
                return `
                <div class="crew-row">
                    <div class="crew-portrait">${this.portraitAvatar(m.portrait, m.name)}</div>
                    <div class="crew-info-block">
                        <strong>${this.escapeHtml(m.name)}${stationBadge}</strong>
                        <small>${this.escapeHtml(m.role)} · SKILL ${m.skill} · XP ${m.xp || 0}/${xpToNext}${statusNote}</small>
                        ${(m.medals || []).length ? `<div class="crew-medals">${m.medals.map(medal => `<span>★ ${this.escapeHtml(medal)}</span>`).join("")}</div>` : ""}
                    </div>
                    <div class="crew-morale-bar" title="Morale ${morale}${moraleNote}">
                        <div class="crew-morale-fill ${moraleClass}" style="width:${morale}%"></div>
                        <span class="crew-morale-text">${morale}${moraleNote}</span>
                    </div>
                    <div class="crew-actions">
                        ${stationSelect}
                        <button class="btn-hud btn-amber" data-train-crew="${this.escapeHtml(m.id)}" ${drillReady ? "" : "disabled"} title="${this.escapeHtml(drillTitle)}">DRILL · ${drillCost}</button>
                        <button class="btn-hud" data-dismiss-crew="${this.escapeHtml(m.id)}" ${away || outpost ? "disabled" : ""}>DISMISS</button>
                    </div>
                </div>
                `;
            }).join("") : `<p class="panel-intro-text">No crew aboard. Dock at a station and recruit specialists.</p>`;
            this.crewRoster.querySelectorAll("[data-station-crew]").forEach(sel =>
                sel.addEventListener("change", (e) => this.postAction("/api/crew/station", { crew_id: sel.getAttribute("data-station-crew"), station: e.target.value }, "crew"))
            );
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
        if (this.surfaceSelectedOp && !operations.some(op => op.id === this.surfaceSelectedOp)) {
            this.surfaceSelectedOp = null;
        }
        const selectedOp = operations.find(op => op.id === this.surfaceSelectedOp);
        const wasHidden = this.surfaceOps.style.display === "none";
        const rows = operations.map((op, index) => {
            const riskClass = op.risk >= 35 ? "risk-high" : (op.risk >= 18 ? "risk-mid" : "risk-low");
            const rewards = [];
            if (op.credits) rewards.push(`+${op.credits} CR`);
            if (op.research) rewards.push(`+${op.research} RES`);
            if (op.credit_cost) rewards.push(`-${op.credit_cost} CR`);
            if (op.heal_injuries) rewards.push(`HEAL ${op.heal_injuries}`);
            if (op.morale) rewards.push(`MORALE ${op.morale > 0 ? "+" : ""}${op.morale}`);
            (op.cargo || []).forEach(item => rewards.push(`+${item.quantity} ${item.name || item.id}`));
            return `<div class="surface-op-row ${op.used ? "is-worked" : ""} ${op.id === this.surfaceSelectedOp ? "is-selected" : ""}">
                <div class="surface-op-main">
                    <strong><span class="surface-site-index">S${index + 1}</span>${this.escapeHtml(op.name)}</strong>
                    <small>${this.escapeHtml(op.description)}</small>
                    <small class="surface-op-reward">${rewards.map(item => this.escapeHtml(item)).join(" · ")}</small>
                </div>
                <div class="surface-op-side">
                    <span class="away-risk ${riskClass}">${op.risk}%</span>
                    <button class="btn-hud" data-surface-op="${this.escapeHtml(op.id)}" ${op.used ? "disabled" : ""}>${op.used ? "WORKED" : "RUN"}</button>
                </div>
            </div>`;
        }).join("");
        const mapMarkup = this.surfaceMap ? `
            <div class="surface-map-wrap">
                <canvas class="surface-map-canvas" id="surfaceMapCanvas" aria-label="Surface map of ${this.escapeHtml(body.name || "world")}"></canvas>
                <div class="surface-map-bar">
                    <span>SURFACE SCAN // ${this.escapeHtml(String(body.body_type || "unknown").replace(/_/g, " ").toUpperCase())}</span>
                    <span>${operations.length} SITES</span>
                </div>
                <div class="surface-map-hint">${selectedOp
                    ? `SELECTED // ${this.escapeHtml(selectedOp.name)} - RUN BELOW`
                    : "CLICK A SITE TO SELECT ITS OPERATION"}</div>
            </div>` : "";
        this.surfaceOps.style.display = "block";
        this.surfaceOps.innerHTML = `
            <div class="surface-header">
                <h4>SURFACE OPERATIONS // ${this.escapeHtml(body.name || "")}</h4>
                <span>${data.used_count}/${data.total_count} WORKED</span>
            </div>
            ${mapMarkup}
            <div class="surface-op-list">${rows || '<p class="panel-intro-text">No operations available.</p>'}</div>
        `;
        const mapCanvas = this.surfaceOps.querySelector("#surfaceMapCanvas");
        if (mapCanvas && this.surfaceMap) {
            this.surfaceMap.draw(mapCanvas, body, operations, this.surfaceSelectedOp);
            mapCanvas.addEventListener("click", event => {
                const site = this.surfaceMap.hitTest(mapCanvas, event);
                if (!site) return;
                this.surfaceSelectedOp = site.id;
                this.renderSurfaceOps();
                const row = this.surfaceOps.querySelector(`[data-surface-op="${site.id}"]`)?.closest(".surface-op-row");
                const card = this.surfaceOps.closest(".nav-target-card");
                if (row && card) {
                    const cardRect = card.getBoundingClientRect();
                    const rowRect = row.getBoundingClientRect();
                    if (rowRect.bottom > cardRect.bottom - 6) card.scrollTop += rowRect.bottom - cardRect.bottom + 6;
                    else if (rowRect.top < cardRect.top + 6) card.scrollTop -= cardRect.top - rowRect.top + 6;
                }
            });
            mapCanvas.addEventListener("mousemove", event => {
                mapCanvas.style.cursor = this.surfaceMap.hitTest(mapCanvas, event) ? "pointer" : "crosshair";
            });
        }
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
        const fontSize = Math.max(12, size * 0.24);
        const gradId = `vf-av-grad-${Math.abs(hash)}`;
        return `<svg viewBox="0 0 40 40" width="${size}" height="${size}" role="img" aria-label="${this.escapeHtml(name || "portrait")}">
            <defs>
                <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="${color}" stop-opacity="0.32"/>
                    <stop offset="100%" stop-color="#040912" stop-opacity="0.95"/>
                </linearGradient>
            </defs>
            <polygon points="10,2 30,2 38,10 38,30 30,38 10,38 2,30 2,10" fill="url(#${gradId})" stroke="${color}" stroke-width="1.2"/>
            <line x1="2" y1="20" x2="6" y2="20" stroke="${color}" stroke-width="1" opacity="0.8"/>
            <line x1="34" y1="20" x2="38" y2="20" stroke="${color}" stroke-width="1" opacity="0.8"/>
            <line x1="20" y1="2" x2="20" y2="6" stroke="${color}" stroke-width="1" opacity="0.8"/>
            <line x1="20" y1="34" x2="20" y2="38" stroke="${color}" stroke-width="1" opacity="0.8"/>
            <path d="M12,12 L20,7 L28,12" fill="none" stroke="${color}" stroke-width="1.4" opacity="0.9"/>
            <circle cx="20" cy="17" r="4.5" fill="${color}" opacity="0.85"/>
            <path d="M9,32 Q20,23 31,32" fill="none" stroke="${color}" stroke-width="1.6" opacity="0.75"/>
            <rect x="10" y="27" width="20" height="9" fill="#040912" stroke="${color}" stroke-width="0.8" rx="1"/>
            <text x="20" y="34.2" text-anchor="middle" font-size="${fontSize}" fill="#ffffff" font-family="'Cascadia Mono', Consolas, monospace" font-weight="700">${this.escapeHtml(initials)}</text>
        </svg>`;
    }

    renderEmpire() {
        if (!this.state || !this.researchSummary) return;
        const research = this.state.research || {};
        const active = research.active_project;
        const queue = research.queue || [];
        const queuedIds = new Set(queue);
        const queued = research.queued || [];
        this.researchSummary.innerHTML = (active
            ? `<strong>${this.escapeHtml(active.name)}</strong> — ${research.progress || 0}/${active.cost} points<br>Banked: ${research.points || 0}`
            : `No active project. Banked points: ${research.points || 0}`)
            + (queue.length ? `<br>Queue: ${queue.map(id => {
                const queuedProject = queued.find(project => project.id === id);
                return this.escapeHtml(queuedProject ? queuedProject.name : id);
            }).join(" → ")}` : "");
        this.researchProjects.innerHTML = (research.available || []).map(p => `
            <div class="research-row">
                <span>${this.escapeHtml(p.name)}<br><small>${this.escapeHtml(p.description)}</small></span>
                <span>${p.cost} pts</span>
                <button class="btn-hud" data-research="${this.escapeHtml(p.id)}">START</button>
                <button class="btn-hud btn-cyan" data-research-queue="${this.escapeHtml(p.id)}" ${queuedIds.has(p.id) ? "disabled" : ""}>${queuedIds.has(p.id) ? "QUEUED" : "QUEUE"}</button>
            </div>
        `).join("") + (queued.length ? `
            <div class="research-queue-header">QUEUED PROJECTS</div>
            ${queued.map(p => `
                <div class="research-row research-queue-row">
                    <span>${this.escapeHtml(p.name)}<br><small>${this.escapeHtml(p.description)}</small></span>
                    <span>${p.cost} pts</span>
                    <button class="btn-hud btn-amber" data-research-cancel="${this.escapeHtml(p.id)}">CANCEL</button>
                </div>
            `).join("")}
        ` : "");
        this.researchProjects.querySelectorAll("[data-research]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/research/start", { project_id: btn.getAttribute("data-research") }, "empire"))
        );
        this.researchProjects.querySelectorAll("[data-research-queue]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/research/queue", { project_id: btn.getAttribute("data-research-queue") }, "empire"))
        );
        this.researchProjects.querySelectorAll("[data-research-cancel]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/research/cancel", { project_id: btn.getAttribute("data-research-cancel") }, "empire"))
        );

        const outposts = this.state.outposts || [];
        this.outpostSummary.textContent = outposts.length
            ? `${outposts.length} outpost(s) producing each tick.`
            : "No outposts founded yet. Orbit a world and found one below.";
        this.renderOutpostBuild();
        const moduleCatalog = this.state.outpost_modules || {};
        const moduleOptions = Object.entries(moduleCatalog).map(([id, module]) =>
            `<option value="${this.escapeHtml(id)}">${this.escapeHtml(module.name)} (${Number(module.cost || 0)} CR)</option>`
        ).join("");
        const specCatalog = this.state.outpost_specializations || {};
        const crewList = this.state.crew || [];
        const crewById = new Map(crewList.map(member => [member.id, member]));
        const assignedCrew = new Set(outposts.flatMap(o => o.assigned_crew || []));
        const awayCrew = new Set(
            (this.state.away_report?.active || []).flatMap(mission => mission.crew_ids || [])
        );
        const availableCrew = crewList.filter(member =>
            member.status === "active" && !assignedCrew.has(member.id) && !awayCrew.has(member.id)
        );
        const crewOptions = availableCrew.map(member =>
            `<option value="${this.escapeHtml(member.id)}">${this.escapeHtml(member.name)} (${this.escapeHtml(member.role)} S${member.skill})</option>`
        ).join("");
        this.outpostList.innerHTML = outposts.map(o => {
            const assigned = (o.assigned_crew || [])
                .map(crewId => crewById.get(crewId))
                .filter(Boolean);
            const crewMult = Number(o.crew_multiplier || 1);
            const capacity = Number(o.crew_capacity || 3);
            const canAssign = availableCrew.length > 0 && assigned.length < capacity;
            const localShipyard = o.outpost_type === "shipyard" && o.system_id === this.state.ship.current_system_id;
            const specId = o.specialization || "";
            const specLabel = o.specialization_label || "None";
            const specUnlocked = Number(o.level) >= 3;
            const specOptions = Object.entries(specCatalog).map(([id, spec]) =>
                `<option value="${this.escapeHtml(id)}" ${id === specId ? "selected" : ""}>${this.escapeHtml(spec.label)} (${Number(spec.cost || 0)} CR)</option>`
            ).join("");
            const sameSystem = outposts.filter(candidate =>
                candidate.id !== o.id && candidate.system_id === o.system_id
            );
            const linkCap = Number(o.supply_capacity || 2);
            const sourceCanLink = !o.supply_hub_id && Number(o.supply_link_count || 0) === 0;
            const hubCandidates = sameSystem.filter(candidate =>
                sourceCanLink
                && !candidate.supply_hub_id
                && Number(candidate.supply_link_count || 0) < Number(candidate.supply_capacity || linkCap)
            );
            const hubOptions = hubCandidates.map(candidate =>
                `<option value="${this.escapeHtml(candidate.id)}">${this.escapeHtml(candidate.name)}</option>`
            ).join("");
            const supplyStatus = o.supply_hub_name
                ? `HUB: ${this.escapeHtml(o.supply_hub_name)} · x${Number(o.supply_multiplier || 1).toFixed(2)}`
                : Number(o.supply_link_count || 0)
                    ? `LINKS ${Number(o.supply_link_count)}/${linkCap} · x${Number(o.supply_multiplier || 1).toFixed(2)}`
                    : "LOCAL · x1.00";
            const supplyControls = o.supply_hub_name
                ? `<button class="btn-hud btn-amber" data-outpost-unlink="${this.escapeHtml(o.id)}">UNLINK</button>`
                : Number(o.supply_link_count || 0) > 0
                    ? `<span class="outpost-supply-status">${this.escapeHtml((o.supply_link_names || []).join(", "))}</span>`
                    : hubOptions
                        ? `<select data-outpost-hub-select="${this.escapeHtml(o.id)}">${hubOptions}</select>
                           <button class="btn-hud btn-cyan" data-outpost-link="${this.escapeHtml(o.id)}">LINK</button>`
                        : `<span class="outpost-supply-status">NO ELIGIBLE HUB</span>`;
            return `
            <div class="outpost-row"><span>${this.escapeHtml(o.name)} - LVL ${o.level} - POP ${this.compactCount(o.population)} / ${this.compactCount(o.population_capacity)} <span class="outpost-integrity">INT ${Math.round(Number(o.integrity || 0))}% · DEF ${Number(o.defense || 10)}</span>${localShipyard ? ` <span class="outpost-service-badge">SERVICES ONLINE</span>` : ""}</span>
            <span class="outpost-row-actions">
                ${Number(o.integrity || 0) < 100 ? `<button class="btn-hud btn-amber" data-outpost-repair="${this.escapeHtml(o.id)}">REPAIR (${Number(o.repair_cost || 100)} CR)</button>` : ""}
                <button class="btn-hud btn-amber" data-outpost-upgrade="${this.escapeHtml(o.id)}">UPGRADE</button>
            </span></div>
            <div class="outpost-module-bar">
                <select data-outpost-module-select="${this.escapeHtml(o.id)}">${moduleOptions}</select>
                <button class="btn-hud btn-green" data-outpost-module-install="${this.escapeHtml(o.id)}">INSTALL MODULE</button>
            </div>
            <div class="outpost-crew-bar">
                <span class="outpost-crew-mult">CREW ${assigned.length}/${capacity} · BONUS x${crewMult.toFixed(2)}</span>
                <select data-outpost-crew-select="${this.escapeHtml(o.id)}" ${canAssign ? "" : "disabled"}>
                    ${crewOptions || `<option value="">No available crew</option>`}
                </select>
                <button class="btn-hud btn-cyan" data-outpost-crew-assign="${this.escapeHtml(o.id)}" ${canAssign ? "" : "disabled"}>ASSIGN</button>
            </div>
            <div class="outpost-crew-list">
                ${assigned.length ? assigned.map(member => `
                    <span class="outpost-crew-chip">${this.escapeHtml(member.name)}
                        <button data-outpost-crew-recall="${this.escapeHtml(o.id)}" data-crew-id="${this.escapeHtml(member.id)}" title="Recall to ship">×</button>
                    </span>
                `).join("") : `<span class="outpost-crew-empty">No specialists stationed.</span>`}
            </div>
            <div class="outpost-spec-bar">
                <span class="outpost-spec-label">SPEC: ${this.escapeHtml(specLabel.toUpperCase())}</span>
                ${specUnlocked
                    ? `<select data-outpost-spec-select="${this.escapeHtml(o.id)}">${specOptions}</select>
                       <button class="btn-hud btn-purple" data-outpost-spec-set="${this.escapeHtml(o.id)}">SET</button>`
                    : `<span class="outpost-spec-locked">UNLOCKS AT LVL 3</span>`}
            </div>
            <div class="outpost-supply-bar">
                <span class="outpost-supply-label">SUPPLY: ${supplyStatus}</span>
                ${supplyControls}
            </div>
        `;
        }).join("");
        this.outpostList.querySelectorAll("[data-outpost-upgrade]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/outpost/upgrade", { outpost_id: btn.getAttribute("data-outpost-upgrade") }, "empire"))
        );
        this.outpostList.querySelectorAll("[data-outpost-repair]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/outpost/repair", {
                outpost_id: btn.getAttribute("data-outpost-repair"),
            }, "empire"))
        );
        this.outpostList.querySelectorAll("[data-outpost-module-install]").forEach(btn =>
            btn.addEventListener("click", () => {
                const outpostId = btn.getAttribute("data-outpost-module-install");
                const select = this.outpostList.querySelector(`[data-outpost-module-select="${outpostId}"]`);
                this.postAction("/api/outpost/module", { outpost_id: outpostId, module_id: select ? select.value : "" }, "empire");
            })
        );
        this.outpostList.querySelectorAll("[data-outpost-crew-assign]").forEach(btn =>
            btn.addEventListener("click", () => {
                const outpostId = btn.getAttribute("data-outpost-crew-assign");
                const select = this.outpostList.querySelector(`[data-outpost-crew-select="${outpostId}"]`);
                if (!select || !select.value) return;
                this.postAction("/api/outpost/crew", {
                    outpost_id: outpostId,
                    crew_id: select.value,
                    action: "assign",
                }, "empire");
            })
        );
        this.outpostList.querySelectorAll("[data-outpost-crew-recall]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/outpost/crew", {
                outpost_id: btn.getAttribute("data-outpost-crew-recall"),
                crew_id: btn.getAttribute("data-crew-id"),
                action: "recall",
            }, "empire"))
        );
        this.outpostList.querySelectorAll("[data-outpost-spec-set]").forEach(btn =>
            btn.addEventListener("click", () => {
                const outpostId = btn.getAttribute("data-outpost-spec-set");
                const select = this.outpostList.querySelector(`[data-outpost-spec-select="${outpostId}"]`);
                if (!select || !select.value) return;
                this.postAction("/api/outpost/specialize", {
                    outpost_id: outpostId,
                    specialization: select.value,
                }, "empire");
            })
        );
        this.outpostList.querySelectorAll("[data-outpost-link]").forEach(btn =>
            btn.addEventListener("click", () => {
                const outpostId = btn.getAttribute("data-outpost-link");
                const select = this.outpostList.querySelector(`[data-outpost-hub-select="${outpostId}"]`);
                if (!select || !select.value) return;
                this.postAction("/api/outpost/link", {
                    outpost_id: outpostId,
                    hub_id: select.value,
                }, "empire");
            })
        );
        this.outpostList.querySelectorAll("[data-outpost-unlink]").forEach(btn =>
            btn.addEventListener("click", () => this.postAction("/api/outpost/link", {
                outpost_id: btn.getAttribute("data-outpost-unlink"),
                action: "unlink",
            }, "empire"))
        );

        const leaders = this.state.faction_leaders || [];
        const wars = this.state.wars || [];
        const standings = this.state.ship.faction_standings || {};
        const allied = new Set(this.state.ship.allies || []);
        const tradePacts = new Set(this.state.ship.trade_pacts || []);
        const researchPacts = new Set(this.state.ship.research_pacts || []);
        const napUntil = this.state.ship.non_aggression_until || {};
        const currentTick = Number(this.state.time?.tick || 0);
        const eliminated = new Set(this.state.eliminated_factions || []);
        this.diplomacyList.innerHTML = leaders.map(l => {
            const standing = Number(standings[l.faction_id] || 0);
            const isEliminated = eliminated.has(l.faction_id);
            const isAllied = allied.has(l.faction_id);
            const isPact = tradePacts.has(l.faction_id);
            const isResearchPact = researchPacts.has(l.faction_id);
            const napRemaining = Math.max(0, Number(napUntil[l.faction_id] || 0) - currentTick);
            const isNap = napRemaining > 0;
            const ownWar = wars.find(w => w.active
                && (w.attacker_id === "sol_coalition" || w.defender_id === "sol_coalition")
                && (w.attacker_id === l.faction_id || w.defender_id === l.faction_id));
            const atWar = wars.some(w => w.active && (w.defender_id === l.faction_id || w.attacker_id === l.faction_id));
            const canAlly = !isEliminated && !isAllied && standing >= 70;
            const canPact = !isEliminated && !isPact && !ownWar && standing >= 40;
            const canResearchPact = !isEliminated && !isResearchPact && !ownWar && standing >= 60;
            const canNap = !isEliminated && !isNap && !isAllied && !ownWar
                && l.faction_id !== "sol_coalition" && standing >= 30;
            const petition = ownWar && Number(this.state.ship.credits || 0) >= 500;
            const creed = l.ideology ? `<br><small class="faction-creed" title="${this.escapeHtml(l.description || "")}">${this.escapeHtml(l.ideology)} · HQ: ${this.escapeHtml(l.headquarters_system || "unknown")}</small>` : "";
            return `<div class="diplomacy-row ${isEliminated ? "eliminated" : ""}">
                <span><strong>${this.escapeHtml(l.name)}</strong> (${this.escapeHtml(l.faction_id)})<br>
                <small>${this.escapeHtml(l.title)} — <span class="leader-behavior">${this.escapeHtml(l.behavior)}</span></small>${creed}</span>
                <span>standing ${standing}${isAllied ? " | ALLIED" : ""}${isPact ? " | PACT" : ""}${isResearchPact ? " | R&D" : ""}${isNap ? ` | NAP ${napRemaining}T` : ""}${atWar ? " | WAR" : ""}</span>
                <div class="diplomacy-actions">
                    <button class="btn-hud" data-diplo-action="improve" data-diplo-id="${this.escapeHtml(l.faction_id)}">IMPROVE</button>
                    <button class="btn-hud btn-green" data-diplo-action="gift" data-diplo-id="${this.escapeHtml(l.faction_id)}" ${isEliminated || Number(this.state.ship.credits || 0) < 300 ? "disabled" : ""}>GIFT 300</button>
                    <button class="btn-hud btn-amber" data-diplo-action="non_aggression" data-diplo-id="${this.escapeHtml(l.faction_id)}" ${canNap ? "" : "disabled"} title="${isNap ? `Non-aggression pact active for ${napRemaining} ticks` : ownWar ? "Unavailable during war" : "Requires standing 30+; blocks new Sol Coalition wars for 90 ticks"}">NAP</button>
                    <button class="btn-hud btn-cyan" data-diplo-action="trade_pact" data-diplo-id="${this.escapeHtml(l.faction_id)}" ${canPact ? "" : "disabled"} title="${isPact ? "Trade pact active" : ownWar ? "Unavailable during war" : "Requires standing 40+; improves buy and sell prices"}">PACT</button>
                    <button class="btn-hud btn-purple" data-diplo-action="research_pact" data-diplo-id="${this.escapeHtml(l.faction_id)}" ${canResearchPact ? "" : "disabled"} title="${isResearchPact ? "Research pact active" : ownWar ? "Unavailable during war" : "Requires standing 60+; +5% passive research"}">R&D</button>
                    <button class="btn-hud btn-purple" data-diplo-action="alliance" data-diplo-id="${this.escapeHtml(l.faction_id)}" ${canAlly ? "" : "disabled"} title="${isAllied ? "Already allied" : "Requires standing 70+ during this campaign"}">ALLY</button>
                    ${ownWar ? `<button class="btn-hud btn-amber" data-diplo-action="ceasefire" data-diplo-id="${this.escapeHtml(l.faction_id)}" ${petition ? "" : "disabled"} title="Envoy costs 500 cr">PETITION 500</button>` : ""}
                </div>
            </div>`;
        }).join("");
        this.diplomacyList.querySelectorAll("[data-diplo-action]").forEach(btn =>
            btn.addEventListener("click", () => this.handleDiplomacyAction(
                btn.getAttribute("data-diplo-id"), btn.getAttribute("data-diplo-action")
            ))
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
            const catIcons = {
                all: "◈", exploration: "✦", command: "⬡", commerce: "¤",
                combat: "⚔", diplomacy: "⚖", legacy: "★",
            };
            const buttonsHtml = [
                `<button class="codex-cat-filter ${activeCat === "all" ? "active" : ""}" data-category="all">◈ ALL (${totals.entries})</button>`,
                ...categories.map(c => `
                    <button class="codex-cat-filter ${activeCat === c.id ? "active" : ""}" data-category="${this.escapeHtml(c.id)}">
                        ${catIcons[c.id] || "◇"} ${this.escapeHtml(c.name.toUpperCase())} (${c.claimed}/${c.entries})
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
        const patrolTicks = Number(fleet.patrol_sweep_ticks || 6);
        const crewList = this.state.crew || [];
        const assignedCrew = new Set([
            ...(this.state.outposts || []).flatMap(o => o.assigned_crew || []),
            ...ships.map(ship => ship.captain_id).filter(Boolean),
        ]);
        const awayCrew = new Set(
            (this.state.away_report?.active || []).flatMap(mission => mission.crew_ids || [])
        );
        const availableCaptains = crewList.filter(member =>
            member.status === "active" && !assignedCrew.has(member.id) && !awayCrew.has(member.id)
        );
        const captainOptions = availableCaptains.map(member =>
            `<option value="${this.escapeHtml(member.id)}">${this.escapeHtml(member.name)} (${this.escapeHtml(member.role)} S${member.skill})</option>`
        ).join("");
        if (this.fleetUpkeepLine) {
            const localShipyard = (this.state.outposts || []).some(o =>
                o.outpost_type === "shipyard" && o.system_id === this.state.ship.current_system_id
            );
            this.fleetUpkeepLine.textContent = `${ships.length} escort(s) · upkeep ${Number(fleet.upkeep_per_month || 0)} cr/month${localShipyard ? " · SHIPYARD LINK" : ""}`;
        }
        const stance = String(fleet.battle_stance || this.state.ship.battle_stance || "balanced").toLowerCase();
        const stanceHints = {
            balanced: "Even damage and evasion.",
            aggressive: "+20% damage, -30% evasion.",
            defensive: "-30% damage, +35% evasion.",
        };
        if (this.fleetStanceHint) {
            this.fleetStanceHint.textContent = stanceHints[stance] || stanceHints.balanced;
        }
        if (this.fleetStanceRow) {
            this.fleetStanceRow.querySelectorAll("[data-fleet-stance]").forEach(btn => {
                const active = btn.getAttribute("data-fleet-stance") === stance;
                btn.classList.toggle("active", active);
                btn.setAttribute("aria-pressed", active ? "true" : "false");
                btn.onclick = () => this.postAction(
                    "/api/combat/stance",
                    { stance: btn.getAttribute("data-fleet-stance") },
                    "fleet"
                );
            });
        }
        if (!ships.length) {
            this.fleetShipRoster.innerHTML = `<p class="panel-intro-text">No escort warships. Commission one below at a drydock.</p>`;
        } else {
            this.fleetShipRoster.innerHTML = ships.map(ship => {
                const rank = ship.rank || "Green";
                const xp = Number(ship.experience || 0);
                const xpMax = Number(ship.experience_max || 300);
                const rankPct = Math.round(Number(ship.rank_progress ?? (xpMax ? xp / xpMax : 0)) * 100);
                const atAce = xp >= xpMax;
                const trainingCost = Number(ship.training_cost || 0);
                const canTrain = !atAce && Number(this.state.ship.credits || 0) >= trainingCost;
                const trainTitle = atAce
                    ? "Already an Ace"
                    : `Train +${ship.training_gain || 0} XP for ${trainingCost} cr`;
                const tacticalRole = String(ship.tactical_role || "screen").toLowerCase();
                const roleLabel = tacticalRole.toUpperCase();
                const nextRole = { screen: "strike", strike: "support", support: "screen" }[tacticalRole] || "screen";
                const roleTitle = {
                    screen: "Screen: +50% evasion, -25% damage",
                    strike: "Strike: +25% damage, -25% evasion",
                    support: "Support: repairs 4 integrity per exchange, -45% damage",
                }[tacticalRole] || "Squadron role";
                return `
                <div class="fleet-ship-card">
                    <div class="fleet-head"><strong>${this.escapeHtml(ship.name)}</strong> <span class="ship-role">${this.escapeHtml(ship.role.toUpperCase())}</span> <button type="button" class="fleet-role role-${this.escapeHtml(tacticalRole)}" data-escort-role="${this.escapeHtml(ship.id)}" data-next-role="${nextRole}" title="${this.escapeHtml(roleTitle)}">${this.escapeHtml(roleLabel)}</button></div>
                    <div class="fleet-sub">HULL ${ship.hull}/${ship.max_hull} | SHIELD ${ship.shield}/${ship.max_shield} | DMG ${ship.damage} | SYS ${this.escapeHtml(ship.assigned_system_id || "?")}</div>
                    <div class="fleet-veterancy">
                        <span class="fleet-rank rank-${this.escapeHtml(rank.toLowerCase())}">${this.escapeHtml(rank.toUpperCase())}</span>
                        <span class="fleet-xp-bar" title="${xp}/${xpMax} XP"><span class="fleet-xp-fill" style="width:${rankPct}%"></span></span>
                        <span class="fleet-xp-label">${xp}/${xpMax} XP</span>
                    </div>
                    <div class="fleet-service">SVC ${Number(ship.battles || 0)}B / ${Number(ship.kills || 0)}K / ${Number(ship.patrol_contacts || 0)}P / ${Number(ship.patrol_credits || 0)}CR</div>
                    <div class="fleet-captain-row">
                        <span>CPT ${this.escapeHtml(ship.captain_name || "NONE")}${ship.captain_role_label ? ` · ${this.escapeHtml(ship.captain_role_label.toUpperCase())}` : ""}${ship.captain_skill ? ` · S${Number(ship.captain_skill)}` : ""}</span>
                        ${ship.captain_id
                            ? `<button class="btn-hud btn-amber" data-escort-captain-recall="${this.escapeHtml(ship.id)}">RECALL</button>`
                            : `<select data-escort-captain-select="${this.escapeHtml(ship.id)}">${captainOptions || `<option value="">No available crew</option>`}</select>
                               <button class="btn-hud btn-cyan" data-escort-captain-assign="${this.escapeHtml(ship.id)}" ${availableCaptains.length ? "" : "disabled"}>ASSIGN</button>`}
                    </div>
                    <div class="fleet-value">${this.escapeHtml(String(ship.status || "").toUpperCase())}<br>${ship.assigned_system_id === this.state.ship.current_system_id ? "LOCAL" : `PATROL ${patrolTicks}T`}</div>
                    <div class="ship-actions">
                        <button class="btn-hud btn-amber" data-escort-repair="${this.escapeHtml(ship.id)}">REPAIR</button>
                        <button class="btn-hud btn-amber" data-escort-train="${this.escapeHtml(ship.id)}" ${canTrain ? "" : "disabled"} title="${this.escapeHtml(trainTitle)}">TRAIN (${trainingCost} CR)</button>
                        <button class="btn-hud btn-green" data-escort-sell="${this.escapeHtml(ship.id)}">SELL (${Number(ship.sale_value || 0)} CR)</button>
                        <button class="btn-hud" data-escort-dismiss="${this.escapeHtml(ship.id)}">DISMISS</button>
                    </div>
                </div>
            `;
            }).join("");
            this.fleetShipRoster.querySelectorAll("[data-escort-repair]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/repair", { amount: 60 }, "fleet"))
            );
            this.fleetShipRoster.querySelectorAll("[data-escort-train]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/train", { ship_id: btn.getAttribute("data-escort-train") }, "fleet"))
            );
            this.fleetShipRoster.querySelectorAll("[data-escort-role]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/role", {
                    ship_id: btn.getAttribute("data-escort-role"),
                    role: btn.getAttribute("data-next-role"),
                }, "fleet"))
            );
            this.fleetShipRoster.querySelectorAll("[data-escort-captain-assign]").forEach(btn =>
                btn.addEventListener("click", () => {
                    const shipId = btn.getAttribute("data-escort-captain-assign");
                    const select = this.fleetShipRoster.querySelector(`[data-escort-captain-select="${shipId}"]`);
                    if (!select || !select.value) return;
                    this.postAction("/api/fleet/escort/captain", {
                        ship_id: shipId,
                        crew_id: select.value,
                        action: "assign",
                    }, "fleet");
                })
            );
            this.fleetShipRoster.querySelectorAll("[data-escort-captain-recall]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/captain", {
                    ship_id: btn.getAttribute("data-escort-captain-recall"),
                    action: "recall",
                }, "fleet"))
            );
            this.fleetShipRoster.querySelectorAll("[data-escort-sell]").forEach(btn =>
                btn.addEventListener("click", () => this.postAction("/api/fleet/escort/sell", { ship_id: btn.getAttribute("data-escort-sell") }, "fleet"))
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

            const integrity = Math.max(0, Math.min(100, Number(d.integrity ?? 100)));
            const roleGlyph = /combat|attack|fighter/i.test(d.drone_type) ? "▲" : /scout|survey/i.test(d.drone_type) ? "◈" : "⬡";
            card.innerHTML = `
                <div class="drone-meta">
                    <strong class="drone-name"><span style="color:var(--console-gold);margin-right:4px;">${roleGlyph}</span>${this.escapeHtml(d.name)}</strong>
                    <span class="drone-sub">${this.escapeHtml(d.drone_type.toUpperCase())} // ${this.escapeHtml(d.assigned_system_id.toUpperCase())} [${this.escapeHtml(d.status.toUpperCase())}]</span>
                </div>
                <div class="vital-meter" style="margin:4px 0 6px;"><div class="meter-fill ${integrity > 50 ? 'fill-green' : 'fill-amber'}" style="width:${integrity}%;"></div></div>
                <div class="drone-stats">
                    LVL ${d.level ?? 1} // EFF ${(d.efficiency ?? 1).toFixed(2)} // INTEGRITY ${integrity}% // SORTIES ${d.sorties ?? 0}${d.specialty ? " // " + this.escapeHtml(d.specialty.toUpperCase()) : ""}
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
            const credits = Number((this.state.ship || {}).credits || 0);
            const hired = new Set((this.state.ship.fleet_drones || []).filter(d => d.drone_type === "mercenary").map(d => d.specialty));
            this.mercenaryRoster.innerHTML = `<h4 class="commission-title">MERCENARY CONTRACTS</h4>` + catalog.map(m => {
                const contracted = hired.has(m.specialty);
                const afford = credits >= Number(m.cost || 0);
                const label = contracted ? "CONTRACTED" : (afford ? "HIRE" : `${m.cost} CR`);
                const title = contracted ? "Already contracted" : (afford ? `Hire for ${m.cost} CR` : `Needs ${m.cost} CR`);
                return `
                <div class="depot-card fleet-procurement-row">
                    <div class="procurement-info"><h4>${this.escapeHtml(m.name)}</h4><small>${this.escapeHtml(m.description)}</small></div>
                    <span class="procurement-value">${m.cost} CR</span>
                    <div class="depot-actions">
                        <button class="btn-hud btn-cyan" data-merc="${this.escapeHtml(m.id)}" ${contracted || !afford ? "disabled" : ""} title="${this.escapeHtml(title)}">${this.escapeHtml(label)}</button>
                    </div>
                </div>
            `; }).join("");
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
        const setBonuses = (this.state.relic_set_bonuses) || {};
        const counts = {};
        for (const r of relics) counts[r.rarity] = (counts[r.rarity] || 0) + 1;
        const thresholds = { common: 3, rare: 3, epic: 2, legendary: 1 };
        const setRows = ["common", "rare", "epic", "legendary"].map(rarity => {
            const have = counts[rarity] || 0;
            const need = thresholds[rarity];
            const active = have >= need;
            return `<div class="relic-set-row ${active ? "is-active" : ""}"><span class="relic-set-name">${rarity.toUpperCase()}</span><span class="relic-set-count">${have}/${need}</span><span class="relic-set-status">${active ? "RESONANCE ACTIVE" : "collecting"}</span></div>`;
        }).join("");
        const bonusLine = Object.keys(setBonuses).length
            ? `<p class="relic-set-bonuses">Set bonuses: ${Object.entries(setBonuses).map(([k, v]) => (k === "shield_cap" ? ("+" + Math.round(v) + " MW " + k) : ("+" + Math.round(v * 100) + "% " + k))).join(", ")}</p>`
            : "";
        const fuseLadder = { common: "rare", rare: "epic", epic: "legendary" };
        const fuseButtons = Object.entries(fuseLadder).map(([rarity, target]) => {
            const have = counts[rarity] || 0;
            const canFuse = have >= 3;
            return `<button class="btn-relic-fuse" data-rarity="${rarity}" ${canFuse ? "" : "disabled"} title="Fuse 3 ${rarity} relics into 1 ${target} relic (${have}/3 ready)">FUSE 3×${rarity.toUpperCase()} → ${target.toUpperCase()}</button>`;
        }).join("");
        const fuseRow = `<div class="relic-fuse-row"><span class="relic-fuse-label">RESONANCE FORGE</span>${fuseButtons}</div>`;
        const setPanel = `<div class="relic-set-panel"><div class="relic-set-title">RELIC SET RESONANCE</div>${setRows}${bonusLine}${fuseRow}</div>`;
        this.relicsGrid.innerHTML = setPanel + relics.map(r => `
            <div class="relic-card">
                <div class="relic-header-row">
                    <strong class="relic-name">${this.escapeHtml(r.name)}</strong>
                    <span class="relic-rarity-pill rarity-${this.escapeHtml(r.rarity)}">${this.escapeHtml(r.rarity)}</span>
                </div>
                <p class="relic-desc">${this.escapeHtml(r.description)}</p>
            </div>
        `).join("");
        this.relicsGrid.querySelectorAll(".btn-relic-fuse").forEach(btn => {
            btn.addEventListener("click", () => this.handleFuseRelics(btn.getAttribute("data-rarity")));
        });
    }

    async handleFuseRelics(rarity) {
        if (!rarity || !this.state) return;
        this.sound.init();
        this.sound.playBeep(660);
        try {
            const res = await apiFetch("/api/relics/fuse", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ rarity }),
            });
            const data = await res.json();
            if (data.ok) {
                this.sound.playChime();
                this.appendLog(data.message || "Relics fused at the resonance forge.", "reward");
            } else {
                this.sound.playAlarm();
                this.appendLog(`[RELICS] ${data.message}`, "hazard");
            }
            if (data.state) {
                this.state = data.state;
                this.renderHUD();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Relic fusion failed: ${e.message}`, "hazard");
        }
    }

    appendLog(text, type = "system") {
        const line = document.createElement("div");
        line.className = `log-line log-${type}`;
        const timeStr = this.state?.tick != null ? `T+${String(this.state.tick).padStart(4, "0")}` : new Date().toLocaleTimeString();
        const tagMatch = String(text || "").match(/^\[([A-Z0-9_\-]+)\]\s*(.*)$/);
        if (tagMatch) {
            const tag = tagMatch[1];
            const rest = tagMatch[2];
            const tagClass = tag.toLowerCase().replace(/[^a-z0-9]/g, "");
            line.innerHTML = `<span class="log-time">[${timeStr}]</span><span class="log-tag tag-${tagClass}">[${this.escapeHtml(tag)}]</span> ${this.escapeHtml(rest)}`;
        } else {
            const defaultTag = type === "reward" ? "DATA" : (type === "hazard" ? "WARN" : "SYS");
            line.innerHTML = `<span class="log-time">[${timeStr}]</span><span class="log-tag tag-${defaultTag.toLowerCase()}">[${defaultTag}]</span> ${this.escapeHtml(text)}`;
        }
        this.flightLogStream.appendChild(line);
        this.flightLogStream.scrollTop = this.flightLogStream.scrollHeight;
    }

    // --- Actions ---

    async handleCombat(action) {
        this.sound.init();
        this.combatFlash = null;
        this.combatBeamUntil = 0;
        const prevShip = (this.state && this.state.ship) || {};
        const prevHull = Number(prevShip.hull || 0);
        const prevShield = Number(prevShip.shield || 0);
        const currentCombo = (this.state && this.state.ship) ? (this.state.ship.tactical_combo || 0) : 0;
        if (action === "fire_lasers" || action === "target_bridge") {
            if (currentCombo >= 2 || action === "target_bridge") {
                this.sound.playCritHit();
            } else {
                this.sound.playLaser();
            }
        } else if (action === "point_defense") {
            this.sound.playFlak();
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
                const at = this.lastShipPosition || this.mapCenter();
                const color = action === "target_bridge" ? "#c96b5a" : (action === "target_engines" ? "#e2c078" : (action === "fire_lasers" ? "#ffd166" : "#7fb7c9"));
                const count = action === "target_bridge" ? 28 : (action === "fire_lasers" ? 20 : 12);
                if (action === "point_defense") {
                    this.particles?.flakBurst?.(at.x, at.y, 28, "#e2c078");
                } else {
                    this.particles?.burst?.(at.x, at.y, count, color, 190);
                    this.particles?.ring?.(at.x, at.y, color, 75, 0.55);
                }
                if (action === "target_bridge" || currentCombo >= 2) {
                    this.particles?.ionArc?.(at.x - 24, at.y - 12, at.x + 24, at.y + 12, "#7fb7c9");
                }
                this.combatBeamUntil = performance.now() + 180;
                this.combatFlash = {
                    action: action,
                    target: (action === "shield_absorb" || action === "evasive_burn" || action === "flee" || action === "point_defense")
                        ? "player" : "enemy",
                    color: action === "flee" ? "#a98bbd" : color,
                    fired: false,
                };
                this.appendLog(json.message, "reward");
            } else {
                this.appendLog(`[COMBAT] ${json.message}`, "hazard");
            }
            this.state = json.state;
            const ship = (json.state && json.state.ship) || null;
            if (ship) {
                const hull = Number(ship.hull || 0);
                const shield = Number(ship.shield || 0);
                if (hull < prevHull) this.sound.playHullDamage();
                else if (shield < prevShield) this.sound.playShieldDeflect();
            }
            this.renderHUD();
        } catch (e) {
            this.appendLog(`[ERROR] Tactical maneuver failed: ${e.message}`, "hazard");
        }
    }

    async handleFabricate(type) {
        this.sound?.init();
        this.sound?.playBeep(440);
        try {
            const res = await apiFetch("/api/fabricate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ munitions_type: type })
            });
            const json = await res.json();
            if (json.ok) {
                this.sound?.playChime();
                this.appendLog(json.message, "reward");
            } else {
                this.sound?.playAlarm?.();
                this.appendLog(`[FABRICATION] ${json.message}`, "hazard");
            }
            this.state = json.state;
            this.renderHUD();
        } catch (e) {
            this.appendLog(`[ERROR] Field fabrication failed: ${e.message}`, "hazard");
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
                const at = this.lastShipPosition || this.mapCenter();
                this.particles?.ring(at.x, at.y, "#7fb7c9", 120, 0.85);
                this.particles?.burst(at.x, at.y, 8, "#9fe6ff", 55);
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
        this.sound.playQuantumWarp();
        try {
            const res = await apiFetch("/api/jump", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target: this.selectedTarget.id })
            });
            const json = await res.json();
            if (json.ok) {
                const at = this.mapCenter();
                this.particles?.burst(at.x, at.y, 30, "#a98bbd", 240);
                this.particles?.ring(at.x, at.y, "#a98bbd", 180, 0.9);
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

    async handleCustomsResolve(action) {
        this.sound.init();
        this.sound.playBeep(440, 0.08, "triangle");
        try {
            const res = await apiFetch("/api/customs/resolve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: action }),
            });
            const data = await res.json();
            if (data.ok) {
                if (action === "bribe") this.sound.playCashRegister();
                else if (action === "flee") this.sound.playQuantumWarp();
                else this.sound.playChime();
                this.appendLog(data.message || "Customs encounter resolved.", "system");
            } else {
                this.sound.playAlarm();
                this.appendLog(`[ERROR] ${data.message}`, "hazard");
            }
            if (data.state) {
                this.state = data.state;
                this.renderHUD();
            }
        } catch (e) {
            this.appendLog(`[ERROR] Customs resolution failed: ${e.message}`, "hazard");
        }
    }

    async handleOverhaul() {
        this.sound.init();
        this.sound.playBeep(750);
        try {
            const res = await apiFetch("/api/overhaul", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({})
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
            this.appendLog(`[ERROR] Overhaul failed: ${e.message}`, "hazard");
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
        let ox = 0;
        let oy = 0;
        if (fromBody) {
            ox = (fromBody.orbit_radius || 0) * Math.cos(fromBody.current_angle || 0);
            oy = (fromBody.orbit_radius || 0) * Math.sin(fromBody.current_angle || 0);
        } else if (this.state?.ship?.waypoint_au) {
            const wAu = Number(this.state.ship.waypoint_au);
            const wAng = Number(this.state.ship.waypoint_angle || 0);
            ox = wAu * Math.cos(wAng);
            oy = wAu * Math.sin(wAng);
        }
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

            this.targetType.textContent = `TARGET: ${this.bodyTypeLabel(b)}`;
            this.targetName.textContent = b.name;
            this.targetDist.textContent = `${distAu.toFixed(2)} AU (ORBIT ${b.orbit_radius.toFixed(2)} AU)`;
            const survey = this.state.survey;
            const surveyNote = survey && survey.total ? ` | SURVEY ${survey.scanned}/${survey.total}` : "";
            this.targetDesc.textContent = (b.scan_completed ? b.scan_discovery : "Uncharted body. Orbital sensor sweep required.") + surveyNote;
            this.btnOrbitTarget.style.display = "inline-block";
            this.btnJumpTarget.style.display = "none";
            if (this.btnHailTarget) this.btnHailTarget.style.display = "none";
            if (this.btnClearTarget) this.btnClearTarget.style.display = "inline-block";
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
            if (this.targetCapacity) {
                const capacity = Number(b.population_capacity ?? 0);
                const devastation = Number(b.devastation ?? 0);
                const remaining = Math.max(0, Math.round(capacity * (1 - DEVASTATION_CAPACITY_LOSS * devastation / 100)));
                this.targetCapacity.textContent = capacity > 0
                    ? `${this.compactCount(remaining)} / ${this.compactCount(capacity)}`
                    : "None";
            }
            if (this.targetTech) {
                this.targetTech.textContent = `TL ${Number(b.tech_level ?? 1)}`;
            }
            this.targetMoons.textContent = `${(b.moons || []).length}`;
            if (this.targetFaction) this.targetFaction.textContent = b.faction || "Unclaimed";
            if (this.targetPopulation) {
                const pop = Number(b.population || 0);
                if (pop <= 0) {
                    this.targetPopulation.textContent = "Uninhabited";
                } else {
                    const tier = pop < 10000 ? "Outpost" : (pop < 1000000 ? "Colony" : (pop < 50000000 ? "Settlement" : (pop < 1000000000 ? "Metropolis" : "Mega-Ecumenopolis")));
                    this.targetPopulation.textContent = `${this.compactCount(pop)} [${tier.toUpperCase()}]`;
                }
            }
            if (this.targetGovernment) this.targetGovernment.textContent = b.government || "None";
            if (this.targetDevastation) {
                const devastation = Number(b.devastation || 0);
                const capacityLoss = Math.round(devastation * DEVASTATION_CAPACITY_LOSS);
                this.targetDevastation.textContent = devastation > 0
                    ? `${devastation.toFixed(1)}% (CAP -${capacityLoss}%)`
                    : "None";
                this.targetDevastation.classList.toggle("is-devastated", devastation >= 25);
            }
            this.targetResources.innerHTML = (b.resources || []).map(r => `<span>${this.escapeHtml(r)}</span>`).join("");
            if (this.btnLandTarget) {
                this.btnLandTarget.style.display = b.landable ? "inline-block" : "none";
                const canLand = b.landable && this.state.ship.orbiting_body_id === b.id && this.state.ship.landed_body_id !== b.id && !travel;
                this.btnLandTarget.disabled = !canLand;
                this.btnLandTarget.textContent = this.state.ship.landed_body_id === b.id ? "LANDED" : "LAND ON SURFACE";
            }
            const bodyDevastation = Number(b.devastation || 0);
            const canReconstruct = (
                !travel
                && bodyDevastation > 0
                && Number(b.population || 0) > 0
                && (this.state.ship.orbiting_body_id === b.id || this.state.ship.landed_body_id === b.id)
            );
            const missingRelief = RELIEF_CARGO.filter(([item, quantity]) =>
                Number((this.state.ship.cargo || {})[item] || 0) < quantity
            );
            if (this.btnRebuildTarget) {
                this.btnRebuildTarget.style.display = canReconstruct ? "inline-block" : "none";
                this.btnRebuildTarget.disabled = !canReconstruct || Number(this.state.ship.credits || 0) < RECONSTRUCTION_CREDIT_COST;
                this.btnRebuildTarget.textContent = `REBUILD WORLD (${RECONSTRUCTION_CREDIT_COST} CR)`;
                this.btnRebuildTarget.title = canReconstruct
                    ? "Spend credits to remove 20 devastation from this world"
                    : "Orbit or land on a devastated inhabited world to rebuild it";
            }
            if (this.btnReliefTarget) {
                this.btnReliefTarget.style.display = canReconstruct ? "inline-block" : "none";
                this.btnReliefTarget.disabled = !canReconstruct || missingRelief.length > 0;
                this.btnReliefTarget.textContent = missingRelief.length
                    ? `RELIEF NEEDS ${missingRelief.map(([item, quantity]) => `${quantity} ${item}`).join(", ")}`
                    : "DELIVER RELIEF";
                this.btnReliefTarget.title = missingRelief.length
                    ? "Load the missing relief supplies first"
                    : "Spend medicines, hydroponics and fuel to remove 40 devastation";
            }
            const mega = this.state.megastructure;
            if (this.btnRestoreTarget) {
                const applies = Boolean(mega && mega.restorable && mega.body_id === b.id);
                this.btnRestoreTarget.style.display = applies ? "inline-block" : "none";
                this.btnRestoreTarget.disabled = !applies || !mega.can_restore;
                this.btnRestoreTarget.textContent = applies && mega.complete
                    ? "MEGASTRUCTURE ONLINE"
                    : applies
                        ? `RESTORE (${Number(mega.cost || 0)} CR)`
                        : "RESTORE MEGASTRUCTURE";
                this.btnRestoreTarget.title = applies
                    ? (mega.complete
                        ? "This megastructure is already restored"
                        : mega.can_restore
                            ? mega.label
                            : "Orbit the structure with enough credits")
                    : "Select a restorable megastructure";
            }
            const salvage = inOrbitHere ? this.state.salvage_site : null;
            if (this.btnSalvageTarget) {
                this.btnSalvageTarget.style.display = salvage ? "inline-block" : "none";
                this.btnSalvageTarget.disabled = !salvage;
                this.btnSalvageTarget.textContent = salvage ? "BOARD DERELICT" : "NO DERELICT";
            }
            if (this.salvageInfo) {
                if (salvage) {
                    const currentStrategy = this.salvageStrategy || "balanced";
                    const baseRisk = Math.max(5, Math.round((salvage.danger || 0) * 100));
                    const estRisk = currentStrategy === "cautious" ? Math.max(2, Math.round(baseRisk * 0.5)) : (currentStrategy === "aggressive" ? Math.min(85, baseRisk + 15) : baseRisk);
                    this.salvageInfo.style.display = "block";
                    this.salvageInfo.innerHTML = `
                        <div class="salvage-header">
                            <span class="salvage-title">DERELICT // ${this.escapeHtml(salvage.name)}</span>
                            <span class="salvage-risk">RISK ~${estRisk}%</span>
                        </div>
                        <div class="salvage-strategy-selector" role="group" aria-label="Salvage Strategy">
                            <button class="btn-salvage-strat ${currentStrategy === "cautious" ? "active" : ""}" data-strategy="cautious" title="Safe extraction: -50% risk, guaranteed minimal hull damage">CAUTIOUS</button>
                            <button class="btn-salvage-strat ${currentStrategy === "balanced" ? "active" : ""}" data-strategy="balanced" title="Standard boarding sweep">BALANCED</button>
                            <button class="btn-salvage-strat ${currentStrategy === "aggressive" ? "active" : ""}" data-strategy="aggressive" title="Heavy breach: +50% credits, bonus cargo, +heat">HEAVY (+50% CR)</button>
                            <button class="btn-salvage-strat ${currentStrategy === "scientific" ? "active" : ""}" data-strategy="scientific" title="Sensor reverse-engineering: +35 Research Data, +XP">ANALYZE (+RES)</button>
                        </div>
                        <div class="salvage-rewards-row">
                            <span>YIELD: <strong>${salvage.credits} CR + ${salvage.cargo_quantity}x ${this.escapeHtml(salvage.cargo_item)}</strong></span>
                        </div>
                    `;
                    this.salvageInfo.querySelectorAll(".btn-salvage-strat").forEach(btn => {
                        btn.addEventListener("click", (e) => {
                            e.stopPropagation();
                            this.salvageStrategy = btn.getAttribute("data-strategy");
                            this.updateTargetCard();
                        });
                    });
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
        } else if (this.selectedType === "captain") {
            if (this.targetDevastation) this.targetDevastation.classList.remove("is-devastated");
            this.transitPreviewBodyId = null;
            this.transitPreviewAt = 0;
            const captain = (this.state.ai_captains || []).find(c => c.id === this.selectedTarget.id);
            if (!captain) {
                this.selectedTarget = null;
                return this.updateTargetCard();
            }
            this.selectedTarget = captain;
            this.targetType.textContent = `TARGET: ${String(captain.archetype || "unknown").toUpperCase()} HULL`;
            this.targetName.textContent = captain.name;
            this.targetDist.textContent = `${String(captain.system_id).toUpperCase()} // TRUST ${captain.trust} // STANDING ${captain.standing}`;
            this.targetDesc.textContent = captain.description || "An independent hull running its own agenda.";
            const cargo = Object.entries(captain.cargo || {}).map(([k, v]) => `${k} x${v}`).join(", ") || "empty hold";
            this.targetGravity.textContent = `${captain.hull}/${captain.max_hull} hull`;
            this.targetAtmosphere.textContent = captain.ally ? "allied" : (captain.hired ? "hired" : "independent");
            this.targetTemp.textContent = `DMG ${captain.damage}`;
            if (this.targetHabitability) this.targetHabitability.textContent = "--";
            if (this.targetCapacity) this.targetCapacity.textContent = cargo;
            if (this.targetTech) this.targetTech.textContent = "--";
            this.targetMoons.textContent = "--";
            if (this.targetFaction) this.targetFaction.textContent = captain.archetype;
            if (this.targetPopulation) this.targetPopulation.textContent = `${captain.credits} cr`;
            if (this.targetGovernment) this.targetGovernment.textContent = "--";
            if (this.targetDevastation) this.targetDevastation.textContent = "--";
            this.targetResources.innerHTML = "";
            this.btnOrbitTarget.style.display = "none";
            this.btnQuantumTarget.style.display = "none";
            this.btnJumpTarget.style.display = "none";
            this.btnLandTarget.style.display = "none";
            this.btnSalvageTarget.style.display = "none";
            this.btnScoopFuel.style.display = "none";
            if (this.btnRebuildTarget) this.btnRebuildTarget.style.display = "none";
            if (this.btnReliefTarget) this.btnReliefTarget.style.display = "none";
            if (this.salvageInfo) this.salvageInfo.style.display = "none";
            if (this.transitPlan) this.transitPlan.style.display = "none";
            if (this.btnHailTarget) {
                this.btnHailTarget.style.display = "inline-block";
                this.btnHailTarget.disabled = false;
            }
            if (this.btnClearTarget) this.btnClearTarget.style.display = "inline-block";
        } else if (this.selectedType === "point") {
            if (this.targetDevastation) this.targetDevastation.classList.remove("is-devastated");
            this.transitPreviewBodyId = null;
            this.transitPreviewAt = 0;
            const p = this.selectedTarget;
            const orbBody = this.state.orbiting_body || (this.state.current_system?.bodies || []).find(x => x.id === this.state.ship?.orbiting_body_id) || null;
            // In open space the ship's anchor is the origin, not the star.
            const originAu = orbBody ? Number(orbBody.orbit_radius ?? 0) : Number(this.state.ship?.waypoint_au ?? 0);
            const originAngle = orbBody ? Number(orbBody.current_angle ?? 0) : Number(this.state.ship?.waypoint_angle ?? 0);
            const dx = Math.cos(p.angle) * p.au - Math.cos(originAngle) * originAu;
            const dy = Math.sin(p.angle) * p.au - Math.sin(originAngle) * originAu;
            const distAu = Math.max(0, Math.hypot(dx, dy));
            const engPwr = this.state.ship?.power?.engines ?? 25;
            const piloting = Number(this.state.character?.skills?.piloting ?? 1);
            const engineFactor = Math.max(0.4, engPwr / 25.0) * (1.0 + Math.max(0, piloting - 1) * 0.04);
            const estTicks = Math.max(1, Math.ceil(distAu / Math.max(0.35, 1.15 * engineFactor)));
            this.targetType.textContent = "TARGET: OPEN SPACE";
            this.targetName.textContent = `VECTOR ${p.au.toFixed(2)} AU`;
            this.targetDist.textContent = `${distAu.toFixed(2)} AU TRANSIT // BEARING ${(p.angle * 180 / Math.PI).toFixed(0)} DEG`;
            this.targetDesc.textContent = "Empty void: no body, no orbit. Hold station here to cut a lane, lie low, or wait out a patrol.";
            this.targetGravity.textContent = "--";
            this.targetAtmosphere.textContent = "vacuum";
            this.targetTemp.textContent = "--";
            if (this.targetHabitability) this.targetHabitability.textContent = "--";
            if (this.targetCapacity) this.targetCapacity.textContent = "--";
            if (this.targetTech) this.targetTech.textContent = "--";
            this.targetMoons.textContent = "0";
            if (this.targetFaction) this.targetFaction.textContent = "Unclaimed";
            if (this.targetPopulation) this.targetPopulation.textContent = "Uninhabited";
            if (this.targetGovernment) this.targetGovernment.textContent = "None";
            if (this.targetDevastation) this.targetDevastation.textContent = "None";
            this.targetResources.innerHTML = "";
            const hasTravel = Boolean(travel);
            this.btnOrbitTarget.style.display = "inline-block";
            this.btnOrbitTarget.disabled = hasTravel;
            this.btnOrbitTarget.textContent = hasTravel ? "TRANSIT LOCKED" : `MOVE TO VECTOR (${estTicks}T)`;
            this.btnOrbitTarget.title = "Sublight transit to this empty-space vector; the ship holds station on arrival.";
            this.btnQuantumTarget.style.display = "inline-block";
            this.btnQuantumTarget.disabled = hasTravel;
            this.btnQuantumTarget.textContent = hasTravel ? "TRANSIT LOCKED" : "QUANTUM VECTOR (1T)";
            this.btnJumpTarget.style.display = "none";
            this.btnLandTarget.style.display = "none";
            this.btnSalvageTarget.style.display = "none";
            this.btnScoopFuel.style.display = "none";
            if (this.btnRebuildTarget) this.btnRebuildTarget.style.display = "none";
            if (this.btnReliefTarget) this.btnReliefTarget.style.display = "none";
            if (this.salvageInfo) this.salvageInfo.style.display = "none";
            if (this.transitPlan) this.transitPlan.style.display = "none";
            if (this.btnHailTarget) this.btnHailTarget.style.display = "none";
            if (this.btnClearTarget) this.btnClearTarget.style.display = "inline-block";
        } else if (this.selectedType === "system") {
            if (this.targetDevastation) this.targetDevastation.classList.remove("is-devastated");
            this.transitPreviewBodyId = null;
            this.transitPreviewAt = 0;
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
            if (this.targetCapacity) this.targetCapacity.textContent = "--";
            if (this.targetTech) this.targetTech.textContent = "--";
            this.targetMoons.textContent = factionName;
            if (this.targetFaction) this.targetFaction.textContent = factionName || "Unclaimed";
            if (this.targetPopulation) this.targetPopulation.textContent = "--";
            if (this.targetDevastation) this.targetDevastation.textContent = "--";
            if (this.targetGovernment) this.targetGovernment.textContent = "--";
            this.targetResources.innerHTML = "";
            if (this.btnLandTarget) this.btnLandTarget.style.display = "none";
            if (this.btnSalvageTarget) this.btnSalvageTarget.style.display = "none";
            if (this.btnScoopFuel) this.btnScoopFuel.style.display = "none";
            if (this.btnRebuildTarget) this.btnRebuildTarget.style.display = "none";
            if (this.btnReliefTarget) this.btnReliefTarget.style.display = "none";
            if (this.salvageInfo) this.salvageInfo.style.display = "none";
            if (this.btnQuantumTarget) this.btnQuantumTarget.style.display = "none";
            this.btnOrbitTarget.style.display = "none";
            this.btnJumpTarget.style.display = "inline-block";
            this.btnJumpTarget.disabled = (!isConn || s.id === curSys.id);
            this.btnJumpTarget.textContent = (s.id === curSys.id) ? "CURRENT LOCATION" : (isConn ? "EXECUTE HYPERSPACE JUMP" : "OUT OF HYPERLANE RANGE");
            if (this.btnHailTarget) this.btnHailTarget.style.display = "none";
            if (this.btnClearTarget) this.btnClearTarget.style.display = "inline-block";
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
        let lastDraw = 0;
        const render = timestamp => {
            if (!document.hidden) {
                const state = this.state;
                const idle = Boolean(state?.time?.is_paused)
                    && !state?.active_combat
                    && !state?.travel
                    && !state?.ship?.travel
                    && !this.travelAnimation;
                if (!idle || timestamp - lastDraw >= IDLE_FRAME_MS) {
                    this.drawRadar();
                    lastDraw = timestamp;
                }
            }
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
        const dustFilament = ctx.createRadialGradient(w * 0.35, h * 0.45, 0, w * 0.35, h * 0.45, Math.max(w, h) * 0.55);
        dustFilament.addColorStop(0, "rgba(169, 139, 189, 0.04)");
        dustFilament.addColorStop(0.5, "rgba(127, 183, 201, 0.025)");
        dustFilament.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = dustFilament;
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

        // Pan physics & smooth camera focus interpolation
        if (this.targetPanX !== null && this.targetPanY !== null) {
            this.panX += (this.targetPanX - this.panX) * 0.14;
            this.panY += (this.targetPanY - this.panY) * 0.14;
            if (Math.hypot(this.targetPanX - this.panX, this.targetPanY - this.panY) < 0.6) {
                this.panX = this.targetPanX;
                this.panY = this.targetPanY;
                this.targetPanX = null;
                this.targetPanY = null;
            }
        } else if (!this.isDragging && (Math.abs(this.panVx) > 0.08 || Math.abs(this.panVy) > 0.08)) {
            this.panX += this.panVx;
            this.panY += this.panVy;
            this.panVx *= 0.90;
            this.panVy *= 0.90;
        } else if (!this.isDragging) {
            this.panVx = 0;
            this.panVy = 0;
        }

        this.particles?.update();
        ctx.setTransform(this.dpr || 1, 0, 0, this.dpr || 1, 0, 0);
        ctx.clearRect(0, 0, w, h);
        this.ensureRadarBackdrop(w, h);
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "source-over";

        // Parallax deep-space backdrop shift (factor 0.08)
        const bgParallax = 0.08;
        const offX = ((this.panX * bgParallax) % w + w) % w - w;
        const offY = ((this.panY * bgParallax) % h + h) % h - h;
        for (let dx = offX; dx < w; dx += w) {
            for (let dy = offY; dy < h; dy += h) {
                ctx.drawImage(this.radarBackdrop, dx, dy, w, h);
            }
        }

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
        if (this.state?.active_combat) this.drawCombatVisual();
    }

    // A close-range tactical view: two hulls, engine plumes, a firing beam and impact
    // particles. It is visual-only; the authoritative bars and buttons sit above it.
    drawCombatVisual() {
        if (!this.combatCanvas || !this.state?.active_combat) return;
        const canvas = this.combatCanvas;
        const dpr = Math.min(2, window.devicePixelRatio || 1);
        const cssW = Math.max(320, Math.round(canvas.clientWidth || 440));
        const cssH = Math.round(cssW * 0.26);
        if (canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
            canvas.width = Math.round(cssW * dpr);
            canvas.height = Math.round(cssH * dpr);
        }
        const ctx = canvas.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        const bg = ctx.createLinearGradient(0, 0, 0, cssH);
        bg.addColorStop(0, "#0a1424");
        bg.addColorStop(1, "#04070d");
        ctx.fillStyle = bg;
        ctx.fillRect(0, 0, cssW, cssH);
        const seed = this.captainHash(String(this.state.active_combat.enemy_name || "hostile"));
        for (let i = 0; i < 46; i++) {
            const sx = ((seed + i * 97) % 1000) / 1000 * cssW;
            const sy = ((seed + i * 193) % 1000) / 1000 * cssH;
            ctx.fillStyle = i % 9 === 0 ? "rgba(201, 163, 90, 0.8)" : "rgba(233, 240, 247, 0.45)";
            ctx.fillRect(sx, sy, i % 7 === 0 ? 1.6 : 1, i % 7 === 0 ? 1.6 : 1);
        }
        const player = { x: cssW * 0.17, y: cssH * 0.52 };
        const enemy = { x: cssW * 0.83, y: cssH * 0.48 };
        this.combatScene = { player, enemy, w: cssW, h: cssH };
        ctx.save();
        ctx.strokeStyle = "rgba(127, 183, 201, 0.22)";
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 4]);
        ctx.beginPath();
        ctx.moveTo(player.x + 16, player.y);
        ctx.lineTo(enemy.x - 16, enemy.y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.strokeStyle = "rgba(224, 122, 102, 0.35)";
        ctx.beginPath();
        ctx.arc(enemy.x, enemy.y, cssH * 0.30, 0, Math.PI * 2);
        ctx.stroke();

        // Tactical Targeting Brackets around Enemy Ship
        ctx.save();
        ctx.strokeStyle = "rgba(201, 107, 90, 0.75)";
        ctx.lineWidth = 1.4;
        const boxS = cssH * 0.28;
        const cornerL = boxS * 0.35;
        // Top-left
        ctx.beginPath();
        ctx.moveTo(enemy.x - boxS, enemy.y - boxS + cornerL);
        ctx.lineTo(enemy.x - boxS, enemy.y - boxS);
        ctx.lineTo(enemy.x - boxS + cornerL, enemy.y - boxS);
        ctx.stroke();
        // Top-right
        ctx.beginPath();
        ctx.moveTo(enemy.x + boxS - cornerL, enemy.y - boxS);
        ctx.lineTo(enemy.x + boxS, enemy.y - boxS);
        ctx.lineTo(enemy.x + boxS, enemy.y - boxS + cornerL);
        ctx.stroke();
        // Bottom-left
        ctx.beginPath();
        ctx.moveTo(enemy.x - boxS, enemy.y + boxS - cornerL);
        ctx.lineTo(enemy.x - boxS, enemy.y + boxS);
        ctx.lineTo(enemy.x - boxS + cornerL, enemy.y + boxS);
        ctx.stroke();
        // Bottom-right
        ctx.beginPath();
        ctx.moveTo(enemy.x + boxS - cornerL, enemy.y + boxS);
        ctx.lineTo(enemy.x + boxS, enemy.y + boxS);
        ctx.lineTo(enemy.x + boxS, enemy.y + boxS - cornerL);
        ctx.stroke();
        // Target acquisition crosshair pip & telemetry readouts
        ctx.fillStyle = "rgba(255, 120, 100, 0.9)";
        ctx.beginPath(); ctx.arc(enemy.x, enemy.y, 2, 0, Math.PI * 2); ctx.fill();
        ctx.font = "12px 'Cascadia Mono', Consolas, monospace";
        ctx.textAlign = "center";
        ctx.fillStyle = "rgba(201, 107, 90, 0.85)";
        ctx.fillText("LOCK: TGT-01", enemy.x, enemy.y - boxS - 6);
        ctx.fillStyle = "rgba(127, 183, 201, 0.75)";
        ctx.fillText("DIST: 1.4M KM", enemy.x, enemy.y + boxS + 14);
        ctx.restore();
        ctx.restore();
        this.combatFx?.trail(player.x - 12, player.y, 0, "#8fd8ff", 0.8);
        this.combatFx?.trail(enemy.x + 12, enemy.y, Math.PI, "#e07a66", 0.7);
        if (Number(this.state.active_combat?.enemy_hull || 0) < Number(this.state.active_combat?.enemy_max_hull || 1) * 0.4) {
            if (Math.random() < 0.35) {
                this.combatFx?.trail(enemy.x + (Math.random() - 0.5) * 16, enemy.y + (Math.random() - 0.5) * 16, Math.PI + (Math.random() - 0.5) * 0.6, "#ff6b5b", 0.6);
            }
        }
        if (performance.now() < this.combatBeamUntil) {
            ctx.save();
            ctx.globalCompositeOperation = "lighter";
            // Volumetric ambient bloom sheath
            ctx.strokeStyle = "rgba(255, 209, 102, 0.25)";
            ctx.shadowColor = "#ffd166";
            ctx.shadowBlur = 14;
            ctx.lineWidth = 6;
            ctx.beginPath();
            ctx.moveTo(player.x + 13, player.y);
            ctx.lineTo(enemy.x - 13, enemy.y);
            ctx.stroke();

            // High-energy radiant plasma beam
            ctx.strokeStyle = "#ffd166";
            ctx.shadowBlur = 8;
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(player.x + 13, player.y);
            ctx.lineTo(enemy.x - 13, enemy.y);
            ctx.stroke();

            // Intense ionizing core with micro-jitter
            const jY = (Math.random() - 0.5) * 1.2;
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1.2;
            ctx.shadowBlur = 2;
            ctx.beginPath();
            ctx.moveTo(player.x + 13, player.y);
            ctx.lineTo((player.x + enemy.x) * 0.5, (player.y + enemy.y) * 0.5 + jY);
            ctx.lineTo(enemy.x - 13, enemy.y);
            ctx.stroke();

            // Firing muzzle flash at player prow
            const muzzle = ctx.createRadialGradient(player.x + 13, player.y, 1, player.x + 13, player.y, 11);
            muzzle.addColorStop(0, "#ffffff");
            muzzle.addColorStop(0.45, "#ffd166");
            muzzle.addColorStop(1, "rgba(255, 209, 102, 0)");
            ctx.fillStyle = muzzle;
            ctx.beginPath();
            ctx.arc(player.x + 13, player.y, 11, 0, Math.PI * 2);
            ctx.fill();

            // Shield deflection ripple arc if target shield is active
            if (Number(this.state.active_combat?.enemy_shield || 0) > 0) {
                ctx.strokeStyle = "rgba(111, 195, 215, 0.85)";
                ctx.lineWidth = 2.5;
                ctx.beginPath();
                ctx.arc(enemy.x - 4, enemy.y, cssH * 0.28, Math.PI * 0.72, Math.PI * 1.28);
                ctx.stroke();
                ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.arc(enemy.x - 4, enemy.y, cssH * 0.28, Math.PI * 0.82, Math.PI * 1.18);
                ctx.stroke();
            }
            ctx.restore();
        }
        if (this.combatFlash && !this.combatFlash.fired) {
            this.combatFlash.fired = true;
            const target = this.combatFlash.target === "player" ? player : enemy;
            if (this.combatFlash.action === "point_defense") {
                this.combatFx?.flakBurst?.(player.x + 18, player.y - 6, 26, "#e2c078");
                this.combatFx?.flakBurst?.(player.x + 22, player.y + 8, 22, "#ffffff");
            } else if (this.combatFlash.action === "drone_strike") {
                this.combatFx?.flakBurst?.(enemy.x, enemy.y, 24, "#ffd166");
            } else {
                this.combatFx?.burst?.(target.x, target.y, 18, this.combatFlash.color || "#ffd166", 190);
                this.combatFx?.ring?.(target.x, target.y, this.combatFlash.color || "#ffd166", 42, 0.5);
            }
            if (this.combatFlash.action === "target_bridge" || this.combatFlash.action === "target_weapons") {
                this.combatFx?.ionArc?.(player.x + 12, player.y, enemy.x - 8, enemy.y, "#7fb7c9");
            }
            if (target === enemy && Number(this.state.active_combat?.enemy_shield || 0) > 0) {
                this.combatFx?.hexShieldImpact?.(target.x - 4, target.y, cssH * 0.28, "rgba(111, 195, 215, 0.85)");
            }
        }
        this.combatFx?.update();
        this.combatFx?.draw(ctx);
        this.celestial?.drawShip(ctx, player.x, player.y, 0, Math.max(12, cssW * 0.035), "#8fbf9f", this.shipVariant());
        this.celestial?.drawShip(ctx, enemy.x, enemy.y, Math.PI, Math.max(14, cssW * 0.04), "#e07a66", this.enemyVariant());
        ctx.font = "12px 'Cascadia Mono', Consolas, monospace";
        ctx.textAlign = "center";
        ctx.fillStyle = "#8fbf9f";
        ctx.fillText("VF-FLAGSHIP", player.x, cssH - 8);
        ctx.fillStyle = "#e07a66";
        ctx.fillText(String(this.state.active_combat.enemy_name || "HOSTILE").toUpperCase(), enemy.x, cssH - 8);
        const vignette = ctx.createRadialGradient(cssW / 2, cssH / 2, cssH * 0.2, cssW / 2, cssH / 2, cssW * 0.7);
        vignette.addColorStop(0, "rgba(0, 0, 0, 0)");
        vignette.addColorStop(1, "rgba(2, 5, 12, 0.55)");
        ctx.fillStyle = vignette;
        ctx.fillRect(0, 0, cssW, cssH);
    }

    drawOrbitsView(cx, cy) {
        if (!this.state) return;
        const ctx = this.ctx;
        const curSys = this.state.current_system;
        const bodies = curSys.bodies;
        const ship = this.state.ship;
        const now = Date.now() * 0.001;
        const auScale = this.orbitFitScale(bodies);
        const labels = [];
        this._radarLabelBoxes = [];
        this.lastShipPosition = { x: cx, y: cy };
        // A Dyson swarm encloses its primary. Drawing the star's corona underneath would
        // bury the collector shell in glare, so the swarm replaces the star sprite.
        const hasDysonSwarm = bodies.some(b => b.body_type === "dyson_sphere");


        if (this.radarGrid) {
            ctx.strokeStyle = "rgba(127, 183, 201, 0.07)";
            ctx.lineWidth = 1;
            for (let radius = 60; radius < Math.max(this.viewW, this.viewH); radius += 60) {
                ctx.beginPath();
                ctx.arc(cx, cy, radius, 0, Math.PI * 2);
                ctx.stroke();
                const auDist = radius / Math.max(1, auScale);
                if (auDist >= 0.25) {
                    ctx.save();
                    ctx.font = "9px 'Cascadia Mono', Consolas, monospace";
                    ctx.fillStyle = "rgba(127, 183, 201, 0.32)";
                    ctx.fillText(`${auDist.toFixed(1)} AU`, cx + radius + 4, cy - 3);
                    ctx.restore();
                }
            }
            for (let x = 0; x < this.viewW; x += 60) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, this.viewH); ctx.stroke();
            }
            for (let y = 0; y < this.viewH; y += 60) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(this.viewW, y); ctx.stroke();
            }

            // Navigational Azimuth Compass Reticle
            const compassR = Math.min(this.viewW, this.viewH) * 0.46;
            if (compassR > 120) {
                ctx.save();
                ctx.strokeStyle = "rgba(127, 183, 201, 0.12)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.arc(cx, cy, compassR, 0, Math.PI * 2);
                ctx.stroke();

                ctx.font = "12px 'Cascadia Mono', Consolas, monospace";
                ctx.fillStyle = "rgba(127, 183, 201, 0.38)";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                const cardinals = [
                    { label: "N 000°", angle: -Math.PI / 2 },
                    { label: "E 090°", angle: 0 },
                    { label: "S 180°", angle: Math.PI / 2 },
                    { label: "W 270°", angle: Math.PI }
                ];
                for (const c of cardinals) {
                    const lx = cx + Math.cos(c.angle) * (compassR + 14);
                    const ly = cy + Math.sin(c.angle) * (compassR + 14);
                    ctx.fillText(c.label, lx, ly);
                    ctx.beginPath();
                    ctx.moveTo(cx + Math.cos(c.angle) * (compassR - 6), cy + Math.sin(c.angle) * (compassR - 6));
                    ctx.lineTo(cx + Math.cos(c.angle) * (compassR + 6), cy + Math.sin(c.angle) * (compassR + 6));
                    ctx.stroke();
                }
                for (let deg = 0; deg < 360; deg += 30) {
                    if (deg % 90 === 0) continue;
                    const rad = (deg * Math.PI) / 180 - Math.PI / 2;
                    ctx.beginPath();
                    ctx.moveTo(cx + Math.cos(rad) * (compassR - 3), cy + Math.sin(rad) * (compassR - 3));
                    ctx.lineTo(cx + Math.cos(rad) * (compassR + 3), cy + Math.sin(rad) * (compassR + 3));
                    ctx.stroke();
                }
                if (this.selectedTarget) {
                    const tX = this.selectedType === "point"
                        ? (cx + Math.cos(this.selectedTarget.angle) * (this.selectedTarget.au * auScale))
                        : (cx + Math.cos(this.selectedTarget.current_angle || 0) * (this.selectedTarget.orbit_radius * auScale));
                    const tY = this.selectedType === "point"
                        ? (cy + Math.sin(this.selectedTarget.angle) * (this.selectedTarget.au * auScale))
                        : (cy + Math.sin(this.selectedTarget.current_angle || 0) * (this.selectedTarget.orbit_radius * auScale));
                    const tAngle = Math.atan2(tY - cy, tX - cx);
                    const hX = cx + Math.cos(tAngle) * compassR;
                    const hY = cy + Math.sin(tAngle) * compassR;
                    ctx.fillStyle = "#c9a35a";
                    ctx.beginPath();
                    ctx.arc(hX, hY, 3.5, 0, Math.PI * 2);
                    ctx.fill();
                }
                ctx.restore();
            }
        }

        bodies.forEach(b => {
            if (b.body_type === "star" && hasDysonSwarm) {
                // The swarm paints its own enclosed core.
                return;
            }
            if (b.body_type === "star" && this.celestial) {
                this.celestial.drawStar(ctx, b, cx, cy, 13 * Math.max(0.8, this.zoom) * Math.min(1.6, this.radarScale()), now);
                // Solar wind ion flare
                if (this.particles && Math.random() < 0.25) {
                    const angle = Math.random() * Math.PI * 2;
                    const dist = 14 + Math.random() * 8;
                    const speed = 25 + Math.random() * 35;
                    this.particles.ion?.(
                        cx + Math.cos(angle) * dist,
                        cy + Math.sin(angle) * dist,
                        Math.cos(angle) * speed,
                        Math.sin(angle) * speed,
                        "#ffd166",
                        0.75,
                        1.4
                    );
                }
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
            let bx = cx + Math.cos(angle) * orbitR;
            let by = cy + Math.sin(angle) * orbitR;
            if (b.body_type === "dyson_sphere") {
                // Pinned to the primary: a swarm is a shell around the star, not a body
                // orbiting a few pixels away from it.
                bx = cx;
                by = cy;
            }

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
                    this.celestial.drawMoons(ctx, b, bx, by, bodyRadius, now, Math.atan2(cy - by, cx - bx));
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
                const pad = bodyRadius + 6;
                const corner = Math.max(5, Math.round(pad * 0.42));
                const pulse = 1.0 + Math.sin(now * 3.5) * 0.05;
                const pPad = pad * pulse;
                ctx.save();
                ctx.strokeStyle = "#7fb7c9";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                // Top-Left ┌
                ctx.moveTo(bx - pPad, by - pPad + corner);
                ctx.lineTo(bx - pPad, by - pPad);
                ctx.lineTo(bx - pPad + corner, by - pPad);
                // Top-Right ┐
                ctx.moveTo(bx + pPad - corner, by - pPad);
                ctx.lineTo(bx + pPad, by - pPad);
                ctx.lineTo(bx + pPad, by - pPad + corner);
                // Bottom-Left └
                ctx.moveTo(bx - pPad, by + pPad - corner);
                ctx.lineTo(bx - pPad, by + pPad);
                ctx.lineTo(bx - pPad + corner, by + pPad);
                // Bottom-Right ┘
                ctx.moveTo(bx + pPad - corner, by + pPad);
                ctx.lineTo(bx + pPad, by + pPad);
                ctx.lineTo(bx + pPad, by + pPad - corner);
                ctx.stroke();

                // Cardinal reticle tick pips
                ctx.strokeStyle = "rgba(127, 183, 201, 0.55)";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(bx, by - pPad - 4); ctx.lineTo(bx, by - pPad);
                ctx.moveTo(bx, by + pPad); ctx.lineTo(bx, by + pPad + 4);
                ctx.moveTo(bx - pPad - 4, by); ctx.lineTo(bx - pPad, by);
                ctx.moveTo(bx + pPad, by); ctx.lineTo(bx + pPad + 4, by);
                ctx.stroke();

                // Orbital tangent velocity vector
                if (orbitR > 0) {
                    const tang = angle + Math.PI / 2;
                    const vLen = Math.max(14, pPad * 0.95);
                    const vx = bx + Math.cos(tang) * vLen;
                    const vy = by + Math.sin(tang) * vLen;
                    ctx.strokeStyle = "rgba(201, 163, 90, 0.75)";
                    ctx.lineWidth = 1.2;
                    ctx.beginPath();
                    ctx.moveTo(bx, by);
                    ctx.lineTo(vx, vy);
                    ctx.stroke();
                    const aHead = 4;
                    ctx.beginPath();
                    ctx.moveTo(vx, vy);
                    ctx.lineTo(vx - Math.cos(tang - 0.5) * aHead, vy - Math.sin(tang - 0.5) * aHead);
                    ctx.moveTo(vx, vy);
                    ctx.lineTo(vx - Math.cos(tang + 0.5) * aHead, vy - Math.sin(tang + 0.5) * aHead);
                    ctx.stroke();
                }
                ctx.restore();
            }

            const activeTravel = ship.travel || this.state.travel || null;
            if (ship.orbiting_body_id === b.id && !activeTravel && !this.travelAnimation) {
                // Parked in orbit: the flagship circles its body, nose along the orbit.
                const parkR = bodyRadius + 12 * Math.max(1, this.zoom);
                const parkA = now * 0.5;
                const sx = bx + Math.cos(parkA) * parkR;
                const sy = by + Math.sin(parkA) * parkR;
                if (this.celestial) {
                    this.celestial.drawShip(ctx, sx, sy, parkA + Math.PI / 2, 6 * Math.max(1, this.zoom), "#8fbf9f", this.shipVariant());
                } else {
                    ctx.beginPath();
                    ctx.arc(sx, sy, 3.5, 0, Math.PI * 2);
                    ctx.fillStyle = "#8fbf9f";
                    ctx.fill();
                }
                this.lastShipPosition = { x: sx, y: sy };
                this.particles?.trail(sx, sy, parkA + Math.PI / 2, "#8fd8ff", 0.9);
                labels.push({
                    text: "VF-FLAGSHIP",
                    x: bx,
                    y: by,
                    radius: bodyRadius + 12 * Math.max(1, this.zoom),
                    color: "#8fbf9f",
                    priority: 3,
                    mono: true,
                });
            }

            if (this.radarLabels) {
                labels.push({
                    text: b.name,
                    x: bx,
                    y: by,
                    radius: bodyRadius,
                    color: "#ece4d4",
                    priority: this.selectedTarget && this.selectedTarget.id === b.id ? 4 : 1,
                });
            }
        });

        const activeCourseTravel = ship.travel || this.state.travel || null;
        const originBody = bodies.find(b => b.id === ship.orbiting_body_id);
        const targetBody = this.selectedTarget && this.selectedType === "body"
            ? bodies.find(b => b.id === this.selectedTarget.id)
            : null;
        const inOpenSpace = !originBody && Number(ship.waypoint_au) > 0;
        if (!activeCourseTravel && (originBody || inOpenSpace) && targetBody && targetBody.id !== originBody?.id) {
            const fromAngle = originBody ? (originBody.current_angle || 0) : Number(ship.waypoint_angle || 0);
            const fromRadius = originBody ? originBody.orbit_radius : Number(ship.waypoint_au || 0);
            const toAngle = targetBody.current_angle || 0;
            const fromX = cx + Math.cos(fromAngle) * fromRadius * auScale;
            const fromY = cy + Math.sin(fromAngle) * fromRadius * auScale;
            const toX = cx + Math.cos(toAngle) * targetBody.orbit_radius * auScale;
            const toY = cy + Math.sin(toAngle) * targetBody.orbit_radius * auScale;
            ctx.save();
            ctx.setLineDash([6, 6]);
            ctx.lineDashOffset = -(now * 24) % 12;
            ctx.strokeStyle = "rgba(111, 195, 215, 0.65)";
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(fromX, fromY);
            ctx.lineTo(toX, toY);
            ctx.stroke();
            ctx.setLineDash([]);
            const distAu = Math.hypot(toX - fromX, toY - fromY) / Math.max(1, auScale);
            ctx.font = "10px 'Cascadia Mono', Consolas, monospace";
            ctx.fillStyle = "rgba(236, 228, 212, 0.85)";
            ctx.fillText(`COURSE PLOT // ${distAu.toFixed(2)} AU`, (fromX + toX) / 2 + 8, (fromY + toY) / 2 - 6);
            ctx.restore();
        }

        // Holding station in open space: the flagship still has to be on the map.
        if (ship && !ship.orbiting_body_id && !ship.travel && !ship.landed_body_id
            && !this.travelAnimation && Number(ship.waypoint_au) > 0) {
            const anchorAu = Number(ship.waypoint_au);
            const anchorAngle = Number(ship.waypoint_angle);
            const sx = cx + Math.cos(anchorAngle) * anchorAu * auScale;
            const sy = cy + Math.sin(anchorAngle) * anchorAu * auScale;
            if (this.celestial) {
                this.celestial.drawShip(ctx, sx, sy, anchorAngle + Math.PI / 2, 6 * Math.max(1, this.zoom), "#8fbf9f", this.shipVariant());
            } else {
                ctx.beginPath();
                ctx.arc(sx, sy, 3.5, 0, Math.PI * 2);
                ctx.fillStyle = "#8fbf9f";
                ctx.fill();
            }
            this.lastShipPosition = { x: sx, y: sy };
            this.particles?.trail(sx, sy, anchorAngle + Math.PI / 2, "#8fd8ff", 0.9);
            labels.push({
                text: "VF-FLAGSHIP (OPEN SPACE)",
                x: sx,
                y: sy,
                radius: 8 * Math.max(1, this.zoom),
                color: "#8fbf9f",
                priority: 4,
                mono: true,
            });
        }
        this.particles?.draw(ctx);
        labels.sort((a, b) => b.priority - a.priority);
        labels.forEach(label => this.placeRadarLabel(
            ctx, label.text, label.x, label.y, label.radius, label.color, label.priority, label.mono,
        ));
        this.drawSystemTraffic(ctx, cx, cy, auScale, now);
        this.drawPointSelection(ctx, cx, cy, auScale, ship);
        this.drawTravelAnimation(ctx, cx, cy, auScale);

        // Offscreen Navigation Reticle for Selected Target
        if (this.selectedTarget && this.mapRect) {
            const tX = this.selectedType === "point"
                ? (cx + Math.cos(this.selectedTarget.angle) * (this.selectedTarget.au * auScale))
                : (cx + Math.cos(this.selectedTarget.current_angle || 0) * (this.selectedTarget.orbit_radius * auScale));
            const tY = this.selectedType === "point"
                ? (cy + Math.sin(this.selectedTarget.angle) * (this.selectedTarget.au * auScale))
                : (cy + Math.sin(this.selectedTarget.current_angle || 0) * (this.selectedTarget.orbit_radius * auScale));
            const mr = this.mapRect;
            const margin = 28;
            const isOffscreen = tX < mr.x + margin || tX > mr.x + mr.w - margin || tY < mr.y + margin || tY > mr.y + mr.h - margin;
            if (isOffscreen) {
                const angle = Math.atan2(tY - cy, tX - cx);
                const edgeX = Math.max(mr.x + margin, Math.min(mr.x + mr.w - margin, cx + Math.cos(angle) * (mr.w * 0.44)));
                const edgeY = Math.max(mr.y + margin, Math.min(mr.y + mr.h - margin, cy + Math.sin(angle) * (mr.h * 0.44)));
                ctx.save();
                ctx.translate(edgeX, edgeY);
                ctx.rotate(angle);
                ctx.fillStyle = "#c9a35a";
                ctx.beginPath();
                ctx.moveTo(10, 0);
                ctx.lineTo(-6, -6);
                ctx.lineTo(-3, 0);
                ctx.lineTo(-6, 6);
                ctx.closePath();
                ctx.fill();
                ctx.restore();

                ctx.save();
                ctx.font = "12px 'Cascadia Mono', Consolas, monospace";
                ctx.fillStyle = "rgba(201, 163, 90, 0.9)";
                const isRight = edgeX > mr.x + mr.w / 2;
                ctx.textAlign = isRight ? "right" : "left";
                const labelX = isRight ? edgeX - 12 : edgeX + 12;
                const distAu = Math.hypot(tX - cx, tY - cy) / Math.max(1, auScale);
                ctx.fillText(`${this.selectedTarget.name || "WAYPOINT"} (${distAu.toFixed(1)} AU)`, labelX, edgeY + 4);
                ctx.restore();
            }
        }

        // Astronomical Range Scale Bar in lower-left corner of visible radar viewport
        if (this.mapRect) {
            const scaleAu = auScale > 180 ? 0.5 : (auScale > 60 ? 1.0 : (auScale > 20 ? 5.0 : 10.0));
            const scalePx = scaleAu * auScale;
            if (scalePx > 20 && scalePx < this.mapRect.w * 0.4) {
                const padX = this.mapRect.x + 22;
                const padY = this.mapRect.y + this.mapRect.h - 18;
                ctx.save();
                ctx.strokeStyle = "rgba(127, 183, 201, 0.45)";
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(padX, padY - 4);
                ctx.lineTo(padX, padY);
                ctx.lineTo(padX + scalePx, padY);
                ctx.lineTo(padX + scalePx, padY - 4);
                ctx.stroke();
                ctx.font = "12px 'Cascadia Mono', Consolas, monospace";
                ctx.fillStyle = "rgba(127, 183, 201, 0.65)";
                ctx.textAlign = "center";
                ctx.fillText(`RANGE SCALE [ ${scaleAu < 1 ? scaleAu.toFixed(1) : scaleAu.toFixed(0)} AU ]`, padX + scalePx * 0.5, padY - 6);
                ctx.restore();
            }
        }
    }

    // Display size is logarithmic in real radius: an Earth ~14px, a gas giant ~22px at 1x,
    // so every world is big enough to show its surface model. Drawing and hit tests share it.
    bodyTypeLabel(body) {
        const type = String((body && body.body_type) || "body");
        return BODY_TYPE_LABELS[type] || type.replace(/_/g, " ").toUpperCase();
    }

    compactCount(value) {
        const number = Number(value || 0);
        if (number >= 1e12) return `${(number / 1e12).toFixed(2)}T`;
        if (number >= 1e9) return `${(number / 1e9).toFixed(2)}B`;
        if (number >= 1e6) return `${(number / 1e6).toFixed(1)}M`;
        if (number >= 1e3) return `${(number / 1e3).toFixed(1)}K`;
        return String(Math.max(0, Math.round(number)));
    }

    bodyDisplayRadius(b) {
        const scale = this.zoom * Math.min(1.4, this.radarScale());
        if (b.body_type === "dyson_sphere") return 34 * scale;
        if (b.body_type === "ring_world") return 24 * scale;
        const sizeLog = Math.log2(Math.max(1, (b.radius_km || 1000) / 1000));
        return Math.max(6, Math.min(22, 6 + sizeLog * 3)) * scale;
    }

    shipVariant() {
        const cls = String(this.state?.ship?.ship_class || "").toLowerCase();
        if (/freight|cargo|hauler|transport/.test(cls)) return "freighter";
        if (/fighter|intercept|strike|gunship/.test(cls)) return "fighter";
        if (/explor|survey|science|pathfinder/.test(cls)) return "explorer";
        if (/stealth|ghost|shadow|phantom/.test(cls)) return "stealth";
        if (/dread|capital|battle|cruiser|carrier/.test(cls)) return "capital";
        return "standard";
    }

    enemyVariant() {
        const combat = this.state?.active_combat || {};
        const cls = String(combat.enemy_class || combat.enemy_name || "").toLowerCase();
        if (/dread|capital|battle|cruiser|carrier/.test(cls)) return "capital";
        if (/fighter|interceptor|strike/.test(cls)) return "fighter";
        if (/freight|hauler|transport/.test(cls)) return "freighter";
        if (/stealth|ghost|shadow/.test(cls)) return "stealth";
        return "standard";
    }

    // The outermost orbit must stay inside the visible radar: at 720p the center panel
    // is only ~246px tall, so a fixed 45px/AU pushed worlds under the command strip.
    orbitFitScale(bodies) {
        const rect = this.mapRect || { w: this.viewW, h: this.viewH };
        const maxAu = Math.max(0.1, ...bodies
            .filter(body => body.body_type !== "dyson_sphere")
            .map(body => Number(body.orbit_radius) || 0));
        const base = 45 * this.radarScale();
        const fit = Math.min(rect.w, rect.h) * 0.43 / maxAu;
        return Math.max(6, Math.min(base, fit)) * this.zoom;
    }

    // Body and flagship labels share one collision map so two names never overlap, and
    // every label stays inside the visible radar rather than sliding under the HUD.
    placeRadarLabel(ctx, text, x, y, radius, color, priority = 0, mono = false) {
        const rect = this.mapRect || { x: 0, y: 0, w: this.viewW, h: this.viewH };
        const boxes = this._radarLabelBoxes || [];
        const font = mono
            ? "12px 'Cascadia Mono', Consolas, monospace"
            : "12px 'Segoe UI'";
        ctx.save();
        ctx.font = font;
        const width = ctx.measureText(text).width;
        const height = 14;
        const gap = 6;
        const candidates = [
            { x: x + radius + gap, y: y - height / 2 },
            { x: x - radius - gap - width, y: y - height / 2 },
            { x: x - width / 2, y: y + radius + gap },
            { x: x - width / 2, y: y - radius - gap - height },
        ];
        const place = box => {
            ctx.fillStyle = "rgba(4, 9, 19, 0.58)";
            ctx.fillRect(box.x, box.y, box.w, box.h);
            ctx.fillStyle = color;
            ctx.fillText(text, box.x + 3, box.y + height - 3);
            boxes.push(box);
            this._radarLabelBoxes = boxes;
        };
        for (const candidate of candidates) {
            const box = { x: candidate.x - 3, y: candidate.y - 2, w: width + 6, h: height + 4 };
            if (box.x < rect.x + 4 || box.y < rect.y + 4
                || box.x + box.w > rect.x + rect.w - 4
                || box.y + box.h > rect.y + rect.h - 4) continue;
            if (boxes.some(other => box.x < other.x + other.w && box.x + box.w > other.x
                && box.y < other.y + other.h && box.y + box.h > other.y)) continue;
            place(box);
            ctx.restore();
            return true;
        }
        if (priority >= 4) {
            // A selected body or the flagship must stay named even in a crowded strip.
            const box = {
                x: Math.max(rect.x + 4, Math.min(rect.x + rect.w - width - 10, x + radius + gap)),
                y: Math.max(rect.y + 4, Math.min(rect.y + rect.h - height - 6, y - height / 2)),
                w: width + 6,
                h: height + 4,
            };
            place(box);
        }
        ctx.restore();
        return false;
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
        const now = Date.now() * 0.001;
        const gx = transform.cx;
        const gy = transform.cy;
        const nodeScale = transform.nodeScale;
        const politics = this.state.galactic_politics || { systems: {}, factions: [], wars: [] };
        const owners = politics.systems || {};
        const at = s => [gx + s.x * scale, gy + s.y * scale];

        this.drawGalaxyNebula(ctx, transform, now);
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
                // Interstellar transit pulse flow
                const laneSeed = ((s1.x * 37 + s2.y * 59) & 0xffff) / 65535;
                const flowPhase = ((now * 0.18 + laneSeed) % 1.0);
                const px = x1 + (x2 - x1) * flowPhase;
                const py = y1 + (y2 - y1) * flowPhase;
                ctx.fillStyle = crossing ? "rgba(236, 228, 212, 0.65)" : "rgba(143, 216, 255, 0.75)";
                ctx.beginPath();
                ctx.arc(px, py, Math.max(1.2, 1.6 * nodeScale), 0, Math.PI * 2);
                ctx.fill();
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

            this.drawStarGlyph(ctx, sx, sy, radius, s.color || "#6fc3d7", s.id, now);
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

        this.drawGalaxyTraffic(ctx, transform, now);
        this.particles?.draw(ctx);
        this.drawPoliticsLegend(ctx, politics);
    }

    // NPC traffic: every AI captain is somewhere, so every system with a hull shows one.
    captainHash(id) {
        let hash = 0;
        const text = String(id || "");
        for (let i = 0; i < text.length; i += 1) {
            hash = (hash * 31 + text.charCodeAt(i)) % 1000003;
        }
        return hash;
    }

    captainMarker(captain, cx, cy, auScale, now, maxAu) {
        const hash = this.captainHash(captain.id);
        const baseAngle = (hash % 6283) / 1000;
        const au = 0.3 + ((hash >> 7) % 1000) / 1000 * Math.max(1, maxAu * 0.7);
        const drift = 0.02 + ((hash >> 13) % 100) / 100 * 0.10;
        const angle = baseAngle + now * drift;
        return { x: cx + Math.cos(angle) * au * auScale, y: cy + Math.sin(angle) * au * auScale, angle };
    }

    captainColor(captain) {
        if (captain.archetype === "pirate") return "#e07a66";
        if (captain.archetype === "mercenary") return "#c9a35a";
        if (captain.ally) return "#8fbf9f";
        return "#6fc3d7";
    }

    drawShipGlyph(ctx, x, y, angle, color, size) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle + Math.PI / 2);
        ctx.beginPath();
        ctx.moveTo(0, -size);
        ctx.lineTo(size * 0.7, size * 0.8);
        ctx.lineTo(0, size * 0.4);
        ctx.lineTo(-size * 0.7, size * 0.8);
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
        ctx.restore();
    }

    systemTrafficPositions(cx, cy, auScale, now) {
        const s = this.state;
        if (!s || !s.current_system) return [];
        const systemId = s.current_system.id;
        const captains = (s.ai_captains || []).filter(c => c.system_id === systemId);
        if (!captains.length) return [];
        const maxAu = Math.max(1, ...s.current_system.bodies.map(b => b.orbit_radius || 0));
        return captains.map(captain => ({
            captain,
            ...this.captainMarker(captain, cx, cy, auScale, now, maxAu),
        }));
    }

    drawSystemTraffic(ctx, cx, cy, auScale, now) {
        this.systemTrafficPositions(cx, cy, auScale, now).forEach(({ captain, x, y, angle }) => {
            const pos = { x, y, angle };
            const color = this.captainColor(captain);
            const selected = this.selectedType === "captain" && this.selectedTarget && this.selectedTarget.id === captain.id;
            this.drawShipGlyph(ctx, pos.x, pos.y, pos.angle, color, selected ? 7 : 5);
            this.particles?.trail(pos.x, pos.y, pos.angle, color, 0.55);
            if (selected) {
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, 12, 0, Math.PI * 2);
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.2;
                ctx.stroke();
            }
            if (this.radarLabels || selected) {
                // NPC names join the body/flag label collision map instead of
                // painting over it; a crowded map drops an unselected name.
                this.placeRadarLabel(
                    ctx, captain.name, pos.x, pos.y, 9, color, selected ? 4 : 0, true,
                );
            }
        });
    }

    galaxyTrafficPositions(transform, now) {
        const captains = (this.state && this.state.ai_captains) || [];
        if (!captains.length) return [];
        const bySystem = new Map();
        captains.forEach(c => {
            if (!bySystem.has(c.system_id)) bySystem.set(c.system_id, []);
            bySystem.get(c.system_id).push(c);
        });
        const nodeScale = Math.max(0.8, transform.nodeScale);
        const positions = [];
        bySystem.forEach((list, systemId) => {
            const system = this.galaxySystems[systemId];
            if (!system) return;
            const sx = transform.cx + system.x * transform.scale;
            const sy = transform.cy + system.y * transform.scale;
            list.slice(0, 4).forEach((captain, index) => {
                const angle = now * 0.4 + index * 1.7;
                const radius = 24 * nodeScale;
                positions.push({
                    captain,
                    x: sx + Math.cos(angle) * radius,
                    y: sy + Math.sin(angle) * radius,
                    angle,
                    size: Math.max(5.5, 7.5 * nodeScale),
                    hitRadius: Math.max(10, 10 * nodeScale),
                });
            });
        });
        return positions;
    }

    drawGalaxyTraffic(ctx, transform, now) {
        this.galaxyTrafficPositions(transform, now).forEach(marker => {
            const color = this.captainColor(marker.captain);
            const selected = this.selectedType === "captain"
                && this.selectedTarget && this.selectedTarget.id === marker.captain.id;
            ctx.save();
            ctx.globalAlpha = selected ? 0.95 : 0.55;
            ctx.beginPath();
            ctx.arc(marker.x, marker.y, marker.size * 2.1, 0, Math.PI * 2);
            ctx.strokeStyle = color;
            ctx.lineWidth = selected ? 1.8 : 1.2;
            ctx.stroke();
            ctx.restore();
            this.drawShipGlyph(
                ctx,
                marker.x,
                marker.y,
                marker.angle + Math.PI / 2,
                color,
                marker.size,
            );
            this.particles?.trail(marker.x, marker.y, marker.angle + Math.PI / 2, color, 0.5);
        });
    }

    // A galaxy-only nebula wash and dust lane behind the territory. It drifts a fraction
    // of the map pan, so the political layer reads as a foreground over deep space.
    drawGalaxyNebula(ctx, transform, now) {
        const w = this.viewW;
        const h = this.viewH;
        const px = this.panX * 0.12;
        const py = this.panY * 0.12;
        const drift = Math.sin(now * 0.03) * 6;
        ctx.save();
        ctx.globalCompositeOperation = "source-over";
        const blue = ctx.createRadialGradient(
            w * 0.70 + px + drift, h * 0.30 + py, 0,
            w * 0.70 + px + drift, h * 0.30 + py, Math.max(w, h) * 0.58,
        );
        blue.addColorStop(0, "rgba(58, 104, 170, 0.20)");
        blue.addColorStop(0.45, "rgba(38, 64, 118, 0.10)");
        blue.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = blue;
        ctx.fillRect(0, 0, w, h);
        const violet = ctx.createRadialGradient(
            w * 0.26 + px * 0.6 - drift, h * 0.74 + py * 0.6, 0,
            w * 0.26 + px * 0.6 - drift, h * 0.74 + py * 0.6, Math.max(w, h) * 0.46,
        );
        violet.addColorStop(0, "rgba(118, 80, 160, 0.13)");
        violet.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = violet;
        ctx.fillRect(0, 0, w, h);
        // Core bulge amber stellar dust lane
        const amber = ctx.createRadialGradient(
            w * 0.52 + px * 0.8, h * 0.48 + py * 0.8 + drift * 0.5, 0,
            w * 0.52 + px * 0.8, h * 0.48 + py * 0.8 + drift * 0.5, Math.max(w, h) * 0.36,
        );
        amber.addColorStop(0, "rgba(201, 163, 90, 0.12)");
        amber.addColorStop(0.35, "rgba(160, 95, 40, 0.05)");
        amber.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = amber;
        ctx.fillRect(0, 0, w, h);
        ctx.translate(w * 0.62 + px, h * 0.48 + py);
        ctx.rotate(-0.42);
        const dust = ctx.createLinearGradient(0, -h * 0.12, 0, h * 0.12);
        dust.addColorStop(0, "rgba(0, 0, 0, 0)");
        dust.addColorStop(0.5, "rgba(4, 8, 16, 0.24)");
        dust.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = dust;
        ctx.fillRect(-w * 0.8, -h * 0.12, w * 1.6, h * 0.24);
        ctx.restore();
    }

    // Seeded star glyph: a soft corona, a white core and four diffraction rays whose
    // length and rotation come from the system id, so no two key stars read alike.
    drawStarGlyph(ctx, x, y, radius, color, seed = "", now = 0) {
        const hash = this.captainHash(seed || color);
        const phase = (hash % 997) / 997 * Math.PI * 2;
        const pulse = 0.92 + Math.sin(now * 1.4 + phase) * 0.08;
        const halo = ctx.createRadialGradient(x, y, radius * 0.5, x, y, radius * 4.4 * pulse);
        halo.addColorStop(0, "rgba(255, 255, 255, 0.42)");
        halo.addColorStop(0.24, color);
        halo.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.save();
        ctx.globalAlpha = 0.22;
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(x, y, radius * 4.4 * pulse, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
        const core = ctx.createRadialGradient(x, y, 0, x, y, radius * 1.35);
        core.addColorStop(0, "#ffffff");
        core.addColorStop(0.35, color);
        core.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = core;
        ctx.beginPath();
        ctx.arc(x, y, radius * 1.35, 0, Math.PI * 2);
        ctx.fill();
        const ray = radius * (2.3 + (hash % 100) / 100 * 1.3);
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(phase * 0.12);
        ctx.strokeStyle = color;
        ctx.lineCap = "round";
        ctx.lineWidth = Math.max(0.8, radius * 0.10);
        ctx.globalAlpha = 0.34;
        ctx.beginPath();
        ctx.moveTo(-ray, 0); ctx.lineTo(ray, 0);
        ctx.moveTo(0, -ray); ctx.lineTo(0, ray);
        ctx.stroke();
        ctx.rotate(Math.PI / 4);
        ctx.globalAlpha = 0.16;
        ctx.lineWidth = Math.max(0.6, radius * 0.06);
        ctx.beginPath();
        ctx.moveTo(-ray * 0.5, 0); ctx.lineTo(ray * 0.5, 0);
        ctx.moveTo(0, -ray * 0.5); ctx.lineTo(0, ray * 0.5);
        ctx.stroke();
        ctx.restore();
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(x, y, Math.max(1.2, radius * 0.34), 0, Math.PI * 2);
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
        // ~960 cells across keeps borders crisp at 1080p while a cached rebuild stays cheap.
        const cell = Math.max(2, Math.round(this.viewW / 960));
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
        sctx.filter = "blur(1.6px)";
        sctx.drawImage(canvas, 0, 0, smooth.width, smooth.height);
        // A fine diagonal hatch gives owned space a cartographic texture without
        // brightening the wash. source-atop keeps it inside the territory mask.
        sctx.filter = "none";
        const hatch = document.createElement("canvas");
        hatch.width = 8;
        hatch.height = 8;
        const hctx = hatch.getContext("2d");
        hctx.strokeStyle = "rgba(255, 255, 255, 0.10)";
        hctx.lineWidth = 1;
        hctx.beginPath();
        hctx.moveTo(-2, 6);
        hctx.lineTo(6, -2);
        hctx.stroke();
        const pattern = sctx.createPattern(hatch, "repeat");
        if (pattern) {
            sctx.globalCompositeOperation = "source-atop";
            sctx.fillStyle = pattern;
            sctx.fillRect(0, 0, smooth.width, smooth.height);
            sctx.globalCompositeOperation = "source-over";
        }
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
            const bodies = this.state.current_system?.bodies || [];
            const auScale = this.orbitFitScale(bodies);
            for (const b of bodies) {
                if (b.body_type === "star") {
                    const starR = Math.max(22, 13 * Math.max(0.8, this.zoom) * Math.min(1.6, this.radarScale()) + 6);
                    if (Math.hypot(mx - cx, my - cy) < starR) {
                        hit = { item: b, type: "body" };
                        break;
                    }
                    continue;
                }
                const orbitR = b.orbit_radius * auScale;
                const angle = b.current_angle || 0;
                const bx = b.body_type === "dyson_sphere" ? cx : cx + Math.cos(angle) * orbitR;
                const by = b.body_type === "dyson_sphere" ? cy : cy + Math.sin(angle) * orbitR;
                const dist = Math.hypot(mx - bx, my - by);
                if (dist < Math.max(18, this.bodyDisplayRadius(b) + 4)) {
                    hit = { item: b, type: "body" };
                    break;
                }
            }
            if (!hit) {
                for (const traffic of this.systemTrafficPositions(cx, cy, auScale, Date.now() * 0.001)) {
                    if (Math.hypot(mx - traffic.x, my - traffic.y) < 14) {
                        hit = { item: traffic.captain, type: "captain" };
                        break;
                    }
                }
            }
        } else if (this.viewMode === "GALAXY") {
            const transform = this.galaxyTransform(cx, cy);
            for (const traffic of this.galaxyTrafficPositions(transform, Date.now() * 0.001)) {
                if (Math.hypot(mx - traffic.x, my - traffic.y) < traffic.hitRadius) {
                    hit = { item: traffic.captain, type: "captain" };
                    break;
                }
            }
            const hitRadius = 18 * Math.max(1, transform.nodeScale);
            if (!hit) for (const s of Object.values(this.galaxySystems)) {
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
            const bodies = this.state.current_system?.bodies || [];
            const auScale = this.orbitFitScale(bodies);
            for (const b of bodies) {
                if (b.body_type === "star") {
                    const starR = Math.max(22, 13 * Math.max(0.8, this.zoom) * Math.min(1.6, this.radarScale()) + 6);
                    if (Math.hypot(mx - cx, my - cy) < starR) {
                        this.selectedTarget = b;
                        this.selectedType = "body";
                        this.sound.playBeep(1000);
                        this.updateTargetCard();
                        hit = true;
                        return;
                    }
                    continue;
                }
                const orbitR = b.orbit_radius * auScale;
                const angle = b.current_angle || 0;
                const bx = b.body_type === "dyson_sphere" ? cx : cx + Math.cos(angle) * orbitR;
                const by = b.body_type === "dyson_sphere" ? cy : cy + Math.sin(angle) * orbitR;
                if (Math.hypot(mx - bx, my - by) < Math.max(18, this.bodyDisplayRadius(b) + 4)) {
                    this.selectedTarget = b;
                    this.selectedType = "body";
                    this.sound.playBeep(1000);
                    this.updateTargetCard();
                    hit = true;
                    return;
                }
            }
            for (const traffic of this.systemTrafficPositions(cx, cy, auScale, Date.now() * 0.001)) {
                if (Math.hypot(mx - traffic.x, my - traffic.y) < 14) {
                    this.selectedTarget = traffic.captain;
                    this.selectedType = "captain";
                    this.sound.playBeep(1000);
                    this.updateTargetCard();
                    hit = true;
                    return;
                }
            }
            // Nothing under the cursor: propose an open-space vector instead of doing nothing.
            const dx = mx - cx;
            const dy = my - cy;
            const distanceAu = Math.hypot(dx, dy) / auScale;
            if (distanceAu >= 0.05) {
                this.selectedTarget = { au: distanceAu, angle: Math.atan2(dy, dx) };
                this.selectedType = "point";
                this.sound.playBeep(760, 0.05);
                this.updateTargetCard();
                hit = true;
            }
        } else if (this.viewMode === "GALAXY") {
            const transform = this.galaxyTransform(cx, cy);
            for (const traffic of this.galaxyTrafficPositions(transform, Date.now() * 0.001)) {
                if (Math.hypot(mx - traffic.x, my - traffic.y) < traffic.hitRadius) {
                    this.selectedTarget = traffic.captain;
                    this.selectedType = "captain";
                    this.sound.playBeep(1000);
                    this.updateTargetCard();
                    hit = true;
                    return;
                }
            }
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

    handleCanvasDblClick(e) {
        const point = this.pointerToCanvas(e);
        const { x: cx, y: cy } = this.mapCenter();
        const baseCenterX = cx - this.panX;
        const baseCenterY = cy - this.panY;
        this.targetPanX = -(point.x - baseCenterX);
        this.targetPanY = -(point.y - baseCenterY);
        this.panVx = 0;
        this.panVy = 0;
        this.sound?.playBeep?.(1200, 0.04);
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
        const masteryLevel = Number((this.state.ship.mastery || {}).level || 1);
        const chartered = masteryLevel >= 2;
        if (!chartered) {
            host.innerHTML = `<h4 class="commission-title">FOUND AN OUTPOST AT ${this.escapeHtml(body.name.toUpperCase())}</h4>`
                + `<p class="panel-intro-text">Outpost charters require Pilot Mastery level 2 (recognized commander); current level ${masteryLevel}. Earn XP through contracts, scans and victories.</p>`;
            return;
        }
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
        const canAffordEnvoy = this.state.ship.credits >= 500;
        host.innerHTML = wars.map(w => {
            const lead = Math.max(-1, Math.min(1, w.war_score / 24));
            const attackerShare = Math.round(50 + lead * 50);
            const captured = (w.captured_systems || []).length;
            const pledge = id => (w.support || {})[id] || 0;
            const enemy = w.attacker_id === "sol_coalition" ? w.defender_id : (w.defender_id === "sol_coalition" ? w.attacker_id : null);
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
                    ${enemy ? `<div class="war-mediate">
                        <button class="btn-hud" data-petition-ceasefire="${this.escapeHtml(enemy)}" ${canAffordEnvoy ? "" : "disabled"} title="${canAffordEnvoy ? "Send a 500 cr envoy to petition the enemy leadership for a ceasefire; they may refuse" : "An envoy costs 500 cr"}">PETITION CEASEFIRE / 500</button>
                    </div>` : `<div class="war-meta">Sovereign war: only the powers themselves can end it.</div>`}
                    ${pledge(w.attacker_id) || pledge(w.defender_id) ? `<div class="war-meta">Your pledges: ${pledge(w.attacker_id)} / ${pledge(w.defender_id)} cr</div>` : ""}
                    <div class="war-meta war-bond-note">Bonds: 1.5x victory · 0.8x stalemate · 0 defeat.</div>
                </div>`;
        }).join("");
        host.querySelectorAll("[data-war]").forEach(btn => btn.addEventListener("click", () =>
            this.postAction("/api/war/support", {
                war_id: btn.getAttribute("data-war"), faction_id: btn.getAttribute("data-side"), credits: 500,
            }, "factions")
        ));
        host.querySelectorAll("[data-petition-ceasefire]").forEach(btn => btn.addEventListener("click", () =>
            this.postAction("/api/diplomacy", {
                faction_id: btn.getAttribute("data-petition-ceasefire"), action: "ceasefire",
            }, "factions")
        ));
    }

    renderFactions() {
        if (!this.state) return;
        this.renderWars();
        if (!this.state.factions || !this.factionsGrid) return;

        this.factionsGrid.innerHTML = "";
        const politics = this.state.galactic_politics || { factions: [] };
        const economyById = {};
        (politics.factions || []).forEach(f => { economyById[f.id] = f; });
        Object.entries(this.state.factions).forEach(([fid, f]) => {
            const card = document.createElement("div");
            card.className = "faction-card";
            const factionColor = this.safeColor(f.primary_color);
            card.style.borderColor = `${factionColor}44`;
            const tierClass = `tier-${this.escapeHtml(f.standing_tier.toLowerCase())}`;
            const barPct = Math.max(0, Math.min(100, Math.round(((f.standing + 100) / 200) * 100)));
            const econ = economyById[fid] || {};
            const treasury = Number(econ.treasury || 0);
            const net = Number(econ.net_income || 0);
            const stability = Number(econ.stability || 0);
            const population = Number(econ.population || 0);
            const worlds = Number(econ.worlds || 0);
            const tech = Number(econ.tech_level || 1);
            const warBurden = Number(econ.war_burden || 0);
            const netLabel = `${net >= 0 ? "+" : ""}${net.toLocaleString("en-US")}`;
            const bankrupt = treasury <= 0 && net < 0;
            const tax = Number(econ.tax_income || 0);
            const trade = Number(econ.trade_income || 0);
            const industry = Number(econ.industrial_output || 0);
            const upkeep = Number(econ.military_upkeep || 0);
            const partners = Number(econ.trade_partners || 0);
            const partnerNames = (econ.trade_partner_names || []).join(", ");
            const techProgress = Math.round(Number(econ.tech_progress || 0));
            const signed = value => `${value >= 0 ? "+" : ""}${value.toLocaleString("en-US")}`;

            card.innerHTML = `
                <div class="faction-top-row">
                    <span class="faction-name" style="color: ${factionColor};">${this.escapeHtml(f.name)}</span>
                    <span class="standing-badge ${tierClass}">${this.escapeHtml(f.standing_tier.toUpperCase())} (${f.standing > 0 ? "+" : ""}${f.standing})</span>
                </div>
                <div class="faction-ideology">Ideology: ${this.escapeHtml(f.ideology)} // HQ: ${this.escapeHtml(f.headquarters_system.toUpperCase())}</div>
                <div class="standing-bar-wrap">
                    <div class="standing-bar-fill" style="width: ${barPct}%; background: ${factionColor};"></div>
                </div>
                <div class="faction-economy${bankrupt ? " is-broke" : ""}">TREASURY ${treasury.toLocaleString("en-US")} cr // NET <span class="econ-net ${net >= 0 ? "is-pos" : "is-neg"}">${netLabel}</span>/t // STABILITY ${stability.toFixed(0)}%</div>
                <div class="faction-economy${bankrupt ? " is-broke" : ""} econ-breakdown" title="Per tick: taxes, trade income, industrial output, military upkeep"><span>TAX ${signed(tax)} · TRADE ${signed(trade)}</span> <span>IND ${signed(industry)} · UPKEEP −${upkeep.toLocaleString("en-US")}</span></div>
                <div class="faction-economy${bankrupt ? " is-broke" : ""} econ-breakdown" title="${partnerNames ? `Trade partners: ${this.escapeHtml(partnerNames)}` : "No active trade routes"}"><span>POP ${this.compactCount(population)} · ${worlds} WORLDS</span> <span>TL${tech} ${techProgress}% · TRADE ${partners}</span></div>
                <div class="faction-economy${bankrupt ? " is-broke" : ""}">WAR BURDEN ${Math.round(warBurden * 100)}%${bankrupt ? " · BANKRUPT" : ""}</div>
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
        const audioIcon = document.getElementById("audioIcon");
        if (audioIcon) audioIcon.textContent = this.sound.enabled ? "◉" : "MUTED";
        const audioButton = document.getElementById("audioToggleBtn");
        if (audioButton) audioButton.style.opacity = this.sound.enabled ? "1" : "0.5";
    }

    applySettingsProfile(profile) {
        const volume = Number(profile.volume);
        this.sound.setEnabled(profile.sound !== false);
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
        this.sound.setEnabled(document.getElementById("settingSound")?.checked !== false);
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

    initDeckScrollHint() {
        // Signal that the terminal deck continues below the fold, so a row cut by the
        // scroll edge reads as "more content" instead of a clipped layout.
        const stack = document.querySelector("#panelLeft > .terminal-content-stack");
        if (!stack) return;
        const host = stack.closest(".panel-left");
        const sync = () => {
            const stackMore = stack.scrollTop + stack.clientHeight < stack.scrollHeight - 2;
            let more = stackMore;
            if (!more) {
                // Some tabs (FACTIONS, MESSAGES) scroll their own panel instead of the
                // stack, so the cue must watch the active inner scroller too.
                for (const panel of stack.querySelectorAll(".tab-content")) {
                    if (panel.offsetParent === null) continue;
                    if (panel.scrollHeight > panel.clientHeight + 2
                        && panel.scrollTop + panel.clientHeight < panel.scrollHeight - 2) {
                        more = true;
                        break;
                    }
                }
            }
            if (host) host.classList.toggle("has-more-below", more);
        };
        stack.addEventListener("scroll", sync, { passive: true });
        stack.addEventListener("scroll", sync, true);
        if (typeof ResizeObserver === "function") {
            new ResizeObserver(sync).observe(stack);
        }
        if (typeof MutationObserver === "function") {
            new MutationObserver(() => requestAnimationFrame(sync)).observe(stack, {
                childList: true,
                subtree: true,
            });
        }
        sync();
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
                const action = q.kind === "contract" && q.completed
                    ? `<button class="btn-claim-contract" data-claim-quest="${this.escapeHtml(q.id)}">CLAIM REWARD</button>`
                    : (q.kind === "story"
                        ? `<button class="btn-hud" data-view-story="1">VIEW IN COMMS LOG</button>`
                        : "");
                return `<div class="quest-card">
                    <h4>${this.escapeHtml(q.title)}</h4>
                    <div>${this.escapeHtml(q.description)}</div>
                    <div>TYPE: ${this.escapeHtml(q.kind.toUpperCase())} // REWARD: ${this.escapeHtml(q.reward)}</div>
                    <div class="quest-progress"><div style="width:${pct}%"></div></div>
                    <div>${q.progress}/${q.target_count} ${q.completed ? "// COMPLETE" : ""} ${action}</div>
                </div>`;
            }).join("") : '<div class="quest-card">No active quests.</div>';
            this.questsList.querySelectorAll("[data-claim-quest]").forEach(btn => {
                btn.addEventListener("click", () => this.handleClaimContract(btn.getAttribute("data-claim-quest")));
            });
            this.questsList.querySelectorAll("[data-view-story]").forEach(btn => {
                btn.addEventListener("click", () => this.switchRightTab("story"));
            });
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
        const credits = Number((this.state.ship || {}).credits || 0);
        this.aiList.innerHTML = captains.map(c => {
            const trust = Number(c.trust || 0);
            const hireCost = 2500;
            const canHire = !c.hired && credits >= hireCost;
            const hireTitle = c.hired ? "Already under contract"
                : (canHire ? `Hire ${c.name} for ${hireCost} CR` : `Needs ${hireCost} CR`);
            const canAlly = !c.ally && trust >= 50;
            const allyTitle = c.ally ? "Already an ally"
                : (canAlly ? "Form an alliance: +5% trade margin" : `Requires 50 trust (current ${trust})`);
            const captainFuel = Number((c.cargo || {})["fuel_cells"] || 0);
            const holdFuel = Number(((this.state.ship || {}).cargo || {})["fuel_cells"] || 0);
            const buyTitle = captainFuel > 0 ? "Buy 1 fuel from this captain" : `${c.name} has no fuel to sell`;
            const sellTitle = holdFuel > 0 ? "Sell 1 fuel to this captain" : "No fuel in hold to sell";
            return `
            <div class="ai-card">
                <h4>${this.escapeHtml(c.name)} <small>[${this.escapeHtml(c.archetype.toUpperCase())}]</small></h4>
                <div>${this.escapeHtml(c.description)}</div>
                <div>SYSTEM: ${this.escapeHtml(c.system_id)} // TRUST: ${trust} // STANDING: ${c.standing}</div>
                <div>CARGO: ${Object.entries(c.cargo || {}).map(([k, v]) => `${this.escapeHtml(k)} x${v}`).join(", ") || "empty"}</div>
                <div class="ai-actions">
                    <button class="btn-hud" data-captain="${this.escapeHtml(c.id)}" data-action="hail">HAIL</button>
                    <button class="btn-hud" data-captain="${this.escapeHtml(c.id)}" data-action="buy" ${captainFuel > 0 ? "" : "disabled"} title="${this.escapeHtml(buyTitle)}">BUY FUEL</button>
                    <button class="btn-hud" data-captain="${this.escapeHtml(c.id)}" data-action="sell" ${holdFuel > 0 ? "" : "disabled"} title="${this.escapeHtml(sellTitle)}">SELL FUEL</button>
                    ${c.archetype === "mercenary" ? `<button class="btn-hud btn-cyan" data-captain="${this.escapeHtml(c.id)}" data-action="hire" ${canHire ? "" : "disabled"} title="${this.escapeHtml(hireTitle)}">HIRE · ${hireCost}</button>` : ""}
                    <button class="btn-hud btn-green" data-captain="${this.escapeHtml(c.id)}" data-action="ally" ${canAlly ? "" : "disabled"} title="${this.escapeHtml(allyTitle)}">ALLY</button>
                </div>
            </div>
        `;
        }).join("") || '<div class="ai-card">No AI captains in range.</div>';
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

    async handleDiplomacyAction(factionId, action) {
        if (!factionId || !action) return;
        const amount = action === "gift" ? 300 : 0;
        await this.postAction("/api/diplomacy", { faction_id: factionId, action, amount }, "empire");
    }

    async handleReconstructAction(mode = "credits") {
        if (!this.selectedTarget || this.selectedType !== "body") return;
        const res = await this.postAction("/api/reconstruct", {
            body_id: this.selectedTarget.id,
            mode,
        });
        if (res && res.ok) {
            this.sound.playChime();
            this.updateTargetCard();
        }
    }

    async handleSalvage() {
        this.sound.init();
        const strategy = this.salvageStrategy || "balanced";
        const res = await this.postAction("/api/salvage", { strategy });
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
        if (!this.selectedTarget) return;
        if (mode === "quantum") {
            this.sound?.playWarp?.();
        } else {
            this.sound?.playJump?.();
        }
        if (this.selectedType === "point") {
            const fromId = this.state?.ship?.orbiting_body_id || null;
            const res = await this.postAction("/api/travel/point", {
                distance_au: this.selectedTarget.au,
                angle: this.selectedTarget.angle,
                mode,
            });
            if (res && res.ok) {
                const activeTravel = this.state?.ship?.travel || this.state?.travel || null;
                this.startTravelAnimation(fromId, null, activeTravel);
                this.selectedTarget = null;
            }
            this.updateTargetCard();
            return;
        }
        if (this.selectedType !== "body") return;
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
        const isPoint = Boolean(activeTravel && activeTravel.destination_body_id == null);
        if (!isPoint && !to) return;
        // A point trip has no destination body: both ends come from the waypoint
        // coordinates, and the origin falls back to the ship's open-space anchor.
        const ship = this.state.ship || {};
        const fromAngle = from ? (from.current_angle || 0) : Number(ship.waypoint_angle ?? 0);
        const fromRadius = from ? from.orbit_radius : Number(ship.waypoint_au ?? 0);
        const toAngle = isPoint ? Number(activeTravel?.waypoint_angle ?? 0) : (to.current_angle || 0);
        const toRadius = isPoint ? Number(activeTravel?.waypoint_au ?? 0) : to.orbit_radius;
        const speed = Math.max(0.25, this.state.time?.speed || 1.0);
        const totalTicks = activeTravel
            ? Math.max(1, activeTravel.duration_ticks || (activeTravel.arrival_tick - activeTravel.started_tick) || 1)
            : 1;
        const travelKey = activeTravel
            ? `${activeTravel.destination_body_id ?? "point"}:${activeTravel.started_tick}:${activeTravel.waypoint_au ?? ""}:${activeTravel.waypoint_angle ?? ""}`
            : `orbit:${destId}:${performance.now()}`;
        this.travelAnimation = {
            fromBodyId: origId,
            toBodyId: isPoint ? null : destId,
            isPoint: isPoint,
            travelKey: travelKey,
            fromAngle: fromAngle,
            fromRadius: fromRadius,
            toAngle: toAngle,
            toRadius: toRadius,
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
        if (activeTravel?.mode === "quantum" && this.lastShipPosition) {
            this.particles?.quantumFlash?.(this.lastShipPosition.x, this.lastShipPosition.y, "#7fb7c9");
        }
    }

    drawPointSelection(ctx, cx, cy, auScale, ship) {
        if (this.selectedType !== "point" || !this.selectedTarget) return;
        if (ship?.travel || this.state?.travel || this.travelAnimation) return;
        const au = Number(this.selectedTarget.au);
        const angle = Number(this.selectedTarget.angle);
        if (!Number.isFinite(au) || !Number.isFinite(angle) || au <= 0) return;
        const tx = cx + Math.cos(angle) * au * auScale;
        const ty = cy + Math.sin(angle) * au * auScale;
        const orbitBody = (this.state?.current_system?.bodies || [])
            .find(b => b.id === ship?.orbiting_body_id);
        const originAu = orbitBody ? Number(orbitBody.orbit_radius || 0) : Number(ship?.waypoint_au || 0);
        const originAngle = orbitBody ? Number(orbitBody.current_angle || 0) : Number(ship?.waypoint_angle || 0);
        const ox = cx + Math.cos(originAngle) * originAu * auScale;
        const oy = cy + Math.sin(originAngle) * originAu * auScale;
        ctx.save();
        ctx.setLineDash([4, 5]);
        ctx.strokeStyle = "rgba(127, 183, 201, 0.55)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(ox, oy);
        ctx.lineTo(tx, ty);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.strokeStyle = "#7fb7c9";
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.arc(tx, ty, 11, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(tx, ty, 18, 0, Math.PI * 2);
        ctx.globalAlpha = 0.45;
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.moveTo(tx - 15, ty);
        ctx.lineTo(tx + 15, ty);
        ctx.moveTo(tx, ty - 15);
        ctx.lineTo(tx, ty + 15);
        ctx.stroke();
        ctx.font = "12px 'Cascadia Mono', Consolas, monospace";
        ctx.fillStyle = "#7fb7c9";
        ctx.fillText(
            `VECTOR ${au.toFixed(2)} AU // ${(angle * 180 / Math.PI).toFixed(0)} DEG`,
            tx + 16,
            ty - 12,
        );
        ctx.restore();
    }

    drawTravelAnimation(ctx, cx, cy, auScale) {
        const activeTravel = this.state?.ship?.travel || this.state?.travel || null;
        const travelKey = activeTravel
            ? `${activeTravel.destination_body_id ?? "point"}:${activeTravel.started_tick}:${activeTravel.waypoint_au ?? ""}:${activeTravel.waypoint_angle ?? ""}`
            : "";
        if (this.travelAnimationEnabled && activeTravel) {
            if (!this.travelAnimation || this.travelAnimation.travelKey !== travelKey) {
                this.startTravelAnimation(activeTravel.origin_body_id, activeTravel.destination_body_id, activeTravel);
            }
        }
        if (!this.travelAnimation) return;
        const anim = this.travelAnimation;
        const bodies = this.state?.current_system?.bodies || [];
        const liveFrom = bodies.find(b => b.id === anim.fromBodyId);
        const liveTo = anim.isPoint ? null : bodies.find(b => b.id === anim.toBodyId);
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

        // The destination reticle stays on the selected vector for the whole trip.
        ctx.beginPath();
        ctx.arc(tx, ty, 9, 0, Math.PI * 2);
        ctx.strokeStyle = anim.isPoint ? "#7fb7c9" : "rgba(127, 183, 201, 0.55)";
        ctx.lineWidth = 1.25;
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(tx - 12, ty);
        ctx.lineTo(tx + 12, ty);
        ctx.moveTo(tx, ty - 12);
        ctx.lineTo(tx, ty + 12);
        ctx.stroke();
        if (anim.isPoint) {
            ctx.font = "12px 'Segoe UI'";
            ctx.fillStyle = "#7fb7c9";
            ctx.fillText("DESTINATION VECTOR", tx + 15, ty - 11);
        }

        const heading = Math.atan2(ty - oy, tx - ox);
        if (this.celestial) {
            this.celestial.drawShip(ctx, x, y, heading, 9 * Math.max(1, this.zoom), "#7fb7c9", this.shipVariant());
        } else {
            ctx.beginPath();
            ctx.arc(x, y, 5, 0, Math.PI * 2);
            ctx.fillStyle = "#7fb7c9";
            ctx.fill();
        }
        this.lastShipPosition = { x, y };
        this.particles?.warp(x, y, heading, "#7fb7c9");
        this.particles?.warp(x, y, heading, "#b7e4ff");
        ctx.font = "12px 'Cascadia Mono', Consolas, monospace";
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
            if (anim.mode === "quantum") {
                this.particles?.quantumFlash?.(tx, ty, "#7fb7c9");
            }
            this.sound?.playDock?.();
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

    // Every control gets a stable handle so a headless test or AI can click it by name.
    ensureTestId(element, index) {
        if (element.dataset.testid) return element.dataset.testid;
        let testId = "";
        const identity = [
            ["slot", "slot"], ["lot", "lot"], ["type", "drone"],
            ["mode", "mode"], ["action", "action"],
        ].find(([key]) => element.dataset[key] !== undefined && element.dataset[key] !== "");
        if (element.id) {
            testId = `id-${element.id}`;
        } else if (identity) {
            // The index keeps repeated row controls (market BUY/SELL) addressable.
            testId = `${identity[1]}-${element.dataset[identity[0]]}-${index}`;
        } else {
            const label = (element.textContent || element.getAttribute("aria-label") || element.value || "")
                .trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
            testId = `${label || element.tagName.toLowerCase()}-${index}`;
        }
        element.dataset.testid = testId;
        return testId;
    }

    clickMap() {
        const selector = [
            "button", "a[href]", "select", "input[type='range']", "input[type='checkbox']",
            "[role='button']", "[data-action]", "[data-captain]", "[data-diplo]", "[data-tab]",
            "[data-war]", "[data-petition-ceasefire]", "[data-mediate-war]", "[data-dismiss-event]",
        ].join(",");
        const controls = Array.from(document.querySelectorAll(selector))
            .filter(element => !element.closest("[aria-hidden='true']"));
        return controls.map((element, index) => ({
            testid: this.ensureTestId(element, index),
            tag: element.tagName.toLowerCase(),
            id: element.id || null,
            text: (element.textContent || element.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 48),
            disabled: Boolean(element.disabled),
            hidden: element.offsetParent === null,
            action: element.getAttribute("data-action")
                || element.getAttribute("data-tab")
                || element.getAttribute("data-captain")
                || element.getAttribute("data-diplo")
                || null,
        }));
    }
}

// Instantiate on load
window.addEventListener("DOMContentLoaded", () => {
    window.cockpit = new CockpitApp();
});

// Stable handles for automated play: no human needed to enumerate or click the cockpit.
window.voidfarerClickMap = () => (window.cockpit ? window.cockpit.clickMap() : []);
window.voidfarerAgentActions = () => fetch("/api/agent/actions").then(response => response.json());
