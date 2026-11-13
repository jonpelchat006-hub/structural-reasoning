# The window is two windows — coverage, holes, and a trivial separator caught in the act

*2026-07-28. Jonathan: "Is it like each arm takes up space going through the window and we want to
cover the whole window, but each arm can't cover the same spot or touch? And if we can get enough
coverage we can form an opinion?"*

**The picture is computable and it splits the project's central question in two. It also caught a
trivial separator forming in the new tier — the same failure that produced the retired 0.952.**

---

## 1. Two kinds of coverage, and they were being conflated

| | question | instrument |
|---|---|---|
| **direction coverage** | do the arms span the space of evidence *types*? | effective rank |
| **case coverage** | do the arms reach the *files* that need a verdict? | fraction with a finding |

"Each arm can't cover the same spot" is direction coverage. "Cover the whole window" is case coverage.
Both are necessary and they fail differently: perfect directions with poor cases is a beautiful basis
that never fires; perfect cases with poor directions is many arms all saying one thing.

## 2. Direction coverage — 13 arms, 7.07 directions

| | |
|---|---|
| arms that ever fire | **13** of 14 |
| **effective rank** | **7.07** |
| window utilisation | **54%** |

The variance is genuinely spread (PC1 only 21.9%, six directions needed for 86%), which is a far
healthier frame than the free pixel stack — `FOLDING_OBSERVER_FRAME` measured **2.82 effective
dimensions from 23 features**, a 12% utilisation where PC1 alone carried 57%.

So the container observer is **4.5× more efficiently packed** than the pixel observer. But 54% still
means nearly half the arms are sharing a spot, and `FOLDING_ARMS_AND_BRACING` already identified the
worst offender: `thumbnail_missing` ↔ `byte_order_wrong` at r = 0.98 with zero conditional value.

## 3. Case coverage — and a conceptual error I made first

My first pass counted **72 genuine captures as "uncovered"** because no arm fires on them, giving a
54.8% hole. That is wrong, and wrong conceptually rather than in code.

> **An arm firing is not the only way to cover a spot.** For a file that claims a device in the
> catalogue, *silence is the finding*: every arm that could have fired did not, and the claim
> survives. That is a verified negative, and a strong one — 0/61 false positives.

Silence only means "uncovered" when there was nothing to test. Three states, not two:

| state | meaning | n |
|---|---|---|
| **covered-positive** | an arm fired; the claim is contradicted | 68 |
| **covered-negative** | a claim existed, was testable, no arm fired | 73 |
| **UNCOVERED** | nothing to bite on | **5** |

**True coverage: 96.6%.** The hole is 5 files, all web photographs with no device claim at all.

## 4. The finding that reorganises it — the window is two windows

96.6% coverage sounds like the job is done. It is not, because **every arm goes through the same
window.**

| | web photographs (n=21) | AI images (n=17) |
|---|---|---|
| `no_exif` + `progressive` | 10 | 0 |
| `adobe_app14` + `photoshop_app13` + `no_device_claim` | 5 | 0 |
| `photoshop_app13` / `progressive` variants | 3 | 0 |
| `is_png` alone | 0 | **15** |

The arms that fire on real web photographs — progressive, Adobe, Photoshop — all report **what pipeline
wrote the file**. They say nothing about who authored the content. An AI image posted to a website and
re-downloaded would fire *exactly the same arms*.

> **There is a history window and an authorship window. The container tier covers the history window
> at 96.6% and the authorship window at 0%.** Not weakly — structurally. It is measuring the writer,
> and the writer of a downloaded AI image is the same software as the writer of a downloaded
> photograph.

That is the precise, mechanical statement of the ceiling `FOLDING_DISCRETE_IMAGINARY_CAMERA` measured
empirically (30/32 real and 2/2 AI in one bucket). And it answers Jonathan's question directly: **yes,
enough coverage forms an opinion — but only about the window you are actually covering.**

## 5. ⚠️ A trivial separator, caught forming

**`is_png` fires on 15 of 17 AI images and 0 of 21 web photographs.** Taken at face value that is a
near-perfect free detector.

**It is a collection artifact and it must be quarantined now.** The AI images are PNG because that is
how Midjourney and Grok hand you a download. A photograph exported as PNG fires the identical arm. The
arm measures *how this corpus was assembled*, not what the images are.

This is the project's signature failure returning in a new tier. `FOLDING_PHOTO_SET_AUTOPSY` retired
the 0.952 headline for exactly this: **stored aspect ratio separated the classes at AUC 1.000 and bits
per pixel at 0.008** — two numbers readable from `ls -l`. `trivial_audit()` was written to catch it
before any observer runs, and it needs to run on the arm set too.

**Action:** `is_png` and `format_mismatch` must be reported as *history* evidence ("this is an export,
not a capture") and must never be allowed to contribute to an authorship claim. `verdict.py` already
phrases them that way; the risk is a future scorer learning them as AI-detectors.

## 6. Does more coverage sharpen the opinion?

| decisive arms on file | n | P(edit) |
|---|---|---|
| 0 | 80 | 0.013 |
| 1 | 22 | 0.000 |
| 2 | 39 | 0.795 |
| 3 | 4 | 0.000 |
| 4 | 1 | 1.000 |

The posterior saturates at one arm. Going from one to two does not sharpen it, because in this tier
the second arm is either the same event (r = 0.98) or fires on a different file entirely (the two arm
families co-occur on **0 of 146** files).

**So "enough coverage lets us form an opinion" is true, and the threshold here is ONE** — not because
one arm is strong, but because the extra arms are not buying new window.

## 7. Where the next arm must go — derived, not chosen

Adding another container arm cannot help. The tier is at 54% utilisation with a structural blind spot,
and the blind spot is a **tie**, not a weakness. A tie cannot be broken by looking harder in the same
place.

To cover the authorship window an arm must fire on files with no provenance — which means it must read
**pixels**. And the corpus already measured which direction is furthest from what we have:

| pair | correlation |
|---|---|
| same model, two samples | 0.94 |
| two vendors (gpt ↔ gemini) | 0.91 |
| most independent models (claude ↔ grok) | 0.70 |
| **semantic ↔ spectral (different type)** | **0.14** |

Observer *type* buys ~5× the independence of observer *vendor*. **"Come in at a different angle" is a
measurable quantity, not a design preference** — and it is the criterion for the second paid observer.

## 8. Honest ledger

**MEASURED**
- Container arm set: 13 live arms, effective rank **7.07**, 54% utilisation — 4.5× better packed than
  the pixel stack's 2.82/23.
- True case coverage **96.6%**; hole = 5 files, all no-device-claim.
- The two arm families co-occur on **0 of 146** files — they partition, not brace.
- Posterior saturates at one decisive arm.

**CORRECTED**
- First coverage pass called 72 genuine captures "uncovered" and reported a 54.8% hole. Silence against
  a testable claim is a **verified negative**, not a gap. Corrected to 96.6%.

**FLAGGED**
- `is_png` separates AI from web real at 15/17 vs 0/21 and is a **collection artifact**. Quarantined to
  history evidence. `trivial_audit()` must be extended to the arm set.

**UNMEASURED**
- Whether pixel and semantic arms actually brace the container arms. Requires those observers to emit
  arms in the same format, then the same co-fire matrix across types.
- n = 17 AI images, one collection method. The authorship-window claim rests on mechanism, not on this
  sample.

**Code:** `coverage.py`, `coverage.json`, `arms.py`.
