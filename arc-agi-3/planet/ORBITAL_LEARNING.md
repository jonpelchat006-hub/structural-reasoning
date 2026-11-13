# Orbital archive, explicit boundaries, and the first submission experiment

2026-09-09. This connects durable storage and online measured observations to
the pin refiner. It is a working limited learning loop, not a claim that general
ARC learning, autonomous experiment selection or all earlier geometry is finished.

## What detaches and what persists

`orbital_archive.py` is a separate SQLite store; the older `archive.py` spiral
drive remains untouched and was not run. It does not move or delete old work.
JSON objects use SHA-256 identities and compressed payloads. Loading verifies
integrity. Bundles retain command/outcome references, scoped pins, fitting and
checking cohorts, rule refinements and terminal/boundary reasons.

Retrieval is explicit and returns candidate bundles. It neither executes saved
commands nor inserts their trials into the active pin as new observations.
The actual private archives live in each comparison worker's learning-archives
directory. They can be reopened after the process exits. On Kaggle, these files
are local notebook-run outputs; persistence across new notebook runs would need
explicit artifact retention/reattachment, not an assumption that RAM survives.
No local recordings or prelearned archives are bundled into the submission.

`learning_session.py` journals each supplied observation before deriving new
learning state. The journal carries raw frames plus trusted game/instance/level
metadata and previous-action identity. A failure in derivation faults the
session rather than retrying a game action; `LearningSession.resume()` reconstructs
pins and boundaries deterministically from that journal. Derived raw-frame
references resolve through the content-addressed object store. Both failed and
successful attempts are retained, as are incomplete checkpoints.

Within one explicit run:

- Game ID change: archive the old working bundle and detach game-specific pins.
- Instance ID change: detach even if the puzzle/game ID happens to match.
- Observed RESET command: start a new attempt, without manufacturing an ordinary
  action-effect observation from the reset frame.
- Level count change: detach board-local pins and start a fresh local scope.
- GAME_OVER / WIN: retain the failed/won attempt with terminal reason.
- Shape discontinuity or unexplained revival after a terminal state: label an
  uncertain boundary, rather than guessing death/reset/new game from overlap.

Motion magnitude and pixel similarity do not classify these events. Scope IDs
include run, game, instance, level and attempt. At 512 observations for one
action pin, the prior window is archived before opening another; nothing is
silently evicted. Terminal bundles carry explicit death/win reasons. A later
run_end/checkpoint bundle is an incomplete checkpoint record, not a replacement
for that earlier terminal outcome. The API stores both.

## Automatic learning now connected to observations

For each non-reset action, the loop measures 16 before-frame colour-presence
bits and the exact boolean outcome "did the returned frame differ?" Raw before
and after frames remain available by hash. This outcome is NOT progress, useful
movement or causal success; HUDs and animation can change it too.

Fitting/checking roles are assigned by ordinal (two fit, one check), without
looking at the outcome. Every 16 trials the existing refiner tries one supported
split. Replay preserves these assignments. A fixture with real before/after
arrays demonstrates selection of a colour-presence condition and learned boolean
branches without supplying a split or predicted answers. This is a supplied
feature vocabulary, not automatic perception or invention of new features.

The initial four real-game comparisons produced no conditional refinements.
That is retained as a limitation, not reinterpreted as evidence for the theory.
Simple colour presence is often insufficient or ambiguous, and consecutive
fitting/checking samples are correlated. The code does not claim statistical
independence or use those frame-change hypotheses to approve planner actions.

## Candidate used for game comparisons

`prioragent_learning.py` starts from the policy in the reviewed .25 notebook,
not the reliability candidate that previously regressed. The executable AST of
`prioragent_reviewed_baseline.py` is checked against that notebook with comments
and docstrings excluded; the copied explanatory Unicode text was normalized by
the Windows console. The original notebook is never modified.

Policy changes are limited to:

1. Invalidating previous-action bindings across explicit/uncertain boundaries,
   avoiding crediting a reset or new board to an ordinary command.
2. Letting three or more consistent recent observed one-axis displacements
   replace the corresponding hard-coded direction inside BFS. Sparse,
   conflicting, diagonal or unusually large movements retain the prior.

Movement observations still depend on the baseline's heuristic self detector;
consistency alone is not causal verification. No additional probing actions are
introduced. Learned colour-condition pins remain observational. The official
framework owns the one actual game transport, not archive helpers. The geometric
four-eye prototype is not another transport layer in this candidate.

This is not yet the full proposed system: archive retrieval is not automatic
transfer, the circuit scheduler is not driving experiments, the refiner lacks
deeper simultaneous search, and frame-change rules do not yet predict useful
object/control relationships. Those gaps remain explicit.

## Evidence and packaging

Four-game cold-start comparison, 2,000 environment calls per game, seed 0:
`D:\planet\arc_compare\orbital_learning_20260909_four_games\comparison.json`.
Baseline: 3 completed levels; candidate: 4. CD82, LP85 and LS20 matched their
baseline scores; VC33 increased from zero to one completed level. The local SDK
mean changed from 1.2984940806 to 1.3076833265. These numbers are NOT the Kaggle
score and cannot be compared numerically with .25. No whole game was won.
No new rule or movement override was used in those four runs, so that small gain
cannot be attributed to learned rules. Archive/learning bookkeeping added
substantial wall-clock overhead (roughly 52-68 seconds per candidate game versus
7-14 seconds for those baselines), though the game-action budgets were equal.

The full 25-game comparison is complete in
`D:\planet\arc_compare\orbital_learning_20260909_public25`: 50/50 successful
runs, seed 0, 2,000 calls each. Baseline completed 3 levels; candidate completed
5, adding TR87 and VC33, with no lower per-game score in this sample. No whole
game was won. Local SDK means: 0.2077590529 baseline, 0.2100614487 candidate.
Imported candidate dependencies were hashed along with the runner, source,
baseline and environments; inputs stayed unchanged during the comparison.

Across candidate runs, 50,025 observations and 1,053 bundles were retained.
Learned displacement maps were used in 544 planner calls. There were ZERO new
colour-condition refinements. This is evidence of a feature/search limitation,
not proof that the automatic rule learner improved play. Multiple seeds,
attribution ablations, stronger object features and runtime optimization remain.

`build_orbital_notebook.py` produces the separate orbital notebook using the
reviewed competition gateway flow, copies all required modules into the writable
framework directory, verifies embedded source hashes, removes old outputs and
preserves the offline competition attachment. It contains no local archives,
environment implementations or account credentials. The supplied gateway's
existing test-key placeholder remains part of that original integration.

The private Kaggle notebook is `jonpelchat/prioragent-orbital-learning`; pushing
a notebook version is separate from submitting it to the competition. A successful
normal notebook run only validates setup and the placeholder output, not hidden
game performance. Source notebook: `prioragent-arc-agi-3-orbital.ipynb`.

Version 1 completed its normal Kaggle run, then was submitted successfully as
competition submission **56129516** on 2026-09-09 at 19:01:09 UTC. Last checked
status: COMPLETE, public score 0.00 (confirmed on 2026-09-09). Subsequent local
diagnosis reproduced a constructor/worker SQLite thread mismatch before the
first game action. The scored-run traceback itself was not retrieved.
The submitted notebook SHA-256 is
`1c74020772273a2fc8cce038f74796b9534f00a57909537875cd6085c9c24999`.
All 191 focused tests passed. The original .25 notebook's SHA-256 remains
`7ace657bfbec62e681caaa369d1e3726396e8621134b554a40872aa8666add88`.

[Private submitted notebook](https://www.kaggle.com/code/jonpelchat/prioragent-orbital-learning)
and [competition submissions](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/submissions).

Reproduce tests:

```powershell
& 'D:\planet\arc_compare\.venv\Scripts\python.exe' -B -m unittest test_orbital_learning test_orbital_notebook test_compare_prioragent_games -v
```

The Kaggle CLI is installed separately at `D:\planet\arc_compare\kaggle_tools`;
the pinned game-comparison environment was not modified. Account authentication
uses the existing token file through the official client; tokens are not copied
into source, notebooks or reports. The reviewed .25 submission was confirmed via
the account's submission list (submission 55898016, completed 2026-08-30).

Current official submission entry point and offline-evaluation requirement:
[ARC Prize competition page](https://arcprize.org/competitions/2026/arc-agi-3).

## Follow-up: local channel version 2

See `PIN_CHANNELS.md` for source connections, the per-pin codec implementation,
worker-owned archive fix, packaged multi-thread regression tests, and remaining
learning limitations. The original submitted notebook above is preserved.
The builder now packages `orbital-channels-2` with a checked threaded runner.
