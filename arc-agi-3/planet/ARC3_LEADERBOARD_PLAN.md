# ARC-AGI-3: what remains for a stronger leaderboard run

Review date: 2026-09-07. Scope: the latest Python `planet` agent and its saved
public-game recordings, not every older agent on the machine. No current
account-specific leaderboard score or rank was retrieved. No submission was
made. The user reports a best score of .25 on their last submission; its exact
artifact and displayed scale have not yet been verified. The helper-cube build
and the fixes below are not yet a measured score increase.

See `PRIORITY_PROGRESS.md` for this implementation pass and test commands.

## Target and scoring

The user confirmed ARC-AGI-3 interactive games. There are distinct entry paths:
the Kaggle code competition, the platform's unverified competition-mode board,
and verified benchmark results. A local diagnostic number is not any of these.

Official scoring combines level completion with human-relative action
efficiency. Completed-level efficiency uses a squared human/agent action ratio;
later levels receive greater weight. Internal reasoning is not an environment
action, although compute and wall time remain practical constraints. Use the
official scorecard as the authority rather than rebuilding the metric from
incomplete local press logs. [Scoring methodology](https://docs.arcprize.org/methodology)

The current competition documentation requires Kaggle submissions with no
internet during evaluation. Prize eligibility also requires open sourcing the
authored solution. The advertised next milestone is September 30, 2026.
Confirm current Kaggle rules and compute limits before a submission; the
overview page alone does not establish the full execution budget.
[Competition overview](https://arcprize.org/competitions/2026/arc-agi-3)

## Highest-priority gaps

| Priority | What exists now | What remains |
| --- | --- | --- |
| 1: Trustworthy evaluation | Validated, hash-identified recording batches; atomic completed reports; explicit failures; isolated play outputs, seeds and full returned scorecards. | Bind the exact submission/code/dependency versions; compare authoritative game results. |
| 2: Competition execution | `play_game` drives a remote REST loop and opens/closes its own scorecard per game. An older `prioragent.py` also exists. | Wrap the latest planner state in the official per-step agent interface and let the competition harness own environment/scorecard lifecycle. Validate locally before submitting. |
| 3: Turn proposals into useful tests | Versioned proposals and a tested, injected one-step executor with condition/budget/target-observer checks. | Connect executor to real planner navigation and relation/ring observers; it is not live-wired yet. |
| 4: Stop the repeated level-three loop | Fixed stale carried colour/matcher, global route caching and repeated-hypothesis budgets; saved-frame regression audit. | Verify actual gameplay wins and action counts; investigate remaining route/budget obstacles. |
| 5: Generalization | Cold-start excludes recordings, saved fences and baseline cache; output state can be isolated. | Matched runs across games and versions; held-out-game testing. |
| 6: Reproducible package | Active new modules live in the Desktop planet checkout; runtime data live on D:. | Pin dependencies, package all modules and permitted assets, remove absolute-machine-path assumptions, and review/preserve user changes before committing or publishing. |

### Evidence for the evaluation gap

`arc3_preflight.py` found 25 valid transition recordings and seven invalid
debug/state archives. Induction now uses that manifest and input hashes,
writes progress separately, and publishes a final report only when the whole
selected batch succeeds. Daily practice checks subprocess success, run identity
and complete coverage; a failed practice run no longer becomes a mock score.
The fresh complete batch is `D:\planet\eye\induce_verified_20260907_codex.json`.

The [preflight manifest](D:/planet/eye/arc3_preflight_20260907_codex.json)
records file hashes, valid early/late split sizes, and explicit rejection
reasons. Schema validity does not certify held-out status or benchmark fairness.

`--no-prior` now also excludes saved fence rules and the baseline cache. Use an
isolated `--output-dir` to keep development state separate. Induction's early/late
split still tests prediction within recorded games, not unseen-game success.

### Evidence for the gameplay gap

The latest inspected [LS20 depth log](D:/planet/eye/play_ls20_depth.log) records
level one at press 149, level two at 267, and a stop after 587 presses with two
levels completed. Its tail repeats source touches and ring refills on level
three without reaching the level goal. This is an old development run, not a
new run of the helper-cube version or an official score.

The log reports 17 voluntary resets. Its operator counter includes reset rows,
giving 592 operator presses versus 587 total. New action metrics exclude resets;
authoritative returned scorecards remain separate from these local counters.

`route.py` now caches only within a planning call, so model/fence updates cannot
reuse legs from earlier calls. Relation attempt budgets now survive restarting
the same hypothesis within a level.

The recorded third level contains four HUD states. The previous level's colour
9 rule recognizes zero matching frames; rebinding the same structural prior to
the uniquely matching colour 12 recognizes 16. Eight recorded source touches
rotate away from an exact match. `relations.py` now performs conservative colour
rebinding and refreshes active matchers. This demonstrates a matching bug, not
that the remaining target route is affordable or the level is solved.

## Submission integration

The official starter exposes `choose_action(frames, latest_frame)` and
`is_done(...)`. Its documented development runtime is Python 3.12; the Python
used for this build's tests is 3.14.3, so those tests are not a competition-runtime
compatibility check. Use an isolated, pinned competition environment. Do not
push a notebook or spend a submission just to discover packaging errors.
[Official starter guide](https://docs.arcprize.org/arc-prize-2026)

Competition mode restricts evaluation to one scorecard and one environment
creation per game, with scoring covering the whole game set. That differs from
the current runner's independent per-game scorecards. The API requirement can
be fulfilled through the competition's provided environment gateway; it does
not justify calling an internet-hosted model from the offline Kaggle run.
[Competition mode](https://docs.arcprize.org/toolkit/competition_mode)

Before publishing, confirm the intended leaderboard/account and package only
the intended solution files. No credentials need to be printed or embedded in
the agent. Open-source/publication and account-rule acceptance were not performed.

## Recommended next experiment

1. Bind the reported .25 submission to an exact agent artifact and scorecard.
2. Run the corrected matcher/planner on actual games under matched versions,
   seeds, budgets and isolated starting state; recorded-frame replay is not a win.
3. Make a helper return the smallest discriminating experiment for a stalled state;
   have the central executor validate and run it once, then update the eye from
   the actual transition. Merely accepting a proposal cannot improve the score.
4. Compare current planner versus experiment-enabled planner on matched seeds,
   game versions, budgets, and isolated prior-state settings. Keep a broader
   held-out public-game group to detect LS20-specific changes.
5. Run the packaged agent through the official local harness, then deliberately
   submit the verified package. Record official score, per-level actions,
   completion, resets, runtime, and errors for every game.

An immediate reproducible diagnostic:

```powershell
Set-Location -LiteralPath 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet'
python -X utf8 -B arc3_preflight.py D:\planet\eye
```

Do not use operator count, quaternion closure, or number of answered prompts
as a leaderboard proxy. They are useful only if matched evaluation shows they
help complete more levels using fewer environment actions.
