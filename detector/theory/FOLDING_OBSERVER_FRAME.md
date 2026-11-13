# The Observer Frame — the axes span 2.8 dimensions, and the sign error costs everything

*Captures a working session (Jonathan + Claude). Jonathan: "wouldn't the observer axes also follow the
quaternion stuff? so some of them should only be on the i axis and some on j, and they would be nested
too. so would it be like spectral is one level down on the blur axis? … maybe we were getting a sign
error because we were using an already combined axis?"*

*All three parts were measurable on the 29 compression-parity images, and all three came back yes.
The detector's 23 features across 4 nominal axes span an **effective rank of 2.82**; exactly two
directions carry signal; and combining those two with the wrong relative sign collapses the committee
from **AUC 0.926 to 0.505** — chance. Companion to `FOLDING_AXIS_INDEPENDENCE`, `FOLDING_OBSERVERS`
(the spanning frame), `FOLDING_FLOORS` §1 (near-orthogonal successive cuts),
`FOLDING_PHYSICS_OBSERVER`. Status: MEASURED, n = 29, one generator family, content-unmatched set —
see caveats.*

---

## Part I — The frame is real, and it is nearly empty

`FOLDING_OBSERVERS` already says the observers should be a **spanning frame**: *"larger structure
looking down / C-core / window-local / neighbouring-C on the tangent ≈ global + normal + local +
tangent — a complete orthonormal basis riding the chain,"* and it measured that a complete frame is
exactly what recovers the invariant fully. `FOLDING_FLOORS` §1 measured successive cuts crossing at
mean **64.3°, 0/8 parallel — "leaning orthogonal (quaternion i/j/k)."*

So the right question is not "is this feature redundant?" but **"which basis direction is it, and which
directions are empty?"** That is Jonathan's reframing, and it is a better question because it is
constructive: it tells you what to build next instead of only what to delete.

Measured — 23 features (spectral, mixedness, reconstruction, two-sided window), correlation-matrix
eigendecomposition:

| | variance | AUC | \|d\| | what loads on it |
|---|---|---|---|---|
| **PC1 — call it i** | **57%** | 0.196 | **0.304** | `thermal_slope`, `return_at_high`, `nonlocal_err_fine`, `spec_entropy` |
| **PC2 — call it j** | **10%** | 0.824 | **0.324** | `nonlocal_asymmetry` (+0.42) vs `mix_frac`, `mix_mean`, `struct_residual` |
| PC3 | 8% | 0.515 | 0.015 | `resid_rms`, `one_over_f_r2` |
| PC4 | 6% | 0.485 | 0.015 | `ladder_fb_agreement`, `sharp_cv` |
| PC5 | 5% | 0.431 | 0.069 | — |

**Effective rank (participation ratio) = 2.82.** Twenty-three features, four nominal axes, under three
effective dimensions.

**Exactly two directions carry signal.** PC1 is the *sharpness / high-frequency energy* direction —
this is what `FOLDING_AXIS_INDEPENDENCE` found spectral and mixedness both sitting on. PC2 is the
*predictability-asymmetry* direction, and `nonlocal_asymmetry` is its dominant loading, which is
exactly why that measure cleared the independence bar when everything else failed. **PC3 through PC5
carry no signal at all** (|d| = 0.015, 0.015, 0.069) despite holding 19% of the variance.

**And j carries as much signal as i on six times less variance.** 0.324 vs 0.304, from 10% of the
variance against 57%. Variance is not information. A committee that weights routes by how much they
vary — or that simply has more members on one direction — will drown j in copies of i, which is what
this detector has been doing.

---

## Part II — "Spectral is one level down on the blur axis" — yes, and that is re-basing, not a new axis

Jonathan's guess about nesting is the right description of the r = 0.97 result. Spectral `slope` and
mixedness `blur_ratio` are not two directions at a shallow angle; they are **the same direction read in
two coordinate systems** — gradient domain and Fourier domain. The corpus already has the word for
this: `FOLDING_FLOORS`' **roof/floor re-basing**, where you fold into the next floor's fresh square and
*"the C line stays on the new wall."* Same line, new frame. A re-basing gives you a new *reading* of an
existing direction; it does not give you a new direction, and it must not be counted as an extra
committee member.

The practical rule this implies: **before adding a route, project it onto the existing frame.** If its
residual after projection is small, it is a re-basing — keep it if the new coordinates are more
convenient to compute, but do not let it vote twice.

---

## Part III — The sign error, and what it actually costs

Jonathan: *"there is also the property where when you multiply them it comes out to -1… maybe we were
getting a sign error because we were using an already combined axis?"*

**The two occupied directions point opposite ways.** PC1 is higher in AI (AUC 0.196); PC2 is higher in
real (0.824). They are orthogonal by construction (r = 0.000) and *anti-aligned in label*. So any
feature that mixes them carries a sign that depends on its mixing ratio — and any combiner that adds
them without checking gets partial or total cancellation.

Measured, on the same 29 images:

| combination | signed AUC |
|---|---|
| i alone | 0.804 |
| j alone | 0.824 |
| **i + j, signs aligned** | **0.926** |
| **i + j, signs NOT aligned** | **0.505** |

**0.505 is chance.** Two directions that each carry 0.80+ annihilate each other completely when added
with the wrong relative sign. This is not degradation, it is destruction — and it is invisible from
inside, because the committee still returns confident-looking scores.

**This is exactly the failure `FOLDING_RECONSTRUCTION` Part 0 was written to prevent.** The polarity
confusion latent in `FOLDING_OUTER_SLOT` Part V ("converge = generated" against the committee's
"converge = authentic") would have caused precisely this: a route added with the inherited sign,
sitting anti-aligned to the direction it should have reinforced. The rule stated there — *emit raw
unsigned sub-measures, fit the sign on data, never inherit one* — now has a price tag on it: **0.42
AUC.**

So Jonathan's diagnosis is right, and one level up from where he pointed it. The problem is not that a
particular feature was secretly a blend; `seed_convergence`, the feature whose sign came back inverted,
is actually *pure* (purity 0.84 on one direction) — it was inverted because the mechanistic prediction
was simply wrong, not because it was mixed. The real mixing hazard is at the **basis** level: i and j
are anti-aligned, so *every* composite of them has an unstable sign, and the committee is a composite
by definition.

---

## Part IV — What transfers from the quaternions, honestly

**What is real and now measured:**
- **A spanning orthonormal frame** is the right model for a committee. Already in `FOLDING_OBSERVERS`
  (global + normal + local + tangent), already measured as near-orthogonal successive cuts
  (`FOLDING_FLOORS` 64.3°), and now measured directly in the detector's own feature space.
- **`ij = k` — combining two independent directions generates capability neither had.** Measured: i
  alone 0.804, j alone 0.824, i + j **0.926**. The product is not an average; it opens a direction. This
  is the one algebraic property that transfers with real content.
- **Order and sign matter absolutely** — the quaternion's `ij = −ji` has a genuine echo here, in that
  getting the relative sign wrong is not a small error but a total one (0.926 → 0.505).

**What does not transfer, and should not be claimed:**
- **`i² = j² = k² = ijk = −1` does not hold on detector scores.** Feature space is a real
  inner-product space, not a division algebra. There is no multiplication of two axis scores that
  yields −1, and writing one down would be numerology. The −1 in the quaternions is a rotation by π in
  a specific algebra; the −1 that matters here is an anti-correlation between two label directions.
  They are different objects that happen to share a symbol.

Stated plainly: **the frame picture is load-bearing and just earned its keep; the specific algebra is a
metaphor.** Keeping those separate is what makes the frame claim usable rather than decorative.

---

## Part V — k is empty, and we know what goes in it

Two directions occupied, and the third — the one a complete frame requires — has nothing in it. Every
route built so far is a statistic of the pixel field, so every new one lands on i or, at best, j.
`FOLDING_PHYSICS_OBSERVER` argues that lighting consistency is independent for a *structural* reason:
it is a statistic of an inferred 3D scene rather than of the pixel distribution. **That is the
candidate for k**, and this analysis is the reason to prioritise it — not because it would add another
feature, but because it is the only proposal that could occupy an empty basis direction rather than
thickening an occupied one.

**Which gives the axis-design rule going forward:** a new route is worth building only if it is
expected to land on an *unoccupied* direction. Project first, build second.

---

## Honest ledger

**MEASURED THIS SESSION (n = 29, compression parity, one generator family)**
- Effective rank 2.82 across 23 features / 4 nominal axes; PC1 = 57% of variance.
- Exactly two directions carry label signal (|d| 0.304, 0.324); PC3–PC5 carry none (0.015–0.069).
- The two are **anti-aligned in label** and orthogonal in feature space.
- Sign-aligned combination 0.926; sign-misaligned 0.505 (chance).
- `nonlocal_asymmetry` is the dominant loading of the second direction — a structural explanation for
  why it passed the independence bar.

**CAVEATS — these matter here**
- n = 29 with 23 features. An eigendecomposition at that ratio is unstable in its *details*; PC3–PC5
  loadings should not be trusted individually. The headline numbers (effective rank ≈ 3, two signal
  directions, the sign collapse) are large enough to survive it, but should be re-derived on the
  matched benchmark.
- The set is content-mismatched (`FOLDING_PHYSICS_OBSERVER` Part I). Content inflates AUCs; it is a
  weaker threat to the *geometry* (correlations among measures on identical images), which is why this
  result is more robust than the AUC values in neighbouring docs — but "more robust" is not "clean."
- The 0.926 is an unweighted two-component sum with no held-out set. It is a demonstration of the sign
  effect, not a benchmark number.

**ACTION**
- Add the effective-rank and PC-signal report to `bench_all_axes.py` so frame occupancy is measured on
  every run alongside redundancy.
- Fit the committee's signs per-direction, not per-axis.
- Prioritise the physics observer as the k candidate.

*Sources: `FOLDING_OBSERVERS` (the spanning frame; agreement = invariant), `FOLDING_FLOORS` §1
(64.3° near-orthogonal cuts; roof/floor re-basing), `FOLDING_AXIS_INDEPENDENCE` (spectral ≈ mixedness
at r 0.97), `FOLDING_RECONSTRUCTION` Part 0 (the polarity rule this puts a price on),
`FOLDING_TWO_SIDED_WINDOW` (`nonlocal_asymmetry`), `FOLDING_PHYSICS_OBSERVER` (the k candidate),
`FOLDING_OUTER_SLOT` Part III (routes must stay independent). Artifacts: `parity_metrics.json`,
`nonlocal_metrics.json`.*
