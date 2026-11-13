# The Matched Benchmark — nothing survives it

*The content-matched, compression-matched, multi-generator test finally ran. **Every model-free
measure in the project collapses to noise.** The two-atom detector's basis is gone: `nonlocal_asymmetry`
0.858 → **0.454**, `blur_ratio` 0.882 → **0.424**, `spectral.slope` 0.907 → **0.617**. Nothing reaches
|AUC − 0.5| ≥ 0.25. This is the result the whole session's discipline was built to produce, and it
means the numbers in every neighbouring doc were confounds. Companion to `FOLDING_PHYSICS_OBSERVER`
(which predicted this), `FOLDING_OBSERVER_FRAME`, `FOLDING_TWO_SIDED_WINDOW`,
`FOLDING_AXIS_INDEPENDENCE`. Status: MEASURED. Caveats in Part IV are load-bearing.*

---

## Part I — The test

| | real | AI |
|---|---|---|
| **portrait** | 12 (stock / editorial photography) | 14 |
| **landscape** | 21 (published landscape photography) | 11 |

AI class spans **six generator families** — flux-2-pro, gpt-image-2, nano-banana, nano-banana-pro,
seedream-5-pro, davinci (plus two topaz upscales). Both classes resized to 512 px and re-encoded
through the identical JPEG q85 path. AUC computed **within each content bucket** and pooled, so
"portrait vs landscape" cannot masquerade as "AI vs real".

This closes all three confounds at once: compression, content, and — because the real class now comes
from many photographers and many cameras rather than one phone — the **device** confound Jonathan
raised himself.

## Part II — The result

| feature | stratified AUC | \|d\| | landscape | portrait |
|---|---|---|---|---|
| `spectral.one_over_f_r2` | 0.664 | **0.164** | 0.65 | 0.68 |
| `spectral.resid_rms` | 0.338 | **0.162** | 0.34 | 0.34 |
| `spectral.hf_frac` | 0.649 | 0.149 | 0.64 | 0.67 |
| `bridge.env_concentration` | 0.643 | 0.143 | 0.64 | — |
| `spectral.slope` | 0.617 | 0.117 | 0.58 | 0.67 |
| `mixed.blur_ratio` | 0.424 | 0.076 | — | — |
| **`window.nonlocal_asymmetry`** | **0.454** | **0.046** | — | — |

**Nothing clears the 0.25 bar. The best measure in the project is at 0.164.**

### What died, and how far it fell

| measure | old (confounded) set | matched set |
|---|---|---|
| `spectral.slope` (**i**) | 0.907 | **0.617** |
| `mixed.blur_ratio` (**i**) | 0.882 | **0.424** |
| `nonlocal_asymmetry` (**j**) | 0.858 | **0.454** |
| two-atom detector | 0.931 | — basis gone |

`nonlocal_asymmetry` is the worst casualty, and it was the session's best original result. It fell
almost exactly to chance. The predictability-asymmetry *mechanism* may still be real — a photograph does
have an outside — but **on this data it does not separate the classes**, and the 0.858 is explained by
content and generator-family rather than by provenance.

The lens observer (Jonathan's newest idea) also failed, and inverted: `ca_radial_ratio` real 0.278 vs
AI 0.334, `ca_growth` real 0.035 vs AI 0.119 — AI images showed *more* radial chromatic structure than
real photographs, at |d| ≤ 0.128. See Part III.

## Part III — Why the lens test could not have worked on this data

Two separate problems, and both are worth recording because the idea is sound.

**1. The instrument is malfunctioning, and there is a tell.** For displacement vectors with no
preferred direction, the expected radial fraction is `2/π ≈ 0.64`. Both classes measured **0.28–0.33**
— *below random*. A measure that lands below its own null is not weakly detecting; it is dominated by
something other than what it claims to measure, almost certainly sub-pixel registration noise on
patches whose true shift is near zero, where "direction" is meaningless. The fix is to count only
patches whose shift magnitude clears the noise floor. Recorded so the next attempt starts from a known
defect rather than a mystery.

**2. Professional photographs have had their chromatic aberration removed.** Every raw converter
(Lightroom, Camera Raw, Capture One) applies lens-correction profiles by default, and published
landscape and editorial work is universally processed that way. So the real class here has been
*lens-corrected*, while the AI class never had a lens to correct. **Lateral CA is untestable on
published photography by construction.**

The sharp irony: Jonathan's own phone snapshots — the set discarded for being one device with a blurry
lens — are the *right* data for this test, because they are closer to camera-original. The CA test
needs unedited files, ideally raw. That is a real, specific data requirement, not a dead end.

## Part IV — Caveats, and they cut both ways

- **n is small per bucket.** Landscape 21×11, portrait 12×14. Stratified AUC at that size carries
  roughly ±0.15. So the honest statement is not "these measures are worthless" but **"none of them
  demonstrates an effect at this sample size"** — which, after a session of measures that looked like
  0.85–0.95, is the finding.
- **The generators are much better.** flux-2-pro, gpt-image-2, nano-banana-pro and seedream-5-pro are
  current models; the earlier set was Midjourney. Part of this collapse is probably real progress in
  generation, not only confound removal. That is worse news, not better: it means low-level statistical
  detection has a shrinking runway.
- **The real class changed population.** Web-sourced professional photography is heavily processed —
  sharpened, denoised, lens-corrected, recompressed. That makes real photographs *more* processed and
  therefore *more* AI-like on exactly these statistics. A camera-original real class would be a
  different, and probably easier, test. Both populations are legitimate; they answer different product
  questions ("is this published image generated?" vs "is this file straight from a camera?").
- **The vision committee was NOT tested here.** Axes 1 and 2 — Claude + Gemini reading the image, and
  the context router — were not run. This benchmark says nothing about them, and they are model-based
  rather than pixel statistics, so nothing here transfers to them. **They may be carrying the entire
  product.** That is now the most important open question in the project.

## Part V — The one lead

Two features are weakly separated **and consistent across both content buckets**:

- `spectral.one_over_f_r2` — 0.65 landscape, 0.68 portrait
- `spectral.resid_rms` — 0.34 landscape, **0.34** portrait

Consistency across independent buckets is worth more than magnitude here: a feature at 0.34 in both is
more credible than one at 0.20 and 0.50. And these two are **the same thing** — how well the image's
power spectrum fits a 1/f law, and what is left over when it does not.

That is precisely the part `FOLDING_AXIS_INDEPENDENCE` identified as the spectral axis's genuinely
independent content (max |r| 0.32 with mixedness, against 0.97 for `slope`), and precisely what
`STATE_OF_THE_DETECTOR` §2 says the axis was designed around: *"real/natural images sit near a
broadband, non-resonant (1/f) reference; generated images deviate with a resonant pattern."*

**The resonance survived; the sharpness did not.** The loud features died and the designed one is the
last thing standing — weakly, at |d| ≈ 0.16, needing far more data to become a claim. If anything in
the model-free stack is worth pursuing, it is this, measured properly on a few hundred images per
bucket.

## Honest ledger

**MEASURED**
- Content-matched, compression-matched, six-generator, multi-photographer benchmark, n = 58.
- Nothing exceeds |AUC − 0.5| = 0.164. Every headline number from earlier in this session is a confound.
- `nonlocal_asymmetry` 0.858 → 0.454; `blur_ratio` 0.882 → 0.424; `spectral.slope` 0.907 → 0.617.
- Lens/CA: |d| ≤ 0.128 and inverted; instrument measured *below its own null* (0.28–0.33 vs 0.64).
- Weak but bucket-consistent: the 1/f fit-quality pair.

**NOT TESTED**
- The vision committee (axes 1–2). The `bench_all_axes.py` run covers model-free axes only.
- The reconstruction axis was skipped in this run for cost; its one marginal feature (`return_at_low`)
  is unmeasured on matched data.
- Jonathan's **material-as-environment** proposal for art (oil, pencil, canvas weave as the environment
  in place of illumination) — a good generalisation of the environment slot, and completely untested.

**WHAT THIS DOES NOT SAY**
- It does not say the framework is wrong. The frame analysis (`FOLDING_OBSERVER_FRAME`) is a statement
  about *relationships between measures on identical images*, which survives a class-separation
  failure. Effective rank 2.82 and the 0.926 → 0.505 sign collapse are still true; there is simply
  much less signal to arrange.
- It does not say the product cannot work. It says the **free half** has no demonstrated generalising
  signal, and the paid half is now the thing to test.

*Sources: `FOLDING_PHYSICS_OBSERVER` (the content confound, which predicted this),
`FOLDING_AXIS_INDEPENDENCE` (resid_rms as the spectral axis's independent content),
`FOLDING_TWO_SIDED_WINDOW`, `FOLDING_OBSERVER_FRAME`, `STATE_OF_THE_DETECTOR` §2. Artifacts:
`bench_all_axes.py`, `bench_matched.json`, `lens_observer.py`, `lens_native.json`.*
