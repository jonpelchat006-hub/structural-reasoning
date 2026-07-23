# Trace synthesizer v1 (the geo-format distillation) — build + result

`trace.ts` — v1 of "everything becomes a trace": anchors (bubbles = isolated markers)
connected by straight segments (H/V/45°-diagonal) under a learned pairing rule (allStraight
/ sameColor / nearest) + colour, induced from the train demo and replayed. Generalizes
`connect` (consecutive H/V only) to arbitrary anchor pairs + diagonals. LOO-gated.

## Result
- **Training: +1 net-new** (`1f876c06`, a diagonal-connect task `connect` missed). Library 90 → 91.
- **Eval: +0.** Same as rays/connect/stamp2.

## The pattern, now locked in across 5 builds this session
| build | training net-new | eval net-new |
|-------|-----------------|--------------|
| cos²θ superposition | 0 | 0 |
| rays / connect (fixed motifs) | ~0 | 0 |
| **stamp2 (learned sprite decoder)** | **+9** | 0 |
| trace v1 (segments between bubbles) | +1 | 0 |

**Training keeps gaining (81 → 91); eval is stuck (~26–27).** Every inducer is a *per-task
learner* (reads each task fresh), yet they transfer to more *training* tasks and **nothing**
to eval. The reason is a genuine **distribution gap**, not a search or memory failure: the
inducer *forms* (sprite, straight-segment) were shaped by the task-types present in training,
and eval's generative tasks have *different forms*. Per-task-fresh is necessary but not
sufficient — the form still has to match.

## What actually moves eval (the honest read)
Not another form-specific inducer (each adds 0–1, and 0 on eval). The only structural lever
left is the **full trace synthesizer** — the complete geo distillation, not the v1:
- **per-bubble inner shells** (each anchor offers line/stamp/fill/turn, not just a segment),
- **erdős-style anchor placement** (choose bubbles by max incidence, the orchard principle),
- **composable pen-programs** (sequences of moves: the actual turtle DSL, induced + θ-gated),
- **curves/repeats/fills** (the geo trace's full vocabulary, the epicycle generality).
That is a research-scale build whose payoff on eval is genuinely uncertain (the form-gap may
persist), but it is the only thing that doesn't bake in a single form — so it's the one with
a structural chance at eval's diverse generative tail.

## Status (banked, honest)
- Training library: **91** (stamp2 +9, trace +1, both LOO-gated, all test-generalizing).
- Eval: unchanged. The trace ARCHITECTURE is validated as the right general basis; the v1
  (segments only) is too narrow; the full turtle synthesizer is the open frontier.

Files: `arc-slice/src/trace.ts`, `arc-slice/src/draw2.ts`, `arc-slice/src/discover.ts` (wiring).
