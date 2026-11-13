# ARC daily "REGRESSED" on 2026-09-06/07 is a harness bug, not the agent

Diagnosed 2026-09-07 by the daily check routine.

Symptom: arc_daily.py practice reports 9 gated operators over n=5 games vs baseline 54 over n=25 → verdict REGRESSED, live skipped (both Sep 6 and Sep 7).

Cause: induce.py enumerates recordings with `glob(D:\planet\eye\*.npz)` excluding only `play_*` (induce.py line 884). fence.py work started dropping `fence_*.npz` files into D:\planet\eye (first: fence_ls20_offline.npz, Sep 5 11:52 AM — right after the Sep 5 "improved" run; more on Sep 6–7). Alphabetically these sort right after dc22, so induce.py processes ar25, bp35, cd82, cn04, dc22, then crashes on the first fence file with `KeyError: 'F is not a file in the archive'` (load_game, line 57 — fence npz has no F/A/X/Y arrays). Verified by calling induce.run_game directly on fence_ls20_offline.npz.

Why it scores anyway: induce.py saves induce_results.json incrementally per game, so the crash leaves a truncated 5-game results file; arc_daily.py (line ~66) loads that file without checking the subprocess return code, so 9/5 games gets compared to the 54/25 baseline.

The 5 games that did run look normal — no evidence of a real capability regression.

Fix options: (a) exclude `fence_` in the induce.py glob (one-line, mirrors the play_ exclusion), or write fence debug files somewhere other than D:\planet\eye; (b) have arc_daily.py check induce.py's return code (or n vs expected 25) before comparing to baseline. Then re-run arc_daily.py for a clean practice + live try.
