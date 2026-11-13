# Blue, the void, nested ratios, and what RG_opp actually is

*2026-07-28. Four experiments run against one question from Jonathan: **if borders follow C lines,
and folding bends pixels so A/B/D can fall into the void, is blue the channel that gets pulled in?
And could those values be nested frequency ratios?** Three of the four came back negative. The
fourth is the most consequential negative in the project since the 0.952 retraction.*

---

## 0. The corpus answers the first half before any code runs

`FOLDING_VOID_LINE_DRAW` already settled the bent-pixel part, and it is worth quoting because it is
the rule that keeps this line of work from eating itself:

> *"'Bent/deformed pixels mark the seam' is **false** in the read direction (`FOLDING_PIXEL_STRAIN`).
> **Bending pixels is a thing you DO when drawing (a rendering choice), never a signal you READ when
> detecting.** Keep the two directions separate."*

So the folding picture is a **generative** account — how a border gets made — and it does not license
a **detection** claim about which channel is depleted. The two directions share a vocabulary and not
a mechanism. That said, the depletion question is separately testable on its own terms, so it was
tested rather than dismissed.

---

## 1. Per-channel information budget — **blue is not depleted**

12 camera-3 frames, camera-original, measured per channel.

| | noise sd | HF energy | entropy (bits) | dynamic range |
|---|---|---|---|---|
| **RED** | 0.9884 | 0.04647 | **6.602** | 128.0 |
| **GREEN** | 0.9884 | 0.04661 | 6.688 | 129.5 |
| **BLUE** | 1.1119 | 0.04678 | 6.626 | 134.0 |

Blue vs green: noise **1.12×**, HF energy **1.00×**, entropy **−0.062 bits**, dynamic range **1.03×**.

**Reading.** Blue is marginally noisier — which is expected and boring, silicon is less sensitive at
short wavelengths and the blue gain is higher. But its **high-frequency content is identical to green
to within 1%**, and the channel with the *least* entropy is **RED**, not blue. If a channel were being
pulled into the void — losing structure, losing information — that would show as depleted HF energy
and depleted entropy. Neither appears. **The hypothesis is not supported.**

## 2. Where blue *is* actually thrown away — and it is not the sensor

The JPEG tables on these files:

- `subsampling = None` — **no chroma subsampling at all.** The usual "blue gets discarded" intuition
  comes from 4:2:0, and this pipeline does not do it.
- chroma quantisation tables are **1.6–1.7× coarser** than luma.

So there *is* a real blue-loss channel in the file format, but it is a **codec** decision, sitting
in Channel A territory, not a sensor or optical fact. It is uniform across every frame this phone
writes, which makes it a constant and therefore useless as evidence. Worth knowing precisely so it
never gets mistaken for signal later.

## 3. Nested frequency ratios — **all three forms fail the gate**

Run through the standard three-control arm (target must beat every control by >0.02 and reach
|AUC − 0.5| ≥ 0.25):

| measure | TARGET | CTRL1 | CTRL2 | CTRL3 | verdict |
|---|---|---|---|---|---|
| `R/G` flat | **0.283** | 0.107 | 0.227 | 0.146 | **CLEARS** |
| `RG_opp` | **0.302** | 0.048 | 0.193 | 0.115 | **CLEARS** |
| `(R/G)/(G/B)` nested | 0.238 | 0.159 | 0.174 | **0.281** | confounded |
| `(R/G)/(B/G)` nested | 0.198 | 0.119 | **0.223** | 0.062 | confounded |
| log nested | 0.123 | 0.159 | 0.220 | **0.292** | confounded |

Every nested form is beaten by at least one control that is *known to be chance*. Nesting does not
add structure here; it adds a second noisy denominator. **The flat ratio outperforms its own nested
version in all three cases.**

Running tally: **42 features tested, 2 have ever cleared.** Both of them are flat colour ratios.

---

## 4. The per-lens shading test — what `RG_opp` is made of

Given that `R/G` and `RG_opp` are now the *only* two survivors out of 42, it matters enormously what
mechanism they encode. There were exactly two candidates:

- **OPTICS** — lens shading is wavelength-dependent, the falloff is a property of *that glass*, and
  different lenses must shade differently. If this is it, the feature is a **lens** fingerprint and
  the enrollment-free story is alive.
- **PROCESSING** — the ISP's colour pipeline leaves a global signature that has nothing to do with the
  lens. If this is it, the feature is a **model** fingerprint and will not transfer to another make.

This phone separates them cleanly, because it has three physically different sensor+lens assemblies
behind **one** image pipeline: ultrawide f=2.2mm, main f=6.3mm, periscope f=27.2mm. Same ISP, same
firmware, same colour science, same photographer, same week. **The only variable is the glass** — so
this is a within-device comparison with none of the content/compression/device confounds that killed
the other 40 features.

### Result

| R/G radial curvature | n | mean | sd |
|---|---|---|---|
| ultrawide | 10 | −0.0380 | 0.1257 |
| main | 15 | +0.0273 | 0.2039 |
| periscope | 11 | +0.0421 | 0.0667 |

between-lens sd **0.0426**, within-lens sd **0.1436** → ratio **0.30**. B/G curvature: ratio **0.42**.
Best single-frame lens discrimination across all three pairs and both ratios: **AUC 0.745**
(pre-registered bar was 0.80).

Re-run after discarding frames whose own radial fit was numerically unstable (negative R², 2 frames
of 36): ratios 0.32 and 0.46, best AUC 0.756. **Same verdict.**

### Verdict — PROCESSING, not optics

The between-lens spread is **one third** of the within-lens scatter. Three genuinely different
lenses — an ultrawide and a 10× periscope are about as different as optics gets inside one body —
are **not separable by their colour shading**.

**This means `RG_opp` is an ISP signature.** It is a fingerprint of *this phone model's colour
pipeline*, not of a lens, and there is no reason to expect it to generalise to an unenrolled phone of
a different make. That is a materially weaker claim than the one the shading observer was written to
make, and it was better to find out on a within-device test costing minutes than on a customer's
photos.

The likely reason: every phone applies lens-shading correction *aggressively*, and it applies it
per-lens with a calibrated profile. Correction is exactly the operation that removes the between-lens
difference. What survives into the JPEG is the residual of the *correction*, which is a pipeline
property — so the pipeline is what we measure. Consistent with `FOLDING_IMAGINARY_CAMERA`, where
computational photography rewrote noise before the file was written, and the photon-transfer fit came
back **inverted**. Same wall, second measure.

---

## 5. What this leaves

**Standing:**

- PRNU per-sensor identification — 36/36 matched, **0/72 mismatched**, ~1200× separation.
- PRNU localisation of local edits — 0.916 vs control 0.342, n=7, **p = 0.0156**.
- Regeneration detection — n=9, all ratios ≤ 0.0033, 10× gap to the nearest retained case.
- 0 false positives in 120 robustness tests.

**Downgraded:** `R/G` and `RG_opp` still clear their controls and are still the only free features
that do — but they are now understood as **device-model** evidence, not optical evidence. That makes
them a useful *corroborator inside an enrolled-device product* and **not** a route to enrollment-free
detection.

**Closed:** the blue-depletion hypothesis, nested frequency ratios, and lens shading as an
enrollment-free invariant. Three doors, all shut on the same afternoon, all shut cheaply.

**Still open as the enrollment-free route:** nothing structural has replaced it. The honest position
is that every enrollment-free invariant tried so far — photon statistics, chromatic aberration,
grain floor, lens shading — has been erased by computational photography before the file is written.
That is not a gap in the method; it is a property of modern phones, and it deserves to be stated
plainly in the DSRI write-up rather than discovered by a reviewer.

**Code:** `per_lens_shading.py`, `per_lens_shading.json`.
