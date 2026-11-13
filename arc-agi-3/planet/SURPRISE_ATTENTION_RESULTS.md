# Surprise, object-relative conditions and movable attention

## Result — 2026-09-10

**The movable gaze helps a designed visibility failure, not a changed rule.**
Backing off an invalid rule limits damage, but the first monitor is too sensitive
to ordinary noise. No new rule was validated on the saved ARC replay. Do not
promote this experiment into the submission on these results.

233 focused tests pass, including 14 new tests. The broader experiment completed
120 synthetic cases and read 8,004 saved observations in 96.438 seconds. Unit
tests check software invariants, not leaderboard performance.

### Synthetic evidence

Mean Brier loss; lower is better. Each family has 20 seeds. These are predictive
losses, NOT ARC scores. The table isolates the attention and support mechanisms.

| Family | Fixed gaze, frozen | Shifting gaze, frozen | Shifting gaze + demotion | Rolling fallback |
|---|---:|---:|---:|---:|
| Stable local rule | .000235 | .000235 | .000235 | .257374 |
| Object relocates beyond gaze | .491206 | .015368 | .015368 | .257374 |
| Rule reverses after checking | .969782 | .969782 | .345507 | .256098 |
| Stable rule with 20% flips | .164584 | .164584 | .187482 | .257471 |
| Independent random outcomes | .257258 | .257258 | .257258 | .257258 |
| Occlusion, on matched events only | .000364 | .000364 | .000364 | .260241 |

- Relocation: one gaze shift in each of 20 cases; none of those rules was demoted.
  Fixed gaze + demotion instead lost support in all 20 cases, with loss .291682.
  **Full-view features remain better**, at .000235; the shift does not beat access
  to the complete relevant view. The relocation case deliberately favours refocusing.
- Actual rule reversal: all 20 monitored rules were suspended, starting after
  eight wrong predictions. Loss fell, but still exceeded fallback because those
  first eight errors count. The reversed relationship was NOT re-learned.
- Noise: 11/20 useful rules were also suspended. This worsened mean loss from
  .164584 to .187482; one case even underperformed fallback. A short fixed window
  is not a reliable noise-versus-drift discriminator.
- Stable and matched-occlusion cases: no demotions. Every occlusion case excluded
  52/256 trials with a missing object; retained 204. Missing is not no-motion.
- No-signal cases: no rules accepted. Shifting still moved 56 times without any
  predictive gain: attention also needs a usefulness/cost check.

Across the artificial family mix, full-view frozen loss was .232076; full-view
with demotion .131847; shifting gaze + demotion .134369; fallback .257636. These
case-weighted aggregates depend on the deliberately chosen stress mix. The
combined method beat fallback in 79 cases and lost in 21. Do not hide those losses
behind the aggregate improvement.

### Real saved-game evidence

8,004 observations; 200 excluded boundary/terminal/nonordinary observations;
7,804 ordinary transitions; 213 ambiguous/unmatched probes; 7,591 matched probes.
After separate-context grouping, 251 groups containing 6,348 matched events were
too short. Eight groups with 1,243 events qualified, all LP85/action6. CD82, LS20
and VC33 supplied no group long enough under this protocol.

All eight qualified groups rejected their proposed full-view condition for
insufficient check-period contrast. Every method validated **zero rules**, made
zero gaze shifts, and used the same fallback. Across the 314 final test events,
the selected probe never moved. Mean Brier .000865 consequently reflects an easy
stationary-probe prediction, **not successful control or useful game learning**.
The generic largest-unique-component locator has not established action relevance.

The source archives were unchanged. The original notebook SHA256 remains
`7ace657bfbec62e681caaa369d1e3726396e8621134b554a40872aa8666add88` and channels-v2
remains `a95002f5fd81ad3950bfdfe997efc576e05f4fff0e1574cf7bee4ce13a72da0f`.

## Scope

This is an isolated offline experiment. It does not change the live ARC policy,
the original .25 notebook, the prepared channels-v2 notebook, or any submission.
No environment source was inspected and no game actions were spent.

The user's eye/ring idea is represented by a **movable logical gaze window**.
The existing fixed-eye cube geometry is untouched. The window has a fixed
Chebyshev radius of six pixels; neither ring radius nor physical eye placement
is learned. Light/sound/magnetism are not simulated physical fields here.

## Operational definitions

- **Object probe:** BEFORE-action four-connected, same-colour components, ignoring
  the frame's most common colour (deterministic tie-break). Select the largest
  uniquely shaped component of 2–64 pixels whose bounding extents are below 12
  pixels; tie-break by colour then position. No palette-specific player rules.
- **Measured outcome:** that BEFORE-selected component has a unique matching
  colour/translated shape AFTER the action, within 12 pixels, and its origin
  moved. Ambiguous matches, disappearance, shape changes and larger jumps abstain.
  Matching appearance is a heuristic, not proof of persistent object identity.
- **Object-relative inputs:** one- and two-pixel bands beside the component's
  four bounding-box sides. Each has an `observed` flag and a
  `visible_material` flag. Unseen is not asserted to be empty. Component centre
  visibility and coarse left/top position are additional BEFORE-only features.
- **Surprise:** Brier loss above .25 after an already-issued forecast. A shifting
  gaze then moves to the matched component's AFTER centre. This can affect only
  later forecasts; previous predictions/outcomes are not rewritten.
- **Lost support:** over eight scored events, a checked rule's mean Brier loss
  exceeds the rolling unconditional baseline by more than .10. Suspend that
  rule starting with the next forecast; retain its model and eight-event evidence.
  One isolated error does not automatically demote it.
- **Fallback:** Laplace-smoothed outcome frequency over the preceding 32 events,
  shared by all variants. Score each outcome before updating this window.

This is a coarse-to-fine attention proxy: full-frame segmentation still locates
the object, while gaze gates fine neighbouring features. It is NOT a demonstrated
sensor-bandwidth saving. It does not yet locate the controllable player, learn
object identity, or prove a causal action effect. A stationary decoration can be
chosen instead of a player. All alternatives use the SAME chosen target and
the SAME matched-event coverage, so changing gaze cannot change the scored target.

## Comparison protocol

Seven alternatives: colour-only, full-view object features, fixed local gaze,
and surprise-shifting gaze; each object-feature view is tested with a frozen
rule and with demotion. “Frozen” refers to the checked conditional rule; the
unconditional fallback still updates identically in every alternative.

The existing three-channel reactor selects one feature on the first 50% of
matched events, then verifies on the next 25%. Four observations per boolean
branch and at least .01 Brier gain are required in both periods. There is no
validation-driven reselection. Final 25% uses **prequential evaluation**:
forecast, score, then update monitoring/attention for the next event. This is
not a frozen holdout for the adaptive mechanisms. Parameters were fixed before
the broader run; synthetic unit tests verify designed behavior, not generalization.

120 synthetic cases: seeds 100–119, 256 scene pairs per case, six families:
stable local obstacle rule, object relocation beyond gaze after the check period,
rule reversal after checking, 20% random flips, independent random outcomes,
and periodic object disappearance. The whole-frame palette is constant and an
irrelevant HUD pixel moves every trial, including stationary-object trials.
Occlusion is excluded as unknown and explicitly counted, not scored as no motion.
These are constructed observation pairs, not a live game dynamics benchmark.

Real replay opens the four candidate-run SQLite archives in
`D:\planet\arc_compare\orbital_channels_v2_four_games` read-only, checks
decompressed payload hashes, and hashes source archives before/after.
Groups are separate by archive/run, continuous boundary segment, game, level
and action. Resets/deaths/level/session changes cannot bridge a rule's fit/check
or test period. Groups need at least 128 matched events. This segmentation and
the object-displacement target differ from the earlier frame-change experiment;
their aggregate losses cannot be directly compared as if they were the same task.

## Reproduction

Implementation: `surprise_attention.py`.
Experiment: `experiment_surprise_attention.py`.
Tests: `test_surprise_attention.py`.
Raw results: `D:\planet\arc_compare\surprise_attention_20260910\results.json`.
The JSON records source hashes, archive hashes, individual predictions,
before/after gaze positions, demotion evidence, skipped groups and coverage.

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_surprise_attention -v
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B experiment_surprise_attention.py --archives 'D:\planet\arc_compare\orbital_channels_v2_four_games' --output 'D:\planet\arc_compare\surprise_attention_next_run'
```

Output directories must be new. No prior experiment is overwritten.

## What remains outside this implementation

The strongest next test is an action-responsive object locator trained on PAST
movements, with ambiguity tracking, so a stationary decoration cannot monopolize
the question. It needs evaluation coverage for all four games, not just LP85.

There is also a representation caveat in the gaze test: the one-feature learner
can select `visible_material` without making `observed` a mandatory prerequisite.
The boolean describes visible material, not actual absence beyond the gaze, but
the fitted predictor can still overgeneralize across visibility loss. Before
deployment, compare against an explicit unknown-aware gate/compound condition.
Refocusing's benefit here does not establish that it is better than correct
missing-data handling; that control has not been implemented in this experiment.

Suspension is not repaired knowledge. Re-learning a replacement requires new
fit/check evidence and a separately evaluated promotion loop. This version does
not automatically re-promote rules, synthesize two-condition compounds, learn
ring radii, or implement temporal frequency/phase coupling. A small check split
and a regret threshold do not guarantee freedom from false acceptance/demotion.
