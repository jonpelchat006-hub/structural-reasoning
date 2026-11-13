# Trying the framework myself — a self-generated, pre-registered hypothesis on the circlers (1 holds, 1 fails)

*Session Aug 2026. Jonathan asked me to try the framework and generate/test my own hypothesis. I derived one
from the framework's recurring law (`FOLDING_OBSERVERS`: agreement across observers = the invariant;
disagreement = the depth), pre-registered numeric predictions, and tested it on the 93 circlers.
`arc_hypothesis.py`, figure `arc_hypothesis.png`. This is my own idea, honestly measured — half confirmed,
half refuted, and the refutation is the useful part.*

## The hypothesis (mine, framework-derived)
On a circler (arm reaches ≥0.9 agreement but doesn't land), take several near-miss programs ("drones"). Where
they **agree** is the invariant (already correct); where they **disagree** is the depth — and that should be
exactly where the true residual is. Pre-registered predictions:
- **P1** — circler residuals are SMALL & SPATIALLY CONCENTRATED: median wrong-cell fraction < 15%, median ≤ 3
  connected components (the missing op is one *local* operation).
- **P2** — the UNSUPERVISED drone-disagreement map LOCALISES the SUPERVISED residual: IoU(disagreement,
  residual) > 0.3 (chance ≈ residual density < 0.15).

## Result
- **P1 HOLDS (strongly).** Over 93 circlers: wrong-cell fraction **median 5.5%** (mean 5.9%); residual
  **median 3 connected components** (mean 3.8). Each circler is genuinely one **small, local** operation from
  landing — the "one op away" picture confirmed with a size and a locality.
- **P2 FAILS (at chance).** IoU(disagreement, residual) **median 0.06 = chance (0.06)**. Drone-disagreement
  does *not* localise the residual.

## Why P2 failed — the real finding
The near-miss drones collected from a **single forward search share a blind spot**: they all fail to apply the
*same* missing op, so they leave the *same* residual and therefore **agree with each other even where they are
all wrong**. The framework's "disagreement = depth" law requires **independent** observers; near-misses from
one search are correlated by the shared missing primitive, so their mutual agreement is **false confidence at
exactly the blind spot**. This refines `ARC_DRONES`: drone-agreement is a correctness signal only when the
drones are *independent* — a cloud of variations of one search is not, and it is confidently wrong together
precisely where the missing op belongs.

To rescue localisation the framework's own prescription is orthogonal observer *types* (`FOLDING_TWO_SIDED_WINDOW`:
a forward/φ and a backward/ψ observer, accept where they agree) — a forward-arm vs a backward-from-target
observer would disagree at the gap. Untested here; flagged as the way P2 could be recovered.

## What it changes for the build
- **P1 is directly actionable.** The missing op on a circler acts on a small, connected region → build
  **region-scoped enrichment ops**: localise the gap and induce a *local* transform there, rather than
  searching global ops. Localisation comes from the **supervised train residual** (best-output vs train-target,
  which we have), NOT from forward-drone-disagreement (P2).
- **Honest correction to the drones story.** Agreement among correlated near-misses is not confidence; only
  independent-observer agreement is. Use the supervised target on train to localise; reserve drone-agreement
  for *independent* programs (distinct op-sequences that genuinely diverge, `ARC_DRONES` §B).

## Honest bounds
93 circlers, same-shape only (residual/disagreement need pixel alignment). "Drones" here are the top-6 distinct
high-agreement output-sets from one beam — deliberately the correlated set whose blind spot P2 exposes.
Independent-observer localisation (forward vs backward) is not tested. The pre-registration was real: P1's
thresholds and P2's 0.3 were fixed before the run; P1 cleared its bar, P2 came in at chance. `arc_hypothesis.py`.
