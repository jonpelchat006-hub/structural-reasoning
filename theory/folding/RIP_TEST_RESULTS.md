# The Rip Is the Easy Direction — a measured brick

*Testing Jonathan's folding-container idea against real PDB structures: a folded sheet is a container; where two containers meet on a thin neck, it **rips** at the sparsest seam of the contact web. Claim: domain boundaries sit at the min-cut of the contact web, recoverable from web sparsity even when the dense fold is not predictable. `riptest.py`, `recur.py`, `weave.py`, `gate.py`, `anm.py`, `survey.py`, `states.py`, `element.py`.*

## Why this could beat the wall
Predicting the fold means predicting *dense* contacts (many-body coupling). A rip is the opposite — a sheet tears where the web is *already thin*; predicting the *absence* of contacts is visible without solving the coupling.

## Results (all downstream of the web — CONFIRMED)
- **Rip = min-cut** finds domain boundaries to ~1 residue: 3PGK/4GCR/5TNC err 1, 1CLL err 3 (random ~40). Seam-depth contrast separates rippable vs solid (multi-domain 4.47 vs single 1.76).
- **Recursive ripper:** clean multi-domain 5/5 exact domain count, 6/6 boundaries; single-domain controls 8/8 intact.
- **Floors = what's woven in:** cross-domain contact fraction clean 4.2% vs failed 15.6% (~4×). Border-dominant residues clean 2.1% vs failed 9.3% (~4.4×). Seal within = weave across.
- **Wet seam:** seam hydropathy −0.56 (wet) vs core +0.86 (greasy). **Gate:** ADK open/closed 77 form, 54 break, 60% at the mobile lids.
- **Rhythm:** functional domain motion lives in the low-frequency subspace — ADK slowest mode overlaps the real open→closed motion 0.80; survey of 10 two-state proteins, best slow mode mean 0.67, 9/10 ≥ 0.50, ~7× above random.
- **Stretch/states:** cross-seam bonds strain 2.5 Å vs 0.5 Å same-side (~5×); two states split the web into permanent core + transient gating overlay (the principle behind coevolution beating one crystal).
- **Elements:** buried interior 84% C / 14% N+O; exposed border 72% C / 26% N+O — the boundary and interior are made of different elements (invariant carbon scaffold + variable heteroatom border).

## Verdict
Everything downstream of the web is cheap and now demonstrated; **predicting the variable web from sequence stays the wall** (sequence-only rip ≈ random). The web is the pivot.
