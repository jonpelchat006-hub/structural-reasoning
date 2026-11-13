# Helper cubes with a closed return path

Implemented 2026-09-07. `cube_router.py` supplies a bounded local request tree
and a central proposal-validation gate. This is a software accounting rule,
not a physical conservation law or a sedenion zero-product assertion.

## Implemented contract

Every request carries a question ID, pin ID, scope, frame/state version, parent
request, named owner, and an opaque return capability. Responses must match
that ticket. A handoff rotates the capability while preserving the destination;
the old owner ticket cannot return again. Capabilities are omitted from report
snapshots. This is bookkeeping isolation inside one Python process, not a
security sandbox for untrusted code.

A parent cannot return while any direct child is open. Since children follow
the same rule, the whole subtree closes before the root returns. Children can
return results, fail, time out, or be cancelled. The parent can collect its own
children's terminal replies. Only a root reply can cross the central gate.

The accounting identity is:

`outstanding = opened - closed`

Returned, integrated, rejected, failed, cancelled, and timed-out requests are
closed. Zero outstanding means no unfinished request remains, not that the
answer is correct or every helper succeeded. Failed descendants anywhere in
the tree prevent a successful-readiness claim at the gate.

The gate checks the current scope/version/question/pin binding, reply schema,
condition and effect identity, control bindings, retained blockers, and an
explicit unverified-proposal label. Duplicate deliveries and integrations are
rejected. A frame/hypothesis change cancels open requests and clears active
proposals; the audit history remains. Reply validation does not change pin
counts, verify causality, or authorize an action.

Limits cover request count, tree depth, explicit work charges, message size,
and elapsed time. Timeouts are checked cooperatively at ledger operations.
They do not kill a blocked worker process or HTTP call: an eventual external
transport must enforce its own timeout and cancellation. A caller that hits
a depth/node limit may choose a fallback or cancel the parent; the provided
batch runner cancels open work on failure.

## First runnable helper network

For each selected open question, the local batch runner creates:

1. An experiment parent cube.
2. A condition helper returning the supplied condition and missing information.
3. A control-binding helper returning only supplied candidate controls.

The parent gathers both replies and returns a combined experiment proposal to
the originating pin. The central gate stores it in a versioned proposal map.
This exercises real request/return/collection logic without an LLM or game API.
The helpers are small deterministic functions over existing records, not new
learned solvers or independent AI agents.

At most eight questions are processed per batch by default. Extra questions
remain deferred; their obligations have not been opened. All game actions
still come from the existing planner. A separate `experiment_executor.py` now
checks current conditions, an already-reached site, a central target observer,
and remaining game budget before one injected action. Its tests connect a
question through helper returns to a real local observation delta. It is not
yet wired to live navigation/action selection; see `PRIORITY_PROGRESS.md`.

`play.py` now includes `cube_flow` in its normal diagonal reports at rebuilds
and at the final level observation. The version includes press count and a
frame digest. Each batch is synchronous and has a fresh ledger; no background
workers survive it. `--no-cubes` disables this proposal stage for an overhead
comparison. It does not disable the question queue or change other features.
Versioned proposals in historical reports must not be reused as current plans.

## Verification

The offline pilot on five saved diagonal reports opened 48 requests, closed 48,
and returned 16 proposals with zero outstanding requests. Those old reports
lack condition patterns, so all 16 proposals request more information rather
than claim an executable test. The input reports were not modified.

[Pilot report](D:/planet/eye/cube_flow_20260907_codex.json)

The 19 router tests cover nested closure, collection, owner handoff, wrong
addresses, duplicate returns, stale versions, changed questions, rejection,
descendant failures, timeouts, budgets, input immutability, and batch limits.
Together with 15 question, 10 algebra/cube, and 3 recording-preflight tests,
47 tests pass. The modified play script passes syntax parsing; no live game,
remote-model run, or leaderboard submission was performed.

```powershell
Set-Location -LiteralPath 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet'
python -X utf8 -B -W error::ResourceWarning -m unittest test_cube_router test_pin_questions test_algebra_memory test_arc3_preflight -v
python -X utf8 -B cube_router.py D:\planet\eye\diagonal_sp80.json
```

The replay CLI supports `--output NEW_PATH.json` and refuses to overwrite an
existing report. The existing question queue remains responsible for answering
sampling requests from observations; helper replies cannot close those questions.
