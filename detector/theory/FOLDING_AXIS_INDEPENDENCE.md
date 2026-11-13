# Axis Independence — the free routes are fewer than four

*Measured this session while building the content-matched benchmark harness. `STATE_OF_THE_DETECTOR`
§2 presents four orthogonal axes, of which two — spectral and mixedness — are described as
independent, model-free routes. Measured on the same 29 compression-parity images, **their headline
features correlate at 0.92–0.97**. They are largely one route seen twice. Companion to
`FOLDING_PHYSICS_OBSERVER`, `FOLDING_TWO_SIDED_WINDOW`, `FOLDING_RECONSTRUCTION`,
`FOLDING_OUTER_SLOT` Part III (routes must *stay* independent). Status: MEASURED, n = 29, one
generator family.*

---

## The measurement

Every spectral feature against every mixedness feature, |Pearson r|:

| spectral feature | max \|r\| vs mixedness | with | verdict |
|---|---|---|---|
| `slope` | **0.97** | `blur_ratio` | redundant |
| `hf_frac` | **0.96** | `blur_ratio` | redundant |
| `spec_entropy` | **0.92** | `blur_ratio` | redundant |
| `peak_energy` | **0.74** | `lap_var` | redundant |
| `one_over_f_r2` | 0.55 | `grad_kurt` | independent |
| **`resid_rms`** | **0.32** | `grad_kurt` | **independent** |

Four of six spectral features fail the project's own 0.7 independence bar against mixedness.

**This is not surprising once stated.** `blur_ratio` is `|grad(blur(x))| / |grad(x)|`; spectral `slope`
is the exponent of the 1/f power-law fit. Both are *how much high-frequency energy is in this image*.
Measuring it in the gradient domain and in the Fourier domain does not make it two observers — it makes
it one observer with two coordinate systems. `FOLDING_OUTER_SLOT` Part III is explicit that
manufactured agreement is the failure mode: *"if the models in the slot dissipate into each other…
you manufacture agreement and lose the seam."* Two routes reading the same quantity will always agree,
and that agreement carries no information.

---

## What the spectral axis actually contributes

**`resid_rms` — the deviation from the 1/f fit — is the genuinely orthogonal part** (max |r| = 0.32).
And it is the part the axis was *designed* around: `STATE_OF_THE_DETECTOR` §2 describes Axis 3 as
"real/natural images sit near a broadband, non-resonant (1/f) reference; generated images deviate with
a **resonant** pattern." The resonance is the idea. The slope is not — the slope is sharpness.

So the axis is not wrong, it is **mis-weighted**: its distinctive feature is `resid_rms`, and its
loudest features (`slope`, `hf_frac`, `spec_entropy`) are the blur axis in Fourier clothing. Dropping
or down-weighting those three would make the spectral route smaller and genuinely independent, which is
worth more to a committee than three extra correlated votes.

---

## The revised architecture picture

Counting *measured* independence rather than nominal axes:

| nominal axis | measured status |
|---|---|
| 1 — vision committee (Claude + Gemini) | genuinely distinct; model-based, not a pixel statistic |
| 2 — context router | genuinely distinct; operates on the activation mask, not the signal |
| **3 + 4 — spectral and mixedness** | **largely ONE route**: global high-frequency energy. Plus `resid_rms` as a real second piece |
| 5 — reconstruction | mostly redundant with that same HF route; `return_at_low` survives (\|r\| 0.61) |
| 6 — two-sided window | `nonlocal_asymmetry` independent of mixedness (0.67) — the strongest new free route |

**The free-route count is closer to three than five**: (a) global HF energy, (b) spectral resonance
residual, (c) predictability asymmetry — plus `return_at_low` as a marginal fourth. That is still a
real committee, and it is still model-free and $0. But *"four orthogonal axes"* is doing load-bearing
work in the pitch, and one of those orthogonality claims does not survive measurement.

**This strengthens the case for the physics observer** (`FOLDING_PHYSICS_OBSERVER`). The pixel-statistic
family keeps collapsing into one thing, because every member is ultimately a function of the same
frequency content. A lighting-consistency measure is a statistic of an *inferred scene*, not of the
pixel field, and is the only proposed route that is independent for a structural reason rather than an
empirical one.

---

## Honest ledger

**MEASURED**
- Spectral `slope` / `hf_frac` / `spec_entropy` vs mixedness `blur_ratio`: r = 0.97 / 0.96 / 0.92,
  n = 29, compression-parity images.
- `resid_rms` is the spectral axis's independent content (max |r| 0.32).

**CAVEATS**
- n = 29, one generator family, and the set is content-mismatched (`FOLDING_PHYSICS_OBSERVER` Part I).
  Content mismatch inflates *AUCs*; it is a weaker threat to *correlations between measures on the same
  images*, which is why this finding is more robust than the AUC numbers in the neighbouring docs — but
  it should still be re-checked on the matched benchmark.
- Correlation is measured on 29 points; ±0.1 is plausible sampling error. It does not move 0.97 to
  below the bar.

**ACTION**
- Re-run under `bench_all_axes.py`, which now performs this cross-axis audit automatically on every
  benchmark run, so redundancy is caught at measurement time rather than discovered later.
- Consider down-weighting `slope` / `hf_frac` / `spec_entropy` in the committee, or folding spectral and
  mixedness into a single declared route with `resid_rms` split out.

*Sources: `STATE_OF_THE_DETECTOR` §2 (the four-axis architecture), `FOLDING_OUTER_SLOT` Part III
(routes must stay independent or agreement is manufactured), `FOLDING_MIXEDNESS_CONFIDENCE`,
`FOLDING_TWO_SIDED_WINDOW` (the 0.7 bar), `FOLDING_PHYSICS_OBSERVER` (the content confound; the
structural-independence argument). Artifacts: `bench_all_axes.py`, `parity_metrics.json`.*
