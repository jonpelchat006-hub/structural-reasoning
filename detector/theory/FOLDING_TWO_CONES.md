# Two Cones — independence comes from asking a different question, not hiring a different vendor

*Jonathan: "is it like the edited spots are like hidden bodies in the frame that behave differently
from everything else? like they would use the frequencies instead of the pixel stuff when its all
supposed to be pixel? is it like ai generated stuff is more resonance based and those appear as spots
that would normally be outside the cones?"*

*All three hold, and the third was measurable. At cell level the spectral reader and the semantic
reader correlate at **|r| = 0.14** — against 0.91 for GPT-vs-Gemini and 0.94 for one model run twice.
**A different observer TYPE buys five times the independence that a different vendor does.** That
reframes the whole committee architecture. Companion to `FOLDING_WITHIN_IMAGE`, `FOLDING_OBSERVERS_AS_D`,
`FOLDING_SEAM_TEST`, `FOLDING_C_PIXELS`, `FOLDING_SKIN` §3.3. Status: MEASURED, n = 13 pairs.*

---

## Part I — "Hidden bodies" is the right description, and it is Jonathan's own phrase

An edited region is visually coherent — the committee cannot find it (`FOLDING_SEAM_TEST`: edited arm
0.538, identical to its own control) and neither can a person glancing at it. But its *internal
statistical constitution* differs from the frame it sits in. Something is in there with a different
composition that does not announce itself.

`FOLDING_C_PIXELS` already named this shape, from the protein side: the buried C core as *"an outside
thing, on the inside."* A generative edit is literally that — foreign material placed inside the frame
and sealed over. And it explains **why the semantic reader is blind to it**: a coherent scene is a
coherent scene. Only a reader that asks about *constitution* rather than *content* sees the foreign
body.

## Part II — "Frequencies where it should be pixels" — this is the mechanism, stated precisely

This is the sharpest part of the question and it is substantially correct.

**A photograph's spectrum is emergent.** The camera generates the image *pixel-wise and locally* — each
photosite integrates photons independently, shot noise is spatially independent, and demosaicing spreads
it over a small neighbourhood. Nothing imposes a frequency structure. The 1/f falloff appears because
natural scenes happen to be scale-invariant; it is a *consequence*, not a design.

**A diffusion patch's spectrum is constructed.** The noise schedule commits structure in frequency
order — coarse first at high noise, fine last at low noise. That is not a metaphor: it is the same
identification `FOLDING_OUTER_SLOT` Part V made when it matched noise level to the thickness-by-level
knob. And the denoiser is a finite network: fixed receptive fields, upsampling stages, and in latent
models a decoder with fixed kernels and strides on a fixed latent grid. Those imprint **characteristic
frequencies** the scene never had.

So: *the photograph's spectrum falls out of physics; the generated patch's spectrum is built, and
carries the builder's own preferred frequencies.*

**That is exactly why the discriminating quantity is the residual from the 1/f fit and not the slope.**
The slope is scene content — which is why it collided with blur at r = 0.97 (`FOLDING_AXIS_INDEPENDENCE`)
and died on the matched benchmark. The residual is the imprint. `STATE_OF_THE_DETECTOR` §2 said this
from the start — *"generated images deviate with a resonant pattern"* — and it is the one claim in the
document that keeps surviving tests.

**Honest note:** the mechanism above is well established in the forensics literature (spectral
fingerprints of generative upsampling and decoder periodicity). Jonathan arrived at it from the
framework rather than from that literature, which is a point in the framework's favour — but it is
*borrowed* ground, not ground this project has demonstrated.

## Part III — "Outside the cones" — measured, and it is the finding

`FOLDING_SKIN` §3.3 defines the cone as the compatibility tolerance: inside it an element dissipates
and merges, outside it a seam persists. Jonathan's question is whether an edit sits **inside one
observer's cone and outside another's**.

Measured at cell level, on the 13 edited images:

| pair | correlation |
|---|---|
| claude vs claude (same model, two samples) | **0.94** |
| gpt vs gemini | **0.91** |
| claude vs grok — most independent *models* | **0.70** |
| **semantic committee vs spectral reader** | **0.14** |

**|r| = 0.14, mean r = −0.02.** The two readers are essentially uncorrelated. They are looking at
different things, so an edit can be well inside the semantic cone — coherent, plausible, accepted — and
outside the spectral cone at the same time. That is precisely what "spots outside the cones" describes,
and it is why the committee cleared regions the spectral reader flags.

### What this does to the committee architecture

`FOLDING_OBSERVERS_AS_D` established that observers are D-class cofactors and that D must be
*chemically distinct* to count. It then measured that the entire independence budget across four
vendors spans 0.94 → 0.70 — vendor diversity buys very little distinctness.

**One change of observer type buys 0.14.** Roughly five times the independence of the best model pair,
for a measure that is free, local, and runs in ten seconds.

So the committee was assembled along the wrong axis. Adding a fourth frontier model is buying almost
nothing; adding one reader that asks a *different kind of question* is the move. That is the same
lesson as `FOLDING_TWO_SIDED_WINDOW` — where the gap between two blind spots was the measurement — now
applying to observer design rather than to scale.

### A caution against the neat story

spec_dev localises slightly **better** in cells the committee flagged (0.652, 8/11) than in cells it
cleared (0.578, 3/8). So the two readers are independent in *what they measure* without being
complementary in *where they succeed* — busy cells are probably easier for both. **The clean
"one covers the other's blind spot" story is not established**, only the independence is. On n = 13
with 8 and 11 usable splits, this could reverse.

## Part IV — CORRECTION: independence is not usefulness

*Added after the fact, and it overturns this doc's practical recommendation.*

The claim below — that the minimum interesting committee is one semantic reader plus one spectral
reader — was **never tested for incremental value**. It has now been, on the 58-image matched
benchmark, and it fails:

| | stratified AUC |
|---|---|
| semantic reader alone (one claude call) | **0.927** |
| free spectral reader alone (`resid_rms`) | 0.662 |
| **semantic + spectral** | **0.887** |
| semantic + `one_over_f_r2` | 0.875 |
| semantic + `nonlocal_asymmetry` | 0.832 |
| semantic + `env_scale_agreement` | 0.850 |

**Every combination is worse than the semantic reader alone.** Adding the independent reader costs
0.040 to 0.095 AUC.

The error in this doc's reasoning: **independence is necessary but not sufficient.** A committee member
must be independent *and* accurate. At 0.662 the spectral reader is too weak, so its independent vote
drags the ensemble down rather than lifting it — which is elementary ensemble behaviour and should have
been caveated when the r = 0.14 was reported.

The r = 0.14 measurement stands. The recommendation built on it does not. The spectral reader's value,
if it has one, is in **localisation** (`FOLDING_WITHIN_IMAGE`: 0.641 vs the committee's 0.538 against a
null control), not in the verdict.

---

## Honest ledger

**MEASURED (13 edited images, cell level)**
- semantic committee vs spectral reader: mean |r| **0.14**, mean r −0.02.
- Against 0.94 (same model), 0.91 (gpt/gemini), 0.70 (claude/grok) from `FOLDING_OBSERVERS_AS_D`.
- spec_dev localisation is not better in committee-cleared cells (0.578, 3/8) than in flagged ones
  (0.652, 8/11).

**AFFIRMED, WITH SOURCES**
- "Hidden bodies" = `FOLDING_C_PIXELS`'s "outside thing, on the inside."
- The emergent-vs-constructed spectrum argument is sound and is standard in the forensics literature;
  it explains why the *residual*, not the slope, is the surviving feature.

**CAVEATS**
- n = 13. spec_dev itself is weak (0.641, 10/13, `FOLDING_WITHIN_IMAGE`) and its size-trend artifact is
  unfixed.
- The correlation is measured on edited images only, at one grid size, with one spectral estimator.
- The mechanism in Part II is borrowed, not demonstrated here.

**WHAT TO DO WITH IT**
- ~~Buy independence by adding observer types.~~ **Superseded by Part IV**: the independent reader
  does not improve the verdict. Independence without accuracy costs AUC.
- The spectral reader's only demonstrated value is **localisation**, where the committee scores zero.
- Test a third type (a physics/environment reader, `FOLDING_PHYSICS_OBSERVER`) against both. If type
  diversity is the real axis, it should land near 0.14 against each — and that would be k.

*Sources: `FOLDING_OBSERVERS_AS_D` (the vendor-independence matrix), `FOLDING_WITHIN_IMAGE` (spec_dev),
`FOLDING_SEAM_TEST` (the committee's failure to localise), `FOLDING_C_PIXELS` ("an outside thing, on
the inside"), `FOLDING_SKIN` §3.3 (the compatibility cone), `FOLDING_OUTER_SLOT` Part V (noise level =
thickness by level), `FOLDING_AXIS_INDEPENDENCE`, `STATE_OF_THE_DETECTOR` §2. Artifacts:
`two_cones.py`, `within_image_observers.py`.*
