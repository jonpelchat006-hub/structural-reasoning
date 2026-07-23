# Cleanup — resolve every pixel into A / B / nothing; what is irreducibly BOTH

*Companion to `FOLDING_CUT_SERIES.md`, `FOLDING_ALIASING.md`, `FOLDING_THE_KNIFE.md`. Jonathan: don't *cut* the mixed pixels away (that failed — power law); *clean* them so every pixel becomes a definite A, B, or nothing (the +1/−1/0 trinity). Tested on 6 proteins; `cleanup.py`.*

## Result — cleanup works, except for a ~15% woven core (CONFIRMED)
Winner-take-all on the field s = d(A)−d(B): before, ~**58%** of interface voxels look mixed; after, they resolve into clean A ~37%, clean B ~40%, thin void ~8% — a crisp A/B/void trinity for ~85% of the interface. The irreducible residual: **~15%** of voxels contain atoms of *both* domains interpenetrating — genuinely both, uncleanable, the **woven** part.

## The convergence — it is all the same object
The ~15% irreducibly-both matches the ~13% floor a *series of cuts* couldn't cancel. Four operations hit the same core: bits (web ~98% unexplained), one cut (~40% biased), many cuts (~13% floor), cleanup (~15% both). The ~13–15% woven core is **the web made physical** — pixels where the two domains interpenetrate so no local operation can separate them. Achieved: a crisp readable A/B/void boundary you can do logic on. Limit: computing it needs the field s (the web), so it makes the boundary readable, not predictable; and the ~15% core survives every local operation — the wall.

*Artifacts: `cleanup.py`, `cleanup.png`.*
