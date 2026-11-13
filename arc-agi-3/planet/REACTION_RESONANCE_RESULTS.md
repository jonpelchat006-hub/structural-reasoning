# Three-channel reaction experiment — 2026-09-10

## Outcome

The implemented selector can learn a planted one-condition relationship, but
the three-channel combination did not outperform an ordinary prediction-error
selector. On the actual saved ARC observations it validated no new rules.
Do not promote this experiment into the live game policy on these results.

No live agent or notebook was changed, no game actions were taken, no submission
was made, and source archives were opened read-only and hashed before/after.

## What was tested (and what was not)

`reaction_resonance.py` gives the proposed channel names operational meanings:

- Light: exact decoded semantic, scope, action-target, and before-action matching
  through the existing `PinCodebook`/`Message` types. Colour is not meaning.
- Magnetism: a condition pin can supply a boolean precondition for the outcome
  question. Its score is balanced observed support for the condition and its
  complement: `2 * min(n_false, n_true) / n_fit`.
- Sound: observed prediction residual, measured as Brier loss (mean squared
  probability error). Quieting is the fractional fit-loss improvement over an
  unconditional predictor. Missing input is not a zero residual.
- Three-channel resonance: geometric mean of semantic compatibility, balanced
  support, and quieting. Zero useful quieting remains zero; no positive floor.

A reaction is a candidate composition: a measured boolean feature plus a
question becomes a two-branch probabilistic prediction. This does not simulate
light, sound, magnetism, oscillatory frequency/phase coupling, Navier–Stokes, or
theta. In particular, this first test covers residual amplitude, not acoustic
rhythm/resonance. The numerical mappings are design choices, not physical laws.

The five selectors receive the SAME admissibility guards and observations:
raw colour affinity (650 nm reference), compatibility-only (balanced support),
residual-only (ordinary one-feature prediction-error selection), three-channel,
and shuffled-sound (negative control). Raw colour matching is intentionally a
weak comparison: pin-local colours are arbitrary. Its performance is not evidence
that an alternative physical model of light failed.

## Protocol fixed before the result

- 140 synthetic cases: seven families, 20 seeds each, 128 events per case.
- Chronological fit/check/test split: 50% / 25% / 25%.
- Laplace-smoothed unconditional fallback and two-branch predictors.
- Minimum four distinct event IDs per branch in both fit and check.
- Fit-selected candidate must improve Brier loss by at least .01 in BOTH fit and
  later check sets. Only one candidate is checked; rejection cannot reselect.
- Fixed lexical tie-breaking. Test outcomes never affect selection, fitting,
  thresholds, or acceptance. Final test is deliberately frozen, with no adaptation.
- At most 64 candidate feature inspections per proposal.
- Missing conditions, after-action labels, wrong scope/action, requested rather
  than observed inputs, corrupted symbols and duplicate candidates are rejected.
- Repeated delivery of one event ID adds no support. IDs/chronology do not prove
  statistical independence; this remains a small observational experiment.

## Synthetic results

Lower Brier loss is better. An unaccepted candidate uses the unconditional
fallback. Means weight cases equally, not events. "Accepted" means it passed the
check-period gate, not that its final test prediction was correct.

| Family | Cases | Three-channel accepted | Final Brier | Fallback Brier |
|---|---:|---:|---:|---:|
| Clear single-condition rule | 20 | 20 | .000881 | .249756 |
| Same, with 20% random flips | 20 | 19 | .171161 | .255028 |
| Independent random outcomes | 20 | 2 | .257907 | .258290 |
| Fit-only misleading relationship | 20 | 0 | .257825 | .257825 |
| Rule reverses AFTER validation | 20 | 20 | .941815 | .255249 |
| Two-feature XOR | 20 | 1 | .261137 | .260893 |
| Disconnected, quiet input | 20 | 0 | .000230 | .000230 |

The residual-only selector produced identical final results in all 140 cases.
Thus this sample supplies no incremental predictive benefit for the combined
resonance score. This does not establish equivalence on all datasets.

Across all deliberately mixed families, three-channel mean loss was **.270136**
versus fallback **.219610**: the aggregate result is WORSE, dominated by the
post-validation reversals. It improved 40 cases and worsened 22. Colour-only,
compatibility-only, and shuffled-sound means were .220018, .231423, and .226968.
Those weaker selectors can look safer by accepting fewer candidates; acceptance
counts alone are not a success metric.

Two of the 20 no-signal cases passed the gate by chance. One XOR case also passed
without a supported single-feature mechanism and worsened on test. A branch quota
and one check split are NOT a calibrated false-discovery guarantee.

The reversal case is a designed stress test, not an estimate of how often ARC
rules change. It demonstrates that earlier agreement cannot certify later context.

## Saved-game replay

Source: `D:\planet\arc_compare\orbital_channels_v2_four_games`.
Read 8,004 journaled observations from four candidate-run archives; excluded 200
bootstrap, boundary, terminal or nonordinary transitions. No environment source,
hidden target answer, or live API was used.

Grouped remaining examples by exact game version, level and action, then used
chronological halves/quarters within each group. Groups below 128 examples were
excluded and individually listed in the JSON report. Seven groups remained:
CD82/action6, LP85/action6, VC33/action6 and LS20/actions1–4 (all level 1).

Predictor inputs were the existing 16 BEFORE-frame colour-presence booleans.
Target was exact returned-frame inequality, which may include animation or HUD
change; it is not a movement/progress/causal label.

**0/7 groups validated a new condition under every selector.** Five groups had
no feature with enough fit-period contrast; two LS20 groups selected a feature
but lacked enough check-period contrast. All selectors consequently used their
fallback, with equal mean Brier loss **.0629783**.

This pinpoints a feature/coverage limitation in this replay, not a proof that
no useful relations exist. A full colour being present almost all the time does
not expose which object is controlled or whether its next square is blocked.

## Tests, reproducibility and next hypotheses

219 focused tests passed, including 14 new reaction tests. Code tests verify
invariants, not a scientific claim of increased intelligence. Cases include
recoding invariance, duplicate evidence, opaque/missing input, wrong time/scope,
after-action leakage, budget bounds, and an explicit regression under future shift.

Raw results and source/input hashes:
`D:\planet\arc_compare\three_channel_reactions_20260910\results.json`.

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_reaction_resonance -v
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B experiment_reaction_resonance.py --archives D:\planet\arc_compare\orbital_channels_v2_four_games --output D:\planet\arc_compare\three_channel_reactions_next_run
```

The output directory must be new. The experiment does not overwrite a prior run.

Useful NEXT tests, not implemented claims:

1. Measure object-relative preconditions and object displacement, rather than
   whole-frame colour presence and generic frame change.
2. Evaluate online residual monitoring and reversible demotion/context splitting
   under a fixed protocol. Do not learn a test answer before scoring that event.
3. Test two-condition compounds (including XOR) rather than assuming that a
   stronger resonance score can compensate for an inadequate hypothesis class.
4. If adding a true temporal channel, measure event-lag/phase relationships and
   compare against the same conventional temporal predictor. Additional frequency
   labels alone cannot contribute new evidence.

Keep actual game-action cost separate from heuristic learning credit. This
experiment spent zero game calls and does not change any remaining action budget.
