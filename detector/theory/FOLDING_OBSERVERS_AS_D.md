# Observers are D — and independence is a measured quantity, not a vendor label

*Jonathan: "adding more observers makes it easier to see void lines? … each add another thread to the
borders sending in the same colors, but that could also reinforce the same color or introduce an
imbalance. the pixels were made of A/B+D so they would be like adding to D right? … pretty much any ai
these days can figure out a human shape, so we really only need one for that, and then additional
observers are like experts inspecting it closely?"*

*All three parts check out, and the middle one turns out to be **definitional rather than analogical**.
With Gemini restored on the new key, four families were measured pairwise: **GPT and Gemini agree at
r = 0.91 — nearly as redundant as running one model twice (0.94).** Vendor diversity is not observer
independence. And across every roster, score and seam signal are anti-correlated at **r = −0.91**:
reinforcement and imbalance are the two ends of one dial. Companion to `FOLDING_COMMITTEE_TEST`,
`FOLDING_D_AND_DIRECTIONS`, `FOLDING_OBSERVERS`, `FOLDING_OUTER_SLOT`. Status: MEASURED, n = 58,
~400 API calls.*

---

## Part I — "adding to D" is exactly right, and the corpus already requires independence

`FOLDING_D_AND_DIRECTIONS` (tested): *"A/B = the two domains, C = their mix; **D = the cofactor**
(retinal, NAD, ATP, a metal) — a chemically distinct material dropped into the pocket, **not made of A
or B**… This names the thing that makes a pocket a **reader** instead of just a hole."*

Map it: A and B are the image's own coherent regions, C is their seam, and an **observer is a D** — an
outside element dropped in that turns the pocket into a reader. Adding observers is not adding more
image material; it is adding reading capacity. Jonathan's identification is correct.

**And the definition of D carries the independence requirement inside it.** D is *chemically distinct*
by definition — a second copy of A is not a cofactor. So the framework already says, without needing
a new claim, that a correlated observer is not a new D. It is more of the same material.

That is precisely his "reinforce the same colour vs. introduce an imbalance," and both halves are now
measured.

## Part II — Independence, measured (the surprise)

Per-cell score correlation between observers, 58 images × 16 cells:

| | claude | gpt | grok | gemini |
|---|---|---|---|---|
| **claude** | 1.00 | 0.79 | **0.70** | 0.75 |
| **gpt** | 0.79 | 1.00 | 0.74 | **0.91** |
| **grok** | 0.70 | 0.74 | 1.00 | 0.78 |
| **gemini** | 0.75 | 0.91 | 0.78 | 1.00 |

**claude pass 0 vs pass 1 (same model, temperature 1.0): r = 0.94.**

- **GPT and Gemini sit at 0.91 — barely more independent than one model run twice.** Two vendors, two
  architectures, two training pipelines, and they behave almost like one observer. **Vendor diversity
  is not observer independence.**
- **Claude and Grok, at 0.70, are the most independent pair available.**
- Sampling noise alone (same model, two passes) leaves r = 0.94, so the *entire* independence budget
  across all four families spans 0.94 → 0.70.

This is `FOLDING_OUTER_SLOT` Part III's warning made quantitative: *"if the models in the slot dissipate
into each other you manufacture agreement and lose the seam."* Two of these four have largely dissipated
into each other. **Independence has to be measured per pair, not assumed from the logo.**

## Part III — Reinforce vs. imbalance is one dial, and it is nearly perfect

| roster | score AUC | seam \|d\| |
|---|---|---|
| A claude ×1 | **0.932** | — |
| F claude + gemini *(the v6 roster)* | **0.930** | 0.229 |
| B claude ×2 *(same model)* | 0.917 | 0.214 |
| C claude + gpt | 0.912 | 0.284 |
| G 4 families | 0.902 | 0.347 |
| E 3 families *(claude+gpt+grok)* | 0.897 | **0.365** |

**corr(score, seam) across rosters = −0.91.**

Both of Jonathan's outcomes are real and they are the two ends of the same dial:

- **Reinforcement.** A correlated observer confirms what the first already said. The score holds up
  (F: 0.930, the best committee) and the seam signal stays near the same-model floor (0.229 vs 0.214).
- **Imbalance.** An independent observer disagrees somewhere the first did not. The seam signal climbs
  (0.365) and the score drifts down (0.897).

**The v6 roster is the reinforcement end.** Claude + Gemini is the *best-scoring* committee here —
0.930, and the best portrait bucket of any committee at **0.88** — precisely *because* those two are
only r = 0.75 apart. It buys score, not localisation. If the shipped product is a verdict, that roster
is well chosen. If it is a seam map, **claude + grok** is the pair to build on, and adding GPT to
Gemini adds almost nothing.

*(Four families scored slightly below three — adding Gemini to claude+gpt+grok moved the seam 0.365 →
0.347. Consistent with the correlation table: Gemini's nearest neighbour, GPT, is already in the room.
At n = 58 that difference is within noise, but the direction is what the r = 0.91 predicts.)*

## Part IV — "One to see the whole, the rest as close inspectors" — confirmed, with an inversion

The proposed two-tier architecture is supported, and it is cheaper than a flat committee:

- **One observer for the global read: 0.932.** The best scorer in the entire experiment. Recognising a
  human shape or a background is, as Jonathan says, a solved problem — one model suffices and more do
  not help.
- **Extra observers earn their cost only on the map.** Seam |d| goes 0.214 → 0.365 with independence
  while the score does not improve at all.

**But the inversion matters.** Testing where the close inspection should go:

| where the disagreement is measured | seam \|d\| |
|---|---|
| in the 4 cells the scout flags as *least* authentic | 0.302 |
| **everywhere the scout did *not* flag** | **0.400** |

**The informative disagreement is in the regions the scout cleared, not the ones it flagged.** Where
the scout says "this looks wrong," the other observers agree it looks wrong — agreement is the
invariant, and there is no depth in it. The signal is where one observer sees nothing and the others
still do not settle. `FOLDING_OBSERVERS` says it exactly: *agreement = the invariant, disagreement =
the depth.* So the router should send experts to the **clean-looking** regions.

## Part V — The seam claim is still untested, and this data cannot test it

A caution that the numbers force:

| | disagreement concentration (max cell / mean cell) |
|---|---|
| real | **1.63** |
| AI | **1.46** |

**Disagreement is more *diffuse* on generated images, not more localised.** The seam picture would
predict the opposite — a boundary where the committee splits.

The resolution is already in `STATE_OF_THE_DETECTOR` §4: *"a subtle fake with no internal seam (a
flawless full-frame regeneration) is the committee's blind spot by construction."* Every AI image in
this benchmark is full-frame generation. **There is no seam to localise** — the whole frame is off, so
the observers are uniformly unsettled. What the disagreement channel measures here is *global
unsettledness*, and that is a real and strong signal (|d| 0.365), but it is **not** seam localisation.

**The localisation claim — the product's headline feature — remains untested**, and this dataset cannot
test it. It needs **composited or inpainted images with known manipulated regions**: a real photo with
a generated patch, where the seam has a ground-truth location. That is the next dataset to build, and
it is the one that would validate or kill the seam map.

## Honest ledger

**MEASURED (n = 58, content- and compression-matched, six generator families)**
- Observer independence matrix: same-model 0.94; gpt↔gemini **0.91**; claude↔grok **0.70** (most
  independent pair). Vendor ≠ independence.
- corr(score, seam) across six rosters = **−0.91**. Reinforcement and imbalance are one dial.
- One observer is the best scorer (0.932); extra observers pay only on the disagreement channel.
- Disagreement away from the scout's flagged cells (|d| 0.400) beats disagreement at them (0.302).
- Disagreement is *more diffuse* on AI (1.46) than on real (1.63).

**AFFIRMED FROM THE CORPUS**
- Observers are D-class cofactors; `FOLDING_D_AND_DIRECTIONS` defines D as chemically distinct, so
  independence is definitional, not an add-on.

**CAVEATS**
- n = 58. Differences under ~0.03 in score are noise; the independence matrix (58×16 = 928 paired
  cells) and the −0.91 tradeoff are the sturdier results.
- Gemini is `gemini-2.5-flash` — the pro tiers return 404 on this key. A stronger Gemini might be less
  correlated with GPT; the 0.91 is specific to this model.
- One prompt, one grid size, one temperature.

**UNTESTED**
- Seam *localisation* — needs composited images with ground-truth manipulated regions.
- Whether any of this survives the next generation of generators.

*Sources: `FOLDING_D_AND_DIRECTIONS` (A/B + D; D as the chemically distinct cofactor that makes a
reader), `FOLDING_OBSERVERS` (agreement = invariant, disagreement = depth), `FOLDING_OUTER_SLOT` Part
III (routes must stay independent or agreement is manufactured), `FOLDING_COMMITTEE_TEST` (the arms),
`STATE_OF_THE_DETECTOR` §4 (the no-seam blind spot). Artifacts: `committee_experiment.py`,
`committee_cache.json`.*
