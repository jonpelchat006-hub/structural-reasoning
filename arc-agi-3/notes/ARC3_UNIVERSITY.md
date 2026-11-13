# Mika's university for ARC-AGI-3: solve → learn → teach, graded by students (Oct 22, 2026)

Jonathan, Oct 21:
> "a level above that where she would have to figure out how to teach or explain to someone else how to learn the game ... she wouldnt consider a level solved until she can collapse it to that point with those 3 levels filled to a minimum ... rating different professors teaching the same class ... a board that oversees those profs ... a department for that field ... she would build a university basically and see if a version of her can make it through with just her learning structure."

Oct 22: *"you can build that now."*

## The ladder

| Level | What it means here | Where it lives |
|---|---|---|
| **Solve** | She wins a level | the explorer (`mika3/explorer2.py`) |
| **Learn** | The look-back: the shortest route in her own map, its waste (spent ÷ shortest), and what it was made of | `hindsight()`; `wins_report.py`, `routes_report.py` |
| **Teach** | A lesson plan (a *professor*) goes to a **fresh student** (blank map, other seed) on games the professor never studied. The professor's grade is how the student does | `mika3/university.py` |
| **Board** | Rules for when a professor may replace the plain plan in a department. The board itself is graded by rotating held-out finals | `board.py`, `board_cv.py` |
| **Employers** (the sideways plane) | Graduates judged on work the school never taught. The unit is the *event* (a press described in kinds of things), and the question is which skills carry to new levels and new games | `events.py`, `events_lift.py`, `takeover.py`, `relations.py` |
| **Goal professors** | Lessons about *what getting somewhere looks like*, built from the employers' findings and graded like every other professor | `goal_report.py` → `trail/goal_report.md` |
| **Image plane** | Proofs from pictures: the before/after picture of each press that mattered, compared under limited turns | `moments.py`, `goalsearch.py` → `trail/moments.md`, `trail/goalsearch.md` |

**"Without cheating":**
- A lesson plan may only say *how* to explore. Concretely, it is a setting of the explorer's learning knobs, plus at most an order of presses fitted on *other* games.
- It never contains coordinates, colours or routes.

**Departments** are decided from the first frame:

| Department | Rule | Public games |
|---|---|---|
| click | clicks, no movement keys | 8 |
| keys | movement keys, no clicks | 6 |
| mixed | both | 11 |

- **The practice final:** 5 games held back (bp35, lp85, r11l, sc25, tu93), stratified by department, drawn with a fixed seed.
- **The real final:** the Kaggle hidden set.

## The faculty (10 professors)

Each was rated on all 25 games × 8 seeds × 3,000 actions on the PC. The runs are in `D:\planet\arc3\uni\`.

| Professor | Lesson | All 25 games |
|---|---|---|
| plain | Untried presses, nearest first; on a new level, click first the kinds that were on the last winning route | 0.518 |
| runs-if-runs | As plain; if the last won route was long runs of one press, explore the next level by runs | 0.516 |
| runs / runs-light | Always explore by runs | 0.377 / 0.399 |
| replay | First try the last level's route again | 0.469 |
| clicks-last | Use moves until they teach nothing new, then click | 0.439 |
| fresh-kinds | Diminishing attention per kind of thing | 0.320 |
| model | Don't spend presses where the movement model has never been wrong | 0.493 |
| route-prior / -light | Order presses the way winning routes in this department's other games did | 0.121 / 0.187 |

**Per department, on the 20 training games** (from `uni/report.md`):
- **click:** runs +0.143 but only 5/8 seeds; runs-if-runs +0.042, 7/8 seeds.
- **keys:** every professor is within ±0.002, except route-prior at −0.18.
- **mixed:** runs-if-runs +0.002, 7/8 seeds; everything else loses. runs and route-prior break the cheap wins.

## The board, and how the board was graded

**Board v1 rules:**
1. Better on average than plain on the department's training games.
2. Better on ≥ 6 of 8 seeds.
3. Keep ≥ 70% of every cheap win (a game where plain scores ≥ 1).

**v1 picked:** runs-if-runs for click and mixed, model for keys. **On the practice final, v1's graduate lost to plain on 8 of 8 seeds** (1.420 against 1.533):
- sc25: 1.95 → 1.67
- tu93: 0.62 → 0.38

v1 had let noise-sized gains (+0.002) through.

**Grading the board itself** (`board_cv.py`): 5 rotating finals over the 25 games. In each, the board picks per department from the other games, and its picks are scored on the held-out games, seed-paired against plain.

| Board rules | Held-out gain against plain | Folds better / worse |
|---|---|---|
| greedy (best average) | −0.257 | 0 / 3 |
| board v1 | −0.023 | 0 / 2 |
| strict (gain ≥ 0.02 and 7/8 seeds, keep cheap wins) | ±0.000 | 0 / 0 |
| relative (gain ≥ 10% and 7/8 seeds) | ±0.000 | 0 / 0 |

**What this shows:**
- The looser the board, the more it loses on games it hasn't seen.
- The strict board never makes things worse. With this faculty, it almost never changes anything.

**Board v2 (strict) is now the rule.** On the 20 training games it promotes one professor: **click → runs-if-runs** (+0.042, 7/8 seeds). Keys and mixed stay plain.
- Score: 0.526 on all 25 games, against 0.518 for plain.
- On the practice final it is 1.522 against 1.533, worse on 1/8 seeds.

**Honesty note:** v2's rules were chosen with rotating finals that include the 5 exam games, so the practice final is spent. The next clean exam is the Kaggle hidden set.

## The trail: the top Mika walks the unsolved levels (Oct 22, later)

Jonathan:
> "theres also the unsolved tests that no mika has done ... one mika at the top going down the unsolved path ... we have to peel off that layer and fill it in with the levels coming in. so each level rearranges to its orientation for the school on the inside and theres a trail on the outside we have to process."

**How it works** (`levelrun.py`, `intake_report.py`, `level_board.py`; results in `D:\planet\arc3\trail\`):
- **The frontier.** The top Mika (the graduate) is dropped **cold** into every level of every public game, using the engine's `set_level`. She gets 12,000 presses per level, over 2 seeds: 366 level runs, about 25 minutes.
- **Intake.** Every level she wins comes inside the school, filed with its department, route anatomy, and waste.
- **Level exams.** Fresh students are dropped straight into each inside level, 4 seeds × 3,000 presses:
  - **cold:** blank mind;
  - **warm:** carrying exactly what the previous level's route teaches (the kinds on the route, the goal colour, its run structure, the route itself, and since the goal professors, what its winning press did and its picture), as if she had won that level herself.
- **Weighting.** Each level counts as the official card counts it: level k weighs k. The board re-peels from these grades, and is graded again on rotating finals.

**What came in:**
- **39 of 183 levels** are now inside the school.
- **14 of them lie beyond what she ever reaches playing in order:**
  - lp85 L4, L5, L7, L8
  - tu93 L3–L5, L7–L9
  - vc33 L3, L4, L6
  - ka59 L5
- **The trail had levels she can win but never gets to.**

| Department | Inside / total | Mean run length on route | Routes with clicks | Waste | Shortest ÷ human |
|---|---|---|---|---|---|
| click | 14 / 59 | 9.8 | 100% | 187× | 0.40 |
| keys | 10 / 46 | 1.8 | 0% | 127× | 0.39 |
| mixed | 15 / 78 | 2.3 | 67% | 197× | 0.42 |

**Level exams and the re-peeled board** (training games only; the full tables are in `trail/level_board.md`):
- **No professor passes the strict board in any department, cold or warm.**
- **Biggest raw gains:**
  - cold click: runs +0.55, but 3/4 seeds;
  - warm mixed: model +0.49, but 1/4 seeds.
  - The board rejects both.
- **runs-if-runs:** in warm click exams (the department where the whole-game ratings promoted it) it is **−0.91**. On deeper levels it doesn't hold.
- **Graded on rotating finals:** greedy boards lose (cold −2.30, 0 of 5 folds better; warm −0.24, 1/5). The strict board stays at about ±0 (−0.009 warm).
- **Curriculum from the trail: plain in every department.**

## The sideways plane: the first employer survey (Oct 22, morning)

Jonathan:
> "do we need something that changes the school too? ... each level that goes in is still sectioned off from each other ... nothing carries over ... the school plane would be one of the orthogonal planes rotating up/down, then theres the 2nd plane that rotates sideways and tries to make those connections."

And:
> "they would be like the employers right? ... jobs arent doing exactly what you learned in school so its like seeing if theres horizontal connections that are able to do work once a student is out."

**Why nothing carried.** Each level's map is keyed by exact screens, so no two levels ever share a state. Only three small notes cross the boundary.

**The sideways unit: events.** An event is a press described in kinds of things: what was pressed, and what it did (moved, recoloured, appeared or vanished, near the actor or elsewhere). Three granularities:

| Granularity | What it keeps |
|---|---|
| fine | colours and sizes |
| mid | colours, no sizes or counts |
| coarse | colour-free roles, e.g. "the clicked thing changed itself", "the mover changed something else" |

**The survey** (`events.py`, `events_lift.py`):
- Every winning route in the casebook was replayed from its level start; the engine is deterministic, and 36 of 39 reproduce the win (18 games).
- Each route was turned into events. For the winning press, the effect is read from the frame *before* the switch to the next level.
- The question: does the winning press repeat an earlier win more often than an ordinary press on the route does? That ratio is the **lift**: how well a known event singles out the goal.

| Granularity | Employer pool | Winning press = an earlier win | Ordinary press = an earlier win | Lift |
|---|---|---|---|---|
| fine | same game, earlier levels (18 levels) | 28% | 1% | **26×** |
| mid | same game, earlier levels | 39% | 7% | **5.6×** |
| coarse | same game, earlier levels | 94% | 73% | 1.3× |
| fine / mid | other games, same department | 0% | 0% | none |
| coarse | other games, same department (36 levels) | 33% | 33% | 1.0× |
| coarse | other departments | 25% | 32% | 0.8× |

**What the employers say:**
- **Inside a game, the goal carries sideways.** The press that wins level k+1 repeats an earlier level's winning event far more often than ordinary presses do: 26× at fine grain, 5.6× at mid.
- **Between games, nothing in this vocabulary does.**
  - Colours change between games, so fine and mid events never match.
  - Colour-free roles match the winning press no more often than an ordinary press (1.0×, 0.8×).
- **In job terms:** skills carry within a company, not between companies, with this vocabulary.

## A ladder of descriptions, general to specific (Oct 22, morning)

Jonathan:
> "it should be more general right? like it should start by describing a victory as something like loss of control with moves available and everything with a definition, and then for games it would be more specific events. so is it just trying to find ways to describe things more generally?"

**Yes, with one condition.** Each rung of the ladder must still single out what matters (lift) **at the scope where it is used**:
- general rungs across games;
- specific rungs within a game.

Generality alone is cheap: the colour-free roles above are general and carry nothing (1.0×). This is the same rule as the slot filler and the board: keep a description only while it holds where it is applied.

**First general rung, from Jonathan's "loss of control with moves available":**
- **"The game took control":** one press produces a longer animation than this game usually produces (≥ 3 frames and ≥ 2× the game's usual). Control is lost for a moment while moves are still available, unlike a death, where the moves are gone.
- It is measured against each game's own usual animation length, so it means the same thing in every game.

**First measurement** (`takeover.py`, 36 replayable winning routes from 18 games, 150 arbitrary presses from each level start): winning press 47%, other route presses 31%, arbitrary presses 12%, i.e. 3.8× and 2.5×.

**Correction (same day).** Both of those lifts overstate it:
1. **The winning press also plays the level-end animation**, so it "takes control" partly because it won. Its 47% can't be used to steer anyway.
2. **Route presses always change something; 62% of arbitrary presses change nothing.** The explorer already prefers presses that change something, so the fair baseline is arbitrary presses that changed something.

Against that baseline, route presses took control 31% of the time vs 26%: **1.2× pooled, 1.6× with every game weighted equally, more often in 8 of 18 games.** A weak signal, not the 2.5× first reported.

## Relational events: the second employer survey (Oct 22)

`relations.py` → `trail/relations.md`. Colour-free descriptions made of relations between things, each tested as a general rung: on route presses (the winning press excluded, because of the level-end animation) against arbitrary presses that changed something, pooled and with every game weighted equally.

| Description | Route presses | Arbitrary presses that changed something | Lift (pooled) | Lift (games equal) | Games where route presses have it more |
|---|---|---|---|---|---|
| made two things equal | 8% | 2.3% | 3.4× | 0.5× | 3 of 18 |
| made two equal things differ | 8% | 3.0% | 2.8× | 0.9× | 4 of 18 |
| a colour vanished | 6% | 3.0% | 2.1× | 1.9× | 8 of 18 |
| **something small changed far from the main change** (an indicator) | 55% | 30% | **1.8×** | **1.9×** | **15 of 18** |
| took control | 31% | 26% | 1.2× | 1.6× | 8 of 18 |
| more / less symmetric, fewer / more things, touched a one-of-a-kind thing | | | 0.5–1.0× | | |

"Made two things equal" looks strong pooled but comes from 3 games. The **indicator** relation is the most consistent between games: present on more than half of all route presses, and more often than on arbitrary presses in 15 of 18 games.

## The goal professors: graded by students (Oct 22)

Jonathan: *"you can do that now."* Built into the explorer as knobs (`mika3/explorer2.py`), taught as professors (`mika3/university.py`). Each rung marks two things: the **kinds of press** that produced the mark (a bonus proportional to how often that kind does), and the **states** where it happened (preferred when choosing where to go next). Every press also records which rung stood behind it (its citation), counted in the run's `rungs` log.

| Professor | Rung |
|---|---|
| took-control / took-light | general: the game took control (relative to this game's usual) |
| win-event | specific: the press repeats what the last win's press did, in this game's colours (only effects that are not what every press does here) |
| two-rungs | both |
| far-change, far-change-win | general: an indicator changed or a colour vanished (relational survey), alone and with win-event |
| far-rare, three-rungs | the same, counted only while it is unusual for this game (< 3 in 10 presses); and all three rungs |
| win-image, took-image, two-rungs-image | the image plane, after the fact (below) |
| goal-search, two-rungs-search | the image plane, forward (below) |
| **pick-only (control)** | none. Every goal professor also chooses among the near unexplored places by score rather than taking the nearest; this professor does only that, so a rung earns its place only if it beats the control |

**Level exams** (all 39 inside levels, 4 seeds, level k weighs k; `trail/goal_report.md`):

| Professor | Cold: vs plain / vs control (seeds) | Warm: vs plain / vs control (seeds) | Where |
|---|---|---|---|
| pick-only (control) | +0.10 | +0.16 (4/4) | keys |
| took-control | +0.32 / **+0.22** (3/4) | +0.39 / **+0.24** (2/4) | click (+0.52 / +0.82 vs control) |
| win-event | (no win to carry, cold) | +0.20 / +0.05 (2/4) | keys (+0.08) |
| **two-rungs** | +0.32 / **+0.22** (3/4) | +0.55 / **+0.39** (3/4) | click +0.82, keys +0.24 vs control |
| far-change / far-rare / three-rungs | −0.50 to −0.61 | −0.60 to −0.86 | keys −1.4 to −1.7 vs control |
| win-image | | +0.00 (identical to the control) | |
| goal-search | | −0.23 (0/4) | keys −0.55 |
| two-rungs-search | | +0.19 (1/4) | |

**Whole games** (25 games × 8 seeds × 3,000 actions):

| Professor | Mean | vs plain (seeds better) | vs control (seeds better) |
|---|---|---|---|
| plain | 0.518 | | |
| pick-only (control) | 0.521 | +0.003 | |
| took-control | 0.548 | +0.030 (6/8) | +0.027 (3/8) |
| win-event | 0.523 | +0.005 (6/8) | +0.002 (2/8) |
| **two-rungs** | **0.577** | +0.059 (6/8) | **+0.056 (4/8)**; up r11l +0.70, sp80 +0.58, tu93 +0.13; down lf52 −0.08 |
| far-change / far-rare / three-rungs | 0.462–0.472 | −0.05 | g50t −0.89 |
| win-image / took-image / two-rungs-image | 0.521 / 0.548 / 0.577 | identical to the same professor without the image rung | |
| goal-search | 0.515 | −0.003 (5/8) | −0.006 (4/8); tu93 −0.19 |
| two-rungs-search | 0.562 | +0.044 (6/8) | +0.041 (5/8); 0.015 below two-rungs |

**Examples of the specific rung working:** on tu93 level 2 (warm), all four two-rungs students won in 32–38 presses; plain took 47–54. tu93 level 3: 1 of 4 plain students won within 3,000 presses, 3 of 4 two-rungs students did.

**The board's verdict:** nothing passes the strict board (training games only, per department). Closest: whole-game click, took-control and two-rungs +0.015 at 7/8 seeds, just under the 0.02 bar; mixed +0.043 but 3/8 seeds. **The curriculum stays as it was.**

**What the goal professors show:**
1. **The ladder works as a lesson where its description is relative to the game's own usual.** Took-control, measured against the game's usual animation, beats the control, mostly on click levels. The specific rung (the last win's event) adds on top, mostly on keys levels. Two-rungs is the best agent on every offline measure so far.
2. **A description that marks winning routes is not automatically a good lesson.** The indicator relation was the most consistent marker across games (15 of 18), and its students did worst of all (g50t −0.89). The same thing happened with the route prior. Only the student test catches it.
3. **The gains are real but lumpy.** Two-rungs beats the control on 3/4 seeds in level exams but on only 4/8 seeds in whole games; most of its whole-game gain comes from three games. That is why the board doesn't promote it.

## The image plane: proofs from pictures (Oct 22)

Jonathan:
> "the inner core would be able to rotate the nodes wouldnt they? but limited. oh like gears thats pull in the helixes? ... each step on the real path needs the reasoning behind it. so maybe the real plane spins in place, and the orthogonal planes build up the evidence behind each step? and that evidence comes from images of previous games where she learned those things."

> "each plane should have a process it does each time it rotates right? one of them would have the solve learn share process, then another could have one that makes those proofs from images? when a new piece of data comes in each one would rotate and turn the raw stuff into something processed."

**The planes as gears of different sizes.** Each turns when its own kind of input is complete, and each turn hands on something more processed:

| Plane | Turns once per… | Process | Hands on |
|---|---|---|---|
| real plane (play) | press | update the map; choose the next press, with its citation | a press and a state |
| image plane | notable moment (a win, the game taking control, a failed prediction) | crop the change and put it in standard form with the limited turns; file it, or match it to one on file | candidate moments, and proofs |
| school plane (solve → learn → share) | level | look back; flatten into blocks; professors teach fresh students | blocks and lessons |
| board / core | batch of games | student tests and controls; promote what holds, retire what doesn't | the core |

A moment becomes a **proof** by its record, not its looks: each citation predicts something, and a moment that has come true every time (≥ 3, never wrong) is certified, as the movement model already is.

**Moments.** The before/after crop of a press's main change (border bars are clocks and are cut away). The **limited turns**: colours renumbered in order of appearance, the 8 flips/rotations, and the shift (where it happened on the screen doesn't matter). Three grains: with one pixel of surroundings, the changed pixels only, the outline only.

**Survey 1: after the fact** (`moments.py` → `trail/moments.md`):
- **Between games, winning pictures never match** (0% at every grain and with every turn). Ordinary presses' pictures do match other games' (moves look alike), but no more on routes than off (0.4–1.1×).
- **Within a game, the turns are what make wins recognisable.** The share of winning presses whose picture matches an earlier level's winning press:

| Grain | No turns | Recolouring | Recolouring + flips | Arbitrary presses (with all turns) |
|---|---|---|---|---|
| with surroundings | 6% | 24% | **47%** | 5% (9.2×) |
| changed pixels only | 12% | 29% | **65%** | 9% (7.5×) |

  The levels of a game reuse the same winning picture, recoloured and rotated. That is the gears, measured.
- **But a picture is only seen after the press.** In tu93 no ordinary route press looks like the win; in lp85 every click does. So matching press pictures can't steer: **win-image changed no decision at all** (identical to the control on every seed and level).

**Survey 2: forward** (`goalsearch.py` → `trail/goalsearch.md`). Look for the *before* half of the last win's picture in the next level's start screen:

| Colours | Levels with a hit | Levels where a hit is on the next win's place | Hits on the place | Blind guess | Lift |
|---|---|---|---|---|---|
| exact, 8 flips | 9 of 12 | 7 | 20% | 3% | **5.8×** |
| recoloured too, 8 flips | 11 of 12 | 11 | 1% | 3% | 0.4× |

Which turns are allowed depends on the use: recolouring helps recognise a win after the fact, but in a forward search it lets the picture fit almost anywhere. "Limited" matters.

**The goal-search professor** clicks things where the before-picture fits first, and prefers presses and places that touch it.
- All of its effect is in tu93. **Reach goes up:** L3 from 1 of 4 students winning to 4 of 4. **Efficiency goes down:** L2 from 35–45 presses to 57–64.
- The squared score punishes the slowdown more than it rewards the reach: −0.23 against the control in warm exams, 0.515 against 0.521 in whole games; with two-rungs, 0.562 against 0.577.

**What the image plane shows:**
1. **The limited gears are real and measurable.** Recolouring + flips makes 65% of wins recognisable as earlier wins of the same game, up from 12% with no turns.
2. **Recognising is not steering.** Pictures of presses only certify a step after it is taken. To guide the next step, the picture has to be used forward (where would this happen here?), and the first forward use finds the next win's place 5.8× better than chance.
3. **Evidence has a cost when it is used.** Following the goal place helps where she would otherwise never win, and slows her where she was already fast. The next version should consult it only when she is stuck (no progress after some presses), so it buys reach without taxing easy levels.

## Kaggle

| Submission | Hidden score |
|---|---|
| PriorAgent v10 | 0.25 |
| Oct 21: v3n (offline 0.52) | **0.29** |
| Oct 22: the university graduate under board v2 (click = runs-if-runs, keys/mixed = plain; edge bug fixed). Notebook v2 | **0.29** |
| Oct 23, 00:12 UTC (experiment): two-rungs everywhere (offline 0.577). Notebook `jonpelchat/mika-arc-agi-3` v3, submission 57542480 | **0.29** |

Offline went from 0.12 to 0.58 (about 5×); hidden only from 0.25 to 0.29, and has not moved across three different versions of the explorer (v3n 0.518, the university 0.526, two-rungs 0.577 offline). **The public games flatter the explorer.** Its cheap public wins (lp85, r11l, vc33, m0r0, g50t, sp80) are not typical of the hidden set; whatever the frames-only explorer wins on the hidden games, all three versions win the same.

From Oct 23 the Kaggle entry is the hybrid (`ARC3_HYBRID.md`): the public LLM harness with Mika's planes as its evidence layer. The frames-only explorer and this university remain the paper's subject.

## What the university says so far

1. **The teach level is where proxy measures fail.** The route prior is a professor whose lectures *sound* right: on unseen games it ranks the winning press in the top quarter. Its students do 4× worse. The indicator relation repeated this: the most consistent marker of winning routes, the worst students. Only the student test shows it.
2. **The board needs grading too.** Noise-level gains (+0.002, even at 7/8 seeds) do not hold on new games. A board that demands a real effect (≥ 0.02 and 7/8 seeds) is the only one that does no harm.
3. **The faculty was the bottleneck.** Every knob-type lesson plan (pressing harder or in a different order) is noise or harmful once the deep levels count at their weight.
4. **Reach is a separate loss.** Of the 39 levels she can win, she reaches only 25 by playing in order. Some score is lost simply because she never gets to levels she could solve.
5. **Lessons about the goal are the first that help offline, if they are relative to the game.** "The game took control" (general, relative to the game's usual) and "what the last win did" (specific, within the game) together make the best offline agent so far (0.577 against 0.518), and beat their control in level exams (+0.22 cold, +0.39 warm). The gain is not consistent enough for the strict board, and it did not show on the hidden set (0.29, the same as before).
6. **Every measurement needs its control.** The goal professors also changed how she picks the next place to explore; the pick-only control shows that change alone is worth about +0.003 whole-game and +0.10–0.16 in level exams. Without it, the rungs would have been credited with that too.
7. **Pictures carry within a game under limited turns, not between games.** The turns (recolouring, flips) make two thirds of wins recognisable from earlier wins; nothing in a picture carries to another game. A picture certifies a step after the fact; used forward, it finds the next goal 5.8× better than chance, but following it costs presses on easy levels.

## How to run it

On the PC, in `D:\planet\arc3`:

| Step | Command |
|---|---|
| Rate the faculty | `uni\run_faculty.bat`. 10 professors × 25 games × 8 seeds, about 55 minutes |
| Board report and curriculum | `python board.py uni` → `uni\report.md`, `mika3\curriculum.json` |
| Grade the boards | `python board_cv.py uni` → `uni\board_cv.md` |
| Walk the trail | `trail\run_frontier.bat`, about 25 minutes. Then `python intake_report.py trail\frontier.json trail\frontier_casebook.json uni\plain.json` |
| Level exams | `trail\run_exams.bat`, 14 exams, about 20 minutes. Then `python level_board.py trail` |
| Employer survey | `python events.py trail\frontier_casebook.json trail\events.json`, then `python events_lift.py trail\events.json` |
| The general rung | `python takeover.py trail\frontier_casebook.json trail\takeover.md` |
| Relational survey | `python relations.py trail\frontier_casebook.json trail\relations.md` (about 5 minutes; `python relations.py trail\relations.json trail\relations.md` re-reports) |
| Image plane surveys | `python moments.py trail\frontier_casebook.json trail\moments.md` (under a minute; pass `trail\moments.json` to re-report), `python goalsearch.py trail\frontier_casebook.json trail\goalsearch.md` |
| Goal professors | `run_goal.bat` … `run_goal5.bat` (exams and whole games, 17–35 minutes each). Then `python goal_report.py trail uni` → `trail\goal_report.md` |
| Build the Kaggle notebook | `python build_nb.py MikaUniversity <tag> 4000` (the board's graduate) or `python build_nb.py Prof_two_rungs <tag> 4000`. It embeds the curriculum and the department priors |
