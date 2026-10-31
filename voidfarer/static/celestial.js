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
    toxic: { surface: "#7a8f3c", bands: ["#b5e48c", "#d9ed92", "#99d98c"], atmo: "190, 230, 120" },
};
const GIANT_STYLES = {
    ringed_giant: { ring: true },
    ice_giant: { ring: false },
};
const STATION_TYPES = new Set(["orbital_station", "research_outpost", "quantum_relay", "solar_collector"]);

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
        if (type === "asteroid_belt") return; // drawn along its orbit by drawAsteroidBelt
        // Stations are tiny in kilometres; keep their models legible on the map.
        if (STATION_TYPES.has(type)) r = Math.max(r, 7);
        const sprite = this.sprite(body, r, dpr);
        const spin = STATION_TYPES.has(type) ? now * 0.35 : 0;
        ctx.save();
        ctx.translate(x, y);
        if (spin) ctx.rotate(spin);
        ctx.drawImage(sprite.canvas, -sprite.half, -sprite.half, sprite.half * 2, sprite.half * 2);
        ctx.restore();
        if (ROCKY_STYLES[type] || GIANT_STYLES[type]) this.drawTerminator(ctx, x, y, r, lightAngle);
        if (GIANT_STYLES[type] && GIANT_STYLES[type].ring) this.drawRingFront(ctx, body, x, y, r);
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

    limb(ctx, R) {
        const edge = ctx.createRadialGradient(-R * 0.25, -R * 0.25, R * 0.2, 0, 0, R);
        edge.addColorStop(0, "rgba(255, 255, 255, 0.10)");
        edge.addColorStop(0.75, "rgba(0, 0, 0, 0)");
        edge.addColorStop(1, "rgba(0, 0, 0, 0.45)");
        ctx.fillStyle = edge;
        ctx.fillRect(-R, -R, R * 2, R * 2);
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
        if (style.caps) {
            ctx.fillStyle = "rgba(240, 248, 255, 0.85)";
            ctx.beginPath(); ctx.ellipse(0, -R * 0.95, R * 0.7, R * 0.22, 0, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath(); ctx.ellipse(0, R * 0.97, R * 0.55, R * 0.16, 0, 0, Math.PI * 2); ctx.fill();
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
        this.limb(ctx, R);
        ctx.restore();
    }

    paintGiant(ctx, R, style, rng, body) {
        const base = body.color || "#c9ada7";
        if (style.ring) this.paintRingBack(ctx, R, body);
        this.atmosphere(ctx, R, "200, 210, 230");
        ctx.save();
        this.clipDisc(ctx, R);
        ctx.fillStyle = base;
        ctx.fillRect(-R, -R, R * 2, R * 2);
        for (let y = -R; y < R;) {
            const h = R * (0.08 + rng() * 0.18);
            ctx.fillStyle = shade(base, (rng() - 0.5) * 0.5);
            ctx.globalAlpha = 0.75;
            ctx.fillRect(-R, y, R * 2, h);
            y += h;
        }
        ctx.globalAlpha = 1;
        if (rng() > 0.35) {
            ctx.fillStyle = shade(base, -0.35);
            ctx.beginPath();
            ctx.ellipse((rng() - 0.5) * R, (rng() - 0.2) * R * 0.8, R * 0.22, R * 0.11, 0, 0, Math.PI * 2);
            ctx.fill();
        }
        this.limb(ctx, R);
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
            ctx.strokeStyle = color;
            ctx.lineWidth = Math.max(1, R * 0.18);
            ctx.beginPath(); ctx.arc(0, 0, R * 0.85, 0, Math.PI * 2); ctx.stroke();
            ctx.lineWidth = Math.max(1, R * 0.1);
            for (let i = 0; i < 4; i++) {
                const a = i * Math.PI / 2;
                ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(a) * R * 0.85, Math.sin(a) * R * 0.85); ctx.stroke();
            }
            ctx.fillStyle = "#e9f7ff";
            ctx.beginPath(); ctx.arc(0, 0, R * 0.25, 0, Math.PI * 2); ctx.fill();
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

    drawStar(ctx, body, x, y, r, now) {
        const color = body.color || "#ffd700";
        const pulse = 1 + Math.sin(now * 1.6) * 0.04;
        const corona = ctx.createRadialGradient(x, y, r * 0.4, x, y, r * 3.2 * pulse);
        corona.addColorStop(0, "rgba(255, 255, 255, 0.9)");
        corona.addColorStop(0.2, color);
        corona.addColorStop(0.45, shade(color, -0.2).replace("rgb", "rgba").replace(")", ", 0.35)"));
        corona.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = corona;
        ctx.beginPath(); ctx.arc(x, y, r * 3.2 * pulse, 0, Math.PI * 2); ctx.fill();
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

    drawBlackHole(ctx, x, y, r, now) {
        ctx.save();
        ctx.translate(x, y);
        const disk = ctx.createRadialGradient(0, 0, r * 0.8, 0, 0, r * 2.6);
        disk.addColorStop(0, "rgba(255, 220, 160, 0.95)");
        disk.addColorStop(0.35, "rgba(255, 140, 60, 0.6)");
        disk.addColorStop(1, "rgba(120, 40, 160, 0)");
        ctx.rotate(-0.35);
        ctx.scale(1, 0.38);
        ctx.fillStyle = disk;
        ctx.beginPath(); ctx.arc(0, 0, r * 2.6, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
        ctx.fillStyle = "#000000";
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = `rgba(255, 230, 190, ${0.55 + Math.sin(now * 2) * 0.15})`;
        ctx.lineWidth = Math.max(1, r * 0.14);
        ctx.beginPath(); ctx.arc(x, y, r * 1.08, 0, Math.PI * 2); ctx.stroke();
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
        ctx.fillStyle = "rgba(170, 160, 150, 0.75)";
        for (let i = 0; i < 160; i++) {
            const a = rng() * Math.PI * 2 + drift;
            const spread = (rng() - 0.5) * 10 * zoom;
            const size = 0.6 + rng() * 1.6 * Math.min(2, zoom);
            ctx.fillRect(cx + Math.cos(a) * (orbitR + spread), cy + Math.sin(a) * (orbitR + spread), size, size);
        }
        ctx.restore();
    }

    drawMoons(ctx, body, x, y, r, now) {
        const moons = body.moons || [];
        moons.slice(0, 4).forEach((moon, i) => {
            const dist = r * (1.9 + i * 0.6);
            const a = now * (0.6 / (i + 1)) + i * 2.1;
            ctx.fillStyle = "rgba(200, 205, 215, 0.85)";
            ctx.beginPath();
            ctx.arc(x + Math.cos(a) * dist, y + Math.sin(a) * dist * 0.6, Math.max(1, r * 0.18), 0, Math.PI * 2);
            ctx.fill();
        });
    }

    // Flagship silhouette, nose along `angle`.
    drawShip(ctx, x, y, angle, size, color = "#8fbf9f") {
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(angle);
        const s = size;
        const glow = ctx.createRadialGradient(-s * 0.9, 0, 0, -s * 0.9, 0, s * 0.7);
        glow.addColorStop(0, "rgba(140, 220, 255, 0.9)");
        glow.addColorStop(1, "rgba(140, 220, 255, 0)");
        ctx.fillStyle = glow;
        ctx.beginPath(); ctx.arc(-s * 0.9, 0, s * 0.7, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#d9e2ec";
        ctx.strokeStyle = color;
        ctx.lineWidth = Math.max(1, s * 0.08);
        ctx.beginPath();
        ctx.moveTo(s, 0);
        ctx.lineTo(-s * 0.35, -s * 0.28);
        ctx.lineTo(-s * 0.7, -s * 0.62);
        ctx.lineTo(-s * 0.8, -s * 0.2);
        ctx.lineTo(-s * 0.8, s * 0.2);
        ctx.lineTo(-s * 0.7, s * 0.62);
        ctx.lineTo(-s * 0.35, s * 0.28);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = color;
        ctx.beginPath(); ctx.arc(s * 0.25, 0, s * 0.13, 0, Math.PI * 2); ctx.fill();
        ctx.restore();
    }
}

window.CelestialRenderer = CelestialRenderer;
