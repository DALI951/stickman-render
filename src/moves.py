"""Move table.

Every attack is a keyframed clip (normalised 0..1 timeline), a hit window, a
damage value, a limb, and sound cues. Reach is DERIVED from the hit pose via
forward kinematics so the geometry can never drift out of sync with the art.

Reactions (block / hurt / knockdown) are separate clips the defender plays.
"""

from .rig import fk, pose

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def limb_reach(pose_name, limb):
    """Horizontal reach of a limb in the given pose, measured from the origin."""
    return fk(pose(pose_name))[limb][0]


def _atk(name, dur, tier, dmg, limb, hit_pose, keys, hit, connect_at,
         push, whoosh, weight, multi=None, launch=0.0, sound="impact",
         knock=False, shake=1.0):
    return dict(
        name=name, dur=dur, tier=tier, dmg=dmg, limb=limb,
        reach=limb_reach(hit_pose, limb),
        keys=keys, hit=hit, connect_at=connect_at,
        push=push, whoosh=whoosh, weight=weight,
        multi=multi or [], launch=launch, sound=sound,
        knock=knock, shake=shake,
    )


# --------------------------------------------------------------------------
# attacks
# --------------------------------------------------------------------------
MOVE = {
    "jab": _atk(
        "jab", 0.32, 1, 5, "haR", "jab_hit",
        keys=[(0.00, "stand"), (0.24, "jab_wind", "hold"),
              (0.42, "jab_hit", "snap"), (0.60, "jab_hit", "linear"),
              (0.86, "stand", "out"), (1.00, "stand")],
        hit=(0.40, 0.62), connect_at=0.46,
        push=0.10, whoosh=0.26, weight=3.0, shake=0.45,
    ),
    "backhand": _atk(
        "backhand", 0.34, 1, 6, "haR", "hook_hit",
        keys=[(0.00, "stand"), (0.22, "hook_wind", "hold"),
              (0.44, "hook_hit", "snap"), (0.60, "hook_hit", "linear"),
              (0.88, "stand", "out"), (1.00, "stand")],
        hit=(0.42, 0.62), connect_at=0.48,
        push=0.13, whoosh=0.28, weight=2.6, shake=0.5,
    ),
    "cross": _atk(
        "cross", 0.44, 2, 9, "haR", "cross_hit",
        keys=[(0.00, "stand"), (0.24, "cross_wind", "hold"),
              (0.44, "cross_hit", "snap"), (0.62, "cross_hit", "linear"),
              (0.88, "stand", "out"), (1.00, "stand")],
        hit=(0.42, 0.64), connect_at=0.48,
        push=0.24, whoosh=0.30, weight=2.2, shake=0.7,
    ),
    "hook": _atk(
        "hook", 0.48, 2, 11, "haR", "hook_hit",
        keys=[(0.00, "stand"), (0.26, "hook_wind", "hold"),
              (0.46, "hook_hit", "snap"), (0.64, "hook_hit", "linear"),
              (0.90, "stand", "out"), (1.00, "stand")],
        hit=(0.44, 0.66), connect_at=0.50,
        push=0.30, whoosh=0.32, weight=2.0, shake=0.85,
    ),
    "elbow": _atk(
        "elbow", 0.42, 2, 12, "elR", "hook_hit",
        keys=[(0.00, "stand"), (0.24, "hook_wind", "hold"),
              (0.44, "hook_hit", "snap"), (0.60, "hook_hit", "linear"),
              (0.88, "stand", "out"), (1.00, "stand")],
        hit=(0.42, 0.62), connect_at=0.48,
        push=0.22, whoosh=0.30, weight=1.8, shake=0.8,
    ),
    "upper": _atk(
        "upper", 0.54, 3, 13, "haR", "upper_hit",
        keys=[(0.00, "stand"), (0.28, "upper_wind", "hold"),
              (0.46, "upper_hit", "snap"), (0.64, "upper_hit", "linear"),
              (0.92, "stand", "out"), (1.00, "stand")],
        hit=(0.44, 0.66), connect_at=0.50,
        push=0.20, whoosh=0.34, weight=1.5, shake=1.0,
        launch=0.22, sound="impact_heavy",
    ),
    "body_kick": _atk(
        "body_kick", 0.46, 2, 10, "ftR", "kick_hit",
        keys=[(0.00, "stand"), (0.26, "kick_wind", "hold"),
              (0.46, "kick_hit", "snap"), (0.62, "kick_hit", "linear"),
              (0.90, "stand", "out"), (1.00, "stand")],
        hit=(0.44, 0.64), connect_at=0.50,
        push=0.40, whoosh=0.32, weight=2.0, shake=0.9,
    ),
    "high_kick": _atk(
        "high_kick", 0.60, 3, 15, "ftR", "kick_hit",
        keys=[(0.00, "stand"), (0.30, "kick_wind", "hold"),
              (0.48, "kick_hit", "snap"), (0.66, "kick_hit", "linear"),
              (0.94, "stand", "out"), (1.00, "stand")],
        hit=(0.46, 0.68), connect_at=0.52,
        push=0.46, whoosh=0.36, weight=1.4, shake=1.15,
        launch=0.10, sound="impact_heavy",
    ),
    "spin_kick": _atk(
        "spin_kick", 0.70, 3, 18, "ftR", "kick_hit",
        keys=[(0.00, "stand"), (0.30, "dash", "hold"),
              (0.44, "kick_wind", "linear"),
              (0.56, "kick_hit", "snap"), (0.70, "kick_hit", "linear"),
              (0.94, "stand", "out"), (1.00, "stand")],
        hit=(0.54, 0.74), connect_at=0.60,
        push=0.62, whoosh=0.40, weight=1.0, shake=1.4,
        launch=0.14, sound="impact_heavy",
    ),
    "super": _atk(
        "super", 1.30, 4, 42, "haR", "super_hit",
        keys=[(0.00, "stand"), (0.14, "super_wind", "hold"),
              (0.34, "super_wind", "linear"),
              (0.44, "dash", "snap"), (0.52, "super_hit", "snap"),
              (0.74, "super_hit", "linear"),
              (0.88, "stand", "out"), (1.00, "stand")],
        hit=(0.50, 0.78), connect_at=0.56,
        push=0.85, whoosh=0.44, weight=1.0, shake=1.8,
        multi=[0.56, 0.64, 0.72], launch=0.26,
        sound="super", knock=True,
    ),
}

# escalation ladder: light -> heavy as the fight goes on
TIERS = {
    1: ["jab", "backhand"],
    2: ["cross", "hook", "elbow", "body_kick"],
    3: ["upper", "high_kick", "spin_kick"],
    4: ["super"],
}

# --------------------------------------------------------------------------
# reaction clips (played by the defender)
# --------------------------------------------------------------------------
REACT = {
    "none": dict(dur=0.20, keys=[(0.00, "stand"), (1.00, "stand")], push=0.0),
    "block": dict(
        dur=0.32, push=0.06,
        keys=[(0.00, "stand"), (0.18, "block", "snap"),
              (0.66, "block", "linear"), (1.00, "stand", "out")],
    ),
    "hurt_light": dict(
        dur=0.34, push=0.14,
        keys=[(0.00, "stand"), (0.16, "hurt_light", "snap"),
              (0.52, "hurt_light", "linear"), (1.00, "stand", "out")],
    ),
    "hurt_heavy": dict(
        dur=0.56, push=0.30,
        keys=[(0.00, "stand"), (0.14, "hurt_heavy", "snap"),
              (0.46, "hurt_heavy", "linear"), (0.80, "crouch", "inout"),
              (1.00, "stand", "out")],
    ),
    "hurt_air": dict(
        dur=0.72, push=0.42,
        keys=[(0.00, "stand"), (0.12, "hurt_heavy", "snap"),
              (0.34, "jump_air", "out"), (0.62, "jump_air", "linear"),
              (0.84, "jump_land", "in"), (1.00, "crouch", "out")],
    ),
    "knockdown": dict(
        dur=1.35, push=0.55,
        keys=[(0.00, "stand"), (0.12, "hurt_heavy", "snap"),
              (0.30, "knockdown", "out"), (0.52, "ground", "out"),
              (0.90, "ground", "linear"), (1.00, "ground", "linear")],
    ),
    "dodge": dict(
        dur=0.38, push=0.0,
        keys=[(0.00, "stand"), (0.24, "dodge", "snap"),
              (0.56, "dodge", "linear"), (1.00, "stand", "out")],
    ),
}

# which reaction a fighter plays for a given hit strength
HIT_REACT = {
    "light": "hurt_light",
    "heavy": "hurt_heavy",
    "air": "hurt_air",
    "down": "knockdown",
}


# --------------------------------------------------------------------------
# resolve pose NAMES into grounded pose dicts, once, at import time.
# Everything downstream (blending, drawing) then works on plain dicts.
# --------------------------------------------------------------------------
def _resolve(keys):
    out = []
    for k in keys:
        out.append((k[0], pose(k[1])) + tuple(k[2:]))
    return out


for _m in MOVE.values():
    _m["keys"] = _resolve(_m["keys"])

for _r in REACT.values():
    _r["keys"] = _resolve(_r["keys"])
