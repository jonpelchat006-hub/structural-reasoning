# The Reconstruction Axis — re-anneal, the rest position, and the polarity inversion

*Captures a working session (Jonathan + Claude) designing Axis 5 of the Shovelcat AI checker: the
reconstruction / re-anneal observer. Jonathan's questions were the right ones — "we should readjust
the void lines or give them a starting position right? but we could start with both a grid and some
outlines, or have them work forward/backwards and see where they converge" — and each one turns out
to name a distinct sub-measure. The session also found a **sign error latent in the corpus** that
would have made this axis subtract from the committee instead of adding to it. Companion to
`FOLDING_OUTER_SLOT` (esp. Part V), `FOLDING_VOID_LINE_DRAW` (esp. Part IV), `SHOVELCAT_CHECKER_V6`,
`FOLDING_MIXEDNESS_CONFIDENCE`. Status: designed, built, and **benchmarked on real data** (12 camera
photos vs 17 Midjourney/Grok, at compression parity). Two predictions confirmed, one refuted, and the
axis **fails its own pre-registered independence bar** on its strongest measures — Parts V and VI carry
the numbers. Read Part II's prediction as superseded by the ledger.*

---

## Part 0 — The polarity inversion (read this before wiring the axis in)

`FOLDING_OUTER_SLOT` Part V says, correctly:

> authentic content is *off*-manifold and does **not** settle back (high reconstruction error, seams
> re-crystallize differently each shake → the region is unstable → **flagged**); generated content is
> already *on*-manifold and sorts right back (low error, **converges**)

Read that against the committee axis, where **convergence = authentic** (`FOLDING_OBSERVERS`;
`SPARSE_VESICA` §18.19: accept only when distinct-route-count = 1). The two statements put the
*authentic* class on opposite sides of the same word. As written, Part V even sends the authentic
region to "flagged."

**It is not a contradiction — it is two θ=1 tests against two different manifolds**, and the
distinction has to be written down or the combiner will get the sign wrong:

| axis | what converges | the reference manifold | convergence means |
|---|---|---|---|
| 1 — vision committee | independent **observers reading** the image | *semantic coherence* | **authentic** |
| 5 — reconstruction | the **image itself under re-annealing** | *a generator's output set* | **generated** |

An authentic photo is a stable floor atom **to the committee** (every reader agrees what it is) and
simultaneously an unstable, off-manifold object **to a generator** (nothing pulls it back to itself).
Both are true. They are different questions.

**Measured refinement (Part V).** This table turned out to be one row short. *Which operator you
apply* also decides the sign: applying the **draw operator** gives fake = stable (confirmed, AUC
0.848 signed), while applying **noise + re-relax** gives real = stable (confirmed, AUC 0.819). An axis
that averaged those two into one "stability score" would cancel its own signal.

**Design consequence.** Axis 5 emits **raw, unsigned sub-measures**. The combiner maps them to
`p_fake` with weights fit on a calibration set. No sub-measure gets a hand-assigned sign inherited
from the committee. The prototype's AUC reporter deliberately prints **unsigned** AUC (0.10 is as
strong as 0.90, it just points the other way) so the sign is read off data, never off intuition.

---

## Part I — Yes, give the lines a starting position: relax first, *then* vibrate

Jonathan: *"we should readjust the void lines or give them a starting position right?"* — Yes, and
this is load-bearing, not housekeeping.

Vibration is only meaningful as **displacement from equilibrium**. Shaking a randomly-initialised
line set measures the initialisation, not the image. So the procedure has a Stage 0:

1. **Seed** → **relax** until the mixing stops (`FOLDING_VOID_LINE_DRAW` Part IV) → **dissolve the
   quiet borders** down to the reserve. Call the result `L*`, the **rest position**.
2. Only now perturb, and always measure **back to `L*`**.

This turns the vibration from "does the answer look similar" into a **restoring-force / stiffness**
measurement, which is a physical quantity we can actually put a number on: perturb the lines off
equilibrium and read how much of the boundary walks back. A void line sitting in a deep, stiff well
is anchored by real structure; a line sitting in a shallow well was placed by a smooth prior, where
every nearby position is nearly as good.

This connects to a **tested** result and inherits its caution. `FOLDING_PIXEL_STRAIN` measured that
the cut runs through the **rigid, buried, well-packed** waist (|r| ≤ 0.05; the seam is *less* mobile
in 5/7). Rigidity is real and is a property of the seam. But that same doc is the corpus's clearest
**REFUTED** entry: *bending pixels is something you do when drawing, never something you read when
detecting.* So stiffness here is measured as the **curvature of the mixing-energy landscape around
the settled line**, never as pixel deformation. Different quantity, and the refuted one stays refuted.

---

## Part II — "both a grid and some outlines" is the independence knob

Jonathan: *"we could start with both a grid and some outlines."* This is the best idea in the
session, because **the seed is where the independence comes from** — and it makes this axis free.

`FOLDING_OUTER_SLOT` Part V's insight was that N noise perturbations of one process can stand in for
N separate models. The seed generalises that: you don't even need the noise.

- **Seed G — the blind grid.** A uniform lattice of thin void lines that knows nothing about the
  image. Content-agnostic prior.
- **Seed O — the outlines.** Centres placed in the flat basins that the image's own gradient
  watershed carves out — i.e. seeded *from* the outlines. Content-committed prior.

Same energy, same iteration count, same dissolve rule, same region count. **The only difference is
where the lines start.** Then compare the two settled line sets. That is *literally* the §18.19
acceptance rule — distinct-route count → 1 — run with initialisations as the routes instead of models.

> ⚠️ **The prediction below was measured and came back inverted and weak** (real 0.835 vs AI 0.769,
> |d| = 0.186). It is left standing as written because the reasoning is worth keeping and the failure
> is informative — see the REFUTED entry in the ledger. The *design* (two seeds as two routes) is
> sound and reusable; the *directional claim* is not.

**The prediction:** a generated image has **over-determined** boundary structure. Its regions are
clean, its edges unambiguous, its texture near-absent, so the blind grid slides straight onto the
same lines the edge-committed seed already found. A real photograph is full of competing basins —
texture creates many places where lines *could* legitimately settle — so the two seeds land
differently. **High seed-agreement = the image told both routes the same story too easily.**

Why this matters commercially: it is **model-free and $0**, like the spectral and mixedness routes,
and it is orthogonal to both — spectral reads *frequency content*, mixedness reads *blur magnitude*,
this reads **where boundaries choose to sit**. That is a third independent free axis.

---

## Part III — "forward/backwards and see where they converge" is two measurements, not one

Jonathan's phrase has two valid readings and **both are worth building**. They answer different
questions.

### III.a — Read ↔ draw: is the image a fixed point of our own engine?

`FOLDING_VOID_LINE_DRAW` Part V already establishes read and draw as one membrane run both ways.
So run the loop:

```
image → relax → L*  →  redraw (void lines + fill)  →  relax again → L**
```

`roundtrip_fixed_point = agreement(L*, L**)`. If the image is already close to what our diffusion-
curves fill engine would have drawn, the round trip barely moves — it is a **fixed point of the draw
operator**. This is the DIRE residual with our own cheap engine standing in for the diffusion model:
we are not asking "is it on Stable Diffusion's manifold," we are asking "is it on the manifold of
piecewise-smooth, void-line-drawable images" — which is a manifold diffusion output sits much closer
to than a photograph does, because that is what a denoiser converges toward.

### III.b — Coarse ↔ fine: the ladder, and the actually diffusion-specific tell

This is the one that answers *"is it a diffusion model"* rather than *"is it fake."*

`FOLDING_OUTER_SLOT` Part V already made the key identification: **noise level = the thickness-by-
level knob**; high noise fixes coarse global structure (thick void lines), low noise fixes fine detail
(thin lines); *"the diffusion schedule is the devil's-staircase zoom run generatively."* Take that
seriously and it hands you a test of the **schedule itself**:

- **Forward, coarse → fine.** Relax at increasing line counts (24 → 96 → 384 → 1536). Record at which
  level each boundary is **born**.
- **Backward, fine → coarse.** One fine relaxation, then dissolve quiet borders upward to matching
  counts. Record at which level each boundary **dies**.

Two things fall out:

1. `ladder_fb_agreement` — do the descending and ascending hierarchies agree about which boundaries
   exist at which level? Jonathan's "see where they converge," made a number.
2. `nonmonotone_fraction` — **the scale orphans.** A real object edge, once born, is an edge at every
   finer level; it only gets thinner. Its presence vector across the ladder is monotone. A boundary
   that appears mid-ladder and is absent both coarser *and* finer is a **scale orphan** — structure
   that exists at one band of the schedule and has no ancestor and no descendant.

A coarse-to-fine annealer commits global layout at high noise and detail at low noise, and the two
are stitched. **The stitch is a seam in scale rather than in space**, and the ordinary committee
cannot see it — the committee reads one scale at a time. This is where Axis 5 earns its place instead
of duplicating Axis 1, and it is the piece that goes past DIRE: DIRE tests *manifold membership*,
this tests *the schedule that built it*.

---

## Part IV — The stopping rule does real work (the reserve as an auto-threshold)

`FOLDING_VOID_LINE_DRAW` Part IV's honest bound — the seam is a **leaky wall (~0.83 transmissive),
woven at fine scale**, so mixing never reaches zero; stop at the **void reserve ≈ 1/5**
(`FOLDING_SATURATION_BUDGET`) — turns out to solve a practical problem, not just a philosophical one.

Every region-merging segmenter needs a dissolve threshold, and hand-tuning it per image is exactly
the kind of knob that manufactures a benchmark result. Instead: **bisect the dissolve threshold for
the largest dissolve that keeps residual mixing ≤ 0.2 × E₀**, where E₀ is the energy of the trivial
one-region partition. The threshold becomes adaptive per image and is set by a framework constant we
already committed to, not by a fit. The saturation budget is doing load-bearing engineering work.

**Validity check, not a signal.** `FOLDING_FLOORS` §1 measured that successive cuts cross
near-orthogonally (mean 64.3°, 0/8 parallel). The prototype computes the orientation concentration of
the settled boundary set and, above 0.60, **marks the run invalid rather than scoring it** — that
pattern means the relaxation stayed grid-locked and never left its seed. This is a guard against the
axis's most likely silent failure, and it is *not* used as a fake/real signal.

---

## Part V — What is built, and what it measured

`reconstruction_observer.py` — standalone, no API, no GPU, ~28–40 s/image at 512 px on CPU. Sibling of
`spectral_observer.py` / `mixedness_observer.py`. `parity_bench.py` is the compression-parity harness.

**Two instrument defects were found and fixed mid-session**, both by looking at the spread rather than
the mean on 17 real Midjourney/Grok images:

- `restoring_fraction` came back **0.973 ± 0.009** — the 2 px nudge was far smaller than the void-line
  spacing, so everything walked back and the probe had no dynamic range. Now scaled to **0.35 × the
  line spacing**.
- `return_spread` came back **0.002** — a single noise amplitude produced no *distribution*, so there
  was no half-life to read, which is the whole point of `SPARSE_VESICA` §18.19's isotope picture. The
  single shake was replaced by a **thermal ladder**: σ ∈ {0.02, 0.06, 0.14}, and the reported quantity
  is `thermal_slope`, the rate at which the void lines let go as the plate heats. That fix produced
  the second-strongest signal family in the benchmark; before it, the measure was flat.

**Benchmark (measured, this session).** 12 real camera photos (phone, JPEG-native) vs 17 AI photos
(15 Midjourney, 2 Grok, PNG-native). **Both classes resized to 512 px and re-encoded through the same
JPEG q85 path before scoring** — without that step the comparison is PNG-vs-JPEG and any result is
partly a compression detector. **0/29 runs hit the orientation validity guard**; the relaxation
behaves on real 4K generative output.

AUC is reported **unsigned** — 0.15 is as strong as 0.85, it just points the other way.

| sub-measure | real | AI | AUC | \|d\| | reads |
|---|---|---|---|---|---|
| `roundtrip_fixed_point` | 0.904 | 0.944 | **0.152** | **0.348** | AI is closer to a fixed point of the draw engine |
| `return_at_low` | 0.978 | 0.963 | **0.819** | **0.319** | real void lines hold under a light shake |
| `return_at_high` | 0.820 | 0.727 | 0.809 | 0.309 | same, hot shake |
| `return_rate` | 0.875 | 0.812 | 0.799 | 0.299 | ladder mean |
| `thermal_slope` | −1.145 | −1.719 | 0.794 | 0.294 | **AI lines let go ~50% faster as the plate heats** |
| `return_spread` | 0.073 | 0.107 | 0.225 | 0.275 | marginal |
| `nonmonotone_fraction` | 0.204 | 0.252 | 0.319 | 0.181 | more scale orphans in AI — right direction, under the bar |
| `seed_convergence` | 0.835 | 0.769 | 0.686 | 0.186 | **inverted vs. prediction**, and under the bar |
| `rest_energy_ratio` | 0.199 | 0.169 | 0.613 | 0.113 | — |
| `restoring_fraction` | 0.889 | 0.861 | 0.603 | 0.103 | — |
| `mean_displacement` | 3.458 | 3.656 | 0.436 | 0.064 | dead |
| `struct_residual` | 0.081 | 0.077 | 0.529 | 0.029 | dead |
| `ladder_fb_agreement` | 0.731 | 0.749 | 0.480 | 0.020 | dead |

At n = 12/17, treat |AUC − 0.5| < 0.25 as noise.

### The two stabilities are not the same stability

The two strongest measures point **opposite ways on the word "stable,"** and that is the session's
main theoretical result rather than a contradiction:

- **Manifold stability** (`roundtrip_fixed_point`): apply the *draw operator*. AI content barely moves
  — it is already what our fill engine would have drawn. **Fake = stable.** This is Part 0's rule,
  confirmed.
- **Anchor stability** (`return_*`, `thermal_slope`): apply *noise, then re-relax*. Real content holds
  its void lines; AI's soft interpolated boundaries get swamped. **Real = stable.** This is the
  `FOLDING_PIXEL_STRAIN` rigid-waist result showing up in the image domain.

So Part 0's table needs a third row: *which operator you apply* decides the sign, not just which
manifold you name. Applying a generative map and applying a thermal perturbation are different
questions, and an axis that mixed them into one "stability score" would cancel its own signal.

---

## Part VI — The independence audit, and the honest verdict

`FOLDING_OUTER_SLOT` Part III is explicit that routes must **stay** independent or you manufacture
agreement. Part VI of the original draft therefore set a bar **before any data was seen**: a
sub-measure correlating at **|r| > 0.7** with the mixedness axis is not a fourth route, it is the blur
axis wearing a hat. That bar was then applied to the same 29 parity images.

| sub-measure | max \|r\| vs any mixedness feature | verdict |
|---|---|---|
| `thermal_slope` | **0.81** (blur_ratio) | **redundant** |
| `roundtrip_fixed_point` | **0.79** (blur_ratio) | **redundant** |
| `return_at_high` | **0.79** | **redundant** |
| `return_rate` | **0.77** | **redundant** |
| `seed_convergence` | 0.70 | borderline |
| `nonmonotone_fraction` | 0.69 | independent |
| `return_at_low` | **0.61** | **independent** |

**Both of the strongest sub-measures fail the independence bar.** The round-trip fixed point and the
thermal slope are substantially restatements of blur, and blur is the axis whose own headline
(`STATE_OF_THE_DETECTOR` §4) is already flagged as untrusted. On this same parity set, mixedness's
`blur_ratio` alone scores a signed **AUC 0.882** — better than anything this axis produced.

**What actually survives both bars: one sub-measure.**

> **`return_at_low`** — the coldest rung of the thermal ladder. Signed **AUC 0.819**, max |r| **0.61**.
> A light shake probes the *curvature of the well at equilibrium*; heavy heating degenerates into
> "how blurry is this image," which is why the hot rungs go redundant and the cold one does not.

**`nonmonotone_fraction` (the scale orphans) is the one to chase.** It is independent (0.69), it moves
in the predicted direction (0.252 AI vs 0.204 real), and it is the only measure here that tests the
*schedule* rather than the surface — but at |d| = 0.181 it is under the noise bar and is **not a
result**. It needs a larger, generator-labelled set before it can be claimed.

**Verdict: Axis 5 is not yet an established fourth route.** It contributes one modest independent
sub-measure and one promising unproven one. It should **not** ship as a headline axis on this
evidence, and the roadmap item "build the reconstruction layer" should be read as *built and measured,
outcome mostly negative* rather than *done*.

---

## Honest ledger

**TESTED (inherited — protein set, 8 structures unless noted)**
- Borders between similar pixels dissolve; efficiency grades with similarity — 8/8
  (`FOLDING_PIXEL_TRANSMISSION`). The relaxation's dissolve rule.
- The seam is a **leaky (~0.83), woven** wall (same doc, Result 2) — why the reserve exists.
- Successive cuts cross near-orthogonally — 64.3°, 0/8 parallel (`FOLDING_FLOORS` §1). Validity guard
  only; **0/29 images tripped it**, so the guard is calibrated sanely.
- The cut runs through the **rigid, well-packed** waist (`FOLDING_PIXEL_STRAIN`).
- Survival = convergence of independent routes (`SPARSE_VESICA` §18.19).

**MEASURED THIS SESSION (n = 12 real / 17 AI, compression parity, single generator family)**
- **The anchor-stability prediction holds.** Real photos' void lines survive heating markedly better;
  `thermal_slope` −1.145 vs −1.719. The rigid-waist result reproduces in the image domain.
- **The manifold-stability prediction holds.** AI images sit closer to a fixed point of the draw
  engine, 0.944 vs 0.904, tightly (AI σ = 0.022 across 17 images).
- **The two stabilities have opposite signs** and must be kept as separate measures.
- **The independence audit fails for both of them** (|r| = 0.79, 0.81 vs blur). Only `return_at_low`
  clears both bars (AUC 0.819, |r| 0.61).
- The two instrument fixes (nudge scaling, thermal ladder) — the ladder produced real dynamic range
  where a single amplitude gave none.

**REFUTED THIS SESSION**
- **The seed-convergence prediction (Part II).** I predicted generated images would be
  *over-determined* — that a blind grid would slide onto the same lines an edge-committed seed found.
  Measured: seed convergence is **higher in real photos** (0.835 vs 0.769), the opposite direction,
  and at |d| = 0.186 it is under the noise bar anyway. The mechanism story was clean and wrong. Real
  photos evidently constrain boundary placement *more*, not less — plausibly because a physical edge
  is unambiguous while a generated gradient offers many near-equal settling positions. **Do not build
  on the Part II prediction as written.**
- `struct_residual` (AUC 0.529) and `ladder_fb_agreement` (0.480) carry no signal at parity. The
  residual looked good on synthetic data and died on real data — a reminder of what synthetic
  validation is worth.

**UNPROVEN — the live hypothesis**
- **Scale orphans as a diffusion-schedule tell.** Independent (0.69), correct direction, under the
  bar. Needs images from generators with *different* schedules, not just different models.

**BLOCKED / NEXT**
- n is small and the AI class is one generator family. The whole table moves on a broad multi-generator
  set — this is the same caveat `STATE_OF_THE_DETECTOR` §4 already carries for the headline number.
- Genuine compression parity needs **PNG-native or RAW real photos**. Here the real class was born
  JPEG and is double-compressed by the harness while the AI PNGs are compressed once; a residual
  asymmetry survives.
- A combined axis score was deliberately **not** fitted: with 29 images and no held-out set, any fit
  is overfitting. Report sub-measures until there is a calibration set.

**REFUTED — inherited, do not build on this**
- Pixel deformation as a read-direction signal (`FOLDING_PIXEL_STRAIN`). Stiffness here is the energy
  landscape's curvature at the settled line, a different quantity.

---

## Operational note — where the code lives

The v6 code was found in `C:\Users\GamerTech\Desktop\Vesica AI\AI Detector` (not the
`Shovelcat-AI\AI Detector` folder, which holds only v4/v5). `reconstruction_observer.py`,
`parity_bench.py` and this doc are committed there alongside it. The benchmark image sets behind
`bench_photo_metrics.json` (n=50, AUC 0.952) are still not on disk — that number remains
unreproducible until the sets are restored.

*Sources: `FOLDING_OUTER_SLOT` Part III/IV/V, `FOLDING_VOID_LINE_DRAW` Part II/IV/V,
`FOLDING_PIXEL_TRANSMISSION`, `FOLDING_PIXEL_STRAIN`, `FOLDING_FLOORS` §1, `SPARSE_VESICA_EXPANSION`
§18.19, `FOLDING_OBSERVERS`, `FOLDING_SKIN_DETECTOR` Test 5, `FOLDING_MIXEDNESS_CONFIDENCE` +
`STATE_OF_THE_DETECTOR` §4, `SHOVELCAT_CHECKER_V6`. External: DIRE (Wang et al., ICCV 2023); diffusion
curves (Orzan et al., 2008); SLIC / Mumford–Shah as the working analog.*
