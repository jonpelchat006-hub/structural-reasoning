# The Trail — C as a graded field is one connected trail, centered, along the cut

*Companion to `FOLDING_CLEANUP.md`, `FOLDING_STAIRCASE.md`, `FOLDING_CONTINUITY.md`. Jonathan: at maximum zoom, is there an invisible connected trail of C — the weak line we cut/fold along? Idea: C isn't binary; allow a trace of the other domain to count, and C should thin from a compact core into a connected trail, quality highest at the center. Tested on 8 proteins; `trail_test.py`.*

## Results — three confirmations, one honest limit
Per-residue **mixedness** = distance-weighted fraction of nearby residues from the other domain; sweep the threshold.
- **C is ONE connected trail, not islands (CONFIRMED):** largest connected component **95–100%** of the C set at every threshold, every protein.
- **Quality peaks at the center and tapers (CONFIRMED, 8/8):** corr(mixedness, dist-to-center) **−0.43 to −0.68**. The ~15% woven core is the high-threshold center; lower threshold radiates outward.
- **C extends far beyond the core (CONFIRMED):** ~3–17% at strict threshold up to **66% (6LDH)** at fine. Ordering tracks knittedness (6LDH most, calmodulin least).
- **Spanning is partial (HONEST LIMIT):** span reaches 0.55–0.72 of the longest diameter — the seam runs *perpendicular* to the domain-to-domain long axis, so the trail spans the **width of the cut**, not a wire to every tip (the interface is a 2D surface through the middle). No single threshold is both a thin wire and reaches every tip.

The trail is the **min-cut surface seen as a continuous quality field** — connected, center-peaked, extensive, aligned with the cut, marking where to fold.

*Artifacts: `trail_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
