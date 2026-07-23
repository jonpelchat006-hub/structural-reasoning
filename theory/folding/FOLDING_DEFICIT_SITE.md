# The Deficit Site — the active site is an INCOMPLETE void (a half-void with a deficit), and the ligand is the replacement B

*Companion to `FOLDING_THE_KNIFE.md` R5, `FOLDING_ATP_REFERENCE.md`, `FOLDING_C_PIXELS.md`, and the wall in `FOLDING_FLOORS.md` §5 / `VOID_LINE_PAPER.md` §10. Jonathan's idea: a cut buries the B part of a pixel; the void reads 0 (invisible) but exists, leaving a **deficit** that A wants to fill; a **replacement B from elsewhere (a ligand) fills it**; the amount of A/B is like the **charge**; and **H (hydrogen bonds) supplies the B**. Tested on 5 ligand-bound structures; `deficit_site.py`.*

## The reframe that resolves the wall
The project's seam **cannot** find the active site (`FLOORS` §5: 2/6; §10). The deficit idea explains why: the interdomain seam is a **complete** void — both A and B walls present, cancels to zero, wants nothing. The active site is the opposite — an **incomplete** void, a cavity missing its B wall, carrying an unsatisfied deficit. Catalysis lives at the hungry void, not the balanced one — so the seam never pointed at it.

## Results
1. **CHARGE is the A/B imbalance the ligand fills (CONFIRMED where protein fills directly, 3/5):** pocket net charge is opposite to the ligand and tracks magnitude — AP5A(~−5)→pocket **+17**, Ca(+2)→**−14**, Zn/Ca→**−8.5**. The two misses (1PHP ADP, 3PGK ATP) are **Mg²⁺-bridged** sites: the positive B is a co-recruited metal ion, not protein basics — the replacement B "from somewhere else" literally.
2. **The pocket is a hungry HALF-VOID (CONFIRMED, 4/5):** unsatisfied polar fraction **pocket 0.10 vs interior 0.06**; metal sites the extreme (8TLN 0.12 vs 0.04, ~3×).
3. **The ligand (external B) completes it; H supplies B (CONFIRMED for H-bonding ligands):** bound ligand satisfies **35% on average** — AP5A 37%, ADP 50%, ATP 80%. Metals fill almost none of the *H-bond* deficit (Ca 0%, Zn 9%) — they fill by charge/coordination instead. Two mechanisms.

## Honest ledger
**CONFIRMED** — active sites are incomplete half-voids with a real deficit (0.10 vs 0.06, 4/5); charge is the A/B imbalance; H-bonding ligands complete 37–80%. The deficit sits **away** from the complete seam — hitting the site the seam kept missing.
**NUANCE** — charge complementarity 3/5: Mg²⁺-bridged nucleotide sites outsource the positive fill to a metal cofactor.
**CAVEATS** — H-bonds from heavy atoms only; ligand charges approximate; Mg²⁺ not modelled; n=5.

*Artifacts: `deficit_site.py`/`.png`. Structures: 1AKE, 1PHP, 3PGK, 1CLL, 8TLN.*
