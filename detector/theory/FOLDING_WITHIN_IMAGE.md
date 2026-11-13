# The Within-Image Turn — the dead axes localise what the committee could not

*The model-free observers were run per-cell on the 13 edited/original pairs, asking the question they
were designed around and had never been asked: not "is this image generated" but **"is this region
inconsistent with the rest of the same image."** Two of the four separate the edits, with a clean
control arm — where the committee's edited arm was indistinguishable from its own control
(`FOLDING_SEAM_TEST`). And the strongest is **`spec_dev`, the 1/f resonance residual — the same single
feature that was the sole survivor of the matched benchmark.** Two unrelated tests, same last measure
standing. Status: MEASURED, n = 13 pairs, model-free, $0. The size-trend caveat in Part III is
load-bearing.*

---

## Part I — Why this is a different question

Every model-free measure failed at class separation (`FOLDING_MATCHED_BENCHMARK`: nothing above
|AUC − 0.5| = 0.164). But `nonlocal_asymmetry` compares a region against the rest of the same image;
the reconstruction axis asks whether a region settles the way its neighbours do. Those are *within-image*
questions, and the benchmark asked a *between-image* one.

Four per-cell measures, each expressed as **deviation from the image's own median** — that framing is
the whole point, and it is why they can work here after failing across images:

| | |
|---|---|
| `noise_dev` | robust sensor-noise level of the cell vs the image's own noise field |
| `sharp_dev` | local sharpness vs the image median |
| `spec_dev` | residual from a 1/f fit on the cell's own spectrum, vs the image median |
| `nl_asym_dev` | can the **rest of the image** predict this cell? fine scale over coarse |

Same control as before: identical computation on the untouched original, reading the same cells.

## Part II — The result

| measure | EDITED | above chance | CONTROL | above chance | edit − control |
|---|---|---|---|---|---|
| **`spec_dev`** | **0.641** | **10/13** | 0.417 | 4/13 | **+0.224** |
| **`nl_asym_dev`** | **0.643** | **10/13** | 0.519 | 7/13 | **+0.125** |
| `noise_dev` | 0.376 | 2/13 | 0.424 | 4/13 | −0.048 |
| `sharp_dev` | 0.387 | 3/13 | 0.422 | 5/13 | −0.034 |
| **`spec_dev` + `nl_asym_dev` averaged** | **0.642** | **10/13** | **0.468** | 5/13 | **+0.174** |

**The control arm behaves.** 0.417 and 0.519 — at or below chance on untouched originals. That is the
contrast that matters, because in `FOLDING_SEAM_TEST` the committee's edited arm (0.538) and its
control (0.478) were *the same number*: it was reacting to regions, not to edits. These are not.

10 of 13 above chance has a sign-test p ≈ 0.046 on its own. Small, but it is the first localisation
signal in the project.

### The convergence worth noticing

`spec_dev` is the 1/f-fit residual. `FOLDING_AXIS_INDEPENDENCE` identified `resid_rms` — the same
quantity — as the **only** genuinely independent content in the spectral axis (max |r| 0.32 against
mixedness, versus 0.97 for `slope`). `FOLDING_MATCHED_BENCHMARK` then found it and `one_over_f_r2` were
**the only two features to survive**, weakly and consistently across both content buckets.

Now, on a completely different test with completely different ground truth, it is the strongest measure
again. And it is precisely what `STATE_OF_THE_DETECTOR` §2 says the spectral axis was designed around:
*"real/natural images sit near a broadband, non-resonant (1/f) reference; generated images deviate with
a resonant pattern."*

**The resonance term has now been the last thing standing in two unrelated tests.** That is the
strongest signal in this project about where to look next.

### The inverted pair is also informative

`noise_dev` and `sharp_dev` came out **below** chance — 0.376 and 0.387. Since these are absolute
deviations from the image median, below 0.5 means the edited cells are **closer to the image's typical
value** than untouched cells are. Generative fill regresses toward the frame's average noise and
sharpness, so the filled region is *more average than real texture is*. That is the smoothing prior,
visible from another angle. It is a weak signal in its own right (|d| ≈ 0.12), inverted from the classic
forensic expectation, and it cannot be used naively — a naive "anomalous region" detector would look in
exactly the wrong place.

## Part III — The caveat that stops this being a feature

**All four measures anti-correlate with edit size** (−0.24 to −0.39). Per-image, `spec_dev` scores 0.94
and 1.00 on the two smallest edits (0.2%, 0.4%) and 0.28 and 0.59 on the two largest (16.1%, 51.6%).

That is the same red flag that killed the committee's localisation — **but here there is a mechanism,
and it is a flaw in my normalisation rather than in the signal**:

> Every measure is a deviation **from the image's own median**. When the edit covers 51% of the frame,
> the median *is* the edited content. The baseline is contaminated by the thing it is supposed to
> measure against, so the deviation collapses by construction.

That is testable and fixable — use a trimmed or iteratively-reweighted baseline that down-weights
suspect cells, or estimate the reference from the least-anomalous quartile. Until that is done, **the
size trend is not evidence the signal is fake, but it is not evidence it is real either.** The
committee had no such mechanism available and its decline stayed unexplained; this one has a named
suspect and a fix to try.

## Honest ledger

**MEASURED (13 pairs, 6×6 grid, model-free, $0, ~10 s/image)**
- `spec_dev` localises edits at 0.641 (10/13) against a control of 0.417 (4/13).
- `nl_asym_dev` at 0.643 (10/13) against a control of 0.519 (7/13) — the cleanest null of the four.
- Combined: 0.642 edited vs 0.468 control.
- `noise_dev` and `sharp_dev` are inverted: edited regions are *more average* than real texture.
- The resonance residual is the strongest measure here **and** was the sole survivor of the matched
  benchmark — two independent tests, same feature.

**CAVEATS — all of them apply**
- n = 13; per-image AUC over 36 cells with 1–22 positives is noisy.
- Negative size trend on every measure, with a specific suspected cause (median contamination) that
  has **not** been fixed or tested.
- One grid size, one editing toolchain, no held-out set.
- The edited-vs-control difference has not been formally significance-tested; the 10/13 sign test is
  the only inferential number here.

**WHAT THIS IS AND IS NOT**
- It **is** the first localisation signal in the project, from the free half, on the one test whose
  ground truth is confound-free by construction.
- It is **not** a shipping feature. Two fixes and n ≈ 50 pairs stand between this and a claim.

**NEXT, in order**
1. Replace the median baseline with a trimmed/robust estimator and re-run — this directly tests
   whether the size trend is an artifact of the normalisation.
2. Extend to ~50 pairs across more than one editing toolchain.
3. If it holds, the seam map becomes a **free, model-free** product feature — which is a better
   position than the committee ever offered, since the committee could not localise at all.

*Sources: `FOLDING_SEAM_TEST` (the committee failed this same test; the dataset and masks),
`FOLDING_MATCHED_BENCHMARK` (resid_rms and one_over_f_r2 as the only survivors),
`FOLDING_AXIS_INDEPENDENCE` (resid_rms as the spectral axis's independent content),
`FOLDING_TWO_SIDED_WINDOW` (nonlocal asymmetry), `STATE_OF_THE_DETECTOR` §2. Artifacts:
`within_image_observers.py`, `within_image_results.json`, `seam/`.*
