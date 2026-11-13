# Radial Shading — the first free feature in 40 to clear the gate, and it clears by a hair

*Jonathan: enrollment-free detection is possible, others do it, we need our own way in. The strongest
untested candidate was **lens shading** — geometric rather than statistical, so it survives the noise
reduction that killed the photon-transfer test. Built and run. **`rg_amp` — the amplitude of the
red/green ratio's radial trend — is the first model-free feature in 40 attempts to clear every
real-vs-real control: target 0.283 against controls of 0.107, 0.227, 0.146.** But it clears its worst
control by **0.056**, and **the blue channel shows nothing (0.027)** — which argues against the optical
mechanism I proposed, because a real lens vignettes red and blue alike. **A lead, not an asset.**
Separately, `radial_r2` separates real from *regenerated* at AUC 0.859. Status: MEASURED. Tally: 40
tested, 1 passed.*

---

## Part I — Why shading, and why ratios

`FOLDING_IMAGINARY_CAMERA` failed inverted because computational photography rewrites noise before the
file is written. Its diagnosis pointed somewhere specific: **structural invariants survive processing
where statistical ones do not.** Noise reduction reshapes noise; it does not move geometry.

Lens shading is the strongest of those. Light falls off toward the corners, radially about **one**
optical centre, and the falloff is **wavelength-dependent** — R, G and B vignette by different amounts.
So a real frame should carry a smooth radial trend in its **colour ratios** about a single point.

**Ratios, not brightness** — that choice is the whole experiment. Fitting brightness against radius
mostly fits the scene: bright sky above dark ground is not vignetting. R/G and B/G are far less
scene-driven, because real scenes rarely have a strong colour gradient that is radially symmetric about
the frame centre, while a lens always does.

## Part II — The raw numbers, before controls

| feature | real | regenerated | AI-generated | AUC real-vs-regen | AUC real-vs-AI |
|---|---|---|---|---|---|
| `radial_r2` | 0.934 | **0.513** | 0.949 | **0.859** | 0.422 |
| `radial_amp` | 0.048 | 0.011 | **0.492** | 0.775 | **0.087** |
| `rg_amp` | 0.030 | 0.006 | **0.777** | 0.800 | **0.093** |

Two things jump out.

**Regenerated phone photos fit a radial model badly** — `radial_r2` 0.513 against 0.934 for real, and
some individual files at −169 and −457, meaning the quadratic fit fails catastrophically. That is
AUC 0.859.

**AI-generated images fit BETTER than real photos, with ten times the amplitude** — `rg_amp` 0.777
against 0.030. Unsigned that is |AUC−0.5| = 0.407, which would clear the project's bar comfortably.

And that second one is exactly the shape that has been wrong 34 times. Generators love centre-weighted
composition and aesthetic vignetting; the AI set here is 12/17 studio beauty close-ups against a real
set of skies and walls. **Content is perfectly correlated with class in that comparison**, as
`FOLDING_PHOTO_SET_AUTOPSY` established. So it goes to the gate before it means anything.

## Part III — The gate

|AUC−0.5| against the three real-vs-real controls:

| feature | TARGET | CTRL1 content | CTRL2 device | CTRL3 content/1 device | verdict |
|---|---|---|---|---|---|
| **`rg_amp`** | **0.283** | 0.107 | **0.227** | 0.146 | **CLEARS CONTROLS** |
| `radial_amp` | 0.176 | 0.143 | 0.242 | 0.104 | confounded |
| `bg_r2` | 0.131 | 0.167 | 0.136 | 0.083 | confounded |
| `radial_r2` | 0.088 | 0.044 | 0.064 | 0.146 | confounded |
| `bg_amp` | 0.027 | 0.087 | 0.159 | 0.021 | confounded |
| `rg_r2` | 0.045 | 0.016 | 0.083 | 0.135 | confounded |

**`rg_amp` is the first model-free feature in 40 attempts to pass.** Given a base rate of 0 for 39,
that is worth recording.

### And three reasons to hold it loosely

1. **It clears by 0.056.** Target 0.283 against a worst control of 0.227 — the device arm. At these
   sample sizes that margin is inside the noise, and every prior near-miss in this project turned out
   to be a miss.
2. **The blue channel shows nothing.** `bg_amp` target is **0.027**. A real lens vignettes red and blue
   alike relative to green; an effect that appears in R/G and is absent in B/G **is not the optical
   mechanism I proposed.** More likely it is a white-balance or colour-rendering difference between
   pipelines — which is a real and possibly useful signal, but it is a *processing* signature, not an
   *optics* one, and it would be far easier for a generator to imitate.
3. **The target itself is weak** — 0.283, barely over the bar, on a set whose confounds are documented.

**Verdict: a lead worth one more experiment, not a feature to build on.** The single most informative
next test is why blue is silent, because that decides whether this is optics or colour processing.

## Part IV — The strategic answer

Jonathan is right that enrollment-free detection is possible and that a niche is winnable. The useful
part is that **we do not have to guess at the niche, because DSRI published it.**

The field's own measured gaps:

| gap | number |
|---|---|
| localisation ceiling | **0.38 IoU** |
| recall on locally synthesised content | **6 of 9 teams below 0.10** |
| composited → fully regenerated | CAT-Net **0.89 → 0.02**, TruFor 0.75 → 0.14 |
| cross-generator transfer | ~**60 F1 points** lost |
| detector accuracy, 2020-21 gens → Flux / MJ v7 | **79% → 18–30%** |

**Regeneration is the hole**, and it is the case where our enrolled method is at its strongest
(9 for 9, ratio ≤ 0.0033, no overlap). The honest sequence is therefore:

1. **Do not rebuild what exists.** IML-ViT and Mesorch are MIT-licensed and IMDL-BenCo is a working
   harness. Standing them up on our 13 + 7 pairs is a few hours and gives a real baseline — *"as good
   as others"* becomes a measured statement rather than an aspiration.
2. **Measure where they fail on our data**, especially the 9 regenerations. If they collapse the way
   the literature says, that is the niche, evidenced on our own files.
3. **Then** add whatever we have that fills it. Right now that is the enrolled fingerprint — powerful
   and market-limiting. `rg_amp` is the only free thing that has ever cleared the gate, and it is one
   marginal result.

**The two-tier product falls straight out**, and it matches the pricing instinct: a free or cheap tier
that runs the pretrained models on any image and performs about as well as anyone else, and a paid tier
for enrolled devices that does something **nobody else can do at all** — localise with a measured zero
false-positive rate. The first gets people in the door; the second is the thing worth paying for.

---

## Honest ledger

**MEASURED**
- **`rg_amp` clears all three real-vs-real controls**: 0.283 vs 0.107 / 0.227 / 0.146. **First pass in
  40 features.**
- `radial_r2` separates real from **regenerated** at AUC 0.859 — but that comparison has not been put
  through the same gate and must be before it is quoted.
- AI-generated images show **10× the radial colour amplitude** of real photos (0.777 vs 0.030) — almost
  certainly generator aesthetics, and the reason the gate exists.

**WHY TO HOLD IT LOOSELY**
- Clears its worst control by **0.056**, on the device arm.
- **Blue channel silent (0.027)** — inconsistent with the optical mechanism claimed. Likely colour
  processing, not lens physics.
- Weak target (0.283), small n, one phone.

**RUNNING TALLY**
- Model-free features tested against real-vs-real controls: **40. Passed: 1.**

**NEXT**
1. **Why is blue silent?** Fit R/G and B/G separately per lens (we now have three sensors) — if it is
   optics, the ultrawide should shade differently from the periscope and both channels should respond.
   If it is white balance, it will track the pipeline instead. This decides what `rg_amp` is.
2. **Stand up IML-ViT / Mesorch via IMDL-BenCo** on our pairs. Gives the baseline, and measures the
   regeneration gap on our own data rather than on the literature's word.
3. Only then decide whether to invest further in a free-tier signal.

*Artifacts: `shading_observer.py`, `shading_results.json`. Sources: internal —
`FOLDING_IMAGINARY_CAMERA` (the diagnosis that pointed at structural invariants),
`FOLDING_PHOTO_SET_AUTOPSY` (the control method and the confounded AI set),
`FOLDING_COMPETITIVE_POSITION` (the field's published gaps), `FOLDING_PER_SENSOR`,
`FOLDING_ROBUSTNESS`. External: TGIF2, COCO-Inpaint, DSRI Image Edit challenge results.*
