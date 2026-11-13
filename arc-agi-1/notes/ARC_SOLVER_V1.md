# ARC-AGI-1 solver v1/v2/v3 — the verified library, the eval wall, the composition arm, and induction

*Session Aug 2026. Applying the three-shell architecture to ARC (repo's original solver was inner-shell only).
`arc_solver.py` (v1 library), `arc_solver2.py` (v2 composition arm), `arc_reach.py`/`arc_settle.py` (the reach
+ circling analysis); `arc_induce.py`/`arc_induce2.py` (mechanical induction); `arc_prior.py` (prior-derived
primitives). Figures `arc_result.png`, `arc_circle.png`, `arc_prior.png`.*

## v1 — verified primitive library (inner shell)
Perception segments each grid; a bank of **12 primitive families** (geometric, learned recolor, denoise,
fill-holes, gravity, symmetrize, object-recolor-by-rank, tile, scale, mirror-quad, crop) is tried, each
required to **reproduce every train pair exactly** before touching the held-out test pair.

| set | solved (exact) | vs |
|---|---|---|
| **ARC-1 training** | **28/400 = 7.0%** | cheap floor 3.8%; existing model-free solver 16.5% |
| **ARC-1 evaluation** | **1/400 = 0.2%** | — |

**The eval wall:** only 1 of 400 eval tasks has *any* family fit its train pairs. The eval set is built so
tasks don't reuse the training set's easy types — each needs a novel abstraction. A fixed library transfers
almost nothing. You cannot win ARC with a bigger inner-shell library; that only memorises train task-types.

## v2 — the composition arm (Jonathan's control picture, measured)
Reframe composition as a **flexible IK arm** (result #1): anchored at the input (inner-shell void points),
actuated only by middle-shell "force" (the ops chosen), reaching for the task's **target-spotlight** in the
outer shell. A beam search steered by agreement-with-target (the spotlight pulling the arm) composes ops,
each step verified exactly.

- Composition **holds train at 7.0%** and **triples eval (0.2% → 0.8%, 3 tasks, two of them two-step)** —
  real but small.
- **Circling is real and common (MEASURED).** Closest-approach distribution over 400 train tasks:
  **131 out-of-reach (<0.6)**, **148 approaching (0.6–0.9)**, **92 CIRCLING (0.9–1.0, not landed)**, 29 landed.
  So on **92 tasks the arm orbits within 10% of the target** — Jonathan's "if it circles, it's reachable"
  confirmed: these are close.
- **But 0 of the 92 circlers settle with existing primitives** — not with a global recolor, not with a
  focused 2-ply corrective reach from the closest-approach node. **The last bit of each circler is a
  primitive we do not have.** This is the flex-between-anchored-points, exactly: the arm reaches the
  neighbourhood by bending known ops, but landing requires a **new op developing in the gap** between them.

## v3 — induction: developing the missing op in the gap
Two ways to grow a new op per task, both gated on exact train reproduction (abstain otherwise), tried
directly and folded onto the arm's closest approach:

**(a) Mechanical induction (`arc_induce2.py`).** Learn the op from the task's own train structure:
local-rewrite (neighbourhood→centre lookup, k=1,2), and object-recolour-by-shape-signature. Result:
**composition 28 + induction 5 = 33/400 = 8.2% train** (families {local1:2, obj_shape:2, arm+obj_shape:1});
**eval 3/400 = 0.8%**. Five tasks genuinely formed a new op from their own data that generalised to the
held-out test — real per-task op formation, the flex developing into a connection.

**(b) Prior-derived primitives (`arc_prior.py`) — Jonathan's "middle-shell muscles" idea.** The middle shell
(model priors) has muscles the inner shell hasn't seen and the mechanical enumerator never produces. We
hand-author a bank of GENERAL, parametric ops that priors say grids often do — `connect_collinear`,
`flood_enclosed`, `draw_rays` (orth/diag), `outline`, `complete_symmetry`, `frame` — each param-searched
over present colours and kept only if it reproduces ALL train pairs exactly. Result:
**composition 28 + mech-induction 4 + prior-ops 2 = 34/400 = 8.5% train**; **eval still 3/400 = 0.8%**.

The two prior wins are both `draw_rays (diagonal)` — a **generative** op (from a seed cell, extend rays to
the border): task `623ea044` (1 seed → 20 cells drawn) and `ea786f4a` (1 seed → 4 cells), both verified
non-degenerate (real cell changes, reproduce train, match held-out test). **Neither the arm's BASE ops nor
the mechanical inducers ever PRODUCE this op** — the middle shell proposed a known-good muscle from priors
and the honest gate kept it. This is exactly "bend the arm into a good position we knew was good but hadn't
defined, and add it."

## What this pins down
The 92 circlers are a **curated target**: tasks that are each ~one new primitive away. Induction (both
kinds) confirms the **mechanism** is right — a new op can develop in the gap and generalise — and the
prior-derived bank confirms Jonathan's specific claim that the middle shell can reach primitives the
enumerator can't. **But eval stays flat at 0.8% through every stage.** The wall is not the mechanism; it is
**breadth**: a hand-authored bank of ~7 prior ops adds ~2 tasks, and 4 mechanical inducers add ~5. Moving
eval needs the model proposing **dozens** of candidate ops per task under the same honest gate — a **growing
DSL / program synthesis** driven by the middle-shell model as the op-proposer (the #49/#50 discovery loop,
replacing the hand-written heuristic). That is the real ARC frontier and a substantial multi-session build.

## The control-theoretic frame (Jonathan)
- **Arm** = the program (sequence of primitives); **anchored** at the inner-shell void points (rigid,
  certified ops); **flexible** in the space between them.
- **Force** = the middle-shell models choosing ops; the arm is *underactuated* — an action bends it and the
  tip moves in coupled ways, so the models must learn the control to land the tip (IK, result #1).
- **Spotlight** = the task's target transform, out in the outer shell.
- **Circling** (bounded high-agreement orbit) = solvable-in-principle / close (measured: 92 tasks).
- **Settling / flex** = developing the new connection in the gap that lands the orbit = primitive induction.
  Existing-primitive settle lands 0/92; mechanical induction lands 5; prior-derived muscles land 2 more.
  The gap genuinely needs new structure, and the middle shell can supply it — at small breadth so far.

*Honest bound:* 8.5% train is real over the 3.8% floor; **eval stays ~0.8% at every stage** (library → arm →
mechanical induction → prior ops). The informative result is the diagnosis: "solve ARC" becomes "have the
middle-shell model propose, per task, the many candidate ops the enumerator can't — each kept only by an
exact train gate." Scripts live in the session and can be added to the repo's ARC thread.
