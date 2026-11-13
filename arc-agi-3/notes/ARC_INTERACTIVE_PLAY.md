# Interactive-game play notes — Jonathan's own solving process, mapped to the architecture, + the accretion measurement

*Session Aug 2026. Jonathan played the interactive ARC games himself (on s5i5) and reported how he solves
them. This is primary data about the TARGET domain (the game/streamer track, `FOLDING_WHAT_ITS_FOR`), and
almost every observation lands on an existing architecture piece. One observation — the primitive evolving in
play — is measured here (`click_game.py`, figure `click_game.png`). Grounds in `SPHERE_GENERATOR` Part J
(affordance discovery / quest-type), `INNER_SHELL` update 3 (compatibility pooling), the bug-finder repair
drive, and the golden-field reserve (T10–T12).*

## The six observations, mapped
1. **Actions reduce to ~6 buttons; everything else is planning + recognition.** The action space is tiny and
   fixed — the "force" (middle-shell op choice) is small; all the intelligence is in recognising state and
   composing a plan. This is the **underactuated arm** exactly (`ARC_SOLVER_V1` control frame): few actuators,
   coupled effects, the work is in the control/plan not the vocabulary of moves.
2. **Unlocked controls signal the task before acting** ("arrows unlocked tells me something; click available
   tells me I'll have to use that"). The **affordance set is a prior/router** — which controls exist tells you
   what kind of task this is before a single move. This is `INNER_SHELL` **compatibility pooling** (load the
   compatible primitive subset, routed by features) and `SPHERE_GENERATOR` J.1 **affordance discovery**
   ("*push* wasn't in your action set until the environment allowed it — operator induction by interaction").
   The unlocked controls ARE the routing signal.
3. **Never undo/reset; keep the mistakes and fix them forward, even at the cost of the round.** No backtracking
   — the **bug-finder residual→0 repair** drive, not tree search with rollback. The kept mistake is **debris /
   a dead drone that marks where not to go** (`ARC_DRONES`). Reset is used only to **probe determinism**: "see
   if the next one is the same or not" — testing whether the environment's rule is fixed.
4. **Probe limits ("see how far things can go") only once solved with time left.** Exploration AFTER
   exploitation, on the **reserve/second-wind budget** (golden-field T10–T12: spend surplus on exploration
   only when the task is secured; a gated, not always-on, curiosity). Boundary-seeking on slack.
5. **"s5i5 is just a click game" = a different inner-core selection with a different toolset + watching
   different parts.** The game type selects the **shell configuration**: which pool of primitives is loaded and
   which parts of the scene get attention. Different game → different outer shell, different tool pool,
   different perceptual focus — the per-domain routing that pooling enables.
6. **A control primitive EVOLVES by accretion:** "+blue" → "+blue opposite side of grey" → "defined by that
   horseshoe button" → "added impassible too." A bare op grows (a) a **relational qualifier** (opposite grey),
   (b) a **trigger binding** (fires on the horseshoe shape), (c) a **constraint** (impassible). This is a
   generator's parameter space growing — the **op-generation grind (`ARC_OPGEN`) observed in a human**, and
   `SPHERE_GENERATOR` J.1 operator-induction-by-interaction. Measured below.

## Measured: primitive accretion (`click_game.py`, 4000 self-generated levels, exact ground truth)
A tiny-action click game (one action: place blue). One primitive accretes through Jonathan's four stages;
each accretion is **forced by the specific failures of the previous stage** (he keeps the mistake and adds the
condition that explains it). Per stage: CORRECT (blue on target), WRONG (fired but missed = "cost the round"),
ABSTAIN (didn't fire).

| stage | primitive | correct | WRONG | abstain |
|---|---|---|---|---|
| 0 | `+blue` (click centre) | 5.9% | 94.1% | 0 |
| 1 | `+blue opposite grey` (relation) | **38.6%** | 61.4% | 0 |
| 2 | `+ gated by the horseshoe` (trigger) | 38.6% | **18.7%** | 42.6% |
| 3 | `+ impassible` (constraint) | **57.4%** | **0.0%** | 42.6% |

- **Stage 1 (the relation) is the big jump** — 5.9% → 38.6%. Naming *what it acts relative to* is most of the
  primitive.
- **Stage 2 (the trigger gate) converts costly WRONGs into honest ABSTAINS** (61%→19% wrong; 1706 levels move
  wrong→abstain). This is precisely "I keep the mistake but stop making the costly one once I know the trigger":
  on levels the primitive doesn't own (a *different* quest), it now stays out instead of firing wrong.
- **Stage 3 (the constraint) recovers the blocked sub-case and drives WRONG to 0** — 38.6%→57.4% correct, and
  every fire is now correct. The accreted primitive **never costs the round**; where it can't be sure, it
  abstains.

**Endpoint (honest):** a primitive that fires only in its domain (the horseshoe/opposite-grey family), is
**never wrong there**, and **abstains on the 42.6% that are a different quest** — which is exactly what a
*pooled* primitive should be: correct-or-silent, ready to be routed by affordance (obs. 2/5) alongside the
other-quest primitive. The accretion IS the "fix it forward" (obs. 3): each condition is the repair of a
named failure, no undo required.

## Why this matters for the build
The accretion curve is the op-generation grind (`ARC_OPGEN`) seen from the inside: a generated op isn't born
whole — it's a **bare op + accreting (relation, trigger, constraint) parameters**, and the honest gate is what
makes each stage safe (fire only when the added condition holds, else abstain). It says the generator families
to build next aren't just new *base* ops but **enrichment operators**: given a primitive that circles, try
adding (i) a relation-to-a-reference, (ii) a trigger/shape gate, (iii) a passability/constraint mask — the
three accretion moves Jonathan used. That's a concrete, small, high-yield next grind set, and it doubles as
the game-track primitive-growth mechanism (same engine, different outer shell).

*Honest bound: the click game is a synthetic testbed (self-generated, exact truth) built to isolate the
accretion mechanism Jonathan reported — clean numbers, toy scale, no claim about the real ARC-3 environment
(not loaded here). The mapping of observations 1–5 to architecture pieces is design grounding, not new
measurement. `click_game.py`; scripts live in the session.*
