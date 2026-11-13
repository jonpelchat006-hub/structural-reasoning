# Probe-first — build a definition for every element before pursuing the goal (Jonathan's play discipline)

*Session Aug 2026. Companion to `ARC_INTERACTIVE_PLAY` (observation #8) and `ARC_STAGED_ARMS`. Jonathan:
"I never start with the main goal even when obvious — I know there's one but I have to do other things first,
and figure out what each thing does before moving on. Some subgoals are 'what is this?', which then turn into
a task on the real goal path. I make sure I have a definition for each colour on screen; if I see red squares
I get at least one interaction with them, and they come in pairs so I watch how they interact." Measured:
`world_probe.py`, figure `world_probe.png`. Grounds in `SPHERE_GENERATOR` J.1 (forward-probe / affordance
discovery / operator-induction-by-interaction) and the discovery loop (#49/#50).*

## The claim
Building the element-definition table BEFORE chasing the goal pays whenever elements have hidden,
consequential meanings. The exploratory "what is this?" subgoals convert into real goal-path tasks (discover a
key → the subgoal becomes "fetch the key first").

## Testbed (grid world, hidden semantics, exact truth)
Grid with start and goal. Each colour has a HIDDEN role, unknown to the agent: **wall** (impassable),
**hazard** (stepping on it loses the round), **key/lock** (the goal is LOCKED; touching a key cell — the
paired "red spots" — opens it), **neutral**. A lost round costs +60 (Jonathan keeps mistakes, but a hazard or
lockout costs the round).
- **goal-rush**: head straight for the goal; learns a wall only by bumping (replan), a hazard only by dying on
  it, the lock only by arriving shut. No definitions built.
- **probe-first**: spend ONE safe interaction per distinct colour (observe from adjacent → reveals its class;
  the key/lock pair reveals the unlock relation), build the table, THEN plan — fetch a key if locked, avoid
  hazards, route around walls.

## Measured (1500 worlds per point, sweeping the consequential fraction)
| consequential colours | goal-rush success | goal-rush cost | probe-first success | probe-first cost |
|---|---|---|---|---|
| 0% (all neutral) | 100% | **16.0** | 100% | 25.5 |
| 25% | 58.1% | 40.7 | 99.9% | 25.6 |
| 50% | 31.6% | 56.0 | 99.3% | 25.9 |
| 75% | 14.3% | 65.8 | **98.9%** | 26.1 |
| 100% | 6.3% | 70.2 | **97.7%** | 26.5 |

At 75% consequential, goal-rush's failures split cleanly into the two hidden semantics it never learned:
**671 hazard deaths + 612 locked-goal arrivals** (of 1500). Probe-first learns both upfront and stays
~98–100% at a **flat ~26 cost**, while goal-rush's cost balloons from lost rounds.

## What the numbers say
- **When meanings are unknown and consequential (the real game), probe-first dominates** — near-perfect
  success at flat cost, vs a goal-rush that dies or gets locked out and pays the round penalty. The cheap
  upfront survey ("a glance per colour") prevents the expensive goal-path failures.
- **The pair interaction is load-bearing**: discovering the key/lock relation (the paired red squares) is what
  converts "what is this red thing?" into the concrete subgoal "touch a key before the goal" — exactly
  Jonathan's "subgoals that turn into tasks on the real goal path." Without it the goal is unreachable.
- **Honest bound (the crossover):** when NOTHING is consequential (0%), probing is pure overhead — goal-rush
  wins on cost (16 vs 25). So the discipline is **calibrated to unknown consequence**, not applied blindly:
  you probe to get definitions, and you only spend MORE exploration ("see how far things go") once the task is
  secured with time left (the reserve/second-wind budget, `FOLDING`/T10–T12). Probe what you don't know; don't
  over-probe what you do.

## For the build
This is the **front-stage `SPHERE_GENERATOR` Part J** made measurable: before laying a line at the target,
survey the affordances and classify each element (operator-induction-by-interaction). Concrete solver levers:
- **A definition pass before search**: for each distinct element/colour, run the known actions once and record
  its effect class (blocks / removes / moves / unlocks / inert). Cheap, and it prunes the plan space hard
  (avoid hazards, route around walls, sequence keys) — the same saving as staging (`ARC_STAGED_ARMS`), from
  knowing the pieces rather than from ordering the subgoals.
- **Interaction-derived primitives**: an element's learned effect IS a local primitive minted by the
  environment ("push wasn't in your set until the world allowed it") — feed it straight into the op-generation
  spine (`ARC_OPGEN`) as a task-local generator, gated as always.
- **Pairs/multiples first**: when an element appears in pairs/multiples, probe the RELATION (does touching one
  affect the other?) — the highest-information probe, and the one that reveals key/lock, source/sink,
  template/copy structure.

*Honest bound: synthetic world, exact truth, built to isolate the probe-first effect Jonathan reported. The
dominance is real and large in the unknown-consequential regime and reverses to overhead in the all-neutral
regime — the crossover is the finding, not a universal win. No claim about the real ARC-3 environment (not
loaded). `world_probe.py`; scripts live in the session.*
