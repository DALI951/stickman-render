# HANDOFF.md — stickman-render

> Current state. Rewritten each session, never left stale.
> Last updated: 2026-11-11

## Done
- Full engine written and working end-to-end: `src/{rng,rig,moves,fighter,choreo,camera,fx,draw,audio,render}.py`.
- One seed → one finished 9:16 MP4 with a synthesised soundtrack. Verified by
  actually reading rendered frames, not by reasoning.
- 25 poses pass geometric invariants (`python tools/ascii.py check`).
- 11 videos rendered and verified (seed 42 full quality, seeds 1–8 batch,
  seeds 3+4 on GitHub Actions).
- Verification tooling: `tools/ascii.py` (poses/fight as ASCII + FK invariant
  checks), `tools/rigdump.py` (numeric joint readout), `tools/frameascii.py`
  (renders an actual output frame as ASCII), `tools/verify.py` (validates an
  MP4: streams, frame count, aspect, motion, audio). All four use ffmpeg+numpy
  only — no cv2 — so they run on a bare CI runner.
- Pushed to `DALI951/stickman-render` (public, commit `84b3daa`).
- **GitHub Actions verified working.** Run
  [43093367824](https://github.com/DALI951/stickman-render/actions/runs/43093367824)
  rendered seeds 3 and 4 at 720x1280 in ~1 min each, in parallel, verified them
  in-job, and uploaded both MP4s as artifacts. Downloaded and re-verified
  locally: both PASS.
- **Cross-platform determinism verified.** Seed 3 rendered locally and on the
  runner produced exactly 780 frames / 26.00 s both times; decoded pixel mean
  absolute difference 0.54/255 (pure x264 encoder variance, not engine drift).
- Fixed in this session: pose-name → pose-dict resolution crash; punch
  wind-ups had no chamber (fists started already forward, so strikes had no
  travel); BLOCK had hanging arms; KICK arms overlapped the leg; HURT arms
  pointed forward; KNOCKDOWN/GROUND were not actually horizontal; jump had no
  lift; fight spacing made fighters overlap; camera zoom clamp cropped both
  fighters off-screen; shockwave rings were oversized; fighters spawned 3.2
  units apart and got cropped for the first second; seed correlation made 4 of
  8 seeds use the same palette; flat reaction variety; outro ran past the KO
  banner; audio called `rng.standard_normal` on a wrapper that had no such
  method; the intensity curve broke on numpy arrays.
- Project contract + docs: `README.md`, `RULES.md`, `HANDOFF.md`, `AGENTS.md`,
  `requirements.txt`, `.gitignore`, `.gitattributes`, `.opencode/commands/`
  (`/battery`, `/ship`).

## In progress
- Nothing half-written.

## Next step
1. Decide the publishing loop: how many seeds per day, upload cadence, titles,
   and thumbnails. The engine is done; volume is now a scheduling problem.
2. Answer the three open questions in `RULES.md` (channel branding in-frame?,
   fixed ~20 s length?, allow committed audio samples?).
3. Optional quality pass: this is the first working version, and the poses are
   good-not-great. Worth a session of purely visual tuning now that `seer`
   is the only missing piece (see Blocked).

## Blocked
- `seer` subagent is unreachable (`ECONNREFUSED`) and this model cannot read
  images, so all visual verification goes through ASCII/pixel checks. If `seer`
  comes back, re-inspect `out/42.mp4` frames visually as a cross-check.

## Environment
- `C:\Users\Dali\Projects\stickman-render` — git repo, remote `origin`
  (`DALI951/stickman-render`, public), branch `main`.
- Python 3.14.6, Pillow 11.3.0, numpy 2.5.1, imageio-ffmpeg 0.7.0, cv2 5.0.0
  (cv2 no longer required by the tools — kept out of requirements on purpose).
- ffmpeg v7.1 lives at
  `C:\Users\Dali\AppData\Roaming\Python\Python314\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe`
  and is found automatically. It is not on PATH.
- Shell is PowerShell 5.1: `&&` is invalid; `git push` exits 1 even on success
  (check the `..` ref line); no heredocs — write commit messages to a file and
  use `git commit -F`.
- CI uses Python 3.12 on `ubuntu-latest`; the engine is version-agnostic.

## Watch-outs
- Local render cost at 540x960/`ss 1`: ~54 simulated fps, ~25 s wall for a
  23 s video. At 1080x1920/`ss 2` expect roughly 16× that — use Actions.
- `out/` is gitignored; don't be surprised it isn't in the repo.
- Audio in `audio/sfx` and `audio/music` is gitignored on purpose.
- The `--still` path and the video path share `simulate()`; a change to the
  fight logic affects both.
- `choreo.OUTRO` and the KO banner duration are coupled — changing one without
  the other leaves dead air after the KO or cuts the banner off.
