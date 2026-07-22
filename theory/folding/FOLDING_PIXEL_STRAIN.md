# Deformed Pixels & the Next Cut — the cut follows the rigid buried waist, not floppy deformed pixels (a correction)

*Companion to `FOLDING_FOLD_OUT.md` (folding creates & buries the seam), `FOLDING_SALTS.md` (the core is shape-locked), `FOLDING_ALIASING.md` (the flat knife on the zigzag void), `FOLDING_RECURSIVE_C.md` / `FOLDING_STAIRCASE.md` (nested cuts), `FOLDING_OBSERVERS.md` (the raised committee), `VOID_LINE_PAPER.md` §10–11 (the wall & the pLM outer layer). Jonathan's chain: the fold **stretches the pixels** into different shapes → a stretched pixel **looks less like what it should be**, so it becomes a **weak point** → weak points are the **next-best candidates for cutting** → the **pLM can add work and rank the candidates**. Tested on the canonical 8; `pipeline.py`, `test_b.py`, `test_c.py`, `test_d.py`; `pixel_strain.png`, `plm_recursion.png`.*

## The headline
The intuition splits cleanly in two. The **local** half is **corrected**: across three deformation measures and two per-residue pLM readouts, the cut line does **not** run through deformed/floppy/mobile material — it runs through the buried, well-packed, rigid woven core. The **nonlocal** half is **confirmed**: the pLM's pairwise contact web fed into a global min-cut ranks not only the first cut but the **next** one too — weaker, but above chance in all 8 proteins.

## 1 — Does the fold stretch pixels into different shapes at the cut? NO (NEGATIVE)
Three deformation measures vs seam-ness (mixedness), pooled n=2310, per-protein z-scored: neighborhood **planarity −0.05**, **anisotropy −0.03**, **Ramachandran atypicality −0.05**, **Cα-kink irregularity −0.05**. All ≈ 0. The pixels do not measurably deform toward the cut. (Caveat: single crystal → static irregularity, not a folded-vs-unfolded strain tensor; but three independent proxies agree on the null.)

## 2 — Are the cut lines "weak" (mobile/deformed)? NO — RIGID and BURIED (CORRECTION)
- **corr(B-factor, seam-ness) = −0.09** — the seam is, if anything, *less* mobile.
- B@seam − B@rest is negative in **5 of 7** usable proteins. 1CLL (calmodulin) is the floor exception (exposed hinge). corr(B, density) = −0.49 confirms B is a real mobility readout.
- **The recursion is real (CONFIRMED):** a coherent second cut exists (Fiedler within the larger domain), and it follows the **same rigid buried core** — AUC(B-factor → secondary seam) = 0.30, AUC(low density → secondary) = 0.37.
- **Two different "weak"s:** *topologically* weak (thin waist / min-cut) vs *mechanically* weak (floppy, deformed). The cut follows the topological waist — mechanically the **strongest, most buried glue**.

## 3 — Can the pLM rank candidates from a per-residue read? NO (re-confirms THE WALL)
ESM2-8M, pooled AUC (0.5=chance): per-residue reconstruction surprise → primary seam **0.50**, → secondary **0.51**; contact-count bridge → seam **0.45**. No local reduction of the pLM finds the cut — the seam carries no local signature.

## 4 — Does the pLM rank the cut through its WEB, and does it carry to the NEXT cut? YES (CONFIRMED)
Take ESM2's predicted contact map, run the same weighted min-cut. **Primary** cut vs true: **0.839** (chance 0.563, +0.28) — replicates §11. **Secondary** cut (within the larger true domain): **0.671** (chance 0.541, +0.13, 8/8 proteins positive, sign test p≈0.004). **Fades with depth** (0.84→0.67, gain halves) — the graceful degradation the framework predicts. So the pLM ranks the recursion's next candidate as a **global web operation applied one level down**, never a per-pixel score.

## Honest ledger
**CONFIRMED:** the recursion is real; the pLM web ranks the cut and the ranking recurses (0.84 → 0.67, fading); the wall re-confirmed at the per-residue level (AUC ≈ 0.50); calmodulin the floor again.
**CORRECTION:** the cut does not follow deformed/floppy material — it rides rigid buried core; deformation doesn't localize to the seam (|r| ≤ 0.05).
**NEGATIVE:** fold stretches pixels at the cut — no; deformed = weak = next cut — no; per-residue pLM ranks the cut — no (chance).
**REFRAMED TRUE:** the pLM ranks the cut only as the outer layer (pairwise web → global min-cut), at every level of the nested recursion, fading with depth.
