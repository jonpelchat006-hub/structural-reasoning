# ARC-AGI-3: the core card, twelve slots tested against the wins (Oct 23, 2026)

Jonathan, Oct 22–23:
> "she doesnt have her inner core filled out so she doesnt have any starting place on her own i think. we just gave her the shape but there were 12 points to fill in so there should be that many rules she can start with right? ... any game should be some combination of those 12 points?"

> "the core points would be like our void too right? they would have to be defined by what we put in them which would be the proofs and examples. its like we can only approach the actual rule like a limit."

> "im imagining it like 4/(4-x) on a graph where it goes to infinity at 4 and the lines go up on either side. then the rules we use would be like drawing a line that connects both sides and we want to get as high up as we can?"

> "lets try the new ideas"

## The twelve slots: six rules, each with a do-side and a mirror side

| Rule | + (do-side) | − (mirror side) | How the frames show it (`coreslots.py`) |
|---|---|---|---|
| CONTROL | moves | blocked | + a same-colour thing turns up shifted; − the press changed nothing on the board |
| CONTACT | makes / collects | removes / kills | + a thing at the acting point changed colour, vanished or appeared; − game over, or back to the start picture |
| MATCH | match | differ | + the press made two things equal (same picture up to flips); − made two equal things differ |
| PLACE | in / onto | out / apart | + the moved thing now touches a still thing; − it stopped touching one |
| COUNT | gather | spend | + something small changed far away, or the last of a colour went; − the step bar or clock ticked |
| ORDER | target shown | undo / reverse | + the press made a thing equal to a thing that never changes on the level; − the board came back to a picture already seen |

## Test 1: the 16 levels the hybrid won, read from the model's own explanations

These are the smoke runs v3 and v4 (ft09 levels 1–6, ls20 1–4, vc33 1–6). A reader agent tagged each win from the model's "Level N solved: the mechanic was …" lines and the presses just before. It split ORDER+ into *target shown* and *order of presses matters*.

| Slot | Levels that needed it (of 16) |
|---|---|
| MATCH+ (make equal) | **16** |
| ORDER+ (target shown) | **16**, exactly the same levels as MATCH+: every match target was displayed (a legend, the box glyph, a coloured gap) |
| CONTACT+ | 13 |
| CONTROL+ and PLACE+ | 10, always together (all of ls20 and vc33; ft09 steers and places nothing) |
| ORDER+ (order of presses matters) | 9 |
| COUNT+ | 7 |
| CONTROL− | 5 |
| MATCH− | 4 |
| COUNT− | 3 (the ls20 fuel) |
| ORDER− | 2 |
| CONTACT−, PLACE− | **0**. No press killed in any of the six transcripts |

**Every win condition is a combination of the slots.** What the slots miss is the *action model*: what each press does to the board. That is where the model spent its effort:
- one click changing five cells (ft09 5–6);
- colour cycles and key rotations (ft09 4, ls20 2–4);
- pistons that push the block (ls20 3–4);
- a fixed total of grey shared between arms, with limits (all of vc33);
- doors that carry a piece across (vc33 4–6).

The model found mechanics by trial and error and by analogy with the previous level. None of the `[Frame facts]` notes revealed a mechanic.

## Test 2: our 36 replayed winning routes (18 games), from frames only

**Method:**
- For each route, the arbitrary baseline is up to 150 random presses from the level start. Only presses that changed the board count, not presses that only ticked the clock or step bar.
- The winning press is read on the first frame after it, before the level-end animation.

**Coverage:**
- 32 of the 36 winning presses fire at least one + slot.
- The other 4 (cd82:0, cd82:1, r11l:0, sc25:1) show their effect only in the animation.
- This coverage is cheap: arbitrary presses fire the same slots almost as often.

| Slot | Winning presses with it | Routes using it | Levels where exploration met it | Route presses | Arbitrary board-changing presses | Lift (pooled / each game equal) |
|---|---|---|---|---|---|---|
| CONTROL+ moves | 26 | 33 | 34 | 84% | 76% | 1.1x / 1.0x |
| CONTROL− blocked | 3 | 4 | **36** | **1%** | (62% of all random presses) | boundary |
| CONTACT+ makes/collects | 17 | 26 | 25 | 36% | 32% | 1.1x / 1.1x |
| CONTACT− removes/kills | 0 | 0 | **32** | **0%** | 6.4% | boundary |
| MATCH+ match | 6 | 20 | 19 | 9% | 9.0% | 1.0x / 0.8x |
| MATCH− differ | 10 | 21 | 15 | 9% | 7.6% | 1.2x / 1.4x |
| PLACE+ in/onto | 8 | 19 | 19 | 15% | 7.3% | **2.1x / 2.2x** (9 of 18 games) |
| PLACE− out/apart | 12 | 20 | 22 | 26% | 10.8% | 2.4x / 1.5x |
| COUNT+ gather | 10 | 27 | 24 | 25% | 17.7% | 1.4x / 1.4x |
| COUNT− spend | 6 | 13 | 13 | 33% | 24.5% | 1.3x / 0.8x |
| ORDER+ target shown | 4 | 13 | 15 | 37% | 25.0% | 1.5x / 1.5x |
| ORDER− undo/reverse | 1 | 3 | **35** | **1%** | 41.2% | boundary |

**The 4/(4−x) picture shows up in the data:**
- Three mirror sides are pure boundaries: blocked, kills and undo.
  - They are almost never on a winning route (0–1% of presses).
  - Exploration meets them in 32–36 of the 36 levels.
  - They are the asymptote. You learn where it is by hitting it, and you win on the other branch.
- The other three mirror sides (differ, out/apart, spend) do occur inside wins. For MATCH, PLACE and COUNT both branches carry the chord.

## Test 3: +C, does the last win's form carry to the next level?

**Method:**
- 14 pairs of consecutive levels, both inside the school, in 5 games (8 of the pairs are tu93).
- The *form* is the + slots of level k−1's winning press, each with its binding: the colours of the still thing it arrived at, the thing touched, the far indicator, or the thing matched.
- The test is on level k (`bindings.py`).

| Slot of the last win | Pairs (games) | Route: slot with the bound colour | Arbitrary: slot with the bound colour | Lift with the binding | Lift for the slot alone | Next winning press has the bound form |
|---|---|---|---|---|---|---|
| CONTROL+ | 13 (5) | 57% | 25.5% | **2.3x** | 1.1x | 12 of 13 |
| CONTACT+ | 9 (4) | 28% | 8.7% | **3.2x** | 1.5x | 7 of 9 |
| PLACE+ | 7 (2) | 27% | 12.5% | **2.1x** | 1.5x | 5 of 7 |
| COUNT+ | 3 (3) | 9% | 0% | (n small) | 3.1x | 2 of 3 |

**The form carries only with its +C.** The bare slot barely separates winning routes from random presses. The slot bound to last level's colours does, by 2–3×. This matches the integration picture: the integral (the rule) is general, and the constant (the bindings) is what lets you differentiate back down onto the next level.

## Test 4: matching pairs on a start screen, as the probe for a game with no notes

**Method:**
- *Twins* are things that occur 2 to 8 times on the level's first screen. Things are same-colour regions, plus composites of small touching regions.
- A press touches a twin if it changes a pixel on or next to one.

| Twins | Levels with any | Route presses touching | Arbitrary presses touching | Lift (each game equal) | Winning press touches one |
|---|---|---|---|---|---|
| exact copies | 29 of 36 | 61% | 45% | 0.9x | 12 of 29 |
| up to flips | 30 of 36 | 61% | 50% | 0.8x | 14 of 30 |
| up to flips and recolouring | 34 of 36 | 48% | 52% | 0.8x | 11 of 34 |
| odd one out (same shape, different colour) | 20 of 36 | 40% | 47% | 1.0x | 3 of 20 |

**This is a negative result.** Things that already match on the first screen do not tell you where to press. In the hybrid's wins, the target is shown but *not yet equal*: the work is to make it equal. So matching belongs in the core as the goal test ("did this press make X equal to the shown Y?"), not as a starting probe. The forward goal search between levels of one game still holds: the last win's before-picture found the next win's place 5.8× better than blind, in `trail/goalsearch.md`.

## What went into Mika's layer (v6, `hybrid/mika_layer_core.py`)

**Made equal (the central slot):**
- A note fires when a press makes a pattern equal to one inside a still thing on the screen. The match must be *the same way up*, but may be *any size*.
- Two things it needed:
  - The keys in ls20 are drawn twice as large as the glyph in the box.
  - Orientation matters: up to flips, the key already "matched" before the plus rotated it.
- On the ls20 route it fires exactly at the plus: *"After UP, the b (blue) pattern inside the thing at rows 53-60, cols 2-10 has the same shape as the b (blue) pattern inside the still thing at rows 9-15, cols 33-39 (same way up, drawn 2x vs 1x)."*
- It is rare: 1.2% of route presses and 0.9% of random board-changing presses across the 39 casebook levels. So it costs few tokens.

**The last win's form, with its +C:**
- The level digest now says what the winning press did in slot words. For example: *"the moved thing arrived next to a still B (black) thing (rows 40-43, cols 28-43); a small thing far away changed (rows 28-35, cols 2-3, now G (dark gray))"*.
- The colours it was bound to are kept, along with the colour clicked.
- At the next level's start: *"Colours of the last win's form on this screen: N (light green) at rows 41-41 cols 14-15, rows 53-53 cols 8-10."* This is said only when the colour has 6 places or fewer.
- During the level, it says when a press brings the moved thing next to a still thing of a bound colour. Walls and floors are excluded (colours over 200 pixels), and it is said at most 3 times per level.

**Footprints:**
- The per-key digest now says how many separate places one press changed, e.g. *"MOUSE on R (red) recoloured 20/20 (9+ places per press 19x)"*.
- This is the action-model gap from Test 1: one click flipping several cells.

**Push and checks:**
- Pushed as `jonpelchat/mika-duck-hybrid` version 5, Save & Run on ls20, vc33 and ft09.
- The installer was checked on a fresh copy of the patched harness.
- The hook test passed on 8 games.
- The layer takes about 10–20 ms per press.

## Smoke run of v6 (Kaggle version 5, Oct 23 14:47–15:17 UTC)

Same setting as the earlier runs: ls20, vc33 and ft09, 30 minutes per game, one pass.

| Version | ft09 | ls20 | vc33 | Mean | Tokens generated |
|---|---|---|---|---|---|
| v3, layer | 6/6 in 95 actions | 4/7 in 180 | 6/7 in 200 | 70.2 | 353k |
| v4, base (no layer) | 6/6 in 90 | 2/7 in 136 | 3/7 in 71 | 44.1 | 229k |
| **v6, layer + core card** | 6/6 in 86 | 3/7 in 254 | 3/7 in 95 | **46.4** | **352k** |

**What the score says:**
- v6 generated as many tokens as v3 but scored like the base.
- The 70.2 against 44.1 gap that tokens might have explained earlier is therefore mostly run-to-run variance.
- One smoke run per version cannot rank layers. vc33 alone swung from 6/7 to 3/7. In v6 it spent 148k tokens on 95 actions, including long algebra about which blocks can line up, and ran out of time on level 4 (the doors).

**The new notes were used both times they mattered:**
- **vc33 level 3.** The model was choosing which of three objects to line up. It quoted *"Colours of the last win's form on this screen: N (light green) at rows 41-41 cols 14-15, rows 53-53 cols 8-10"* and reasoned *"the harness highlights colors from the last win's form … the next relevant object might be the green one"*. It called it "a weak hint" and tried the green object first, and the level was won on the green object's button.
- **ls20 level 2.** The glyph note fired when the key turned to match the box: *"Excellent! The legend is now pose A, matching the box glyph (the frame facts confirm: 'the b pattern inside the thing at rows 53-60 cols 2-10 has the same shape as the b pattern inside the still thing at rows 39-45 cols 13-19 (same way up)')"*. The level was won 5 presses later.

**Note counts:** the log has 33 turns with notes. The core-card lines among them:
- the glyph match, 1;
- the whole thing equal to a still thing, 1;
- the last win's colours on the new screen, 4;
- arrivals next to a bound colour, 3 (all in vc33, all next to a black bar);
- the rest were digests, boards already seen and step-bar notes.

**Decision:** tonight's submission stays v3. The hidden set (110 games) is the better meter, and v3's score will be the first layer number there.

## Many cores: levels as a chain, games as branches (Jonathan, Oct 23 morning)

> "we can have more than one core right? ... couldnt we chain these together and have multiple things hanging off the same set of lines?"

> "would stacking these above or below or beside be different iterations or have different options? ... since our matrix is limited, some games or levels would need all the space for one job, and then it would need another one for a different job, and then those become one body ... the answer was a point far out in our space before ... different levels would be going further out in similar directions and different games would be different branches?"

**The picture we settled on:**
- **The lines** are the 12 slot rules, with no game's specifics in them.
- **A core** is one level's filled card hanging on those lines: examples on both sides, plus its +C.
- **Out along a branch:** the levels of one game.
- **Branches:** different games.
- **Above and below:** iterations (lives and retries at one spot).
- **Beside:** options (rival readings at one point).
- **Forward and back:** the tunnel's two directions (review and forge).
- **The far point:** the shown target, which was on the screen in all 16 hybrid wins. Building backward from it was cheap. Building forward from the controls (what each press does) was the model's real work.

**Checks:**
- **Levels go further out in similar directions.**
  - In the 16 hybrid wins, each level kept the previous level's slots and added one or two:
    - ft09 added gather at level 2, differ at level 3 and undo at level 5.
    - ls20 added the fuel budget at level 2.
    - vc33 added blocked and press-order at level 2, then contact (the doors) at level 4.
  - From frames, over 14 consecutive level pairs: 59 slots kept, 20 new and 14 dropped. So 81% of the previous level's slots carry over, with about 1.4 new per level. Most drops are the noisy counter detectors.
- **Branches share lines only where they share slots.** This was leave-one-game-out over 18 games:
  - The line chosen from the other 17 games was "arrived next to a still thing" every time.
  - In the 11 held-out games where that slot occurs at all, winning routes had it more often than random presses in 8 (median 1.9×).
  - In the other 7 games (click games with no moved thing) the line says nothing.
- **Two jobs in one level (a body of two cores).** I tried this from frames: group a level's goal events by the places they touch, leaving out the moved thing, which is the seam. It found "two jobs" on almost every level, but what it actually separates is a press from its own indicator, not two jobs. So it is logged only and not said to the model. The semantic cases (ls20 L2: match the key + manage the fuel; vc33 L4: line up the levels + use the doors) need something better than shared places.

## v8 (Kaggle version 6, pushed Oct 23 10:50 MDT): the card as a chain of cores

**The card is a real object** (`_Card`).
- For each of the 12 slots it keeps how often it fired, its first example, and the colours it was bound to.
- It also keeps the places involved and the slots of the winning press.
- The sensors are the existing detectors:

| Slot | Sensor |
|---|---|
| CONTROL+ | a thing moved |
| CONTROL− | the press changed nothing |
| CONTACT+ | the clicked thing changed, or something changed without a move |
| CONTACT− | the life ended |
| MATCH+ / ORDER+ | a pattern or thing was made equal to a still one, same way up, any size |
| PLACE+ | arrived next to a still thing |
| COUNT+ | a small change far away, or colour passing between two things |
| COUNT− | the step bar went down |
| ORDER− | a board seen before, or a click cycle |

**The chain:**
- Each won level's card is kept. The next level starts with one line about it, e.g. *"Card from levels 1-3: wins came with bringing the moved thing next to a still thing (2 of 3); every level so far also had a step bar running down; new on the last level: making a pattern equal to a still one."*
- Slots that fire on most presses of this game say nothing and are left out: every click changes something, every key moves something. The cut-off is a share of 35%.
- MATCH+ and ORDER+ are said once, as one slot.

**The port:**

| Spray | What it is |
|---|---|
| narrow | the bound places and the made-equal notes, said where they happen (from v6) |
| wide | the stall note (below) |
| guard | the boundary sprays: boards already seen, loops, lives ended (from earlier versions) |
| silent | anything already said this level |

**The stall note:**
- It fires once per level, when the level has taken at least 40 presses and 1.5× the last level's.
- It names the kinds of event from earlier wins that haven't happened yet on this level.
- On level 1 there are no earlier wins, so it falls back to the shared lines.

**Shared lines:**
- The competition rerun plays all 110 games as threads of one process, so a module-level store, protected by a lock, collects across games:
  - each game's winning-press slots;
  - its ordinary-press slots, which give the baseline.
- When a game stalls with no card of its own, it hears the line with the best lift from the *other* games. For example: *"In the other games being played right now, k of n winning presses involved bringing the moved thing next to a still thing (ordinary presses: 7%)."*
- The line needs at least 8 wins from at least 3 other games and a lift of at least 1.5.
- Trivial lines are left out: moving, "changed what it touched", and the boundaries.
- Tested with 6 games in threads; the store filled from all of them.

**Notes are no longer lost:**
- Before v8, notes beyond the 3-per-turn cap were dropped at level starts.
- Now they wait for the next turn (up to 6).

## Smoke run of v8 (Kaggle version 6, Oct 23 17:02–17:32 UTC)

| Version | ft09 | ls20 | vc33 | Mean | Tokens generated |
|---|---|---|---|---|---|
| v3, layer | 6/6 | 4/7 | 6/7 | 70.2 | 353k |
| v4, base (no layer) | 6/6 | 2/7 | 3/7 | 44.1 | 229k |
| v6, layer + core card | 6/6 | 3/7 | 3/7 | 46.4 | 352k |
| **v8, card as a chain of cores** | 6/6 in 95 actions | 4/7 in 256 | 4/7 in 162 | **56.2** | **406k** |

**What it shows:**
- Still one run per version, and v8 had the most thinking (406k tokens; the server ran faster this time, 225 tokens/s against 193).
- The four runs span 44–70 with no version clearly ahead, so the ranking has to come from the hidden set.
- vc33 got past level 4 (the doors), where v6 ran out of time.

**The new lines, 71 notes in all:**
- 13 card lines;
- 3 click-cycle notes, one of them ft09's 3-colour cycle: *"Clicking the thing at rows 22-27, cols 28-33 cycles its colour: b -> R -> O -> b (3 clicks back to the start)"*;
- 3 equal-pattern notes;
- no stall notes, since no level ran 1.5× longer than the one before past 40 presses;
- no shared-lines notes, which with only 3 games could never reach "8 wins from 3 other games".

**The model used a card line as its working hypothesis.** On vc33 level 5, stuck: *"Let me reconsider the frame facts hint: 'Card from levels 1-4: wins came with bringing the moved thing next to a still thing (4 of 4)'. So the goal = bring the moved thing next to a still thing. Here the 'moved thing' = a plug ..., the 'still thing' = the socket marker in the wall."* Time ran out before level 5 was won. The ls20 glyph note fired again at the key match, on two levels.

## v7 (not pushed on its own; included in v8): two more action-model notes

These target the gap from Test 1.

**Click cycles:**
- Example: *"Clicking the thing at rows 44-49, cols 52-57 cycles its colour: b -> R -> b (2 clicks back to the start)."*
- Said once per cycle per level.

**Transfers between things:**
- Example: *"Conserved so far: in 4 presses Y (yellow) pixels moved between places but their total stayed 24."*
- It counts only when the gained pixels join one thing and the lost pixels leave another one standing. One thing moving is not a transfer. A first version fired 87 times in random play, mostly on moving sprites and rotating rings; the stricter version fires 3 times.
- **Limit:** it does not catch vc33's mechanic. There, two colours trade, and colour 0 + colour 3 stays constant at 2,499 pixels while each changes. Any recolouring conserves a pair sum, so a pair rule would be trivial.

**Rates in random play:** 150 random presses on each of the 39 casebook levels, with clicks repeated half the time. The new notes fired: made-equal 10, cycles 6, transfers 3. About 1,100 other notes fired in the same runs.

**Already in the harness:** its segmentation gives same-colour objects with rotation-free and rotation-sensitive hashes. Mika's equal-pattern note adds two things it lacks: patterns at different sizes, and patterns inside multi-colour things.

## Files

- `/home/claude/arc3/coreslots.py`: slot detectors, the survey and the matching-pair survey. Output in `trail/coreslots.md` and `.json`.
- `/home/claude/arc3/bindings.py`: the +C test. Output in `trail/bindings.md`.
- `/home/claude/arc3/hybrid/mika_layer_core.py`: layer v8. Earlier versions are kept as `mika_layer_core_v5.py`, `_v6.py`, `_v7.py` (`_v8.py` is a copy of the current one).
- PC copies:
  - `D:\planet\kaggle_push\mika-duck-v6\` and `mika-duck-v8\` (the notebooks);
  - `D:\planet\arc3\hybrid\mika_layer_core_v6.py` and `_v8.py`.
