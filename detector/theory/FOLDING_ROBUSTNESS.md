# Robustness — it dies at the first platform hop, and it never once lies

*The sweep that bounds both tracks. **Re-encoding is survivable: q85 keeps 62% of the fingerprint at
8/8 detection, and a double q85 round trip keeps the same. A 90% centre crop keeps 94%.** But **every
realistic platform pipeline kills it completely — WhatsApp-like, Instagram-like and screenshot-like all
score 0/8.** Downscaling is the killer, exactly as pre-registered. And the finding that matters most for
the product: **0 false positives across all 120 negative tests, in every single condition.** Degradation
destroys signal and never manufactures a match. **It fails silent, not wrong.** Status: MEASURED,
8 positives / 8 negatives × 15 conditions.*

---

## Part I — The table

Reference from 7 main-camera frames; positives are 8 disjoint main-camera frames; negatives are 8
**ultrawide** frames — a genuinely different sensor in the same body, the hardest realistic negative.
Where a condition changes geometry the reference is transformed identically, which is what a real
verifier would do since it knows the claimed device. PCE peak searched over the full correlation
surface, so the crop conditions mean something.

| condition | median PCE | % of baseline | detected | **false pos** |
|---|---|---|---|---|
| original | 2197.5 | 100% | **8/8** | 0/8 |
| resize 0.75 | 2574.8 | **117%** | **8/8** | 0/8 |
| centre crop 90% | 2063.9 | 94% | **8/8** | 0/8 |
| re-encode q95 | 2077.5 | 95% | **8/8** | 0/8 |
| re-encode q85 | 1362.1 | 62% | **8/8** | 0/8 |
| double re-encode q85 ×2 | 1359.4 | 62% | **8/8** | 0/8 |
| re-encode q75 | 700.6 | 32% | 7/8 | 0/8 |
| crop 90% + q80 | 445.1 | 20% | 7/8 | 0/8 |
| resize 0.50 | 399.1 | 18% | 6/8 | 0/8 |
| re-encode q60 | 316.5 | 14% | 5/8 | 0/8 |
| re-encode q50 | 231.4 | 11% | 5/8 | 0/8 |
| **screenshot-like** (1080px q85) | 24.2 | 1.1% | **0/8** | 0/8 |
| **WhatsApp-like** (1600px q70) | −0.8 | 0% | **0/8** | 0/8 |
| **Instagram-like** (1080px q75) | −22.1 | −1% | **0/8** | 0/8 |
| **resize 0.25** | −22.1 | −1% | **0/8** | 0/8 |

**Total false positives across every condition: 0 / 120.**

## Part II — What survives and what does not

**Compression alone is survivable.** q85 holds 8/8 at 62% of baseline, and running it through q85
*twice* costs nothing further — the second pass lands on the same quantiser and barely moves the file.
Detection degrades gracefully from q75 down and is still partial at q50.

**Cropping is survivable**, once the correlation peak is searched rather than assumed at zero lag —
94% of baseline at a 90% crop, 8/8. That matters because crops are common and would otherwise look like
a total failure for a purely bookkeeping reason.

**Mild downscaling is fine and slightly helps.** Resize to 0.75 came in at **117% of baseline** — above
the original. Most likely mild resampling suppresses JPEG blocking noise while leaving the fingerprint
intact, improving the ratio. Interesting, not load-bearing, and not worth building on at n = 8.

**Downscaling past ~0.5 is fatal**, and this is the pre-registered prediction confirmed: resize 0.50
already drops to 18% and 6/8; resize 0.25 is gone. PRNU lives at photosite resolution and averaging
photosites together destroys it. `FOLDING_PRNU` measured the same thing from the other direction — the
resized real-world set at PCE 18 against 1460 for camera-original.

**Every realistic platform pipeline kills it.** WhatsApp-like, Instagram-like and screenshot-like all
score **0/8**, because they all combine aggressive downscaling with re-encoding. It is the resize doing
the damage, not the compression — but they always arrive together.

## Part III — The finding that matters most

**The false-positive rate is zero in all 15 conditions, 120 negative tests.** The maximum negative PCE
across the entire sweep was 38.0, against a bar of 50, and it did not trend upward as conditions got
harsher.

**Degradation destroys signal. It never manufactures a match.**

That is the property `FOLDING_CLEAN_HISTORY` argued for and `FOLDING_RATCHET_AND_ROUTING` measured at
0/33 — now confirmed under adversarial-ish conditions. **The system fails to "cannot tell", never to
"wrong answer".** For anything used in a claim, a dispute, or an evidentiary setting, that is the
correct failure mode and it is the opposite of what the market currently ships: NewsGuard measured a
13.3% false-positive rate across five leading tools on authentic images.

The correct product behaviour follows directly: **when the fingerprint is absent, abstain — do not
accuse.** Absence is consistent with "generated", "heavily processed" and "not from this device", and
those cannot be separated. The verdict is three-valued, not two.

## Part IV — What it means for each track

### For the product

The addressable market is **capture-time and one hop**, not "any photo on the internet":

| works | fails |
|---|---|
| capture inside a controlled app | anything through WhatsApp / Messenger / Instagram |
| direct file transfer, cable, original-size email | any screenshot |
| cloud storage originals | any thumbnail or web-optimised copy |
| a re-encode or two, even at q75 | anything downscaled past half |
| a crop | |

**This validates the proof-of-work product shape and rules out the open-web one.** A contractor
photographing a job through your app is entirely inside the working envelope. A user pasting a photo
they found on Facebook is entirely outside it, and no amount of engineering changes that — the evidence
was destroyed before the file arrived.

Stated positively for a pitch: *"works on the file as captured, and on a copy of it — not on something
that has been through a social platform."* That is a limitation to lead with, not bury, because it is
also what makes the zero false-positive rate possible.

### For the DSRI paper

This is the limitations section, and it is a strong one rather than an apology: graceful degradation
under compression, hard failure under downscaling, **and a zero false-positive rate maintained across
every degradation level tested**. The last point is the publishable one — most forensic measures get
*noisier* under degradation, which is how false positives appear.

---

## Honest ledger

**MEASURED (8 positives, 8 negatives, 15 conditions, 120 negative tests)**
- Re-encode q85 → 62% of baseline, **8/8**; double q85 → 62%, 8/8; q75 → 32%, 7/8; q50 → 11%, 5/8.
- Crop 90% → 94%, 8/8 (requires peak search, not zero-lag).
- Resize 0.75 → 117%, 8/8. Resize 0.50 → 18%, 6/8. **Resize 0.25 → 0/8.**
- **WhatsApp-like, Instagram-like, screenshot-like: 0/8 each.**
- **0 false positives in 120 tests. Max negative PCE 38.0 against a bar of 50, no upward trend.**

**CAVEATS**
- The platform conditions are **simulations**, not actual platform round-trips. Real WhatsApp and
  Instagram pipelines may differ in resize target, chroma handling and metadata stripping. **Sending a
  photo through the real apps and re-testing is a ten-minute job and should be done before this is
  quoted to anyone.**
- n = 8 per condition. One phone, one sensor, one scene set.
- Geometry-changing conditions assume the verifier knows the claimed device and can transform its own
  reference. True for an enrolled-device product; not true for an arbitrary image.

**WHAT THIS SETTLES**
- The product is **capture-time**, and that is now measured rather than feared.
- The failure mode is **abstention, not accusation** — under every degradation tested.
- The verdict must be **three-valued**: authentic / altered-here / cannot determine.

**NEXT**
1. Real platform round-trips — actually send files through WhatsApp, Messenger, Instagram, Signal, and
   an email client, then re-run. Cheap and it replaces a simulation with a fact.
2. Whether *localisation* survives the survivable conditions — this tested identification only. A q85
   re-encode keeps 62% of the global fingerprint; whether it still localises a 0.4% edit is a separate
   and product-relevant question.

*Artifacts: `robustness.py`, `robustness_results.json`. Sources: internal — `FOLDING_PRNU` (resized set
at PCE 18), `FOLDING_PER_SENSOR` (the 0/72 that this extends to 0/120),
`FOLDING_PRNU_LOCALISATION`, `FOLDING_CLEAN_HISTORY` (abstention as the design goal),
`FOLDING_XPRIZE_ENTRY` (the product shape this bounds).*
