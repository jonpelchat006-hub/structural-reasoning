# PriorAgent reliability candidate

Update, 2026-09-08: real-game comparisons are now complete. This candidate scored
worse than the baseline on the first 25-game public sample. Its passing
regression tests are not evidence of better gameplay. See
`ARC_COMPARISON_RESULTS_20260908.md` before choosing a submission version.

Built from the exact notebook the user identified as their last .25 submission:
`C:\Users\GamerTech\Downloads\prioragent-arc-agi-3.ipynb`.
Its SHA-256 remains
`7ace657bfbec62e681caaa369d1e3726396e8621134b554a40872aa8666add88`.
The baseline notebook and existing local `prioragent.py` were not changed.
The .25 score is user-reported; the notebook does not contain a saved scorecard.

## Deliverables

- `prioragent_candidate.py`: standalone candidate source, compatible with the
  baseline's `PriorAgent` class/interface and local `arcshim` tests.
- `prioragent-arc-agi-3-candidate.ipynb`: a separate candidate notebook. Its agent
  cell exactly matches that source. Setup/gateway/submission cells are retained
  from the baseline; execution counts and outputs are cleared, not represented
  as a successful run. Provenance/source hash is in notebook metadata.
- `test_prioragent_candidate.py`: 24 local synthetic regression tests.
- `compare_prioragent_regressions.py`: baseline-versus-candidate diagnostic. It
  checks the baseline hash and loads only reviewed function/class definitions;
  installation, shell, gateway and submission cells are never executed.

This is a submission **candidate**, not a verified competition run or a new
leaderboard score. The notebook has not been uploaded or submitted.

## Changes

1. Reset, invalid observation, level change and board-size change break the
   previous-action/observation link. Old click chains and pending plans cannot
   interpret a replacement board as an action's result. Board-specific palette,
   lattice, floor/wall and ambient evidence reset on a new level. Same-level
   legitimate transitions still update action effects.
2. Ambient changes are excluded consistently from frame-difference accounting
   and exploration keys, while raw frames remain available. Recurring-pixel
   candidates need eight observations across at least three controls. Simple
   two-colour horizontal border bars can also be recognized by a moving boundary
   rather than expecting the same pixels to change repeatedly. Known self pixels
   are protected, masks over 10% of the board are rejected, and new bar colours
   or shapes invalidate that bar hypothesis.
3. Changing an ambient mask invalidates old hash-based exploration/banning
   evidence. Local no-op counts no longer depend on whether an action succeeded
   somewhere else earlier in the game.
4. Each agent uses a private RNG seeded by a stable game-ID digest, not Python's
   process-randomized `hash()`. Frame keys are stable digests including shape and
   mask identity. Interleaving agents does not consume one another's RNG stream.
5. Available non-click controls are probed once per level, not again on every
   reset. Pending probes/plans are checked against current action availability.
   Click-only games receive clicks, not movement probes.

Optional constructor controls: `candidate_seed=...`, `mask_ambient=False`,
`probe_actions=False`. Defaults enable the candidate features. These flags are
for controlled comparisons; disabling them is not an exact restoration of the
baseline's lifecycle and random behavior.

No cube/relation planner integration or unrelated local v11 click/perception
changes were included. The Desktop `play.py` fixes and this standalone submission
candidate remain separate branches of the implementation.

## Verification

All 24 candidate tests pass under Python 3.12 and Python 3.14. The broader
existing-plus-candidate suite passes 98 tests under Python 3.14. These tests use
the local interface shim, not the real competition SDK/gateway.

The comparison report is
`D:\planet\eye\prioragent_candidate_regressions_20260907.json`:

| Synthetic diagnostic | Submitted baseline | Candidate |
| --- | --- | --- |
| Reset falsely credited as an action effect | 1 | 0 |
| New level falsely credited as an action effect | 1 | 0 |
| Distinct last-five states, counter-only changes | 5 | 1 |
| Distinct last-five states, shrinking-border-bar only | 5 | 1 |
| Timer-only changes credited over 14 transitions | 14 | 7 warmup transitions |

These are accounting regressions, **not game wins, saved actions or scores**.
Ambient detection is still a heuristic: it does not cover arbitrary animated
HUDs or all bar layouts, and action-dependent recurring effects could resemble
noise. Raw bar values are preserved, but a future budget planner must explicitly
use them rather than treating the novelty key as the complete game state.

## Reproduce and next gate

```powershell
Set-Location -LiteralPath 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet'
py -3.12 -X utf8 -B -m unittest test_prioragent_candidate -q
python -X utf8 -B compare_prioragent_regressions.py 'C:\Users\GamerTech\Downloads\prioragent-arc-agi-3.ipynb'
```

The next gate is real-game baseline/candidate evaluation under matched game
versions and budgets, followed by the official local harness. The baseline's
notebook metadata records Python 3.12.13 and its saved installation output names
arc-agi 0.9.8 / arcengine 0.9.3; this candidate did not install or validate that
competition environment. Its retained non-competition cell produces a dummy
submission file, which must not be interpreted as an agent score.

If editing the source again, also regenerate the embedded notebook cell and its
source hash; the package regression test intentionally fails if they diverge.
