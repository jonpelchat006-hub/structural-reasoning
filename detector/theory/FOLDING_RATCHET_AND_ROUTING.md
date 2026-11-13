# The Ratchet — the rule is right, the instrument never rings the bell

*Jonathan: "once one spot reaches that fake bar i call the whole thing fake ... its always going to be
fake from there," and "arent they kind of like tools for specific things to check?" Both were tested.
**On the free measures the max rule fails outright** — a maximum has no cancellation, so it amplifies
noise, and the control arm rises with it. **On the committee the rule is vindicated in the one way that
matters: at every bar tested it condemns 0 of 33 real photographs. Precision 5/5. Recall 20%.** The
committee almost never puts a cell below 50 — 33/33 real images and 20/25 AI images have zero — so the
ratchet is correct and starved. That makes it a **gate in front of the mean, not a replacement for it**,
and it makes the prompt, not the aggregation, the thing to fix. Status: MEASURED, $0, on cached scores.
Companion to `FOLDING_SEAM_REBUILD_AND_DENSITY`, `FOLDING_PHOTO_SET_AUTOPSY`.*

---

## Part I — Why the question is worth asking at all

**Every combination in this project has been an average.** The committee averages observers. The free
stack averages features. Per-image scores average cells. `FOLDING_DEBATE_AND_SEAM_DATA` even found that
plain averaging beat four attempts to improve on it, which quietly entrenched the operator.

Averaging is correct when every element is a noisy estimate of **one global quantity**. It is wrong when
the evidence is **local and sparse** — because a single decisive cell gets divided by the cell count.

That distinction is not academic here. `FOLDING_SEAM_REBUILD_AND_DENSITY` found `spec_dev` localises
edits of 0.5–1% of frame (0.97, 0.88) and nothing above 4%. **A 0.5% edit is one cell out of 36.** Under
a mean, one screaming cell moves the image score by 1/36 of its magnitude. Under a max, it decides the
verdict. So the image-level result that came back "not significant" may have been measured with the
wrong operator — and that is testable.

## Part II — On the free measures, the ratchet fails

13 rebuilt seam pairs, paired design: each edited image against **its own untouched original**, so
camera, scene, lighting and compression are identical and no threshold calibration is needed. Four
aggregation rules × three combination rules over seven per-cell measures.

| combination | rule | edited wins | sign p | mean edit | mean orig |
|---|---|---|---|---|---|
| mean-over-tools | mean | 7/13 | 1.000 | 1.95 | 2.12 |
| mean-over-tools | top3 | 9/13 | 0.267 | 5.79 | 7.59 |
| max-over-tools | max | **6/13** | 1.000 | 25.39 | **54.56** |
| max-over-tools | count@3 | 4/13 | 0.267 | 18.00 | 18.23 |
| `spec_dev` alone | top3 | 9/13 | 0.267 | 4.57 | 4.13 |

**Nothing reaches significance, and the max rule is the worst of them.** Look at the last column of the
`max-over-tools | max` row: the *untouched originals* score **54.56** against the edited images' 25.39.
The rule fires harder on clean photographs than on manipulated ones.

That is pre-registered risk 4, confirmed exactly as written: *"max over 36 cells × 7 measures is the
maximum of ~250 noisy draws, and a maximum has no cancellation — noise only ever pushes it up."*

### The localisation form fails the same way

Does the single most anomalous cell land inside the true mask?

| | |
|---|---|
| argmax lands in the edited region | **2/13 = 0.15** |
| chance, from the masks themselves | **0.24** |
| control — same operator on the untouched originals | **2/13 = 0.15** |
| lift over chance | **−0.08** (control lift −0.08, identical) |

**Below chance, and the control is identical.** Worse, the only two "hits" are the 47% and 32% edits,
where chance is already 0.58 and 0.50 — so they are not hits, they are what chance predicts.

**This is not a verdict on the idea. It is a verdict on the instruments.** The ratchet requires that
when a tool fires hard it is *right*. These measures' extreme values are noise. The max operator is
faithful — it reports the loudest thing — and the loudest thing here is not evidence.

## Part III — On the committee, the rule is vindicated

The committee is the only instrument in this project with any claim to decisive local evidence, and its
per-cell scores for all 58 matched-benchmark images were already cached, so this cost nothing. Cells are
**authenticity** 0–100, so the ratchet is the **minimum**.

### As a ranker, it does not beat the mean

| rule | stratified AUC | vs mean |
|---|---|---|
| **mean** (what the product does now) | **0.900** | — |
| q10 | 0.900 | +0.000 |
| bottom3 | 0.898 | −0.001 |
| median | 0.897 | −0.003 |
| **min** (the pure ratchet) | **0.888** | **−0.011** |
| count below 50 | 0.368 | −0.268 |

### As a trigger, it is perfect

This is the table the rule lives or dies on. *If one cell below the bar condemns the image, how many
real photographs does that condemn?*

| bar | AI caught | **REAL wrongly condemned** | precision |
|---|---|---|---|
| 10 | 2/25 | **0/33** | **100%** |
| 20 | 2/25 | **0/33** | **100%** |
| 30 | 4/25 | **0/33** | **100%** |
| 40 | 4/25 | **0/33** | **100%** |
| 50 | 5/25 | **0/33** | **100%** |

**Zero false positives at every bar tested.** When this committee says a specific region is definitively
wrong, it has never once said it about a real photograph. That is Jonathan's rule, measured, and it
holds.

### And the reason it is not already useful

| bar | real images with ZERO failing cells | AI images with ZERO failing cells |
|---|---|---|
| 50 | **33/33** | **20/25** |
| 30 | 33/33 | 21/25 |
| 10 | 33/33 | 23/25 |

**The committee almost never rings the bell.** Asked to score each cell 0–100 for authenticity, it
returns graded, compressed, high numbers — a global impression smeared across cells. It is not being
asked whether anything is *categorically* wrong, so it does not answer that, and the ratchet has almost
nothing to fire on. Recall 20%.

**The aggregation was never the problem. The prompt is.** A graded 0–100 score per cell and a
categorical "is anything here definitively wrong" are different questions, and only the second one
produces the evidence a ratchet needs.

## Part IV — What this implies for the architecture

Jonathan's two remarks are one design, and the measurement supports it:

> **Specialist tools + a router + a ratchet gate — not a panel and a mean.**

**1. The ratchet belongs in FRONT of the mean, not instead of it.**

```
    ratchet gate      any observer reports a categorical, localised failure
                      -> FAKE. Stop. Irreversible. Nothing downstream reverses it.
                      measured: 0/33 false positives, 5/25 recall
         | silent
    graded score      the averaged committee read, stratified AUC 0.900-0.932
                      -> the ordinary verdict with its confidence band
         |
    severity          keep searching only to report HOW fake, never to revisit
                      the verdict. Count of failing regions, not a re-vote.
```

This uses both operators for what each is good at, and it matches the way Jonathan actually works: a
high-precision trigger that ends the question, then a graded read for everything the trigger did not
catch. **The two are not competing rules; they are different stages.**

**2. "Tools for specific things" is correct, and the router is what is missing — but routing cannot
rescue a tool that has no jurisdiction anywhere.**

The specialist framing was tested directly, as max-over-tools versus mean-over-tools, and lost. But that
test gave every tool a vote everywhere, which is precisely what a router would prevent. The honest
statement is narrower than either "the tools work" or "the tools are dead":

- A router can only help a tool that is **right somewhere**. The gating requirement is that a tool
  clears a real-vs-real control **within its own domain**.
- **28 free features have now been tested against real-vs-real controls. None has cleared one anywhere.**
  There is not yet a tool for the router to route to.
- The one candidate is `spec_dev`, which has a domain — **edits under ~1% of frame** — with 0.97 and
  0.88 on the two smallest, and nothing above 4%. That is exactly what a routed specialist looks like.
  At n = 13 it is two data points and cannot be separated from luck.

**So the router is the right architecture and it is blocked on having something worth routing.** Both
unblock the same way: more pairs.

**3. The context layer is where the tools come from, not where they get sorted.**

`FOLDING_SEAM_REBUILD_AND_DENSITY` Part V found that a per-material baseline halves the size trend
(−0.58 → −0.29) — real mechanism — but its free proxy leaks region-detection into its own control. A
tool that knows *"this is skin, skin has pores and subsurface scatter, this patch has neither"* is a
specialist with a jurisdiction and a bar it can cross categorically. That is simultaneously the context
layer, the source of routable tools, and the instrument that can ring the ratchet's bell. **The three
things Jonathan has been circling are one build.**

## Part V — A bug this run caught in the project's own AUC

`count@bar` first came back at **AUC 0.000** on every bar — a perfect inverted detector, which is not a
borderline result but an impossible one. Cause: the project's standard
`np.argsort(np.argsort(x))` AUC **breaks ties arbitrarily**, and `count@bar` is 0 for 54 of 58 images,
so nearly every value ties.

`FOLDING_PHOTO_SET_AUTOPSY` Part V flagged exactly this and cleared it — *"0 tied values across all 12
features × 39 images, so it never fires here. Flagged because it would matter on quantised features."*
**It fired the first time a quantised feature was introduced.** Fixed with average ranks
(`scipy.stats.rankdata`), verified against `sklearn.roc_auc_score` on heavily tied integer data over 200
trials at **1.11 × 10⁻¹⁶**, and `auc([0,0,0,0],[0,0,0])` now returns 0.500 rather than 0.000.

**Any measure that is a count, a flag or a small integer must use the tie-aware version.** The ratchet
family is all counts, so this is not incidental — it is the operator the new architecture runs on.

---

## Honest ledger

**MEASURED**
- Free measures, max/ratchet: **6–9 of 13, no rule significant**; `max-over-tools` scores *higher on
  untouched originals* (54.56) than on edited images (25.39).
- argmax localisation **0.15 against chance 0.24**, control identical at 0.15.
- Committee, ratchet as ranker: min **0.888** vs mean **0.900**. Does not beat averaging.
- Committee, ratchet as trigger: **0/33 false positives at every bar from 10 to 50**; 5/25 recall at
  bar 50. **Precision 100%.**
- Committee firing rate: **33/33 real and 20/25 AI images have zero cells below 50.**
- AUC tie bug found, fixed, and verified to 1.11e-16 against sklearn on tied data.

**WHAT THIS CHANGES**
- The ratchet is adopted as a **gate in front of the averaged verdict**, not as a replacement. It is the
  only component in the project with a measured zero false-positive rate.
- The next committee experiment is a **prompt change, not an aggregation change**: ask for a categorical
  "is anything here definitively wrong, and where" alongside the graded score, and measure the firing
  rate and the false-positive rate separately.

**UNCHANGED**
- Verdict product: one semantic call, stratified 0.900–0.932.
- **No free measure has cleared a real-vs-real control. 28 tested, 0 passed.**

**BLOCKED ON THE SAME THING AS EVERYTHING ELSE**
- 50 pairs, two toolchains, PNG export. It settles `spec_dev`'s small-edit domain, gives the router its
  first routable tool, and unblocks density and optics. Four separate lines, one dataset.

*Sources: `FOLDING_SEAM_REBUILD_AND_DENSITY` (the rebuilt masks, spec_dev's small-edit domain, the
material-baseline mechanism), `FOLDING_PHOTO_SET_AUTOPSY` (the control-arm method, and the tie warning
that came true), `FOLDING_DEBATE_AND_SEAM_DATA` (averaging beat four alternatives, entrenching the mean),
`FOLDING_COMMITTEE_TEST` (the 0.932 and the cached cell scores). Artifacts: `aggregation_test.py` +
`aggregation_results.json`, `ratchet_committee.py` + `ratchet_results.json`.*
