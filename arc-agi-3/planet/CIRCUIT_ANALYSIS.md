# Pin circuit diagnostics and bounded priorities

2026-09-09. A read-only analysis layer over EvidencePin; no live ARC actions,
submission changes, physical electrical simulation or automatic rule mutation.

## Measured state versus supplied estimates

`circuit_analysis.py` provides CircuitProbe. Sample a pin at monotonically
increasing observation-clock steps, then request a budgeted priority report.

- Structural height is retained for layout and excluded from priorities.
- Declared need is the maximum of a basic sample-coverage deficit, an unresolved
  prediction contradiction, missing branch context and a missing rule. The
  last three are binary flags. This is not entropy, calibrated uncertainty,
  expected information gain or a guarantee of complete knowledge.
- Potential (the "voltage" analogy) is declared need times a caller's estimated
  decision impact in [0,1]. Unknown impact produces unknown potential.
- Estimated cost (the "resistance" analogy) is a positive cost in one explicit
  unit system. Unknown cost is not zero. Physical resistance is not calculated.
- Effort (the "current" analogy) comes from receipts of actual work already
  done, not scheduled work. A receipt can reference returned observations or
  have an empty list if work produced no usable observation. A fresh receipt ID
  means a distinct attempt, not another delivery of the same cost record.

Priority is estimated impact times need divided by estimated cost. Only active
leaves with positive declared value, known cost and explicitly true reachability
enter the ranked action-test proposals. Unknown/unreachable cases remain visible.
A greedy pass selects at most one proposal per leaf without exceeding the
supplied budget. It is not an optimal allocation solver. Repeated calls do not
reserve or spend budget. One probe handles one pin; cross-pin scheduling and
global accounting are not implemented. Parent/child evidence overlaps must not
be added up as independent trials.

Costs and actual effort must use comparable units; compute time and game actions
must not be added without an explicit conversion chosen by the caller. The
default unit name is action_units. Estimates are not learned in this version.

## What changes at each node

Samples retain compact node history and the latest detailed pin snapshot. Nodes
include matching trial IDs, missing-context signals, factor yes/no/unknown
counts, distinct bit/outcome signatures, actual effort totals and structural
height. Their detailed view retains raw before/after observations, bit bands,
arrival routes and directions. Colours and orientations remain metadata.

Diagnostics distinguish:

- Effort with no newly observed trial, including recirculating old evidence.
- Fresh trials repeating existing bit/outcome signatures while the declared
  need remains unresolved. This suggests reviewing experiments or missing
  features; it does NOT mean repeats are useless for repeatability assessment.
- A decrease in the explicitly defined need metric. This is not a causal proof
  or a measured improvement in game score.

New signature counts measure novelty in the supplied representation, not useful
information or causality. A contradictory new observation may be valuable even
when it increases need. Zero listed need does not mean every context is tested.

Effort rate is the change in accumulated effort divided by elapsed sampled
steps for an unchanged node model. Need-change rate counts metric changes per
step. Neither is frequency in hertz: no timestamps, waveform, phase or physical
oscillation is inferred. The first sample is a baseline, so it has no rate.
Parent refinements start a new model-history segment; unrelated structural
lifts do not change an unaffected node's priority. Diagnostics describe the
latest interval; they are not latched alarms or automatic tool-disable rules.

## Integrity and limits

Effort receipts use stable IDs, current model revisions and known node/trial
references. Repeated identical receipts do not increase cost; inconsistent
duplicates reject the whole sample. Old effort must be recorded before a rule
is lifted, or reconciled explicitly outside this prototype. Sampling checks
that previously retained trial records have not disappeared or changed.
Stale analysis requests require a new sample. `detail()` intentionally returns
the last sampled state, not an unsampled live view.

The API is synchronous, single-owner and in-memory. Defaults cap history at
256 samples and effort records at 1024. Hitting a cap raises an error without
silently evicting anything. Checkpoints, archival and resuming a probe are not
implemented. Callers attest scope, clock steps, real attempts and cost units;
the probe does not authenticate those external facts. All returned reports
are copies. Reading, zooming and ranking never change EvidencePin evidence.

## Demonstration

`demo_circuit_analysis.py` creates two unresolved branches. With supplied
impact/cost estimates, the contact-present branch ranks at 0.8 versus 0.3 for
contact-absent. Under a three-unit budget, the greedy scheduler proposes the
one-unit test and leaves two units unallocated, rather than overspending.

Four stages demonstrate initial gaps, two units spent revisiting an existing
observation, another unit producing a repeated context, and a final unit
producing a new context. The unresolved need stays at one while effort grows;
different diagnostics explain what changed. These are hand-authored fixtures,
not measured ARC effects. The in-conversation inspector uses compact data from
these same fixtures and switches between overview, bit detail and sample history.

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_circuit_analysis -v
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B demo_circuit_analysis.py
```

The demo prints JSON and makes no game, model or file-writing calls. Scheduling
uses EvidencePin's declared gaps and coverage only; AutomaticPinRefiner's richer
ambiguity/checking questions still need an adapter. The next integration is
recorded ARC transitions, measured experiment costs, and that proposal adapter
before a planner consumes recommendations. Physical circuit laws and 3-6-9
number patterns are not used as evidence or as approval conditions.
