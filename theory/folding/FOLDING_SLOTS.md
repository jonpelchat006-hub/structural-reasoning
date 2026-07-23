# The Slots — structure is built from a small, universal, discrete library

*Companion to `RIP_TEST_RESULTS.md`, `FOLDING_TWO_WALLS.md`. Jonathan's model: the "window" latches onto discrete **slots** in the web with some residual tilt; the Ramachandran 3 basins are those slots. Tested via φ/ψ and χ1 across 8 proteins (2,325 residues); `basins.py`, `intersect.py`.*

## Result — the slots are real, discrete, and recur at two levels (CONFIRMED)
Backbone: **3 basins** (82% of φ/ψ space forbidden; αR 43%, β/PPII 34%, αL 4%). Side chains: **3 rotamer wells** (χ1 gauche−/trans/gauche+, ~86% in three). The same threeness one level down. The slots come from hard steric geometry (Ramachandran 1963) — a **fixed, universal library**, not learned, not Earth's tilt.

## The intersection: placing the window on the fixed map (CONFIRMED)
Predicting a residue's backbone slot, held-out: chance (3 slots) 33% → fixed web alone 52% → **fixed web ∩ residue 60%**. The intersection removes ~9% of slot uncertainty (this procedure is **fragment assembly** — the method behind Rosetta, reconstructed from first principles). But the residual ~40% is set by the **global web** — which distant residue this one touches — the wall. Structure is combinatorial: a small universal alphabet of slots (knowable), sequenced by the global web (the wall). The intersection buys everything the fixed side offers and stops exactly at the wall.

*Artifacts: `basins.py`, `intersect.py`.*
