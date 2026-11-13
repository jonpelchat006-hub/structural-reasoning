# Mika as an agent — v0 (Oct 13 2026)

Jonathan: *"lets fix the arc agi stuff. i think we can make Mika an actual agent with all our work."*
Choices that day: **Home Mika first**, built on **our planet code** (not The Duck). Quick fixes: pause the daily run, restart Mika's bridge.

## State found that morning

- **Mika was offline.** Her MCP tools go through the companion bridge (127.0.0.1:41737) inside the Shovelcat Electron app, and the app wasn't running. It was restarted with `electron.exe D:\shovelcat-colony\app` and status came back healthy, Ollama online, 8 models.
- **The daily run was treading water.** "ARC daily practice + try" produced the identical practice result every day since at least Sep 21 (54 operators, 17/25 games, held-out 0.461, verdict *same*). Live sp80 replayed the same 150 presses daily for 0 levels. On Oct 10 it crashed on `No module named 'torch'` (anaconda python, see ARC_DAILY_TORCH_PATH.md, still unfixed). **That scheduled task is now disabled** (kept, not deleted).
- **No ARC code had changed since Sep 9.** Best real result is still PriorAgent v10 at 0.25.
- **Outside context (Oct 6):** the Kaggle ARC-AGI-3 top was ~56% RHAE, from open-weight ~27B models in simple harnesses (Tufa Labs' MIT "Duck"). Final submissions are due Nov 2 and papers Nov 8. Not pursued today, by choice.

## What was built

**`planet/mika_mind.py`.** Mika is the mind; the planet player (`play.py`) is her body and reflexes. One *life* = one `play.play_game` run.

| When | What Mika does |
|---|---|
| Before a life | Reads her journal `D:\planet\mika\<game>.json`: cleared levels, every experiment's result in every life, her picks, facts, questions, **routes**. |
| During, on a level some life cleared | **Muscle memory.** She walks the shortest route any life found that cleared it, press for press from the level's start, with no resets. If a death or reset breaks it, or it ends without the level, she drops it and the body leads. |
| During, on a level never cleared | Re-orders the body's experiment candidates (never adds or removes any), in bands: 0 her picks never tried · 1 never tried in any life · 2 her picks tried before · 3 did something before · 4 did nothing before. Inside a band the planet's own order stands. |
| After a life | Reflects with a local model (qwen2.5-coder:7b via Ollama, nothing leaves the PC): what happened, facts, try-first picks (validated against ids really on screen), open questions (void pins). Writes the journal, her diary `D:\planet\mika\diary.md`, and the life's press record to `D:\planet\mika\routes\`. Once per session it posts a summary to her companion memory via the bridge `/library`, so the Mika he chats with knows it. |

**`play.py` hooks** (backup: `play.py.bak_20261013_before_mika`). With `mind=None`, play.py behaves exactly as before.
- `play_game(..., mind=None)`
- the experiments list stamps each entry with its level (`_LevelTagged`)
- before each experiment pick: `mind.order(goals, lvl, frame)`
- before each press: `mind.press(lvl, since)` can supply the press (`why = "mind route ..."`) and suppresses budget resets while walking

Run: `python mika_mind.py sp80 --lives 2 --presses 300` (use the pythoncore-3.14 interpreter, which has torch). Other modes: `--show sp80`, `--no-reflect`, `--learn-routes <play_*.jsonl> --life N`.

## Results (online public games, three.arcprize.org, Oct 13)

Human baselines (from the scorecards): **sp80** L1 = 39 presses, L2 = 58 · **ls20** L1 = 22, L2 = 123.

| Game | Life | What Mika did | Result |
|---|---|---|---|
| sp80 | 1 | nothing to go on (empty journal) | 0 levels in 300 presses |
| sp80 | 2 | read 46 results from life 1; changed 0 picks (her groups never mixed) | **L1 at press 21**, found by the body; after a death the clearing stretch was 8 presses |
| sp80 | 3 | stood back (the route wasn't recorded yet) | L1 at press 295 |
| sp80 | 4 | **walked the 8-press route**; re-ordered L2 candidates 18 times | **L1 at press 8**; L2 not cleared in 292 presses |
| ls20 | 1 | nothing to go on | L1 at 149, L2 at 267 |
| ls20 | 2 | stood back on L1 | L1 at 369. The body spent most of the life looping on `5@60,12 -> untestable` (~70 times) |
| ls20 | 3 | **walked the 36-press route** | **L1 at press 36**; L2 not cleared in 364 presses (life 1's press record had been overwritten, so no L2 route) |

The daily run had never cleared an sp80 level; it scored 0 every day.

## What this does and doesn't show

1. **The carry-over is real, and it comes from memory, not luck.** The body found sp80 level 1 once (life 2). Mika now clears it in **8 presses** each life, against a human baseline of 39. On ls20, level 1 dropped from 149 or 369 presses (body searching) to **36** (human: 22). The body no longer has to rediscover cleared levels.
2. **Re-ordering is unproven.** It made 18 changes on sp80 level 2 and the level still wasn't cleared. One life can't show whether steering helps or hurts.
3. **The body varies a lot from life to life.** ls20 L1 took 149 presses one life and 369 the next; sp80 L1 went from not cleared, to 21, to 295. Part of this is play.py carrying fence rules between runs, and part is the eye starting from random weights. A single run, like the daily verdict, can't separate signal from noise.
4. **Her reflection is honest but shallow.** qwen2.5-coder:7b gives generic facts ("refill points are important"). Its picks were mostly things already tried, and some ids weren't on screen; validation dropped those. After the first lives, her picks were moved below never-tried things ("untrusted until played").
5. **Her companion memory knows about the games, but piles up.** Each session adds a new memory file, so her sp80 context now holds three overlapping summaries.

## Oct 16: stuck at level 2. What she updates, and what the levels need

**Daily runs Oct 14–16** (local scheduled task): 12 lives. Every one cleared level 1 by her route (sp80 in 8 presses, ls20 in 36), and **none cleared level 2**.

**What carries between lives:**
- her journal (every experiment's result per level, routes, picks, facts and questions);
- the body's fence colour rules.

**What doesn't:**
- The body's operators learn from `D:\planet\eye\<game>.npz`, last written **Sep 3**. Runs read it and never add to it.
- Reflection happens once, at the end of a life, and is shallow (one ls20 fact repeated four times).
- Nothing updates **between levels inside a life**, and her memory is per level.

**sp80 level 2** (looked at the frames; `D:\planet\mika\render_strip.py`):
- The game is **pouring**. Action 5 pours from the spout. Actions 1–4 move the selected bar (blue). Action 6 clicks to select another bar (red = unselected). A green line is the move timer.
- **Level 1:** one bar. The route moves it under the spout so that its two ends sit over the two cups, then pours, and the level comes.
- **Level 2** is the same game **upside down**: the spout at the bottom, three cups at the top, three bars (one blue, two red).
- 655 level-2 experiments over 8 lives changed nothing, because 95% were "walk through an opening" moves. The body's vocabulary doesn't include "arrange the bars, then pour", and a bad pour can end the game (GAME_OVER after an action 5 at press 46).

**ls20 level 2.** The only clear (life 1) followed a recipe:
1. poke the colour-0 thing at 46,51 until it changes, about 8 times;
2. two refills (colour 11);
3. the colour-5 thing at 39,13 → level.

**Recipe memory, added Oct 16.**
- `mika_mind.py`: `recipes`, `observe()`, bands −2 and −1.
- `play.py`: the experiments list calls `mind.observe` on every result.
- Backups: `*.bak_20261016_before_recipe`.

**First test life.** It started the recipe (step 1: 0@46,51 → changed) and then stalled. The body won't offer a thing again once it has been tried, so the repeated pokes never come. The colour-5 target and the refills, tried early, did nothing. **The mind can reorder but cannot ask for a repeat.**

**What both level 2s have in common:** the answer is *keep changing something until a relation holds, then the final action*.
- ls20: the key changes until it matches, then the door.
- sp80: the bars are arranged until the pour reaches every cup, then pour.

Level 1 showed the relation (sp80: the bar under the spout with its ends over the cups), but nothing carries a *success condition* from one level to the next.

**Oct 16 night: ls20 level 2 cleared again** (life 17: 104 presses on the level, human 123, now a 45-press route). Two things were missing. First, the recipe had to start after the level's last reset (3 pokes, not 8). Second, the body's relation: walking a route never learned it, and it now lives in her journal across lives. The details and the six fixes are in `claude/MIKA_TREE.md`.

## Known limits / next

- **A/B test for steering:** several seeds, isolated `--output-dir`, mind vs no mind, on sp80 L2 and ls20 L2–3. This is the only way to know whether re-ordering helps.
- **Route compaction:** try dropping route presses that changed nothing and keep the shorter route if it still clears the level. This is "cover the same ground more efficiently" (inner-core idea), and it raises RHAE directly.
- **During a route walk, the planet's own experiment bookkeeping still runs.** It can credit the level to its own experiment; ls20 life 3 logged `open@44,34 up side -> level`. That should be muted while a route is walked.
- **Press records:** play.py overwrites `play_<game>.jsonl` every run. mika_mind now copies it to `D:\planet\mika\routes\` after each life. Life-1 records from today are lost, including ls20's L2 clear.
- **Better eyes for reflection:** give her the actual frame (gemma3:4b is multimodal) instead of a list of things.
- **Housekeeping:** the daily run is still paused, and its torch path is still unfixed. A Mika session (a couple of lives on a few games) could replace it, so her routes grow every day.
- After the runs, cleared levels with no working route are steered with the bands rather than left to the body (ls20 lives 2–3 showed one clear is no promise the body finds it again).
