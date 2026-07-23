# Sparse Vesica superposition — build + result (honest)

Built `arc-slice/src/vesica.ts`: the cos²θ Born superposition with the one thing
`angle.ts` doesn't do — keeping amplitude on **antimatter-setup op1s** (low-cosθ moves
that exist only to spray orthogonally and enable a high-cosθ op2). COLLAPSE = exact verify
on train AND the held-out test split. Run over all 400 training tasks (in quarters).

## Result
| | single-op | 2-step | net-new vs combined | from antimatter-setup |
|--|--|--|--|--|
| total (400) | 26 | 11 | **2** (`4258a5f9`, `694f12f3`) | **0** |

- The superposition **reproduces** the 2 net-new the angular work already found
  (4258a5f9 = update-16, 694f12f3 = update-15). All test-generalizing.
- **The antimatter-setup branch — the superposition's unique addition — contributed 0
  net-new.** Neither the Born (cos²) reweighting nor the orthogonal-spray widening unlocked
  a task the cos-greedy 2-step misses.

## Honest verdict — vocabulary-bound, again, from a new angle
This is the standing law one more time (cf. INNER_SHELL meta-conclusion): **search
reorganization converges to the same set; the ceiling is the OPERATOR VOCABULARY, not how
the search is organized.** The Born superposition is a cleaner, more principled search than
cos-greedy — but it re-finds, it doesn't invent. The antimatter-setup moves don't help
because the 2-op programs they enable aren't reachable with the current ops (the tasks that
need them need a *new primitive* or a generative op, not a better 2-op coupling).

The build is sound and reusable; it just confirms the diagnosis rather than beating it.

## What this means for the eval gap (the real target)
The superposition was the "smallest first step," and it shows the deterministic search side
is saturated. The lever for **eval generalization** is NOT more search — it is the
overfit-guard stack from `MINING_NOTES.md` Tier-1, which picks the *generalizing* program
among train-fitting candidates:
1. **Leave-one-out acceptance gate** — induce on k−1 train pairs, require predicting the
   held-out pair; prefer the candidate surviving the most folds. (`looeval.ts` stub exists.)
2. **Reproduction-consensus + closure-drain scoring** — `lib/agents/{reproduction-test,
   closure-test}.ts`, drop-in, pick the simplest/most-reconstructible program.
These attack the train→eval drop directly; the superposition does not (it's a search-side
mechanism, and search is the part that's already saturated).

Files: `arc-slice/src/vesica.ts` (run: `tsx src/vesica.ts [start] [end]`).
