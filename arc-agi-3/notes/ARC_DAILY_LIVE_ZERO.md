# Live agent at zero since Sep 20 (practice gate does not see it)

Recorded 2026-09-21 from the daily run (`arc_daily.py`, reports in `D:\planet\arc_daily\`).

## What the daily run says

Practice (offline induction) is unchanged: 54 gated operators in 17 of 25 games, mean held-out
accuracy 0.461 best / 0.300 gated, against a baseline of 54 — verdict `same`. Because the gate only
compares practice wins, the daily verdict stays `same` while the live side is failing, so this
regression will not surface in the report's verdict line.

Live (`ls20`, `play.py`) cleared 0 levels in 250 presses on both Sep 20 and Sep 21, with 8 voluntary
resets and 0 deaths. On Sep 16-19 the same agent cleared 2 levels in roughly 550-575 presses with 19
resets, reaching level 1 at press 112-153.

The oracle (`ls20_chain.py`) completed 5 of 5 expected levels in 217 actions on every one of those
days, including both failing days. The API key, the network path to three.arcprize.org and the game
itself are therefore healthy; the fault is in the general agent.

## What changed between Sep 19 and Sep 20

No code in the planet folder changed. `play.py` (Sep 7), `eye.py` (Sep 3), `arc_daily.py` (Sep 7) and
`ls20_chain.py` (Sep 2) are all untouched, and the only edits in the last eight days are the
`alignment_*.py` experiment files (Sep 18-20), which `play.py` does not import.

What did change is the run signature recorded in `history.jsonl`. The meter now reads the budget bar
as `drain 2.0` where every earlier run read `drain 4.0`. Lives consequently run much longer — the
closing segments are 42, 43 and 41 presses against 19-35 before — the planner takes 8 voluntary resets
instead of 19, and the adaptive press budget (`PLAY_PRESSES = "auto"` in `arc_daily.py`, capped at 3x
the human baseline per level) terminates the run at 250 presses rather than ~570. The run therefore
ends before the agent reaches the point where it normally clears level 1.

The world-model line is not a discriminator: Sep 17 and Sep 18 both ran an all-`displace` operator
stack and still cleared 2 levels, so the `displace (promoted)` slot-1 operator that first appears on
Sep 20 is unlikely to be the cause on its own.

Likeliest culprit, then, is the meter's drain estimate for the ls20 budget bar rather than any recent
edit — worth reproducing by running `play.py` on ls20 directly and checking what `meter.py` derives
for `budget colour 11`.

## Loose end

There are no daily reports for Sep 10-15; the history jumps from Sep 9 to Sep 16.
