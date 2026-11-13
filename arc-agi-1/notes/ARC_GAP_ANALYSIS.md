# ARC-AGI-1 gap analysis — where the solves live (the "analyze first" step)

*Session Aug 2026. Pulled the public ARC-AGI-1 dataset (400 train / 400 eval) and profiled the training set
to map where progress can come from, before building. Honest floor established; one self-caught overcount
corrected. `arc_baseline.py`, `arc_profile.py`, `arc_crop_fix.py`, `arc_gap.py`; figure `arc_gap.png`.*

## The honest solve ladder
- **Trivial geometric** (rot/flip/transpose, applied only when it maps every train pair): **7/400 = 1.8%**.
- **Honest cheap families** (first-match, each rule must actually *produce* the output and pass the test
  pair): geometric 7 + recolor-map 4 + real crop (bbox / largest-object) 3 + tiling 1 = **15/400 = 3.8%**.
- **Existing model-free solver** (repo thread 1, on the author's machine): **66/400 = 16.5%**.
- **Frontier** (top systems): far above — the gap is the work.

**Honesty note (self-caught):** a first pass counted a "crop-subgrid" solver at 30, but it only checked the
output *is* a contiguous subgrid of the input — i.e. it confirmed the answer exists somewhere in the input
without a rule to extract it. That is not a solve. Replaced with real extraction rules (crop to non-bg
bounding box; crop to the largest object), which solve **3**. The 3.8% is the honest cheap-family ceiling.

## Structural distribution (by output-shape relationship)
| bucket | tasks | share | typical operations |
|---|---|---|---|
| **same-shape** (in==out shape every pair) | **262** | **66%** | recolor, denoise, fill, gravity, complete, object-recolor, symmetry-repair |
| fixed output size (all outputs one size) | 76 | 19% | count / summarize / select-one |
| output smaller | 46 | 12% | crop / extract / select an object |
| output larger | 16 | 4% | tile / scale / mirror-out |
| variable | 0 | 0% | — |

## The tractable frontier
- **Same-shape is the big bucket (262), and cheap solvers barely touch it.** Inside it, **130 tasks change
  fewer than 15% of cells** — the *local-edit zone* (denoise, fill a hole, complete a pattern, recolor an
  object). This is the most tractable next push and exactly where **object-perception + local rules** apply.
- **55% of all tasks have ≥3 objects** — object-centric reasoning (segment → per-object rule) is central.
- **33% introduce new colors in the output** (110 of them same-shape) — these need a source for the new
  color (a palette rule, a mapping from position/shape), not just rearrangement.

## Where the baby-brain architecture plugs in
- **Perception lenses (#55):** ARC grids are exactly the pixel domain — an object/segmentation lens, a
  symmetry lens, a color-map lens, a size-change lens. Pick the right lens per task = earn the task signature.
- **Memory/discovery (#51):** retrieve a solved task by signature-resonance (the repo solver already does a
  version of this), then adapt; discover a new rule on a miss and fold it in.
- **Inner-shell primitives (framework `INNER_SHELL`):** the same-shape local-edit ops (fill, denoise,
  recolor-by-object, gravity) are a small primitive set that could lift the same-shape bucket materially.

## Recommended next step
Target the **same-shape local-edit bucket** (130 tasks): build an object-segmentation lens + a small set of
honest local-edit primitives (recolor-by-object, fill-enclosed, denoise, symmetry-complete), each verified
to reproduce all train pairs before applying to test. Measure exact-solve count against the 3.8% cheap floor
and the 16.5% existing solver — every solve reported with whether it generalizes to the held-out test pair.
