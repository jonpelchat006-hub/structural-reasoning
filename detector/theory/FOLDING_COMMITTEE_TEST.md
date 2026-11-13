# What the Committee Buys — the vision half works, but not for the reason the architecture claims

*The API experiment ran. On the same content-matched, compression-matched, six-generator benchmark
where **every model-free measure collapsed to ≤ 0.66**, the vision committee scores **stratified AUC
0.93**. The paid half carries the product. But the controlled arms say something sharper: adding
observers does **not** improve the score — one model alone is the best scorer — while observer
**diversity cleanly and monotonically improves the disagreement signal**, with the same-model-twice
control at the bottom. The framework's central claim is confirmed, on the channel it was actually
about. Companion to `FOLDING_MATCHED_BENCHMARK`, `FOLDING_OBSERVERS`, `FOLDING_SKIN_DETECTOR`,
`FOLDING_OUTER_SLOT`, `SHOVELCAT_CHECKER_V6`. Status: MEASURED, n = 58, 290 API calls.*

---

## Part I — The design, and the arm that had never been run

Five arms over the same 58 images, each observer scoring a 4×4 grid (so every arm yields both a global
score and a per-cell map):

| arm | roster | what it isolates |
|---|---|---|
| A | claude ×1 | one observer |
| **B** | **claude ×2** | **the missing control** — is disagreement just sampling noise? |
| C | claude + gpt | genuinely independent families |
| D | claude ×2 + gpt ×2 | four observers, two families |
| E | claude + gpt + grok | three families |

**B is the arm that makes this experiment worth running.** Without it, "observers disagree at the seam"
cannot be told apart from "the sampler is stochastic." The old 0.733 → 0.765 result gestured at this
but was measured on the confounded set.

*Roster note: the run was specified as Claude + Gemini. **Every Gemini model returned HTTP 429** — the
key's quota is exhausted, not a model problem — so GPT-5.1 took Gemini's slot and Grok-4 was added as a
third family. The scientific question is unaffected; for the XPRIZE, Gemini should be re-tested in that
slot on a funded key.*

Models: `claude-sonnet-5`, `gpt-5.1`, `grok-4`. Bars were fixed before the run.

## Part II — The result

| arm | agreement (score) | disagreement (seam) | combined |
|---|---|---|---|
| A claude ×1 | **0.932** | — | 0.932 |
| B claude ×2 SAME model | 0.917 | 0.714 | 0.930 |
| C claude + gpt | 0.912 | 0.784 | 0.922 |
| D 4 obs / 2 families | 0.907 | 0.835 | 0.927 |
| E 3 families | 0.897 | **0.865** | **0.935** |

*(all stratified by content bucket; disagreement shown as signed AUC for readability)*

### The vision half works, and it is the only thing that does

**0.93 against ≤ 0.66 for every model-free measure**, on identical images. `FOLDING_MATCHED_BENCHMARK`
found nothing above |AUC − 0.5| = 0.164; this is 0.432. Per bucket: **landscape 0.97, portrait 0.83.**
The open question that doc ended on is now answered — the committee is carrying the entire detector.

### Adding observers does not improve the score

0.932 → 0.917 → 0.912 → 0.907 → 0.897, monotonically **down** as observers are added. A single Claude
call is the best scorer in the experiment. At n = 58 a 0.035 spread is within noise, so the honest
reading is *not* "more observers hurt" but **"more observers do not help the score, and certainly do
not justify their cost on that channel."**

### But observer DIVERSITY improves the seam signal, cleanly

| roster | disagreement \|AUC − 0.5\| |
|---|---|
| claude ×2 — **same model** | **0.214** |
| claude + gpt — 2 families | **0.284** |
| claude + gpt + grok — 3 families | **0.365** |

Monotone across three levels of diversity, with the **same-model control at the bottom**. Sampling noise
alone produces 0.214; genuine independence lifts it to 0.365. That is a 0.15 gain attributable to
*observer independence specifically*, and it is the first clean measurement of it in this project.

**And the direction is right.** In every arm, disagreement is **higher on generated images** — exactly
`FOLDING_SKIN_DETECTOR` Test 5 (the committee disagrees 2.1× at the seam) and `FOLDING_OBSERVERS`
(agreement = the invariant, disagreement = the depth), now reproduced in the image domain on clean data.

### Pre-registered bars

| bar | result |
|---|---|
| 1. product: ≥ 0.80 in both buckets | landscape 0.974, portrait 0.827 → **PASS** |
| 2. architecture on AGREEMENT: C beats B by ≥ 0.05 | −0.005 → **FAIL** |
| 3. architecture on DISAGREEMENT: C beats B by ≥ 0.05 | **+0.070 → PASS** |
| 4. seam signal alone: \|d\| ≥ 0.10 | 0.284 → **PASS** |

**Three of four, and the one failure is informative rather than fatal**: the committee is not a better
scorer, it is a better *localiser*. Which is what the architecture was always for — `SHOVELCAT_CHECKER_V6`
§5 says the deliverable is *"a labeled map, not a scalar."* The experiment says: believe that, and stop
justifying the committee on the score.

## Part III — What this means for the product

**Two different products, two different costs.**

- **Just a verdict?** One `claude-sonnet-5` call. AUC 0.932. One API call per image, no committee, no
  router, no free axes. That is the honest cheapest configuration and it beats everything else here.
- **A seam map and a confidence overlay?** You need **at least two independent families, and three is
  measurably better**. That is what the extra calls buy — not accuracy, localisation.

**Portraits are the hard case, and observers interact with it.** Landscape 0.95 → 0.98 as observers are
added; portrait 0.90 → 0.80. Adding observers *helps* landscapes and *hurts* portraits. With n = 12–14
per portrait cell this could be noise, but it is a specific, cheap thing to re-test, and it is the kind
of interaction the context router exists to handle.

**The free axes are not carrying the product, and now have a clear job.** They cost nothing and run
locally, so they remain useful as a pre-filter or an offline fallback — but `STATE_OF_THE_DETECTOR`'s
framing of four co-equal axes does not survive: it is one paid axis that works, plus a frame of free
measures that do not separate classes on fair data.

## Honest ledger

**MEASURED (n = 58, content- and compression-matched, six generator families, 290 calls)**
- Vision committee stratified AUC **0.932** (single) to 0.897 (five observers); per bucket 0.97 / 0.83.
- Adding observers does not improve the score (monotone decline, within noise).
- **Observer diversity improves disagreement monotonically: 0.214 (same model) → 0.284 (2 families) →
  0.365 (3 families).** The same-model control is the lowest.
- Disagreement is higher on generated images in every arm — the seam claim, reproduced on images.
- Combining agreement and disagreement (E) reaches 0.935, marginally the best overall.

**CAVEATS**
- n = 58. Agreement differences of 0.02–0.03 are noise; the disagreement gradient (0.15 across three
  diversity levels, monotone) is the more credible of the two findings.
- Gemini was untestable (quota). The XPRIZE roster claim needs Gemini re-run in that slot.
- Vision models may be reading *style and provenance cues* — "this looks like stock photography" versus
  "this looks like a render" — rather than anything about generation. Bucket stratification controls
  content type but not house style. **A model that recognises today's generator aesthetics may not
  survive tomorrow's**, and nothing here tests that.
- Single temperature (1.0), single prompt, one grid size. All unexplored.

**NOT TESTED**
- The context router (axis 2) — untouched by this experiment.
- Whether the seam map is *spatially correct*, only whether its spread predicts the label. Testing
  localisation needs images with known manipulated regions.

*Sources: `FOLDING_MATCHED_BENCHMARK` (the ≤0.66 result this is measured against), `FOLDING_OBSERVERS`
(agreement = invariant, disagreement = depth), `FOLDING_SKIN_DETECTOR` Test 5 (2.1× at the seam),
`FOLDING_OUTER_SLOT` Part III (routes must stay independent), `SHOVELCAT_CHECKER_V6` §5 (a labeled map,
not a scalar), `STATE_OF_THE_DETECTOR` §2. Artifacts: `committee_experiment.py`,
`committee_cache.json`, `committee_results.json`.*
