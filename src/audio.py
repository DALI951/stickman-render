"""Procedural sound design.

The whole soundtrack is synthesised in numpy, so a fresh clone produces a
finished video with audio and no asset files. If you drop real samples in
`audio/sfx/` (whoosh.wav, impact.wav, impact_heavy.wav, block.wav, super.wav,
ko.wav, land.wav) or a track in `audio/music/`, those are used instead.

Sound is roughly half of why these videos read as professional, so the mixing
here matters as much as the drawing.
"""

import glob
import os
import wave

import numpy as np

SR = 44100

# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------
def _n(rng, n):
    return rng.normal(n).astype(np.float32)


def _ma(x, k):
    """Moving average - a cheap lowpass that runs at C speed."""
    k = int(k)
    if k < 2 or x.size < k:
        return x.astype(np.float32)
    kern = np.ones(k, np.float32) / k
    return np.convolve(x, kern, mode="same").astype(np.float32)


def _place(out, snd, i, gain=1.0):
    if i >= out.size:
        return
    n = min(snd.size, out.size - i)
    out[i:i + n] += snd[:n] * gain


# --------------------------------------------------------------------------
# one-shots
# --------------------------------------------------------------------------
def whoosh(rng, dur=0.24):
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float32) / SR
    u = t / dur
    env = np.sin(np.pi * np.clip(u, 0.0, 1.0)) ** 1.5
    nz = _n(rng, n)
    lo = _ma(nz, 110)
    hi = _ma(nz, 7)
    s = (lo * (1.0 - u) + hi * u) * env
    return (s * 0.75).astype(np.float32)


def impact(rng, strength=1.0, heavy=False):
    dur = 0.42 if heavy else 0.30
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float32) / SR
    crack = _ma(_n(rng, n), 4) * np.exp(-t * (22.0 if heavy else 32.0))
    f0 = 62.0 if heavy else 88.0
    body = np.sin(2 * np.pi * f0 * t) * np.exp(-t * (11.0 if heavy else 17.0))
    click = np.exp(-t * 380.0) * 0.55
    s = crack * 0.62 + body * (1.0 if heavy else 0.8) + click * 0.45
    return (s * (0.85 if heavy else 0.72) * strength).astype(np.float32)


def block_sfx(rng):
    n = int(SR * 0.26)
    t = np.arange(n, dtype=np.float32) / SR
    a = np.sin(2 * np.pi * 1720.0 * t) * np.exp(-t * 26.0)
    b = np.sin(2 * np.pi * 2610.0 * t) * np.exp(-t * 34.0)
    nz = _ma(_n(rng, n), 3) * np.exp(-t * 90.0)
    return ((a * 0.5 + b * 0.32 + nz * 0.45) * 0.62).astype(np.float32)


def super_sfx(rng):
    """Riser into a huge boom, plus a decaying tail."""
    pre = 0.42
    dur = 1.55
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float32) / SR
    rise = np.clip(t / pre, 0.0, 1.0) ** 2.2
    riser = _ma(_n(rng, n), 5) * rise * np.exp(-np.clip(t - pre, 0.0, None) * 8.0)
    after = np.clip(t - pre, 0.0, None)
    boom = np.sin(2 * np.pi * 44.0 * after) * np.exp(-after * 2.9)
    boom2 = np.sin(2 * np.pi * 67.0 * after) * np.exp(-after * 4.6) * 0.5
    sub = np.sin(2 * np.pi * 27.0 * after) * np.exp(-after * 2.0) * 0.8
    tail = _ma(_n(rng, n), 46) * np.exp(-after * 2.0) * 0.30
    s = riser * 0.45 + boom * 1.0 + boom2 * 0.45 + sub * 0.7 + tail
    return (s * 0.8).astype(np.float32)


def land_sfx(rng):
    n = int(SR * 0.30)
    t = np.arange(n, dtype=np.float32) / SR
    body = np.sin(2 * np.pi * 70.0 * t) * np.exp(-t * 20.0)
    nz = _ma(_n(rng, n), 12) * np.exp(-t * 45.0)
    return ((body * 0.7 + nz * 0.4) * 0.45).astype(np.float32)


def step_sfx(rng):
    n = int(SR * 0.11)
    t = np.arange(n, dtype=np.float32) / SR
    nz = _ma(_n(rng, n), 16) * np.exp(-t * 70.0)
    body = np.sin(2 * np.pi * 120.0 * t) * np.exp(-t * 60.0)
    return ((nz * 0.35 + body * 0.30) * 0.30).astype(np.float32)


# --------------------------------------------------------------------------
# music bed - a simple fight pulse, no assets required
# --------------------------------------------------------------------------
def _kick():
    n = int(SR * 0.30)
    t = np.arange(n, dtype=np.float32) / SR
    f = 120.0 * np.exp(-t * 26.0) + 44.0
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 9.0) * 0.95).astype(np.float32)


def _hat(rng, open_=False):
    n = int(SR * (0.16 if open_ else 0.06))
    t = np.arange(n, dtype=np.float32) / SR
    nz = _n(rng, n)
    hi = nz - _ma(nz, 6)
    return (hi * np.exp(-t * (24.0 if open_ else 70.0)) * 0.30).astype(np.float32)


def _snare(rng):
    n = int(SR * 0.22)
    t = np.arange(n, dtype=np.float32) / SR
    nz = _n(rng, n)
    mid = _ma(nz, 5)
    tone = np.sin(2 * np.pi * 190.0 * t) * np.exp(-t * 26.0) * 0.5
    return ((mid * np.exp(-t * 22.0) * 0.55 + tone) * 0.65).astype(np.float32)


def music_bed(rng, duration, intensity):
    """intensity(t) -> 0..1 drives how hard the bed hits."""
    n = int(SR * duration) + SR
    out = np.zeros(n, np.float32)
    bpm = 88.0
    spb = 60.0 / bpm
    k_kick = _kick()
    k_snare = _snare(rng)
    k_hat = _hat(rng)
    k_ohat = _hat(rng, True)

    beat = 0
    while beat * spb < duration + 0.5:
        tt = beat * spb
        i = int(tt * SR)
        amp = 0.45 + 0.55 * intensity(tt)
        out_i = out
        if beat % 2 == 0:
            _place(out_i, k_kick, i, 0.55 * amp)
        else:
            _place(out_i, k_snare, i, 0.30 * amp)
        _place(out_i, k_hat, i + int(spb * 0.5 * SR), 0.55)
        if beat % 4 == 3:
            _place(out_i, k_ohat, i + int(spb * 0.75 * SR), 0.45)
        beat += 1

    # low drone that swells with intensity
    t = np.arange(n, dtype=np.float32) / SR
    swell = np.clip(intensity(t), 0.0, 1.0)
    drone = (np.sin(2 * np.pi * 55.0 * t) * 0.5
             + np.sin(2 * np.pi * 82.5 * t) * 0.25)
    out += (drone * swell * 0.16).astype(np.float32)
    return out[:int(SR * duration)]


# --------------------------------------------------------------------------
# sample loading
# --------------------------------------------------------------------------
def _load_audio(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        with wave.open(path, "rb") as w:
            ch = w.getnchannels()
            sw = w.getsampwidth()
            fr = w.getframerate()
            raw = w.readframes(w.getnframes())
        dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(sw)
        if dtype is None:
            return None
        data = np.frombuffer(raw, dtype=dtype).astype(np.float32)
        if sw == 1:
            data = (data - 128.0) / 128.0
        else:
            data /= float(2 ** (8 * sw - 1))
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1)
    else:
        try:
            import imageio.v3 as iio
            data = np.asarray(iio.imread(path), dtype=np.float32)
            if data.ndim > 1:
                data = data.mean(axis=1)
            if data.size and np.abs(data).max() > 2.0:
                data = data / float(2 ** 15)
        except Exception:
            return None
    if data.size == 0:
        return None
    return data.astype(np.float32)


def _pool(directory, names):
    """Return {name: samples} for any real samples found."""
    out = {}
    if not os.path.isdir(directory):
        return out
    files = glob.glob(os.path.join(directory, "*"))
    for name in names:
        for f in files:
            base = os.path.splitext(os.path.basename(f))[0].lower()
            if base == name:
                s = _load_audio(f)
                if s is not None:
                    out[name] = s
                    break
    return out


# --------------------------------------------------------------------------
# build the full track
# --------------------------------------------------------------------------
def build_track(rng, duration, events, root, intensity):
    """events = [(t_seconds, kind, strength)] -> mono float32 track."""
    n = int(SR * (duration + 0.6))
    out = np.zeros(n, np.float32)

    sfx_dir = os.path.join(root, "audio", "sfx")
    music_dir = os.path.join(root, "audio", "music")
    pool = _pool(sfx_dir, ["whoosh", "impact", "impact_heavy", "block",
                           "super", "ko", "land", "step"])

    def synth(kind, strength):
        if kind == "whoosh":
            return whoosh(rng, 0.20 + 0.10 * strength)
        if kind == "impact":
            return impact(rng, strength)
        if kind == "impact_heavy":
            return impact(rng, strength, heavy=True)
        if kind == "block":
            return block_sfx(rng)
        if kind == "super":
            return super_sfx(rng)
        if kind == "ko":
            return super_sfx(rng) * 1.0
        if kind == "land":
            return land_sfx(rng)
        if kind == "step":
            return step_sfx(rng)
        return None

    def get(kind, strength):
        s = pool.get(kind)
        if s is not None:
            return s * (0.55 + 0.55 * strength)
        return synth(kind, strength)

    for t, kind, strength in events:
        s = get(kind, strength)
        if s is None:
            continue
        _place(out, s, int(t * SR), 1.0)

    # music
    tracks = []
    for ext in ("*.wav", "*.mp3", "*.ogg", "*.flac", "*.m4a"):
        tracks += glob.glob(os.path.join(music_dir, ext))
    tracks.sort()
    if tracks:
        bed = _load_audio(tracks[0])
        if bed is not None and bed.size > SR:
            reps = int(np.ceil((n + SR) / bed.size))
            bed = np.tile(bed, reps)[:n]
            # fade out
            fade = min(int(SR * 1.2), n)
            bed[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
            out += bed * 0.55
    else:
        out += music_bed(rng, duration + 0.6, intensity) * 0.42

    # gentle limiter then normalise
    peak = float(np.max(np.abs(out))) or 1.0
    out = np.tanh(out / max(0.55, peak) * 1.15) * 0.92
    return out.astype(np.float32)


def write_wav(path, mono):
    data = np.clip(mono, -1.0, 1.0)
    pcm = (data * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
