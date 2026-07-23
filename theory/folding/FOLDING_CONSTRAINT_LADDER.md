# The Constraint Ladder — how much do knowable rules narrow the fold, and where do they stop?

*Companion to `FOLDING_SLOTS.md`, `FOLDING_WINDOW_SEAM.md`. Jonathan's proposal: build a rule set (amino acid → window → contacts), intersect the layers, watch the fold space shrink — "a good job for AI." Tested as an **information budget** in bits/residue; 9 proteins; `ladder.py`.*

## The ladder, in bits per residue (measured)
Raw allowed backbone 7.87 → + window alphabet **1.81** (−6.05, the big cut) → + sequence→window rule **1.63** (−0.19). **The basins do essentially all the local cutting** — and they are universal geometry, not learned. The sequence-specific rule adds only **0.19 bits** (knowing the amino acid barely sharpens the window). Local rules asymptote here.

## Fold-space collapse (median protein, N=318)
Raw backbone ~10⁷⁵³ → after window alphabet ~10¹⁷⁴ (a ~580-order cut — the rules really do narrow) → after sequence→window ~10¹⁵⁶. The real fold is **one** of that 10¹⁵⁶.

## Where it stops — the web does the selecting (measured)
Uncertainty about whether a long-range pair is in contact: H = 0.105 bits/pair; explained by knowing both residues' windows: I = 0.0019 bits/pair. **Windows explain 1.8% of the web; 98.2% is web-only.** The local ladder prunes 10⁷⁵³ → 10¹⁵⁶, then the web selects the single fold while being ~98% orthogonal to everything local. Yes, building the rule set is worthwhile (~580 orders pruned), but it cannot finish — the residual is selected by the web, which local rules are 98% blind to.

## The one genuinely open direction — the "series of webs"
Jonathan's deeper idea: not one web but a **hierarchy** (backbone-H-bond web → sidechain-packing web → cross-domain web), each cut in turn. This measured the *flat* web (one 10¹⁵⁶ selection). The open bet is whether the flat web **factorizes** into a series of smaller, individually-cheaper webs whose product is the fold — which is exactly what modern folding networks exploit implicitly (iterative refinement). Testing whether the web factorizes is the live frontier.

*Artifacts: `ladder.py`, `constraint_ladder.png`.*
