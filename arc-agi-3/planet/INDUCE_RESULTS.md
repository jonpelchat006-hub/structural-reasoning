# Transition induction — first result (2026-09-03)

`induce.py` runs the ARC-AGI-1 inducers from `D:\shovelcat-colony\arc-slice` and `arc-proposer` (June 2026,
81/400 train) over ARC-AGI-3 presses. A press is a train pair: (frame, action) -> next frame. Presses are
grouped by action; one operator per action is induced from the early presses and scored on the late presses
it never saw, with the same early/late split (first min(80, 67%) of non-RESET presses) and the same
changed-cell metrics as `eye.py`, so the two columns compare directly. Data: the 25 `D:\planet\eye\<game>.npz`
files collect.py kept (about 3,000 presses). No API calls.

## Operators (ported)

| operator | source | what it says |
|---|---|---|
| displace | arc-proposer `induce.ts` induceMove, arc-slice `discover.ts` induceMoveByColor, `quaternion.ts` (D4 stage) | the mover's cells shift by one (dy,dx) per action, optionally mirrored/rotated; floor colours learned from where it went; refused when the destination holds any other colour |
| slide | `discover.ts` induceGravity, on the mover | shift in one direction until a wall |
| restore | (new, from the vc33 reset button) | the press returns the level to the frame it started from; for clicks the trigger is the colour under the click |
| local1 / local2 | `prune.ts` induceLocalRule | each cell's next value is a function of its 3x3 / 5x5 neighbourhood; conflicting keys abstain |
| click | local1 with the clicked component and the distance to the click in the key | ACTION6 only |
| ambient | local2 on the register cells, keyed on the action | the budget bar / counter (`budget_lab.py`); register found as the cells touched by presses that changed <= 4 cells, widened to the full row or column |

The gate (the operator-induction gate the August docs cite): displace/slide/restore must reproduce every
early press of their action exactly on the non-register cells; a local rule must have zero conflicting keys.
BEST = the operator that scored best on a held-out quarter of the early presses, gate or not.
STRICT = the best among gated operators; no-change when none passed.

## The table

Late presses, changed cells. `acc` = fraction of truly changed cells predicted with the right colour;
`f1` = change-detection F1; `mech` = acc on non-register cells only. `*` = passed the gate.

```
(morning run, before the tr87 work)
  game   BEST acc     f1   mech   STRICT     f1  EYE CAT     f1  operators per action
  ar25      0.258   0.28  0.248    0.014   0.03    0.923   0.94  1:restore 2:local2 3:displace 4:local2 5:displace 6:restore
  bp35      0.099   0.18  0.085    0.015   0.03    0.678   0.48  3:local2 4:local2 6:click
  cd82      0.003   0.01    0.0    0.003   0.01    0.643   0.53  1:displace 2:displace 3:displace 4:displace 5:displace 6:restore
  cn04      0.226   0.46  0.228    0.208   0.44    0.671   0.41  1:displace* 2:displace* 3:displace 4:displace 5:local2 6:click
  dc22      0.275   0.43   0.32    0.376   0.55    0.812   0.53  1:displace* 2:local1 3:displace* 4:displace 6:restore
  ft09        0.0   0.00    0.0      0.0   0.00    0.202   0.21  6:restore
  g50t      0.477   0.57  0.486    0.144   0.25    0.845   0.73  1:displace* 2:local2 3:displace 4:local2 5:restore
  ka59      0.393   0.56  0.531    0.213   0.35    0.746   0.66  1:displace 2:local2 3:displace* 4:local1 6:restore
  lf52      0.576   0.55    0.5    0.152   0.26    0.837   0.60  1:displace 2:displace 3:displace 4:displace 6:restore
  lp85       None   0.00   None     None   0.00     None   0.00  6:restore
  ls20      0.694   0.76  0.728    0.402   0.57    0.883   0.81  1:displace* 2:displace 3:displace* 4:restore
  m0r0       0.36   0.53  0.375      0.0   0.00     0.83   0.84  1:displace 2:displace 3:displace 4:local2 5:displace 6:restore
  r11l       0.16   0.22  0.147    0.016   0.03    0.521   0.35  6:restore
  re86      0.137   0.22  0.156    0.025   0.05    0.659   0.55  1:displace 2:local1 3:displace 4:local2 5:displace
  s5i5       0.57   0.52  0.444    0.289   0.45      1.0   0.88  6:restore
  sb26      0.159   0.27  0.033    0.318   0.48    0.411   0.60  5:displace 6:click
  sc25      0.154   0.26  0.188    0.205   0.35    0.732   0.76  1:local1 2:displace* 3:local1 4:displace 6:restore
  sk48      0.258   0.41  0.261      0.0   0.00    0.835   0.82  1:local2 2:local2 3:local2 4:displace 6:restore
  sp80       0.99   0.88    1.0     0.99   0.88    0.995   0.85  1:displace* 2:displace* 3:displace* 4:displace* 5:displace 6:restore
  su15      0.281   0.44  0.448    0.013   0.03    0.956   0.93  6:click
  tn36      0.727   0.84    0.0    0.727   0.84    0.945   0.97  6:restore
  tr87       0.43   0.46   0.43      0.0   0.00    0.976   0.89  1:local2 2:local2 3:displace 4:local1
  tu93      0.613   0.76  0.556     0.35   0.52    0.988   0.93  1:displace 2:local2 3:displace* 4:local1
  vc33      0.514   0.68    0.5    0.037   0.07      1.0   0.98  6:restore
  wa30       0.64   0.77  0.648      0.0   0.00    0.948   0.93  1:local2 2:local2 3:local2 4:local2 5:displace
  MEAN      0.375   0.44  0.346    0.187   0.25    0.793   0.69
```

Gated action-operators: 14, in 8 games (cn04, dc22, g50t, ka59, ls20, sc25, sp80, tu93). Full per-operator
scores (select, exact, gate) per action are in `D:\planet\eye\induce_results.json`.

## Reading

1. **The eye predicts pixels better; induction produces something the eye cannot: an operator with a
   precondition.** Mean changed-cell accuracy 0.375 (best) / 0.187 (gated) against the eye's 0.793. But every
   `*` is a rule of the form "ACTION3 moves the (9,12) block by (0,-5) when the five cells ahead are colour 3
   or 5" — plannable, and exact on every early press. The eye's 0.79 is a number, not a rule.
2. **sp80 is fully modelled.** All four movement actions gated, 0.99 on late presses, equal to the eye. That is
   the first game where the symbolic path can plan end to end with nothing hand-written.
3. **ls20's move rules are exact; the remaining misses are pickups and refills** (a ring vanishing, the bar
   jumping), i.e. second-order mechanics a single-shift operator does not cover. Movement itself is right on
   actions 1 and 3 and on all late presses of action 4.
4. **Where induction fails it fails for nameable reasons**, each a next inducer: tu93's sprite mirrors when
   it changes direction (the D4 stage catches action 3, not yet 2 and 4); tr87 and r11l are non-rigid
   cascades (many components recolour per press); m0r0 is data-starved (the collect policy spent 70% of
   presses on clicks, leaving 1-7 presses per movement action); ft09 and lp85 barely change at all in 120
   random presses; cd82 changes on nearly every press in ways no shift explains.
5. **The register matters as much as the mover.** Before the tick region was learned, no operator could be
   exact on any game because the bar drained two cells per press outside the 80%-of-presses ambient mask.
   The register is found by budget_lab's signature idea (presses that changed almost nothing) and predicted
   by its own local rule keyed on the action.
6. **A caveat on the comparison.** The eye's numbers include the register cells, which are easy; `mech`
   excludes them for induction but the eye was not re-scored that way.

## Layer 3, first live run — sp80 level 1 at press 29 (2026-09-03, later the same day)

`play.py` now carries the world model (`induce.Operators`): the gated operators are fitted from the game's
prior touches, refitted every 20 presses on the run's own presses, and wherever an action has one its
prediction replaces the eye's with no uncertainty. `plan_step` is the proposer over that model: breadth-first
over the gated operators to the nearest bar position the run has not stood in, ties broken toward the
nearest goal (play.py's `approach`), first action of the path pressed, replanned every press. At every fourth
new place one button no operator explains is probed.

Three fixes were needed on the way, each a law the run taught: a mover partly leaving the frame is refused
(the edge is a wall); a refusal with floor ahead is remembered by place, and the same coordinate refused at
two places along the motion axis becomes an arena bound (sp80's bar lives between rows 12 and 44); and a
local rule that has never explained a real change cannot pass the gate — "nothing ever happens" is not a
law, so ACTION5 stayed a button to probe.

| sp80, 150 presses | levels | places visited | planned presses | surprise op / eye |
|---|---|---|---|---|
| eye only, three runs earlier today (`play_batch_*.jsonl`) | 0, 0, 0 | — | 0 | — |
| operators, no planner (`play_sp80_ops.log`) | 0 | — | 0 | 0.029 / 0.097 |
| operators + planner, before the bounds fix (`play_sp80_plan.log`) | 0 | 85 | 108 | 0.021 / 0.892 |
| operators + planner + bounds (`play_sp80_plan2.log`) | **1 at press 29** | 86 | 120 | 0.285 / 1.0 |

How the level fell: the planner walked the bar toward a goal with exact 4-px moves (distance 32 → 8), a
life went to the budget on an ACTION5 probe at press 25, the bar was walked back to distance 12 after the
reset, and the ACTION5 probe at press 29 changed 1,168 cells: level complete. ACTION5 is the act button,
and it only does something when the bar stands in the right place — exactly the kind of state-dependent
button the "nothing ever happens" gate keeps probing. All four movement operators kept their gate for the
whole run; operator surprise rose after the level because level 2's layout was not in the fit yet.

## The motion map — the derivative of the screen per button (`flow.py`, same day)

Jonathan's picture: the map should carry a direction for every pixel, walls at 0, the budget's drain as a
constant pattern, each button in the foreground with pins into the pixels it controls, and the surprises
piling up behind the screen. `flow.py` builds exactly that from the recorded presses: for each press the
motion of every changed pixel (the displace search, then per-piece block matching; floor and wall colours
never move), aggregated into PINS = per (button, colour) the mode vector and how often the pixel obeyed it;
the register as a front with a fixed drift; a surprise layer counting, per pixel, the presses where the
pixel did not do what its pins said. Rendered to `D:\planet\eye\flow_<game>.png`.

What the pins say, straight from the data:

| game | pins | register |
|---|---|---|
| sp80 | up/down/left/right move colour 9 by exactly 4 cells, **100% obeyed** on 320–800 px each; 5 and click move nothing | top row, front −2 cells/press |
| ls20 | the four buttons move colours 9 and 12 (the key block) by 5 cells, 96–100% obeyed | rows 61–62, front +1 cell/press |
| tr87 | left/right move colour 0 by **±7** at 100% (a selector stepping along a row of tiles); up/down give colours 5 and 7 vectors obeyed only 17–34% | none |

The tr87 row is a reading of the game the operators could not make: left/right select a tile (pitch 7),
up/down transform the selected glyph in place. A transform is not a shift, so its "flow" is incoherent —
it is the per-object D4 case (quaternion.ts) applied about the object's own centre, the next inducer.

The pins are the world model in another coordinate: a displace operator IS a pin (button → colour →
vector) plus a floor rule. The map form adds what the operator form hid — which pixels a button does not
reach, where the surprise concentrates (sp80: the two arena bounds; tr87: the glyph interiors), and the
register's drift as motion rather than as a masked-out nuisance.

## Per-object pins and the tr87 reading (later the same day)

Jonathan asked for per-object transform pins for tr87, and for the pins to attach both ways: every control
wants every pixel and breaks off where its claim fails; every pixel wants to stay independent and attaches
only under repeated evidence. Built:

- **Transform** (quaternion.ts about the object's own centre): the smallest square containing the diff whose
  contents are a D4 image of themselves, anchored to a selector colour. Fired nowhere yet — tr87's glyphs
  are not rotated, see below — but it is the right shape for tu93's mirrored sprite, where it was chosen for
  action 4.
- **Cycle** (the per-object STATE pin): the button replaces one region's contents with the next state of a
  finite sequence; region learned relative to an anchor colour's box (the smallest box in anchor
  coordinates that held every change), table content -> next content, unseen content abstains. tr87's up/down
  cycle the 5x5 glyph under the black selector: 29 distinct before-states in 120 presses, one with two
  successors. Down gated at exact 1.00; up 0.86. Also gated on sp80 (left/right), tu93 (2), wa30 (1, 2, 4),
  sk48 (3).
- **Wrap**: the displace step plus one long jump the other way along the same axis, fired at a learned
  coordinate (tr87's selector leaves col 15 and reappears at col 43).
- **Figure over ground**: between two shifts that both reproduce the frame, the mover is the RARER colour. A
  symmetric bracket over uniform floor reads either way, and a periodic row of tiles lets the floor "move" by
  a whole pitch; rarity first, shift length second.
- **Multi-piece movers**: the selector is two brackets; the locator now takes all cells of the mover's
  colours when their count matches.
- **The register by its own signature**: tr87's counter ticks every second press on the bottom row, so no
  press was ever small enough for the tick rule. New rule: a line whose cells change 1-3 times each, in
  strictly one-after-another order of first change, hit on >= 40% of presses. Movers fail the strict order
  because they change several cells at once.
- **Bonds** (`flow.py`): per (button, colour) a bond that starts at 0.1, climbs by 35% of the gap when the
  colour obeyed on a press, halves on a violation, and decays 10% per press where nothing happened. The map
  draws a pin only while its bond holds (>= 0.5). tr87: left/right on colour 0 hold at 0.99; the glyph
  colours under up/down broke off to 0.00-0.01; sp80's four pins hold at 0.76-0.96.

tr87 offline: **0.43 -> 0.893** best (gated 0.774), against the eye's 0.976; left/right displace with wrap
gated at exact 1.00, down gated as a cycle. Live (`play_tr87_plan3.log`): the gates held through 150
presses, 112 planned, 149 places visited, operator surprise 0.012 vs the eye's 0.996 on the same run; no
level, because the planner knows how tr87 moves and nothing about what it wants (the pairs at the top of the
screen are the targets; the agent has no notion of "match").

The batch after all of it (`induce_table_v4.txt`):

```
transition induction vs the eye; 25 games (late presses, changed cells; * = passed the gate)
  game   BEST acc     f1   mech   STRICT     f1  EYE CAT     f1  operators per action
  ar25      0.258   0.28  0.248    0.014   0.03    0.923   0.94  1:restore 2:local2 3:displace 4:local2 5:displace 6:restore
  bp35      0.099   0.18  0.085    0.015   0.03    0.678   0.48  3:local2 4:local2 6:click
  cd82      0.003   0.01    0.0    0.003   0.01    0.643   0.53  1:displace 2:displace 3:displace 4:displace 5:displace 6:restore
  cn04      0.042   0.08  0.042      0.0   0.00    0.671   0.41  1:displace 2:displace 3:local2 4:displace 5:local2 6:click
  dc22       0.43   0.60    0.5     0.43   0.60    0.812   0.53  1:displace* 2:displace* 3:displace* 4:displace* 6:restore
  ft09        0.0   0.00    0.0      0.0   0.00    0.202   0.21  6:restore
  g50t      0.814   0.83  0.831     0.24   0.39    0.845   0.73  1:displace* 2:displace* 3:displace 4:displace 5:restore
  ka59      0.393   0.56  0.531    0.557   0.71    0.746   0.66  1:displace 2:local2 3:displace* 4:local1 6:restore
  lf52      0.576   0.55    0.5    0.152   0.26    0.837   0.60  1:displace 2:displace 3:displace 4:displace 6:restore
  lp85       None   0.00   None     None   0.00     None   0.00  6:restore
  ls20      0.694   0.76  0.728    0.402   0.57    0.883   0.81  1:displace* 2:displace 3:displace* 4:restore
  m0r0      0.719   0.79   0.75     0.36   0.53     0.83   0.84  1:displace 2:displace* 3:displace 4:transform 5:displace 6:restore
  r11l       0.16   0.22  0.147    0.016   0.03    0.521   0.35  6:restore
  re86      0.087   0.16   0.08    0.036   0.07    0.659   0.55  1:displace 2:local2 3:displace 4:local2 5:displace
  s5i5       0.57   0.52  0.444    0.289   0.45      1.0   0.88  6:restore
  sb26      0.159   0.27  0.033    0.131   0.23    0.411   0.60  5:displace 6:click
  sc25      0.154   0.26  0.188    0.296   0.46    0.732   0.76  1:local1 2:displace* 3:local1 4:displace 6:restore
  sk48       0.65   0.79  0.658     0.08   0.14    0.835   0.82  1:cycle 2:cycle 3:cycle* 4:displace 6:restore
  sp80       0.99   0.88    1.0     0.99   0.88    0.995   0.85  1:displace* 2:displace* 3:cycle* 4:cycle* 5:displace 6:restore
  su15      0.281   0.44  0.448    0.013   0.03    0.956   0.93  6:click
  tn36      0.727   0.84    0.0    0.727   0.84    0.945   0.97  6:restore
  tr87      0.893   0.94  0.915    0.774   0.87    0.976   0.89  1:cycle 2:cycle* 3:displace* 4:displace*
  tu93        0.8   0.67  0.833      0.8   0.89    0.988   0.93  1:displace 2:cycle* 3:displace* 4:transform
  vc33      0.514   0.68    0.5    0.037   0.07      1.0   0.98  6:restore
  wa30      0.818   0.90  0.828    0.524   0.69    0.948   0.93  1:cycle* 2:cycle* 3:cycle 4:cycle* 5:displace
  MEAN      0.451   0.49  0.429    0.287   0.35    0.793   0.69
```

Gated non-restore action-operators: 53 in 17 games (morning: 14 in 8). Regression: cn04 fell from 0.23 to
0.04 — it has 2-6 presses per movement action, and its earlier gate was on that noise.

## Rhythm, cycle lengths, and the bond in the gate (later still, Sep 3)

Jonathan: "we could recognise cycles and patterns in the movement — a spinning bar's pixels each return to
their origin." Built as `Rhythm` in induce.py: a cell whose colour sequence over the run repeats with period
p for at least two full periods is a rhythm cell; cells sharing a period are one turning thing; its next
value is its value p presses ago, whatever the button, laid over the operator's prediction on the cells the
operator left alone. Cells that ever held a mover's colour are excluded, so a bar the planner walks back and
forth is not "spinning". `cycle_lengths` reads the same return-to-origin off a Cycle operator's table: how
many presses bring a state back to itself.

What the recorded presses contain: almost nothing periodic. Across the 25 games only r11l has a rhythm
object (4 cells, period 37); the collect policy was random and nothing in these games spins on its own —
ls20's patrolling patch moves one step per agent move and a random walk breaks its period. The mechanism is
in place and costs nothing; it will matter on a game with an animation. The cycle lengths are real: tr87's
glyph sequence returns to origin after **7** presses of up or down (`cyc[7]` on both), so the planner can
now reach any of the 7 glyph states from any other in at most 6 presses.

The bond moved into the gate (`Operators.fit`): instead of "exact on every press", every candidate is run
through the action's presses in order with the bond dynamics (start 0.6; +35% of the gap on a hit; x0.6 on a
miss; x0.97 when it abstains), the candidate with the highest trust at the end is the action's operator, and
it may plan while its live bond stays >= 0.5. `Operators.observe` updates the live bond after every real
press; a level change resets every bond to 0.6, forgets the visited places, and forces a refit 8 presses in.

Why it was needed: from ls20's full 120-press prior the exactness gate passed nothing (pickups and refills
break exactness for good); the bond gate passes 2:displace b0.94 and 3:displace b1.00. From the same priors:
sp80 all four (b0.95-0.98), tr87 1 and 2 as cycles (b0.99, b1.00), tu93 three, wa30 four, dc22 four.

Live: ls20 (`play_ls20_bond2.log`) — 90/150 presses by operator, 78 planned, 60 places, operator surprise
0.03 vs the eye's 0.46; operators retired on a miss and were re-gated at the next refit; no level (the
planner has no notion of the key/keyhole/goal relation). sp80 (`play_sp80_bond2.log`) — level 1 at press 117;
after the level change every operator was wrong on the new layout, retired within two presses, and re-gated
at the next refit with b1.00: the bond doing exactly its job, and the reason for the early refit.

## The touch graph — body, objects, and what happens when they meet (`touch.py`, Sep 3, evening)

Jonathan's proposal: the body is the object connected to the controls; a goal has something pointing at it
that is not a wall pointing at a wall; nothing may be called useless for good. Built from the recordings:
BODY = the colours the bond-gated displace operators move, ranked by (buttons, bond sum), with a cycle
operator's anchor as a chain (the selector that chooses what up/down act on). OBJECTS = components of the
non-floor colours in the level's first frame, minus body and register. EDGES = one per press, from the button
through the body to the object it met, typed refusal / pass / state / level / nothing; a button with no body
operator (ACTION5, clicks) points at what is adjacent, else at what lies in the body's row-and-column band,
else at the place itself. LABELS are bonds per type, so a wall stays a wall only while refusals keep coming.

**Check 1 — the body rank** (`touch_check1.txt`). Right in every game I can verify by eye: sp80 colour 9
(the bar), ls20 colours 9+12 (the key block), tr87 colour 0 (the two-bracket selector) with the glyph as its
chain, tu93 colour 9 (the sprite). Plausible in the rest with a body: dc22 (4 buttons, bond 3.9), g50t (4,
3.7), wa30 (4, 4.6), sc25 (4), cn04 (5 buttons), ka59 (4), m0r0 (2), re86 (3). No body, correctly, in the
click games and the non-movers: ar25, ft09, lf52, lp85, r11l, tn36, vc33; and none once a one-button,
low-bond coincidence is refused: bp35, cd82, sb26, sk48, su15. Where the strict version of the rule
("connected to ALL controls") fails is tr87: the selector holds left/right, the glyph under it holds up/down;
the body is a chain, and the rank has to allow that.

**Check 2 — do the things that mattered get a non-wall edge?**
- ls20 (collect): the keyhole `0@31,21` carries the only state edges (2); the yellow is `wall:4` with 35
  refusals and nothing else; the green corridor is pass (52); the goal box `5@9,33` is nothing/refusal — a
  wall until the key matches, exactly the case predicted, and the reason labels are bonds.
- tr87 (collect): every state edge lands on the glyph under the selector (7@51,14: 59; the tile-1 glyph 20-22;
  tile 3: 8; tile 5: 6; tile 4: 3), none on the other tiles, none on walls.
- sp80 (the planner run that cleared level 1): the goal press (ACTION5 at press 65, bar at rows 12-15, cols
  24-43, adjacent to nothing) puts a level edge on the token (`4@1,36`, `6@4,36`) and on both cups
  (`11@52,16`, `11@52,40`) and the floor strip, and on nothing else; the bound has 22 refusals and no
  level edge. The majority label of those objects is still "nothing" (12-29 probe presses each), so the goal
  question is EXISTENCE of a state/level edge, not the majority label; the report now ranks candidates that
  way. What the graph cannot yet do is choose between the token and the cups: one level event, five aligned
  objects. Two more level events would settle it.

Three attribution laws the runs forced: the body is located by the operator's own size-matched locator (the
HUD draws a copy of the key in the key's colours); a button points first at what is inside the body's row
AND column band, then at either (the selector's brackets are two cells from the glyph); and a level press
has no destination, because the screen redraws.

Verdict on the theory: it holds on the data. Body by bond rank is right everywhere it can be checked; the
objects that mattered have a non-refusal edge and the walls do not; the one case it would have mislabelled
(ls20's box) is the case the bonds are for. Ready to be the tie-breaker in `plan_step` in place of
distance-to-anything.

## Resets as checkpoints (Sep 4)

Jonathan: the reset button is almost a death, and deaths were already our checkpoints — so a reset is a manual
memory segment: explore one thing, reset, keep the learning, keep going without the penalty; build the path up
between resets. Is there a limit?

The rules, from docs.arcprize.org (start-or-reset-game-instance, methodology, competition_mode):
- "If at least one ACTION command has been issued since the last level transition, only the current level is
  restarted. If no ACTIONs have been issued, the entire game resets." Levels completed persist. Competition
  mode: "Only Level Resets are permitted, Game Resets are not allowed and become Level Resets."
- Scoring: `level_score = (human_baseline_actions / ai_actions) ^ 2`, capped at 1.15x baseline; game score =
  per-level scores weighted by 1-indexed level number; 100% needs every level. Every action ever spent on a
  level counts (lp85's scorecard: 4 resets, level_actions [81, 1419]). Resets are counted on the scorecard but
  nothing is documented as a limit on them.
- So: a reset costs no life and refills the budget; its only cost is the actions already spent, which a death
  costs too. Reset is the cheaper checkpoint. (ACTION7 is an undo; the project's no-undo law bans it — a
  decision left where it is.)

Built into play.py: a reset is not a press; the level's start frame is the checkpoint; visited places persist
across resets, so `plan_step` walks the known path back to the frontier by itself; the first death teaches
the budget (`life_len`); a reset fires when the planned target is farther than the presses left in this life,
or when nothing new is reachable from here (dead end, after >= 4 presses, no unexplained button to probe).
A level change forgets the budget with the places.

| run | levels | deaths | voluntary resets | places | note |
|---|---|---|---|---|---|
| sp80 (`play_sp80_reset.log`) | 1 at press 57 | 5 | 1 | 51 | lives measured 29, 24, 28, 24, 20 presses — shrinking, so the budget rule fired only at the very end |
| ls20 (`play_ls20_reset.log`) | 0 | 0 | 3 | 48 | all three were dead-end resets; each time the planner replayed out to a new frontier |

What the two runs say: the mechanism works, and on sp80 it changes nothing yet, because a death and a reset
are the same event there (no lives) and the register runs out before the budget rule's estimate. Where it
will pay is ls20-class games with pips, and anywhere a probe wrecks the board: "explore one thing, reset" —
the probe-at-a-candidate then reset rule is the next line, once the touch graph's candidates are in the planner.

## Reset before the death: the register budget and the segment (Sep 4, later)

Jonathan: reset before a death — just recognise when the budget will run out; place the reset where we think
it runs out and feel it out (too far = die and adjust); the route to the solve is laid down one section at a
time, capped by a reset, and until a section reaches the goal we explore. And retire the no-undo law: the
framework learns from failure through the bonds and the touch graph, resets are the harmless way to fail.

Built (`play.py`):
- `Register`: the budget read off the register band the operators already find — fill = cells of the bar's
  colour in the band, drain = median cells lost per press (the colour that loses cells on the most presses;
  refills are jumps and ignored); presses left = fill / drain. Fit from the prior, refit with the operators.
- The segment: a reset fires when the planned target is farther than (budget left − margin), or when the
  budget is down to the margin, or at a dead end. A death before the planned reset means it was placed too
  far: margin += 2. Three clean budget resets in a row: margin −= 1. A level change discards the budget model
  until it is refit on the new level; a budget reset needs the segment to have visibly drained (the first
  version reset after every single press on sp80 level 2, 67 times, because level 1's band read zero there).
- The no-undo law retired in `arc3_client.py`; ACTION7 is used, where a game offers it, to take back a probe
  that changed the board without a level. No public game offers it (available_actions never lists 7).

| run | budget read | segments (r = planned reset, d = death) | levels |
|---|---|---|---|
| ls20 (`play_ls20_segments.log`) | colour 11, 2 cells/press, 42 presses at start | 20r 5r 39r 40r 40r — zero deaths | 0 |
| sp80 (`play_sp80_segments2.log`) | colour 14, 2 cells/press, 32 presses | 28r 28r, then level 1 at press 61; level 2: 28d 20d 20r, margin 2 → 4 → 6 | 1 |

ls20 is the clean case: the register says 42, each segment runs 39-40 presses and resets with 2 to spare,
and the run never dies. sp80 level 1 the same (28-press segments on a 32-press register, then the level).
sp80 level 2 is the feel-out: the model, fitted on level 1, said 12 and 18 presses were left when the run
died, so the margin grew to 6 and the third segment ended in a planned reset. The remaining gap is that the
register band and drain are per level (level 2 drains faster than the model says); the margin absorbs it for
now, and a per-level refit of the band is the next fix.

## The experiment loop, the per-level register, and the sleep (Sep 4, evening)

Jonathan: do the per-level register refit and the experiment loop; and the reset and undo buttons should
trigger our sleep cycles — there is strategic use in them that way.

Built (`play.py`, `touch.py`):
- **The sleep.** A reset, a death, and the periodic refit all call one function: refit the operators, re-read
  THIS level's register from its own presses (band = ambient | tick of the level's presses), rebuild the touch
  graph on the level's presses with the live operators, re-rank the candidates. Consolidation happens at the
  checkpoint boundary, which is where the planet's own sleeps happen.
- **The experiment loop.** `touch.candidates`: things pointed at by a state or level edge first, then things
  never touched (smallest first), never walls, bounds, register, or body. An experiment plans ONE path to the
  candidate with `plan_to` (breadth-first over the trusted operators, depth 40, up to 2,500 states) to
  adjacency, or failing that to alignment in the body's row/column band (sp80's bar can never touch the token;
  the act button works on the column); follows the path; re-plans only when the world deviates from the
  operators' prediction. At contact it presses each unexplained button once, then bumps into the object once.
  A level ends it; a changed board is recorded and the run moves on; nothing means reset and the next candidate.
- The body is located by the MOST TRUSTED displace operator (the first version took the first one in the dict,
  ACTION1's at bond 0.05, and declared everything unreachable).

| run | experiments (candidate -> result, presses) | segments | levels |
|---|---|---|---|
| sp80 (`play_sp80_exp2.log`) | level 1: token and cups unreachable (0); level 2: 4@60,40 changed (2), 6@56,40 changed (10), 8@16,8 unreachable, 11@4,44 changed (26) | 28r 41d 27d 20d 24d | 1 |
| ls20 (`play_ls20_exp2.log`) | keyhole 0@31,21 changed (4), goal box 5@9,33 unreachable, HUD 5@60,12 / 5@63,12 changed (2), corridor 3@8,14 changed (3) | 41r 40r 41r, zero deaths | 0 |

What it says. The loop does what was asked: on ls20 the keyhole is the first candidate and touching it
changes the board (the HUD glyph turns); on sp80 level 2 three of four candidates were reached along planned
paths and touched. Two honest limits: (1) "unreachable" is often "not with the operators I trust yet" — ls20's
right move (action 4) has not gated, so the box is out of reach and the keyhole was reached by alignment
rather than adjacency; (2) sp80 level 2's budget is still misread (drain 1/press, deaths at 20-41 presses
while the model said 6-36 left) — level 2 has a register or a cost the level-1 reading does not, and the
margin climbed to 10 covering for it. The next fix is a budget model that learns from the deaths directly
(fit drain to the presses-to-death), not only from the bar.

## The budget learns from the deaths; the route; the markers — and ls20 level 1 by the general agent (Sep 4, night)

Jonathan: the budget model should learn from the deaths; the focus shifts from exploration to goal-driven as
the route grows, until the reset can be placed past the goal; the undo is a cheap checkpoint and a sleep,
so a planned path has an estimated length ending in a reset, with markers along it where we naturally want
to sleep, and a known part and an unknown part.

Built (`play.py`):
- `Register.remaining(f, since, deaths)`: from the bar, fill / drain; from the deaths, each death gives
  fill-at-segment-start / presses-to-death, a drain the bar may not show; the stricter wins. With no
  readable bar the deaths alone give the life length. Deaths are per level. The margin widens only when the
  model was wrong by more than the margin.
- The route: at every sleep, if an experiment has a path, log the known presses to the candidate against the
  budget: "goal-driven: the reset sits past the goal" when the path fits inside budget − margin, else
  "exploring: the reset falls before the goal".
- The marker: a surprise above 0.5 in the unknown part triggers a sleep (at most one per 8 presses); where a
  game offers ACTION7 the probe that caused it is undone first. No public game offers ACTION7.

| run | what happened | segments | levels |
|---|---|---|---|
| ls20 (`play_ls20_deaths.log`) | keyhole experiment first (changed), 13 experiments, 3 planned resets, zero deaths; **level 1 at press 115** — the first ls20 level cleared by the general agent rather than the hand-written chain | 41r 38r 19r | **1** |
| sp80 (`play_sp80_deaths.log`) | first death at 23 presses raised the drain from the bar's 2.0 to 2.78 cells/press; level 1 at press 41; on level 2 deaths at 45, 23, 20 drove the death-drain to 3.2 and the margin to 8 | 23d 8r 45d 23d 20d | 1 |

What it says. The death-learning does what was asked: the bar under-reads sp80's cost and the deaths correct
it within one life. sp80 level 2 is still not converged (the model said 13 were left at the last death):
its cost per press seems to vary, so a single drain is not the right shape there — the next model is a per-
segment cost fitted to the deaths' fill-vs-presses curve. ls20's level came from the loop as designed: the
keyhole was the first candidate, the touch changed the board (the key turned), and the planned resets kept the
run alive on a budget of 42 with no deaths at all.

Where the strategy sits now. Exploration and goal-driven are not two modes but one loop with a threshold:
while no candidate's path fits inside the budget, the reset falls before the goal and the run explores
(the boss-fight pattern: probe every button in every new place, keep what surprised); once a path fits, the
reset sits past the goal and the run walks the known part, experiments at the end of it, and sleeps at the
markers. The erdos search discipline — verify at the seam, steal work under pressure — is the bond and the
replan-on-deviation; the neurofungus is the surprise marker, growth where the surprise is.

## The daily switched to the general agent; the chain is the oracle (Sep 4)

`arc_daily.py` now runs play.py (150 presses) as the live try and, for ls20, runs `ls20_chain.py` after it
as the oracle: expected 5/7, recorded on its own line, flagged REGRESSED if lower, never the daily's score.
First run: play.py 0 levels in 150 presses, 6 planned resets, 0 deaths, keyhole experiment first; oracle
5/7 ok. The earlier run today cleared level 1 at press 115, so the daily will now show the general agent's
real run-to-run variance instead of a replayed script. The practice step still runs the mock maze and still
measures nothing relevant; replacing it with the offline induction batch (deterministic, no API) is the next
change to the ritual.

## The practice step is the offline induction batch (Sep 4)

`arc_daily.py`'s practice no longer plays the mock maze. It runs `induce.py` over the 25 recorded public games
(deterministic, no API, about 40 s) and scores itself on the number of action-operators that pass the gate —
the vocabulary the live agent plays with — with the mean held-out accuracies alongside. The baseline is the
best earlier run of the same practice (mock wins and operator counts are never compared), and REGRESSED
means 5 or more gated operators lost. First row: 53 gated operators in 17 of 25 games, best 0.451 /
gated 0.287, first-baseline. The ritual is now: world model regression (offline) -> general agent live ->
chain as oracle.

## Auto presses: the shape decides (Sep 4, late)

Jonathan: not a flat 150 — the steps should be the lines it takes to go around the model; fully explore
what we have, then switch method; the shape is different per game; the goal is closure on a slice inside the
model space; going around the circle means we have tried all our capabilities, so we have to grow, and
surprises find the gaps we follow.

Measured first, from the priors alone (`closure`: every state the trusted operators reach, cap 3000):

| game | trusted buttons | closure | radius | budget/segment | segments to wrap |
|---|---|---|---|---|---|
| sp80 | 1 2 3 4 | 139 | 16 | 32 | 4.3 |
| ls20 | 2 3 | 4 | 3 | 42 | 0.1 |
| tr87 | 1 2 | 7 | 4 | 64 | 0.1 |
| tu93 | 2 3 4 | 5 | 3 | 64 | 0.1 |
| wa30 | 1 2 3 4 | 888 | 20 | 64 | 13.9 |

So the "model size" is the number of trusted buttons as much as the game: ls20, tr87 and tu93 start with
two or three, and their circles are tiny until the run gates more — which is also why the experiment loop
kept saying "unreachable".

Built (`play.py --presses auto`, and the daily now uses it): at every sleep the closure is measured from the
current frame — size, radius, slice covered (visited ∩ closure), segments to wrap (size / budget), growth
since the last sleep — and logged as the SHAPE. The run stops when the slice covers the circle (>= 95%),
every button the level offers is trusted, the circle has not grown across two sleeps, a full segment has
been played and no candidate is waiting ("switch method"); or at three times the human baseline for the
level. The baselines come from the closed scorecard (`level_baseline_actions`) and are saved per game in
`D:\planet\eyeaselines.json`: sp80 [39, 58, 25, 148, 96, 152], wa30 [71, 119, 183, 98, 368, 68, 79,
442, 415]. The first version stopped after 20 presses because one trusted button gives a one-state circle;
"nothing left to try" now requires the maturity above.

| run | the shape over the run | stop | levels |
|---|---|---|---|
| sp80 (`play_sp80_auto2.log`) | level 1 in the first 40; level 2: circle 96 states, slice 5% -> 62%, collapsing to 9 whenever a vertical bond broke and back to 96 at the next sleep | 174 presses on level 2 = 3x baseline 58 | 1 |
| wa30 (`play_wa30_auto2.log`) | circle 26 states, slice drawn out 10% -> 100% by press ~140 — every capability tried — then a button gated and the circle jumped to 2264, then 3000+, slice 1-3% | 213 presses on level 1 = 3x baseline 71 | 0 |

What it says. The shape is different per game and it is the right thing to watch: sp80's slice grows
steadily inside a fixed circle; wa30's slice completed its circle and the circle then grew by two orders
of magnitude, which is the moment the run has tried all it had and must grow — and it did, because a new
button gated (a surprise that became an operator). The 3x-baseline cap then ended wa30 with 3% of a
3000+ circle covered: a circle that large cannot be wrapped, and that is the signal for the other method
(relations, not travel). One artefact to fix next: the circle collapses to a handful of states whenever a
bond dips below 0.5 for a sleep, so the shape should be measured with the operators that were EVER gated on
this level, not only those trusted at this instant.

## The ring: the shape with every operator ever gated, the search where the slice ends, refills as subgoals (Sep 4, night)

Jonathan: measure the shape with every operator ever gated on the level; when going round returns nothing,
search at that intersection and start a new circle where the slice ends; that is how subgoals like a refill
form; a surprise is a hole in the wall, and the ring is made bigger rather than the goal pulled in; we are
not using all of the whole, so the parts that could match must be added.

Built (`play.py`):
- The circle is now every state EVER reachable on the level (the union of the closures measured at each
  sleep, with every operator ever gated), so a bond dipping for one sleep no longer collapses it.
- Operators are fit PER LEVEL: the prior counts only on level 1; a later level is fit from its own presses.
  Fitting on both levels at once gated nothing (the bounds contradict), which was the real cause of the
  swinging circles — not the bonds.
- THE RING: the closure's gap states — where a trusted operator refused or abstained (walls, first), or where a
  button the level offers has no operator (open). When the slice covers the circle, the circle has stopped
  growing across two sleeps, a full segment has been played and nothing points anywhere, the run enters the
  ring search: travel to each gap state and press only what the model cannot answer there (the unexplained
  buttons, and the trusted buttons that refuse at that state). A HOLE is a change the operators did not
  predict; holes found on the ring start a new circle from there; a ring with no hole is "switch method".
- REFILLS as subgoals: a press after which the register jumps up is remembered by place; when the path to a
  goal candidate is longer than the budget, the run detours to a refill first if that is shorter than the
  budget — the ring made bigger rather than the goal pulled in.

| run (auto) | the shape | levels |
|---|---|---|
| sp80 (`play_sp80_ring3.log`) | level 1 in the first segment (28 presses); level 2 is an 894-state circle (level 1 was ~108), slice 2% -> 9% over 174 presses, ring 108 gap states, never covered; stopped at 3x baseline 58 | 1 |
| wa30 (`play_wa30_ring3.log`) | a 21-state circle, then 47, drawn out to 100% by press ~150 — then the circle grew to 720 (a new region opened), then ACTION5 gated and it grew past 7,000; slice 2%; stopped at 3x baseline 71 | 0 |

What it says. The shape is now honest and stable, and it is different per game exactly as predicted: sp80's
level 2 is a much larger space than its level 1, and wa30 grows in steps as buttons gate. The ring search
did not get to fire in either run, because the circle kept growing (wa30) or the cap ended the run first
(sp80 level 2). The first ring run before these fixes did fire and exposed the hole definition (an ordinary
move at a gap state was counted as a hole); holes are now unpredicted changes only.

Where the "whole" comes in. What the run adds when the ring returns nothing is, in order: the unexplained
buttons at the gap states (built); the operators that were BEST but not gated (the next candidate kind, not
yet wired); the eye's own predictions as hypotheses; and the June relation inducers — the parts of the whole
that could match. The ring is the place all of them are tried, because it is where the current model has
literally nothing to say.

## Hypotheses on the ring: the best-but-not-gated operators, on trial (Sep 4, late night)

Jonathan: wire the best-but-not-gated operators into the ring search.

Built (`induce.py`, `play.py`): every action that fails the gate keeps its best-scoring usable candidate as a
HYPOTHESIS with a trial bond (start 0.3, +35% of the gap when its prediction holds, x0.6 when it breaks).
Any press of an unexplained button is a trial of its hypothesis — on the ring the buttons with a hypothesis
are pressed first — and at 0.5 the hypothesis is PROMOTED into the operators, so the circle grows. A
promoted operator is earned by trial, not by the history gate: it survives refits while its live bond
holds (the first version re-promoted sp80's ACTION5 six times, once per refit, because every refit rebuilt
the operators from the history gate alone).

sp80 (`play_sp80_hyp2.log`): level 1 at press 89; on level 2 the hypotheses for ACTION1/2 (local rules)
broke at once, the ACTION5 hypothesis (local1: "this button does nothing here") held and was promoted at
press 169, stayed promoted through the following sleeps at bond 0.62-0.70, and the level-2 circle was drawn
out from 17% to 57% of 159 states over 12 planned resets and 2 deaths, 216 of 263 presses planned.
wa30: no hypotheses arose, because all five buttons gated on their own; its circle grew 642 -> 914.

What it says. The mechanism does what was asked, and it also shows what a hypothesis is worth: on sp80 the
promoted ACTION5 operator says "does nothing" everywhere it was tried — true, and useless for the level,
because the one place it acts (the bar under the token) is the place the run has not stood in yet. So a
promoted "nothing" operator must not silence the ring: the ring still presses trusted buttons whose operator
predicts no change at that state (the wall test), which keeps ACTION5 in play at every new place. The next
parts of the whole to put on trial, in order: the eye's own prediction as a hypothesis for an unexplained
button (it scored 0.99 on sp80), and the June relation inducers for the glyph-matching games.

## The pin registry, and the rides it uncovered (Sep 5)

Jonathan: the pins are empty containers asking "what is this?" — the rings held context and purpose, the
sideways ring holds feel, the pins hold what controls what; the pins are the hypothesis about what
everything is, so we always want something more than nothing for every control. Lineage: SPARSE_VESICA
§39b "an idle basis term is an empty slot awaiting its C", §27 "actively move the empty containers to an
attractor", FOLDING Part XXXIX (the rings as lenses), the Sep 2 note "the real stuff on the normal axis".

Built (`pins.py`, wired into play.py, touch.py, induce.py), four rules:
1. A pin per control x thing from the level's first frame, state EMPTY; emptiness is counted.
2. "Does nothing" fills a pin only with a place attached (NOTHING HERE), never globally; in the hypothesis
   gate a fulfilled prediction of "no change" is no longer evidence, so a "nothing" can never be promoted.
3. Attention goes to the emptiest control: the probe picks the control whose pins are most empty (every
   2nd new place when over half empty, else every 4th), and the ring presses the emptiest control first.
4. The fraction of pins answered is logged with the shape at every sleep and saved with the run.
Candidates come from the pins: things with a state/level pin first, then things with empty pins (most
empty first), then nothing-here-only; walls last. Touch edges now carry the place they happened at.

| run | pins |
|---|---|
| sp80 (`play_sp80_pins.log`) | level 2: 40 pins (5 controls x 8 things), 10% answered, 25 empty, 11 nothing-here; emptiest control 3 (100%), then 4 (88%) |
| ls20 (`play_ls20_pins2.log`) | 32 pins (4 x 8), 19% answered, 26 empty; emptiest 2/3/4 (88%) |

What the pins showed at once: on ls20 the pins of the keyhole, the rings and the box stayed EMPTY under every
control, because the body could not reach them — and the reason was a missing law, not a missing search.
The right move never gated on ls20. Diagnosis (`play_ls20_rides.log` and offline): a "right" press moved
the key up or down 9 times in 44, and once by 20 or 25 cells — the FAN CELLS, the rides prioragent's
wind-learning and the chain's fan map already knew. Built into the displace operator as RIDES: every press
that did not take the usual step is either the wrap (one long jump the other way along the axis, at the
row's end) or a ride keyed by the place it happened at. Result: in the live run all four ls20 buttons
gated and the closure from the start went from 4 states to 69; the batch's gated accuracy rose 0.287 ->
0.300 and wa30's best to 0.818.

Two more laws the runs forced: the run's record now carries voluntary resets (one frame, no press), because
the offline reconstruction drifted a frame per reset and read "down" as "up"; and the auto cap is three
times the baseline but never under 150 presses — three times a 22-press level gave ls20 66 presses to learn
a seven-level game. An experiment that reaches its thing with no button to press there (all trusted, no
bump possible) is now "untestable", not "nothing", and spends no reset.

Honest state: ls20's pins on the keyhole, rings and box are still empty after 150 presses, because 69 of
about 144 lattice positions are reachable with the rides learned so far and the keyhole is not among them
by adjacency. The next lever is not the pins but the rides: the chain's fan map has every one of them, and
a run that learns them all is a run whose closure covers the level.

## Lines: pins that connect pixels, and the chain's fan map as the oracle (Sep 5)

Jonathan: learn the rides from the chain's fan map; and the pins can connect different pixels — a fan has a
line that crosses the floor until the wall; pressing a control runs its lines to the body, the body moves and
touches the pins already there; a fan draws a sideways line, and the pixel with the fan on it leaves that
path on its pin.

Built (`lines.py`, wired into play.py's sleep): every ride a displace operator learned (the body at place p
was carried by w) becomes a LINE owned by the object beside p — from p, in w's direction, to the landing.
Lines generalise: every object of the same colour and orientation gets the same kind of line from its open
side, cast across the floor by the lattice quantum until the first non-floor cell. The generalised lines are
seeded back into every movement operator as rides, so the closure includes fans never ridden. The chain's
`fan_cells` is the oracle: precision and recall of the learned fan cells against it, at every sleep. Lines
are saved per game (`lines_<game>.json`) for the map.

What the oracle said on ls20 level 1 (`play_ls20_lines.log`): the chain finds NO fans on level 1 (its fans
are on levels 3-5), and the single "ride" the operators had learned — a 25-row jump at (20,34) — was
therefore not a fan: it is the respawn when the bar empties (the chain's own note: "bar-empty consumes a pip
AND respawns the agent"). Precision 0, correctly. The earlier count of nine rides on the right move was
the offline reconstruction's reset drift, not the game. So on level 1 rides are not the missing law, and
all four buttons gate without them; the 69-state closure with the slice at 51% is level 1's reachable
region as the operators know it.

What is actually missing on ls20 level 1 is the second kind of line, the one the keyhole draws: a bump into
the keyhole turns the HUD glyph (a state edge from the keyhole to a region across the screen), and the box
accepts the key only when the glyph matches. The experiment loop bumps each thing once; it cannot yet
"enter the keyhole until the glyph matches, then push into the box". That is a line from one object to
another (keyhole -> HUD glyph, box <- HUD glyph), learned from state edges the touch graph already records as
"the thing that changed", and it is the relation layer the June work called relations.ts. Next.

## The relation layer — ls20 level 1 solved by discovery (Sep 5)

Jonathan: build the relation layer. Built (`relations.py`, wired into play.py):
- region(A): the union box of what changed, away from body and register, on the presses that touched A with
  a state edge (touch.build's edges now carry their press index).
- pattern(box): the rarest colour's shape inside a box, cropped and shrunk while its blocks are uniform (the
  chain's shrink) — a small binary shape. cycle(A): the region's patterns after each touch of A.
- target: an object whose inner pattern equals one of the region's reachable states up to D4; matched_now
  when the region's pattern equals it exactly. The relation is source -> region -> target.
- The loop: touch the source until the region matches, then go to the target and bump. A relation with a
  target outranks the ring search (goal-driven beats going round) and earns the level 100 more presses.

What it took to make the loop run, each a law the runs forced:
1. The ring fires on STAGNATION (three sleeps at the same coverage), not only at 95% — going round returning
   nothing is the signal, whatever the number. With it the ring fired at press 80, ACTION1 into the keyhole
   changed 58 and 60 cells unpredicted, the closure grew 69 -> 138 -> 207, and the relation was read off the
   edges: "0@31,21 -> region rows 55-60 cols 3-8 (the HUD glyph) -> 5@9,33 (the goal box), D4 1 away".
2. A move with a side effect elsewhere is still a move: explain the mover on a window around the largest
   changed piece and leave the rest to the relation layer. Without it the floor never learned the keyhole's
   colours (0 and 1; the chain's PASS set) and the keyhole stayed a wall in the model.
3. Adjacency means "a move from here lands on it": a keyhole is a floor feature the key drives onto, never
   one cell away on a 5-lattice. Until then every keyhole experiment was "untestable".
4. Protected travel: after the match, the route to the target treats the source (dilated) as lava — the
   chain's "once matched, treat rotators as lava"; before it the planner walked back through the keyhole and
   un-matched the glyph on the way to the box.
5. A bump per side (the box accepts the key from one side only), and a productive bump is REPEATED: the
   insert takes three pushes (the chain's "ACTION1 x3"). The first version bumped once and concluded.
6. Mundane but decisive: the relations list was assigned inside the sleep without `nonlocal` and the loop
   saw an empty list for a whole run.

Result (`play_ls20_rel8.log`): **ls20 level 1 at press 155 — "experiment 5@9,33: LEVEL"**. The general
agent found the keyhole, learned that touching it turns the HUD glyph, learned that the box's inner pattern
is a state the glyph can reach, turned the glyph until it matched, walked to the box without crossing the
keyhole, and pushed in three times. Nothing about ls20 was written into it. The chain does the same level
in 13 presses; this run spent 155, most of them on the ring and on learning the five laws above in place.
Level 2 then ran to the 600-press hard cap without a level: its budget is 4 cells/press and its rings
(refills) and rotators are the next relations to find.

## The water map and the antennas (Sep 5)

Jonathan: extend the pins into depth — thin straight lines in front of the screen, and behind it the colours
piling up from earlier like water, with a faint pin things can anchor to; press a hand against all the pins
and see which fall back and which stay out; the water leaves a small hypothesis antenna poking out, and we
try to fill it.

Built (play.py, flow.py):
- THE WATER: per level, per cell, the change that nothing in front predicted — the trusted operator when
  there is one, else the hypothesis on trial; the register subtracted, the body's own move credited to its
  operator. Saved per level (`water_<game>_L<n>.npy`).
- THE SWEEP, at every sleep: the fraction of the level's changed cells explained in front versus only known
  behind, and the water total.
- THE ANTENNA of a thing: the water within two cells of it, weighted by how empty its pins are (0.5 + the
  empty fraction). Measured over every thing on the level; the experiments rank by tier (pointed-at first)
  and then by antenna. The top antennas are logged and saved.
- The map draws the water as a blue wash behind the screen and the antennas as spikes on the things.

| run | sweep | antennas |
|---|---|---|
| ls20 level 1 (`play_ls20_water3.log`) | 89-97% explained in front; level 1 at press 155 again | early: the keyhole (25, pins 75% empty) and the corridor; late: the HUD glyph objects |
| ls20 level 2 | 95% explained in front over 404 presses (3x baseline 123), no level | 5@39,13 (98), the HUD glyphs, and the two REFILL RINGS 11@51,40 (35) and 11@16,15 (28), pins 50-75% empty |
| sp80 level 2 (`play_sp80_water3.log`) | 62-70% explained in front, water 3410, no level | the two colour-8 PLATFORMS: 8@24,28 (345) and 8@16,8 (292) |

What it says. The antennas point at the mechanics each level introduced and nothing in front explains yet:
ls20 level 2's refill rings and sp80 level 2's platforms. That is the picture working as described — the
water finds the spike, and the spike is where the next hypothesis is due. The sweep also gives each level a
single honest number: ls20 is 95% in front (its remaining 5% is the rings and the glyph), sp80 level 2 is
only two-thirds in front, so it is the game where the eye still knows more than the lines.

Two laws the runs forced: the stop rule reads only the current level's shape (it fired the press after a
level change, on the old level's stagnation), and the antennas are measured over all things, not only the
current candidates (sp80's platforms were never candidates and so never showed).

## The water as a void line; the residue credited to its cause (Sep 5)

Jonathan: attribute the water to the thing that caused it; and the line in the water is a void line — what
cancels to 0 and is defined only by the pairs around it — while the line in front is a real line; that is why
it was imagined dark: it is supposed to go to 0 along a line.

That reading is exact for how the water is computed. Each cell's water is observation minus prediction: the
pair cancels where the front explains, and leaves a residue where it does not. The line behind the screen has
no content of its own; it is defined by the pairs around it, and the run's work is to drive it to zero along
its length. A pin whose water has gone to zero is a closed void line; an antenna is one the pairs have not
closed. Dark is the right colour for a place that is defined but empty.

Built: the residue of each press (its unexplained mass) is credited to the thing the body ACTED ON that
press — the touch edge's object, excluding 'pass' edges (a pass names the floor the body walked over, never a
cause), shared when a press names several things — instead of to the cells it landed on. The antenna is
cause first, the nearby cell water as a tie-breaker, weighted by the pins' emptiness; a thing whose pins are
all 'pass' is floor and has no antenna.

| level | antennas by cause |
|---|---|
| ls20 level 2 (`play_ls20_cause.log`) | the keyhole 0@46,51 (caused 58), the refill rings 11@51,40 (50) and 11@16,15 (50), 5@39,13 (50); the corridor is gone from the top |
| ls20 level 1 | the keyhole and the corridor tied by cause (98 each: the key entering the keyhole overlaps both) until floor-class things were excluded; the box and the HUD glyph at 0 cause once explained |

Final run (`play_ls20_cause5.log`): level 1 cleared again (298 presses in all, level 2 to its cap). Level-1
antennas by cause: the corridor 3@8,14 and the keyhole 0@31,21 credited EQUALLY (86 each — the key entering
the keyhole overlaps both, and the corridor carries state pins from that shared credit, so it is not floor by
the pass rule), the HUD glyph 5@53,1 and the box 5@9,33 at 0 cause once explained. Two runs in between did
not finish level 1: one for want of presses under the cap, one from a crash where the repeat-bump chose a
press and then fell through into the travel branch, which cleared the experiment in the same iteration —
fixed by skipping travel once a press is chosen. The level-2 antennas are the useful result: the rings are the refill subgoal the planner
already knows how to use, and the keyhole is the relation's source; the water names them without help.

## The floor flow field: middle pins, border pins, the colour rule, the openings (Sep 5)

Jonathan: the floor develops its own flow area. Each pixel of floor has a pin that gets laid down pointing
in the directions you are allowed to go; moving the body over it knocks it over, and that starts a trail —
the hallway is connected to the goal because those flow lines developed. There is a fence on the pixel
border too: moving onto the pixel bends its middle pin, leaving bends the border pin, but a wall breaks the
border pin. The middle pins reach to the border and the border pins reach to the next middle: a way to
double-verify where you can go. Against a bottom wall, left, right and up leave their pins and down does not,
so far away, with the same floor and wall colours, it won't bend that way either.

Built (`fence.py`, wired into `play.py`, `induce.py`, `flow.py`):

- `mid[k,y,x]`: the middle pin of a cell, laid (+1) when the body passed over the cell going k. A 5-cell
  step lays pins on every cell it sweeps.
- `border[k,y,x]`: the fence between a cell and its neighbour in direction k — bent (+1) when the body
  crossed it, broken (-1) when a press in that direction was refused. The wall is the first cell ahead within
  the step whose colour is not the floor the body walks on; if every cell ahead looks like floor, the border
  right at the leading edge breaks (an unseen wall — what `Displace.blocked` recorded per position before).
- `rule[(near colour, far colour, k)] = [passes, blocks]`: the generalisation. Compiled onto the level's
  ground (the start frame with the body painted floor) it predicts every untouched border with the same
  colours; a bent or broken border keeps its own answer. A rule seen BOTH ways (the keyhole: blocked until
  the region matched, then passed) is left unknown — something else decides there, and the planner must
  not be walled off from the box by the fence.
- `Displace._step` asks the fence before stepping: a broken or predicted-broken border on the way refuses
  the move. The closure and the planner inherit that.
- THE OPENINGS: a middle pin laid toward a border that is neither bent nor broken nor predicted broken is
  where the chain mid -> border -> mid stops. They become experiment goals after the pin candidates and
  before the ring search; the bump through one either lays new pins (the trail goes on) or breaks the border
  (the rule learns), with no reset either way. Openings whose far colour already blocks in some other
  direction rank last: one bump there verifies the rule for this direction.
- The map draws the pins as white ticks along the trail, broken borders red, the rule's far-away
  predictions dark red, openings cyan.

Offline, on the recorded final run of ls20 level 1 (152 presses): 2225 pins laid, 1470 borders bent, 60
broken; from those the rule predicts 203 untouched borders blocked (3>4 left/up/right); the fence
contradicts none of the 152 recorded moves; the closure is unchanged (no unseen walls on ls20 — the floor
colours already refuse). What it exposed: nobody ever bumped DOWN into the wall colour, so the rule is
honestly silent on down and the bottoms of the vertical corridors are openings — one bump answers all of
them. And the corridor going right at rows 45-49 past column 43, never walked, is the first real opening.

Live (`play_ls20_fence1.log`, then `play_ls20_fence.log`): the first run walked the openings in order —
open@25,23 left, open@45,39 right, open@25,18 left, open@40,43 left all PASSED (the trail went on), then
open@24,44 up, open@50,39 down, open@40,14 down, open@50,19 down all broke the border, and the rule went
from "3>4 left" to "3>4 left, down, up" (200 borders predicted blocked, the openings from 65 down to 15).
Then the relation matched and the box was UNREACHABLE: the bump into the box at press 55, before the
relation opened it, had broken that border, and the fence — rebuilt from the level's presses at every sleep
— re-learned the block each time. Fixed: a relation's matched target exempts its borders from the fence
(carried across rebuilds); the fence never blocks what another layer answers for. Second run: level 1
cleared at press 173 ("the region MATCHES 5@9,33 — going to it (the fence lets its borders go)"); level 1's
fence at the end: 1950 pins laid, 1450 borders bent, 70 broken, 177 borders predicted blocked, 15 openings
left; the one rule seen both ways, 3>5 up (15 passes, 15 blocks), correctly left unknown. Level 2 ran to its
cap (369 presses) with the openings queued behind the pin candidates, which never emptied — the ordering
(pins, then openings, then the ring) is a choice, not a finding.

### The openings ahead of the untouched things; the sides drag the pins down; the circuit (Sep 5, later)

Jonathan: put the openings ahead of the untouched things — it is like connecting a circuit; and if the border
pin is against a wall, sliding along the wall drags it down too: we want ALL the pins laid down to make a map.

Built: goals are now the things whose pins already hold a state or a level, then the openings, then the
never-touched things, then the ring. As the body slides, its flanks brush the side borders of every swept
cell; a brushed border the rule calls a wall is a pin DRAGGED DOWN along the wall (laid, part of the map); a
brushed border onto floor nobody walked, not predicted a wall, is a SIDE OPENING — a branch the trail passed
without turning. The circuit is the share of the walked floor's borders with an answer (bent, broken,
dragged, or predicted); 100% is closed: no open terminal on the trail.

What the runs taught, in order (`play_ls20_fence3..5.log`):

- Run 3 walked 26 openings (20 passed, 6 broke), the circuit read 86-98%, and missed the level: the
  relation matched right after `up` was retired by three keyhole touches in a row (each a "miss" for the
  displace operator, x0.6 each), so the box was unreachable, and the match was re-made every press.
- Fixes: the fence is lifted while an operator is judged (the walls are the fence's account, not the
  operator's); a relation-source touch — a press MEANT to change the body — is not a miss; a fence prediction
  holds only while the far cell still has the colour it was learned on (a door, a state); the cap's +100 stays
  once a relation has been found on the level; an unreachable matched target parks the relation until the next
  sleep instead of re-matching every press.
- Run 4 closed the circuit to 100% at press ~200 and still missed: `left` and `right` lost the GATE at the
  refit — 52 of 55 left presses exact, the three exceptions the keyhole touches, and three consecutive misses
  in the bond simulation retire any operator. Fix in `Operators.fit`: an operator exact on >= 90% of at least
  ten presses is a law; its exceptions belong to another layer and do not cost it the gate.
- Run 5: level 1 at press 96 — the best yet (135, 155, 173 before). The first three presses of the level were
  openings around the box (three walls, and the rule 3>5 left from them), then the relation source, then the
  trail down the right side; the relation matched at press 91. Level 1's fence: 1675 pins laid, 1020 borders
  bent, 40 broken, 71 dragged down along walls, circuit 96.5% closed. On level 2 the circuit closed to 100%
  (2800 pins, 269 dragged, the rule blocking 3>4 in all four directions) with all four operators at bond 1.00,
  and the level still ran to its cap: a closed circuit is the map of where the body can go, not yet of what
  the rings and rotators do — those are the next relations.

## The ring and the rotator: level 2's relations, and the sheet of pins on the border (Sep 5, evening)

Jonathan: build the ring and rotator relations for level 2. And the border has a lot of pins, enough to match
each colour and direction and object, so it looks like a wall or sheet; when we bump into a wall, the pin
matching those colours and direction breaks off and lays down inside the wall pixel, and that is how the walls
connect inside; the pin with the same colours but a different direction stays attached to slide along; the
broken pins fall in enough to be disconnected from the floor pixels.

The sheet of pins is what `fence.rule` already is: one pin per (near colour, far colour, direction) on every
border; a bump breaks exactly that pin and the others stay attached — 3>4 left breaks on one bump while 3>4 up
still lets the body slide along that wall. Built to the letter of the rest: the broken pin now FALLS INTO THE
WALL PIXEL (`fence.fallen`: the far cell of every broken or trail-facing predicted border, never a trail cell)
and where fallen pins touch they connect into WALL PIECES (23 on ls20 level 1 from 170 fallen pins) — the wall
grows an inside of its own, disconnected from the floor's circuit. Drawn as short grey pins inside the wall.

THE ROTATOR is the keyhole (0@46,51): the relation learned on level 1 (source colour, HUD region, the patterns
its touches cycle through, target colour) is CARRIED to the next level by colour (`relations.carry`), so the
loop starts on level 2 without touching anything first. What it took to make it real:

- the level-2 HUD is read in the same colour as on level 1 — on level 1 the key's 9s were the rarer colour
  inside the region, on level 2 the 5 gaps were, and the region came out as the box's negative; the relation
  now remembers its colour (9) and reads with it; the HUD that holds the region is never its own target;
- the level-1 walls, bounds and rides are cleared from the operators at a level change; the last level's
  register band stays until the new level shows its own (eight presses into level 2 no cell was ambient yet,
  the bar's drain fell inside the mask and 'up' was retired for not predicting it);
- a reset re-plans the experiment's route (it used to keep an empty path and drift for 300 presses);
- relation touches are kept out of the operator refit (they are the relation's presses, not the operators');
  a law's bond is its accuracy, so 52-of-55 outranks a Cycle that memorised 43 states.

THE RING (`rings.py`): a thing of the register's own colour standing on the floor is a ring by hypothesis
before any refill is seen, and learned from the refills after (colour 11, the bar refills to full). The ring
is floor to the move (the operators' floor rule never saw the pass — a refill press is not a plain shift), and
the planner takes it as a DETOUR when the goal plus the presses needed at it exceed the budget: the ring that
serves the goal is the one nearest it (walk to the goal first when a ring near it is still affordable after
the walk; the rings elsewhere are kept for the trip after), and only a ring the bar still reaches counts, the
ring's own refill being the margin on the press that lands on it.

Two facts of level 2 measured on the way (`play_ls20_rings*.log`): the HUD state does NOT survive a reset
(so every touch must happen in one life), and a REFUSED press does not drain the bar at all (24 refusals at 0,
every move -4): bumps are free, moves are the budget.

Runs 1-14 of the level-2 loop, in order: the keyhole touched once per life for 25 lives (the route bug); the
carried relation matched the HUD's negative; the ring unreachable in the model (not floor); three touches in
one life but no match (the colour); the match at press 154 with both rings spent on the way (order); the
detour one press short of the ring, twice (a strict less-than); the match every life with the near ring's
refill (run 14: matched at 144, 214, 264, 314, 364), and the box 20 presses away with 12 left and the far
ring 17 away — the level's arithmetic: walk 16, three touches, ring, and the box needs a full bar.

Runs 15-16 (`play_ls20_rings16.log`): the loop is steady — level 1 at press 96; on level 2 the keyhole is
touched, the near ring refills the bar, two more touches, the region MATCHES (presses 152, 222, 272, 322) —
and the box is 20 presses away with 12 left, the far ring 17 away, every time. The level's arithmetic: a bar
is 21 moves (84 cells at 4 per move; refused presses are free), the walk to the keyhole is 16, the three
touches cost 1 + 2 + 2 moves at best, and the box needs a full bar from the keyhole (20) or the far ring
(17, then 6). It closes only if the touches run to the last move before the near ring is taken and the
touches after the refill cost two moves each; the experiment loop spends 3-5 on them (it steps back, replans,
bumps). That is the next thing to shave, and it is a matter of the experiment's economy, not of the relations,
which are built and firing.

## The pins persist; the magnets; the route with two refill points (Sep 6)

Jonathan: the pins we bend and break should persist through everything. There are two refill points in that
game — it is not the route, it is recognizing a second point is the same and adding another goal. And the
pins are like magnets: a pin that breaks off pulls all the similar pins with it; it drags pins of other colours
or directions too, but weakly — which tells us it probably won't go into a wall from another direction either.

Built:

- THE PINS PERSIST (`fence.prior`, `fence_rules_<game>.json`): the colour rules survive a reset (they always
  did: the fence is re-laid from the level's presses), a level change (merged and carried as `prior`) and a
  run (saved at the end, loaded at the start: 45 rules carried in on the next run of ls20). A carried rule is
  a magnet at 0.75, not a wall, until one bump on the new level confirms it. A respawn (the bar ran dry and
  the body reappeared at the start) is no longer read as a 30-cell move: it had taught "3>4 right passes" 20
  times and poisoned that rule.
- THE MAGNETS (`fence.pull`): a broken pin pulls its likes — the same colours and direction at 1.0 (a wall for
  the planner), the same colours in another direction at 0.5, the same far colour anywhere at 0.25. The
  openings are ranked by the pull (a border pulled at 0.5 or more goes last: one bump there verifies the rule
  for that direction). ls20 level 2 after ten presses: 243 borders pulled weakly from the carried rules
  before a single bump; 6216 by the end of the run.
- THE ROUTE WITH REFILL POINTS (`route.py`): every standing ring is a goal. A life is planned as stops — the
  walk to the source, its touches, the target — with each ring inserted wherever the bar closes, the legs
  priced by the planner's own paths on imagined frames (the operators walked forward), a touch from adjacency
  one move, from the source itself two, a ring leg allowed the whole bar. The first stop decides the next
  experiment; a reset clears the relation's experiment so every life is planned from a full bar; the touches
  still needed are counted round the remembered cycle from the current HUD state to the target (not "states
  minus one"); a touch ends the moment the region changed and a ring stop the moment the bar rose (the step
  off the keyhole and the step back toward a ring that is gone used to cost 1 and 4 presses).

The route on the level-2 start frame: touch1 -> ring 11@51,40 -> touch2 -> touch3 -> ring 11@16,15 -> box,
46 moves, 17 to spare in the model. Live (`play_ls20_route5.log`): level 1 at press 97; on level 2 the route
runs as planned every life — walk 16 and touch (17), the near ring first (refill 8 -> 84), the touches (3, 2),
the MATCH — and the bar reads 16 at the match with the far ring 17 away. One move. The model's legs are from
the frame after the walk (adjacent); the body is ON the source after a touch, and from there the near ring is
3 moves, not 1, and the return 2, not 1. The next step is to price the legs from the on-source frame and let
the planner see that the two-touch order (touch, touch, ring, touch, far ring) is the one that closes.

## ls20 level 2 cleared: the legs priced from the source, the meter as pins, the game corrects the rules (Sep 6)

Jonathan: price the legs from the on-source frame. And the budget meter is one colour changing to another,
surrounded by one other; each turn it drains we see how much, then predict that each turn drains it; each pixel
in the bar puts its pins in that direction dragging the rest, but not the surrounding colour — that is where it
ends. And: a mistaken press taught that walls were floor; the game always wins, so the rule should update; the
magnets give the way — the pins break anyway when we try, the new broken pins displace the imagined bent ones,
and a small mistake (more colours share the interaction) merges at the centre.

**Level 2 is cleared** (`play_ls20_route17.log`): level 1 at press 96, level 2 at press 176 — 80 presses on a
level whose human baseline is 123. The route ran as planned: walk 16 and touch, the near ring first (bar 8 ->
84), two touches, the region matched, the far ring (bar 8 -> 84), the box. Level 3 (a new layout; the carried
relation and two new rings found at once) ran to its cap.

What it took, from the run that was one move short:

- THE LEGS FROM THE ON-SOURCE FRAME (`route.py`): after a touch the body is on the source; the ring legs and the
  return are priced from that frame (the walk simulated with the operators, the touch simulated as the step
  onto the source). The far ring is 15-16 from the keyhole itself, the box 4 from the far ring.
- THE METER AS PINS (`meter.py`): the band collapsed to a line; every drained cell lays its pin down toward the
  drain; the standing pins are the moves left; the end is where the bar met the surround; a refill stands the
  pins up again (so does a reset, now). ls20: 2 columns per move toward +x, 42 pins standing, the end at 54,
  21 moves; the pins predicted the drain in 350/350 presses. It reads the same as the register when the bar is
  low and disagrees only about the full bar (the register's band was the drained part).
- THE LAST LEVEL'S LAW UNTIL THIS LEVEL SPEAKS: a button this level has not pressed eight times keeps the last
  level's presses in its fit. The walk to the keyhole never needs 'left', so 'left' had no evidence on level 2
  and was dropped — and both rings lie to the left.
- THE TOUCH DANCE IS THE RELATION'S: the bump onto the keyhole and the step off it (the glyph hides under the
  body and reappears) were charging the up and down operators, which lost their gate at the keyhole every life;
  any press with the body on the source before or after is kept out of the bond and the fit.
- THE STATE KEY LEAVES THE WHOLE REGISTER BAND OUT: with only the often-changing cells masked, a full bar's far
  end made every planned state new and the search hit its cap before any far target.
- THE FENCE VETOES THE FLOOR: a colour the fence has bumped five times and never passed is not floor on one
  press's word (one recorded right-move into a colour-4 patch had made walls floor for the planner and its
  imagined states exploded). The route caches legs, never failures.

THE GAME ALWAYS WINS (`fence.compile`): a rule seen both ways is decided by the refusals when they outweigh the
passes five to one — the broken pins displace the imagined bent ones; the stray pass stays as a faint pull until
more refusals push it out. THE MERGE: when two or more near colours agree that a far colour blocks in a
direction, the pins align at the centre and the far colour blocks from any near colour at 0.75 until each pair
is seen. Logged as "corrected by the game" and "merged".

## The centre magnets: every thing's hidden response, rebuilt from the pins that broke into it (Sep 6)

Jonathan: the centre of a pixel wants a pin where the void line is; that centre has some magnet we don't know
and have to recreate from the pins. A goal without its key needs a complex magnet, walls respond the same way
to everything, and the walls are the first thing we meet, so at the start the goal is empty while the walls
already have pins. Pins that bounce off the inside give hints: partially aligned means shared properties with
something missing.

Built (`magnet.py`, wired into the sleep): one response table per thing — the touch graph's objects and the
wall pieces — keyed by (control, side, WHICH PART of the thing the pin went into), holding what the game
answered: pass, refuse, state (something elsewhere changed), level. From it:

- a KIND per thing: wall (refuses and nothing else), open (passes only), state (its touches change something
  elsewhere), goal (a level), empty (nothing on it yet), door (THE SAME PIN GOT TWO ANSWERS);
- a CLOSURE per thing: how much of (controls x sides) has an answer — walls close with a few pins;
- for every door, THE KEY: the region of the frame that is constant across the presses with the higher answer
  (level > state > pass) and different in every press with the lower one — away from the body, the band and
  the thing itself. That is the missing property the bounced pin points at.

On the recorded ls20 level 1: 8 things — 2 walls, 5 empty, and the box 5@9,33 as a door: the same pin from
below (ACTION1) passed three times into its mouth and once completed the level, and the key is 4 cells at rows
57-58 cols 3-4 — inside the HUD region (rows 55-60 cols 3-8) the relation layer had found from the keyhole's
state edges. The box's own bounced pins point at the HUD without the touch graph. The part matters: keyed by
side alone, the mouth and the door were one row and the search found the body's own trail.

When a door has a key and this level has no relation with targets, the key becomes one (`raw_open`): touch the
thing whose state edges change that region until it reads as it did when the door opened. The keyhole falls
out of the search run backwards; on ls20 the touch-graph relation is found first, so the magnet's stands by.

Live (`play_ls20_magnet.log`): level 1 at 96 and level 2 at 176 again — the second run in a row with the same
numbers. Magnets on level 1: 2 walls, 2 mixed, 3 open, 7 empty at the match; no door, since this run never
bumped the box unmatched. Level 3: 1 wall, 3 open, 10 empty by the cap — nothing contradicted itself yet, which
is the honest reading: the magnets there have not been pushed. sp80 (`play_sp80_magnet.log`): the magnets read
"empty 5, open 1" throughout — sp80's things are not entered by a body, so the pins never break into them; the
layer needs the act button's pins (ACTION5 on a thing) to say anything there. And sp80 did NOT clear level 1 in
this run (150 presses; the previous run cleared it at 33) — a regression from today's changes to check.

## The act button's pins; the act button as a complex magnet; sp80's regression found and fixed (Sep 6)

Jonathan: give the magnets the act button's pins, sp80 first. The act button is a complex magnet from the start
— we don't know what it does either — and where things expect something complex we would want to try it there.

Built (`magnet._act`): a button that moves nothing puts its pin into every thing the body is LINED UP with
(rows or columns overlapping) from the side the thing lies on, keyed by the overlapping span, and into 'afar'
when nothing is lined up. The answer: the thing itself changed (pass — the pin went in), something elsewhere
changed (state), nothing (refuse), or the level. The button has a magnet of its own — its table from wherever
it was pressed: 'inert' (never did anything), 'plain' (always the same), 'complex' (its answer depends on where).
Attention follows the magnets: the goals are re-ranked by what expects something complex — doors, then things
with nothing on them, then state things, then open floor, walls last — so a complex button is tried there first.

sp80's regression (level 1 not cleared, where the run before cleared it at 33): two causes, both found in the
data, not by guessing. (1) 'left' and 'right' were being fit as Cycle (a table that remembers every position the
bar stood in scores 1.0) instead of Displace; a Displace at 0.9 or better is now preferred over a Cycle — a
movement law beats a memorised table. (2) The fence's UNSEEN WALL (every cell ahead looks like floor) was
teaching the colour rule "12 into 12 going down blocks" from the bar's arena bound, and the bar could not be
planned downward anywhere. An unseen wall is a place, not a law of colours: it breaks the border where it is and
teaches nothing. The carried sp80 rules were cleaned of the two poisoned entries. Also: the experiment's
'changed' no longer counts the register's drain (ACTION5 at the token read as 'changed after 3 presses' when
only the bar had drained).

`play_sp80_act2.log`: level 1 at press 31. Level 2 to its cap (174 presses): the magnets read 7 walls, 3 inert
buttons, 2 empty things; ACTION5 lined up under six different things answered refuse every time. That is the
honest reading of level 2 so far: every platform tried answers the act button like a wall, and the two things
with nothing on them are where the loop has not yet stood. The act button is 'inert' by its own magnet on both
levels — it acted exactly once, on the level, which the magnet records under the level's own press.

## Standing on sp80's two empty things; the act button hands control to a block (Sep 6)

Jonathan: go stand on the two empty things on sp80 level 2.

To get there the bar had to be readable as a mover: `explain_shift` was reading the bar's 4-column step as a
10-column two-patch "teleport" (a wide uniform bar shifted by less than its width changes only its two ends, so
the moved set found from the diff missed the middle and the true short shift failed the exactness test). The
moved set is now grown to the whole connected body of its colours before a shift is tested; sp80's left and
right came back as Displace (0, +-4) on the whole 80-cell bar, and ls20 fits unchanged.

`play_sp80_stand.log`: level 1 at press 40; on level 2 the bar lined up with both empty things — 11@4,44
(nothing after 4 presses) and 8@16,8 (nothing after 2) — and with every other thing on the level, and every one
answered nothing to the act button. But the frames of press 51 say what the act button does on this level: the
bar (colour 9, 20 wide, rows 16-19) lined up directly above the block 8@24,28 pressed act, and the COLOURS
SWAPPED — the bar became an inert 8 and the block below became 9, the controlled body. The act button hands
control to the block beneath. The loop's 'changed' test missed it because the block's cells became the body and
the body is masked out of 'changed'; the magnets missed it for the same reason. Fixed: a thing's own change
counts even when the body is what it became, and a button that turns the body into something else has acted.
Read that way the act button's own magnet is COMPLEX (one state, fifteen refusals) and its key — the body's own
place being the missing property, which for a button it may be — is rows 16-19 cols 24-43: the bar directly
above the block, lined up. The key of a thing excludes the body's place; the key of a button keeps it.

What level 2 is, then: two 8 blocks, three platforms with 4-wide gaps between their legs at the top, a token at
the bottom, and an act button that makes whichever block the bar stands over the new bar. That is the shape of
the level's magnet, and it is what the loop should now push on: stand over a block, take it, and see what the
taken block's act does at a platform.

Live (play_sp80_swap.log): level 1 at press 40; on level 2 the magnets now read the act button as complex (2 state / 5 refuse) and the block 8@24,28 as a door. The first sleep's key for the button was the bar's place directly above the block; once a second swap happened somewhere else, the absolute search found no constant region — a button's key is relative to the body (the thing directly beneath it), which the search does not yet express. Level 2 ran to its cap.

## The diagonal pins, and the key search in body coordinates (Sep 6, night)

Jonathan: the controller is the front wall with long pins to each pixel; a diagonal pin goes in and out of the
screen into the logic space — the back wall, with coordinates — and connects far-apart pixels or is conditional;
each pin has an eye; we still see the end of a diagonal pin in its pixel as a small arrow pointing at the pixels
it affects; the angle it comes in at can enter nearby pixels; a full path runs front wall to back wall.

Built:

- THE KEY SEARCH IN BODY COORDINATES (`magnet.key`): the search for a door's missing property runs first in screen
  coordinates, then with every frame shifted so the body sits at the origin, and the region comes back as an
  offset from the body. A key must have content (a thing, not a patch of empty floor) and in body coordinates the
  nearest such region wins. When no one offset is constant across the opens, each open is searched alone against
  all the closes and the keys are merged by colour: "a thing of colour c touching the body above or below".
- THE DIAGONAL PINS (`diagonal.py`): one kind of thing made from three layers — the relations (foot: the source;
  back: the region and what it must read; effect: the target), the rings (foot: the ring; back: the register;
  effect: a refill), the magnets' keys (foot: the door or the button; back: the key in screen or body frame). Each
  pin has a front (the buttons that drive it), a width (the span it is lined up with) and AN EYE: over the presses
  whose pin went into the foot, fired with the condition / fired without / silent with / silent without. Real
  when it fired only with and never stayed silent with; leaky otherwise; unproven with no firing. A PATH is
  complete for a button when a front pin (an operator or act pins) reaches a foot with a diagonal pin.
- The feet are drawn (`flow.py`): a magenta arrow inside the foot pointing at the back-wall coordinate, a
  magenta corner mark where it lands, the eye's counts beside it.

sp80 level 2 (`play_sp80_diag.log`, level 1 at press 40): four diagonal pins, all from the magnets. The two swaps
are read as doors on the blocks; ACTION5's own pin lands at rows 20-23 cols 20-39 (the bar's place at the first
swap) with an eye of 1 firing, 0 without, 0 silent-with, 6 silent-without — "real" on one firing, which is the
eye saying nothing yet. The body-frame keys the search found for the blocks are a platform leg 20 rows above
the body (eye 3/0/0/4) and a wide band above — coincidences of where the bar stood, and the eye cannot tell
them from causes at three firings. The honest finding from the frames: the act swaps with a block adjacent
below (press 7) and with one adjacent above (press 11) but NOT with one adjacent above at press 4 — so "a
block touching the body" is not the whole key, and the per-open merge rightly did not claim it. Paths: 2 of 5
buttons complete (up, and the act button).

ls20 (`play_ls20_diag.log`): level 1 missed this run (the keyhole unreachable at press 11 with the operators not
yet gated, then the cap) — the third miss in about eighteen runs today; no pins formed.

Later (play_ls20_diag3/4.log): the magnets' re-ranking had put the empty things ahead of the openings and cost ls20 its level twice (the fence's order — the openings first — stands, the magnets order the things after them); with that restored ls20 level 1 cleared at press 87, a new best, twice. Its diagonal pins: on level 1 the keyhole -> the HUD region -> the box (relation) and, on level 2, the two rings -> the register (one refill seen: eye 1/0/0/0, real). A relation's eye is read at its target with the relation's own match test, and it fires only when the target opens; the counts in these two logs predate that last correction. In the last of them level 2 was cleared as well (the run ended with levels 2), so the route and the pins stood together.

## The three views: one memory per pixel, three eyes, each blind to the pin it looks along (Sep 7)

Jonathan: each eye has the pin aligned with it invisible, and the other three make up what that pixel is to that
perspective. The side eye sees the directional, border and normal pins and stores that set; the front eye sees
the flat and diagonal pins and keeps the diagonal with its back-wall coordinates — which pixel is for what, and
the context; the full memory is all of them combined. Keep the openings first.

Built (`views.py`, `flow.py --view side|front|eyes`): one memory per pixel composed from the layers, as three
projections that each drop one component —

- THE SIDE EYE looks along the screen and sees what STANDS: the middle pins not yet laid, the trail, the border
  pins, the walls (the fallen pins), the openings, the magnets' pull on untouched borders. Its memory is the
  fence. It is blind to the diagonals, so a door is a wall to it.
- THE FRONT EYE looks straight at the screen and sees what LIES FLAT — bent, broken, dragged — and the diagonals
  foreshortened: every foot with its back-wall coordinate (screen or body frame) and condition, every cell that
  is a back-wall coordinate for some pin, the thing each pixel belongs to and the kind of magnet it has. Its
  memory is the relations, the rings, the magnets and the paths. It is blind to what stands, so it cannot say
  where the body can go.
- THE EYES look down each pin and see only whether it held: the water on the cell, the meter's pins on the band,
  the diagonal pins' counts on their feet. Blind to geometry and to context.
- ONLY THE UNION sees a door: a wall or a refusal to the side eye, a diagonal foot to the front eye.

The goal order is untouched: the openings first, then the things the magnets rank, walls last.

Where the walls go, in the agent: the front wall is the controller (the buttons the API offers), the screen is
the frames, the back wall is everything fitted and kept — the operators, the fence's colour rules, the relations,
the rings, the route, the magnets, the pins, and the JSON saved between runs. The colour rules and the pins that
persist across runs are the stable part of the back wall. For the assistant the picture is the same one step out:
its weights are fixed and do not learn from this; the back wall of the work is the session's context and the
memory directory, and the ledger and the map are the part of it that survives the session.

Live (play_ls20_views2.log): level 1 at press 90, level 2 at 208. At the level-1 match the side eye saw 550 trail cells, 67 wall cells and 75 openings; the front eye saw 895 foot cells and 36 back-wall cells over 7 things (4 empty, 2 mixed, 1 open); the eyes saw 246 wet cells and 895 cells under a pin's eye. What only the union saw as a door was the corridor 3@8,14, not the box: the corridor carries a relation foot (its touches change the HUD, like the keyhole's) and a refused border, which is the union's definition met by the wrong thing — the box itself had no broken border in this run because the loop never bumped it unmatched. The per-pixel memory is saved per level once the views outlive the sleep (a scope fix made after this run).

## The cube: two side eyes, the quaternion memory, the octonion of a pixel and its neighbour (Sep 7)

Jonathan: imagine all of this inside a cube — the front and back walls, the roof where the assistant sits, the
lower ocean as the floor, the side walls the circuit the flat pins form; four eyes — front, top, and the two side
faces, with what was called the side eye really on the corner; memory stored as quaternions, recall choosing a
real-axis eye and leaving the other three imaginary; and since the pixels each carry a direction, the octonion
would be the quaternion of the starting pixel with the imaginary terms of the next.

Built:

- THE TWO SIDE EYES (`views.side_x`, `views.side_y`): the left face looks along the rows and sees only the vertical
  pins (up/down borders, the trail's vertical legs, the walls); the bottom face sees only the horizontal ones. The
  corner is their union — what was first built as "the side eye" saw all four directions, which only the corner can.
- THE QUATERNION MEMORY (`quat.py`, `views.q`): four numbers per pixel — top: what held (+1 fired only with its
  condition, -1 fired without, the water as a negative when there is no pin); front: the context (+1 a diagonal
  foot or a back-wall coordinate, +0.5 flat pins only); side_x: the vertical borders (+0.5 bent, -0.5 broken, summed);
  side_y: the horizontal. RECALL from an eye puts that eye on the real axis and the other three on i, j, k. Saved
  per level as `views_<game>_L<n>_q.npy`.
- THE PATH PRODUCT: a diagonal pin's path — its foot, its back-wall coordinate, its effect — as the Hamilton product
  of the pixels' quaternions in order (non-commutative, as the route is), with its real part and norm, and as the
  Cayley–Dickson chain of neighbour pairs (a, b)(c, d) = (ac - d*b, da + bc*), with its norm and its largest
  associator |(AB)C - A(BC)|, which is where the path does not split freely. Checked at every sleep against the
  pin's own eye. The algebra is verified: quaternions associate and multiply norms, the octonion does not
  associate and collapses to the quaternion when the second halves are zero.

Yes to the octonion reading: the Cayley–Dickson pair IS "the quaternion of this pixel and the quaternion of the
next", and the doubling is what loses associativity — a path of three pixels multiplies differently depending on
where it is grouped, so the associator marks the pixel where a basin ends and another begins.

What the eyes and the products are for: if the real part of a path's product tracks the pin's eye (fired with the
condition against fired without) across pins, the multiplication is a law of the memory and not a filing system.

Live (play_ls20_quat3.log): level 1 at press 112, level 2 at 211. The side eyes at the level-1 match: 447 cells of vertical pins, 385 of horizontal (the corner: 500 trail cells, 67 walls, 50 openings). The products, each pixel lifted to one plus its memory so an empty pixel is the identity: on level 3 the two ring pins read real +0.50, |q| 2.55, |o| 2.92, associator 0, against an eye of 5 firings with the condition and none without — the product's real part is positive where the eye is clean. On level 1 the relation pin keyhole -> HUD -> box read real +0.00, |q| 2.45, against an eye of 0/0/0/4: four silences with the condition met and no firing counted, because the box's opening is the level itself and the level's press is filed under the goal, not under the relation — an accounting gap to close before the check can say anything about relations. Two pins agree with their eyes and one is unscored; that is what the test has to say so far. An earlier run of the same code missed level 1 (the intermittent early-keyhole miss, about one run in four) and is not evidence either way.

## The level's last word; the same term round a border; the collapse of a region into one term (Sep 7)

Jonathan: close the accounting gap so the relation pin gets its eye. What happens when the basins are the same and
the quaternion math ends up back where it was — one cell in a wall, each cell round its border the same, going
round the edge the same term over and over? Could that whole section collapse into one term, and the body in
the game be one quaternion instead of a grid of pixels each calculated?

Built:

- THE LEVEL'S LAST WORD (`play.py`, at the level change): the press that opened the goal is in the level's presses
  but no sleep ever saw it, because the sleep runs before the press and the level change clears the presses after.
  Now, at the level change, the magnets are rebuilt with that press counted as the level, and every pin's eye is
  scored once more; the relation pin gets its firing. The level's diagonal file keeps those eyes.
- THE SAME TERM ROUND A BORDER (`quat.holonomy`): a pixel enters a product as one plus its memory; for the direction
  part that is a rotation by a fixed angle per step. Going round a uniform region's edge is that rotation applied
  once per perimeter cell. It comes back to where it started only when the total is a whole turn. A corridor cell
  whose memory is "context only" (front = 1) lifts to (1, 1, 0, 0), a quarter turn per step, so its border closes
  exactly when the perimeter is a multiple of four — a region of 350 cells with a 75-cell edge does not close (three
  quarters left over), one with a 26-cell edge does not either (a half turn), and 7 of the 66 regions on ls20
  level 1 do. That is the honest answer to "what happens": the same term repeated is a rotation, and whether the
  border returns is a property of the region's shape, its perimeter modulo the term's order. The growth per step
  (the norm of the lifted term, 1.41 for one component, 1.73 for two) is the other half: a loop of the same term
  grows geometrically, which is what a norm-multiplicative product must do, and is why a region should be one term
  and not a product of its cells.
- THE COLLAPSE (`quat.collapse`, `views.collapse`): connected pixels with the same memory collapse into one term —
  the quaternion, the cell count, the perimeter, the holonomy round the edge. ls20 level 1: 4096 pixels become 69
  terms, 66 of them with memory, the largest term the untouched floor at 2956 cells; the body is one term for its
  25 cells whenever its pixels agree, which the sleep now reports. A wall piece is one term, a corridor is one, and
  the body is one quaternion instead of a grid.

Live (play_ls20_collapse2.log): level 1 at press 153, level 2 at 271. The level's last word on level 1: keyhole -> HUD -> box, eye 1 firing with the condition, 0 without, 0 silent with, 4 silent without — real; on level 2 the same pin 1/0/0/0. The relation pin has its eye. The collapse at the level-1 match: 4096 pixels -> 65 terms, 62 with memory, 7 whose edge comes back; the body is 2 terms for its 25 cells (its top rows and its bottom rows carry different border pins, so it is two terms, not one — the body collapses to one only where its pixels remember the same thing). Also fixed on the way: a thing found unreachable was retired for the level (the keyhole, tried at press 11 before the operators were gated, was never asked again, which was the intermittent level-1 miss); it is asked again thirty presses later.

## The growth law, and the body stitched into one nested term (Sep 7)

Jonathan: the terms lift by the square root of the steps — 1.41 is root 2, 1.73 is root 3. The body is two colours,
so it is probably seen as two terms; they stay constant relative to each other, so they should merge; the diagonal
between them barely has to go anywhere, so it stitches them; and the theory used nested quaternions, so the body
would nest into its parts.

- THE GROWTH LAW is exact: a pixel enters a product as one plus its memory, so a term with k unit components has
  norm sqrt(1 + k) — sqrt 2 for one, sqrt 3 for two, and 2 for a pixel with all three eyes lit (term 64 on ls20
  level 1: q = (0, 1, 1, 1), growth 2.000). Checked on the saved memory.
- THE BODY'S PARTS ARE ITS RIM, NOT ITS COLOURS. On the saved level-1 memory the body's 25 cells fall into four
  terms: the 16-cell interior (front 0.5, side_x 1, side_y 1), a 4-cell bottom row, a 4-cell right column, and the
  corner cell — split by the fence's border pins, which only the rim carries, since the body bumps with one edge
  at a time. The memory has no colour component, so the two colours do not divide it; they would, one level
  further down, if the front eye carried colour.
- THE STITCH (`quat.stitch`, wired into the sleep): the parts keep a constant position relative to each other, so
  they nest into one term — the largest part real, the next its imaginary half (the Cayley–Dickson pair), further
  parts chained. The body: four parts nested into one octonion of norm 4.56, its whole (the lifted product of the
  parts) of norm about 6. The sleep now says "the body is 4 terms for its 25 cells — stitched into one nested term".
  Yes, that is the nested quaternion of the earlier theory: the body is one term whose components are terms.

## The depth count, the floor thinning, and one connection per side wall (Sep 7)

Jonathan: add the depth count and the floor thinning. Would we want the only wall connections at the side walls?
The circuit wants one in and one output; an answer wanting four eye terms should reduce to one connection per side
wall through the nested terms, and every connection to a non-side wall is a short circuit.

Built (`play.py`):

- THE DEPTH COUNT: every changed cell of every press is filed by where its pin lands — layer 1, the pixel (the
  front predicted it: an operator, the fence); layer 2, the thing (an unexplained change inside a thing the magnets
  know — its state answer); layer 3, the relation (inside a relation's region); or 0, wall to wall — the water, a
  short circuit. Logged at each sleep as shares of the level's change.
- THE FLOOR THINNING: the floor's field collapsed again with the body's cells emptied (the body has detached the
  pins that travel with it), and the rule sheet split into the body's own colour against the walls and the other
  colour pairs left behind.

`play_ls20_depth.log`: level 1 at press 149, level 2 at 267. Depth at the first sleep of level 1: 99% at layer 1,
1% wall to wall — not "every pin wall to wall at the start", because the movement laws come in as the prior from the
last run and predict the body's own change from the first press; the folding shows in the layers above it. By the
match: 84% layer 1, 14% layer 2 (the keyhole's touches and the HUD's changes, answered by the things' magnets), 1%
layer 3 (inside the relation's region), 1% short circuits. Floor at the match: 60 terms with the body's pins, 59
after it detached them (the body's four rim terms were one term's worth of floor), and the sheet keeps 8 rules of
other colour pairs while 15 are the body's own colour against the walls.

One in, one out. The agent already has it by construction: each press is one button at the front wall and one
outcome at the back, and every eye's count reduces by nesting to the one pin it sits on. What the depth count
measures is the short circuits: a press whose change is not threaded through the three layers is a wall-to-wall
pin, and on ls20 level 1 that is one percent of the change by the match. Any connection from the geometry (the side
walls) straight to the answer that skips the pixel, the thing and the relation would show up there.

## Next

- Score the eye on non-register cells for a like-for-like `mech` column (its fold models are saved; the CAT
  models need re-tuning).
- Per-object transform pins (rotate/flip about the object's own centre) for tr87-class buttons; per-object
  displacement (several movers) for the cascades. Then the planner gets tr87.
- On a level change, refit the operators at once and clear the visited set (new ground); learn ACTION5's
  precondition as an operator (bar position relative to the goal) so the planner can aim for it instead of
  probing at every fourth place.
- Run the planner on the other games with gated operators (ls20, tu93, cn04, dc22, g50t, ka59, sc25).
- Per-object displace (several movers, each with its own vector) for the cascade games; a pickup operator
  (a small object vanishes when the mover enters it, the register jumps) for ls20's remaining misses.
- Use the gated operators as the world model in play.py's `choose`: imagine by applying the operator
  instead of the eye where an operator exists, keep the eye elsewhere. sp80 first.
- Re-collect with a movement-biased policy for the data-starved games.
