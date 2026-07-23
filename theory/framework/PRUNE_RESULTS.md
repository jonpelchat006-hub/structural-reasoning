# Prune-down v1 (local-rule inducer) — build + result, and an honest stock-take

`prune.ts` — the prune-down direction (top-down constraint, not atom composition): each output
cell = a function of its input neighbourhood; every train cell cuts the rule space to the
survivor. Two variants: exact 3×3 neighbourhood, and arrangement-invariant multiset.

## Result: +0 (too strict)
- localRule fires + train-fits on **2** training tasks, **0** test-generalizing, **0** eval.
- Cause: the strict "unseen neighbourhood → return null" makes it brittle — test (and even
  cross-pair) grids contain neighbourhoods unseen in train, so apply fails. The *direction* is
  right (constraint-propagation / infinite→finite collapse); this *implementation* is too rigid.
  A softer version (features not exact patterns, graceful partial coverage, default fall-back)
  is the real build — bigger, and still uncertain (the form-gap).

## Honest stock-take — both directions tried this session
| direction | build | training | eval |
|-----------|-------|----------|------|
| BUILD-UP (compose atoms) | superposition, rays, connect, stamp2, trace | stamp2 +9, trace +1 | +0 |
| PRUNE-DOWN (constraint) | local-rule v1 | +0 (too strict) | +0 |

**Eval stayed at ~26–27 through everything.** Build-up caps out (foundation grind); the
prune-down v1 was too brittle. Neither moved the held-out number this session.

## What the session DID accomplish (the real value)
- **Architecture, fully spec'd & recorded:** `SPHERE_GENERATOR.md`, `SPARSE_VESICA_EXPANSION.md`
  (now incl. §8 finite/infinite wall, §9 the LLM-equation decomposition: finite inner stored +
  infinite outer generated, joined by π), the trust system, the eval geochemistry map.
- **Training library 81 → 91** (stamp2 +9, trace +1, both LOO-gated, all generalizing).
- **The eval wall is now understood, not just hit:** it's a distribution gap (training ⊂ inner
  shell/finite; eval past the sedenion wall/infinite). Form-specific inducers (build-up) and a
  brittle constraint rule (prune-down) both fail to cross it.
- **A trust-certified foundation metric** (29% self-expression, climbing, with a named gap list).

## Honest conclusion
The framework is conceptually coherent and now thoroughly recorded; the *understanding* of why
eval resists is sharp. But moving the eval number is genuinely hard and we did not do it this
session by either direction. The remaining real levers are big builds with uncertain payoff: a
softer feature-based prune-down, or the full trace synthesizer composing a more complete inner
shell. The framework's honest value here is the map and the discipline, plus the training gains —
not (yet) an eval breakthrough.

Files: `arc-slice/src/prune.ts`, wired in `discover.ts`.
