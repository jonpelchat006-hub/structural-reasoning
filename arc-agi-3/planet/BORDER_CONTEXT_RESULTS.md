# Border pins as outside-context contracts — 2026-09-12

## Result

**Outside context repairs the designed local-view failures; border pins add
explicit obligations/provenance, not extra predictive power over that same
context supplied normally.** Missing-data guards prevent unjustified suspension
when the required condition cannot be observed. They do not distinguish every
possible causal failure or learn replacement rules.

250 focused tests passed, including 17 new border tests. The broader experiment
completed 180 synthetic cases and read 8,004 saved observations in 177.265 seconds.
There is no demonstrated ARC leaderboard gain and no live promotion/submission.

### Synthetic results

Lower Brier loss is better. Means weight each of the 20 cases in a family equally.
Outside-plain and border-context predictions were IDENTICAL on every evaluated
event, with an explicit equality assertion. Losses below are not ARC scores.

| Family | Inside naive | Inside guarded | Outside / border | Fallback |
|---|---:|---:|---:|---:|
| Stable rule | .000235 | .000235 | .000235 | .258423 |
| Object leaves local view | .290283 | .258423 | .000235 | .258423 |
| Rule reverses after checking | .348396 | .348396 | .348396 | .259555 |
| Stable rule, 20% random flips | .172857 | .172857 | .172857 | .260516 |
| Independent random outcomes | .255640 | .255640 | .255640 | .255640 |
| Occlusion, matched events only | .000369 | .000369 | .000369 | .254502 |
| Outside context unavailable | .290283 | .258423 | .258423 | .258423 |
| Outside context stale | .290283 | .258423 | .258423 | .258423 |
| Triangle/slot exact-fill contract | .290283 | .258423 | .000235 | .258423 |

When the object leaves local view, the naive method suspends all 20 useful rules.
The guarded local method suspends none but cannot resolve the question; outside
context supplies the missing condition and preserves accurate predictions.
The triangle/slot example shows the same pattern under its supplied exact-fill
definition. The two designed families each contain 563 local loss-above-.25
predictions corrected by providing context (1,126 total). These are comparisons
of model inputs, not counts of improved game actions.

In unavailable/stale-context families, each has 1,280 final events with a missing
selected condition. The guarded models use fallback and suspend zero rules.
The stale-context family rejects 10,240 individual pin bindings (eight pins per
event), not 10,240 independent observations. A duplicate view cannot multiply
evidence. Relocation produces 160 bent bindings; translated triangle destinations
produce 20. Geometry changes are explicit transport operations, not learned
physical pin behavior or proof of the origin of earlier border mechanisms.

All 20 genuinely reversed rules are suspended, but final loss still exceeds
fallback because detection takes eight observed errors. Five noisy-but-useful
rules are also suspended. That noise failure persists; the difference from the
previous seed set's 11/20 is NOT evidence that the monitor was improved.

Across this artificial nine-family mixture, mean losses are .215403 naive,
.201243 guarded-local, .143868 outside/border, and .258036 fallback. Outside/border
beat fallback in 99 cases and lost in 21; 60 tied. The mixture includes deliberately
favourable geometry tasks and is not an estimate of real-game prevalence.

### Saved-game outcome and limitations

8,004 observations, 200 boundary/nonordinary exclusions, 7,804 eligible
transitions, 213 ambiguous/unmatched probes and 7,591 matched events. Of these,
6,348 events in 251 groups are below the minimum length. Eight groups with 1,243
events qualify, all LP85/action6. The other three games have no qualifying group.

Every candidate is rejected for insufficient check-period feature contrast.
Across all 314 test events, the chosen probe does not move. All methods use the
same fallback, with mean Brier .000865; this is a stationary-probe prediction,
not useful control or a new validated game rule. Reported selected-condition
missing counts are zero because there is NO accepted condition, not because all
possible questions have been answered. Object selection and coverage still
block a meaningful game-learning test of this mechanism.

Next priorities: identify action-responsive objects using past evidence; evaluate
unknown-aware border/context features on their outcomes; then test noise-aware
rule replacement using separate later evidence. Missing context and an incorrect
rule can coexist, so an exposed pin cannot certify that the rule remains correct.

## What this experiment means

A border pin is an explicit request for an outside-region predicate, attached
to the selected object's bounding-box edge. A blank layer alone supplies no
facts. Local and outside views are masked subsets of ONE before-action frame;
they are not independent witnesses or extra cameras.

- **Exposed:** some required pixels are unobserved. Value is `None`, not False.
- **Bound:** the exact requested region is observed in the matching scope,
  event, step, before phase and frame version.
- **Bent:** a fresh binding updates the anchor or external region after motion,
  while keeping the same object-shape/predicate role. This tests translation,
  not general learned rotation or deformation.
- **Broken binding:** a proposed source is stale, cross-scope, wrong-frame or
  wrong-phase. Reject that binding without erasing its history or the object.
- **Changed context:** an observed predicate changes value. This is not itself
  a broken rule: conditional rules must be allowed to follow changing inputs.
- **Observed prediction error:** a prediction with the required context was
  wrong. This can challenge a rule, but is NOT proof of the causal failure source.

The binding ledger retains provenance and deduplicates deliveries of the same
event/feature. Copying evidence through two views gives the same evidence ID.
Hashes and equality checks are integrity bookkeeping, not an authentication or
encryption system against a malicious caller.

The existing `border.py` implements a mail ticker, not these context contracts;
it is untouched. Existing channel, cube geometry, live policy and notebooks are
also untouched. The new module has no game-action execution path.

## Protocol fixed before the broader result

180 constructed cases, seeds 200–219, nine families of 256 observation pairs:
stable obstacle rule, local object relocation, rule reversal, 20% outcome flips,
independent random outcomes, object occlusion, unavailable outside context,
stale outside context, and triangle/slot exact-fill. Occlusion excludes unmatched
outcomes as unknown. The three new context/shape families are designed mechanism
tests, not evidence of discovered game semantics.

Triangle/slot scenes provide the source object, destination coordinates and an
EXACT-FILL criterion. They alternate a matching triangle region and a square
region. A smaller triangle may physically fit inside a square hole; that is not
the task here. The feature directly computes the supplied exact-shape relation,
so success demonstrates correct context access/transport, not learned geometry
or autonomous discovery of what a destination is. The destination translates
after checking to exercise bending.

All four variants share the SAME full-context before-action fit/check history
and SAME object outcomes. This isolates TEST-TIME context delivery; it does not
compare learning from an inside-only history with learning from a full view.
Chronological split: 50% fit / 25% check / 25% prequential test. Existing reactor
selects one condition, requiring four examples per boolean branch and .01 Brier
improvement in fit AND check. No reselection against check/test answers.

Four matched alternatives:

1. **Inside naive:** unavailable selected condition is treated as False, the
   deliberately weak comparison that recreates the previous visibility failure.
2. **Inside guarded:** unknown condition uses the rolling unconditional fallback
   and cannot count against the conditional rule.
3. **Outside plain:** ordinary observed external-region features, with source
   freshness and missing-data checks, but no border graph/ledger.
4. **Border context:** same observed facts through explicit border requests,
   bindings and their lifecycle/provenance ledger.

All share a 32-event Laplace-smoothed rolling fallback. Conditional models stay
fixed unless suspended. Eight consecutive usable predictions with mean excess
Brier loss above .10 suspend a model after scoring the eighth event. Missing
conditions clear that comparison window. No replacement-rule learning or
re-promotion occurs. The earlier noise-sensitive threshold is kept unchanged;
this is not a calibrated change detector.

Outside context can be read BEFORE the current action prediction; it is already
part of the supplied game observation. No later outcome is used for the current
forecast, object selection or feature value. Outcomes are scored before monitor
updates. “Recovered with context” compares two forecasts on the same observation;
it is a model/input comparison, not a causal intervention on the game.

## Saved ARC replay

Read-only source: `D:\planet\arc_compare\orbital_channels_v2_four_games`.
Reuse the prior generic object probe: largest unique compact same-colour shape,
matched by translated appearance. It is NOT an identified controlled player.
The question remains whether that selected probe displaced, not whether a move
was useful or whether the task progressed. No environment source is read.

Archive/run, game, level, action and continuous reset/death boundary segment
remain separate. A group needs 128 matched events. This intentionally preserves
the earlier coverage limitations; we did not tune grouping or object selection
after seeing failures to produce a positive replay result.

## Reproduction and artifacts

Implementation: `border_context.py`.
Experiment: `experiment_border_context.py`.
Tests: `test_border_context.py`.
Raw report: `D:\planet\arc_compare\border_context_20260912\results.json`.

The report contains source/archive hashes, every test prediction, per-family
results, first-test pin coordinates/provenance, lifecycle counts, exclusion
counts, check rejection reasons, and rule-suspension evidence. Source archives
are opened read-only, payload hashes checked, and input hashes verified again
at completion. Each output directory must be new.

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_border_context -v
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B experiment_border_context.py --archives 'D:\planet\arc_compare\orbital_channels_v2_four_games' --output 'D:\planet\arc_compare\border_context_next_run'
```

Neither the .25 submission notebook nor channels-v2 was changed. Their SHA256s:

- Original: `7ace657bfbec62e681caaa369d1e3726396e8621134b554a40872aa8666add88`.
- Channels-v2: `a95002f5fd81ad3950bfdfe997efc576e05f4fff0e1574cf7bee4ce13a72da0f`.

No game actions or submissions were made. Software tests do not establish a
leaderboard gain, and geometry/provenance labels alone do not add information.
