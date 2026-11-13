# Automatic pin refinement: first working loop

2026-09-09. Offline implementation, not an ARC score or a live agent update.

## What is now automatic

`automatic_pin_refiner.py` examines an EvidencePin's recorded boolean factors
and outcomes. It chooses a split feature and learns the absent/present outcome
predictions, instead of the caller specifying those to `lift()`. Accepted local
refinements keep the original observations, parent rule and counterexamples.

No existing code, runtime configuration, report, notebook or submission was
modified. The new files use the previous EvidencePin and ExternalEyeCircuit APIs.

## Selection and checking

The caller assigns observation IDs to disjoint fitting and checking cohorts
before inspecting outcomes. Defaults require at least two fitting and two
checking observations PER branch; these are coverage quotas, not probabilities
or proof of statistical independence. Four eye deliveries of one observation
still count as one trial.

For each active leaf, the learner:

1. Selects fitting observations matching the leaf's conditions. Missing parent
   context blocks refinement rather than being treated as false.
2. Tries each declared unused boolean factor. Both branches must have enough
   fitting examples, internally consistent outcomes, and different predictions.
   Missing factor measurements cannot silently drop difficult examples.
3. Abstains if no factor qualifies. If several qualify, it emits a question
   containing concrete assignments on which two hypotheses disagree. It does
   not break a tie alphabetically or use checking outcomes to select the winner.
4. Checks the unique fitting candidate against the disjoint checking cohort.
   Both branches need support and zero observed prediction errors. Failure does
   not trigger a search for a different feature on those checking outcomes.
5. Lets all retained evidence veto unresolved contradictions/missing context,
   even if omitted from both cohorts. Unassigned evidence cannot promote a rule.
6. Installs at most one local candidate split, then requires a fresh inspection.

`inspect()` is read-only. `apply()` re-computes the proposal and rejects altered
or stale proposals, including changes to evidence, scope, model or policy.
`step()` combines inspection and application. The API assumes one synchronous
owner; it is not thread-safe, an authenticated boundary, or a game-action grant.
Rule-budget exhaustion raises an error without changing or evicting evidence.

Do not use the unassigned-record veto as an excuse to put final evaluation data
inside the pin. Keep final evaluation separate and freeze both model and evidence.
Checking data used repeatedly during development is not a final unbiased test.
Real cohorts should separate episodes/time blocks to avoid near-duplicate leakage;
different IDs by themselves cannot establish independent trials.

## Demonstration and results

`demo_automatic_pin_learning.py` supplies a toy environment where an action
succeeds iff contact AND blue wall are present. It declares those measured
features plus an irrelevant wobble feature. The environment, feature extractor,
and sequence of contexts remain hand-authored; neither the split choices nor
the branch predictions are passed to the learner.

- First eight trials reveal the contact distinction. The learner chooses contact.
- Four further trials expose a colour-dependent failure inside contact-present.
  The learner chooses blue-wall for the second lift.
- All 12 fitting/checking observations remain unchanged through both lifts.
  There are 48 routed view receipts, not 48 independent trials.
- A frozen model then predicts eight further feature combinations: 8/8 correct,
  zero abstentions. Evaluation outcomes never enter the pin or alter its model.
- All 20 toy actions use the external port; outstanding requests finish at zero.

This is genuine automatic selection within a supplied vocabulary, but a small,
designed demonstration—not autonomous pixel understanding or ARC generalization.

## Deliberate limits, tested rather than hidden

The first learner requires a clean, unique ONE-STEP split. It does not install
constant predictions, tolerate noisy labels, invent new features, or search
multi-level trees at once. On all 16 two-input boolean truth tables presented
up front, it installs only a, not-a, b and not-b; it abstains on the other 12.
That includes AND/OR/XOR when no first split yields pure branches. The staged
demo learns AND because an earlier context subset supports a first split before
later counterexamples require a second. Its curriculum is a meaningful limitation.

Other tests cover tied/correlated factors, a new observed contrast resolving a
tie, failed checks, missing features, unknown parent context policy, duplicate
eye receipts, retained counterexamples, stale/edited proposals, rule budgets,
and arbitrary feature names/colours. Asking a question does not fill its gap.

## Reproduce

From this project directory:

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_automatic_pin_refiner -v
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B demo_automatic_pin_learning.py
```

The demo prints JSON; no game API, model API or output-file write is performed.

## Next connection to real games

Reuse the observed-transition machinery in `induce.py` to supply named measured
conditions with raw before/after provenance. Then replay separate ARC episodes
through this learner, measuring prediction errors AND abstention/coverage.
The emitted disagreement questions still need reachability/budget handling and
an adapter to the existing experiment queue. Durable checkpoints, deeper bounded
search and planner integration remain unimplemented. The current PriorAgent's
learned effects also need to influence its planner to produce gameplay value.

In the vortex metaphor: raw "grains" remain in the trial ledger, a candidate
rule is a reusable summary, and a contradiction sends that summary back for
refinement. Neither recirculation nor a 3-6-9 identity creates new evidence.
