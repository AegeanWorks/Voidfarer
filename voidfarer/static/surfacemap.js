/**
 * VOIDFARER // Surface tile map
 * Seeded, visual-only terrain for a landed world. Operations become numbered sites on
 * the map; clicking a site selects its row in the existing surface list.
 */

const SURFACE_BIOMES = {
    terrestrial: { name: "TERRESTRIAL", water: "#1d4e89", coast: "#c2b280", base: "#3f7d4e", grass: "#6a994e", rock: "#6b705c", high: "#9aa38a", sand: "#d4a373", ice: "#e8f4ff", waterLevel: 0.42, atmo: "120, 180, 255" },
    oceanic: { name: "OCEANIC", water: "#0f5e8c", coast: "#e6c79c", base: "#2f7d5a", grass: "#7fb069", rock: "#6b705c", high: "#a7c957", sand: "#e6c79c", ice: "#e8f4ff", waterLevel: 0.60, atmo: "110, 200, 255" },
    savanna: { name: "SAVANNA", water: "#2a6f97", coast: "#e6c79c", base: "#b08968", grass: "#90be6d", rock: "#8d6e63", high: "#c9a227", sand: "#d4a373", ice: "#e8f4ff", waterLevel: 0.34, atmo: "150, 200, 255" },
    tundra: { name: "TUNDRA", water: "#3d5a80", coast: "#e0e1dd", base: "#bde0fe", grass: "#cfe8ef", rock: "#98c1d9", high: "#f1f7ff", sand: "#d8e6ee", ice: "#ffffff", waterLevel: 0.46, atmo: "190, 220, 255" },
    super_earth: { name: "SUPER-EARTH", water: "#264653", coast: "#bc6c25", base: "#386641", grass: "#6a994e", rock: "#5c7f4a", high: "#a7c957", sand: "#d4a373", ice: "#e8f4ff", waterLevel: 0.38, atmo: "140, 200, 160" },
    desert_world: { name: "DESERT", water: "#c58b4a", coast: "#f4e1b6", base: "#e9c46a", grass: "#d4a373", rock: "#b08968", high: "#c58b4a", sand: "#e9c46a", ice: "#f4e1b6", waterLevel: 0.0, atmo: "233, 196, 106" },
    barren: { name: "BARREN", water: "#6c757d", coast: "#adb5bd", base: "#8d99ae", grass: "#adb5bd", rock: "#5c677d", high: "#ced4da", sand: "#adb5bd", ice: "#e8f4ff", waterLevel: 0.0, atmo: "180, 190, 205" },
    ice_world: { name: "ICE WORLD", water: "#7fb7c9", coast: "#e8f6f8", base: "#cfe8ef", grass: "#dff5f8", rock: "#98c1d9", high: "#ffffff", sand: "#d8eef4", ice: "#ffffff", waterLevel: 0.0, atmo: "200, 235, 255" },
    lava_world: { name: "LAVA WORLD", water: "#ff7b2e", coast: "#5a1a10", base: "#2b0f0a", grass: "#3a1510", rock: "#1a0a08", high: "#ffb703", sand: "#3a1510", ice: "#5a1a10", waterLevel: 0.0, atmo: "255, 110, 60" },
    volcanic: { name: "VOLCANIC", water: "#ff5a2e", coast: "#5a1a10", base: "#33130d", grass: "#452016", rock: "#1a0a08", high: "#ffb703", sand: "#452016", ice: "#5a1a10", waterLevel: 0.0, atmo: "255, 100, 60" },
    toxic: { name: "TOXIC", water: "#99d98c", coast: "#b5e48c", base: "#7a8f3c", grass: "#99d98c", rock: "#52631f", high: "#d9ed92", sand: "#a7b86a", ice: "#d9ed92", waterLevel: 0.30, atmo: "190, 230, 120" },
    gas_giant: { name: "GAS GIANT", cloud: ["#f4a261", "#e76f51", "#ffd7a8"], base: "#f4a261", gas: true, atmo: "244, 162, 97" },
    ringed_giant: { name: "RINGED GIANT", cloud: ["#c9ada7", "#e6d5c3", "#a98f88"], base: "#c9ada7", gas: true, atmo: "230, 214, 190" },
    ice_giant: { name: "ICE GIANT", cloud: ["#a2d2ff", "#c8e7ff", "#7fb7d9"], base: "#a2d2ff", gas: true, atmo: "162, 210, 255" },
    methane_storm: { name: "METHANE STORM", cloud: ["#70c1b3", "#b2f7ef", "#4f9d92"], base: "#70c1b3", gas: true, atmo: "162, 230, 220" },
    ring_world: { name: "RING HABITAT", water: "#2a1c3d", coast: "#6d5a8a", base: "#3d3450", grass: "#6d5a8a", rock: "#4a3f5e", high: "#c77dff", sand: "#4a3f5e", ice: "#c77dff", habitat: true, waterLevel: 0.0, atmo: "199, 125, 255" },
};
const SURFACE_GRID_W = 30;
const SURFACE_GRID_H = 12;
const SURFACE_SITE_HINTS = {
    surface_survey: ["base", "grass", "sand", "ice", "rock", "ash", "cloud", "habitat"],
    core_sample: ["rock", "high"],
    ruin_excavation: ["base", "sand", "rock", "ash"],
    wreck_salvage: ["base", "sand", "regolith", "ice"],
    field_rest: ["base", "grass", "sand", "habitat"],
    geothermal_tap: ["rock", "high", "vent"],
    bio_prospecting: ["grass", "swamp", "reef", "base"],
    crash_site_recovery: ["base", "regolith", "sand", "ice"],
    cryo_drill: ["ice", "rock"],
    magma_tap: ["vent", "lava", "rock"],
    reef_harvest: ["reef", "coast", "water"],
    cloud_scoop: ["cloud"],
    deep_mine: ["rock", "high", "regolith"],
};

function surfaceHash(text) {
    let h = 2166136261;
    for (let i = 0; i < text.length; i++) {
        h ^= text.charCodeAt(i);
        h = Math.imul(h, 16777619);
    }
    return h >>> 0;
}

function surfaceHash2(x, y, seed) {
    let n = Math.imul(x + 1, 374761393) ^ Math.imul(y + 1, 668265263) ^ seed;
    n = Math.imul(n ^ (n >>> 13), 1274126177);
    return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
}

class SurfaceMapRenderer {
    constructor() {
        this.cache = new Map();
        this.current = null;
    }

    biomeFor(body) {
        const type = String((body && body.body_type) || "");
        return SURFACE_BIOMES[type] || SURFACE_BIOMES.terrestrial;
    }

    generate(body, operations) {
        const list = Array.isArray(operations) ? operations : [];
        const key = `${body.id || "surface"}|${body.body_type || ""}|${list.map(op => `${op.id}:${op.used ? 1 : 0}`).join(",")}`;
        if (this.cache.has(key)) return this.cache.get(key);
        const palette = this.biomeFor(body);
        const seed = surfaceHash(String(body.id || "surface"));
        const smooth = (x, y, scale) => {
            const sx = x / scale;
            const sy = y / scale;
            const xi = Math.floor(sx);
            const yi = Math.floor(sy);
            const xf = sx - xi;
            const yf = sy - yi;
            const u = xf * xf * (3 - 2 * xf);
            const v = yf * yf * (3 - 2 * yf);
            const a = surfaceHash2(xi, yi, seed);
            const b = surfaceHash2(xi + 1, yi, seed);
            const c = surfaceHash2(xi, yi + 1, seed);
            const d = surfaceHash2(xi + 1, yi + 1, seed);
            return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v;
        };
        const tiles = [];
        for (let y = 0; y < SURFACE_GRID_H; y++) {
            for (let x = 0; x < SURFACE_GRID_W; x++) {
                const f = surfaceHash2(x, y, seed + 7);
                if (palette.gas) {
                    const band = Math.abs(Math.sin(y * 0.55 + smooth(x, y, 5) * 1.4));
                    const color = palette.cloud[Math.min(2, Math.floor(band * 2.99))];
                    tiles.push({ x, y, kind: "cloud", fill: color, feature: f > 0.82 ? "storm" : "band", f });
                    continue;
                }
                const elevation = 0.55 * smooth(x, y, 7) + 0.30 * smooth(x + 11, y + 5, 3.5) + 0.15 * smooth(x * 1.7, y * 1.3, 2.2);
                let kind = "base";
                if (elevation < palette.waterLevel) kind = "water";
                else if (elevation < palette.waterLevel + 0.055) kind = "coast";
                else if (elevation > 0.78) kind = "high";
                else if (elevation > 0.62) kind = "rock";
                else if (palette.habitat) kind = "habitat";
                else if (palette.name === "DESERT" || palette.name === "BARREN") kind = "sand";
                else if (palette.name === "ICE WORLD") kind = "ice";
                else if (palette.name === "LAVA WORLD" || palette.name === "VOLCANIC") kind = "lava";
                else if (palette.name === "TOXIC") kind = "swamp";
                else if (palette.grass && smooth(x + 30, y, 4) > 0.55) kind = "grass";
                if (kind === "high" && (palette.name === "LAVA WORLD" || palette.name === "VOLCANIC")) kind = "vent";
                if (kind === "high" && palette.name === "BARREN") kind = "regolith";
                if (kind === "sand" && palette.name === "BARREN") kind = "regolith";
                const fill = palette[kind] || palette.base || "#55606a";
                let feature = null;
                if (kind === "sand" && f > 0.42) feature = "dune";
                else if ((kind === "rock" || kind === "high") && f > 0.48) feature = "ridge";
                else if (kind === "regolith" && f > 0.30) feature = "crater";
                else if (kind === "ice" && f > 0.38) feature = "crack";
                else if ((kind === "lava" || kind === "vent") && f > 0.22) feature = "vent";
                else if (kind === "grass" && f > 0.48) feature = "tuft";
                else if (kind === "water" && f > 0.82) feature = "wave";
                else if (kind === "coast" && f > 0.66) feature = "reef";
                else if (kind === "habitat") feature = "grid";
                tiles.push({ x, y, kind, fill, feature, f });
            }
        }
        list.forEach((op, index) => {
            const wants = SURFACE_SITE_HINTS[op.id] || ["base", "grass", "sand", "rock", "ice", "regolith", "habitat", "cloud"];
            let candidates = tiles.filter(tile => !tile.site && wants.includes(tile.kind));
            if (!candidates.length) candidates = tiles.filter(tile => !tile.site && tile.kind !== "water");
            if (!candidates.length) candidates = tiles.filter(tile => !tile.site);
            if (!candidates.length) return;
            const tile = candidates[Math.floor(surfaceHash2(index, seed, 13) * candidates.length)];
            tile.site = {
                id: op.id,
                name: op.name || op.id,
                index: index + 1,
                risk: Number(op.risk || 0),
                used: Boolean(op.used),
                x: tile.x,
                y: tile.y,
            };
        });
        const map = { w: SURFACE_GRID_W, h: SURFACE_GRID_H, tiles, palette, key };
        if (this.cache.size > 6) this.cache.delete(this.cache.keys().next().value);
        this.cache.set(key, map);
        return map;
    }

    draw(canvas, body, operations, selectedOpId = null) {
        if (!canvas) return;
        const map = this.generate(body, operations);
        const dpr = Math.min(2, window.devicePixelRatio || 1);
        const cssW = Math.max(300, Math.round(canvas.clientWidth || 600));
        const cssH = Math.round(cssW * 0.4);
        if (canvas.width !== Math.round(cssW * dpr) || canvas.height !== Math.round(cssH * dpr)) {
            canvas.width = Math.round(cssW * dpr);
            canvas.height = Math.round(cssH * dpr);
        }
        const ctx = canvas.getContext("2d");
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, cssW, cssH);
        ctx.fillStyle = "#04070d";
        ctx.fillRect(0, 0, cssW, cssH);
        const tw = cssW / map.w;
        const th = cssH / map.h;
        const seed = surfaceHash(String(body.id || "surface"));
        for (const tile of map.tiles) {
            const x = tile.x * tw;
            const y = tile.y * th;
            ctx.fillStyle = tile.fill;
            ctx.fillRect(x, y, tw + 1, th + 1);
            // Elevation relief: raised kinds catch a top highlight, low/water
            // kinds settle with a deeper base shade. Flat cost, no extra passes.
            if (tile.kind === "high" || tile.kind === "rock" || tile.kind === "regolith") {
                ctx.fillStyle = "rgba(255, 255, 255, 0.09)";
                ctx.fillRect(x, y, tw + 1, 1);
                ctx.fillStyle = "rgba(0, 0, 0, 0.20)";
                ctx.fillRect(x, y + th - 1, tw + 1, 1);
            } else if (tile.kind === "water" || tile.kind === "vent" || tile.kind === "lava") {
                ctx.fillStyle = "rgba(0, 0, 0, 0.22)";
                ctx.fillRect(x, y, tw + 1, th + 1);
                ctx.fillStyle = "rgba(255, 255, 255, 0.04)";
                ctx.fillRect(x, y, tw + 1, 1);
            } else {
                ctx.fillStyle = "rgba(255, 255, 255, 0.055)";
                ctx.fillRect(x, y, tw + 1, 1);
                ctx.fillStyle = "rgba(0, 0, 0, 0.16)";
                ctx.fillRect(x, y + th - 1, tw + 1, 1);
            }
            this.drawFeature(ctx, tile, x, y, tw, th, seed);
        }
        ctx.strokeStyle = "rgba(4, 9, 19, 0.20)";
        ctx.lineWidth = 0.5;
        for (let x = 0; x <= map.w; x++) {
            ctx.beginPath(); ctx.moveTo(x * tw, 0); ctx.lineTo(x * tw, cssH); ctx.stroke();
        }
        for (let y = 0; y <= map.h; y++) {
            ctx.beginPath(); ctx.moveTo(0, y * th); ctx.lineTo(cssW, y * th); ctx.stroke();
        }
        ctx.globalAlpha = 0.10;
        ctx.fillStyle = "#02040a";
        for (let y = 0; y < cssH; y += 3) ctx.fillRect(0, y, cssW, 1);
        ctx.globalAlpha = 1;
        const vignette = ctx.createRadialGradient(cssW / 2, cssH / 2, cssH * 0.18, cssW / 2, cssH / 2, cssW * 0.62);
        vignette.addColorStop(0, "rgba(0, 0, 0, 0)");
        vignette.addColorStop(1, "rgba(2, 5, 12, 0.50)");
        ctx.fillStyle = vignette;
        ctx.fillRect(0, 0, cssW, cssH);
        // Topographic sweep sensor line
        const scanY = ((performance.now() * 0.04) % (cssH + 20)) - 10;
        if (scanY >= 0 && scanY <= cssH) {
            ctx.fillStyle = "rgba(127, 183, 201, 0.22)";
            ctx.fillRect(0, scanY, cssW, 1.5);
            ctx.fillStyle = "rgba(127, 183, 201, 0.06)";
            ctx.fillRect(0, Math.max(0, scanY - 8), cssW, 8);
        }
        this.current = { map, cssW, cssH };
        const sites = map.tiles.filter(tile => tile.site);
        for (const tile of sites) {
            const site = tile.site;
            const x = (site.x + 0.5) * tw;
            const y = (site.y + 0.5) * th;
            const selected = site.id === selectedOpId;
            const color = site.used ? "#6b7280" : site.risk >= 35 ? "#c96b5a" : site.risk >= 18 ? "#c9a35a" : "#8fbf9f";
            ctx.save();
            ctx.translate(x, y);
            // Risk glow: unused elevated-risk sites breathe in their risk
            // color so danger reads before the player commits a party.
            // Phase is seeded per site so markers stay out of sync.
            if (!site.used && site.risk >= 18) {
                const pulse = 0.5 + 0.5 * Math.sin(performance.now() * 0.004 + site.index * 1.3);
                ctx.save();
                ctx.globalAlpha = 0.22 + pulse * 0.34;
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.arc(0, 0, 7 + pulse * 2.5, 0, Math.PI * 2);
                ctx.stroke();
                ctx.restore();
            }
            if (selected) {
                ctx.strokeStyle = "#8fd8ff";
                ctx.lineWidth = 1.4;
                ctx.beginPath();
                ctx.arc(0, 0, 9 + Math.sin(performance.now() * 0.006) * 1.5, 0, Math.PI * 2);
                ctx.stroke();
                const bSize = 12;
                ctx.strokeStyle = "rgba(255, 255, 255, 0.9)";
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.moveTo(-bSize, -bSize + 4); ctx.lineTo(-bSize, -bSize); ctx.lineTo(-bSize + 4, -bSize);
                ctx.moveTo(bSize - 4, -bSize); ctx.lineTo(bSize, -bSize); ctx.lineTo(bSize, -bSize + 4);
                ctx.moveTo(-bSize, bSize - 4); ctx.lineTo(-bSize, bSize); ctx.lineTo(-bSize + 4, bSize);
                ctx.moveTo(bSize - 4, bSize); ctx.lineTo(bSize, bSize); ctx.lineTo(bSize, bSize - 4);
                ctx.stroke();
            }
            ctx.rotate(Math.PI / 4);
            ctx.fillStyle = color;
            ctx.fillRect(-4, -4, 8, 8);
            ctx.strokeStyle = "#06101d";
            ctx.lineWidth = 1.2;
            ctx.strokeRect(-4, -4, 8, 8);
            ctx.restore();
            ctx.fillStyle = "#06101d";
            ctx.font = "9px 'Cascadia Mono', Consolas, monospace";
            ctx.textAlign = "center";
            ctx.fillText(site.used ? "X" : String(site.index), x, y + 2.6);
        }
        const selectedTile = map.tiles.find(tile => tile.site && tile.site.id === selectedOpId);
        if (selectedTile) {
            const site = selectedTile.site;
            const x = (site.x + 0.5) * tw;
            const y = (site.y + 0.5) * th;
            const lat = (90 - site.y * (180 / map.h)).toFixed(0);
            const lon = (site.x * (360 / map.w) - 180).toFixed(0);
            const line1 = site.name;
            const line2 = `POS [${lat >= 0 ? "+" : ""}${lat}°, ${lon >= 0 ? "+" : ""}${lon}°] · RISK ${site.risk}%`;
            ctx.font = "10px 'Segoe UI'";
            const w1 = ctx.measureText(line1).width;
            ctx.font = "9px 'Cascadia Mono', Consolas, monospace";
            const w2 = ctx.measureText(line2).width;
            const width = Math.max(w1, w2) + 12;
            const lx = Math.max(2, Math.min(cssW - width - 2, x - width / 2));
            const ly = Math.max(2, y - 30);
            ctx.fillStyle = "rgba(4, 9, 19, 0.92)";
            ctx.fillRect(lx, ly, width, 26);
            ctx.strokeStyle = "#7fb7c9";
            ctx.lineWidth = 1;
            ctx.strokeRect(lx, ly, width, 26);
            ctx.font = "10px 'Segoe UI'";
            ctx.fillStyle = "#ece4d4";
            ctx.textAlign = "left";
            ctx.fillText(line1, lx + 6, ly + 11);
            ctx.font = "9px 'Cascadia Mono', Consolas, monospace";
            ctx.fillStyle = site.risk >= 35 ? "#c96b5a" : site.risk >= 18 ? "#c9a35a" : "#8fbf9f";
            ctx.fillText(line2, lx + 6, ly + 22);
        }
        ctx.font = "10px 'Cascadia Mono', Consolas, monospace";
        ctx.textAlign = "right";
        ctx.fillStyle = "rgba(201, 163, 90, 0.82)";
        ctx.fillText("N", cssW - 8, 14);
        ctx.beginPath();
        ctx.moveTo(cssW - 11, 18);
        ctx.lineTo(cssW - 8, 26);
        ctx.lineTo(cssW - 5, 18);
        ctx.strokeStyle = "rgba(201, 163, 90, 0.82)";
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    drawFeature(ctx, tile, x, y, tw, th, seed) {
        const cx = x + tw / 2;
        const cy = y + th / 2;
        const r = surfaceHash2(tile.x, tile.y, seed + 5);
        ctx.save();
        if (tile.feature === "crater") {
            const radius = Math.min(tw, th) * (0.14 + r * 0.12);
            ctx.fillStyle = "rgba(0, 0, 0, 0.28)";
            ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
            ctx.lineWidth = 0.8;
            ctx.beginPath(); ctx.arc(cx - 0.8, cy - 0.8, radius, Math.PI * 0.8, Math.PI * 1.7); ctx.stroke();
        } else if (tile.feature === "ridge") {
            ctx.strokeStyle = "rgba(0, 0, 0, 0.28)";
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(x + tw * 0.15, cy + th * 0.18);
            ctx.lineTo(cx, cy - th * 0.18);
            ctx.lineTo(x + tw * 0.85, cy + th * 0.10);
            ctx.stroke();
        } else if (tile.feature === "dune") {
            ctx.strokeStyle = "rgba(120, 72, 30, 0.35)";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x + 1, cy);
            ctx.quadraticCurveTo(cx, cy - th * 0.22, x + tw - 1, cy);
            ctx.stroke();
        } else if (tile.feature === "crack") {
            ctx.strokeStyle = "rgba(127, 183, 201, 0.45)";
            ctx.lineWidth = 0.9;
            ctx.beginPath();
            ctx.moveTo(cx - tw * 0.3, cy - th * 0.1);
            ctx.lineTo(cx - tw * 0.05, cy + th * 0.15);
            ctx.lineTo(cx + tw * 0.18, cy - th * 0.02);
            ctx.stroke();
        } else if (tile.feature === "vent") {
            ctx.fillStyle = "rgba(255, 120, 40, 0.85)";
            ctx.beginPath(); ctx.arc(cx, cy, 1.4, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = "rgba(255, 100, 40, 0.45)";
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(cx - tw * 0.18, cy + th * 0.16);
            ctx.lineTo(cx, cy);
            ctx.lineTo(cx + tw * 0.18, cy + th * 0.16);
            ctx.stroke();
        } else if (tile.feature === "tuft") {
            ctx.fillStyle = "rgba(30, 70, 40, 0.35)";
            ctx.fillRect(cx - 1, cy - 1, 2, 2);
        } else if (tile.feature === "wave") {
            ctx.strokeStyle = "rgba(220, 240, 255, 0.28)";
            ctx.lineWidth = 0.7;
            ctx.beginPath();
            ctx.moveTo(x + tw * 0.18, cy);
            ctx.quadraticCurveTo(cx, cy - 1.2, x + tw * 0.82, cy);
            ctx.stroke();
        } else if (tile.feature === "reef") {
            ctx.fillStyle = "rgba(230, 199, 156, 0.55)";
            ctx.beginPath(); ctx.arc(cx, cy, 1.2, 0, Math.PI * 2); ctx.fill();
        } else if (tile.feature === "storm") {
            ctx.fillStyle = "rgba(30, 20, 20, 0.28)";
            ctx.beginPath();
            ctx.ellipse(cx, cy, tw * 0.30, th * 0.16, 0.3, 0, Math.PI * 2);
            ctx.fill();
        } else if (tile.feature === "band") {
            ctx.strokeStyle = "rgba(255, 255, 255, 0.18)";
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(x, cy);
            ctx.lineTo(x + tw, cy + Math.sin(tile.x * 0.7) * 1.5);
            ctx.stroke();
        } else if (tile.feature === "grid") {
            ctx.strokeStyle = "rgba(199, 125, 255, 0.25)";
            ctx.lineWidth = 0.6;
            ctx.strokeRect(x + tw * 0.2, y + th * 0.2, tw * 0.6, th * 0.6);
        }
        ctx.restore();
    }

    hitTest(canvas, event) {
        if (!this.current || !canvas) return null;
        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) return null;
        const px = Math.max(0, Math.min(0.999, (event.clientX - rect.left) / rect.width));
        const py = Math.max(0, Math.min(0.999, (event.clientY - rect.top) / rect.height));
        const tx = Math.floor(px * this.current.map.w);
        const ty = Math.floor(py * this.current.map.h);
        const tile = this.current.map.tiles[ty * this.current.map.w + tx];
        return tile && tile.site ? tile.site : null;
    }
}

window.SurfaceMapRenderer = SurfaceMapRenderer;
