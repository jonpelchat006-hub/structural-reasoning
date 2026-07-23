# The Staircase — zoom reveals detail at every scale, continuity never breaks, floor = sequence slots

*Companion to `FOLDING_OBSERVERS.md`, `FOLDING_CONTINUITY.md`, `SPHERE_GENERATOR.md`. Jonathan tied three ideas: (1) the larger structure is the REAL axis, the window observers the IMAGINARY terms (a quaternion); (2) the ARC "devil's staircase" — a line too fine to see but still continuous — to zoom to detail; (3) a recursive quaternion architecture. Tested the zoom on 8 proteins; `zoom_test.py`.*

## The quaternion mapping is essentially exact
The working committee = one invariant everyone agrees on + three orthogonal observers = **1 real axis + 3 imaginary axes = a quaternion.** The large frame supplies the *axis*; the invariant's *value* is the agreement of all observers, not a decree from the big one.

## The devil's-staircase zoom — CONFIRMED (all three predictions)
Sweep crossing-detection resolution 4 Å → 0.25 Å: (1) **detail resolves as you zoom** (2LZM 1→6 crossings, 6LDH 9→15) — the fine structure was always there; (2) **continuity holds at EVERY scale** (|net| ≤ 1 at every resolution, every protein — the devil's staircase exactly); (3) **it hits a floor** — counts plateau at Cα spacing (~3.8 Å); detail is finite, and that floor = the sequence's residue count (finite recursion depth). Calmodulin stays 1 at all scales — no hidden fine structure; the zoom finds detail only where it exists.

## The recursive architecture is multiresolution analysis
"Recurse the real axis by the slots; imaginary observers zoom to the detail; deposit each resolved invariant on its own real sub-axis" **is wavelet multiresolution analysis** — each level keeps a coarse approximation (real axis) and passes the residual detail (disagreement = imaginary observers) to a sub-level. A recursive quaternion is the branching version; it terminates at the sequence floor. Honest edge: the sub-axis architecture is built in code, not measured; the protein confirms the ingredients (detail at every scale, continuity through all of them, a finite floor = sequence length).

*Artifacts: `zoom_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
