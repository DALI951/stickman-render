"""Look at a rendered frame as text.

Extracts a frame from an mp4 (or reads a png) with ffmpeg and prints it as
luminance ASCII, so the ACTUAL output can be inspected - fighters, ground,
effects, HUD, text - without an image viewer. ffmpeg + numpy only.

    python tools/frameascii.py out/42.mp4 5.2 12.0
    python tools/frameascii.py out/still.png 100
"""

import shutil
import subprocess
import sys

import numpy as np

RAMP = " .:-=+*#%@"


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def read_gray(ff, path, t=None):
    """One frame as a 2D uint8 array. t = seconds (video only)."""
    cmd = [ff, "-hide_banner", "-loglevel", "error"]
    if t is not None:
        cmd += ["-ss", f"{t:.4f}"]
    cmd += ["-i", path, "-frames:v", "1", "-f", "rawvideo",
            "-pix_fmt", "gray", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return None
    # ffmpeg gives us a flat buffer; recover the shape from the stream info
    info = subprocess.run([ff, "-hide_banner", "-i", path],
                          capture_output=True, text=True).stderr
    import re
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", info)
    if not m:
        return None
    w, h = int(m.group(1)), int(m.group(2))
    need = w * h
    buf = np.frombuffer(p.stdout, dtype=np.uint8)
    if buf.size < need:
        return None
    return buf[:need].reshape(h, w)


def to_ascii(gray, cols=78):
    h, w = gray.shape
    # terminal characters are ~2x taller than wide, so compress the rows
    rows = max(1, int(cols * (h / w) * 0.48))
    yi = (np.linspace(0, h - 1, rows)).astype(int)
    xi = (np.linspace(0, w - 1, cols)).astype(int)
    small = gray[np.ix_(yi, xi)].astype(np.float32)
    lo, hi = float(small.min()), float(small.max())
    if hi - lo < 1.0:
        return "\n".join(" " * cols for _ in range(rows)), 0.0
    n = (small - lo) / (hi - lo)
    idx = np.clip((n * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)
    lines = ["".join(RAMP[v] for v in row) for row in idx]
    return "\n".join(lines), float(gray.std())


def main():
    ff = find_ffmpeg()
    if not ff:
        print("no ffmpeg available")
        return 1
    path = sys.argv[1] if len(sys.argv) > 1 else "out/42.mp4"
    rest = sys.argv[2:]
    cols = 78

    if path.lower().endswith((".png", ".jpg", ".jpeg")):
        if rest and rest[0].isdigit():
            cols = int(rest[0])
        g = read_gray(ff, path)
        if g is None:
            print(f"cannot read {path}")
            return 1
        art, std = to_ascii(g, cols)
        print(f"\n=== {path}  {g.shape[1]}x{g.shape[0]}  std={std:.1f}")
        print(art)
        return 0

    times = [float(x) for x in rest] or [1.0, 5.0, 9.0]
    for t in times:
        g = read_gray(ff, path, t)
        if g is None:
            print(f"cannot read frame at t={t}")
            continue
        art, std = to_ascii(g, cols)
        print(f"\n=== {path}  t={t:.2f}s  {g.shape[1]}x{g.shape[0]}  std={std:.1f}")
        print(art)
    return 0


if __name__ == "__main__":
    sys.exit(main())
