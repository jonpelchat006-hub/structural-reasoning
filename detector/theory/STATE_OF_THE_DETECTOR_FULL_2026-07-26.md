# Shovelcat AI Checker — State of the Detector

*Rewritten 2026-07-26 against a full session of measurement. **This supersedes the 2026-07-25 version,
whose headline numbers were confounded.** Every figure below was measured on a content-matched,
compression-matched, six-generator benchmark or on ground-truth manipulation masks; where something is
untested, it says so. The short version: **one paid axis works and carries the product; the free axes
do not separate classes; the committee does not improve the score; the seam map does not yet localise;
and the most valuable thing built this session is the discipline that established all four.***

---

## 1. What it is, in one paragraph

The checker reads an image and asks whether it was generated or altered. Its organising idea is
imported from a tested body of protein-folding work — *agreement across independent observers is the
invariant; disagreement is the depth* — and the ambition is a **seam map**, not a score. That ambition
is not yet met. What exists today and works is a **semantic reader**: a vision model scoring the image
over a grid, at **stratified AUC 0.93**. What exists today and is promising but unproven is a **second
observer of a genuinely different type** — a spectral reader that is nearly uncorrelated with the first
(**r = 0.14**) and is the only thing in the project that has ever localised an edit.

---

## 2. Architecture — as measured, not as designed

The previous version described **four orthogonal axes**. Measurement does not support that count.

**Axis 1 — Vision committee (paid).** One or more vision models score the image over a grid. **This is
the detector.** On the matched benchmark a single `claude-sonnet-5` call scores **0.932**
(landscape 0.97, portrait 0.83). Everything else in the stack is currently decoration on top of it.

**Axis 2 — Context router.** Untouched by this session's measurement. Its earlier contribution
(real-art false positives 16 → 2) was measured on the confounded set and has not been re-derived.
**Status: unverified.**

**Axes 3 + 4 — Spectral and mixedness are largely ONE axis.** `spectral.slope` correlates with
`mixed.blur_ratio` at **r = 0.97**; `hf_frac` 0.96; `spec_entropy` 0.92. Both are measuring global
high-frequency energy in two coordinate systems. The genuinely independent content of the spectral
route is **`resid_rms` / `one_over_f_r2`** — the *resonance* residual, max |r| 0.32 — which is what the
axis was designed around in the first place.

**The whole free stack spans 2.82 effective dimensions.** Eigendecomposition of 23 features across all
axes: PC1 (57% of variance, sharpness) and PC2 (10%, predictability asymmetry) carry all the label
signal; PC3–PC5 carry none (|d| 0.015–0.069). **More features made performance worse** — all 23
sign-aligned scored 0.789, while the best *pair* scored 0.931, because 21 of 23 sit on one direction
and drown the other.

**The real independence axis is observer TYPE, not vendor.**

| pair | correlation |
|---|---|
| claude vs claude (same model, two samples) | 0.94 |
| gpt vs gemini | 0.91 |
| claude vs grok (most independent models) | 0.70 |
| **semantic reader vs spectral reader** | **0.14** |

Changing the *kind of question* buys roughly five times the independence of changing vendor. This is
the single most actionable architectural finding in the project.

---

## 3. Benchmark results

**Set:** 12 real / 14 AI portraits, 21 real / 11 AI landscapes. AI spans six generator families
(flux-2-pro, gpt-image-2, nano-banana, nano-banana-pro, seedream-5-pro, davinci). Real from many
photographers and cameras. Both classes resized to 512 px and re-encoded through one identical JPEG
q85 path. **AUC computed within each content bucket and pooled**, so "portrait vs landscape" cannot
masquerade as "AI vs real".

### The vision committee

| roster | score AUC | seam signal \|d\| |
|---|---|---|
| **claude ×1** | **0.932** | — |
| claude + gemini (the v6 roster) | 0.930 | 0.229 |
| claude ×2 (same model) | 0.917 | 0.214 |
| claude + gpt | 0.912 | 0.284 |
| 4 families | 0.902 | 0.347 |
| claude + gpt + grok | 0.897 | **0.365** |

Two facts, both important:

- **Adding observers does not improve the score.** It declines monotonically. One call is the best
  scorer.
- **Observer diversity does improve the disagreement signal**, monotonically, with the same-model
  control at the bottom (0.214 → 0.284 → 0.365). Across rosters, **corr(score, seam) = −0.91**:
  reinforcement and independence are the two ends of one dial.

### The free axes

**Nothing exceeds |AUC − 0.5| = 0.164.** The strongest are `one_over_f_r2` (0.664) and `resid_rms`
(0.338), and their value is that they are **consistent across both content buckets** (0.65/0.68 and
0.34/0.34) rather than large.

### What the old numbers became

| measure | old (confounded) | matched |
|---|---|---|
| photo committee headline | 0.952 | — *(image sets missing; unreproducible)* |
| `spectral.slope` | 0.907 | **0.617** |
| `mixed.blur_ratio` | 0.882 | **0.424** |
| `nonlocal_asymmetry` | 0.858 | **0.454** |

---

## 4. The seam map — the headline feature, and it does not work yet

Tested on **13 matched pairs from a phone**: the original photo and a generative edit of it, both
saved, so diffing them yields a pixel-exact mask. Edits span **0.22% to 51.6%** of the frame. This is
the only test in the project whose ground truth is a mask *inside one image* — camera, lens, sensor,
processing, compression, content and lighting are identical on both sides of the seam, so **every
confound cancels exactly.**

| | edited | control (untouched original) |
|---|---|---|
| **committee — edited cells score lower** | 0.538 (6/13) | 0.478 (7/13) |
| **committee — edited cells disagree more** | 0.477 (5/13) | 0.506 (7/13) |
| **`spec_dev`** (1/f residual) | **0.641 (10/13)** | 0.417 (4/13) |
| **`nl_asym_dev`** | **0.643 (10/13)** | 0.519 (7/13) |

**The committee cannot localise.** Its edited arm and its control arm are the same number — it is
reacting to regions, not edits — and localisation *anti*-correlates with edit size (r = −0.58), so
resolution is not the excuse.

**The free spectral reader can, weakly.** `spec_dev` and `nl_asym_dev` both fire on 10/13 with a clean
control. This is the first localisation signal in the project, it is free, and it comes from the same
resonance residual that was the only survivor of the matched benchmark. **Two unrelated tests, same
last measure standing.**

Image-level edit detection is weak and not significant (+9.6 points, 8/13, mean/se 1.89) — and where
it fires it is **semantic**: the largest score drops came from the *smallest* edits. The committee
responds to implausibility, not to manipulation artifacts.

---

## 5. Honest ledger

**MEASURED AND SOLID**
- Vision committee at **0.932** stratified on a content- and compression-matched, six-generator set.
- Spectral and mixedness are one axis (r = 0.97); the free stack spans 2.82 effective dimensions.
- Sign misalignment between the two occupied directions collapses a committee from **0.926 to 0.505** —
  chance. Never inherit a sign; fit it.
- Observer *type* buys ~5× the independence of observer *vendor* (0.14 vs 0.91/0.94).
- Adding observers does not improve the score; observer diversity does improve the disagreement signal.
- **Plain averaging beats every reasoning variant.** Debate collapsed the seam signal to 0.152 —
  *below* the same-model floor of 0.214, i.e. three model families became more correlated with each
  other than one model is with itself.
- Content confound: changing only the content of a real photo reproduces **54–77%** of the apparent
  signal.

**MEASURED AND PROMISING, NOT YET A CLAIM**
- `spec_dev` / `nl_asym_dev` localisation (0.64, 10/13, clean control). Caveats: n = 13, and every
  measure anti-correlates with edit size because the within-image baseline is a median that a large
  edit contaminates. **A robust baseline is the single highest-value fix available.**
- `env_scale_agreement` (the environment-as-bridge measure): AUC 0.750 and **off the existing frame**
  (|r| 0.21 / 0.27) — but n = 11, and on the matched set it fell to |d| 0.143.

**UNTESTED**
- The context router.
- The recursive zoom layer.
- Seam localisation on anything but this one editing toolchain.
- Whether any of this survives the next generation of generators.

**BLOCKED ON DATA**
- **Optics-consistency measures need unprocessed files.** Chromatic aberration is stripped by every raw
  converter; the blur↔spectrum balance law could not be fitted because JPEG truncates the
  high-frequency tail (σ degenerate in 49% of cells). Two independent measures, same wall. Needs
  PNG/raw pairs.

**RETIRED**
- The 0.952 headline. Its image sets are not on disk and it predates every confound control.
- "Four orthogonal axes." Two of them are one axis.
- The reconstruction axis as a headline route — one sub-measure (`return_at_low`) survived the old set
  at |r| 0.61 and is untested on matched data.

---

## 6. Why this is still worth building

The previous version claimed the moat was interpretability — a seam map instead of a black-box score.
**That feature is not demonstrated**, so the claim cannot be made. Three things are real:

**One thing the frontier models cannot do.** Asked to localise a real generative edit against a
ground-truth mask, a three-model committee scores **0.538 against a control of 0.478** — nothing. The
free spectral reader scores **0.641 on 10/13 with a clean control**. That is the only place in this
project where a framework-derived measure beats the models outright, and localisation is the one part
of this problem that is *not* commoditised. It is n = 13 with an unfixed artifact, so it is a
hypothesis, not an asset — but it is the only one left.

*Note: the free reader does **not** help the verdict. Tested directly: semantic alone 0.927, semantic +
spectral 0.887. Independence is necessary but not sufficient — at 0.662 the second reader is too weak
to add. See `FOLDING_TWO_CONES` Part IV.*

**The resonance residual.** It has been the last measure standing in two unrelated tests, and it has a
mechanism: a photograph's spectrum is *emergent* (photon statistics plus scene scale-invariance) while
a diffusion patch's spectrum is *constructed* (the schedule commits frequencies in order; the decoder
imprints its own periodicities). That is why the **residual** discriminates and the **slope** does not.

**The methodology.** Compression parity, content stratification, same-model controls, pre-registered
bars, false-positive control arms, and a watermark check that caught six images that would have faked
a triumph. Most detector claims in this field do not survive these. **A benchmark harness that
reliably kills your own results is an asset**, and it is why the numbers above can be trusted at the
precision they are stated.

---

## 7. Roadmap

1. **Robust within-image baseline.** Replace the median with a trimmed estimator so a large edit stops
   contaminating its own reference. Directly tests whether the size trend is an artifact. Free, hours.
2. **Extend the manipulation set to ~50 pairs** across at least two editing toolchains, **exported as
   PNG**. Settles the localisation signal *and* unblocks both optics measures at once.
3. **Ship the honest product now:** one semantic call for the verdict (0.932) plus the free spectral
   reader as a second opinion. Do not ship a seam map.
4. **Re-run the context router** under stratification; it is the only untested axis that once showed a
   real effect.
5. **Test a third observer type** (the physics/environment reader) against both. If type diversity is
   the real axis, it should land near 0.14 against each.
6. **Re-test Gemini** on a funded key in the committee slot for the XPRIZE roster claim — it was
   quota-blocked, then only available as `gemini-2.5-flash`.

---

## 8. Artifacts

**Code:** `shovelcat_free.py` (two-atom free detector, polar verdict), `bench_all_axes.py`
(stratified, parity-enforcing harness with a built-in cross-axis independence audit),
`committee_experiment.py`, `seam_localize.py`, `within_image_observers.py`, `nonlocal_observer.py`,
`environment_observer.py`, `reconstruction_observer.py`, `lens_observer.py`, `balance_observer.py`,
`debate_experiment.py`, plus the existing `spectral_observer.py`, `mixedness_observer.py`,
`shovelcat_checker_v6.py`.

**Metrics:** `bench_matched.json`, `committee_cache.json`, `seam_results.json`,
`within_image_results.json`, `balance_results.json`, `lens_native.json`.

**Design docs (project):** `FOLDING_COMMITTEE_TEST`, `FOLDING_MATCHED_BENCHMARK`,
`FOLDING_OBSERVER_FRAME`, `FOLDING_AXIS_INDEPENDENCE`, `FOLDING_OBSERVERS_AS_D`, `FOLDING_SEAM_TEST`,
`FOLDING_WITHIN_IMAGE`, `FOLDING_TWO_CONES`, `FOLDING_BALANCE_LAW`, `FOLDING_PHYSICS_OBSERVER`,
`FOLDING_ENVIRONMENT_BRIDGE`, `FOLDING_AXIS_INNER_SHELL`, `FOLDING_TWO_SIDED_WINDOW`,
`FOLDING_RECONSTRUCTION`, `FOLDING_DEBATE_AND_SEAM_DATA` — grounded in the tested `FOLDING_OBSERVERS`,
`FOLDING_UNIVERSAL_READER`, `FOLDING_SKIN_DETECTOR`, `FOLDING_PIXEL_TRANSMISSION`, `FOLDING_FLOORS`,
`SPARSE_VESICA_EXPANSION` §18.19.
