# First real-game comparison — 2026-09-08

Outcome: the reliability candidate is **not a demonstrated gameplay upgrade**.
The runner and isolated runtime now work; all requested runs below completed.
No Kaggle upload/submission or online game actions were performed.

The exact .25 notebook and candidate source stayed unchanged throughout.
Runtime, source, framework and public game-version hashes are saved with each
batch. The official local game engine and official `Agent.main()` loop were
used, not mocks. Network access was blocked inside evaluation workers.

## Full public set: 25 games, seed 0, 2,000 calls per game

| Metric | Submitted baseline | Reliability candidate |
| --- | ---: | ---: |
| Completed runs | 25 | 25 |
| Levels completed across games | 3 | 2 |
| Entire games won | 0 | 0 |
| Mean local SDK score | 0.207759 | 0.013530 |
| Environment calls, including resets | 50,000 | 50,000 |
| Reset calls | 1,013 | 708 |

These are **local SDK scores on current public versions**, not Kaggle/hidden
scores, and must not be compared numerically to the reported .25 submission.
This broad pass uses one seed; it does not establish average performance across
all random runs or unseen games. Fewer resets did not translate into better scores.

Where they differed:

- CD82: baseline completed one level; candidate completed none.
- LS20: both completed one level, but baseline reached it at call 133 and
  candidate at call 665 (including four resets). The candidate's efficiency was
  substantially worse in this run.
- LP85: both completed one level, with equal local SDK scores.
- Neither completed a level on the other 22 games.

Full report: `D:\planet\arc_compare\public25_2000_s0_20260908\comparison.json`.

## Feature-disabled tests: CD82 and LS20, seeds 0/1/2

Each variant had six game/seed runs, each capped at 2,000 calls.

| Variant | Levels across six runs | Mean local SDK score |
| --- | ---: | ---: |
| Baseline | 3 | 0.810038 |
| Candidate | 3 | 0.001954 |
| Candidate without masking | 3 | 0.001954 |
| Candidate without initial probing | 6 | 0.607679 |

Disabling blanket initial probing restored a CD82 level completion at call 109
in all three runs. Disabling masking did not restore that completion. Turning
probing off did not improve the LS20 score versus the normal candidate, and
even the no-probe variant's mean score on this two-game sample was below the
baseline's. More levels and higher action efficiency are distinct objectives.

The candidate uses a fixed private game-ID seed by design. Its repeated results
on these environment seeds were identical, so they are not three independent
samples of candidate policy randomness. The baseline varied with its process
hash seed. Further tests should separate environment variability from policy
RNG variability before drawing statistical conclusions.

Feature-test report:
`D:\planet\arc_compare\ablation_cd82_ls20_20260908\comparison.json`.

## Reproducibility and checks

- The seed-0 baseline/candidate action logs for both CD82 and LS20 were identical
  byte-for-byte between the broad batch and the separate feature-test batch.
- All 74 main/feature-test runs completed; none were silently converted to zeros.
- Six runner tests pass; the broader suite passes 104 tests. Thirty
  runner-plus-candidate tests pass inside the isolated Python 3.12 runtime.
- The PowerShell convenience command was also executed on a four-call smoke run.
- Initial pilot: two games, two agents, 200 calls each. That small pilot was a
  setup check and is not included in the broad-set figures above.
- Runtime, framework, cached games and recordings occupy about 3.8 GB on D:.
  All replay data were retained; no user data were deleted.

## What to do next

1. Keep the original submission as the benchmark; do not label this candidate
   an improvement just because its accounting tests pass.
2. Investigate selective, budget-aware probing instead of unconditional initial
   probing. The CD82 comparison gives a concrete failure to replay.
3. Compare lifecycle fixes separately from changes to RNG, floor/palette carry,
   no-op handling and probing. These are currently bundled; this experiment does
   not establish which other change caused LS20's loss of efficiency.
4. Address the larger gap: both agents failed to clear any level on 22 of the
   25 public games. Navigation heuristics alone are not enough; use the newer
   relation/question machinery to choose discriminating tests, then measure it.
5. Use regular Kaggle submissions for hidden-set feedback as the user prefers.
   Local evidence should guide the next candidate, not indefinitely delay a
   submission. No replacement notebook was silently selected or submitted here.

See `ARC_COMPARISONS.md` for the reusable one-command runner and setup details.
