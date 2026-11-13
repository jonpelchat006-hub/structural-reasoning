# ARC op-generation — the grind ledger (the middle shell PROPOSES ops; the eval wall keeps moving)

*Session Aug 2026. Op-generation spine + grind. Each generator reads a task's train pairs and SYNTHESISES a
candidate op, kept only if it reproduces every train pair exactly (abstain otherwise); the whole library runs
per task (arm → inducers → prior → generators, direct and folded onto the closest approach). `arc_gen.py`
(Set A), `arc_gen2.py` (Set B + fill-void gate), `arc_gen3.py` (Set C — null). Figures `arc_opgen.png`,
`arc_ladder.png`. Living grind ledger — each set appends here.*

## The ladder (measured)
| stage | train | eval |
|---|---|---|
| cheap floor | 3.8% | — |
| v1 library | 7.0% | 0.2% |
| v2 arm | 7.0% | 0.8% |
| + mechanical induction | 8.2% | 0.8% |
| + prior-derived ops | 8.5% | 0.8% |
| + op-gen Set A | 10.2% (41/400) | 1.5% (6/400) |
| + op-gen Set B | 11.0% (44/400) | 2.0% (8/400) |
| + op-gen Set C (enrichment) | 11.0% (44/400) | 2.0% (8/400) — **null** |

**Eval went 0.2% → 2.0% (10×) across Sets A–B; Set C added nothing.** All exact held-out solves, train-gated.

## Set A — object-relational + selection
periodic_fill (train +4, EVAL +2), move_vec (+1), recolor_by_prop{size,height,width} (EVAL +1). Built &
abstaining: flood_by_encloser, keep_predicate, bbox_solid/hollow.

## Set B — new families + the fill-void diagnosis gate (`arc_gen2.py`)
- **connect_newcolor** (connect aligned same-colour cells with a learned line colour): train +3, EVAL +1
  (`aa18de87`, verified).
- **count→emit** (output a function of object count): train +1, EVAL +1 (`e872b94a`, verified).
- Built & abstaining: recolor_by_enclosing, sym_complete_newcolor, obj_gravity_contact.
- **Fill-void gate**: unsolved tasks store a closest-family diagnosis; **90 eval circlers (agree ≥0.9)** = the
  frustration map of where breadth is still needed.

## Set C — enrichment operators: an HONEST NULL, predicted by our own hypothesis (`arc_gen3.py`)
Built the accretion forms — **recolor_by_reference** (relation: recolour objects to the largest/smallest/
unique object's colour), **recolor_by_neighbor**, **barrier_move** (constraint: gravitate objects but stop at a
learned barrier colour). All verified to run correctly; **0 landings, train and eval unchanged**.

**Why (and it's the useful part): the null was predicted by `ARC_HYPOTHESIS_TEST` P1.** That test measured the
circler residual to be **small & local** (median 5.5% of cells, 3 connected components). But these Set C ops act
**globally** (recolour *every* object, move *every* object), so they change far more than the tiny residual and
cannot reproduce train. I generated the right diagnosis (localise; the op is local) and then built ops that
didn't respect it. **The corrected build is residual-scoped:** run the arm to closest approach, localise the
gap with the *supervised* train residual (P1 small/local; P2 says NOT via drone-disagreement), and induce a
correction **only inside that region** — a region-gated local op, not a global one. That is the next set.

## Why generated ops generalise (Sets A–B)
A fixed library memorises train task-types (eval 0.2%); a generator stores a **procedure that reads the task**
(this grid's period, this task's count→output map, this task's line colour), so it fires on unseen tasks and
the exact-train gate makes it abstain rather than guess — a 10× eval climb with zero memorisation.

## The grind, honestly
Breadth is the climb; each *fitting* family adds a few tenths of a %, and a *mis-shaped* family (Set C) adds
nothing — the shape of the op must match the residual. The fill-void frustration map + the P1 locality result
now point the next set precisely: **residual-scoped local enrichment** on the 90 circlers. Honest state: **11.0%
train / 2.0% eval**, every solve exact and train-gated; Set B eval solves verified non-degenerate; Set C a clean,
diagnosed null. Scripts (`arc_gen.py`/`arc_gen2.py`/`arc_gen3.py`) live in the session.
