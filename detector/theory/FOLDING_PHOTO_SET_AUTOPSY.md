# Autopsy of the Photo Set — the confound was never the compression

*Jonathan asked to re-run his own photos with parity enforced, on the expectation from
`FOLDING_MATCHED_BENCHMARK` Part IV that a **camera-original** real class would be a different and
probably easier test. It is not an easier test. It is not a test at all. **The set carries two free
separators that reach AUC 1.000 and 0.008, and every one of the fifteen model-free features separates
two sets of REAL photographs MORE strongly than it separates real from AI.** A live loader bug —
EXIF orientation never applied — was scoring 15 of 22 real photos rotated 90° while every AI image
was upright. Status: MEASURED, with a positive control and a bootstrap. Companion to
`FOLDING_MATCHED_BENCHMARK`, `STATE_OF_THE_DETECTOR` §3.*

---

## Part I — What was actually on disk

`real photos/` n=22, `ai photos/` n=17. This is the set behind `bench_photo_metrics.json`
(**AUC 0.952**, retired in `STATE_OF_THE_DETECTOR` §5 as "unreproducible"). The image sets *are*
on disk — it is the harness that was never fit to run on them.

| | real class | AI class |
|---|---|---|
| device / origin | **21 of 22 one Samsung Galaxy S23 Ultra** (1 Galaxy S6) | Midjourney ×15, Grok ×2 |
| format | JPEG | PNG ×15, JPEG ×2 |
| bits per pixel | **3.73** | **11.92** |
| stored aspect ratio | 1.78 (all ≥ 1.33) | 0.67 (all ≤ 1.00) |
| stored sideways | **15 / 22** | **0 / 17** |
| content | casual snapshots — cat, food, street, forest, rocks, bird, bridge, selfies | **12 / 17 studio beauty close-ups**, 2 anime, 1 magazine cover, 1 typography poster, 1 car interior |

`benchmark_v6.py`, the harness that produced the 0.952, contains **no resize and no re-encode step of
any kind** — verified by inspection, there is no parity code in the file. It was handed these files
as they sit.

## Part II — The two free separators

Neither of these knows anything about provenance.

| separator | AUC | \|AUC−0.5\| | |
|---|---|---|---|
| **stored aspect ratio** | **1.000** | **0.500** | perfect. 22/22 real land one side, 17/17 AI the other |
| **bits per pixel** | **0.008** | **0.492** | near-perfect. JPEG-vs-PNG with a number on it |
| true aspect ratio (EXIF applied) | 0.591 | 0.091 | ← the confound was *entirely* the unapplied tag |
| megapixels | 0.484 | 0.016 | clean |

**The best feature in the entire model-free stack reaches |AUC−0.5| = 0.37. Two numbers that could be
read off `ls -l` reach 0.50 and 0.49.** No observer result from this set can mean anything.

### The loader bug, stated precisely

Neither `PIL.Image.open` nor `skimage.io.imread` applies **EXIF tag 274 (Orientation)**. A phone photo
shot in portrait is stored as a landscape-shaped buffer plus a flag saying *rotate me*. Every loader in
this project ignored the flag. Generated images have no EXIF at all, so they are never affected.

- **15 of 22 real photos were fed to every observer — and to the vision committee — rotated 90°.**
- **0 of 17 AI images were.**
- Applying the tag collapses the aspect-ratio separator from **1.000 to 0.591**.

This is not a data-collection problem. It is a code defect, it is one line per loader, and it silently
manufactured a perfect separator.

**It also reaches the seam set.** In `more photos/altered/`, **7 of the 13 pairs** have the original
stored `4000×2252` with orientation=6 while the edit — rewritten by the editing app, which baked the
rotation in — is stored `2252×4000` with orientation=1. Read naively those two arrays *are not the same
shape*, so the pixel diff that produces the ground-truth mask is not well defined for more than half the
set. `seam/index.json` and the `*_mask.npy` files are **not on disk**, so `seam_results.json` and
`within_image_results.json` cannot currently be reproduced or checked. Until the masks are rebuilt with
the tag applied, the `spec_dev` 0.641 localisation result — the project's one remaining live hypothesis
— has an unquantified defect underneath it.

## Part III — Parity does not save it

Four arms, identical feature extraction, only the preparation differs. |AUC−0.5|, real vs AI:

| feature | A as-shipped | B current parity (512+q85) | C + orientation | D full parity (square 448) |
|---|---|---|---|---|
| `spectral.slope` | 0.369 | 0.366 | 0.366 | **0.356** |
| `spectral.hf_frac` | 0.334 | 0.329 | 0.329 | 0.348 |
| `spectral.spec_entropy` | 0.310 | 0.305 | 0.305 | 0.340 |
| `mixed.blur_ratio` | 0.345 | 0.340 | 0.340 | 0.337 |
| `mixed.lap_var` | 0.238 | 0.225 | 0.225 | 0.249 |
| `window.nonlocal_asymmetry` | 0.203 | 0.246 | 0.273 | 0.179 |
| **best of 15** | **0.369** | 0.366 | 0.366 | **0.356** |

Arm D applies the orientation tag, centre-crops to square and resizes to a fixed 448×448 — which kills
aspect ratio, pixel count *and* the per-image resampling ratio together — then puts both classes through
one JPEG q85 encode.

**Nothing moves.** 0.369 → 0.356. **So format, orientation and geometry were not what these features
were reading.** That was the working assumption for the whole compression-parity programme, and on this
set it is wrong. Something else is doing the work.

## Part IV — The control arms, and this is the result

The right question is not *"do these features separate real from AI"* — they do, at ~0.35. It is
*"what else do they separate just as well?"* So they were given jobs where the correct answer is
**known in advance to be chance**. Every arm runs through the arm-D parity path.

|AUC−0.5|:

| feature | TARGET real vs AI | CTRL1 web portrait vs web landscape **both real** | CTRL2 his phone vs web real **both real** | CTRL3 his close-ups vs his scenes **both real, one phone** |
|---|---|---|---|---|
| `spectral.slope` | 0.356 | **0.478** | 0.444 | 0.375 |
| `spectral.spec_entropy` | 0.340 | **0.463** | 0.455 | 0.385 |
| `spectral.hf_frac` | 0.348 | **0.460** | 0.444 | 0.333 |
| `mixed.blur_ratio` | 0.337 | **0.456** | 0.416 | 0.302 |
| `mixed.lap_var` | 0.249 | **0.434** | 0.444 | 0.354 |
| `window.nonlocal_asymmetry` | 0.179 | 0.353 | 0.301 | 0.083 |
| `spectral.resid_rms` | 0.123 | 0.185 | 0.031 | 0.021 |

**15 of 15 features have a control at or above the target. Zero survive.**

Bootstrap, 4000 resamples, target vs CTRL1:

| feature | target (95% CI) | CTRL1 both-real (95% CI) | P(control > target) |
|---|---|---|---|
| `spectral.slope` | 0.355 [0.219, 0.460] | 0.478 [0.423, 0.500] | **0.986** |
| `spectral.spec_entropy` | 0.340 [0.203, 0.447] | 0.463 [0.394, 0.500] | 0.974 |
| `spectral.hf_frac` | 0.346 [0.208, 0.457] | 0.460 [0.390, 0.500] | 0.958 |
| `mixed.blur_ratio` | 0.336 [0.195, 0.452] | 0.456 [0.375, 0.500] | 0.953 |
| `mixed.lap_var` | 0.248 [0.078, 0.388] | 0.434 [0.328, 0.500] | 0.983 |

**`spectral.slope` separates web portrait photography from web landscape photography — both real — at
0.478, essentially perfectly, while separating real from AI at 0.356.** CTRL3 is the tightest of the
three: same phone, same photographer, same processing, same era, differing *only* in whether the frame
is filled by a face or by a scene — and it still reaches 0.375 on `slope`, above the target.

This is a stronger statement than `FOLDING_MATCHED_BENCHMARK` was able to make. That doc concluded
*"none of them demonstrates an effect at this sample size"* — underpowered. This concludes **the effect
is present, larger, and points at content and population rather than provenance.** The confound is
identified, signed and measured, not merely suspected.

### Why: what these features are

`slope`, `hf_frac`, `spec_entropy`, `blur_ratio`, `lap_var` are all readings of **how sharpness is
distributed across the frame**. A studio beauty close-up at f/1.4 — one plane of skin in focus,
everything else fallen away — has a radically different sharpness profile from a landscape snapshot
where a phone's deep depth of field holds everything at once. The AI class here is 12/17 studio
close-ups and the real class is almost entirely deep-focus scenes. **The features are reading
photographic genre, and reading it well.** `STATE_OF_THE_DETECTOR` §5 already recorded that content
alone reproduces 54–77% of the apparent signal; on this set it reproduces **more than 100%.**

## Part V — Verification, because a null result needs an instrument that works

A dead pipeline produces the same table as a real null. Three checks:

1. **AUC implementation.** Cross-checked against `sklearn.roc_auc_score` over 300 random trials of
   random size and offset: **max absolute difference 1.11 × 10⁻¹⁶**. Analytic cases correct. Chance at
   n=4000 returns 0.5016 ± 0.0045. *Known limit:* the rank formula does not split exact ties
   (`auc([1,2,3],[1,2,3])` → 0.333, not 0.500). Checked — **0 tied values across all 12 features × 39
   images**, so it never fires here. Flagged because it would matter on quantised features.
2. **Positive control.** Each of the 22 real photos against a Gaussian-blurred (σ 1.2) copy of *itself*
   — a difference the sharpness features are obliged to see. `hf_frac` 0.500, `resid_rms` 0.500,
   `slope` 0.496, `spec_entropy` 0.496, `one_over_f_r2` 0.475, `lap_var` 0.479. **6 of 12 respond at
   ceiling. The instrument is alive**, so the null is about the data.
3. **Bootstrap and direction**, in the Part IV table above.

## Part VI — What a usable set requires

The set cannot be salvaged by reprocessing; the defects are in what was collected.

1. **Match content, per bucket, before anything else.** A bucket must exist on both sides with
   comparable n. The current AI class is 12/17 studio close-up faces; nothing in `real photos/`
   matches it. Either shoot real close-up portraits at comparable aperture, or generate AI landscapes
   and snapshots. **This is the binding constraint** — it is the one confound that survived full parity.
2. **Run the trivial audit first and read it first.** `trivial_audit()` is now in `bench_all_axes.py`.
   If stored aspect ratio or bits-per-pixel separates the classes at |AUC−0.5| ≥ 0.35, stop — no
   observer number from that set can support a claim. This check would have caught the whole episode
   in one second.
3. **Mix orientations within each class.** Both portrait and landscape frames on both sides, so shape
   cannot correlate with label even if a loader misbehaves again.
4. **More than one camera** on the real side, and more than one generator family on the AI side. One
   phone versus one generator measures the phone against the generator.
5. **Export AI output as JPEG at a stated quality**, and keep real photos camera-original — then let
   the harness equalise. Note the real class here is *not* camera-original: dimensions like 1596×1197
   and 1911×1434 are not native S23 Ultra sizes, Software and ExifImageWidth are stripped on 21/22, and
   all files sit near 1 MB regardless of dimension. **These have already been through a
   downsize-and-recompress pipeline** — the premise of the re-test was wrong before it started.

## Honest ledger

**MEASURED**
- Stored aspect ratio separates the classes at **AUC 1.000**; bits per pixel at **0.008**. Both beat
  every observer feature in the project.
- **EXIF orientation is applied nowhere.** 15/22 real photos scored rotated 90°, 0/17 AI. Removing the
  bug drops the aspect separator from 1.000 to 0.591.
- Full parity — orientation, square crop, fixed 448, one q85 encode — moves the best feature from
  0.369 to 0.356. **Format and geometry were not the confound.**
- **15 of 15 features score at or above their target on a real-vs-real control.** P(control > target)
  = 0.95–0.99 on the top five.
- The instrument passes an sklearn cross-check and a blur positive control.
- 7/13 seam pairs have original and edit at **transposed dimensions**; `seam/` masks are not on disk.

**CORRECTED IN CODE**
- `image_io.py` — single EXIF-correct loader (`load_rgb`, `load_gray`, `parity`, `audit`). Observers
  must stop calling `Image.open` / `imread` directly.
- `bench_all_axes.transcode` — applies `exif_transpose`; optional `square=` for full geometric parity.
- `bench_all_axes.trivial_audit` — free-separator audit, to be run before any benchmark.
- `within_image_observers.measure` — EXIF-correct load.

**BUILT, NOT YET MEASURED**
- `within_image_observers.dev_trimmed` — roadmap item 1, the iteratively-trimmed within-image baseline.
  Honest limit noted in the docstring: at 51.6% coverage the edited cells are the *majority*, and no
  location estimator can identify the authentic mode from location alone. Expect it to fix the mid-size
  cases, not the largest.

**UNCHANGED BY THIS WORK**
- The vision committee's **0.932** stands — it was measured on the `more photos` matched set, not this
  one. But the retired **0.952** is now not merely unreproducible, it is *explained*: a set with two
  perfect free separators, in which two thirds of the real class was shown to the models sideways.

**NEXT, in order**
1. Rebuild the seam masks with EXIF applied; confirm whether the 7 transposed pairs were handled
   correctly before, and re-run `spec_dev`. The project's only live hypothesis rests on this.
2. Then `dev_trimmed` vs `dev` on the rebuilt set — report both.
3. Collect a content-matched set per Part VI before any further class-separation work.

*Sources: `FOLDING_MATCHED_BENCHMARK` Part IV (predicted a camera-original class would be easier —
refuted), `STATE_OF_THE_DETECTOR` §3/§5, `FOLDING_WITHIN_IMAGE` Part III (the median-contamination
suspect), `FOLDING_SEAM_TEST`, `FOLDING_PHYSICS_OBSERVER` Part I (content drift 54–77%). Artifacts:
`image_io.py`, `parity_arms.py` + `parity_arms.json`, `control_arms.py` + `control_arms.json`,
`verify.py`, patched `bench_all_axes.py` and `within_image_observers.py`.*
