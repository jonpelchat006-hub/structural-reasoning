# Movement — testing the recent ideas on spatial tasks instead of the detector

*The detector kept hitting the content-confound wall (`FOLDING_GALAXY_BRIDGE` §4: the low-level stack is
near chance once content is matched). Movement is the framework's **native** material — `moveToContact` /
`gravity` motor ops (`INNER_SHELL`), the **jet as force-cancellation** (`jet.ts`, INNER_SHELL log 12), the
**meet-in-the-middle double bounce** (`SPARSE_VESICA` §18.3), the **min-cut seam** (the trail / doorway),
the **IK redundancy-manifold** already written in `FOLDING_SKIN` §3.3. So it's a better testbed:
self-generating, exact ground truth, no confound. Experiments run live (Aug 2026): `movement_testbed.py`,
`growth_web.py`, `growth_muygps.py`, `memory_clip_web.py`, `bottle_closure.py`, `memory_bubble.py`,
`second_wind.py`, `ship_repair.py`, `crisis_creativity.py`. Design-stage: toy scale, but clean numbers.*

## Test 1 — Redundant-arm IK (fine motor): the .14 reserve is load-bearing (WIN)
5-link planar arm reaching a 2-D point → 3 redundant DOF. **A** = damped-least-squares reach only; **B** =
same reach **plus the null-space** (the redundant *reserve*) pushing joints toward comfort.

| method | reach success | joint-limit hits | mean nearest-limit margin |
|---|---|---|---|
| A — DLS reach only (baseline) | 77.0% | **197 / 300** | 0.104 |
| B — DLS + null-space reserve | **87.3%** | **41 / 300** | **0.597** |

- Keeping the reserve open reaches +10 pts **and** saturates a joint ~5× less with a 6× healthier margin.

## Test 4 — Metabolic reserve: the endurance law — CONFIRMED
Reserve as a tank R0 refilled at supply `s`, drained at demand `d`. Measured TTF matched **R0/(d−s) to the
tick**; **d ≤ s → sustainable forever**; recovery = `depleted/(s−d)` exactly.

## Test 5 — Growth into the empty tail: capability expansion
Each fiber is a tuning curve; growth = on failure allocate a new fiber at that load and refit. Frontier
0.75 → 0.98 with growth; fixed fibers on the same tail data gain **nothing** — the vocabulary ceiling.

## Test 6 — Growth on a real GP (MuyGPyS): variance = know-what-we-don't-know + demand
MuyGPyS predictive variance reads 0.75 in a gap vs 0.05 covered (~15×). Growth = variance × demand reaches
lower query error with fewer fibers and 0 wasted on the queryless "Pluto" region (left at variance 0.978).

## Tests 7–9 — The memory arc: clip at the gap → context seals the return → the window of time
21/21 clips resolve gap→anchor (variance drop 0.322), revisit worst-first pays 18% less error (T7); the
return round-trip error drops 0.214 → 0.013 with the real branch/scene context (T8); the missing coordinate
is a **window of time** — 1 frame → velocity RMSE 1.45, 2 frames → 0.016 (Takens delay-embedding, T9).

## Tests 10–12 — The golden-field reserve's three faces
One budget can't be intelligent: NONE 81/200 (burns out at a fixed reach), ALWAYS-on adrenaline crashes the
mass to 0 (85/200), GATED second-wind 134/200 (T10). Sail+patch survival: sail-only dies at event 32,
always-unfold at 58, survival-gated survives all 140 on 22 surgical unfolds (T11). Crisis creativity: rigid
0/240, always-hot 63/240, crisis heat-spike+cool 222/240 (T12, simulated annealing across a rule-border).

*(This is the abbreviated repo copy; the full working doc with all grounding citations lives in the
FOLDING_SYNTHESIS ledger and the session project. Tests T1–T12 are results #1–#12 in the ledger.)*
