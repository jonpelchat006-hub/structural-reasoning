# ARC-AGI-3 priority implementation — 2026-09-07

The user's best reported submission is .25. No new official score has been
obtained, and none of the diagnostic figures here can be compared to .25.
The user subsequently supplied `C:\Users\GamerTech\Downloads\prioragent-arc-agi-3.ipynb`
as that submission's notebook. It embeds a standalone older `PriorAgent`, not
the `play.py` cube/relation planner discussed below. A separate reliability
candidate is now packaged; see `PRIORAGENT_CANDIDATE.md` for its 24 regression
tests, baseline comparison and remaining competition-harness validation.
Work was made in the Desktop `planet` checkout; runtime outputs below are on D:.
Existing user changes were preserved. Nothing was submitted, committed or pushed.

## Concrete improvements

- Evaluation: `evaluation_batch.py` validates recording manifests and hashes,
  separates progress/failure from completed reports, rejects stale run identities
  and stops partial-corpus result mixing. `arc_daily.py` now reports practice
  errors as failures, not fallback/mock scores.
- Routing: `route.py` caches only within a call. A regression verifies different
  learned movement costs produce different routes even on identical pixels.
- Repetition: `relation_guard.py` budgets actual source experiments per semantic
  hypothesis per level. Restarts/resets do not replenish that budget; matched
  goals remain eligible. Exhaustion produces a diagnostic question, not a proof
  that the hypothesis is impossible. `--no-relation-guard` supports ablation.
- Matching: carried structure no longer depends unconditionally on the previous
  level's literal colour. An absent colour is rebound only when exactly one
  current mask fits a remembered shape. Active matchers are refreshed from new
  evidence and pending source plans are rechecked before another touch.
- Experiments: `experiment_executor.py` turns a validated question/proposal into
  at most one injected action at an already-reached site. It rechecks the actual
  condition, budget, control and central target observer; returns observations,
  never causal proof; blocks stale/duplicate dispatch and uncertain retries.
  It is deliberately NOT yet connected to live planner action selection.
- Run hygiene: `play.py` accepts an injected transport, isolated output directory
  and seed; saves the full returned scorecard; cold-start excludes saved fences,
  recordings and baselines. Action counters exclude reset rows.

## Evidence and limits

`D:\planet\eye\induce_verified_20260907_codex.json`: complete batch of 25 games,
54 gated non-restore operators across 17 games. Mean strict changed-cell
prediction accuracy is approximately .3004. This is a recorded-transition
diagnostic, **not a leaderboard score**. The old default result was preserved.

`D:\planet\eye\relation_replay_20260907_codex.json`: the third level of the saved
LS20 run has 320 actions, four HUD states and 38 state-changing touches. The
previous colour-9 matcher recognizes zero matching frames; the colour-12
structural rebinding recognizes 16. At presses 334, 370, 406, 442, 478, 514, 550
and 586, the recorded agent rotates away from an exact match. Inputs are real
saved frames, but this is only a counterfactual matcher audit, not alternate
gameplay. Winning, route affordability and action savings are unproven.

`D:\planet\eye\smoke_codex_20260907_relations\smoke_result.json`: the actual
play loop on an injected local mock, CUDA, seed 7, 16 actions. Returned action
accounting agrees with the transport. This checks integration, not competence;
the simple mock does not exercise populated relation/cube planning. Earlier
CPU smoke was stopped after verifying it was our process; its partial log is
retained in `D:\planet\eye\smoke_codex_20260907`. It used no live API.

74 focused regression tests pass on Python 3.14. Python 3.12 is installed but
lacks SciPy and Torch; an earlier compatibility run stopped on missing SciPy.
No dependency installation or official competition-runtime validation was done.

## Reproduce

```powershell
Set-Location -LiteralPath 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet'
python -X utf8 -B -m unittest test_relation_refresh test_evaluation_batch test_planner_guards test_experiment_executor test_cube_router test_pin_questions test_algebra_memory test_arc3_preflight -q
python -X utf8 -B relation_replay.py D:\planet\eye\play_ls20 --level 2 --region 55 60 3 8 --source 0@11,51 --target 5@49,53 --prior-colour 9 --output D:\planet\eye\relation_replay_review.json
python -X utf8 -B local_play_smoke.py --output-dir D:\planet\eye\smoke_review_new --device cuda --presses 16 --seed 7
```

Choose a new output directory for each smoke run. The replay report path is
atomically replaced if it already exists. The smoke refuses existing directories.

## Next gates and ideas at the next wall

1. Identify the .25 submission and run version-matched, cold-start gameplay
   comparisons. Package the latest planner into the official per-step interface
   with the harness owning the scorecard/environment lifecycle. Save source and
   dependency hashes as well as game versions before claiming an improvement.
2. Connect the executor to planner navigation and central relation/ring effect
   observers. Its present support is only an immediate rectangular target-pattern
   appearance with a back-pattern condition; no clicks or delayed effects.
3. If a glyph matches but the goal still refuses, ask which additional condition
   distinguishes refusal from success: entry side, position, another object, or
   timing. Keep the matched state fixed and change one condition per experiment.
4. If the goal cannot be reached on the remaining bar, reason jointly over
   position, glyph state and remaining energy; a refill may alter the best order.
   Do not simply add more source rotations or reset the same trial budget.
5. Audit observation timing: post-action world-model rebuilds currently read the
   outer pre-action frame in some paths. Before live cube execution, bind every
   proposal to the actual latest observation. Also review the existing REST
   sender's automatic action retries; an uncertain action must not be duplicated.
6. Add held-out games and pinned Python 3.12 dependencies. A passing mock and a
   repaired LS20 matcher alone do not establish generalization or score gains.
