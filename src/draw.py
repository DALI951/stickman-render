"""Rasterisation: palettes, stickman strokes, fx, and post-processing.

The whole frame is drawn at `ss`x resolution (2x by default) and box-reduced
down at the end - that is where the anti-aliasing comes from. Every coordinate
inside a frame therefore lives in supersampled pixel space.

Layer plan (keeps alpha blending correct, since PIL's ImageDraw overwrites
alpha rather than blending it):
    scene  - opaque background + ground + fighters + solid fx
    soft   - translucent fx (dust, afterimages) -> alpha_composite
    glow   - bright bloom, downscaled + blurred + screen-blended
"""

from math import cos, pi, sin

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import rig

# --------------------------------------------------------------------------
# palettes - one is picked per seed so every video has its own identity
# --------------------------------------------------------------------------
PALETTES = [
    dict(name="noir", bg=(11, 11, 14), bg2=(24, 24, 32), ground=(46, 46, 56),
         grid=(30, 30, 40), p1=(242, 242, 247), p2=(255, 77, 94),
         text=(255, 255, 255), accent=(255, 77, 94)),
    dict(name="ink", bg=(9, 13, 18), bg2=(13, 24, 34), ground=(28, 46, 60),
         grid=(18, 32, 44), p1=(238, 243, 248), p2=(53, 208, 255),
         text=(255, 255, 255), accent=(53, 208, 255)),
    dict(name="ember", bg=(18, 13, 10), bg2=(36, 21, 13), ground=(62, 38, 26),
         grid=(38, 25, 18), p1=(255, 232, 214), p2=(255, 138, 61),
         text=(255, 245, 236), accent=(255, 138, 61)),
    dict(name="toxic", bg=(9, 17, 15), bg2=(11, 28, 23), ground=(22, 52, 42),
         grid=(16, 36, 30), p1=(232, 255, 244), p2=(77, 255, 158),
         text=(240, 255, 248), accent=(77, 255, 158)),
    dict(name="vhs", bg=(17, 9, 26), bg2=(30, 15, 46), ground=(50, 32, 70),
         grid=(34, 21, 50), p1=(245, 234, 255), p2=(177, 77, 255),
         text=(248, 240, 255), accent=(177, 77, 255)),
    dict(name="paper", bg=(243, 240, 231), bg2=(225, 221, 208),
         ground=(199, 193, 178), grid=(214, 209, 196), p1=(24, 23, 27),
         p2=(192, 57, 43), text=(24, 23, 27), accent=(192, 57, 43)),
]

_FONTS = {}


def font(size):
    size = max(8, int(size))
    if size in _FONTS:
        return _FONTS[size]
    for path in (
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ):
        try:
            f = ImageFont.truetype(path, size)
            _FONTS[size] = f
            return f
        except Exception:
            continue
    try:
        f = ImageFont.load_default(size)
    except TypeError:
        f = ImageFont.load_default()
    _FONTS[size] = f
    return f


# --------------------------------------------------------------------------
# background
# --------------------------------------------------------------------------
_BG_CACHE = {}


def background(w, h, pal):
    key = (w, h, pal["name"])
    if key in _BG_CACHE:
        return _BG_CACHE[key].copy()
    t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    c0 = np.array(pal["bg"], np.float32)[None, :]
    c1 = np.array(pal["bg2"], np.float32)[None, :]
    col = (c0 + (c1 - c0) * t).astype(np.uint8)          # (h,3)
    arr = np.repeat(col[:, None, :], w, axis=1)          # (h,w,3)
    img = Image.fromarray(arr, "RGB").convert("RGBA")
    _BG_CACHE[key] = img
    return img.copy()


def draw_ground(d, proj, pal, ss):
    gy = proj.ground_y()
    W = proj.w
    H = proj.h
    d.rectangle([-20, gy, W + 20, H + 20], fill=pal["ground"] + (255,))
    d.line([(-20, gy), (W + 20, gy)], fill=pal["p1"] + (70,), width=max(1, int(2 * ss)))

    # vertical ticks in world space -> they scroll with the camera (motion cue)
    step = 0.5
    x0 = proj.cx - (W * 0.5) / proj.scale
    x1 = proj.cx + (W * 0.5) / proj.scale
    k = int(x0 / step) - 1
    w = max(1, int(1.6 * ss))
    while k * step <= x1 + step:
        wx = k * step
        sx = proj.pt((wx, 0.0))[0]
        long = (k % 2 == 0)
        hh = (0.16 if long else 0.08) * proj.scale
        d.line([(sx, gy), (sx, gy + hh)], fill=pal["grid"] + (255,), width=w)
        k += 1


# --------------------------------------------------------------------------
# stickman
# --------------------------------------------------------------------------
def chain(d, pts, color, w):
    if len(pts) < 2:
        return
    d.line(pts, fill=color, width=max(1, int(round(w))), joint="curve")


def blob(d, p, w, color):
    r = w * 0.5
    d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)


def stickman(d, j, proj, origin_x, facing, color, back_color, w, alpha=255):
    def P(p):
        return proj.pt((origin_x + facing * p[0], p[1]))

    hip = P(j["hip"]); neck = P(j["neck"]); head = P(j["head"]); sh = P(j["sh"])
    elL = P(j["elL"]); haL = P(j["haL"]); elR = P(j["elR"]); haR = P(j["haR"])
    knL = P(j["knL"]); ftL = P(j["ftL"]); knR = P(j["knR"]); ftR = P(j["ftR"])

    if alpha < 255:
        color = tuple(color) + (alpha,)
        back_color = tuple(back_color) + (alpha,)
    else:
        color = tuple(color) + (255,)
        back_color = tuple(back_color) + (255,)

    wf = max(2, int(round(w)))
    wb = max(2, int(round(w * 0.86)))

    # far side first (depth)
    chain(d, [hip, knL, ftL], back_color, wb)
    chain(d, [sh, elL, haL], back_color, wb)
    blob(d, ftL, wb, back_color)
    blob(d, haL, wb, back_color)

    # body
    chain(d, [hip, neck, head], color, wf)
    blob(d, hip, wf, color)
    blob(d, sh, wf, color)

    # head
    r = proj.size(rig.HEAD_R)
    d.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=color)

    # near side
    chain(d, [hip, knR, ftR], color, wf)
    chain(d, [sh, elR, haR], color, wf)
    blob(d, ftR, wf, color)
    blob(d, haR, wf, color)


def draw_fighter(d, f, proj, pal, color, ss):
    w = proj.size(rig.LINE_W)
    back = tuple(int(c * 0.45 + pal["bg"][i] * 0.55) for i, c in enumerate(color))

    for pose, age in f.after:
        a = int(110 * max(0.0, 1.0 - age / 0.15))
        if a <= 4:
            continue
        stickman(d, rig.fk(pose), proj, f.x, f.facing, color, back, w, alpha=a)

    stickman(d, f._fk, proj, f.x, f.facing, color, back, w)


# --------------------------------------------------------------------------
# fx
# --------------------------------------------------------------------------
def draw_fx_solid(d, fx, proj, pal, ss):
    """Opaque fx: slashes and rings."""
    for s in fx.slashes:
        u = s["t"] / s["max"]
        a = int(255 * (1.0 - u) ** 1.5)
        if a <= 6:
            continue
        r0 = 0.02 + 0.05 * u
        r1 = r0 + s["sp"] * s["t"]
        x0 = s["x"] + cos(s["a"]) * r0
        y0 = s["y"] + sin(s["a"]) * r0
        x1 = s["x"] + cos(s["a"]) * r1
        y1 = s["y"] + sin(s["a"]) * r1
        col = tuple(s["color"]) + (a,)
        d.line([proj.pt((x0, y0)), proj.pt((x1, y1))],
               fill=col, width=max(1, int(s["w"] * proj.scale)))

    for r in fx.rings:
        u = r["t"] / r["max"]
        a = int(220 * (1.0 - u) ** 1.4)
        if a <= 6:
            continue
        rad = (r["r0"] + (r["r1"] - r["r0"]) * (1.0 - (1.0 - u) ** 2))
        c = proj.pt((r["x"], r["y"]))
        rr = rad * proj.scale
        d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr],
                  outline=tuple(r["color"]) + (a,),
                  width=max(1, int(r["w"] * proj.scale * (1.0 - u * 0.6))))


def draw_fx_soft(layer, proj, fx, ss):
    """Translucent fx on their own layer, then alpha_composited."""
    d = ImageDraw.Draw(layer)
    for p in fx.parts:
        u = p["life"] / p["max"]
        a = int(255 * (1.0 - u) ** 1.6)
        if a <= 4:
            continue
        if p["kind"] == "dust":
            a = int(a * 0.45)
        c = proj.pt((p["x"], p["y"]))
        rr = max(1.0, p["r"] * proj.scale * (1.0 - 0.45 * u))
        d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr],
                  fill=tuple(p["color"]) + (a,))


def draw_popups(d, fx, proj, ss, pal):
    for p in fx.popups:
        u = p["t"] / p["max"]
        a = int(255 * (1.0 - u ** 2.2))
        if a <= 6:
            continue
        scale = 1.0 + 0.35 * max(0.0, 1.0 - u * 5.0)
        size = max(8, int(p["size"] * proj.scale * scale))
        f = font(size)
        c = proj.pt((p["x"], p["y"]))
        txt = p["text"]
        col = tuple(p["color"]) + (a,)
        d.text((c[0], c[1]), txt, font=f, fill=(0, 0, 0, int(a * 0.55)),
               anchor="mm", stroke_width=max(2, size // 12),
               stroke_fill=(0, 0, 0, int(a * 0.55)))
        d.text((c[0], c[1]), txt, font=f, fill=col, anchor="mm")


def draw_banners(img, fx, pal, ss):
    """Big centred words - drawn after the scene so they read on top."""
    d = ImageDraw.Draw(img)
    W, H = img.size
    for b in fx.banners:
        u = b["t"] / b["max"]
        if u > 0.86:
            a = int(255 * (1.0 - (u - 0.86) / 0.14))
        else:
            a = int(255 * min(1.0, u / 0.08))
        if a <= 6:
            continue
        pop = 1.0 + 0.30 * max(0.0, 1.0 - u * 6.0)
        size = int(H * 0.115 * pop)
        f = font(size)
        y = H * 0.34
        d.text((W * 0.5, y), b["text"], font=f, anchor="mm",
               fill=tuple(b["color"]) + (a,),
               stroke_width=max(2, size // 14),
               stroke_fill=(0, 0, 0, int(a * 0.8)))
        if b["sub"]:
            fs = font(int(size * 0.32))
            d.text((W * 0.5, y + size * 0.72), b["sub"], font=fs, anchor="mm",
                   fill=tuple(b["color"]) + (int(a * 0.9),),
                   stroke_width=max(2, size // 26),
                   stroke_fill=(0, 0, 0, int(a * 0.8)))


def draw_burst(d, proj, pal, amount, rng):
    """Radial speed streaks radiating out from the centre of the action."""
    c = proj.pt((proj.cx, proj.cy))
    n = int(16 + 30 * amount)
    a_col = int(50 + 130 * amount)
    col = tuple(pal["accent"]) + (a_col,)
    for _ in range(n):
        ang = rng.f(0.0, 6.283185307179586)
        r0 = proj.scale * rng.f(0.50, 1.05)
        r1 = r0 + proj.scale * rng.f(0.30, 1.40) * amount
        d.line([(c[0] + cos(ang) * r0, c[1] + sin(ang) * r0),
                (c[0] + cos(ang) * r1, c[1] + sin(ang) * r1)],
               fill=col,
               width=max(1, int(proj.scale * rng.f(0.004, 0.015))))


def draw_hud(img, fighters, pal, ss, hp_frac):
    """Thin health bars top-left / top-right."""
    d = ImageDraw.Draw(img)
    W, H = img.size
    bw = W * 0.36
    bh = H * 0.010
    m = W * 0.045
    y = H * 0.038
    for i, f in enumerate(fighters):
        frac = max(0.0, min(1.0, f.hp / f.max_hp))
        if i == 0:
            x0 = m
            x1 = m + bw
            col = pal["p1"]
        else:
            x1 = W - m
            x0 = W - m - bw
            col = pal["p2"]
        d.rectangle([x0, y, x1, y + bh], fill=(0, 0, 0, 150))
        w = bw * frac
        if i == 0:
            d.rectangle([x0, y, x0 + w, y + bh], fill=tuple(col) + (255,))
        else:
            d.rectangle([x1 - w, y, x1, y + bh], fill=tuple(col) + (255,))


# --------------------------------------------------------------------------
# post
# --------------------------------------------------------------------------
def vignette_mask(w, h):
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    r2 = xx * xx * 0.62 + yy * yy * 0.9
    v = 1.0 - 0.42 * np.clip(r2, 0.0, 1.4)
    return v[:, :, None]


def post(img, cam, vmask):
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    if cam.darken > 0.01:
        arr *= (1.0 - 0.55 * cam.darken)
    if cam.chroma > 0.02:
        k = int(1 + cam.chroma * 7)
        if k > 0:
            arr[:, :, 0] = np.roll(arr[:, :, 0], k, axis=1)
            arr[:, :, 2] = np.roll(arr[:, :, 2], -k, axis=1)
    if cam.flash > 0.004:
        arr += (255.0 - arr) * cam.flash
    arr *= vmask
    return Image.fromarray(np.clip(arr, 0.0, 255.0).astype(np.uint8), "RGB")
