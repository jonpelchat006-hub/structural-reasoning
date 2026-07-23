# "Our own version of drawing" — the learned sprite decoder (build + result)

Built three generative draw inducers into `discover.ts` (LOO-gated), the last one being
the real one — a per-task LEARNED decoder, the discrete analog of the epicycle decoder
(`epicycle-mineral-decoder.jsx`): instead of Fourier components, the learned CODE is a
relative-offset SPRITE.

- `rays` (fixed motif) — lines from markers. `arc-slice/src/discover.ts`.
- `connect` (fixed motif) — fill gaps between aligned cells. `discover.ts`.
- **`stamp2` (learned decoder)** — induce, from the train pairs, the sprite (keyed by
  marker-colour) drawn around each isolated marker; decode it at test markers.
  `arc-slice/src/draw2.ts`.

## Result — the draw DECODER works (on training); the train→eval gap is sharp

**TRAINING (LOO-gated, all test-generalizing):**
- `rays`/`connect`: fixed motifs, ~0 unique.
- **`stamp2`: +9 NET-NEW** vs the combined-81 set — `0ca9ddb6 4258a5f9 54d9e175 913fb3ed
  a9f96cdd b60334d2 ce22a75a d364b489 dc1df850`. The single biggest inducer win in the
  session (vs `shapeRecolor`'s +3). The learned-sprite decoder is a strong, general
  generative primitive. Training discovery → ~90/400 (22.5%).

**EVAL (LOO-gated):**
- rays + connect + stamp2: **+0 net-new.** `connect` reproduces one already-solved eval
  task (`aa18de87`); the one overall net-new (`d4b1c2b1`) came from the existing
  `scaleByFeat`. **stamp2 uniquely solves 0 eval tasks.**

## The honest reading — this is the train→eval gap in one experiment
`stamp2` is a *per-task learner* (reads each task fresh, no memory), exactly the kind of
thing that "should" transfer — and it adds **+9 on training but +0 on eval.** That is the
clearest demonstration yet of the central ARC fact: eval is a *deliberately independent*
set, and the generative tail is where its diversity is sharpest. Training has a cluster of
"isolated-marker → fixed-sprite" draw tasks (9 of them); eval's generative tasks (139
INK-ADD) have *different* structure, so a decoder tuned to one sprite-grammar transfers
nothing. The mineral-lineage point, measured: the generative compounds are "biological" —
each its own form — so no single decoder grammar covers eval's tail.

## What this does and doesn't establish
- **Does:** "draw as decoding a learned code" is the right architecture — it produced the
  session's biggest training gain. `stamp2` is a keeper; it grows the library (lineage).
- **Doesn't:** it does not move eval. Moving eval's 139 INK-ADD tasks needs not *one* more
  decoder grammar but a *general draw SYNTHESIZER* — a small DSL of draw ops (stamp, line,
  fill-region, repeat-by-period, mirror-copy) whose parameters AND composition are induced
  per task and θ-validated. That is the generative analog of the deterministic op-search,
  and the honest research frontier (the epicycle decoder is the hint: a *general* basis
  represents any shape; ARC needs a general *draw-program* basis, induced from sparse
  demonstrations).

## Action
- **Bank the +9** into `combined_solved.txt` (training library grows 81→90). `stamp2` stays.
- Eval frontier remains the general draw synthesizer (research), not more single decoders.

Files: `arc-slice/src/draw2.ts` (stamp2), `arc-slice/src/discover.ts` (rays/connect + wiring),
`arc-slice/src/rungen_eval.ts`.
