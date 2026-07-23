# The Void Reach — the void line is the long-range channel to the far-out atoms (budgeted, mixed), and the deficit sits on it

*Companion to `VOID_LINE_PAPER.md` §10 (the wall), `FOLDING_SEQUENCE_BUDGET.md` (the long-range path budget), `FOLDING_DEFICIT_SITE.md`, `FOLDING_C_PIXELS.md`, `SPARSE_VESICA_EXPANSION.md`. Jonathan's idea: things travel down the void line as if in **superposition**; the **deficit could reach down the void line and pull far things**; there is a **budget** so it can't reach everywhere; and the void can take from **A and B at once**. Tested on the canonical 8 + the 5 ligand pockets; `void_reach.py`.*

## The mapping
Void line = the seam (cross-domain-contacting / Fiedler-near-zero residues). "Far-out atoms" = long-range contacts (sequence separation |i−j| > 20 — the nonlocal web §10 says local methods can't reach).

## Results
1. **The void line carries the long-range reach (CONFIRMED):** seam residues carry **2.51 vs 1.54** long-range contacts (1.6×), seam > non-seam in **7/8**.
2. **The void line IS the reach corridor (CONFIRMED, 8/8 — headline):** betweenness centrality seam **0.025 vs 0.012 non-seam, ~2.1×, 8/8**. The void line carries twice the long-range shortest-path traffic — the corridor through which distant parts communicate.
3. **The reach is BUDGETED / sparse (CONFIRMED, qualitative):** long-range contacts per residue = **1.14** — each reaches only ~1 far partner. (Honest: "sparse and bounded," not a numeric match to the ~0.2×L path budget.)
4. **The void takes from BOTH A and B (CONFIRMED):** **25%** of long-range contacts cross the A|B seam — up to **44%** in the most knitted folds.
5. **The deficit sits ON the channel (CONFIRMED for enzyme sites):** ligand-pocket betweenness vs protein mean **1AKE 1.3×, 1PHP 2.8×, 3PGK 2.1×** — active sites are high-reach hubs (the substrate of allostery). The **metal** sites are *not* on the channel the same way (1CLL 0.6×, 8TLN 1.1×).

## Honest ledger
**CONFIRMED** — the void line carries the long-range reach (1.6×, 7/8) and **is** the shortest-path corridor (betweenness 2.1×, **8/8**); reach is sparse/budgeted; 25% (up to 44%) A|B-mixed; enzyme active-site deficits sit on the channel (1.3–2.8×).
**NUANCE** — betweenness is a network-model proxy; the budget is shown qualitatively, not as the 0.2×L number; metal-ion sites do not sit on the channel like enzyme sites.
**CONCEPTUAL** — "superposition travel" = the Fiedler-near-zero (undetermined-A/B) corridor.

*Artifacts: `void_reach.py`/`.png` (betweenness via networkx). Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM; pockets 1AKE, 1PHP, 3PGK, 1CLL, 8TLN.*
