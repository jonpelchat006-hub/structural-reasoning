# The Seam Test — the headline feature fails its first honest exam

*Jonathan supplied 13 matched pairs from his own phone: the original photo and a generative edit of it,
both saved. Diffing each pair yields a **pixel-exact manipulation mask** with no annotation, and edit
sizes span **0.22% to 51.6%** of the frame. This is the only test in the project whose ground truth is
a mask **inside one image**, so camera, lens, sensor, processing, compression, content and lighting are
identical on both sides of the seam — every confound that killed the model-free axes cancels exactly.*

***The committee cannot localise the edits.*** *Cell-level performance is indistinguishable from the
control run on the untouched originals, and localisation gets **worse** as the edit gets bigger
(r = −0.58). Image-level detection is weak, directionally right, and not significant at n = 13.
Companion to `FOLDING_DEBATE_AND_SEAM_DATA`, `FOLDING_COMMITTEE_TEST`, `FOLDING_OBSERVERS_AS_D`,
`SHOVELCAT_CHECKER_V6` §5, `STATE_OF_THE_DETECTOR` §4. Status: MEASURED, n = 13 pairs, 78 calls.*

---

## Part 0 — A trap that would have faked the result

Six of the thirteen edited images carry a visible **"✦ AI-generated content"** watermark stamped by the
phone's editor. The originals do not.

Vision models read text. Left in, they would have scored those six as altered by reading the label, the
"seam" would have landed on the watermark, and the test would have reported a triumph while measuring
nothing. **The bottom 15% of the frame was cropped from both versions** before anything else, and the
masks were re-derived after the crop. All 13 pairs survive.

Recording it because it is a general hazard: **phone and cloud editors increasingly stamp their
output**, so any manipulation benchmark built from consumer tools needs this check before it is
believed.

## Part I — What the pairs give

| edit size (% of frame) | 0.22 · 0.39 · 0.71 · 0.85 · 1.54 · 2.35 · 2.60 · 2.70 · 3.33 · 5.68 · 9.59 · 16.14 · 51.57 |
|---|---|

Masks by direct diff after rotation alignment (7 of 13 were saved rotated 90°), median-filtered and
morphologically cleaned so JPEG re-encoding noise does not register. Spot-checked visually: they land
on an added dog on a road, an object removed from a carpet, a changed blanket, and so on.

## Part II — The result

Three independent families (claude, gpt, grok), 6×6 grid, scored on the **edited** image and — as a
false-positive control — on the **untouched original**, reading the same cells.

| | mean AUC | above chance |
|---|---|---|
| **EDITED — edited cells score lower** | **0.538** | 6/13 |
| **EDITED — edited cells disagree more** | **0.477** | 5/13 |
| CONTROL — same cells, unedited original, score lower | 0.478 | 7/13 |
| CONTROL — same cells, unedited original, disagree more | 0.506 | 7/13 |

**The edited arm and the control arm are the same.** Whatever small per-image deviations appear are
properties of the *regions* — a bit of sky here, a busy corner there — not of the edits. The committee
is not finding the seam.

### It gets worse as the edit gets bigger

**corr(edit size, localisation AUC) = −0.58.**

| | score AUC | disagree AUC |
|---|---|---|
| large edits only (> 5% of frame, n = 4) | **0.357** | 0.482 |

Both below chance. This kills the obvious defence. If the failure were a resolution problem — a 6×6
grid too coarse for a 0.2% edit — performance would *improve* with edit size. It declines. A 16%
edit and a 51% edit are enormous at this grid, and they score 0.26 and 0.04.

## Part III — Image-level detection: weak, real-ish, and semantic

The same pairs asked a different question — not *where* but *whether*. Paired, same photograph:

| | |
|---|---|
| mean global-score drop, original → edited | **+9.6 points** |
| edited scored lower on | 8/13 |
| mean / standard error | **1.89** (≈ p 0.08) |

Directionally right, **not significant at n = 13**. But the shape of it is the interesting part:

| image | edit size | score drop |
|---|---|---|
| 20250531_174853 | **1.5%** | **−57.3** |
| 20250605_162057 | **0.7%** | **−31.3** |
| 20250519_224651 | 51.6% | −24.7 |
| 20250131_195339 | 0.4% | −15.0 |
| 20250611_173518 | 16.1% | +2.3 |
| 20250601_182744 | 5.7% | +0.3 |

**The biggest detections come from the smallest edits.** A 1.5% change cost 57 points; a 16% change
cost nothing. So when the committee does fire, it is responding to **semantic implausibility** — the
edit put something in the scene that does not belong — not to manipulation artifacts, area, or seam
structure.

That is consistent with everything else measured this session: `FOLDING_MATCHED_BENCHMARK` found the
pixel-statistic axes dead while the vision models scored 0.93, and `FOLDING_COMMITTEE_TEST` warned the
models may be reading style and provenance rather than generation. **This is the same finding from a
new angle: the working half of the detector is a semantic reader, and it has no access to the seam.**

## Part IV — What this costs the product

`SHOVELCAT_CHECKER_V6` §5 makes the seam map the deliverable — *"a labeled map, not a scalar"* — and
`STATE_OF_THE_DETECTOR` §5 sells interpretability, *"a seam map and a confidence overlay, not a
black-box score,"* as the moat. `FOLDING_COMMITTEE_TEST` then found the committee's only justification
was localisation, since it does not improve the score.

**On its first confound-free test, the localisation does not work.** Which means, stated plainly:

- The **verdict** product stands. One model call, stratified AUC 0.932 (`FOLDING_COMMITTEE_TEST`).
- The **seam map** product is not supported by evidence. It should not be sold as a working feature
  until it clears this test or one like it.
- The **committee** loses its remaining justification. It does not improve the score
  (`FOLDING_COMMITTEE_TEST`), and the localisation it was supposed to buy does not appear here.

`STATE_OF_THE_DETECTOR` §4 already conceded the blind spot for full-frame regeneration. This extends it:
the blind spot also covers **high-quality local edits**, which is the more common real-world threat.

## Part V — What has not been ruled out

- **n = 13.** Small. The image-level effect (mean/se 1.89) is exactly the size that becomes real or
  vanishes at n = 50. That test is cheap and should be run.
- **One prompt, one grid.** The prompt did say "generated, or digitally altered," so the models were
  primed for edits — but a zoom-and-recheck pass (the designed-but-unbuilt recursive layer,
  `SHOVELCAT_CHECKER_V6` §4) is a genuinely different method and is untested here.
- **The model-free axes have not been run in within-image mode**, and this is the one dataset built for
  it. They failed at *class separation* — "is this image generated." They have never been asked "is
  this region inconsistent with that one," which is the question the reconstruction and predictability
  observers were designed around. `nonlocal_asymmetry` in particular compares a region against the rest
  of the same image, which is exactly this task. **That is the next thing to run, and it is free.**
- These are Google/Samsung generative edits — near state of the art. Cruder manipulations would be
  easier, and a product may only need to catch those.

## Honest ledger

**MEASURED (13 pairs, 78 calls, 3 independent families, 6×6 grid)**
- Cell-level localisation on edited images: score AUC 0.538, disagreement AUC 0.477 — **matched by the
  control on unedited originals** (0.478, 0.506).
- Localisation *anti*-correlates with edit size, r = −0.58; large edits (>5%) score 0.357.
- Image-level paired detection: +9.6 points mean drop, 8/13, mean/se 1.89 — not significant.
- Detection magnitude is unrelated to edit size; the largest drops came from the smallest edits.

**CAUGHT BEFORE IT CONTAMINATED THE RESULT**
- Editor watermarks on 6/13 edited images. Cropped from both versions.

**CAVEATS**
- n = 13; one prompt; one grid size; one family of editing tools.

**NEXT**
- Run the model-free observers in within-image mode on these same pairs. Free, and it is the question
  they were built for.
- Extend to n ≈ 50 pairs to settle the image-level effect.

*Sources: `FOLDING_DEBATE_AND_SEAM_DATA` (the dataset spec this fulfils), `FOLDING_COMMITTEE_TEST`
(0.932 verdict; localisation as the committee's only justification), `FOLDING_MATCHED_BENCHMARK`,
`FOLDING_OBSERVERS_AS_D`, `SHOVELCAT_CHECKER_V6` §4–§5, `STATE_OF_THE_DETECTOR` §4–§5. Artifacts:
`seam_localize.py`, `seam_results.json`, `seam_cache.json`, `seam/`.*
