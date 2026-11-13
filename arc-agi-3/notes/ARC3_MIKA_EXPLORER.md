# ARC-AGI-3: Mika's explorer and the look-back lens (Oct 21, 2026)

**Context.**
- Jonathan, Oct 21, chose **"Our agent + paper only"**, and gave permission to run and submit on Kaggle.
- He added: *"she tries to fill out her map of each level and their solves, but once that fills out she could look back on it through a different lens ... if she moved this way earlier she could have learned this lesson faster, or if she did some action some different way she could have learned 2 things at once."*

## Where things stand

**The Kaggle board, Oct 21** (downloaded with the Kaggle CLI):
- Tufa Labs is first at 68.91.
- Gold line (rank 19) 37.98, silver (rank 228) 32.25, bronze (rank 457) 30.91.
- About 1,800 teams sit at 25–33, by copying Franzen's public Milestone-2 notebook (the Duck harness, Qwen3.8-Flash-Next on an RTX Pro 6000).

**Our submissions:**

| Submission | Score |
|---|---|
| PriorAgent v1 | 0.12 |
| PriorAgent v9 | 0.14 |
| PriorAgent v10 | 0.25 (rank 3,069 of 4,592) |
| Orbital learning v1 | 0.00 |
| **Mika v3n (Oct 21)** | **0.29** |
| Mika university (Oct 22, see `ARC3_UNIVERSITY.md`) | pending |

The limit is **1 submission per day**.

## The offline bench (`D:\planet\arc3`)

- **What it runs:** the 25 public games from the competition data, with the official `arc_agi` engine and the official scorecard code, one scorecard per game.
- **Scoring:**
  - A level scores `min((human/agent actions)² × 100, 115)`.
  - Level k is weighted k; unfinished levels score 0.
  - A game scores the weighted mean of its levels; the total is the mean over games.
  - RESETs count as actions. RESET keeps the level.
- **End-to-end check:** the same file was run through a local competition-mode gateway with the official `main.py`, and gave the same score.
- **Running it** (on the PC):
  - `harness.py <file>:<Class> --workers 12 --seeds 8` takes about 4–5 minutes per variant.
  - Launch it detached: `Invoke-CimMethod Win32_Process Create`. A redirected `Start-Process` stalls the bridge.
- **Files sent to the PC:** stage each under a unique name and check its md5. A second staging of the same path can deliver the stale copy.
- **Baseline:** PriorAgent v10 (the 0.25 submission) scores **0.119** offline, with 2 of 183 levels.
- **Variance:** a single run doesn't tell you much. One agent ranges from 0.34 to 0.74 across seeds. All numbers below are means over 8 seeds unless noted.
- **Public is not hidden.** Offline went from 0.12 to 0.52 (about 4×); hidden only from 0.25 to 0.29. The explorer's cheap public wins are not typical of the hidden games.

## The agent (`mika3/explorer.py`, `mika3/explorer2.py`)

**What she does:**
- Each level is a graph. A state is the frame with ticker lines masked; the ticker lines are the life and step bars on the border.
- She tries what she hasn't tried, walks the shortest known path to the nearest state with something untried, and keeps away from presses that ended a life.
- She learns the life budget from deaths at the same press count, and plans inside it.

**Clicks:** one per object (a same-colour region). Kinds (colour × size) that change things are tried first. Kinds that never change anything sink to the back.

**Look-back lessons (Jonathan's lens):**
- When a level is won, she takes the shortest path in her own map from the start to the win.
- The kinds clicked on that path go first on the next level.
- The colour entered on the winning press becomes a goal colour.

**Movement model (verify-before-act):**
- She learns each move's displacement, the sprite's look for each direction, and which colours are passable, blocking, pushable or deadly.
- She skips presses the model can predict and plans through predicted states.
- The strict version trusts a move only after 3 correct predictions and 0 wrong ones.

## Results (offline, 25 public games, 3,000 actions per game)

| Agent | Score (8 seeds) | Levels per seed |
|---|---|---|
| PriorAgent v10 | 0.119 (1 run) | 2 |
| **v3n: explorer + look-back lessons** | **0.518** | 21.5 |
| + adaptive momentum (lesson about *how* to learn, below) | 0.516 | **22.3** |
| + replay last level's route at level start | 0.469 | 21 |
| + momentum always on (2.0 / 0.8) | 0.377 / 0.399 | 22 |
| + learned order from cross-game look-back, weight 0.5 / 1.0 | 0.231 / 0.105 | 19–20 |
| + clock-pixel masking | 0.518 (no change) | 21.5 |

**Earlier, on 4 seeds:**

| Agent | Score |
|---|---|
| v1 | 0.567 |
| v3n | 0.618 |
| + strict movement model | 0.579 |
| + loose movement model | 0.389 |
| + diminishing returns per click kind | 0.358 |
| + clicks only after moves are exhausted | 0.520 |

**Separately:** 20,000 actions instead of 3,000 adds about 8 levels but no score.

**What the table says:**
- **The score lives in a few games' cheap first levels**: g50t, lp85, r11l, m0r0, sc25, vc33. Each heuristic speeds up some games and slows others.
- Because the score is quadratic in efficiency, **anything that reorders her first presses tends to cost more on the cheap wins than it gains elsewhere.**
- **Momentum** ("keep pressing what just changed something"):
  - Faster: bp35 L1 (1,918 → 216 presses), vc33 (37 → 11), sc25.
  - Slower: m0r0 (46 → 468) and r11l (35 → 136).
  - **Adaptive momentum** turns it on for the next level only if the won route was long runs of one press. It is neutral on score and clears more levels.
- **The learned order** (a conditional logit over candidate features, fit to the presses on won routes, left out game by game):
  - It does rank the route press higher on games it has never seen: mean rank fraction 0.24, against 0.5 by chance.
  - It still lowers the score, and more weight lowers it more.
  - Predicting the route is not the same as finding it cheaply.
- **Bug found and fixed:** a shadow-prediction slice error near the frame edge. When it fired, she would wipe her map and reset. It is in the Oct 21 submission, and fixed in Oct 22's. The 8-seed runs show it never changed a score.

The professors, departments and board built on top of these runs are in **`ARC3_UNIVERSITY.md`**.

## The look-back lens, measured

For every won level (v3n, 8 seeds, 6,000 actions), compare the actions she spent with the shortest path in her own finished map.

| Game, level | Spent | Shortest in her map | Human |
|---|---|---|---|
| ar25 L1 | 774 | 15 | 32 |
| cd82 L1 | 631 | 5 | 55 |
| ft09 L1 | 1,246 | 4 | 43 |
| s5i5 L1 | 1,190 | 14 | 20 |
| sp80 L1 | 472 | 4 | 39 |
| tu93 L1–L4 | 352 / 44 / 1,629 / 691 | 18 / 10 / 20 / 17 | 19 / 16 / 34 / 42 |
| vc33 L1–L2 | 24 / 168 | 3 / 13 | 7 / 18 |
| **All 183 won levels** | **22,153** | **361** | **858** |

**What it shows:**
- With what she knows once a level's map is complete, she would beat the human baseline: **0.42× the human's actions**.
- She spends **61× that** to learn it.
- The score is lost entirely in how she learns, not in what she knows. That is the lever Jonathan's idea points at.

**What the won routes are made of (cross-game):**
- **Runs of one press.** For example, ar25 is A2×10 then A3×5, ft09 is 4 clicks on one kind, and s5i5 is two kinds ×6.
- **The final press** was a click 69 times, A5 29 times, and a move 85 times.
- In games with both moves and clicks, 7 of 10 won with no click at all: ar25, cd82, cn04, ls20, m0r0, sp80 and g50t.
- **Lessons hold within a game:** lf52 wins every level with (14,2)+(2,0); sc25 with (0,1); vc33 with (9,2).

## Next

1. Better professors: lessons about what to look at and what the goal is, not just how persistently to press (see `ARC3_UNIVERSITY.md`).
2. Where waste is large and safe to cut: reachable-but-exhausted maps (g50t, ls20 L2: up to 2,000 re-presses). The frontier is unreachable through known edges.
3. **The paper (Nov 8):**
   - verify-before-act (slot filler: 33/33 when gated);
   - the look-back waste metric (0.42× human known vs 61× spent);
   - the cross-game route anatomy;
   - the university (students grade professors; rotating finals grade the board);
   - honest ablations, including the negative results.
