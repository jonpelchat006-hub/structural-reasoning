# The void as the 3rd domain — the expectation residual driven to 0, which predicts the surprise's size and place

*Session Aug 2026. Extends `ARC_PERCEPTION_SURPRISE` and `ARC_TWO_PLANES`. Jonathan: the void is a 3rd,
invisible domain — an EXPECTATION path we drive to 0. It is the ALIGNMENT of the φ (real) and ψ (meaning)
planes (their pixel borders lining up), and it PREDICTS the size and location of the surprise. Learning an
operator element (grey clusters ROTATE the pattern, so seeing a new grey cluster tells you what to expect)
pre-applies the transform and keeps the void at 0. The outer shell still needs a wall — not a real wall, a
**wall of 0s**. `void_align.py`, figure `void_align.png`.*

## Grounding — the void is already the corpus's "dissipate-if-compatible" residual
- **Void → 0 = dissipation.** `FOLDING_OUTER_SLOT`: a new element that *aligns* with the structure is absorbed
  and **its residual goes to zero** (θ→1, the Born-alignment cone = the two planes' borders lining up). An
  element that can't be absorbed **persists as a residue**, and **the residue is exactly where a carried rule
  is violated** (`FOLDING_COMBINE_MEMBRANE`) — i.e. the void's nonzero part *is* the surprise, localised.
- **The wall of 0s = the second wall.** `FOLDING_COMBINE_MEMBRANE` IX / `FOLDING_TWO_WALLS`: the workspace
  needs a fixed reference wall (the goal/ATP wall and the void-reserve wall). The outer boundary is a **ring of
  0s** against which the pattern's borders register — not a physical barrier, a zero-boundary that pins
  alignment.
- So the void is the third signal beyond φ (the executed line) and ψ (the meaning cloud): **the alignment
  residual between what the model predicts and what is observed**, driven to 0 when compatible.

## Measured (pattern-rotation game, inside a wall of 0s, 800 games/point)
Operator elements = grey clusters; each rotates a 3×3 region of the pattern every frame. The **void model**
pre-applies the *known* operators and takes the residual against the actual frame; the naive model predicts a
static frame. We sweep the fraction of operators the model has learned.

| operators known | A) en-route void (misaligned cells) | B) predicted-change IoU (where/size, pre-event) | C) goal cleanly isolated |
|---|---|---|---|
| 0% (naive static) | 24.0 | 0.00 | 0% |
| 25% | 18.4 | 0.26 | 0% |
| 50% | 12.7 | 0.50 | 0% |
| 75% | 6.5 | 0.74 | 0% |
| 100% | **0.0** | **0.98** | **100%** |

**A) The void is drivable to 0.** Learning the operator elements collapses the en-route expectation residual
24 → 0. The naive static model carries a large void every frame.

**B) The void predicts where and how big the surprise is, before it happens.** From merely *seeing* the grey
clusters, the void model predicts the change region with IoU rising to **0.98** — "I saw another cluster and
already had an idea what to expect," quantified.

**C) "One surprise at the goal" requires the void driven ALL the way to 0 — a sharp threshold.** The single
real, non-operator novelty at the goal only stands ALONE when *every* operator is known (void ≈ 0). With even
one unknown operator, its rotation (~6 cells of unexplained void) **buries** the goal. Partial operator
knowledge reduces the void gracefully (A) but does not isolate the goal (C). You must learn all the operator
elements before the goal-surprise is trustworthy.

## What this adds to the loop
The void is the **third domain that couples φ and ψ**: 0 when the meaning-cloud's prediction and the executed
frame align, and its nonzero part predicts (size + location) the next disagreement. It upgrades the perception
layer from *reactive* to *predictive*: **operator elements** (learned transforms attached to a visible marker)
are the op-generation spine's task-local primitives used *forward* to pre-cancel the change; **drive the void
to 0 en route** so the only residual left is the genuine novelty (the goal, or an unmodelled dynamic → the
re-plan trigger); the **wall of 0s** is the registration boundary. Threshold lesson: **close the void first,
then read the goal.**

## Honest bounds
Synthetic pattern game, exact truth. Operators handed as known/unknown fractions rather than learned by
interaction — wiring the op-generation spine to induce grey→rotate from watching frames is the next step
(`SPHERE_GENERATOR` J.1; done in `ARC_OPERATOR_INDUCTION`). The sharp goal-isolation threshold depends on
operator changes being sizable (~6 cells); smaller operators would blur it. No claim about the real ARC-3
environment (not loaded). `void_align.py`; scripts live in the session.
