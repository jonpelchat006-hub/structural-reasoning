# External port and persistent evidence shafts

Offline prototype, 2026-09-08. No live game adapter, submission notebook, saved
pin report, or runtime configuration is changed. No network calls are made.

## What is built

`external_eye_circuit.py` wraps the existing GamePort. The declared layout has
an outer cube with coordinates [-2,2], a port at (0,0,4), two front-wall relay
eyes at z=2, four inner eyes at z=1, and a circuit endpoint at the origin.
Each logical route goes from port through one outer relay and one inner eye
to the circuit. Internal paths represent tunnels, not light passing through
opaque walls. This is neither an optical simulator nor an algebraic identity.
The paired outer relays are separate from the six face eyes in OuterEyeCube;
existing eye/shave geometry is not overwritten or automatically connected.

Four view packets contain copies of one observation with the SAME provenance
ID. A separate session ID prevents two circuits in the same scope from sharing
an observation identity accidentally. Views contain no transport callback.
One reply or explicit abstention is required for each view, echoing its route,
scope, version and observation ID. Agreeing non-abstaining proposals merge into
ONE game action. Disagreement or all-abstention dispatches nothing; this is
not majority voting. The central adapter supplies legal actions and still
owns policy decisions. Agreement does not establish safety or correctness.

GamePort pairs that action with its returned observation. An uncertain exchange
blocks further views/dispatch, without automatic retries. A real adapter still
needs timeout and reconciliation handling. Python encapsulation is not a
security boundary and other code is not prevented from owning a game client.

## What fills a pin

`evidence_pin.py` gives a question a persistent identity independent of whether
it has evidence. Its subject can name a pixel, border, object or action context.
Each instance has one fixed scope, action and named boolean-outcome question.
It does not allocate a pin for every pixel or infer perception from images.

The caller declares 1..16 boolean factor names and their display colours.
Each observed trial retains its before/after observations, factor values,
outcome and stable observation ID. Its bit bundle contains horizontal-band
layout metadata: height, factor, colour and yes/no/unknown state. Missing bits
stay unknown. Colours label factors rather than imply truth; they are separate
from a game's wall colours. Directions identify incoming routes but carry no
additional evidence weight. Conflicting outcomes appear in the rule summary,
not by changing an individual trial's recorded boolean answer.

Duplicate deliveries may add bounded route metadata but never add trials.
Conflicting duplicates, including boolean/number substitutions in raw data,
are rejected. Raw observations and refined rules are returned as deep copies.
Default bounds are 512 trials, 63 rule nodes, eight route receipts per trial,
and 100 KB per raw observation record; hitting a limit evicts nothing. These
are in-memory records: durable storage/checkpointing is not implemented.

## Lifting without losing support

`lift()` retains a leaf rule as a historical parent and adds absent/present
branches for one declared factor. The old rule ID, prediction, counterexamples
and trial records remain. The refinement event also records the previous rule.
Display heights shift to make room below the parent; this is hierarchy, not
mechanical support or a guarantee that reasoning cannot regress.

The caller proposes branch predictions. Trials route into branches only when
their recorded bits match every condition. Missing context is not guessed.
Historical parent conflicts remain inspectable; active leaves produce questions:

- `untested_case`: no observed trial for this combination.
- `missing_context`: potentially relevant trials lack a needed condition.
- `unexplained_observation`: a prediction is contradicted or outcomes disagree.
- `unmodelled_relationship`: observations exist, but no outcome rule is proposed.

Each gap names the subject, action, conditions, outcome question and provenance
needed to investigate it. Gaps are local proposal records, not external prompts
or executable actions. They are not automatically inserted into QuestionQueue,
whose existing pin schema differs. Arbitrary geometric empty space creates no
questions. A leaf prediction abstains without matching support, with unresolved
counterexamples, or with missing query conditions. A supported prediction is
still only a candidate; there is no confidence threshold or causal certification.
Zero listed gaps means only no gaps of these specified types, not complete
knowledge. Replication, reachability and broader test coverage remain necessary.

## End-to-end demonstration

`demo_evidence_shaft.py` supplies a toy environment where pressing moves a wall
iff contact is present AND the wall is blue. It deliberately supplies the rule,
factor extractor, next contexts and both refinement choices; it does not learn
these from pixels or perform automatic feature search.

1. A broad "pressing moves the wall" rule sees one success, then a failure.
2. The first lift splits on contact while retaining the original counterexample.
3. Contact with a non-blue wall produces a new failure and reopens that branch.
4. A second lift splits that branch on wall colour, preserving all three trials.
5. The resulting fixed rule structure predicts four further combinations, 4/4
   correct. Predictions precede each returned outcome; evidence is then recorded.

All seven trials go through the same external circuit and game port. There are
28 inner-view receipts but only seven unique trials and seven action dispatches.
The port ends with zero outstanding requests. This demonstrates bookkeeping and
refinement mechanics, not ARC improvement or statistical generalization. The
same scheme can still learn a bad rule if supplied poor features or hypotheses.

Run from this directory:

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_evidence_shaft -v
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B demo_evidence_shaft.py
```

The demonstration prints JSON, with no files or game state written. Next real
integration needs a trusted game-transition-to-factors mapper, durable trial
provenance, a proposal adapter to the existing experiment queue, and comparisons
on recorded ARC transitions before the live planner consumes candidate rules.
The existing volume prototype remains separate: no 3D coordinates are invented
from these boolean factors, and no missing evidence is forced into a pi closure.
