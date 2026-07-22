# Golden Depth — the cut recursion IS self-similar (follow it to any depth); the spacing is NOT golden, and the [½, φ] band is generic

*Companion to `FOLDING_FLOORS.md`, `FOLDING_TOWER.md`, `FOLDING_STAIRCASE.md`, `SPHERE_GENERATOR.md` §J.6. Jonathan: the reference spots persist as traces, but folding+rotation means it isn't exactly √5; the golden ratio is recursive (φ = [1;1,1,…]) so can't we follow the pattern to the depth we need? And: it never drops below ½, and φ appears in nature to varying degrees — maybe the object is a range between ½ and φ. Tested; `test_i.py`, `test_k.py`.*

## (a) Self-similar recursion — YES, follow it to the floor (CONFIRMED)
Repeatedly Fiedler-cut, keep the larger half; the larger-fraction kept per cut is **flat across depth**: per-level means 0.591, 0.587, 0.555, 0.555, 0.596, 0.577 over six levels. The same rule repeats at every level, carried to the finite floor set by residue count (3–6 levels here). "Follow it to the depth we need": yes.

## (b) Is the spacing golden? NO (NEGATIVE)
Pooled over 39 recursive cuts: mean larger-fraction **0.576** (95% CI [0.552, 0.601]). **1/φ = 0.618 lies OUTSIDE the CI** — not the golden section (and 0.5 also outside). Spot-step contraction ~0.77–0.82, not 0.618.

## (c) The [½, φ] band — real but GENERIC, not golden-specific (NEGATIVE, corrected null)
74% of real cuts fall in [0.5, 1/φ] (median 0.551) — Jonathan's range observation is factually correct. But the 0.5 floor is **definitional** (the larger half is always ≥ 0.5). And a **fair uniform-density ellipsoid null** occupies the *same* band: mean 0.572, 82% in-band, **AUC(real vs null) = 0.514** — no separation. (An earlier *Gaussian* blob null at 0.695 was unfair — density gradient — and its "real is more even" claim is retracted.) So the band is a generic property of recursively bisecting any compact 3-D shape, not a golden fingerprint; φ is not a hard ceiling (cuts reach 0.875).

## Honest note on not fishing
The pre-registered golden quantity (the golden section) was tested once and excluded; no hunt for some other function of the cut that might land on a φ-power. Both the point test and the band test say: no golden-specific signal.

## Ledger
**CONFIRMED:** the recursion is self-similar (flat ~0.58 across 6 levels) — followable to the floor; the cuts empirically live in ~[0.5, φ]. **NEGATIVE:** the spacing is not golden (0.576, CI excludes 1/φ and 0.5); the [½, φ] band is not golden-/protein-specific (fair null identical, AUC 0.514). **FRAMEWORK:** ℚ(√5) stays a Shovelcat-side substrate; the self-similarity is the real transferable part, the golden value is not in the material.
