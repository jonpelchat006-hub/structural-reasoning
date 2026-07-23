# Vortex Deposition — the turn writes on the seam walls (oblique), and the wall IS the outer border moved into position

*Companion to `FOLDING_VORTEX.md` (the void line is the rotation axle; ~24% of the web turns over), `FOLDING_THE_KNIFE.md` R4, `FOLDING_SATURATION_BUDGET.md`. Jonathan's thread: the vortex leaves stuff on the walls as it turns; the border hits the wall at an angle; and the walls should be the **outer borders moved into position**. Tested on the ADK open→closed pair (4AKE→1AKE); `vortex_deposition.py`.*

## Setup
E. coli adenylate kinase, chain A, 214 residues. Domains: NMP 30–67, LID 118–160, CORE the rest. Aligned on **CORE Cα** (Kabsch RMSD **1.55 Å**; LID then moves **13.6 Å**, NMP **9.5 Å** — textbook ADK closure).

## Results
1. **The turn deposits contacts on the seam walls (CONFIRMED):** open→closed **94 form, 49 break** (~27% turnover). Of the contacts that form, **46% are cross-domain** — since cross-domain is only ~8% of all contacts, formed contacts are **~5.5× enriched** for the seam. The turn writes preferentially onto the walls.
2. **The moving border approaches OBLIQUELY (CONFIRMED):** displacement makes a **median ~37°** angle with the local wall normal; 50% in the oblique 30–75° band — an angled swing, what a rotation about the seam axle produces.
3. **The wall IS the outer border moved into position (CONFIRMED — the new claim):** the 49 residues that become the closed seam wall have mean **RSA 0.22 when open** (surface) and **0.05 when closed** (buried) — a ~4× drop, 37% strictly flipping exposed→buried. The wall is literally the outer border carried in.
4. **The seam reserve fills as the vortex turns (CONFIRMED via proxies):** LID centroid-to-CORE **30.1→20.9 Å**, cross-domain contacts nearly double **45→80**.

## Honest ledger
**CONFIRMED** — formed contacts land on the seam walls (~5.5× enriched); oblique approach (~37°); the wall is the moved outer border (RSA 0.22→0.05); the seam gap clamps.
**UNDERPOWERED** — charge complementarity of the newly formed faces (only 6 charged contacts).
**OPEN** — the seam reserve measured through proxies, not by isolating seam void volume.

*Artifacts: `vortex_deposition.py`/`.png`. Structures: 4AKE (open), 1AKE (closed + AP5A).*
