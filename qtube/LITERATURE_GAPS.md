# QTUBE: literature gaps and the next executable experiment

Research checked November 1, 2026. Scope: strengthen the existing quaternion
model and connect it to observed game transitions before the submission deadline.
Paper claims and proposed adaptations are separated below.

## What the local library contains

`D:\shovelcat-colony\brain\library` contains **9,009 JSON digests**.
`D:\shovelcat-colony\companion\library` currently contains **8,997 source files**
recursively. These counts measure different stores; neither is a count of unique
research papers. The visible source collection is largely the user's notes,
theory documents, code, and copied project material. It is valuable project
history, but should not be treated as an up-to-date, independently verified
scientific bibliography. `D:\planet\papers.json` is assignment/read bookkeeping.

The sources below were checked separately against primary papers or official
repositories. Their inclusion is a targeted reading list, not a claim that the
whole local collection has been reviewed.

## Six useful primary works

### 1. Theory learning, exploration, and prediction checks

**Human-Level Reinforcement Learning through Theory-Based Modeling, Exploration,
and Planning** — Tsividis et al.; first submitted **July 27, 2021**.
[Paper and Methods](https://arxiv.org/html/2107.12544v1).

**Paper claim:** EMPA learns object dynamics, interaction rules, and termination
conditions within a supplied game-description language. Exploration seeks
unresolved interactions; planning predicts future states and replans after
prediction error. Its evaluated variant assumes fully observed object state and
knows avatar and wall identities/types.

**QTUBE inference:** preserve competing contact laws, seek distinguishing
observations, and invalidate predictions contradicted by actual frames. Borrow
the learning/planning separation without claiming its supplied semantics were
discovered from pixels.

### 2. Symmetry can make a single canonical pose inappropriate

**Equivariant Frames and the Impossibility of Continuous Canonicalization** —
Dym, Lawrence, Siegel; first submitted **February 25, 2024**, ICML **July 2024**.
[Proceedings](https://proceedings.mlr.press/v235/dym24a.html).

**Paper claim:** canonicalization/frame selection has fundamental continuity
limitations for several important group actions; weighted frames address
robustness problems.

**QTUBE inference:** retain the set of D4 transformations consistent with each
observed glyph transition. An unchanged symmetric glyph does not establish an
identity action. Intersect support across discriminating examples. Keep exact
masks or richer part sets alongside covariance; low-order moments are not a
complete shape description. The continuous-group theorem is not itself a proof
about every finite D4 implementation.

### 3. Algebra choice is not sufficient evidence of reasoning advantage

**Scalars are universal: Equivariant machine learning, structured like classical
physics** — Villar et al.; first submitted **June 11, 2021**, NeurIPS **2021**.
[Proceedings](https://proceedings.neurips.cc/paper/2021/hash/f1b0775946bc0329b35b823b86eeb5f5-Abstract.html).

**Paper claim:** broad classes of equivariant functions can be expressed using
scalar products/contractions and appropriate combinations of vector/tensor
inputs.

**QTUBE inference:** quaternion composition is useful supplied geometry; adding
hypercomplex dimensions alone does not establish added reasoning ability.
Continue distance/vector/matrix controls and representation ablations. The
existing synthetic results do not demonstrate a useful annihilation mechanism
or an advantage over distance matching.

### 4. Object representations need persistent correspondence and interactions

**Object-Centric World Models Meet Monte Carlo Tree Search** — Vakhitov,
Ugadiarov, Panov; first submitted **January 10, 2026**.
[Paper](https://arxiv.org/html/2601.06604v1).

**Paper claim:** ObjectZero combines pretrained object-slot encoders,
action-conditioned graph dynamics, and MCTS. Previous slots initialize the next
observation's slots to stabilize correspondence. Results are roughly comparable
to the monolithic EfficientZeroV2 baseline. Representation pretraining requires
large observation datasets; segmentation and quadratic graph cost are limits.

**QTUBE inference:** track which object changed before assigning its effect.
Nested part/object frames should coexist with relations between objects; a tree
alone does not capture all interactions. Reuse current perception for the
deadline experiment rather than starting large-scale slot pretraining.

### 5. Separate persistent shape from action-conditioned motion

**Learning Action-Conditional and Object-Centric Gaussian Splatting World Models
for Rigid Objects** — Kreber, Mack, Stueckler; first submitted **June 1, 2026**,
revised **October 26, 2026**.
[Current paper](https://arxiv.org/html/2606.01950v2).

**Paper claim:** object-frame geometry supports predicting relative motion from
history and future actions. The method directly supervises relative position and
rotation-matrix predictions. Its setting assumes object segmentation and uses
multiview reconstruction for robotic manipulation.

**QTUBE inference:** retain shape identity while changing pose, and optimize
next-state geometry rather than stopping at correct candidate classification.
Use history/context when one contact does not have a globally fixed effect.
The robotics assumptions and reported performance do not establish ARC transfer.

### 6. Retain observations that a compressed representation may later need

**VISTA: A Visual Harness for Reasoning in an Interactive World** — Han et al.;
first submitted **October 1, 2026**.
[Paper](https://arxiv.org/html/2610.02200v1),
[official implementation](https://github.com/joshhhhhan/VISTA).

**Paper claim:** the harness retains original observations, including intermediate
animation frames, indexed by turn/frame, and permits later inspection. Results
use existing multimodal models on the 25 public ARC-AGI-3 games. The authors
acknowledge possible training contamination and identify private-game evaluation
as a stronger generalization test.

**QTUBE inference:** retain original grids and action history losslessly so
counterexamples can trigger re-encoding. Separate persistent per-game laws from
per-level state. This is useful memory design evidence, not evidence for
quaternion architecture or a requirement to add an LLM.

## What to execute before expanding the model

The [official ARC-AGI-3 report, April 22, 2026](https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf)
tests exploration, modeling, goal discovery, and action-efficient execution.
[Official action documentation](https://docs.arcprize.org/actions.md) describes
game-dependent key effects and coordinate-bearing clicks. Therefore, raw
keyboard actions and meaningful object contacts must remain distinct.

1. **Acquire effects from contacts.** Record the actual before/after frames and
   the object/contact reached. A navigation action can step away without changing
   the glyph, while the same direction later triggers a contact effect. Do not
   label every keypress with a globally fixed rotation.
2. **Preserve symmetry uncertainty.** Compute all compatible D4 effects from
   masks. Two observations that narrow support are evidence; a forced single
   label from one symmetric shape is not. Choose probes where surviving effects
   predict different results.
3. **Fit and freeze the pose model.** Fit on acquired transitions, then predict
   new contacts before execution without updating on those holdout outcomes.
   Compare exact-mask predictions against identity and discrete-D4 controls.
   Resolved evidence support and a well-fitted continuous quaternion are separate
   requirements: the optimizer can remain at an incorrect solution.
4. **Represent non-pose changes separately.** Color, deletion/spawn, selection,
   counters, navigation, hidden guards, and level boundaries need additional
   fields or hypotheses. A pose mismatch may expose a missing precondition rather
   than a new rotation. Abstain outside the encoder's supported mask dimensions.
5. **Plan, execute, falsify.** Search short supported contact sequences, execute
   one step, and compare predicted with observed changes. Stop/revise when they
   disagree. Confidence based on two examples is an operational gate, not a
   calibrated probability or proof of a universal rule.
6. **Report the actual task.** Returning to an observed glyph is an experimental
   goal. Report it separately from game completion, acquired win conditions, and
   official action-efficiency scoring. A supplied crop and demonstration route
   are perception/navigation priors, not autonomous exploration.

## Current implementation boundary

The newest active branch now completes the first `ls20` level in 25 official
actions across three model seeds, with no demonstration reads or supplied crop/
target coordinates. It probes controls, infers floor, approaches a small object,
discovers a changing display, learns the contact effect, selects a visible target,
and verifies entry through an engine level increment. `ACTIVE_GAME_AGENT.md`
records its assumptions and exact results. The supplied body detector and visual
hypothesis classes remain game-informed priors. This development result on one
known public level does not establish unseen-game performance or a quaternion
advantage over a discrete D4 solver.

Budget-aware planning was added after an overlong verification run exhausted a
shrinking strip and reset the body. `qbudget.py` infers the strip and consumption
from observation history; planning reserves action capacity and can reduce
optional verification contacts. `qeffects.py` separately stores observed
recoloring and reshaping under level/contact/context scopes. The current active
goal controller still handles pose-only objectives; the non-pose effect book has
recorded-data validation, not general closed-loop control validation.

`qtransition.py` now provides observed contact rules, set-valued D4 support,
quaternion fitting, and conservative contact planning. `qgame_loop.py` connects
fresh engine observations to acquisition, frozen prediction checks, and planned
execution. Their current scope is a demonstration-assisted experiment.

The integration check reports a 26-action replay matching all recorded frames.
The first fresh-contact pilot resolved support from `{3, 4}` to `{3}` after two
observations, but its continuous quaternion fit stayed at an incorrect stationary
point and frozen prediction failed. Training-only multistart fitting resolved
that numerical failure. Three development replications, with different frozen
encoders and fitting seeds, then predicted 12/12 frozen contacts and completed
all three two-contact return plans. Each used 40 engine actions and completed
zero game levels. A discrete D4 evidence baseline also predicts 12/12, so this
does not demonstrate a quaternion advantage.

The final implementation additionally gates planning on training pose loss at
most `1e-6`, exact reconstruction of both acquired transitions, and agreement
among remaining evidence-compatible laws. State/level/reset boundaries are
checked before sending a return action. `game_loop_ls20_verified_s0/summary.json`
records the final gated run. This is a development/regression experiment on one
four-pose shape orbit, following method revision after a failed pilot; it is not
an untouched generalization evaluation. See `REAL_GAME_LOOP.md` for reproduction
and limitations.

**Supplied priors:** object/crop extraction, bootstrap navigation, D4 structure,
quaternion rotation application, frozen synthetic encoder, experimental target.
**Acquired semantics:** which observed contact selects which effect, its evidence
support, and whether later observations uphold that prediction. General contact
guards, nested object/part discovery, and game-goal inference remain open work.
