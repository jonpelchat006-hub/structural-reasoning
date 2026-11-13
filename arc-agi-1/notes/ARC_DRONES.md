# ARC drones — many programs land the same spot, they mostly agree (confidence) and sometimes diverge (under-determination)

*Session Aug 2026. Testing Jonathan's drone decomposition: a drone = the program/work that solves a task;
many different algorithms can solve one task (trig vs derivatives) as drones on different sides of the arm,
ending at the same spot; dead drones mark where not to go and can cut bad paths before flying them; when a
whole region dies, fold to where they're alive and throw a second arm. `arc_drones2.py` (multiplicity),
`arc_vote.py` (agreement/vote), `arc_drones.py` (failure-buffer prune). Figure `arc_drones.png`. Follows
`ARC_SOLVER_V1.md`, `ARC_RATCHET.md`. Grounds in `swarm-core.ts` FailureBuffer, SPARSE_VESICA §18.5
balancing filter, RESULTS.md "better search re-finds; it doesn't invent".*

## A) Multiplicity — CONFIRMED, strong (Jonathan's "different work, same spot")
Exhaustive enumeration of op-sequences to depth ≤2 (no state-dedup, so alternative programs aren't collapsed
by a seen-set — the first, buggy run dedup-ed by output state and reported a false mean of 1.00). Per solved
ARC-1 train task, distinct op-sequences that reproduce ALL train pairs exactly:

- **mean 5.74 distinct landing programs, median 5, max 38.**
- **81% of solved tasks have MORE THAN ONE distinct program** (dist: 1 prog ×6, 2–3 ×5, 4–9 ×18, 10+ ×2).

So a task is landed by a whole cloud of drones on different sides — `flipH+transpose`, `rot180+rot270`, and
`rot90` all reach the same 3×3 result; `cropL`, `cropBB+cropL`, `denoise+cropL` all crop to the same content.
Different work, same spot — quantified.

## B) Agreement vs divergence — the honest, subtle part
Do the drones that agree on the *examples* agree on the held-out *test*?

- **27/31 solved tasks: all landing programs AGREE on the test output** — a free confidence signal (a unanimous
  cloud of independent derivations).
- **4/31 DIVERGE** — the train pairs under-determine the answer, and the "different ways to do it" part company
  past the visible data. Concrete: **ed36ccf7** has 7 landing programs → 2 distinct test answers; 5 drones
  (`rot90`, `flipH+transpose`, `rot180+rot270`, …) give the TRUE answer, 2 "dead" drones (the ones that append a
  spurious `denoise`) give a wrong one. **Majority vote (5 vs 2) picks the truth.** Across the 4 divergent
  tasks, majority resolves **3/4** (the 4th, aabf363d, has NO correct drone — it needs an op we don't have, so
  no vote can save it).

**Honest bound on the vote:** majority-vote scores **30/31 = the same as a single arbitrary drone (30/31)** —
no raw-solve gain, because divergence is rare (4 tasks) and a single program is usually already right. The
value of drone-agreement here is **calibration/confidence** (unanimous vs split), not extra solves. This is
also the cleanest measurement in the project of ARC's *under-determination*: only the held-out pair adjudicates
between equally-train-valid programs.

## C) Dead-drone pruning — honest partial null (the failure buffer / balancing filter)
"Cut bad paths before flying them" tested two ways in the beam search:
- **Conservation filter** (SPARSE_VESICA §18.5 balancing): on the 37 train tasks whose train conserves the
  colour histogram, discard any candidate whose grids break the histogram before scoring. **Result: 0.8% fewer
  node expansions, solves preserved (29→29).**
- The state-dedup `seen`-set is the other half of the failure buffer and already runs.

The conservation prune barely bites because it **overlaps the agreement beam** — a histogram-breaking candidate
is usually also a low-agreement candidate the beam already drops. The failure buffer is not additive *on this
search*; it would matter more in a wider/unpruned search or across tasks (transferable dead regions), which is
the `swarm-core` FailureBuffer's intended regime.

## D) Fold-to-living second arm — already measured 0 extra
Jonathan's "keep sending drones, they die from a cloud we can't see, fold to where they're alive and throw a
2nd arm" is the ratchet re-anchor. `ARC_RATCHET.md` measured it: re-anchoring at the closest-approach (living)
node and searching again lands **0 additional** of the 92 circlers. The fold's value is cheaper reach to
*known* solves, not new solves — the circler gaps are missing primitives, not distance.

## What this pins down
Two of the four drone sub-ideas are **confirmed and quantified** (multiplicity — a task is a cloud of
equivalent programs; agreement/divergence — mostly unanimous, a usable confidence signal, occasionally
under-determined). Two are **honestly bounded** (the failure-buffer prune overlaps the existing beam; the
fold-to-living arm adds no solves). The through-line is unchanged from `ARC_SOLVER_V1`/`ARC_RATCHET`: search
machinery (drones, votes, ratchets, buffers) **re-finds and re-scores what the operator set already allows**;
the one lever that adds reach is **new primitives** (induction + prior-derived ops, `ARC_SOLVER_V1` v3). The
drone cloud is what a *good* op set will make dense and self-verifying — its agreement is the confidence, its
divergence is the honest flag of ambiguity — but it does not, by itself, break the eval wall.

*Honest bound: all numbers are ARC-1 train, exhaustive depth≤2 or the depth-3 beam. Multiplicity mean 5.74 and
81%-multiple are solid; the vote gain is a true null (30/31 = 30/31); the conservation prune is 0.8% (overlap);
fold-to-living is 0 (ARC_RATCHET). Scripts live in the session and can be added to the repo's ARC thread.*
