# Capture protocol v2

Everything here exists because something broke on it. What changed since v1 is at
the top; v1's rules still hold and are restated compactly at the bottom.

**If you only do one thing: shoot RAW.** Three separate measures are blocked on it.

---

## 1. RAW / DNG — the top priority ⭐ NEW

**~10 flat frames + ~5 edited pairs, saved as DNG.**

On the S23 Ultra: **Expert RAW** app, or Pro mode with RAW enabled. It saves a DNG
alongside the JPEG — **I need the DNG**, and the JPEG alongside it is a bonus
because it gives a matched processed/unprocessed pair.

Why this is first: the phone's noise reduction rewrites the sensor's noise before
the JPEG is ever written. The "imaginary camera" test — fit the photon transfer
curve from the image and ask whether any real sensor could produce it — came back
**inverted** on your JPEGs: gain positive on 0 of 12 real photos and 6 of 11 AI
images. The fitter is verified correct (recovers a known gain to 0.2% on synthetic
noise); the evidence simply isn't in a processed JPEG.

**Three measures unblock at once:**

| measure | what it needs RAW for |
|---|---|
| imaginary camera (photon transfer) | noise not yet rewritten by NR |
| chromatic aberration | lens correction not yet applied |
| grain-floor density | shot-noise floor not yet denoised |

All three would work without any enrolled device — which is the constraint that
currently limits everything to "a camera we have a reference for".

---

## 2. The other lenses on the same phone ⭐ NEW — and it replaces the second phone for now

**~10 flat frames from the ultrawide (0.6×) and ~10 from the telephoto (3× or 10×).**

Pick the lens explicitly in Pro mode so it can't switch on you. Note which is which.

This is the cheapest valuable thing on the list. The fingerprint is **per-sensor,
not per-model** — and that claim is completely untested. The S23 Ultra has four
separate sensors, so the ultrawide is effectively a different camera in the same
body. If the main-camera reference correctly **rejects** ultrawide frames, that
proves per-sensor specificity **without needing a second phone at all**.

It also gives the lens-shading test its material: shading profile is per-lens, so
flat frames from each lens are what that measure needs.

Still get a second phone when convenient — it is the cleanest version of the same
proof — but this is available today and answers most of it.

---

## 3. Fully regenerated frames ⭐ NEW — 10 of them

One turned up in your last batch by accident (`20260726_145954(1)` — the whole
frame replaced, with the "AI-generated content" watermark). It gave the most
decisive number in the project: **PCE 8838 → 5.7, a ratio of 0.001**, and it sits
**3.4σ** below what its own content predicts.

This is the **easiest** case, not the hardest — and it is the one the rest of the
field cannot do (published models collapse from 0.89 to 0.02 on regeneration). It
deserves proper n, and right now it is n = 1.

Make them however that one was made — whole-image "reimagine" / regenerate, any
tool. Save the original too. **Do not crop out the AI watermark**; it is a Channel A
fact and it is measured separately, never mixed into the pixel evidence.

---

## 4. More edited pairs — 15 to 20

The localisation result is **0.927 against a control of 0.273, 5 of 5**, sign
p = 0.062. Fifteen to twenty pairs takes that from suggestive to conclusive.

Composition, updated by what actually worked:

| | why |
|---|---|
| **small edits are now the priority** — several well under 1% | PRNU is **best** on the smallest ones: 0.917 and 0.985 on 0.36% and 0.38%, with controls at 0.046 and 0.048. This **inverts** the old guidance — every earlier measure got worse as edits shrank; this one gets better |
| **at least half on flat / low-texture scenes** | sky, walls, water, snow, fog. Texture buries the fingerprint: flat frames PCE 1460, textured 671, and on the old resized set 32.6 vs 1.0 |
| a few large edits (>20%) for the range | the large-edit controls are live (0.53, 0.59) and need more data to interpret |
| **both orientations held** | stored aspect ratio once separated the old classes at AUC 1.000 |
| **two different editing tools** | cross-toolchain generalisation is where published models lose ~60 F1 points |

---

## 5. Unchanged from v1, and still the rules that matter most

- **Transfer camera-original.** Cable, or "Keep Original" / "Actual Size". Not
  WhatsApp, not a Photos download. Every file in the first batch had been resized
  before it reached me and PRNU showed up on only 2 of 13; the camera-original
  batch went to 11 of 11.
- **One camera, one resolution mode per batch, written down.** PRNU is
  resolution-specific and per-sensor.
- **Save BOTH versions of every edited photo**, same app, same export path.
- **No enhance / upscale / crop / rotate after editing.** Generative upscaling
  wipes the traces on its own — measured elsewhere at 0.87 → 0.06.
- **Flat means texture-free**: clear sky, blank wall, defocused surface. Slightly
  bright, not blown out.
- Filters, colour grading and crops are **not** edits for this purpose — they
  change the whole frame and leave no local seam.

---

## 6. Don't bother

- More AI images for the class-separation benchmark. That set can't be fixed by
  collecting more of the same — content is perfectly correlated with class.
- More flat reference frames on the main camera. Eleven already gives 11/11 above
  the identification bar. More is nice, not needed.
- Textured scenes for the reference set specifically. They contribute little.

---

## Quick checklist

- [ ] **DNG/RAW**: ~10 flat + ~5 pairs, main camera
- [ ] **Ultrawide**: ~10 flat frames, lens noted
- [ ] **Telephoto**: ~10 flat frames, lens noted
- [ ] **Regenerated**: 10 whole-frame regenerations + their originals, watermark left intact
- [ ] **Pairs**: 15–20, several under 1%, half on flat scenes, both orientations, two tools
- [ ] Everything transferred camera-original, one resolution mode, noted
- [ ] Nothing enhanced, upscaled, cropped or rotated after editing

**If time is short, in this order: RAW → ultrawide/tele flats → regenerated → pairs.**
The first two answer questions nothing else can, and the first one unblocks three
measures at once.
