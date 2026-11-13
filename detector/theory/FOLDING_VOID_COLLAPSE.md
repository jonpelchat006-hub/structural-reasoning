# Void collapse — one strength, many pairs, and a rank-one test

*2026-07-28. Jonathan: "If we took a bunch of pairs, shouldn't they all reflect the strength of the
void point? So if we have a bunch of pairs that were different differences, but only one void with one
strength, then those points wouldn't make sense."*

**That is an over-determination argument and it is exact. It predicts a specific, checkable algebraic
form — and the prediction holds. It also refuted a claim I made in my own code while building it.**

---

## 1. The argument, made precise

Let each frame's noise residual be

    w_i = a_i · K + n_i

where `K` is the one shared thing (the sensor fingerprint — the void point), `a_i` is how strongly
frame *i* expresses it, and `n_i` is that frame's own independent noise. Then for any pair:

    corr(w_i, w_j)  ∝  a_i · a_j

A **product** of per-frame terms and nothing else. Which means:

> **One void with one strength ⟹ the pairwise correlation matrix is RANK ONE.**

That is Jonathan's "they should all reflect the strength of the void point," written as a matrix
property. And "those points wouldn't make sense" is literally what the spectrum reports: if the matrix
needs two directions, there are two causes.

It also answers the pressure question directly. **The outward force is felt across the whole space
because the model is a single outer product** — every entry in the matrix depends on the same set of
`a_i`. There is no way for one pair to feel the void differently from another without breaking the
rank.

## 2. Is a clean set rank one? Yes

8 frames, all from the main camera, full resolution:

| | |
|---|---|
| mean pairwise correlation | 0.0093 (sd 0.0068) |
| leading eigenvalue share | **82.4%** |
| **effective rank** | **1.42** |
| rank-1 fit residual | 0.0034 |

Pre-registration 1 holds. One sensor, one direction.

## 3. The collapse — and it needed a proper null

Contaminating with ultrawide frames (a physically different sensor in the same body) raises the rank:

| contamination | mean corr | effective rank |
|---|---|---|
| 0 of 8 | 0.0093 | 1.42 |
| 2 of 8 | 0.0065 | 1.58 |
| 3 of 8 | 0.0048 | **2.04** |
| 4 of 8 | 0.0040 | 1.91 |

A single comparison proves nothing, so: **40 random draws per arm**, 6 fixed main frames plus 2
swapped, against a **null arm that swaps in 2 *more main-camera frames*** — same sensor, different
frames.

| statistic | null (+2 main) | treatment (+2 ultrawide) | AUC |
|---|---|---|---|
| **effective rank** | 1.576 ± 0.206 | **2.023 ± 0.369** | **0.853** |
| rank-1 residual | 0.004 ± 0.001 | 0.005 ± 0.001 | 0.669 |
| gap (3rd/2nd weakest) | 1.292 ± 0.299 | 1.544 ± 1.366 | 0.568 |

**Effective rank separates at AUC 0.853.** The other two statistics — including the "gap" measure I
invented — are near-worthless, and the gap's enormous variance (±1.366) says it is noise.

And, operationally, ranking frames by their implied strength `a_i`:

- **contaminants identified: 48/80 = 60%**
- **same statistic on the null arm: 20/80 = 25%** — which is *exactly* the chance floor (2 of 8)

The null landing precisely at chance is the control working. The test finds real structure and finds
none where there is none.

## 4. The claim I made in my own code, and had to withdraw

`void_collapse.py` originally said this test *"would have caught"* the two mislabelled files that
poisoned the toolchain catalogue. That was an assertion, not a result, and there was a strong reason
to doubt it: `FOLDING_PRNU_LOCALISATION` established that an edited frame **retains** the sensor
fingerprint everywhere outside the edited region. Same silicon, same void point.

Tested rather than assumed — 30 draws, swapping in **edited frames from the same camera**:

| arm | effective rank | AUC vs null |
|---|---|---|
| null (+2 main) | 1.554 ± 0.157 | — |
| **+2 same-sensor EDITS** | 1.587 ± 0.311 | **0.510 — chance** |
| +2 ultrawide | 1.896 ± 0.341 | 0.803 |

**The overclaim is refuted.** This test detects a **wrong device**, not a **wrong history**. It would
not have caught the catalogue contamination, and the docstring now carries the correction rather than
the claim.

And note that the negative *confirms the theory rather than damaging it*: an edit does not change the
sensor, so there genuinely is still only one void, and the test correctly reports one. The model is
behaving exactly as the algebra says it should.

## 5. What it is actually good for

A **reference-free set-homogeneity test**. Given N frames asserted to come from one device, and no
reference fingerprint at all, it answers *"is this really one sensor?"* at AUC 0.853.

That fills a real hole: catalogue enrolment currently assumes ~20 supplied frames are all from one
device and **nothing checks it**. This checks the device question — while leaving the history question
to the container and pixel arms, which is the correct division of labour and now a measured one rather
than an assumed one.

It is also the first measure in this project that needs **neither an enrolled reference nor an
original**. It needs only *several frames claimed to share a source*, which is exactly the enrolment
situation.

## 6. Honest ledger

**MEASURED**
- Clean single-sensor set: effective rank **1.42**, leading eigenvalue **82.4%**. Rank-one prediction
  confirmed.
- Different-sensor contamination vs a same-sensor null, 40 draws each: effective rank AUC **0.853**.
- Contaminant identification 60% against a 25% chance floor, with the null arm sitting **exactly** at
  chance.
- Texture confound checked: ultrawide frames are *more* textured (2.639 vs 2.179) yet have **5× lower**
  implied strength, so flatness cannot explain the ranking.

**REFUTED**
- My own claim that this would catch same-sensor edits. AUC **0.510** — chance. Wrong device, not wrong
  history.
- The "gap" statistic (AUC 0.568) and the strength-disagreement measure add nothing over effective
  rank. Effective rank alone is the instrument.

**LIMITS**
- One phone, three sensors, 15 main + 10 ultrawide frames. A second *body* of the same model is the
  untested and harder case — two S23 Ultras should be two voids, and if the test cannot separate them
  it is reading sensor *type*, not sensor *identity*.
- Repeated draws share a small frame pool, so the 40 draws are not 40 independent experiments.
- The collapse is not monotone in contamination (1 contaminant *lowered* the rank to 1.26 in the
  single-run sweep). With 2 of 8 the direction is reliable; with 1 of 8 it is not.

**Code:** `void_collapse.py`, `void_collapse.json`, `void_draws.json`.
