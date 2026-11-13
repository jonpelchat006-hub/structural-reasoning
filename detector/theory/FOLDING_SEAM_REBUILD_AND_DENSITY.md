# The Rebuild — the localisation signal shrinks, and three new ideas get tested honestly

*The seam masks were rebuilt with EXIF orientation applied and **visually verified against the edits**.
On correct ground truth the project's one live hypothesis weakens: `spec_dev` falls from
**0.641 (10/13) to 0.550 (7/13)** under the same estimator. The trimmed baseline recovers it to
**0.582 (9/13)** but **refutes** the median-contamination story it was built to test. Jonathan's three
new directions were then built and gated: **density fails the control**, **format handling produces a
rule rather than a feature**, and **the material baseline halves the size trend but leaks into its own
control**. Status: MEASURED, n = 13 pairs, model-free, $0. Companion to `FOLDING_PHOTO_SET_AUTOPSY`,
supersedes the numbers in `FOLDING_WITHIN_IMAGE` and `FOLDING_SEAM_TEST`.*

---

## Part I — The masks, rebuilt and checked

All 13 pairs now align: `exif_transpose` puts the 7 transposed originals and their edits on the same
shape. Masks were then **inspected visually as overlays**, and every one lands on a coherent inserted
or altered object — a person on a foggy road, a sheep on a lawn, an object on a desk, birds, a replaced
night sky, a regenerated blanket. The ground truth is now something that can be looked at rather than
trusted.

Thresholding note, recorded because the first attempt failed silently: the difference distribution is
strongly bimodal — JPEG recompression noise at 0.001–0.010, edited pixels at 0.15–0.45, with a clean
gap. The first version centred on q60 and scaled by (q60−q40). On `20250519_224651`, where ~47% of the
frame is edited, q40–q60 straddles the gap, the scale exploded, the threshold went to **2.72 against a
maximum difference of 0.56, and the mask came back EMPTY for the largest edit in the set**. Fixed by
estimating the noise floor from the low quartile, which the signal cannot reach unless an edit exceeds
75% of the frame. **Estimate scale from a region the signal cannot occupy — the same lesson as the
median-contamination problem, one level up.**

| pair | new | old (unverifiable) | | pair | new | old |
|---|---|---|---|---|---|---|
| 20250605_161631 | 0.49% | — | | 20250520_081320 | 6.00% | 2.60% |
| 20250131_195339 | 0.59% | 0.39% | | 20250601_182744 | 25.09% | — |
| 20250605_162057 | 0.86% | — | | 20250528_142137 | 27.98% | 9.59% |
| 20250615_174352 | 0.96% | — | | 20250611_173518 | 32.09% | — |
| 20250531_174853 | 4.22% | 1.55% | | 20250519_224651 | 47.11% | 51.57% |
| 20250409_123854 | 4.45% | 3.33% | | | | |
| 20250518_110837 | 4.62% | 2.70% | | 20250522_134100 | 5.91% | 2.35% |

**The new masks are roughly twice the old ones**, and the change does not split cleanly along the
transposed/upright line — so the old builder evidently handled the transpose somehow, and the
difference is mostly threshold choice. Since the old masks and the builder are both gone, **that cannot
be checked, which is the whole problem**: every AUC in `FOLDING_WITHIN_IMAGE` and `FOLDING_SEAM_TEST`
was computed against a ground truth nobody can now inspect.

## Part II — Localisation on correct masks

Same measures, same control arm, same 6×6 grid.

| measure | baseline | EDITED | >chance | CONTROL | >chance | edit−control | corr w/ size |
|---|---|---|---|---|---|---|---|
| **`spec_dev`** | median | **0.550** | 7/13 | 0.406 | 4/13 | **+0.144** | −0.48 |
| **`spec_dev`** | **trimmed** | **0.582** | **9/13** | 0.428 | 5/13 | **+0.154** | **−0.58** |
| `nl_asym_dev` | median | 0.563 | 7/13 | 0.531 | 10/13 | +0.032 | −0.06 |
| `nl_asym_dev` | trimmed | 0.577 | 8/13 | 0.517 | 8/13 | +0.059 | −0.02 |
| `noise_dev` | trimmed | 0.437 | 4/13 | 0.407 | 4/13 | +0.031 | +0.09 |
| `sharp_dev` | trimmed | 0.379 | 2/13 | 0.385 | 2/13 | −0.005 | +0.31 |

**Against `FOLDING_WITHIN_IMAGE`: `spec_dev` 0.641 → 0.550, and 10/13 → 7/13, on the same estimator.**
The edit−control gap falls from +0.224 to +0.144. `nl_asym_dev` collapses from 0.643/+0.125 to
0.563/+0.032 and is no longer distinguishable from its control.

The control arm still behaves — 0.406 to 0.428, at or below chance — so this is a weaker signal, not an
artifact. But **9/13 has a sign-test p ≈ 0.13. It is not significant.**

### The median-contamination hypothesis is refuted for `spec_dev`

`FOLDING_WITHIN_IMAGE` Part III named the plain median as the suspect for the size anti-correlation and
called a robust baseline *"the single highest-value fix available"*. It was built and run:

| measure | corr(size, AUC) median → trimmed |
|---|---|
| `noise_dev` | −0.50 → **+0.09** ✓ fixed |
| `sharp_dev` | −0.12 → **+0.31** ✓ fixed |
| **`spec_dev`** | −0.48 → **−0.58** ✗ **worse** |
| `nl_asym_dev` | −0.06 → −0.02 — |

**The fix works, on the two measures that carry no signal, and fails on the one that does.** So for
`spec_dev` the size trend is *not* a normalisation artifact. It is real, and the per-image table says
what it is:

| edit size | `spec_dev` (trimmed) |
|---|---|
| 0.49% | 0.97 |
| 0.59% | 0.88 |
| 0.86% | 0.62 |
| 0.96% | 0.66 |
| 4.2–6.0% (5 pairs) | 0.41–0.61 |
| 25–47% (4 pairs) | 0.31–0.57 |

**`spec_dev` localises small edits and does nothing on large ones.** At 1–3 positive cells out of 36
the per-image AUC is also at its noisiest, so "a genuine small-edit detector" and "four lucky draws"
are not separable at n = 13. The honest position: **the localisation hypothesis is weaker than recorded
and still alive, and n = 50 pairs is now the only thing that will settle it.**

---

## Part III — Data density: the idea was right, the measurement was the file

> *"the ai class has 11.92 bits per pixel and real is only 3.73. but we have jpeg and png, but then a
> real photo should be evenly spread or computable right?"*

The instinct is correct and the project had never tested it. Filesize-per-pixel is worthless — it is
PNG-vs-JPEG plus a quality slider — but the quantity underneath is real: **an image has an intrinsic
information content, and where that information sits in the frame is a property of how it was made.**
Re-encode everything through one identical encoder and that quantity is measurable.

Three channels, because density is not one thing:

- **lossy** — JPEG bits/pixel at fixed quality, header-corrected. Structure only; the encoder discards
  grain.
- **lossless** — zlib bits/pixel after a horizontal-difference predictor. Structure *plus* grain.
- **noise** — zlib bits/pixel of the residual after a 3×3 median filter. The grain channel alone.

The third is the sharp form of *"evenly spread"*. **A photograph has a sensor noise floor everywhere** —
even blank sky carries photon shot noise, so its local incompressible content never reaches zero. A
diffusion decoder makes genuinely smooth gradients: its flat regions are flat all the way down. So the
claim is about **the floor**, not the average — and `noise_floor_ratio` (10th-percentile cell density ÷
mean cell density) is **scale-free**, which is what should survive a genre confound: change the scene
and numerator and denominator move together.

### Pre-registered, then run

Written before the run: (1) every `*_mean` fails the control, because mean density is scene complexity
is genre; (2) `noise_floor_ratio` is the only candidate; (3) real should be **higher**; (4) risk —
phone noise reduction and processed stock photography also flatten the grain floor.

| | TARGET | CTRL1 content | CTRL2 device | CTRL3 content/1dev |
|---|---|---|---|---|
| `noise_mean` | 0.198 | **0.372** | **0.364** | 0.208 |
| `grain_share` | 0.305 | **0.434** | **0.402** | 0.323 |
| `lossless_floor_ratio` | 0.144 | 0.016 | **0.213** | 0.146 |
| `noise_floor_ratio` | 0.187 | — | — | — |

**Prediction 3 confirmed: `noise_floor_ratio` = 0.687 raw AUC, real photos have the higher floor,
exactly the predicted direction.** Predictions 1 and 4 also confirmed. **Prediction 2 fails on
magnitude: |AUC−0.5| = 0.187, and the controls are not cleared. Nothing survives.**

Localisation was no better — `dens_lossy_dev` +0.021, `dens_lossless_dev` +0.019, `dens_noise_dev`
−0.018 edit−control. Nothing.

**Read this as a clean, cheap kill of a good idea.** The mechanism is real — the direction came out as
predicted, from a prediction made in advance — but on a real class that has been through phone noise
reduction and a resize, the grain floor the argument depends on has already been removed. **This
measure needs camera-original or raw files, which is the same wall `FOLDING_MATCHED_BENCHMARK` hit for
the optics measures.** Three independent measures, one data requirement.

---

## Part IV — Multiple file types: the answer is a rule, not a feature

> *"we probably should be able to handle multiple types of image files. that doesnt really change what
> the image is it just gives different starting conditions and needs the right methods for it."*

Exactly right, and the consequence is a rule the project did not have:

> **There are two kinds of evidence and they must never be mixed.**
>
> **Channel A — evidence about the FILE.** Format, JPEG quantisation tables, estimated quality, chroma
> subsampling, EXIF completeness, camera make/model, maker note, ICC profile. Real, often decisive,
> and **trivially forged** — re-save any generated image through a phone gallery app and the whole
> channel flips.
>
> **Channel B — evidence about the IMAGE.** Everything measured from pixels after parity normalisation.

**Blending them is what produced the 0.952.** Bits-per-pixel separated that benchmark at AUC 0.008 —
but it was reading PNG-vs-JPEG, a Channel A fact, while being reported as a pixel measurement. Once
blended it cannot be detected after the fact.

`format_probe.py` implements Channel A explicitly and refuses to hand it to the observers. What it says
about the sets on disk:

| set | source class | JPEG quality | EXIF | camera make | maker note |
|---|---|---|---|---|---|
| his real (22) | camera_jpeg_stripped ×22 | **96–97** | 22/22 | 22/22 | **0/22** |
| his AI (17) | lossless_native ×15, recompressed ×2 | 99 | 2/17 | 0/17 | 0/17 |
| web real (34) | recompressed ×30, webp ×2, camera ×2 | 89 (55–98) | 15/34 | 2/34 | 0/34 |
| seam pairs (26) | camera_jpeg_stripped ×26 | 94–97 | 26/26 | 26/26 | **0/26** |

**Zero maker notes anywhere**, including on files that carry a Samsung make/model — further confirmation
that the "camera-original" class has been through a re-encoder that stripped them.

*Bug found and fixed in my own code:* the quality estimator had the two IJG branches swapped and
reported quality **838** for a phone JPEG and **2825** for a Midjourney re-save. A quality estimate that
exceeds 100 is not a borderline result, it is a broken formula — **the output range is the check**.
After the fix, encoding at known qualities 40/55/70/75/85/90/95 reads back with **0.0 mean absolute
error**.

**What "the right methods" means per format** is recorded in the module: JPEG sources are already
8×8 quantised and their high-frequency tail is truncated (which is why the balance law could not be
fitted); their block grid is recoverable and a misaligned grid is itself a splice cue. PNG/lossless
carries the generator's full frequency content and *must* go through the same encoder before any
spectral comparison. WebP-lossy is its own artifact family. RAW is the only format where the optics
measures are testable at all.

---

## Part V — The material layer: right mechanism, leaky proxy

> *"it seems like theres more to the context parts we dont have yet. like knowing what we are looking at
> and what each piece should be doing."*

This names a category error sitting under every within-image measure in the project. **They compare a
cell against the whole image's baseline.** A frame of sky, skin, foliage and asphalt has four different
correct answers for "how much high-frequency energy belongs here", and the image median is an average
over all four — a number that describes none of them. Sky is legitimately smooth. Comparing a sky cell
to a sky-plus-foliage average tells you the cell is sky, not that it is fake.

A free proxy was built: cluster the 36 cells into 4 material groups by colour and texture, then score
each cell against **its own cluster's** trimmed baseline. The clustering descriptor is deliberately not
one of the measures being tested, so the clustering cannot absorb the signal.

| measure | baseline | EDITED | CONTROL | edit−control | corr w/ size |
|---|---|---|---|---|---|
| `spec_dev` | global | 0.582 | 0.428 | **+0.154** | −0.58 |
| `spec_dev` | **material** | 0.598 | 0.461 | +0.137 | **−0.29** |
| `noise_dev` | global | 0.437 | 0.407 | +0.031 | +0.09 |
| `noise_dev` | **material** | **0.600** | **0.588** | +0.012 | −0.32 |
| `sharp_dev` | global | 0.379 | 0.385 | −0.005 | +0.31 |
| `sharp_dev` | **material** | **0.593** | **0.576** | +0.018 | −0.57 |
| `nl_asym_dev` | material | 0.517 | 0.550 | −0.033 | −0.17 |

Three pre-registered predictions, three different answers:

1. **"Material beats global" — refuted.** `spec_dev` edit−control +0.154 → +0.137. No measure gains.
2. **"The size trend weakens" — confirmed, and it is the real finding.** `spec_dev` corr(size)
   **−0.58 → −0.29**, and the two largest edits improve outright: 32.1% coverage 0.31 → 0.49, 47.1%
   coverage 0.40 → 0.60. **A large edit no longer destroys its own reference, because the rest of the
   sky is still there to compare against.** The mechanism Jonathan pointed at is real and measurable.
3. **"The control must stay at chance" — violated, and it diagnoses the proxy.** `noise_dev` and
   `sharp_dev` both jump ~0.20 on the edited arm — and **their controls jump by the same amount**
   (0.407 → 0.588, 0.385 → 0.576). That is `FOLDING_SEAM_TEST`'s committee failure repeated exactly:
   reacting to regions, not to edits. Cause is identifiable — the clusters are spatially contiguous, so
   cluster boundaries *are* image structure, and any cell straddling one is anomalous within its own
   cluster whether or not anything was edited.

**Verdict: the framing is right and this implementation of it is not.** The fix is specific — assign
material at pixel level rather than per cell, and exclude or down-weight boundary-straddling cells, so
"different material next door" stops being scored as "inconsistent with my material". `spec_dev` is the
one measure whose control held (0.461), which is consistent with it being the only one carrying real
signal.

**And this is where the paid layer earns its place.** The free proxy knows only that some cells cluster
together; it cannot know that a region *is* skin, and therefore should have pores and subsurface
scatter, or *is* sky, and therefore should have a smooth gradient plus grain. `FOLDING_PHOTO_SET_AUTOPSY`
established that global model-free statistics are exhausted on this problem. This test says the next
move is not another statistic — it is **naming the region and giving it its own expectation**, which is
a semantic question and needs the vision model. That is the context layer Jonathan says is missing, and
the evidence now points at it.

---

## Honest ledger

**MEASURED**
- 13 masks rebuilt EXIF-correctly, all pairs aligned, **verified visually** against the edits.
- `spec_dev` localisation **0.641 (10/13) → 0.550 (7/13)** on the same estimator; 0.582 (9/13) trimmed,
  sign-test p ≈ 0.13 — **not significant**.
- `nl_asym_dev` no longer separable from its control (+0.032 median, +0.059 trimmed).
- **Median contamination refuted for `spec_dev`** (corr(size) −0.48 → −0.58) and confirmed for the two
  measures that carry no signal.
- Density: pre-registered direction **confirmed** (`noise_floor_ratio` 0.687, real higher), magnitude
  0.187, **controls not cleared, nothing survives**. Localisation ±0.02, nothing.
- Material baseline **halves the size anti-correlation** (−0.58 → −0.29) and improves both largest
  edits, but the free proxy's control arm rises with its edited arm on 2 of 4 measures.
- JPEG quality estimator verified exact (0.0 mean absolute error over 7 known qualities) after fixing
  swapped branches that reported quality 838 and 2825.
- **0 maker notes across all 48 phone files** carrying Samsung make/model.

**BUILT**
- `rebuild_seam.py` — EXIF-correct masks with a low-quartile noise-floor threshold.
- `density_observer.py` / `density_test.py` — three density channels, pre-registered, control-gated.
- `format_probe.py` — Channel A / Channel B separation, source-class routing, per-format method notes.
- `material_context.py` / `material_test.py` — per-material baseline, head-to-head against global.
- `seam_rerun.py` — both baselines side by side on the rebuilt masks.

**STILL TRUE**
- The verdict product stands at 0.932 (untouched by any of this).
- **No free measure in this project has cleared a real-vs-real control.** Count is now 15 + 13 density
  features = 28.

**NEXT, in order**
1. **50 pairs, two toolchains, PNG export.** This is now the only thing that will settle `spec_dev`,
   and it unblocks the density and optics measures at the same time. Everything else is blocked
   behind it.
2. **Pixel-level material assignment** with boundary cells excluded — the specific fix for Part V's
   leak. Free.
3. **Finer grid.** At 6×6 on 768 px a 0.5% edit is one cell; the resolution is the binding limit on
   exactly the edits `spec_dev` is best at.
4. **The paid material layer**: vision model names each region, supplies its expectation, and the
   region is scored against that instead of against the frame.

*Sources: `FOLDING_PHOTO_SET_AUTOPSY` (the EXIF bug, the control-arm method), `FOLDING_WITHIN_IMAGE`
(the numbers this supersedes; the median-contamination hypothesis), `FOLDING_SEAM_TEST` (the committee's
region-not-edit failure, repeated here by the material proxy), `FOLDING_MATCHED_BENCHMARK` Part IV (the
raw-file wall the density measure has now also hit). Artifacts: `rebuild_seam.py`, `seam_rerun.py` +
`seam_rerun_results.json`, `density_observer.py`, `density_test.py` + `density_results.json`,
`format_probe.py`, `material_context.py`, `material_test.py` + `material_results.json`,
`seam_overlays.png`, `seam/`.*
