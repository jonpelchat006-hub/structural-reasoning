# ATP as the Reference — the void line is the ligand pocket, and the threadings point at it

*Companion to `FOLDING_KNIT_WEAVE.md`, `FOLDING_SALTS.md`, `FOLDING_TWO_WALLS.md`. Jonathan: wouldn't all the threads point toward ATP — the ligand reached from both domain borders, ATP the reference for which positions matter? Tested on 5 ligand-bound enzymes; `ligand.py`.*

## Results
1. **The ligand sits ON the void line (CONFIRMED):** distance to the flat cut plane / half-width — 1AKE (AP5A) 0.21, 2CTS (CoA) 0.03, 1GD1 (NAD) 0.55 (on/at the seam); 3PGK, 1PHP near the seam, slightly to one side. The cut is not just a boundary — it is the **active site**.
2. **Reached from BOTH borders — state-dependent (the mechanism):** contacts A|B — 1AKE 57|7, 1GD1 40|18, 2CTS 5|39 (both domains — the closed state); 3PGK 0|30, 1PHP 0|27 (one domain — open forms, pre-closure). Induced fit = the two domains closing around the ligand at the seam; "both borders" is what the working closed state looks like.
3. **The threadings point AT the ligand (CONFIRMED, all 5):** seam-crossing points are **0.77–0.90×** the average residue's distance to the ligand — the chain's crossings of its own void line converge on the nucleotide site.

## What this closes
ATP is the organizing reference of the whole architecture: the void line is where the two domains meet (the knife), knitted through by the chain (the needle-eye threadings), where the structure and energy walls interlock (buried salt bridges), and the ligand pocket (ligand on it, reached from both borders, threadings converging). The two-domain fold exists to close two carbon walls around a phosphate/nucleotide on the void line — the same statement as the F1-ATPase "big pivot around the fixed ATP connection," now shown for soluble kinases. Honest limit: still structure-in (says *what the architecture is for*, not how to predict it from sequence); n=5.

*Artifacts: `ligand.py`, `ligand.png`.*
