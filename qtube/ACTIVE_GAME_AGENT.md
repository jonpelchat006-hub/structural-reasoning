# Active quaternion agent: first real level

November 1, 2026. The active branch completes the first public `ls20` level in
**25 official engine actions, zero resets**, across three model seeds. It uses no
LLM, saved demonstration route, supplied display crop, or target coordinates.
This is development on a known public level, with explicit perception and
geometry priors. It is not a completed game, hidden-set result, or evidence that
quaternion matching beats a symbolic D4 solver.

## What it discovers and learns

1. Probe each initially available noncomplex action once. Infer action directions
   from actual body displacement. No action ID is assigned a direction beforehand.
2. Infer the likely traversable surface from pixels revealed when the body leaves.
   Select a small nonfloor island as a contact hypothesis. Its coordinates and
   colours come from the current image.
3. Approach that object through predicted floor cells, checking every movement.
   The first contact changes an enclosed glyph panel while another compatible
   panel remains constant. That identifies a state-display hypothesis and crop.
4. Observe a second contact. Preserve all compatible D4 laws: the first example
   leaves `{3,4}`, the second leaves `{3,6}`, and their intersection is `{3}`.
   Fit a quaternion to both observed next poses using the frozen mean/covariance
   encoder. Training fit and exact reconstruction must pass before planning.
5. Select one visible enclosed glyph with compatible shape and colour as a goal
   hypothesis. Plan three contacts to match it, predicting and verifying each.
6. Navigate to the candidate box. Entry remains an unverified probe until the
   engine reports a level increment. The loop stops immediately after that increment.

Action decomposition: **4 control probes + 6 object-approach steps + 2 steps for
the second acquisition contact + 6 planned contact steps + 7 target-navigation
steps = 25**. The first contact is included in the object approach.

## Verified results

| Run | First contact | Acquired contacts | Planned contacts correct | Actions | Resets | Levels |
|---|---:|---:|---:|---:|---:|---:|
| `game_active_ls20_s0` | 10 | 2 | 3/3 | 25 | 0 | 1/7 |
| `game_active_ls20_s1` | 10 | 2 | 3/3 | 25 | 0 | 1/7 |
| `game_active_ls20_s2` | 10 | 2 | 3/3 | 25 | 0 | 1/7 |

Each run uses its corresponding frozen synthetic encoder and quaternion fitting
seed. These are three model initializations on the same deterministic public
level, not three games or an untouched test set. There are zero extra frozen
holdout contacts; the three frozen planned-contact predictions are the execution
checks. The first ambiguous acquisition prediction can be wrong and is explicitly
marked unverified.

The official local scorecard agrees with the action/reset/level counts. Its
first-level human baseline is 22 actions, first-level efficiency score is 77.44,
and aggregate score across all seven levels is 2.7657142857142856 (the remaining
six levels are uncompleted). The environment is still `NOT_FINISHED`.

All 25 prediction records precede their corresponding observation records.
The code stops after the first level increment; no new-level action is sent.

## Resource constraint found during development

The earlier goal run used a 26-action demonstration prefix plus unnecessary
verification contacts. It correctly matched the target, then reset at action 46
while navigating. The frame history shows a strip exhausting and refilling with
the body/display reset.

`qbudget.py` now discovers the strip's position and colours from observations,
estimates drain per action, and reserves capacity for contact and navigation.
It does not assume that every shrinking strip is a proven death counter.
`can_afford` is conditional on future consumption staying within the observed
maximum. Unknown, ambiguous, or reset/refill-uncertain meters do not authorize
a budget-dependent plan.

For the demonstration branch, the resource check automatically reduces four
requested optional verification contacts to three. This leaves a 13-action plan
within the observed 15-action capacity and completes the first level in 41
actions (`game_goal_ls20_budget_s0`). The active branch avoids the demonstration
detour and completes it in 25.

## Additional effect memory

`qeffects.py` stores effects by `(level, contact ID, context, guard)`. Geometric
support, colour mappings, and exact-state reshaping are separate hypotheses.
Objects sharing a marker colour are not assigned a global effect.

The recorded-data audit extracts 20 changes: 15 pose effects, four recolours, and
one reshape across six contact scopes. Nine predictions supported before the
next observation are correct; eleven abstain. The recolour and reshape examples
are mostly acquisition evidence, not unseen-effect prediction tests. Shape
changes remain lookups, and opaque contexts/guards are supplied keys rather than
learned conditions. This effect memory is not yet a general mixed-effect planner.

## Reproduce

From `D:\planet\qtube`, use a fresh output directory:

```powershell
python qgame_loop.py --bootstrap active --goal visible --navigate-goal --holdout 0 --seed 0 --checkpoint models_r6_ports_clean/dist_s0.pt --out game_active_ls20_new
```

The successful development runs explicitly passed nonexistent `--demo-frames`
and `--demo-actions` paths to confirm those inputs are unnecessary in active mode.
The active branch never calls the demonstration loader or bootstrap finder.

The existing ARC Python environment serves public observations through
`qengine_rpc.py`; the main Torch environment performs geometry learning. Neither
environment was modified. All outputs stay in the selected run directory.

Relevant modules: `qbootstrap.py`, `qscene.py`, `qnav.py`, `qbudget.py`,
`qtransition.py`, `qmoments.py`, and `qgame_loop.py`. Each run retains full returned
animation frames, actions, predictions, training evidence, and official scorecard.

## Explicit limits and next work

The body detector is supplied and game-informed: a five-by-five, two-tone strip
pattern with colour exclusions inherited from the existing observer. The visual
component/enclosure rules, object-area limit, D4 group, and synthetic encoder are
also priors. Display/target coordinates and contact semantics are acquired, but
this is not perception learned from arbitrary pixels.

The current controller requires one unambiguous small contact-object hypothesis
and a pose-compatible target. It abstains for unresolved objects, recolouring,
reshaping, conditional effects, or unsupported navigation. It does not carry this
rule blindly into the next level. General object identity, multiple-object probe
selection, effect guards, and mixed-effect planning are the next steps.

The Kaggle notebook still needs a portable adapter, broader evaluation, and
integration. These local results do not establish the state of a submitted entry.
