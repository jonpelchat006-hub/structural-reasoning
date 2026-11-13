# The Small Eye — is recognition a size thing? (Sep 3 2026)

## The claim (Jonathan)

"Cats and flies have eyes too. If things with basically no brain can still see, recognition is not
an intelligence-only thing or a trillion-parameter thing. Our eyes would be surrounded by your
parameters, and the size of them could scale up: more markers from the color stuff, and the focus
can change up to the amount of markers the tunnel can attach to for the shave. The controls would
be how we touch. We can look at something, then shut off vision to think about it, and power
organs on and off as we need them. I think we can do it with a small machine, just over more time."

## What was tested

Two organs, both new tonight:

- **collect.py — the touch.** A deliberately dumb hand presses every public ARC-AGI-3 game 120
  times (clickables first, then random cells; random actions with momentum) and keeps *every*
  frame with the press that made it (`D:\planet\eye\<game>.npz`). Before this the frames on disk
  were snapshots every 20 presses — nothing an eye could learn from. 25 games, ~3000 touches,
  ~40 minutes, cheap scorecards.
- **eye.py — the small eye.** A 262,624-parameter fully-convolutional net (dilated blocks so it
  can see across the 64×64 grid) that takes a frame and a press and predicts the next frame.
  Changed cells weigh 21× in the loss so it cannot pass by predicting "nothing changes".
  Trained on the RTX 5060 Ti in a few minutes per fold (torch + cu128 installed tonight).

Three measures per game, all on the cells that actually changed (a "nothing changes" model
scores 0), on the last ~40 touches of the game:

- **FLY** — the eye has never seen this game; trained on the other 20 (fixed circuits).
- **CAT** — the same eye after 300 steps of training on this game's own first 80 touches
  (the small machine over more time).
- **SCRATCH** — an eye trained only on those 80 touches, nothing else.

## Result (5-fold, 25 games; `python eye.py --summary`)

| | changed-cell accuracy | change-detection F1 |
|---|---|---|
| FLY (never seen the game) | **0.08** | 0.04 |
| CAT (80 own touches) | **0.79** | 0.69 |
| SCRATCH (80 own touches only) | **0.80** | 0.68 |

Per game (CAT): vc33 1.00, s5i5 1.00, sp80 0.99, tu93 0.99, tr87 0.98, su15 0.96, tn36 0.95,
wa30 0.95, ar25 0.92, ls20 0.88, g50t 0.85, lf52 0.84, sk48 0.84, m0r0 0.83, dc22 0.81,
ka59 0.75, sc25 0.73, bp35 0.68, cn04 0.67, re86 0.66, cd82 0.64, r11l 0.52, sb26 0.41,
ft09 0.20, lp85 — (no changed cells in its late touches: nothing to score).

vc33 is the game that took a human hour of probing to write a solver for (vc33_solver.py);
the eye learned its physics to 100 % from 80 random touches. Finished 10:07 PC time.

## What it says

1. **The claim holds for seeing.** A quarter-million parameters — a thousandth of the smallest
   local language model — learns what a press does in a game it has never seen, to 85–99 % on
   the changed cells for the best half of the games, from about a minute of touching. It is
   not size; it is time on the thing.
2. **The fly cannot read a new game.** 8 % is barely above chance. Fixed circuits (which is also
   what the ambient mask, the clickables and probe.py are) see motion and change; they do not
   see *meaning* in a mechanism they have never touched. Recognition here is the cat's kind,
   not the fly's: you learn the room by touching it.
3. **The other games taught it nothing.** CAT ≈ SCRATCH. Pretraining on 20 games did not help
   the 21st. That is ARC working as designed — each game is its own physics — and it is why
   the Kaggle leaders learn *at play time* (test-time training) rather than shipping a
   pretrained brain. It also means the nightly torus/pool "feel-prior across games" is not
   where cross-game gain will come from; within-game learning is.
4. **The weak games are the hand's fault, not the eye's.** ft09 (4 of 120 presses changed
   anything) and lp85 (6 of 120) gave the eye nothing to learn from. sb26 and r11l change on
   every press but in ways 80 samples do not cover. Better touching — probe the pieces, repeat
   what moved something — is the lever there, not more parameters.

## Mapping to the architecture

- *eyes surrounded by parameters* — the small eye wraps the fixed ring readers; the rings feed
  it, it learns the game's physics around them.
- *markers scale the focus* — the objects the eye segments are the markers; how many it tracks
  is the focus; the shave chooses which.
- *controls are how we touch* — a press is the hand; the effect of the touch is the only
  teacher (CAT vs FLY is the whole result).
- *shut off vision to think* — roll the eye forward on imagined presses without sending them:
  the only way to spend fewer actions than the human baseline on a fixed budget. **Not built
  yet — this is the next organ.**
- *power organs on and off* — the on-call board already gates which organs turn; the eye is
  one more organ on it.

## Learn by playing — play.py (same day, later)

Jonathan: "we should be taking one [snapshot] every move at the start and then slowing down as
we figure it out; it should go down with the amount of surprises we expect, and at the start
everything is a surprise ... I'll remember every move I did and then make checkpoints like at a
refill. And we have to do it by actually playing."

**play.py** does exactly that, live, with a blank eye: every press the eye *imagines* every
candidate press (available actions; clickables + 4 random cells for click games) without
sending them, sends the one it is least sure about (entropy + predicted change, minus how often
that press was tried on this screen), measures **surprise = 1 − F1** between what it said would
change (and to which color) and what did — ignoring the tick region (the budget bar: cells that
move on presses where ≤3 cells change) — keeps the transition only if surprise > 0.05, or it is
one of the first 12 presses, or the level turned (checkpoint), and takes 8 + 32·surprise
learning steps on the memory (sampled by surprise). GAME_OVER → RESET and continue.

Result, 25 public games, 150 presses each, ~50 s per game on the 5060 Ti
(`play_batch_20260903_1037.jsonl`, `python play.py --summary`):

- **Recording rate falls as predicted in 19 of 25 games** — e.g. tu93 [1.0, 0.1, 0, 0, 0, 0,
  0, 0] per 20 presses, sp80 [0.9, 0.1, 0, 0.1, 0.05, 0, 0, 0], m0r0 [1.0, 0.7, 0.6, 0.4,
  0.3, 0.25, 0, 0]; mean surprise first 20 presses ≈ 0.8, last 20 ≈ 0.1. It stays high where
  the screen keeps doing new things (r11l, sc25, bp35, lf52).
- **Levels: 3** (ft09 L1 at press 85, vc33 L1 at 17, r11l L1 at 4) against the random hand's
  1 (r11l) and PriorAgent v11's 1/176. In the first single run on vc33 the eye reached L2 at
  press 84 (12 presses for L2, human baseline 18) — the same two levels the hand-written
  solver reaches, with no solver.
- **ft09 was dead for the random hand** (4 of 120 presses changed anything); the curious hand
  made 63 of 150 presses change something and cleared a level: curiosity is the better hand.

What it says: the eye learns while playing, and the recording slows as the surprises run out
— the claim holds. Curiosity alone does not clear levels: it finds what moves, not what the
level wants. The missing organ is the **goal** — something that says which imagined frame is
closer to done. Candidates that need no internet and no big model: (1) reach-novel-screens
(state novelty on the *imagined* frame, not cell entropy) so the hand walks somewhere instead
of poking; (2) after the first level turns, the frames just before it become the target and the
eye plans toward frames that look like them; (3) an RL value head on the eye's features trained
on the level signal. This is the leaders' recipe; the eye is the part of it that now exists.

## Rising — the goal read off the imagined frames (same day, later)

Jonathan: "wouldn't the wisdom rings be able to trace a path towards the inner core, which would
be the direction a goal would want to go? The side eyes would be in a position to see a goal,
and with their position it would look like rising upwards."

Before the first level turns nothing in a frame says where the core is, so the path has to be
read off something that *rises*. In a puzzle that is irreversible change: a key picked up, a
door opened, a cell filled, new ground walked on. Reversible motion (the agent going back and
forth over the same cells) is not rising. So `rise(frame)` = cells that differ from the level's
start frame, have changed at most twice so far, and are not the tick — and the hand takes the
candidate whose *imagined* frame rises most (curiosity as tiebreak, and alone when nothing
rises). A level turn or a reset makes the current frame the new start. It is the side-eye
"climbing" verdict applied to the eye's imagination instead of to a log.

Result (`play_batch_20260903_1143.jsonl`, 25 games × 150 presses): **4 levels** — vc33 L1 at
press 53 and L2 at 131, lf52 L1 at 104 (a 10-level game, first time anything cleared it), tn36
L1 at 18 — against curiosity-only's 3 (ft09, vc33, r11l) an hour earlier and the random hand's
1. Between the two eye runs five different games have now had a level cleared by a blank eye in
150 presses (ft09, vc33, r11l, lf52, tn36). Run-to-run variance is large (the first twelve
touches are random), so 3 vs 4 is not a difference; 3–4 vs 1 is.

Honest limits: rise is one-step (the eye imagines one press ahead; a corridor that needs ten
presses before anything rises is invisible to it); it counts *any* lasting change as up, so a
game where the wrong lasting change is easy (paint the wrong cell) will chase it; and after a
level turns the new level's start is taken as the new floor, with nothing carried over about
what "done" looked like. Next: multi-step imagining (rollouts of 2–4 presses in the eye), and
the checkpoint memory — frames just before a level turn as what the core looks like.

## The layers behind the screen (same day, later)

Jonathan: "wouldn't the side eyes be seeing behind the screen, and each move would add to each
pixel if it changes? So it would see a topology rather than a line. Walls wouldn't move — the
only thing there would be the color, a thin layer. The end goal doesn't move either, but it
wouldn't share the same colors as the border, so it wouldn't have any layer behind or share
with other parts of the screen. We would want to touch the walls and see that they do nothing
first, so a minimum of 2 layers."

Built as: a per-cell change count (the layers). (1) It is now **input to the eye** — two more
channels, depth = layers so far (capped at 8) and wall = never changed — for the live player
and for eye.py's offline training (`layers()` rebuilds it along each recorded sequence).
(2) It is what the **goal is read from** (`topology()`): walls = one thin layer that never
changed; the mover = the color that keeps adding layers (ls20 → 9, the agent body; vc33 → 4,
the arrow; checked offline); the goal = a blob that never changed whose color is not the
border's, not the background's and not the mover's. The "minimum two layers": nothing is called
a wall or a goal until the first twelve touches are done. The hand steers by rise + **near**
(the mover closer to a goal blob in the imagined frame). Also fixed: the screen's identity for
the repeat penalty now ignores the tick region — with the fuel bar draining, ls20 had pressed
the same wall eight times "on a new screen" each time.

Result (`play_batch_20260903_1244.jsonl`, 25 games × 150 presses): **5 levels** — vc33 L1 at
71 and L2 at 108, su15 L1 at 27 (new), tn36 L1 at 118, m0r0 L1 at 74 (new) — against 4 (rise
only), 3 (curiosity only) and 1 (random hand). Seven different public games have now had a
level cleared by a blank quarter-million-parameter eye learning the game as it presses (ft09,
vc33, r11l, lf52, tn36, su15, m0r0). The trend 1 → 3 → 4 → 5 is real; any single step is
inside the run-to-run noise.

Files: `collect.py`, `eye.py`, `play.py` (planet dir); data, models and runs under
`D:\planet\eye\` (`<game>.npz`, `eye_fold*.pt`, `eye_results.json`, `collect.jsonl`,
`play_<game>.jsonl/.npz`, `play_batch_*.jsonl`).
