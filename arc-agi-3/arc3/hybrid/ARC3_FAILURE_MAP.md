# ARC-AGI-3: how the hybrid fails, game by game, and the objective types (Oct 29, 2026)

Jonathan, Oct 29:
> "how has she been failing? i can try coming up with notes if i know what she is struggling with. maybe we could come up with types of objectives to look for? theres matching, symmetry, movement, filling, and some other categories to think about. its like we need a game or objective for each inner core node. then she could see the arc games as combinations of those other games. kind of like what people do with games"

**Source:** the Oct 24 Save & Run on all 25 public games (`D:\planet\kaggle_push\out_emu2`, hybrid with the v8 layer, mean 13.30).
- One pass, about 70k generated tokens per game, and one shared clock of 1 hour for all 25 games. So time pressure is higher than in the hidden rerun, which allows about 180k tokens per game. The patterns of waste still apply there.
- Five reader agents went through all 25 transcripts. Their reports are summarised here.

## Per game

| Game | Levels | Main failure | Objective types | The miss |
|---|---|---|---|---|
| bp35 | 0/9 | barely played (15 presses) | navigation (reach the "+"), removing blocks, buoyancy | tokens spent deciding whether the screen scrolled |
| dc22 | 0/6 | wrong objective | connecting or matching (unclear) | searched all 36 states of its model, found no win, decided "the game has no win" |
| g50t | 0/7 | barely played (3 presses) | navigation to the matching target (guess) | SPACE never tried |
| sc25 | 0/6 | wrong objective, controls unsettled | matching a keypad pattern to drive a plug (guess) | a purple flash (the game checking an input) not used |
| sk48 | 0/8 | wrong objective | matching a shown layout, sorting, pushing into place | rejected the bottom-bar target on an untested belief ("blocks never change rows") |
| tn36 | 0/7 | wrong objective | toggling switches to copy something on screen | blind pattern guessing; no reference found |
| tr87 | 0/6 | barely played (3.5 min) | matching (dictionary translation), cycling glyphs | right idea, no slot ever set |
| ls20 | 1/7 | time + over-planning | navigation, collecting, rotating, matching | planned 43 presses around new rings it never touched |
| ka59 | 1/7 | execution (budget) | pushing into place, shape matching, navigation, click-to-select | 62-press plan for a 64-press bar |
| lf52 | 1/10 | wrong objective in L2 | removing pegs down to a count; L2 adds a track (movement) | arrows untested in L2 because they did nothing in L1 |
| s5i5 | 1/8 | time | extending to reach a place, pushing | multi-step push planning without presses |
| su15 | 1/9 | time (5 min of play) | navigation; L2 merging up a ladder (guess) | refused far clicks cost about 10 presses |
| wa30 | 1/9 | execution | carrying into place, filling slots | waited on a self-moving helper that had stopped; misread the board |
| cn04 | 1/6 | wrong objective in L2 | connecting (tip to pin), rotating, movement | MOUSE never tried in the whole game |
| r11l | 1/6 | execution | moving a derived point (midpoint, centroid) onto a target | refused clicks (object must fit), "no 2-move solutions" |
| sp80 | 1/6 | missed a control | filling (pouring into pockets), positioning | MOUSE written off after one no-op; clicking a bar swaps it |
| ft09 | 2/6 | bookkeeping | matching a key by toggling colours | click list had 11 of the 14 cells its own table listed |
| m0r0 | 2/6 | missed a control | movement with mirrored controls (symmetry), bringing together | MOUSE never probed for 2.5 levels |
| tu93 | 3/9 | execution | navigation with timed hazards | its clock was not reset after a death |
| re86 | 3/8 | wrong objective in L4 | covering by colour, positioning, recolouring | new swatches not touched for about 115 presses |
| vc33 | 3/7 | new element not probed | matching (blade to marker), levers, water levels | "proved" L4 impossible; clicked the new window segment last |
| cd82 | 3/6 | time | filling/painting to copy a preview | 31k tokens of geometry on L1 |
| lp85 | 5/8 | time | sorting by cyclic shifts, matching into brackets | fast and correct; the clock ran out |
| ar25 | 6/8 | time | symmetry (reflection) to cover a template | found "a click moves control to another piece" only after 23 presses |
| sb26 | 8/8 | solved | matching a sequence, nesting | target on screen, UNDO, a failed submit flashes exactly what is wrong |

## Four patterns

1. **Thinking instead of pressing.** Long turns with no press (sp80 9 turns, r11l 14, cn04 8). Every unsolved game ended mid-level on the clock, three of them just as the key mechanic was found.
2. **A new element or an unused control is not touched.** This is the most repeatable cause:
   - controls never tried: MOUSE in cn04, m0r0 and sp80; SPACE in g50t; arrows in lf52 L2;
   - new things on a level not touched: vc33 windows, re86 swatches, ls20 rings, m0r0 dots.
   - The fix was always one press.
3. **"Impossible" means a rule is missing.**
   - dc22, vc33 and sp80 each proved their own model had no win.
   - sk48 rejected the right target because of an untested belief.
4. **Execution and bookkeeping:**
   - ft09's click list;
   - tu93's clock after a death (her track clock already knows the tick restarts);
   - m0r0's mirrored-move bug;
   - ka59's budget.

## The objective types (Jonathan's list, filled in from the 25 games)

| Objective | Games | Core-card slots (ARC3_CORE_CARD.md) |
|---|---|---|
| **Matching**: make a thing equal a shown target | ls20, ft09, tr87, sk48, sb26, cd82, re86, vc33, r11l, ka59, lp85 | MATCH+, ORDER+ (target shown) |
| **Symmetry**: a mirror image or mirrored controls | ar25, m0r0 | MATCH+ under a reflection |
| **Movement / navigation**: reach a place | tu93, bp35, g50t, su15, s5i5, ls20 (the exit) | CONTROL+, PLACE+ |
| **Filling**: fill containers, slots or a canvas | sp80, cd82, wa30 | PLACE+, COUNT+ |
| **Pushing / carrying into place** | ka59, wa30, s5i5, sk48 | CONTROL+, PLACE+, CONTACT+ |
| **Sorting / ordering** | lp85, sk48, sb26 | ORDER+ |
| **Toggling / switches** | tn36, ft09 | CONTACT+ (a click changes the thing) |
| **Connecting**: join two ends | cn04, dc22 (?), m0r0 | PLACE+ between two things |
| **Removing / counting down** | lf52 (pegs to one), bp35 (crates) | CONTACT−, COUNT− |
| **Covering**: lay a shape over marks | re86, ar25 | PLACE+, MATCH+ |
| **Rotating / transforming** | ls20, cn04, tr87 | MATCH+ (a transform law) |
| **Timing / avoiding** | tu93 (patroller), ls20 L6 (tracks) | CONTROL+, CONTACT− |
| **Indirect levers**: a press moves something else | vc33 (water), sp80 (pour), ar25 (control passes) | CONTROL+ on a far thing |
| **Merging / combining** | su15 L2 (guess) | CONTACT+, COUNT |

**Matching is in 11 of the 25 games, and it is the only type in every game the hybrid solved well.** Every game is a combination, as Jonathan said. Examples:
- ls20 = navigation + rotating + matching + a step budget;
- ka59 = pushing + shape matching + navigation;
- re86 = covering + colour matching + recolouring;
- sp80 = filling + positioning + an indirect lever.

**Each level usually adds one node to the game's combination:**
- re86 adds recolouring in L4;
- lf52 adds a track in L2;
- vc33 adds windows in L4;
- tu93 adds a patroller in L4.

That is the "new element" failure seen from the other side.

## Notes these failures suggest (for Jonathan to write)

The frames can check each of these exactly:

1. **Every action once.** A valid action has never been pressed after some presses in this game (cn04, m0r0, sp80, g50t, lf52).
2. **A new kind of thing.** A look that was not on any earlier level is on this one (vc33, re86, ls20, m0r0). Touch it once before planning around it.
3. **The target is shown.** A still picture whose colours and shapes match the movable things is probably the goal (sk48, tn36, cd82, sb26). This is the ORDER+ node; it was on screen in every hybrid win.
4. **The flash is the game checking.** The game took control for several frames after a press (sc25, sb26). Look at what flashed.
5. **Impossible means a rule is missing.** Needs the reflective layer (reading the model's text); until then, the "board seen N times" loop note is the nearest sign from the frames.
6. **The objective type from the first screen.** Read the kit on the first screen and name the likely objective nodes:
   - a shown target → matching;
   - a mirror line → symmetry;
   - one mover and a marked place → navigation;
   - empty slots or containers → filling;
   - a row of switches → toggling to copy something.
