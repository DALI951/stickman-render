"""Fighter state machine.

A fighter owns position, facing, health, a state and a pose. It decides
nothing - the director writes `target_x` and calls `attack()` / `react()`.
Movement toward target_x is the single mechanism behind stepping in, walking,
and being knocked backwards; only the speed changes per state.
"""

from . import rig
from .moves import MOVE, REACT


class Fighter:
    def __init__(self, x, facing, name="P1", hp=100.0):
        self.x = float(x)
        self.facing = 1 if facing >= 0 else -1
        self.name = name
        self.hp = float(hp)
        self.max_hp = float(hp)
        self.vx = 0.0
        self.target_x = float(x)
        self.state = "idle"
        self.t = 0.0
        self.dur = 1e9
        self.move = None
        self.clip = None
        self.clip_name = None
        self.phase = 0.0
        self.flash = 0.0
        self.after = []            # [[pose, age], ...] afterimages
        self.knocked = False
        self.walk_speed = 2.9
        self._pose = rig.pose("stand")
        self._fk = rig.fk(self._pose)

    # ---- geometry --------------------------------------------------------
    def chest_y(self):
        j = self._fk
        return (j["neck"][1] + j["hip"][1]) * 0.5

    def world_point(self, local):
        return (self.x + self.facing * local[0], local[1])

    def hit_point(self, limb="haR"):
        return self.world_point(self._fk[limb])

    def body_segment(self):
        return (self.world_point(self._fk["hip"]),
                self.world_point(self._fk["neck"]))

    # ---- instructions from the director ---------------------------------
    def set_target(self, x):
        self.target_x = float(x)

    def attack(self, move_name, facing=None):
        if facing:
            self.facing = 1 if facing >= 0 else -1
        self.state = "attack"
        self.move = MOVE[move_name]
        self.dur = self.move["dur"]
        self.t = 0.0

    def react(self, react_name):
        self.state = "react"
        self.clip_name = react_name
        self.clip = REACT[react_name]
        self.dur = self.clip["dur"]
        self.t = 0.0

    def go_down(self):
        self.state = "down"
        self.dur = 1e9
        self.t = 0.0
        self.knocked = True

    def getup(self, dur=0.75):
        self.state = "getup"
        self.dur = dur
        self.t = 0.0
        self.knocked = False

    def idle(self):
        self.state = "idle"
        self.dur = 1e9
        self.t = 0.0

    def celebrate(self):
        self.state = "win"
        self.dur = 1e9
        self.t = 0.0

    # ---- per frame -------------------------------------------------------
    def update(self, dt):
        self.t += dt

        speed = self.walk_speed
        if self.state == "attack":
            speed = self.walk_speed * 0.55
        elif self.state in ("react", "getup"):
            speed = self.walk_speed * 1.6
        elif self.state in ("down", "win"):
            speed = 0.0

        dx = self.target_x - self.x
        step = speed * dt
        if abs(dx) <= step or step == 0.0:
            self.x = self.target_x
            self.vx = 0.0
        else:
            d = step if dx > 0 else -step
            self.x += d
            self.vx = d / dt if dt > 0 else 0.0

        self.phase = (self.phase + abs(self.vx) * dt * 1.55) % 1.0

        if self.state in ("attack", "react", "getup") and self.t >= self.dur:
            self.idle()

        self._pose = self._pose_now()
        self._fk = rig.fk(self._pose)

        if self.state == "attack" and self.move and self.move["tier"] >= 3:
            self.after.append([dict(self._pose), 0.0])
            if len(self.after) > 5:
                self.after.pop(0)
        for a in self.after:
            a[1] += dt
        if self.after:
            self.after = [a for a in self.after if a[1] < 0.15]

        self.flash = max(0.0, self.flash - dt * 7.0)

    def _pose_now(self):
        st = self.state
        if st == "attack" and self.move:
            u = min(1.0, self.t / self.dur)
            return rig.eval_keys(self.move["keys"], u)
        if st == "react" and self.clip:
            u = min(1.0, self.t / self.dur)
            return rig.eval_keys(self.clip["keys"], u)
        if st == "down":
            return rig.pose("ground")
        if st == "getup":
            u = min(1.0, self.t / self.dur)
            return rig.lerp(rig.pose("ground"), rig.pose("stand"),
                            rig.ease(u, "inout"))
        if st == "win":
            return rig.pose("win")
        if abs(self.vx) > 0.15:
            return rig.walk_pose(self.phase)
        return rig.idle_pose(self.t)

    # ---- queries ---------------------------------------------------------
    def pose_now(self):
        return self._pose

    def is_attacking(self):
        return self.state == "attack"

    def attack_progress(self):
        return self.t / self.dur if self.dur > 0 else 0.0

    def is_idle_ish(self):
        return self.state in ("idle", "win", "down")
