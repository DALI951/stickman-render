"""Verify a rendered mp4: streams, frame count, and that frames aren't blank.

    python tools/verify.py out/42.mp4

Uses ffmpeg (which imageio-ffmpeg provides) + numpy only - no cv2, no ffprobe -
so it runs unchanged on a bare CI runner. A file that exists but is a black
rectangle is a failed render, not a pass.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

PROBE_W, PROBE_H = 96, 170          # small enough to decode fast, big enough to see


def find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def probe(ff, path):
    """ffmpeg -i prints stream info to stderr."""
    p = subprocess.run([ff, "-hide_banner", "-i", path],
                       capture_output=True, text=True)
    return p.stderr


def parse_probe(text):
    info = dict(w=0, h=0, fps=0.0, seconds=0.0, audio=False)
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", text)
    if m:
        info["w"], info["h"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
    if m:
        info["fps"] = float(m.group(1))
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if m:
        info["seconds"] = (int(m.group(1)) * 3600 + int(m.group(2)) * 60
                           + float(m.group(3)))
    info["audio"] = "Audio:" in text
    return info


def decode_gray(ff, path, w, h):
    """Decode every frame as small grayscale -> (n, h, w) uint8."""
    p = subprocess.run(
        [ff, "-hide_banner", "-loglevel", "error", "-i", path,
         "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return None
    buf = np.frombuffer(p.stdout, dtype=np.uint8)
    n = buf.size // (w * h)
    if n == 0:
        return None
    return buf[:n * w * h].reshape(n, h, w)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "out/42.mp4"
    if not os.path.isfile(path):
        print(f"FAIL: {path} does not exist")
        return 1

    ff = find_ffmpeg()
    if not ff:
        print("FAIL: no ffmpeg available")
        return 1

    info = parse_probe(probe(ff, path))
    size_mb = os.path.getsize(path) / 1048576

    print(f"file      : {path}  ({size_mb:.2f} MB)")
    print(f"resolution: {info['w']}x{info['h']}  "
          f"aspect {(info['w'] / info['h'] if info['h'] else 0):.3f}")
    print(f"fps       : {info['fps']:.2f}")
    print(f"duration  : {info['seconds']:.2f}s")
    print(f"audio     : {'yes' if info['audio'] else 'NO'}")

    fails = []
    if info["w"] == 0 or info["h"] == 0:
        fails.append("no video stream")
    if info["seconds"] < 2.0:
        fails.append(f"duration only {info['seconds']:.2f}s")
    if info["h"] and abs((info["w"] / info["h"]) - (9 / 16)) > 0.02:
        fails.append(f"aspect {info['w'] / info['h']:.3f} is not 9:16")
    if not info["audio"]:
        fails.append("no audio stream")

    frames = decode_gray(ff, path, PROBE_W, PROBE_H)
    if frames is None:
        fails.append("could not decode any frames")
    else:
        n = frames.shape[0]
        f = frames.astype(np.float32)
        stds = f.reshape(n, -1).std(axis=1)
        diffs = np.abs(np.diff(f, axis=0)).reshape(max(0, n - 1), -1).mean(axis=1)
        print(f"frames    : {n}  ({n / max(0.001, info['fps']):.2f}s)")
        print(f"frame std : min {stds.min():.1f}  max {stds.max():.1f}  "
              f"(blank would be ~0)")
        if diffs.size:
            print(f"motion    : mean {diffs.mean():.2f}  max {diffs.max():.2f}  "
                  f"(frozen would be ~0)")
        if stds.min() < 5.0:
            fails.append(f"a frame is nearly blank (std {stds.min():.1f})")
        if diffs.size == 0 or diffs.max() < 1.0:
            fails.append("video is frozen - no frame-to-frame change")

    if fails:
        print("\nFAIL:")
        for x in fails:
            print(f"  - {x}")
        return 1
    print("\nPASS: video is valid, animated and has audio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
