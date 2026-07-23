# Structural Reasoning — an independent research program

*Work in progress. Independent, self-funded, no institution.*

This repository collects an ongoing attempt to solve abstract-reasoning problems
**by structure alone** — without a large language model doing the thinking — and to
understand where that approach reaches its limits. It is under construction. What's
below is what is real and reproducible today; the rest is honestly marked as unfinished.

The stance throughout is one thing: **name the claim, test it, and believe the number —
even when the number bounds the idea.** Every result here is reported with its baseline
and its ceiling. Where something doesn't beat a trivial baseline, that is said plainly.

---

## 1. A model-free ARC-AGI solver  *(the main result)*

[ARC-AGI](https://arcprize.org/) is a benchmark of abstract visual-reasoning puzzles
designed to resist memorization — each task is novel, and the test is whether a system
can infer a transformation from a few examples and apply it. Most current approaches
bolt a large language model to the problem. This one uses **no language model anywhere.**

It perceives each task as a structured signature, retrieves related solved tasks by
resonance, and reasons by *bending a flexible program against the hard constraint of the
worked examples* — the exact-match on the training pairs does the reasoning that a model
would otherwise stand in for. It learns online as it runs.

**Where it stands, honestly:**

| stage | solved (of 400 train) | note |
|---|---|---|
| initial operator set | 26 | 11 primitives |
| + relational / nesting | 56 | |
| + "muscle group" primitives | 64 | one good batch = +8 |
| + induced operators | **66 / 400 (16.5%)** | every solve generalizes to held-out test |

- **No model. Pure structure. Every solve generalizes** to the hidden test pair.
- The **ceiling is mapped three independent ways** and they agree: the residual is
  operator-bound (tasks are one-off rules, not classes), dimension-bound (the system
  *transforms* content but barely *generates* new content — the lowest-solved class), and
  diversity-bound (ARC's tail is deliberately idiosyncratic). More single tricks return
  ~0; the honest next levers are a large primitive grind or per-task operator generation.
- **Honest limit:** 16.5% on train (~6.5% on the harder eval set) is *not* competitive
  with the top of the ARC leaderboard, which uses far heavier machinery. The interest
  here is not the score — it is that a fully model-free, interpretable, online-learning
  system reaches this at all, and that its ceiling is understood rather than guessed.

*(Status: the reasoning engine is built and validated. The generative half — inducing
what-to-draw per task — is the open research frontier, in progress.)*

---

## 2. The folding thread — a worked example of the same lens

The same structural question — *what is local and knowable versus what is global and
hard* — shows up cleanly in protein folding, and this repo includes a self-contained
exploration of it. It is **not novel biology**; it re-derives things structural
biologists already know (domain interfaces are complementary, active sites sit in the
interdomain cleft, local structure is only weakly sequence-readable). The value is that
it arrives there *from scratch, by feel*, and maps exactly where the wall sits — the same
local-vs-nonlocal wall as the ARC work.

Reproducible findings, each tested against real PDB structures with the baseline stated:

- **The domain boundary is a flat plane** (85–98% linearly separable), a "knife" made of
  absence — the contact gap between two units.
- **The two faces are complementary imprints** — shape fits 2.4× better in the true
  orientation than any rotated one; 70% of cross-cut charged contacts are salt bridges.
- **Local structure is cheap; the global "web" is the wall.** Knowable local rules prune
  the fold space ~580 orders of magnitude, then stop: the long-range contact pattern is
  ~98% independent of any local descriptor. Predicting the *seam* or the *active site*
  from local features does **not** beat a trivial baseline — reported honestly, not hidden.
- **The fold is one chain knitted through its own boundary** (the backbone threads the
  domain seam 1–7×), and the ligand sits on that seam, reached from both domains.

Every figure and script is included. The through-line: *local structure describes the
fold beautifully; the route is not in the sequence.* That is the same barrier the ARC
solver hits, found independently.

---

## 3. The bigger picture  *(under construction)*

These two pieces are part of a larger research program on structural / non-model
reasoning. The connective framework and the LLM-assisted components are **actively being
built and are not ready to show** — they are omitted here rather than presented half-done.
This front page deliberately leads with the parts that stand on their own and are
reproducible today.

---

## On the author

Independent researcher, no formal affiliation. The work is self-taught and self-funded.
It is put here in the open because the ideas should be judged by whether they hold up,
not by whose name is on them — and because the arenas that matter for this work
(ARC-AGI's public leaderboard, open reproducible code) are the ones that judge the work,
not the credential.

---

### Decisions for you (Jonathan) before this goes public
1. **Repo name / title** — placeholder above; your call.
2. **How much of the broader framework to include** — my honest recommendation is to keep
   leading with the demonstrable ARC + folding work and keep the more speculative
   theory (and the alpha derivation) *out of the front page*, so the credible work isn't
   judged by association. It can live in its own clearly-labeled "speculative / theory"
   section deeper in, if at all.
3. **Which artifacts to attach** — the folding figures are ready to include now; the ARC
   code lives on your machine and would need to be added to the repo.
