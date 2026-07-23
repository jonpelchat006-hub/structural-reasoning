# Aliasing at the Cut — a flat knife can't follow a zigzag void

*Companion to `FOLDING_THE_KNIFE.md` R5, `FOLDING_SLOTS.md`. Jonathan: the true void line zigzags (the 45° digital bisector), but the knife is a flat plane; so a straight cut leaves some A-biased, some B-biased, and only a few true-void spots — the same partial-pixel effect as rasterizing a tilted line. Tested on 6 proteins; `aliasing.py`.*

## Result — the flat cut is mostly biased, split evenly A/B (CONFIRMED, with calibration)
On-cut voxels classified by the true bias s = d(A)−d(B): mean **A-biased 29%, true-void 41%, B-biased 30%**. So **59% of the straight cut lands in biased material, only 41% on true void** — the flat knife can't ride the zigzag; it wobbles to one side or the other. The A and B biases are nearly equal (the aliasing signature — the cut deviates to both sides about equally). Honest calibration: Jonathan said "only a few actual void spots"; the measured true-void is 41%, not "a few" — that part overshoots, but the core claim (majority biased, balanced A/B) confirms.

## Why it's the same as the web∩window "incomplete parts"
Rasterizing a tilted/nonlocal boundary onto a grid always leaves partial-coverage cells: web∩window resolves ~60%, leaves ~40% incomplete; flat cut ~59% biased / ~41% void. The shared statement: a straight/local operation on a tilted/nonlocal boundary leaves a fixed fraction of ambiguous cells — the aliasing tax, geometric, doesn't vanish with finer rules. A cut that sat purely on the void couldn't be straight.

*Artifacts: `aliasing.py`, `aliasing.png`.*
