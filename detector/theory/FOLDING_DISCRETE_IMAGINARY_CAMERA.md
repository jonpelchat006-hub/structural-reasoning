# The discrete imaginary camera — the closed-world toolchain test

*2026-07-28. Jonathan's argument: the imaginary camera should not be abandoned, it should be
**enumerated**. There are only so many cameras, encoders, editors and libraries; the set is finite and
knowable; so ask whether ANY member of the known world could have written this file such that every
part of the file agrees with that same member. This is the first enrollment-free capability in the
project that has survived its controls.*

**Headline: 1 false positive in 61 genuine captures, 19 of 20 known edits caught, zero pixel
evidence used. And a hard ceiling that must be stated in the same breath — it does not detect AI.**

---

## 1. Why this is not the measure that already failed twice

`FOLDING_IMAGINARY_CAMERA` asked a **continuous** question: fit the photon transfer curve and ask
what sensor could have made those photons. It failed *inverted* — gain positive on 0/12 real, 6/11 AI.
`FOLDING_BLUE_VOID_AND_PER_LENS` then hit the same wall from the optics side: three physically
different lenses were not separable by their shading (between/within ratio 0.30–0.46), because the ISP
corrects shading per-lens before writing.

Both failures have one shape: **the phone's software erases the physics before the file exists.**

The discrete question is different in kind. It does not ask what sensor made these photons. It asks
**what program wrote these bytes** — and that is answerable, because the writing program leaves an
exact, enumerable signature. These are not statistics that survive or die by degree. They are
integers. A file either has this camera's metadata layout or it does not.

`shading_observer.py` had already written the rule down and then went the wrong way with it:
*"structural invariants survive processing where statistical ones do not."* Encoder identity is the
most structural thing in a file.

## 2. The finding that reorganises everything: values are adaptive, layout is fixed

First run keyed the catalogue on the quantisation-table hash, assuming a phone writes one table.

> **39 distinct quantisation signatures across 61 camera-original frames.** Samsung quantises
> adaptively per image. "Table not in catalogue" is the *normal* case for a genuine file.

But across those same 61 frames there were only **2 metadata layouts with real support** (48 + 11),
against 16 distinct layouts in 21 web photographs. So within one writer:

| | camera-original, n=61 | web photographs, n=21 |
|---|---|---|
| distinct QT signatures | **39** | 15 |
| distinct structural layouts | **2** | 16 |

**The values are adaptive; the layout is fixed.** Any catalogue must be built on structure — marker
sequence, which IFDs exist, byte order, tag counts, thumbnail presence — and never on quantised
values. This is the same distinction that has held everywhere else in the project.

## 3. What the editor actually changes

Measured on matched original/edit pairs rather than assumed:

| | camera original | camera-app edit |
|---|---|---|
| IFD0 tag count | 12 | **15** |
| ExifIFD tag count | 30 | **31** (+0x9208 LightSource) |
| thumbnail IFD | present, 18.6 KB | **absent** |
| byte order | **II** (little-endian) | **MM** (big-endian) |
| MakerNote | absent (this camera writes none) | absent |
| Make / Model / Software | unchanged | **unchanged** |

The editor rebuilds the metadata block from scratch and does not put the thumbnail back. Note that
`Make`, `Model` and `Software` are **identical** on both sides — the fields anyone would look at first
are exactly the ones that carry no information. The evidence is in the layout, not the content of the
tags.

## 4. Results

Four outcomes, and **only one of them is an accusation**. The asymmetry is deliberate and is what
protects the false-positive rate.

| class | meaning |
|---|---|
| `coherent-capture` | claims a device, carries a layout that device's camera app is known to write |
| `rewritten-after-capture` | claims a device, but the metadata block is not one that device writes |
| `unknown-device` | claims a device with no catalogue entry — a gap, not a finding |
| `no-provenance` | asserts no device at all. **Not a fake claim.** Most of the web is here |

| set | n | coherent | rewritten | no-provenance |
|---|---|---|---|---|
| camera 2 originals | 25 | 24 | 1 | — |
| camera 3 originals | 15 | 15 | 0 | — |
| camera 4 originals | 21 | 21 | 0 | — |
| known edits | 20 | 1 | **19** | — |
| `altered` set (13 pairs) | 26 | 13 | **13** | — |
| web photographs | 32 | — | 2 *(unknown-device)* | **30** |
| AI images | 2 | — | — | **2** |

**False positives: 2 of 61 as counted mechanically, and both are diagnosable.**

- `20260726_145915.jpg` sits in the originals folder but carries the editor's exact layout
  (MM, no thumbnail, 15/31 tags) — and a same-named file exists in the edits folder. It is a
  **mislabelled edit**, i.e. a correct flag counted in the wrong column.
- `20260726_171934.jpg` is a **genuine false positive**: a real capture with GPS enabled, MM byte
  order, 13/34 tags. It is a capture mode the catalogue saw only once. The cause is an incomplete
  catalogue, not a broken rule — and it is fixable by enrolling each capture mode once.

**True rate: 1 / 61, cause known.** Recall on rewrites: **19–20 / 20**.

## 5. The ceiling — say this before anyone else does

**Web photographs and AI images land in the same bucket.** 30/32 real web photos and 2/2 AI images are
`no-provenance`. That is *correct behaviour*, and it is the limit of the method.

This separates **files that carry a history** from **files that do not**. It says nothing about whether
a history-less file is real. A downloaded photograph and a generated image are indistinguishable here
because they are indistinguishable *in fact* at the container level — the download stripped the
history, and the generator never had one.

So the honest product sentence is **"this file is not a coherent capture from the device it claims"**,
never "this file is AI". Which is precisely the `FOLDING_CLEAN_HISTORY` framing, now measured.

**It is also Channel A, and Channel A is forgeable.** `exiftool` transplants a metadata block in one
command. The forger's task is harder than it looks — they must reproduce the layout *including a
correctly sized thumbnail IFD and the right byte order*, and the layout is per-model — but it is not
hard. This can never be the whole verdict. What it is:

- high precision, low recall, near-zero cost (no pixels read, milliseconds per file)
- effective against the overwhelming majority of real fakes, which are **not adversarial**
- **enrollment-free** in the way that matters commercially: it needs a **per-model catalogue built
  once and shared**, not a per-user reference built from the customer's own device. That is a
  completely different product shape from PRNU
- it composes with the ratchet — a contradiction is exactly the kind of single finding that should
  latch a verdict

## 6. Two bugs, recorded because they are the same bug twice

**MakerNote detection has now broken this project three times, in three directions.** PIL silently
drops tag 0x927C, which produced the retracted "zero maker notes across 48 files". The replacement
scanned raw bytes for `\x92\x7c` across 200 KB of JPEG entropy data — that pattern occurs by chance
~95% of the time, so the detector returned True on essentially every file **including files with no
EXIF block at all**, and run 1 reported 21/21 web photos and 2/2 AI images as contradictions reading
"EXIF asserts None None". Those flags were noise and are withdrawn. Fixed by `exif_raw.py`, a real
TIFF walker. Then a *third* form: the rule "claims a camera but no MakerNote" fired on genuine
captures, because **this camera writes no MakerNote at all** — a guess about cameras in general applied
to a camera it does not describe. Whether a MakerNote is expected is a **per-model fact** and belongs
in the catalogue.

The general lesson, again: *a signal read from the wrong place looks exactly like a signal.*

One more, worth keeping: the catalogue is learned from files labelled by filename convention, and two
mislabelled edits leaked in and taught it the **editor's** signature — which it would then have
excused. Fixed with a minimum-support rule (a layout must appear ≥3 times to be admitted), which
removes contamination without hand-picking. **A catalogue that learns from unaudited data will learn
to forgive the thing you are hunting.**

## 7. Where this goes — the layers Jonathan named

The proposal has three zoom levels. Only the first is now measured.

1. **Imaginary camera (done).** Which device layouts exist, and does this file match one?
2. **Imaginary programs and libraries (next, and cheap).** The same catalogue for editors, converters
   and platforms. Every hop leaves a layout. `FOLDING_STACK_THICKNESS` is the theory of this and it now
   has an instrument. The testable claim: **the layout identifies not just *that* a file was rewritten
   but *by what*** — and a chain of hops should be readable in order.
3. **Plausible human action (untested, and the interesting one).** "Could a person realistically do the
   edits that appear." For the geometric-art case Jonathan raises, this is sharper than it sounds: a
   vector or layer-based tool produces shapes whose edges are **exactly** axis-consistent, whose
   anti-aliasing follows one renderer's rule, and whose count is small. A diffusion decoder produces
   shapes that are *approximately* geometric. **Consistency of construction is measurable and
   content-independent** — the same property that makes the coherence test safe. This deserves its own
   pre-registration.

The general principle worth extracting: **all three levels are consistency tests between two things
inside one file.** That is why they escape the confound that killed 40 of 42 features — the control is
the file itself, exactly as in the within-image seam test.

**Code:** `exif_raw.py`, `toolchain.py`, `toolchain2.py`, `toolchain3.py`, `toolchain3.json`.
