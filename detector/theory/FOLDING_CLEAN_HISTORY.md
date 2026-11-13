# A Clean History — stop discriminating, start modelling the authentic

*Two things at once. **The reconstruction axis came back CONFOUNDED**, but not like the other 33: its
direction was confirmed, it is the strongest target in the free stack, and its controls **match** it
rather than beating it — the first near-miss in the project, and `return_at_low` posts the first
genuinely **clean content control** ever recorded here (0.042). Running tally: **34 tested, 0 passed.**
Then Jonathan's reframe, which is the most important architectural move in the thread: *"we should know
what a clean history looks like too ... we could say its not an original photo if there is history
erasure."* That inverts the problem from discrimination to **one-class modelling of the authentic** —
and it fixes the failure direction the entire industry has backwards. Status: MEASURED + ARCHITECTURE.
Companion to `FOLDING_TWO_CHANNEL_LOOP`, `FOLDING_COMPETITIVE_POSITION`.*

---

## Part I — The reconstruction axis, through the gate

73 images, full parity (EXIF applied, centre-cropped square 448, one identical JPEG q85 encode),
target plus two real-vs-real controls. Predictions pre-registered in `recon_control.py` before running.

| measure | TARGET | CTRL1 content | CTRL2 device | raw target AUC | verdict |
|---|---|---|---|---|---|
| **`roundtrip_fixed_point`** | **0.291** | 0.258 | 0.283 | **0.209** | CONFOUNDED |
| `nonmonotone_fraction` | 0.241 | 0.328 | 0.315 | 0.259 | CONFOUNDED |
| `thermal_slope` | 0.233 | 0.419 | 0.339 | 0.733 | CONFOUNDED |
| `return_at_high` | 0.219 | 0.350 | 0.311 | 0.719 | CONFOUNDED |
| **`return_at_low`** | 0.203 | **0.042** | 0.213 | 0.703 | CONFOUNDED |
| `seed_convergence` | 0.142 | 0.386 | 0.266 | 0.642 | CONFOUNDED |

**`roundtrip_fixed_point` fell from 0.848 to 0.291** once parity and controls were applied — the
expected collapse, since its original benchmark was the set `FOLDING_PHOTO_SET_AUTOPSY` destroyed.

But two things distinguish this from the other 33 failures, and both should be recorded rather than
rounded away:

**1. The direction was confirmed.** Raw target AUC **0.209** — AI images sit closer to a fixed point of
the draw operator, exactly as `FOLDING_RECONSTRUCTION` Part 0 predicted and exactly as pre-registered.
The mechanism is real. It is the magnitude that is insufficient.

**2. Its controls match it rather than beating it.** Target 0.291 against a worst control of 0.283 — it
misses the bar by 0.012. Compare `spectral.slope`, which posted target 0.356 against a **content
control of 0.478**: the control beat the target by a wide margin, which is what "this is a genre
detector" looks like. Here the target is marginally the *highest* number in its row. That is not a pass
— an effect that cannot be separated from its own null is not an effect — but it is the first time in
34 attempts that the null did not win outright.

**3. And `return_at_low` posts the first clean content control in the project: 0.042.** Web portrait
versus web landscape, both real, essentially chance. No free measure has done that before; `slope`,
`hf_frac`, `spec_entropy` and `blur_ratio` were all at 0.45–0.48 on that arm. **Its failure is CTRL2 —
the device/population arm (0.213) — not content.** That is a materially different defect, and it is
one the router in `FOLDING_TWO_CHANNEL_LOOP` conditions on directly: Channel A knows the device
population before any pixel is read.

**Honest verdict: the reconstruction axis does not clear the gate and must not ship. It is the only
free measure whose mechanism survived its own test, and `return_at_low` is the only one whose content
control is clean.** Both remain hypotheses at n = 73, and the base rate is 0 for 34.

---

## Part II — The reframe: model the authentic, don't discriminate the fake

> *"but at the same time we should know what a clean history looks like too right? if its a real photo
> it should have a pretty simple history wouldnt it? ... it should have been taken with an actual
> camera with that kind of signature, or it should show signs of programs real people would use,
> instead of a flat regenerated history?"*

This is a different problem statement, not a different feature. Everything in this project — and
essentially everything in the field — has been a **discriminator**: learn the boundary between two
classes. Jonathan is proposing a **one-class model**: learn what an authentic history looks like, and
flag departures from it.

**Why that matters more than it sounds.** A discriminator trained on today's generators fails when the
generators move — the measured collapse is ~79% accuracy on 2020–21 generators to **18–30% on Flux Dev,
Firefly v4 and Midjourney v7**. It fails *open*: it keeps producing confident answers on inputs unlike
anything it was trained on. A one-class model of the authentic has the opposite failure mode. Novel
generators are simply *not the reference distribution*, so they do not require the model to have seen
them. **It fails closed: silence unless something departs.**

And that is the same shape as the ratchet. `FOLDING_RATCHET_AND_ROUTING` measured our gate at 0 false
positives on 33 real photographs precisely because it stays silent by default. **A positive model of
the authentic is the natural instrument for a ratchet**, in a way that a discriminator never is:
*"this history is impossible"* is a categorical claim; *"this scores 0.61"* is not.

### But three things are being merged here, and the difference is adversarial

| | what it reads | who asserts it | forgeable by |
|---|---|---|---|
| **Manifold membership** | the pixels — is the content on a generator's output set | nobody; it is measured | regenerating differently; not by metadata |
| **Attested provenance** | C2PA manifest, watermark | a **third party** with a key | breaking crypto, or the capture-signing gap |
| **History plausibility** | the container — EXIF, quant tables, software tags | **the file itself** | anyone with exiftool |

Jonathan's question merges the second and third. They are not the same thing and the gap is exactly
where C2PA got hurt: the **Nikon Z6III** case was an *attested* claim that was true about the capture
event and false about the content. History plausibility is weaker still — it is **self-reported**. A
file saying "Galaxy S23 Ultra" is a file saying so.

**So history plausibility is evidence of the absence of effort, not evidence of authenticity.** It
catches the lazy 95%. It does nothing against anyone who round-trips a generated image through a phone
gallery app to acquire a real camera signature — which takes one minute and no expertise.

### The base-rate problem, and it is severe — measured on our own files

"History erasure implies not an original" is true. **It is also true of most real photographs.**

| set | camera make | maker note | native dimensions |
|---|---|---|---|
| **Jonathan's 22 "real" photos** | 22/22 | **0/22** | ~1/22 |
| the 26 seam-pair files | 26/26 | **0/26** | mixed |
| web real photography (34) | 2/34 | **0/34** | unknown |

**Every single one of Jonathan's own authentic photographs fails a strict history test.** Non-native
dimensions, stripped Software tags, zero maker notes, all sitting near 1 MB regardless of pixel count —
they went through a share-and-download pipeline. Of the web real class, **15 of 34 have no EXIF at
all**.

So as a test for *"is this generated"*, history erasure has a catastrophic false-positive rate. It
would condemn the entire real class.

### Which is why the scoping is the whole point, and it is not a consolation prize

Jonathan called it *"not as satisfying but still something."* It is better than that:

> **"This is not a camera original" is answerable, checkable, and defensible.
> "This is AI-generated" is not.**

These are different claims, and **conflating them is precisely what the vendors do** — Sensity
advertising "court-ready" pixel heatmaps with zero published validation, Sightengine citing 98.3% while
an independent test caught 5 of 15. The honest product makes the claim it can support and refuses the
one it cannot. In a market where **no vendor publishes a false-positive rate at all**, shipping a
narrower claim with a measured FPR is a differentiator rather than a retreat.

It also happens to be what most real users need. "Was this photo edited before you sent it to me" and
"did a machine make this from nothing" are different questions, and the first one is asked far more
often.

## Part III — The strong version: claimed history versus observed pixels

The forgeable-metadata problem dissolves the moment the two channels are **cross-checked instead of
each being read alone**:

> A file claiming capture on a Galaxy S23 Ultra should carry S23 Ultra **sensor noise**, S23 Ultra
> **demosaic and lens-correction residue**, S23 Ultra **quantisation tables**, and an S23-shaped
> **resize history**. Faking the metadata is trivial. Faking the metadata *and* the physics it implies,
> consistently, is not.

That is the return leg of the `FOLDING_TWO_CHANNEL_LOOP` diagram, and it is where the loop earns its
keep. It is also, again, the framework's own invariant: two independent observers, and **the
disagreement is the finding**. A claimed history that the pixels do not corroborate is the sedenion
seam between channels.

### And the classical technique for it is PRNU — where we hold the rare prerequisite

**Photo-response non-uniformity** is sensor-level fixed-pattern noise: a manufacturing fingerprint
unique to an individual sensor, not a model. It is the one classical forensic method that answers
*"was this taken by THIS camera"* rather than *"does this look wrong"* — a positive membership test,
which is exactly what Jonathan is describing.

Its cost is that it needs **many images from the same device** to estimate the reference pattern, which
is why it is rarely usable. **We have 22 photos plus 26 seam-pair files from one Galaxy S23 Ultra —
48 images from a single sensor.** That is an unusual asset, and it makes a real test available:

1. Build a PRNU reference from a held-out subset of the S23 files.
2. Test whether individual held-out S23 images correlate with it — does the fingerprint survive the
   resize-and-recompress pipeline these files went through? **That question alone is worth answering**,
   because it bounds every history-based claim we could make about consumer files.
3. Test whether an AI image round-tripped through the same pipeline correlates. It should not.
4. Then the real one: **does PRNU drop inside the edited regions of the 13 seam pairs?** PRNU
   suppression is a documented tampering cue, the mask is known, and the control arm is the untouched
   original. Unlike everything else tried here, this is a *within-image* test of a *device-specific*
   quantity — so genre cannot confound it, and the same-camera-same-scene design makes population
   confounds cancel exactly.

Caveats, stated in advance: PRNU is degraded by resize, recompression and strong denoising, and all
these files have been through at least the first two; the seam pairs are the better material at near-
native resolution. And if PRNU is absent from the *authentic* files, that is itself the answer — it
says consumer-pipeline images cannot support device attribution, which is a real and publishable
negative.

---

## Honest ledger

**MEASURED**
- Reconstruction axis, 73 images, full parity, two real-vs-real controls: **nothing clears.**
  `roundtrip_fixed_point` 0.848 → **0.291**, controls 0.258 / 0.283.
- **Direction confirmed** (raw AUC 0.209, AI closer to a fixed point) — pre-registered and correct.
- **`return_at_low` posts the project's first clean content control, 0.042**; it fails on the device
  arm (0.213), a confound the router conditions on directly.
- **34 free features tested against real-vs-real controls. 0 passed.**
- Every one of Jonathan's 22 authentic photos fails a strict history test; 15/34 web real photos carry
  no EXIF at all.

**ARCHITECTURE ADOPTED**
- Move from **discrimination** to a **one-class model of the authentic**. It fails closed rather than
  open, it does not need to have seen the generator, and it is the natural instrument for the ratchet.
- Scope the claim to **"not a camera original"**, which is answerable, and refuse **"AI-generated"**,
  which is not — with the false-positive rate published either way.
- History plausibility is **Channel A self-report**: evidence of absence of effort, not of authenticity.
  It must be cross-checked against pixels, never trusted alone.

**NEXT, and it is cheap**
1. **PRNU on the 48 single-sensor files.** Does the fingerprint survive the consumer pipeline? Does it
   drop inside the seam masks? A within-image, device-specific test that genre cannot confound.
2. The mobile-OEM composited-vs-regenerated measurement (`FOLDING_TWO_CHANNEL_LOOP`), still the one
   number that decides the router.
3. Do **not** ship the reconstruction axis. Keep `return_at_low` on the list for the routed regime only.

*Sources: internal — `FOLDING_RECONSTRUCTION` (the 0.848 and Part 0's sign discipline),
`FOLDING_PHOTO_SET_AUTOPSY` (the control method and the set that produced the 0.848),
`FOLDING_RATCHET_AND_ROUTING` (0/33 false positives), `FOLDING_TWO_CHANNEL_LOOP`, `format_probe.py`
(the EXIF/maker-note audit). External: detector generational collapse (arxiv.org/abs/2602.07814),
C2PA capture-signing gap and the Nikon incident (arxiv.org/abs/2604.24890). Artifacts:
`recon_control.py`, `recon_control_results.json`.*
