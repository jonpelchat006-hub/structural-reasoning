# Camera 5 — the toolchain layer holds, the effort layer is refuted

*2026-07-28. Five files, no matched pairs, no labels given beyond "I edited a few and a couple were
made by someone else." The container layer read all five correctly with zero pixel analysis. The two
hand-drawn edits then supplied the human control arm that `FOLDING_EFFORT_BUDGET` said was the highest-
value data outstanding — and **it killed level 4 as formulated**, exactly at the pre-registered kill
condition.*

---

## 1. What the container layer said, before any pixels were read

| file | verdict | evidence |
|---|---|---|
| `20250519_144256.jpg` | **rewritten-after-capture** | thumbnail IFD stripped; byte order MM not II |
| `20250814_203232.jpg` | **rewritten-after-capture** | thumbnail IFD stripped; byte order MM not II |
| `Screenshot_…_YouTube.jpg` | **no-provenance** | EXIF present, no device asserted; `Software=Android UP1A.231005.007.S918WVLS6CYB3` — the Android **screenshot** writer, not the camera |
| `20250605_162103.png` | **not a capture** | PNG, RGBA, 3714×1903. No phone camera writes PNG. The alpha channel and irregular black border are a **panorama stitch** boundary |
| `RDT_20251223_….jpg` | **not a capture** | **the file is WEBP, not JPEG — the extension lies.** 640×433, 27 KB, `RDT_` prefix = Reddit app download |

Five for five, in milliseconds, on structure alone. Both of Jonathan's edits were caught by the same
two-part signature that caught every previous edit; both "made by someone else" files were separated
from captures without any need to judge their content — which is fortunate, because **both are human
art, not AI**: an ink/marker drawing of two men, and a screenshot of a painted animation. Those are
precisely the false-positive trap for a content-based detector, and the container layer never had to
form an opinion about them.

Two container facts worth keeping:

- **Extension does not imply format.** A `.jpg` that is really WEBP is a one-line check and it is a
  provenance fact in its own right (it means an app re-containerised the file on download).
- **PNG from a phone means processing.** No capture path writes PNG; RGBA means compositing.

## 2. The human arm — and it refutes level 4

Two frames carry **hand-drawn strokes** — a green line over a photo of two cats, a blue scribble over a
landscape — made on a phone with a finger. This is the real tool grammar executed by an actual hand,
which the earlier synthetic controls could only approximate.

### Run 1: pre-registration 1 failed

`FOLDING_EFFORT_BUDGET` predicted a hand stroke would land **below** the machine masks' range
(454–5302 boundary vertices @2 px). The green line landed at 25. **The blue scribble landed at 1280 —
inside the machine range.**

Part of that was a bug: the chroma segmentation used saturation > 90, which also captured the hazy blue
city skyline along the horizon. The mask was 24% of frame across 15 components, most of it landscape.
Repaired at s > 210 (the horizon's 99th-percentile saturation is 170; the ink's median is 230).

But part of it was the measure, and that part is not fixable. **A thin stroke's boundary runs up one
side and back down the other, so boundary vertices double-count and scale with stroke LENGTH, not with
deliberate placements.** The blue scribble was perhaps three seconds of continuous motion. Calling it
"1280 deliberate placements" is false. Vertex count answers *how complex is this outline*, not *how
much work was this*.

### Run 2: the replacement measure also failed

The tool grammar's real constraint is that **a brush is a swept disc** — one width, set once. So
measure width directly: distance transform → medial axis → coefficient of variation of the half-width.
Pre-registered: hand low CV, machine high CV, kill condition if they overlap.

| | width CV | vertices @2 px |
|---|---|---|
| synthetic grammar (code) | 0.005 – 0.007 | 4 – 62 |
| **HUMAN HAND (n=2)** | **0.324 – 0.602** | 25 – 683 |
| MACHINE MASK (n=22) | 0.193 – 3.706 | 444 – 4671 |

**They overlap completely.** Only 10 of 22 machine masks exceed both hand strokes. The kill condition
fired.

### The excuse, tested and refuted

Both hand strokes measure half-width 2.0 px, so the obvious defence is that width CV is meaningless at
the rasterisation floor. Tested rather than assumed — synthetic strokes drawn by code at matched
widths:

| code brush radius | measured half-width | width CV |
|---|---|---|
| 2 | 2.2 | **0.000** |
| 3 | 3.2 | 0.031 |
| 4 | 4.2 | 0.000 |
| 10 | 10.2 | 0.014 |
| 40 | 40.1 | 0.008 |

Code at r = 2 gives CV **0.000**. The hand gives 0.324 and 0.602. **The high variance is real** — it is
finger tremor, antialiasing and JPEG ringing on the stroke edge. The rasterisation excuse is dead, and
with it the measure.

## 3. What this actually means

**Level 4 (`FOLDING_EFFORT_BUDGET`) is refuted as formulated.** Neither boundary complexity nor width
discipline separates a human hand from a machine mask. The 22-of-22 separation reported earlier *was*
an artifact of comparing real data against idealised code — which is what the missing control arm was
supposed to test for, and it did its job.

**Two caveats that are real but must not be used to rescue the result:**

- **n = 2.** Two strokes is not a sample. The direction is bad and the pre-registered kill condition
  fired, so the honest move is to report the refutation and not to collect data until it passes.
- **Possible category error.** A drawn stroke is *ink added on top*; a machine mask is a region where
  content was *replaced*. These may not be the same kind of object, and comparing them may be unfair to
  both. But in the wild you do not know which kind you are looking at, so a measure that needs to be
  told is not usable anyway.

**The one thing that survived:** the green line at 25 vertices with **gradient adherence 0.42** — a
hand drawing where it wants, cutting across content, versus machine masks at 1.24 that snap to object
contours. Gradient adherence is the only component of level 4 still pointing the right way, and with
n = 2 it is a hypothesis, not a finding.

## 4. Running tally

| level | question | status |
|---|---|---|
| 1 — imaginary camera | which device layout wrote this? | **holds**, 1/61 FP, now 5/5 on camera 5 |
| 2 — imaginary programs | which editor / platform rewrote it? | catalogue exists, untested |
| 3 — plausible human action | could a person have done this at all? | untested |
| 4 — effort budget | could a person have done it in the time? | **REFUTED** by the human arm |

Feature tally: **44 tested, 2 have ever cleared** — and level 4 has moved from the passed column to the
failed one.

## 5. The data that would settle it properly

The strokes Jonathan supplied are *drawn ink*. What level 4 actually needed, and still needs, is
**hand-made SELECTION edits** — a person doing clone-stamp, heal, or copy-paste manually in
Photoshop/GIMP, where the output is a replaced region exactly like the machine's, but the mask was
placed by hand. That is the true apples-to-apples arm. Without it, level 4 has been tested against the
wrong control and *still* failed, which is a worse position than untested.

**Code:** `human_arm.py`, `human_arm2.py`, `human_arm2.json`.
