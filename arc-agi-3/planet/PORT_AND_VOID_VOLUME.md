# One port, shared pin volumes, and an explicit test reserve

2026-09-08. Offline prototypes and a synthetic diagnostic, not a new ARC score.
No live adapter, PriorAgent source, submitted notebook, runtime settings or
existing pin counts were changed.

## One game-facing port

`game_port.py` supplies one bidirectional interface. A central action leaves
with scope, observation version and request ID; the transport's returned
observation must match that same request. The initial observation is supplied
at bootstrap. Only one action can be in flight. Stale/illegal actions are
rejected before spending budget, which is consumed before transport dispatch.
Timeouts, malformed replies and mismatched returns retain an unresolved request
and block further dispatch: no automatic repeat of an uncertain action.

For a successful exchange, outstanding returns to zero. That means request
accounting closes, not that the game was solved or physical energy conserved.
The port does not count replies as extra game actions. Game transitions can
change the observation while the game/session scope stays stable.

The injected transport must be the sole game owner when integrated. Helper
cubes should return proposals through the existing CubeLedger and never hold
the transport. This module currently enforces its own exchanges only; it does
not reroute existing play.py/PriorAgent transports. It is an in-process contract,
not a sandbox. A real transport needs its own timeout and uncertain-request
reconciliation; this wrapper does not interrupt blocked callbacks. Available
actions and observation semantics must be supplied/validated by a trusted SDK
adapter. The abstract port does not authenticate physical observations.

## A volume can expose a local common condition

`void_volume.py` clips straight pin segments against an open axis-aligned box.
The three coordinates belong to an explicitly named hypothesis space; no depth
is inferred from a pixel's colour. Tangencies and zero-length points do not
count as crossing volume. A future mapper must define the axes and transforms.

Each pin has factor annotations on intervals along its length. A factor is
eligible only if its annotations cover the complete portion inside the volume.
Annotations outside it do not count. The intersection across compatible pins
is a candidate common factor. Scope, hypothesis version, coordinate space,
action and target-effect identity must match. At least two distinct observation
IDs are required; they are provenance IDs, not proof of statistical independence.
Conflicting labels are excluded. At most 256 pins and 64 spans per pin are read.

This is common-factor extraction from supplied annotations, not discovery of
those annotations, not full spatial overlap reconstruction, and not a causal
test. Different pins may occupy different parts of the same volume. The useful
question is whether their shared condition predicts outcomes on other cases,
including failures and cases where that condition is absent.

## Reserve = untested possibilities, not invented evidence

`ColourReserve` tracks a declared finite set of candidate wall colours for a
scoped question. It separates observed success/failure from untested-reachable,
untested-unreachable and unknown-reachability cases. Duplicate trial IDs do not
add evidence, and conflicting duplicate outcomes are rejected. Untested cases
emit proposal-only questions: these are the exposed antenna ends.

The reserve fraction is untested colours / declared candidate colours. This
denominator is a hypothesis set, not a claim that all those colours occur in
the game. One observation marks basic colour coverage only, not a verified
conditional law. Repeated trials and with/without-condition tests remain the
existing QuestionQueue's responsibility. The reserve is not confidence, entropy,
physical volume, or a term chosen to force a jet sum to pi.

## What the offline experiment added

`compare_void_volume.py` uses a hand-authored toy rule: pressing succeeds if
contact is present; wall colour is irrelevant. Two training pins have different
colour annotations outside the box and a shared contact annotation inside.

- Whole-pin continuous common-factor check: no factor covers the full pins.
- Local volume check: extracts `contact=yes`.
- Three held-out cases (two new colours, one absent-contact counterexample):
  3/3 predictions match returned observations. All five trial exchanges pass
  through the port and close their request IDs.
- Exact-colour lookup abstains on all three held-out cases; abstention is not
  scored as an incorrect prediction.
- Basic colour reserve falls from 3/5 to 1/5 after actual toy observations;
  the unreachable fifth colour stays untested, with a question still exposed.

The geometry, annotations and toy rule are designed fixtures. This establishes
that the mechanism can express a useful distinction, not a learned advantage
on ARC. The current baseline/candidate do not use it.

Read-only audit of five saved LS20/SP80 diagonal reports found 10 pin records.
All 10 lack start/end volume coordinates, named coordinate space, per-trial
observation IDs, interval annotations and the newer condition field. Those
records cannot establish this proposed effect; screen/body boxes must not be
silently treated as one 3D space. Original reports were left unchanged.

Next integration: derive annotated pin spans from observed transitions under
a declared coordinate mapping, retain colour/condition trial provenance, and
test proposed factors on held-out recorded transitions before planner use.
The jet equation is not used to approve any of these hypotheses.

## Verification / reproduction

```powershell
python -B -m unittest test_game_port_volume -v
python -B compare_void_volume.py D:\planet\eye\diagonal_ls20_L1.json D:\planet\eye\diagonal_sp80_L1.json
```

The comparison prints JSON; it does not write game state or call any API.
