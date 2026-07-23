# Pixel Transmission — every border has a graded efficiency; similar pixels DISSOLVE, the seam is a leaky wall (only under coarse-graining)

*Companion to `FOLDING_THE_KNIFE.md`, `FOLDING_CUT_SERIES.md`, `FOLDING_C_PIXELS.md`, `FOLDING_FLOORS.md`, `FOLDING_ONTO_PLM.md`. Jonathan's idea: the pixel borders *inside* would act like walls but, being between **similar** pixels, they **dissolve**; and each border has an **efficiency** of how well one pixel passes info to the next. Tested on the canonical 8; `pixel_transmission.py`, `pixel_transmission_coarse.py`.*

## The model
Residues = pixels; a border = two residues in contact (Cα < 8 Å). **Efficiency** = overlap of their contact-neighbourhoods (shared local web) ∈ [0,1] — high = same web = info passes = dissolves. **Info jump** = |fᵢ − fⱼ| on the Fiedler field. Coarse version: pixels = spatial k-means clusters of ~b residues; transmission = (#contacts between pixels)/min(|p|,|q|).

## Results
1. **The graded-efficiency claim holds cleanly (CONFIRMED, 8/8):** the info-field jump is larger across the seam in 8/8; efficiency falls as the two sides get less alike — Spearman(eff, dφ) negative in 8/8. "Similar → transmits → dissolves" is directionally true everywhere.
2. **At RESIDUE scale there is no clean wall (NEGATIVE at fine scale):** efficiency internal 0.160 vs seam 0.142 (internal higher in only 5/8); lowest-efficiency borders are *not* enriched for the seam. The interface is **woven, not a clean cut** — at fine grain the seam is stitched.
3. **Coarse-grain and the wall EMERGES, but stays leaky (CONFIRMED, scale-dependent):** seam/internal transmission ratio by pixel size — b=1:1.00, b=4:0.90, b=8:**0.83**, b=12:0.90; seam<internal in 7/8 at b=8. The seam resolves into a **leaky wall** (~17% cut, never a hard barrier) at ~8-residue pixels.

## Why the leak is a feature
A perfectly sealed wall couldn't carry the seam's job: the domains rotate about it and ~24% of the web turns over across it. That only works if the wall still passes most of its info — **a wall you can still talk through** (~83% transmissive).

## Honest ledger
**CONFIRMED** — every border has a graded transmission efficiency, grading with similarity (8/8); under coarse-graining (~b=8) internal borders dissolve and the seam becomes a **leaky wall (~0.83, 7/8)**.
**NEGATIVE / nuance** — at residue scale there is no clean wall (the seam is woven). The wall is a coarse, leaky feature.

*Artifacts: `pixel_transmission.py`, `pixel_transmission_coarse.py`, `pixel_transmission.png`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
