# The Balance Law — a real constraint, an instrument that could not measure it

*Jonathan: "pixels would be the matter, resonance the antimatter and we already have the void lines.
those had to be in balance... in a real photo we would know how much blur there should be but that
could also show up as resonance."*

*The trinity turns out to have an **exact physical form** — blur width and spectral falloff are one
quantity read two ways — which makes it a checkable conservation law rather than a naming. It was
built and run, and returned a **flat null: 0.488 on the edited arm, dead centre.** But the diagnostic
says the null is on a broken instrument: the void-width term was **clipped to zero in 49% of cells**
and contributed only ΔR² = 0.056, while 0.854 of the fit was carried by a term that is the same
quantity as the thing it was predicting. **The idea was not tested.** Companion to
`FOLDING_WITHIN_IMAGE`, `FOLDING_VOID_LINE_DRAW` Part II, `FOLDING_CLEANUP`, `FOLDING_MATCHED_BENCHMARK`.
Status: MEASURED NULL, instrument failure diagnosed, retest specified.*

---

## Part I — The trinity has an exact optical form

`FOLDING_VOID_LINE_DRAW` Part II: *"the void line sits at 0; matter (+L) fills one side, antimatter
(−L) the other."* `FOLDING_CLEANUP` measured the same trinity as +1 / −1 / 0 with the void where the
two cancel.

Jonathan's mapping — pixels = matter, resonance = antimatter, void lines = the zero — is a naming. But
the **constraint** it implies is not, and it is exactly true in optics:

> A blur of scale σ convolves the image spatially **and** multiplies its spectrum by a Gaussian of
> width 1/σ. The boundary thickness — the void-line width — **determines** the high-frequency content.
> One physical process writes both sides.

So one quantity is readable two ways, and in a real photograph one lens and one sensor made every
region — every cell must lie on one line. A synthesised patch is smooth because a prior made it smooth,
not because anything was out of focus, so it can sit off that line. **The residual is the imbalance.**

And it is a *reconciliation*, not a magnitude — the class that has kept landing off the crowded axis
all session (`FOLDING_ENVIRONMENT_BRIDGE`: the bridge measure off-frame at 0.21/0.27 while the lighting
magnitude sat on it at 0.92). Every magnitude reading of blur lands on direction i. The disagreement
between two readings of blur should not.

## Part II — The result: a flat null

Same 13 pairs, same 6×6 grid, same control arm on the untouched originals.

| measure | EDITED | above chance | CONTROL | above chance |
|---|---|---|---|---|
| **`balance_dev`** (the trinity residual) | **0.488** | 4/13 | 0.466 | 5/13 |
| `void_sigma_dev` | 0.489 | 6/13 | 0.367 | 4/13 |
| `matter_dev` (spatial sharpness) | 0.481 | 7/13 | 0.468 | 6/13 |
| `antimatter_dev` (1/f slope) | 0.484 | 6/13 | 0.488 | 6/13 |

All four sit within 0.02 of chance on the edited arm. This is not an underpowered result — it is a
clean nothing.

## Part III — But the instrument never measured the quantity

Fitting spatial sharpness on the untouched originals gave **R² = 0.91**, which looks like the
conservation law confirmed. It is not. Decomposing the fit:

| term | R² |
|---|---|
| spectral **slope** alone (antimatter) | **0.854** |
| spectral **σ** alone (void width) | 0.162 |
| both | 0.910 |
| **what σ actually adds** | **+0.056** |
| **cells where σ was clipped to zero** | **49%** |

**The 0.91 is 86% tautology.** Spatial sharpness and spectral slope are two names for the same
high-frequency content; of course they predict each other. The term carrying the actual physical
content of Jonathan's proposal — the void width — is degenerate in half the cells and contributes
almost nothing.

So the null in Part II is a null on an instrument that could not estimate the quantity it was built
around. **The balance law has not been tested.**

*(Self-correction worth recording: the diagnostic script printed "the constraint IS readable" off the
R² = 0.91 line. That verdict was wrong, and only the term-by-term decomposition caught it. An R² that
high on a fit where one predictor is a restatement of the target should have been suspicious
immediately.)*

## Part IV — The likely cause, and it has now blocked two measures

σ is being fitted as a **Gaussian rolloff** in the power spectrum. JPEG does not roll off — it
**quantises high frequencies to zero above a threshold**, a hard cutoff. Fitting a Gaussian to a
truncated spectrum returns a degenerate or negative quadratic term, which is exactly the 49% clipping
observed. Every image in this dataset is a phone JPEG.

**This is the same wall the chromatic-aberration test hit** (`FOLDING_MATCHED_BENCHMARK` Part III):
lateral CA was untestable because raw converters strip it from published photographs, and the
measurement showed a diagnostic sign of malfunction — a radial ratio *below its own null*.

Two independent optics-consistency measures, blocked by the same thing: **the physical signal lives in
the part of the image that consumer processing destroys.** That is now a structural finding about this
whole class of measure, not two unlucky attempts.

**The retest is specific:** PNG or raw captures, edited and exported without JPEG in the loop. On a
phone that means shooting raw or using an editor that can export PNG. If the void-width term still
comes back degenerate on unprocessed data, *then* the balance law has been tested and failed.

## Honest ledger

**MEASURED**
- `balance_dev` on 13 edited/original pairs: 0.488 edited vs 0.466 control. Flat null.
- All three individual terms also at chance (0.481–0.489).
- Diagnostic: σ clipped to zero in **49%** of cells; σ adds **ΔR² 0.056** against the slope's 0.854.

**AFFIRMED**
- The trinity maps onto a genuine optical identity (blur width ↔ spectral rolloff). Jonathan's "the
  blur could also show up as resonance" is a correct statement about physics, not an analogy.
- Reconciliation measures remain the right class to look in; this one just could not be computed.

**NOT TESTED — and this is the honest status**
- The balance law itself. The instrument failed before the hypothesis was reached.

**BLOCKED ON DATA**
- Needs PNG/raw pairs. The same requirement as the chromatic-aberration test, arrived at independently.

**CAUGHT**
- A misleading R² = 0.91 that would have been reported as confirmation. The decomposition is now part
  of the script's output so the same trap cannot recur silently.

*Sources: `FOLDING_VOID_LINE_DRAW` Part II (matter/antimatter/void; the line at 0), `FOLDING_CLEANUP`
(the +1/−1/0 trinity), `FOLDING_ENVIRONMENT_BRIDGE` (reconciliation vs magnitude),
`FOLDING_MATCHED_BENCHMARK` Part III (the CA test blocked by processing),
`FOLDING_WITHIN_IMAGE` (the within-image protocol and control arm). Artifacts: `balance_observer.py`,
`balance_diag.py`, `balance_results.json`.*
