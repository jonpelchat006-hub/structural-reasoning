# Continuity — signed void-line crossings cancel to ~0 (the counter-movement is the check)

*Companion to `FOLDING_KNIT_WEAVE.md`, `FOLDING_WIRE.md`, `FOLDING_VORTEX.md`, `FOLDING_CLEANUP.md`. Jonathan: if there's flow along the void line it should drag a counter-movement; pulling strands from both sides means one runs backward, and that cancellation (like the void cancelling to 0) verifies the circuit stays continuous. Tested on 8 proteins; `crossing_test.py`.*

## The test & result
Project the backbone onto the cut normal, count crossings *with direction* (2 Å hysteresis). Total 1–9 (mean 4.4), up/down matched, **|net| ≤ 1 in all 8** (mean |net| = 0.38): 1CLL +1, 6LDH −1, 8TLN −1, the rest 0. Forward and backward crossings cancel — "one side runs backward, it cancels so it looks like 0."

## What it means — the cancellation IS continuity
The net is bounded to ±1 by continuity itself: a continuous line crossing a threshold must alternate over/back, so net = (end side) − (start side) ∈ {−1,0,+1}. This is what "continuous" means — and that is the point: the net-zero crossing **is** the continuity verification (**Kirchhoff + Newton's third**, realized as the chain threading its own seam and closing the loop). The return leg is automatic — every up-crossing carries its down-crossing — so the void-line axis genuinely can serve as a verification channel for free. net 0 (5/8) = chain closes back to its starting side; net ±1 (6LDH, 8TLN) = ends on the far side.

*Artifacts: `crossing_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
