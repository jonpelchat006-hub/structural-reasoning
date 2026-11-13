# Observed contact learning in the real ARC engine

**Newer result:** `ACTIVE_GAME_AGENT.md` describes a demonstration-free active
branch that discovers the display/target and completes the first public level
in 25 actions. The sections below preserve the earlier contact-loop experiment
and its narrower results.

November 1, 2026. The loop now runs against the official local ARC-AGI-3 engine,
with fresh environment observations, no LLM, no network connection, and no game
implementation inspected. It is a demonstration-assisted geometry experiment,
not an autonomous ARC solver or a submission score improvement.

## Result

Three development replications use different frozen distance encoders and
quaternion fitting seeds. Each run:

1. Replays a 26-action route from a previous observation recording. Every returned
   frame must match the recording exactly; otherwise it stops.
2. Observes one contact at the end of that route, then steps away and returns for
   a second contact. The inverse movement action is inferred from a previously
   observed body displacement, not assigned a hardcoded arrow meaning.
3. Fits one quaternion for contact with that particular observed object. It does
   not fit a quaternion for the keyboard action: identical keyboard actions have
   different effects depending on where the body is.
4. Freezes the learned operator and predicts four fresh contact outcomes before
   executing them. All 12 predictions across the three runs are correct. The
   identity baseline is correct on 0/12; a discrete D4 evidence baseline is also
   correct on 12/12.
5. Searches a short plan using learned pose predictions, executes two contacts,
   and verifies each result. All three plans return to the selected initial glyph.

Each run uses **40 official environment actions**, including the 26-action
demonstration prefix. Each completes **zero game levels**. The experimental goal
is returning to an observed glyph; it is not the game's inferred win condition.

Detailed development results:

- `game_loop_ls20_s0_multistart/summary.json`
- `game_loop_ls20_s1_multistart/summary.json`
- `game_loop_ls20_s2_multistart/summary.json`

`game_loop_ls20_verified_s0/summary.json` repeats seed 0 with the final training-fit
and episode-boundary gates. It also gets 4/4 frozen predictions and completes the
two-contact plan. Its acquired-transition feature loss is about `1.03e-15`.

## What changed from the first failed pilot

The initial glyph has reflection symmetry. The first observed change is
compatible with D4 elements `{3,4}`. The next source pose gives `{3,6}`, so their
intersection is `{3}`: the observed contact is a clockwise quarter turn.
This label is inferred from observations, not attached to an action ID.

A single continuous quaternion optimizer initially fit the reflection perfectly.
After the second example ruled it out, that quaternion remained at a stationary
point with training feature loss `0.859485`. The model then failed a frozen
prediction. The failed run is preserved in `game_loop_ls20_s0/summary.json`.

The new fitter uses the warm solution plus three independent random starts,
selecting by acquisition-data feature loss only. No frozen outcomes select the
quaternion. The final gate additionally requires finite loss <=`1e-6` and exact
reconstruction of both acquired transitions. An unresolved or poorly fitted
model cannot authorize a plan.

Because the method was revised after inspecting the failed pilot, the successful
runs are development/regression evidence. The four frozen contact sources cover
one four-pose shape orbit: two source poses were absent from acquisition, and two
repeat acquisition sources. This does not establish new-shape, new-mechanic, or
new-game generalization.

## Reproduce

From `D:\planet\qtube`, choose a new output directory (existing results are never
overwritten):

```powershell
python qgame_loop.py --seed 0 --checkpoint models_r6_ports_clean/dist_s0.pt --out game_loop_ls20_new
```

The existing Python 3.12 ARC environment runs the engine in a separate process;
the main Python environment runs Torch. No package installation or mutation of
either environment is needed.

Files:

- `qengine_rpc.py`: JSONL worker around public OFFLINE engine APIs. Preserves all
  returned animation frames and official scorecard counts.
- `qrecording.py`: observation-only demonstration alignment, glyph/body extraction,
  bootstrap discovery, and empirical inverse movement. Selective AST loading of
  existing extractor functions avoids importing the full agent or its journals.
- `qtransition.py`: learned contact quaternion, set-valued D4 evidence, covariance
  pose loss, multiple fit starts, and conservative contact planning.
- `qgame_loop.py`: fresh acquisition, frozen verification, bounded plan execution,
  and failure/scorecard capture.

Each output directory contains `transitions.jsonl`, `frames_actions.npz`,
`engine_stderr.log`, and `summary.json`. Prediction records are flushed before
the corresponding engine request. Exactly two contact transitions train the
operator; frozen prediction and plan outcomes do not update it.

## Explicit priors and remaining work

The supplied priors are the D4 geometry, quaternion/moment transformation law,
frozen synthetic encoder, existing crop/body extractors, a HUD crop taken from
earlier observations, demonstration navigation, and an experimental target.
Object segmentation, navigation discovery, and game-goal discovery are not
learned in this experiment. The glyph crop is the CLI's `--region` argument.

The acquired quantity is which geometric effect a particular within-level contact
causes. The loop checks body position, unchanged glyph while stepping away,
colour, episode state, level, resets, and the predicted next glyph. It stores full
frames but does not yet predict the complete scene or every changed object.

Recolouring, reshaping, deletion/spawn, conditional effects, and changed contact
gates require additional state/effect models. The current experiment abstains
when these invalidate its scope. New contexts should get new rules rather than
binding all objects of one colour to a global quaternion.

The next useful step is autonomous object/contact discovery and target binding,
then learning non-pose effects and preconditions. Only after that should this be
tested as a game-solving policy or wired into the Kaggle entry. The primary-paper
review in `LITERATURE_GAPS.md` explains the evidence for that direction and the
assumptions in each source.
