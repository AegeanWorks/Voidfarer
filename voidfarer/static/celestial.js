/**
 * VOIDFARER // Celestial renderer
 * Procedural, seeded models for stars, worlds, giants, stations, megastructures and the flagship.
 * Each body's surface is painted once into an offscreen sprite keyed by id and pixel size;
 * per frame only the sprite blit, the star-facing terminator and small animations are drawn.
 */

const ROCKY_STYLES = {
    terrestrial: { ocean: "#1d4e89", land: ["#6a994e", "#a7c957", "#d4a373"], caps: true, clouds: 0.35, atmo: "120, 180, 255" },
    oceanic: { ocean: "#0f5e8c", land: ["#7fb069", "#e6c79c"], landShare: 0.35, caps: true, clouds: 0.45, atmo: "110, 200, 255" },
    super_earth: { ocean: "#264653", land: ["#6a994e", "#386641", "#bc6c25"], landShare: 1.4, clouds: 0.3, atmo: "140, 200, 160" },
    savanna: { ocean: "#2a6f97", land: ["#90be6d", "#c9a227", "#b08968"], landShare: 1.6, clouds: 0.2, atmo: "150, 200, 255" },
    tundra: { ocean: "#3d5a80", land: ["#bde0fe", "#e0e1dd", "#98c1d9"], landShare: 1.2, caps: true, clouds: 0.25, atmo: "190, 220, 255" },
    desert_world: { surface: "#e9c46a", craters: 6, dunes: "#c58b4a", atmo: "233, 196, 106" },
    barren: { surface: "#8d99ae", craters: 14 },
    ice_world: { surface: "#cfe8ef", cracks: "#7fb7c9", caps: true, atmo: "200, 235, 255" },
    lava_world: { surface: "#2b0f0a", veins: "#ff7b2e", atmo: "255, 110, 60" },
    volcanic: { surface: "#33130d", veins: "#ff5a2e", craters: 8, atmo: "255, 100, 60" },
    toxic: { surface: "#7a8f3c", bands: ["#b5e48c", "#d9ed92", "#99d98c"], atmo: "190, 230, 120" },
};
const GIANT_STYLES = {
    gas_giant: { ring: false, storms: 2, atmo: "244, 162, 97", bands: ["#f4a261", "#e76f51", "#ffd7a8"] },
    ringed_giant: { ring: true, storms: 1, atmo: "230, 214, 190", bands: ["#c9ada7", "#e6d5c3", "#a98f88"] },
    ice_giant: { ring: false, storms: 1, atmo: "162, 210, 255", bands: ["#a2d2ff", "#c8e7ff", "#7fb7d9"] },
    methane_storm: { ring: false, storms: 2, atmo: "162, 230, 220", bands: ["#70c1b3", "#b2f7ef", "#4f9d92"] },
};
const STATION_TYPES = new Set(["orbital_station", "research_outpost", "quantum_relay", "solar_collector"]);
// One slow axial turn per four minutes keeps a rocky surface alive without drawing the eye.
const SURFACE_SPIN_PERIOD_MS = 240000;

function celestialHash(text) {
    let h = 2166136261;
    for (let i = 0; i < text.length; i++) {
        h ^= text.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return h >>> 0;
}

function celestialRng(seedText) {
    let a = celestialHash(seedText) || 1;
    return () => {
        a |= 0; a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function shade(hex, amount) {
    const valid = /^#[0-9a-fA-F]{6}$/.test(hex || "") ? hex : "#8899aa";
    const rgb = [1, 3, 5].map(i => parseInt(valid.slice(i, i + 2), 16));
    const mixed = rgb.map(c => Math.round(amount >= 0 ? c + (255 - c) * amount : c * (1 + amount)));
    return `rgb(${mixed[0]}, ${mixed[1]}, ${mixed[2]})`;
}

class CelestialRenderer {
    constructor() {
        this.sprites = new Map();
    }

    // Draws one body at (x, y) with on-screen radius r; lightAngle points from the body to its star.
    drawBody(ctx, body, x, y, r, lightAngle, now, dpr = 1) {
        const type = body.body_type;
        if (type === "black_hole") return this.drawBlackHole(ctx, x, y, r, now);
        if (type === "wormhole") return this.drawWormhole(ctx, x, y, r, now);
        if (type === "jump_gate" || (body.name && body.name.toLowerCase().includes("gate"))) {
            return this.drawJumpGateSingularity(ctx, x, y, Math.max(r, 9), now);
        }
        if (type === "comet" || (body.name && body.name.toLowerCase().includes("comet"))) {
            return this.drawComet(ctx, body, x, y, Math.max(r, 5), lightAngle, now);
        }
        if (type === "asteroid_belt") return; // drawn along its orbit by drawAsteroidBelt
        // Stations are tiny in kilometres; keep their models legible on the map.
        if (STATION_TYPES.has(type)) r = Math.max(r, 7);
        const sprite = this.sprite(body, r, dpr);
        const spin = STATION_TYPES.has(type) ? now * 0.35 : this.surfaceSpin(body, now);
        ctx.save();
        ctx.translate(x, y);
        if (spin) ctx.rotate(spin);
        ctx.drawImage(sprite.canvas, -sprite.half, -sprite.half, sprite.half * 2, sprite.half * 2);
        ctx.restore();
        if (STATION_TYPES.has(type)) this.drawStationSignal(ctx, x, y, r, now, body.color || "currentColor");
        if (ROCKY_STYLES[type] && ROCKY_STYLES[type].caps) this.drawCaps(ctx, x, y, r);
        if (ROCKY_STYLES[type] && ROCKY_STYLES[type].clouds) {
            this.drawCloudDrift(ctx, body, x, y, r, now);
        }
        if (ROCKY_STYLES[type] || GIANT_STYLES[type]) {
            this.drawLimb(ctx, x, y, r, lightAngle);
            this.drawRayleighAtmosphere(ctx, body, x, y, r, lightAngle);
            this.drawTerminator(ctx, x, y, r, lightAngle);
            if (ROCKY_STYLES[type] && (type === "terrestrial" || type === "super_earth" || type === "savanna" || (body.name && (body.name.includes("Citadel") || body.name.includes("Earth"))))) {
                this.drawNightsideCityLights(ctx, body, x, y, r, lightAngle, now);
            }
        }
        if (GIANT_STYLES[type] && GIANT_STYLES[type].ring) {
            this.drawRingShadow(ctx, body, x, y, r);
            this.drawRingFront(ctx, body, x, y, r);
        }
    }

    sprite(body, r, dpr) {
        const px = Math.max(3, Math.round(r * dpr / 4) * 4);
        const key = `${body.id}|${body.body_type}|${px}`;
        let sprite = this.sprites.get(key);
        if (sprite) {
            this.sprites.delete(key);
            this.sprites.set(key, sprite);
            return sprite;
        }
        const pad = GIANT_STYLES[body.body_type] && GIANT_STYLES[body.body_type].ring ? 2.6 : 1.5;
        const half = r * pad;
        const size = Math.ceil(px * pad * 2);
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        // Paint in device pixels; drawBody maps the sprite back to CSS pixels.
        ctx.translate(size / 2, size / 2);
        const R = px;
        const rng = celestialRng(body.id || body.name || "body");
        const type = body.body_type;
        if (ROCKY_STYLES[type]) this.paintRocky(ctx, R, ROCKY_STYLES[type], rng, body);
        else if (GIANT_STYLES[type]) this.paintGiant(ctx, R, GIANT_STYLES[type], rng, body);
        else if (type === "ring_world") this.paintRingWorld(ctx, R, body);
        else if (type === "dyson_sphere") this.paintDyson(ctx, R, body, rng);
        else if (STATION_TYPES.has(type)) this.paintStation(ctx, R, type, body);
        else this.paintRocky(ctx, R, { surface: body.color || "#8899aa", craters: 4 }, rng, body);
        sprite = { canvas, half };
        if (this.sprites.size > 600) this.sprites.delete(this.sprites.keys().next().value);
        this.sprites.set(key, sprite);
        return sprite;
    }

    clipDisc(ctx, R) {
        ctx.beginPath();
        ctx.arc(0, 0, R, 0, Math.PI * 2);
        ctx.clip();
    }

    // A slow axial turn so a rocky surface reads as a sphere rather than a decal. The
    // star-facing limb and terminator are drawn after the sprite, so the lit crescent
    // stays put while the terrain drifts under it. Giants keep their static bands.
    surfaceSpin(body, now) {
        if (!ROCKY_STYLES[body.body_type]) return 0;
        return ((now % SURFACE_SPIN_PERIOD_MS) / SURFACE_SPIN_PERIOD_MS) * Math.PI * 2;
    }

    // Polar caps belong to the axis, not the surface, so they are painted over the
    // turning sprite instead of being baked into it.
    drawCaps(ctx, x, y, r) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.clip();
        ctx.fillStyle = "rgba(240, 248, 255, 0.85)";
        ctx.beginPath(); ctx.ellipse(x, y - r * 0.95, r * 0.7, r * 0.22, 0, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.ellipse(x, y + r * 0.97, r * 0.55, r * 0.16, 0, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
    }

    // A day-side rim that follows the actual star direction. The sprite itself carries no
    // baked highlight, so the lit edge always agrees with the terminator.
    drawLimb(ctx, x, y, r, lightAngle) {
        const lx = x + Math.cos(lightAngle) * r * 0.55;
        const ly = y + Math.sin(lightAngle) * r * 0.55;
        const glow = ctx.createRadialGradient(lx, ly, r * 0.08, lx, ly, r * 1.08);
        glow.addColorStop(0, "rgba(255, 255, 255, 0.20)");
        glow.addColorStop(0.45, "rgba(255, 255, 255, 0.055)");
        glow.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.clip();
        ctx.fillStyle = glow;
        ctx.fillRect(x - r, y - r, r * 2, r * 2);
        ctx.restore();
    }

    atmosphere(ctx, R, rgb) {
        if (!rgb) return;
        const glow = ctx.createRadialGradient(0, 0, R * 0.92, 0, 0, R * 1.35);
        glow.addColorStop(0, `rgba(${rgb}, 0.55)`);
        glow.addColorStop(1, `rgba(${rgb}, 0)`);
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(0, 0, R * 1.35, 0, Math.PI * 2);
        ctx.fill();
    }

    paintRocky(ctx, R, style, rng, body) {
        this.atmosphere(ctx, R, style.atmo);
        ctx.save();
        this.clipDisc(ctx, R);
        ctx.fillStyle = style.ocean || style.surface;
        ctx.fillRect(-R, -R, R * 2, R * 2);
        if (style.land) {
            const blobs = Math.round(5 * (style.landShare || 1));
            for (let i = 0; i < blobs; i++) {
                ctx.fillStyle = style.land[i % style.land.length];
                const bx = (rng() * 2 - 1) * R;
                const by = (rng() * 1.6 - 0.8) * R;
                for (let k = 0; k < 5; k++) {
                    ctx.beginPath();
                    ctx.arc(bx + (rng() - 0.5) * R * 0.6, by + (rng() - 0.5) * R * 0.4, R * (0.12 + rng() * 0.22), 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        }
        if (style.bands) {
            for (let y = -R; y < R; y += R * (0.12 + rng() * 0.12)) {
                ctx.fillStyle = style.bands[Math.floor(rng() * style.bands.length)];
                ctx.globalAlpha = 0.55;
                ctx.fillRect(-R, y, R * 2, R * (0.06 + rng() * 0.1));
            }
            ctx.globalAlpha = 1;
        }
        if (style.dunes) {
            ctx.strokeStyle = style.dunes;
            ctx.globalAlpha = 0.5;
            ctx.lineWidth = Math.max(1, R * 0.06);
            for (let i = 0; i < 6; i++) {
                const y = (rng() * 2 - 1) * R;
                ctx.beginPath();
                ctx.moveTo(-R, y);
                ctx.quadraticCurveTo(0, y + (rng() - 0.5) * R * 0.5, R, y + (rng() - 0.5) * R * 0.3);
                ctx.stroke();
            }
            ctx.globalAlpha = 1;
        }
        for (let i = 0; i < (style.craters || 0); i++) {
            const cr = R * (0.05 + rng() * 0.16);
            const x = (rng() * 2 - 1) * R;
            const y = (rng() * 2 - 1) * R;
            ctx.fillStyle = "rgba(0, 0, 0, 0.28)";
            ctx.beginPath(); ctx.arc(x, y, cr, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
            ctx.lineWidth = Math.max(0.6, cr * 0.25);
            ctx.beginPath(); ctx.arc(x - cr * 0.15, y - cr * 0.15, cr, Math.PI * 0.9, Math.PI * 1.7); ctx.stroke();
        }
        if (style.veins || style.cracks) {
            ctx.strokeStyle = style.veins || style.cracks;
            ctx.lineWidth = Math.max(0.8, R * (style.veins ? 0.07 : 0.035));
            if (style.veins) { ctx.shadowColor = style.veins; ctx.shadowBlur = R * 0.35; }
            for (let i = 0; i < 7; i++) {
                let x = (rng() * 2 - 1) * R;
                let y = (rng() * 2 - 1) * R;
                ctx.beginPath();
                ctx.moveTo(x, y);
                for (let k = 0; k < 4; k++) {
                    x += (rng() - 0.5) * R * 0.7;
                    y += (rng() - 0.5) * R * 0.7;
                    ctx.lineTo(x, y);
                }
                ctx.stroke();
            }
            ctx.shadowBlur = 0;
        }
        if (style.clouds) {
            ctx.strokeStyle = `rgba(255, 255, 255, ${style.clouds})`;
            ctx.lineWidth = Math.max(0.8, R * 0.09);
            ctx.lineCap = "round";
            for (let i = 0; i < 6; i++) {
                const y = (rng() * 1.6 - 0.8) * R;
                const x = (rng() * 2 - 1) * R;
                ctx.beginPath(); ctx.moveTo(x - R * 0.35, y); ctx.lineTo(x + R * 0.35, y + (rng() - 0.5) * R * 0.15); ctx.stroke();
            }
        }
        ctx.restore();
    }

    paintGiant(ctx, R, style, rng, body) {
        const base = body.color || "#c9ada7";
        const bands = style.bands || [shade(base, 0.12), base, shade(base, -0.18)];
        if (style.ring) this.paintRingBack(ctx, R, body);
        this.atmosphere(ctx, R, style.atmo || "200, 210, 230");
        ctx.save();
        this.clipDisc(ctx, R);
        ctx.fillStyle = base;
        ctx.fillRect(-R, -R, R * 2, R * 2);
        // Latitudinal belts with a gentle wave so the planet reads as atmosphere,
        // not as a stack of straight rectangles.
        for (let y = -R; y < R;) {
            const h = R * (0.07 + rng() * 0.16);
            const color = bands[Math.floor(rng() * bands.length)];
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.72;
            ctx.beginPath();
            ctx.moveTo(-R, y);
            for (let x = -R; x <= R; x += R * 0.25) {
                ctx.lineTo(x, y + Math.sin(x / R * 2.2 + y * 0.05) * R * 0.012);
            }
            ctx.lineTo(R, y + h);
            ctx.lineTo(-R, y + h);
            ctx.closePath();
            ctx.fill();
            y += h;
        }
        ctx.globalAlpha = 1;
        const storms = Math.max(0, style.storms ?? 1);
        for (let i = 0; i < storms; i++) {
            ctx.fillStyle = shade(base, -0.34);
            ctx.beginPath();
            ctx.ellipse((rng() - 0.5) * R * 1.2, (rng() - 0.5) * R * 1.1, R * (0.16 + rng() * 0.1), R * (0.07 + rng() * 0.05), (rng() - 0.5) * 0.5, 0, Math.PI * 2);
            ctx.fill();
        }
        // A thin bright equatorial haze catches the star and separates the belts.
        const haze = ctx.createLinearGradient(0, -R * 0.25, 0, R * 0.25);
        haze.addColorStop(0, "rgba(255, 255, 255, 0)");
        haze.addColorStop(0.5, "rgba(255, 255, 255, 0.08)");
        haze.addColorStop(1, "rgba(255, 255, 255, 0)");
        ctx.fillStyle = haze;
        ctx.fillRect(-R, -R * 0.25, R * 2, R * 0.5);
        ctx.restore();
    }

    ringTilt(body) {
        return 0.25 + (celestialHash(body.id || "ring") % 40) / 100;
    }

    paintRingBack(ctx, R, body) {
        ctx.save();
        ctx.rotate(this.ringTilt(body));
        ctx.strokeStyle = "rgba(220, 200, 170, 0.55)";
        ctx.lineWidth = R * 0.22;
        ctx.beginPath();
        ctx.ellipse(0, 0, R * 2.05, R * 0.55, 0, Math.PI, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
    }

    drawRayleighAtmosphere(ctx, body, x, y, r, lightAngle) {
        const type = body?.body_type;
        const style = ROCKY_STYLES[type] || GIANT_STYLES[type];
        if (!style || !style.atmo) return;

        // 1. Inner atmospheric Rayleigh scattering gradient
        const rx = x + Math.cos(lightAngle) * r * 0.82;
        const ry = y + Math.sin(lightAngle) * r * 0.82;
        const atmoGlow = ctx.createRadialGradient(rx, ry, r * 0.08, x, y, r * 1.14);
        atmoGlow.addColorStop(0, `rgba(${style.atmo}, 0.65)`);
        atmoGlow.addColorStop(0.38, "rgba(255, 175, 105, 0.28)");
        atmoGlow.addColorStop(0.85, "rgba(0, 0, 0, 0)");
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, r * 1.02, 0, Math.PI * 2);
        ctx.clip();
        ctx.fillStyle = atmoGlow;
        ctx.fillRect(x - r * 1.2, y - r * 1.2, r * 2.4, r * 2.4);
        ctx.restore();

        // 2. Outer forward-scattering airglow crescent along the stellar limb
        ctx.save();
        const limbGlow = ctx.createRadialGradient(x, y, r * 0.94, x, y, r * 1.22);
        const atmoCol = (o) => `rgba(${style.atmo}, ${o})`;
        limbGlow.addColorStop(0, atmoCol(0.55));
        limbGlow.addColorStop(0.45, atmoCol(0.22));
        limbGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = limbGlow;
        ctx.beginPath();
        ctx.arc(x, y, r * 1.22, lightAngle - Math.PI * 0.48, lightAngle + Math.PI * 0.48);
        ctx.arc(x, y, r * 0.94, lightAngle + Math.PI * 0.48, lightAngle - Math.PI * 0.48, true);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    }

    drawRingShadow(ctx, body, x, y, r) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(this.ringTilt(body));
        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.clip();
        ctx.fillStyle = "rgba(4, 7, 16, 0.62)";
        ctx.beginPath();
        ctx.ellipse(0, r * 0.14, r * 1.8, r * 0.16, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    drawRingFront(ctx, body, x, y, r) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(this.ringTilt(body));
        ctx.strokeStyle = "rgba(230, 210, 180, 0.7)";
        ctx.lineWidth = r * 0.22;
        ctx.beginPath();
        ctx.ellipse(0, 0, r * 2.05, r * 0.55, 0, 0, Math.PI);
        ctx.stroke();
        ctx.restore();
    }

    paintRingWorld(ctx, R, body) {
        const color = body.color || "#c77dff";
        ctx.strokeStyle = shade(color, -0.35);
        ctx.lineWidth = R * 0.42;
        ctx.beginPath(); ctx.ellipse(0, 0, R * 1.25, R * 0.42, -0.35, 0, Math.PI * 2); ctx.stroke();
        ctx.strokeStyle = "rgba(144, 190, 109, 0.9)";
        ctx.lineWidth = R * 0.14;
        ctx.beginPath(); ctx.ellipse(0, 0, R * 1.2, R * 0.38, -0.35, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = "#fff4d6";
        ctx.beginPath(); ctx.arc(0, 0, R * 0.22, 0, Math.PI * 2); ctx.fill();
    }

    paintDyson(ctx, R, body, rng) {
        // A Dyson swarm is a star wrapped in millions of independent collectors, not a
        // solid wireframe globe. Keep the shell mostly transparent: a dim stellar core,
        // faint orbital tracks, and discrete dark collector panels with gold edges.
        const glow = ctx.createRadialGradient(0, 0, R * 0.12, 0, 0, R * 1.2);
        glow.addColorStop(0, "rgba(255, 240, 190, 0.34)");
        glow.addColorStop(0.35, "rgba(255, 196, 96, 0.12)");
        glow.addColorStop(0.72, "rgba(255, 150, 50, 0.04)");
        glow.addColorStop(1, "rgba(255, 140, 40, 0)");
        ctx.fillStyle = glow;
        ctx.beginPath(); ctx.arc(0, 0, R * 1.2, 0, Math.PI * 2); ctx.fill();

        const core = ctx.createRadialGradient(0, 0, 0, 0, 0, R * 0.20);
        core.addColorStop(0, "#ffffff");
        core.addColorStop(0.38, "#fff0b0");
        core.addColorStop(1, "rgba(255, 170, 60, 0)");
        ctx.fillStyle = core;
        ctx.beginPath(); ctx.arc(0, 0, R * 0.20, 0, Math.PI * 2); ctx.fill();

        const bands = [
            { dist: 0.30, tilt: 0.90, panels: 11, spin: 0.35, size: 0.120 },
            { dist: 0.46, tilt: 0.72, panels: 15, spin: -0.22, size: 0.112 },
            { dist: 0.62, tilt: 0.55, panels: 19, spin: 0.12, size: 0.104 },
            { dist: 0.78, tilt: 0.38, panels: 23, spin: -0.40, size: 0.096 },
            { dist: 0.93, tilt: 0.22, panels: 27, spin: 0.05, size: 0.088 },
        ];
        for (const band of bands) {
            ctx.save();
            ctx.rotate(band.spin);
            ctx.strokeStyle = "rgba(255, 209, 102, 0.10)";
            ctx.lineWidth = Math.max(0.4, R * 0.008);
            ctx.beginPath();
            ctx.ellipse(0, 0, R * band.dist, R * band.dist * band.tilt, 0, 0, Math.PI * 2);
            ctx.stroke();
            for (let i = 0; i < band.panels; i++) {
                const angle = (i / band.panels) * Math.PI * 2 + rng() * 0.10;
                const dist = R * band.dist * (0.97 + rng() * 0.06);
                const x = Math.cos(angle) * dist;
                const y = Math.sin(angle) * dist * band.tilt;
                const w = Math.max(2.2, R * band.size);
                const h = Math.max(1.3, R * band.size * 0.58);
                ctx.save();
                ctx.translate(x, y);
                ctx.rotate(angle + Math.PI / 2);
                ctx.fillStyle = i % 7 === 0 ? "rgba(255, 226, 150, 0.98)" : "rgba(10, 14, 21, 0.98)";
                ctx.fillRect(-w / 2, -h / 2, w, h);
                ctx.strokeStyle = "rgba(255, 205, 120, 0.88)";
                ctx.lineWidth = Math.max(0.4, R * 0.007);
                ctx.strokeRect(-w / 2, -h / 2, w, h);
                ctx.restore();
            }
            ctx.restore();
        }

        // Broken shell arcs show the swarm is unbuilt, not a sealed planet.
        ctx.strokeStyle = "rgba(255, 236, 180, 0.35)";
        ctx.lineWidth = Math.max(0.6, R * 0.014);
        for (let i = 0; i < 4; i++) {
            const start = i * 1.6 + rng() * 0.3;
            ctx.beginPath();
            ctx.arc(0, 0, R * 0.99, start, start + 0.55);
            ctx.stroke();
        }
    }

    paintStation(ctx, R, type, body) {
        const color = body.color || "#00f0ff";
        ctx.lineCap = "round";
        if (type === "orbital_station") {
            // Horizontal photovoltaic solar array truss
            ctx.strokeStyle = color;
            ctx.lineWidth = Math.max(1, R * 0.08);
            ctx.beginPath();
            ctx.moveTo(-R * 1.45, 0); ctx.lineTo(-R * 0.85, 0);
            ctx.moveTo(R * 0.85, 0); ctx.lineTo(R * 1.45, 0);
            ctx.stroke();
            ctx.fillStyle = color;
            for (const dir of [-1, 1]) {
                for (let k = 0; k < 3; k++) {
                    const px = dir * (R * 0.98 + k * R * 0.15);
                    ctx.save();
                    ctx.globalAlpha = 0.72;
                    ctx.fillRect(px - R * 0.05, -R * 0.24, R * 0.10, R * 0.48);
                    ctx.restore();
                }
            }

            // Torus hull ring and spokes
            ctx.strokeStyle = color;
            ctx.lineWidth = Math.max(1, R * 0.18);
            ctx.beginPath(); ctx.arc(0, 0, R * 0.85, 0, Math.PI * 2); ctx.stroke();
            ctx.lineWidth = Math.max(1, R * 0.1);
            for (let i = 0; i < 4; i++) {
                const a = i * Math.PI / 2;
                ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(a) * R * 0.85, Math.sin(a) * R * 0.85); ctx.stroke();
            }

            // Docking clearance strobe beacons: seeded phase keeps each
            // station's 1.2s blink out of sync without freezing the animation.
            const strobePhase = (celestialHash(body.id || body.name || "station") % 1200) / 1200;
            const strobeLit = ((Date.now() / 1200 + strobePhase) % 1) < 0.5;
            for (let i = 0; i < 4; i++) {
                const a = i * Math.PI / 2;
                ctx.save();
                ctx.fillStyle = strobeLit ? color : "#ece4d4";
                ctx.beginPath();
                ctx.arc(Math.cos(a) * R * 0.85, Math.sin(a) * R * 0.85, Math.max(1.4, R * 0.09), 0, Math.PI * 2);
                ctx.fill();
                ctx.restore();
            }

            // Central command hub and observation spire
            ctx.fillStyle = "#e9f7ff";
            ctx.beginPath(); ctx.arc(0, 0, R * 0.25, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = color;
            ctx.beginPath(); ctx.arc(0, 0, R * 0.12, 0, Math.PI * 2); ctx.fill();
        } else if (type === "research_outpost") {
            ctx.fillStyle = color;
            ctx.fillRect(-R * 0.35, -R * 0.35, R * 0.7, R * 0.7);
            ctx.strokeStyle = "#e9f7ff";
            ctx.lineWidth = Math.max(1, R * 0.14);
            ctx.beginPath(); ctx.arc(R * 0.55, -R * 0.55, R * 0.45, Math.PI * 0.6, Math.PI * 1.4); ctx.stroke();
            ctx.fillStyle = "rgba(111, 195, 215, 0.85)";
            ctx.fillRect(-R * 1.0, -R * 0.12, R * 0.6, R * 0.24);
            ctx.fillRect(R * 0.4, -R * 0.12, R * 0.6, R * 0.24);
        } else if (type === "quantum_relay") {
            ctx.fillStyle = color;
            ctx.shadowColor = color;
            ctx.shadowBlur = R * 0.8;
            ctx.beginPath(); ctx.moveTo(0, -R); ctx.lineTo(R * 0.6, 0); ctx.lineTo(0, R); ctx.lineTo(-R * 0.6, 0); ctx.closePath(); ctx.fill();
            ctx.shadowBlur = 0;
            ctx.fillStyle = "#ffffff";
            ctx.beginPath(); ctx.arc(0, 0, R * 0.2, 0, Math.PI * 2); ctx.fill();
        } else {
            ctx.fillStyle = "#3a2f0b";
            ctx.fillRect(-R * 0.15, -R * 0.15, R * 0.3, R * 0.3);
            ctx.fillStyle = color;
            for (const sx of [-1, 1]) {
                for (let k = 0; k < 3; k++) ctx.fillRect(sx * (R * 0.25 + k * R * 0.26), -R * 0.32, R * 0.22, R * 0.64);
            }
        }

    }

    drawStationSignal(ctx, x, y, r, now, color) {
        const phase = (now % 1800) / 1800;
        const radius = r * (1.45 + phase * 0.9);
        ctx.save();
        ctx.globalAlpha = (1 - phase) * 0.32;
        ctx.strokeStyle = color;
        ctx.lineWidth = Math.max(0.6, r * 0.035);
        ctx.setLineDash([Math.max(2, r * 0.35), Math.max(2, r * 0.22)]);
        ctx.beginPath();
        ctx.arc(x, y, radius, -Math.PI * 0.25, Math.PI * 0.8);
        ctx.stroke();
        ctx.restore();
    }

    // Seeded cloud bands slide across the disc, giving inhabited worlds a living
    // atmosphere without repainting the cached surface sprite every frame.
    drawCloudDrift(ctx, body, x, y, r, now) {
        const style = ROCKY_STYLES[body.body_type];
        if (!style || !style.clouds) return;
        const rng = celestialRng(`${body.id || body.name || "world"}|clouds`);
        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.clip();
        ctx.strokeStyle = `rgba(255, 255, 255, ${Math.min(0.22, style.clouds * 0.45).toFixed(3)})`;
        ctx.lineWidth = Math.max(0.8, r * 0.07);
        ctx.lineCap = "round";
        for (let i = 0; i < 4; i++) {
            const bandY = (rng() * 1.6 - 0.8) * r;
            const width = r * (0.5 + rng() * 0.5);
            const seedX = (rng() * 2 - 1) * r;
            const drift = ((now * (2.4 + i * 0.6) + seedX) % (r * 3)) - r * 1.5;
            ctx.beginPath();
            ctx.moveTo(x + drift - width / 2, y + bandY);
            ctx.quadraticCurveTo(x + drift, y + bandY - r * 0.08, x + drift + width / 2, y + bandY);
            ctx.stroke();
        }
        ctx.restore();
    }

    // Night side: a gradient across the disc, dark away from the star.
    drawTerminator(ctx, x, y, r, lightAngle) {
        const dx = Math.cos(lightAngle) * r;
        const dy = Math.sin(lightAngle) * r;
        const shadow = ctx.createLinearGradient(x + dx, y + dy, x - dx, y - dy);
        // A soft but distinct terminator just past the middle of the disc.
        shadow.addColorStop(0, "rgba(0, 0, 0, 0)");
        shadow.addColorStop(0.46, "rgba(0, 0, 0, 0.04)");
        shadow.addColorStop(0.58, "rgba(2, 4, 10, 0.72)");
        shadow.addColorStop(1, "rgba(2, 4, 10, 0.93)");
        ctx.fillStyle = shadow;
        ctx.beginPath();
        ctx.arc(x, y, r * 1.01, 0, Math.PI * 2);
        ctx.fill();
    }

    // Populated worlds show sparkling urban constellations across their night-side hemisphere.
    drawNightsideCityLights(ctx, body, x, y, r, lightAngle, now) {
        if (r < 7) return;
        const rng = celestialRng(`${body.id || body.name}|city_lights`);
        const numClusters = Math.min(18, Math.max(5, Math.floor(r * 0.75)));
        const nx = Math.cos(lightAngle);
        const ny = Math.sin(lightAngle);

        ctx.save();
        ctx.beginPath();
        ctx.arc(x, y, r * 0.98, 0, Math.PI * 2);
        ctx.clip();

        for (let c = 0; c < numClusters; c++) {
            const angle = rng() * Math.PI * 2;
            const dist = rng() * r * 0.85;
            const px = Math.cos(angle) * dist;
            const py = Math.sin(angle) * dist;

            // Dot product with sun-facing vector: negative is night side
            const sunDot = (px * nx + py * ny) / r;
            if (sunDot > -0.12) continue;

            const nightWeight = Math.min(1.0, (-sunDot - 0.12) * 3.5);
            const twinkle = 0.8 + 0.2 * Math.sin(now * 3.0 + c * 1.7);
            const alpha = nightWeight * twinkle;
            const cx = x + px;
            const cy = y + py;

            const pts = 3 + Math.floor(rng() * 4);
            for (let p = 0; p < pts; p++) {
                const ox = (rng() - 0.5) * r * 0.18;
                const oy = (rng() - 0.5) * r * 0.18;
                const dotSize = Math.max(0.6, r * 0.025 * (0.8 + rng() * 0.6));
                const isHub = rng() > 0.7;
                ctx.fillStyle = isHub
                    ? `rgba(127, 183, 201, ${alpha * 0.85})`
                    : `rgba(226, 192, 120, ${alpha * 0.95})`;
                ctx.beginPath();
                ctx.arc(cx + ox, cy + oy, dotSize, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();
    }

    // Concentric rotating containment rings and Cherenkov pulse for hyperlane gates
    drawJumpGateSingularity(ctx, x, y, r, now) {
        ctx.save();
        ctx.translate(x, y);

        // Sub-space gravitational distortion halo
        ctx.strokeStyle = "rgba(169, 139, 189, 0.25)";
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 6]);
        ctx.beginPath();
        ctx.arc(0, 0, r * 1.35, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);

        // Outer electromagnetic containment gantry
        ctx.strokeStyle = "rgba(127, 183, 201, 0.85)";
        ctx.lineWidth = Math.max(1.2, r * 0.15);
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.9, 0, Math.PI * 2);
        ctx.stroke();

        // Counter-rotating containment field emitters with stator teeth
        const spin = now * 1.4;
        for (let i = 0; i < 3; i++) {
            const rot = spin * (i % 2 === 0 ? 1 : -1) + (i * Math.PI * 2) / 3;
            ctx.strokeStyle = i % 2 === 0 ? "rgba(169, 139, 189, 0.85)" : "rgba(127, 183, 201, 0.85)";
            ctx.lineWidth = Math.max(1, r * 0.09);
            ctx.beginPath();
            ctx.arc(0, 0, r * (0.65 + i * 0.12), rot, rot + Math.PI * 0.9);
            ctx.stroke();
        }

        // Stator arc lightning discharges between rings
        const arcSeed = Math.sin(now * 12.0);
        if (arcSeed > 0.45) {
            ctx.strokeStyle = "rgba(226, 240, 255, 0.9)";
            ctx.lineWidth = 1.0;
            ctx.beginPath();
            const arcAngle = (now * 2.5) % (Math.PI * 2);
            const r1 = r * 0.65;
            const r2 = r * 0.9;
            ctx.moveTo(Math.cos(arcAngle) * r1, Math.sin(arcAngle) * r1);
            const midAngle = arcAngle + 0.15 * Math.sin(now * 30.0);
            ctx.lineTo(Math.cos(midAngle) * ((r1 + r2) * 0.5), Math.sin(midAngle) * ((r1 + r2) * 0.5));
            ctx.lineTo(Math.cos(arcAngle + 0.05) * r2, Math.sin(arcAngle + 0.05) * r2);
            ctx.stroke();
        }

        // Cherenkov sub-space core with dark event horizon
        const pulse = 0.8 + 0.2 * Math.sin(now * 4.0);
        const coreGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 0.45 * pulse);
        coreGrad.addColorStop(0, "#ffffff");
        coreGrad.addColorStop(0.3, "rgba(127, 183, 201, 0.9)");
        coreGrad.addColorStop(0.7, "rgba(169, 139, 189, 0.4)");
        coreGrad.addColorStop(1, "rgba(6, 9, 15, 0)");
        ctx.fillStyle = coreGrad;
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.45 * pulse, 0, Math.PI * 2);
        ctx.fill();

        // Dark singularity eye
        ctx.fillStyle = "#06090f";
        ctx.beginPath();
        ctx.arc(0, 0, Math.max(1.2, r * 0.18), 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    // Comets: dual sublimation tails (curved dust plume + straight magnetic ion stream) and bright coma
    drawComet(ctx, body, x, y, r, lightAngle, now) {
        ctx.save();
        ctx.translate(x, y);
        const tailAngle = lightAngle + Math.PI;
        ctx.rotate(tailAngle);

        const tailLen = Math.max(40, r * 9.0);

        // 1. Broad curving golden dust tail (Type II)
        ctx.save();
        const dustGrad = ctx.createRadialGradient(0, 0, r * 0.8, tailLen * 0.6, tailLen * 0.25, tailLen * 0.85);
        dustGrad.addColorStop(0, "rgba(236, 228, 212, 0.7)");
        dustGrad.addColorStop(0.35, "rgba(226, 192, 120, 0.38)");
        dustGrad.addColorStop(0.7, "rgba(201, 163, 90, 0.14)");
        dustGrad.addColorStop(1, "rgba(6, 9, 15, 0)");
        ctx.fillStyle = dustGrad;
        ctx.beginPath();
        ctx.moveTo(0, -r * 0.6);
        ctx.quadraticCurveTo(tailLen * 0.45, tailLen * 0.18, tailLen, tailLen * 0.38);
        ctx.quadraticCurveTo(tailLen * 0.55, 0, 0, r * 0.6);
        ctx.closePath();
        ctx.fill();
        ctx.restore();

        // 2. Collimated cyan magnetic ion plasma tail (Type I)
        ctx.save();
        const ionGrad = ctx.createLinearGradient(0, 0, tailLen * 1.35, 0);
        ionGrad.addColorStop(0, "rgba(255, 255, 255, 0.95)");
        ionGrad.addColorStop(0.15, "rgba(127, 183, 201, 0.8)");
        ionGrad.addColorStop(0.55, "rgba(127, 183, 201, 0.35)");
        ionGrad.addColorStop(1, "rgba(127, 183, 201, 0)");
        ctx.fillStyle = ionGrad;
        ctx.beginPath();
        ctx.moveTo(0, -r * 0.35);
        ctx.lineTo(tailLen * 1.35, -r * 0.15);
        ctx.lineTo(tailLen * 1.35, r * 0.15);
        ctx.lineTo(0, r * 0.35);
        ctx.closePath();
        ctx.fill();

        // Ion stream filaments
        ctx.strokeStyle = "rgba(255, 255, 255, 0.5)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        const j = Math.sin(now * 6.0) * r * 0.2;
        ctx.lineTo(tailLen * 1.2, j);
        ctx.stroke();
        ctx.restore();

        // 3. Glowing sublimation coma surrounding icy nucleus
        const coma = ctx.createRadialGradient(0, 0, r * 0.2, 0, 0, r * 2.2);
        coma.addColorStop(0, "rgba(255, 255, 255, 0.95)");
        coma.addColorStop(0.4, "rgba(127, 183, 201, 0.6)");
        coma.addColorStop(1, "rgba(127, 183, 201, 0)");
        ctx.fillStyle = coma;
        ctx.beginPath();
        ctx.arc(0, 0, r * 2.2, 0, Math.PI * 2);
        ctx.fill();

        // Micro ice sparkle glints in coma
        for (let g = 0; g < 3; g++) {
            const gAngle = now * 2.0 + (g * Math.PI * 2) / 3;
            const gDist = r * (0.8 + 0.5 * Math.sin(now * 3.0 + g));
            const gx = Math.cos(gAngle) * gDist;
            const gy = Math.sin(gAngle) * gDist;
            ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
            ctx.fillRect(gx - 0.5, gy - 0.5, 1.2, 1.2);
        }

        // 4. Icy nucleus core
        ctx.fillStyle = "#f0f8ff";
        ctx.beginPath();
        ctx.arc(0, 0, Math.max(1.5, r * 0.7), 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    drawPulsar(ctx, body, x, y, r, now) {
        ctx.save();
        ctx.translate(x, y);
        const spin = now * 5.0;
        const jetLen = r * 5.5;
        const beamHalf = 0.22;
        // Dual relativistic collimated polar jet cones
        for (const dir of [0, Math.PI]) {
            const angle = spin + dir;
            ctx.save();
            ctx.rotate(angle);
            const jetGrad = ctx.createLinearGradient(0, 0, jetLen, 0);
            jetGrad.addColorStop(0, "rgba(255, 255, 255, 0.95)");
            jetGrad.addColorStop(0.2, "rgba(111, 235, 255, 0.75)");
            jetGrad.addColorStop(0.6, "rgba(51, 204, 255, 0.3)");
            jetGrad.addColorStop(1, "rgba(51, 204, 255, 0)");
            ctx.fillStyle = jetGrad;
            ctx.beginPath();
            ctx.moveTo(r * 0.4, 0);
            ctx.lineTo(jetLen, -Math.tan(beamHalf) * jetLen);
            ctx.lineTo(jetLen, Math.tan(beamHalf) * jetLen);
            ctx.closePath();
            ctx.fill();
            // Intense core laser spine
            ctx.strokeStyle = "rgba(255, 255, 255, 0.85)";
            ctx.lineWidth = Math.max(1, r * 0.12);
            ctx.beginPath();
            ctx.moveTo(r * 0.3, 0);
            ctx.lineTo(jetLen * 0.85, 0);
            ctx.stroke();
            ctx.restore();
        }
        // Magnetic torus / field loops
        ctx.strokeStyle = "rgba(80, 220, 255, 0.25)";
        ctx.lineWidth = Math.max(0.8, r * 0.08);
        for (let i = 0; i < 3; i++) {
            ctx.beginPath();
            ctx.ellipse(0, 0, r * (1.8 + i * 0.7), r * (0.8 + i * 0.3), spin * 0.3 + i * 0.5, 0, Math.PI * 2);
            ctx.stroke();
        }
        // Ultra-dense glowing core
        const core = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 1.5);
        core.addColorStop(0, "#ffffff");
        core.addColorStop(0.35, "#70e5ff");
        core.addColorStop(0.7, "#0099cc");
        core.addColorStop(1, "rgba(0, 102, 153, 0)");
        ctx.fillStyle = core;
        ctx.beginPath();
        ctx.arc(0, 0, r * 1.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
    }

    drawStar(ctx, body, x, y, r, now) {
        if (body && (body.spectral_type === "Neutron" || body.body_type === "pulsar" || (body.name && body.name.toLowerCase().includes("pulsar")))) {
            return this.drawPulsar(ctx, body, x, y, r, now);
        }
        if (body && (body.spectral_type === "Binary" || (body.name && body.name.toLowerCase().includes("binary")))) {
            return this.drawBinaryStar(ctx, body, x, y, r, now);
        }
        const color = body.color || "#ffd700";
        const pulse = 1 + Math.sin(now * 1.6) * 0.04;
        const corona = ctx.createRadialGradient(x, y, r * 0.4, x, y, r * 3.2 * pulse);
        corona.addColorStop(0, "rgba(255, 255, 255, 0.9)");
        corona.addColorStop(0.2, color);
        corona.addColorStop(0.45, shade(color, -0.2).replace("rgb", "rgba").replace(")", ", 0.35)"));
        corona.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = corona;
        ctx.beginPath(); ctx.arc(x, y, r * 3.2 * pulse, 0, Math.PI * 2); ctx.fill();

        // Magnetic Solar Prominence Loops
        this.drawSolarProminences(ctx, x, y, r, now, color, (body && body.seed) || 1);

        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(now * 0.05);
        ctx.strokeStyle = "rgba(255, 240, 200, 0.12)";
        ctx.lineWidth = Math.max(1, r * 0.08);
        for (let i = 0; i < 12; i++) {
            const a = i * Math.PI / 6;
            const len = r * (1.9 + (i % 3) * 0.45);
            ctx.beginPath(); ctx.moveTo(Math.cos(a) * r * 1.05, Math.sin(a) * r * 1.05); ctx.lineTo(Math.cos(a) * len, Math.sin(a) * len); ctx.stroke();
        }
        ctx.restore();
        const disc = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r);
        disc.addColorStop(0, "#fffef5");
        disc.addColorStop(0.6, shade(color, 0.35));
        disc.addColorStop(1, color);
        ctx.fillStyle = disc;
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
    }

    drawSolarProminences(ctx, x, y, r, now, color, seed) {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(now * 0.06);
        const count = 3 + (seed % 3);
        for (let i = 0; i < count; i++) {
            const baseAngle = i * (Math.PI * 2 / count) + Math.sin(now * 0.3 + i) * 0.2;
            const height = r * (0.32 + Math.sin(now * 1.4 + i * 2.3) * 0.14);
            const span = 0.22;
            const x1 = Math.cos(baseAngle - span) * r * 0.96;
            const y1 = Math.sin(baseAngle - span) * r * 0.96;
            const x2 = Math.cos(baseAngle + span) * r * 0.96;
            const y2 = Math.sin(baseAngle + span) * r * 0.96;
            const cx = Math.cos(baseAngle) * (r + height);
            const cy = Math.sin(baseAngle) * (r + height);

            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.quadraticCurveTo(cx, cy, x2, y2);
            ctx.strokeStyle = "rgba(255, 110, 50, 0.45)";
            ctx.lineWidth = Math.max(1.2, r * 0.05);
            ctx.stroke();

            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.quadraticCurveTo(cx, cy, x2, y2);
            ctx.strokeStyle = "rgba(255, 230, 160, 0.8)";
            ctx.lineWidth = Math.max(0.6, r * 0.02);
            ctx.stroke();
        }
        ctx.restore();
    }

    drawBinaryStar(ctx, body, x, y, r, now) {
        const orbitAngle = now * 0.25;
        const d = r * 1.35;
        const x1 = x + Math.cos(orbitAngle) * d * 0.45;
        const y1 = y + Math.sin(orbitAngle) * d * 0.45;
        const x2 = x - Math.cos(orbitAngle) * d * 0.55;
        const y2 = y - Math.sin(orbitAngle) * d * 0.55;
        const r1 = r * 0.85;
        const r2 = r * 0.58;
        const col1 = body.color || "#ffd700";
        const col2 = "#9bb0ff";

        // Roche-lobe mass transfer plasma bridge
        ctx.save();
        const bridgeGrad = ctx.createLinearGradient(x2, y2, x1, y1);
        bridgeGrad.addColorStop(0, "rgba(155, 176, 255, 0.6)");
        bridgeGrad.addColorStop(0.5, "rgba(255, 220, 140, 0.85)");
        bridgeGrad.addColorStop(1, "rgba(255, 215, 0, 0.5)");
        ctx.strokeStyle = bridgeGrad;
        ctx.lineWidth = Math.max(1.5, r * 0.12);
        ctx.beginPath();
        const midX = (x1 + x2) / 2 + Math.sin(orbitAngle) * (r * 0.2);
        const midY = (y1 + y2) / 2 - Math.cos(orbitAngle) * (r * 0.2);
        ctx.moveTo(x2, y2);
        ctx.quadraticCurveTo(midX, midY, x1, y1);
        ctx.stroke();
        ctx.restore();

        // Primary star corona & disc
        const corona1 = ctx.createRadialGradient(x1, y1, r1 * 0.3, x1, y1, r1 * 2.5);
        corona1.addColorStop(0, "rgba(255, 255, 255, 0.85)");
        corona1.addColorStop(0.3, col1);
        corona1.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = corona1;
        ctx.beginPath(); ctx.arc(x1, y1, r1 * 2.5, 0, Math.PI * 2); ctx.fill();

        this.drawSolarProminences(ctx, x1, y1, r1, now, col1, 7);

        const disc1 = ctx.createRadialGradient(x1 - r1 * 0.25, y1 - r1 * 0.25, r1 * 0.1, x1, y1, r1);
        disc1.addColorStop(0, "#fffef5");
        disc1.addColorStop(0.6, col1);
        disc1.addColorStop(1, shade(col1, -0.2));
        ctx.fillStyle = disc1;
        ctx.beginPath(); ctx.arc(x1, y1, r1, 0, Math.PI * 2); ctx.fill();

        // Companion star corona & disc
        const corona2 = ctx.createRadialGradient(x2, y2, r2 * 0.3, x2, y2, r2 * 2.2);
        corona2.addColorStop(0, "rgba(255, 255, 255, 0.9)");
        corona2.addColorStop(0.3, col2);
        corona2.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = corona2;
        ctx.beginPath(); ctx.arc(x2, y2, r2 * 2.2, 0, Math.PI * 2); ctx.fill();

        const disc2 = ctx.createRadialGradient(x2 - r2 * 0.25, y2 - r2 * 0.25, r2 * 0.1, x2, y2, r2);
        disc2.addColorStop(0, "#ffffff");
        disc2.addColorStop(0.6, col2);
        disc2.addColorStop(1, shade(col2, -0.25));
        ctx.fillStyle = disc2;
        ctx.beginPath(); ctx.arc(x2, y2, r2, 0, Math.PI * 2); ctx.fill();
    }

    drawBlackHole(ctx, x, y, r, now) {
        ctx.save();
        ctx.translate(x, y);
        // Einstein gravitational lensing photon sphere
        const lensGrad = ctx.createRadialGradient(0, 0, r * 0.95, 0, 0, r * 1.5);
        lensGrad.addColorStop(0, "rgba(255, 240, 200, 0.9)");
        lensGrad.addColorStop(0.4, "rgba(255, 170, 70, 0.45)");
        lensGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = lensGrad;
        ctx.beginPath(); ctx.arc(0, 0, r * 1.5, 0, Math.PI * 2); ctx.fill();

        // Upper gravitational lensed arc (back of accretion disk bent over top)
        ctx.save();
        ctx.scale(1, 0.32);
        ctx.rotate(-0.25);
        const lensArc = ctx.createRadialGradient(0, -r * 0.8, r * 0.4, 0, -r * 0.8, r * 2.8);
        lensArc.addColorStop(0, "rgba(255, 220, 150, 0.85)");
        lensArc.addColorStop(0.5, "rgba(255, 120, 40, 0.4)");
        lensArc.addColorStop(1, "rgba(100, 20, 140, 0)");
        ctx.fillStyle = lensArc;
        ctx.beginPath(); ctx.arc(0, -r * 0.5, r * 2.5, Math.PI * 0.85, Math.PI * 2.15); ctx.fill();
        ctx.restore();

        // Main tilted accretion disk with Doppler asymmetry
        ctx.save();
        ctx.rotate(-0.35);
        ctx.scale(1, 0.38);
        const disk = ctx.createRadialGradient(0, 0, r * 0.8, 0, 0, r * 3.0);
        disk.addColorStop(0, "rgba(255, 240, 200, 0.98)");
        disk.addColorStop(0.3, "rgba(255, 150, 50, 0.7)");
        disk.addColorStop(0.7, "rgba(200, 60, 40, 0.35)");
        disk.addColorStop(1, "rgba(60, 10, 80, 0)");
        ctx.fillStyle = disk;
        ctx.beginPath(); ctx.arc(0, 0, r * 3.0, 0, Math.PI * 2); ctx.fill();

        // Swirling relativistic accretion filaments
        ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
        ctx.lineWidth = Math.max(0.8, r * 0.1);
        for (let i = 0; i < 4; i++) {
            const rot = now * 1.2 + (i * Math.PI / 2);
            ctx.beginPath();
            ctx.arc(0, 0, r * (1.2 + i * 0.4), rot, rot + Math.PI * 0.8);
            ctx.stroke();
        }
        ctx.restore();

        // Absolute Event Horizon (pitch black core)
        ctx.fillStyle = "#010204";
        ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.fill();

        // Innermost Stable Circular Orbit (ISCO) sharp glowing rim
        const pulse = 0.65 + Math.sin(now * 2.5) * 0.15;
        ctx.strokeStyle = `rgba(255, 235, 200, ${pulse.toFixed(3)})`;
        ctx.lineWidth = Math.max(1, r * 0.12);
        ctx.beginPath(); ctx.arc(0, 0, r * 1.05, 0, Math.PI * 2); ctx.stroke();
        ctx.restore();
    }

    drawWormhole(ctx, x, y, r, now) {
        ctx.save();
        ctx.translate(x, y);
        for (let i = 0; i < 4; i++) {
            ctx.rotate(now * 0.6 + i);
            ctx.strokeStyle = `rgba(208, 191, 255, ${0.65 - i * 0.13})`;
            ctx.lineWidth = Math.max(1, r * 0.16);
            ctx.beginPath(); ctx.arc(0, 0, r * (0.5 + i * 0.32), 0, Math.PI * 1.3); ctx.stroke();
        }
        ctx.restore();
        const core = ctx.createRadialGradient(x, y, 0, x, y, r * 0.55);
        core.addColorStop(0, "#ffffff");
        core.addColorStop(1, "rgba(160, 120, 255, 0)");
        ctx.fillStyle = core;
        ctx.beginPath(); ctx.arc(x, y, r * 0.55, 0, Math.PI * 2); ctx.fill();
    }

    // A belt is a band of seeded rocks along its orbit rather than a single dot.
    drawAsteroidBelt(ctx, body, cx, cy, orbitR, zoom, now) {
        const rng = celestialRng(`${body.id}|belt`);
        const drift = now * (body.orbit_speed || 0.01) * 0.2;
        ctx.save();
        for (let i = 0; i < 160; i++) {
            const a = rng() * Math.PI * 2 + drift;
            const spread = (rng() - 0.5) * 10 * zoom;
            const size = 0.6 + rng() * 1.6 * Math.min(2, zoom);
            const shadeTone = 150 + Math.floor(rng() * 60);
            ctx.fillStyle = `rgba(${shadeTone}, ${shadeTone - 10}, ${shadeTone - 20}, ${0.55 + rng() * 0.3})`;
            ctx.fillRect(cx + Math.cos(a) * (orbitR + spread), cy + Math.sin(a) * (orbitR + spread), size, size);
        }
        ctx.restore();
    }

    drawMoons(ctx, body, x, y, r, now, lightAngle = 0) {
        const moons = body.moons || [];
        moons.slice(0, 4).forEach((moon, i) => {
            const dist = r * (1.9 + i * 0.6);
            const a = now * (0.6 / (i + 1)) + i * 2.1;
            const mx = x + Math.cos(a) * dist;
            const my = y + Math.sin(a) * dist * 0.6;
            const mr = Math.max(1, r * 0.18);
            ctx.fillStyle = "rgba(200, 205, 215, 0.9)";
            ctx.beginPath();
            ctx.arc(mx, my, mr, 0, Math.PI * 2);
            ctx.fill();
            // Cheap night-side shading so moons read as spheres, not flat dots.
            const shadow = ctx.createLinearGradient(
                mx + Math.cos(lightAngle) * mr, my + Math.sin(lightAngle) * mr,
                mx - Math.cos(lightAngle) * mr, my - Math.sin(lightAngle) * mr,
            );
            shadow.addColorStop(0, "rgba(0, 0, 0, 0)");
            shadow.addColorStop(1, "rgba(2, 4, 10, 0.55)");
            ctx.fillStyle = shadow;
            ctx.beginPath();
            ctx.arc(mx, my, mr, 0, Math.PI * 2);
            ctx.fill();
        });
    }

    // Hull silhouette, nose along `angle`. Variants keep class identity readable at
    // 6-12px on the radar and 16-20px in the combat viewport.
    drawShip(ctx, x, y, angle, size, color = "#8fbf9f", variant = "standard") {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle);
        const s = size;
        const glow = ctx.createRadialGradient(-s * 0.9, 0, 0, -s * 0.9, 0, s * 0.7);
        glow.addColorStop(0, color);
        glow.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = glow;
        ctx.beginPath(); ctx.arc(-s * 0.9, 0, s * 0.7, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = variant === "stealth" ? "#9fb2c6" : "#d9e2ec";
        ctx.strokeStyle = color;
        ctx.lineWidth = Math.max(1, s * 0.08);
        ctx.beginPath();
        if (variant === "freighter") {
            ctx.moveTo(s * 0.75, 0);
            ctx.lineTo(s * 0.45, -s * 0.45);
            ctx.lineTo(-s * 0.55, -s * 0.45);
            ctx.lineTo(-s * 0.75, -s * 0.2);
            ctx.lineTo(-s * 0.75, s * 0.2);
            ctx.lineTo(-s * 0.55, s * 0.45);
            ctx.lineTo(s * 0.45, s * 0.45);
        } else if (variant === "fighter") {
            ctx.moveTo(s * 1.15, 0);
            ctx.lineTo(-s * 0.15, -s * 0.22);
            ctx.lineTo(-s * 0.85, -s * 0.75);
            ctx.lineTo(-s * 0.55, -s * 0.05);
            ctx.lineTo(-s * 0.75, 0);
            ctx.lineTo(-s * 0.55, s * 0.05);
            ctx.lineTo(-s * 0.85, s * 0.75);
            ctx.lineTo(-s * 0.15, s * 0.22);
        } else if (variant === "explorer") {
            ctx.moveTo(s * 1.2, 0);
            ctx.lineTo(s * 0.1, -s * 0.16);
            ctx.lineTo(-s * 0.55, -s * 0.42);
            ctx.lineTo(-s * 0.85, -s * 0.2);
            ctx.lineTo(-s * 0.85, s * 0.2);
            ctx.lineTo(-s * 0.55, s * 0.42);
            ctx.lineTo(s * 0.1, s * 0.16);
        } else if (variant === "stealth") {
            ctx.moveTo(s * 1.05, 0);
            ctx.lineTo(-s * 0.25, -s * 0.35);
            ctx.lineTo(-s * 0.75, -s * 0.2);
            ctx.lineTo(-s * 0.55, 0);
            ctx.lineTo(-s * 0.75, s * 0.2);
            ctx.lineTo(-s * 0.25, s * 0.35);
        } else if (variant === "capital") {
            ctx.moveTo(s * 0.95, 0);
            ctx.lineTo(s * 0.55, -s * 0.28);
            ctx.lineTo(s * 0.15, -s * 0.5);
            ctx.lineTo(-s * 0.5, -s * 0.5);
            ctx.lineTo(-s * 0.8, -s * 0.25);
            ctx.lineTo(-s * 0.8, s * 0.25);
            ctx.lineTo(-s * 0.5, s * 0.5);
            ctx.lineTo(s * 0.15, s * 0.5);
            ctx.lineTo(s * 0.55, s * 0.28);
        } else {
            ctx.moveTo(s, 0);
            ctx.lineTo(-s * 0.35, -s * 0.28);
            ctx.lineTo(-s * 0.7, -s * 0.62);
            ctx.lineTo(-s * 0.8, -s * 0.2);
            ctx.lineTo(-s * 0.8, s * 0.2);
            ctx.lineTo(-s * 0.7, s * 0.62);
            ctx.lineTo(-s * 0.35, s * 0.28);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        if (variant === "freighter") {
            ctx.fillStyle = "rgba(0, 0, 0, 0.28)";
            ctx.fillRect(-s * 0.58, -s * 0.34, s * 0.34, s * 0.22);
            ctx.fillRect(-s * 0.58, s * 0.12, s * 0.34, s * 0.22);
        } else if (variant === "explorer") {
            ctx.strokeStyle = color;
            ctx.lineWidth = Math.max(0.8, s * 0.05);
            ctx.beginPath();
            ctx.arc(s * 0.36, 0, s * 0.13, 0, Math.PI * 2);
            ctx.stroke();
        } else if (variant === "stealth") {
            ctx.strokeStyle = "#8fbf9f";
            ctx.lineWidth = Math.max(0.8, s * 0.04);
            ctx.beginPath();
            ctx.moveTo(-s * 0.45, 0);
            ctx.lineTo(s * 0.7, 0);
            ctx.stroke();
        } else if (variant === "capital") {
            ctx.fillStyle = color;
            ctx.beginPath(); ctx.arc(-s * 0.62, -s * 0.28, s * 0.08, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.arc(-s * 0.62, s * 0.28, s * 0.08, 0, Math.PI * 2); ctx.fill();
        }
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(s * 0.25, 0, s * 0.13, 0, Math.PI * 2); ctx.fill();

        // High-tech cockpit canopy glint
        if (s >= 7) {
            ctx.fillStyle = "rgba(226, 192, 120, 0.75)";
            ctx.beginPath();
            ctx.ellipse(s * 0.32, 0, Math.max(1.2, s * 0.14), Math.max(0.8, s * 0.08), 0, 0, Math.PI * 2);
            ctx.fill();
        }

        // Navigation strobe beacons (port red, starboard green, 1.2s cadence)
        const strobeT = (Date.now() % 1200) / 1200;
        if (strobeT < 0.16 && s >= 8) {
            let wingY = s * 0.58;
            let wingX = -s * 0.55;
            if (variant === "fighter") { wingY = s * 0.72; wingX = -s * 0.82; }
            else if (variant === "explorer") { wingY = s * 0.40; wingX = -s * 0.52; }
            else if (variant === "capital") { wingY = s * 0.48; wingX = -s * 0.25; }
            ctx.fillStyle = "#c96b5a";
            ctx.beginPath();
            ctx.arc(wingX, -wingY, Math.max(1.0, s * 0.08), 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = "#8fbf9f";
            ctx.beginPath();
            ctx.arc(wingX, wingY, Math.max(1.0, s * 0.08), 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.restore();
    }
}

window.CelestialRenderer = CelestialRenderer;
