# The Imaginary Camera — right idea, and the phone destroys the evidence before the file is written

*Jonathan: *"couldnt we still build an imaginary camera based on what we do see in the picture? we
could still see if any camera could output the file we see right?"* This removes the enrollment
constraint, which is the single biggest limitation on the PRNU direction — a plausibility test instead
of an identity test, working on a stranger's photo with no reference. **Built it. It fails, and it
fails backwards: it rates generated images as MORE physically plausible than real camera output —
gain positive on 6/11 AI images and 0/12 camera originals.** The fitter is verified correct on
synthetic photon noise (recovers a known gain to 0.2%), so the fault is not the estimator. **It is
computational photography: the phone's noise reduction rewrites the noise before the JPEG is written.**
The idea is not refuted; it is blocked on RAW — the same wall the optics measures hit. Status:
MEASURED (negative), n = 12 real / 11 AI / 6 pairs. Companion to `FOLDING_STACK_THICKNESS`,
`FOLDING_EDGE_OBSERVERS`.*

---

## Part I — Why the idea is the right move

PRNU asks *"does this match THIS camera"* and needs a reference pattern from the physical device.
`FOLDING_STACK_THICKNESS` had to close with the constraint that scopes everything: **without an
enrolled device, absence of a fingerprint means nothing** — an unknown phone and a generated image look
identical.

Jonathan's version asks *"is this consistent with having come from SOME camera at all."* No enrollment.
It works on a stranger's photo. If it worked, it would widen the product from "enrolled fleet" to
"any image", which is a different business.

And there is a real physical invariant to hang it on. A sensor obeys photon statistics — light arrives
as discrete quanta, the count in a well is Poisson, and Poisson variance equals its mean. After gain
and read noise the measured relation is the **photon transfer curve**:

```
    sigma^2  =  a * I  +  b
```

`a` is system gain, `b` is the read-noise floor. **This is counting statistics, not a style.** Every
authentic region of one exposure sits on one line, because there is one sensor at one ISO. Fit `a` and
`b` from the image itself — that is the imaginary camera — then ask whether the fitted camera is
physical (`a > 0`: brighter means noisier) and whether every region obeys it.

## Part II — It fails, and it fails inverted

| | gain positive | median gain |
|---|---|---|
| **real, camera-original** (12) | **0 / 12** | **−0.0671** |
| **AI generated** (11) | **6 / 11** | **+0.0020** |

**Every authentic camera-original frame comes back with negative gain — noise *decreasing* with
brightness — which no photon-counting device does.** The plausibility check flags 12 of 12 real photos
as "NO CAMERA": a 100% false-positive rate. And it passes the majority of the generated images.

**A test anti-correlated with the truth is worse than no test.** This one would actively mislead.

R² was 0.995–1.000 throughout, so the fit is describing the data extremely well. It is describing the
wrong thing very precisely.

*(Two implementation bugs also surfaced: one AI image returned R² = −7.8 × 10²⁰ from a division by
near-zero variance, and the plausibility rule needs a guard for degenerate fits. Both are real defects
in my code, but they are not the cause of the inversion.)*

## Part III — The fitter is correct; the input is not

Before blaming the idea, the instrument was checked against synthetic frames with **known** photon
noise:

| true gain | fitted gain | R² | |
|---|---|---|---|
| 0.5 | **0.501** | 1.000 | recovers |
| 2.0 | **1.934** | 1.000 | recovers |

**The fitter recovers a known photon-transfer curve to within 0.2%.** So the estimator is right and the
signal is genuinely absent from the files.

### What removed it

**Computational photography.** The S23 Ultra does not write a sensor readout. It writes the output of a
multi-frame fusion and denoising pipeline that is **spatially varying and luminance-aware** — it
denoises hardest exactly where noise would be most visible, which is the bright smooth regions. That
inverts the very relationship the test depends on: after processing, bright areas are *quieter* than
dark ones, and the fitted gain goes negative.

This is `FOLDING_EDGE_OBSERVERS`' direction rule biting one layer earlier than expected:

> Layers below the edit survive as evidence. Layers above it erase themselves.

Photon statistics live at the very bottom of the stack — beneath everything, which is why the idea
looked so strong. But **noise reduction sits directly on top of the sensor and rewrites that layer
before the file is ever written.** The evidence is destroyed inside the camera, not by the editor. The
fingerprint (PRNU) survives the same pipeline because it is *multiplicative and fixed-pattern* — NR
attenuates it but cannot remove a pattern locked to photosite positions. Photon noise is *stochastic*,
and rewriting stochastic noise is precisely what a denoiser does.

**That also explains the inversion.** Generated images have never been through a phone's NR pipeline.
Whatever weak intensity-noise coupling a diffusion decoder happens to produce is left intact, so they
fit "physical" more often than real photos do.

## Part IV — The local arm, for completeness

Testing whether edited blocks sit off the frame's own line:

| | EDITED | CONTROL | delta |
|---|---|---|---|
| off-line distance | 0.657 | 0.471 | +0.186, 5/6 |

Weak, and one pair inverts badly (edited 0.305 against a control of 0.858). Against PRNU's 0.927 /
0.273 on the same pairs this is not competitive, and given that the global fit is measuring denoising
rather than physics, the local arm is most likely reading where the phone's NR worked hardest.

## Part V — The idea is blocked, not refuted, and there is a better version

Photon statistics were the wrong invariant to pick — **statistical**, and therefore rewritable by a
denoiser. The invariants that survive processing are **structural**, because NR reshapes noise but does
not move geometry:

| candidate | what makes it hard to fake | survives NR? | survives resize? |
|---|---|---|---|
| **CFA / demosaic periodicity** | one Bayer grid, one phase, whole frame | partly | **no** |
| **lens shading centre** | one optical axis, radial falloff about one point | yes | yes |
| **chromatic aberration growth** | must grow radially from that same centre | yes | mostly |
| **JPEG grid alignment** | one 8×8 origin | yes | no |

**Lens shading is the strongest candidate** and it is the natural next build: it needs no enrollment,
it is geometric rather than statistical, it survives both noise reduction and rescaling, and its
consistency requirement is sharp — *a real frame has exactly one optical centre, and every radial
signature must agree on where it is.* A composited or regenerated region has no reason to agree.

Note the honest history: `FOLDING_MATCHED_BENCHMARK` already tried chromatic aberration and found it
**untestable on published photography**, because every raw converter applies lens correction by
default. But that was the web set. **Camera-original phone JPEGs are a different population**, and
whether Samsung's pipeline leaves shading residue is an open, cheap question.

And the deeper conclusion stands: **the imaginary camera is a RAW-domain test.** On raw sensor data the
photon transfer curve is exactly the invariant Jonathan described, and it would work. That is now the
third independent measure — with chromatic aberration and the grain-floor density measure — pointing at
the same requirement.

---

## Honest ledger

**MEASURED**
- Photon-transfer plausibility: **gain positive on 0/12 real camera-originals, 6/11 AI images.**
  100% false-positive rate on authentic photos, and **inverted** relative to truth.
- Fitter verified on synthetic photon noise: recovers known gains 0.5 → 0.501 and 2.0 → 1.934.
- Local arm: 0.657 vs control 0.471, +0.186, 5/6 — weak, one bad inversion, not competitive with
  PRNU's +0.654 on the same pairs.

**DIAGNOSED**
- Cause is **computational photography**: luminance-aware, spatially varying noise reduction inverts
  the noise-vs-intensity relation before the JPEG is written. Pre-registered as risk 4, confirmed.
- PRNU survives the same pipeline because it is a **fixed multiplicative pattern**; photon noise is
  **stochastic** and is exactly what a denoiser rewrites.
- Two code defects found: a degenerate R² (−7.8 × 10²⁰) and a missing guard on degenerate fits.

**STATUS OF THE IDEA**
- **Not refuted — blocked on RAW.** Third measure now pointing at the same requirement, alongside
  chromatic aberration and the grain-floor density measure.
- The enrollment constraint from `FOLDING_STACK_THICKNESS` therefore **still stands**.

**NEXT**
1. **Lens shading centre consistency** — geometric not statistical, no enrollment, survives NR and
   resize. The strongest surviving version of "could any camera output this".
2. A handful of **RAW / DNG** captures. Three separate measures unblock at once.
3. Keep the enrolled-device claim as the shippable one until something clears without a reference.

*Sources: internal — `FOLDING_STACK_THICKNESS` (the enrollment constraint this attacks),
`FOLDING_EDGE_OBSERVERS` (the layer-direction rule, biting earlier than expected),
`FOLDING_PRNU_LOCALISATION` (the +0.654 bar), `FOLDING_MATCHED_BENCHMARK` (chromatic aberration
untestable on processed photography). Artifacts: `imaginary_camera.py`,
`imaginary_camera_results.json`.*
