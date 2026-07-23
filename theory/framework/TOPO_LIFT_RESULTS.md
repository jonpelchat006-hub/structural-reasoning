# The topology lift — the best-aimed shot, and an honest result

The conceptual arc (circle → helix → torus → hole) and the eval data converged on the same axis:
**topology / enclosure** (200/400 eval tasks at 8%, `lift_axis.py`). And the lift mechanism is the
*one* thing that ever crossed anything (update-16, spatial axis). So this was the most justified
lever of the entire effort: validated mechanism, data-identified axis, theory-confirmed.

Built `topo.ts` — topology inducers keyed on holes/enclosure: `holeEncloser` (fill each hole by
its surrounding colour) and `holeRank` (fill by hole size-rank). Generalize the single-colour
`holeFill`.

## Result
- **Training: +2 net-new** (`694f12f3`, `c0f76784`, via holeRank). Library 91 → 93.
- **Eval: +0.** The "hole" match on eval is the *existing* `holeFill` (already solved); the new
  topology inducers added nothing new on the 200 topology tasks.

## The robust conclusion — all three directions now tested
| direction | mechanism | training | eval |
|-----------|-----------|----------|------|
| build-up | compose atoms (stamp2, trace) | +9, +1 | +0 |
| prune-down | constraint/local-rule | +0 (brittle) | +0 |
| **dimension-lift** | **topology (best-aimed)** | **+2** | **+0** |

**Even the best-aimed lever — validated mechanism aimed at the data's biggest gap — added 0 to
eval.** Two specific hole-rules catch the *generic* topology slice; the 200 topology tasks are
*diverse*, each with its own hole-rule. This is the same wall every build hit: eval is a maximally
diverse independent set, and **no finite inducer set — in any direction, however well-aimed —
crosses it**, because each task needs its own specific rule.

## What this honestly establishes
- **The axis is right** (geometry + data + theory all converged on topology) — that convergence is
  real and valuable. The *understanding* is sound.
- **The crossing is not a finite-inducer problem.** Lifting the topology *dimension* is necessary
  but catching the 200 tasks needs **per-task topology RULE induction** — the full general
  synthesizer (induce *this task's* hole-rule from its examples), not a fixed pair of hole-rules.
  That is the open research, and it is the same conclusion reached from every other angle.
- **Pace is fine** (weeks vs billions of years). The achievement is the map and the framework, not
  (yet) an eval number — and the map is now complete and honest: we know exactly where the wall is,
  why it resists, and that crossing it needs per-task induction, not another well-placed brick.

Files: `arc-slice/src/topo.ts`, `lift_axis.py`; framework in `SPARSE_VESICA_EXPANSION.md` §8–10.
