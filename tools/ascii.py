"""Text-mode preview.

Renders the rig and whole fight frames as ASCII so the animation can be
inspected without an image viewer (and so verification is possible from a
plain terminal). This is how the poses were tuned.

    python tools/ascii.py poses
    python tools/ascii.py fight 42
"""

import sys

sys.path.insert(0, ".")

from src import rig  # noqa: E402
from src.choreo import Director  # noqa: E402
from src.fighter import Fighter  # noqa: E402
from src.moves import MOVE  # noqa: E402
from src.rng import Rng  # noqa: E402

COLS = 54
ROWS = 21


class Grid:
    def __init__(self, xr, yr, cols=COLS, rows=ROWS):
        self.g = [[" "] * cols for _ in range(rows)]
        self.xr = xr
        self.yr = yr
        self.cols = cols
        self.rows = rows

    def map(self, p):
        u = (p[0] - self.xr[0]) / (self.xr[1] - self.xr[0])
        v = (p[1] - self.yr[0]) / (self.yr[1] - self.yr[0])
        c = int(round(u * (self.cols - 1)))
        r = int(round((1.0 - v) * (self.rows - 1)))
        return c, r

    def put(self, c, r, ch):
        if 0 <= r < self.rows and 0 <= c < self.cols:
            self.g[r][c] = ch

    def line(self, a, b, ch):
        c0, r0 = self.map(a)
        c1, r1 = self.map(b)
        n = max(abs(c1 - c0), abs(r1 - r0), 1)
        for i in range(n + 1):
            t = i / n
            self.put(int(round(c0 + (c1 - c0) * t)),
                     int(round(r0 + (r1 - r0) * t)), ch)

    def circle(self, c0, r0, rad, ch):
        cc, rr = self.map((c0, r0))
        pr = max(1, int(round(rad / (self.xr[1] - self.xr[0]) * self.cols)))
        for r in range(rr - pr, rr + pr + 1):
            for c in range(cc - pr, cc + pr + 1):
                if (c - cc) ** 2 + (r - rr) ** 2 <= pr * pr:
                    self.put(c, r, ch)

    def text(self):
        return "\n".join("".join(row) for row in self.g)


def draw_figure(g, j, origin_x, facing, head_ch="O", torso_ch="#",
                armF="r", armB="b", legF="R", legB="L", foot_ch="v"):
    def P(p):
        return (origin_x + facing * p[0], p[1])

    # back side
    g.line(P(j["hip"]), P(j["knL"]), legB)
    g.line(P(j["knL"]), P(j["ftL"]), legB)
    g.line(P(j["sh"]), P(j["elL"]), armB)
    g.line(P(j["elL"]), P(j["haL"]), armB)
    # torso
    g.line(P(j["hip"]), P(j["neck"]), torso_ch)
    g.line(P(j["neck"]), P(j["head"]), torso_ch)
    # front side
    g.line(P(j["hip"]), P(j["knR"]), legF)
    g.line(P(j["knR"]), P(j["ftR"]), legF)
    g.line(P(j["sh"]), P(j["elR"]), armF)
    g.line(P(j["elR"]), P(j["haR"]), armF)
    # head
    hc = P(j["head"])
    g.circle(hc[0], hc[1], rig.HEAD_R, head_ch)
    g.put(*g.map(P(j["hip"])), "+")
    g.put(*g.map(P(j["sh"])), "+")
    g.put(*g.map(P(j["ftR"])), foot_ch)
    g.put(*g.map(P(j["ftL"])), foot_ch)
    g.put(*g.map(P(j["haR"])), "o")
    g.put(*g.map(P(j["haL"])), "o")


def show_poses(names):
    for name in names:
        p = rig.pose(name)
        j = rig.fk(p)
        low = min(j["ftL"][1], j["ftR"][1])
        g = Grid((-0.85, 0.85), (-0.08, 1.12))
        g.line((-0.85, 0.0), (0.85, 0.0), "=")
        draw_figure(g, j, 0.0, 1)
        print(f"\n=== {name}   (lowest foot y = {low:+.4f}, "
              f"head y = {j['head'][1]:.3f}, handR x = {j['haR'][0]:+.3f}, "
              f"footR x = {j['ftR'][0]:+.3f})")
        print(g.text())


def check_poses(names):
    """Geometric invariants - the part that catches impossible poses."""
    bad = []
    for name in names:
        p = rig.pose(name)
        j = rig.fk(p)
        errs = []

        def near(a, b, tol=1e-6):
            return abs(a - b) <= tol

        if not near(dist(j["hip"], j["neck"]), rig.TORSO):
            errs.append("torso length")
        if not near(dist(j["neck"], j["head"]), rig.NECK_HEAD):
            errs.append("neck length")
        if not near(dist(j["sh"], j["elR"]), rig.UPPERARM):
            errs.append("upper arm R")
        if not near(dist(j["elR"], j["haR"]), rig.FOREARM):
            errs.append("forearm R")
        if not near(dist(j["hip"], j["knR"]), rig.THIGH):
            errs.append("thigh R")
        if not near(dist(j["knR"], j["ftR"]), rig.SHIN):
            errs.append("shin R")

        if name not in rig.LIE_POSES:
            if j["head"][1] <= j["neck"][1]:
                errs.append("head not above neck")
            if j["neck"][1] <= j["hip"][1]:
                errs.append("neck not above hip")
        if name not in rig.AIR_POSES:
            low = min(j["ftL"][1], j["ftR"][1])
            if abs(low) > 1e-6:
                errs.append(f"feet not on ground ({low:+.5f})")

        if errs:
            bad.append((name, errs))
    return bad


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def show_fight(seed, fps=30, duration=None, times=None):
    rng = Rng(seed * 7919 + 13)
    duration = duration or 24.0
    d = Director(rng, fps, duration)
    first = d.beats[0]
    a = Fighter(first["ax"], 1, "P1")
    b = Fighter(first["dx"], -1, "P2")
    a.set_target(first["ax"])
    b.set_target(first["dx"])
    beats, impacts = d.beats, d.impacts
    bi = ii = 0
    dt = 1.0 / fps
    t = 0.0
    frames = 0
    want = set(int(round(x * fps)) for x in (times or []))
    while t < duration and frames < fps * duration * 1.5:
        t += dt
        frames += 1
        while bi < len(beats) and t >= beats[bi]["t0"]:
            bt = beats[bi]
            fighters = [a, b]
            fighters[bt["atk"]].attack(bt["move"], facing=bt["facing"])
            fighters[bt["atk"]].set_target(bt["ax"])
            fighters[bt["dfn"]].set_target(bt["dx"])
            bi += 1
        while ii < len(impacts) and t >= impacts[ii]["t"]:
            ev = impacts[ii]
            fs = [a, b]
            pt = fs[ev["atk"]].hit_point(MOVE[ev["move"]]["limb"])
            if ev["connect"]:
                fs[ev["dfn"]].react(ev["react"])
            if "dx2" in ev:
                fs[ev["dfn"]].set_target(ev["dx2"])
            print(f"    >> t={t:5.2f} {ev['move']:9s} "
                  f"P{ev['atk']+1}->P{ev['dfn']+1} "
                  f"connect={ev['connect']} react={ev['react']:11s} "
                  f"limb=({pt[0]:+.2f},{pt[1]:.2f}) "
                  f"gap={abs(a.x-b.x):.2f}")
            ii += 1
        a.update(dt)
        b.update(dt)
        if frames in want:
            print(f"\n--- frame {frames}  t={t:.2f}s  "
                  f"P1 x={a.x:+.2f} {a.state}  P2 x={b.x:+.2f} {b.state}  "
                  f"gap={abs(a.x-b.x):.2f}")
            g = Grid((-1.35, 1.35), (-0.08, 1.20), cols=76, rows=22)
            g.line((-1.35, 0.0), (1.35, 0.0), "=")
            draw_figure(g, a._fk, a.x, a.facing)
            draw_figure(g, b._fk, b.x, b.facing)
            print(g.text())


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    names = list(rig.POSES.keys())
    if mode == "check":
        bad = check_poses(names)
        if bad:
            print("POSE INVARIANT FAILURES:")
            for n, e in bad:
                print(f"  {n}: {', '.join(e)}")
        else:
            print(f"all {len(names)} poses pass geometric invariants")
    elif mode == "poses":
        show_poses(sys.argv[2:] if len(sys.argv) > 2 else names)
    elif mode == "fight":
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42
        times = [float(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 \
            else [1.4, 3.0, 6.0, 12.0]
        show_fight(seed, times=times)


if __name__ == "__main__":
    main()
