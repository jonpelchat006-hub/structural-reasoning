# The Wall Gradient — the seam is a CAMBIUM, not skin: commitment grades across the cut, not up the wall

*Companion to `FOLDING_THE_KNIFE.md`, `FOLDING_C_PIXELS.md`, `FOLDING_CLIMB_WALL.md`. Jonathan's idea (the deposits/dead-skin thread): the pLM went through the C parts, so the **skin is what's above** — the C pixels are the base of the cut and other pixels climb the walls; a maturation gradient where the buried base is mixed/undecided and the exposed top is committed A or B (skin: undecided basal → dead committed keratin). Tested on the canonical 8; `wall_gradient.py`.*

## The test
Fiedler-bisect into A/B with a continuous field `f`; cut-plane normal `n`; signed distance `s`. **Wall residues** line the cut. Two commitment measures: contact-based (`1 − other/(own+other)`) and graph-based (`|f|/σ`). Height = exposure (RSA). Test whether commitment grades up the wall; sanity-check perpendicular to the cut.

## Results
1. **The up-the-wall (skin) gradient is ABSENT, even slightly reversed (NEGATIVE):** contact measure pooled Spearman **−0.13** (n=1441), positive in only 2/8; the buried base is *more* committed than the exposed top (0.65 vs 0.59). The graph measure (packing-independent) lands at **+0.07** ≈ 0. No differentiation gradient climbs the wall.
2. **The real gradient runs PERPENDICULAR, across the seam (CONFIRMED):** commitment vs distance from the cut plane |s| — **Spearman +0.31, 7/8**. The mixed/cancelling material is a thin slab straddling the seam plane at every height, committed-A on one side, committed-B on the other.

## Where it lands — cambium, not skin
Not stratified skin (basal-undecided → surface-committed). It's the **cambium**: a thin dividing sheet at one radius laying down committed tissue on *both* sides, uniformly along its height. The seam is that sheet; the two complementary wall faces are the dead written layers — stratified **by side of the seam, not by height up the wall.** The deposit/skin idea survives; only the layering axis changes (perpendicular to the cut).

## Honest ledger
**CONFIRMED** — the commitment gradient is perpendicular to the cut (+0.31, 7/8).
**NEGATIVE** — the up-the-wall differentiation gradient does not exist (contact −0.13; graph +0.07 ≈ 0).
**Caveat** — the contact measure is confounded by packing density; the graph measure is the clean one.

*Artifacts: `wall_gradient.py`/`.png`. Set: 1CLL, 3PGK, 1PHP, 1GD1, 6LDH, 8TLN, 4AKE, 2LZM.*
