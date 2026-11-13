# PRNU — the fingerprint works, and the old files were the problem

*Rewritten 2026-07-26 after Jonathan supplied camera-original flat frames. **This supersedes the
earlier headline.** On the old resized files PRNU was marginal — mean PCE 18, above the identification
bar on 2 of 13. On 11 camera-original flat frames from the same phone it is **mean PCE 1460.3, above
the bar on 11 of 11, with rot90 and rot180 controls dead at +0.00001 and −0.00072.** An 81× improvement
from changing nothing but the input files. And the localisation demonstration stands: on the one old
image where the fingerprint was strong, the edited region reads **AUC 0.812 against a control of 0.403**.
Status: MEASURED. The device test is real; the localisation is still n = 1 and now cheap to settle.
Companion to `FOLDING_CLEAN_HISTORY`, `FOLDING_TWO_CHANNEL_LOOP`.*

---

## Part I — Why this test is not like the 34 that died

Every free measure tested here asked *"does this image look generated"* and every one turned out to be
answering *"what is this a picture of"*. PRNU asks something with no semantic content: **was this frame
read off this particular piece of silicon.** Photo-response non-uniformity is a manufacturing defect —
each photosite has a slightly different gain, fixed for the sensor's life, unique to the individual unit
rather than the model. **It cannot be a genre detector, because it is not a property of scenes.**

### The orientation trap, and it is the exact inverse of the earlier bug

`FOLDING_PHOTO_SET_AUTOPSY` found the pipeline scoring 15 of 22 photos sideways because EXIF orientation
was never applied, and the fix was to apply it everywhere. **For PRNU that fix is wrong.** The
fingerprint lives in *sensor* coordinates; a camera JPEG's stored buffer **is** the sensor readout and
the orientation tag is a display instruction. Originals must be read **as stored**, and edits whose
editor baked the rotation in must be rotated **back**. Semantic work needs display orientation; sensor
forensics needs sensor orientation. **Same file, two opposite correct answers.**

---

## Part II — The new frames, and the size of the difference

Jonathan supplied 25 frames from `more photos/camera 2`. The audit:

| | old "real photos" (22) | **new camera 2 (25)** |
|---|---|---|
| dimensions | 1414–2589 px, non-native | **4000×2252 / 4000×3000 — native** |
| `Software` tag | stripped 21/22 | **present 25/25** (`S918WVLS8FZF1`) |
| camera / focal | unknown | **one camera, 6.3 mm on all 25** |
| JPEG quality | 96–97 | 94–96 |
| orientations | 15/22 sideways | mixed (6, 1, 8, 3) — good |
| texture | ordinary scenes | **10 sky frames at 0.014–0.023** |

These are camera-original. That was the one rule in the protocol that mattered most and it was followed.

### Leave-one-out, with the rotated-self control

The control is a rotated copy of the same image — same sensor, same scene, same processing, only the
pixel-to-photosite alignment destroyed. No second camera needed.

| reference set | mean NCC | positive | **mean PCE** | **PCE > 50** | rot90 | rot180 |
|---|---|---|---|---|---|---|
| **NEW, flat frames only** (n=11) | **+0.04591** | **11/11** | **1460.3** | **11/11** | +0.00001 | −0.00072 |
| NEW, all native frames (n=22) | +0.02258 | 21/22 | 671.2 | 17/22 | +0.00018 | −0.00036 |
| OLD, 13 resized ordinary scenes | +0.00246 | 10/13 | 18.0 | 2/13 | −0.00014 | +0.00023 |

**PCE 18 → 1460. An 81× improvement from changing nothing but the input files.** PCE > 50 is the usual
identification bar; the flat camera-original set clears it on every single frame, and both rotation
controls sit at zero.

Flat frames beat textured ones 2× on NCC and 2.2× on PCE within the same batch, which is the masking
mechanism confirmed a second time — texture hides the fingerprint, and the protocol's request for flat
reference frames was the right call.

## Part III — The cross-batch test: the old files were the limit, not the method

A reference built from the **new** flat frames, tested against the **old** seam originals — same phone,
different batch, different firmware build, files already resized upstream:

| | mean NCC | positive | mean PCE | PCE > 50 |
|---|---|---|---|---|
| new reference vs old seam originals | +0.00241 | **10/13** | **20.6** | 2/13 |
| rot90 control | −0.00015 | — | — | — |

**Identical to what the old self-reference produced (18.0, 2/13).** So the earlier weak result was never
a reference-quality problem — **it was the files.** Downscaling averages photosites together and it
cannot be undone. Two useful conclusions:

1. **It is the same physical phone.** 10/13 positive cross-batch with a dead rotation control, across
   two firmware versions, is device attribution — weak, but consistent and in the right direction.
2. **The old files cannot be rescued.** No reference improvement will recover them. Anything PRNU-based
   needs camera-original input, which is now a hard requirement rather than a preference.

## Part IV — The localisation demonstration (unchanged, still n = 1)

`20250519_224651` — PCE 109 on the original and a 47.1% sky replacement. Full-resolution reference from
the other 12 originals, 256 px blocks, correlation inside the mask versus outside.

| | NCC inside | NCC outside | **AUC** |
|---|---|---|---|
| **EDITED** | **+0.00053** | +0.00605 | **0.812** |
| **CONTROL** (untouched original, same cells) | +0.01359 | +0.01207 | **0.403** |

**edit − control = +0.410.** Read the control row first: in the untouched original the fingerprint is
+0.0136 inside and +0.0121 outside — the same number, as it must be. In the edited version it collapses
to **zero inside** while the surroundings hold. **The generative fill wrote pixels that never passed
through the sensor.**

| test | edited | control | edit − control |
|---|---|---|---|
| vision committee | 0.538 | 0.478 | +0.060 |
| `spec_dev`, rebuilt masks | 0.582 | 0.428 | +0.154 |
| material baseline | 0.598 | 0.461 | +0.137 |
| **PRNU** | **0.812** | **0.403** | **+0.410** |

**2.7× the best previous result — and still n = 1**, on the largest edit in the set, on a file whose
fingerprint was 13× weaker than the new frames now deliver. With a PCE-1460 reference this test should
be far stronger, and it needs edited pairs of the new quality to run.

## Part V — The one thing that is not clean, named honestly

The AI-image control is **not** null: mean NCC **+0.00103, positive on 10 of 11**. That is 45× smaller
than the flat-frame signal (+0.04591) and does not threaten identification, but it is not zero and the
rotation controls *are* zero, so it needs a cause rather than a shrug.

Likely mechanism: `zero_mean` removes row and column means, which strips the CFA and JPEG-block
periodicities shared across a camera *model*. It does **not** remove **radial** structure — lens
shading and vignetting leave a centre-bright falloff that any natural-looking image weakly shares. The
standard fix is Fourier-domain Wiener filtering of the reference pattern, which is routine in PRNU work
and not yet implemented here.

**No PRNU threshold should be set until that is done**, because the false-positive rate is exactly what
this component is supposed to contribute.

### And a correction to an earlier claim

`FOLDING_PHOTO_SET_AUTOPSY` and `FOLDING_CLEAN_HISTORY` both stated **"zero maker notes across all 48
phone files"** and used it as evidence the capture record had been stripped. **That was wrong.** A raw
byte scan finds maker-note tag `0x927C` present in 5 of 5 sampled files — PIL's `get_ifd` simply does
not expose Samsung's maker note. **Maker-note absence via PIL is not evidence of stripping**, and the
inference built on it should be discarded. The *other* evidence for upstream processing — non-native
dimensions and stripped `Software` tags — stands, and the new batch confirms it by having both intact.

---

## Honest ledger

**MEASURED**
- **New camera-original flat frames: mean PCE 1460.3, above the identification bar 11/11**, rotation
  controls at +0.00001 / −0.00072. Old resized files: PCE 18.0, 2/13. **81×.**
- Flat beats textured within the same batch (PCE 1460 vs 671, NCC 0.046 vs 0.023) — masking mechanism
  confirmed twice.
- **Cross-batch attribution works and the old files are the limit:** new reference on old originals
  gives 20.6 / 2-of-13, identical to the old self-reference. Same phone, unrecoverable files.
- Localisation on `20250519_224651`: **AUC 0.812 vs control 0.403, +0.410.**

**CAVEATS, ALL LOAD-BEARING**
- Localisation is **n = 1**, largest edit in the set, weakest-era file.
- **The AI control is +0.00103, not 0.** Named cause (radial shading not removed by row/column
  zero-mean), known fix (Fourier Wiener filtering). No threshold until then.
- One camera assumed; the S23 Ultra has four sensors and PRNU is per-sensor. The new batch is uniform at
  6.3 mm, which is correct — keep it that way.
- 11 flat frames is enough to work but is a small reference by PRNU standards.

**CORRECTED**
- "Zero maker notes across 48 files" was a PIL parsing artifact, not a stripped record. Retracted.

**NEXT, in priority order**
1. **Edited pairs at the new file quality.** This is now the only thing between +0.410 at n=1 and a real
   result. Camera-original, native resolution, and *include flat-ish scenes* — sky, walls, water — since
   that is where the fingerprint is exposed. 10 pairs would settle it.
2. **Fourier-domain Wiener filtering of the reference**, then measure the false-positive rate properly.
   Cheap, and it is the number the product needs.
3. A few more flat frames if convenient — 20–30 makes a textbook reference, though 11 already works.

*Artifacts: `prnu.py`, `prnu_results.json`, `prnu_texture.json`, `prnu_localise.json`,
`prnu_camera2.json`, `camera2_sheet.png`, `CAPTURE_PROTOCOL.md`. Sources: internal —
`FOLDING_CLEAN_HISTORY` (the one-class reframe that pointed here), `FOLDING_TWO_CHANNEL_LOOP`
(regeneration erases seams but not fingerprints), `FOLDING_PHOTO_SET_AUTOPSY` (the orientation bug this
test inverts, and the maker-note claim now retracted).*
