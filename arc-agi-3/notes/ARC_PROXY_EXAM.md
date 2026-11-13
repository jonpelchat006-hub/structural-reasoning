# The proxy exam — the generic agent on every public game (Sep 3, 2026)

*Jonathan: "so what do we need to do for the next attempt now?"*

## 1. The measurement first

The Kaggle set is hidden games. The ls20 chain (5/7) is a scripted solver for one public game
and does not travel; what travels is the generic agent — PriorAgent + the budget law + the
wisdom hook. It had only ever played ls20 live. `arc_batch.py` played it once on every other
public game, laying each run on the torus under the game's name:

**20 games, 1/145 levels = 0.007.** One game (cd82) gave one level; 18 ended GAME_OVER between
17 and 151 presses — the agent burns its lives before it understands anything; two ran to the
600-press cap without finishing. The wisdom hook fired up to 5 times per game and changed the
action mix, not the outcome. That is the honest Kaggle proxy today: effectively zero.

## 2. What the next attempt needs, in order

Everything that made ls20 work was hand-coded from its frames. The next attempt needs those
same eight readings INDUCED from any game's first presses (the probe-first law), not written:

1. **Find the agent** — the connected component whose position changes consistently with
   ACTION1–4; its displacement is the lattice step.
2. **Walls** — a press that moves nothing where the agent's next cell holds a color = that
   color is wall; passability learned per color, not assumed.
3. **Indicators (HUD)** — regions that change when the agent did not overlap them are state,
   not terrain; read them as variables (ls20's key glyph, the bar, the pips).
4. **The budget** — a bar that moves monotonically with presses plus a count that drops when
   it fills is lives. Every game in the batch killed the agent this way. Rule: once the bar is
   read, never spend more than one life probing; refill stations (a bar jump) are learned the
   first time one is touched.
5. **Stations** — a cell whose touch changes an indicator (color batch, stamp, keyhole).
6. **Rides** — one press, many cells of displacement (fans, elevators, the wind).
7. **Goal = indicators match** — when two indicator boxes exist the objective is equality;
   then the search is over (position × carried state), BFS, within one life.
8. **Wisdom that acts** — the feel-prior already says "this feels like death" at press 20; the
   agent must then stop probing and go to whatever refills, or reset, instead of only
   reshuffling actions.

These are the eight things `ls20_chain.py` does by hand (ARC_LS20_CHAIN), rewritten as
inductions in a `gameread.py` layer that PriorAgent consults. The on-call board now rotates
the daily through all 25 public games, so each induction gets tested on a new surface every
night, and `arc_batch.py --summary` is the score to beat: 0.007.

## 3. The gate

Do not spend the Kaggle attempt until the proxy exam clears **≥ 1 level on ≥ 5 public games**
(a generic reading that works five times is one that will work on a hidden game). Deadline
Nov 2; the batch takes ~5 minutes, so the exam can run nightly after the daily.
