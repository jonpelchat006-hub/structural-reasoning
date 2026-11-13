# Staged arms — solving by subgoal factors a product search into a sum (Jonathan's place-then-fill)

*Session Aug 2026. Companion to `ARC_INTERACTIVE_PLAY` (observation #7). In the shapes-over-dots game Jonathan
solves in STAGES: first place every shape on its dot (position subgoal), checkpoint, then take them all to the
colour fill (colour subgoal) — "setting up multiple arms," one per subgoal, in sequence, not object-by-object
end-to-end. Measured: `stage_arms.py`, figure `stage_arms.png`. Grounds in `SPARSE_VESICA` §18 (the synthesis
tree of 3-part sub-reactions) and the arm/spotlight frame (`ARC_SOLVER_V1`): each arm reaches a sub-spotlight.*

## The claim
Factoring a task into a solvable ORDER of subgoals (position, then colour) collapses a **product** search
space into a **sum**. Multiple arms in sequence, each with its own checkpoint, beat one arm searching the
joint space.

## Testbed: place-and-fill (self-generated, exact truth)
K slots, each a dot needing a shape and a colour. K scattered objects (shapes matching the slots, wrong
current colours). Goal: every slot filled by a shape-matching object recoloured to the slot's colour. The
game's rule (faithful to real play): **a shape's target colour is only readable once it sits on its dot** —
the dot's colour becomes visible there. So you can't colour-match before you place.

- **JOINT (do it all at once):** commit (slot, colour) per object; colour must be **guessed blind** and only a
  completed board reveals correctness (global check). Wrong colour guesses dead-end only at full depth → the
  solver grinds ~Cᴷ colour combinations.
- **STAGED (multiple arms):** arm 1 places every shape by SHAPE (verifiable per step) → **checkpoint** (all on
  dots) unlocks the colour oracle → arm 2 fills colour, one read per object.

## Measured (120 puzzles/K, C=4 colours; search expansions counted)
| K | JOINT expansions | STAGED expansions | ratio | joint solved |
|---|---|---|---|---|
| 2 | 11.6 | 4.4 | 2.7× | 120/120 |
| 3 | 52.2 | 7.1 | 7.4× | 120/120 |
| 4 | 347.7 | 9.9 | 34.9× | 120/120 |
| 5 | 3,118.8 | 12.6 | 247× | 120/120 |
| 6 | 23,472.9 | 15.6 | 1,506× | 120/120 |
| 7 | 211,845.9 | 19.4 | **10,896×** | 114/120 (6 hit the 1M cap) |

**Joint grows ~Cᴷ (exponential); staged grows ~K (linear).** By K=7 the joint solver is ~11,000× more
expensive and has started **failing** (hitting the cap), while staged always solves in <20 expansions.

## Why it works, and the honest bound
Staging wins because the **checkpoint makes the second subgoal's oracle available**: once a shape is on its
dot, its target colour is readable, so arm 2 is a per-object read instead of a blind Cᴷ guess. This is exactly
why Jonathan places first. The requirements (honest bound):
1. the subgoals must be **separable** (position ⟂ colour here);
2. the environment must **unlock the second oracle at the checkpoint** (the dot's colour becomes visible on
   contact) — if colour stayed blind after placement, staging wouldn't help;
3. you must pick the **right order** (position enables colour, not the reverse). Finding that order is the
   recognition step — "find out where they go first."

## For the build
This is the **synthesis-tree / reaction-network** (`SPARSE_VESICA` §18) made concrete and measured: a sub-
reaction's product (shapes placed) plugs in as the reactant of the next (colour fill). In the arm/spotlight
frame, staging = reaching a **sequence of sub-spotlights**, each verified before the next, rather than one
spotlight in the product space. Two concrete levers for the solver track:
- **Subgoal detection**: before searching, test whether the target factors (does a shape/position-only
  transform get partway, leaving a pure colour residual?). If so, stage it — solve the position residual to a
  checkpoint, then the colour residual. This is a cheap front-end that could turn some deep joint reaches into
  two shallow ones (relevant to the circlers and to multi-step eval tasks).
- **Checkpoint verification**: each arm's endpoint is independently exact-checkable — the same honest gate,
  applied per stage, so a wrong first arm is caught before the second is even attempted.

*Honest bound: synthetic testbed, exact ground truth, built to isolate the staging effect Jonathan reported;
the Cᴷ-vs-K separation is real and large, but it assumes the factorisation and the checkpoint-unlocked oracle
(both true in the shapes-over-dots game). No claim about the real ARC-3 environment (not loaded).
`stage_arms.py`; scripts live in the session.*
