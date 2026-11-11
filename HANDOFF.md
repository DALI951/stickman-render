# HANDOFF.md — stickman-render

> Current state. Rewritten each session, never left stale.
> Last updated: 2026-11-11

## Done
- Full engine written and working end-to-end: `src/{rng,rig,moves,fighter,choreo,camera,fx,draw,audio,render}.py`.
- One seed → one finished 9:16 MP4 with a synthesised soundtrack. Verified by
  actually reading rendered frames, not by reasoning.
- 25 poses pass geometric invariants (`python tools/ascii.py check`).
- 9 videos rendered and verified (seed 42 full quality, seeds 1–8 batch).
- Verification tooling: `tools/ascii.py` (poses/fight as ASCII + FK invariant
  checks), `tools/rigdump.py` (numeric joint readout), `tools/frameascii.py`
  (renders an actual output frame as ASCII), `tools/verify.py` (validates an
  MP4: streams, frame count, aspect, motion, audio).
- Fixed in this session: pose-name → pose-dict resolution crash; punch
  wind-ups had no chamber (fists started already forward, so strikes had no
  travel); BLOCK had hanging arms; KICK arms overlapped the leg; HURT arms
  pointed forward; KNOCKDOWN/GROUND were not actually horizontal; jump had no
  lift; fight spacing made fighters overlap; camera zoom clamp cropped both
  fighters off-screen; shockwave rings were oversized; fighters spawned 3.2
  units apart and got cropped for the first second; seed correlation made 4 of
  8 seeds use the same palette; flat reaction variety; outro ran past the KO
  banner.
- Project contract + docs: `README.md`, `RULES.md`, `HANDOFF.md`, `AGENTS.md`,
  `requirements.txt`, `.gitignore`.
- `.github/workflows/render.yml` — parallel per-seed rendering on GitHub
  runners, MP4s uploaded as artifacts. **Not yet executed on GitHub.**

## In progress
- Nothing half-written.

## Next step
1. `git init`, first commit, `gh repo create DALI951/stickman-render`, push.
2. Trigger the Actions workflow once and confirm it produces MP4s
   (the workflow is written but has never run — treat it as UNVERIFIED).
3. Then: decide the publishing loop (how many seeds per day, upload cadence,
   titles/thumbnails), and whether to bake channel branding into the frames.

## Blocked
- `seer` subagent is unreachable (`ECONNREFUSED`) and this model cannot read
  images, so all visual verification goes through ASCII/pixel checks. If `seer`
  comes back, re-inspect `out/42.mp4` frames visually as a cross-check.

## Environment
- `C:\Users\Dali\Projects\stickman-render` — not yet a git repo.
- Python 3.14.6, Pillow 11.3.0, numpy 2.5.1, imageio-ffmpeg 0.7.0, cv2 5.0.0.
- ffmpeg v7.1 lives at
  `C:\Users\Dali\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`
  and is found automatically. It is not on PATH.
- Shell is PowerShell 5.1: `&&` is invalid; `git push` exits 1 even on success
  (check the `..` ref line).

## Watch-outs
- Local render cost at 540x960/`ss 1`: ~54 simulated fps, ~25 s wall for a
  23 s video. At 1080x1920/`ss 2` expect roughly 16× that — use Actions.
- `out/` is gitignored; don't be surprised it isn't in the repo.
- Audio in `audio/sfx` and `audio/music` is gitignored on purpose.
- The `--still` path and the video path share `simulate()`; a change to the
  fight logic affects both.
- `choreo.OUTRO` and the KO banner duration are coupled — changing one without
  the other leaves dead air after the KO or cuts the banner off.
