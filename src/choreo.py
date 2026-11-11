"""Fight director.

Turns a seed into a readable fight with a guaranteed dramatic arc:

    phase 1 (0-30%)   fighter A dominates        - establish
    phase 2 (30-58%)  fighter B answers back     - reversal
    phase 3 (58-84%)  both low, trading blows    - escalation
    phase 4 (84-100%) finisher KO                - payoff

The director decides who attacks, with what, and whether it lands. It never
simulates: positions are chosen so the strike visibly connects, and the render
loop reads the REAL limb position at the impact frame for the effects.
"""

from .moves import MOVE, REACT, TIERS

INTRO = 0.95
OUTRO = 2.25


class Director:
    def __init__(self, rng, fps, duration):
        self.rng = rng
        self.fps = fps
        self.duration = duration
        self.beats = []
        self.impacts = []
        self.meta = {}
        self.build()

    # ------------------------------------------------------------------
    def _place(self, atk, gap, center):
        """Absolute x for (attacker, defender) with the given gap."""
        if atk == 0:
            return (center - gap * 0.5, center + gap * 0.5)
        return (center + gap * 0.5, center - gap * 0.5)

    def _reaction(self, move, connect, rng):
        if not connect:
            return "block" if rng.chance(0.55) else "dodge"
        if move["tier"] >= 4:
            return "knockdown"
        if move["launch"] > 0.15:
            return "hurt_air" if rng.chance(0.55) else "hurt_heavy"
        if move["tier"] >= 3:
            return "hurt_heavy" if rng.chance(0.78) else "hurt_air"
        if move["tier"] == 2:
            return rng.wpick([("hurt_light", 4.0), ("hurt_heavy", 5.0),
                              ("block", 2.0)])
        return rng.wpick([("hurt_light", 6.0), ("block", 2.5),
                          ("dodge", 1.5)])

    def build(self):
        rng = self.rng
        dur = self.duration
        winner = rng.i(0, 1)
        loser = 1 - winner
        palette = rng.i(0, 5)

        fight_start = INTRO
        fight_end = dur - OUTRO
        finisher_t = fight_end - 0.55

        hp = [100.0, 100.0]
        center = rng.f(-0.30, 0.30)
        start_center = center

        t = fight_start
        guard = 0
        while t < finisher_t - 0.70 and guard < 200:
            guard += 1
            p = (t - fight_start) / max(0.001, finisher_t - fight_start)

            # who attacks
            if p < 0.30:
                atk = 0 if rng.chance(0.74) else 1
            elif p < 0.58:
                atk = 1 if rng.chance(0.70) else 0
            elif p < 0.84:
                atk = rng.i(0, 1)
            else:
                atk = winner if rng.chance(0.60) else loser
            dfn = 1 - atk

            # how hard
            if p < 0.16:
                tier = 1
            elif p < 0.44:
                tier = rng.wpick([(1, 2.2), (2, 3.0)])
            elif p < 0.70:
                tier = rng.wpick([(2, 3.0), (3, 1.7)])
            else:
                tier = rng.wpick([(2, 1.6), (3, 3.2)])

            move_name = rng.pick(TIERS[tier])
            move = MOVE[move_name]

            # does it land
            connect = rng.chance(0.74)
            react = self._reaction(move, connect, rng)

            reach = move["reach"]
            if connect:
                # the strike must land ON the defender's body, so the gap is
                # the limb's forward reach plus a small overlap margin
                gap = reach + rng.f(0.02, 0.08)
            elif react == "block":
                gap = reach + rng.f(0.10, 0.17)
            else:
                gap = reach + rng.f(0.16, 0.28)
            gap = max(0.24, min(1.90, gap))

            ax, dx = self._place(atk, gap, center)
            fi = 1 if atk == 0 else -1

            if connect:
                if react == "block":
                    # a blocked strike still connects, but barely moves anyone
                    dmg = max(1, int(round(move["dmg"] * 0.25)))
                    push_k = 0.22
                else:
                    dmg = move["dmg"]
                    push_k = 1.0
                dx2 = dx + fi * move["push"] * push_k
                ax2 = ax + fi * move["push"] * 0.18 * push_k
            else:
                dx2 = dx + fi * 0.05
                ax2 = ax
                dmg = 0

            react_dur = REACT[react]["dur"]
            beat_dur = max(move["dur"], react_dur)
            gap_t = rng.f(0.05, 0.30) * (1.0 - 0.40 * p)

            self.beats.append(dict(
                t0=t, atk=atk, dfn=dfn, move=move_name, react=react,
                connect=connect, ax=ax, dx=dx, ax2=ax2, dx2=dx2,
                dmg=dmg, beat_dur=beat_dur, tier=tier,
                facing=[1, -1][atk],
            ))

            impact_t = t + move["dur"] * move["connect_at"]
            strength = 0.42 + 0.24 * move["tier"]
            if connect and react == "block":
                strength *= 0.55
            self.impacts.append(dict(
                t=impact_t, atk=atk, dfn=dfn, move=move_name, connect=connect,
                react=react, strength=strength, dmg=dmg,
                multi=0, last=True, big=False,
                ax2=ax2, dx2=dx2,
            ))
            if connect:
                hp[dfn] -= dmg

            center += fi * move["push"] * (0.55 if connect else 0.12)
            center = max(-1.05, min(1.05, center))

            t += beat_dur + gap_t

        # ---------------------------------------------------------------
        # finisher
        # ---------------------------------------------------------------
        fin_move = MOVE["super"]
        fi = 1 if winner == 0 else -1
        gap = fin_move["reach"] + 0.05
        ax, dx = self._place(winner, gap, center)
        dx2 = dx + fi * fin_move["push"]
        ax2 = ax + fi * fin_move["push"] * 0.20

        t = finisher_t
        self.beats.append(dict(
            t0=t, atk=winner, dfn=loser, move="super", react="knockdown",
            connect=True, ax=ax, dx=dx, ax2=ax2, dx2=dx2,
            dmg=fin_move["dmg"], beat_dur=fin_move["dur"] + 1.5,
            tier=4, facing=[1, -1][winner],
        ))

        first = t + fin_move["dur"] * 0.50
        for k, u in enumerate(fin_move["multi"]):
            self.impacts.append(dict(
                t=t + fin_move["dur"] * u, atk=winner, dfn=loser,
                move="super", connect=True, react="knockdown",
                strength=1.15 + 0.25 * k, dmg=fin_move["dmg"] // 3,
                multi=k, last=(k == len(fin_move["multi"]) - 1), big=True,
                ax2=ax2, dx2=dx2,
            ))

        ko_t = t + fin_move["dur"] * fin_move["multi"][-1] + 0.42
        self.meta = dict(
            winner=winner, loser=loser, palette=palette,
            ko_t=ko_t, finisher_t=t, hp=hp,
            start_center=start_center,
            title="K.O.",
            hook=rng.pick(["FIGHT", "ROUND 1", "1 v 1", "NO MERCY",
                           "FINAL ROUND", "LET'S GO"]),
            out_frames_extra=1.0,
        )
        self.impacts.sort(key=lambda e: e["t"])
