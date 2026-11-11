"""Deterministic seeded RNG.

One seed must always produce the exact same video, so every random decision in
the whole engine goes through this class. No global `random` anywhere.
"""

import numpy as np


def _mix(seed):
    """SplitMix64 finaliser.

    numpy seeds small consecutive integers into correlated first draws - with
    raw seeds 1..8, 4 of 8 videos came out with the same palette. Mixing the
    seed first spreads every derived stream (palette, beats, fx) properly.
    """
    M = 0xFFFFFFFFFFFFFFFF
    x = (int(seed) + 0x9E3779B97F4A7C15) & M
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M
    return (x ^ (x >> 31)) & M


class Rng:
    def __init__(self, seed):
        self.seed = int(seed)
        h = _mix(self.seed)
        self._s = np.random.default_rng([h >> 32, h & 0xFFFFFFFF])

    def f(self, a=0.0, b=1.0):
        """Uniform float in [a, b)."""
        return float(self._s.uniform(a, b))

    def i(self, a, b):
        """Uniform integer in [a, b] inclusive."""
        return int(self._s.integers(a, b + 1))

    def pick(self, seq):
        return seq[self.i(0, len(seq) - 1)]

    def wpick(self, pairs):
        """Weighted pick. pairs = [(item, weight), ...]."""
        total = sum(w for _, w in pairs)
        r = self.f(0.0, total)
        acc = 0.0
        for item, w in pairs:
            acc += w
            if r <= acc:
                return item
        return pairs[-1][0]

    def chance(self, p):
        return self.f() < p

    def normal(self, n, scale=1.0):
        """Standard normal samples - used by the sound synthesis."""
        return self._s.standard_normal(int(n)) * scale

    def sign(self):
        return 1 if self.f() < 0.5 else -1

    def jitter(self, amount):
        return self.f(-amount, amount)
