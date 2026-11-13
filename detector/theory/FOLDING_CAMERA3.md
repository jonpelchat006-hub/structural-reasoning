# Camera 3 — localisation reaches significance, regeneration goes to n=5, and Samsung's RAW is not raw

*The camera-3 batch delivered three things and blocked one. **Localisation is now n = 7, edited 0.916
against a control of 0.342, 7 of 7, sign p = 0.0156** — it has crossed from suggestive to significant.
**Regeneration went from n = 1 to n = 5**, and every single one collapses to a fingerprint ratio ≤ 0.001
against originals reading 1823–12941. The new reference is the strongest yet: **PCE mean 5516, 15 of 15
above the identification bar.** And the RAW does not work — **Samsung Expert RAW writes `RawType.Stack`
LinearRaw**: multi-frame merged, already demosaiced, and denoised by roughly an order of magnitude
before the file is written. Also **6 of 15 DNGs will not decode.** Status: MEASURED.*

---

## Part I — The headline: localisation is now significant

Pooling camera 2 and camera 3, each edit against **its own untouched original** at the same blocks:

| pair | EDITED | CONTROL |
|---|---|---|
| c2 `145908(1)` (0.36%) | 0.917 | 0.046 |
| c2 `171934(1)` (0.38%) | 0.985 | 0.048 |
| c2 `171842(1)(1)` (2.66%) | 0.952 | 0.590 |
| c2 `150002(1)` (3.72%) | 0.862 | 0.531 |
| c2 `171926(1)` (5.08%) | 0.918 | 0.147 |
| **c3 `093509(1)` (0.32%)** | **0.998** | 0.583 |
| **c3 `093606(1)` (46.5%)** | 0.778 | 0.447 |

**n = 7 · EDITED 0.916 · CONTROL 0.342 · +0.574 · 7 of 7 · sign test two-sided p = 0.0156.**

It was n = 5 at p = 0.062. Two pairs took it across. The pattern also holds: the smallest edit in the
new batch (0.32%) gives the highest score in the whole set at **0.998**.

## Part II — Regeneration: n = 1 → n = 5, and the separation is total

Four of the seven camera-3 "edits" turned out to be **whole-frame regenerations** — visually confirmed,
completely different images carrying the AI-content watermark. That is the case I asked for, and it
arrived by accident again.

| | original PCE | regenerated PCE | ratio |
|---|---|---|---|
| c2 `145954(1)` | 8838.3 | 5.7 | 0.0010 |
| c3 `093438(1)` | 1822.8 | **−0.0** | −0.0000 |
| c3 `093459(1)` | 2774.9 | **−0.1** | −0.0000 |
| c3 `093515(1)` | 12941.1 | 0.6 | 0.0000 |
| c3 `093523(1)` | 6573.1 | 0.8 | 0.0001 |

**Five for five. Every ratio ≤ 0.001, against originals spanning 1823 to 12941 — a seven-fold range in
starting strength and it makes no difference.** Two of them read slightly *negative*: not merely absent,
but anti-correlated at the noise level.

There is no overlap and no threshold argument to have. This is the regime where published localisation
models collapse from 0.89 to 0.02, and it is the easiest case here.

A sixth, `093434(1)`, sits at ratio **0.031** — visually a near-total replacement rather than a clean
regeneration. It reads as "heavily replaced", which is the correct intermediate answer and the first
evidence that the ratio grades the middle of the ladder rather than only its ends.

## Part III — The new reference is the best yet

Leave-one-out over the 15 camera-3 originals:

| | NCC mean | positive | PCE mean | PCE > 50 |
|---|---|---|---|---|
| **camera 3** | **+0.0389** | **15/15** | **5516.6** | **15/15** |
| camera 2, flat frames | +0.0459 | 11/11 | 1460.3 | 11/11 |
| old resized set | +0.0025 | 10/13 | 18.0 | 2/13 |

Individual frames reach PCE 12941 and 19104. This is a strong reference built from ordinary scenes, not
just flat ones — which suggests the camera-original transfer matters more than scene flatness once the
files are native.

**One protocol problem:** camera 3 is **4000×1868**, camera 2 is **4000×2252**. Different capture aspect
ratio means different sensor crops, so the two batches need **separate references and cannot be pooled**.
Everything above uses each batch's own. Keep one aspect ratio per batch from here.

## Part IV — Samsung Expert RAW is not raw

This was the top ask and it does not deliver. What the DNGs actually contain:

| property | value | meaning |
|---|---|---|
| `raw_type` | **`RawType.Stack`** | a multi-frame **merge**, not a single exposure |
| shape | (1868, 4000, **4**) | LinearRaw — one value per colour **per pixel** |
| `raw_pattern` | **None** | no CFA mosaic — **demosaicing already applied** |
| noise sd | **0.088 – 0.277 DN** | a single-exposure readout should be order **1–3 DN** |

**It has been stacked, demosaiced and denoised inside the phone before the DNG is written.** The noise
has been reduced by roughly an order of magnitude, which is exactly the quantity the photon-transfer
test depends on.

Measured on the same scenes, JPEG versus DNG:

| | gain positive | median gain |
|---|---|---|
| JPEG | 2 / 9 | **−0.0013** |
| DNG | 7 / 9 | **+0.0002** |

**The sign inverts — the DNG escapes "anti-correlated" — but the magnitude is ~0.0002, which is no
intensity dependence at all.** So Expert RAW gets the test out of actively-misleading and not into
measurable. `FOLDING_IMAGINARY_CAMERA`'s diagnosis stands and sharpens: **the evidence is destroyed by
multi-frame fusion, not only by noise reduction, and Samsung's "RAW" happens after both.**

**What would actually work:** a DNG whose `raw_pattern` is a real 2×2 CFA and whose `raw_type` is not
`Stack` — i.e. a *single-exposure Bayer* capture. On Android that usually means a third-party app
requesting `SENSOR` / RAW_SENSOR directly rather than the OEM pipeline. Whether the S23 Ultra exposes it
is an open question worth ten minutes with a camera app that offers it.

## Part V — Six DNGs will not decode

`093459, 093515, 093523, 093533, 093625, 093654` all fail with *"data corrupted at N"* at varying
offsets (3.4 M to 13.4 M). **The staged byte counts match the source listing exactly**, so the transfer
was complete — these are not truncated in transit.

Two possibilities and they need separating on your side: the files are damaged as written, or they use a
Samsung compression variant LibRaw rejects. Nine of fifteen decode with identical code, which argues
per-file rather than systematic. **Worth checking whether those six open in Lightroom or the phone's own
gallery** — if they do, it is a LibRaw limitation; if they do not, the phone wrote bad files.

Note this cost nothing here: the JPEG side of all fifteen is intact and every result above comes from
the JPEGs.

---

## Honest ledger

**MEASURED**
- **Localisation n = 7: edited 0.916, control 0.342, +0.574, 7/7, sign p = 0.0156.** Crossed from
  suggestive to significant.
- **Regeneration n = 5: every ratio ≤ 0.001**, originals 1823–12941, two reading slightly negative.
  Total separation.
- One intermediate case at ratio 0.031 — first evidence the measure grades the middle of the ladder.
- New reference: **PCE mean 5516, 15/15 above the bar**, individual frames to 19104.

**BLOCKED**
- Expert RAW is `RawType.Stack` LinearRaw with noise reduced ~10×. Photon-transfer gain median +0.0002.
  Needs a **single-exposure Bayer** DNG, which the OEM app does not produce.

**DEFECTS**
- 6 of 15 DNGs undecodable; transfer verified complete, cause unresolved.
- camera 3 is 4000×1868 vs camera 2's 4000×2252 — separate references, cannot pool.

**STILL OPEN**
- The +0.00103 AI-control offset in the PRNU reference. Still blocks any absolute threshold.
- Second sensor / second phone — per-sensor vs per-model specificity remains completely untested. The
  ultrawide and telephoto frames would answer most of it for free.

**NEXT**
1. **Ultrawide and telephoto flats.** Now the single highest-value missing item — it is the only
   untested claim the whole ladder rests on.
2. A camera app that writes true Bayer RAW, if one exists for this phone. Ten minutes to find out.
3. Fourier-Wiener the reference, then measure the false-positive rate properly.
4. Keep one aspect ratio per batch.

*Artifacts: `prnu_camera3.json`, `camera3_regen.json`, `raw_vs_jpeg.json`, `camera3_edits.png`.
Sources: internal — `FOLDING_PRNU_LOCALISATION` (the n=5 result this extends),
`FOLDING_IMAGINARY_CAMERA` (the photon-transfer diagnosis this confirms),
`FOLDING_STACK_THICKNESS` (the ladder the 0.031 case populates), `CAPTURE_PROTOCOL_v2`.*
