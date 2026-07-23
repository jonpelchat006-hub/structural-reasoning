# The Eye — the detector the darkroom was missing (a chromophore that collapses on light)

*Companion to `FOLDING_C_PIXELS.md` (the darkroom, no detector), `FOLDING_GLOW.md`. Jonathan: eyes read light too — maybe the sheets are near a threshold and light causes a collapse. Tested against rhodopsin (1U19) and the cofactor pockets; `eye_test.py`, `nad_test.py`.*

## The eye is a real single-photon reader, and its mechanism is Jonathan's "collapse"
Rods signal a **single absorbed photon** via **rhodopsin**: an 11-cis retinal chromophore snaps to all-trans on absorbing a photon (a conformational collapse), pushing opsin into a new shape and firing a **G-protein amplification cascade** (one photon → large chemical signal). "Light causes a collapse and that sends the message" is essentially the textbook mechanism.

## The reader sits in a fully sealed darkroom (measured)
Retinal in 1U19 is **100% buried** (SASA 2.1 Å² vs 537 Å² isolated), lined by 22 residues (Lys296 Schiff base, Glu113 counterion). And the darkroom in Jonathan's OWN set already holds a chromophore: **GAPDH (1GD1) NAD 84% buried**, and NADH is a genuine chromophore (absorbs ~340 nm, fluoresces ~460 nm).

## Two honest corrections
- **"Near a threshold / delicate" — sharpen it:** retinal is *poised* (a strained cis shape ready to snap) but NOT thermally near-threshold — spontaneous isomerization ~once per few centuries per molecule. Deaf to heat, exquisitely sensitive to light, then amplified — a quiet-against-noise, loud-to-signal catcher plus gain.
- **"Refraction sends messages" — no:** the cornea/lens only *focus*; the reading is the retinal photochemistry.

Biology builds photon-readers with the same recipe (a chromophore in a buried pocket + a conformational flip + amplification — rhodopsin, LOV, cryptochrome, phytochrome). The framework supplies the pocket and even a chromophore; the eye adds tuning + gain + a signal path — the honest remaining gap. Next test: is there a poised element positioned to change state when the bound chromophore absorbs (the amplifier)?

*Artifacts: `eye_test.py`, `nad_test.py`. Sources: J. Gen. Physiol. 150:383 (2018); Sci. Rep. 5:11081 (2015).*
