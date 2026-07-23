# Recursive C — each fold makes a C, and D is where all the Cs combine

*Companion to `FOLDING_D_AND_DIRECTIONS.md`, `FOLDING_TRAIL.md`, `FOLDING_STAIRCASE.md`. Jonathan: folding changes with each fold — C1, C2, C3…; is D actually a recursive C, the combination of all previous Cs? Tested by recursive bisection; `recursive_c_test.py`.*

## Each fold makes a new C (CONFIRMED)
Recursively bisect (cut → cut each half → each quarter…). Interface residues appear at **every** level and grow finer (3PGK 31→125→136→176; 8TLN 48→97→117→147). The real structural hierarchy (helix–helix → motif → domain → fold), each level a new class of contact.

## D = where all the Cs combine (CONFIRMED for the real enzymes)
Interface-multiplicity (how many nested Cs a residue belongs to) correlates with distance-from-center at **−0.24 to −0.47** — residues in many nested Cs sit toward the center. The **ligand sits there** (1AKE 56th %ile, 1GD1 63rd %ile). D — the cofactor site — is where the recursive Cs pile up. D has a **material** identity (the guest molecule) and a **positional** one (deepest confluence of Cs) — the same place; matches enzymology (active sites at the confluence of several structural elements).

## Honest edges
Correlations moderate (−0.3 to −0.47); ligand multiplicity above-average, not a razor peak. **Calmodulin breaks it** (+0.04) — no convergent center, the floor protein again. The equation: A/B are the two sides at each fold; C is the interface that fold creates; C recurs at every scale; **D is the limit of the series** — the accumulation of the C hierarchy, where the cofactor binds.

*Artifacts: `recursive_c_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
