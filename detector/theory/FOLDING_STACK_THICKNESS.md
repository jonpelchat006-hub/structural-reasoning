# Stack Thickness — the content predicts it, and the regenerated frame is 3.4σ flat

*Jonathan: *"the new paper can say whatever it wants, but it always changes the thickness that our 3rd
observer can see ... our 3rd observer should be able to tell what the thickness SHOULD be. but if it
comes back as completely flat or with different info we know its not the original?"* **Both halves
measured.** Content predicts fingerprint strength at **R² = 0.607** from texture alone — so thickness
is forecastable, which is what makes a residual meaningful. And against that forecast the fully
regenerated frame lands at **z = −3.37**, while all six locally edited frames land **inside the band**.
That is the correct behaviour, not a failure: whole-image thickness catches **regeneration**, and local
edits need the within-image comparison that already gives +0.654. The honest band is wide — 7.7×
scatter — so this instrument reads "flat", not "slightly thinner". Status: MEASURED, n = 22 authentic
/ 7 edited. Companion to `FOLDING_EDGE_OBSERVERS`, `FOLDING_PRNU_LOCALISATION`.*

---

## Part I — There are four positions, and the fourth is the forgeable one

Jonathan noticed the asymmetry: *"oh so theres only 3 then? but its still in the same position just
without the opposite side."*

Three are built. The fourth exists and is already in the codebase under another name.

| | position | what it reads | status |
|---|---|---|---|
| 1 | face-on, coarse→fine | content at structure scale | built, `FOLDING_TWO_SIDED_WINDOW` |
| 2 | face-on, fine→coarse | content at mark scale | built, same |
| 3 | **edge-on, from below** | the bottom layer — the sensor | **PRNU, +0.654** |
| 4 | **edge-on, from above** | the top layer — the claim | `format_probe.py`, Channel A |

**The fourth observer is the new paper.** EXIF, quantisation tables, C2PA manifests, the compression
history — everything written on top after the fact. And its defining property is exactly the one
Jonathan named: **it can say whatever it wants.** Anyone with exiftool can rewrite it; the Nikon Z6III
was made to cryptographically sign an AI image within nine days of shipping capture signing.

So the frame is complete at four. It is just that one of the four is untrustworthy **by construction**,
which is precisely why it has to be crossed with the observer reading from the other end of the stack
rather than believed on its own.

`FOLDING_EDGE_OBSERVERS` established why the from-above position is weak beyond forgery: the compression
channel was built (JPEG ghosts) and refuted — 0.877 against a control of 0.684, 2 of 4 — because the
editor re-presses the whole frame, so the top layer carries no within-image contrast. **Layers above
the edit erase themselves as evidence. Layers below it survive.** Position 4 is above; position 3 is
below. That is the whole asymmetry.

## Part II — Does the content predict the thickness?

It has to, or the residual means nothing. And there is a specific reason to worry: **raw fingerprint
strength is content-dependent** — a flat sky exposes it, a textured wall buries it. Reading raw PCE
would reinvent the confound that killed 34 features.

Fitted on the 22 authentic camera-original frames, log PCE against log texture:

```
log PCE = -2.19 x log(texture) - 1.55
R² = 0.607     Pearson -0.779     Spearman -0.712
```

**Texture alone explains 61% of the variance in log fingerprint strength.** Thickness *is* forecastable
from content, which is exactly what Jonathan's third observer needs in order to know what it should be
seeing.

**But the honest band is wide.** Leave-one-out residual sd is 2.04 in log units — a **7.7× scatter**
around the prediction. So this instrument can say *"there is nothing here"*. It cannot say *"this is
slightly thinner than it should be."* Any claim finer than an order of magnitude is not supported.

## Part III — What the edited frames do to it

| image | edit % | PCE original | PCE edit | ratio | **z vs prediction** | reading |
|---|---|---|---|---|---|---|
| `145954(1)` | **regenerated** | 8838.3 | **5.7** | **0.001** | **−3.37** | **no stack** |
| `171842(1)` | 0.18% | 8907.0 | 6314.2 | 0.709 | +2.63 | within band |
| `171934(1)` | 0.38% | 6005.2 | 4809.4 | 0.801 | +2.36 | within band |
| `171842(1)(1)` | 2.66% | 8907.0 | 5604.6 | 0.629 | +2.56 | within band |
| `150002(1)` | 3.72% | 7541.5 | 6105.7 | 0.810 | +1.27 | within band |
| `171926(1)` | 5.08% | 17846.3 | 9701.0 | 0.544 | +1.66 | within band |

**Exactly the structure the model predicts.** Whole-image thickness separates the regenerated frame
decisively — z = −3.37, three and a half standard deviations below what its content says it should be,
and a ratio of 0.001 against its own original. Local edits do not move it: a 0.4% edit cannot change
the whole-frame fingerprint, and it should not.

**So the two readings work at different scales and both are needed.**

| scale | question | measure | result |
|---|---|---|---|
| whole image | is the stack there at all? | thickness vs content prediction | **z −3.37 on regeneration** |
| within image | is the stack there *everywhere*? | per-block fingerprint | **0.927 vs 0.273 control** |

Jonathan's *"completely flat or with different info"* is the whole-image test. *"Which paper got stuck
on where"* is the within-image one. They are not competing; they catch different states.

## Part IV — The ladder, and what it can honestly support

*"theres a bunch of different things we could say right? like its been edited, not original, a copy of
original, filtered, regenerated, and then eventually in some cases generated?"*

Yes — and the fingerprint sorts them by **how the attenuation is distributed**, which is a cleaner
organising principle than the labels themselves.

| state | fingerprint signature | evidence here | separable? |
|---|---|---|---|
| **camera original** | full, matches content prediction | PCE 1460 flat / 671 all frames | ✅ with an enrolled device |
| **copy / re-encoded** | present, **uniformly** thinner | old resized set, PCE 18–21 | ✅ uniform ≠ local |
| **filtered / globally graded** | present, uniform | — | ❌ **not separable from a copy** by fingerprint |
| **locally edited** | present outside, **absent inside** | AUC 0.927 vs control 0.273 | ✅ n = 5 |
| **regenerated from a photo** | **absent everywhere** | z −3.37, ratio 0.001 | ✅ |
| **generated from nothing** | absent everywhere | — | ❌ **not separable from regenerated** |

Two collapses, and both are honest limits rather than gaps to be engineered away:

- **A global filter and a re-save look identical to the fingerprint.** Both attenuate uniformly. Telling
  them apart is a content question, which is positions 1 and 2 — the face-on pair. This is a genuine
  place where the crossing is *required*, not decorative.
- **Regenerated and generated-from-nothing are the same to this observer.** Both have no fingerprint.
  Separating them needs Channel A (was there ever a camera claim?) or the semantic committee. And
  Channel A is the forgeable one — so this distinction is the weakest in the ladder and should be
  offered with the least confidence.

### And the constraint that scopes everything

**All of it requires an enrolled device.** Without a reference pattern from the camera, absence of a
fingerprint means nothing at all — an unknown phone and a generated image look the same. So the
supportable product claim is not *"this is AI"*; it is:

> **"This is / is not an unmodified capture from this enrolled camera — and here is the region that
> is not."**

That is narrower than "AI detector" and it is answerable, which per `FOLDING_CLEAN_HISTORY` is the
trade this project should be making. It also has a natural market shape: a phone that enrols its own
sensor, or an organisation enrolling its fleet.

---

## Honest ledger

**MEASURED**
- Content predicts fingerprint strength: **R² 0.607**, Spearman −0.712, from texture alone, on 22
  authentic camera-original frames.
- Honest prediction band is **7.7× (leave-one-out)**. This reads "absent", not "attenuated".
- Regenerated frame: **z = −3.37** against its content's prediction; ratio 0.001 to its own original.
- All 6 locally edited frames land **inside the band** — correct behaviour, not a miss.
- Fourth observer position identified as Channel A (`format_probe.py`) — complete frame, one member
  forgeable by construction.

**CAVEATS**
- n = 22 authentic / 7 edited, one phone, one camera, one editor.
- The regenerated case is **n = 1**. Its z of −3.37 rests on a band fitted to 22 frames.
- Texture is a crude content predictor; brightness, saturation and scene depth are unmodelled.
- The +0.00103 AI-control offset in the PRNU reference is still unresolved and still blocks any
  absolute threshold.

**HONEST LIMITS OF THE LADDER**
- Filtered vs copied: **not separable** by fingerprint. Needs the face-on pair.
- Regenerated vs generated-from-nothing: **not separable** by fingerprint. Needs Channel A, which is
  the forgeable member.
- Everything requires an **enrolled device**. This is not a general internet-image detector.

**NEXT**
1. A better thickness model — add brightness and saturation, and refit on the larger flat set when it
   arrives. Narrowing the 7.7× band is what turns "flat" into "thinner than it should be".
2. More regenerated frames. On this evidence full regeneration is the **easiest** case, and it is the
   one the rest of the field cannot do.
3. Second phone: proves the reference is device-specific rather than model-specific — the claim the
   whole ladder rests on and the one thing still completely untested.

*Sources: internal — `FOLDING_EDGE_OBSERVERS` (the direction rule and the refuted ghost channel),
`FOLDING_PRNU_LOCALISATION` (+0.654 and the regeneration collapse), `FOLDING_PRNU` (the reference),
`FOLDING_CLEAN_HISTORY` (one-class framing and claim scoping), `FOLDING_TWO_CHANNEL_LOOP` (Channel A
forgeability, the Nikon case). Artifacts: `prnu_camera2.json`, `prnu_camera2_localise.json`.*
