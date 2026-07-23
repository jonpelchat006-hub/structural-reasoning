# The C Pixels — the leftover woven core as a shielded darkroom (contrast, not strength)

*Companion to `FOLDING_CLEANUP.md`, `FOLDING_GLOW.md`, `FOLDING_ATP_REFERENCE.md`. Jonathan's idea: a faint signal doesn't have to be strong, just CONTRASTED — the mixed A/B "C pixels" around the void line give a dark background, and being buried they act like "an outside thing, on the inside." Tested on 8 proteins; `c_pixels_test.py`.*

## The test & result (CONFIRMED)
C residues by geometry (cross-face heavy-atom contact < 4.5 Å), then solvent accessibility: **C pixels mean RSA 0.21, 57% buried, 28% fully dark** vs whole-protein 0.25 / 48%. C residues more buried than average, **p = 3×10⁻⁴**; dark fraction reaches 44% (8TLN), 37% (1GD1). A real subset of the woven core is fully desolvated — a sealed dark interior, exactly "an outside thing, on the inside."

## The bonus — desolvation also reduces quenching
**Water quenches excited states** (singlet oxygen lives ~µs in water, far longer in a nonpolar pocket; fluorophores brighten in aprotic environments). Excluding water from the C core means an excited state faces less background AND emits more strongly — signal-to-noise helped on both ends. And the reaction site sits here (ligand on the void line), so any emission happens *in* the darkroom.

## Honest caveats
Modest average contrast (0.21 vs 0.25) — rides on the fully-dark 28% subset, not the whole interface. **Calmodulin breaks it** (exposed hinge, no dark core — the floor again). Burial shields against light and excludes quenching water; it does **not** show the system *reads* the emission. The detector step (an element whose state flips when a photon lands) is still the open claim — the leftover ~15% core gets a job (the darkroom), but a darkroom is not yet a reader.

*Artifacts: `c_pixels_test.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
