# Trails Meet — two sides overlap when closed, the trail runs to ATP, tilt steers the cut

*Companion to `FOLDING_TRAIL.md`, `FOLDING_ATP_REFERENCE.md`, `FOLDING_MATCHING_SLOT.md`. Jonathan: (A) the same trail runs from the other side — if each side spans >50% they meet; (B) does the trail run to ATP; (C) tilt could steer a fixed-depth cut off the core. Tested; `trail2_test.py`.*

## A — the two one-sided trails MEET (CONFIRMED, meeting = the closed state)
Each side reaches ~half; for compact enzymes the two spans sum **>1.0 → they overlap** in the middle (the woven core): 2LZM 1.22, 8TLN 1.16, 1GD1 1.09, 4AKE 1.07, 6LDH 1.02. The exceptions are the floor (calmodulin 0.27) and the open-form PGKs (1PHP 0.82, 3PGK 0.74) — domains apart. **Trails meeting is the signature of the closed, working conformation.**

## B — the trail leads to ATP (CONFIRMED)
Ligand-neighborhood mixedness percentile: 1AKE (AP5A) 68th, 1GD1 (NAD) 84th, 2CTS (CoA) 60th — the ligand sits on the trail. Path and destination are one object.

## C — tilt steers whether a fixed-depth cut hits the core (CONFIRMED, with a trade-off)
The core is never shallow (≥ ~14 Å from every angle — protected by centrality), but depth-to-core varies 2–4× with angle (14 → 34–54 Å), so a fixed-depth cut's reach depends on tilt. Honest catch: the shallow direction *is* the cleft/seam — the natural minimal cut runs straight through the core; protecting it means cutting off-seam, deeper, at a cost. Tilt can protect the core, but not for free.

*Artifacts: `trail2_test.py`. Set as in FOLDING_TRAIL; ligands AP5A/NAD/CoA.*
