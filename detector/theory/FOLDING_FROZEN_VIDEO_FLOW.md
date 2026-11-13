# The frozen video — filament flow and rootedness

*2026-07-28. Jonathan: "An image is still just a frozen video right? … hair should tend to flow
downwards … shouldn't each pixel have a flow into the next pixel? … each hair should have a connection
back, but AI often have random hairs coming from nowhere."*

**Two claims live in that, and they had to be separated before either could be tested. The whole-frame
version is refuted and turns out to be a content detector. The hair-restricted version points the
predicted way but sits below the noise floor of the real set itself — underpowered, not refuted, and
the distinction matters.**

---

## 1. Separating the two claims first

| | claim | kind |
|---|---|---|
| **flow coherence** | neighbouring pixels agree on which way structure runs | **statistical** — this is the structure tensor, well-trodden |
| **rootedness** | every filament traces back to a source; a hair grows out of a head | **structural / topological** — genuinely different |

The project's record says which to bet on. Statistical measures have died repeatedly here — photon
transfer came back *inverted*, lens shading gave between/within 0.30, 40 of 42 free features failed
their controls. What survived was structural: container layout, the rank-one spectrum, metadata shape.
`shading_observer.py` wrote the rule down: *"structural invariants survive processing where statistical
ones do not."*

A floating hair fragment is not a weak statistic. It is a connected component that touches nothing. So
rootedness was measured as **connected-component analysis of the ridge skeleton** — Frangi filter at
hair scale (σ 1–3 px), skeletonise, then ask how much of the filament mass sits in isolated fragments
rather than in the connected mat a real head of hair forms.

Full parity throughout: EXIF-correct, 768 px longest side, one identical JPEG q85 encode. Without it
the PNG/JPEG split does the separating — that difference alone once separated these classes at AUC
0.008.

## 2. Whole-frame: refuted, and it is a content detector

Gate: target must beat both controls by > 0.02 **and** reach |AUC − 0.5| ≥ 0.25.

| measure | TARGET (AI vs real portrait) | CTRL content (portrait vs landscape) | CTRL noise | verdict |
|---|---|---|---|---|
| orphan_frac | 0.088 | **0.262** | 0.024 | no |
| components_per_kpx | 0.070 | **0.244** | 0.071 | no |
| filament_density | 0.147 | 0.229 | **0.452** | no |
| coherence | 0.038 | **0.317** | 0.143 | no |
| coherence_sd | 0.210 | 0.013 | 0.167 | no |
| largest_share | 0.052 | 0.035 | **0.286** | no |

**Nothing clears.** And the pattern is the one `FOLDING_PHOTO_SET_AUTOPSY` warned about: the content
control beats the target on four of six measures. `orphan_frac` separates *real portraits from real
landscapes* at 0.262 while separating real from AI at 0.088 — it is measuring **grass and twigs**, not
provenance.

**The direction is also inverted.** Median orphan fraction: AI **0.311**, real portraits **0.363**. Real
photographs have *more* floating filament fragments than generated ones — which on reflection makes
sense: noise, motion blur and depth of field break real strands, while a diffusion decoder produces
locally-smooth, locally-consistent texture. The intuition runs the opposite way to the physics of
capture.

## 3. Hair-restricted: the direction comes back, the power does not

A fair objection to the above: a landscape is *nothing but* filaments. The claim was about hair. So —
restrict to the upper-central band where hair sits in a portrait, portraits only.

| measure | AI median | real median | TARGET | **noise floor** |
|---|---|---|---|---|
| orphan_frac | **0.394** | 0.355 | 0.106 | **0.286** |
| largest_share | **0.083** | 0.133 | 0.233 | **0.310** |
| components_per_kpx | 47.35 | 47.51 | 0.106 | 0.143 |

**The direction is now the predicted one on both connectivity measures.** AI hair has a higher orphan
fraction and — more tellingly — a *smaller* largest component: 0.083 against 0.133. AI hair is less
connected into one mat. That is Jonathan's claim, pointing the right way.

**But the noise floor exceeds the target on both.** Splitting the 13 real portraits at random separates
them more strongly (0.286, 0.310) than AI separates from real (0.106, 0.233). At this n the measurement
cannot distinguish signal from the sampling variation of the real set alone.

Note also what the restriction costs: with a hair-specific measure there is **no content control
available** — landscapes have no hair region — so only the noise floor remains. That is a real
weakening, which is why this is a follow-up rather than the headline test.

## 4. The honest verdict, in two parts

- **Whole-frame flow and rootedness: REFUTED.** Fails the gate, the content control beats it, and the
  effect runs backwards. It is a texture-of-scene measure.
- **Hair-restricted rootedness: UNDERPOWERED, not refuted.** Direction correct on two independent
  connectivity measures; magnitude below the noise floor at n = 17 vs 13.

Those are different states and must not be collapsed. Calling the second one "refuted" would repeat the
error made in `FOLDING_CAMERA5_HUMAN_ARM`, where a measure was written off on the wrong test and had to
be partly restored a turn later.

**Coherence — the statistical form — failed independently and by a wider margin** (target 0.038 against
a content control of 0.317). So the well-trodden version of the idea is dead here even though the
structural version is merely unresolved, which is consistent with everything else this project has
found.

## 5. What would actually settle it

The binding constraint is not the method, it is the sample. A noise floor of 0.286 from a 13-image set
means the experiment cannot resolve anything smaller than that, and the effect looks smaller.

> **~50 real portraits and ~50 AI portraits, content-matched** — same framing, similar subjects, hair
> visible, both classes through one identical export path.

This is the same request `FOLDING_PHOTO_SET_AUTOPSY` Part VI made and it has been outstanding for the
whole project. It is now blocking a *second* line of work, which raises its priority: it is the only
missing input that would let the class-separation question be asked at all.

A second refinement worth building once the data exists: **trace each filament and test whether its
endpoint terminates against a mass** (scalp, shoulder, frame edge) rather than in smooth empty space.
That is closer to Jonathan's actual formulation than connected-component counting, which only detects
fragments that touch *nothing* — a hair emerging from nowhere but crossing another hair would be caught
by endpoint tracing and missed by components.

## 6. Tally

**52 features tested across the project, 2 have ever cleared the gate** (flat `R/G`, `RG_opp` — and
both are now understood as device-model evidence rather than authorship evidence). This adds 8 tested,
0 passed, 2 in the underpowered column awaiting data.

**Code:** `flow.py`, `flow.json`.
