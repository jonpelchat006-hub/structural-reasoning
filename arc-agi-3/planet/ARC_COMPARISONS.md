# Real-game comparisons

The first broad run and feature-disabled comparisons have completed. See
`ARC_COMPARISON_RESULTS_20260908.md`: the current reliability candidate regressed
on the single-seed 25-game sample; no leaderboard improvement is claimed.

The comparison runtime is installed at `D:\planet\arc_compare\.venv`, using
Python 3.12.10. It is separate from the user's existing environments. The
baseline notebook recorded Python 3.12.13, so the patch versions differ.
ARC packages are pinned to the baseline's recorded `arc-agi==0.9.8`,
`arcengine==0.9.3`, and `numpy==2.0.2`; the complete installed dependency set is
`requirements.arc-compare.lock`.

The 25 public games were downloaded once using anonymous access and are now
cached under `D:\planet\arc_compare\environments`. No game internals were used
to design policies. Worker processes are offline, have network operations
blocked, and do not use API keys, remote models, or shared learned state.

## Run a comparison

```powershell
Set-Location -LiteralPath 'C:\Users\GamerTech\Desktop\Vesica AI\AI Detector\planet'
# All cached public games, baseline and candidate, 2,000 calls per game.
.\Run-ArcComparison.ps1

# Multiple seeds on selected games, including feature-disabled candidates.
.\Run-ArcComparison.ps1 -Games 'cd82,ls20' -Seeds '0,1,2' -Variants 'baseline,candidate,candidate_no_mask,candidate_no_probe'
```

Each command creates a fresh timestamped results directory. An existing output
directory is refused; prior runs are never merged into a new comparison.
`-Budget`, `-Workers` and `-OutputDirectory` are configurable. Defaults are
2,000 environment calls, four worker processes, and one seed (0).

## What the runner actually compares

- Exact source from the reviewed .25 notebook versus `prioragent_candidate.py`.
  The baseline file hash is checked before loading only its agent code, never
  notebook installation, shell, or submission cells.
- The official `Agent.main()` implementation from framework commit
  `4743e7d0aaae0ded0d98a89a7e282e63564cd58b`, with its core imports loaded without
  the unrelated model-provider registry. It is **not** the local `arcshim`.
- Fresh subprocess and fresh local environment per game/variant/seed. Both sides
  use identical full game-version IDs, environment seeds, and starting-frame
  hashes. No saved fences, demonstrations, or cross-game memories are loaded.
- The shipped RNG logic is preserved: each pair receives the same
  `PYTHONHASHSEED`; the baseline uses Python's game-ID hash, and the candidate
  uses its private stable seed. These are not identical RNG streams. A game that
  ignores environment seeds may produce identical candidate repeats; this is
  recorded behavior, not independent statistical evidence.
- Equal maximum environment calls, **including resets**. The framework loop uses
  `<= MAX_ACTIONS`, so the runner sets its limit to `budget - 1` and verifies the
  actual calls. Wins can stop earlier. Reset and non-reset counts remain separate.

The reported local score is computed by the installed SDK and retained in each
run's scorecard. Batch means average every included game/seed, including valid
zero-score runs. Failures, timeouts, mismatched starts, missing results and changed
inputs prevent a completed aggregate; they are not silently assigned zero.

Local results are public-game development measurements, **not a hidden Kaggle
score**. They must not be compared numerically with the user-reported .25.
Public-game selection, sample size and seed policy are part of every report.

## Outputs

- `provenance.json`: source/runner hashes, framework commit and file hashes,
  dependency versions, complete game-file hashes, seeds and budgets.
- `progress.json`: incremental, explicitly running progress.
- `comparison.json`: final status, paired game results, per-variant aggregates
  only if complete, and all per-run rows.
- Each worker directory: `result.json`, `scorecard.json` (no API key),
  `actions.jsonl`, `worker.log`, and full SDK frame/action recordings.

Workers have a 300-second per-game timeout by default. Their errors remain
visible in the report. The command runs synchronously and exits nonzero if the
batch is incomplete. No detached automation or background monitor was created.

## Rebuilding the setup elsewhere

Create a new isolated Python 3.12 venv and install
`requirements.arc-compare.lock`. Clone
`https://github.com/arcprize/ARC-AGI-3-Agents.git` into its `framework` directory
and check out the recorded commit. Run `prepare_arc_compare_games.py --root NEW_ROOT`
with that environment to download public games. Existing caches are not refreshed
in place; another download can have different game versions and metadata hashes.
Do not treat it as the same corpus without checking the manifest.

## Submission feedback

The user prefers regular submission feedback and is not concerned about the
daily limit. Local comparison is useful for diagnosing changes, not a reason to
postpone submissions indefinitely. These commands do not upload or submit;
Kaggle runs and competition submission remain explicit separate actions.
