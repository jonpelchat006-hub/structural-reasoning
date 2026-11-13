# Two planes — the button path (normal) and the meaning behind it (orthogonal), the rotation, and the middle-shell notes + recursion-level scope

*Session Aug 2026. `ARC_INTERACTIVE_PLAY` #9 capstone (the two planes), extended with two later placements
(the window writes only to the middle shell; "global" = the current recursion level's border) and the
type-generalization measurement. Measured: `two_planes.py` (planes), `type_gen.py` (type-generalization),
figures `two_planes.png`, `type_gen.png`. Grounds in `FOLDING_OBSERVERS`, `FOLDING_REBASING`,
`FOLDING_GALAXY_BRIDGE` (element-invariance), `INNER_SHELL` (compatibility pooling).*

## The two planes (recap)
Normal plane = φ = the real path = the button sequence. Orthogonal plane = ψ = the MEANING = the subgoal
dependency DAG. "Rotate to cover" = project the meaning onto a valid button order. A) one meaning realises up
to hundreds of button-orders (fan-in mean 5.7→417 as K grows); B) on a break the meaning rotates to a valid
new path (85%) while a flat sequence violates a forgotten dependency (~1/3). The full unification of drones =
fan-in, keep-and-repair = rotate, probe-first = build the DAG, staging = choose one extension is in the body
below (unchanged).

## Placement 1 — the window writes only to the MIDDLE shell (where the notes live)
At its angle/position the window does not touch the inner core (innate, data-free, **read-only** —
`FOLDING_TRAMPOLINE` §8 / `FOLDING_REBASING`: Ramachandran-style certified foundation) and the outer shell is
the environment (**we can't write it**). The only layer that can *add* is the **middle shell — the learned
models**. So the fill-void store (`ARC_VOID_FILL`: hypotheses, diagnosis, frustration tag, things-to-try) is a
**middle-shell object** — the one writable scratchpad. This is the architectural home of the notes/context: not
the innate core, not the environment, but the learned middle where the models keep their working state.

## Placement 2 — "global" = the border of the current RECURSION LEVEL; click descends at a spot
"Global" is not the whole image. It is the **border of wherever you currently are** in the recursion
(`ARC_RECURSIVE_VOID`; `SPARSE_VESICA` §11.7 "an atom AND a bond-site"). Jonathan's actual hierarchy on the
horseshoe game: **board → the grey border → each side → the squares**, and **clicking descends to level 3 at
that spot**. So you *select* a border (decide where/what to click), **watch that border** (recognise by the
outline, not a single pixel change), and descend. This gives the principled fix for the Set C null
(`ARC_OPGEN`): scope the op to the **element's border at its recursion level**, not a whole-board global op.

## Placement 3 (measured) — a type is an INVARIANT: one instance teaches all same-type instances
Jonathan: "once I figured out one control switch, the other colored switches do the same thing." A type is an
**invariant** — `FOLDING_GALAXY_BRIDGE`: *"a material used as an element is an invariant (iron is iron
everywhere) — no source check."* So recognise an element by its **border/shape signature** and every instance
of that type **shares the operator**: induce ONCE per type, apply to all — compatibility pooling by type
(`INNER_SHELL` update 3), not per pixel.

**Measured (`type_gen.py`, 400 boards, 3 types):**
| instances/board | PER-INSTANCE (induce each) | TYPE-GEN (induce once/type) | saving |
|---|---|---|---|
| 4.5 | 4.5 interactions | **3.0** (flat = #types) | 1.5× |
| 7.7 | 7.7 | **3.0** | 2.6× |
| 10.9 | 10.9 | **3.0** | 3.6× |

Both **100% correct**; TYPE-GEN has **0 false-generalisations** (the border signature distinguishes types, so
"same-type does the same" holds exactly). TYPE-GEN's cost is **flat at the number of types** regardless of
instance count, so the saving grows as instances-per-type — the more copies of a switch, the more one
induction buys. This is Jonathan's blue-switch insight, quantified, and it is the same mechanism as ARC's
`obj_recolor_by_shape` (one rule over a shape-class), now framed as learn-one-reuse-all by border.

## What these change for the build
- **The notes store is middle-shell** — a writable working memory beside the models, carrying the fill-void
  diagnoses across tasks/levels (the accumulating to-try list of `ARC_VOID_FILL`).
- **Op scope = the element's border at its recursion level, shared across its type.** This is the corrected
  Set C: localise via the re-based border (`ARC_RECURSIVE_VOID`) → induce a local op (P1 small/local,
  `ARC_HYPOTHESIS_TEST`) → **generalise it to every same-border instance for free** (this doc). Three measured
  pieces compose into one op-form: local, recursion-scoped, type-shared.
- **Recognition is by border, not pixel** — track the outline across frames; a colour change on one instance
  predicts the same on its type-mates (reference the learned one).

## Honest bounds
Type-generalisation is synthetic (border signature = a clean 6-bit stamp; real borders need the re-based
segmentation of `ARC_RECURSIVE_VOID` and a tolerance band). The saving is exactly instances-per-type and no
more — it does nothing for singleton types. Placements 1–2 are architectural readings grounded in the corpus,
not new measurements; Placement 3 is measured. No claim about the real ARC-3 environment (not loaded).
`type_gen.py`, `two_planes.py`; scripts live in the session.

---

## (original two-plane measurements retained below)
Normal plane = the button sequence; orthogonal plane = the subgoal dependency DAG; "rotate to cover" = a linear
extension. Fan-in mean 3.7 (K=3) → 417 (K=8); break-robustness meaning 85% vs flat sequence ~64%; the two
diverge with complexity. Unifies drones (fan-in), keep-and-repair (rotate), probe-first (build the DAG),
staging (one extension). `two_planes.py`.
