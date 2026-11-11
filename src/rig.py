"""Stickman rig: proportions, forward kinematics, pose library, interpolation.

COORDINATES
    World space: x = right, y = UP, ground at y = 0. One unit = one character
    height (so a fighter is ~1.0 tall). Fighters are authored FACING RIGHT;
    a left-facing fighter is mirrored at projection time.

BONE ANGLES
    Degrees, 0 = straight UP, positive = clockwise on screen.
    So 90 = right, 180 = down, -90 = left, 0 = up.
    All angles are ABSOLUTE (not relative to the parent bone) - that makes
    hand-authoring poses far easier, and blending is a plain per-key lerp.

POSES
    Flat dicts of named floats, so two poses can be blended by lerping every
    key. `plant()` then snaps the pose onto the ground so feet never float.
"""

from math import sin, cos, radians

# --------------------------------------------------------------------------
# proportions (character-height units)
# --------------------------------------------------------------------------
HIP_H = 0.500          # hip height with legs straight
TORSO = 0.220          # hip -> neck
NECK_HEAD = 0.078      # neck -> head centre
HEAD_R = 0.064         # head radius
UPPERARM = 0.140
FOREARM = 0.140
THIGH = 0.240
SHIN = 0.260
SHOULDER_DROP = 0.040  # shoulders sit this far below the neck along the torso
LINE_W = 0.028         # default bone thickness

BONES = ("torso", "head", "shL", "elL", "shR", "elR", "thL", "knL", "thR", "knR")
POSE_KEYS = BONES + ("rootx", "rooty")


def unit(angle):
    """Unit direction vector for a bone angle (0 = up, + = clockwise)."""
    a = radians(angle)
    return (sin(a), cos(a))


def add(p, q):
    return (p[0] + q[0], p[1] + q[1])


def mul(p, k):
    return (p[0] * k, p[1] * k)


def fk(p):
    """Forward kinematics. Returns world joint positions for a pose.

    Origin is the point on the ground directly under the hip, so a pose with
    rooty = 0 and straight legs puts the feet exactly at y = 0.
    """
    hip = (p["rootx"], HIP_H + p["rooty"])
    neck = add(hip, mul(unit(p["torso"]), TORSO))
    head = add(neck, mul(unit(p["head"]), NECK_HEAD))
    sh = add(neck, mul(unit(p["torso"]), -SHOULDER_DROP))

    elL = add(sh, mul(unit(p["shL"]), UPPERARM))
    haL = add(elL, mul(unit(p["elL"]), FOREARM))
    elR = add(sh, mul(unit(p["shR"]), UPPERARM))
    haR = add(elR, mul(unit(p["elR"]), FOREARM))

    knL = add(hip, mul(unit(p["thL"]), THIGH))
    ftL = add(knL, mul(unit(p["knL"]), SHIN))
    knR = add(hip, mul(unit(p["thR"]), THIGH))
    ftR = add(knR, mul(unit(p["knR"]), SHIN))

    return {
        "hip": hip, "neck": neck, "head": head, "sh": sh,
        "elL": elL, "haL": haL, "elR": elR, "haR": haR,
        "knL": knL, "ftL": ftL, "knR": knR, "ftR": ftR,
    }


def plant(p, mode="feet", ground=0.0):
    """Shift rooty so the pose touches the ground. Returns a new dict.

    mode "feet" - only the feet matter (standing, walking, attacking).
    mode "all"  - any joint may touch (lying down, knocked out).
    """
    j = fk(p)
    if mode == "all":
        low = min(v[1] for v in j.values())
    else:
        low = min(j["ftL"][1], j["ftR"][1])
    out = dict(p)
    out["rooty"] += ground - low
    return out


# --------------------------------------------------------------------------
# easing
# --------------------------------------------------------------------------
def ease(t, kind="inout"):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    if kind == "linear":
        return t
    if kind == "in":
        return t * t
    if kind == "out":
        return 1.0 - (1.0 - t) ** 2
    if kind == "snap":                 # very fast start, long settle
        return 1.0 - (1.0 - t) ** 3
    if kind == "hold":                 # slow build, hard stop (wind-ups)
        return t * t * t
    return t * t * (3.0 - 2.0 * t)     # inout


def lerp(a, b, t):
    return {k: a[k] + (b[k] - a[k]) * t for k in POSE_KEYS}


def eval_keys(keys, t, default="inout"):
    """keys = [(t_norm, pose) | (t_norm, pose, easing)], sorted by t_norm."""
    if t <= keys[0][0]:
        return dict(keys[0][1])
    if t >= keys[-1][0]:
        return dict(keys[-1][1])
    for i in range(len(keys) - 1):
        t0 = keys[i][0]
        t1 = keys[i + 1][0]
        if t0 <= t <= t1:
            k = keys[i + 1]
            e = k[2] if len(k) > 2 else default
            u = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            return lerp(keys[i][1], keys[i + 1][1], ease(u, e))
    return dict(keys[-1][1])


# --------------------------------------------------------------------------
# pose library - authored for a character FACING RIGHT
# --------------------------------------------------------------------------
STAND = dict(torso=2, head=-2, shL=196, elL=184, shR=166, elR=176,
             thL=192, knL=176, thR=169, knR=185, rootx=0.0, rooty=0.0)

CROUCH = dict(torso=14, head=-10, shL=206, elL=196, shR=150, elR=168,
              thL=214, knL=142, thR=150, knR=206, rootx=0.02, rooty=0.0)

DASH = dict(torso=28, head=-20, shL=222, elL=200, shR=122, elR=152,
            thL=214, knL=170, thR=122, knR=176, rootx=0.03, rooty=0.0)

JUMP_UP = dict(torso=10, head=-6, shL=232, elL=200, shR=128, elR=160,
               thL=200, knL=110, thR=160, knR=120, rootx=0.0, rooty=0.10)
JUMP_AIR = dict(torso=6, head=-4, shL=214, elL=196, shR=146, elR=176,
                thL=206, knL=128, thR=150, knR=150, rootx=0.0, rooty=0.26)
JUMP_LAND = CROUCH

JAB_WIND = dict(torso=0, head=-2, shL=198, elL=186, shR=205, elR=40,
                thL=194, knL=178, thR=168, knR=184, rootx=-0.01, rooty=0.0)
JAB_HIT = dict(torso=6, head=2, shL=202, elL=192, shR=92, elR=90,
               thL=196, knL=178, thR=164, knR=184, rootx=0.03, rooty=0.0)

CROSS_WIND = dict(torso=-8, head=-8, shL=206, elL=150, shR=200, elR=30,
                  thL=196, knL=178, thR=170, knR=186, rootx=-0.02, rooty=0.0)
CROSS_HIT = dict(torso=10, head=4, shL=208, elL=170, shR=94, elR=92,
                 thL=200, knL=178, thR=160, knR=182, rootx=0.045, rooty=0.0)

HOOK_WIND = dict(torso=-8, head=-6, shL=204, elL=180, shR=216, elR=112,
                 thL=194, knL=178, thR=170, knR=186, rootx=-0.015, rooty=0.0)
HOOK_HIT = dict(torso=12, head=6, shL=206, elL=176, shR=64, elR=96,
                thL=200, knL=178, thR=158, knR=182, rootx=0.05, rooty=0.0)

UPPER_WIND = dict(torso=16, head=-12, shL=210, elL=196, shR=168, elR=142,
                  thL=212, knL=148, thR=154, knR=204, rootx=0.0, rooty=0.0)
UPPER_HIT = dict(torso=-8, head=6, shL=212, elL=186, shR=28, elR=44,
                 thL=196, knL=180, thR=166, knR=184, rootx=0.05, rooty=0.04)

KICK_WIND = dict(torso=-10, head=-6, shL=130, elL=155, shR=210, elR=190,
                 thL=190, knL=178, thR=236, knR=130, rootx=-0.02, rooty=0.0)
KICK_HIT = dict(torso=-16, head=10, shL=100, elL=110, shR=232, elR=200,
                thL=192, knL=180, thR=94, knR=96, rootx=0.0, rooty=0.02)

BLOCK = dict(torso=12, head=-8, shL=215, elL=-30, shR=132, elR=-8,
             thL=206, knL=158, thR=158, knR=198, rootx=0.0, rooty=0.0)

HURT_LIGHT = dict(torso=-14, head=-20, shL=202, elL=210, shR=185, elR=200,
                  thL=190, knL=176, thR=176, knR=196, rootx=-0.03, rooty=0.0)
HURT_HEAVY = dict(torso=-28, head=-34, shL=205, elL=230, shR=220, elR=245,
                  thL=182, knL=172, thR=196, knR=206, rootx=-0.07, rooty=0.0)

KNOCKDOWN = dict(torso=-70, head=-95, shL=300, elL=320, shR=290, elR=310,
                 thL=130, knL=150, thR=120, knR=145, rootx=-0.10, rooty=0.25)
GROUND = dict(torso=-92, head=-100, shL=330, elL=350, shR=300, elR=320,
              thL=88, knL=84, thR=95, knR=100, rootx=-0.16, rooty=0.10)

SUPER_WIND = dict(torso=-14, head=-10, shL=228, elL=208, shR=238, elR=214,
                  thL=198, knL=178, thR=170, knR=192, rootx=-0.04, rooty=0.0)
SUPER_HIT = dict(torso=22, head=8, shL=236, elL=228, shR=86, elR=88,
                 thL=206, knL=162, thR=152, knR=204, rootx=0.07, rooty=0.0)

DODGE = dict(torso=-24, head=-16, shL=228, elL=205, shR=175, elR=150,
             thL=178, knL=174, thR=202, knR=216, rootx=-0.05, rooty=0.0)

WIN = dict(torso=-4, head=6, shL=222, elL=228, shR=132, elR=126,
           thL=192, knL=176, thR=170, knR=184, rootx=0.0, rooty=0.0)

# poses that must NOT be snapped to the ground by the feet
AIR_POSES = {"jump_up", "jump_air", "knockdown", "ground"}
LIE_POSES = {"knockdown", "ground"}

POSES = {
    "stand": STAND, "crouch": CROUCH, "dash": DASH,
    "jump_up": JUMP_UP, "jump_air": JUMP_AIR, "jump_land": JUMP_LAND,
    "jab_wind": JAB_WIND, "jab_hit": JAB_HIT,
    "cross_wind": CROSS_WIND, "cross_hit": CROSS_HIT,
    "hook_wind": HOOK_WIND, "hook_hit": HOOK_HIT,
    "upper_wind": UPPER_WIND, "upper_hit": UPPER_HIT,
    "kick_wind": KICK_WIND, "kick_hit": KICK_HIT,
    "block": BLOCK, "dodge": DODGE,
    "hurt_light": HURT_LIGHT, "hurt_heavy": HURT_HEAVY,
    "knockdown": KNOCKDOWN, "ground": GROUND,
    "super_wind": SUPER_WIND, "super_hit": SUPER_HIT,
    "win": WIN,
}


def grounded(name, pose):
    """Snap a named pose onto the ground appropriately."""
    if name in LIE_POSES:
        # lowest joint a little above zero so the head circle is not buried
        return plant(pose, "all", ground=0.055)
    if name in AIR_POSES:
        return dict(pose)
    return plant(pose, "feet")


def pose(name):
    """Look up a named pose, already grounded."""
    return grounded(name, POSES[name])


# --------------------------------------------------------------------------
# procedural cycles (walk / run / idle) - smoother than hand keyframes
# --------------------------------------------------------------------------
def walk_pose(phase, amp=30.0, lean=5.0, arm_amp=26.0, knee=26.0):
    a = phase * 6.283185307179586
    s = sin(a)
    c = cos(a)
    thR = 180.0 - amp * s
    thL = 180.0 + amp * s
    knR = thR + 10.0 + knee * max(0.0, -c)
    knL = thL + 10.0 + knee * max(0.0, c)
    shR = 180.0 + arm_amp * s
    shL = 180.0 - arm_amp * s
    p = dict(torso=lean, head=-lean * 0.7,
             shL=shL, elL=shL + 20.0, shR=shR, elR=shR + 20.0,
             thL=thL, knL=knL, thR=thR, knR=knR,
             rootx=0.0, rooty=0.0)
    return plant(p, "feet")


def idle_pose(t, speed=1.0):
    """Gentle breathing bob around STAND."""
    a = t * 2.1 * speed
    s = sin(a)
    p = dict(STAND)
    p["torso"] = STAND["torso"] + 1.6 * s
    p["head"] = STAND["head"] - 1.2 * s
    p["shR"] = STAND["shR"] - 2.5 * s
    p["shL"] = STAND["shL"] + 2.0 * s
    p["elR"] = STAND["elR"] + 3.0 * s
    p["rooty"] = STAND["rooty"] + 0.006 * sin(a * 2.0)
    return plant(p, "feet")


def block_pose(t):
    p = dict(BLOCK)
    s = sin(t * 3.0)
    p["shR"] = BLOCK["shR"] - 2.0 * s
    p["shL"] = BLOCK["shL"] + 2.0 * s
    return plant(p, "feet")
