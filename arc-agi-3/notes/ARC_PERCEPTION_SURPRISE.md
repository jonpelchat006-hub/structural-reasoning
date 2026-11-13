# Perception + surprise — the detector reads frames over time; surprise validates the path and marks the goal

*Session Aug 2026. The perception layer for the game loop (`ARC_GAME_LOOP`). Jonathan: perception is the
detector looking at the screen through the angled window between the floor (φ / real path) and the orthogonal
plane (ψ); feed a frame between each action, dissolve/segment it (flood-until-balance), and read SURPRISE —
"expect no surprise on the way, one surprise at the goal." `perception_surprise.py`, figure
`perception_surprise.png`. Grounds in `FOLDING_TWO_SIDED_WINDOW` (the two-cone φ/ψ window, accept-where-agree),
`FOLDING_MOVEMENT` ("movement needs TIME → the model becomes a VIDEO, not stateless images — the detector's
problem"), `FOLDING_COMBINE_MEMBRANE` (flood/basin to balance = a segment), `MINING_NOTES` #14 (surprise-gated
compute).*

## The idea, made literal
- **Perception = the detector on the screen.** The observer committee reads each frame; agreement = the stable
  invariant (the floor/φ), disagreement = depth/motion (the orthogonal/ψ). The frame is dissolved and
  **segmented by flood-until-balance** (label diffusion to equilibrium → a region = a unit to process).
- **A frame between each action** turns the stateless-image detector into a **video** — the fix
  `FOLDING_MOVEMENT` names.
- **Surprise = prediction error** between the world-model's predicted next frame and the actual one.
- **Jonathan's rule:** on a correctly-understood path, expect **no surprise en route** and **one surprise at
  the goal**. Surprise then does three jobs: ≈0 en route = the path is understood (keep burning it); >0 en
  route = the model is WRONG here → re-probe / re-collapse; the one at the goal = the win-condition firing.

## Measured (MicroGame frames, grid, hidden roles, locked goal + key)
**A) The profile holds exactly.** On a clean static run with a correct model: surprise = **0 on every one of
the 24 en-route frames**, then **8 at the goal** (the exit/lock opens — the expected terminal surprise).

**B) Surprise is a perfect win-detector (when the model is right).** Over **7,996 en-route frames** across 400
worlds: surprise mean **0.00**, max **0**. Every goal frame = **8**. **Clean separation: every goal surprise >
every en-route surprise.** So surprise perfectly separates "goal reached" from "on the way," and — the
contrapositive — **any en-route surprise is an unambiguous model-error flag.**

**C) An en-route surprise is the re-plan trigger (hidden dynamics).** Add a **drifting hazard** the static
model didn't know (a moving red square). The surprise fires the moment the frame diverges from prediction.

| agent | success | hazard deaths |
|---|---|---|
| surprise-BLIND (ignores it) | 88.3% | 127 |
| surprise-MONITOR (model the drift, wait it out) | **95.7%** | **16** |

Detecting the surprise and responding (learn the world has a hidden dynamic, model the drift, **wait a tick**
for the transient hazard to pass) lifts success +7.4 pts and cuts deaths **8×**. The residual 16 are cases
where the drifter arrives with no time to react.

## Honest note on how C was earned
The first monitor was WORSE than blind (82.3% vs 88.3%): it detected the surprise perfectly but its *response*
was crude — it avoided the drifter's cell and either thrashed (stuck) or declared the goal unreachable
(no_path 249×) when the transient hazard merely blocked the route for one tick. Two fixes made the response
sane: on a surprise, **wait** rather than step; and treat "no path right now" from a *transient* dynamic as a
**wait**, not a failure. Detection was always perfect; the win came from fixing the reaction. The intermediate
null is recorded because it is the honest lesson: **surprise-as-signal is trivially reliable; surprise-as-
control needs a real policy.**

## Where it plugs into the loop
This is the ψ-1/ψ-2 front-end of `ARC_GAME_LOOP` made real on pixels-over-time instead of a handed-in state:
- **Perception (detector + video frames)** replaces the sim's handed-in definitions — the roles come from
  reading and segmenting frames.
- **Surprise** is the runtime monitor over the whole cycle: burn the φ path while surprise ≈ 0; on an en-route
  surprise, re-expand to ψ (re-probe/re-collapse — `ARC_TWO_PLANES`); treat the terminal surprise as the win.
- **Flood-until-balance segmentation** is the same basin geometry the ARC union synthesizer routes on
  (`FOLDING_COMBINE_MEMBRANE`) — one mechanism for "what is a piece on the screen."

## Honest bounds
Synthetic MicroGame frames, exact truth; the detector here is a clean predicted-vs-actual diff, not the real
observer-committee on raw pixels (that is the detector project, `STATE_OF_THE_DETECTOR`, still at semantic-AUC
0.93 and no localisation). The surprise profile's perfection is a property of a *correct* model on a *static*
world; the whole point of C is that real worlds aren't static, and there the signal degrades gracefully into a
re-plan trigger rather than breaking. No claim about the real ARC-3 environment (not loaded).
`perception_surprise.py`; scripts live in the session.
