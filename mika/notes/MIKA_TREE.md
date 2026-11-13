# Mika's memory as a growing tree of cubes (Oct 16 2026)

Jonathan:
- *"she is kind of like a plant and she should grow as she processes things right? there would be different kinds of growth too. she is like the core and then each game would be different trunks in different directions and they would get their own branches and grow a little at a time"*
- *"each cell growth would be like adding another cube into our space right?"*

Code: `planet/mika_tree.py`. The data lives in `D:\planet\mika\tree\`. Hooked into `mika_mind.py` (backup `mika_mind.py.bak_20261016_before_tree`).

## The shape

Every node is a cube with the same fields: `id, kind, parent, born, data, cells, strength, evidence`. Adding a cell = adding a cube inside its parent, which is the market cube's recursion applied to her own memory.

| Node | File | What it holds |
|---|---|---|
| **Core** (her) | `tree\core.json` | Lessons that should work in any game. A lesson starts as a **seed** (seen in one game) and moves into the core when a **second game confirms it**. |
| **Trunk** (one per game) | `tree\<game>\trunk.json` | Lives played and how many levels she has cleared. |
| **Branch** (one per level) | `tree\<game>\L<n>.json` | State: growing, stalled or cleared. |
| **Cell** (a cube inside a branch) | inside the branch file | `route` (the press route), `effect` (a thing that did something), `pruned` (tried 3+ times, never did anything), `snapshot` (the screen just before the winning press, plus the press and the things on screen), recipe steps. A cell's **strength** grows each time a life confirms it. |
| **Ring** (one per day) | `tree\rings\<date>.json` | That day's growth events, by kind. |

## Kinds of growth

| Growth | In a plant | For Mika |
|---|---|---|
| **tip** | growing at the tips | reached a level for the first time |
| **thicken** | a growth ring | did a known thing again or better (a route held, a route got shorter) |
| **light** | growing toward light | found something that changes, advanced a recipe step, saved a winning snapshot |
| **prune** | dropping a dead branch | stopped feeding a thing tried 3+ times that never did anything |
| **graft** | a branch onto another trunk | a lesson confirmed in a second game moves into the core |
| **stall** | no growth | a life with no tip, light or thicken on the level she is stuck on |

## What changed in how she plays

- **Pruning.** Pruned things go to the very back of the body's list (band 5).
- **Asking for a repeat.** When a recipe step's thing is no longer offered, she puts it back at the front (up to 3 times per step). This is the first time the mind can add a candidate: before, it could only reorder.
- **Reflection sees the tree.** Her reflection now gets two extra lines: what the screen looked like just before she won each level, and the lessons she carries.

## First build (moved from her journals, Oct 13–16)

**Core:** two **seeds**, read from her own records by Claude, not yet confirmed by her:
1. *A thing that changes each time it is touched may need touching more than once before the way opens.* From ls20 life 1, where the colour-0 thing changed 8 times before the level came.
2. *Some levels are won by arranging things first and then doing one final action; the final action does nothing until the arrangement is right.* From the sp80 level-1 route: move the bar, then pour.

**sp80:** 10 lives.
- **L1** is cleared. The route has strength 9, and there is a snapshot: the bar sits at rows 20–23, columns 24–43, under the spout (columns 36–39), with its ends over the two cups (columns 16–27 and 40–51); the winning press is action 5. There are 5 pruned cells.
- **L2** is stalled, with 9 lives on it and 22 pruned cells. It has no effect cells at all: nothing on it has ever changed.

**ls20:** 10 lives.
- **L1** is cleared: a 36-press route plus a snapshot.
- **L2** is stalled, with 4 effect cells and 3 pruned.
- **L3** has 1 life (life 1) and 3 effect cells.

**Rings Oct 14–16:** every day, thickening on level 1 and a stall on level 2 in both games. That is the plateau, now visible as a stall instead of hiding inside "levels: 1".

## Test lives on ls20 level 2 (Oct 16, afternoon)

1. **Life 11.** She asked the body to repeat the key 3 times, but play.py threw the request away: it only accepted an order with exactly as many candidates as it had offered.
   - **Fix:** `play.py` now accepts an order that adds back a thing she saw this life, as long as all of the body's own candidates are still there. Backup: `play.py.bak_20261016_before_repeat`.
2. **Life 12.**
   - **The repeat works:** six key changes in a row (steps 1–6 of 11).
   - **The refill steps failed:** they "did nothing" 3 times (the bar was full), so the recipe switched off.
3. **Life 13** (400 presses, refills briefly removed from the recipe).
   - She walked **all 8 key changes** and then the door (colour 5 at 39,13), but the door did nothing.
   - The log shows why: after every key change, the body hit **RESET** for energy ("budget 2 left"). A reset puts the level back, so the changes never added up.
   - In life 1 the refills between the changes kept the energy up so they could add up.
   - **So refills are part of the recipe after all.** They are back in. A refill step is now never a failure: with a full bar it is just skipped.

**New seed lesson in the core:** *A reset puts the level back to its start, so a change being built up is lost; while building one, keep the energy up (refill) instead of resetting.*

At that point the mind could steer *what* the body tries, but not *when it resets*. That is what the evening's build added.

## Oct 16 evening: changing her mind

Jonathan:
- *"the paths she builds would have some strength to them right? so if an option becomes heavier than the path then could it break and we switch to that option?"*
- *"she would also need to tell herself to wait and weigh her options sometimes. and also being able to react to things"*
- *"we can add steps in between the path blocks and those new instructions just have to end with that button press"*
- *"after getting that first solve on a level, wouldnt she want to start exploring other paths too? ... competing with herself. if she has to redo level 1 every time she could figure it out completely"*

Five pieces were built (`mika_mind.py`, `play.py`, `mika_tree.py`, `mika_daily.py`; backups `*.bak_20261016_before_weigh` and later):

| Piece | How it works |
|---|---|
| **Weighing** | Before the body resets, she pauses and weighs. Path strength = 1 + the steps built since the last reset. The reset's weight: 0 if the next target is affordable with a press to spare, 2 if exactly affordable, 99 if not (0 when the target is a refill, since stepping onto it refills). The path holds while it is heavier. Budget, target, "experiment over" and "dead end" resets are all weighed; each pause is logged. |
| **Detours between blocks** | Mid-recipe with the bar low, a refill goes first, then the recipe picks up where it left off. She takes the refill **nearest the thing she just changed** and never walks back to a ring she already spent this try. |
| **Leaderboard and trimmed routes** | Each level keeps a record (presses, budget left) and logs "new personal best". A route that has held twice is tried once with its no-op presses dropped (≤ 3 cells changed, i.e. only the energy tick). If the trimmed walk fails, she resets and walks the full route, and that trim is never tried again. |
| **Study lives** | `--mode study`: on a level she has a route for, she looks around for 60 presses (the body leads, steered toward things that did something), then resets and walks her route. The daily run is now **one push life and one study life per game**, one after the other. |
| **Surprise watch** | On every route press she compares the cells changed with what that press changed last time. One surprise is logged; two in a row break the path and the body leads. No route has been surprised yet. |

## Oct 16 night: the test lives, and what they turned up

**Trimmed routes worked the first time they were tried:**
- sp80 level 1: **5 presses** (was 8; human 39).
- ls20 level 1: **25 presses** (was 36; human 22), now her personal best.

**ls20 level 2: cleared again for the first time since life 1 (Oct 13).** Life 17 cleared it at press 129: 104 presses on the level, against 118 in life 1 and a human baseline of 123. She now remembers a 45-press route for it. Getting there took six fixes, each found by a test life:

1. **"Unreachable" is not a failure** (life 14). Eight presses into level 2 the body did not yet trust its *down* move, so the key looked unreachable three times and the recipe was dropped. Now she waits 10 presses while the body learns its moves, then asks again. She gives up only after 6 tries.
2. **The recipe starts at the last put-back** (from the Oct 13 log). Life 1 poked the key 8 times, but over four tries: three resets wiped its progress. The try that won was *poke, refill beside the key, poke, poke, far refill, door*: **3 pokes, not 8**. The 8-poke recipe could never work. Resets are now recorded in every life (`resets_at`), and a recipe is the stretch after the level's last reset. Life 1's resets were filled in from its log.
3. **A refill is a refill** (life 16). Walking into a ring raised the bar, but the body went on bumping and filed "nothing". Its habit reset ("experiment over, nothing happened") then wiped the key change. Now the experiment ends as a refill the moment the bar rises, and habit resets are weighed like budget resets.
4. **A poke is a touch, not a test of the move** (life 16). The press that changed the key also "proved" the *down* operator wrong (the key's colour changed under it), so down was retired and the refill three presses away became unreachable. Bumps into a thing are no longer counted against the move.
5. **No second detour on a stale reading** (life 17's first try). Right after a refill she still read the old energy, sent the body back to the spent ring, and lost 6 presses. That was enough to leave the far ring out of reach.
6. **The joint between levels: relations.** On level 1, life 1 learned *"touch the colour-0 thing until the pattern shown in colour 9 matches the colour-5 thing"*, and the body carried that to level 2 inside the same life. **Walking a route never learns it**: the level clears between two of the body's sleeps, so the relation was never read. Since routes began on Oct 13, every level 2 started blind.
   - Now, as a level clears, the body takes **one last look** at all of the level's presses for relations.
   - Every relation learned is **kept in her journal** (`relations`). When a life arrives at a level having learned none on the way, she hands the body the ones from earlier lives.
   - Life 17 learned it on level 2 (3 states) and kept it. It also carried it into level 3, where the body ran the loop for the first time: touch the colour-0 thing at 11,51 until it matches the colour-5 thing at 49,53, then walk to it. The door did not open in the presses left.

Two more fixes: a ring reached on the winning press was briefly filed as a refill, because the new level's full bar looked like one (fixed, and life 17's record corrected). And two lives started at once closed each other's scorecard (one key, one open game), so lives always run one after the other.

**ls20 life 17, level 2, the try that won:** poke the key → detour to the refill beside it (the mind **held her path** instead of the budget reset) → poke → poke → the far refill → the door → **LEVEL 2**. Over the life: she held her path 4 times, let it break 4 times (the target was truly out of reach), and took 2 refill detours.

**The tree after life 17.**
- ls20 L1 route: strength 16.
- ls20 L2: personal best 104 (was 118), a 45-press route, a win snapshot.
- ls20 L3: first light (14@46,31 changes).
- The core keeps the seed *reset-undoes-change*; the night's lives confirmed it again.

**sp80 study life (life 11).** She looked around level 1 for 58 presses, reset, and walked the trimmed route, which cleared level 1 in 5 presses (press 63 of the life). She now remembers the 5-press route. **Level 2 is untouched by all of this.** It still needs an arrangement planner (three bars, upside down).

## Next

- **ls20 level 3.** The relation loop runs; the door did not open yet. Watch the daily lives.
- **sp80 level 2: transfer.** The level-1 snapshot sits in the tree and in her reflection. Carrying it into *action* needs a planner that tries arrangements before the final press. The planet body has no such plan type yet.
- **A picture of the tree** (cubes growing over the days) as a page she and Jonathan can look at.
