# Edge Observers — the stack has a direction, and only the bottom layer survives

*Jonathan proposed a four-observer frame: the existing forward/backward pair looking through the
window, plus **two more looking at it edge-on, seeing "the layers on the window stacking up that hold
the provenance info."** The frame is right and the measurement is not flattering to three quarters of
it. **Both existing observers are face-on** — that is why the free stack collapses to 2.8 effective
dimensions and why PC1 turned out to be photographic genre. The edge-on axis is genuinely new, and it
is the one that produced +0.654. But a second edge channel was built and tested here — compression
history via JPEG ghosts — and **it fails: 0.877 against a control of 0.684, beating its own control on
2 of 4.** Why it fails is the useful part, and it gives a rule for choosing edge observers:
**layers below the edit survive as evidence; layers above it are re-applied uniformly and erase
themselves.** Status: MEASURED (negative), n=4. Companion to `FOLDING_TWO_SIDED_WINDOW`,
`FOLDING_PRNU_LOCALISATION`.*

---

## Part I — What the existing window actually is

`FOLDING_TWO_SIDED_WINDOW` built the pair Jonathan is describing: one observer reading coarse→fine,
one reading fine→coarse, and the *difference between their blind spots* as the signal. It produced
`nonlocal_asymmetry`, which cleared the independence bar when nothing else did.

But both of those observers are looking **through the glass at the picture.** The axis they differ
along is **scale**, not position. `FOLDING_OBSERVER_FRAME` measured the consequence: 23 features
across four nominal axes span an effective rank of **2.82**, and PC1 — 57% of variance — is the
sharpness direction. `FOLDING_PHOTO_SET_AUTOPSY` then identified PC1 as **photographic genre**:
`spectral.slope` separates real portrait photography from real landscape photography at 0.478 while
separating real from AI at 0.356.

**So the face-on pair is complete, built, and mostly measuring what the picture is of.** 34 free
features have now been tested against real-vs-real controls and none has passed.

## Part II — Edge-on is a different axis, and PRNU is already one

An edge-on observer does not look at the picture. It looks at **the stack of processing layers the
picture was pushed through**: sensor → demosaic → noise reduction → JPEG → resize → edit → re-encode.
Face-on you see the image; edge-on you see the history.

PRNU is exactly this. It reads the **bottom** layer — the silicon — through everything above it, and
its strength degrades monotonically as layers accumulate:

| | PCE |
|---|---|
| camera-original | **1460** |
| resized and reshared | 18 |
| fully regenerated | **5.7** |

That is not an analogy for "seeing the layers stack up." It is the measurement of it. And it delivered
the project's only working localisation: **edited 0.927 vs control 0.273, +0.654, 5/5**
(`FOLDING_PRNU_LOCALISATION`).

**So Jonathan's edge observer is not speculative — it is the thing that worked, and he is naming its
position in the frame.** The frame is real. It is just not symmetric: three of the four positions are
built and mostly dead, and the fourth is carrying everything.

## Part III — The second edge channel, built and refuted

If edge-on is an axis rather than a lucky measure, it should have more than one channel. The obvious
second one is **compression history**, and it needs no reference and no enrolled device.

Method: JPEG ghosts (Farid 2009). A JPEG saved at quality q is near a fixed point of the q quantiser —
re-encode at q and little moves. Sweep q, and the curve's shape reports what the file was last pressed
at. A region pressed twice carries two quantisers and should have a different curve from one pressed
once. Computed per block, it localises.

### The instrument was broken first, and that had to be fixed before reading anything

The first run returned `q_min = 99` for every image, original and edited alike. That is not a finding —
the raw ghost difference falls **monotonically** with quality, because a higher-quality re-encode always
changes less, so the minimum sits at the top of the sweep by construction. **The measurement was of my
sweep, not of the files.** Fixed by dividing each block's curve by the image's own mean curve, which
removes the monotone trend and leaves only where a block departs from the frame's shared history — a
within-image framing, which is the one that has worked repeatedly here.

### And then it still fails

| image | edit % | blocks in | **dev AUC** | **control** | tilt AUC | control |
|---|---|---|---|---|---|---|
| `150002(1)` | 3.72% | 23 | 0.763 | **0.766** | 0.765 | 0.768 |
| `171842(1)(1)` | 2.66% | 15 | 0.877 | 0.610 | 0.868 | 0.072 |
| `171926(1)` | 5.08% | 29 | 0.867 | **0.943** | 0.720 | **0.956** |
| `171934(1)` | 0.38% | 1 | 1.000 | 0.417 | 1.000 | 0.654 |

**dev: edited 0.877, control 0.684, +0.192, beats its own control on 2 of 4.**
**tilt: edited 0.838, control 0.613, +0.226, 2 of 4.**

Two of the four controls are at or above their edited arm (0.766 vs 0.763; 0.943 vs 0.867). That is
the region-not-edit failure — the same one that killed the committee's localisation
(`FOLDING_SEAM_TEST`) and the material-baseline proxy (`FOLDING_SEAM_REBUILD_AND_DENSITY`). At n = 4,
with two live controls, this is not a signal.

The global arm failed identically: mean `q_min` 99.0 for originals and 98.6 for edits, mean depth
0.989 vs 0.987. Indistinguishable.

## Part IV — Why it fails, and the rule that falls out

This was **pre-registered as risk 2** and it is confirmed: *"the whole file is re-saved by the editor,
so the GLOBAL curve may be identical for both."*

The editing app re-presses the **entire frame**. Every pixel — generated and authentic alike — leaves
through the same quantiser at the same quality. So the compression layer carries no *within-image*
contrast, and its evidence about the edit is destroyed by the very act of saving the edit.

Compare PRNU. The sensor layer sits **below** the edit. Generative fill cannot write sensor noise it
never had, and the final re-press attenuates that noise everywhere equally without restoring it where
it is missing. **The contrast survives because the layer is beneath the thing being detected.**

> **The stack has a direction.**
>
> **Layers BELOW the edit survive as evidence.** The edit had to physically replace them and cannot
> synthesise them. Sensor PRNU, optical signatures, lens correction residue.
>
> **Layers ABOVE the edit erase themselves as evidence.** They are re-applied uniformly across
> authentic and generated pixels alike, so they carry no within-image contrast. Compression, resize,
> global filters, "enhance".

This is a selection rule for edge observers, and it explains the results already in hand rather than
being asserted: `FOLDING_TWO_CHANNEL_LOOP` found seam models collapse 0.89 → 0.02 on regeneration —
they read a *boundary between histories*, which regeneration removes. PRNU reads a *layer beneath the
history*, which regeneration cannot supply. The rule covers both.

**Consequence: the edge axis currently has exactly one working channel, and it is the bottom-most
layer.** The next candidates should be chosen by the rule — things beneath the edit, not around it.
Optical signatures (lens shading profile, chromatic aberration) are the obvious next ones, and
`FOLDING_MATCHED_BENCHMARK` already established they need raw or camera-original files, which is now
available.

## Part V — On the void lines carrying source attribution

Jonathan: *"wouldnt they connect back to their source observer and we would have multiple sets running
through at a time checking different things?"*

The design is right and it is a real upgrade in principle: `FOLDING_RECONSTRUCTION` Part II runs two
seeds (blind grid vs edge-committed outline) and reduces their comparison to **one scalar**,
`seed_convergence`. Keeping the attribution — *which seed's lines survived where* — turns a scalar into
a map, and this project has repeatedly found that the within-image version of a failed global measure
is the interesting one (`FOLDING_WITHIN_IMAGE`).

**But the machinery underneath does not currently clear a control.** `seed_convergence` was **refuted**
— measured inverted from prediction, 0.835 real vs 0.769 AI. And the whole reconstruction axis went
through the real-vs-real gate and came back **target 0.291 against controls of 0.258 and 0.283**
(`FOLDING_CLEAN_HISTORY`). Adding attribution to a measure that cannot separate itself from its own
null adds structure to noise, and it would be expensive structure.

**Recommendation: hold it.** If the reconstruction axis ever clears a control — and `return_at_low` is
the one candidate, with the project's first clean *content* control at 0.042 — then per-line source
attribution is the right next move on it. Not before.

## Part VI — The crossing, as it actually stands

Jonathan: *"or its like the 2 observers have to connect and we have 2 sets kind of crossing?"*

Yes, and that is the two-channel loop from `FOLDING_TWO_CHANNEL_LOOP` in the framework's own geometry:

```
   FACE-ON      what image the stack makes        content, semantics, genre
   (built, 2.8 dims, PC1 = genre, 34/34 features dead at the control gate)
                              ×
   EDGE-ON      what stack the image came through  PRNU: +0.654, 5/5
   (one working channel -- the bottom layer. Compression channel refuted, Part III)
```

The crossing is the cross-check: **does the stack seen edge-on match the image seen face-on?** A valid
signature on on-manifold content; a claimed Galaxy S23 capture with no S23 fingerprint in one region.
`STATE_OF_THE_DETECTOR` §1: *agreement across independent observers is the invariant; disagreement is
the depth.* Face-on and edge-on are as independent as two observers get — one is about meaning, the
other about physics.

**What is honest to say today:** the crossing has one strong arm and one weak one. The edge arm works
and localises; the face arm is 34 features with no survivors, and its only remaining product is the
paid semantic committee at 0.932 for the verdict. That is not the symmetric four-observer frame — but
it is a real frame, and it now has one measured member.

---

## Honest ledger

**MEASURED**
- Ghost/compression channel: **dev edited 0.877, control 0.684, 2 of 4 beat their own control**;
  global `q_min` 99.0 vs 98.6, indistinguishable. **Refuted at n = 4.**
- Instrument fault found and fixed first: raw ghost curves are monotone in quality, so `argmin` sat at
  the top of the sweep for every file. Detrending against the image's own mean curve was required
  before any reading was possible.
- Pre-registered risk 2 confirmed as the cause: the editor re-presses the whole frame.

**ESTABLISHED BY THIS**
- **The stack has a direction.** Layers below the edit survive as evidence; layers above it are
  re-applied uniformly and erase themselves. This is a selection rule for future edge observers and it
  retrodicts both the PRNU success and the seam-model collapse.
- The existing two-sided window is a **face-on pair**, differing along scale. The edge axis is new and
  currently has one working channel.

**HELD, NOT BUILT**
- Per-line source attribution for the void lines. The reconstruction axis it rests on scores 0.291
  against controls of 0.283. Revisit if `return_at_low` clears a device-arm control.

**NEXT**
1. Optics as the second edge channel — lens shading profile and chromatic aberration are *below* the
   edit and now testable, because camera-original files exist.
2. Fourier-Wiener the PRNU reference, then a real false-positive rate.
3. More pairs and a second phone — the second phone is what proves the reference is device-specific
   rather than model-specific, which is the difference between "this camera" and "this camera model".

*Sources: internal — `FOLDING_TWO_SIDED_WINDOW` (the face-on pair), `FOLDING_OBSERVER_FRAME` (2.82
effective rank), `FOLDING_PHOTO_SET_AUTOPSY` (PC1 = genre), `FOLDING_PRNU_LOCALISATION` (+0.654),
`FOLDING_TWO_CHANNEL_LOOP` (seam collapse on regeneration), `FOLDING_RECONSTRUCTION` (the seeds and the
refuted `seed_convergence`), `FOLDING_CLEAN_HISTORY` (the reconstruction control gate). External: JPEG
ghosts, Farid 2009. Artifacts: `ghost_observer.py`, `ghost_results.json`.*
