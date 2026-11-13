# The Two-Channel Loop — provenance routes detection, detection audits provenance

*Jonathan, four questions in one: other models fail on **reconstruction**; they also throw **false
positives**; the reconstruction failure has a place in our framework already (*"that 2 papers glued
together idea"* — the sedenion seam); and provenance and detection should **hand back and forth**.
All four hold. The first is the strongest: the field's models fail **0.89 → 0.02** exactly where a
manifold-membership test should be at its best, which is an **anti-correlated pair** and therefore the
one honest argument for a router. The fourth corrects a rule I wrote too broadly: Channel A must never
be **evidence**, but it is the right thing to **route on**. Status: ARCHITECTURE, with one decisive
test now running. Companion to `FOLDING_COMPETITIVE_POSITION`, `FOLDING_RATCHET_AND_ROUTING`.*

---

## Part I — Yes: they fail on reconstruction, and that is our opening

The number, from TGIF2 (271,788 images), pixel F1 on pretrained models:

| | patch composited back into the original file | **whole frame regenerated** |
|---|---|---|
| CAT-Net | 0.89 | **0.02** |
| TruFor | 0.75 | **0.14** |
| MMFusion | 0.64 | **0.13** |

The mechanism is not mysterious and it is the same object this project has been circling. Classical
forensics reads a **local discontinuity**: a JPEG grid that does not align, a noise floor that steps,
a compression history that changes across a boundary. That is a seam in the literal sense — and it is
the same thing `SHOVELCAT_CHECKER_V6` §1 named as the **sedenion seam**, *"a pair of octonions glued
by Cayley–Dickson doubling ... the zero-divisors appear only at the seam where the two halves
connect."* Two coherent halves; the junction is where consistency fails. `FOLDING_THE_KNIFE` Result 4
is the physical version: the two faces of a cut are complementary imprints, a mold and its cast.

**Jonathan's "two papers glued together" is exactly right as a description of what those models
detect** — and it explains their failure precisely. *Push the whole sheet through the press and there
is only one paper.* No junction, no zero-divisor, nothing to find. The tool is not weak; its object
has been removed.

### The anti-correlation, which is the actual opportunity

But a fully regenerated image is not less detectable in principle — it is **more on-manifold**. And
`FOLDING_RECONSTRUCTION` built the measure for exactly that: `roundtrip_fixed_point` applies our own
draw operator and asks whether the image moves. Generated content barely moves, because it already is
what a piecewise-smooth fill engine would have drawn.

| regime | local seam | seam-based models | manifold test |
|---|---|---|---|
| composited edit | present | **0.89** | weak — only a patch is on-manifold |
| fully regenerated | absent | **0.02** | **should be strongest** |

**They fail in opposite regimes.** That is the ideal condition for a router — not two tools that
mostly agree, but two whose blind spots are complements. It is also the only structural argument in
this project for why a framework-derived measure would beat the field's models *somewhere* rather
than having to beat them everywhere. `FOLDING_RECONSTRUCTION` Part 0 already worked out the sign
discipline this needs: the committee's convergence means **authentic**, the reconstruction axis's
convergence means **generated**, and *"an axis that averaged those two into one stability score would
cancel its own signal."*

### The caveat, and it is large

`roundtrip_fixed_point` scored **AUC 0.848 signed, |d| 0.348** — the strongest measure in that
benchmark. **That benchmark was 12 real phone JPEGs versus 17 AI PNGs: the set
`FOLDING_PHOTO_SET_AUTOPSY` destroyed.** Stored aspect ratio separated those classes at AUC 1.000 and
bits-per-pixel at 0.008. The number has never seen parity or a real-vs-real control.

Base rate: **28 of 28 free features have died at that gate.** The obvious failure mode here is that a
smooth studio portrait sits closer to a piecewise-smooth drawable manifold than a foliage landscape
does, for reasons with nothing to do with provenance — which is CTRL1, and which is exactly how
`slope` and `blur_ratio` died.

One reason it might not follow the base rate: the 28 that died were all **static statistics** —
sharpness, spectrum, density. This one applies an **operator** and measures displacement. Different
kind of quantity, so the prior may not transfer. That is a hypothesis, not a defence.

**`recon_control.py` is running now** — 73 images, full parity, target plus two real-vs-real controls,
predictions pre-registered in the module docstring. Roughly 70 minutes at 2 cores. It is the cheapest
decisive test available and it should be believed either way.

## Part II — Yes: and their false positives are the market gap, not just a flaw

NewsGuard, May 2026, five leading detectors on 15 authentic images: **13.3% collective false-positive
rate**; one tool called 6 of 15 real photos fake. AIGIBench: the best detector scores 96.8% on real
images and **63.0% on fakes** — and under JPEG at QF50, fake-detection accuracy collapses to near 0%
while real accuracy holds at ~95%, meaning compressed detectors converge on calling everything real.
**No vendor publishes a false-positive rate.** Deepfake-Eval-2024, the one rigorous independent
benchmark, could only publish anonymised per-vendor results.

Against that, `FOLDING_RATCHET_AND_ROUTING` measured our gate at **0 false positives out of 33 real
photographs, at every threshold from 10 to 50**. Recall is only 20%, and that is the honest weakness —
but the field's problem is not recall, it is that **a heatmap has no null output.** It always returns
a confident blob. A component that can stay silent is the rarer thing.

## Part III — Yes to the loop, with one correction to a rule I wrote too broadly

I wrote in `FOLDING_SEAM_REBUILD_AND_DENSITY` Part IV: *"there are two kinds of evidence and they must
never be mixed."* That is right about **evidence** and wrong as a blanket rule, and Jonathan's question
finds the gap.

> **Channel A must never be an INPUT TO THE SCORE. It is the right thing to ROUTE ON.**

Why routing is legitimate where blending is not: **the composited-vs-regenerated split is the decisive
variable** — 0.89 against 0.02 — and it is substantially **readable from the file itself**. An intact,
aligned 8×8 JPEG grid with a single quantisation history says a patch was composited into an existing
file: run the seam models, they are in their 0.89 regime. A uniform re-encode with no grid
discontinuity says the whole frame went through a generator: **do not run them at all**, they are in
their 0.02 regime and will return a confident blob anyway. `format_probe.py` already reads most of
what that decision needs.

This is not blending. The router chooses **which tools have jurisdiction**; it never contributes a
number to their output.

**The safeguard, and it is not optional:** if the router's decision leaks into the score, we are back
to bits-per-pixel as evidence and the 0.952 all over again. So —

> **Every route gets its own real-vs-real control arm and its own calibration.** A tool validated on
> the composited route has no validated performance on the regenerated route. Routing multiplies the
> number of control arms required; it does not reduce it.

### And the return leg is the stronger half

*"wouldn't the detection part help with the provenance?"* — Yes, and specifically at the two places
provenance is known to break:

- **Nikon, Aug–Sep 2025.** The Z6III shipped C2PA capture signing. Within nine days a photographer
  used multiple-exposure mode to get an AI image cryptographically signed as camera-captured. Nikon
  suspended the service and revoked every certificate — and because `c2patool` does not check
  revocation by default, most validators still accept the forgeries. **Signature validity ≠ content
  truth**, and only a content check catches it.
- **The "Integrity Clash"** (CVPR'26 workshop): the C2PA spec does not mandate disclosing generative
  origin, so an attacker omits the AI assertion. **100% success over 500 SDXL images** — valid
  manifests claiming human authorship on images still carrying an AI watermark. No cryptography
  broken. Again, only a content check catches it.

So the loop is symmetric and each leg covers the other's specific documented failure:

```
   CHANNEL A  provenance                      CHANNEL B  content
   format, JPEG tables, EXIF,     ──route──▶  seam models  |  manifold test
   C2PA manifest, watermark                   material context | committee
        ▲                                              │
        └──────────── amend the claim ◀────────────────┘
              "region R has a different origin"
              "signature valid but content is on-manifold"  ← the Nikon case
                            │
                      ratchet gate
              fires categorically, or stays silent
```

**And this is the framework's own invariant, one level up.** `STATE_OF_THE_DETECTOR` §1: *agreement
across independent observers is the invariant; disagreement is the depth.* Provenance and pixels are
about as independent as two observers get — one is cryptographic and social, the other physical. When
they agree, that is the invariant. **When they disagree — a valid signature on on-manifold content —
that disagreement is the finding.** That is the sedenion seam applied to channels instead of to
regions: two coherent halves, and the junction between them is where the truth fails to close.

Worth noting: **SAFIRE** (AAAI'25) is already partway here — it does *multi-source partitioning*,
"which region came from which source," rather than binary tampered/clean. Nobody has closed the loop
back to the provenance claim, and nobody has put a silent gate on the end of it.

---

## Honest ledger

**ESTABLISHED**
- Seam-based localisation collapses on reconstruction: CAT-Net 0.89 → 0.02, TruFor 0.75 → 0.14.
- Field false-positive problem is real and unmeasured by vendors: NewsGuard 13.3%; no published FPRs.
- C2PA fails at capture (Nikon forgery + unchecked revocation) and in distribution (manifest
  stripping); the Integrity Clash is 100% effective without breaking any cryptography.

**SOUND ARCHITECTURE, NOT YET EVIDENCE**
- The anti-correlated pair (seam models vs manifold test) — the structural case for a router.
- Channel A as router rather than evidence, with per-route control arms as the price.
- The provenance ↔ detection loop, with channel disagreement as a first-class finding.

**THE ONE THING THAT WOULD MAKE THIS REAL, AND IT IS RUNNING**
- `roundtrip_fixed_point` through parity + two real-vs-real controls. Its 0.848 came from the set the
  autopsy destroyed. Pre-registered: most likely another genre detector; the argument that it might
  not be is that it applies an operator rather than reading a static statistic.

**AND THE ONE MEASUREMENT THAT DECIDES THE ROUTER**
- Run TruFor / Mesorch / IML-ViT on our 13 Samsung pairs as-is. Do mobile-OEM generative edits behave
  like **composited** (0.89 regime) or **regenerated** (0.02)? Nobody has measured this for any mobile
  OEM — it is an open gap in the literature. If Samsung composites, the field's models solve our
  problem and we contribute the gate. If Samsung regenerates, the seam models are dead on the phone
  photos that matter most and the manifold route is the only thing left.

*Sources: TGIF2 (arxiv.org/abs/2603.28613), COCO-Inpaint (arxiv.org/abs/2504.18361), SAFIRE
(arxiv.org/abs/2412.08197), AIGIBench (arxiv.org/abs/2505.12335), Deepfake-Eval-2024
(arxiv.org/abs/2503.02857), NewsGuard special report, C2PA security analysis
(arxiv.org/abs/2604.24890), Integrity Clash (CVPR 2026 APAI workshop). Internal: `FOLDING_RECONSTRUCTION`
Part 0/III.a and Part V, `SHOVELCAT_CHECKER_V6` §1 (the sedenion seam), `FOLDING_THE_KNIFE` Result 4
(complementary imprints), `FOLDING_PHOTO_SET_AUTOPSY`, `FOLDING_RATCHET_AND_ROUTING`,
`FOLDING_COMPETITIVE_POSITION`. Artifact: `recon_control.py`.*
