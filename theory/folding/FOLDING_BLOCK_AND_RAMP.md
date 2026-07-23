# Block-and-rotate, ends at the void line, and the coil as an energy ramp

*Companion to `FOLDING_ONE_SIDE.md`, `FOLDING_ATP_REFERENCE.md`, `FOLDING_STRANDS.md`. Three predictions tested on the two-domain set (+ the ADK open/closed pair); `reading_energy_tests.py`.*

## T1 — the chain ends lean toward the void line — WEAK POSITIVE
Mean terminus percentile 0.40; **69% of termini in the seam-half** — a real tilt, but weak (≈ p=0.08, n=16): some ends sit at the seam (2LZM 0.05, 3PGK N 0.03), others far out (6LDH N 1.00, 8TLN N 0.94). A soft yes.

## T2 — block one strand, let the other ROTATE to meet it — STRONG CONFIRM
This is **induced-fit closure**. ADK open (4AKE) vs closed (1AKE), superimposed on the CORE (the "blocked" strand): CORE 1.34 Å (pinned), NMP swings 9.96 Å, **LID swings 14.36 Å** to close over the ligand. Exactly "block one, rotate the other to register" — the closed lid over the active site *is* where the read happens (on the ATP sitting on the seam). Reading = registration at closure, not a static polar scan — the strongest hit in this batch.

## T3 — the coil as an energy ramp — REAL PHYSICS, WEAK FINGERPRINT
(a) A coil IS an energy ramp, by construction: an α-helix carries a macrodipole (+N-terminus, −C-terminus), so axial height is an electrostatic potential — "height in a field, costs energy to climb" is physically correct. (b) Do proteins arrange charge to climb it? Over 62 helices, mean (C-half − N-half) = +0.226 (right direction), but only 48% of helices follow it (Wilcoxon p=0.30) — too weak to call here. The field is real; the deliberate arrangement is only faintly present.

*Artifacts: `reading_energy_tests.py`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM; ADK pair.*
