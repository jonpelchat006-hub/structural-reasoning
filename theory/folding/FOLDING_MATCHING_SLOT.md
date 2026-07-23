# The Matching Slot — does face A's voltage predict a complementary slot on face B?

*Companion to `FOLDING_SALTS.md`, `FOLDING_CLEANUP.md`, `FOLDING_STRANDS.md`. Jonathan's layering idea: if a wire carries a "voltage" into a window, the floor must have a matching slot — so across the void line, charge on face A should be answered by a **complementary** charge on face B, by design not accident. Tested on 8 proteins; `layering_test.py`.*

## Result — the matching slot is REAL, and it is the close rivet (CONFIRMED, small n)
Sign every charged residue, find cross-seam charged contacts, test opposite-sign vs a label-permutation null. Complementarity sharpens toward true salt-bridge distance: 4.0 Å 75% (z=1.90), **4.5 Å 81% (z=2.70)**, 5.0 Å 78% (z=2.71), decaying to ~60% (chance) by 8 Å. At rivet distance **81% opposite-sign, organized beyond chance (p<0.01)** — face A's charge is answered by a complementary slot on face B, by design. The loose interface is incidental; the matched slots are the buried rivets. Honest exception: thermolysin (8TLN) inverts (metal-cluster protease, like-signed charges clumping around Ca/Zn) — a real counter-class.

## What it buys
Complementarity across the void line is a **positioned, opposite-sign register at rivet distance**, not a diffuse dipole. Still structure-in (used the fold to find the slots). But the payoff: because the pairing is *organized* (z=2.70, not chance), the two positions co-vary across evolution — and that co-variation *is* readable from an alignment. A random pairing would leave no signal; this says the pairing isn't random. The matching slot is the physical basis of the coevolution route over the wall. (DNA/RNA anchor: the void line as a double-strand register, matched slots ≈ base pairs, the peeled single loop ≈ the transcript — a principled mapping unifying the fold and codon threads through complementarity.)

*Artifacts: `layering_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM; n small (16 rivet contacts).*
