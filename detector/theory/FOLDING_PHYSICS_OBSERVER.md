# The Physics Observer — the environment outside the window, and the content confound it fixes

*Captures a working session (Jonathan + Claude). Jonathan: "would we use the rest of the space the
window is in as like the environment? we could see where the shadows are and place an imaginary sun
inside our structure that would make those, and see if that would match everything else… if we place a
light that reflects in one eye we would know where the reflection would be in the other."*

*Two things happened. First, checking whether his idea was runnable on the current data exposed a
**content confound that undermines every AUC measured in this line so far** — including the existing
mixedness headline. Second, his proposal turns out to be the one measurement class that is
**structurally immune** to that confound. Companion to `FOLDING_TWO_SIDED_WINDOW`,
`FOLDING_RECONSTRUCTION`, `FOLDING_OBSERVERS`, `FOLDING_OUTER_SLOT`. Status: confound MEASURED;
physics observer designed, not built.*

---

## Part I — The content confound (urgent, and it is ours)

Looking at the benchmark images as contact sheets rather than as filenames:

- **AI class (n=17):** ~13 tight studio-lit beauty portraits, shallow depth of field, smooth skin,
  controlled key light. Plus a magazine cover, a t-shirt shot, a car interior.
- **Real class (n=12):** outdoor phone snapshots — a valley, a bridge, a forest trail, fog, rocks, a
  bird, a dog in a car, a cat on a bed. **Two** contain a human face.

The classes differ in *content and lighting setup* at least as much as in provenance. So the obvious
test: split the real class by content alone and see how far that moves the score.

| measure | real outdoor (n=8) | real close/indoor (n=4) | AI (n=17) | content drift as % of the real-vs-AI gap |
|---|---|---|---|---|
| `nonlocal_asymmetry` | 0.580 | 0.414 | 0.330 | **66%** |
| `blur_ratio` (mixedness) | 0.352 | 0.505 | 0.552 | **77%** |
| `return_at_low` (reconstruction) | 0.981 | 0.971 | 0.963 | **54%** |

**Changing only the content of a genuinely real photograph reproduces 54–77% of the "AI signal."** One
real human face scores `blur_ratio` 0.580 — *more AI-like than the AI class average* of 0.552.

**This is the same class of error as the compression confound**, caught one layer later. Compression
parity was enforced; content parity was not. Every AUC in `FOLDING_RECONSTRUCTION` and
`FOLDING_TWO_SIDED_WINDOW` is therefore an upper bound contaminated by "studio portrait vs outdoor
snapshot," and so, on this set, is `blur_ratio`'s 0.882. The *relative* findings survive better than
the absolute ones — the independence audit compares measures on identical images, so
`nonlocal_asymmetry` clearing the bar while its own endpoints fail it is still a statement about the
measures. But **no number in this line should be quoted until the benchmark is content-matched.**

**The fix is a matched-content benchmark**, and it is cheap: for every AI portrait, a real portrait
shot in comparable conditions; for every AI landscape, a real landscape. `bench_photo_metrics.json`
(n=50, AUC 0.952) should be re-derived under the same discipline — its image sets are still missing
from disk, so it currently cannot be audited for this at all.

---

## Part II — Why Jonathan's idea is the structural answer, not just another feature

Every measure built in this line so far — spectral, mixedness, reconstruction, predictability — is a
**statistic of the pixel field**. That is exactly why they keep colliding with sharpness (|r| = 0.79,
0.81, 0.89) and why they are vulnerable to content: a statistic of the pixels moves when the pixels
depict something else.

A lighting-consistency measure is not that. It asks a **within-image** question: *does this image's own
light have a single consistent explanation?* No cross-image statistic is involved, so:

- **It is confound-immune by construction.** A landscape and a portrait can each be self-consistent or
  not. Content parity stops mattering. So does compression parity, largely — JPEG does not move a
  shadow.
- **It is the strongest independence available.** The physics of light does not correlate with blur
  because it is not a property of the pixel distribution at all; it is a property of an *inferred 3D
  scene*. This is the first candidate that should clear the independence bar for a structural reason
  rather than an empirical one.
- **It fills the outer slot with physics instead of a model.** `FOLDING_OUTER_SLOT` Part I: the slot is
  polymorphic — ESM for proteins, an LLM for ARC, a VLM for images. A *renderer* is a legitimate
  occupant, and unlike the others it costs nothing per call and never goes stale as generators improve.

**And the corpus was already using his image as a metaphor.** `FOLDING_OBSERVERS`: *"This is stereo
vision exactly: two eyes see slightly different shadows, and the difference between shadows is
distance."* Jonathan's catchlight test is that sentence made literal — two eyes as two observers of one
invariant (the light), and their disagreement as the seam.

---

## Part III — The three probes, hardest last

### III.a — Catchlights: two eyes, one light (build this first)

A specular highlight on a cornea is a **mirror image of the light source**. Two eyes in one face are
two observers of the same light from slightly different angles, so the highlight's position, shape and
count are geometrically constrained between them. A single consistent light → the two agree. A
manufactured face → they drift independently.

This is an **established forensic technique**, not a new idea: Johnson & Farid, *Detecting Photo
Manipulation from Eye Reflections* (2007), estimates the light direction from the corneal highlight and
tests inter-eye consistency. It has been revived recently for GAN and diffusion faces — generators
produce plausible eyes without a shared scene model, so the two highlights are frequently inconsistent.

Concretely: locate the eyes (mediapipe face mesh is available), crop the iris at **native resolution**,
extract the specular blob, and compare position-within-iris, shape, orientation and count between the
two. Emit an inconsistency score plus a *fired / did-not-fire* flag.

### III.b — The imaginary sun: shadow consistency

Jonathan's "place an imaginary sun inside our structure that would make those, and see if that would
match everything else." Each shadow gives a **constraint line** from the shadow point to its casting
point; a real scene's constraints intersect at one light position. Fit the best single light and report
the residual — a large residual means no single sun explains the picture. Also established (Kee,
O'Brien & Farid on inconsistent shadows). Harder in the wild than catchlights because it needs
shadow-to-caster correspondences, which is itself a vision problem.

### III.c — The lighting studio / terrain: full inverse rendering

"Build a lighting studio in the foreground, or the terrain, and see if they would all make sense." This
is inverse rendering — recover geometry, material and illumination, re-render, compare. The most
complete form of the idea and the least tractable; treat it as the direction of travel, not the next
build.

---

## Part IV — The honest limits of the physics observer

- **It is conditional, and that is fine.** It fires only when the scene supplies the cue: two visible
  eyes, or clear cast shadows. Perhaps a third of images. That makes it a **high-precision,
  low-recall** branch, which is exactly what an `axis_router` is for — not a global axis, and it must
  report *did-not-fire* rather than a neutral score, or it will dilute the committee on every image
  that lacks the cue.
- **It needs native resolution.** A catchlight is a few pixels wide. The 512 px working side used
  everywhere else in this pipeline destroys it. This observer must read the original file.
- **The margin is shrinking.** Generators have improved on eye rendering specifically. Expect this to
  degrade with each generation — unlike the framework's structural measures, which is an argument for
  keeping both kinds.
- **It cannot be benchmarked on the current data.** The real class has two faces; the AI class has
  thirteen. Testing catchlight consistency here would be a portrait detector wearing a physics costume
  — precisely the error Part I just documented.

---

## Honest ledger

**MEASURED THIS SESSION**
- The content confound: 54–77% of the apparent signal on three separate measures is reproducible by
  changing the content of a real photo alone. One real face out-scores the AI mean on `blur_ratio`.

**ESTABLISHED EXTERNALLY (not our result)**
- Corneal-highlight light estimation and inter-eye consistency as a manipulation detector
  (Johnson & Farid 2007) and its recent application to generated faces.
- Shadow-constraint consistency (Kee, O'Brien & Farid).

**DESIGN-STAGE**
- The physics observer as an outer-slot occupant; the confound-immunity argument, which is structural
  and therefore strong, but **not yet demonstrated on images**.
- Its independence from the pixel-statistic axes — argued from first principles, must still be measured
  the same way everything else was.

**BLOCKED**
- Both the confound fix and the catchlight test need **matched-content image sets**: real portraits
  against AI portraits, real landscapes against AI landscapes.

*Sources: `FOLDING_OBSERVERS` (stereo vision; agreement = invariant, disagreement = depth),
`FOLDING_OUTER_SLOT` Part I (the polymorphic slot), `FOLDING_TWO_SIDED_WINDOW` (the independence bar
and the measures audited here), `FOLDING_RECONSTRUCTION` (the compression-parity discipline this
extends to content), `FOLDING_MIXEDNESS_CONFIDENCE`. External: Johnson & Farid, *Detecting Photo
Manipulation from Eye Reflections* (2007); Kee, O'Brien & Farid on shadow consistency; inverse
rendering generally.*
