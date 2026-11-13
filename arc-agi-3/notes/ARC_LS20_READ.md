# Reading the real ls20 — what the live game actually is, and what scores higher

*Sep 2 2026. Jonathan: "what can we do to make sure the next attempt scores higher?" Answered
with evidence from three live runs the same day, the first ever to reach the real game.*

## 1. What the three live runs established

1. The first live 0 (arc_daily) was a RANDOM WALK's score: the live path ran arc3_client.play(),
   the v0 walker (probe, then random among live actions). PriorAgent — the Kaggle 0.25 agent —
   had never played live. Fixed: `--prior` drives PriorAgent through the live API exactly as
   practice drives it on the mocks.
2. PriorAgent live: 175 actions, GAME_OVER, 0/7 levels, not one score_up. Real agent, same 0.
   The mock/real gap is confirmed for the real agent, not just the walker.
3. PriorAgent + the budget law (below): 140 actions, GAME_OVER, 0/7. Waste cut from 40 dead
   presses to 6; still no understanding of the goal.

## 2. What ls20 actually is (read off the real frames, ls20_snaps.png)

Not a key-door maze. Yellow (4) is wall, green (3) is corridor, the dark-red piece (9) is the
player. Two gray-boxed glyphs are a HUD: the TOP box shows a TARGET SHAPE; the BOTTOM-LEFT box
shows the shape the player is CURRENTLY CARRYING, and it changes as the player passes through
certain places (it flipped at snap 2 and again at snap 6-7). So ls20 is SHAPE MATCHING:
transform what you carry until it equals the target (and, presumably, deliver it up the corridor
to the target box).

The bottom bar is a STEP BUDGET: it fills green as moves are spent (green cells 892 -> 988,
gray 84 -> 0). When it fills, one blue square at the right is lost (blue cells 12 -> 8 -> 4 ->
0: three LIVES) and the bar resets. Lives at 0 = GAME_OVER — exactly how every run died.
Level 1's baseline is 22 actions: a competent agent clears it inside ONE life.

## 3. The budget law (built the same hour, arc3_client.play_prior)

Every press spends the life bar, so an action the real surface has shown does NOTHING is a
free death. play_prior now tracks effects per action; after 3 consecutive nothings an action
is vetoed and the press goes to the action that has changed the world most. On the real game
it vetoed ACTION5 and ACTION6 by itself (they are no-ops in ls20; the moon's real map had
already said so). Waste: 40 -> 6 presses. Generalizes to any ARC-3 game: never pay for a
button that has proven dead.

## 4. What will actually score higher — in order of expected value

1. UNDERSTAND THE GOAL, NOT JUST THE WALLS (the big one). The agent needs three generic
   perceptions this game makes explicit and every ARC-3 game likely shares in some form:
   a. HUD detection — small boxed regions that change state WITHOUT the player entering them
      are state indicators, not terrain. Read them as variables.
   b. Budget/lives detection — a bar that fills monotonically with moves, and a count that
      decrements when it fills, is a resource. Plan within one life; prefer short paths.
   c. Goal = make indicators MATCH — when two indicator boxes exist, the objective is almost
      certainly equality. Then the search is over (position x carried-state) to reach the
      target state and deliver it.
   Together these turn ls20 from "wander a maze" into "find which tiles transform the carried
   shape, compose transforms to hit the target, deliver in <= 22 moves."
2. LEARN THE TRANSFORM MAP FROM THE MOON. The real transition log + frames already show where
   the carried glyph changed; correlating player position at each flip gives the transform
   tiles. That is exactly a moon roll with position attached — one more field in the log.
3. PRACTICE ON THE REAL SURFACE, NOT THE MOCKS. Scorecards are cheap; the mocks measured the
   wrong game. The daily should try ls20 live every day as the practice AND the exam, with the
   real transition log rolling the moon. A real-frame replay harness (the 9 snapshots + log)
   can regression-test the HUD reader offline.
4. THE KAGGLE ATTEMPT. The Kaggle set is many hidden games, not ls20 — so generic priors (1a-c,
   the budget law) are what transfer. Do NOT spend a Kaggle attempt until the live ls20 clears
   at least level 1; that is the cheap signal that the priors work on a real game.

## 5. Honesty

Two of today's gains are certain (PriorAgent now plays live; dead buttons no longer burn
lives). The game reading in §2 is inference from 9 frames and one transition log — the HUD
and lives interpretation is strong (the counts move exactly as described) but the shape-
transform mechanic is a hypothesis until the position-tagged log confirms which tiles flip
the glyph. The claim that clears level 1 is §4.1c; until it does, the score is 0 and should be
reported as 0.
