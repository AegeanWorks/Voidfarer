/**
 * VOIDFARER // Particle and motion FX
 * Visual-only, pooled canvas particles: engine exhaust, transit warp streaks, scan rings,
 * counter-battery sparks and combat bursts. Nothing here touches simulation state.
 */

class ParticleSystem {
    constructor(max = 640) {
        this.max = max;
        this.items = [];
        this.last = performance.now();
        // A tiny xorshift keeps repeated captures close without seeding gameplay.
        let seed = 0x9e3779b9;
        this.rng = () => {
            seed ^= seed << 13; seed ^= seed >>> 17; seed ^= seed << 5;
            return (seed >>> 0) / 4294967296;
        };
    }

    random(min, max) {
        return min + this.rng() * (max - min);
    }

    spawn(options) {
        if (this.items.length >= this.max) this.items.shift();
        const life = Math.max(0.05, options.life || 0.8);
        this.items.push({
            x: options.x || 0,
            y: options.y || 0,
            vx: options.vx || 0,
            vy: options.vy || 0,
            life,
            maxLife: life,
            size: options.size || 2,
            color: options.color || "#7fb7c9",
            kind: options.kind || "dot",
            opacity: options.opacity ?? 1,
            drag: options.drag ?? 0.92,
            gravity: options.gravity || 0,
            length: options.length || 0,
            radius: options.radius || 0,
            grow: options.grow || 0,
        });
    }

    update(now = performance.now()) {
        const dt = Math.min(0.05, Math.max(0, (now - this.last) / 1000));
        this.last = now;
        const alive = [];
        for (const particle of this.items) {
            particle.life -= dt;
            if (particle.life <= 0) continue;
            const damp = Math.pow(particle.drag, dt * 60);
            particle.vx *= damp;
            particle.vy *= damp;
            particle.vy += particle.gravity * dt;
            particle.x += particle.vx * dt;
            particle.y += particle.vy * dt;
            if (particle.kind === "ring") particle.radius += particle.grow * dt;
            alive.push(particle);
        }
        this.items = alive;
    }

    draw(ctx) {
        if (!this.items.length) return;
        ctx.save();
        for (const particle of this.items) {
            const alpha = Math.max(0, Math.min(1, particle.life / particle.maxLife)) * particle.opacity;
            if (particle.kind === "ring") {
                ctx.globalCompositeOperation = "lighter";
                ctx.globalAlpha = alpha * 0.8;
                ctx.strokeStyle = particle.color;
                ctx.lineWidth = Math.max(0.6, particle.size * alpha);
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, Math.max(1, particle.radius), 0, Math.PI * 2);
                ctx.stroke();
            } else if (particle.kind === "smoke") {
                ctx.globalCompositeOperation = "source-over";
                ctx.globalAlpha = alpha * 0.28;
                ctx.fillStyle = particle.color;
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, particle.size * (1.6 - alpha * 0.6), 0, Math.PI * 2);
                ctx.fill();
            } else if (particle.kind === "spark") {
                ctx.globalCompositeOperation = "lighter";
                ctx.globalAlpha = alpha;
                ctx.strokeStyle = particle.color;
                ctx.lineWidth = Math.max(0.7, particle.size);
                const length = particle.length || particle.size * 5;
                const speed = Math.hypot(particle.vx, particle.vy) || 1;
                ctx.beginPath();
                ctx.moveTo(particle.x, particle.y);
                ctx.lineTo(
                    particle.x - (particle.vx / speed) * length,
                    particle.y - (particle.vy / speed) * length,
                );
                ctx.stroke();
            } else if (particle.kind === "hex") {
                ctx.globalCompositeOperation = "lighter";
                ctx.globalAlpha = alpha * 0.85;
                ctx.strokeStyle = particle.color;
                ctx.lineWidth = Math.max(0.8, particle.size);
                ctx.beginPath();
                const hR = particle.radius;
                for (let k = 0; k < 6; k++) {
                    const hA = (k * Math.PI) / 3;
                    const hX = particle.x + Math.cos(hA) * hR;
                    const hY = particle.y + Math.sin(hA) * hR;
                    if (k === 0) ctx.moveTo(hX, hY);
                    else ctx.lineTo(hX, hY);
                }
                ctx.closePath();
                ctx.stroke();
                ctx.fillStyle = particle.color;
                ctx.globalAlpha = alpha * 0.18;
                ctx.fill();
            } else {
                ctx.globalCompositeOperation = "lighter";
                ctx.globalAlpha = alpha * 0.9;
                ctx.fillStyle = particle.color;
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, Math.max(0.5, particle.size * alpha), 0, Math.PI * 2);
                ctx.fill();
            }
        }
        ctx.restore();
    }

    trail(x, y, heading, color = "#8fd8ff", power = 1) {
        const angle = heading + Math.PI + this.random(-0.34, 0.34);
        const speed = this.random(24, 68) * power;
        const vx = Math.cos(angle) * speed;
        const vy = Math.sin(angle) * speed;
        this.spawn({
            x, y, vx, vy,
            life: this.random(0.4, 0.85),
            size: this.random(1.1, 2.2) * power,
            color,
            kind: "dot",
            drag: 0.9,
        });
        // A wide, faint puff behind the bright core gives the plume a soft edge.
        if (power > 0.6 && this.rng() > 0.42) {
            this.spawn({
                x, y, vx: vx * 0.6, vy: vy * 0.6,
                life: this.random(0.25, 0.5),
                size: this.random(2.2, 3.6) * power,
                color,
                kind: "dot",
                drag: 0.9,
                opacity: 0.26,
            });
        }
    }

    thrustPlume(x, y, heading, power = 1) {
        const angle = heading + Math.PI + this.random(-0.16, 0.16);
        const speed = this.random(75, 180) * Math.max(0.4, power);
        const vx = Math.cos(angle) * speed;
        const vy = Math.sin(angle) * speed;
        let coreColor = "#8fd8ff";
        if (power >= 1.4) coreColor = "#c77dff";
        else if (power >= 0.8) coreColor = "#70c1b3";

        this.spawn({
            x, y, vx, vy,
            life: this.random(0.18, 0.42),
            size: this.random(1.4, 2.8) * Math.min(1.5, power),
            color: coreColor,
            kind: "spark",
            drag: 0.91,
            length: this.random(8, 22) * power,
        });

        if (this.rng() > 0.4) {
            this.spawn({
                x, y, vx: vx * 0.45, vy: vy * 0.45,
                life: this.random(0.3, 0.6),
                size: this.random(2.0, 4.5) * power,
                color: "rgba(111, 195, 215, 0.4)",
                kind: "dot",
                drag: 0.88,
                opacity: 0.35,
            });
        }
    }

    warp(x, y, heading, color = "#7fb7c9") {
        const angle = heading + this.random(-0.10, 0.10);
        const speed = this.random(110, 250);
        this.spawn({
            x, y,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed,
            life: this.random(0.22, 0.5),
            size: this.random(1, 2.1),
            color,
            kind: "spark",
            drag: 0.98,
            length: this.random(10, 28),
        });
    }

    burst(x, y, count = 14, color = "#ffd166", speed = 160) {
        for (let i = 0; i < count; i++) {
            const angle = this.random(0, Math.PI * 2);
            const velocity = this.random(speed * 0.22, speed);
            this.spawn({
                x, y,
                vx: Math.cos(angle) * velocity,
                vy: Math.sin(angle) * velocity,
                life: this.random(0.32, 0.9),
                size: this.random(1, 2.4),
                color,
                kind: this.rng() > 0.28 ? "spark" : "smoke",
                drag: 0.94,
                gravity: 14,
                length: this.random(4, 16),
            });
        }
    }

    ion(x, y, vx, vy, color = "#8fd8ff", life = 0.5, size = 1.2) {
        this.spawn({
            x, y, vx, vy,
            life,
            size,
            color,
            kind: "dot",
            drag: 0.95,
        });
    }

    ring(x, y, color = "#7fb7c9", maxRadius = 90, life = 0.7) {
        this.spawn({
            x, y,
            life,
            color,
            kind: "ring",
            radius: 4,
            grow: Math.max(1, maxRadius) / Math.max(0.1, life),
            size: 2,
        });
    }

    shieldRipple(x, y, radius = 28, color = "#7fb7c9", life = 0.55) {
        this.spawn({
            x, y,
            life,
            color,
            kind: "ring",
            radius: Math.max(10, radius * 0.7),
            grow: (radius * 1.6) / Math.max(0.1, life),
            size: 2.2,
            opacity: 0.85,
        });
        for (let i = 0; i < 6; i++) {
            const angle = this.random(0, Math.PI * 2);
            const speed = this.random(20, 60);
            this.spawn({
                x: x + Math.cos(angle) * radius,
                y: y + Math.sin(angle) * radius,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: this.random(0.2, 0.45),
                size: 1.4,
                color: "#e2c078",
                kind: "spark",
                drag: 0.92,
                length: 6,
            });
        }
    }

    hexShieldImpact(x, y, radius = 28, color = "#7fb7c9", life = 0.5) {
        this.shieldRipple(x, y, radius, color, life);
        const hexSize = Math.max(6, radius * 0.35);
        this.spawn({
            x, y, life,
            color,
            kind: "hex",
            radius: hexSize,
            size: 1.5,
            opacity: 0.9,
            drag: 0.9,
        });
        const d = hexSize * Math.sqrt(3);
        for (let i = 0; i < 6; i++) {
            const a = (i * Math.PI) / 3 + Math.PI / 6;
            this.spawn({
                x: x + Math.cos(a) * d * 0.85,
                y: y + Math.sin(a) * d * 0.85,
                life: life * this.random(0.65, 0.95),
                color,
                kind: "hex",
                radius: hexSize * 0.9,
                size: 1.1,
                opacity: 0.65,
                drag: 0.9,
            });
        }
    }

    rcsPuff(x, y, angle, color = "rgba(236, 228, 212, 0.85)", speed = 35) {
        for (let i = 0; i < 4; i++) {
            const spread = (this.rng() - 0.5) * 0.45;
            const spd = speed * (0.7 + this.rng() * 0.6);
            this.spawn({
                x, y,
                vx: Math.cos(angle + spread) * spd,
                vy: Math.sin(angle + spread) * spd,
                life: this.random(0.15, 0.35),
                size: 1.1,
                color,
                kind: "smoke",
                drag: 0.85,
                opacity: 0.7,
            });
        }
    }

    flakBurst(x, y, radius = 22, color, sparkColor, smokeColor) {
        const ringCol = color || (String.fromCharCode(35) + "e2c078");
        const sparkCol = sparkColor || (String.fromCharCode(35) + "ffffff");
        const smokeCol = smokeColor || `rgb${"a"}阳180, 190, 205, 0.5)`.replace("阳", "(");
        this.spawn({
            x, y,
            life: 0.35,
            color: ringCol,
            kind: "ring",
            radius: 4,
            grow: radius * 3.5,
            size: 2.0,
            opacity: 0.9,
        });
        for (let i = 0; i < 10; i++) {
            const angle = this.random(0, Math.PI * 2);
            const speed = this.random(40, 95);
            this.spawn({
                x: x + Math.cos(angle) * 3,
                y: y + Math.sin(angle) * 3,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: this.random(0.18, 0.4),
                size: 1.5,
                color: sparkCol,
                kind: "spark",
                drag: 0.88,
                length: 6,
            });
        }
        for (let i = 0; i < 3; i++) {
            const angle = this.random(0, Math.PI * 2);
            const speed = this.random(8, 22);
            this.spawn({
                x, y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: this.random(0.25, 0.5),
                size: 1.4,
                color: smokeCol,
                kind: "smoke",
                drag: 0.82,
                opacity: 0.6,
            });
        }
    }

    ionArc(x1, y1, x2, y2, color) {
        const arcColor = color || (String.fromCharCode(35) + "7fb7c9");
        const dx = x2 - x1;
        const dy = y2 - y1;
        const dist = Math.hypot(dx, dy);
        const steps = Math.max(3, Math.floor(dist / 14));
        let cx = x1;
        let cy = y1;
        for (let i = 1; i <= steps; i++) {
            const t = i / steps;
            const jitter = (this.rng() - 0.5) * 12 * Math.sin(t * Math.PI);
            const nx = x1 + dx * t - (dy / (dist || 1)) * jitter;
            const ny = y1 + dy * t + (dx / (dist || 1)) * jitter;
            this.spawn({
                x: (cx + nx) * 0.5,
                y: (cy + ny) * 0.5,
                life: this.random(0.08, 0.18),
                size: 1.8,
                color: arcColor,
                kind: "spark",
                drag: 0.85,
                length: Math.hypot(nx - cx, ny - cy),
            });
            cx = nx;
            cy = ny;
        }
    }

    quantumFlash(x, y, color, coreColor) {
        const flashCol = color || (String.fromCharCode(35) + "7fb7c9");
        const coreCol = coreColor || (String.fromCharCode(35) + "ffffff");
        this.spawn({
            x, y,
            life: 0.45,
            color: flashCol,
            kind: "ring",
            radius: 6,
            grow: 110,
            size: 2.2,
            opacity: 0.95,
        });
        this.spawn({
            x, y,
            life: 0.28,
            color: coreCol,
            kind: "ring",
            radius: 2,
            grow: 65,
            size: 1.6,
            opacity: 0.9,
        });
        for (let i = 0; i < 14; i++) {
            const angle = (i / 14) * Math.PI * 2 + (this.rng() - 0.5) * 0.25;
            const speed = this.random(75, 190);
            this.spawn({
                x, y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: this.random(0.18, 0.42),
                size: 1.8,
                color: flashCol,
                kind: "spark",
                drag: 0.91,
                length: 16,
            });
        }
    }
}

window.ParticleSystem = ParticleSystem;
