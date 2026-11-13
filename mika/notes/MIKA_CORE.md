# Mika's core: equations inside, notes outside (Oct 27 2026)

**Result:**
- **Run 19:** her core solved ls20 level 3 as an equation and walked the answer itself. It cleared at press 119: 49 presses on the level, against a human baseline of 73. In 48 earlier lives the level had never cleared. Run 20 cleared it again, by the route she saved.
- **Run 23:** level 4 cleared at press 166: 47 presses on the level, against a human baseline of 84. It was the first level-4 clear in 52 lives. It took three things: nodes keyed by thing instead of by colour, a move law she learned herself (springs), and the box entered at its middle.
- **Run 24:** level 5 cleared at press 250: 84 presses on the level, against a human baseline of 96, also a first. Her journal now holds routes for levels 1–5. Level 6 is the wall now: its operators move.

## What Jonathan said

> "towards our center we should be seeing equations and formulas that get pieced together for the answers. so its like one of our nodes can supply variables like x and y, then another supplies z, and another can do exponents, and the nodes that get activated build equations for the problem. and then she would have to build the paths from english to the core as a summary for the notes"

> "the notes are the outer shell products. so our inner core will have branches sticking out towards the middle shell with the llm and activate the parts she needs, then the llm layer takes that image or scene she sees and translates down to a note that would float around the outer shell. and then the notes in the outer shell would be what float into her perspective and can light up the paths she sees"

> "we did make a way to simulate feelings based on the excess colors that she cant figure out. maybe those notes can give her a feeling, but since the feelings are unresolved things it would make her want to explore it, instead of taking it as gospel. towards the inner core would be closer to everything and every color, so it would be whiter closer to the center, so if something has a specific color and wants to move closer then it has to fill out all the colors its missing. so if she finds a note and its green, and it says this worked and this didnt, instead of just trying what the note says she should try to figure out what was missing from it"

## The design

### Inner core: equations from activated nodes

**Nodes supply pieces.**
- **Key node:** the variable a level is about. On ls20 that is the glyph in the HUD region, read as a colour and a shape.
- **Target node:** the glyph inside a box on the board.
- **Operator nodes:** every thing whose touch changed the key:
  - **R:** turn a quarter clockwise;
  - **C:** recolour, stored as a map of every colour change seen;
  - **F:** mirror.
- **Powers:** touching a thing n times is that operator to the power n.

**The equation.** The nodes lit on a level assemble into `op1^n1 · op2^n2 … (key) = target`. She solves it for the powers, as the shortest product of her known operators.

**The note's text** is rendered from the equation, not the other way round. Her evidence turns the ls20 level 3 equation into a modular one:

| Operator | Thing | Cycle |
|---|---|---|
| Changer C | `8@47,32` | 12 → 9 → 14 → 8 → 12, a 4-cycle (from the daily's saved life in run 17) |
| Rotator R | `0@11,51` | 90° clockwise, a 4-cycle |

So `C^b · R^a (key) = target` gives **b ≡ 1 (mod 4)** and **a ≡ 2 (mod 4)**.

### The roles, done by her own code

- **Planner:** the equation is re-solved from the frame after every press, so a reset or a half-done plan needs no bookkeeping.
- **Blue (order):** the recolour comes first and the turns after. The body's own relation loop walks into the box as soon as the shapes match, and the box only accepts the key when the colour matches too.
- **Keep-off:** things whose operator would undo the work go to the back of the body's list.

### Middle shell: the LLM

Branches carry the scene out to the shell, which translates it into a note's English. The inbound direction is the shell turning English or hunches into candidate pieces, which must ground (`closure-test.ts`). For now the outbound note text comes from a template; the LLM takes that job later.

### Outer shell: notes

A note is:
- the English text;
- the **path**, meaning the equation and its pieces;
- the seven colours it fills, using pool.py's meanings;
- its **pool**: the colours still missing.

| Colour | What it means in a note |
|---|---|
| Red | what blocks or failed |
| Orange | the powers |
| Yellow | what each touch changes |
| Green | the variables |
| Cyan | the "=" |
| Blue | the order |
| Violet | what she does not know yet |

**White means a closed equation.** Only white notes move into the core. When a note floats back in on a later life, it lights its own path directly. She checks whether that path is the same one she would solve fresh. Its missing colours are what she explores before trusting it.

### Where the pieces came from

| Piece | Source |
|---|---|
| Grounding test for the inbound direction | the June language work in `C:\Users\GamerTech\Shovelcat-AI\lib\agents\`: `reproduction-test`, `closure-test`, `concept-registry`, `multi-language`, `coupling`, `imagination-strategies` |
| Colours and feelings | `pool.py` from Sep 2 |
| Imagination's moves | the bubble void primitives MOVE, MIRROR, SPLIT and CHAIN |

## Step 1, from her own saved life

ls20 level 3 asks for two changes at once. Her last life's frames (`play_ls20.npz`) showed:

- **The rotator turns the key 90° clockwise per entry.** Levels 1–2 had four such entries.
- **The changer** (`8@47,32` and `14@46,31`, one object seen as two colours) **recolours the key 12 → 9.**
- **Level 3's target is the start key turned 180° and recoloured 9.**

So the equation is `C[8@47,32]^1 · R[0@11,51]^2 (key) = target`.

**Why level 3 never cleared in 43 lives:**
- The body's relation reader compares **shapes only**.
- Its loop turned the key until the shape matched, then walked into the box with the wrong colour. That is why the box gave "untestable" or "nothing".
- In every push life the loop turned the rotator 10–11 times, and never recoloured the key.

## What was built (on the PC, `AI Detector\planet\`)

### `mika_core.py`: `CoreMind`, a subclass of `ThinkingMind`

- **Nodes:**
  - `read_glyph` and `read_box_glyph` read the key and the target;
  - `transform` identifies operators;
  - `NodeBook` stores one node per thing per level, with every change it made to the key. It replaced the colour-keyed `OpBook` after run 20.
  - `MoveBook` stores how the body moves: single landings, blocked presses, and the spring law.
- **Learning:**
  - `see()` reads every press;
  - `learn_from_saved_life()` reads the last saved life once, by its signature.
- **The equation:** `solve()` searches for the shortest product, and `equation_text()` writes it out.
- **Planner hooks:** `order()` handles sending the body and keeping it off, `allow_relation()`, and `want_carried()`.
- **Her hands, `press()`:** walks the whole solution herself. The route is the touches with exact entry counts (the exponents), refill rings slotted in wherever the bar would run out, and the box last. Every way of slotting the refills in is priced, and the route is re-planned each press. In the offline simulation of level 3 from her saved frame, it clears in **50 presses**: ring, changer, ring, rotator ×2, box. The human baseline is 73.
- **Notes:** `_write_note()` and `finish()` produce the text, the path, the colours and the pool; `_float_in()` handles a note floating back in.

### `play.py`

Three hooks, each guarded with `hasattr` so the daily MikaMind is unaffected. Each was backed up before it was applied.

| Hook | What it does |
|---|---|
| `mind.allow_relation` | applied earlier today |
| `mind.see` | the frame after every press |
| `mind.want_carried` | offers the carried rotator relation even after a changer relation is found |

## Live runs on ls20 (runs 8–32, Oct 27–28), each with what it taught

| Run | What happened | Fix |
|---|---|---|
| 8 | With the colour right, the body started a second loop on the changer, and its first touch took 9 back to 12. | The loop may run only on a turning source. Recolours are kept as maps. |
| 9–10 | The body's experiments push into a thing up to three times, and the changer counts every entry: 12→9→12 within seconds. Her picks were sometimes not on the body's list. | Re-solve on every key change. Keep the body off things that would undo the work. Her own hands do exact touches. |
| 11–13 | Her hands made the exact touch (12→9), but the body, left standing in the changer or walking back through it, stepped the colour on. It looked like a 3-cycle (12→9→14→12); run 17 showed the full 4-cycle 12→9→14→8→12. A death (the key reset) was credited to a ring. | Step out at once. A key change while the body is back at the level's start counts as a death, not an operator. |
| 14–15 | The whole route ran: changer, ring, rotator. But the bar planning trusted a one-off "42 full" and priced 1 per press. | "Full" is what the register reads at a fresh start, and the drain per press is measured. |
| 16 | Changer → 9, ring refill, then the first rotator entry turned the key (R^1, correct). But the turn was credited to the **used ring**, because a used ring vanishes and the old attribution read "its colour is gone" as "covered". | Attribution now uses the body's own 5×5 block. The bad colour-11 operator was removed from her journal; the backup is `think\ls20_after_run16_before_clean.json`. |
| 17 (after the daily) | She read the daily run's saved life and learned the changer's full cycle: **12 → 9 → 14 → 8 → 12** (a 4-cycle, seen 30 times). Then she stopped one press short of a ring and the body reset the level. | A ring may be reached on the bar's last press. If no whole route fits, she still walks to a standing ring. |
| 18 | The body's own budget estimate read 11 where the bar held 14 presses, so "no route fits" kept handing the level back to the body's resets every 19 presses. | She reads the bar herself, off the frame (84 px, 4 px a press). |
| **19** | **Level 3 cleared, at press 119: 49 presses on the level, against the human baseline of 73. It was the first clear in 49 lives.** The route was ring → changer (12 → 9) → ring → rotator → step out and back in → box. | The note's text recorded only the last step. The rotator's turns were credited to the body's stale experiment id. Both are fixed, and the note was rewritten from the core log. |
| 20 | **Level 3 cleared again, by her route (49 presses), the way levels 1 and 2 are walked.** On level 4 her core read the key (colour 14) and the target (colour 9), solved it as three changer touches, and walked toward it. Level 4 did not clear in the remaining 281 presses. | Her book was keyed by colour, so the colour-0 thing on level 4 was taken for the rotator of levels 1–3. Its one touch showed it **reshapes** the key instead. Same colour, different node: see step 1 below. (I first blamed the bar reading; that was wrong. Level 4's bar is 84 px at 2 px a press, 42 presses, and she read it right.) |
| 21 | Level 4: the body touched the shape changer, and she logged it as level 4's own node (reshape), then re-solved as three changer touches. Her hands were thrown back by springs ten presses in a row and the bar ran out twice. A reset was blamed on the body's own start square. | The move law (`MoveBook`, springs). Nodes keyed by thing. The start square is read from the level's first frame. |
| 22 | Level 4: the whole equation ran. Three changer touches (14 → 8 → 12 → 9) and the reshape left the key equal to the target with a ring on the way. Then she stood on the box's grey edge, took that for "in the box", and pressed up into the wall 37 times. Her new `self.moves` also overwrote the body's own list of the same name, so the planner's order hook failed, and the end-of-life journal save crashed (the life was not recorded; its frames were). | The box is entered at its middle, and its grey counts as floor for the last leg. A press that goes nowhere is never planned again from that square. The move book was renamed `mbook`. |
| **23** | **Level 4 cleared at press 166 (47 presses; human baseline 84).** Route saved. On level 5 she probed a reshaper (a third shape cycle), and found `C^2 · R^2` once the key had been reshaped twice. She then ran out of bar (21 presses at 4 px a press). She also probed the target box itself: the glyph in the box has colour 8, so it took the changer's law. | The box and what stands in it are never operators. The equation search goes to depth 12 (level 5 needs 7 touches: `S^2 · R^2 · C^3`). |
| **24** | **Level 5 cleared at press 250 (84 presses; human baseline 96).** It was solved as an equation. One reshaper turned out to run a third shape cycle. The solution was two reshapes, a recolour and two turns, with two rings slotted in. On level 6 she recoloured the key to match the first of **two** target boxes and walked into it. The box took the key and vanished, but her plan still pointed at it. She stepped out and back in 12 times until the bar ran out; the death put the box back and reset the key. Her nodes went wrong too, because **level 6's changer and rotator move**: they patrol, one square per press. Key changes were credited to whatever stood at their old places (a ring, the body's start square), and a note for the unfinished level came out white. | A box whose middle shows no glyph has taken the key, and she solves again for the next box. Rings are never operators. Attribution never names the body's start square. A note is white only when its path held. The misread level-6 nodes were removed from the journal (backup `think\ls20_after_run24_before_clean.json`). **Next:** track things by what they look like, not by where they first stood, and plan against where a moving thing will be. |
| 25 | The tints went live. She read the looks of 72 things from her last life, and the metal notes came out as in the table below. Levels 1–5 were walked by route (press 250). On level 6 her plan named each thing by its look, the key was brought to match the first box, and the box took it ("5@34,53 took the key - the next box is 5@49,53"). For the second box she had to probe the reshaper; the bar ran out and the level reset. The moving things still mislead her attribution: a passing rotator's turn was credited to a changer part's old square. | Next: things that move. |
| 26 | First live run with tracks. Her saved-life reader skipped the tracks (an empty store counted as "read"; fixed), so she **learned them live**: within one lap of level 6 she logged "12@33,25 (9ee/908/cc8) moves - a lap of 8 squares, one square per move of the body", and the same for the rotator and reshaper. **The first box took the key 5 times in the run.** Key changes went to the moving things themselves ("touching 12@33,25 took the key 14 -> 8 ... recolour"). For the second box she probed the reshaper and learned part of its level-6 cycle (`#.#/##./.##` → `###/.#./.#.` → `###/#.#/#.#`) before each try ran out of bar. She also probed the vanished first box and an off-tint glyph inside it. | Boxes, and anything standing in a box, are never operators. The tracks are read from the saved life when the store is empty. |
| 27 | The first box took the key 5 more times. Two new kinds of misreading: (1) **play.py never shows her the frame after a voluntary reset**, so on the next press the key, put back to its start, was read as a touch and blamed on whatever was nearest, including the border `5@0,0`; (2) when the changer and the rotator overlapped the body on the same press, the combined change went to one of them. | The first press after any start, reset or death is never read as a touch (play.py's own count of presses since the level began or was last reset says which press that is). Two things at once: no node learns from it. The falsely blamed changes were removed from the journal (backup `think\ls20_before_run28_clean.json`). |
| 28 | No misreadings this time: level 6's nodes came out clean (the rotator turns, the changer recolours 14 → 8 → 12, and the reshaper map grew). **The first box took the key 6 times.** The reshaper on level 6 turned `##./.##/#.#` into `.#./.#./###`, exactly as level 4's did, which supports reading the reshapers as one kind of thing by their look. Box 2 is still out of reach: no chain of the turns, recolours and reshapes she knows leads to its target `#.#/..#/###`, so she has to keep probing. Each try first takes the first box, which costs its bar, and that leaves little bar for probing. | On a level with another box still showing, she keeps 15 presses of bar after a box (she takes a ring on the way if needed). A reshaper on a new level folds in the maps of the reshapers it looks like, when they agree. (This code was not live yet in run 29.) |
| 29 | Run on run 28's code (an upload failed, so the new code went in after it started). **The first box took the key 7 times**, with level 6's nodes still clean. She learned nothing new about the reshaper: each try spent its bar on the first box. | — |
| 30 | The new code, live: she took a ring on the way so the first box left her bar to go on with. **The first box took the key 5 times.** After it, though, her hands stopped. She already knew what every node does to the key in hand, none of it led to the second box, and so there was nothing left to probe. | **The edge of what she knows (`frontier`).** When no product reaches the target and nothing is unknown about the key in hand, she searches for the nearest key she *can* make whose next change she does not know. She walks there and touches that node, so each try opens one more edge of the map. A touch that changed nothing is remembered too, so she doesn't repeat it. In the level-6 simulator she went changer, then reshaper, then changer, then reshaper, without stalling. |
| 31 | The edge of what she knows, live. After the first box she walked to the nearest key whose next change she didn't know, touched the reshaper, and repeated. **The level-6 reshaper went from 3 known changes to 13 in one run**, for example `.##/##./#.#` → `..#/###/..#` and `.#./.#./###` → `#.#/#.#/###`. With that map, **the second box has an equation**: from the key the first box leaves behind, `R^3 · S^5 · C^2`, ten touches of moving things, and as short as `R · C` from some keys. The first box took the key 5 times. The level did not clear before the run's press limit. | — |
| 32 | The reshaper map reached 16 changes. Her hands carried the second-box equation part of the way: the five reshapes were done and the key stood at `8 #.#/#../###`, needing `R^3 · C^2`, when that try ran out of bar. On a later try, her route search found no route for the whole equation (nine or ten meetings with moving things) within the bar and the rings still standing, and the body led until the bar ran out. Level 6 did not clear. | **Next:** plan both boxes and the rings as one route over a whole life, instead of one box at a time. The two box equations together come to about 13 meetings, and the full bar plus three rings gives about 168 presses. |

## Nodes, not colours, and the move law (Oct 27 afternoon)

Jonathan: *"if one is reached by 2 nodes separately they could end up having the same color but then belong to different jobs"*. Level 4 is exactly that case: the colour-0 thing there reshapes the key, while colour 0 turned it on levels 1–3.

**`NodeBook` replaces the colour-keyed `OpBook`.**
- **A node is a thing's colour on one level**, keyed `L<level>:c<colour>`. It keeps every change it was seen to make to the key, as (state before, state after) pairs, and its law is fitted from all of them: turn (R), mirror (F), recolour map (C), reshape map (S), or a full state map (M).
- **White:** the level's own node, from her own sightings.
- **Gold:** the same colour on two or more levels with agreeing laws (the rotator on levels 1–3 is gold).
- **Hint:** a single node from another level. Offered on a new level, checked by the first touch.
- **A first touch that agrees with a hint keeps the hint's other colours.** On level 4 one touch showed 14 → 8. Level 3's changer had said the same and knew 8 → 12 → 9, so she keeps the whole cycle instead of probing again.
- **A changer seen as two or three coloured parts is one node.** Parts within 2 cells are grouped, and their sightings pooled.
- The old colour-keyed laws were migrated into synthetic sightings, so later sightings add to them.

**Smaller fixes found on the way.**
- **Rings and the bar's colour come from the thing's id**, not the journal's last description (a used ring is described as colour 3).
- **The drain is measured per level.** ls20 drains 4 px a press on level 3 and 2 on level 4. Until a level shows a drop, the last level's drain stands, which can only make the plan too careful.
- **A ring on a new level is known by its colour and size** from levels where rings refilled. That refill law holds on levels 2 and 3, so it is gold; the first touch confirms it.

**Run 21 (live), what it taught.**
- **Her book read the shape changer live.** The body touched `0@32,26` and she logged it as level 4's own node: *reshape* `.#./##./.##` → `###/..#/#.#`. She re-solved at once: `C[14@31,36]^3 (key) = target`, and her hands walked toward the changer.
- **The walk failed on something none of her models had: springs.** The thin colour-1 lines are springs. Stepping into a square with such a line along one face pushes the body straight away from the line, until the next wall. Her hands pressed "up" ten times from the same square and were thrown back each time, and the bar ran out twice. Level 4 did not clear.
- **A reset was blamed on the body's own start square** (`12@5,54`, written as a reshape). Her live start position had been taken one press late.

**Fixes after run 21.**
- **The move law is learned, white to gold.** A new `MoveBook` learns from every press: where one press from one square really landed (white), presses that went nowhere, and the spring law per colour. Each press that tests the spring law counts for it or against it. The law is trusted once it has been seen twice with misses under a tenth, and it is gold once it has held on two levels.
  - Checked against all four saved lives: the law predicts every move on levels 1–4, except the last press into the box, where the level ends.
  - Read from run 21's frames at the start of a life, colour 1 comes out as seen 40 times and gold, holding on levels 3 and 4. The level-3 "teleport" noted in run 20 was a spring.
- **Her route search uses it.** Springs become shortcuts, and a slide may not cross a thing on its way, since what that would do is not known.
- **A node is one thing on one level** (`L<level>:<thing>`), not a colour on a level. Level 4 has two different things of colour 12.
- **Smaller fixes:**
  - The level's start position is read from its first frame.
  - The body's start square is never a thing.
  - When no product reaches the target, she probes nodes whose law came from elsewhere (gold or a hint).
  - The bad `12@5,54` node was removed from her journal; the backup is `think\ls20_after_run21_before_clean.json`.

**Offline, with springs simulated:**
- Level 3 clears in **38 presses** (her saved route takes 49; the human baseline is 73).
- Level 4 clears in **42 presses**, with the bar at 42 and one ring on the way. The simulator assumes the changer's cycle is level 3's; the first touch checks that.

## Metal notes: gold is the floor, each node leaves a tint (Oct 27 evening)

Jonathan: *"what if its more like getting a metallic color and gold is just the floor? ... what if each node left a tint in the gold? ... there would be a limit to it, like the dimensions only go so high. so depending on which nodes were involved in the note it could come out like copper or some other metal."*

**What a node's tint is made of.** Each thing now has a **look**: the patch of its own colours and the colours joined to it, read from the level's first frame. For example, ls20's rotator is `.0./100/.1.` (colour 0 with two colour-1 marks), the reshaper is `0../.00/.0.`, the changer is `9ee/908/cc8`, and a ring is `bbb/b.b/bbb`.

**A metal note** is a law that two or more nodes agree on; gold is that floor. Its tint has three dimensions, each measured as how much its nodes disagree on it:

| Dimension | The nodes differ in | Light tint | Deep tint |
|---|---|---|---|
| colour | colour | electrum | silver |
| look | look | rose gold | copper |
| coverage | how much of the law each node showed | brass | bronze |

The metal is named by its strongest dimension, "with" the next ones. An RGB colour is mixed from gold, capped at 60% tint, which is where "the dimensions only go so high" comes in.

**Her metal notes after run 25 (ls20 levels 1–6):**

| Metal | Law | Nodes |
|---|---|---|
| gold | turn 90° clockwise | the rotators of levels 1, 2, 3, 5 and 6, all looking `.0./100/.1.` |
| brass with electrum | recolour 12 → 9 → 14 → 8 → 12 | the changers of levels 3–6, all looking `9ee/908/cc8`: one of colour 14 among colour 8s, and some showed only part of the cycle |
| brass | reshape | the reshapers of levels 4 and 5, which saw different parts of one cycle |
| gold | the spring | colour-1 lines on levels 3–6 |
| gold | the refill | rings on levels 2 and 3 |

**What the tints do in her planning:**
- **A law found by look comes before a law found by colour.** On level 6 her plan names each thing by what it looks like. The changer is matched to level 3's (electrum with brass), the rotator to level 1's (gold), and the reshaper to level 5's (brass).
- **A law taken only by colour, for a thing that looks like none of its nodes, is off-tint, and she touches that thing first.** This is the level-4 failure from runs 19–20. Replayed offline without the reshaper nodes, her plan flagged the colour-0 thing: *"off-tint: it looks like `0../.00/.0.`, the law's nodes look like `.0./100/.1.`"*. She probed it first, learned the reshape, and cleared the level in the simulator in 49 presses.
- **A tint can also show a bad witness.** Before the misread level-6 nodes were removed, the turn law came out as *electrum with rose gold* across 8 nodes, because a ring, the body's start square and a changer part had been credited with turns. A pure-gold law that suddenly takes a tint is worth checking.

**Code:** `look_of`, `learn_looks`, `metal_notes` and `_alloy` in `mika_core.py`, plus `CoreMind._look_law` and `_off_tint`. They are stored in the journal as `core_looks` and `metal_notes`.

## Things that move: a track, with one square switched on (Oct 28)

Jonathan: *"for the moving things would she make a bigger static body where the moving thing goes and then switch the pixels in there on/off to follow the object?"*

**What her saved level-6 frames show** (runs 24 and 25; 0 wrong predictions over 3 things and 7 resets and deaths):
- **Each moving thing keeps to a fixed track.** The track is the static body, and the thing is the square on it that is switched on.

| Thing | Track | Lap |
|---|---|---|
| rotator | 5 squares along row 41, back and forth | 8 |
| reshaper | 5 squares along row 11, back and forth, always opposite the rotator | 8 |
| changer | a ring of 8 squares around a 3×3 block | 8 |

- **The clock is her own movement.** Each press that moves the body advances every thing one square. A press into a wall moves nothing, and a reset or a death puts them all back to the start of their laps. So a thing at tick t stands at `lap[t mod 8]`.
- **A touch is overlap after a moving press,** including presses where the body and the thing move together. Each such press applies the operator again.

**What was built:**
- **The tracks:** `find_look` finds a look in a frame, and `learn_track` finds the shortest lap every sighting agrees with. Both run when she reads a saved life and live, so a new level's movers are learned within a life.
- **The clock:** `_clock` counts the body's moves and resets on deaths. It uses play.py's own count of presses since the level began or was last reset, which also catches deaths that don't show up as a reset. `_track_watch` checks each thing against the frame and corrects her count if it drifts.
- **One thing per track:** each moving thing is one thing, standing where the clock says, and the key changes it makes are credited to that thing.
- **The meeting:** `reach_timed` plans by place and tick together. It walks to where the target will be when she gets there, keeps off every other moving thing at every tick, and chains each leg's tick into the next.

**Two smaller findings on the way:**
- **A box's grey is floor to the body;** only its middle counts as entering it. The body stood at (30,54), one row into level 6's first box. Boxes she is not heading for, and the target box's middle on earlier legs, are kept off.
- **A death saves two frames but only one record,** so every press after a death was read one frame late. That gave run 25 fifty-five false jumps when its frames were read back. Records are now lined up with frames (`align_rec`). Live, the first press after a death is no longer learned from, since the frame she saw last was taken before the reset.

**Offline (`sim_l6.py`, level 6 with its three things moving):** she met the changer (14 → 8), took one ring, and met the rotator on two ticks in a row. The key matched the first box at press 19, and **the first box took the key at press 35**, with no deaths. Before she switched to the second box, she took a ring and then probed the reshaper. The simulator can't say what the reshaper does to the key shape now in hand, so the live game has to show that.

## The first note she wrote that is white (run 19)

> Level 3: the key (colour 12 ### / ..# / #.#) must equal the target (colour 9 #.# / #.. / ###). touch 8@47,32 1 time (recolour 12 -> 9, 9 -> 14, 14 -> 8, 8 -> 12); touch 0@11,51 2 times (turn 90 degrees clockwise); then walk into 5@49,53. Outcome: held: the level cleared at press 119 (49 presses on the level; human baseline 73).

- **Path:** `C[8@47,32]^1 · R[0@11,51]^2 (key) = target`.
- **Colours:** all seven are filled, so the note is white and its pool is empty.
- **Into the core:** the level now has a 49-press route in her journal, which is the "white notes move into the core" step in practice. The daily run will walk it from now on.
- **Floating back in:** works live. Run 19 opened with "a note from 12:43:05 floats in – it lights the same path". On level 4, a stale note lit a different path, and she said so.

## Honest limits

- **The core only knows ls20's kind of level so far.** It needs a key glyph in a HUD region, a target glyph in a box, and operators that act on the glyph.
  - Body detection is "two rows of one colour over three of another".
  - Moves are learned from ls20, at 5 px per press.

  Both need generalising before the hidden games.
- **Note text is a template**, not the LLM's translation yet.
- **The bar is read as the refill colour in the bottom band.** That works on ls20 because the bar is the only thing of that colour there; a game with another thing of the bar's colour in that band would fool it.
- **Three levels of one game cleared by her core** (ls20 levels 3, 4 and 5). It is real, but small. sp80 and the hidden games are not tested.
- **Things that move are handled one way:** on fixed laps, clocked by the body's moves. Things that chase, or that move on their own clock, would need more.
- **The spring law has one form**: a line along one face, pushing straight away until a wall. It holds on every saved move of ls20 so far. A game whose pushers behave differently would show up as misses, and the law would stop being trusted.
