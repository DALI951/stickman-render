---
description: stickman-render battery — the real checks for this project. Green means it renders, verifies and stays deterministic.
agent: absolute
---

Run this project's actual checks, in order, from
`C:\Users\Dali\Projects\stickman-render`. Report PASS/FAIL per step and stop at
the first red.

1. **Deps present** — `python -c "import PIL, numpy, imageio_ffmpeg; print(PIL.__version__, numpy.__version__)"`
2. **Import sanity** — `python -c "import sys; sys.path.insert(0,'.'); import src.render, src.choreo, src.audio; print('imports ok')"`
   (catches syntax errors in modules the other checks don't touch)
3. **Rig geometry** — `python tools/ascii.py check`
   Must print `all N poses pass geometric invariants`.
4. **Fight geometry** — `python tools/ascii.py fight 42 1.4,3.0,12.0`
   Must show two figures per frame and `connect=True` lines where the limb
   coordinate reaches the defender.
5. **Determinism** — render the same seed twice at low res and compare:
   ```
   python -m src.render --seed 7 --out out/_d1.mp4 --w 270 --h 480 --ss 1 --dur 8 --no-audio
   python -m src.render --seed 7 --out out/_d2.mp4 --w 270 --h 480 --ss 1 --dur 8 --no-audio
   ```
   Then compare frame data with `python tools/verify.py` on both and check the
   decoded frame hashes match. Same seed must give the same video.
6. **End-to-end render + verify** —
   ```
   python -m src.render --seed 42 --out out/_battery.mp4 --w 360 --h 640 --ss 1 --dur 10
   python tools/verify.py out/_battery.mp4
   ```
   Must print `PASS: video is valid, animated and has audio`.
7. **Clean up** the `out/_*` scratch files.

If all green: say so in one line and suggest `/ship`.
If anything is red: report the exact failing command and the output, and stop.
