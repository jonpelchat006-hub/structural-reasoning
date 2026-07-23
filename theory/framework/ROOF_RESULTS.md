# Building the roof — the first per-task tool, and an honest result

The floor (trust-audit kitchen) reached 85% and ran out of fixed-atom bricks: every remaining gap
is a *roof* op (per-task arrangement). So the next tool had to be a roof tool — per-task induction,
built with the bridge mechanics (SPARSE_VESICA §12): superpose candidate panels, register the right
one by its non-smoothness lock, search the combine rule, **remember** which rule fit (the grooves).

## What was built — `src/roof.ts`, `induceRegisterCombine`
A discovery inducer for the **panel-combine** family (a new capability — output is HALF the input,
which no existing same-dim residual inducer covers):
1. **Split** the input into two equal panels A,B (by a constant-colour divider line, else by halves).
2. **Register** B by trying its dihedral orientations (id, flipH, flipV, rot180) — the "rotate until
   it meshes" lock.
3. **Search the combine rule**: learn the 2×2 truth table T[a_on][b_on]→on/off, keeping the one
   that **locks** (is consistent) across *all* train pairs (= the grooves/memory recording the fit).
4. Require the rule to depend on *both* panels (not a trivial copy), single painted output colour.

## Result — the mechanism works; the coverage does not extend
- **Fires on 9 eval tasks** (`identity_registerCombine:9`) — the most of any single kind in the run.
  The roof machinery genuinely solves real panel-combine tasks end to end (split→register→lock→paint),
  passing the leave-one-out gate and the held-out test check. **The dream-layer mechanism is validated.**
- **+0 net-new on eval.** All 9 were already in the verified-26 set; the run's one net-new
  (`d4b1c2b1`) came from an unrelated inducer (scaleByFeat). On training likewise: its solves were
  already in the banked library, so 0 new there too.

## The honest read
- **A roof tool is real and runnable.** This is the first piece of the per-task synthesizer actually
  built and tested, and the bridge mechanics (register + lock + rule-memory) work as a solver.
- **One roof tool catches its slice, then hits the same diversity wall.** The panel-combine slice was
  already covered; the *uncovered* eval tasks are each a different per-task rule. Adding specific roof
  tools one by one will re-hit the wall every build hit — eval is a maximally diverse independent set.
- **The frontier is now sharp:** crossing needs the roof to be **general** — induce an *arbitrary*
  per-task rule from the examples — not a growing library of specific roof tools. The mechanics built
  here (split/register/lock/memory) are the right engine; what's missing is generality over the rule
  space, which is the real open research (the same conclusion every floor probe reached, now reached
  from inside the roof with a working tool in hand).

Files: `arc-slice/src/roof.ts`, wired in `src/discover.ts` as `["registerCombine",induceRegisterCombine]`.

---

# §13.4 — the ability-draft wired into the solver (built + measured)

Built `arc-slice/src/ability_draft.ts`: each of the 24 inducers tagged with a (slot × effect ×
execution) ability coordinate; a LEARN pass runs all 440 training tasks and records which ability
WINS each solve → master success counts; an EVAL pass DRAFTS the learned order per task (reusing
`solveDiscovery`'s existing `order` param) and measures against the fixed-sweep baseline.

## Learned ability prior (training, 75 solves)
Top by success: reflect(8), gravity(8), stamp2, registerCombine(4 — the roof tool earns its place),
colorMap, connect, scaleByFeat, shapeRecolor. 17 abilities ever win; a long tail wins once.

## Eval result (full 400, looGate) — HONEST
| | solved | net-new |
|---|---|---|
| BASELINE (fixed sweep) | 17 | 1 |
| DRAFTED (learned order) | 17 | 1 |

- **Identical solves & net-new.** Expected: with full fallback, reordering the *same* abilities cannot
  add or lose a solve — it only changes tie-breaks. Drafting alone does **not** move eval.
- **But the prior is strongly predictive (the real result):** of the 17 drafted solves, the winning
  ability was in the training-learned **TOP-4 for 11/17 (65%)** and **TOP-8 for 15/17 (88%)**. Per-task
  ability success is **learnable** — the ability that cracks an eval task is almost always one of the
  few the training pass flagged as most successful.

## What this honestly establishes
- **The draft infrastructure is real and correct:** inducers carry ability coordinates, success is
  recorded, the order is learned and applied — §13 is now running code, not just design (§13.1–13.4).
- **Drafting is a learnable prior, not an eval lever by itself.** It buys *efficiency* (try ~8 of 24
  abilities, keep 88% of solves) and is the scaffold for adaptation — but reordering the existing
  abilities cannot cross the wall, because the wall is *missing* abilities, not mis-ordered ones.
- **Consistent with §14/§15:** eval gain must come from raising the **roof-projection** (new per-task
  synthesis capacity / new drafted abilities), not from re-weighting the floor's existing set. The
  draft is the right engine; it now needs new abilities to draft. The wall is unmoved and its location
  is confirmed once more — this time from inside a working, learning draft.

Files: `arc-slice/src/ability_draft.ts`, `ability_stats.json` (learned prior), reuses
`solveDiscovery(train, order, looGate)`.
