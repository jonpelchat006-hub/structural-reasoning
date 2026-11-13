# Arguing Makes It Worse — four ways — and the one dataset the confounds can't touch

*Jonathan: "couldn't we have them debate the decisions? after the initial score comes in, couldn't we
see why they disagree and choose the one with the strongest point?" and "could i edit some of the
pictures on my phone and we can use those?"*

*The first was tested four ways and **every one made it worse than plain averaging**. Conferring
collapses the seam signal to 0.152 — **below the same-model floor of 0.214** — which is manufactured
agreement measured directly. The second is the more valuable idea: it is the only test in this project
that is **structurally immune** to every confound that has killed everything else. Companion to
`FOLDING_OBSERVERS_AS_D`, `FOLDING_COMMITTEE_TEST`, `FOLDING_OUTER_SLOT` Part III. Status: MEASURED
(n = 58), with one arm underpowered and flagged.*

---

## Part I — Every way of making them reason lost to plain averaging

| condition | score AUC | seam \|d\| | n |
|---|---|---|---|
| **BASELINE — 3 independent observers, averaged** | **0.897** | **0.365** | 58 |
| observers state evidence for their strongest calls | 0.810 | 0.335 | 58 |
| DEBATE — each re-scores after seeing the others | 0.820 | **0.152** | 58 |
| JUDGE on the numbers | 0.734 | — | 58 |
| JUDGE weighing the arguments | 0.660 | — | **23** ⚠ |

**The plain, independent, unjustified panel average wins by a wide margin.** Four different
interventions, four losses.

### The dissipation prediction was right, and it cost more than predicted

Before running, the pre-registered prediction was: *debate raises the score and lowers the seam*, on
the grounds that conferring is a dissipation operation (`FOLDING_OUTER_SLOT` Part III: *"if the models
in the slot dissipate into each other you manufacture agreement and lose the seam"*).

**The seam half was confirmed, hard.** 0.365 → **0.152** — and the same-model-twice control is 0.214.
**After one round of debate, three different model families are more correlated with each other than a
single model is with itself across two samples.** That is manufactured agreement with a number on it.

**The score half was wrong.** Debate did not buy accuracy in exchange — the score also fell, 0.897 →
0.820. It is not a trade. It is loss on both channels.

### Why averaging is so hard to beat

Three honest readings of the same result:

- **Averaging independent noisy estimates is statistically strong.** Any procedure that *selects* one
  observer instead of pooling them throws away variance reduction. Both judge arms select; both lost.
- **Verbalising degraded the perception.** Asking observers to name evidence for their strongest calls
  cost 0.087 AUC (0.897 → 0.810) *before any judging happened*. Forcing a locally-nameable
  justification appears to pull the model off a holistic read that was better than its own account of
  itself.
- **Debate converges on the persuasive, not the correct.** A known failure mode of multi-agent debate,
  and here it is visible as the correlation collapse rather than inferred.

### The arm that is not a fair test

**JUDGE weighing arguments returned parseable output on only 23 of 58 images** — a 60% failure rate on
a task asking for 16 cell scores plus a rationale. That 0.660 is on a selected subset and should be
read as *"this design did not work"*, not as a measurement of the idea. Jonathan's proposal deserves a
better-engineered judge before it is called dead — but it now has to clear 0.897, and three sibling
designs are below it.

**Practical conclusion: do not add a reasoning or debate stage to the scoring path.** If explanations
are wanted for the user interface, generate them *after* the verdict, from the independent readings,
and do not let them feed back into the score.

---

## Part II — Editing photos on the phone is the right next dataset, and here is why

**Yes — and it is worth more than everything else on the list.**

`FOLDING_OBSERVERS_AS_D` Part V ended on the fact that the seam claim is untested and *cannot* be
tested on this data: every AI image here is full-frame generation, so there is no internal seam to
localise, and disagreement is measuring global unsettledness instead. `STATE_OF_THE_DETECTOR` §4 named
this blind spot from the start.

**An edited photo has a seam with a known location.** And it has a property nothing else in this
project has had:

> **Ground truth is a mask *inside a single image*, so the comparison is within-image.**
> Camera, lens, sensor, processing pipeline, compression, content, subject and lighting are all
> **identical on both sides of the seam**. Every confound that killed the model-free axes — device,
> content, compression, professional editing — **cancels exactly.**

That is not a smaller test. It is a **cleaner** one than anything run so far, and it tests the actual
product feature — the seam map — rather than a proxy for it.

### What makes a usable pair

**Save BOTH versions of every photo — the original and the edited one.** Diffing them yields a
pixel-exact manipulation mask automatically; no hand-annotation, no judgement calls about where the
edit "really" is. This is the single most important instruction.

**Edits that count** — localised *content* changes:

- generative fill / magic eraser / object removal
- adding an object or a person that was not there
- sky replacement
- face or expression swap
- moving or duplicating something within the frame

**Edits that do not count** — global changes with no seam to find:

- filters, colour grading, exposure, contrast, saturation
- crops, rotations, straightening
- whole-image upscaling or denoising

**Vary the edit size on purpose.** A few tiny removals, a few medium objects, a couple of large
region replacements. That gives a **detection floor** — the smallest seam the committee can find —
which is a far more useful product spec than a single accuracy number.

**Keep the export path identical** for original and edited (same app, same format, same quality), so
the pair differs only in the edited region.

**20–30 pairs is enough for a first read**, and variety of edit type matters more than count.

### What we would then measure, for the first time

1. **Does committee disagreement land on the edited region?** Overlap between the disagreement map and
   the true mask — this is the seam claim, tested directly, and it has never been possible before.
2. **The detection floor.** Smallest edited area still localised above chance.
3. **Whether independence buys localisation specifically.** `FOLDING_OBSERVERS_AS_D` measured that
   independence trades score for seam signal (r = −0.91) — but "seam signal" there was really global
   unsettledness. This is the test that says whether independent observers genuinely *localise better*,
   which is the whole justification for the committee.
4. **Whether the model-free axes revive.** They died at class separation, but a within-image test asks
   something different: not "is this image generated" but "is this region inconsistent with that one."
   The reconstruction and predictability measures were *built* for that question and have never been
   asked it.

---

## Honest ledger

**MEASURED (n = 58, content- and compression-matched)**
- Plain independent averaging (0.897 / 0.365) beat all four reasoning and debate variants.
- Debate collapsed the seam signal to **0.152, below the 0.214 same-model floor** — three families
  became more correlated than one model with itself. Dissipation, measured.
- Debate lost score as well (0.897 → 0.820): not a trade, a loss.
- Forcing evidence-citation alone cost 0.087 AUC before any judging.

**FLAGGED AS UNFAIR**
- The argument-weighing judge parsed on 23/58. Underpowered and selection-biased; a design failure,
  not a verdict on the idea.

**CAVEATS**
- One round of debate, one prompt per condition, one judge model. Better designs exist; they now have
  to clear 0.897.
- n = 58; differences under ~0.03 are noise. The 0.213 seam collapse is not.

**NEXT — and it is the highest-value thing left**
- The edited-photo pairs. First test of seam localisation, and the only test in this project whose
  ground truth is confound-free by construction.

*Sources: `FOLDING_OUTER_SLOT` Part III (dissipation manufactures agreement), `FOLDING_OBSERVERS_AS_D`
(the −0.91 score/seam tradeoff; the 0.214 same-model floor), `FOLDING_COMMITTEE_TEST` (the arms),
`STATE_OF_THE_DETECTOR` §4 (the no-seam blind spot). Artifacts: `debate_experiment.py`,
`judge_fixed.py`, `debate_results.json`.*
