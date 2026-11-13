# The arms — and the one that was bracing nothing

*2026-07-28. Jonathan: "Are there arms coming from the observers that verify different things? Would
these arms be supporting them too? One or more arms could come from each observer and it would go into
the window space and fix both in place?"*

**The structure is right and it is already what `verdict.py` emits. But "fix both in place" is a claim
that can be false, and measuring it found a live bug in the engine I shipped one turn ago: two arms I
was reporting separately are the same event, and multiplying them would have inflated an edited file's
likelihood ratio from 20:1 to as much as 400:1.**

---

## 1. The framework already forbids what my combiner allowed

`FOLDING_D_AND_DIRECTIONS`: *"A/B = the two domains, C = their mix; **D = the cofactor** — a chemically
distinct material dropped into the pocket, not made of A or B."* An observer is a D, and **D is
chemically distinct by definition** — so a correlated observer is not a new D, it is more of the same
material. `FOLDING_OBSERVERS_AS_D` then measured the consequence: GPT and Gemini agree at **r = 0.91**,
barely more independent than one model run twice (0.94). Vendor diversity is not observer
independence.

The same rule applies one level down, to arms. **Two arms only fix each other if they are
independent.** If they always fire together they are one brace with two labels.

## 2. Measured — 136 files, 14 arms, binary fire matrix

### The redundancy that was live in the product

| pair | r | conditional value |
|---|---|---|
| `thumbnail_missing` ↔ `byte_order_wrong` | **0.98** | **zero** |

- P(edit) = 0.226
- P(edit \| thumbnail missing) = **0.914** (n = 35)
- P(edit \| byte order wrong) = 0.889 (n = 36)
- P(edit \| **both**) = **0.914** — the second arm moves the posterior by **exactly 0.000**

They disagree on **1 file of 36** — and that one file is `20260726_171934.jpg`, the single genuine
false positive already identified in `FOLDING_DISCRETE_IMAGINARY_CAMERA` (a real capture with GPS on
and MM byte order, but *with* its thumbnail). So the disagreement is not extra information; it is the
weaker arm being wrong.

`verdict.py` was printing these as two findings. They are now merged into one, flagged in the output as
*"[one finding: these two always co-occur]"*.

### Two "perfect redundancies" that were artifacts

The first pass reported `is_png == has_alpha` and `ifd0_count_wrong == exif_count_wrong` at r = 1.00.
Both fired on exactly **one file**. Perfect correlation on a single observation is not evidence of
anything, and a minimum-support check caught it. Recorded because it is the same error class as the
n=1 catalogue contamination and the n=1 MakerNote scan — **this project's characteristic failure is
believing a statistic computed on one observation.**

### The structural answer: the container arms partition, they do not brace

| | files |
|---|---|
| rewrite family only (`thumbnail_missing`, `byte_order_wrong`) | **36** |
| no-provenance family only (`no_exif`, `no_device_claim`, `progressive`, `adobe_app14`, `photoshop_app13`) | **33** |
| **both** | **0** |

**They never co-fire.** A file either still carries a device claim to be checked, or it does not. So
*within the container tier*, "fix both in place" is **false** — the arms are alternatives, not
supports. That is a fact about the tier, not a flaw in Jonathan's structure.

### Where bracing is real

Inside the no-provenance family the arms *do* co-fire and are only partly correlated (`adobe_app14` ↔
`photoshop_app13` r = 0.75; `no_device_claim` ↔ `photoshop_app13` r = 0.64):

- 20 files fire **2** of that family, 7 fire **3 or more**
- **P(genuine capture \| ≥2 of the family) = 0.000**, n = 27

That is a genuine three-arm brace on "professional editing pipeline", and it is the only place in the
container tier where the arms support rather than substitute for each other.

## 3. The correct combiner

> **LR_total = product over independent GROUPS of ( strongest arm within that group )**

This is Jonathan's structure stated exactly: one or more arms per observer; arms that verify
**different** things brace each other; arms that verify the **same** thing are not counted twice.

The old combiner took the plain max — safe, but it discards bracing. A naive product over all 13 live
arms would have inflated by up to **400×**. **Overstating a forensic likelihood ratio is the worst
failure this product could have**, worse than missing a fake, because it is the failure that survives
into a courtroom.

Both are now wrong in the code's favour: grouped product, capped at 3× the strongest single arm, so no
combination can outrun the sample its strongest member rests on.

## 4. The architectural consequence — where the next arm must come from

Bracing requires arms that **can co-fire** and are **only partly correlated**. Within one observer,
arms tend to be either redundant (r = 0.98) or mutually exclusive (never co-fire). Neither braces.

So real bracing requires arms of **different type**, and the corpus has already measured that this is
where independence lives:

| pair | correlation |
|---|---|
| same model, two samples | 0.94 |
| gpt ↔ gemini (two vendors) | 0.91 |
| claude ↔ grok (most independent models) | 0.70 |
| **semantic reader ↔ spectral reader** | **0.14** |

Observer *type* buys roughly **five times** the independence of observer *vendor*. The window-space
picture is therefore right in a specific and testable way: **arms from the container observer, the
pixel observer and the semantic observer are the ones that can genuinely fix each other in place**, and
arms from within a single observer mostly cannot.

That also settles a product question. The second paid observer, when it is added, must ask a
**different kind of question** — not the same question of a different company's model.

## 5. What is still unmeasured

The cross-type bracing claim is **inferred from the corpus's observer-correlation matrix, not measured
on arms.** To measure it properly the pixel and semantic observers must emit arms in the same evidence
format as the container observer, and then the same co-fire matrix must be run across all three types.
That is the next experiment, and it is cheap once the semantic reader is wired in.

Until then: the container tier reports a max, honestly labelled, and the bracing rule is in place
waiting for arms that can actually exercise it.

**Code:** `arms.py`, `arms.json`, `verdict.py` (combiner + merged finding).
