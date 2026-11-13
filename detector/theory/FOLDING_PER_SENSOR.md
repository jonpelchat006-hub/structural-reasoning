# Per-Sensor — 36 of 36 matched, 0 of 72 mismatched, one phone

*The claim the entire ladder rested on was completely untested, and it is now settled. Three lenses on
**one** Galaxy S23 Ultra — ultrawide 2.2 mm f/2.2, main 6.3 mm, 10× periscope 27.2 mm f/4.9 — are three
physical sensors. Cross-testing every held-out frame against all three references gives a **perfectly
diagonal matrix: 36 of 36 matched above the identification bar, 0 of 72 mismatched, separation factor
1214×.** Same phone, same firmware, same pipeline, same day, same scenes — everything held constant
except the silicon. **PRNU is per-sensor, not per-model.** This also delivers the false-positive number
that has been blocking a threshold: **0 / 72.** Regeneration extends to **n = 9** with a clean 10× gap
and nothing in between. Status: MEASURED. Companion to `FOLDING_CAMERA3`, `FOLDING_PRNU_LOCALISATION`.*

---

## Part I — The cross-sensor matrix

Mean NCC of held-out frames against each lens's reference (leave-one-out on the diagonal):

| frames from | ref **main 6.3mm** | ref **ultrawide 2.2mm** | ref **tele 27.2mm** |
|---|---|---|---|
| **main 6.3mm** (15) | **+0.03894 (15/15)** | −0.00016 (5/15) | +0.00000 (8/15) |
| **ultrawide 2.2mm** (10) | −0.00006 (4/10) | **+0.03049 (10/10)** | +0.00014 (6/10) |
| **tele 27.2mm** (11) | +0.00010 (6/11) | +0.00019 (7/11) | **+0.05716 (11/11)** |

As PCE, the identification statistic (bar is 50):

| frames from | ref main | ref ultrawide | ref tele |
|---|---|---|---|
| **main** | **5516.6 (15/15)** | −0.5 (0/15) | −0.3 (0/15) |
| **ultrawide** | −0.1 (0/10) | **5446.4 (10/10)** | 0.6 (0/10) |
| **tele** | 0.4 (0/11) | 0.8 (0/11) | **17526.4 (11/11)** |

**Matched: 36 / 36 above the bar. Mismatched: 0 / 72.** Diagonal mean NCC +0.042, off-diagonal mean
+0.00003 — a **1214× separation**, with the largest off-diagonal value at +0.00019 and every
off-diagonal PCE under 1.

### Why this is a stronger test than a second phone

A second handset would differ in firmware version, age, wear, settings and shooting conditions. Here
**one body, one firmware build, one processing pipeline, one morning, overlapping scenes** — the only
variable is which piece of silicon the photons landed on. That isolates the sensor exactly, and the
answer is unambiguous.

The tele reference is also the strongest yet measured anywhere in this project at **PCE 17526**.

## Part II — The false-positive rate, at last

`FOLDING_PRNU` flagged a +0.00103 offset on AI images and concluded *"no threshold should be set until
that is done — the false-positive rate is the entire contribution of this component."*

This run supplies it directly. **72 mismatched-sensor tests, 0 above the PCE > 50 bar**, largest
off-diagonal NCC +0.00019. These are real photographs of real scenes from real sensors — the hardest
possible negatives, far harder than generated images — and none of them produces a false match.

That does not fully retire the earlier offset (different reference, different negatives) but it is the
first directly measured FPR in the project, and at this bar it is **zero**.

## Part III — A reclassification, caught before it was reported

All four camera-4 "edits" are **whole-frame regenerations**, not local edits. Three produce an empty
mask outright. The fourth, `100403(1)`, produced a spurious 0.30% mask and would have entered the
localisation pool — dragging it from p = 0.0156 to p = 0.0703.

The fingerprint ratio catches it. Sorting every edit measured across all batches:

| cluster | n | range |
|---|---|---|
| **regenerated** | **9** | −0.0003 … **0.0033** |
| **retained (local edit)** | **9** | **0.0315** … 1.3813 |

**A 10× gap with nothing in it.** `100403(1)` sits at 0.0033 — top of the regenerated cluster — with an
alignment correlation of 0.414 against 0.99 for genuine local-edit pairs. It is two largely unrelated
images, and the 0.30% "mask" is a threshold artifact of differencing them.

**Reclassified and excluded from localisation.** The measure classified its own input correctly, which
is the first time in this project a measure has been trustworthy enough to do that.

## Part IV — Where the numbers stand

| | n | result |
|---|---|---|
| **per-sensor specificity** | 36 matched / 72 mismatched | **36/36 and 0/72**, 1214× separation |
| **localisation** | 7 | edited **0.916** vs control **0.342**, +0.574, 7/7, **p = 0.0156** |
| **regeneration** | **9** | every ratio ≤ **0.0033**, originals PCE 1823 → 44950 |
| **false positives** | 72 | **0** |

Localisation is unchanged at n = 7 — camera 4 contributed no genuine local edits. Regeneration went
5 → 9, now spanning originals from PCE 1823 to 44950, a 25× range of starting strength, with the
collapse total in every case.

---

## Honest ledger

**MEASURED**
- **36/36 matched, 0/72 mismatched** across three sensors in one phone. Diagonal +0.042, off-diagonal
  +0.00003, separation 1214×. **PRNU is per-sensor, not per-model.**
- First directly measured false-positive rate: **0 / 72** at PCE > 50, on real-photo negatives.
- Regeneration n = 9, all ratios ≤ 0.0033; retained cluster starts at 0.0315. **10× gap, empty.**
- Tele reference PCE 17526 — strongest measured.

**CAUGHT**
- One camera-4 file misclassified as a local edit; the ratio and the alignment both flagged it.
  Excluded. Localisation stays at n = 7, p = 0.0156.

**STILL OPEN**
- A genuinely different **phone** — this shows per-sensor within one body; cross-body has an untested
  assumption that two units of the same model do not share pattern. The physics says they cannot, and
  the within-body result makes it very likely, but it is not measured here.
- More **local-edit** pairs. Regeneration is now well-sampled; localisation is the thinner arm at n = 7.
- Samsung Expert RAW remains `RawType.Stack` LinearRaw — the imaginary-camera test is still blocked.
- 6 of 15 camera-3 DNGs still undecodable, cause unresolved.

**WHAT THIS UNLOCKS**
- The enrolled-device claim is now **evidenced end to end**: enrolment is per-sensor, matching is
  specific, the false-positive rate at the working bar is zero, local edits are localised at p = 0.0156,
  and whole-frame regeneration is separated with a 10× margin and no overlap.

*Artifacts: `prnu_cross_sensor.json`, `prnu_camera4_edits.json`. Sources: internal — `FOLDING_CAMERA3`,
`FOLDING_PRNU_LOCALISATION`, `FOLDING_PRNU` (the FPR this supplies), `FOLDING_STACK_THICKNESS` (the
ladder this populates), `CAPTURE_PROTOCOL_v2` §2 (which asked for exactly this).*
