"""Particles, rings, slashes, dust, damage popups, wind streaks.

Pure data + a step function; all drawing lives in `draw.py`.
Everything is seeded, so a given seed produces identical juice.
"""

from math import cos, pi, sin


class Fx:
    def __init__(self, rng):
        self.rng = rng
        self.parts = []      # spark / dust particles
        self.rings = []      # expanding shockwave rings
        self.slashes = []    # radiating hit lines
        self.popups = []     # floating damage numbers
        self.banners = []    # big centred words (KO!, PERFECT...)
        self.wind = 0.0      # 0..1 speed-line intensity
        self.burst = 0.0     # 0..1 radial streak intensity (supers)

    # ---- spawners --------------------------------------------------------
    def impact(self, x, y, strength=1.0, color=(255, 255, 255), dirn=1):
        n = int(9 + 20 * strength)
        for _ in range(n):
            a = self.rng.f(0.0, 2.0 * pi)
            sp = self.rng.f(0.7, 3.6) * (0.55 + strength)
            self.parts.append(dict(
                x=x, y=y, vx=cos(a) * sp, vy=sin(a) * sp,
                life=0.0, max=self.rng.f(0.16, 0.44),
                r=self.rng.f(0.009, 0.026) * (0.7 + strength),
                color=color, drag=2.8, grav=-4.2, kind="spark"))
        self.rings.append(dict(x=x, y=y, t=0.0, max=0.24,
                               r0=0.02, r1=0.13 + 0.24 * strength,
                               color=color, w=0.012 + 0.014 * strength))
        for _ in range(int(3 + 6 * strength)):
            base = 0.0 if dirn > 0 else pi
            a = self.rng.f(-0.85, 0.85) + base
            self.slashes.append(dict(
                x=x, y=y, a=a, sp=self.rng.f(2.0, 4.8) * (0.6 + strength),
                t=0.0, max=self.rng.f(0.09, 0.20),
                w=0.018 + 0.022 * strength, color=color))

    def block_spark(self, x, y, strength=1.0, color=(180, 220, 255)):
        for _ in range(int(6 + 10 * strength)):
            a = self.rng.f(-1.4, 1.4) + pi * 0.5
            sp = self.rng.f(1.4, 3.6)
            self.parts.append(dict(
                x=x, y=y, vx=cos(a) * sp, vy=sin(a) * sp,
                life=0.0, max=self.rng.f(0.10, 0.26),
                r=self.rng.f(0.006, 0.016), color=color,
                drag=3.4, grav=-2.0, kind="spark"))

    def dust(self, x, y=0.0, n=10, spread=0.22, dirn=0, power=1.0):
        for _ in range(n):
            a = self.rng.f(0.0, pi)
            sp = self.rng.f(0.3, 1.5) * power
            self.parts.append(dict(
                x=x + self.rng.f(-spread, spread), y=y,
                vx=cos(a) * sp * (0.4 + 0.6 * abs(dirn)) + dirn * 0.5,
                vy=sin(a) * sp * 0.7,
                life=0.0, max=self.rng.f(0.30, 0.85),
                r=self.rng.f(0.014, 0.040),
                color=(150, 150, 158), drag=2.2, grav=-0.5, kind="dust"))

    def popup(self, x, y, text, color=(255, 255, 255), size=0.055, rise=0.55):
        self.popups.append(dict(x=x, y=y, text=str(text), color=color,
                                size=size, t=0.0, max=rise,
                                vy=self.rng.f(0.55, 0.8),
                                vx=self.rng.f(-0.12, 0.12)))

    def banner(self, text, color=(255, 255, 255), dur=1.1, sub=""):
        self.banners.append(dict(text=text, sub=sub, color=color,
                                 t=0.0, max=dur))

    def set_wind(self, v):
        self.wind = max(self.wind, v)

    def set_burst(self, v):
        self.burst = max(self.burst, v)

    # ---- step ------------------------------------------------------------
    def update(self, dt):
        alive = []
        for p in self.parts:
            p["life"] += dt
            if p["life"] >= p["max"]:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += p["grav"] * dt
            k = max(0.0, 1.0 - p["drag"] * dt)
            p["vx"] *= k
            p["vy"] *= k
            alive.append(p)
        self.parts = alive

        for r in self.rings:
            r["t"] += dt
        self.rings = [r for r in self.rings if r["t"] < r["max"]]

        for s in self.slashes:
            s["t"] += dt
        self.slashes = [s for s in self.slashes if s["t"] < s["max"]]

        for p in self.popups:
            p["t"] += dt
            p["y"] += p["vy"] * dt
            p["x"] += p["vx"] * dt
            p["vy"] *= max(0.0, 1.0 - 2.2 * dt)
        self.popups = [p for p in self.popups if p["t"] < p["max"]]

        for b in self.banners:
            b["t"] += dt
        self.banners = [b for b in self.banners if b["t"] < b["max"]]

        self.wind *= pow(0.02, dt)
        self.burst *= pow(0.05, dt)
        if self.wind < 0.02:
            self.wind = 0.0
        if self.burst < 0.02:
            self.burst = 0.0

    def busy(self):
        return bool(self.parts or self.rings or self.slashes)
