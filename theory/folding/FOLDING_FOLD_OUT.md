# Fold-Out? — folding CREATES the C seam, it doesn't remove it (a correction)

*Companion to `FOLDING_TRAIL.md`, `FOLDING_C_PIXELS.md`, `FOLDING_CLEANUP.md`, `FOLDING_SALTS.md`. Jonathan: when we fold on top of the trail, the C pixels close up — are we trying to fold all the C pixels OUT (remove the mixed "outside" stuff)? Tested; `foldout_test.py`.*

## Results — mostly a correction
- **Does folding bury the trail? Only weakly, not above baseline.** corr(mixedness, exposure) = **−0.06** pooled; ~48–69% of the trail is buried, but so is ~half of *every* residue. The tight woven core *is* buried (p<0.001), but the broad graded trail is not specially hidden.
- **Is C the hydrophobic stuff folding hides? No — corr = 0.00.** The trail is compositionally ordinary, not hydrophobic — and burying hydrophobic surface is *the* driving force of folding, so the trail is simply not that material (consistent with the core being held by shape, not charge or hydrophobicity).
- **Is the exposed leftover C the functional opening? Mostly no** (0–30% near the ligand).

## The reframe — C is created by folding, not removed by it
"Fold all the C pixels out?" is backwards. C only exists because the two domains pack together — there is no A/B interface until you fold. **Folding folds C into existence**; most of it ends buried because a two-domain contact is, by geometry, an interior — not because folding hunts mixed pixels to hide. And it can't be eliminated: the ~15% irreducibly-both core is the glue. The conflation: "clean up the C labels" (bookkeeping) vs "fold the C out physically" (which *makes* the contact) feel identical but are opposite. Honest headline: folding **creates and buries the seam**; the seam is compositionally ordinary, shape-locked, irreducible at its core.

*Artifacts: `foldout_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
