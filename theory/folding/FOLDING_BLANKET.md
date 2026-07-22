# The Blanket — folding keeps creating seam, but only up to a DEFINITE bounded total (the finite sheet)

*Companion to `FOLDING_FOLD_OUT.md` (folding CREATES the seam), `FOLDING_STAIRCASE.md` (finite floor), `VOID_LINE_PAPER.md` §11–12 (the ~0.2×L path budget), `SHOVELCAT_THEORY.md` Part XV (the theta field as a blanket — "finite total area, variable concentration"). Jonathan: making the border/window cuts a finite piece out of the golden field — we only have that sheet, it folds in too, like a blanket with a definite size we keep track of. Tested; `test_l.py`.*

## Folding creates seam — NOT one conserved sheet redistributed (correction)
Each cut severs **new** contacts. Cumulative severed edges are **4–7× the first cut**. So the strict "single sheet, folding only redistributes it" is wrong — folding makes interface (`FOLDING_FOLD_OUT.md`).

## But the TOTAL is a definite size — the blanket has a fixed, trackable area (CONFIRMED)
Across L = 144–415, the whole fold recursion sends a **definite, tight** fraction through the cuts:

| quantity | mean | CV | range |
|---|---|---|---|
| **seam residues / L** | **0.36** | **0.15** | 0.29–0.45 |
| total contacts cut / all | 0.13 | 0.19 | 0.10–0.18 |
| primary cut / L (cloth threads/residue) | 0.15 | 0.36 | 0.07–0.22 |

~36% of residues ever lie on a cut, ~13% of contacts severed — CV 0.15 on the residue budget. That tightness is the "definite size." Folding keeps creating seam, but the creation **saturates at a bounded total** — you can't fold past the sheet you have.

## The budget is SPENT DOWN
Per-level severed edges peak at level 1–2 and decline toward the floor (e.g. 8TLN 71→76→29→19→21). Deep cuts run out of cloth — the sheet is used up over the fold levels.

## Connections
The theta blanket ("finite total area, variable concentration") — total fixed (~36%), per-level concentration varies (peaks early, tapers). The primary cloth budget cut1/L ≈ 0.15 **adapts to knittedness** (calmodulin 0.07 → 6LDH 0.21), like the ~0.2×L path budget.

## Ledger
**CONFIRMED:** the interface is a finite blanket of definite size (~36% residues, CV 0.15; ~13% contacts), spent down over the fold levels, adapting to knittedness. **CORRECTION:** not one conserved sheet redistributed — folding creates new seam each cut (cumulative 4–7×); the "blanket" is the definite bounded total the creation saturates at.
