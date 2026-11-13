# The game-loop skeleton — five play-observations assembled as the ψ↔φ (quantum↔classical) cycle

*Session Aug 2026. The runnable integration Jonathan asked for: probe → build the meaning DAG → collapse to a
staged, gated button line → execute → re-collapse on a block. `game_loop.py`, figure `game_loop.png`.
Capstone of `ARC_PROBE_FIRST`, `ARC_TWO_PLANES`, `ARC_STAGED_ARMS`, `ARC_INTERACTIVE_PLAY` (accretion),
`ARC_DRONES`. Grounds the two planes in the classical/quantum split of Shovelcat Theory 10 (Table 16).*

## The unification Jonathan named
The two planes ARE the ψ/φ duality of the earlier theory (Shovelcat Theory 10, Table 16 — *ψ-domain*:
wavefunction, **parallel superposition**, high entropy = exploration; *φ-domain*: trajectory, **serial
definite outcome**, low entropy = execution; **collapse = ψ→φ**, many possibilities → one, irreversible):
- **ORTHOGONAL plane = ψ** = the meaning: a **superposition of all valid paths**, held as the subgoal
  dependency DAG (the "fuzzy layer / the light showing the surroundings"). This is the drone cloud.
- **NORMAL plane = φ** = the real path: **one definite button/subgoal sequence** — a collapse of ψ.
- **"Rotate to cover the real path" = collapse** (ψ→φ): project the meaning onto one executable order.
- **A blocked button = re-expand to ψ and collapse elsewhere** — keep the meaning, no undo.

## The loop (runnable, `game_loop.py`)
Per playthrough of MicroGame (grid, hidden hazards/walls, locked goal needing a key, 2 shapes each needing
place-then-fill):
- **ψ-1 PROBE** → build the element-definition table (roles known safely, hazards to avoid). *(probe-first)*
- **ψ-2 BUILD DAG** → the meaning superposition: subgoals {place_i, fill_i, key, goal} with edges
  `fill_i ← place_i`, `goal ← key ∧ all fill_i`. *(two-plane orthogonal / drone cloud)*
- **φ-1 COLLAPSE / ROTATE** → pick a ready subgoal (prereqs met), preferring non-goal first so the **staged**
  order emerges (all places+fills, key, then goal); each action **gated** (fire only where valid, route around
  hazards). *(staging + accretion)*
- **φ-2 EXECUTE** → serial definite run; on a **block** (a button that won't press this tick), **RE-COLLAPSE**
  to another ready subgoal — rotate to a different linear extension rather than fail. *(drones / keep-and-repair)*

## Measured (MicroGame, 2000 seeds, 11×11)
| agent | success | mean cost |
|---|---|---|
| FLAT goal-rush (no meaning) | **0.0%** | 101.1 |
| ASSEMBLED ψ↔φ | **95.3%** | 53.5 |

The flat baseline fails completely — **1477 hazard deaths + 510 locked-goal arrivals** — because it has no
definition table and no dependency meaning: it walks onto unknown hazards and arrives at a goal it never
unlocked. The assembled agent solves 95.3% at **half the cost**. The residual 5% "stuck" are genuine DAG
bottlenecks (a subgoal cell walled/hazard-locked off, or a persistent block) — the honest `ARC_TWO_PLANES`
bound reappearing in the integrated system: the orthogonal plane is exactly as robust as the structure allows
alternatives.

## One annotated playthrough with a block (seed 2, SOLVED at cost 50)
```
ψ-1 PROBE: defined 19 elements (hazards, walls, key, 2 dots)
ψ-2 BUILD DAG: 6 subgoals, edges fill←place, goal←key & all fills
  φ block on place0  → re-collapse (rotate) to another ready subgoal
  φ execute: place1 → place0
  φ execute: fill0, fill1        (staged: fill after place)
  φ block on key     → re-collapse (rotate)
  φ execute: key → goal
```
Every facet fires in one run: the definition pass (probe), the DAG (meaning), the staged order (place before
fill, key before goal), the collapse to a definite line, and two re-collapses when buttons blocked — no undo,
the meaning preserved across both breaks.

## Status and honest bounds
This is a **skeleton on a synthetic MicroGame**, not the real ARC-3 environment (not loaded). What it
demonstrates is that the five separately-measured play-observations **compose into one coherent runtime** and
that the composition is a large, real win over a memoryless baseline in a world with hidden consequential
semantics. What it does NOT yet contain: perception from raw pixels (the definitions are handed by the sim,
not induced from a screen), true operator-induction-by-interaction (roles are revealed, not learned by
minting a primitive), and a learned model choosing the collapse order (here it's a heuristic topo-sort). Those
are the next layers — and each maps onto an existing piece: perception → the ARC generator/perception rung;
operator-induction → the op-generation spine (`ARC_OPGEN`); learned collapse → the middle-shell model as the
arm-mover. The skeleton is the scaffold they slot into. `game_loop.py`; scripts live in the session.
