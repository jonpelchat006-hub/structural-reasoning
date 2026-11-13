# ARC ratchet + drones — the mechanism works, but the circlers need new ops, not more depth

*Session Aug 2026. Testing Jonathan's fold-and-reanchor ratchet and the sever-into-drones idea, then the
honest ARC reality check. `arc_ratchet.py`; figure `arc_ratchet.png`. Follows `ARC_SOLVER_V1.md`.*

## The mechanism (Jonathan's picture)
For a solve too far for one arm: reach partway, **fold the arm in** (re-base the frame, which drags the far
solve closer, #47), then throw a **new arm** from the closer base — a ratchet. And **sever** a good
intermediate arm into a **persistent drone** (a reusable waypoint/macro, #54) so later reaches reuse it. The
solve, once found, is spent — **debris** in the outer shell.

## Measured — synthetic reach (the mechanism is real)
- **Ratchet reaches far.** A single bounded arm succeeds only for targets within one reach; **fold-and-reanchor
  succeeds at every distance** (each fold pays a small flex loss but re-bases toward the target).
- **Drones amortize.** Over a stream of clustered targets, severing solved reaches into persistent drones
  cuts cumulative cost far below reaching from scratch each time (compounding, the #51 amortization).

## Measured — ARC reality check (the honest null)
Applying the ratchet (re-anchor at the closest-approach node, search again) to the **93 circlers**:
**0 additional solves** (still 28/400 train). Combined with v2's focused 2-ply settle (also 0), this is
decisive: **the circlers' gaps are not distance/depth.** More composition, re-anchoring, and deeper search do
not land them. **Each gap is a genuinely missing primitive.**

## The conclusion this pins
Across three builds we have now measured what fixed-primitive approaches can and cannot do on ARC:
- v1 fixed library: 7.0% train / 0.2% eval (memorises train task-types).
- v2 composition arm: 7.0% train / 0.8% eval; **92 tasks circle** (reach ≥90% agreement) — close/reachable.
- ratchet + drones: mechanism works in synthetic; **0 extra on the circlers** — the gap is a new op.

**The sole remaining lever is primitive INDUCTION:** synthesise the missing op from the residual structure
(best-output vs target on the train pairs) — genuine program synthesis over a growing DSL — and fold it into
the persistent set. The ratchet (chaining) and drones (reuse) are proven mechanisms that will compound *once
induction exists*, but they cannot substitute for the ops. This is the real ARC frontier and a substantial
build; the 92 circlers are the curated target (each ~one induced op from solved).

*Honest through-line: every lever short of inducing new primitives has now been measured and bounded. That is
the honest map the project is for — we know exactly where the fixed-primitive ceiling is and why.*
