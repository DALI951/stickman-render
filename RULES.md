# RULES.md — stickman-render

> Project rules. Binding for every session, on every machine.
> Injected into the system prompt automatically (plugin `project-contract.ts`).
> **Keep this file under ~120 lines** — it is prompt budget on every request.
> Rules only — state goes in `HANDOFF.md`.
> Last reviewed: 2026-11-11

## What this project is
A code-render engine that turns a single integer seed into a finished vertical
(9:16) stickman fight short — MP4 video plus a procedurally synthesised
soundtrack. Lives at `C:\Users\Dali\Projects\stickman-render`, repo
`DALI951/stickman-render`. Purpose: Dali's viral Shorts pipeline — volume comes
from seeds, not from hand animation.

## Stack
- Python 3 (developed on 3.14.6) + Pillow + numpy. Nothing else at runtime.
- ffmpeg via `imageio_ffmpeg.get_ffmpeg_exe()`; `shutil.which("ffmpeg")` first.
  **ffmpeg is NOT on PATH on the main PC** — never assume `ffmpeg` works.
- No rendering framework, no node, no GPU, no npm. Do not add one.
- Heavy renders belong on **GitHub Actions**, never on Dali's PC.

## Commands (exact, copy-ready)
| Purpose | Command | Working dir |
|---|---|---|
| install | `pip install -r requirements.txt` | `C:\Users\Dali\Projects\stickman-render` |
| render one | `python -m src.render --seed 42 --out out/42.mp4` | same |
| render batch | `python -m src.render --seed 100 --batch 10 --outdir out` | same |
| full quality | `python -m src.render --seed 42 --out out/42.mp4 --w 1080 --h 1920 --ss 2` | same |
| still frame | `python -m src.render --seed 42 --still 6.0 --out out/still.png` | same |
| test / check | `python tools/ascii.py check` | same |
| verify output | `python tools/verify.py out/42.mp4` | same |
| look at output | `python tools/frameascii.py out/42.mp4 5.2 12.0` | same |
| ship | `.opencode/commands/ship.md` (`/ship`) | same |

## Conventions
- `python -m src.render` **must** be run from the project root (it does
  `from . import ...` and resolves `ROOT` from `__file__`).
- World space: x = right, y = UP, ground at y = 0, 1 unit = character height.
  Fighters are authored **facing right**; left-facing is mirrored at projection.
- Bone angles are **absolute** degrees, `0` = up, positive = clockwise.
- Every random decision goes through `src/rng.Rng` (seeded). **Never** import
  the stdlib `random` — one seed must always give one identical video.
- Verify with the ASCII/numeric tools, never by claiming it "should" look right.
- `tools/` holds verification and inspection helpers; `src/` holds the engine.
  Keep that split.

## Do NOT
- Never npm-install or run a heavy render locally — that's a hard rule from the
  `remotion-logo` project. Renders go to Actions.
- Never commit `out/` (gitignored). Never commit audio samples you don't have
  the rights to (`audio/sfx/*`, `audio/music/*` are gitignored on purpose).
- Never commit secrets, tokens or API keys.
- Never "fix" a visual problem by reasoning alone — render a frame and read it
  with `tools/frameascii.py`. Claims without an observed check are UNVERIFIED.
- Never delete or rewrite a pose without re-running `python tools/ascii.py check`.
- Never force-push a shared branch without telling Dali.
- Don't hand-tune a value twice in a row without re-rendering — guessing wastes
  more time than checking.

## Decisions (why, append-only)
- 2026-11-11 — **Code-render engine over Stick Nodes/Pivot** — the genre's
  bottleneck is volume, and a seed-based engine removes the per-video labour.
  Dali's coding ability is the moat in a genre full of hand animators.
- 2026-11-11 — **Director, not physics simulation** — stick figures have no
  mass, so a sim reads as floaty. The director chooses positions so strikes
  visibly connect, and effects are placed from the real limb position at the
  impact frame.
- 2026-11-11 — **Pillow + numpy, no rendering framework** — must run on a
  phone-grade machine and a bare CI runner. Zero exotic deps.
- 2026-11-11 — **Procedural audio in numpy** — a fresh clone must produce a
  finished video with sound and no asset files. Real samples override it when
  present.
- 2026-11-11 — **Supersample-then-reduce for AA** — `ImageDraw` has no
  anti-aliasing; drawing at `ss`× and box-reducing is simple and resolution
  independent.
- 2026-11-11 — **Layered drawing (scene / soft / post)** — PIL's `ImageDraw`
  overwrites alpha instead of blending it, so translucent effects must go on
  their own layer and be `alpha_composite`d.
- 2026-11-11 — **Reach derived from FK, never hand-typed** — `moves.limb_reach()`
  reads the hit pose, so the geometry can't drift out of sync with the art.
- 2026-11-11 — **Seed is mixed through SplitMix64 before seeding numpy** — raw
  consecutive seeds produced correlated first draws (4 of 8 videos came out the
  same palette). See `src/rng.py::_mix`.

## Open questions for Dali
- [ ] Do you want the videos to carry any channel branding (handle/watermark)
      baked in, or keep the frames clean and add branding at upload time?
- [ ] Target length: currently seed-derived 21–31 s. Want a fixed ~20 s for
      Shorts retention, or keep the variety?
- [ ] Should `audio/` accept committed samples (e.g. royalty-free packs), or
      stay gitignored and procedural-only?
