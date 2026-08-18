# Shovelcat AI Checker — State of the Detector

*Measured on a content-matched, compression-matched, six-generator benchmark and on ground-truth
manipulation masks. Where something is untested, it says so. The short version: **one paid axis works and
carries the product; the free axes do not separate classes and are reading content and camera population
instead; the committee does not improve the score; the seam map does not yet localise; and the most
valuable thing built is the discipline that established all four.***

---

## 1. What it is
The checker reads an image and asks whether it was generated or altered. Its organising idea is imported
from tested protein-folding work — *agreement across independent observers is the invariant; disagreement
is the depth* — and the ambition is a **seam map**, not a score. That ambition is not yet met. What works
today is a **semantic reader**: a vision model scoring the image over a grid, at **stratified AUC 0.93**.
What is promising but unproven is a **spectral reader of a different observer type**, nearly uncorrelated
with the first (**r = 0.14**), the only thing in the project that has ever localised an edit.

## 2. Architecture — as measured
- **Axis 1 — Vision committee (paid). This is the detector.** A single `claude-sonnet-5` call scores
  **0.932** on the matched set (landscape 0.97, portrait 0.83). Everything else is decoration on top.
- **Axes 3+4 — Spectral and mixedness are largely ONE axis** (`spectral.slope` ↔ `mixed.blur_ratio`
  r = 0.97). The genuinely independent content is the **resonance residual** (`resid_rms`/`one_over_f_r2`).
  The whole free stack spans **2.82 effective dimensions**; adding more features made it *worse*.
- **The real independence axis is observer TYPE, not vendor:** claude-vs-claude 0.94, gpt-vs-gemini 0.91,
  claude-vs-grok 0.70, **semantic-vs-spectral 0.14**. Changing the *kind of question* buys ~5× the
  independence of changing vendor.

## 3. Benchmark results
Six generator families (flux-2-pro, gpt-image-2, nano-banana, nano-banana-pro, seedream-5-pro, davinci);
real from many cameras; both classes resized to 512 px through one identical JPEG q85 path; AUC computed
**within each content bucket and pooled**.

- Vision committee: **claude ×1 = 0.932** (best); adding observers *declines* the score monotonically but
  *improves* the disagreement/seam signal monotonically (corr(score, seam) = −0.91).
- Free axes: nothing exceeds |AUC − 0.5| = 0.164; the loudest (`slope` 0.907 → 0.617, `blur_ratio` 0.882 →
  0.424) collapsed toward chance once content was matched.

## 4. The seam map — the headline feature, and it does not work yet
On 13 phone original-vs-edit pairs (pixel-exact masks, every confound cancels): **the committee cannot
localise** (edited arm 0.538 ≈ control arm 0.478 — it reacts to regions, not edits). **The free spectral
reader can, weakly:** `spec_dev` fires on 10/13 with a clean control (0.641 vs 0.417). First localisation
signal in the project; n = 13, so a hypothesis, not an asset. *(A known EXIF-orientation defect in ~7/13
pairs is flagged for a mask rebuild.)*

## 5. Honest ledger
**MEASURED AND SOLID:** committee 0.932 stratified; spectral+mixedness are one axis (r = 0.97); observer
*type* buys ~5× vendor independence; adding observers doesn't help the score; plain averaging beats every
reasoning variant; the loud free features are **genre detectors** (15/15 above target on a real-vs-real
control). **PROMISING, NOT A CLAIM:** `spec_dev`/`nl_asym_dev` localisation (0.64, 10/13). **RETIRED:** the
0.952 headline (explained: perfect free separators + two thirds of the real class shown sideways via
un-applied EXIF orientation); "four orthogonal axes" (two are one).

## 6. Why it is still worth building
One thing frontier models cannot do — **localise a real generative edit against a mask** (committee 0.538
vs control 0.478 = nothing; free reader 0.641 on 10/13). Plus the **resonance-residual** mechanism (a
photo's spectrum is *emergent*, a diffusion patch's is *constructed*) and, above all, **the methodology** —
parity, stratification, same-model controls, pre-registered bars, and a real-vs-real control arm that
killed fifteen features in one run. A benchmark harness that reliably kills your own results is the asset.

## 7. Ship the honest product now
One semantic call for the verdict (0.932). Do not ship a seam map. Do not ship the free axes as a second
opinion until one survives a real-vs-real control. Fix the calibration (the verdict ranks well but has no
absolute scale). The interpretability moat is a *hypothesis* resting on n = 13, not a demonstrated asset.

*The measurement code (EXIF-correct loader `image_io.py`, the observers, the parity-enforcing harness
`bench_all_axes.py`) lives on the author's machine and is to be added. The full design docs
(FOLDING_MATCHED_BENCHMARK, FOLDING_OBSERVER_FRAME, FOLDING_TWO_CONES, FOLDING_PHOTO_SET_AUTOPSY,
FOLDING_OBSERVERS_AS_D, …) live in the session project.*
