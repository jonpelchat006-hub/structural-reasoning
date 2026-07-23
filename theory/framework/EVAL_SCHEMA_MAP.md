# Eval geochemistry map — which formation schemas does eval ask for?

Characterized all 400 eval tasks by transformation type (the "substrate"), split by
solved (`verified_eval.txt`, 26) vs unsolved (374). Each task labelled with the ONE
formation schema (inducer family) that would form it. Ranked by unsolved yield.
Script: `arc-slice/eval_schema_map.py`.

| formation schema (inducer family) | unsolved | solved | solve% |
|------------------------------------|---------:|-------:|-------:|
| **INK-ADD / DRAW (generate content)** | **119** | 1 | **1%** |
| CROP/SELECT (extract a region/object) | 74 | 15 | 17% |
| OTHER / COMPOUND | 53 | 1 | 2% |
| MOVE / REARRANGE (same content, new positions) | 39 | 1 | 2% |
| RECOLOR (by feature/map) | 30 | 2 | 6% |
| TILE/REPEAT | 27 | 4 | 13% |
| INK-REMOVE / DENOISE | 17 | 0 | 0% |
| SYMMETRY-COMPLETE | 6 | 1 | 14% |
| SCALE-UP | 5 | 0 | 0% |
| SHRINK/REDUCE | 5 | 0 | 0% |

top-5 schemas cover **315/374 unsolved (84%)**.

## The headline
**INK-ADD / DRAW is the dominant unsolved class — 119 tasks (32% of all unsolved),
solved at ~1%.** Eval concentrates on the GENERATIVE schema: drawing/creating content
that isn't a rearrangement of the input. This is the "biological mineral" frontier — the
compounds that must be *grown* (induced per task), not selected from existing content. It
is the single biggest lever by a wide margin, and the place the current vocabulary is
weakest. (Matches the training-side rep-gap finding that INK_ADDED was lowest — but on
eval it is both larger and less solved.)

The second class — CROP/SELECT (74, 17% solved) — is where the antimatter/extraction
sphere already partly works; richer predicates extend it. Everything else is a long tail.

## Ranked build list (formation schemas to add to `discover.ts`), by yield
1. **GENERATIVE / draw inducers (119, ~1%)** — the lever. Per-task "what to draw and
   where," induced from the train delta: draw-by-rule (rays/lines from markers),
   pattern-extend/continue, legend/key-driven stamping, fill-enclosed-by-rule,
   complete-to-template. `gen2` targets this class but isn't reaching eval's drawing tasks
   — widen its induced templates here first.
2. **SELECT/EXTRACT predicates (74, 17%)** — extend the partly-working extraction sphere
   with relational / count-based / odd-one-out predicates (which region/object to keep).
3. **MOVE / REARRANGE (39, 2%)** — induced move-by-vector, gravity-to-target,
   place-by-anchor (the parametric motion families, induced per task).
4. **RECOLOR-by-feature (30, 6%)** — extend the working `shapeRecolor`/`rankRecolor`
   discoveries (rank/shape/position → colour). `discover.ts` is already on this lineage.
5. **TILE/REPEAT (27, 13%)** — tiling with induced period + per-cell transform.

## Honest caveats
- Labels are a heuristic decision-tree on averaged train signals; some tasks mis-bin, and
  **OTHER/COMPOUND (53)** is the residual needing multi-schema *lineage* (compounds-of-
  compounds, no single family). The per-bin solve% uses the small 26-solved set.
- The map names WHICH families to build; building the **generative induction** itself
  (inducing what-to-draw per task, validated by θ on the held-out pair) is the hard part —
  exactly the frontier the whole thread keeps landing on. But the priority is now data-
  grounded: **generative draw first (119), by a 1.6× margin over the next class.**
