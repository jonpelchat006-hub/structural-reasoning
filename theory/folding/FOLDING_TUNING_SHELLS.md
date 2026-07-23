# Tuning Shells — heterogeneous C sets the wavelength; pre-filters subtract before the core

*Companion to `FOLDING_THE_EYE.md`, `FOLDING_C_PIXELS.md`. Jonathan: the C parts aren't identical — maybe a main C pixel is surrounded by different ratios of C that absorb/flip at certain wavelengths, filtering light before the core reads it. Tested against opsin spectral tuning + cone oil droplets, and shell geometry on rhodopsin; `shell_test.py`.*

## Half 1 — surrounding composition sets the flip wavelength (opsin spectral tuning) — REAL
The three human cones use the identical 11-cis retinal and peak at ~420/534/564 nm purely by lining the pocket with different amino acids around the shared chromophore. A few substitutions slide λmax by tens of nm — exactly "different As and Bs make the core flip at a different wavelength." Established science. The shell geometry is real on rhodopsin: a main pixel (retinal) wrapped in compositionally distinct concentric shells (contact 22 residues incl. Glu113; inner 44; outer 61), with known spectral-tuning sites spread across all three.

## Half 2 — pre-filters subtract wavelengths before the core (cone oil droplets) — REAL
Birds/reptiles put a colored oil droplet in the light path in front of the opsin — a long-pass filter absorbing shorter wavelengths before they reach the retinal. "Filter certain wavelengths in front, read the remainder" is a genuine strategy.

## Honest seams
Two structures, not one onion (tuning = residues *touching* the chromophore; pre-filtering = a *separate organelle*). Readout is multi-channel comparison (opponent processing across differently-tuned cones), not one filtered remainder. Same ingredients, different wiring. The premise is load-bearing and correct — heterogeneous C is the raw material a tuned reader needs, and the void-line core has it; the open claim is whether an ordinary enzyme's shells are *tuned for reading* vs arranged for folding/catalysis.

*Artifacts: `shell_test.py`. Sources: PubMed 24422511 (2014); 24395968 (2014).*
