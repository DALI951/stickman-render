# stickman-render

One seed in, one finished vertical stickman fight short out — video **and**
soundtrack — generated entirely in code. No animation software, no asset files,
no GPU.

```
python -m src.render --seed 42 --out out/42.mp4
```

That command writes a 9:16 MP4, 22–31 s long, 1080x1920, with a procedurally
synthesised fight soundtrack. The same seed always produces the exact same
video.

## Why this exists

Stickman fight Shorts are one of the highest-volume, lowest-barrier viral
formats. Almost everyone making them animates by hand in Stick Nodes or Pivot,
which caps them at a few videos a week. This renders them from a seed, so the
volume ceiling is your CPU and your imagination — and each video gets its own
palette, its own fight, its own camera work.

## How it works

The engine is a **director, not a physics simulation**. A physics sim looks
fake here because stick figures have no mass and no recovery time; instead the
director picks positions so that strikes *visibly connect*, then reads the real
limb position at the impact frame to place the effects.

```
seed
 └─ rng.Rng              one seeded stream per subsystem (fight, camera, fx, audio)
     ├─ rig.py           proportions, forward kinematics, 25-pose library
     ├─ moves.py         attack table; reach is DERIVED from the hit pose via FK
     ├─ choreo.py        Director: 4-phase arc (establish → reversal → escalate → KO)
     ├─ fighter.py       state machine; movement toward target_x is the only motion
     ├─ camera.py        auto-framing + impact punch-in, shake, roll, slow-motion
     ├─ fx.py            sparks, shockwave rings, slash lines, dust, popups, banners
     ├─ draw.py          rasteriser: 6 palettes, stickman strokes, post-processing
     ├─ audio.py         procedural SFX + music bed, all synthesised in numpy
     └─ render.py        CLI, frame loop, PNG sequence, ffmpeg encode
```

Key design choices:

- **Anti-aliasing comes from supersampling.** The frame is drawn at `ss`×
  resolution and box-reduced at the end. Simple and resolution-independent.
- **Layered drawing.** PIL's `ImageDraw` *overwrites* alpha instead of blending
  it, so translucent effects go on their own layer and get `alpha_composite`d.
- **Absolute bone angles.** `0` = up, positive = clockwise. Blending two poses
  is a plain per-key lerp — no quaternion maths, no gimbal surprises.
- **`plant()`** snaps a pose onto the ground, so feet never float no matter how
  the pose was authored.
- **Procedural audio.** Whooshes, impacts, blocks, the KO boom and the music
  bed are all synthesised, so a fresh clone produces a finished video with
  sound and zero asset files. Drop real samples in `audio/sfx/` to override.

## Install

```bash
pip install -r requirements.txt
```

`imageio-ffmpeg` ships a static ffmpeg binary, so you do not need ffmpeg on
your PATH.

## Use

```bash
# one video, seed picks duration + palette + the whole fight
python -m src.render --seed 42 --out out/42.mp4

# a batch of consecutive seeds
python -m src.render --seed 100 --batch 10 --outdir out

# full quality
python -m src.render --seed 42 --out out/42.mp4 --w 1080 --h 1920 --ss 2

# a single still frame instead of a video (fast iteration)
python -m src.render --seed 42 --still 6.0 --out out/still.png
```

| Flag | Default | Meaning |
|---|---|---|
| `--seed` | 1 | Everything derives from this. Same seed = same video. |
| `--out` | `out/<seed>.mp4` | Output file |
| `--batch N` | 0 | Render N consecutive seeds |
| `--w` / `--h` | 1080 / 1920 | Resolution (9:16) |
| `--fps` | 30 | Frames per second |
| `--dur` | 0 | Force a duration; 0 = derive from the seed (21–31 s) |
| `--ss` | 2 | Supersample factor — this is the anti-aliasing |
| `--still T` | — | Render one PNG at sim time T instead of a video |
| `--no-audio` | off | Skip the soundtrack |
| `--keep-frames` | off | Keep the PNG sequence |

## Verify

Nothing here is claimed to work because it "should". These check it:

```bash
python tools/ascii.py check        # 25 poses vs geometric invariants (FK lengths, feet on ground)
python tools/ascii.py poses        # render poses as ASCII art
python tools/ascii.py fight 42 1.4,3.0,12.0   # ASCII preview of the whole fight
python tools/rigdump.py jab_wind jab_hit      # numeric joint readout
python tools/frameascii.py out/42.mp4 5.2     # look at the ACTUAL rendered output
python tools/verify.py out/42.mp4             # streams, frame count, motion, audio
```

`tools/verify.py` is the one that matters before shipping: it fails a render
that is blank, frozen, the wrong aspect, or missing audio. A file that exists
is not a file that worked.

## Palettes

Six, picked per seed, so no two videos look like the same channel:

`noir` (white vs red) · `ink` (white vs cyan) · `ember` (cream vs orange) ·
`toxic` (mint vs green) · `vhs` (lilac vs purple) · `paper` (ink on newsprint)

## Custom sound

Drop samples in `audio/sfx/` named `whoosh`, `impact`, `impact_heavy`, `block`,
`super`, `ko`, `land`, `step` (`.wav`/`.mp3`/`.ogg`/`.flac`/`.m4a`), and a track
in `audio/music/`. Anything present is used; anything missing is synthesised.
Audio in these folders is gitignored on purpose — don't commit samples you
don't have the rights to.

## Rendering at scale

`.github/workflows/render.yml` renders a list of seeds on GitHub's runners, in
parallel, one job per seed, and uploads each MP4 as an artifact. Your machine
does nothing. Trigger it from the Actions tab (**Render** → *Run workflow*) and
pass the seeds you want.

## Tuning

- **Poses / proportions** → `src/rig.py` (most tuning happens here)
- **Attacks, damage, reach, hit windows** → `src/moves.py`
- **Fight structure, who wins, spacing, escalation** → `src/choreo.py`
- **Camera framing, punch-in, shake** → `src/camera.py`
- **Effects** → `src/fx.py`
- **Colours, post-processing** → `src/draw.py`
- **Sound** → `src/audio.py`

After changing a pose, run `python tools/ascii.py check` — it catches
impossible geometry (wrong bone lengths, floating feet) before you waste a
render on it.
