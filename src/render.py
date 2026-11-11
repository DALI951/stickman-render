"""CLI + simulation loop + encoding.

    python -m src.render --seed 42 --out out/42.mp4
    python -m src.render --seed 42 --still 2.4 --out out/still.png
    python -m src.render --batch 6 --outdir out

Renders a PNG sequence into a temp folder, synthesises the soundtrack from the
recorded event timeline, then hands both to ffmpeg.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw
import numpy as np

from . import audio as audio_mod
from . import draw
from .camera import Camera
from .choreo import Director
from .fighter import Fighter
from .fx import Fx
from .moves import MOVE
from .rng import Rng

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for p in (os.path.join(ROOT, "tools", "ffmpeg.exe"),):
        if os.path.isfile(p):
            return p
    raise RuntimeError("ffmpeg not found on PATH and imageio_ffmpeg missing")


# --------------------------------------------------------------------------
# one frame of drawing
# --------------------------------------------------------------------------
def draw_frame(a, b, fx, cam, pal, w, h, ss, vmask, extra=None):
    proj = cam.projector(ss)
    scene = draw.background(w * ss, h * ss, pal)
    d = ImageDraw.Draw(scene)

    draw.draw_ground(d, proj, pal, ss)

    if fx.burst > 0.02 and extra is not None:
        draw.draw_burst(d, proj, pal, fx.burst, extra)

    draw.draw_fighter(d, a, proj, pal, pal["p1"], ss)
    draw.draw_fighter(d, b, proj, pal, pal["p2"], ss)
    draw.draw_fx_solid(d, fx, proj, pal, ss)

    if fx.parts:
        soft = Image.new("RGBA", scene.size, (0, 0, 0, 0))
        draw.draw_fx_soft(soft, proj, fx, ss)
        scene = Image.alpha_composite(scene, soft)
        d = ImageDraw.Draw(scene)

    if fx.popups:
        draw.draw_popups(d, fx, proj, ss, pal)

    if ss > 1:
        scene = scene.reduce(ss)

    if fx.banners:
        draw.draw_banners(scene, fx, pal, ss)
    draw.draw_hud(scene, [a, b], pal, ss, 0)

    return draw.post(scene, cam, vmask)


# --------------------------------------------------------------------------
# the simulation
# --------------------------------------------------------------------------
def simulate(seed, fps, duration, w, h, ss, want_frames=None, log=print):
    """Run the fight. If want_frames is a set of frame indices, only those are
    rasterised (used for --still). Returns (frames_dict, events, info)."""
    rng = Rng(seed)
    drng = Rng(seed * 7919 + 13)
    director = Director(drng, fps, duration)
    meta = director.meta
    pal = draw.PALETTES[meta["palette"]]

    frng = Rng(seed * 104729 + 7)
    cam = Camera(w, h, frng)
    fx = Fx(frng)
    vmask = draw.vignette_mask(w, h)

    # spawn the fighters already at their first beat marks - walking in from
    # off-screen just crops them out of frame for the first second
    first = director.beats[0]
    a = Fighter(first["ax"], 1, "P1", hp=100.0)
    b = Fighter(first["dx"], -1, "P2", hp=100.0)
    fighters = [a, b]

    a.set_target(first["ax"])
    b.set_target(first["dx"])

    beats = director.beats
    impacts = director.impacts
    bi = 0
    ii = 0
    ko_done = False
    hook_done = False

    dt_real = 1.0 / fps
    max_frames = int(duration * fps * 1.45)
    t = 0.0
    frames = 0
    out = {}
    events = []
    last_phase = [a.phase, b.phase]
    busy_states = ("attack", "react", "down", "getup")

    def intensity(tt):
        u = tt / duration
        if u < 0.10:
            return 0.12
        return min(1.0, 0.34 + 0.92 * u)

    t0 = time.time()
    while t < duration and frames < max_frames:
        dt = dt_real * cam.slowmo
        t += dt
        frames += 1
        now = frames / fps

        # ---- hook title (retention: something to read in the first second) --
        if not hook_done and t >= 0.10:
            hook_done = True
            fx.banner(meta.get("hook", "FIGHT"), pal["accent"], dur=0.95)

        # ---- issue beats -------------------------------------------------
        while bi < len(beats) and t >= beats[bi]["t0"]:
            bt = beats[bi]
            atk = fighters[bt["atk"]]
            dfn = fighters[bt["dfn"]]
            atk.attack(bt["move"], facing=bt["facing"])
            atk.set_target(bt["ax"])
            dfn.set_target(bt["dx"])
            events.append((now, "whoosh", 0.42 + 0.14 * bt["tier"]))
            bi += 1

        # ---- impacts -----------------------------------------------------
        while ii < len(impacts) and t >= impacts[ii]["t"]:
            ev = impacts[ii]
            atk = fighters[ev["atk"]]
            dfn = fighters[ev["dfn"]]
            mv = MOVE[ev["move"]]
            pt = atk.hit_point(mv["limb"])
            acc = pal["p2"] if ev["atk"] == 0 else pal["p1"]

            if ev["connect"] and ev["react"] == "block":
                fx.block_spark(pt[0], pt[1], 1.1, pal["p2"])
                fx.impact(pt[0], pt[1], ev["strength"] * 0.6, acc,
                          dirn=atk.facing)
                dfn.react("block")
                dfn.hp = max(0.0, dfn.hp - ev["dmg"])
                if ev["dmg"]:
                    fx.popup(pt[0], pt[1] + 0.12, str(ev["dmg"]), acc, 0.040)
                cam.kick(0.40)
                events.append((now, "block", 0.70))
            elif ev["connect"]:
                fx.impact(pt[0], pt[1], ev["strength"], acc, dirn=atk.facing)
                dfn.react(ev["react"])
                dfn.hp = max(0.0, dfn.hp - ev["dmg"])
                fx.popup(pt[0], pt[1] + 0.12, str(ev["dmg"]), acc, 0.048)
                if ev["big"]:
                    cam.kick(2.1, roll=2.4)
                    cam.hit_flash(0.66)
                    cam.chroma_pulse(1.1)
                    cam.slow(0.28)
                    fx.set_burst(1.0)
                    events.append((now, "super", 1.0))
                else:
                    kind = "impact_heavy" if ev["strength"] > 0.95 else "impact"
                    cam.kick(0.75 + ev["strength"] * 1.05,
                             roll=0.5 + 0.4 * ev["strength"])
                    if ev["strength"] > 0.95:
                        cam.hit_flash(0.26)
                    events.append((now, kind, ev["strength"]))
            else:
                if ev["react"] == "block":
                    fx.block_spark(pt[0], pt[1], 0.85, pal["p2"])
                    cam.kick(0.42)
                    events.append((now, "block", 0.55))
                else:
                    events.append((now, "whoosh", 0.30))
                dfn.react(ev["react"])
            if "dx2" in ev:
                dfn.set_target(ev["dx2"])
            ii += 1

        # ---- fighters ----------------------------------------------------
        for f in fighters:
            f.update(dt)

        # footsteps
        for i, f in enumerate(fighters):
            if f.state in busy_states:
                last_phase[i] = f.phase
                continue
            ph = f.phase
            if (last_phase[i] < 0.5 <= ph) or (last_phase[i] > ph and ph < 0.5):
                events.append((now, "step", 0.25))
            last_phase[i] = ph

        # ---- KO payoff ---------------------------------------------------
        if not ko_done and t >= meta["ko_t"]:
            ko_done = True
            winner = fighters[meta["winner"]]
            loser = fighters[meta["loser"]]
            loser.go_down()
            winner.celebrate()
            winner.set_target(winner.x)
            loser.set_target(loser.x)
            fx.dust(loser.x, 0.02, 26, 0.30, dirn=-loser.facing, power=1.5)
            fx.banner(meta["title"], pal["accent"], dur=1.4,
                      sub=f"{winner.name} WINS")
            cam.kick(2.4, roll=2.6)
            cam.hit_flash(0.7)
            cam.slow(0.34)
            events.append((now, "ko", 1.0))

        fx.update(dt)
        cam.update(dt, a, b, dt_real=dt_real)

        # ---- raster ------------------------------------------------------
        if want_frames is None or frames in want_frames:
            img = draw_frame(a, b, fx, cam, pal, w, h, ss, vmask, frng)
            out[frames] = img

        if log and frames % 60 == 0:
            log(f"  frame {frames:5d}  t={t:6.2f}s  "
                f"zoom={cam.zoom:.2f}  parts={len(fx.parts)}")

    elapsed = time.time() - t0
    info = dict(seed=seed, frames=frames, duration=frames / fps,
                meta=meta, palette=pal["name"], elapsed=elapsed,
                events=events)
    if log:
        log(f"  simulated {frames} frames in {elapsed:.1f}s "
            f"({frames / max(0.001, elapsed):.1f} fps)")
    return out, events, info


# --------------------------------------------------------------------------
# encode
# --------------------------------------------------------------------------
def encode(frames_dir, pattern, fps, out_path, wav=None):
    ff = find_ffmpeg()
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error",
           "-framerate", str(fps), "-i", os.path.join(frames_dir, pattern)]
    if wav:
        cmd += ["-i", wav]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if wav:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [out_path]
    subprocess.run(cmd, check=True)


def render_one(seed, out_path, fps, w, h, duration, ss, no_audio=False,
               keep_frames=False, log=print):
    log(f"[seed {seed}] {w}x{h} @ {fps}fps  ss={ss}  target {duration:.1f}s")
    out, events, info = simulate(seed, fps, duration, w, h, ss, log=log)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="stickman_")
    try:
        for i in sorted(out):
            out[i].save(os.path.join(tmp, f"f_{i:05d}.png"), compress_level=1)

        wav = None
        if not no_audio:
            arng = Rng(seed * 31 + 5)
            track = audio_mod.build_track(arng, info["duration"], events, ROOT,
                                          _intensity_fn(info["duration"]))
            wav = os.path.join(tmp, "track.wav")
            audio_mod.write_wav(wav, track)
            log(f"  audio: {track.size / audio_mod.SR:.2f}s "
                f"{len(events)} cues")

        encode(tmp, "f_%05d.png", fps, out_path, wav)

        if keep_frames:
            keep = os.path.join(os.path.dirname(os.path.abspath(out_path)),
                                f"frames_{seed}")
            if os.path.isdir(keep):
                shutil.rmtree(keep)
            shutil.move(tmp, keep)
            tmp = None
            log(f"  frames kept in {keep}")
    finally:
        if tmp and os.path.isdir(tmp):
            shutil.rmtree(tmp, ignore_errors=True)

    size = os.path.getsize(out_path) if os.path.isfile(out_path) else 0
    log(f"  -> {out_path}  ({size / 1048576:.2f} MB, "
        f"{info['duration']:.2f}s, palette {info['palette']})")
    return info


def _intensity_fn(duration):
    """Music/energy curve. Array-safe: audio.py calls it with a sample array."""
    def f(tt):
        u = np.asarray(tt, dtype=np.float32) / float(duration)
        return np.where(u < 0.10, 0.12,
                        np.minimum(1.0, 0.34 + 0.92 * u)).astype(np.float32)
    return f


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser("stickman-render")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=None, help="output mp4 (single seed)")
    ap.add_argument("--outdir", default="out", help="output dir for --batch")
    ap.add_argument("--batch", type=int, default=0, help="render N seeds")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--dur", type=float, default=0.0, help="0 = pick from seed")
    ap.add_argument("--ss", type=int, default=2, help="supersample factor")
    ap.add_argument("--still", type=float, default=None,
                    help="render one PNG at this sim time instead of a video")
    ap.add_argument("--still-at", default="",
                    help="comma list of extra sim times for stills")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args(argv)

    if args.still is not None or args.still_at:
        times = []
        if args.still is not None:
            times.append(args.still)
        times += [float(x) for x in args.still_at.split(",") if x.strip()]
        return _stills(args, times)

    if args.batch:
        os.makedirs(args.outdir, exist_ok=True)
        seeds = [args.seed + i for i in range(args.batch)]
        for s in seeds:
            render_one(s, os.path.join(args.outdir, f"{s}.mp4"), args.fps,
                       args.w, args.h, _duration_for(s, args.dur), args.ss,
                       args.no_audio, args.keep_frames)
        print(f"\ndone: {len(seeds)} videos in {args.outdir}")
        return 0

    out = args.out or os.path.join(args.outdir, f"{args.seed}.mp4")
    render_one(args.seed, out, args.fps, args.w, args.h,
               _duration_for(args.seed, args.dur), args.ss,
               args.no_audio, args.keep_frames)
    return 0


def _duration_for(seed, explicit):
    if explicit and explicit > 0:
        return float(explicit)
    r = Rng(seed * 977 + 41)
    return r.f(21.0, 31.0)


def _stills(args, times):
    fps = args.fps
    dur = _duration_for(args.seed, args.dur)
    want = {}
    for tt in times:
        want[max(1, int(round(tt * fps)))] = tt
    frames, events, info = simulate(args.seed, fps, dur, args.w, args.h,
                                    args.ss, want_frames=set(want), log=print)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    for i in sorted(frames):
        base, ext = os.path.splitext(args.out)
        path = f"{base}_{i:05d}.png" if len(frames) > 1 else args.out
        frames[i].save(path)
        print(f"  wrote {path}  (frame {i}, t={want[i]:.2f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
