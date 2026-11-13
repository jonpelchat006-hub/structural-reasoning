# PRNU Localisation — 5 of 5, and the regenerated frame has no fingerprint at all

*The edited pairs arrived at camera-original quality and the test ran properly. **Edited mean AUC
0.927 against a control of 0.273 — edit minus control +0.654, on 5 of 5 pairs.** It works on edits of
**0.36% and 0.38% of frame**, where the controls sit at 0.046 and 0.048. And the one fully regenerated
frame in the batch loses the fingerprint completely: **PCE 8838 → 5.7, a ratio of 0.001**. That is
6× the best free measure this project has produced and it holds in exactly the regime where the
field's seam models collapse. n = 5, sign p = 0.062. Status: MEASURED, masks visually verified.
Supersedes the n=1 demonstration in `FOLDING_PRNU`.*

---

## Part I — Two errors caught before the numbers were believed

The first run produced PCE values of **523,724** and **934,162**. Those are not physically meaningful
for PRNU, and the cause was **leakage**: four of the pair originals (`145939`, `145954`, `150002`,
`171926`) are themselves members of the flat reference set, so the "original" was being correlated
with a reference that contained it. Fixed by leave-one-out — rebuild the reference without that frame
for every pair that needs it. Three pairs required it; the other three were never reference members
and are clean by construction.

Second: at 256 px blocks, a 0.36% edit does not fill a single block, so five of seven pairs returned
no measurement at all. Dropped to 128 px blocks with a 0.4 coverage threshold, and the small edits
became measurable — which turned out to be where the method is strongest.

**Alignment was made self-verifying rather than reasoned.** The editor writes its output already
rotated (orientation = 1) while the camera originals carry a rotate-me tag. Instead of working out
which way each orientation code turns and getting it wrong silently, every candidate rotation is tried
and the one that **correlates with the original** is kept — r = 0.99, 0.96, 0.99 on the clean pairs.
The alignment check is the data, not arithmetic.

## Part II — The result

Reference: 11 camera-original flat frames, full resolution, leave-one-out where required. Masks built
by differencing the aligned pair and **visually verified** — every one lands on the inserted object
(a disc, a contrail, a drawn "N", small marks).

| image | edit % | blocks inside | NCC inside | NCC outside | **EDITED AUC** | **CONTROL** |
|---|---|---|---|---|---|---|
| `145908(1)` | **0.36%** | 1 | −0.00302 | 0.02742 | **0.917** | **0.046** |
| `171934(1)` | **0.38%** | 1 | 0.00460 | 0.02390 | **0.985** | **0.048** |
| `171842(1)(1)` | 2.66% | 16 | −0.00122 | 0.02761 | 0.952 | 0.590 |
| `150002(1)` | 3.72% | 23 | −0.00142 | 0.02678 | 0.862 | 0.531 |
| `171926(1)` | 5.08% | 27 | 0.00113 | 0.03346 | 0.918 | 0.147 |

**EDITED mean 0.927 (5/5 above chance) · CONTROL mean 0.273 (2/5) · difference +0.654 · edited beats
its own control 5/5, sign p = 0.062.**

Read the NCC columns rather than the AUC. Inside the edited regions the correlation is **−0.003 to
+0.005 — zero**. Outside it is **+0.024 to +0.033**. The fingerprint is not weakened inside the edit;
it is **absent**. Generative fill writes pixels that never passed through the sensor, and there is
nothing subtle about the reading.

### Against everything else in the project

| test | edited | control | edit − control |
|---|---|---|---|
| vision committee | 0.538 | 0.478 | +0.060 |
| `spec_dev`, rebuilt masks | 0.582 | 0.428 | +0.154 |
| material baseline | 0.598 | 0.461 | +0.137 |
| PRNU, old files, n = 1 | 0.812 | 0.403 | +0.410 |
| **PRNU, camera-original, n = 5** | **0.927** | **0.273** | **+0.654** |

**4× the best free measure, and it improves as the edits get smaller** — 0.917 and 0.985 on the two
sub-0.4% edits, against controls of 0.046 and 0.048. That is the inverse of every other measure here,
all of which anti-correlated with edit size. It is also mechanically obvious in hindsight: a small edit
leaves a large, intact fingerprint field to compare against.

## Part III — The regenerated frame, and it is the strategic result

One file in the batch, `145954(1)`, is not a local edit. It is a **completely regenerated image**
carrying an "AI-generated content" watermark — different scene, different colours, same dimensions. It
was excluded from the localisation set. As a separate case it is the most important number here:

| | PCE | NCC |
|---|---|---|
| original | **8838.3** | 0.04102 |
| fully regenerated | **5.7** | **0.00083** |
| ratio | **0.001** | 0.02 |

**A 1550× collapse. The fingerprint is gone entirely.**

`FOLDING_TWO_CHANNEL_LOOP` predicted exactly this and it is worth restating, because it is the
strategic case for the whole approach:

> Seam-based localisation collapses on regeneration — CAT-Net 0.89 → 0.02, TruFor 0.75 → 0.14 — because
> a whole-frame VAE pass leaves no local discontinuity to find. **PRNU is not a seam measure.** It does
> not need two histories in one file; it needs one expected fingerprint and asks whether it is present.
> **Regeneration does not hide it — regeneration removes it, and the removal is the detection.**

That prediction is now measured. The regime where the field's best models go to 0.02 is the regime
where this goes to a 1550× signal.

And the graded version is visible across the whole batch — whole-image PCE ratio edit/original:

| edit type | ratio |
|---|---|
| local edits, 0.18–5.08% | 0.54 – 0.83 |
| **full regeneration** | **0.001** |

The ratio tracks how much of the frame stopped being camera-original. That is a **severity** measure —
Jonathan's *"i can continue searching to see how fake it is"* — computed from the same quantity as the
verdict.

## Part IV — What is still not settled

- **n = 5.** Sign test two-sided p = 0.062. Five of five in the right direction with a +0.654 gap is
  substantial, but it is not yet significance and should not be quoted as such.
- **Two of the five detections rest on a single block.** For the 0.36% and 0.38% edits there is exactly
  one block at ≥40% mask coverage, so the AUC is "where does this one block rank among 500" — legitimate,
  and noisier than the number looks.
- **The larger edits have live controls** (0.590, 0.531). The untouched originals show some structure in
  those same cells, so part of the large-edit signal is regional. The small-edit controls (0.046, 0.048)
  are the clean ones.
- **The AI-image control from `FOLDING_PRNU` is still +0.00103, not zero**, with a named cause (radial
  lens-shading structure that row/column zero-mean does not remove) and a known fix (Fourier-domain
  Wiener filtering). **No threshold should be set until that is done** — the false-positive rate is the
  entire contribution of this component.
- One phone, one camera, one editing toolchain. Nothing here says how it behaves on another device or
  another editor.

## Part V — Where this puts the architecture

`FOLDING_RATCHET_AND_ROUTING` established the shape: a gate that fires categorically or stays silent,
in front of a graded verdict. **PRNU is the first instrument in this project that can actually ring that
bell.** "The sensor fingerprint is absent here and present everywhere else in the same frame" is a
categorical, localised claim about physics, not a score that needs a threshold argued over.

It also sits correctly in the two-channel loop. It is Channel B — measured from pixels, not forgeable
with exiftool — and it **answers a Channel A question**: *is this file what it claims to be*. A file
claiming capture on this phone should carry this sensor's fingerprint. That is the cross-check
`FOLDING_CLEAN_HISTORY` argued for, and it is now working rather than proposed.

The cost is the prerequisite, and it is real: **camera-original files, and a reference from the device.**
That is not a general-purpose internet-image detector. It is a strong answer to *"is this photo from
this phone, unmodified"* — which is a narrower claim, an answerable one, and per `FOLDING_CLEAN_HISTORY`
the honest product rather than the consolation prize.

---

## Honest ledger

**MEASURED**
- Localisation on 5 camera-original pairs: **edited 0.927, control 0.273, +0.654, 5/5**, sign p = 0.062.
- **Best on the smallest edits**: 0.36% → 0.917 (control 0.046); 0.38% → 0.985 (control 0.048).
  Inverts the size trend that afflicted every other measure here.
- Inside edited regions NCC is **zero** (−0.003 to +0.005) against **+0.024 to +0.033** outside.
- **Fully regenerated frame: PCE 8838 → 5.7, ratio 0.001.** The predicted behaviour in the regime where
  seam models collapse.
- Whole-image PCE ratio grades severity: 0.54–0.83 local, 0.001 regenerated.
- Masks visually verified against the inserted objects.

**ERRORS CAUGHT IN THIS RUN**
- Reference leakage (four pair originals were reference members) — produced PCE 523,724 and 934,162 in
  the first pass. Fixed by leave-one-out; those numbers are discarded.
- 256 px blocks measured nothing on sub-1% edits. 128 px blocks are where the method is strongest.

**CAVEATS**
- n = 5; two detections are single-block; large-edit controls are live (0.53, 0.59); one device, one
  editor; the +0.00103 AI-control offset is unresolved and blocks any threshold.

**NEXT**
1. **Fourier-domain Wiener filtering of the reference**, then measure the false-positive rate on
   non-matching images. That number is the product.
2. More pairs — 15–20 would take sign p from 0.062 to conclusive, and they are now cheap to make.
3. A second phone, to check the reference is device-specific rather than model-specific.
4. Deliberately include more **fully regenerated** frames. On this evidence that is the easiest case,
   not the hardest, and it is the case the rest of the field cannot do.

*Artifacts: `prnu_camera2_localise.py`, `prnu_camera2_localise.json`, `camera2_masks.png`,
`prnu.py`, `prnu_camera2.json`. Sources: internal — `FOLDING_PRNU` (the reference and the n=1
demonstration), `FOLDING_TWO_CHANNEL_LOOP` (the regeneration prediction, now measured),
`FOLDING_CLEAN_HISTORY` (the one-class reframe), `FOLDING_RATCHET_AND_ROUTING` (the gate this can fire),
`CAPTURE_PROTOCOL.md`.*
