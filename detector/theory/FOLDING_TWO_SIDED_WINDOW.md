# The Two-Sided Window — predictability asymmetry, and the best independent signal yet

*Captures a working session (Jonathan + Claude). Jonathan's claim: "real things are more predictable
aren't they? the shape of a person should settle back into a person, but the prediction of a person
would settle back into the prediction. and a mark on someones face is completely random, we wouldn't
be able to predict it at all, so things should drift more from things like that... our window would
have observers on both sides, but there is a primary direction through the whole structure, so the one
looking back would see the whole thing and the other would see the individual marks?"*

*It turns out to unify two results the corpus had already measured **from opposite ends and never
connected**, and — once implemented with the right predictor — it produces the first new measure in
this detector line that beats the independence bar. Companion to `FOLDING_RECONSTRUCTION` (whose
strongest measures failed that bar), `FOLDING_OBSERVERS`, `FOLDING_UNIVERSAL_READER`,
`FOLDING_WINDOW_SEAM`, `FOLDING_STAIRCASE`. Status: built and benchmarked, n = 12 real / 17 AI at
compression parity. One confirmed result, one instructive failure, small n.*

---

## Part I — The claim, decomposed

Jonathan's sentence contains two opposite statements about the same image, and the power is in the
*pair*, not either half:

| scale | real photograph | generated image |
|---|---|---|
| **structure** (a person's shape) | predictable — settles back into a person | predictable — settles back into *the prediction* |
| **mark** (a mole, a stray hair, grain) | **unpredictable** — nothing generated it but the world | **predictable** — it came from the same predictor as the structure |

A photograph has an **outside**. Light, optics, skin, dust and a sensor put information into it that
no process inside the image can account for. A generated image has no outside: its marks and its
structure were drawn from one distribution, so its marks are conditionally predictable in a way a real
mark is not.

**Therefore the discriminant is neither term alone — it is the gap between them.** "Is this image
predictable?" is the wrong question. "Is this image *much less* predictable at the mark scale than at
the structure scale?" is the right one. That distinction is what makes this measurable, and it is
exactly what Jonathan's "coming at it from 2 directions… things are inverted and both sides work
together" says.

---

## Part II — The corpus already measured both observers, from opposite ends

This is the part worth flagging: the two-sided window is not a new hypothesis. It is **two existing
tested results** that were never put side by side.

**The observer looking along the primary direction — sees the whole, blind to the marks.**
`FOLDING_OBSERVERS`, honest ceiling: three orthogonal observers recover the coarse ±1 height **100%**
on the large-offset proteins, and the doc states the limit plainly — *"the committee gets the big true
things every time and the tiny things never."* A global committee resolves structure and cannot
resolve detail. **Tested.**

**The observer looking back — sees its own mark, blind to the whole.**
`FOLDING_UNIVERSAL_READER`: every C residue confirms the boundary it sits on from its own neighbourhood
(**95–100%**, A and B neighbours at 110–131°, opposite sides) — and the same doc's honest seam:
*"it cannot know where the whole C line goes from its own neighbourhood"* (`FOLDING_WINDOW_SEAM`: the
seam's global route is not locally readable). A local registrar resolves detail and cannot resolve
structure. **Tested.**

Two observers, each measured, each with a *complementary blind spot*. Jonathan's window with a face on
each side is the correct reading of the pair, and `FOLDING_UNIVERSAL_READER` states the architecture
almost literally: *"two cones tip-to-tip — the bidirectional transducer… outside cone catches the
point; inside cone sends it on."* The detector already runs this shape too — `SHOVELCAT_CHECKER_V6` §3
has the Dolphin forward pass as φ and the Shark backward pass as ψ, accepting where they agree.

What was missing is that **their blind spots are the measurement.** Compare what each observer can
predict, and the *difference between two blind spots* is the signature of an outside.

---

## Part III — Attempt 1: right idea, wrong predictor (instructive failure)

`predictability_observer.py`. Mask a checkerboard of b×b blocks and reconstruct them from context by
harmonic (Laplace) diffusion — deliberately the *same* fill engine as `FOLDING_VOID_LINE_DRAW` Part
III, run as a predictor. Sweep b ∈ {2,4,8,16,32}; take `E(fine)/E(coarse)`.

**The direction came out exactly as predicted.** Asymmetry **0.320 real vs 0.188 AI**, AUC 0.740, and
the ratio beat both of its own endpoints (fine 0.706, coarse 0.627) — the gap was doing real work.

**And it failed the independence bar hard: |r| = 0.89 with `lap_var`.** Higher than anything else
measured in this line. Combining it with blur (0.868) did not beat blur alone (0.882). It added
nothing.

**The diagnosis is specific and it is a property of the predictor, not of the idea.** A Laplace fill
blurs across everything, so *any* high-frequency content registers as unpredictable. But **a real edge
is sharp and perfectly predictable** — it continues, and a dozen other edges in the same photograph
look just like it. A smooth interpolator cannot represent "sharp but regular," so it collapses
*unpredictable* and *sharp* into one number. That number already has a name: `lap_var`.

I had predicted the ratio would cancel the blur confound as common mode. It did not, because the fine
and coarse terms do not carry the confound with the same scaling. That reasoning was wrong.

---

## Part IV — Attempt 2: read from the neighbours

The fix is named in `FOLDING_UNIVERSAL_READER`'s own question — *"do readers see only their neighbors
and confirm A/B/C"*. The local observer does not work by smoothing. It works by **comparison with its
neighbourhood**.

`nonlocal_observer.py`: predict each block by searching the **same image** for the patch whose
surrounding ring best matches this block's ring (cosine distance, DC removed, self and near-neighbours
excluded), then copying that patch's centre. The rest of the image is the model.

- a sharp edge → other edges match its ring → **predicted well**
- a repeated texture → recurs → **predicted well**
- a mole, a stray hair, sensor grain → nothing else in the image predicts it → **predicted badly**

Sharpness is decoupled *by construction*. That is the entire point of the change.

Measured at the mark scale (b=4) and the structure scale (b=16), same 29 parity images:

| feature | real | AI | AUC | \|d\| |
|---|---|---|---|---|
| `nonlocal_err_fine` | 0.207 | 0.096 | 0.672 | 0.172 |
| `nonlocal_err_coarse` | 0.384 | 0.287 | 0.559 | 0.059 |
| **`nonlocal_asymmetry`** | **0.525** | **0.331** | **0.858** | **0.358** |

**The ratio scores 0.858 while neither endpoint clears 0.68.** A measure that beats both its own
components by that margin is not a repackaged endpoint — the asymmetry itself is the signal, which is
precisely Jonathan's claim.

---

## Part V — The independence audit it passes

Same pre-registered bar as `FOLDING_RECONSTRUCTION` Part VI: |r| > 0.7 with the mixedness axis means
it is the blur axis wearing a hat.

| feature | max \|r\| vs mixedness | verdict |
|---|---|---|
| `nonlocal_err_fine` | 0.91 (lap_var) | redundant |
| `nonlocal_err_coarse` | 0.80 | redundant |
| **`nonlocal_asymmetry`** | **0.67** (blur_ratio) | **independent** |

**Both endpoints are redundant and the ratio is not.** That is the decoupling working exactly as
designed, and it is the cleanest evidence in this line that the framework's two-observer picture buys
something a single magnitude cannot.

It is also independent of the reconstruction axis: |r| = 0.22 vs scale orphans, 0.52 vs
`return_at_low`, 0.65 vs round-trip, 0.46 vs thermal slope, and 0.58 vs its own Laplace predecessor.

**And it adds.** Unweighted z-score combinations on the same 29 images:

| combination | signed AUC |
|---|---|
| `blur_ratio` alone (best existing free feature) | 0.882 |
| `nonlocal_asymmetry` alone | 0.858 |
| asymmetry + blur | **0.902** |
| asymmetry + blur + `return_at_low` | **0.926** |

This is the first time in this line that new work has **improved on the existing axes instead of
restating them**. Treat 0.926 as a direction of travel, not a number: it is an unweighted sum on 29
images with no held-out set, and it *will* move.

Cost: **~0.8 s/image**, model-free, $0 — roughly 35× cheaper than the reconstruction observer.

---

## Part VI — What "the primary direction" turns out to mean

Jonathan asked whether there is a primary direction through the structure, with the observer looking
back seeing the whole and the other seeing the marks. The measurement says: **yes, and the direction
is scale.** Reading down the staircase (coarse → fine) is the forward pass; reading back up is the
return. `FOLDING_STAIRCASE` already established the ladder and that it hits a floor; `SHOVELCAT_CHECKER_V6`
§4 already frames the detector as wavelet-style multiresolution, each level keeping the agreed coarse
invariant and passing the disagreement down.

The new content is what to do with the two ends. Not *combine* them — **subtract** them. The corpus's
own honest ceilings say each observer is blind to what the other resolves, so their difference isolates
the thing neither can see alone: whether information entered this image from outside its own generating
process.

Note the sign relationship to `FOLDING_RECONSTRUCTION` Part 0, because it is a third distinct case.
Applying the *draw operator* gives fake = stable. Applying *noise + re-relax* gives real = stable.
Applying the *two-observer difference* gives **real = asymmetric**. Three operators, three signs. The
lesson stands and hardens: **the operator you apply decides the sign — never inherit one.**

---

## Honest ledger

**TESTED (inherited)**
- Global committee recovers coarse invariants 100%, "the tiny things never" (`FOLDING_OBSERVERS`).
- Local C registrar confirms its own boundary 95–100%, cannot see the global route
  (`FOLDING_UNIVERSAL_READER`, `FOLDING_WINDOW_SEAM`).
- The two-cone bidirectional transducer as the literal reader architecture (`FOLDING_UNIVERSAL_READER`).
- Detail resolves with zoom, continuity holds, and it hits a floor (`FOLDING_STAIRCASE`).

**MEASURED THIS SESSION (n = 12 real / 17 AI, compression parity, one generator family)**
- **Jonathan's asymmetry claim holds.** Real photos are markedly less predictable at the mark scale
  relative to the structure scale: 0.525 vs 0.331, AUC **0.858**.
- **It clears the independence bar** (max |r| 0.67) while **both of its own endpoints fail it**
  (0.91, 0.80) — the ratio is the mechanism, not an artifact.
- **It adds to the existing axes**: 0.882 → 0.902 → 0.926 as it and `return_at_low` are stacked on
  `blur_ratio`.
- Cheap: ~0.8 s/image, no model, no API.

**REFUTED THIS SESSION**
- **The harmonic-fill implementation of the same idea** (|r| = 0.89 with `lap_var`, adds nothing over
  blur). Kept in the record because the failure diagnoses the requirement: a predictor that cannot
  represent *sharp-but-regular* content cannot separate unpredictable from sharp. Any future
  predictability measure must be checked against that trap.
- My prediction that a ratio automatically cancels the blur confound as common mode. It does not — it
  did for the non-local predictor and did not for the harmonic one. Whether a ratio cancels is a
  property of the predictor, and has to be measured, not argued.

**UNPROVEN / NEXT**
- n = 29, one generator family (15 Midjourney, 2 Grok), real class born as JPEG and double-compressed
  by the parity harness. Every number here moves on a broad multi-generator set.
- The 0.926 stack is unweighted and unheld-out. No fitted combination should be quoted until there is
  a calibration/test split.
- **The obvious next probe**: `nonlocal_asymmetry` should be *scale-resolved*, not two-point. The
  curve of non-local error across b ∈ {2,4,8,16,32,64} is the devil's-staircase read of the same
  quantity, and its *shape* may separate generators — which would connect to the still-unproven
  scale-orphan measure in `FOLDING_RECONSTRUCTION` (|r| = 0.22 with this, so genuinely independent;
  the two together are the schedule probe).
- A real inpainting model in place of the patch search would be a strictly stronger local observer,
  at the usual cost in independence and money.

*Sources: `FOLDING_OBSERVERS` (agreement = invariant; the honest ceiling), `FOLDING_UNIVERSAL_READER`
(the two cones; the C registrar; readers see their neighbours), `FOLDING_WINDOW_SEAM` (the global route
is not locally readable), `FOLDING_STAIRCASE` (multiresolution ladder and its floor),
`SHOVELCAT_CHECKER_V6` §3–§4 (φ/ψ forward-backward; wavelet multiresolution),
`FOLDING_VOID_LINE_DRAW` Part III (the fill engine used as the attempt-1 predictor),
`FOLDING_RECONSTRUCTION` (the polarity rule and the independence bar this reuses),
`FOLDING_MIXEDNESS_CONFIDENCE` (the axis both attempts were audited against). External analog:
non-local self-similarity / exemplar inpainting.*
