# Phone capture protocol

Everything here exists because something in this project broke on it. Each rule
has the failure it prevents attached, so nothing is cargo cult.

---

## 0. The one rule that matters more than the rest

**Transfer camera-original. USB cable, or "Keep Original" / "Actual Size".**

Not WhatsApp. Not Messenger. Not a Google Photos download. Not AirDrop-equivalent
"optimised" transfer.

Why: every one of the 22 photos we have been calling "real camera originals" had
been resized and recompressed before it reached us. Non-native dimensions
(1596×1197, 1911×1434 — the S23 Ultra shoots nothing like those), `Software` tag
stripped on 21 of 22, **zero maker notes across all 48 files**, and every file
sitting near 1 MB regardless of pixel count. Downscaling averages photosites
together and is the classic sensor-fingerprint killer — it is the single most
likely reason PRNU showed up on only 2 of 13 files.

If a batch comes through resized, it is not a smaller version of the right data.
It is the wrong data.

---

## 1. PRNU reference set — the new thing, and the cheapest big win

**20–30 flat frames from ONE named camera.**

- **Flat means texture-free**: clear blue sky, a blank painted wall, a defocused
  surface, an evenly lit sheet of paper. No detail anywhere in frame.
- Slightly bright but **not blown out** — aim mid-grey to light. Avoid pure white.
- **Same camera every time.** The S23 Ultra has four sensors and PRNU is
  *per-sensor*. An ultrawide frame will not match a main-camera reference. Pick
  the **main (1×) camera**, do not zoom, do not let it switch. Note which one.
- Default photo mode. No portrait mode, no night mode, no HDR bracketing if it can
  be turned off — those fuse multiple frames and blur the fingerprint.
- Highest resolution the camera offers. If there is a 12 MP / 50 MP / 200 MP
  choice, **pick one and use it for everything**, including the edited pairs
  below. PRNU is resolution-specific.

Why it matters: this is the standard way the reference pattern is estimated and we
have never had one. It would replace a marginal 13-image reference built from
ordinary scenes with a strong one, and it costs ten minutes of pointing the phone
at the sky.

**This set needs no editing at all.** It is pure reference material.

---

## 2. Edited pairs — the standing bottleneck

**Target 50 pairs. Save BOTH versions of every photo.**

The original and the edited file, from the same export path. Diffing them gives a
pixel-exact mask with no hand annotation. This is the single most important
instruction and it has not changed.

### What counts as an edit

Localised **content** changes:

- generative fill / magic eraser / object removal
- adding an object or person that was not there
- sky replacement
- moving or duplicating something in frame

### What does not count

Global changes leave no seam to find:

- filters, colour grading, exposure, contrast, saturation
- crops, rotations, straightening
- whole-image upscale, "enhance", or denoise

**Do not hit "enhance" after editing.** Generative super-resolution applied as a
last step wipes the traces on its own — measured, CAT-Net 0.87 → 0.06. An innocent
final tap is a forensic wipe.

### Composition of the set

| | why |
|---|---|
| **at least 10 pairs on FLAT / low-texture scenes** | sky, walls, water, fog, snow. This is where the fingerprint is exposed — mean PCE 32.6 on flat scenes vs 1.0 on textured. **New, and the highest-value addition.** |
| **several very small edits** (well under 1% of frame) | `spec_dev` only works below ~1%; that domain needs more than two data points |
| **a spread of sizes** up to large | gives a detection floor rather than one accuracy number |
| **both portrait and landscape held** | so frame shape cannot correlate with anything. Stored aspect ratio separated our old classes at AUC **1.000** |
| **two different editing tools** | e.g. Samsung's built-in generative edit and Google Photos Magic Editor. Cross-toolchain generalisation is where the field's models lose ~60 F1 points |

### Keep the export path identical

Same app, same format, same quality for original and edit, so the pair differs
**only** in the edited region.

**If the editor offers PNG, use it.** JPEG truncates the high-frequency tail, which
is what blocked the optics and balance-law measures.

**Do not rotate, crop or straighten between saving the two versions.** 7 of our 13
pairs came back with the original stored 4000×2252 and the edit stored 2252×4000
because the editor baked the rotation in. It is recoverable, but it silently
corrupted the ground-truth masks for over half the set.

---

## 3. Nice to have, if it is easy

- **A few RAW / DNG captures.** The only format where chromatic aberration and the
  blur↔spectrum balance law are testable at all — every JPEG pipeline has already
  applied lens correction and stripped what those measures read.
- **A second phone**, any model. One device means "real" and "this phone" are the
  same category, and nothing can tell them apart.
- **A note of which camera and which resolution mode** was used, per batch. Thirty
  seconds now, saves an unanswerable question later.

---

## 4. What NOT to bother with

- Collecting more AI-generated images for the class-separation benchmark. That set
  is unusable for reasons collection cannot fix — content is perfectly correlated
  with class (12 of 17 AI images are studio beauty close-ups, none of the real ones
  are). Fixing it needs *matched content on both sides*, which is a different and
  larger job. The edited pairs are worth more per photo and are confound-free by
  construction.
- Anything already on a computer, downloaded, or screenshotted.

---

## 5. Quick self-check before sending a batch

- [ ] Transferred by cable or "keep original" — dimensions look native
- [ ] One named camera, one resolution mode, noted
- [ ] PRNU set: 20–30 flat frames, no detail, not blown out, unedited
- [ ] Pairs: both versions saved, same export path
- [ ] At least 10 pairs on flat scenes; several edits under 1%
- [ ] Both orientations present
- [ ] Two editing tools
- [ ] No enhance / upscale / crop / rotate after editing
