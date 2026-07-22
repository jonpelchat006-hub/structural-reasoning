# The Closure Unit — the free number is k, the golden value is k=1, and the [½, φ] band IS the unit band k∈[0,1]

*Companion to `FOLDING_GOLDEN_DEPTH.md`, `SPHERE_GENERATOR.md` §J.6 & `SPHERE_GENERATOR_TEST.md` Test E. Jonathan: the golden value isn't fundamental — the numbers in that equation were made from something else and can change; maybe the object is a range between ½ and φ. Tested; `test_k.py`.*

## Where the golden value comes from (the derivation)
The **closure equation** is x² = x + k ("whole = part + one unit k of self-reference"); fixed point x = (1+√(1+4k))/2, forcing the field **√(1+4k)**. 1+4k is a perfect square (rational) **iff k is pronic** (0, 2, 6, 12…). **k=1 is the smallest non-pronic case** — the first unit forced to leave ℚ — so unit-1 gives √5 and φ. The golden value is "made from" the choice k=1; change the unit and you change the field.

## The bridge to the measured cut fraction
Generalize the golden section to a **k-section**: the larger:smaller ratio x satisfies x²=x+k, so the larger-fraction is f = x/(1+x). This maps the free unit directly onto the cut fraction:

| k | field √(1+4k) | larger-fraction f |
|---|---|---|
| **0** | 1 | **0.500** (even — no self-reference) |
| 0.5 | √3 | 0.577 |
| **1** | √5 | **0.618** (golden — one full unit) |

**Jonathan's band [½, φ] = the closure-unit band k ∈ [0, 1]** — from no self-reference (even) to one full unit (golden). The measured folds sit at **k ≈ ½** (pooled f=0.576 ⇒ k=0.49, field ≈√3; per-protein mean k=0.51). Read through the framework: the fold carries about half a unit of self-reference — off-origin, not the full golden unit — exactly the shift Jonathan predicted folding+rotation would cause.

## The honest boundary
Solid: the closure family √(1+4k) with k=1 ⇒ golden is a real result already in the work; the k-section mapping is exact, giving the band's endpoints principled meaning. **Not** solid: the folds' k≈0.49 is *indistinguishable from the null* (a uniform blob sits at k≈0.45), so k≈½ is where generic bisection lands, not proof the fold selected a golden-related unit. The √3/k=½ match is a fit read back through the mapping.

## What would turn the fit into a prediction
Derive, on the Shovelcat side, what folding + rotation (being off the origin) does to k — then check f forward instead of reading it backward. Until then: the mapping gives the band its meaning (real); the data places the folds at half a unit (fact, but = null).
