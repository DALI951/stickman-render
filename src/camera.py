"""Camera director.

Choreographed by hand, not simulated: the camera frames both fighters, punches
in on impacts, shakes, rolls and drops into slow motion for finishers. Every
value is smoothed so nothing snaps.

The world -> screen transform lives in `Projector` and includes roll, so roll
costs nothing extra (no post-rotate pass on the frame).
"""

from math import cos, radians, sin


class Camera:
    def __init__(self, w, h, rng):
        self.w = w
        self.h = h
        self.rng = rng
        self.base_scale = h * 0.34          # pixels per world unit at zoom 1
        self.cx = 0.0                       # world point at screen centre
        self.cy = 0.62
        self.zoom = 1.0
        self.roll = 0.0
        self.shake = 0.0
        self.shake_roll = 0.0
        self.flash = 0.0
        self.chroma = 0.0
        self.darken = 0.0
        self.slowmo = 1.0
        self._shake_x = 0.0
        self._shake_y = 0.0
        self.zoom_bias = 0.0

    # ---- impulses --------------------------------------------------------
    def kick(self, strength=1.0, roll=0.0):
        self.shake = max(self.shake, 10.0 * strength)
        self.shake_roll = max(self.shake_roll, roll)
        self.zoom_bias = max(self.zoom_bias, 0.10 * strength)

    def hit_flash(self, amount=0.55):
        self.flash = max(self.flash, amount)

    def chroma_pulse(self, amount=1.0):
        self.chroma = max(self.chroma, amount)

    def slow(self, factor=0.35, duration=0.0):
        self.slowmo = min(self.slowmo, factor)

    # ---- per-frame -------------------------------------------------------
    def update(self, dt, a, b, focus=None, dt_real=None):
        dt_real = dt_real if dt_real is not None else dt

        # --- framing ------------------------------------------------------
        mx = (a.x + b.x) * 0.5
        gap = abs(a.x - b.x)
        if focus is not None:
            mx = mx * 0.55 + focus[0] * 0.45

        span = gap + 0.60
        fit = self.w / (self.base_scale * span)
        fit = max(0.52, min(2.40, fit))
        target_zoom = fit + self.zoom_bias

        # vertical: keep the action band centred, lift a little when airborne
        top = max(a.chest_y(), b.chest_y())
        target_cy = 0.63 + (top - 0.70) * 0.30

        # look slightly ahead of the pair so movement reads
        lead = (a.vx + b.vx) * 0.05

        self.zoom += (target_zoom - self.zoom) * min(1.0, dt_real * 3.2)
        self.cx += ((mx + lead) - self.cx) * min(1.0, dt_real * 2.6)
        self.cy += (target_cy - self.cy) * min(1.0, dt_real * 2.0)

        # --- decay --------------------------------------------------------
        self.shake *= pow(0.0025, dt_real)
        self.shake_roll *= pow(0.004, dt_real)
        self.flash *= pow(0.00002, dt_real)
        self.chroma *= pow(0.01, dt_real)
        self.zoom_bias *= pow(0.01, dt_real)
        self.darken *= pow(0.02, dt_real)

        if self.shake < 0.05:
            self.shake = 0.0
        if self.flash < 0.004:
            self.flash = 0.0
        if self.chroma < 0.02:
            self.chroma = 0.0
        if self.darken < 0.01:
            self.darken = 0.0

        amp = self.shake
        self._shake_x = self.rng.f(-amp, amp)
        self._shake_y = self.rng.f(-amp, amp)
        self.roll = self.rng.f(-self.shake_roll, self.shake_roll) * 0.6

        # slow motion recovers toward 1.0
        if self.slowmo < 1.0:
            self.slowmo += dt_real * 0.55
            if self.slowmo > 1.0:
                self.slowmo = 1.0

    def projector(self, ss=1):
        """Build a projector in supersampled pixel space."""
        return Projector(self.w * ss, self.h * ss, self.cx, self.cy,
                         self.base_scale * self.zoom * ss, self.roll,
                         self._shake_x * ss, self._shake_y * ss)


class Projector:
    """world (x right, y up, ground y=0) -> screen pixels."""

    def __init__(self, w, h, cx, cy, scale, roll_deg, sx, sy):
        self.w = w
        self.h = h
        self.cx = cx
        self.cy = cy
        self.scale = scale
        self.sx = sx
        self.sy = sy
        r = radians(roll_deg)
        self._c = cos(r)
        self._s = sin(r)

    def pt(self, p):
        x = (p[0] - self.cx) * self.scale
        y = (p[1] - self.cy) * self.scale
        xr = x * self._c - y * self._s
        yr = x * self._s + y * self._c
        return (self.w * 0.5 + xr + self.sx, self.h * 0.5 - yr + self.sy)

    def size(self, units):
        return units * self.scale

    def ground_y(self):
        return self.pt((0.0, 0.0))[1]
